"""Tests for the PromptAssembler."""

from __future__ import annotations

from whaleclaw.agent.prompt import PromptAssembler
from whaleclaw.config.schema import WhaleclawConfig


class TestPromptAssembler:
    def test_build_returns_system_message(self) -> None:
        assembler = PromptAssembler()
        messages = assembler.build(WhaleclawConfig(), "你好")
        assert len(messages) == 1
        assert messages[0].role == "system"
        assert "WhaleClaw" in messages[0].content
        assert "任务追踪" in messages[0].content
        assert "任务专注" in messages[0].content

    def test_static_has_cache_control(self) -> None:
        assembler = PromptAssembler()
        messages = assembler.build(WhaleclawConfig(), "test")
        assert messages[0].cache_control is not None
        assert messages[0].cache_control.type == "ephemeral"

    def test_estimate_tokens_cjk(self) -> None:
        assembler = PromptAssembler()
        tokens = assembler.estimate_tokens("你好世界")
        assert tokens > 0

    def test_estimate_tokens_latin(self) -> None:
        assembler = PromptAssembler()
        tokens = assembler.estimate_tokens("hello world")
        assert tokens > 0

    def test_build_supports_custom_assistant_name(self) -> None:
        assembler = PromptAssembler()
        messages = assembler.build(
            WhaleclawConfig(),
            "你好",
            assistant_name="旺财",
        )
        assert "你是 旺财" in messages[0].content
