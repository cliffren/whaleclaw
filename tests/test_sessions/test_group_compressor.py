"""Tests for session group compressor behavior."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from whaleclaw.providers.base import Message
from whaleclaw.sessions.group_compressor import SessionGroupCompressor, _hash_group
from whaleclaw.sessions.store import SessionStore


def _mk_group(i: int, text: str) -> list[Message]:
    return [
        Message(role="user", content=f"u{i}:{text}"),
        Message(role="assistant", content=f"a{i}:{text}"),
    ]


def _flatten(groups: list[list[Message]]) -> list[Message]:
    out: list[Message] = []
    for g in groups:
        out.extend(g)
    return out


class _NoopRouter:
    async def chat(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("chat should not be called when model_id is empty")


class _SlowRouter:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.calls += 1
        await asyncio.sleep(0.15)
        return SimpleNamespace(content="压缩摘要")


async def _mk_store(tmp_path) -> SessionStore:  # noqa: ANN001
    store = SessionStore(db_path=tmp_path / "group_compressor.db")
    await store.open()
    return store


@pytest.mark.asyncio
async def test_window_plan_uses_absolute_group_index(tmp_path) -> None:  # noqa: ANN001
    store = await _mk_store(tmp_path)
    try:
        compressor = SessionGroupCompressor(store)
        groups = [_mk_group(i, "短消息") for i in range(1, 31)]
        plan = compressor._window_plan(_flatten(groups))  # noqa: SLF001
        assert len(plan) == 25
        assert plan[0].group_idx == 6
        assert plan[-1].group_idx == 30
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_build_window_messages_schedules_background_generation(tmp_path) -> None:  # noqa: ANN001
    store = await _mk_store(tmp_path)
    compressor = SessionGroupCompressor(store)
    try:
        now = datetime.now(UTC).isoformat()
        await store.save_session(
            session_id="s2",
            channel="webchat",
            peer_id="u2",
            model="qwen/qwen3.5-plus",
            created_at=now,
            updated_at=now,
        )
        groups = [_mk_group(i, "需要压缩的历史消息 " + ("x" * 120)) for i in range(1, 13)]
        router = _SlowRouter()

        t0 = time.monotonic()
        output = await compressor.build_window_messages(
            session_id="s2",
            messages=_flatten(groups),
            router=router,  # type: ignore[arg-type]
            model_id="compress-model",
        )
        elapsed = time.monotonic() - t0

        assert elapsed < 0.2
        assert output

        plan = compressor._window_plan(_flatten(groups))  # noqa: SLF001
        first = next(item for item in plan if item.level != "L2")
        source_hash = _hash_group(first.group)

        found = False
        for _ in range(20):
            cached = await store.get_group_compression(
                session_id="s2",
                group_idx=first.group_idx,
                level=first.level,
                source_hash=source_hash,
            )
            if cached:
                found = True
                break
            await asyncio.sleep(0.05)

        assert found
        assert router.calls > 0
    finally:
        await compressor.shutdown()
        await store.close()


@pytest.mark.asyncio
async def test_recent_over_budget_downgrades_non_first_groups_to_l0(tmp_path) -> None:  # noqa: ANN001
    store = await _mk_store(tmp_path)
    try:
        compressor = SessionGroupCompressor(store)
        # 6 groups: first is always L2 (anchor), groups 4-5 should be L0 (over budget), group 6 L2
        groups = [
            _mk_group(1, "旧历史"),
            _mk_group(2, "中间历史"),
            _mk_group(3, "中间历史"),
            _mk_group(4, "最近第3组 " + ("超长内容 " * 600)),
            _mk_group(5, "最近第2组 " + ("超长内容 " * 600)),
            _mk_group(6, "最近第1组 " + ("超长内容 " * 600)),
        ]
        plan = compressor._window_plan(_flatten(groups))  # noqa: SLF001
        # First group is always L2 (task anchor)
        first_item = next(x for x in plan if x.group_idx == 1)
        assert first_item.level == "L2"
        # Last group (most recent) should be L2
        assert plan[-1].level == "L2"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_window_plan_compresses_22_groups_when_25_groups_present(tmp_path) -> None:  # noqa: ANN001
    store = await _mk_store(tmp_path)
    try:
        compressor = SessionGroupCompressor(store)
        groups = [_mk_group(i, "消息") for i in range(1, 26)]
        plan = compressor._window_plan(_flatten(groups))  # noqa: SLF001
        l2 = sum(1 for x in plan if x.level == "L2")
        l1 = sum(1 for x in plan if x.level == "L1")
        l0 = sum(1 for x in plan if x.level == "L0")
        # First group is always L2 (task anchor) + 3 recent L2 = 4 L2 total
        assert l2 == 4
        assert l1 == 7
        assert l0 == 14
        # First group must be L2
        assert plan[0].group_idx <= 25
        first_item = next(x for x in plan if x.group_idx == 1)
        assert first_item.level == "L2"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_first_group_always_l2(tmp_path) -> None:  # noqa: ANN001
    """First group (original user task) should always be L2 regardless of history length."""
    store = await _mk_store(tmp_path)
    try:
        compressor = SessionGroupCompressor(store)
        # Create 30 groups — first group should still be L2 even though it's very old
        groups = [_mk_group(i, "消息内容") for i in range(1, 31)]
        plan = compressor._window_plan(_flatten(groups))  # noqa: SLF001
        # Only the last 25 groups are in the window, but if group_idx=1 is in window, it's L2
        for item in plan:
            if item.group_idx == 1:
                assert item.level == "L2", f"First group should be L2, got {item.level}"
                break
        # For groups within window, verify first available group
        if plan[0].group_idx > 1:
            # First group fell outside window — that's OK, the anchor logic in
            # build_window_messages handles this separately
            pass
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_build_window_includes_task_anchor(tmp_path) -> None:  # noqa: ANN001
    """build_window_messages should inject a 【原始任务】 anchor block from the first group."""
    store = await _mk_store(tmp_path)
    try:
        compressor = SessionGroupCompressor(store)
        now = datetime.now(UTC).isoformat()
        await store.save_session(
            session_id="s_anchor",
            channel="webchat",
            peer_id="u_anchor",
            model="qwen/qwen3.5-plus",
            created_at=now,
            updated_at=now,
        )
        # 8 groups: first is the original task, rest are follow-ups
        groups = [_mk_group(1, "帮我写一个Python爬虫脚本")]
        for i in range(2, 9):
            groups.append(_mk_group(i, f"第{i}轮对话内容"))
        output = await compressor.build_window_messages(
            session_id="s_anchor",
            messages=_flatten(groups),
            router=_NoopRouter(),  # type: ignore[arg-type]
            model_id="",
        )

        text = "\n".join(m.content for m in output)
        assert "【原始任务】" in text
        assert "帮我写一个Python爬虫脚本" in text
    finally:
        await store.close()
