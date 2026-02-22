"""Audit logging for security-relevant events."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Single audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str
    session_id: str | None = None
    channel: str | None = None
    peer_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    session_id TEXT,
    channel TEXT,
    peer_id TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_events(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
"""


class AuditLogger:
    """SQLite-backed audit logger."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        """Open database and ensure schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        await self._ensure_table()

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def _ensure_table(self) -> None:
        if self._db is None:
            raise RuntimeError("AuditLogger not opened")
        await self._db.executescript(_AUDIT_SCHEMA)
        await self._db.commit()

    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("AuditLogger not opened")
        return self._db

    async def log(self, event: AuditEvent) -> None:
        """Append event to audit log."""
        await self._conn().execute(
            """INSERT INTO audit_events
               (timestamp, event_type, session_id, channel, peer_id, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event.timestamp.isoformat(),
                event.event_type,
                event.session_id,
                event.channel,
                event.peer_id,
                json.dumps(event.details),
            ),
        )
        await self._conn().commit()

    async def query(
        self,
        event_type: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with optional filters."""
        clauses: list[str] = []
        params: list[object] = []
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        cursor = await self._conn().execute(
            f"SELECT timestamp, event_type, session_id, channel, peer_id, details "
            f"FROM audit_events{where} ORDER BY timestamp DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        return [
            AuditEvent(
                timestamp=datetime.fromisoformat(r[0]),
                event_type=r[1],
                session_id=r[2],
                channel=r[3],
                peer_id=r[4],
                details=json.loads(r[5]) if r[5] else {},
            )
            for r in rows
        ]
