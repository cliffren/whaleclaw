"""WebChat channel plugin — connects browser clients to the Agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from whaleclaw.channels.base import ChannelMessage, ChannelPlugin
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class WebChatChannel(ChannelPlugin):
    """WebChat channel — served via Gateway WebSocket."""

    name = "webchat"

    def __init__(self) -> None:
        self._callback: Callable[
            [ChannelMessage], Awaitable[None]
        ] | None = None

    async def start(self) -> None:
        log.info("webchat.started")

    async def stop(self) -> None:
        log.info("webchat.stopped")

    async def send(
        self, peer_id: str, content: str, **kwargs: Any
    ) -> None:
        log.debug("webchat.send", peer_id=peer_id, length=len(content))

    async def on_message(
        self,
        callback: Callable[[ChannelMessage], Awaitable[None]],
    ) -> None:
        self._callback = callback
