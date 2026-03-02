"""Aliyun Bailian provider adapter (OpenAI-compatible, dashscope endpoint)."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class BailianProvider(OpenAICompatProvider):
    """Aliyun Bailian (百炼) — qwen3, glm, kimi-k2, minimax-m2 etc.

    Uses the OpenAI-compatible DashScope endpoint.
    API key obtained from https://bailian.console.aliyun.com/
    """

    provider_name = "bailian"
    default_base_url = "https://dashscope.aliyuncs.com/v1"
    env_key = "BAILIAN_API_KEY"
