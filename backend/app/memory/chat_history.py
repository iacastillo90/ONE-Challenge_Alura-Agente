import json
import sqlite3
import time
from pathlib import Path

from loguru import logger

from app.llm.base import Message


class ChatHistoryManager:
    def __init__(self, db_path: str = "./chat_history.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                messages TEXT NOT NULL,
                max_history INTEGER DEFAULT 10,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_messages(self, session_id: str, max_history: int = 10) -> list[Message]:
        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            "SELECT messages FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()

        if not row:
            return []

        messages = json.loads(row[0])
        return [Message(**m) for m in messages[-max_history:]]

    def add_message(self, session_id: str, message: Message, max_history: int = 10):
        messages = self.get_messages(session_id)
        messages.append(message)

        if len(messages) > max_history:
            messages = messages[-max_history:]

        now = time.time()
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO sessions (session_id, messages, max_history, created_at, updated_at)
               VALUES (?, ?, ?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?)""",
            (
                session_id,
                json.dumps([m.__dict__ for m in messages]),
                max_history,
                session_id,
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()

    def clear_session(self, session_id: str):
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        logger.info(f"Cleared session: {session_id}")
