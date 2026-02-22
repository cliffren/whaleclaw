"""Canvas tool — Agent-driven visual workspace updates."""

from __future__ import annotations

import json
from typing import Any

from whaleclaw.canvas.host import CanvasHost
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class CanvasTool(Tool):
    """Update/reset/get canvas state for a session."""

    def __init__(self, host: CanvasHost, session_id: str) -> None:
        self._host = host
        self._session_id = session_id

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="canvas",
            description="更新或获取 Canvas 可视化工作区内容 (HTML/CSS/JS)。",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="操作: push 更新内容, reset 清空, get 获取当前状态。",
                    enum=["push", "reset", "get"],
                ),
                ToolParameter(
                    name="html",
                    type="string",
                    description="HTML 内容 (push 时使用)。",
                    required=False,
                ),
                ToolParameter(
                    name="css",
                    type="string",
                    description="CSS 内容 (push 时使用)。",
                    required=False,
                ),
                ToolParameter(
                    name="js",
                    type="string",
                    description="JS 内容 (push 时使用)。",
                    required=False,
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description="Canvas 标题 (push 时使用)。",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = str(kwargs.get("action", "")).lower()

        if action == "push":
            html = str(kwargs.get("html", ""))
            css = str(kwargs.get("css", "")) if kwargs.get("css") else ""
            js = str(kwargs.get("js", "")) if kwargs.get("js") else ""
            title = str(kwargs.get("title", "")) if kwargs.get("title") else ""
            state = self._host.push(self._session_id, html=html, css=css, js=js, title=title)
            return ToolResult(
                success=True,
                output=f"Canvas 已更新: {state.title or '(无标题)'}",
            )

        if action == "reset":
            self._host.reset(self._session_id)
            return ToolResult(success=True, output="Canvas 已重置")

        if action == "get":
            state = self._host.get(self._session_id)
            if state is None:
                return ToolResult(success=True, output="{}")
            data = state.model_dump(mode="json")
            return ToolResult(success=True, output=json.dumps(data))

        return ToolResult(
            success=False,
            output="",
            error=f"未知操作: {action}，应为 push/reset/get",
        )
