# Выводит список всех диалогов с их ID. Используется для поиска правильного chat_id нужной группы.
import asyncio
from config import load_config
from telethon import TelegramClient


async def main():
    config = load_config()
    proxy = {
        "proxy_type": config.proxy_type,
        "addr": config.proxy_host,
        "port": config.proxy_port,
        "username": config.proxy_username,
        "password": config.proxy_password,
        "rdns": True,
    } if config.proxy_type else None
    client = TelegramClient(config.session_file, config.api_id, config.api_secret, proxy=proxy)
    await client.connect()
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.title}")
    await client.disconnect()


asyncio.run(main())
