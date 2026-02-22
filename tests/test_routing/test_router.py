"""Tests for message router."""

from __future__ import annotations

import pytest

from whaleclaw.channels.base import ChannelMessage
from whaleclaw.routing.router import MessageRouter
from whaleclaw.routing.rules import RoutingMatch, RoutingRule, RoutingTarget


@pytest.mark.asyncio
async def test_route_matches_first_rule() -> None:
    rules = [
        RoutingRule(
            name="feishu-sandbox",
            priority=10,
            match=RoutingMatch(channel="feishu", group_id="*"),
            target=RoutingTarget(agent_id="sandbox", sandbox=True),
        ),
        RoutingRule(
            name="webchat-main",
            priority=5,
            match=RoutingMatch(channel="webchat"),
            target=RoutingTarget(agent_id="main"),
        ),
    ]
    router = MessageRouter(rules=rules)
    msg = ChannelMessage(
        channel="feishu",
        peer_id="u1",
        group_id="g1",
        content="hello",
    )
    result = await router.route(msg)
    assert result.agent_id == "sandbox"
    assert result.security_policy.sandbox is True


@pytest.mark.asyncio
async def test_route_default_target() -> None:
    rules = [
        RoutingRule(
            name="webchat-only",
            match=RoutingMatch(channel="webchat"),
            target=RoutingTarget(agent_id="main"),
        ),
    ]
    default = RoutingTarget(agent_id="default", workspace="/tmp/ws")
    router = MessageRouter(rules=rules, default_target=default)
    msg = ChannelMessage(channel="feishu", peer_id="u1", content="hi")
    result = await router.route(msg)
    assert result.agent_id == "default"
    assert result.workspace == "/tmp/ws"


@pytest.mark.asyncio
async def test_route_session_id_format() -> None:
    router = MessageRouter(rules=[])
    msg_dm = ChannelMessage(channel="webchat", peer_id="user1", content="hello")
    result_dm = await router.route(msg_dm)
    assert result_dm.session_id == "webchat:user1"

    msg_group = ChannelMessage(
        channel="feishu",
        peer_id="u1",
        group_id="g123",
        content="hi",
    )
    result_group = await router.route(msg_group)
    assert result_group.session_id == "feishu:g123:u1"
