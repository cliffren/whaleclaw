"""File read tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

_MAX_SIZE = 500_000


class FileReadTool(Tool):
    """Read file contents, optionally with line range."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="Read the contents of a file. Supports optional line offset and limit.",
            parameters=[
                ToolParameter(name="path", type="string", description="File path to read."),
                ToolParameter(
                    name="offset",
                    type="integer",
                    description="Line number to start reading from (1-based).",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Number of lines to read.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        offset: int = int(kwargs.get("offset", 0))
        limit: int | None = kwargs.get("limit")
        if limit is not None:
            limit = int(limit)

        if not file_path:
            return ToolResult(success=False, output="", error="文件路径为空")

        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            return ToolResult(success=False, output="", error=f"文件不存在: {p}")

        if p.stat().st_size > _MAX_SIZE:
            return ToolResult(success=False, output="", error=f"文件过大 (>{_MAX_SIZE} bytes)")

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        lines = text.splitlines(keepends=True)

        if offset > 0:
            lines = lines[offset - 1 :]
        if limit is not None and limit > 0:
            lines = lines[:limit]

        numbered = [f"{i + (offset or 1):>6}|{line}" for i, line in enumerate(lines)]
        return ToolResult(success=True, output="".join(numbered))
