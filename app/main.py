import os
from dotenv import load_dotenv
import discord
import asyncio
import aiohttp
from fastapi.responses import StreamingResponse
import aiofiles
import io
from aiohttp import ClientSession
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Form
from pydantic import HttpUrl
from urllib.parse import urlparse
import argparse
from datetime import datetime
from urllib.parse import urlparse, unquote

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
key = eval(os.getenv('AES_KEY'))
# cipher = AES.new(key, AES.MODE_CBC)
MODE = AES.MODE_GCM
FILE_SIZE = 8*1024*1024
CHUNK_SIZE = FILE_SIZE
LIMIT = 1000
CHANNEL_ID_STORAGE = 1178285965056417862
CHANNEL_ID_RECORDS = 1178293013466849381


app = FastAPI()


origins = [
    "http://localhost:5173",  # Your Svelte frontend
    "http://127.0.0.1:5173", # Add this if accessing via 127.0.0.1
    "http://localhost:8000", # Include your backend
    "http://127.0.0.1:8000", # Add this if accessing backend via 127.0.0.1
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.post("/api/upload/")
async def create_upload_file(file: UploadFile):

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
        'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
    }

    # Use aiofiles to read the file in chunks and update progress
    chunk_size = FILE_SIZE  # 8 MB chunks
    sha1 = hashlib.sha1()
    nonce = get_random_bytes(12)
    cipher = AES.new(key, MODE, nonce)
    message_ids = []
    counter = 0
    uploaded_size = 0

    async with aiofiles.open(file.filename, "wb") as buffer:
        while content := await file.read(chunk_size):
            uploaded_size += len(content)
            sha1.update(content)
            # Encrypt data
            encrypted_chunk = cipher.encrypt(content)
            await buffer.write(encrypted_chunk)

            # Simulate uploading the chunk to Discord
            message = await channels['storage'].send(
                "",
                file=discord.File(fp=io.BytesIO(encrypted_chunk), filename=f"{file.filename}_{counter}")
            )
            message_ids.append(str(message.id))
            counter += 1

    # Record metadata in 'records' channel
    await channels['records'].send(
        f"{file.filename}\n{sha1.hexdigest()}\n{nonce}\n{uploaded_size}",
        file=discord.File(io.BytesIO(bytes(",".join(message_ids), encoding="UTF-8")), filename="message_ids")
    )

    return {"message": "File uploaded successfully"}


@app.post("/api/upload_url/")
async def upload_file_from_url(url: str = Form(...)):
    parsed_url = urlparse(url)
    filename = unquote(os.path.basename(parsed_url.path))

    # Fetch the file from the URL using streaming
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed to fetch URL with status code {response.status}"
                )
            
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded_size = 0

            # Fetch the Discord channels
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)
            await client.login(TOKEN)

            channels = {
                'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
                'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
            }

            # Read in chunks
            temp_file = io.BytesIO()
            async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                temp_file.write(chunk)
                downloaded_size += len(chunk)

                # Log progress (optional: useful for debugging)
                print(f"Downloaded {downloaded_size}/{total_size} bytes")

            temp_file.seek(0)
            await send_file(
                UploadFile(filename=filename, file=temp_file),
                channels
            )

    return {"message": "File uploaded successfully"}


@app.get("/api/file/{filename}")
async def read_item(filename: str):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
        'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
    }

    async for msg in channels['records'].history(limit=LIMIT):
        temp = msg.content.split("\n")
        if temp[0] == filename:
            if len(temp) == 4:
                file_size = int(temp[-1])
            else:
                return RuntimeError("Error Filesize not found")
    
    f = download_file(filename, channels)
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Length": str(file_size)
    }
    return StreamingResponse(f, media_type="application/octet-stream", headers=headers)


@app.get("/api/update_file_sizes/")
async def update_file_sizes():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
        'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
    }

    await update_missing_file_sizes(channels)
    await client.close()

    return {"message": "File sizes updated"}

async def update_missing_file_sizes(channels: dict[str, discord.TextChannel]):
    records_channel = channels['records']
    storage_channel = channels['storage']

    async for msg in records_channel.history(limit=LIMIT):
        temp = msg.content.split("\n")
        print(f"Cheking {temp[0]}")
        # Check if message has only 3 lines (missing file size)
        if len(temp) == 3:
            filename = temp[0]
            message_ids_file = msg.attachments[0]

            # Read stored message IDs
            message_ids = (await message_ids_file.read()).decode("UTF-8").split(",")
            total_size = 0

            # Calculate total file size from stored Discord messages
            for msg_id in map(int, message_ids):
                storage_msg = await storage_channel.fetch_message(msg_id)
                total_size += storage_msg.attachments[0].size  # Get file size from attachment

            # Update the message with the missing file size
            updated_content = f"{msg.content}\n{total_size}"
            await msg.edit(content=updated_content)
            print(f"Updated {filename} with size {total_size} bytes")

