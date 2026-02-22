"""Plugin SDK — WhaleclawPluginApi and WhaleclawPlugin base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from whaleclaw.channels.base import ChannelPlugin
from whaleclaw.plugins.hooks import HookCallback, HookPoint
from whaleclaw.tools.base import Tool

if TYPE_CHECKING:
    from whaleclaw.sessions.manager import Session


class CommandHandler(Protocol):
    """Protocol for plugin-registered chat command handlers."""

    async def __call__(self, text: str, session: Session) -> str | None:
        """Handle command. Return response string or None if not handled."""
        ...


class WhaleclawPluginApi:
    """API for plugins to interact with WhaleClaw core."""

    def __init__(
        self,
        plugin_id: str,
        get_config_fn: Callable[[str, str, Any], Any],
        get_secret_fn: Callable[[str, str], str | None],
        channel_register_fn: Callable[[ChannelPlugin], None],
        tool_register_fn: Callable[[Tool], None],
        hook_register_fn: Callable[[HookPoint, HookCallback, int], None],
        command_register_fn: Callable[[str, CommandHandler], None],
    ) -> None:
        self._plugin_id = plugin_id
        self._get_config = get_config_fn
        self._get_secret = get_secret_fn
        self._register_channel = channel_register_fn
        self._register_tool = tool_register_fn
        self._register_hook = hook_register_fn
        self._register_command = command_register_fn

    def register_channel(self, channel: ChannelPlugin) -> None:
        """Register a message channel."""
        self._register_channel(channel)

    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        self._register_tool(tool)

    def register_hook(
        self,
        hook: HookPoint,
        callback: HookCallback,
        priority: int = 0,
    ) -> None:
        """Register a hook callback."""
        self._register_hook(hook, callback, priority)

    def register_command(self, command: str, handler: CommandHandler) -> None:
        """Register a chat command handler."""
        self._register_command(command, handler)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Read plugin configuration value."""
        return self._get_config(self._plugin_id, key, default)

    def get_secret(self, key: str) -> str | None:
        """Read plugin secret/credential."""
        return self._get_secret(self._plugin_id, key)


class WhaleclawPlugin(ABC):
    """Base class for WhaleClaw plugins."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name."""
        ...

    @abstractmethod
    def register(self, api: WhaleclawPluginApi) -> None:
        """Register channels, tools, hooks, and commands via the API."""
        ...

    async def on_start(self) -> None:
        """Called when the plugin is started."""
        return

    async def on_stop(self) -> None:
        """Called when the plugin is stopped."""
        return
