"""Tests for PluginRegistry."""

from __future__ import annotations

import pytest

from whaleclaw.plugins.loader import PluginMeta
from whaleclaw.plugins.registry import PluginRegistry
from whaleclaw.plugins.sdk import WhaleclawPlugin, WhaleclawPluginApi


class MockPlugin(WhaleclawPlugin):
    def __init__(self, plugin_id: str = "mock", plugin_name: str = "Mock") -> None:
        self._id = plugin_id
        self._name = plugin_name
        self._started = False
        self._stopped = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def register(self, api: WhaleclawPluginApi) -> None:
        pass

    async def on_start(self) -> None:
        self._started = True

    async def on_stop(self) -> None:
        self._stopped = True


@pytest.mark.asyncio
async def test_register_get_list() -> None:
    reg = PluginRegistry()
    plugin = MockPlugin("my-plugin", "My Plugin")
    meta = PluginMeta(id="my-plugin", name="My Plugin", description="x", entry="x")

    await reg.register(plugin, meta)
    assert reg.get("my-plugin") is plugin
    assert reg.list_plugins() == [meta]


@pytest.mark.asyncio
async def test_start_all_stop_all() -> None:
    reg = PluginRegistry()
    p1 = MockPlugin("p1", "P1")
    p2 = MockPlugin("p2", "P2")
    await reg.register(p1, PluginMeta(id="p1", name="P1", entry=""))
    await reg.register(p2, PluginMeta(id="p2", name="P2", entry=""))

    await reg.start_all()
    assert p1._started
    assert p2._started

    await reg.stop_all()
    assert p1._stopped
    assert p2._stopped


@pytest.mark.asyncio
async def test_unregister_calls_on_stop() -> None:
    reg = PluginRegistry()
    p = MockPlugin("x", "X")
    await reg.register(p, PluginMeta(id="x", name="X", entry=""))
    await reg.unregister("x")
    assert p._stopped
    assert reg.get("x") is None
