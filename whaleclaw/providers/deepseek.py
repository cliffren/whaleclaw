"""DeepSeek provider adapter (OpenAI-compatible)."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    """DeepSeek API (deepseek-chat, deepseek-reasoner)."""

    provider_name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"
    env_key = "DEEPSEEK_API_KEY"
