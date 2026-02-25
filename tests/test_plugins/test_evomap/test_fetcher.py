"""Tests for AssetFetcher local cache search."""

from __future__ import annotations

import json

from whaleclaw.plugins.evomap.fetcher import AssetFetcher


class _DummyClient:
    async def fetch(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return {"assets": []}


def test_search_cached_by_signals_hits_summary(tmp_path) -> None:
    fetcher = AssetFetcher(_DummyClient(), cache_dir=tmp_path)  # type: ignore[arg-type]
    asset = {
        "asset_id": "sha256:abc",
        "summary": "修复 websocket 超时重连策略",
        "trigger": ["timeout", "websocket"],
    }
    (tmp_path / "a.json").write_text(json.dumps(asset, ensure_ascii=False), encoding="utf-8")

    out = fetcher.search_cached_by_signals(["websocket"], limit=3)
    assert len(out) == 1
    assert out[0]["asset_id"] == "sha256:abc"
