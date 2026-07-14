"""Slash handlers for /remnant conductor commands."""

from __future__ import annotations

from conductor.core.runtime import ConductorRuntime
from conductor.session.store import SessionStore


def handle_remnant_slash(
    store: SessionStore,
    session_id: str,
    args: list[str],
) -> str:
    conductor = ConductorRuntime(store)
    if not args:
        active = conductor.list_remnants(session_id, active_only=True)
        if not active:
            return "No active remnants. Use /remnant spawn <objective>"
        lines = [f"Active remnants: {len(active)}"]
        for rem in active:
            rid = str(rem.get("remnant_id", ""))
            short = rid[:8]
            obj = str(rem.get("task_objective", ""))
            status = str(rem.get("status", ""))
            lines.append(f"  • {short} ({rid}) [{status}] {obj}")
        return "\n".join(lines)

    sub = args[0].lower()
    rest = args[1:]

    if sub in {"fanout", "parallel"}:
        text = " ".join(rest).strip()
        if "||" in text:
            objectives = [p.strip() for p in text.split("||") if p.strip()]
        else:
            objectives = [p.strip() for p in rest if p.strip()]
        if len(objectives) < 2:
            return "Usage: /remnant fanout <obj1> || <obj2>  (or two+ args)"
        payload = conductor.fanout_remnants(session_id, objectives=objectives)
        lines = [f"Fanout spawned {payload.get('count')} remnants:"]
        for rem in payload.get("remnants") or []:
            rid = str(rem.get("remnant_id", ""))
            lines.append(f"  • {rid[:8]} — {rem.get('objective', '')}")
        return "\n".join(lines)

    if sub == "spawn":
        objective = " ".join(rest).strip()
        if not objective:
            return "Usage: /remnant spawn <objective> [strategy]"
        strategy = ""
        if " --strategy " in f" {objective} ":
            parts = objective.split(" --strategy ", 1)
            objective = parts[0].strip()
            strategy = parts[1].strip()
        payload = conductor.spawn_remnant(session_id, objective=objective, strategy=strategy)
        rid = str(payload["remnant_id"])
        return (
            f"Remnant spawned: {rid}\n"
            f"Short id: {rid[:8]} (usable for heartbeat/merge)\n"
            f"Objective: {objective}\n"
            f"Snapshot: {payload.get('snapshot_id', '')}\n"
            f"Track: {payload.get('track_id', '')}"
        )

    if sub == "heartbeat":
        if len(rest) < 2:
            return "Usage: /remnant heartbeat <remnant_id> <subtask> [progress%]"
        remnant_id = rest[0]
        progress = 0.0
        subtask_parts = rest[1:]
        if subtask_parts and subtask_parts[-1].rstrip("%").replace(".", "", 1).isdigit():
            progress = float(subtask_parts[-1].rstrip("%"))
            subtask_parts = subtask_parts[:-1]
        subtask = " ".join(subtask_parts).strip()
        payload = conductor.record_remnant_heartbeat(
            session_id,
            remnant_id=remnant_id,
            current_subtask=subtask,
            progress_percent=progress,
            new_insights=[subtask] if subtask else [],
        )
        resolved = str(payload.get("remnant_id", remnant_id))
        return f"Heartbeat recorded for {resolved[:8]} ({resolved}) — {payload['progress_percent']}%"

    if sub == "merge":
        remnant_ids = rest if rest else None
        # Prefer tier1; on divergence fall through to reflective
        try:
            payload = conductor.merge_remnants_tier1(session_id, remnant_ids=remnant_ids)
            tier = "Tier 1"
        except ValueError as exc:
            if "divergence" not in str(exc).lower():
                raise
            payload = conductor.merge_remnants_reflective(session_id, remnant_ids=remnant_ids)
            tier = "Tier 2 reflective"
        insights = ", ".join(payload.get("merged_insights") or []) or "(none)"
        return (
            f"{tier} merge complete — {len(payload.get('remnant_ids') or [])} remnant(s)\n"
            f"Insights: {insights}"
        )

    if sub in {"merge_reflective", "reflective"}:
        remnant_ids = rest if rest else None
        payload = conductor.merge_remnants_reflective(session_id, remnant_ids=remnant_ids)
        insights = ", ".join(payload.get("merged_insights") or []) or "(none)"
        return (
            f"Tier 2 reflective merge complete — "
            f"{len(payload.get('remnant_ids') or [])} remnant(s)\n"
            f"Insights: {insights}\n"
            f"Notes: {payload.get('governance_notes', '')}"
        )

    if sub in {"merge_deep", "deep"}:
        remnant_ids = rest if rest else None
        payload = conductor.merge_remnants_deep(
            session_id,
            remnant_ids=remnant_ids,
            human_acknowledged=True,
            run_rbmc=True,
        )
        insights = ", ".join(payload.get("merged_insights") or []) or "(none)"
        return (
            f"Tier 3 deep merge complete — "
            f"{len(payload.get('remnant_ids') or [])} remnant(s)\n"
            f"Insights: {insights}\n"
            f"Notes: {payload.get('governance_notes', '')}"
        )

    if sub == "status":
        return conductor.format_json(conductor.status(session_id))

    return (
        "Usage: /remnant [spawn|fanout|heartbeat|merge|merge_reflective|merge_deep|status]\n"
        "  /remnant spawn <objective>\n"
        "  /remnant fanout <obj1> || <obj2>\n"
        "  /remnant heartbeat <id> <subtask> [progress%]\n"
        "  /remnant merge [remnant_id ...]           — tier1, auto-escalates on divergence\n"
        "  /remnant merge_reflective [remnant_id …]  — tier2 high-divergence\n"
        "  /remnant merge_deep [remnant_id …]         — tier3 + RBMC/Crucible\n"
        "  /remnant status"
    )
