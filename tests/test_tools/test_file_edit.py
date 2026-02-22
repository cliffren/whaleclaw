"""Tests for the file edit tool."""

from __future__ import annotations

import pytest

from whaleclaw.tools.file_edit import FileEditTool


@pytest.fixture()
def tool() -> FileEditTool:
    return FileEditTool()


@pytest.mark.asyncio
async def test_replace(tool: FileEditTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    result = await tool.execute(path=str(f), old_string="world", new_string="earth")
    assert result.success
    assert f.read_text() == "hello earth"


@pytest.mark.asyncio
async def test_not_found(tool: FileEditTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "test.txt"
    f.write_text("hello")
    result = await tool.execute(path=str(f), old_string="xyz", new_string="abc")
    assert not result.success
    assert "未找到" in (result.error or "")


@pytest.mark.asyncio
async def test_not_unique(tool: FileEditTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "test.txt"
    f.write_text("aaa bbb aaa")
    result = await tool.execute(path=str(f), old_string="aaa", new_string="ccc")
    assert not result.success
    assert "不唯一" in (result.error or "")


@pytest.mark.asyncio
async def test_nonexistent_file(tool: FileEditTool) -> None:
    result = await tool.execute(
        path="/tmp/nonexistent_whaleclaw_test",
        old_string="a",
        new_string="b",
    )
    assert not result.success
