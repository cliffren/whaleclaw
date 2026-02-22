"""Feishu document (docx) tool."""

from __future__ import annotations

from typing import Any

from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FeishuDocxTool(Tool):
    """Create, read, and update Feishu documents."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="feishu_docx",
            description="Operate on Feishu documents (create/read/update).",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform.",
                    enum=["create", "read", "list"],
                ),
                ToolParameter(
                    name="document_id",
                    type="string",
                    description="Document ID (for read).",
                    required=False,
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description="Document title (for create).",
                    required=False,
                ),
                ToolParameter(
                    name="folder_token",
                    type="string",
                    description="Parent folder token.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")

        if action == "create":
            title = kwargs.get("title", "Untitled")
            folder = kwargs.get("folder_token", "")
            body: dict[str, Any] = {"title": title}
            if folder:
                body["folder_token"] = folder
            data = await self._client.request("POST", "/docx/v1/documents", json=body)
            doc_id = data.get("data", {}).get("document", {}).get("document_id", "")
            return ToolResult(success=True, output=f"文档已创建: {doc_id}")

        if action == "read":
            doc_id = kwargs.get("document_id", "")
            if not doc_id:
                return ToolResult(success=False, output="", error="document_id 为空")
            data = await self._client.request("GET", f"/docx/v1/documents/{doc_id}/raw_content")
            content = data.get("data", {}).get("content", "")
            return ToolResult(success=True, output=content)

        if action == "list":
            folder = kwargs.get("folder_token", "")
            path = f"/drive/v1/files?folder_token={folder}" if folder else "/drive/v1/files"
            data = await self._client.request("GET", path)
            files = data.get("data", {}).get("files", [])
            lines = [f"- {f.get('name', '')} ({f.get('token', '')})" for f in files]
            return ToolResult(success=True, output="\n".join(lines) or "无文件")

        return ToolResult(success=False, output="", error=f"未知操作: {action}")
