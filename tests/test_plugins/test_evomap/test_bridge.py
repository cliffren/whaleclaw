"""Tests for EvoMap bridge helpers."""

from __future__ import annotations

from whaleclaw.plugins.evomap.bridge import build_memory_hint_from_hook_data


def test_build_memory_hint_from_hook_data() -> None:
    block = build_memory_hint_from_hook_data(
        {
            "evomap_suggestions": [
                {"asset_id": "sha256:1", "summary": "先定位瓶颈再并行化"},
                {"asset_id": "sha256:2", "title": "错误恢复模板"},
            ]
        }
    )
    assert "EvoMap 协作经验候选" in block
    assert "先定位瓶颈再并行化" in block
    assert "错误恢复模板" in block


def test_build_memory_hint_caps_to_four_items() -> None:
    block = build_memory_hint_from_hook_data(
        {
            "evomap_suggestions": [
                {"summary": "s1"},
                {"summary": "s2"},
                {"summary": "s3"},
                {"summary": "s4"},
                {"summary": "s5"},
            ]
        }
    )
    assert "s1" in block and "s4" in block
    assert "s5" not in block
