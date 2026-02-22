"""Cron job scheduler."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


def _parse_cron_field(field: str, min_val: int, max_val: int, now_val: int) -> bool:
    if field == "*":
        return True
    try:
        return int(field) == now_val
    except ValueError:
        return False


class CronAction(BaseModel):
    """Action to perform when a cron job fires."""

    type: Literal["message", "agent", "webhook"]
    target: str
    payload: dict[str, Any] = {}


class CronJob(BaseModel):
    """Cron job definition."""

    id: str
    name: str
    schedule: str
    action: CronAction
    enabled: bool = True
    created_at: datetime
    last_run: datetime | None = None
    next_run: datetime | None = None


class CronScheduler:
    """In-memory cron scheduler with 60s tick."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def add_job(self, job: CronJob) -> None:
        self._jobs[job.id] = job

    async def remove_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def list_jobs(self) -> list[CronJob]:
        return list(self._jobs.values())

    async def trigger_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        logger.info("cron_job_executing", job_id=job_id, action=job.action.model_dump())
        job = job.model_copy(update={"last_run": datetime.now()})
        self._jobs[job_id] = job

    def _should_run(self, job: CronJob, now: datetime) -> bool:
        if not job.enabled:
            return False
        parts = job.schedule.split()
        if len(parts) != 5:
            return False
        min_match = _parse_cron_field(parts[0], 0, 59, now.minute)
        hour_match = _parse_cron_field(parts[1], 0, 23, now.hour)
        dom_match = _parse_cron_field(parts[2], 1, 31, now.day)
        mon_match = _parse_cron_field(parts[3], 1, 12, now.month)
        dow_match = _parse_cron_field(parts[4], 0, 6, now.weekday())
        return min_match and hour_match and dom_match and mon_match and dow_match

    async def _run_loop(self) -> None:
        while self._running:
            await asyncio.sleep(60)
            if not self._running:
                break
            now = datetime.now()
            for job in list(self._jobs.values()):
                if self._should_run(job, now):
                    await self.trigger_job(job.id)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
