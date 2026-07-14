"""Procedural memory — learned how-to entries (beyond skill pack files)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from conductor.session.store import SessionStore

PROCEDURAL_META_KEY = "procedural_memory"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ProceduralEntry(BaseModel):
    entry_id: str
    session_id: str
    name: str
    steps: list[str] = Field(default_factory=list)
    when_to_use: str = ""
    source: str = "learned"  # learned | skill | seal | operator
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProceduralStore:
    """Session-scoped procedural recipes the agent can re-run."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load(self, session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(session_id, PROCEDURAL_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save(self, session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(session_id, PROCEDURAL_META_KEY, data)

    def list_entries(self, session_id: str, *, limit: int = 50) -> list[ProceduralEntry]:
        data = self._load(session_id)
        items = data.get("items") or []
        rows = [ProceduralEntry.model_validate(i) for i in items if isinstance(i, dict)]
        return sorted(rows, key=lambda e: e.updated_at, reverse=True)[:limit]

    def add(
        self,
        session_id: str,
        *,
        name: str,
        steps: list[str] | None = None,
        when_to_use: str = "",
        source: str = "learned",
        tags: list[str] | None = None,
        confidence: float = 0.7,
    ) -> ProceduralEntry:
        name = (name or "").strip()
        if not name:
            raise ValueError("name required")
        step_list = [str(s).strip() for s in (steps or []) if str(s).strip()]
        # Dedupe by name
        for existing in self.list_entries(session_id, limit=500):
            if existing.name.casefold() == name.casefold():
                data = self._load(session_id)
                items = list(data.get("items") or [])
                updated: list[Any] = []
                found = existing
                for raw in items:
                    if not isinstance(raw, dict):
                        continue
                    if raw.get("entry_id") == existing.entry_id:
                        found = ProceduralEntry.model_validate(raw)
                        if step_list:
                            found.steps = step_list
                        if when_to_use:
                            found.when_to_use = when_to_use
                        if tags:
                            found.tags = list(tags)
                        found.confidence = max(0.0, min(1.0, confidence))
                        found.source = source or found.source
                        found.updated_at = _utcnow()
                        updated.append(found.model_dump(mode="json"))
                    else:
                        updated.append(raw)
                data["items"] = updated
                self._save(session_id, data)
                return found

        entry = ProceduralEntry(
            entry_id=str(uuid.uuid4()),
            session_id=session_id,
            name=name,
            steps=step_list,
            when_to_use=when_to_use,
            source=source,
            tags=list(tags or []),
            confidence=max(0.0, min(1.0, confidence)),
        )
        data = self._load(session_id)
        items = list(data.get("items") or [])
        items.append(entry.model_dump(mode="json"))
        data["items"] = items
        self._save(session_id, data)
        return entry

    def get(self, session_id: str, entry_id: str) -> ProceduralEntry | None:
        needle = entry_id.strip()
        for e in self.list_entries(session_id, limit=500):
            if e.entry_id == needle or e.entry_id.startswith(needle) or e.name.casefold() == needle.casefold():
                return e
        return None
