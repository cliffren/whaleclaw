"""Agent context — bundles session, tools, and router for a single turn."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from whaleclaw.tools.base import ToolResult


class ToolCallCallback:
    """Typed callback protocol for tool-call notifications."""


OnToolCall = Callable[[str, dict[str, Any]], Awaitable[None]]
OnToolResult = Callable[[str, ToolResult], Awaitable[None]]
