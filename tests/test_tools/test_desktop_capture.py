"""Tests for desktop capture tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from whaleclaw.tools.desktop_capture import DesktopCaptureTool


@pytest.mark.asyncio
async def test_desktop_capture_non_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = DesktopCaptureTool()
    monkeypatch.setattr("whaleclaw.tools.desktop_capture.sys.platform", "linux")
    result = await tool.execute()
    assert result.success is False
    assert "仅支持 macOS" in (result.error or "")


@pytest.mark.asyncio
async def test_desktop_capture_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = DesktopCaptureTool()
    monkeypatch.setattr("whaleclaw.tools.desktop_capture.sys.platform", "darwin")
    monkeypatch.setattr("whaleclaw.tools.desktop_capture._SCREENSHOT_DIR", tmp_path)

    async def fake_run(*args: str, timeout: float = 8.0) -> tuple[int, str, str]:  # noqa: ARG001
        if "/usr/sbin/screencapture" in args:
            out = Path(args[-1])
            out.write_bytes(b"png")
        return 0, "", ""

    monkeypatch.setattr(tool, "_run", fake_run)
    result = await tool.execute(filename="desk_test.png", wake=True, delay_ms=0)
    assert result.success is True
    assert "桌面截图已保存" in result.output
    assert (tmp_path / "desk_test.png").is_file()

