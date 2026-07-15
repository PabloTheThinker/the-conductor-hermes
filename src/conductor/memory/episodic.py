"""Episodic memory store — durable events with outcome + valence."""

from __future__ import annotations

import uuid
from typing import Any

from conductor.memory.models import EmotionalValence, EpisodicEntry
from conductor.session.store import SessionStore

EPISODIC_META_KEY = "episodic_memory"
# Hard cap keeps session meta JSON bounded; newest retained.
EPISODIC_MAX_ITEMS = 2000

_FAILURE_OUTCOMES = frozenset({"failure", "fail", "error", "blocked", "reject"})
_SUCCESS_OUTCOMES = frozenset({"success", "ok", "done", "resolved"})


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
        if len(items) > EPISODIC_MAX_ITEMS:
            items = items[-EPISODIC_MAX_ITEMS:]
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
        content: str | None = None,
        limit: int = 50,
    ) -> list[EpisodicEntry]:
        """Filter by tag, outcome, and/or free-text match on content/context/tags."""
        rows = self.list_entries(agent_session_id, limit=10_000)
        if tag:
            rows = [e for e in rows if tag in (e.tags or [])]
        if outcome:
            rows = [e for e in rows if e.outcome == outcome]
        if content:
            qlow = content.strip().lower()
            if qlow:
                rows = [
                    e
                    for e in rows
                    if qlow in (e.content or "").lower()
                    or qlow in (e.context or "").lower()
                    or any(qlow in str(t).lower() for t in (e.tags or []))
                ]
        return rows[:limit]

    def select_for_inject(
        self,
        agent_session_id: str,
        *,
        limit: int = 4,
        pool: int = 40,
    ) -> list[EpisodicEntry]:
        """Rank recent episodes for prompt injection: failures + high valence first."""
        rows = self.list_entries(agent_session_id, limit=pool)
        if not rows:
            return []

        def _score(e: EpisodicEntry) -> tuple[float, float, float]:
            outcome = (e.outcome or "").strip().lower()
            intensity = float(e.emotional_valence.intensity or 0.0)
            fail_boost = 2.0 if outcome in _FAILURE_OUTCOMES else 0.0
            success_nudge = 0.35 if outcome in _SUCCESS_OUTCOMES else 0.0
            # created_at as secondary recency (higher = newer)
            try:
                recency = e.created_at.timestamp()
            except Exception:  # noqa: BLE001
                recency = 0.0
            return (fail_boost + intensity + success_nudge, recency, intensity)

        ranked = sorted(rows, key=_score, reverse=True)
        return ranked[:limit]


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
