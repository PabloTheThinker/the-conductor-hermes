"""Host-spawn compliance — detect and block orchestration theater.

Live lesson (self-study): MCP fanout returns tool_calls; if the parent never
spawns host subagents / never spawn_acks, merge-with-fake-reports is ceremony
without parallel work.

Rules (1.18.6+):
- host_spawn_required + awaiting_host clones → not compliant
- host backends need clone_handle after spawn_ack or report
- merge without compliance raises unless force + accept_theater
- report from awaiting_host without handle is soft-blocked (require handle)
"""

from __future__ import annotations

from typing import Any

from conductor.core.models import CloneStatus, RemnantRecord


def assess_spawn_compliance(
    remnants: list[RemnantRecord],
    *,
    host_spawn_required: bool = False,
    host_spawn_count: int = 0,
) -> dict[str, Any]:
    """Return compliance verdict for active (or provided) remnant clones."""
    rows: list[dict[str, Any]] = []
    theater_flags: list[str] = []
    ok = True

    hostish = {"host", "hybrid", "hermes", "auto"}
    for r in remnants:
        backend = (r.clone_backend or "").strip().lower() or "none"
        st = r.clone_status
        handle = (r.clone_handle or "").strip()
        has_result = bool(r.clone_result)
        row: dict[str, Any] = {
            "remnant_id": r.remnant_id,
            "objective": (r.task_objective or "")[:80],
            "clone_backend": backend,
            "clone_status": st.value if hasattr(st, "value") else str(st),
            "clone_handle": handle or None,
            "has_result": has_result,
            "compliant": True,
            "issues": [],
        }
        issues: list[str] = []

        if st == CloneStatus.AWAITING_HOST:
            ok = False
            issues.append("still awaiting_host — parent must SPAWN tool_calls then spawn_ack")
            theater_flags.append(f"{r.remnant_id[:8]}:awaiting_host")
        elif st == CloneStatus.PENDING:
            ok = False
            issues.append("clone still pending dispatch")
            theater_flags.append(f"{r.remnant_id[:8]}:pending")
        elif st == CloneStatus.RUNNING:
            # Host child in flight is OK for await, not for merge
            ok = False
            issues.append("clone still running")
            theater_flags.append(f"{r.remnant_id[:8]}:running")
        elif backend in hostish or host_spawn_required:
            if st in {
                CloneStatus.SPAWNED,
                CloneStatus.REPORTED,
                CloneStatus.COMPLETED,
                CloneStatus.FAILED,
            }:
                if not handle and st != CloneStatus.COMPLETED:
                    # COMPLETED local hybrid preflight may lack host handle until deepen
                    if backend != "local":
                        ok = False
                        issues.append(
                            "host clone missing clone_handle (no spawn_ack / spawn proof)"
                        )
                        theater_flags.append(f"{r.remnant_id[:8]}:no_handle")
                if st == CloneStatus.REPORTED and not handle:
                    ok = False
                    if f"{r.remnant_id[:8]}:no_handle" not in theater_flags:
                        theater_flags.append(f"{r.remnant_id[:8]}:report_without_handle")
                        issues.append("reported without spawn handle — likely theater")

        # Fake report: claimed host report but no handle when host was required
        cr = r.clone_result or {}
        if (
            host_spawn_required
            and isinstance(cr, dict)
            and cr.get("reported_by_host")
            and not handle
        ):
            ok = False
            issues.append("host report without clone_handle")
            if f"{r.remnant_id[:8]}:fake_report" not in theater_flags:
                theater_flags.append(f"{r.remnant_id[:8]}:fake_report")

        row["issues"] = issues
        row["compliant"] = len(issues) == 0
        if not row["compliant"]:
            ok = False
        rows.append(row)

    if host_spawn_required and host_spawn_count > 0:
        handled = sum(1 for r in remnants if (r.clone_handle or "").strip())
        if handled < min(host_spawn_count, len(remnants)):
            ok = False
            theater_flags.append(
                f"handles={handled}<spawn_count={host_spawn_count}"
            )

    verdict = {
        "ok": ok and len(rows) > 0,
        "host_spawn_required": host_spawn_required,
        "host_spawn_count": host_spawn_count,
        "total": len(rows),
        "compliant_count": sum(1 for r in rows if r["compliant"]),
        "theater_risk": not ok,
        "theater_flags": theater_flags,
        "clones": rows,
        "next": (
            "compliant — merge when clone_readiness.ready"
            if ok and rows
            else (
                "THEATER RISK: PARENT must execute tool_calls (spawn_subagent / "
                "delegate_task) THIS turn → spawn_ack with real handles → "
                "report findings → merge. Do NOT invent report results without spawn."
            )
        ),
    }
    return verdict


def merge_blocked_message(compliance: dict[str, Any]) -> str:
    flags = ", ".join(compliance.get("theater_flags") or []) or "unknown"
    return (
        "spawn compliance failed — merge blocked (orchestration theater). "
        f"flags=[{flags}]. "
        "Do NOT stop the mission. "
        "Next: SPAWN host tools from fanout tool_calls / hermes_batch, "
        "then remnant_orchestrate action=spawn_ack with real clone_handles, "
        "then report each child with findings, then merge. "
        "force=true + accept_theater=true only if you knowingly accept incomplete parallel work."
    )


def evidence_markers_in_text(text: str) -> bool:
    """Heuristic: does this insight/finding look like proof, not narration?"""
    import re

    low = (text or "").lower()
    if not low or len(low) < 12:
        return False
    patterns = (
        r"\bpytest\b",
        r"\bpassed\b",
        r"\bexit\s*0\b",
        r"\bhttp\s*[12]\d\d\b",
        r"https?://\S+",
        r"\bwrote\b.+\.(py|js|ts|html|css|md)\b",
        r"\bcreated\b.+\.(py|js|ts|html)\b",
        r"\bfile[s]?\s+(touched|written|examined)\b",
        r"\b\d+\s+tests?\b",
        r"\[clone:finding\]",
        r"touch candidate:",
        r"greenfield deliverable:",
        r"scaffold wrote:",
    )
    return any(re.search(p, low) for p in patterns)


def judgment_from_merge_insights(insights: list[str]) -> dict[str, Any]:
    """Combo G lite: is the merge surface evidence-shaped?"""
    hits = [i for i in insights if evidence_markers_in_text(str(i))]
    return {
        "done_proven": len(hits) >= 1 and len(insights) >= 1,
        "evidence_hits": len(hits),
        "insight_count": len(insights),
        "note": (
            "Merge has evidence-shaped insights — still verify with host tests/serve."
            if hits
            else (
                "Merge insights lack evidence markers (paths/tests/URLs). "
                "Fold Combo G: run pytest/serve and memory_episodic before claiming done."
            )
        ),
        "sample_evidence": hits[:4],
    }
