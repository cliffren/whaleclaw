"""SQLite-backed session and message persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import aiosqlite

from whaleclaw.config.paths import SESSIONS_DIR
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)

_DB_PATH = SESSIONS_DIR / "sessions.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    peer_id TEXT NOT NULL,
    model TEXT NOT NULL,
    thinking_level TEXT DEFAULT 'off',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_call_id TEXT,
    tool_name TEXT,
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id, timestamp);
"""


class SessionRow:
    """Typed wrapper for a session row."""

    __slots__ = (
        "id",
        "channel",
        "peer_id",
        "model",
        "thinking_level",
        "metadata",
        "created_at",
        "updated_at",
    )

    def __init__(self, row: aiosqlite.Row) -> None:
        self.id: str = row[0]
        self.channel: str = row[1]
        self.peer_id: str = row[2]
        self.model: str = row[3]
        self.thinking_level: str = row[4]
        self.metadata: dict[str, object] = json.loads(row[5]) if row[5] else {}
        self.created_at: str = row[6]
        self.updated_at: str = row[7]


class MessageRow:
    """Typed wrapper for a message row."""

    __slots__ = (
        "id",
        "session_id",
        "role",
        "content",
        "tool_call_id",
        "tool_name",
        "timestamp",
        "metadata",
    )

    def __init__(self, row: aiosqlite.Row) -> None:
        self.id: int = row[0]
        self.session_id: str = row[1]
        self.role: str = row[2]
        self.content: str = row[3]
        self.tool_call_id: str | None = row[4]
        self.tool_name: str | None = row[5]
        self.timestamp: str = row[6]
        self.metadata: dict[str, object] = json.loads(row[7]) if row[7] else {}


class SessionStore:
    """Async SQLite store for sessions and messages."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        """Open the database and ensure schema exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.commit()
        log.debug("session_store.opened", path=str(self._db_path))

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            msg = "SessionStore not opened"
            raise RuntimeError(msg)
        return self._db

    async def save_session(
        self,
        *,
        session_id: str,
        channel: str,
        peer_id: str,
        model: str,
        thinking_level: str = "off",
        metadata: dict[str, object] | None = None,
        created_at: str,
        updated_at: str,
    ) -> None:
        await self._conn.execute(
            """INSERT OR REPLACE INTO sessions
               (id, channel, peer_id, model, thinking_level, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                channel,
                peer_id,
                model,
                thinking_level,
                json.dumps(metadata or {}),
                created_at,
                updated_at,
            ),
        )
        await self._conn.commit()

    async def get_session(self, session_id: str) -> SessionRow | None:
        cursor = await self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return SessionRow(row) if row else None

    async def get_session_by_peer(self, channel: str, peer_id: str) -> SessionRow | None:
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE channel = ? AND peer_id = ?"
            " ORDER BY updated_at DESC LIMIT 1",
            (channel, peer_id),
        )
        row = await cursor.fetchone()
        return SessionRow(row) if row else None

    async def list_sessions(self) -> list[SessionRow]:
        cursor = await self._conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        return [SessionRow(r) for r in await cursor.fetchall()]

    async def get_message_counts(self) -> dict[str, int]:
        """Return {session_id: message_count} for all sessions."""
        cursor = await self._conn.execute(
            "SELECT session_id, COUNT(*) FROM messages GROUP BY session_id"
        )
        return {row[0]: row[1] for row in await cursor.fetchall()}

    async def delete_session(self, session_id: str) -> None:
        await self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._conn.commit()

    async def update_session_field(
        self, session_id: str, **fields: object
    ) -> None:
        """Update arbitrary fields on a session row."""
        allowed = {"model", "thinking_level", "metadata", "updated_at"}
        parts: list[str] = []
        values: list[object] = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "metadata" and isinstance(v, dict):
                v = json.dumps(v)
            parts.append(f"{k} = ?")
            values.append(v)
        if not parts:
            return
        values.append(session_id)
        sql = f"UPDATE sessions SET {', '.join(parts)} WHERE id = ?"  # noqa: S608
        await self._conn.execute(sql, values)
        await self._conn.commit()

    async def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        timestamp: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> int:
        ts = timestamp or datetime.now().isoformat()
        cursor = await self._conn.execute(
            """INSERT INTO messages
               (session_id, role, content, tool_call_id, tool_name, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, role, content, tool_call_id, tool_name, ts, json.dumps(metadata or {})),
        )
        await self._conn.commit()
        return cursor.lastrowid or 0

    async def get_messages(
        self, session_id: str, *, limit: int | None = None
    ) -> list[MessageRow]:
        sql = "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC"
        params: list[object] = [session_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        cursor = await self._conn.execute(sql, params)
        return [MessageRow(r) for r in await cursor.fetchall()]

    async def get_recent_messages(
        self, session_id: str, limit: int = 50
    ) -> list[MessageRow]:
        """Get the most recent N messages (returned in chronological order)."""
        sql = """SELECT * FROM (
                    SELECT * FROM messages WHERE session_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                 ) sub ORDER BY timestamp ASC"""
        cursor = await self._conn.execute(sql, (session_id, limit))
        return [MessageRow(r) for r in await cursor.fetchall()]

    async def delete_messages(self, session_id: str) -> None:
        await self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self._conn.commit()

    async def count_messages(self, session_id: str) -> int:
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
