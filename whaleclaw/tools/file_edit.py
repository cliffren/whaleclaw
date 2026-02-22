"""File edit tool — exact string replacement."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FileEditTool(Tool):
    """Replace an exact string in a file."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_edit",
            description=(
                "Replace an exact string occurrence in a file. "
                "The old_string must be unique."
            ),
            parameters=[
                ToolParameter(name="path", type="string", description="File path to edit."),
                ToolParameter(
                    name="old_string", type="string", description="Exact string to find."
                ),
                ToolParameter(
                    name="new_string", type="string", description="Replacement string."
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs.get("path", "")
        old_string: str = kwargs.get("old_string", "")
        new_string: str = kwargs.get("new_string", "")

        if not file_path:
            return ToolResult(success=False, output="", error="文件路径为空")
        if not old_string:
            return ToolResult(success=False, output="", error="old_string 为空")

        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            return ToolResult(success=False, output="", error=f"文件不存在: {p}")

        try:
            text = p.read_text(encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        count = text.count(old_string)
        if count == 0:
            return ToolResult(success=False, output="", error="未找到匹配的字符串")
        if count > 1:
            return ToolResult(
                success=False,
                output="",
                error=f"找到 {count} 处匹配，old_string 不唯一",
            )

        new_text = text.replace(old_string, new_string, 1)
        try:
            p.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))

        return ToolResult(success=True, output=f"已替换 {p} 中的内容")
