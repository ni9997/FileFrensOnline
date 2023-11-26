import os
from dotenv import load_dotenv
import discord
import asyncio
import io
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
key = eval(os.getenv('AES_KEY'))
# cipher = AES.new(key, AES.MODE_CBC)
iv = get_random_bytes(16)



app = FastAPI()


@app.post("/upload/")
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

@app.get("/file/{filename}")
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


async def file_exists(path, channels: dict[str, discord.TextChannel]) -> bool:
    async for msg in channels['records'].history(limit=1_000):
        temp = msg.content.split("\n")
        if temp[0] == path:
            return True
    return False

async def clear_history(channels: dict[str, discord.TextChannel]):
    for key in channels:
        await channels[key].purge(limit=1_000)

async def send_file(file: UploadFile, channels: dict[str, discord.TextChannel]):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    if await file_exists(file.filename, channels):
        print("Gibt schon")
        return
    sha1 = hashlib.sha1()
    message_ids = []
    counter = 0
    while True:
        data = await file.read(24*1024*1024)
        if not data:
            break
        sha1.update(data)
        message = await channels['storage'].send(f"", file=discord.File(fp=io.BytesIO(cipher.encrypt(pad(data, 16))), filename=f"{file.filename}_{counter}"))
        message_ids.append(str(message.id))
        # print(message)
        counter += 1
    await channels['records'].send(f"{file.filename}\n{sha1.hexdigest()}", file=discord.File(io.BytesIO(bytes(",".join(message_ids), encoding="UTF-8")), filename="message_ids"))

async def download_file(name: str, channels: dict[str, discord.TextChannel]):
    async for msg in channels['records'].history(limit=1_000):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        temp = msg.content.split("\n")
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
                print(data)
                data = cipher.decrypt(data)
                print(data)
                data = unpad(data, 16)
                print(data)
                sha1.update(data)
                yield data
                # f.write(data)
            ok = sha1.hexdigest()==temp[1]
            print(f"Checksum match {ok}")


async def main():
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)
    await client.login(TOKEN)

    channels = {
        'storage': await client.fetch_channel(1178285965056417862),
        'records': await client.fetch_channel(1178293013466849381),
    }

    await clear_history(channels=channels)
    # await send_file("files/Rick.and.Morty.S07E05.1080p.10bit.WEBRip.6CH.x265.HEVC-PSA.mkv", channels=channels)
    # await download_file("files/Rick.and.Morty.S07E05.1080p.10bit.WEBRip.6CH.x265.HEVC-PSA.mkv", channels=channels)
    await client.close()

# asyncio.run(main())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
    # with open("file2.txt", 'rb') as a:
    #     print(a.read().hex())

    # with open("text2.txt", 'rb') as a:
    #     print(a.read().hex())
