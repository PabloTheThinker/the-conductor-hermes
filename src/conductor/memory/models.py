"""Memory Fabric — episodic layer models (Phase 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EmotionalValence(BaseModel):
    primary: str = "neutral"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str | None = None


OutcomeKind = Literal["success", "failure", "pending", "info", ""]


class EpisodicEntry(BaseModel):
    entry_id: str
    session_id: str
    content: str
    context: str = ""
    outcome: str = "info"  # success | failure | pending | info
    emotional_valence: EmotionalValence = Field(default_factory=EmotionalValence)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
