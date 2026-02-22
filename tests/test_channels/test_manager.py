"""Tests for the channel manager."""

from __future__ import annotations

import pytest

from whaleclaw.channels.manager import ChannelManager
from whaleclaw.channels.webchat.handler import WebChatChannel


@pytest.mark.asyncio
async def test_register_and_start() -> None:
    mgr = ChannelManager()
    ch = WebChatChannel()
    mgr.register(ch)
    assert mgr.get("webchat") is ch
    await mgr.start_all()
    await mgr.stop_all()


@pytest.mark.asyncio
async def test_get_nonexistent() -> None:
    mgr = ChannelManager()
    assert mgr.get("feishu") is None
