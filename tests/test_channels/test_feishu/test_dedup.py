"""Tests for Feishu message deduplication."""

from __future__ import annotations

from whaleclaw.channels.feishu.dedup import MessageDedup


class TestMessageDedup:
    def test_not_duplicate(self) -> None:
        d = MessageDedup()
        assert not d.is_duplicate("msg1")

    def test_mark_then_duplicate(self) -> None:
        d = MessageDedup()
        d.mark("msg1")
        assert d.is_duplicate("msg1")
        assert not d.is_duplicate("msg2")

    def test_eviction(self) -> None:
        d = MessageDedup(ttl=0)
        d.mark("msg1")
        assert not d.is_duplicate("msg1")
