# Remnant Protocol — Data Models & Pydantic Schemas

**Status**: Implementation Specification (Phase 1)  
**Version**: 0.1.0  
**Related Documents**: `REMNANT_PROTOCOL.md`, `REMNANT_MERGE_LOGIC.md`, `TRACK_SYSTEM.md`

---

## 1. Overview

This document defines the core data models for the Remnant Protocol. These models support:

- Task-scoped snapshots (lightweight, not full memory dumps)
- Live parallel Remnant execution
- Heartbeat monitoring
- Merge proposal collection
- Integration with the Track System and Memory Fabric

All models are designed to be serializable, versioned, and suitable for both in-process use (MVP) and future persistence in SQLite / durable log.

---

## 2. Core Pydantic Models

```python
from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class RemnantStatus(str, Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    SYNCING = "syncing"
    TERMINATED = "terminated"
    MERGED = "merged"
    FAILED = "failed"


class MergeTier(str, Enum):
    FAST = "fast"                    # Tier 1
    REFLECTIVE = "reflective"        # Tier 2
    DEEP_SIMULATION = "deep_simulation"  # Tier 3 (Crucible)


class EmotionalValence(BaseModel):
    """Emotional tone and intensity at a point in time."""
    primary: str = Field(..., description="Primary emotion (e.g., determined, anxious, hopeful, frustrated)")
    intensity: float = Field(..., ge=0.0, le=1.0, description="0.0 = none, 1.0 = overwhelming")
    secondary: Optional[List[str]] = Field(default=None, description="Secondary emotions")
    notes: Optional[str] = Field(default=None, description="Contextual notes about emotional state")


class TrackReference(BaseModel):
    """Lightweight reference to a Track or Track branch."""
    track_id: UUID
    branch_id: Optional[UUID] = None
    version: int
    summary: str = Field(..., max_length=500)


class MemorySlice(BaseModel):
    """Task-scoped memory snapshot (not full memory)."""
    episodic_ids: List[UUID] = Field(default_factory=list)
    semantic_keys: List[str] = Field(default_factory=list)
    emotional_valence_at_spawn: EmotionalValence
    context_summary: str = Field(..., max_length=2000)


class RemnantSnapshot(BaseModel):
    """
    Lightweight, task-scoped snapshot used to spawn a Remnant.
    This is NOT a full memory clone.
    """
    snapshot_id: UUID = Field(default_factory=uuid4)
    spawned_at: datetime = Field(default_factory=datetime.utcnow)
    parent_conductor_id: UUID
    task_objective: str
    relevant_tracks: List[TrackReference]
    memory_slice: MemorySlice
    governance_scope: Dict[str, Any] = Field(default_factory=dict)  # Inherited constitutional rules
    tool_access_scope: List[str] = Field(default_factory=list)

    @field_validator('relevant_tracks')
    @classmethod
    def validate_tracks_not_empty(cls, v):
        if not v:
            raise ValueError("At least one relevant track must be provided")
        return v


class ProgressHeartbeat(BaseModel):
    """Periodic status update from a running Remnant."""
    heartbeat_id: UUID = Field(default_factory=uuid4)
    remnant_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    current_subtask: str
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    key_decisions: List[str] = Field(default_factory=list)
    emotional_valence_delta: EmotionalValence
    blocking_issues: List[str] = Field(default_factory=list)
    new_insights: List[str] = Field(default_factory=list)
    estimated_completion: Optional[datetime] = None


class RemnantInstance(BaseModel):
    """Represents a live running Remnant."""
    remnant_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    snapshot_id: UUID
    status: RemnantStatus = RemnantStatus.SPAWNING
    spawned_at: datetime = Field(default_factory=datetime.utcnow)
    terminated_at: Optional[datetime] = None
    current_heartbeat: Optional[ProgressHeartbeat] = None
    forked_track_branch_id: UUID
    resource_usage: Dict[str, Any] = Field(default_factory=dict)  # tokens, time, etc.


class RemnantSession(BaseModel):
    """A bounded session containing one or more Remnants working toward a shared goal."""
    session_id: UUID = Field(default_factory=uuid4)
    parent_conductor_id: UUID
    objective: str
    spawned_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, merging, completed, failed
    remnants: List[RemnantInstance] = Field(default_factory=list)
    heartbeats: List[ProgressHeartbeat] = Field(default_factory=list)
    merge_proposals: List[MergeProposal] = Field(default_factory=list)
    final_merged_track_id: Optional[UUID] = None


class MergeProposal(BaseModel):
    """A proposal from one or more Remnants to be merged back into the main self."""
    proposal_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    remnant_ids: List[UUID]
    tier: MergeTier
    proposed_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    track_deltas: List[Dict[str, Any]] = Field(default_factory=list)  # Changes to Track graph
    memory_deltas: List[Dict[str, Any]] = Field(default_factory=list)
    emotional_reconciliation: EmotionalValence
    confidence: float = Field(..., ge=0.0, le=1.0)
    risks: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)  # From Voice of Action influence
    divergence_score: float = Field(..., ge=0.0, le=1.0)


class MergeResult(BaseModel):
    """Outcome of a merge operation."""
    result_id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    merged_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    new_track_version: int
    new_track_id: UUID
    emotional_valence_final: EmotionalValence
    governance_notes: Optional[str] = None
    escalated_to_human: bool = False
    escalated_reason: Optional[str] = None
```

---

## 3. Key Design Notes

### Snapshot Philosophy
- `RemnantSnapshot` is intentionally **task-scoped**, not a full memory dump. This keeps spawning fast and focused.
- Emotional valence is captured at spawn time and carried as a baseline for later reconciliation.

### Heartbeat Design
- Heartbeats are the primary observability mechanism.
- They should be emitted every 30–120 seconds during active work.
- Missed heartbeats can trigger alerts or automatic termination by the main Conductor.

### MergeProposal
- This is the central artifact that feeds into `REMNANT_MERGE_LOGIC.md`.
- It carries enough information for Tier 1 (Fast), Tier 2 (Reflective), or Tier 3 (Deep Simulation) merge strategies.
- `divergence_score` helps the Governance layer decide which merge tier to use.

### Relationship to Track System
- Every Remnant works on a **forked Track branch**.
- Merge results create explicit **merge nodes** in the Track graph with full provenance (`remnant_ids`, `proposal_id`, etc.).

---

## 4. Future Extensions (Phase 2+)

- Add `RemnantProfile` for persistent identity for persistent identity across sessions.
- Add cryptographic signing of heartbeats and merge proposals for auditability.
- Add `RemnantCheckpoint` model for checkpoint-fork-style time-travel and resumption.
- Integrate with the native task ledger if scale demands it.

---

These models provide a solid, implementable foundation for Phase 1 of the Remnant Protocol while leaving room for the more sophisticated patterns we may need later.

---

## 5. Related Documents

| Document | Purpose |
|----------|---------|
| `REMNANT_PROTOCOL.md` | Lifecycle and spawn rules |
| `REMNANT_MERGE_LOGIC.md` | Tiered merge strategies |
| `REMNANT_RESEARCH.md` | Conceptual deep dive and implementation priorities |