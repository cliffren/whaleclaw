"""Telegram channel configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    bot_token: str = ""
    mode: Literal["polling", "webhook"] = "polling"
    webhook_url: str | None = None
    webhook_path: str = "/webhook/telegram"
    dm_policy: Literal["open", "closed"] = "open"
    allowed_user_ids: list[int] = Field(default_factory=list)
