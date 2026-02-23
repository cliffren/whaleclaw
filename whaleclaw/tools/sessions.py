"""Session management tools for Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

if TYPE_CHECKING:
    from whaleclaw.sessions.manager import SessionManager


class SessionsListTool(Tool):
    """List active sessions."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._manager = session_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="sessions_list",
            description="列出活跃会话",
            parameters=[],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        sessions = await self._manager.list_sessions()
        lines = [
            f"- {s.id}: channel={s.channel}, last_active={s.updated_at.isoformat()}"
            for s in sessions
        ]
        return ToolResult(success=True, output="\n".join(lines) if lines else "无活跃会话")


class SessionsHistoryTool(Tool):
    """Fetch message history for a session."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._manager = session_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="sessions_history",
            description="获取会话的消息历史",
            parameters=[
                ToolParameter(
                    name="session_id",
                    type="string",
                    description="会话 ID",
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="最多返回的消息条数",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        session_id = kwargs.get("session_id", "")
        limit = kwargs.get("limit")
        limit = int(limit) if limit is not None else 20

        if not session_id:
            return ToolResult(success=False, output="", error="session_id 为空")

        session = await self._manager.get(session_id)
        if session is None:
            return ToolResult(success=False, output="", error="会话未找到")

        msgs = session.messages[-limit:] if limit > 0 else session.messages
        lines: list[str] = []
        for m in msgs:
            prefix = f"[{m.role}]"
            if m.tool_calls:
                tool_names = ", ".join(tc.name for tc in m.tool_calls)
                lines.append(f"{prefix}: (调用工具: {tool_names}) {m.content or ''}")
            elif m.tool_call_id:
                snippet = m.content[:200] if m.content else ""
                lines.append(f"{prefix}: [工具结果] {snippet}")
            else:
                lines.append(f"{prefix}: {m.content}")
        return ToolResult(success=True, output="\n".join(lines) if lines else "无消息")


class SessionsSendTool(Tool):
    """Send a message to a session as assistant."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._manager = session_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="sessions_send",
            description="向指定会话发送助手消息",
            parameters=[
                ToolParameter(
                    name="session_id",
                    type="string",
                    description="会话 ID",
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="要发送的消息内容",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        session_id = kwargs.get("session_id", "")
        message = kwargs.get("message", "")

        if not session_id:
            return ToolResult(success=False, output="", error="session_id 为空")
        if not message:
            return ToolResult(success=False, output="", error="message 为空")

        session = await self._manager.get(session_id)
        if session is None:
            return ToolResult(success=False, output="", error="会话未找到")

        try:
            await self._manager.add_message(session, "assistant", message)
            return ToolResult(success=True, output="消息已发送")
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))
