import os
from dotenv import load_dotenv
import discord
import asyncio
import io
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import argparse


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
key = eval(os.getenv('AES_KEY'))
# cipher = AES.new(key, AES.MODE_CBC)
MODE = AES.MODE_GCM
FILE_SIZE = 24*1024*1024
LIMIT = 1000

app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload/")
async def create_upload_file(file: UploadFile):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(1178285965056417862),
        'records': await client.fetch_channel(1178293013466849381),
    }
    await send_file(file, channels=channels)

@app.get("/api/file/{filename}")
async def read_item(filename: str):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(1178285965056417862),
        'records': await client.fetch_channel(1178293013466849381),
    }
    f = download_file(filename, channels)
    return StreamingResponse(f, media_type="application/octet-stream")

@app.get("/api/files")
async def get_files():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(1178285965056417862),
        'records': await client.fetch_channel(1178293013466849381),
    }
    files = await get_all_files(channels)
    return files





app.mount("/", StaticFiles(directory="website/build", html=True), name="website")



async def get_all_files(channels: dict[str, discord.TextChannel]):
    files = []
    async for msg in channels['records'].history(limit=LIMIT):
        temp = msg.content.split("\n")
        files.append(temp[0])
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
    while True:
        data = await file.read(FILE_SIZE)
        if not data:
            break
        sha1.update(data)
        message = await channels['storage'].send(f"", file=discord.File(fp=io.BytesIO(cipher.encrypt(data)), filename=f"{file.filename}_{counter}"))
        message_ids.append(str(message.id))
        # print(message)
        counter += 1
    # nonce_str = nonce.decode("UTF-8")
    await channels['records'].send(f"{file.filename}\n{sha1.hexdigest()}\n{nonce}", file=discord.File(io.BytesIO(bytes(",".join(message_ids), encoding="UTF-8")), filename="message_ids"))

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
        'storage': await client.fetch_channel(1178285965056417862),
        'records': await client.fetch_channel(1178293013466849381),
    }

    await clear_history(channels=channels)
    await client.close()

# async def main():
#     intents = discord.Intents.default()
#     intents.message_content = True

#     client = discord.Client(intents=intents)
#     await client.login(TOKEN)

#     channels = {
#         'storage': await client.fetch_channel(1178285965056417862),
#         'records': await client.fetch_channel(1178293013466849381),
#     }

#     await clear_history(channels=channels)
#     # await send_file("files/Rick.and.Morty.S07E05.1080p.10bit.WEBRip.6CH.x265.HEVC-PSA.mkv", channels=channels)
#     # await download_file("files/Rick.and.Morty.S07E05.1080p.10bit.WEBRip.6CH.x265.HEVC-PSA.mkv", channels=channels)
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
