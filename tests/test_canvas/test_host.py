"""Tests for CanvasHost."""

from __future__ import annotations

import pytest

from whaleclaw.canvas.host import CanvasHost


@pytest.fixture()
def host() -> CanvasHost:
    return CanvasHost()


def test_push_and_get(host: CanvasHost) -> None:
    """Push html, get returns it."""
    host.push("s1", html="<div>hello</div>")
    state = host.get("s1")
    assert state is not None
    assert state.html == "<div>hello</div>"
    assert state.session_id == "s1"


def test_reset(host: CanvasHost) -> None:
    """Push then reset, get returns None."""
    host.push("s1", html="<p>x</p>")
    host.reset("s1")
    assert host.get("s1") is None


def test_list_sessions(host: CanvasHost) -> None:
    """Push to 2 sessions, list returns both."""
    host.push("a", html="a")
    host.push("b", html="b")
    sessions = host.list_sessions()
    assert set(sessions) == {"a", "b"}
