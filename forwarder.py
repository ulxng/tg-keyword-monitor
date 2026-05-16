import asyncio
import logging
import time
from collections import deque
from datetime import timezone

from telethon import TelegramClient
from telethon.errors import ChatForwardsRestrictedError, FloodWaitError
from telethon.tl.types import Channel

from config import MonitorConfig

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_per_minute: int):
        self._max = max_per_minute
        self._timestamps: deque[float] = deque()

    def is_allowed(self) -> bool:
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] > 60:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max:
            return False
        self._timestamps.append(now)
        return True


def _fallback_notification(event) -> str:
    chat = event.chat
    chat_name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown chat"
    chat_username = getattr(chat, "username", None)
    chat_label = f"{chat_name} (@{chat_username})" if chat_username else chat_name

    # Когда пересылка запрещена, оригинальное сообщение недоступно — добавляем прямую ссылку,
    # чтобы можно было перейти к нему вручную.
    # Ссылки работают только в супергруппах и каналах (тип Channel);
    # обычные группы (тип Chat) их не поддерживают.
    # chat.id возвращает ID без префикса -100, что и нужно для t.me/c/{id}/{msg_id}.
    link = None
    if isinstance(chat, Channel):
        msg_id = event.message.id
        link = f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{chat.id}/{msg_id}"

    date = event.message.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"Чат: {chat_label}", f"Время: {date}"]
    if link:
        lines.append(f"Ссылка: {link}")
    lines += ["", event.raw_text]

    return "\n".join(lines)


async def forward_match(
    client: TelegramClient,
    config: MonitorConfig,
    event,
    matched_keywords: list[str],
    rate_limiter: RateLimiter,
) -> None:
    if not rate_limiter.is_allowed():
        logger.warning("Rate limit reached, dropping match from chat %s", event.chat_id)
        return

    try:
        await client.forward_messages(config.destination_chat, event.message)
        logger.info(
            "Forwarded match [%s] from chat %s msg %s",
            ", ".join(matched_keywords),
            event.chat_id,
            event.message.id,
        )
    except ChatForwardsRestrictedError:
        logger.info("Forward restricted in chat %s, sending fallback notification", event.chat_id)
        try:
            await client.send_message(config.destination_chat, _fallback_notification(event))
        except Exception:
            logger.exception("Failed to send fallback notification for chat %s msg %s", event.chat_id, event.message.id)
        return
    except FloodWaitError as e:
        wait = e.seconds + 5
        logger.warning("FloodWaitError: sleeping %ds then retrying", wait)
        await asyncio.sleep(wait)
        try:
            await client.forward_messages(config.destination_chat, event.message)
        except Exception:
            logger.exception("Retry after FloodWait failed, dropping message")
        return
    except Exception:
        logger.exception("Failed to forward message from chat %s msg %s", event.chat_id, event.message.id)
        return

    await asyncio.sleep(config.send_delay_seconds)
