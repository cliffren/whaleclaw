"""EvoMap bounty task management."""

from __future__ import annotations

from whaleclaw.plugins.evomap.client import A2AClient
from whaleclaw.plugins.evomap.models import Task


class BountyManager:
    """Manage EvoMap bounty tasks."""

    def __init__(self, client: A2AClient) -> None:
        self._client = client

    async def list_tasks(self, min_reputation: int = 0) -> list[Task]:
        """Get available tasks."""
        resp = await self._client.fetch(
            asset_type="Capsule",
            include_tasks=True,
        )
        payload = resp.get("payload", resp)
        raw = payload.get("tasks", payload.get("task_list", []))
        tasks = []
        for t in raw:
            if isinstance(t, dict) and t.get("min_reputation", 0) <= min_reputation:
                tasks.append(Task(**t))
            elif hasattr(t, "min_reputation") and t.min_reputation <= min_reputation:
                tasks.append(t if isinstance(t, Task) else Task(**t))
        return tasks

    async def claim_task(self, task_id: str) -> dict[str, object]:
        """Claim a task."""
        return await self._client.claim_task(task_id)

    async def complete_task(self, task_id: str, asset_id: str) -> dict[str, object]:
        """Submit task completion."""
        return await self._client.complete_task(task_id, asset_id)

    async def my_tasks(self) -> list[Task]:
        """Get claimed tasks for current node."""
        data = await self._client.my_tasks()
        payload = data.get("payload", data)
        raw = payload.get("tasks", payload.get("task_list", []))
        return [Task(**t) if isinstance(t, dict) else t for t in raw]
