"""macOS desktop capture tool with optional display wake-up."""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any

from whaleclaw.config.paths import WHALECLAW_HOME
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

_SCREENSHOT_DIR = WHALECLAW_HOME / "screenshots"


class DesktopCaptureTool(Tool):
    """Capture desktop screenshot on macOS."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="desktop_capture",
            description="Capture macOS desktop screenshot; can wake display first.",
            parameters=[
                ToolParameter(
                    name="wake",
                    type="boolean",
                    description="Wake display before screenshot (default true).",
                    required=False,
                ),
                ToolParameter(
                    name="delay_ms",
                    type="integer",
                    description="Delay after wake-up before capture (default 350ms).",
                    required=False,
                ),
                ToolParameter(
                    name="filename",
                    type="string",
                    description="Optional output filename (png).",
                    required=False,
                ),
            ],
        )

    async def _run(
        self,
        *args: str,
        timeout: float = 8.0,
    ) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return 124, "", "command timeout"
        return (
            proc.returncode or 0,
            out.decode(errors="replace"),
            err.decode(errors="replace"),
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        if sys.platform != "darwin":
            return ToolResult(success=False, output="", error="desktop_capture 仅支持 macOS")

        wake = bool(kwargs.get("wake", True))
        delay_ms = int(kwargs.get("delay_ms", 350))
        filename = str(kwargs.get("filename", "")).strip()
        if filename and not filename.lower().endswith(".png"):
            filename += ".png"
        if not filename:
            filename = f"desktop_{uuid.uuid4().hex[:8]}.png"

        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _SCREENSHOT_DIR / filename

        if wake:
            # Simulate user activity to wake display; ignore failure and continue.
            _ = await self._run("/usr/bin/caffeinate", "-u", "-t", "2", timeout=3.0)
            if delay_ms > 0:
                await asyncio.sleep(min(delay_ms, 4000) / 1000)

        code, _out, err = await self._run(
            "/usr/sbin/screencapture",
            "-x",
            str(output_path),
            timeout=8.0,
        )
        if code != 0 or not output_path.is_file():
            return ToolResult(
                success=False,
                output="",
                error=f"桌面截图失败: {err.strip() or f'exit={code}'}",
            )
        return ToolResult(success=True, output=f"桌面截图已保存: {output_path}")
