"""WhaleClaw plugin system."""

from whaleclaw.plugins.hooks import HookContext, HookManager, HookPoint, HookResult
from whaleclaw.plugins.loader import PluginLoader, PluginMeta
from whaleclaw.plugins.registry import PluginRegistry
from whaleclaw.plugins.sdk import WhaleclawPlugin, WhaleclawPluginApi

__all__ = [
    "HookContext",
    "HookManager",
    "HookPoint",
    "HookResult",
    "PluginLoader",
    "PluginMeta",
    "PluginRegistry",
    "WhaleclawPlugin",
    "WhaleclawPluginApi",
]
