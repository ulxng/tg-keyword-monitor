import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat, User

from config import MonitorConfig

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 1000


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


def _build_message_link(chat, message_id: int) -> str:
    if isinstance(chat, Channel):
        if chat.username:
            return f"https://t.me/{chat.username}/{message_id}"
        return f"https://t.me/c/{chat.id}/{message_id}"
    return ""


def _get_chat_name(chat) -> str:
    if isinstance(chat, (Channel, Chat)):
        return chat.title or "Unknown chat"
    if isinstance(chat, User):
        parts = [chat.first_name or "", chat.last_name or ""]
        return " ".join(p for p in parts if p) or "Unknown user"
    return "Unknown"


def _get_sender_label(sender) -> str:
    if sender is None:
        return "Unknown"
    name_parts = [getattr(sender, "first_name", "") or "", getattr(sender, "last_name", "") or ""]
    name = " ".join(p for p in name_parts if p) or "Unknown"
    username = getattr(sender, "username", None)
    if username:
        return f"{name} (@{username})"
    return name


def _build_notification(event, matched_keywords: list[str]) -> str:
    chat = event.chat
    sender = event.sender
    message = event.message

    kw_display = ", ".join(f"`{k}`" for k in matched_keywords)
    chat_name = _get_chat_name(chat)
    link = _build_message_link(chat, message.id)
    sender_label = _get_sender_label(sender)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    text = message.raw_text or ""
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + " [truncated]"

    has_media = message.media is not None and not message.raw_text

    lines = [
        f"**Keyword match:** {kw_display}",
        "",
        f"**Chat:** {chat_name}" + (f" — {link}" if link else ""),
        f"**From:** {sender_label}",
        f"**Time:** {timestamp}",
    ]

    if text:
        lines += ["", "---", text]
    if has_media:
        lines += ["", "_[media attached]_"]

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

    notification = _build_notification(event, matched_keywords)

    try:
        await client.send_message(config.destination_chat, notification, parse_mode="md")
        logger.info(
            "Forwarded match [%s] from chat %s msg %s",
            ", ".join(matched_keywords),
            event.chat_id,
            event.message.id,
        )
    except FloodWaitError as e:
        wait = e.seconds + 5
        logger.warning("FloodWaitError: sleeping %ds then retrying", wait)
        await asyncio.sleep(wait)
        try:
            await client.send_message(config.destination_chat, notification, parse_mode="md")
        except Exception:
            logger.exception("Retry after FloodWait failed, dropping message")
        return
    except Exception:
        logger.exception("Failed to send notification for chat %s msg %s", event.chat_id, event.message.id)
        return

    await asyncio.sleep(config.send_delay_seconds)
