"""Small SQLite-backed, user-scoped conversation memory for the principles Agent."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_MAX_TURNS = 4
DEFAULT_DATABASE = Path(__file__).resolve().parents[2] / "runs" / "principles_memory.sqlite3"


class PrincipleConversationMemory:
    """Persist only completed user/assistant turns and keep a bounded recent window."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE, *, max_turns: int = DEFAULT_MAX_TURNS):
        if not 1 <= max_turns <= 20:
            raise ValueError("max_turns must be between 1 and 20.")
        self.db_path = Path(db_path).resolve()
        self.max_turns = max_turns
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS principle_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS principle_turns (
                    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES principle_sessions(session_id)
                        ON DELETE CASCADE,
                    user_message TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_principle_turns_session
                    ON principle_turns(session_id, turn_id);
                """
            )

    def history(self, session_id: str, owner_user_id: str | None) -> list[dict[str, str]]:
        self._validate_session_id(session_id)
        owner = owner_user_id or ""
        with closing(self._connect()) as connection, connection:
            self._check_owner(connection, session_id, owner)
            rows = connection.execute(
                """SELECT user_message, assistant_message
                FROM principle_turns WHERE session_id = ? ORDER BY turn_id DESC LIMIT ?""",
                (session_id, self.max_turns),
            ).fetchall()
        messages: list[dict[str, str]] = []
        for user_message, assistant_message in reversed(rows):
            messages.extend(
                (
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                )
            )
        return messages

    def append_turn(
        self,
        session_id: str,
        owner_user_id: str | None,
        *,
        user_message: str,
        assistant_message: str,
    ) -> int:
        self._validate_session_id(session_id)
        if not user_message.strip() or not assistant_message.strip():
            raise ValueError("Only non-empty completed turns can be stored.")
        owner = owner_user_id or ""
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_owner(connection, session_id, owner)
            connection.execute(
                "INSERT OR IGNORE INTO principle_sessions(session_id, owner_user_id) VALUES (?, ?)",
                (session_id, owner),
            )
            connection.execute(
                """INSERT INTO principle_turns(session_id, user_message, assistant_message)
                VALUES (?, ?, ?)""",
                (session_id, user_message.strip(), assistant_message.strip()),
            )
            connection.execute(
                """DELETE FROM principle_turns
                WHERE session_id = ? AND turn_id NOT IN (
                    SELECT turn_id FROM principle_turns WHERE session_id = ?
                    ORDER BY turn_id DESC LIMIT ?
                )""",
                (session_id, session_id, self.max_turns),
            )
            count = connection.execute(
                "SELECT COUNT(*) FROM principle_turns WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
        return int(count)

    def clear(self, session_id: str, owner_user_id: str | None) -> bool:
        self._validate_session_id(session_id)
        owner = owner_user_id or ""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_owner(connection, session_id, owner)
            cursor = connection.execute(
                "DELETE FROM principle_sessions WHERE session_id = ? AND owner_user_id = ?",
                (session_id, owner),
            )
            return cursor.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _check_owner(connection: sqlite3.Connection, session_id: str, owner: str) -> None:
        row = connection.execute(
            "SELECT owner_user_id FROM principle_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is not None and row[0] != owner:
            raise PermissionError("This conversation belongs to a different demo identity.")

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 120:
            raise ValueError("session_id must contain between 1 and 120 characters.")

