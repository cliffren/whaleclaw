"""MiniMax (海螺 AI) provider adapter (OpenAI-compatible)."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class MiniMaxProvider(OpenAICompatProvider):
    """MiniMax API (MiniMax-M2.5, MiniMax-M2.1, etc.)."""

    provider_name = "minimax"
    default_base_url = "https://api.minimax.chat/v1"
    env_key = "MINIMAX_API_KEY"
