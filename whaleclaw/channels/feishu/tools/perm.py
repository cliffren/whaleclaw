"""Feishu permissions management tool."""

from __future__ import annotations

from typing import Any

from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FeishuPermTool(Tool):
    """View and manage document permissions in Feishu."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="feishu_perm",
            description="Manage Feishu document permissions.",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform.",
                    enum=["list", "add"],
                ),
                ToolParameter(name="token", type="string", description="Document token."),
                ToolParameter(
                    name="type",
                    type="string",
                    description="Document type (doc/sheet/bitable).",
                ),
                ToolParameter(
                    name="member_id",
                    type="string",
                    description="Member open_id (for add).",
                    required=False,
                ),
                ToolParameter(
                    name="perm",
                    type="string",
                    description="Permission level (view/edit/full_access).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")
        token = kwargs.get("token", "")
        doc_type = kwargs.get("type", "doc")

        if action == "list":
            data = await self._client.request(
                "GET",
                f"/drive/v1/permissions/{token}/members?type={doc_type}",
            )
            members = data.get("data", {}).get("items", [])
            lines = [
                f"- {m.get('member_id', '')} ({m.get('perm', '')})"
                for m in members
            ]
            return ToolResult(success=True, output="\n".join(lines) or "无协作者")

        if action == "add":
            member_id = kwargs.get("member_id", "")
            perm = kwargs.get("perm", "view")
            data = await self._client.request(
                "POST",
                f"/drive/v1/permissions/{token}/members?type={doc_type}",
                json={
                    "member_type": "openid",
                    "member_id": member_id,
                    "perm": perm,
                },
            )
            return ToolResult(success=True, output=f"已添加协作者: {member_id}")

        return ToolResult(success=False, output="", error=f"未知操作: {action}")
