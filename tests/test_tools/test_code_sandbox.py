"""Tests for CodeSandboxTool."""

from __future__ import annotations

import pytest

from whaleclaw.tools.code_sandbox import CodeSandboxTool


@pytest.mark.asyncio
async def test_execute_print_hello() -> None:
    tool = CodeSandboxTool()
    result = await tool.execute(
        language="python",
        code='print("hello")',
    )
    assert result.success
    assert "hello" in result.output
