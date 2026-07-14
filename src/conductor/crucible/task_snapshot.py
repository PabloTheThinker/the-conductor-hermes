"""Task-scoped Crucible snapshot — Phase 2a pocket dimension (in-process)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from conductor.memory.snapshot_export import export_task_scoped_slice
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskScopedSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_session_id: str
    objective: str = ""
    exported_at: datetime = Field(default_factory=_utcnow)
    memory_slice: dict[str, Any] = Field(default_factory=dict)
    track_refs: list[dict[str, Any]] = Field(default_factory=list)
    conductor_objective: str = ""
    workspace_seed_labels: list[str] = Field(default_factory=list)


def export_crucible_task_snapshot(
    store: SessionStore,
    agent_session_id: str,
    *,
    objective: str = "",
    conductor_meta: dict[str, Any] | None = None,
) -> TaskScopedSnapshot:
    memory_slice = export_task_scoped_slice(store, agent_session_id, objective=objective)
    track_store = TrackStore(store)
    track_refs = [t.model_dump(mode="json") for t in track_store.list_tracks(agent_session_id)[:5]]
    meta = conductor_meta or {}
    seed_labels: list[str] = []
    last = meta.get("last_snapshot")
    if isinstance(last, dict):
        for slot in last.get("slots") or []:
            if isinstance(slot, dict) and slot.get("label"):
                seed_labels.append(str(slot["label"]))

    return TaskScopedSnapshot(
        parent_session_id=agent_session_id,
        objective=objective,
        memory_slice=memory_slice,
        track_refs=track_refs,
        conductor_objective=str(meta.get("objective") or ""),
        workspace_seed_labels=seed_labels[:8],
    )


def snapshot_summary(snapshot: TaskScopedSnapshot) -> str:
    episodic_count = len(snapshot.memory_slice.get("episodic_entries") or [])
    tracks = len(snapshot.track_refs)
    return (
        f"objective={snapshot.objective or '(open)'}; "
        f"episodic={episodic_count}; tracks={tracks}; "
        f"seeds={len(snapshot.workspace_seed_labels)}"
    )
