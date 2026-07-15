"""Durable scar ledger on session meta."""

from __future__ import annotations

from typing import Any

from conductor.healing.models import Scar, _utcnow
from conductor.session.store import SessionStore

SCARS_META_KEY = "healing_scars"
_MAX_SCARS = 200


class ScarStore:
    def __init__(self, store: SessionStore) -> None:
        self.store = store

    def _load(self, session_id: str) -> list[dict[str, Any]]:
        raw = self.store.get_meta(session_id, SCARS_META_KEY, default={})
        if isinstance(raw, dict):
            items = raw.get("items") or []
            return [i for i in items if isinstance(i, dict)]
        if isinstance(raw, list):
            return [i for i in raw if isinstance(i, dict)]
        return []

    def _save(self, session_id: str, items: list[dict[str, Any]]) -> None:
        # keep newest tail
        trimmed = items[-_MAX_SCARS:]
        self.store.set_meta(session_id, SCARS_META_KEY, {"items": trimmed})

    def list_scars(self, session_id: str, *, limit: int = 50, status: str | None = None) -> list[Scar]:
        rows = [Scar.from_dict(i) for i in self._load(session_id)]
        rows.sort(key=lambda s: s.updated_at, reverse=True)
        if status:
            rows = [s for s in rows if s.status == status]
        return rows[:limit]

    def get(self, session_id: str, scar_id: str) -> Scar | None:
        for s in self.list_scars(session_id, limit=_MAX_SCARS):
            if s.scar_id == scar_id or s.scar_id.startswith(scar_id):
                return s
        return None

    def find_coalesce_target(
        self,
        session_id: str,
        *,
        kind: str,
        path: str = "",
        source_tool: str = "",
    ) -> Scar | None:
        """Reuse an active scar for the same wound class instead of minting UUIDs.

        Preference: same kind+path → same kind+tool → most recent same kind.
        Healed scars are not reused (a new failure after heal is a new event).
        """
        active = {"open", "healing", "chronic", "escalated"}
        kind_n = (kind or "").strip()
        if not kind_n:
            return None
        path_n = (path or "").strip()
        tool_n = (source_tool or "").strip()
        candidates = [
            s
            for s in self.list_scars(session_id, limit=_MAX_SCARS)
            if s.kind == kind_n and s.status in active
        ]
        if not candidates:
            return None
        if path_n:
            for s in candidates:
                if (s.path or "").strip() == path_n:
                    return s
        if tool_n:
            for s in candidates:
                if (s.source_tool or "").strip() == tool_n:
                    return s
        # Same kind flood (false-positive or chronic): one ledger row.
        return candidates[0]

    def upsert(self, scar: Scar) -> Scar:
        scar.updated_at = _utcnow()
        items = self._load(scar.session_id)
        found = False
        for i, row in enumerate(items):
            if row.get("scar_id") == scar.scar_id:
                items[i] = scar.to_dict()
                found = True
                break
        if not found:
            items.append(scar.to_dict())
        self._save(scar.session_id, items)
        return scar

    def open_count(self, session_id: str) -> int:
        return len(self.list_scars(session_id, limit=_MAX_SCARS, status="open")) + len(
            self.list_scars(session_id, limit=_MAX_SCARS, status="healing")
        )
