"""Tests for the file read tool."""

from __future__ import annotations

import pytest

from whaleclaw.tools.file_read import FileReadTool


@pytest.fixture()
def tool() -> FileReadTool:
    return FileReadTool()


@pytest.mark.asyncio
async def test_read_file(tool: FileReadTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n")
    result = await tool.execute(path=str(f))
    assert result.success
    assert "line1" in result.output
    assert "line3" in result.output


@pytest.mark.asyncio
async def test_read_with_offset(tool: FileReadTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "test.txt"
    f.write_text("a\nb\nc\nd\n")
    result = await tool.execute(path=str(f), offset=2, limit=2)
    assert result.success
    assert "b" in result.output
    assert "c" in result.output


@pytest.mark.asyncio
async def test_nonexistent(tool: FileReadTool) -> None:
    result = await tool.execute(path="/tmp/nonexistent_whaleclaw_test")
    assert not result.success


@pytest.mark.asyncio
async def test_empty_path(tool: FileReadTool) -> None:
    result = await tool.execute(path="")
    assert not result.success
