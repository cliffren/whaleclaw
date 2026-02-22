"""Tests for launchd service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from whaleclaw.daemon.launchd import PLIST_LABEL, LaunchdService


def test_plist_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify install writes correct plist to PLIST_PATH."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr("whaleclaw.daemon.launchd.LOGS_DIR", log_dir)
    svc = LaunchdService(plist_path=tmp_path / "ai.whaleclaw.gateway.plist")

    with patch("subprocess.run"):
        svc.install(
            python_path="/usr/bin/python3.12",
            port=18790,
            bind="127.0.0.1",
        )

    plist = tmp_path / "ai.whaleclaw.gateway.plist"
    assert plist.exists()
    content = plist.read_text(encoding="utf-8")
    assert PLIST_LABEL in content
    assert "/usr/bin/python3.12" in content
    assert "-m" in content
    assert "whaleclaw" in content
    assert "gateway" in content
    assert "run" in content
    assert "18790" in content
    assert "127.0.0.1" in content
    assert "RunAtLoad" in content
    assert "KeepAlive" in content


def test_is_installed_when_exists(tmp_path: Path) -> None:
    """is_installed returns True when plist exists."""
    plist = tmp_path / "test.plist"
    plist.write_text("")
    svc = LaunchdService(plist_path=plist)
    assert svc.is_installed() is True


def test_is_installed_when_not_exists(tmp_path: Path) -> None:
    """is_installed returns False when plist does not exist."""
    plist = tmp_path / "nonexistent.plist"
    svc = LaunchdService(plist_path=plist)
    assert svc.is_installed() is False


def test_status_installed(tmp_path: Path) -> None:
    """status returns 'installed' when plist exists."""
    plist = tmp_path / "test.plist"
    plist.write_text("")
    svc = LaunchdService(plist_path=plist)
    assert svc.status() == "installed"


def test_status_not_installed(tmp_path: Path) -> None:
    """status returns 'not_installed' when plist does not exist."""
    plist = tmp_path / "nonexistent.plist"
    svc = LaunchdService(plist_path=plist)
    assert svc.status() == "not_installed"
