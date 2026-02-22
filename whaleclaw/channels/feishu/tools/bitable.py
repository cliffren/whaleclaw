"""Feishu Bitable (multi-dimensional spreadsheet) tool."""

from __future__ import annotations

from typing import Any

from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class FeishuBitableTool(Tool):
    """Read and write records in Feishu Bitable."""

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="feishu_bitable",
            description="Operate on Feishu Bitable records.",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform.",
                    enum=["list_records", "create_record"],
                ),
                ToolParameter(name="app_token", type="string", description="Bitable app token."),
                ToolParameter(name="table_id", type="string", description="Table ID."),
                ToolParameter(
                    name="fields",
                    type="object",
                    description="Record fields (for create_record).",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")
        app_token = kwargs.get("app_token", "")
        table_id = kwargs.get("table_id", "")

        if action == "list_records":
            data = await self._client.request(
                "GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            )
            records = data.get("data", {}).get("items", [])
            lines = [str(r.get("fields", {})) for r in records[:20]]
            return ToolResult(success=True, output="\n".join(lines) or "无记录")

        if action == "create_record":
            fields = kwargs.get("fields", {})
            data = await self._client.request(
                "POST",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                json={"fields": fields},
            )
            record_id = data.get("data", {}).get("record", {}).get("record_id", "")
            return ToolResult(success=True, output=f"记录已创建: {record_id}")

        return ToolResult(success=False, output="", error=f"未知操作: {action}")
