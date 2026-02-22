"""Feishu drive (cloud storage) tool."""

from __future__ import annotations

from typing import Any

from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FeishuDriveTool(Tool):
    """List, upload, and manage files in Feishu Drive."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="feishu_drive",
            description="Operate on Feishu Drive files.",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform.",
                    enum=["list", "create_folder"],
                ),
                ToolParameter(
                    name="folder_token",
                    type="string",
                    description="Folder token.",
                    required=False,
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="Folder name (for create_folder).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")

        if action == "list":
            folder = kwargs.get("folder_token", "")
            params = f"?folder_token={folder}" if folder else ""
            data = await self._client.request("GET", f"/drive/v1/files{params}")
            files = data.get("data", {}).get("files", [])
            lines = [f"- {f.get('name', '')} ({f.get('type', '')})" for f in files]
            return ToolResult(success=True, output="\n".join(lines) or "无文件")

        if action == "create_folder":
            name = kwargs.get("name", "New Folder")
            folder = kwargs.get("folder_token", "")
            body: dict[str, str] = {"name": name, "folder_token": folder}
            data = await self._client.request("POST", "/drive/v1/files/create_folder", json=body)
            token = data.get("data", {}).get("token", "")
            return ToolResult(success=True, output=f"文件夹已创建: {token}")

        return ToolResult(success=False, output="", error=f"未知操作: {action}")
