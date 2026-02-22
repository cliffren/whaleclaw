"""Reminder tool - one-shot cron jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from whaleclaw.cron.scheduler import CronAction, CronJob, CronScheduler
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class ReminderTool(Tool):
    """Set a one-shot reminder N minutes from now."""

    def __init__(self, scheduler: CronScheduler) -> None:
        self._scheduler = scheduler

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="reminder",
            description="Set a reminder to notify after N minutes.",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Reminder message.",
                ),
                ToolParameter(
                    name="minutes",
                    type="integer",
                    description="Minutes from now to trigger.",
                ),
            ],
        )

    async def execute(self, **kwargs: object) -> ToolResult:
        message = str(kwargs.get("message", ""))
        raw_min = kwargs.get("minutes")
        if raw_min is None:
            return ToolResult(success=False, output="", error="缺少 minutes 参数")
        try:
            minutes = int(raw_min)
        except (TypeError, ValueError):
            return ToolResult(success=False, output="", error="minutes 必须为整数")
        if minutes < 1:
            return ToolResult(success=False, output="", error="minutes 必须大于 0")
        now = datetime.now()
        target = now + timedelta(minutes=minutes)
        schedule = f"{target.minute} {target.hour} {target.day} {target.month} {target.weekday()}"
        job = CronJob(
            id=f"reminder-{uuid4().hex[:12]}",
            name=f"提醒: {message[:20]}...",
            schedule=schedule,
            action=CronAction(
                type="message",
                target="user",
                payload={"text": message},
            ),
            enabled=True,
            created_at=now,
            next_run=target,
        )
        await self._scheduler.add_job(job)
        return ToolResult(
            success=True,
            output=f"提醒已设置，{minutes} 分钟后通知",
            error=None,
        )
