"""Node invoke tool — Call device node actions."""

from __future__ import annotations

import json
from typing import Any

from whaleclaw.nodes.manager import NodeManager
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class NodeInvokeTool(Tool):
    """Invoke actions on registered device nodes."""

    def __init__(self, node_manager: NodeManager) -> None:
        self._manager = node_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="node_invoke",
            description="调用已注册设备节点的能力 (如 camera.snap, notification 等)。",
            parameters=[
                ToolParameter(
                    name="node_id",
                    type="string",
                    description="节点 ID。",
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    description="要执行的能力或操作，如 camera.snap, notification。",
                ),
                ToolParameter(
                    name="params",
                    type="string",
                    description="JSON 格式的参数字符串，可选。",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        node_id = str(kwargs.get("node_id", ""))
        action = str(kwargs.get("action", ""))
        params_raw = kwargs.get("params")

        if not node_id:
            return ToolResult(success=False, output="", error="node_id 不能为空")
        if not action:
            return ToolResult(success=False, output="", error="action 不能为空")

        params: dict = {}
        if params_raw:
            try:
                params = json.loads(str(params_raw))
                if not isinstance(params, dict):
                    params = {}
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="params 不是有效 JSON")

        result = await self._manager.invoke(node_id, action, params)
        output = json.dumps(result)
        success = result.get("status") != "error" and result.get("status") != "not_implemented"
        return ToolResult(
            success=success,
            output=output,
            error=result.get("error") if not success else None,
        )
