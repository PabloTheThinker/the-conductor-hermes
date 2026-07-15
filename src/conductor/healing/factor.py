"""Integrity cascade — reflex → field repairs → learn → advance.

Conductor-native autonomic integrity (see governance/HEALING.md, SOUL.md).
"""

from __future__ import annotations

from typing import Any

from conductor.agent.tool_result import ToolResult
from conductor.healing.classify import classify_tool_failure
from conductor.healing.learn import record_scar_learning
from conductor.healing.models import HealReport, Remediation, Scar
from conductor.healing.recover import (
    ensure_parent_dirs,
    has_mirror,
    mirror_write,
    path_exists,
    restore_path,
)
from conductor.healing.store import ScarStore
from conductor.session.store import SessionStore


def maybe_mirror_write(
    path: str,
    content: str,
    *,
    session_id: str | None,
    ok: bool,
) -> dict[str, Any] | None:
    """On successful writes, leave a recovery imprint for later rebuild."""
    if not ok or not path or not session_id:
        return None
    return mirror_write(path, content, session_id=session_id)


def heal_moment(
    store: SessionStore,
    session_id: str,
    *,
    tool: str,
    error: str,
    arguments: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> HealReport:
    """Run integrity cascade: classify wound, field repairs, learn, advance."""
    args = dict(arguments or {})
    meta = dict(meta or {})
    clf = classify_tool_failure(tool, error, arguments=args, meta=meta)

    path_hint = clf.path or str(args.get("path") or meta.get("path") or "")
    scar_store = ScarStore(store)
    existing = scar_store.find_coalesce_target(
        session_id,
        kind=clf.kind,
        path=path_hint,
        source_tool=tool,
    )
    actions: list[str] = []
    healed = False
    coalesce_hit = existing is not None
    if existing is not None:
        scar = existing
        scar.severity = max(scar.severity, clf.severity)
        scar.summary = f"{tool} failed: {(error or 'unknown error')[:240]}"
        scar.source_tool = tool or scar.source_tool
        scar.error = (error or scar.error)[:2000]
        if path_hint:
            scar.path = path_hint
        # Re-open healed-like motion only if still active; keep escalated/chronic.
        if scar.status in {"open", "healing"}:
            scar.status = "healing"
        actions.append("coalesce_scar")
    else:
        scar = Scar.open_new(
            session_id=session_id,
            kind=clf.kind,
            severity=clf.severity,
            summary=f"{tool} failed: {(error or 'unknown error')[:240]}",
            source_tool=tool,
            error=error,
            path=path_hint,
        )
        scar.status = "healing"
        scar.tier = "field"

    # --- field repairs by kind ---
    if clf.kind == "path_missing" and scar.path:
        parent = ensure_parent_dirs(scar.path)
        scar.remediations.append(
            Remediation(
                action="ensure_parent_dirs",
                result="success" if parent.get("ok") else "failure",
                detail=str(parent.get("path") or parent.get("error") or ""),
            )
        )
        actions.append("ensure_parent_dirs")

        if has_mirror(scar.path):
            restored = restore_path(scar.path)
            scar.remediations.append(
                Remediation(
                    action="restore_from_imprint",
                    result="success" if restored.get("ok") else "failure",
                    detail=str(restored.get("bytes") or restored.get("error") or ""),
                )
            )
            actions.append("restore_from_imprint")
            if restored.get("ok") and path_exists(scar.path):
                healed = True
                scar.recovered_paths.append(scar.path)
                scar.seal = (
                    f"When {scar.path} is missing, rebuild from CONDUCTOR_HOME/recovery imprint."
                )
                scar.forward_step = f"Re-read or re-use rebuilt file: {scar.path}"
        elif path_exists(scar.path):
            healed = True
            scar.seal = f"Ensure parent directories exist before accessing {scar.path}."
            scar.forward_step = f"Retry access to {scar.path}"
        else:
            scar.forward_step = (
                f"Recreate {scar.path} with write_file or operator backup; "
                "continue with the smallest recreatable artifact."
            )

    elif clf.kind == "permission":
        scar.remediations.append(
            Remediation(
                action="spine_hold",
                result="skipped",
                detail="Conductor spine / safety floors are not bypassed by repair",
            )
        )
        actions.append("spine_hold")
        scar.status = "escalated"
        scar.tier = "deep"
        scar.forward_step = (
            "Choose an allowed path or request operator authority; do not force deny zones."
        )
        scar.seal = (
            "Permission and path-safety denials require an alternate path or human ack — never bypass."
        )

    elif clf.kind == "shell":
        # NEVER auto-re-run shell from integrity cascade — especially destructive ops.
        # Real-world failure mode: agents mass-deleting home/root while "fixing" things.
        from conductor.agent.path_safety import integrity_may_not_auto_retry

        cmd_hint = str(meta.get("command") or args.get("command") or "")
        if integrity_may_not_auto_retry(cmd_hint):
            scar.remediations.append(
                Remediation(
                    action="no_auto_retry_destructive",
                    result="skipped",
                    detail="Integrity cascade never re-runs rm/dd/mkfs/find -delete or denied shells",
                )
            )
            actions.append("no_auto_retry_destructive")
            scar.seal = (
                "Never auto-retry destructive shell. Diagnose; use scoped project paths only; "
                "mass-delete of home/root is forbidden."
            )
            scar.forward_step = (
                "Do NOT re-run the failed shell. Inspect error, work in a scoped project directory, "
                "and prefer write_file / read_file over broad rm."
            )
        else:
            scar.remediations.append(
                Remediation(
                    action="record_and_continue",
                    result="success",
                    detail="Non-zero shell recorded; no automatic re-run",
                )
            )
            actions.append("record_and_continue")
            scar.forward_step = (
                "Inspect shell output, fix command or environment deliberately "
                "(human-visible), or open a bounded subgoal — no blind retry."
            )
            scar.seal = (
                "Shell failures: diagnose output first; never blind-retry."
            )

    elif clf.kind == "provider":
        scar.forward_step = (
            "Degrade gracefully: set CONDUCTOR_PROVIDER / CONDUCTOR_BASE_URL / CONDUCTOR_MODEL, "
            "or use CONDUCTOR_PROVIDER=test offline; continue with local tools where possible."
        )
        scar.seal = (
            "Provider outages: use alternate base_url or tools-only mode; do not invent keys."
        )
        actions.append("provider_guidance")

    else:
        scar.remediations.append(
            Remediation(
                action="classify_and_continue",
                result="success",
                detail=f"kind={clf.kind}",
            )
        )
        actions.append("classify_and_continue")
        scar.forward_step = (
            "Acknowledge the failure, pick an alternate approach, "
            "and take the smallest next verifiable step."
        )

    if healed:
        scar.status = "healed"
    elif scar.status != "escalated":
        scar.status = "open"

    if not scar.forward_step:
        scar.forward_step = "Continue mission with the next smallest verifiable step."

    # High severity open wounds may need deep reconstitution later
    if not healed and scar.severity >= 4 and scar.status == "open":
        scar.tier = "deep"

    ScarStore(store).upsert(scar)
    # Coalesced re-hits: do not re-write Memory Fabric seals every tool call.
    if not coalesce_hit or healed:
        record_scar_learning(store, scar, healed=healed)

    # Loop engineering: stop / escalate when chronic or spine-hold
    loop_suffix = ""
    try:
        from conductor.loop_policy import evaluate_loop, loop_decision_suffix

        decision = evaluate_loop(store, session_id, last_scar=scar)
        if decision.action in {"stop", "escalate"}:
            actions.append(f"loop_{decision.action}")
            if decision.action == "escalate" and scar.status not in {"healed"}:
                scar.tier = "deep"
                prior_status = scar.status
                if scar.status == "open":
                    scar.status = "chronic"
                ScarStore(store).upsert(scar)
                # Full Max Effort package once per wound class; re-hits stay short.
                already_packaged = (
                    prior_status in {"escalated", "chronic"}
                    and "max effort" in (scar.forward_step or "").lower()
                ) or (coalesce_hit and prior_status in {"escalated", "chronic"})
                if already_packaged:
                    loop_suffix = loop_decision_suffix(decision)
                else:
                    try:
                        from conductor.escalate_path import (
                            build_escalate_package,
                            escalate_package_suffix,
                        )

                        pkg = build_escalate_package(store, session_id, decision, scar=scar)
                        loop_suffix = loop_decision_suffix(decision) + escalate_package_suffix(pkg)
                        scar.forward_step = str(
                            pkg.get("forward_step") or decision.escalate_hint or scar.forward_step
                        )
                        if scar.status not in {"escalated", "chronic"}:
                            scar.status = "escalated"
                        ScarStore(store).upsert(scar)
                    except Exception:  # noqa: BLE001
                        loop_suffix = loop_decision_suffix(decision)
                        if decision.escalate_hint and not healed:
                            scar.forward_step = decision.escalate_hint
            else:
                loop_suffix = loop_decision_suffix(decision)
                if decision.escalate_hint and not healed:
                    scar.forward_step = decision.escalate_hint
    except Exception:  # noqa: BLE001
        pass

    if scar.recovered_paths:
        detail = f"Rebuilt from imprint: {', '.join(scar.recovered_paths)}."
    elif actions:
        detail = "Applied allowlisted field repairs."
    else:
        detail = "Scar recorded."

    message = (
        f"Wound classified ({scar.kind}, severity={scar.severity}). "
        f"{detail} Learning written to Memory Fabric; advancing."
    )
    if loop_suffix:
        message = message + loop_suffix

    return HealReport(
        scar=scar,
        healed=healed,
        actions=actions,
        message=message,
        forward_step=scar.forward_step,
    )


def apply_healing_to_result(
    result: ToolResult,
    report: HealReport | None,
) -> ToolResult:
    """Annotate failed tool output with integrity-cascade context."""
    if report is None or result.ok:
        return result
    suffix = report.as_tool_suffix()
    if result.error:
        result.error = (result.error.rstrip() + suffix).strip()
    else:
        result.content = (result.content or "").rstrip() + suffix
    result.meta["healing"] = report.to_dict()
    if report.healed:
        result.meta["healing_healed"] = True
    return result
