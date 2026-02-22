"""Chat commands — slash-commands handled before reaching the LLM."""

from __future__ import annotations

from whaleclaw.sessions.manager import Session, SessionManager
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)

_HELP_TEXT = """\
可用命令:
  /new, /reset   — 重置当前会话
  /status        — 显示会话状态
  /model <id>    — 切换模型 (如 /model openai/gpt-4o)
  /think <level> — 设置思考深度 (off/low/medium/high)
  /compact       — 压缩会话上下文
  /help          — 显示此帮助"""

_VALID_THINKING = {"off", "low", "medium", "high", "xhigh"}


class ChatCommand:
    """Parse and execute slash-commands."""

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    async def handle(self, text: str, session: Session) -> str | None:
        """If *text* is a command, execute it and return a response string.

        Returns ``None`` if *text* is not a command.
        """
        stripped = text.strip()
        if not stripped.startswith("/"):
            return None

        parts = stripped.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/new", "/reset"):
            await self._sm.reset(session.id)
            return "会话已重置。"

        if cmd == "/status":
            return (
                f"会话 ID: {session.id}\n"
                f"模型: {session.model}\n"
                f"思考深度: {session.thinking_level}\n"
                f"消息数: {len(session.messages)}\n"
                f"渠道: {session.channel}"
            )

        if cmd == "/model":
            if not arg:
                return f"当前模型: {session.model}\n用法: /model <provider/model>"
            await self._sm.update_model(session, arg)
            return f"已切换到 {arg}"

        if cmd == "/think":
            if not arg or arg not in _VALID_THINKING:
                opts = "|".join(sorted(_VALID_THINKING))
                return f"当前: {session.thinking_level}\n用法: /think <{opts}>"
            await self._sm.update_thinking(session, arg)
            return f"思考深度已设置为 {arg}"

        if cmd == "/compact":
            return "上下文压缩功能将在后续版本实现。"

        if cmd == "/help":
            return _HELP_TEXT

        return f"未知命令: {cmd}\n输入 /help 查看可用命令。"
