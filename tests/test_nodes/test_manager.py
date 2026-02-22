"""Tests for NodeManager."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from whaleclaw.nodes.manager import DeviceNode, NodeManager


def _make_node(node_id: str = "node-1") -> DeviceNode:
    now = datetime.now(UTC)
    return DeviceNode(
        id=node_id,
        name="Test",
        platform="darwin",
        connected_at=now,
        last_heartbeat=now,
    )


@pytest.fixture()
def manager() -> NodeManager:
    return NodeManager()


@pytest.mark.asyncio
async def test_register_and_list(manager: NodeManager) -> None:
    """Register node, list returns it."""
    node = _make_node()
    await manager.register(node)
    nodes = await manager.list_nodes()
    assert len(nodes) == 1
    assert nodes[0].id == "node-1"
    assert nodes[0].name == "Test"


@pytest.mark.asyncio
async def test_unregister(manager: NodeManager) -> None:
    """Register then unregister, list empty."""
    node = _make_node()
    await manager.register(node)
    await manager.unregister("node-1")
    nodes = await manager.list_nodes()
    assert len(nodes) == 0


@pytest.mark.asyncio
async def test_heartbeat(manager: NodeManager) -> None:
    """Register, heartbeat updates time."""
    t0 = datetime.now(UTC)
    node = _make_node()
    node.last_heartbeat = t0
    await manager.register(node)
    ok = await manager.heartbeat("node-1")
    assert ok
    n = (await manager.list_nodes())[0]
    assert n.last_heartbeat >= t0


@pytest.mark.asyncio
async def test_invoke_stub(manager: NodeManager) -> None:
    """Invoke returns not_implemented."""
    node = _make_node()
    await manager.register(node)
    result = await manager.invoke("node-1", "camera.snap", {})
    assert result["status"] == "not_implemented"
    assert "节点调用尚未实现" in result["error"]
