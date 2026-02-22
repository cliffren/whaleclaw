"""Tests for the channel abstraction layer."""

from __future__ import annotations

from whaleclaw.channels.base import ChannelMessage, MediaAttachment


class TestChannelMessage:
    def test_defaults(self) -> None:
        msg = ChannelMessage(channel="webchat", peer_id="u1", content="hi")
        assert msg.channel == "webchat"
        assert msg.id
        assert msg.timestamp
        assert msg.media == []

    def test_media_attachment(self) -> None:
        ma = MediaAttachment(type="image", url="https://example.com/img.png")
        msg = ChannelMessage(
            channel="webchat",
            peer_id="u1",
            content="see image",
            media=[ma],
        )
        assert len(msg.media) == 1
        assert msg.media[0].type == "image"
