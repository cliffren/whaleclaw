"""Alibaba Qwen (通义千问) provider adapter (OpenAI-compatible DashScope)."""

from __future__ import annotations

from typing import Any

from whaleclaw.providers.base import Message, ToolSchema
from whaleclaw.providers.openai_compat import OpenAICompatProvider


class QwenProvider(OpenAICompatProvider):
    """DashScope API (qwen3.5-plus, qwen3-max, qwq-plus, qwen-max, qwen-plus)."""

    provider_name = "qwen"
    default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    env_key = "DASHSCOPE_API_KEY"

    def _build_body(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolSchema] | None,
    ) -> dict[str, Any]:
        body = super()._build_body(messages, model, tools)
        if body.get("stream"):
            body["stream_options"] = {"include_usage": True}
        return body
