"""Tests for TailscaleManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from whaleclaw.remote.tailscale import TailscaleManager


@pytest.fixture()
def manager() -> TailscaleManager:
    return TailscaleManager()


@pytest.mark.asyncio
async def test_status_not_installed(manager: TailscaleManager) -> None:
    """Mock subprocess to raise FileNotFoundError, verify returns error message."""
    with patch(
        "asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        side_effect=FileNotFoundError("tailscale: command not found"),
    ):
        result = await manager.status()
    assert result == "Tailscale 未安装"
