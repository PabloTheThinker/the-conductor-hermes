"""Slash handlers for /governance."""

from __future__ import annotations

from conductor.core.runtime import ConductorRuntime
from conductor.governance.constitutional import CONSTITUTIONAL_RULES, constitutional_rule_ids
from conductor.session.store import SessionStore


def handle_governance_slash(store: SessionStore, session_id: str, args: list[str]) -> str:
    conductor = ConductorRuntime(store)

    if not args:
        records = conductor.list_audit_records(session_id, limit=5)
        summary = conductor.audit_summary(session_id)
        lines = [
            "Governance layer: Tier 0 constitutional + Tier 1 policy + ethics checklist",
            f"Constitutional rules: {len(CONSTITUTIONAL_RULES)} ({', '.join(constitutional_rule_ids())})",
            f"Recent audits listed: {len(records)} · trail total: {summary.get('total', 0)}",
        ]
        lines.append("")
        lines.append("Usage: /governance status|audit|summary|check <action> <text>")
        return "\n".join(lines)

    sub = args[0].lower()
    rest = args[1:]

    if sub == "status":
        soul = conductor.soul_status()
        records = conductor.list_audit_records(session_id, limit=3)
        summary = conductor.audit_summary(session_id)
        lines = [
            f"SOUL: {soul['tagline']}",
            f"SOUL integrity: {'ok' if soul['integrity_ok'] else 'failed'}",
            f"Constitutional rules: {len(CONSTITUTIONAL_RULES)}",
            (
                f"Audit trail: total={summary.get('total', 0)} "
                f"allowed={summary.get('allowed', 0)} "
                f"blocked={summary.get('blocked', 0)} "
                f"escalated={summary.get('escalated', 0)}"
            ),
        ]
        if records:
            lines.append("Latest:")
            for rec in records:
                lines.append(f"  • {rec.action_type} → {rec.outcome}")
        return "\n".join(lines)

    if sub == "summary":
        return conductor.format_json(conductor.audit_summary(session_id))

    if sub == "audit":
        records = conductor.list_audit_records(session_id, limit=15)
        if not records:
            return "No audit records."
        return conductor.format_json([r.model_dump(mode="json") for r in records])

    if sub == "check":
        if len(rest) < 2:
            return "Usage: /governance check <action_type> <description>"
        action_type = rest[0]
        description = " ".join(rest[1:])
        gate = conductor.evaluate_governance(action_type, {"description": description})
        conductor.record_governance_gate(
            session_id, action_type=action_type, context={"description": description}, gate=gate
        )
        lines = [f"Tier: {gate.tier}", f"Allowed: {gate.allowed}", gate.summary]
        matched = (gate.context or {}).get("matched_constitutional_rules") or []
        if matched:
            lines.append(f"Matched rules: {', '.join(matched)}")
        if gate.ethics:
            for point in gate.ethics.points:
                if point.status != "clear":
                    lines.append(f"  • {point.point_id}: {point.status}")
        return "\n".join(lines)

    return "Usage: /governance [status|audit|summary|check]"
