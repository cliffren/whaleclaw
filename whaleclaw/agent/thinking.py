"""Thinking mode — budget and provider-specific params for extended reasoning."""

from __future__ import annotations

from enum import StrEnum


class ThinkingLevel(StrEnum):
    """Thinking/reasoning budget level."""

    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


THINKING_BUDGET: dict[ThinkingLevel, int] = {
    ThinkingLevel.OFF: 0,
    ThinkingLevel.LOW: 1024,
    ThinkingLevel.MEDIUM: 4096,
    ThinkingLevel.HIGH: 8192,
    ThinkingLevel.XHIGH: 16384,
}

_OPENAI_EFFORT: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",
}


def apply_thinking_params(
    level: ThinkingLevel,
    provider: str,
    params: dict[str, object],
) -> dict[str, object]:
    """Apply thinking/reasoning params per provider. Returns modified params dict."""
    if level == ThinkingLevel.OFF:
        return params

    budget = THINKING_BUDGET.get(level, 0)
    if budget <= 0:
        return params

    result = dict(params)

    if provider == "anthropic":
        result["thinking"] = {"type": "enabled", "budget_tokens": budget}
    elif provider == "openai":
        result["reasoning_effort"] = _OPENAI_EFFORT.get(level.value, _OPENAI_EFFORT["high"])
    elif provider == "deepseek" and level in (ThinkingLevel.HIGH, ThinkingLevel.XHIGH):
        result["model"] = "deepseek-reasoner"

    return result
