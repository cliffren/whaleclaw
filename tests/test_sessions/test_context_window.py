"""Tests for context window management."""

from __future__ import annotations

from whaleclaw.providers.base import Message
from whaleclaw.sessions.context_window import ContextWindow


class TestContextWindow:
    def test_compute_budget(self) -> None:
        cw = ContextWindow()
        budget = cw.compute_budget("claude-sonnet-4-20250514")
        assert budget.total == 200_000
        assert budget.system_prompt > 0
        assert budget.conversation > 0
        assert budget.reply_reserve > 0

    def test_compute_budget_unknown_model(self) -> None:
        cw = ContextWindow()
        budget = cw.compute_budget("unknown-model")
        assert budget.total == 128_000

    def test_trim_keeps_recent(self) -> None:
        cw = ContextWindow()
        budget = cw.compute_budget("claude-sonnet-4-20250514")
        msgs = [
            Message(role="system", content="system prompt"),
            *[Message(role="user", content=f"msg {i}") for i in range(10)],
        ]
        trimmed = cw.trim(msgs, budget)
        assert trimmed[0].role == "system"
        assert len(trimmed) > 1
