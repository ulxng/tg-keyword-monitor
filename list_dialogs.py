# Выводит список всех диалогов с их ID. Используется для поиска правильного chat_id нужной группы.
import asyncio
from config import load_config
from telethon import TelegramClient
from main import _build_proxy_kwargs


async def main():
    config = load_config()
    client = TelegramClient(config.session_file, config.api_id, config.api_secret, **_build_proxy_kwargs(config))
    await client.connect()
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.title}")
    await client.disconnect()


asyncio.run(main())
