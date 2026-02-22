"""Configuration management for WhaleClaw."""

from whaleclaw.config.loader import get_config, load_config
from whaleclaw.config.paths import ensure_dirs
from whaleclaw.config.schema import AgentConfig, GatewayConfig, WhaleclawConfig

__all__ = [
    "AgentConfig",
    "GatewayConfig",
    "WhaleclawConfig",
    "ensure_dirs",
    "get_config",
    "load_config",
]
