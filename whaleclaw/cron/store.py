"""Persistent storage for cron jobs."""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from whaleclaw.cron.scheduler import CronAction, CronJob


class CronStore:
    """aiosqlite-backed persistence for cron jobs."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._conn = await aiosqlite.connect(str(self._path))
        await self._ensure_table()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _ensure_table(self) -> None:
        if not self._conn:
            return
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                schedule TEXT NOT NULL,
                action_json TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                last_run TEXT,
                next_run TEXT
            )
            """
        )
        await self._conn.commit()

    def _job_to_row(self, job: CronJob) -> tuple:
        return (
            job.id,
            job.name,
            job.schedule,
            json.dumps(job.action.model_dump()),
            1 if job.enabled else 0,
            job.created_at.isoformat(),
            job.last_run.isoformat() if job.last_run else None,
            job.next_run.isoformat() if job.next_run else None,
        )

    def _row_to_job(self, row: tuple) -> CronJob:
        from datetime import datetime

        (
            id_,
            name,
            schedule,
            action_json,
            enabled,
            created_at,
            last_run,
            next_run,
        ) = row
        action_data = json.loads(action_json)
        return CronJob(
            id=id_,
            name=name,
            schedule=schedule,
            action=CronAction.model_validate(action_data),
            enabled=bool(enabled),
            created_at=datetime.fromisoformat(created_at),
            last_run=datetime.fromisoformat(last_run) if last_run else None,
            next_run=datetime.fromisoformat(next_run) if next_run else None,
        )

    async def save_job(self, job: CronJob) -> None:
        if not self._conn:
            return
        row = self._job_to_row(job)
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO cron_jobs
            (id, name, schedule, action_json, enabled, created_at, last_run, next_run)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        await self._conn.commit()

    async def load_jobs(self) -> list[CronJob]:
        if not self._conn:
            return []
        cursor = await self._conn.execute("SELECT * FROM cron_jobs")
        rows = await cursor.fetchall()
        return [self._row_to_job(r) for r in rows]

    async def delete_job(self, job_id: str) -> None:
        if not self._conn:
            return
        await self._conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
        await self._conn.commit()
