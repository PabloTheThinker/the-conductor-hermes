"""Slash handlers for /ethics and /soul."""

from __future__ import annotations

from conductor.core.runtime import ConductorRuntime
from conductor.ethics.checklist import ETHICS_CHECKLIST
from conductor.ethics.evaluator import EthicsEvaluator
from conductor.session.store import SessionStore
from conductor.soul.identity import load_soul_identity


def handle_ethics_slash(store: SessionStore, session_id: str, args: list[str]) -> str:
    conductor = ConductorRuntime(store)
    evaluator = EthicsEvaluator()

    if not args:
        lines = ["Ethics Decision Checklist (7 points):"]
        for point in ETHICS_CHECKLIST:
            lines.append(f"  {point.point_id}: {point.title}")
        lines.append("")
        lines.append("Usage: /ethics check <action_type> <description>")
        lines.append("       /ethics audit")
        return "\n".join(lines)

    sub = args[0].lower()
    rest = args[1:]

    if sub == "check":
        if len(rest) < 2:
            return "Usage: /ethics check <action_type> <description>"
        action_type = rest[0]
        description = " ".join(rest[1:])
        gate = conductor.evaluate_governance(action_type, {"description": description})
        conductor.record_governance_gate(
            session_id,
            action_type=action_type,
            context={"description": description},
            gate=gate,
        )
        evaluation = gate.ethics or evaluator.evaluate(action_type, {"description": description})
        lines = [gate.summary]
        for point in evaluation.points:
            if point.status != "clear":
                lines.append(f"  • [{point.status}] {point.title}: {point.rationale}")
        return "\n".join(lines)

    if sub == "audit":
        records = conductor.list_audit_records(session_id, limit=10)
        if not records:
            return "No governance audit records yet."
        lines = [f"Recent governance audits ({len(records)}):"]
        for rec in records:
            lines.append(
                f"  • {rec.record_id[:8]}… {rec.action_type} → {rec.outcome} — {rec.gate.summary[:60]}"
            )
        return "\n".join(lines)

    if sub == "list":
        lines = ["Ethics checklist:"]
        for point in ETHICS_CHECKLIST:
            lines.append(f"  {point.point_id}: {point.question}")
        return "\n".join(lines)

    return "Usage: /ethics [check|audit|list]"


def handle_soul_slash(_store: SessionStore, _session_id: str, args: list[str]) -> str:
    identity = load_soul_identity()
    sub = args[0].lower() if args else "status"

    if sub in {"resonate", "resonance", "wavelength", "pair"}:
        from conductor.soul.resonance import resonate, soul_mode_from_env

        result = resonate(search_host=True)
        lines = [
            "◆ Soul Resonance",
            f"  Mode:     {result.mode} (env CONDUCTOR_SOUL_MODE={soul_mode_from_env()})",
            f"  Resonant: {'yes — wavelengths locked' if result.resonant else 'no — solo or host-only'}",
        ]
        if result.host:
            lines.append(
                f"  Meister:  {result.host.label} [{result.host.source}]"
                + (f" {result.host.path}" if result.host.path else "")
            )
            lines.append(f"  Host len: {len(result.host.content)} chars")
        else:
            lines.append("  Meister:  (none found — set CONDUCTOR_HOST_SOUL or place HOST_SOUL.md)")
        lines.append(f"  Partner:  Conductor ({result.conductor_chars} chars)")
        if result.conductor_path:
            lines.append(f"  Partner path: {result.conductor_path}")
        for n in result.notes:
            lines.append(f"  · {n}")
        lines.append("  Spec: docs/SOUL_RESONANCE.md")
        return "\n".join(lines)

    if sub == "integrity":
        status = "✓ intact" if identity.integrity_ok else "✗ integrity check failed"
        lines = [
            f"SOUL integrity: {status}",
            f"Canonical: {identity.path}",
            f"Hash: {identity.content_hash[:16]}…",
            f"Ethics directive: {'yes' if identity.has_ethics_directive else 'no'}",
            f"Immutable marker: {'yes' if identity.has_immutable_marker else 'no'}",
        ]
        if identity.runtime_overridden and identity.runtime_path:
            lines.append(f"Runtime override: {identity.runtime_path}")
        return "\n".join(lines)

    if sub == "hash":
        return identity.content_hash or "(empty)"

    # status — include resonance snapshot
    from conductor.soul.resonance import resonate

    res = resonate(search_host=True)
    lines = [
        f"SOUL partner: {identity.tagline}",
        f"Path: {identity.path}",
        f"Words: {identity.word_count}",
        f"Integrity: {'ok' if identity.integrity_ok else 'check failed'}",
        f"Resonance: {'locked with ' + res.host.label if res.resonant and res.host else 'solo / no meister'}",
    ]
    if res.host and res.host.path:
        lines.append(f"Meister: {res.host.path}")
    lines.append("Commands: /soul status|resonate|integrity|hash")
    return "\n".join(lines)
