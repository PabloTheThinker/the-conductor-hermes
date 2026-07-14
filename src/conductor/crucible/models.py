"""Pydantic models for the Crucible Global Workspace layer."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class EmotionalValence(BaseModel):
    primary: str
    intensity: float = Field(ge=0.0, le=1.0)
    secondary: list[str] | None = None
    notes: str | None = None


class WorkspaceConcept(BaseModel):
    concept_id: UUID = Field(default_factory=uuid4)
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    salience: float = 0.0
    source_clone_id: str | None = None
    reasoning_layer: int = 0
    valence: EmotionalValence
    track_refs: list[str] = Field(default_factory=list)
    reportable: bool = True
    automatic: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def _label_max_length(cls, value: str) -> str:
        if len(value) > 120:
            raise ValueError("label must be at most 120 characters")
        return value

    def compute_salience(self) -> float:
        reportable_factor = 1.0 if self.reportable else 0.3
        return self.confidence * (0.5 + 0.5 * self.valence.intensity) * reportable_factor

    @model_validator(mode="after")
    def _set_salience(self) -> WorkspaceConcept:
        self.salience = self.compute_salience()
        return self


class WorkspaceState(BaseModel):
    generation: int = 0
    slots: list[WorkspaceConcept] = Field(default_factory=list)
    capacity: int = 32
    active_clone_ids: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkspaceOperation(str, Enum):
    POST = "POST"
    REPLACE = "REPLACE"
    EVICT = "EVICT"
    READ = "READ"
    CLEAR = "CLEAR"
    CLONE_REGISTER = "CLONE_REGISTER"


class WorkspaceEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    operation: WorkspaceOperation
    actor_clone_id: str | None = None
    concept: WorkspaceConcept | None = None
    evicted_labels: list[str] = Field(default_factory=list)
    generation_after: int = 0


class CloneStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class CloneIdentity(BaseModel):
    clone_id: str
    birth_moment_label: str
    snapshot_summary: str
    forked_from: str | None = None
    status: CloneStatus = CloneStatus.ACTIVE


class DistillationCandidate(BaseModel):
    label: str
    confidence: float
    supporting_events: list[UUID] = Field(default_factory=list)
    valence: EmotionalValence | None = None
    track_refs: list[str] = Field(default_factory=list)
    proposed_action: str | None = None


class DistillationResult(BaseModel):
    promoted_insights: list[str] = Field(default_factory=list)
    proposed_skills: list[str] = Field(default_factory=list)
    track_updates: list[dict[str, Any]] = Field(default_factory=list)
    quarantined: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
