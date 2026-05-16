import asyncio
import logging
import time
from collections import deque

from telethon import TelegramClient
from telethon.errors import FloodWaitError

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
