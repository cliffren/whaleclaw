"""Routing rules — match conditions and targets."""

from __future__ import annotations

import re

from pydantic import BaseModel

from whaleclaw.channels.base import ChannelMessage


def _match_id(
    msg_val: str | None,
    rule_val: str | list[str] | None,
) -> bool:
    if rule_val is None:
        return True
    if msg_val is None:
        return False
    if rule_val == "*":
        return True
    if isinstance(rule_val, str):
        return msg_val == rule_val
    return msg_val in rule_val


class RoutingMatch(BaseModel):
    """Match conditions for routing rules."""

    channel: str | None = None
    peer_id: str | list[str] | None = None
    group_id: str | list[str] | None = None
    pattern: str | None = None

    def matches(self, msg: ChannelMessage) -> bool:
        if self.channel is not None and msg.channel != self.channel:
            return False
        if not _match_id(msg.peer_id, self.peer_id):
            return False
        if not _match_id(msg.group_id, self.group_id):
            return False
        return self.pattern is None or re.search(self.pattern, msg.content) is not None


class RoutingTarget(BaseModel):
    """Routing target — agent and workspace config."""

    agent_id: str = "default"
    workspace: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    sandbox: bool = False


class RoutingRule(BaseModel):
    """Single routing rule with match and target."""

    name: str
    priority: int = 0
    match: RoutingMatch
    target: RoutingTarget
