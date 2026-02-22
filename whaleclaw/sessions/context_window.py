"""Context window management with token budgeting."""

from __future__ import annotations

from pydantic import BaseModel

from whaleclaw.providers.base import Message

MODEL_MAX_CONTEXT: dict[str, int] = {
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "gpt-4o": 128_000,
    "gpt-4.1": 1_000_000,
    "o3": 200_000,
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,
    "qwen-max": 32_000,
    "qwen-plus": 131_072,
    "qwen-turbo": 131_072,
    "glm-5": 200_000,
    "glm-4.7": 200_000,
    "glm-4.7-flash": 200_000,
    "MiniMax-M2.5": 1_000_000,
    "MiniMax-M2.1": 1_000_000,
    "kimi-k2.5": 256_000,
    "kimi-k2-thinking": 128_000,
    "gemini-3.1-pro-preview": 1_000_000,
    "gemini-3-pro-preview": 1_000_000,
    "gemini-3-flash-preview": 1_000_000,
    "meta/llama-3.1-8b-instruct": 128_000,
}

_DEFAULT_CONTEXT = 128_000


class TokenBudget(BaseModel):
    """Token budget allocation for the context window."""

    total: int
    system_prompt: int
    tools_schema: int
    conversation: int
    reply_reserve: int


def _estimate_tokens(text: str) -> int:
    """Quick token estimate: ~1.5 chars/token CJK, ~4 chars/token Latin."""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin = len(text) - cjk
    return max(1, int(cjk / 1.5 + latin / 4))


class ContextWindow:
    """Manages context window trimming and budget allocation."""

    def compute_budget(self, model: str) -> TokenBudget:
        """Compute token budget based on model's max context."""
        total = MODEL_MAX_CONTEXT.get(model, _DEFAULT_CONTEXT)
        return TokenBudget(
            total=total,
            system_prompt=int(total * 0.15),
            tools_schema=int(total * 0.05),
            conversation=int(total * 0.55),
            reply_reserve=int(total * 0.25),
        )

    def trim(
        self, messages: list[Message], budget: TokenBudget
    ) -> list[Message]:
        """Trim conversation messages to fit within the conversation budget.

        Always keeps the most recent messages. System messages are excluded
        from trimming (they have their own budget).
        """
        non_system = [m for m in messages if m.role != "system"]
        system = [m for m in messages if m.role == "system"]

        total = 0
        kept: list[Message] = []
        for msg in reversed(non_system):
            cost = _estimate_tokens(msg.content)
            if total + cost > budget.conversation:
                break
            kept.append(msg)
            total += cost

        kept.reverse()
        return [*system, *kept]
