"""File write tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FileWriteTool(Tool):
    """Write (overwrite) a file with the given content."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description=(
                "Write content to a file, creating it if necessary. "
                "Overwrites existing content."
            ),
            parameters=[
                ToolParameter(name="path", type="string", description="File path to write."),
                ToolParameter(
                    name="content", type="string", description="Content to write to the file."
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("path", "")
        content: str = kwargs.get("content", "")

        if not file_path:
            return ToolResult(success=False, output="", error="文件路径为空")

        p = Path(file_path).expanduser().resolve()

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        return ToolResult(success=True, output=f"已写入 {len(content)} 字符到 {p}")
