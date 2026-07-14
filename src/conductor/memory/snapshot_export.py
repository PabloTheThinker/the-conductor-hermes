"""Export task-scoped memory slices for Crucible and Remnant snapshots."""

from __future__ import annotations

from typing import Any

from conductor.memory.episodic import EpisodicStore
from conductor.memory.models import EmotionalValence
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore


def export_task_scoped_slice(
    store: SessionStore,
    agent_session_id: str,
    *,
    objective: str = "",
    episodic_limit: int = 5,
) -> dict[str, Any]:
    """Build a lightweight memory slice for pocket-dimension / remnant spawn."""
    episodic = EpisodicStore(store)
    tracks = TrackStore(store)
    recent = episodic.recent_slice(agent_session_id, limit=episodic_limit)
    track_list = tracks.list_tracks(agent_session_id)

    emotion = EmotionalValence()
    if recent:
        emotion = recent[0].emotional_valence

    return {
        "episodic_ids": [e.entry_id for e in recent],
        "episodic_entries": [e.model_dump(mode="json") for e in recent],
        "semantic_keys": [f"track:{t.track_id}" for t in track_list[:3]],
        "emotional_valence_at_spawn": emotion.model_dump(mode="json"),
        "context_summary": objective or (recent[0].content[:500] if recent else ""),
        "track_count": len(track_list),
    }
