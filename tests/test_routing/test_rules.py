"""Tests for routing rules."""

from __future__ import annotations

from whaleclaw.channels.base import ChannelMessage
from whaleclaw.routing.rules import RoutingMatch


def test_routing_match_channel() -> None:
    match = RoutingMatch(channel="webchat")
    msg = ChannelMessage(channel="webchat", peer_id="user1", content="hello")
    assert match.matches(msg) is True
    msg_feishu = ChannelMessage(channel="feishu", peer_id="user1", content="hello")
    assert match.matches(msg_feishu) is False


def test_routing_match_wildcard_group() -> None:
    match = RoutingMatch(channel="feishu", group_id="*")
    msg = ChannelMessage(
        channel="feishu",
        peer_id="u1",
        group_id="g123",
        content="hi",
    )
    assert match.matches(msg) is True
    msg_dm = ChannelMessage(channel="feishu", peer_id="u1", content="hi")
    assert match.matches(msg_dm) is False


def test_routing_match_peer_list() -> None:
    match = RoutingMatch(channel="webchat", peer_id=["alice", "bob"])
    msg_alice = ChannelMessage(channel="webchat", peer_id="alice", content="x")
    assert match.matches(msg_alice) is True
    msg_bob = ChannelMessage(channel="webchat", peer_id="bob", content="y")
    assert match.matches(msg_bob) is True
    msg_carol = ChannelMessage(channel="webchat", peer_id="carol", content="z")
    assert match.matches(msg_carol) is False


def test_routing_match_pattern() -> None:
    match = RoutingMatch(channel="webchat", pattern=r"^/cmd\s")
    msg_match = ChannelMessage(channel="webchat", peer_id="u", content="/cmd run")
    assert match.matches(msg_match) is True
    msg_nomatch = ChannelMessage(channel="webchat", peer_id="u", content="hello")
    assert match.matches(msg_nomatch) is False


def test_no_match() -> None:
    match = RoutingMatch(channel="webchat", peer_id="alice")
    msg = ChannelMessage(channel="feishu", peer_id="bob", content="hi")
    assert match.matches(msg) is False
