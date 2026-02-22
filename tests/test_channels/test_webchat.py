"""Tests for the WebChat channel."""

from __future__ import annotations

import pytest

from whaleclaw.channels.webchat.handler import WebChatChannel


@pytest.mark.asyncio
async def test_webchat_lifecycle() -> None:
    ch = WebChatChannel()
    assert ch.name == "webchat"
    await ch.start()
    await ch.send("user1", "hello")
    await ch.stop()


@pytest.mark.asyncio
async def test_webchat_on_message_callback() -> None:
    ch = WebChatChannel()
    called = False

    async def cb(msg):  # noqa: ANN001, ANN202
        nonlocal called
        called = True

    await ch.on_message(cb)
    assert ch._callback is not None
