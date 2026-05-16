import asyncio
import sys

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import load_config
from proxy import build_proxy_kwargs


async def main() -> None:
    config = load_config("config.yaml")
    client = TelegramClient(
        config.session_file,
        config.api_id,
        config.api_secret,
        **build_proxy_kwargs(config),
    )

    await client.connect()
    try:
        if await client.is_user_authorized():
            print(f"Already authorized. Session: {config.session_file}")
            return

        print("Scan the QR code below with your Telegram app.")
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            qr_login = await client.qr_login()
            qr = qrcode.QRCode()
            qr.add_data(qr_login.url)
            qr.make()
            qr.print_ascii(invert=True)
            print(f"Waiting for scan... (attempt {attempt}/{max_attempts})")
            try:
                await qr_login.wait()
                break
            except SessionPasswordNeededError:
                password = input("2FA password: ").strip()
                await client.sign_in(password=password)
                break
            except asyncio.TimeoutError:
                print(f"QR code expired (attempt {attempt}/{max_attempts})")
                if attempt == max_attempts:
                    sys.exit("QR code expired too many times. Please restart and try again.")
            except Exception as e:
                sys.exit(f"Authorization failed: {e}\nPlease restart and try again.")

        print(f"Authorized. Session saved to: {config.session_file}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
