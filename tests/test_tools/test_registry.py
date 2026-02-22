"""Tests for the tool registry."""

from __future__ import annotations

from whaleclaw.tools.bash import BashTool
from whaleclaw.tools.file_read import FileReadTool
from whaleclaw.tools.registry import ToolRegistry


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        reg = ToolRegistry()
        reg.register(BashTool())
        assert reg.get("bash") is not None
        assert reg.get("nonexistent") is None

    def test_list_tools(self) -> None:
        reg = ToolRegistry()
        reg.register(BashTool())
        reg.register(FileReadTool())
        defs = reg.list_tools()
        assert len(defs) == 2
        names = {d.name for d in defs}
        assert "bash" in names
        assert "file_read" in names

    def test_to_llm_schemas(self) -> None:
        reg = ToolRegistry()
        reg.register(BashTool())
        schemas = reg.to_llm_schemas()
        assert len(schemas) == 1
        assert schemas[0].name == "bash"
        assert "properties" in schemas[0].input_schema

    def test_to_prompt_fallback(self) -> None:
        reg = ToolRegistry()
        reg.register(BashTool())
        text = reg.to_prompt_fallback()
        assert "bash" in text
        assert "command" in text

    def test_empty_fallback(self) -> None:
        reg = ToolRegistry()
        assert reg.to_prompt_fallback() == ""
