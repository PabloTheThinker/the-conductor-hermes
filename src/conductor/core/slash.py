"""Slash handlers for conductor / Crucible workspace and Remnant Protocol."""

from __future__ import annotations

from conductor.core.ethics_slash import handle_ethics_slash, handle_soul_slash
from conductor.core.governance_slash import handle_governance_slash
from conductor.core.memory_slash import handle_memory_slash
from conductor.core.remnant_slash import handle_remnant_slash
from conductor.core.runtime import ConductorRuntime
from conductor.core.track_slash import handle_track_slash
from conductor.session.store import SessionStore

__all__ = [
    "handle_crucible_slash",
    "handle_ethics_slash",
    "handle_governance_slash",
    "handle_memory_slash",
    "handle_remnant_slash",
    "handle_soul_slash",
    "handle_track_slash",
]


def handle_crucible_slash(
    store: SessionStore,
    session_id: str,
    args: list[str],
) -> str:
    conductor = ConductorRuntime(store)
    if not args:
        return conductor.status_text(session_id)

    sub = args[0].lower()
    rest = args[1:]

    if sub == "start":
        objective = " ".join(rest).strip()
        payload = conductor.start_crucible(session_id, objective)
        return (
            f"Crucible workspace opened ({payload['crucible_session_id'][:8]}…)\n"
            f"Objective: {objective or '(open simulation)'}\n"
            f"Capacity: {payload.get('capacity', 32)} deliberate concepts"
        )

    if sub == "status":
        return conductor.status_text(session_id)

    if sub == "post":
        label = " ".join(rest).strip()
        if not label:
            return "Usage: /crucible post <concept label>"
        payload = conductor.post_concept(session_id, label=label, clone_id="prime")
        slots = ", ".join(payload.get("slot_labels") or []) or "(empty)"
        return f"Posted: {label}\nWorkspace: {slots}"

    if sub == "read":
        clone_id = rest[0] if rest else "prime"
        state = conductor.read_workspace(session_id, clone_id)
        if not state.slots:
            return "Workspace empty."
        lines = [f"Workspace (gen {state.generation}):"]
        for concept in state.slots[:12]:
            lines.append(f"  • {concept.label} ({concept.confidence:.2f})")
        return "\n".join(lines)

    if sub == "distill":
        result = conductor.distill(session_id)
        lines = ["Distillation complete."]
        if result.promoted_insights:
            lines.append("Promoted: " + ", ".join(result.promoted_insights))
        if result.quarantined:
            lines.append("Quarantined: " + ", ".join(result.quarantined))
        if not result.promoted_insights and not result.quarantined:
            lines.append("(no concepts met promotion threshold)")
        return "\n".join(lines)

    if sub in {"noesis", "rbmc", "simulate"}:
        objective = " ".join(rest).strip()
        payload = conductor.run_noesis(session_id, objective=objective)
        lines = [
            f"Noesis RBMC complete — objective: {payload.get('objective', '')}",
            f"Clones: {', '.join(payload.get('clone_ids') or []) or '(none)'}",
            f"Phases: {', '.join(p.get('phase', '') for p in (payload.get('phases') or []))}",
        ]
        distilled = payload.get("distilled") or {}
        promoted = distilled.get("promoted_insights") or []
        if promoted:
            lines.append("Promoted: " + ", ".join(promoted[:8]))
        if payload.get("pocket_path"):
            lines.append(f"Pocket: {payload['pocket_path']}")
        return "\n".join(lines)

    if sub in {"max", "max_effort", "effort"}:
        decision = " ".join(rest).strip()
        if not decision:
            return "Usage: /crucible max_effort <decision>"
        payload = conductor.run_max_effort(session_id, decision=decision)
        lines = [
            f"Max Effort complete — {payload.get('decision', '')}",
            f"Next step (24–48h): {payload.get('next_step', '')}",
            f"Owner: {payload.get('owner', '')}",
            f"Done when: {payload.get('success_criteria', '')}",
        ]
        if payload.get("pocket_path"):
            lines.append(f"Pocket: {payload['pocket_path']}")
        return "\n".join(lines)

    if sub == "pocket":
        from conductor.crucible.pocket import pocket_status

        cid = conductor.active_crucible_id(session_id)
        if not cid:
            return "No active pocket dimension. /crucible start <objective> or /crucible noesis"
        st = pocket_status(cid)
        return (
            f"Pocket dimension: {st['path']}\n"
            f"Workspace snapshots: {st['workspace_files']}\n"
            f"Clone notes: {st['clone_notes']}\n"
            f"Distill artifacts: {st['distill_files']}"
        )

    if sub == "clone":
        if len(rest) < 2:
            return "Usage: /crucible clone <id> <birth moment label>"
        clone_id = rest[0]
        birth = " ".join(rest[1:])
        conductor.register_clone(
            session_id,
            clone_id=clone_id,
            birth_moment_label=birth,
            snapshot_summary=f"Slash-registered clone for {birth}",
        )
        return f"Clone registered: {clone_id} — {birth}"

    if sub == "fork":
        if len(rest) < 2:
            return "Usage: /crucible fork <clone_id> <birth moment label>"
        clone_id = rest[0]
        birth = " ".join(rest[1:])
        payload = conductor.fork_clone_from_snapshot(
            session_id, clone_id=clone_id, birth_moment_label=birth
        )
        return (
            f"Clone forked from snapshot: {clone_id}\n"
            f"Summary: {payload.get('snapshot_summary', '')}\n"
            f"Episodic in snapshot: {payload.get('episodic_in_snapshot', 0)}"
        )

    return (
        "Usage: /crucible [start|status|post|read|distill|clone|fork|noesis|max_effort|pocket]\n"
        "  /crucible start [objective]\n"
        "  /crucible noesis [objective]     — RBMC pocket simulation + distill\n"
        "  /crucible max_effort <decision>  — Four Voices deliberation\n"
        "  /crucible pocket                 — filesystem pocket status\n"
        "  /crucible post <label>\n"
        "  /crucible read [clone_id]\n"
        "  /crucible distill\n"
        "  /crucible clone <id> <birth moment>\n"
        "  /crucible fork <id> <birth moment>"
    )
