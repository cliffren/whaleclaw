"""Abstract base class for Agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """Describes a single tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Full tool definition (name + description + parameters)."""

    name: str
    description: str
    parameters: list[ToolParameter]


class ToolResult(BaseModel):
    """Result returned by a tool execution."""

    success: bool
    output: str
    error: str | None = None


class Tool(ABC):
    """Abstract base for all tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's definition."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""
