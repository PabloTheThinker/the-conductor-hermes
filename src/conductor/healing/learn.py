"""Learn from scars — episodic + learned seals in Memory Fabric."""

from __future__ import annotations

from typing import Any

from conductor.healing.models import Scar
from conductor.memory.episodic import EpisodicStore
from conductor.memory.semantic import SemanticStore
from conductor.session.store import SessionStore


def record_scar_learning(
    store: SessionStore,
    scar: Scar,
    *,
    healed: bool,
) -> dict[str, Any]:
    """Write episodic scar event and optional learned seal (semantic)."""
    out: dict[str, Any] = {"episodic": False, "seal": False}
    epi = EpisodicStore(store)
    outcome = "success" if healed else "failure"
    emotion = "satisfaction" if healed else "concern"
    intensity = 0.45 if healed else 0.65
    entry = epi.write(
        scar.session_id,
        content=f"Scar {scar.kind}: {scar.summary}",
        context=scar.error[:500] if scar.error else scar.forward_step,
        outcome=outcome,
        emotion_primary=emotion,
        emotion_intensity=intensity,
        tags=["scar", "heal", "integrity", scar.kind, f"status:{scar.status}"],
    )
    out["episodic"] = True
    out["entry_id"] = entry.entry_id

    if healed and scar.seal:
        note = SemanticStore(store).add_note(
            scar.session_id,
            statement=scar.seal,
            source_entry_ids=[entry.entry_id],
            tags=["seal", "heal", "integrity", scar.kind],
            confidence=0.75,
        )
        out["seal"] = True
        out["note_id"] = note.note_id
        # Cross-session antibody index
        try:
            from conductor.memory.global_seals import add_global_seal

            gs = add_global_seal(
                scar.seal,
                kind=scar.kind,
                source_session=scar.session_id,
                confidence=0.75,
            )
            out["global_seal_id"] = gs.seal_id
        except Exception:  # noqa: BLE001
            pass
    return out
