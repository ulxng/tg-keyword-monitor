import asyncio
import logging
import sys

from telethon import events, utils

from client import create_client
from config import load_config
from dedup import DedupStore
from forwarder import RateLimiter, forward_match
from matcher import compile_keywords, find_matches


def setup_logging(config) -> None:
    handlers = []
    if config.log_to_stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    if config.log_file:
        handlers.append(logging.FileHandler(config.log_file, encoding="utf-8"))
    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


async def main() -> None:
    config = load_config("config.yaml")
    setup_logging(config)
    logger = logging.getLogger(__name__)

    try:
        compiled_kws = compile_keywords(config.keywords)
    except ValueError as e:
        sys.exit(str(e))

    dedup = DedupStore(db_path=config.db_file)
    dedup.prune_old(days=7)
    rate_limiter = RateLimiter(config.rate_limit_per_minute)

    client = create_client(config)

    await client.connect()
    if not await client.is_user_authorized():
        logger.error("No valid session. Run 'python login.py' first to authorize.")
        sys.exit(1)

    logger.info("Loading dialogs to resolve chat entities...")
    await client.get_dialogs()
    logger.info("Dialogs loaded.")

    destination_entity = await client.get_entity(config.destination_chat)
    destination_chat_id = utils.get_peer_id(destination_entity)

    def _should_process(event: events.NewMessage.Event) -> bool:
        if event.out or event.is_private:
            return False
        if event.chat_id == destination_chat_id:
            return False
        if config.chat_whitelist is not None and event.chat_id not in config.chat_whitelist:
            return False
        if config.chat_blacklist is not None and event.chat_id in config.chat_blacklist:
            return False
        return True

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            logger.debug("Incoming: chat_id=%s msg_id=%s out=%s is_private=%s", event.chat_id, event.message.id, event.out, event.is_private)
            if not _should_process(event):
                return
            text = event.raw_text or ""
            chat_id = event.chat_id
            msg_id = event.message.id
            logger.debug("Message received: chat_id=%s msg_id=%s text=%r", chat_id, msg_id, text[:100])
            matched = find_matches(text, compiled_kws)
            if not matched:
                return
            logger.debug("Keyword match: %s in chat_id=%s msg_id=%s", matched, chat_id, msg_id)
            if dedup.is_seen(chat_id, msg_id):
                logger.info("Skipping duplicate: chat_id=%s msg_id=%s", chat_id, msg_id)
                return
            if await forward_match(client, config, event, matched, rate_limiter):
                dedup.mark_seen(chat_id, msg_id)
        except Exception:
            logger.exception("Unhandled error in message handler")

    logger.info(
        "Userbot started. Monitoring all chats, forwarding to %s. Keywords: %s",
        config.destination_chat,
        ", ".join(config.keywords),
    )

    while True:
        try:
            await client.run_until_disconnected()
        except Exception:
            logger.exception("Client disconnected unexpectedly, reconnecting in 30s")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
