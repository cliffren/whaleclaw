"""Background bash execution tool.

Launches a long-running command as a detached process whose stdout/stderr are
redirected to a dedicated log file.  Returns immediately with a task_id and the
log path so the Agent can confirm the launch without waiting for completion.

The gateway's TaskMonitor polls for process completion and sends a system
notification back to the session when the process exits.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

from whaleclaw.config.paths import WHALECLAW_HOME
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

_BG_TASK_DIR = WHALECLAW_HOME / "bg_tasks"

# Module-level monitor reference – injected by create_default_registry
_task_monitor: Any = None


def set_task_monitor(monitor: Any) -> None:
    """Inject the TaskMonitor instance so this tool can register tasks."""
    global _task_monitor  # noqa: PLW0603
    _task_monitor = monitor


class BashBackgroundTool(Tool):
    """Run a bash command in the background and return immediately.

    The command is detached from the current process; its stdout and stderr
    are saved to a log file under WHALECLAW_HOME/bg_tasks/.  A task_id is
    returned so the Agent can reference the task later.

    The gateway's TaskMonitor polls for process exit and automatically
    notifies the session when the task completes.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash_background",
            description=(
                "Run a long-running bash command in the background. "
                "Returns immediately with a task_id and log file path. "
                "You will be notified automatically when the task finishes. "
                "Use this instead of bash when a command may take more than a minute."
            ),
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The bash command to execute in the background.",
                ),
                ToolParameter(
                    name="task_name",
                    type="string",
                    description="A short human-readable name for this task (e.g. 'train ResNet').",
                    required=False,
                ),
                ToolParameter(
                    name="session_id",
                    type="string",
                    description=(
                        "Session ID to notify when done. "
                        "If omitted the monitor will use the calling session."
                    ),
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        command: str = kwargs.get("command", "").strip()
        task_name: str = kwargs.get("task_name", "background task")
        session_id: str = kwargs.get("session_id", "")

        if not command:
            return ToolResult(success=False, output="", error="命令为空")

        task_id = uuid.uuid4().hex[:10]
        _BG_TASK_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _BG_TASK_DIR / f"{task_id}.log"

        # Write a small header so the user can tail the log immediately
        log_path.write_text(
            f"# task_id: {task_id}\n# command: {command}\n# status: running\n\n",
            encoding="utf-8",
        )

        # Build a wrapper that appends exit code at the end
        wrapped = (
            f"( {command} ) >> {log_path} 2>&1; "
            f"echo \"\\n[exit_code: $?]\" >> {log_path}"
        )

        env = os.environ.copy()
        try:
            proc = await asyncio.create_subprocess_shell(
                wrapped,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,   # detach from parent process group
                env=env,
            )
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        pid = proc.pid

        # Register with the monitor if available
        if _task_monitor is not None:
            await _task_monitor.register(
                task_id=task_id,
                pid=pid,
                task_name=task_name,
                log_path=log_path,
                session_id=session_id,
            )
            notify_msg = "任务启动成功，完成后会自动通知你。"
        else:
            notify_msg = "任务已启动（通知功能未激活，请稍后手动查看日志）。"

        return ToolResult(
            success=True,
            output=(
                f"✅ 后台任务已启动\n"
                f"task_id: {task_id}\n"
                f"PID: {pid}\n"
                f"名称: {task_name}\n"
                f"日志: {log_path}\n"
                f"{notify_msg}"
            ),
        )
