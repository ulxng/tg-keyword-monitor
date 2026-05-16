# Выводит список всех диалогов с их ID. Используется для поиска правильного chat_id нужной группы.
import asyncio
from client import create_client
from config import load_config


async def main():
    config = load_config()
    client = create_client(config)
    await client.connect()
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.title}")
    await client.disconnect()


asyncio.run(main())
