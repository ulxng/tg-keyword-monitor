import sqlite3
from datetime import datetime, timedelta, timezone


class DedupStore:
    def __init__(self, db_path: str = "seen.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages (
                chat_id    INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                seen_at    TEXT    NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            )
            """
        )
        self._conn.commit()

    def is_seen(self, chat_id: int, message_id: int) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM seen_messages WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        )
        return cur.fetchone() is not None

    def mark_seen(self, chat_id: int, message_id: int) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_messages (chat_id, message_id, seen_at) VALUES (?, ?, ?)",
            (chat_id, message_id, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def prune_old(self, days: int = 7) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        self._conn.execute("DELETE FROM seen_messages WHERE seen_at < ?", (cutoff,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
