"""Tests for the file write tool."""

from __future__ import annotations

import pytest

from whaleclaw.tools.file_write import FileWriteTool


@pytest.fixture()
def tool() -> FileWriteTool:
    return FileWriteTool()


@pytest.mark.asyncio
async def test_write_file(tool: FileWriteTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "out.txt"
    result = await tool.execute(path=str(f), content="hello world")
    assert result.success
    assert f.read_text() == "hello world"


@pytest.mark.asyncio
async def test_write_creates_dirs(tool: FileWriteTool, tmp_path) -> None:  # noqa: ANN001
    f = tmp_path / "sub" / "dir" / "out.txt"
    result = await tool.execute(path=str(f), content="nested")
    assert result.success
    assert f.read_text() == "nested"


@pytest.mark.asyncio
async def test_empty_path(tool: FileWriteTool) -> None:
    result = await tool.execute(path="", content="x")
    assert not result.success
