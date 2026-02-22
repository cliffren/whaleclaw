"""NVIDIA NIM provider adapter (OpenAI-compatible)."""

from __future__ import annotations

from whaleclaw.providers.base import AgentResponse, Message, ToolSchema
from whaleclaw.providers.openai_compat import OpenAICompatProvider
from whaleclaw.types import StreamCallback

_NIM_TOOL_CAPABLE_PREFIXES = (
    "meta/llama-3",
    "mistralai/",
    "nvidia/llama-3",
    "nvidia/nemotron",
    "gpt-oss-",
    "z-ai/glm-4",
    "z-ai/glm4",
    "z-ai/glm-5",
    "z-ai/glm5",
    "qwen/qwen",
    "stepfun-ai/step",
    "moonshotai/kimi",
)


class NvidiaProvider(OpenAICompatProvider):
    """NVIDIA NIM API (free models via build.nvidia.com).

    NIM supports function calling only for certain model families.
    For others we fall back to prompt-based tool injection.
    """

    provider_name = "nvidia"
    default_base_url = "https://integrate.api.nvidia.com/v1"
    env_key = "NVIDIA_API_KEY"
    supports_native_tools = True

    @staticmethod
    def model_supports_tools(model: str) -> bool:
        """Check if a specific NIM model supports native function calling."""
        lower = model.lower()
        return any(lower.startswith(p) for p in _NIM_TOOL_CAPABLE_PREFIXES)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        *,
        tools: list[ToolSchema] | None = None,
        on_stream: StreamCallback | None = None,
    ) -> AgentResponse:
        effective_tools = tools if self.model_supports_tools(model) else None
        return await super().chat(
            messages, model, tools=effective_tools, on_stream=on_stream
        )
