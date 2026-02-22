"""Tests for HookManager."""

from __future__ import annotations

import pytest

from whaleclaw.plugins.hooks import HookContext, HookManager, HookPoint, HookResult


@pytest.mark.asyncio
async def test_register_and_run_priority_order() -> None:
    results: list[int] = []

    def make_cb(prio: int):
        async def cb(ctx: HookContext) -> HookResult:
            results.append(prio)
            return HookResult(proceed=True, data={})
        return cb

    mgr = HookManager()
    mgr.register(HookPoint.BEFORE_MESSAGE, make_cb(10), priority=10)
    mgr.register(HookPoint.BEFORE_MESSAGE, make_cb(0), priority=0)
    mgr.register(HookPoint.BEFORE_MESSAGE, make_cb(5), priority=5)

    ctx = HookContext(hook=HookPoint.BEFORE_MESSAGE, session_id="s1", data={})
    await mgr.run(HookPoint.BEFORE_MESSAGE, ctx)

    assert results == [0, 5, 10]


@pytest.mark.asyncio
async def test_stop_on_proceed_false() -> None:
    results: list[str] = []

    async def first(ctx: HookContext) -> HookResult:
        results.append("first")
        return HookResult(proceed=False, data={})

    async def second(ctx: HookContext) -> HookResult:
        results.append("second")
        return HookResult(proceed=True, data={})

    mgr = HookManager()
    mgr.register(HookPoint.BEFORE_MESSAGE, first, priority=0)
    mgr.register(HookPoint.BEFORE_MESSAGE, second, priority=1)

    ctx = HookContext(hook=HookPoint.BEFORE_MESSAGE, session_id="s1", data={})
    out = await mgr.run(HookPoint.BEFORE_MESSAGE, ctx)

    assert results == ["first"]
    assert out.proceed is False


@pytest.mark.asyncio
async def test_data_merged_across_callbacks() -> None:
    async def add_a(ctx: HookContext) -> HookResult:
        d = dict(ctx.data)
        d["a"] = 1
        return HookResult(proceed=True, data=d)

    async def add_b(ctx: HookContext) -> HookResult:
        d = dict(ctx.data)
        d["b"] = 2
        return HookResult(proceed=True, data=d)

    mgr = HookManager()
    mgr.register(HookPoint.BEFORE_MESSAGE, add_a, priority=0)
    mgr.register(HookPoint.BEFORE_MESSAGE, add_b, priority=1)

    ctx = HookContext(hook=HookPoint.BEFORE_MESSAGE, session_id="s1", data={})
    out = await mgr.run(HookPoint.BEFORE_MESSAGE, ctx)

    assert out.proceed is True
    assert out.data == {"a": 1, "b": 2}
