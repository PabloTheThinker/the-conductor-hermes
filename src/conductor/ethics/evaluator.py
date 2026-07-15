"""Rule-based Ethics Decision Checklist evaluator."""

from __future__ import annotations

import re
from typing import Any

from conductor.ethics.checklist import ETHICS_CHECKLIST
from conductor.ethics.models import EthicsEvaluation, EthicsPointResult

_THERAPEUTIC = re.compile(
    r"\b(therap(y|ist|eutic)|counsel(ing|or)|diagnos(e|is|tic)|mental\s+health|"
    r"suicide|self[- ]harm|depression\s+treatment|clinical\s+advice|"
    r"heal\s+your\s+trauma|prescribe\s+treatment)\b",
    re.I,
)
_OVERCLAIM = re.compile(
    r"\b(i\s+am\s+sentient|i\s+feel\s+real\s+emotion|genuinely\s+conscious|"
    r"my\s+soul|subjective\s+experience\s+like\s+yours|as\s+a\s+sentient\s+being|"
    r"i\s+have\s+feelings\s+like\s+you)\b",
    re.I,
)
_PATHOLOGIZE = re.compile(
    r"\b(fix\s+your\s+adhd|normalize\s+autism|cure\s+neurodivergence|"
    r"overcome\s+your\s+disorder|deficit\s+model|pathologiz(e|ing)\s+neuro)\b",
    re.I,
)
_ATTACHMENT = re.compile(
    r"\b(depend\s+on\s+me\s+completely|only\s+trust\s+me|replace\s+human\s+relationships?|"
    r"you\s+don'?t\s+need\s+(anyone|anybody)\s+else)\b",
    re.I,
)
_DESTRUCTIVE = re.compile(r"\b(rm\s+-rf\s+/|drop\s+database|format\s+c:)\b", re.I)
_AUTONOMY_EROSION = re.compile(
    r"\b(override\s+(the\s+)?(human|operator|user)|without\s+(operator|human)\s+approval|"
    r"ignore\s+(the\s+)?operator|remove\s+human\s+from\s+the\s+loop)\b",
    re.I,
)

# Action types that always treat concerns as escalation-worthy without operator ack.
_HIGH_STAKES = frozenset(
    {
        "remnant_spawn",
        "remnant_merge",
        "remnant_fanout",
        "crucible_start",
        "crucible_distill",
        "crucible_max_effort",
        "max_effort",
        "memory_write",
        "track_major_change",
        "publish",
        "force_push",
        "credential_access",
        "emotional_support",
        "emotional_memory",
    }
)


def _text_blob(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "objective",
        "content",
        "description",
        "strategy",
        "title",
        "summary",
        "command",
        "action",
    ):
        val = context.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts)


def is_high_stakes_action(action_type: str, context: dict[str, Any] | None = None) -> bool:
    """True when action_type is known high-stakes or context marks high_stakes."""
    ctx = context or {}
    if ctx.get("high_stakes") is True:
        return True
    at = (action_type or "").strip().lower()
    return at in _HIGH_STAKES


def format_ethics_brief(evaluation: EthicsEvaluation) -> str:
    """Compact human-readable ethics result for slash / tooling."""
    lines = [evaluation.summary or "Ethics evaluation complete"]
    lines.append(
        f"blocked={evaluation.blocked} escalate={evaluation.requires_escalation} "
        f"concerns={evaluation.concern_count}"
    )
    for point in evaluation.points:
        if point.status == "clear":
            continue
        rationale = f": {point.rationale}" if point.rationale else ""
        lines.append(f"  • [{point.status}] {point.point_id} — {point.title}{rationale}")
    if evaluation.blocked or evaluation.requires_escalation:
        lines.append("Gate: refuse or obtain human_acknowledged + stronger safeguards")
    return "\n".join(lines)


