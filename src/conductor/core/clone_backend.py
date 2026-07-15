"""Shadow-clone backends — dispatch remnant missions to local or host subagents.

dispatch modes:
- ``local``  — run :func:`run_clone_mission` in-process (parallel ThreadPool)
- ``host``   — emit spawn_request for Grok/Claude/Codex/etc.; parent reports back
- ``hybrid`` — local scan first, then host spawn with local findings in prompt
- ``hermes`` — host-shaped for Hermes + best-effort local if no Hermes runtime
- ``auto``   — CONDUCTOR_CLONE_BACKEND env, else host if CONDUCTOR_HOST set, else local
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

from conductor.core.clone_worker import build_host_spawn_request, run_clone_mission

DispatchMode = Literal["local", "host", "hybrid", "hermes", "auto"]


def resolve_dispatch_mode(requested: str | None = None) -> str:
    raw = (requested or os.environ.get("CONDUCTOR_CLONE_BACKEND", "") or "auto").strip().lower()
    if raw in {"local", "host", "hybrid", "hermes"}:
        return raw
    # auto
    host = os.environ.get("CONDUCTOR_HOST", "").strip().lower()
    if host in {"grok", "xai", "claude", "anthropic", "codex", "cursor"}:
        return "host"
    if host in {"hermes", "ilo"}:
        return "hermes"
    # MCP clients often leave host unset — prefer host contract when under MCP
    if os.environ.get("CONDUCTOR_MCP", "").strip() in {"1", "true", "yes"}:
        return "host"
    return "local"


def detect_host_name() -> str:
    return (
        os.environ.get("CONDUCTOR_HOST", "").strip().lower()
        or os.environ.get("CONDUCTOR_MCP_HOST", "").strip().lower()
        or "generic"
    )


def dispatch_clones(
    *,
    mode: str,
    clones: list[dict[str, Any]],
    session_id: str = "",
    parent_goal: str = "",
    work_root: str | None = None,
    max_workers: int = 4,
) -> dict[str, Any]:
    """Dispatch clone missions.

    ``clones`` items need: remnant_id, objective, strategy?, work_pack?
    """
    mode = resolve_dispatch_mode(mode)
    host = detect_host_name()
    if mode == "hermes":
        host = "hermes"

    if mode == "local":
        return _dispatch_local(
            clones,
            parent_goal=parent_goal,
            work_root=work_root,
            max_workers=max_workers,
        )

    local_results: list[dict[str, Any]] = []
    if mode == "hybrid":
        local_out = _dispatch_local(
            clones,
            parent_goal=parent_goal,
            work_root=work_root,
            max_workers=max_workers,
        )
        local_results = list(local_out.get("completed") or [])
        by_id = {str(r.get("remnant_id")): r for r in local_results}

        def _enrich(c: dict[str, Any]) -> dict[str, Any]:
            pack = dict(c.get("work_pack") or {})
            loc = by_id.get(str(c["remnant_id"])) or {}
            findings = list(loc.get("findings") or [])[:8]
            files = list(loc.get("files_examined") or [])[:12]
            if findings or files:
                try:
                    from conductor.core.wave_planner import hybrid_safe_preflight_pack

                    preflight = hybrid_safe_preflight_pack(
                        findings=findings,
                        files_examined=files,
                        work_root=work_root,
                    )
                except Exception:  # noqa: BLE001
                    preflight = {
                        "findings": findings,
                        "files_examined": files,
                        "backend": "local",
                        "wave": "A",
                        "tool_class": "safe_parallel",
                    }
                pack = {
                    **pack,
                    "local_preflight": {
                        **preflight,
                        "backend": "local",
                    },
                    "steps": list(pack.get("steps") or [])
                    + [
                        f"Local preflight found {len(files)} files; deepen implementation",
                    ],
                }
            return {**c, "work_pack": pack}

        clones = [_enrich(c) for c in clones]

    # host / hermes / hybrid — prepare spawn requests parent MUST execute
    requests: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    for c in clones:
        rid = str(c["remnant_id"])
        req = build_host_spawn_request(
            remnant_id=rid,
            objective=str(c.get("objective") or ""),
            strategy=str(c.get("strategy") or ""),
            work_pack=dict(c.get("work_pack") or {}),
            parent_goal=parent_goal,
            session_id=session_id,
            host=host,
        )
        # Attach local preflight summary into prompt/context if hybrid
        if mode == "hybrid" and c.get("work_pack", {}).get("local_preflight"):
            pre = c["work_pack"]["local_preflight"]
            pre_block = (
                "\n\n## Local preflight (already run)\n"
                + "\n".join(f"- {f}" for f in (pre.get("findings") or [])[:6])
                + "\nFiles: "
                + ", ".join((pre.get("files_examined") or [])[:8])
            )
            req["prompt"] = str(req.get("prompt") or "") + pre_block
            if req.get("context") is not None:
                req["context"] = str(req.get("context") or "") + pre_block
            if isinstance(req.get("tool_call"), dict):
                args = dict(req["tool_call"].get("arguments") or {})
                tool_name = str(req["tool_call"].get("tool") or "")
                if tool_name == "delegate_task":
                    args["context"] = req.get("context") or req["prompt"]
                else:
                    args["prompt"] = req["prompt"]
                req["tool_call"] = {**req["tool_call"], "arguments": args}
        # Normalize every host spawn so validation never rejects hermes/ilo
        req = _normalize_spawn_request(req, remnant_id=rid)
        requests.append(req)
        if req.get("tool_call"):
            tool_calls.append(req["tool_call"])
        pending.append(
            {
                "remnant_id": rid,
                "clone_status": "awaiting_host",
                "spawn_request": req,
            }
        )

    # Validate tool_calls are complete enough for parent execution (host-aware)
    for tc in tool_calls:
        _validate_host_tool_call(tc)

    parent_checklist = [
        {
            "step": i + 1,
            "remnant_id": req["remnant_id"],
            "label": str(req.get("description") or req.get("goal") or "")[:80],
            "spawn": req.get("tool_call"),
            "after": req.get("after_complete"),
        }
        for i, req in enumerate(requests)
    ]

    n = len(tool_calls)
    hermes_batch = _build_hermes_batch(requests) if host in {"hermes", "ilo"} else None
    host_tool = (
        "delegate_task"
        if host in {"hermes", "ilo"}
        else "Task"
        if host in {"claude", "anthropic"}
        else "spawn_subagent"
    )
    # Wave plan for host spawn requests (all wave C; hybrid preflight = A)
    try:
        from conductor.core.wave_planner import plan_waves, WAVE_LABELS

        wave_plan = plan_waves(requests)
    except Exception:  # noqa: BLE001
        wave_plan = {
            "summary": {"A": 0, "B": 0, "C": n, "total": n},
            "wave_order": ["A", "B", "C"],
            "wave_labels": {"A": "reads", "B": "writes", "C": "spawn"},
            "guidance": f"Wave C spawn batch n={n}",
        }
        WAVE_LABELS = {"A": "reads", "B": "writes", "C": "spawn"}  # type: ignore[misc]

    hybrid_preflight_n = len(local_results) if mode == "hybrid" else 0
    waves_field = {
        "order": list(wave_plan.get("wave_order") or ["A", "B", "C"]),
        "labels": dict(wave_plan.get("wave_labels") or WAVE_LABELS),
        "summary": dict(wave_plan.get("summary") or {}),
        "A": {
            "count": hybrid_preflight_n,
            "kind": "hybrid_safe_preflight" if hybrid_preflight_n else "none",
            "note": (
                "Local scan already ran; do not re-scan same paths."
                if hybrid_preflight_n
                else "No wave-A work in this fanout payload."
            ),
        },
        "B": {"count": 0, "note": "Writes happen inside host children, not parent fanout."},
        "C": {
            "count": n,
            "spawn_count": n,
            "prefer": "hermes_batch / one multi-task spawn" if n > 1 else "single spawn",
            "batch_id": (hermes_batch or {}).get("batch_id"),
        },
        "guidance": wave_plan.get("guidance")
        or "Prefer one host batch this turn; host may segment tools.",
        "do_not_dual_own_scheduler": True,
    }
    protocol = {
        "steps": [
            f"1. SPAWN: call host tool {host_tool} for EVERY tool_calls[i] "
            "(or hermes_batch once) in THIS turn — parallel (wave C)",
            "2. spawn_ack: remnant_orchestrate action=spawn_ack with "
            "[{remnant_id, clone_handle}, …]",
            "3. When each child finishes: remnant_orchestrate action=report",
            "4. remnant_orchestrate action=merge when await ready",
        ],
        "host_tool": host_tool,
        "parallel": True,
        "wave": "C",
        "mcp_cannot_spawn": True,
        "note": (
            "MCP cannot call Grok/Hermes tools. You (the parent) must execute "
            "host spawn tools; Conductor only tracks remnant_ids + report/merge. "
            "Hermes segments large mixed tool batches — do not reimplement that here."
        ),
    }
    concurrency_note = None
    if hermes_batch and n > 3:
        concurrency_note = (
            f"Hermes default max_concurrent_children is 3; set "
            f"delegation.max_concurrent_children >= {n} in config.yaml "
            f"or split batches."
        )

    return {
        "dispatch_mode": mode,
        "host": host,
        "completed": local_results if mode == "hybrid" else [],
        "pending": pending,
        "spawn_requests": requests,
        "tool_calls": tool_calls,
        "parent_checklist": parent_checklist,
        "execute_tool_calls_now": True,
        "parent_must_spawn": True,
        "spawn_count": n,
        "protocol": protocol,
        "hermes_batch": hermes_batch,
        "waves": waves_field,
        "concurrency_note": concurrency_note,
        "anti_theater": (
            "Do not implement all axes yourself. SPAWN tool_calls / hermes_batch "
            "first, then report with real clone_handle values."
        ),
        "host_contract": _host_contract(mode, host),
        "mandatory_host_action": _mandatory_host_action(host, n=n),
        "note": (
            "Shadow clones await host subagents. parent_must_spawn=true: execute "
            "host tools THIS turn, then spawn_ack → report → merge. "
            "MCP cannot spawn — only the parent can. "
            "waves.C marks host spawn batch (advisory; host owns scheduling)."
        ),
    }


def _dispatch_local(
    clones: list[dict[str, Any]],
    *,
    parent_goal: str,
    work_root: str | None,
    max_workers: int,
) -> dict[str, Any]:
    completed: list[dict[str, Any]] = []

    def _run(c: dict[str, Any]) -> dict[str, Any]:
        return run_clone_mission(
            remnant_id=str(c["remnant_id"]),
            objective=str(c.get("objective") or ""),
            strategy=str(c.get("strategy") or ""),
            work_pack=dict(c.get("work_pack") or {}),
            work_root=work_root,
            parent_goal=parent_goal,
        )

    workers = max(1, min(max_workers, len(clones) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_run, c): c for c in clones}
        for fut in as_completed(futs):
            try:
                completed.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                c = futs[fut]
                completed.append(
                    {
                        "ok": False,
                        "kind": "shadow_clone_result",
                        "backend": "local",
                        "remnant_id": str(c.get("remnant_id")),
                        "error": str(exc),
                        "insights": [f"[clone:error] {exc}"],
                        "progress_percent": 0.0,
                    }
                )

    return {
        "dispatch_mode": "local",
        "host": "local",
        "completed": completed,
        "pending": [],
        "spawn_requests": [],
        "host_contract": None,
        "note": "Local shadow clones finished in-process; results applied to remnants.",
    }


def _mandatory_host_action(host: str, *, n: int = 0) -> str:
    h = (host or "generic").lower()
    count = f" ({n} clones)" if n else ""
    if h in {"hermes", "ilo"}:
        return (
            f"SPAWN NOW{count}. Prefer ONE Hermes call: hermes_batch "
            "(delegate_task with tasks[]). Fallback: each tool_calls[i] is "
            "delegate_task(goal, context). Then remnant_orchestrate action=spawn_ack "
            "with clone handles, then report, then merge. Do not only read contracts."
        )
    if h in {"claude", "anthropic"}:
        return (
            f"SPAWN ALL tool_calls NOW{count} (parallel). Claude: Task tool with each "
            "tool_calls[i].arguments (description+prompt). Then spawn_ack → report → merge."
        )
    return (
        f"SPAWN ALL tool_calls NOW{count} (parallel). Grok: spawn_subagent with each "
        "tool_calls[i].arguments (prompt+description). MCP cannot spawn — you must. "
        "Then remnant_orchestrate action=spawn_ack, then report each, then merge."
    )


def _build_hermes_batch(requests: list[dict[str, Any]]) -> dict[str, Any] | None:
    """One Hermes delegate_task(tasks=[…]) for parallel batch fan-out.

    1.18.9+: includes ``waves`` (wave C spawn batch) and batch_id for thrash.
    Conductor does **not** segment host tool schedules — Hermes does.
    """
    if not requests:
        return None
    tasks: list[dict[str, str]] = []
    remnant_ids: list[str] = []
    for req in requests:
        rid = str(req.get("remnant_id") or "")
        goal = str(req.get("goal") or req.get("objective") or "")
        context = str(req.get("context") or req.get("prompt") or "")
        if not goal:
            continue
        tasks.append({"goal": goal, "context": context})
        remnant_ids.append(rid)
    if not tasks:
        return None
    n = len(tasks)
    batch_id = f"hermes_batch:{n}:{remnant_ids[0][:8] if remnant_ids else 'x'}"
    return {
        "tool": "delegate_task",
        "arguments": {
            "tasks": tasks,
            # thrash / wave meta (host ignores unknown keys safely)
            "_conductor_batch": batch_id,
            "_conductor_wave": "C",
        },
        "remnant_ids": remnant_ids,
        "batch_id": batch_id,
        "wave": "C",
        "tool_class": "spawn",
        "waves": {
            "C": {
                "count": n,
                "remnant_ids": remnant_ids,
                "label": "delegate / remnant / host spawn",
            }
        },
        "requires_config": {
            "delegation.max_concurrent_children": f">={n}",
        },
        "note": (
            "Call Hermes native tool delegate_task ONCE with arguments.tasks. "
            "Index i maps to remnant_ids[i] for spawn_ack + report. "
            "Wave C batch — do not reimplement Hermes tool-batch segmentation."
        ),
    }


def _normalize_spawn_request(req: dict[str, Any], *, remnant_id: str) -> dict[str, Any]:
    """Ensure every spawn request has a complete, host-native tool_call."""
    out = dict(req)
    desc = str(
        out.get("description")
        or out.get("goal")
        or out.get("objective")
        or f"clone:{remnant_id[:8]}"
    )[:80]
    prompt = str(
        out.get("prompt")
        or out.get("context")
        or out.get("goal")
        or out.get("objective")
        or ""
    )
    context = str(out.get("context") or prompt)
    if not out.get("description"):
        out["description"] = desc
    if not out.get("prompt") and prompt:
        out["prompt"] = prompt
    if not out.get("context") and context:
        out["context"] = context

    tc = out.get("tool_call")
    if isinstance(tc, dict):
        tool = str(tc.get("tool") or "")
        args = dict(tc.get("arguments") or {})
        if tool == "delegate_task":
            # Hermes: goal + context only (no description required on tool args)
            if not args.get("goal"):
                args["goal"] = out.get("goal") or out.get("objective") or desc
            if not args.get("context"):
                args["context"] = context
            # strip non-hermes noise if present
            args.pop("description", None)
            args.pop("prompt", None)
            args.pop("kind", None)
            args.pop("remnant_id", None)
        else:
            if not args.get("description"):
                args["description"] = desc
            if not args.get("prompt") and prompt:
                args["prompt"] = prompt
            if out.get("goal") and not args.get("goal"):
                args["goal"] = out["goal"]
        out["tool_call"] = {**tc, "arguments": args}

    if not out.get("after_complete"):
        out["after_complete"] = {
            "tool": "remnant_orchestrate",
            "arguments": {
                "action": "report",
                "remnant_id": remnant_id,
                "result": {
                    "ok": True,
                    "reported_by_host": True,
                    "findings": ["…from clone…"],
                    "insights": ["…"],
                    "done": True,
                },
            },
        }
    return out


def _validate_host_tool_call(tc: dict[str, Any] | None) -> None:
    """Host-aware completeness check for parent-executable tool_calls.

    Grok spawn_subagent and Claude Task require prompt+description.
    Hermes delegate_task requires goal + context (or prompt alias).
    """
    if not isinstance(tc, dict):
        raise ValueError("host tool_call must be an object")
    args = dict(tc.get("arguments") or {})
    tool = str(tc.get("tool") or "")
    if tool == "delegate_task":
        if not args.get("goal"):
            raise ValueError("host tool_call (delegate_task) missing goal")
        if not (args.get("context") or args.get("prompt")):
            raise ValueError("host tool_call (delegate_task) missing context")
        return
    has_body = bool(args.get("prompt") or args.get("goal"))
    has_desc = bool(args.get("description"))
    if not has_body:
        raise ValueError(
            f"host tool_call ({tool or 'unknown'}) missing prompt or goal"
        )
    if not has_desc:
        raise ValueError(
            f"host tool_call ({tool or 'unknown'}) missing description"
        )


def _host_contract(mode: str, host: str) -> dict[str, Any]:
    h = (host or "generic").lower()
    steps = [
        "1. SPAWN host subagents THIS turn (tool_calls or hermes_batch) — MCP cannot",
        "2. remnant_orchestrate action=spawn_ack with clone_handle per remnant_id",
        "3. When a clone finishes: remnant_orchestrate action=report "
        "with remnant_id + result={findings,insights,suggested_edits,done}",
        "4. remnant_orchestrate action=await until ready",
        "5. remnant_orchestrate action=merge (or force=true if stuck)",
    ]
    if h in {"hermes", "ilo"}:
        steps[0] = (
            "1. Prefer hermes_batch: ONE delegate_task(tasks=[…]). "
            "Or per-clone tool_calls[i] with goal+context"
        )
    elif h in {"claude", "anthropic"}:
        steps[0] = (
            "1. Claude: Task tool with description, prompt from each tool_calls[i]"
        )
    else:
        steps[0] = (
            "1. Grok: spawn_subagent(**tool_calls[i].arguments) for ALL i in parallel"
        )

    return {
        "mode": mode,
        "host": host,
        "depth_limit": 1,
        "mcp_cannot_spawn": True,
        "steps": steps,
        "grok_spawn_subagent_schema": {
            "tool": "spawn_subagent",
            "required": ["prompt", "description"],
            "optional": [
                "subagent_type",
                "background",
                "capability_mode",
                "isolation",
                "cwd",
            ],
            "subagent_types": ["general-purpose", "explore", "plan"],
            "note": "Subagents cannot spawn children (nesting depth 1).",
        },
        "hermes_delegate_schema": {
            "tool": "delegate_task",
            "required": ["goal", "context"],
            "batch": "arguments.tasks = [{goal, context}, …]",
            "optional": ["role"],
            "note": (
                "Native Hermes tool. Prefer hermes_batch one-shot. "
                "Config: delegation.max_concurrent_children >= N."
            ),
        },
        "claude_task_schema": {
            "tool": "Task",
            "required": ["description", "prompt"],
            "optional": ["subagent_type"],
        },
        "spawn_ack_example": {
            "action": "spawn_ack",
            "handles": [
                {"remnant_id": "<id>", "clone_handle": "<subagent_id>"},
            ],
        },
        "report_example": {
            "action": "report",
            "remnant_id": "<id>",
            "clone_handle": "<subagent_id from spawn>",
            "result": {
                "ok": True,
                "findings": ["…"],
                "insights": ["…"],
                "suggested_edits": [],
                "done": True,
            },
        },
        "hybrid_note": (
            "hybrid mode: local preflight already ran; host clone deepens implementation."
            if mode == "hybrid"
            else None
        ),
    }
