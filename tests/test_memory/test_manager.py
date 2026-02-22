"""Tests for MemoryManager."""

from __future__ import annotations

import pytest

from whaleclaw.memory.manager import MemoryManager
from whaleclaw.memory.vector import SimpleMemoryStore


@pytest.fixture
def store() -> SimpleMemoryStore:
    return SimpleMemoryStore()


@pytest.fixture
def manager(store: SimpleMemoryStore) -> MemoryManager:
    return MemoryManager(store)


@pytest.mark.asyncio
async def test_recall(manager: MemoryManager) -> None:
    await manager.memorize("用户喜欢 Rust 编程语言", source="session-1")
    result = await manager.recall("Rust 喜欢", max_tokens=500)
    assert "Rust" in result


@pytest.mark.asyncio
async def test_memorize(manager: MemoryManager) -> None:
    entry = await manager.memorize("重要信息：会议在明天", source="manual", tags=["meeting"])
    assert entry.id
    assert entry.content == "重要信息：会议在明天"
    assert "meeting" in entry.tags


@pytest.mark.asyncio
async def test_compact(manager: MemoryManager, store: SimpleMemoryStore) -> None:
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好"},
        {"role": "user", "content": "我最喜欢的语言是 Python"},
    ]
    summary = await manager.compact(messages, source="session-x")
    assert isinstance(summary, str)
    assert len(summary) > 0
    recent = await store.list_recent(limit=10)
    assert len(recent) >= 1
