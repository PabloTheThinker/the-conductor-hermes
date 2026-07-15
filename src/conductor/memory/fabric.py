"""Memory Fabric facade — four layers + global seals in one status surface."""

from __future__ import annotations

from typing import Any

from conductor.memory.episodic import EpisodicStore
from conductor.memory.global_seals import list_global_seals
from conductor.memory.procedural import ProceduralStore
from conductor.memory.semantic import SemanticStore
from conductor.session.store import SessionStore
from conductor.skills.loader import skills_index


class MemoryFabric:
    """Unified view of episodic · semantic · procedural · track-linked · seals."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self.episodic = EpisodicStore(store)
        self.semantic = SemanticStore(store)
        self.procedural = ProceduralStore(store)

    def status(self, session_id: str = "") -> dict[str, Any]:
        from conductor.memory.episodic import EPISODIC_MAX_ITEMS

        skills = skills_index()
        seals = list_global_seals(limit=50)
        out: dict[str, Any] = {
            "layers": {
                "episodic": "session events with valence",
                "semantic": "distilled notes / seals",
                "procedural": "learned how-to + skill pack",
                "track_linked": "tracks + episodic tags",
            },
            "global_seals": len(seals),
            "global_seal_samples": [
                {"kind": s.kind, "hits": s.hits, "statement": s.statement[:100]}
                for s in seals[:5]
            ],
            "bundled_skills": len(skills),
            "skill_names": [s.name for s in skills[:20]],
            "episodic_max_items": EPISODIC_MAX_ITEMS,
        }
        if session_id:
            eps = self.episodic.list_entries(session_id, limit=EPISODIC_MAX_ITEMS)
            failures = sum(
                1
                for e in eps
                if (e.outcome or "").lower() in {"failure", "fail", "error", "blocked"}
            )
            session: dict[str, Any] = {
                "episodic": len(eps),
                "semantic": len(self.semantic.list_notes(session_id, limit=1000)),
                "procedural": len(self.procedural.list_entries(session_id, limit=500)),
                "episodic_failures": failures,
            }
            try:
                from conductor.tracks.store import TrackStore

                session["tracks"] = len(TrackStore(self.store).list_tracks(session_id))
            except Exception:  # noqa: BLE001
                session["tracks"] = 0
            out["session"] = session
            # Prefer valence-ranked inject selection for "what matters"
            recent = self.episodic.select_for_inject(session_id, limit=3)
            out["recent_episodic"] = [
                {
                    "id": e.entry_id[:8],
                    "content": e.content[:80],
                    "outcome": e.outcome,
                    "emotion": e.emotional_valence.primary,
                    "intensity": e.emotional_valence.intensity,
                }
                for e in recent
            ]
        return out

    def write_episode(
        self,
        session_id: str,
        *,
        content: str,
        context: str = "",
        outcome: str = "info",
        emotion_primary: str = "neutral",
        emotion_intensity: float = 0.5,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        entry = self.episodic.write(
            session_id,
            content=content,
            context=context,
            outcome=outcome,
            emotion_primary=emotion_primary,
            emotion_intensity=emotion_intensity,
            tags=tags,
        )
        return entry.model_dump(mode="json")

    def add_semantic(
        self,
        session_id: str,
        *,
        statement: str,
        tags: list[str] | None = None,
        confidence: float = 0.7,
    ) -> dict[str, Any]:
        note = self.semantic.add_note(
            session_id,
            statement=statement,
            tags=tags,
            confidence=confidence,
        )
        return note.model_dump(mode="json")

    def add_procedure(
        self,
        session_id: str,
        *,
        name: str,
        steps: list[str] | None = None,
        when_to_use: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        entry = self.procedural.add(
            session_id,
            name=name,
            steps=steps,
            when_to_use=when_to_use,
            tags=tags,
        )
        return entry.model_dump(mode="json")
