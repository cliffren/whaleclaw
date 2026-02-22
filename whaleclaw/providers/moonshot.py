"""Moonshot Kimi (月之暗面) provider adapter (OpenAI-compatible)."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class MoonshotProvider(OpenAICompatProvider):
    """Moonshot API (kimi-k2.5, kimi-k2-thinking, etc.)."""

    provider_name = "moonshot"
    default_base_url = "https://api.moonshot.cn/v1"
    env_key = "MOONSHOT_API_KEY"
