"""Canvas state management per session."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CanvasState(BaseModel):
    """Per-session canvas state."""

    session_id: str
    html: str = ""
    css: str = ""
    js: str = ""
    title: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CanvasHost:
    """Manages canvas states per session."""

    def __init__(self) -> None:
        self._states: dict[str, CanvasState] = {}

    def push(
        self,
        session_id: str,
        html: str,
        css: str = "",
        js: str = "",
        title: str = "",
    ) -> CanvasState:
        """Create or update canvas state for session."""
        now = datetime.now(UTC)
        state = CanvasState(
            session_id=session_id,
            html=html,
            css=css,
            js=js,
            title=title,
            updated_at=now,
        )
        self._states[session_id] = state
        return state

    def reset(self, session_id: str) -> None:
        """Remove canvas state for session."""
        self._states.pop(session_id, None)

    def get(self, session_id: str) -> CanvasState | None:
        """Get canvas state for session."""
        return self._states.get(session_id)

    def list_sessions(self) -> list[str]:
        """Return session IDs that have canvas state."""
        return list(self._states.keys())
