"""Feishu @mention extraction and formatting."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel


class MentionTarget(BaseModel):
    """A single @mention target."""

    user_id: str
    name: str
    id_type: str = "open_id"


def extract_mention_targets(message: dict[str, Any]) -> list[MentionTarget]:
    """Extract @mention targets from a Feishu message event."""
    mentions = message.get("mentions") or []
    targets: list[MentionTarget] = []
    for m in mentions:
        key = m.get("key", "")
        user_id = m.get("id", {}).get("open_id", "") or m.get("id", {}).get("user_id", "")
        name = m.get("name", key)
        if user_id:
            targets.append(MentionTarget(user_id=user_id, name=name))
    return targets


def is_bot_mentioned(
    message: dict[str, Any], bot_open_id: str
) -> bool:
    """Check if the bot is @mentioned in a message."""
    return any(target.user_id == bot_open_id for target in extract_mention_targets(message))


def strip_bot_mention(text: str, bot_name: str) -> str:
    """Remove @bot_name from the text."""
    pattern = re.compile(rf"@{re.escape(bot_name)}\s*", re.IGNORECASE)
    return pattern.sub("", text).strip()


def format_mention_for_text(user_id: str, name: str) -> str:
    """Format an @mention for a text message."""
    return f'<at user_id="{user_id}">{name}</at>'


def format_mention_for_card(user_id: str, name: str) -> dict[str, Any]:
    """Format an @mention element for a card message."""
    return {
        "tag": "at",
        "user_id": user_id,
        "user_name": name,
    }
