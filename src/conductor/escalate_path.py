"""Escalate path — turn loop escalate into real Max Effort structure + next steps."""

from __future__ import annotations

from typing import Any

from conductor.healing.models import Scar
from conductor.loop_policy import LoopDecision
from conductor.noesis.max_effort import (
    build_deterministic_voices,
    parse_action_fields,
    validate_action_input,
)
from conductor.session.store import SessionStore


def build_escalate_package(
    store: SessionStore | None,
    session_id: str,
    decision: LoopDecision,
    *,
    scar: Scar | None = None,
) -> dict[str, Any]:
    """Deterministic Max Effort package (no LLM) for escalate decisions."""
    topic = decision.reason
    if scar:
        topic = f"{scar.kind}: {scar.summary}" if scar.summary else scar.kind
    decision_text = (
        f"Escalate integrity cascade — {decision.reason}. "
        f"Do not re-run the same failing tool/path."
    )
    voices = build_deterministic_voices(decision_text)
    action_text = voices.get("Voice of Action") or (
        f"Within 48h, owner=operator+conductor must take the smallest verifiable step on '{topic[:40]}'. "
        "Done = alternate path works or evidence logged."
    )
    step = parse_action_fields(action_text)
    ok, rej = validate_action_input(
        step.action,
        owner=step.owner,
        success_criteria=step.success_criteria,
        deadline=step.deadline,
    )
    tradeoffs = [
        "Blind retry wastes attention budget and deepens scars",
        "Deep reconstitution costs more but breaks chronic loops",
        "Operator authority may be required for spine/safety holds",
    ]
    verification = (
        "Judgment: run a different verification command or restore imprint; "
        "log shell_verify / write evidence; re-check heal_status open scars → 0 for this kind."
    )
    crucible_hint = (
        "Invoke: /crucible max_effort  or tool crucible_workspace action=max_effort "
        f"decision={decision_text[:120]!r}"
    )
    package = {
        "action": "escalate",
        "reason": decision.reason,
        "chronic_kinds": list(decision.chronic_kinds),
        "Decision": decision_text,
        "voices": voices,
        "Actions": [step.to_dict()],
        "Tradeoffs": tradeoffs,
        "Verification": verification,
        "action_valid": ok,
        "action_rejection": rej if not ok else "",
        "crucible_hint": crucible_hint,
        "next_step": step.action,
        "forward_step": decision.escalate_hint or step.action,
    }
    if store and session_id:
        try:
            store.set_meta(session_id, "last_escalate_package", package)
        except Exception:  # noqa: BLE001
            pass
    return package


def escalate_package_suffix(package: dict[str, Any]) -> str:
    """Append structured Max Effort sections to tool/heal output."""
    lines = [
        "",
        "---",
        "[Escalate → Max Effort package]",
        f"Decision: {package.get('Decision', '')}",
        "Actions:",
    ]
    for a in package.get("Actions") or []:
        if isinstance(a, dict):
            lines.append(
                f"  - owner={a.get('owner')} deadline={a.get('deadline')}: {a.get('action')}"
            )
        else:
            lines.append(f"  - {a}")
    lines.append("Tradeoffs:")
    for t in package.get("Tradeoffs") or []:
        lines.append(f"  - {t}")
    lines.append(f"Verification: {package.get('Verification', '')}")
    if package.get("crucible_hint"):
        lines.append(f"Next: {package['crucible_hint']}")
    return "\n".join(lines)
