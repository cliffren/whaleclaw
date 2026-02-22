"""Memory storage abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class MemoryEntry(BaseModel):
    """Single memory entry."""

    id: str
    content: str
    source: str
    tags: list[str] = []
    importance: float = 0.5
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    embedding: list[float] | None = None


class MemorySearchResult(BaseModel):
    """Search result with relevance score."""

    entry: MemoryEntry
    score: float


class MemoryStore(ABC):
    """Abstract memory storage backend."""

    @abstractmethod
    async def add(self, content: str, source: str, tags: list[str] | None = None) -> MemoryEntry:
        """Add a memory entry."""

    @abstractmethod
    async def search(
        self, query: str, limit: int = 5, min_score: float = 0.5
    ) -> list[MemorySearchResult]:
        """Search by query, return sorted by score."""

    @abstractmethod
    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Get entry by id."""

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete entry, return True if existed."""

    @abstractmethod
    async def list_recent(self, limit: int = 20) -> list[MemoryEntry]:
        """List most recent entries."""
