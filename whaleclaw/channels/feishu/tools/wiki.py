"""Feishu wiki (knowledge base) tool."""

from __future__ import annotations

from typing import Any

from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FeishuWikiTool(Tool):
    """Search and read Feishu knowledge base nodes."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="feishu_wiki",
            description="Search or read Feishu wiki nodes.",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform.",
                    enum=["search", "read"],
                ),
                ToolParameter(
                    name="space_id",
                    type="string",
                    description="Wiki space ID.",
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query (for search).",
                    required=False,
                ),
                ToolParameter(
                    name="node_token",
                    type="string",
                    description="Node token (for read).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")
        space_id = kwargs.get("space_id", "")

        if action == "search":
            query = kwargs.get("query", "")
            data = await self._client.request(
                "POST",
                f"/wiki/v2/spaces/{space_id}/nodes/search",
                json={"query": query},
            )
            nodes = data.get("data", {}).get("items", [])
            lines = [f"- {n.get('title', '')} ({n.get('node_token', '')})" for n in nodes]
            return ToolResult(success=True, output="\n".join(lines) or "无结果")

        if action == "read":
            node_token = kwargs.get("node_token", "")
            if not node_token:
                return ToolResult(success=False, output="", error="node_token 为空")
            data = await self._client.request(
                "GET", f"/wiki/v2/spaces/{space_id}/nodes/{node_token}"
            )
            content = data.get("data", {}).get("node", {}).get("title", "")
            return ToolResult(success=True, output=content)

        return ToolResult(success=False, output="", error=f"未知操作: {action}")
