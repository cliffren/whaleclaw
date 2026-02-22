"""Feishu interactive card builder."""

from __future__ import annotations

import json
from typing import Any


class FeishuCard:
    """Build Feishu interactive cards (message card v2)."""

    @staticmethod
    def text_card(
        content: str, title: str | None = None
    ) -> str:
        """Build a Markdown text card and return as JSON string."""
        elements: list[dict[str, Any]] = [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}},
        ]
        card: dict[str, Any] = {
            "config": {"wide_screen_mode": True},
            "elements": elements,
        }
        if title:
            card["header"] = {
                "title": {"tag": "plain_text", "content": title},
            }
        return json.dumps(card, ensure_ascii=False)

    @staticmethod
    def streaming_card(initial_text: str = "") -> str:
        """Build an initial streaming card (shows spinner)."""
        text = initial_text or "思考中..."
        elements: list[dict[str, Any]] = [
            {"tag": "div", "text": {"tag": "lark_md", "content": text}},
        ]
        card: dict[str, Any] = {
            "config": {"wide_screen_mode": True},
            "elements": elements,
        }
        return json.dumps(card, ensure_ascii=False)

    @staticmethod
    def error_card(error: str) -> str:
        """Build an error card."""
        card: dict[str, Any] = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "错误"},
                "template": "red",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": error}},
            ],
        }
        return json.dumps(card, ensure_ascii=False)

    @staticmethod
    def tool_call_card(
        tool_name: str,
        arguments: dict[str, Any],
        result: str | None = None,
    ) -> dict[str, Any]:
        """Build a collapsible tool-call card element."""
        args_text = json.dumps(arguments, ensure_ascii=False, indent=2)
        header = f"**🔧 {tool_name}**"
        body = f"```\n{args_text}\n```"
        if result is not None:
            body += f"\n\n**结果:**\n```\n{result}\n```"
        return {
            "tag": "collapsible_panel",
            "expanded": False,
            "header": {
                "title": {"tag": "plain_text", "content": header},
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": body}},
            ],
        }
