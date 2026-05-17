import asyncio
import logging
import time
from collections import deque
from datetime import timezone

from telethon import TelegramClient, events
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


def _chat_label(chat) -> str:
    name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown chat"
    username = getattr(chat, "username", None)
    return f"{name} (@{username})" if username else name


def _build_message_link(message: events.NewMessage.Event) -> str | None:
    # Ссылки поддерживаются только для супергрупп и каналов (тип Channel).
    # chat.id возвращает ID без префикса -100, что нужно для t.me/c/{id}/{msg_id}.
    chat = message.chat
    if not isinstance(chat, Channel):
        return None
    chat_username = getattr(chat, "username", None)
    msg_id = message.message.id
    return f"https://t.me/{chat_username}/{msg_id}" if chat_username else f"https://t.me/c/{chat.id}/{msg_id}"


def _fallback_notification(message: events.NewMessage.Event) -> str:
    chat_label = _chat_label(message.chat)
    link = _build_message_link(message)
    date = message.message.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"Чат: {chat_label}\n"
        f"Время: {date}\n"
        f"{f'Ссылка: {link}\n' if link else ''}"
        f"\n"
        f"{message.raw_text}"
    )


async def _resend_message(client: TelegramClient, destination: str | int, message: events.NewMessage.Event) -> None:
    forwarded = await client.forward_messages(destination, message.message)

    # Добавляем ссылку на оригинальное сообщение.
    # В пересланных сообщениях из групп непонятно, из какого чата они пришли — в заголовке только имя отправителя.
    # Для каналов (broadcast) источник понятен, там ссылка лишняя —
    # кроме случая, когда само сообщение является форвардом: тогда заголовок покажет источник оригинала, а не канал.
    is_broadcast_channel = isinstance(message.chat, Channel) and message.chat.broadcast
    is_forwarded_message = message.message.fwd_from is not None
    if is_broadcast_channel and not is_forwarded_message:
        return None
    note = _build_message_link(message)
    if note:
        forwarded_id = forwarded.id
        await client.send_message(destination, note, reply_to=forwarded_id)


async def forward_match(
    client: TelegramClient,
    config: MonitorConfig,
    event: events.NewMessage.Event,
    matched_keywords: list[str],
    rate_limiter: RateLimiter,
) -> bool:
    if not rate_limiter.is_allowed():
        logger.warning(
            'Rate limit reached, dropping match [%s] from "%s" (id=%s, msg_id=%s)',
            ", ".join(matched_keywords),
            _chat_label(event.chat),
            event.chat_id,
            event.message.id,
        )
        return False

    try:
        await _resend_message(client, config.destination_chat, event)
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
            return False
        await asyncio.sleep(config.send_delay_seconds)
        return True
    except FloodWaitError as e:
        wait = e.seconds + 5
        logger.warning("FloodWaitError: sleeping %ds then retrying", wait)
        await asyncio.sleep(wait)
        try:
            await _resend_message(client, config.destination_chat, event)
        except Exception:
            logger.exception("Retry after FloodWait failed, dropping message")
            return False
    except Exception:
        logger.exception("Failed to forward message from chat %s msg %s", event.chat_id, event.message.id)
        return False

    await asyncio.sleep(config.send_delay_seconds)
    return True
