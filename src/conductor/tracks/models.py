"""Track System models — multiverse chessboard nodes."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TrackRecord(BaseModel):
    track_id: str
    title: str
    summary: str = ""
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    status: str = "active"  # active | pruned | resolved | archived | forked
    domain: str = "orchestration"
    version: int = 1
    branch_id: str | None = None
    parent_id: str | None = None
    root_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    conductor_notes: str = ""
    emotional_valence: dict[str, float | str] = Field(
        default_factory=lambda: {"primary": "neutral", "intensity": 0.5}
    )


# Graph edge relations (TRACK_SYSTEM.md)
EDGE_RELATIONS = (
    "leads_to",
    "conflicts_with",
    "compounds_with",
    "inspired_by",
    "blocks",
    "extends",
    "forked_from",
)


class TrackEdge(BaseModel):
    """Directed relationship between two tracks on the multiverse chessboard."""

    edge_id: str
    from_track_id: str
    to_track_id: str
    relation: str = "leads_to"
    strength: float = Field(default=0.7, ge=0.0, le=1.0)
    reason: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    discovered_in_crucible: str | None = None
