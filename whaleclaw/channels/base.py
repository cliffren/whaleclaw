"""Channel abstraction layer — common interface for all message channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MediaAttachment(BaseModel):
    """A media file attached to a message."""

    type: Literal["image", "audio", "video", "file"]
    url: str | None = None
    path: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    size: int | None = None


class ChannelMessage(BaseModel):
    """Channel-agnostic standard message format."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    channel: str
    peer_id: str
    group_id: str | None = None
    content: str
    media: list[MediaAttachment] = Field(default_factory=list)
    reply_to: str | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    raw: dict[str, Any] = Field(default_factory=dict)


class ChannelPlugin(ABC):
    """Abstract base for all channel plugins."""

    name: str = "unknown"

    @abstractmethod
    async def start(self) -> None:
        """Start the channel (connect / register webhooks, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel."""

    @abstractmethod
    async def send(
        self, peer_id: str, content: str, **kwargs: Any
    ) -> None:
        """Send a message to a peer via this channel."""

    async def send_stream(
        self, peer_id: str, stream: AsyncIterator[str]
    ) -> None:
        """Stream a reply to a peer (default: collect then send)."""
        parts: list[str] = []
        async for chunk in stream:
            parts.append(chunk)
        await self.send(peer_id, "".join(parts))

    @abstractmethod
    async def on_message(
        self,
        callback: Callable[[ChannelMessage], Awaitable[None]],
    ) -> None:
        """Register an incoming-message callback."""
