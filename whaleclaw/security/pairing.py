"""DM pairing service and allowlist for unknown senders."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import aiosqlite
from pydantic import BaseModel


class PairingRequest(BaseModel):
    """Pending pairing request."""

    code: str
    channel: str
    peer_id: str
    peer_name: str | None = None
    created_at: datetime
    expires_at: datetime
    status: Literal["pending", "approved", "rejected", "expired"]


class AllowListEntry(BaseModel):
    """Allowlist entry for approved channel+peer."""

    channel: str
    peer_id: str
    approved_by: str = "system"
    approved_at: datetime


class PairingService:
    """In-memory pairing code service."""

    def __init__(self, ttl_minutes: int = 5) -> None:
        self._ttl_minutes = ttl_minutes
        self._pending: dict[str, PairingRequest] = {}

    async def generate_code(self, channel: str, peer_id: str) -> str:
        """Generate 6-digit pairing code, expires in ttl_minutes."""
        code = "".join(str(random.randint(0, 9)) for _ in range(6))
        now = datetime.now()
        expires = now + timedelta(minutes=self._ttl_minutes)
        self._pending[code] = PairingRequest(
            code=code,
            channel=channel,
            peer_id=peer_id,
            created_at=now,
            expires_at=expires,
            status="pending",
        )
        return code

    async def verify(self, code: str) -> PairingRequest | None:
        """Return request if code is valid and not expired."""
        req = self._pending.get(code)
        if not req:
            return None
        if req.status != "pending":
            return req
        if datetime.now() >= req.expires_at:
            req.status = "expired"
            return None
        return req

    async def approve(self, code: str) -> bool:
        """Mark request as approved. Return True if succeeded."""
        req = self._pending.get(code)
        if not req or req.status != "pending":
            return False
        if datetime.now() >= req.expires_at:
            req.status = "expired"
            return False
        req.status = "approved"
        return True

    async def reject(self, code: str) -> bool:
        """Mark request as rejected. Return True if succeeded."""
        req = self._pending.get(code)
        if not req or req.status != "pending":
            return False
        req.status = "rejected"
        return True

    async def list_pending(self) -> list[PairingRequest]:
        """Return all pending requests."""
        now = datetime.now()
        return [r for r in self._pending.values() if r.status == "pending" and r.expires_at > now]


_ALLOWLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS allowlist (
    channel TEXT NOT NULL,
    peer_id TEXT NOT NULL,
    approved_by TEXT NOT NULL DEFAULT 'system',
    approved_at TEXT NOT NULL,
    PRIMARY KEY (channel, peer_id)
);

CREATE INDEX IF NOT EXISTS idx_allowlist_channel ON allowlist(channel);
"""


class AllowListStore:
    """SQLite-backed allowlist for channel+peer approvals."""

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
            raise RuntimeError("AllowListStore not opened")
        await self._db.executescript(_ALLOWLIST_SCHEMA)
        await self._db.commit()

    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("AllowListStore not opened")
        return self._db

    async def is_allowed(self, channel: str, peer_id: str) -> bool:
        """Return True if (channel, peer_id) is in allowlist."""
        cursor = await self._conn().execute(
            "SELECT 1 FROM allowlist WHERE channel = ? AND peer_id = ?",
            (channel, peer_id),
        )
        row = await cursor.fetchone()
        return row is not None

    async def add(
        self,
        channel: str,
        peer_id: str,
        approved_by: str = "system",
    ) -> None:
        """Add (channel, peer_id) to allowlist."""
        now = datetime.now().isoformat()
        await self._conn().execute(
            """INSERT OR REPLACE INTO allowlist (channel, peer_id, approved_by, approved_at)
               VALUES (?, ?, ?, ?)""",
            (channel, peer_id, approved_by, now),
        )
        await self._conn().commit()

    async def remove(self, channel: str, peer_id: str) -> None:
        """Remove (channel, peer_id) from allowlist."""
        await self._conn().execute(
            "DELETE FROM allowlist WHERE channel = ? AND peer_id = ?",
            (channel, peer_id),
        )
        await self._conn().commit()

    async def list_all(self, channel: str | None = None) -> list[AllowListEntry]:
        """List allowlist entries, optionally filtered by channel."""
        if channel is not None:
            cursor = await self._conn().execute(
                "SELECT channel, peer_id, approved_by, approved_at "
                "FROM allowlist WHERE channel = ?",
                (channel,),
            )
        else:
            cursor = await self._conn().execute(
                "SELECT channel, peer_id, approved_by, approved_at FROM allowlist",
            )
        rows = await cursor.fetchall()
        return [
            AllowListEntry(
                channel=r[0],
                peer_id=r[1],
                approved_by=r[2],
                approved_at=datetime.fromisoformat(r[3]),
            )
            for r in rows
        ]
