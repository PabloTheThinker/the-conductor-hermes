"""Episodic memory store — durable events with outcome + valence."""

from __future__ import annotations

import uuid
from typing import Any

from conductor.memory.models import EmotionalValence, EpisodicEntry
from conductor.session.store import SessionStore

EPISODIC_META_KEY = "episodic_memory"


class EpisodicStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load(self, agent_session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(agent_session_id, EPISODIC_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save(self, agent_session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(agent_session_id, EPISODIC_META_KEY, data)

    def write(
        self,
        agent_session_id: str,
        *,
        content: str,
        context: str = "",
        outcome: str = "info",
        emotion_primary: str = "neutral",
        emotion_intensity: float = 0.5,
        tags: list[str] | None = None,
    ) -> EpisodicEntry:
        entry = EpisodicEntry(
            entry_id=str(uuid.uuid4()),
            session_id=agent_session_id,
            content=content,
            context=context,
            outcome=outcome or "info",
            emotional_valence=EmotionalValence(
                primary=emotion_primary,
                intensity=emotion_intensity,
            ),
            tags=tags or [],
        )
        data = self._load(agent_session_id)
        items: list[Any] = list(data.get("items") or [])
        items.append(entry.model_dump(mode="json"))
        data["items"] = items
        self._save(agent_session_id, data)
        return entry

    def list_entries(self, agent_session_id: str, *, limit: int = 50) -> list[EpisodicEntry]:
        data = self._load(agent_session_id)
        items = data.get("items") or []
        entries = [EpisodicEntry.model_validate(item) for item in items if isinstance(item, dict)]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)[:limit]

    def get_entry(self, agent_session_id: str, entry_id: str) -> EpisodicEntry | None:
        for entry in self.list_entries(agent_session_id, limit=10_000):
            if entry.entry_id == entry_id:
                return entry
        return None

    def recent_slice(self, agent_session_id: str, *, limit: int = 5) -> list[EpisodicEntry]:
        return self.list_entries(agent_session_id, limit=limit)

    def query(
        self,
        agent_session_id: str,
        *,
        tag: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
    ) -> list[EpisodicEntry]:
        rows = self.list_entries(agent_session_id, limit=10_000)
        if tag:
            rows = [e for e in rows if tag in e.tags]
        if outcome:
            rows = [e for e in rows if e.outcome == outcome]
        return rows[:limit]


def record_lifecycle_event(
    store: SessionStore,
    agent_session_id: str,
    *,
    kind: str,
    content: str,
    outcome: str = "info",
    emotion_primary: str = "neutral",
    emotion_intensity: float = 0.5,
    context: str = "",
    extra_tags: list[str] | None = None,
) -> EpisodicEntry:
    """Write a lifecycle episodic event (goal / remnant / delegate / etc.)."""
    tags = ["lifecycle", kind]
    if extra_tags:
        tags.extend(extra_tags)
    return EpisodicStore(store).write(
        agent_session_id,
        content=content,
        context=context or kind,
        outcome=outcome,
        emotion_primary=emotion_primary,
        emotion_intensity=emotion_intensity,
        tags=tags,
    )
