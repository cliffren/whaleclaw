"""OpenAI GPT provider adapter."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class OpenAIProvider(OpenAICompatProvider):
    """OpenAI Chat Completions API (GPT-4o, GPT-4.1, o3, etc.)."""

    provider_name = "openai"
    default_base_url = "https://api.openai.com/v1"
    env_key = "OPENAI_API_KEY"
    supports_cache_control = False
