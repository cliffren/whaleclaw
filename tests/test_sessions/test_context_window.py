"""Tests for context window management."""

from __future__ import annotations

from whaleclaw.providers.base import Message
from whaleclaw.sessions.context_window import ContextWindow


class TestContextWindow:
    def test_get_max_context_known(self) -> None:
        cw = ContextWindow()
        assert cw.get_max_context("claude-sonnet-4-20250514") == 200_000

    def test_get_max_context_unknown(self) -> None:
        cw = ContextWindow()
        assert cw.get_max_context("unknown-model") == 128_000

    def test_no_compression_when_within_budget(self) -> None:
        """All messages fit → nothing should be changed."""
        cw = ContextWindow()
        msgs = [
            Message(role="system", content="system prompt"),
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi there"),
            Message(role="user", content="做个PPT"),
            Message(role="assistant", content="好的，PPT做好了"),
        ]
        trimmed = cw.trim(msgs, "glm-4.7")
        assert len(trimmed) == 5
        assert trimmed[1].content == "hello"
        assert trimmed[4].content == "好的，PPT做好了"

    def test_tool_output_compressed_when_needed(self) -> None:
        """Tool outputs in old zone get compressed when budget is tight."""
        cw = ContextWindow()
        long_tool = "[bash] " + "成功执行\n路径: /tmp/test\nlog output\n" * 200
        msgs = [
            Message(role="system", content="s" * 20000),
            Message(role="user", content="运行命令"),
            Message(role="assistant", content=long_tool),
            *[Message(role="user", content="对话内容 " * 200) for _ in range(40)],
            Message(role="user", content="最新消息"),
            Message(role="assistant", content="好的"),
        ]
        trimmed = cw.trim(msgs, "qwen-max")
        tool_msgs = [m for m in trimmed if "[bash]" in m.content]
        if tool_msgs:
            assert len(tool_msgs[0].content) < len(long_tool)

    def test_no_compression_when_fits(self) -> None:
        """Nothing compressed when everything fits within budget."""
        cw = ContextWindow()
        long_tool = "[bash] " + "log output line\n" * 500
        msgs = [
            Message(role="system", content="sys"),
            Message(role="user", content="运行命令"),
            Message(role="assistant", content=long_tool),
            Message(role="user", content="好"),
        ]
        trimmed = cw.trim(msgs, "glm-4.7")
        tool_msg = [m for m in trimmed if m.content.startswith("[bash]")][0]
        assert tool_msg.content == long_tool

    def test_recent_messages_protected(self) -> None:
        """Recent messages should not be compressed."""
        cw = ContextWindow()
        recent_content = "这是最近的重要消息，包含具体指令和要求" * 10
        msgs = [
            Message(role="system", content="s" * 20000),
            *[Message(role="user", content="old " * 200) for _ in range(50)],
            Message(role="user", content=recent_content),
            Message(role="assistant", content="收到"),
        ]
        trimmed = cw.trim(msgs, "qwen-max")
        assert trimmed[-1].content == "收到"
        assert trimmed[-2].content == recent_content

    def test_drops_old_with_summary_when_extreme(self) -> None:
        """When even compression can't fit, drop oldest and add summary."""
        cw = ContextWindow()
        msgs = [
            Message(role="system", content="s" * 25000),
            *[Message(role="user", content="重要消息 " * 300) for _ in range(100)],
            Message(role="user", content="最新消息"),
        ]
        trimmed = cw.trim(msgs, "qwen-max")
        assert trimmed[-1].content == "最新消息"
        assert len(trimmed) < len(msgs)
        has_summary = any("摘要" in m.content for m in trimmed)
        assert has_summary
