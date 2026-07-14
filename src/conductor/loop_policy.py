"""Loop engineering — stop conditions, chronic scars, escalate paths.

reason → act → verify → adjust, with clear stop and escalation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from conductor.healing.models import Scar
from conductor.healing.store import ScarStore
from conductor.session.store import SessionStore

# Defaults (overridable via env later)
CHRONIC_KIND_THRESHOLD = 3  # same kind open/healing/chronic within window
CHRONIC_WINDOW = 40  # recent scars scanned
MAX_OPEN_SCARS_BEFORE_STOP = 8
SEVERITY_ESCALATE = 4


@dataclass
class LoopDecision:
    """What the loop should do next."""

    action: str  # continue | stop | escalate
    reason: str
    chronic_kinds: list[str]
    open_scars: int
    escalate_hint: str = ""
    # Clarifies for agents: stop ≠ abandon mission
    scope: str = ""  # e.g. "this_failure_class" | "mission_ok_to_continue_elsewhere"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "chronic_kinds": list(self.chronic_kinds),
            "open_scars": self.open_scars,
            "escalate_hint": self.escalate_hint,
            "scope": self.scope,
        }


def count_kind_recent(
    scars: list[Scar],
    *,
    kind: str,
    window: int = CHRONIC_WINDOW,
) -> int:
    recent = scars[:window]
    return sum(
        1
        for s in recent
        if s.kind == kind and s.status in {"open", "healing", "chronic", "escalated"}
    )


def detect_chronic_kinds(
    store: SessionStore,
    session_id: str,
    *,
    threshold: int = CHRONIC_KIND_THRESHOLD,
    window: int = CHRONIC_WINDOW,
) -> list[str]:
    """Return wound kinds that have repeated enough to be chronic."""
    scars = ScarStore(store).list_scars(session_id, limit=window)
    counts: Counter[str] = Counter()
    for s in scars:
        if s.status in {"open", "healing", "chronic", "escalated"}:
            counts[s.kind] += 1
    return sorted(k for k, n in counts.items() if n >= threshold)


def mark_chronic_scars(
    store: SessionStore,
    session_id: str,
    *,
    kinds: list[str] | None = None,
    threshold: int = CHRONIC_KIND_THRESHOLD,
) -> list[Scar]:
    """Flip matching open/healing scars to chronic; return updated scars."""
    kinds = kinds or detect_chronic_kinds(store, session_id, threshold=threshold)
    if not kinds:
        return []
    ss = ScarStore(store)
    updated: list[Scar] = []
    for scar in ss.list_scars(session_id, limit=CHRONIC_WINDOW):
        if scar.kind in kinds and scar.status in {"open", "healing"}:
            scar.status = "chronic"
            scar.tier = "deep"
            if not scar.forward_step or "escalat" not in scar.forward_step.lower():
                scar.forward_step = (
                    f"CHRONIC {scar.kind}: stop blind retries. "
                    "Run Max Effort / deep reconstitution or escalate to operator."
                )
            ss.upsert(scar)
            updated.append(scar)
    return updated


def evaluate_loop(
    store: SessionStore,
    session_id: str,
    *,
    last_scar: Scar | None = None,
    thrash: bool = False,
) -> LoopDecision:
    """Decide continue / stop / escalate after an act or wound.

    Stop = do not auto-retry same class of damage.
    Escalate = deep reconstitution / Max Effort / human.
    """
    ss = ScarStore(store)
    open_n = ss.open_count(session_id)
    chronic = detect_chronic_kinds(store, session_id)
    if chronic:
        mark_chronic_scars(store, session_id, kinds=chronic)
        return LoopDecision(
            action="escalate",
            reason=f"chronic wound kinds: {', '.join(chronic)}",
            chronic_kinds=chronic,
            open_scars=open_n,
            escalate_hint=(
                "NOT abort-mission. Stop this wound class only. "
                "Use Max Effort (/crucible max_effort) or a different approach; "
                "do not re-run the same failing shell/path."
            ),
            scope="this_failure_class",
        )

    # Spine/safety already escalated: stop auto-retry (before severity re-escalate)
    if last_scar and last_scar.status == "escalated":
        return LoopDecision(
            action="stop",
            reason="spine/safety escalation — do not auto-continue destructive path",
            chronic_kinds=[],
            open_scars=open_n,
            escalate_hint=(
                last_scar.forward_step
                or "Choose a non-destructive alternate path. Mission may continue elsewhere."
            ),
            scope="this_failure_class",
        )

    if last_scar and last_scar.severity >= SEVERITY_ESCALATE and last_scar.status != "healed":
        return LoopDecision(
            action="escalate",
            reason=f"high severity scar ({last_scar.severity}) kind={last_scar.kind}",
            chronic_kinds=[],
            open_scars=open_n,
            escalate_hint=(
                "Deep reconstitution or human ack for this wound — "
                "other workstreams may still proceed."
            ),
            scope="this_failure_class",
        )

    if open_n >= MAX_OPEN_SCARS_BEFORE_STOP:
        return LoopDecision(
            action="stop",
            reason=f"too many open scars ({open_n}) — pause thrash on wounds",
            chronic_kinds=[],
            open_scars=open_n,
            escalate_hint=(
                "Triage via heal_status; fix one wound class at a time. "
                "Do not stop the whole mission — stop only blind multi-wound retries."
            ),
            scope="this_failure_class",
        )

    if thrash:
        return LoopDecision(
            action="stop",
            reason="thrash signal (identical tool+args repeated)",
            chronic_kinds=[],
            open_scars=open_n,
            escalate_hint=(
                "Change args/tool/scope (new fingerprint). "
                "NOT 'stop everything' — continue the goal with a different action."
            ),
            scope="this_failure_class",
        )

    return LoopDecision(
        action="continue",
        reason="no stop/escalate condition",
        chronic_kinds=[],
        open_scars=open_n,
        scope="mission",
    )


def loop_decision_suffix(decision: LoopDecision) -> str:
    """Append to tool/model output when stop or escalate."""
    if decision.action == "continue":
        return ""
    lines = [
        "",
        "---",
        f"[Loop policy] action={decision.action} — {decision.reason}",
    ]
    if decision.scope:
        lines.append(
            f"Scope: {decision.scope} "
            "(stop/escalate applies to this failure class, not the whole mission)"
        )
    if decision.escalate_hint:
        lines.append(f"Next: {decision.escalate_hint}")
    return "\n".join(lines)
