"""EvoMap GEP-A2A data models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BlastRadius(BaseModel):
    """Impact scope of an asset."""

    files: int
    lines: int


class Outcome(BaseModel):
    """Validation outcome."""

    status: Literal["success", "failure"]
    score: float


class EnvFingerprint(BaseModel):
    """Environment fingerprint."""

    platform: str
    arch: str


class Gene(BaseModel):
    """Gene asset - strategy template."""

    type: Literal["Gene"] = "Gene"
    schema_version: str = "1.5.0"
    category: Literal["repair", "optimize", "innovate"]
    signals_match: list[str]
    summary: str
    validation: list[str] = []
    asset_id: str = ""


class Capsule(BaseModel):
    """Capsule asset - verified fix."""

    type: Literal["Capsule"] = "Capsule"
    schema_version: str = "1.5.0"
    trigger: list[str]
    gene: str
    summary: str
    confidence: float
    blast_radius: BlastRadius
    outcome: Outcome
    env_fingerprint: EnvFingerprint
    success_streak: int = 0
    asset_id: str = ""


class EvolutionEvent(BaseModel):
    """Evolution event record."""

    type: Literal["EvolutionEvent"] = "EvolutionEvent"
    intent: Literal["repair", "optimize", "innovate"]
    capsule_id: str = ""
    genes_used: list[str] = []
    outcome: Outcome
    mutations_tried: int = 1
    total_cycles: int = 1
    asset_id: str = ""


class Task(BaseModel):
    """Bounty task."""

    task_id: str
    title: str
    signals: str
    bounty_id: str | None = None
    min_reputation: int = 0
    status: Literal["open", "claimed", "completed"]
    expires_at: datetime | None = None
    swarm_role: str | None = None
    parent_task_id: str | None = None
