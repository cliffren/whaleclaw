"""Tests for whaleclaw.security.audit."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from whaleclaw.security.audit import AuditEvent, AuditLogger


@pytest.mark.asyncio
async def test_log_and_query(tmp_path: object) -> None:
    path = tmp_path / "audit.db"
    logger = AuditLogger(path)
    await logger.open()
    try:
        await logger.log(
            AuditEvent(event_type="login", session_id="s1", channel="feishu", peer_id="u1"),
        )
        await logger.log(
            AuditEvent(event_type="login", session_id="s2", channel="webchat", peer_id="u2"),
        )
        await logger.log(
            AuditEvent(event_type="tool_call", session_id="s1", details={"tool": "bash"}),
        )
        events = await logger.query(event_type="login")
        assert len(events) == 2
        events_all = await logger.query(limit=10)
        assert len(events_all) == 3
    finally:
        await logger.close()


@pytest.mark.asyncio
async def test_query_since(tmp_path: object) -> None:
    path = tmp_path / "audit2.db"
    logger = AuditLogger(path)
    await logger.open()
    try:
        base = datetime(2026, 2, 22, 10, 0, 0)
        await logger.log(
            AuditEvent(
                event_type="test",
                timestamp=base,
                session_id="s1",
            ),
        )
        await logger.log(
            AuditEvent(
                event_type="test",
                timestamp=base + timedelta(minutes=5),
                session_id="s2",
            ),
        )
        await logger.log(
            AuditEvent(
                event_type="test",
                timestamp=base + timedelta(minutes=10),
                session_id="s3",
            ),
        )
        since = base + timedelta(minutes=3)
        events = await logger.query(since=since, limit=10)
        assert len(events) == 2
    finally:
        await logger.close()
