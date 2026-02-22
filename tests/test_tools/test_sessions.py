"""Tests for session management tools."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from whaleclaw.providers.base import Message
from whaleclaw.sessions.manager import Session, SessionManager
from whaleclaw.tools.sessions import (
    SessionsHistoryTool,
    SessionsListTool,
    SessionsSendTool,
)


@pytest.fixture()
def mock_manager() -> AsyncMock:
    return AsyncMock(spec=SessionManager)


@pytest.fixture()
def sessions_list_tool(mock_manager: AsyncMock) -> SessionsListTool:
    return SessionsListTool(session_manager=mock_manager)  # type: ignore[arg-type]


@pytest.fixture()
def sessions_history_tool(mock_manager: AsyncMock) -> SessionsHistoryTool:
    return SessionsHistoryTool(session_manager=mock_manager)  # type: ignore[arg-type]


@pytest.fixture()
def sessions_send_tool(mock_manager: AsyncMock) -> SessionsSendTool:
    return SessionsSendTool(session_manager=mock_manager)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_sessions_list(sessions_list_tool: SessionsListTool, mock_manager: AsyncMock) -> None:
    now = datetime.now(UTC)
    mock_manager.list_sessions.return_value = [
        Session(
            id="s1",
            channel="webchat",
            peer_id="p1",
            model="claude",
            created_at=now,
            updated_at=now,
        ),
        Session(
            id="s2",
            channel="feishu",
            peer_id="p2",
            model="gpt",
            created_at=now,
            updated_at=now,
        ),
    ]
    result = await sessions_list_tool.execute()
    assert result.success
    assert "s1" in result.output
    assert "webchat" in result.output
    assert "s2" in result.output
    assert "feishu" in result.output
    mock_manager.list_sessions.assert_called_once()


@pytest.mark.asyncio
async def test_sessions_list_empty(
    sessions_list_tool: SessionsListTool, mock_manager: AsyncMock
) -> None:
    mock_manager.list_sessions.return_value = []
    result = await sessions_list_tool.execute()
    assert result.success
    assert "无活跃会话" in result.output


@pytest.mark.asyncio
async def test_sessions_history_not_found(
    sessions_history_tool: SessionsHistoryTool, mock_manager: AsyncMock
) -> None:
    mock_manager.get.return_value = None
    result = await sessions_history_tool.execute(session_id="nonexistent")
    assert not result.success
    assert "会话未找到" in (result.error or "")


@pytest.mark.asyncio
async def test_sessions_history(
    sessions_history_tool: SessionsHistoryTool, mock_manager: AsyncMock
) -> None:
    now = datetime.now(UTC)
    mock_manager.get.return_value = Session(
        id="s1",
        channel="webchat",
        peer_id="p1",
        messages=[
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi"),
        ],
        model="claude",
        created_at=now,
        updated_at=now,
    )
    result = await sessions_history_tool.execute(session_id="s1", limit=20)
    assert result.success
    assert "[user]: hello" in result.output
    assert "[assistant]: hi" in result.output


@pytest.mark.asyncio
async def test_sessions_send(sessions_send_tool: SessionsSendTool, mock_manager: AsyncMock) -> None:
    now = datetime.now(UTC)
    sess = Session(
        id="s1",
        channel="webchat",
        peer_id="p1",
        model="claude",
        created_at=now,
        updated_at=now,
    )
    mock_manager.get.return_value = sess
    result = await sessions_send_tool.execute(session_id="s1", message="reply")
    assert result.success
    assert "消息已发送" in result.output
    mock_manager.add_message.assert_called_once_with(sess, "assistant", "reply")


@pytest.mark.asyncio
async def test_sessions_send_not_found(
    sessions_send_tool: SessionsSendTool, mock_manager: AsyncMock
) -> None:
    mock_manager.get.return_value = None
    result = await sessions_send_tool.execute(session_id="bad", message="hi")
    assert not result.success
    assert "会话未找到" in (result.error or "")
    mock_manager.add_message.assert_not_called()
