"""Tests for EvoMapIdentity."""

from __future__ import annotations

import json

from whaleclaw.plugins.evomap.identity import EvoMapIdentity


def test_creates_sender_id(tmp_path) -> None:
    path = tmp_path / "identity.json"
    ident = EvoMapIdentity(path=path)
    sid = ident.get_or_create_sender_id()
    assert sid.startswith("node_")
    assert len(sid) == len("node_") + 16


def test_persists_and_reloads_same_id(tmp_path) -> None:
    path = tmp_path / "identity.json"
    ident1 = EvoMapIdentity(path=path)
    sid1 = ident1.get_or_create_sender_id()

    ident2 = EvoMapIdentity(path=path)
    sid2 = ident2.get_or_create_sender_id()
    assert sid1 == sid2


def test_save_claim_code(tmp_path) -> None:
    path = tmp_path / "identity.json"
    ident = EvoMapIdentity(path=path)
    ident.get_or_create_sender_id()
    ident.save_claim_code("REEF-4X7K", "https://evomap.ai/claim/REEF-4X7K")

    data = json.loads(path.read_text())
    assert data["claim_code"] == "REEF-4X7K"
    assert data["claim_url"] == "https://evomap.ai/claim/REEF-4X7K"
