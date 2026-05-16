from telethon import TelegramClient

from config import MonitorConfig


def create_client(config: MonitorConfig) -> TelegramClient:
    proxy = {
        "proxy_type": config.proxy_type,
        "addr": config.proxy_host,
        "port": config.proxy_port,
        "username": config.proxy_username,
        "password": config.proxy_password,
        "rdns": True,
    } if config.proxy_type else None

    return TelegramClient(
        config.session_file,
        config.api_id,
        config.api_secret,
        proxy=proxy,
    )
