"""Tests for SimpleMemoryStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from whaleclaw.memory.vector import SimpleMemoryStore


@pytest.mark.asyncio
async def test_add_and_search() -> None:
    store = SimpleMemoryStore()
    entry = await store.add("用户最喜欢的编程语言是 Rust", source="session-1", tags=[])
    assert entry.id
    assert "Rust" in entry.content
    results = await store.search("Rust 编程", limit=5, min_score=0.5)
    assert len(results) == 1
    assert results[0].entry.content == entry.content
    assert results[0].score > 0


@pytest.mark.asyncio
async def test_search_no_match() -> None:
    store = SimpleMemoryStore()
    await store.add("今天天气很好", source="session-1")
    results = await store.search("xyz unknown", limit=5, min_score=0.5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete() -> None:
    store = SimpleMemoryStore()
    entry = await store.add("要删除的记忆", source="s1")
    got = await store.get(entry.id)
    assert got is not None
    deleted = await store.delete(entry.id)
    assert deleted is True
    got2 = await store.get(entry.id)
    assert got2 is None
    deleted2 = await store.delete("non-existent")
    assert deleted2 is False


@pytest.mark.asyncio
async def test_list_recent() -> None:
    store = SimpleMemoryStore()
    await store.add("第一条", source="s1")
    await store.add("第二条", source="s1")
    await store.add("第三条", source="s1")
    recent = await store.list_recent(limit=2)
    assert len(recent) == 2
    contents = [e.content for e in recent]
    assert "第三条" in contents
    assert "第二条" in contents
    assert "第一条" not in contents


@pytest.mark.asyncio
async def test_persistence(tmp_path: Path) -> None:
    path = tmp_path / "mem"
    store1 = SimpleMemoryStore(persist_dir=path)
    await store1.add("持久化测试内容", source="test")
    store2 = SimpleMemoryStore(persist_dir=path)
    recent = await store2.list_recent(limit=10)
    assert len(recent) == 1
    assert recent[0].content == "持久化测试内容"
