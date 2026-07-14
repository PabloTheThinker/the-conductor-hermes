"""Remnant Protocol data models — Phase 1 MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RemnantStatus(str, Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    SYNCING = "syncing"
    TERMINATED = "terminated"
    MERGED = "merged"
    FAILED = "failed"


class MergeTier(str, Enum):
    FAST = "fast"
    REFLECTIVE = "reflective"
    DEEP_SIMULATION = "deep_simulation"


class EmotionalValence(BaseModel):
    primary: str = "neutral"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    secondary: list[str] = Field(default_factory=list)
    notes: str | None = None


class TrackReference(BaseModel):
    track_id: str
    branch_id: str | None = None
    version: int = 1
    summary: str = Field(..., max_length=500)


class MemorySlice(BaseModel):
    episodic_ids: list[str] = Field(default_factory=list)
    semantic_keys: list[str] = Field(default_factory=list)
    emotional_valence_at_spawn: EmotionalValence = Field(default_factory=EmotionalValence)
    context_summary: str = Field(default="", max_length=2000)


class RemnantSnapshot(BaseModel):
    snapshot_id: str
    spawned_at: datetime = Field(default_factory=_utcnow)
    parent_session_id: str
    task_objective: str
    relevant_tracks: list[TrackReference]
    memory_slice: MemorySlice
    governance_scope: dict[str, Any] = Field(default_factory=dict)
    tool_access_scope: list[str] = Field(default_factory=list)


class ProgressHeartbeat(BaseModel):
    heartbeat_id: str
    remnant_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    current_subtask: str = ""
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    key_decisions: list[str] = Field(default_factory=list)
    emotional_valence_delta: EmotionalValence = Field(default_factory=EmotionalValence)
    blocking_issues: list[str] = Field(default_factory=list)
    new_insights: list[str] = Field(default_factory=list)


class CloneStatus(str, Enum):
    """Shadow-clone lifecycle (host subagent or local worker)."""

    NONE = "none"
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HOST = "awaiting_host"
    SPAWNED = "spawned"  # parent acked host spawn (clone_handle set); not merge-ready yet
    COMPLETED = "completed"
    FAILED = "failed"
    REPORTED = "reported"


class RemnantRecord(BaseModel):
    remnant_id: str
    session_id: str
    snapshot_id: str
    status: RemnantStatus = RemnantStatus.SPAWNING
    spawned_at: datetime = Field(default_factory=_utcnow)
    terminated_at: datetime | None = None
    strategy: str = ""
    task_objective: str = ""
    forked_track_branch_id: str = ""
    current_heartbeat: ProgressHeartbeat | None = None
    merge_insights: list[str] = Field(default_factory=list)
    # Structured offline work pack for the host (not empty shells)
    work_pack: dict[str, Any] = Field(default_factory=dict)
    # Shadow clone (subagent) state — Naruto-style parallel mission
    clone_backend: str = ""  # local | host | hermes
    clone_status: CloneStatus = CloneStatus.NONE
    clone_handle: str = ""  # host subagent id if known
    spawn_request: dict[str, Any] = Field(default_factory=dict)
    clone_result: dict[str, Any] = Field(default_factory=dict)


class MergeProposal(BaseModel):
    proposal_id: str
    session_id: str
    remnant_ids: list[str]
    tier: MergeTier = MergeTier.FAST
    proposed_at: datetime = Field(default_factory=_utcnow)
    summary: str = ""
    track_deltas: list[dict[str, Any]] = Field(default_factory=list)
    memory_deltas: list[dict[str, Any]] = Field(default_factory=list)
    emotional_reconciliation: EmotionalValence = Field(default_factory=EmotionalValence)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    divergence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class MergeResult(BaseModel):
    result_id: str
    proposal_id: str
    merged_at: datetime = Field(default_factory=_utcnow)
    success: bool = True
    new_track_version: int = 1
    new_track_id: str = ""
    merged_insights: list[str] = Field(default_factory=list)
    emotional_valence_final: EmotionalValence = Field(default_factory=EmotionalValence)
    governance_notes: str | None = None
