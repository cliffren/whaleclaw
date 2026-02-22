"""Shared test fixtures for WhaleClaw."""

from __future__ import annotations

import pytest

from whaleclaw.config.loader import reset_config
from whaleclaw.config.schema import AgentConfig, GatewayConfig, WhaleclawConfig


@pytest.fixture()
def default_config() -> WhaleclawConfig:
    """Return a default WhaleclawConfig for testing."""
    return WhaleclawConfig()


@pytest.fixture()
def custom_config() -> WhaleclawConfig:
    """Return a customised config for testing."""
    return WhaleclawConfig(
        gateway=GatewayConfig(port=19000, bind="0.0.0.0", verbose=True),
        agent=AgentConfig(model="anthropic/claude-sonnet-4-20250514"),
    )


@pytest.fixture(autouse=True)
def _reset_global_config() -> None:
    """Ensure global config is reset between tests."""
    reset_config()
