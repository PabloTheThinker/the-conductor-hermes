"""Live memory injection — scars, seals, and recent episodes every turn.

Not a dead store: builds a compact block for system/pre_llm context so the
engine actually *uses* Memory Fabric on each turn.
"""

from __future__ import annotations

from conductor.healing.store import ScarStore
from conductor.memory.episodic import EpisodicStore
from conductor.memory.semantic import SemanticStore
from conductor.session.store import SessionStore


def build_live_memory_block(
    store: SessionStore,
    session_id: str,
    *,
    max_scars: int = 5,
    max_seals: int = 6,
    max_episodes: int = 4,
    max_chars: int = 1800,
) -> str:
    """Compact memory block for prompt injection (deterministic, no LLM)."""
    if not session_id:
        return ""

    parts: list[str] = ["## Conductor live memory (this session — use it)"]

    # Open / chronic scars first (actionable)
    scars = ScarStore(store).list_scars(session_id, limit=40)
    active = [s for s in scars if s.status in {"open", "healing", "chronic", "escalated"}]
    healed = [s for s in scars if s.status == "healed"][:2]
    if active:
        parts.append("### Active scars (do not ignore)")
        for s in active[:max_scars]:
            line = f"- [{s.status}/{s.kind}] {s.summary[:120]}"
            if s.forward_step:
                line += f" | advance: {s.forward_step[:100]}"
            parts.append(line)
    if healed:
        parts.append("### Recent healed (pattern works)")
        for s in healed:
            parts.append(f"- {s.kind}: {s.seal[:140] if s.seal else s.summary[:100]}")

    # Learned seals (semantic + cross-session global)
    try:
        notes = SemanticStore(store).list_notes(session_id, limit=30)
        seals = [n for n in notes if "seal" in (n.tags or []) or "antibody" in (n.tags or [])]
        if not seals:
            seals = notes[:max_seals]
        else:
            seals = seals[:max_seals]
        if seals:
            parts.append("### Learned seals (prefer these remediations)")
            for n in seals:
                parts.append(f"- {n.statement[:160]}")
    except Exception:  # noqa: BLE001
        pass
    try:
        from conductor.memory.global_seals import format_global_seals_block

        gblock = format_global_seals_block(max_seals=max_seals)
        if gblock:
            parts.append(gblock)
    except Exception:  # noqa: BLE001
        pass

    # Recent episodic
    try:
        eps = EpisodicStore(store).list_entries(session_id, limit=max_episodes)
        if eps:
            parts.append("### Recent episodes")
            for e in eps:
                parts.append(f"- ({e.outcome}) {e.content[:120]}")
    except Exception:  # noqa: BLE001
        pass

    if len(parts) <= 1:
        return ""

    block = "\n".join(parts)
    if len(block) > max_chars:
        block = block[: max_chars - 3] + "..."
    return block


def pre_llm_context_payload(
    store: SessionStore | None,
    session_id: str,
) -> dict[str, str] | None:
    """Hermes pre_llm_call shape: {\"context\": \"...\"} or None."""
    if not store or not session_id:
        return None
    block = build_live_memory_block(store, session_id)
    if not block.strip():
        return None
    return {"context": block}
