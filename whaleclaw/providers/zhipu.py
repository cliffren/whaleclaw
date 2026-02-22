"""Zhipu GLM (智谱) provider adapter (OpenAI-compatible)."""

from __future__ import annotations

from whaleclaw.providers.openai_compat import OpenAICompatProvider


class ZhipuProvider(OpenAICompatProvider):
    """Zhipu Open Platform API (glm-5, glm-4.7, glm-4.7-flash)."""

    provider_name = "zhipu"
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    env_key = "ZHIPU_API_KEY"
