"""Semantic memory notes — consolidated patterns from episodic lifecycle events."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from conductor.memory.episodic import EpisodicStore
from conductor.session.store import SessionStore

SEMANTIC_META_KEY = "semantic_memory"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SemanticNote(BaseModel):
    note_id: str
    session_id: str
    statement: str
    source_entry_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)


_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "for",
        "in",
        "on",
        "at",
        "is",
        "was",
        "with",
        "from",
        "that",
        "this",
        "into",
        "via",
        "set",
        "goal",
    }
)


def _tokens(text: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", text.lower())
        if t not in _STOP
    ]


class SemanticStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load(self, session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(session_id, SEMANTIC_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save(self, session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(session_id, SEMANTIC_META_KEY, data)

    def list_notes(self, session_id: str, *, limit: int = 50) -> list[SemanticNote]:
        data = self._load(session_id)
        items = data.get("items") or []
        notes = [SemanticNote.model_validate(i) for i in items if isinstance(i, dict)]
        return sorted(notes, key=lambda n: n.created_at, reverse=True)[:limit]

    def add_note(
        self,
        session_id: str,
        *,
        statement: str,
        source_entry_ids: list[str] | None = None,
        tags: list[str] | None = None,
        confidence: float = 0.7,
    ) -> SemanticNote:
        note = SemanticNote(
            note_id=str(uuid.uuid4()),
            session_id=session_id,
            statement=statement.strip(),
            source_entry_ids=list(source_entry_ids or []),
            tags=list(tags or []),
            confidence=max(0.0, min(1.0, confidence)),
        )
        data = self._load(session_id)
        items: list[Any] = list(data.get("items") or [])
        # Dedupe identical statements (case-insensitive)
        needle = note.statement.casefold()
        for raw in items:
            if isinstance(raw, dict) and str(raw.get("statement") or "").casefold() == needle:
                return SemanticNote.model_validate(raw)
        items.append(note.model_dump(mode="json"))
        data["items"] = items
        self._save(session_id, data)
        return note


def consolidate_episodic(
    store: SessionStore,
    session_id: str,
    *,
    limit: int = 40,
) -> dict[str, Any]:
    """Turn recent episodic events into durable semantic notes.

    Offline, deterministic consolidation:
    - Tag frequency → pattern notes
    - Outcome clustering (success/failure)
    - Recurring content tokens → insight bullets
    """
    episodic = EpisodicStore(store)
    semantic = SemanticStore(store)
    entries = episodic.list_entries(session_id, limit=limit)
    if not entries:
        return {"created": 0, "notes": [], "scanned": 0}

    tag_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    by_tag_sources: dict[str, list[str]] = {}

    for entry in entries:
        outcome_counts[entry.outcome or "info"] += 1
        for tag in entry.tags:
            tag_counts[tag] += 1
            by_tag_sources.setdefault(tag, []).append(entry.entry_id)
        for tok in _tokens(entry.content):
            token_counts[tok] += 1

    created: list[SemanticNote] = []

    for tag, count in tag_counts.most_common(12):
        if count < 1 or tag in {"lifecycle"}:
            continue
        statement = f"Recurring operational pattern: '{tag}' appeared in {count} recent events"
        note = semantic.add_note(
            session_id,
            statement=statement,
            source_entry_ids=by_tag_sources.get(tag, [])[:8],
            tags=["consolidated", "tag-pattern", tag],
            confidence=min(0.95, 0.55 + 0.05 * count),
        )
        created.append(note)

    for outcome, count in outcome_counts.items():
        if count < 1 or not outcome:
            continue
        statement = f"Outcome distribution: {count} event(s) ended as '{outcome}'"
        note = semantic.add_note(
            session_id,
            statement=statement,
            source_entry_ids=[e.entry_id for e in entries if e.outcome == outcome][:8],
            tags=["consolidated", "outcome", outcome],
            confidence=min(0.9, 0.5 + 0.05 * count),
        )
        created.append(note)

    # Top content tokens as compound insights
    for tok, count in token_counts.most_common(8):
        if count < 2:
            continue
        statement = f"Compounded signal: term '{tok}' recurred {count} times across episodic memory"
        note = semantic.add_note(
            session_id,
            statement=statement,
            source_entry_ids=[e.entry_id for e in entries if tok in e.content.lower()][:6],
            tags=["consolidated", "compound", tok],
            confidence=min(0.88, 0.5 + 0.04 * count),
        )
        created.append(note)

    # Dedupe list for response (add_note may return existing)
    unique: dict[str, SemanticNote] = {n.note_id: n for n in created}
    return {
        "created": len(unique),
        "scanned": len(entries),
        "notes": [n.model_dump(mode="json") for n in unique.values()],
    }
