"""Cron management tool - list/add/remove/trigger jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from whaleclaw.cron.scheduler import CronAction, CronJob, CronScheduler
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class CronManageTool(Tool):
    """Manage cron jobs: list, add, remove, trigger."""

    def __init__(self, scheduler: CronScheduler) -> None:
        self._scheduler = scheduler

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="cron",
            description="Manage cron jobs: list, add, remove, or trigger.",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: list, add, remove, trigger.",
                    enum=["list", "add", "remove", "trigger"],
                ),
                ToolParameter(
                    name="job_id",
                    type="string",
                    description="Job ID (for remove/trigger).",
                    required=False,
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="Job name (for add).",
                    required=False,
                ),
                ToolParameter(
                    name="schedule",
                    type="string",
                    description="Cron expression (for add): min hour dom mon dow.",
                    required=False,
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message payload (for add).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: object) -> ToolResult:
        action = str(kwargs.get("action", "")).lower()
        job_id = str(kwargs.get("job_id", "")) if kwargs.get("job_id") else None
        name = str(kwargs.get("name", "")) if kwargs.get("name") else None
        schedule = str(kwargs.get("schedule", "")) if kwargs.get("schedule") else None
        message = str(kwargs.get("message", "")) if kwargs.get("message") else None
        if action == "list":
            jobs = await self._scheduler.list_jobs()
            lines = [f"- {j.id}: {j.name} ({j.schedule})" for j in jobs]
            return ToolResult(success=True, output="\n".join(lines) or "无定时任务")
        if action == "add":
            if not name or not schedule:
                return ToolResult(success=False, output="", error="add 需要 name 和 schedule")
            job = CronJob(
                id=f"cron-{uuid4().hex[:12]}",
                name=name,
                schedule=schedule,
                action=CronAction(
                    type="message",
                    target="user",
                    payload={"text": message or name},
                ),
                enabled=True,
                created_at=datetime.now(),
            )
            await self._scheduler.add_job(job)
            return ToolResult(success=True, output=f"已添加任务: {job.id}")
        if action == "remove":
            if not job_id:
                return ToolResult(success=False, output="", error="remove 需要 job_id")
            await self._scheduler.remove_job(job_id)
            return ToolResult(success=True, output=f"已删除任务: {job_id}")
        if action == "trigger":
            if not job_id:
                return ToolResult(success=False, output="", error="trigger 需要 job_id")
            await self._scheduler.trigger_job(job_id)
            return ToolResult(success=True, output=f"已触发: {job_id}")
        return ToolResult(success=False, output="", error=f"未知操作: {action}")
