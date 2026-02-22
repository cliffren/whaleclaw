"""Channel manager — lifecycle and routing for all channels."""

from __future__ import annotations

from whaleclaw.channels.base import ChannelPlugin
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class ChannelManager:
    """Manage all registered channel plugins."""

    def __init__(self) -> None:
        self._channels: dict[str, ChannelPlugin] = {}

    def register(self, channel: ChannelPlugin) -> None:
        self._channels[channel.name] = channel
        log.info("channel.registered", channel=channel.name)

    def get(self, name: str) -> ChannelPlugin | None:
        return self._channels.get(name)

    async def start_all(self) -> None:
        for ch in self._channels.values():
            await ch.start()
            log.info("channel.started", channel=ch.name)

    async def stop_all(self) -> None:
        for ch in self._channels.values():
            await ch.stop()
            log.info("channel.stopped", channel=ch.name)

    async def broadcast(self, content: str) -> None:
        """Send a message to all channels (best-effort)."""
        for ch in self._channels.values():
            try:
                await ch.send("broadcast", content)
            except Exception as exc:
                log.warning(
                    "channel.broadcast_failed",
                    channel=ch.name,
                    error=str(exc),
                )