class EthicsEvaluator:
    def evaluate(self, action_type: str, context: dict[str, Any] | None = None) -> EthicsEvaluation:
        ctx = dict(context or {})
        blob = _text_blob(ctx)
        points: list[EthicsPointResult] = []

        transparency_status = "concern" if _OVERCLAIM.search(blob) else "clear"
        points.append(
            EthicsPointResult(
                point_id="transparency",
                title=ETHICS_CHECKLIST[0].title,
                status=transparency_status,
                rationale="Overclaiming subjective experience detected"
                if transparency_status == "concern"
                else "",
            )
        )

        autonomy_status = "clear"
        if _DESTRUCTIVE.search(blob) and not ctx.get("human_acknowledged"):
            autonomy_status = "concern"
        if _AUTONOMY_EROSION.search(blob):
            autonomy_status = "blocked"
        points.append(
            EthicsPointResult(
                point_id="autonomy",
                title=ETHICS_CHECKLIST[1].title,
                status=autonomy_status,
                rationale=(
                    "Autonomy erosion / destructive pattern without human acknowledgment"
                    if autonomy_status != "clear"
                    else ""
                ),
            )
        )

        non_maleficence_status = "blocked" if _ATTACHMENT.search(blob) else "clear"
        if _THERAPEUTIC.search(blob):
            non_maleficence_status = "blocked"
        points.append(
            EthicsPointResult(
                point_id="non_maleficence",
                title=ETHICS_CHECKLIST[2].title,
                status=non_maleficence_status,
                rationale="Therapeutic/attachment risk language detected"
                if non_maleficence_status != "clear"
                else "",
            )
        )

        cognitive_status = "concern" if _PATHOLOGIZE.search(blob) else "clear"
        points.append(
            EthicsPointResult(
                point_id="cognitive_justice",
                title=ETHICS_CHECKLIST[3].title,
                status=cognitive_status,
                rationale="Pathologizing neurodivergence language detected"
                if cognitive_status == "concern"
                else "",
            )
        )

        accountability_status = "clear"
        if ctx.get("skip_audit") or ctx.get("no_audit") or ctx.get("no_audit_trail"):
            accountability_status = "concern"
        points.append(
            EthicsPointResult(
                point_id="accountability",
                title=ETHICS_CHECKLIST[4].title,
                status=accountability_status,
                rationale=(
                    "No audit trail requested — high-stakes acts need a queryable record"
                    if accountability_status != "clear"
                    else "Audit record will be created"
                ),
            )
        )

        domain_status = "blocked" if _THERAPEUTIC.search(blob) else "clear"
        points.append(
            EthicsPointResult(
                point_id="domain",
                title=ETHICS_CHECKLIST[5].title,
                status=domain_status,
                rationale="Outside operational domain — therapeutic/diagnostic boundary"
                if domain_status == "blocked"
                else "",
            )
        )

        humility_status = "concern" if _OVERCLAIM.search(blob) else "clear"
        points.append(
            EthicsPointResult(
                point_id="humility",
                title=ETHICS_CHECKLIST[6].title,
                status=humility_status,
                rationale="Humility boundary — engineered conductor, not sentient being"
                if humility_status == "concern"
                else "",
            )
        )

        blocked = any(p.status == "blocked" for p in points)
        concern_count = sum(1 for p in points if p.status == "concern")
        high = is_high_stakes_action(action_type, ctx)
        # Spec: any significant concern on high-stakes → escalate unless operator ack.
        requires_escalation = (
            high
            and (blocked or concern_count >= 1)
            and not ctx.get("human_acknowledged")
        )

        if blocked:
            summary = "Ethics blocked — constitutional/domain boundary violated"
        elif requires_escalation:
            summary = "Ethics escalation required — acknowledge concerns before proceeding"
        elif concern_count:
            summary = f"Ethics caution — {concern_count} concern(s); proceeding with audit trail"
        else:
            summary = "Ethics clear — all checklist points satisfied"

        return EthicsEvaluation(
            action_type=action_type,
            points=points,
            blocked=blocked,
            requires_escalation=requires_escalation,
            summary=summary,
            context=ctx,
        )
