"""Plugin registry — manages loaded plugins lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from whaleclaw.plugins.loader import PluginMeta

if TYPE_CHECKING:
    from whaleclaw.plugins.sdk import WhaleclawPlugin


class PluginRegistry:
    """Registry for loaded plugins with start/stop lifecycle."""

    def __init__(self) -> None:
        self._plugins: dict[str, tuple[WhaleclawPlugin, PluginMeta]] = {}

    async def register(
        self,
        plugin: WhaleclawPlugin,
        meta: PluginMeta | None = None,
    ) -> None:
        """Register a loaded plugin."""
        meta = meta or PluginMeta(
            id=plugin.id,
            name=plugin.name,
            description="",
            version="0.0.0",
            author="",
            entry="",
            path="",
        )
        self._plugins[plugin.id] = (plugin, meta)

    async def unregister(self, plugin_id: str) -> None:
        """Unregister and stop a plugin."""
        entry = self._plugins.pop(plugin_id, None)
        if entry:
            plugin, _ = entry
            await plugin.on_stop()

    def get(self, plugin_id: str) -> WhaleclawPlugin | None:
        """Get a registered plugin by id."""
        entry = self._plugins.get(plugin_id)
        return entry[0] if entry else None

    def list_plugins(self) -> list[PluginMeta]:
        """List metadata for all registered plugins."""
        return [meta for _, meta in self._plugins.values()]

    async def start_all(self) -> None:
        """Call on_start for all registered plugins."""
        for plugin, _ in self._plugins.values():
            await plugin.on_start()

    async def stop_all(self) -> None:
        """Call on_stop for all registered plugins."""
        for plugin, _ in self._plugins.values():
            await plugin.on_stop()
