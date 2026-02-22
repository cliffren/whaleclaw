"""Hook system for plugin extensibility."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class HookPoint(StrEnum):
    """Available hook points in the message pipeline."""

    BEFORE_MESSAGE = "before_message"
    AFTER_MESSAGE = "after_message"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    ON_SESSION_CREATE = "on_session_create"
    ON_SESSION_RESET = "on_session_reset"
    ON_ERROR = "on_error"


class HookContext(BaseModel):
    """Context passed to hook callbacks."""

    hook: HookPoint
    session_id: str
    data: dict[str, Any] = {}


class HookResult(BaseModel):
    """Return value from hook callbacks."""

    proceed: bool = True
    data: dict[str, Any] = {}


HookCallback = Callable[[HookContext], Awaitable[HookResult]]


class HookManager:
    """Manages hook registration and execution."""

    def __init__(self) -> None:
        self._callbacks: dict[HookPoint, list[tuple[int, HookCallback]]] = {
            hp: [] for hp in HookPoint
        }

    def register(
        self,
        hook: HookPoint,
        callback: HookCallback,
        priority: int = 0,
    ) -> None:
        """Register a callback for a hook point."""
        self._callbacks[hook].append((priority, callback))
        self._callbacks[hook].sort(key=lambda x: x[0])

    async def run(self, hook: HookPoint, context: HookContext) -> HookResult:
        """Execute callbacks in priority order. Stops if proceed=False."""
        merged_data = dict(context.data)
        for _priority, cb in self._callbacks[hook]:
            ctx = HookContext(
                hook=hook,
                session_id=context.session_id,
                data=merged_data,
            )
            result = await cb(ctx)
            merged_data = result.data
            if not result.proceed:
                return HookResult(proceed=False, data=merged_data)
        return HookResult(proceed=True, data=merged_data)
