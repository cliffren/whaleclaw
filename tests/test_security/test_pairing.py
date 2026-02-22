"""Tests for whaleclaw.security.pairing."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from whaleclaw.security.pairing import PairingService


@pytest.mark.asyncio
async def test_generate_and_verify() -> None:
    svc = PairingService(ttl_minutes=5)
    code = await svc.generate_code("feishu", "user_123")
    assert len(code) == 6
    assert code.isdigit()
    req = await svc.verify(code)
    assert req is not None
    assert req.status == "pending"
    assert req.channel == "feishu"
    assert req.peer_id == "user_123"


@pytest.mark.asyncio
async def test_approve() -> None:
    svc = PairingService(ttl_minutes=5)
    code = await svc.generate_code("feishu", "user_456")
    ok = await svc.approve(code)
    assert ok is True
    req = await svc.verify(code)
    assert req is not None
    assert req.status == "approved"


@pytest.mark.asyncio
async def test_expired_code() -> None:
    svc = PairingService(ttl_minutes=5)
    code = await svc.generate_code("feishu", "user_789")
    req = svc._pending[code]
    req.expires_at = datetime.now() - timedelta(minutes=1)
    result = await svc.verify(code)
    assert result is None
