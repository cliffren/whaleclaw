"""Tests for CronScheduler."""

from __future__ import annotations

from datetime import datetime

import pytest

from whaleclaw.cron.scheduler import CronAction, CronJob, CronScheduler


@pytest.fixture
def scheduler() -> CronScheduler:
    return CronScheduler()


@pytest.fixture
def sample_job() -> CronJob:
    return CronJob(
        id="job-1",
        name="Test",
        schedule="30 14 * * *",
        action=CronAction(type="message", target="user", payload={}),
        enabled=True,
        created_at=datetime(2025, 2, 22, 12, 0, 0),
    )


@pytest.mark.asyncio
async def test_add_and_list_jobs(scheduler: CronScheduler, sample_job: CronJob) -> None:
    await scheduler.add_job(sample_job)
    jobs = await scheduler.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "job-1"
    assert jobs[0].name == "Test"


@pytest.mark.asyncio
async def test_remove_job(scheduler: CronScheduler, sample_job: CronJob) -> None:
    await scheduler.add_job(sample_job)
    await scheduler.remove_job("job-1")
    jobs = await scheduler.list_jobs()
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_should_run(scheduler: CronScheduler) -> None:
    job = CronJob(
        id="m",
        name="M",
        schedule="32 14 22 2 5",
        action=CronAction(type="message", target="x", payload={}),
        enabled=True,
        created_at=datetime(2025, 2, 22),
    )
    now = datetime(2025, 2, 22, 14, 32, 0)
    assert now.weekday() == 5
    assert scheduler._should_run(job, now) is True


@pytest.mark.asyncio
async def test_should_not_run(scheduler: CronScheduler) -> None:
    job = CronJob(
        id="m",
        name="M",
        schedule="35 14 22 2 5",
        action=CronAction(type="message", target="x", payload={}),
        enabled=True,
        created_at=datetime(2025, 2, 22),
    )
    now = datetime(2025, 2, 22, 14, 32, 0)
    assert scheduler._should_run(job, now) is False
