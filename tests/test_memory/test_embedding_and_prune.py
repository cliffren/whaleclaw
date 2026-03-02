"""Tests for embedding and smart-prune features (opt-in toggles)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from whaleclaw.memory.base import MemoryEntry
from whaleclaw.memory.manager import MemoryManager, _recency_score
from whaleclaw.memory.vector import SimpleMemoryStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HAS_FASTEMBED = True
try:
    import fastembed  # noqa: F401
except ImportError:
    _HAS_FASTEMBED = False

needs_fastembed = pytest.mark.skipif(
    not _HAS_FASTEMBED,
    reason="fastembed not installed – run: pip install fastembed",
)


# ---------------------------------------------------------------------------
# SimpleMemoryStore – use_embedding=False (legacy, regression guard)
# ---------------------------------------------------------------------------


class TestLegacyMode:
    """Ensure that use_embedding=False gives identical behaviour to before."""

    @pytest.mark.asyncio
    async def test_add_no_embedding(self) -> None:
        store = SimpleMemoryStore(use_embedding=False)
        entry = await store.add("测试内容", source="s1")
        assert entry.embedding is None

    @pytest.mark.asyncio
    async def test_search_keyword_only(self) -> None:
        store = SimpleMemoryStore(use_embedding=False)
        await store.add("用户喜欢 Rust 编程语言", source="s1")
        results = await store.search("Rust 编程", limit=5, min_score=0.5)
        assert len(results) == 1
        assert "Rust" in results[0].entry.content

    @pytest.mark.asyncio
    async def test_search_no_semantic_match(self) -> None:
        """Without embedding, semantically-related but keyword-different queries miss."""
        store = SimpleMemoryStore(use_embedding=False)
        await store.add("用户对海鲜过敏", source="s1")
        results = await store.search("贝类能吃吗", limit=5, min_score=0.3)
        # Pure keyword: "贝类" ∩ "海鲜" = ∅ → no results
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_importance_stored(self) -> None:
        store = SimpleMemoryStore(use_embedding=False)
        entry = await store.add("test", source="s1", importance=0.9)
        assert entry.importance == 0.9


# ---------------------------------------------------------------------------
# SimpleMemoryStore – use_embedding=True
# ---------------------------------------------------------------------------


@needs_fastembed
class TestEmbeddingMode:
    """Tests that require fastembed to be installed."""

    @pytest.mark.asyncio
    async def test_add_computes_embedding(self) -> None:
        store = SimpleMemoryStore(use_embedding=True)
        entry = await store.add("测试内容", source="s1")
        assert entry.embedding is not None
        assert len(entry.embedding) > 0

    @pytest.mark.asyncio
    async def test_semantic_search(self) -> None:
        """Embedding search should recall semantically related content."""
        store = SimpleMemoryStore(use_embedding=True)
        await store.add("用户对海鲜过敏，不能吃虾和螃蟹", source="s1")
        await store.add("用户喜欢用 Python 写代码", source="s1")
        results = await store.search("晚餐可以吃贝类吗", limit=5, min_score=0.3)
        assert len(results) >= 1
        assert "海鲜" in results[0].entry.content

    @pytest.mark.asyncio
    async def test_hybrid_keyword_boost(self) -> None:
        """Exact keyword match should boost ranking in hybrid mode."""
        store = SimpleMemoryStore(use_embedding=True)
        await store.add("公司名叫深蓝星辰", source="s1")
        await store.add("深蓝色是用户最喜欢的颜色", source="s1")
        results = await store.search("深蓝星辰", limit=5, min_score=0.3)
        assert len(results) >= 1
        assert results[0].entry.content == "公司名叫深蓝星辰"

    @pytest.mark.asyncio
    async def test_persistence_preserves_embedding(self, tmp_path) -> None:
        path = tmp_path / "mem"
        store1 = SimpleMemoryStore(persist_dir=path, use_embedding=True)
        await store1.add("持久化嵌入测试", source="s1")

        # Reload from disk (no embedding model needed for read)
        store2 = SimpleMemoryStore(persist_dir=path, use_embedding=False)
        recent = await store2.list_recent(limit=10)
        assert len(recent) == 1
        assert recent[0].embedding is not None
        assert len(recent[0].embedding) > 0


# ---------------------------------------------------------------------------
# MemoryManager – smart_prune=False (legacy)
# ---------------------------------------------------------------------------


class TestLegacyPrune:
    """Ensure that smart_prune=False prunes purely by time (newest kept)."""

    @pytest.mark.asyncio
    async def test_prune_raw_time_based(self) -> None:
        store = SimpleMemoryStore()
        manager = MemoryManager(store, smart_prune=False)

        # Insert 5 raw entries
        for i in range(5):
            await store.add(
                f"raw entry {i}",
                source="s1",
                tags=["auto_capture"],
            )
            await asyncio.sleep(0.01)  # ensure ordering

        await manager._prune_raw(max_raw_entries=3)
        remaining = await store.list_recent(limit=10)
        raws = [e for e in remaining if "auto_capture" in e.tags]
        assert len(raws) == 3
        # Newest 3 should survive
        contents = {e.content for e in raws}
        assert "raw entry 4" in contents
        assert "raw entry 3" in contents
        assert "raw entry 2" in contents


# ---------------------------------------------------------------------------
# MemoryManager – smart_prune=True
# ---------------------------------------------------------------------------


class TestSmartPrune:
    """Verify importance-weighted pruning."""

    @pytest.mark.asyncio
    async def test_high_importance_old_entry_survives(self) -> None:
        store = SimpleMemoryStore()
        manager = MemoryManager(store, smart_prune=True)

        # Insert an old but high-importance entry
        old_important = await store.add(
            "用户对花生严重过敏",
            source="s1",
            tags=["auto_capture"],
            importance=0.95,
        )

        # Insert several newer but low-importance entries
        for i in range(5):
            await store.add(
                f"闲聊内容 {i}",
                source="s1",
                tags=["auto_capture"],
                importance=0.3,
            )
            await asyncio.sleep(0.01)

        await manager._prune_raw(max_raw_entries=3)
        remaining = await store.list_recent(limit=10)
        raws = [e for e in remaining if "auto_capture" in e.tags]
        assert len(raws) == 3
        # The high-importance entry should survive despite being oldest
        remaining_ids = {e.id for e in raws}
        assert old_important.id in remaining_ids

    @pytest.mark.asyncio
    async def test_no_prune_when_under_limit(self) -> None:
        store = SimpleMemoryStore()
        manager = MemoryManager(store, smart_prune=True)

        for i in range(3):
            await store.add(f"entry {i}", source="s1", tags=["auto_capture"])

        await manager._prune_raw(max_raw_entries=5)
        remaining = await store.list_recent(limit=10)
        raws = [e for e in remaining if "auto_capture" in e.tags]
        assert len(raws) == 3  # nothing pruned


# ---------------------------------------------------------------------------
# MemoryManager – importance scoring in auto_capture
# ---------------------------------------------------------------------------


class TestImportanceScoring:
    """Verify that auto_capture assigns appropriate importance values."""

    @pytest.mark.asyncio
    async def test_force_flush_high_importance(self) -> None:
        store = SimpleMemoryStore()
        manager = MemoryManager(store, smart_prune=True)

        await manager.auto_capture_user_message(
            "请记住，我对花生严重过敏",
            source="s1",
            mode="balanced",
            cooldown_seconds=0,
            max_per_hour=100,
        )
        recent = await store.list_recent(limit=10)
        captured = [e for e in recent if "auto_capture" in e.tags]
        assert len(captured) >= 1
        assert all(e.importance >= 0.8 for e in captured)

    @pytest.mark.asyncio
    async def test_default_importance(self) -> None:
        store = SimpleMemoryStore()
        manager = MemoryManager(store, smart_prune=True)

        await manager.auto_capture_user_message(
            "以后叫我老王",
            source="s1",
            mode="balanced",
            cooldown_seconds=0,
            max_per_hour=100,
        )
        recent = await store.list_recent(limit=10)
        captured = [e for e in recent if "auto_capture" in e.tags]
        assert len(captured) >= 1
        # "以后叫我老王" → triggers capture but not force-flush → importance 0.5
        assert all(e.importance >= 0.5 for e in captured)
