"""Message channels (WebChat, Feishu, etc.)."""

from whaleclaw.channels.base import ChannelMessage, ChannelPlugin, MediaAttachment
from whaleclaw.channels.manager import ChannelManager

__all__ = [
    "ChannelManager",
    "ChannelMessage",
    "ChannelPlugin",
    "MediaAttachment",
]