@app.get("/api/files")
async def get_files():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
        'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
    }
    files = await get_all_files(channels)
    return files





app.mount("/", StaticFiles(directory="website/build", html=True), name="website")


class Item:
    def __init__(self, info, date):
        self.name = info[0]
        if len(info) == 4:
            self.size = f"{int(info[-1])/(1024**3):0.3f} GB"
        else:
            self.size = "unknown"
        self.date = date
        self.parse_type()

    def parse_type(self):
        end = self.name.split('.')[-1]
        if end in ["mkv","mp4"]:
             self.type = "video"
        elif end in ["mp3","flac","wav","opus"]:
             self.type = "audio"
        else: self.type = "other"

async def get_all_files(channels: dict[str, discord.TextChannel]):
    files = []
    async for msg in channels['records'].history(limit=LIMIT):
        temp = msg.content.split("\n")
        date = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        i = Item(temp,date)
        files.append(i)
    return files

async def file_exists(path, channels: dict[str, discord.TextChannel]) -> bool:
    async for msg in channels['records'].history(limit=LIMIT):
        temp = msg.content.split("\n")
        if temp[0] == path:
            return True
    return False

async def clear_history(channels: dict[str, discord.TextChannel]):
    for key in channels:
        await channels[key].purge(limit=LIMIT)


async def send_file(file: UploadFile, channels: dict[str, discord.TextChannel]):
    nonce = get_random_bytes(12)
    print(f"ENCRYPT NONCE: {nonce}")
    cipher = AES.new(key, MODE, nonce)
    if await file_exists(file.filename, channels):
        # print("Gibt schon")
        return
    sha1 = hashlib.sha1()
    message_ids = []
    counter = 0
    filesize = 0
    while True:
        data = await file.read(FILE_SIZE)
        if not data:
            break
        sha1.update(data)
        message = await channels['storage'].send(f"", file=discord.File(fp=io.BytesIO(cipher.encrypt(data)), filename=f"{file.filename}_{counter}"))
        message_ids.append(str(message.id))
        # print(message)
        filesize += len(data)
        counter += 1
    # nonce_str = nonce.decode("UTF-8")
    await channels['records'].send(f"{file.filename}\n{sha1.hexdigest()}\n{nonce}\n{filesize}", file=discord.File(io.BytesIO(bytes(",".join(message_ids), encoding="UTF-8")), filename="message_ids"))

async def download_file(name: str, channels: dict[str, discord.TextChannel]):
    async for msg in channels['records'].history(limit=LIMIT):
        temp = msg.content.split("\n")
        nonce = eval(temp[2])
        print(f"DECRYPT NONCE: {nonce}")
        cipher = AES.new(key, MODE, nonce)
        if temp[0] == name:
            # print("file found")
            f = msg.attachments[0]
            msg_ids = map(int, (await f.read()).decode("UTF-8").split(","))
            file_name = name.split("/")[-1]
            # with open(f"downloads/{file_name}", 'wb') as f:
            sha1 = hashlib.sha1()
            for id in msg_ids:
                # print(id)
                msg = await channels['storage'].fetch_message(id)
                # print(msg)
                
                data = await msg.attachments[0].read()
                # print(data)
                data = cipher.decrypt(data)
                # print(data)
                # data = unpad(data, 16)
                # print(data)
                sha1.update(data)
                yield data
                # f.write(data)
            ok = sha1.hexdigest()==temp[1]
            print(f"Checksum match {ok}")

async def clear():
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
        'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
    }

    await clear_history(channels=channels)
    await client.close()

# async def main():
#     intents = discord.Intents.default()
#     intents.message_content = True

#     client = discord.Client(intents=intents)
#     await client.login(TOKEN)

#     channels = {
#         'storage': await client.fetch_channel(CHANNEL_ID_STORAGE),
#         'records': await client.fetch_channel(CHANNEL_ID_RECORDS),
#     }

#     await clear_history(channels=channels)
#     await client.close()

# asyncio.run(main())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="FileFrensOnline"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--mode", choices=['clear', 'website'], default='website')
    result = parser.parse_args()
    
    if result.mode == "clear":
        asyncio.run(clear())
    if result.mode == "website":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
