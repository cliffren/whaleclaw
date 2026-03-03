"""TaskMonitor: polls background tasks and notifies sessions on completion.

Design
------
- A single asyncio task runs an infinite loop sleeping 10 seconds between checks.
- Process existence is checked via ``os.kill(pid, 0)`` — a zero-signal no-op
  that costs only a kernel call (microseconds, no CPU, no I/O).
- On completion the last N lines of the log are read and a system message is
  pushed to the originating session via the Gateway's WebSocket / channel bridge.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from whaleclaw.utils.log import get_logger

if TYPE_CHECKING:
    pass

log = get_logger(__name__)

_POLL_INTERVAL = 10          # seconds between polls
_LOG_TAIL_LINES = 30         # lines to include in the completion notification


@dataclass
class BackgroundTask:
    task_id: str
    pid: int
    task_name: str
    log_path: Path
    session_id: str
    # callbacks populated by the gateway after construction
    notify_fn: Any = field(default=None, repr=False)


class TaskMonitor:
    """Lightweight asyncio service that watches detached background processes."""

    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTask] = {}
        self._loop_task: asyncio.Task[None] | None = None
        # Injected by gateway after startup: async (session_id, text) -> None
        self.notify_fn: Any = None

    # ── Public API ────────────────────────────────────────────

    async def register(
        self,
        *,
        task_id: str,
        pid: int,
        task_name: str,
        log_path: Path,
        session_id: str,
    ) -> None:
        """Register a newly launched background task for monitoring."""
        bt = BackgroundTask(
            task_id=task_id,
            pid=pid,
            task_name=task_name,
            log_path=log_path,
            session_id=session_id,
        )
        self._tasks[task_id] = bt
        log.info(
            "task_monitor.registered",
            task_id=task_id,
            pid=pid,
            task_name=task_name,
        )

    async def start(self) -> None:
        """Start the background polling loop."""
        self._loop_task = asyncio.create_task(
            self._poll_loop(), name="bg-task-monitor"
        )
        log.info("task_monitor.started")

    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None
        log.info("task_monitor.stopped")

    # ── Internal ─────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(_POLL_INTERVAL)
            await self._check_all()

    async def _check_all(self) -> None:
        finished = []
        for _, bt in list(self._tasks.items()):
            if _is_process_gone(bt.pid):
                finished.append(bt)

        for bt in finished:
            del self._tasks[bt.task_id]
            await self._notify_done(bt)

    async def _notify_done(self, bt: BackgroundTask) -> None:
        """Read the task log tail and push a system message to the session."""
        tail = _read_tail(bt.log_path, _LOG_TAIL_LINES)
        content = (
            f"[系统通知] 后台任务「{bt.task_name}」(PID {bt.pid}) 已完成。\n"
            f"任务ID: {bt.task_id}\n"
            f"日志尾部:\n```\n{tail}\n```\n"
            f"请根据以上结果告诉我分析结论。"
        )
        log.info(
            "task_monitor.task_done",
            task_id=bt.task_id,
            session_id=bt.session_id,
        )
        if self.notify_fn is not None:
            try:
                await self.notify_fn(bt.session_id, content)
            except Exception as exc:
                log.warning(
                    "task_monitor.notify_failed",
                    task_id=bt.task_id,
                    error=str(exc),
                )


# ── Helpers ───────────────────────────────────────────────────

def _is_process_gone(pid: int) -> bool:
    """Return True if the process no longer exists."""
    try:
        os.kill(pid, 0)
        return False       # process is alive
    except ProcessLookupError:
        return True        # process is gone
    except PermissionError:
        return False       # process exists but we lack permission to signal it


def _read_tail(path: Path, n: int) -> str:
    """Read the last n lines of a text file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[-n:]) if len(lines) > n else text
    except OSError:
        return "(日志不可读)"
