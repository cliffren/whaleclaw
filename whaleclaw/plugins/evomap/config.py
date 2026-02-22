"""EvoMap plugin configuration."""

from __future__ import annotations

from pydantic import BaseModel


class EvoMapConfig(BaseModel):
    """EvoMap plugin configuration."""

    enabled: bool = False
    hub_url: str = "https://evomap.ai"
    auto_fetch: bool = True
    auto_publish: bool = False
    sync_interval_hours: float = 4.0
    webhook_url: str | None = None
    min_confidence_to_publish: float = 0.7
    auto_search_on_error: bool = True
