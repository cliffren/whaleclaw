"""Tests for AssetHasher."""

from __future__ import annotations

from whaleclaw.plugins.evomap.hasher import AssetHasher


def test_compute_asset_id_deterministic() -> None:
    asset = {"type": "Capsule", "summary": "fix for X", "schema_version": "1.5.0"}
    a = AssetHasher.compute_asset_id(asset)
    b = AssetHasher.compute_asset_id(asset)
    assert a == b


def test_compute_asset_id_starts_with_sha256() -> None:
    asset = {"type": "Gene", "signals_match": ["err"]}
    result = AssetHasher.compute_asset_id(asset)
    assert result.startswith("sha256:")


def test_compute_asset_id_ignores_asset_id_field() -> None:
    base = {"type": "Capsule", "summary": "same"}
    a = AssetHasher.compute_asset_id({**base, "asset_id": "sha256:old"})
    b = AssetHasher.compute_asset_id({**base, "asset_id": "sha256:other"})
    c = AssetHasher.compute_asset_id(base)
    assert a == b == c
