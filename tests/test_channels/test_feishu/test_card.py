"""Tests for Feishu card builder."""

from __future__ import annotations

import json

from whaleclaw.channels.feishu.card import FeishuCard


class TestFeishuCard:
    def test_text_card(self) -> None:
        card_str = FeishuCard.text_card("Hello", title="Test")
        card = json.loads(card_str)
        assert card["header"]["title"]["content"] == "Test"
        assert card["elements"][0]["text"]["content"] == "Hello"

    def test_streaming_card(self) -> None:
        card_str = FeishuCard.streaming_card()
        card = json.loads(card_str)
        assert "思考中" in card["elements"][0]["text"]["content"]

    def test_error_card(self) -> None:
        card_str = FeishuCard.error_card("Something went wrong")
        card = json.loads(card_str)
        assert card["header"]["template"] == "red"

    def test_tool_call_card(self) -> None:
        element = FeishuCard.tool_call_card("bash", {"command": "ls"}, "file1.py")
        assert element["tag"] == "collapsible_panel"
