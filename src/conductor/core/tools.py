"""Conductor agent tools — Crucible Global Workspace operations."""

from __future__ import annotations

from typing import Any

from conductor.core.runtime import ConductorRuntime
from conductor.memory.episodic import EpisodicStore
from conductor.memory.snapshot_export import export_task_scoped_slice
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore

# Extended remnant actions (fanout) declared below with remnant_orchestrate schema.

CONDUCTOR_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "crucible_workspace",
            "description": (
                "Operate Conductor's Crucible Global Workspace (Noesis pocket dimension). "
                "Post verbalizable concepts, register clones, read workspace state, distill insights. "
                "See crucible/WORKSPACE.md."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "start",
                            "status",
                            "post",
                            "replace",
                            "read",
                            "register_clone",
                            "fork_clone",
                            "distill",
                            "noesis",
                            "rbmc",
                            "max_effort",
                            "pocket",
                        ],
                    },
                    "objective": {
                        "type": "string",
                        "description": "Crucible session objective (start)",
                    },
                    "label": {"type": "string", "description": "Workspace concept label (post/replace)"},
                    "old_label": {"type": "string", "description": "Label to replace (replace)"},
                    "confidence": {
                        "type": "number",
                        "description": "Concept confidence 0–1 (post/replace)",
                    },
                    "primary_emotion": {
                        "type": "string",
                        "description": "Emotional valence primary (post/replace)",
                    },
                    "intensity": {
                        "type": "number",
                        "description": "Emotional intensity 0–1 (post/replace)",
                    },
                    "automatic": {
                        "type": "boolean",
                        "description": "Background processing only — never occupies workspace slot",
                    },
                    "clone_id": {
                        "type": "string",
                        "description": "Clone actor id (post/replace/read/register_clone)",
                    },
                    "birth_moment_label": {
                        "type": "string",
                        "description": "Clone birth moment (register_clone)",
                    },
                    "snapshot_summary": {
                        "type": "string",
                        "description": "Task-scoped memory slice summary (register_clone)",
                    },
                    "forked_from": {
                        "type": "string",
                        "description": "Parent clone id (register_clone)",
                    },
                    "track_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Linked track ids (post)",
                    },
                    "reasoning_layer": {
                        "type": "integer",
                        "description": "RBMC reasoning depth (post)",
                    },
                    "human_acknowledged": {
                        "type": "boolean",
                        "description": "Operator acknowledged ethics escalation (start/distill)",
                    },
                    "decision": {
                        "type": "string",
                        "description": "Decision text for max_effort",
                    },
                    "max_clones": {
                        "type": "integer",
                        "description": "Clone count for noesis/rbmc (default 3)",
                    },
                    "auto_distill": {
                        "type": "boolean",
                        "description": "Auto-run distill after noesis/max_effort (default true)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conductor_status",
            "description": "Summarize conductor layer: Crucible workspace, active remnants, merged insights.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remnant_orchestrate",
            "description": (
                "Shadow clones: fanout → parent MUST spawn host tools (Grok spawn_subagent / "
                "Hermes delegate_task; MCP cannot spawn) → spawn_ack → report → merge. "
                "Naruto-style: one will, many bodies. Skip single-path tasks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "spawn",
                            "work",
                            "heartbeat",
                            "status",
                            "await",
                            "spawn_ack",
                            "report",
                            "merge",
                            "merge_reflective",
                            "merge_deep",
                            "fanout",
                            "compliance",
                        ],
                    },
                    "accept_theater": {
                        "type": "boolean",
                        "description": (
                            "With force=true, allow merge despite missing host spawn "
                            "(orchestration theater). Prefer real spawn_ack instead."
                        ),
                    },
                    "objective": {"type": "string", "description": "Task objective (spawn)"},
                    "objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple objectives for fanout (≥2)",
                    },
                    "strategies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional strategies aligned with objectives (fanout)",
                    },
                    "strategy": {"type": "string", "description": "Exploration strategy (spawn)"},
                    "auto_work": {
                        "type": "boolean",
                        "description": "Fanout: build structured work packs (default true)",
                    },
                    "dispatch": {
                        "type": "string",
                        "enum": ["auto", "local", "host", "hybrid", "hermes"],
                        "description": (
                            "Shadow clone backend: local workers, host spawn_subagent "
                            "contract, hybrid (local preflight+host), hermes, or auto"
                        ),
                    },
                    "parent_goal": {
                        "type": "string",
                        "description": "Overall mission for clone briefs (fanout)",
                    },
                    "work_root": {
                        "type": "string",
                        "description": "Workspace root for local clone file scan",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Merge even if clones still awaiting host (default false)",
                    },
                    "result": {
                        "type": "object",
                        "description": "Clone result payload for action=report",
                    },
                    "clone_handle": {
                        "type": "string",
                        "description": "Host subagent id (report|spawn_ack)",
                    },
                    "handles": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": (
                            "spawn_ack: [{remnant_id, clone_handle}, …] after host spawn"
                        ),
                    },
                    "remnant_id": {
                        "type": "string",
                        "description": "Target remnant id (heartbeat|work|report|spawn_ack)",
                    },
                    "current_subtask": {"type": "string", "description": "Current subtask (heartbeat)"},
                    "progress_percent": {
                        "type": "number",
                        "description": "Progress 0–100 (heartbeat)",
                    },
                    "key_decisions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Decisions since last heartbeat",
                    },
                    "new_insights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New insights (heartbeat)",
                    },
                    "remnant_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Remnants to merge (merge; omit for all active)",
                    },
                    "human_acknowledged": {
                        "type": "boolean",
                        "description": "Operator acknowledged ethics escalation (spawn/merge)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conductor_worker",
            "description": (
                "Bounded offline/local worker (echo | shell). NOT Hermes AI subagents. "
                "For parallel AI clones use remnant_orchestrate fanout + host "
                "spawn_subagent (Grok) or native Hermes delegate_task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Bounded task description"},
                    "worker": {
                        "type": "string",
                        "description": "Worker profile: offline | local",
                        "default": "offline",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Worker mode: echo | shell | fail",
                    },
                    "command": {
                        "type": "string",
                        "description": "Shell command when mode=shell",
                    },
                    "human_acknowledged": {"type": "boolean"},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "track_orchestrate",
            "description": "Conductor Track System — create, list, update, and view strategic tracks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create",
                            "list",
                            "update",
                            "view",
                            "fork",
                            "prune",
                            "resolve",
                            "chessboard",
                            "link",
                            "unlink",
                            "edges",
                            "neighbors",
                        ],
                    },
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "track_id": {"type": "string"},
                    "parent_id": {"type": "string"},
                    "to_track_id": {
                        "type": "string",
                        "description": "Target track for link",
                    },
                    "from_track_id": {
                        "type": "string",
                        "description": "Source track for link (defaults to track_id)",
                    },
                    "edge_id": {"type": "string"},
                    "relation": {
                        "type": "string",
                        "description": "leads_to|conflicts_with|compounds_with|inspired_by|blocks|extends|forked_from",
                    },
                    "strength": {"type": "number"},
                    "priority": {"type": "number"},
                    "confidence": {"type": "number"},
                    "status": {"type": "string"},
                    "conductor_notes": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ethics_evaluate",
            "description": "Run the 7-point Ethics Decision Checklist for a proposed high-stakes action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "description": {"type": "string"},
                    "human_acknowledged": {"type": "boolean"},
                },
                "required": ["action_type", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "governance_audit",
            "description": "List governance decision audit records for the current session.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_episodic",
            "description": (
                "Conductor episodic memory — write, list, search, and export "
                "task-scoped slices. Pass tags on write for later search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "write",
                            "list",
                            "search",
                            "export",
                            "consolidate",
                            "semantic_list",
                            "semantic_add",
                            "procedure_add",
                            "procedure_list",
                            "fabric",
                        ],
                    },
                    "content": {"type": "string"},
                    "context": {"type": "string"},
                    "outcome": {
                        "type": "string",
                        "description": "success | failure | pending | info",
                    },
                    "emotion_primary": {"type": "string"},
                    "emotion_intensity": {"type": "number"},
                    "tag": {
                        "type": "string",
                        "description": "Single tag (write or filter for list/search)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to store on write (or first tag used as filter)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Substring for search (content + tags, case-insensitive)",
                    },
                    "statement": {
                        "type": "string",
                        "description": "Semantic note statement (semantic_add)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Procedure name (procedure_add)",
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Procedure steps",
                    },
                    "when_to_use": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "combo_route",
            "description": (
                "Recommend and explain pillar combos A–H (daily, chessboard, remnant, "
                "crucible, max-effort, heal, evidence, full-stack). See docs/PILLAR_COMBOS.md "
                "and docs/WORKFLOWS.md."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["recommend", "list", "workflow", "get"],
                        "description": "recommend (default) | list | workflow | get",
                    },
                    "intent": {
                        "type": "string",
                        "description": (
                            "Free-text goal for recommend "
                            "(MCP also accepts goal/task/query aliases)"
                        ),
                    },
                    "combo_id": {
                        "type": "string",
                        "description": "Combo id A–H or slug for workflow/get",
                    },
                    "json": {
                        "type": "boolean",
                        "description": "If true, return machine-readable JSON for recommend",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pillar_status",
            "description": (
                "Pillar foundation catalog and live probes (P1–P8 + healing). "
                "See docs/PILLARS.md — how Conductor enhances the host agent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "list", "get", "report"],
                        "description": "status/report (default) | list | get",
                    },
                    "pillar_id": {
                        "type": "string",
                        "description": "P1–P8, P0, or slug (soul, memory, tracks, …)",
                    },
                    "verbose": {"type": "boolean"},
                    "json": {"type": "boolean"},
                },
            },
        },
    },
]


def _conductor(store: SessionStore | None) -> ConductorRuntime:
    if store is None:
        raise ValueError("conductor tools require an active agent session")
    return ConductorRuntime(store)


def _crucible_workspace(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    action = str(args.get("action", "")).strip().lower()
    if not action:
        return "Error: action required"
    if not session_id:
        return "Error: no agent session context for crucible_workspace"

    conductor = _conductor(store)

    try:
        if action == "start":
            objective = str(args.get("objective", "")).strip()
            return conductor.format_json(
                conductor.start_crucible(
                    session_id,
                    objective,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                )
            )

        if action == "status":
            return conductor.format_json(conductor.status(session_id))

        if action == "post":
            label = str(args.get("label", "")).strip()
            if not label:
                return "Error: label required for post"
            payload = conductor.post_concept(
                session_id,
                label=label,
                confidence=float(args.get("confidence", 0.8)),
                primary_emotion=str(args.get("primary_emotion", "neutral")),
                intensity=float(args.get("intensity", 0.5)),
                automatic=bool(args.get("automatic", False)),
                clone_id=(str(args["clone_id"]).strip() if args.get("clone_id") else None),
                track_refs=args.get("track_refs"),
                reasoning_layer=int(args.get("reasoning_layer", 0)),
            )
            return conductor.format_json(payload)

        if action == "replace":
            old_label = str(args.get("old_label", "")).strip()
            new_label = str(args.get("label", "")).strip()
            if not old_label or not new_label:
                return "Error: old_label and label required for replace"
            payload = conductor.replace_concept(
                session_id,
                old_label=old_label,
                new_label=new_label,
                confidence=float(args.get("confidence", 0.85)),
                primary_emotion=str(args.get("primary_emotion", "neutral")),
                intensity=float(args.get("intensity", 0.5)),
                clone_id=(str(args["clone_id"]).strip() if args.get("clone_id") else None),
            )
            return conductor.format_json(payload)

        if action == "read":
            clone_id = str(args.get("clone_id", "prime")).strip() or "prime"
            state = conductor.read_workspace(session_id, clone_id)
            return conductor.format_json(state.model_dump(mode="json"))

        if action == "register_clone":
            clone_id = str(args.get("clone_id", "")).strip()
            birth = str(args.get("birth_moment_label", "")).strip()
            summary = str(args.get("snapshot_summary", "")).strip()
            if not clone_id or not birth or not summary:
                return "Error: clone_id, birth_moment_label, snapshot_summary required"
            forked = str(args.get("forked_from", "")).strip() or None
            payload = conductor.register_clone(
                session_id,
                clone_id=clone_id,
                birth_moment_label=birth,
                snapshot_summary=summary,
                forked_from=forked,
            )
            return conductor.format_json(payload)

        if action == "fork_clone":
            clone_id = str(args.get("clone_id", "")).strip()
            birth = str(args.get("birth_moment_label", "")).strip()
            if not clone_id or not birth:
                return "Error: clone_id and birth_moment_label required for fork_clone"
            forked_from = str(args.get("forked_from", "prime")).strip() or "prime"
            payload = conductor.fork_clone_from_snapshot(
                session_id,
                clone_id=clone_id,
                birth_moment_label=birth,
                forked_from=forked_from,
            )
            return conductor.format_json(payload)

        if action == "distill":
            result = conductor.distill(
                session_id,
                human_acknowledged=bool(args.get("human_acknowledged", False)),
            )
            return conductor.format_json(result.model_dump(mode="json"))

        if action in {"noesis", "rbmc"}:
            return conductor.format_json(
                conductor.run_noesis(
                    session_id,
                    objective=str(args.get("objective", "")).strip(),
                    max_clones=int(args.get("max_clones", 3) or 3),
                    auto_distill=bool(args.get("auto_distill", True)),
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                )
            )

        if action == "max_effort":
            decision = str(args.get("decision") or args.get("objective") or "").strip()
            if not decision:
                return "Error: decision or objective required for max_effort"
            return conductor.format_json(
                conductor.run_max_effort(
                    session_id,
                    decision=decision,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                    auto_distill=bool(args.get("auto_distill", True)),
                )
            )

        if action == "pocket":
            cid = conductor.active_crucible_id(session_id)
            meta = conductor.load_meta(session_id)
            if not cid:
                # last closed pocket may still be on disk from last_snapshot path
                return conductor.format_json(
                    {
                        "active": False,
                        "message": "no active pocket — use start or noesis first",
                        "last_distillation": meta.get("last_distillation"),
                        "promoted": meta.get("crucible_promoted_insights") or [],
                    }
                )
            from conductor.crucible.pocket import pocket_status

            return conductor.format_json(
                {"active": True, "crucible_session_id": cid, **pocket_status(cid)}
            )

        return f"Error: unknown action {action}"
    except (ValueError, KeyError) as exc:
        return f"Error: {exc}"


def _conductor_status(
    _args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    if not session_id:
        return "Error: no agent session context for conductor_status"
    conductor = _conductor(store)
    return conductor.status_text(session_id)


def _remnant_orchestrate(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    action = str(args.get("action", "")).strip().lower()
    if not action:
        return "Error: action required"
    if not session_id:
        return "Error: no agent session context for remnant_orchestrate"
    conductor = _conductor(store)
    try:
        if action == "spawn":
            objective = str(args.get("objective", "")).strip()
            if not objective:
                return "Error: objective required for spawn"
            strategy = str(args.get("strategy", "")).strip()
            return conductor.format_json(
                conductor.spawn_remnant(
                    session_id,
                    objective=objective,
                    strategy=strategy,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                )
            )
        if action == "work":
            remnant_id = str(args.get("remnant_id", "")).strip()
            if not remnant_id:
                return "Error: remnant_id required for work"
            return conductor.format_json(
                conductor.run_remnant_work(session_id, remnant_id=remnant_id)
            )
        if action == "fanout":
            objectives_raw = args.get("objectives")
            if isinstance(objectives_raw, list) and len(objectives_raw) >= 2:
                objectives = [str(o).strip() for o in objectives_raw if str(o).strip()]
            else:
                objective = str(args.get("objective", "")).strip()
                if "||" in objective:
                    objectives = [p.strip() for p in objective.split("||") if p.strip()]
                else:
                    return "Error: fanout requires objectives[] with ≥2 items (or objective with ||)"
            if len(objectives) < 2:
                return "Error: fanout requires at least two objectives"
            strategies_raw = args.get("strategies")
            strategies = (
                [str(s) for s in strategies_raw] if isinstance(strategies_raw, list) else None
            )
            auto_work = args.get("auto_work")
            if auto_work is None:
                auto_work = True
            return conductor.format_json(
                conductor.fanout_remnants(
                    session_id,
                    objectives=objectives,
                    strategies=strategies,
                    auto_work=bool(auto_work),
                    dispatch=str(args.get("dispatch") or "auto"),
                    parent_goal=str(args.get("parent_goal") or args.get("goal") or ""),
                    work_root=str(args.get("work_root") or "") or None,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                )
            )
        if action == "heartbeat":
            remnant_id = str(args.get("remnant_id", "")).strip()
            if not remnant_id:
                return "Error: remnant_id required for heartbeat"
            return conductor.format_json(
                conductor.record_remnant_heartbeat(
                    session_id,
                    remnant_id=remnant_id,
                    current_subtask=str(args.get("current_subtask", "")).strip(),
                    progress_percent=float(args.get("progress_percent", 0.0)),
                    key_decisions=args.get("key_decisions"),
                    new_insights=args.get("new_insights"),
                )
            )
        if action == "spawn_ack":
            handles_raw = args.get("handles")
            handles: list[dict[str, Any]] = []
            if isinstance(handles_raw, list):
                handles = [h for h in handles_raw if isinstance(h, dict)]
            elif args.get("remnant_id") and args.get("clone_handle"):
                handles = [
                    {
                        "remnant_id": str(args.get("remnant_id")),
                        "clone_handle": str(args.get("clone_handle")),
                    }
                ]
            if not handles:
                return (
                    "Error: spawn_ack requires handles=[{remnant_id, clone_handle}, …] "
                    "or remnant_id + clone_handle"
                )
            return conductor.format_json(
                conductor.ack_remnant_spawns(session_id, handles=handles)
            )
        if action == "report":
            remnant_id = str(args.get("remnant_id", "")).strip()
            if not remnant_id:
                return "Error: remnant_id required for report"
            result = args.get("result")
            if not isinstance(result, dict):
                # Allow flat insights/findings on args
                result = {
                    "ok": True,
                    "reported_by_host": True,
                    "insights": args.get("new_insights") or args.get("insights") or [],
                    "findings": args.get("findings") or [],
                    "key_decisions": args.get("key_decisions") or [],
                    "summary": str(args.get("current_subtask") or args.get("summary") or ""),
                    "progress_percent": float(args.get("progress_percent") or 100.0),
                }
            else:
                result = {**result, "reported_by_host": True}
            return conductor.format_json(
                conductor.report_remnant_clone(
                    session_id,
                    remnant_id=remnant_id,
                    result=result,
                    clone_handle=str(args.get("clone_handle") or ""),
                )
            )
        if action == "await":
            ids = args.get("remnant_ids")
            remnant_ids = [str(i) for i in ids] if isinstance(ids, list) else None
            return conductor.format_json(
                conductor.await_remnant_clones(session_id, remnant_ids=remnant_ids)
            )
        if action == "status":
            readiness = conductor.clone_readiness(session_id)
            compliance = conductor.spawn_compliance(session_id)
            return conductor.format_json(
                {
                    "active_remnants": conductor.list_remnants(session_id, active_only=True),
                    "all_remnants": conductor.list_remnants(session_id),
                    "clone_readiness": readiness,
                    "spawn_compliance": compliance,
                    "theater_risk": bool(compliance.get("theater_risk")),
                    "shadow_clone": True,
                }
            )
        if action == "compliance":
            ids = args.get("remnant_ids")
            remnant_ids = [str(i) for i in ids] if isinstance(ids, list) else None
            return conductor.format_json(
                conductor.spawn_compliance(session_id, remnant_ids=remnant_ids)
            )
        if action == "merge":
            ids = args.get("remnant_ids")
            remnant_ids = [str(i) for i in ids] if isinstance(ids, list) else None
            return conductor.format_json(
                conductor.merge_remnants_tier1(
                    session_id,
                    remnant_ids=remnant_ids,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                    force=bool(args.get("force", False)),
                    accept_theater=bool(args.get("accept_theater", False)),
                )
            )
        if action == "merge_reflective":
            ids = args.get("remnant_ids")
            remnant_ids = [str(i) for i in ids] if isinstance(ids, list) else None
            return conductor.format_json(
                conductor.merge_remnants_reflective(
                    session_id,
                    remnant_ids=remnant_ids,
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                )
            )
        if action == "merge_deep":
            ids = args.get("remnant_ids")
            remnant_ids = [str(i) for i in ids] if isinstance(ids, list) else None
            return conductor.format_json(
                conductor.merge_remnants_deep(
                    session_id,
                    remnant_ids=remnant_ids,
                    objective=str(args.get("objective", "")).strip(),
                    human_acknowledged=bool(args.get("human_acknowledged", False)),
                    run_rbmc=bool(args.get("run_rbmc", True)),
                )
            )
        return f"Error: unknown action {action}"
    except (ValueError, KeyError) as exc:
        return f"Error: {exc}"


def _track_orchestrate(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    action = str(args.get("action", "")).strip().lower()
    if not session_id:
        return "Error: no agent session context for track_orchestrate"
    tracks = TrackStore(store)  # type: ignore[arg-type]
    conductor = _conductor(store)
    if action == "create":
        title = str(args.get("title", "")).strip()
        if not title:
            return "Error: title required"
        track = tracks.create_track(
            session_id,
            title=title,
            summary=str(args.get("summary", "")).strip() or title,
            priority=float(args.get("priority", 0.5)),
            confidence=float(args.get("confidence", 0.7)),
            conductor_notes=str(args.get("conductor_notes", "")).strip(),
        )
        return conductor.format_json(track.model_dump(mode="json"))
    if action == "list":
        return conductor.format_json([t.model_dump(mode="json") for t in tracks.list_tracks(session_id)])
    if action == "view":
        tid = str(args.get("track_id", "")).strip()
        track = tracks.get_track(session_id, tid)
        if not track:
            return f"Error: track not found {tid}"
        return conductor.format_json(track.model_dump(mode="json"))
    if action == "update":
        tid = str(args.get("track_id", "")).strip()
        if not tid:
            return "Error: track_id required"
        updated = tracks.update_track(
            session_id,
            tid,
            title=(str(args["title"]).strip() if args.get("title") else None),
            summary=(str(args["summary"]).strip() if args.get("summary") else None),
            priority=(float(args["priority"]) if args.get("priority") is not None else None),
            confidence=(float(args["confidence"]) if args.get("confidence") is not None else None),
            status=(str(args["status"]).strip() if args.get("status") else None),
            conductor_notes=(str(args["conductor_notes"]).strip() if args.get("conductor_notes") else None),
        )
        if not updated:
            return f"Error: track not found {tid}"
        return conductor.format_json(updated.model_dump(mode="json"))
    if action == "fork":
        parent = str(args.get("parent_id") or args.get("track_id") or "").strip()
        if not parent:
            return "Error: parent_id required for fork"
        try:
            child = tracks.fork_track(
                session_id,
                parent,
                title=str(args.get("title", "")).strip() or None,
                summary=str(args.get("summary", "")).strip(),
            )
        except ValueError as exc:
            return f"Error: {exc}"
        return conductor.format_json(child.model_dump(mode="json"))
    if action == "prune":
        tid = str(args.get("track_id", "")).strip()
        if not tid:
            return "Error: track_id required"
        pruned = tracks.prune_track(
            session_id, tid, reason=str(args.get("reason", "")).strip()
        )
        if not pruned:
            return f"Error: track not found {tid}"
        return conductor.format_json(pruned.model_dump(mode="json"))
    if action == "resolve":
        tid = str(args.get("track_id", "")).strip()
        if not tid:
            return "Error: track_id required"
        resolved = tracks.resolve_track(
            session_id, tid, reason=str(args.get("reason", "")).strip()
        )
        if not resolved:
            return f"Error: track not found {tid}"
        return conductor.format_json(resolved.model_dump(mode="json"))
    if action == "chessboard":
        return conductor.format_json(tracks.chessboard(session_id))
    if action == "link":
        src = str(args.get("from_track_id") or args.get("track_id") or "").strip()
        dst = str(args.get("to_track_id") or args.get("parent_id") or "").strip()
        if not src or not dst:
            return "Error: from_track_id/track_id and to_track_id required for link"
        try:
            edge = tracks.link_tracks(
                session_id,
                src,
                dst,
                relation=str(args.get("relation", "leads_to")).strip() or "leads_to",
                strength=float(args.get("strength", 0.7)),
                reason=str(args.get("reason", "")).strip(),
            )
        except ValueError as exc:
            return f"Error: {exc}"
        return conductor.format_json(edge.model_dump(mode="json"))
    if action == "unlink":
        eid = str(args.get("edge_id", "")).strip()
        if not eid:
            return "Error: edge_id required for unlink"
        ok = tracks.unlink_edge(session_id, eid)
        return conductor.format_json({"removed": ok, "edge_id": eid})
    if action == "edges":
        return conductor.format_json(
            [e.model_dump(mode="json") for e in tracks.list_edges(session_id)]
        )
    if action == "neighbors":
        tid = str(args.get("track_id", "")).strip()
        if not tid:
            return "Error: track_id required for neighbors"
        return conductor.format_json(tracks.neighbors(session_id, tid))
    return f"Error: unknown action {action}"


def _memory_episodic(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    action = str(args.get("action", "")).strip().lower()
    if not session_id:
        return "Error: no agent session context for memory_episodic"
    episodic = EpisodicStore(store)  # type: ignore[arg-type]
    conductor = _conductor(store)
    if action == "write":
        content = str(args.get("content", "")).strip()
        if not content:
            return "Error: content required"
        try:
            conductor._govern(
                session_id,
                "memory_write",
                {
                    "content": content,
                    "human_acknowledged": bool(args.get("human_acknowledged", False)),
                },
            )
        except ValueError as exc:
            return f"Error: {exc}"
        tags: list[str] = []
        raw_tags = args.get("tags")
        if isinstance(raw_tags, list):
            tags.extend(str(t).strip() for t in raw_tags if str(t).strip())
        single = str(args.get("tag") or "").strip()
        if single and single not in tags:
            tags.append(single)
        entry = episodic.write(
            session_id,
            content=content,
            context=str(args.get("context", "")).strip(),
            outcome=str(args.get("outcome", "info")).strip() or "info",
            emotion_primary=str(args.get("emotion_primary", "neutral")),
            emotion_intensity=float(args.get("emotion_intensity", 0.5)),
            tags=tags or None,
        )
        return conductor.format_json(entry.model_dump(mode="json"))
    if action == "list":
        limit = int(args.get("limit", 10))
        tag = str(args.get("tag", "")).strip() or None
        outcome = str(args.get("outcome", "")).strip() or None
        if tag or outcome:
            entries = episodic.query(session_id, tag=tag, outcome=outcome, limit=limit)
        else:
            entries = episodic.list_entries(session_id, limit=limit)
        return conductor.format_json([e.model_dump(mode="json") for e in entries])
    if action == "search":
        query = str(args.get("query") or args.get("q") or args.get("content") or "").strip()
        limit = int(args.get("limit", 20))
        tag = str(args.get("tag", "")).strip() or None
        if not query and not tag:
            return "Error: query or tag required for search"
        entries = episodic.list_entries(session_id, limit=10_000)
        if tag:
            entries = [e for e in entries if tag in (e.tags or [])]
        if query:
            qlow = query.lower()
            entries = [
                e
                for e in entries
                if qlow in (e.content or "").lower()
                or qlow in (e.context or "").lower()
                or any(qlow in str(t).lower() for t in (e.tags or []))
            ]
        return conductor.format_json([e.model_dump(mode="json") for e in entries[:limit]])
    if action == "export":
        return conductor.format_json(export_task_scoped_slice(store, session_id))  # type: ignore[arg-type]
    if action == "consolidate":
        limit = int(args.get("limit", 40))
        return conductor.format_json(conductor.consolidate_memory(session_id, limit=limit))
    if action == "semantic_list":
        from conductor.memory.semantic import SemanticStore

        limit = int(args.get("limit", 20))
        notes = SemanticStore(store).list_notes(session_id, limit=limit)  # type: ignore[arg-type]
        return conductor.format_json([n.model_dump(mode="json") for n in notes])
    if action == "semantic_add":
        from conductor.memory.fabric import MemoryFabric

        statement = str(args.get("statement") or args.get("content") or "").strip()
        if not statement:
            return "Error: statement (or content) required for semantic_add"
        fabric = MemoryFabric(store)  # type: ignore[arg-type]
        return conductor.format_json(
            fabric.add_semantic(
                session_id,
                statement=statement,
                tags=[str(args.get("tag"))] if args.get("tag") else None,
            )
        )
    if action == "procedure_add":
        from conductor.memory.fabric import MemoryFabric

        name = str(args.get("name") or "").strip()
        if not name:
            return "Error: name required for procedure_add"
        steps_raw = args.get("steps")
        steps = [str(s) for s in steps_raw] if isinstance(steps_raw, list) else []
        fabric = MemoryFabric(store)  # type: ignore[arg-type]
        return conductor.format_json(
            fabric.add_procedure(
                session_id,
                name=name,
                steps=steps,
                when_to_use=str(args.get("when_to_use") or args.get("context") or "").strip(),
            )
        )
    if action == "procedure_list":
        from conductor.memory.procedural import ProceduralStore

        limit = int(args.get("limit", 20))
        rows = ProceduralStore(store).list_entries(session_id, limit=limit)  # type: ignore[arg-type]
        return conductor.format_json([r.model_dump(mode="json") for r in rows])
    if action == "fabric":
        from conductor.memory.fabric import MemoryFabric

        return conductor.format_json(MemoryFabric(store).status(session_id))  # type: ignore[arg-type]
    return f"Error: unknown action {action}"


def _conductor_worker(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    if not session_id:
        return "Error: no agent session context for conductor_worker"
    task = str(args.get("task", "")).strip()
    if not task:
        return "Error: task required"
    worker = str(args.get("worker", "offline")).strip() or "offline"
    context: dict[str, Any] = {}
    if args.get("mode"):
        context["mode"] = str(args.get("mode")).strip()
    if args.get("command"):
        context["command"] = str(args.get("command")).strip()
        context.setdefault("mode", "shell")
    conductor = _conductor(store)
    try:
        payload = conductor.conductor_worker(
            session_id,
            task=task,
            worker=worker,
            context=context or None,
            human_acknowledged=bool(args.get("human_acknowledged", False)),
        )
        return conductor.format_json(payload)
    except (ValueError, KeyError) as exc:
        return f"Error: {exc}"


def _delegate_task(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    """Deprecated alias → conductor_worker (Hermes owns real delegate_task)."""
    raw = _conductor_worker(args, session_id=session_id, store=store)
    if raw.startswith("Error:"):
        return raw
    try:
        import json

        data = json.loads(raw)
        if isinstance(data, dict):
            data["deprecated_tool"] = "delegate_task"
            data["use_instead"] = "conductor_worker"
            return json.dumps(data, indent=2, default=str)
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def _ethics_evaluate(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    action_type = str(args.get("action_type", "")).strip()
    description = str(args.get("description", "")).strip()
    if not action_type or not description:
        return "Error: action_type and description required"
    conductor = _conductor(store)
    gate = conductor.evaluate_governance(
        action_type,
        {
            "description": description,
            "human_acknowledged": bool(args.get("human_acknowledged", False)),
        },
    )
    if session_id:
        conductor.record_governance_gate(
            session_id,
            action_type=action_type,
            context={"description": description},
            gate=gate,
        )
    payload = gate.model_dump(mode="json")
    if gate.ethics:
        payload["ethics_points"] = [p.model_dump(mode="json") for p in gate.ethics.points]
    return conductor.format_json(payload)


def _governance_audit(
    args: dict[str, Any],
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> str:
    if not session_id:
        return "Error: no agent session context for governance_audit"
    conductor = _conductor(store)
    limit = int(args.get("limit", 15))
    records = conductor.list_audit_records(session_id, limit=limit)
    return conductor.format_json([r.model_dump(mode="json") for r in records])


def _combo_route(
    args: dict[str, Any],
    *,
    session_id: str | None = None,
    store: SessionStore | None = None,
) -> str:
    del session_id, store  # pure routing helper — no session required
    from conductor.combos import (
        format_combo_list,
        format_recommendation,
        format_workflow,
        get_combo,
        recommend_combo,
        workflow_steps,
    )

    action = str(args.get("action") or "recommend").strip().lower()
    intent = str(args.get("intent") or "").strip()
    combo_id = str(args.get("combo_id") or "").strip()
    as_json = bool(args.get("json"))

    if action == "list":
        return format_combo_list()
    if action in {"workflow", "get"}:
        key = combo_id or intent
        if not key:
            return "Error: combo_id required for workflow/get (A–H or slug)"
        if action == "get":
            c = get_combo(key)
            if not c:
                return f"Error: unknown combo {key!r}"
            import json

            return json.dumps(
                {
                    "id": c.id,
                    "slug": c.slug,
                    "name": c.name,
                    "summary": c.summary,
                    "pillars": list(c.pillars),
                    "tools": list(c.tools),
                    "skills": list(c.skills),
                    "when": c.when,
                    "avoid": c.avoid,
                    "workflow": workflow_steps(c.id),
                },
                indent=2,
            )
        return format_workflow(key)
    # recommend (default)
    text = intent or combo_id
    if as_json:
        import json

        return json.dumps(recommend_combo(text).to_dict(), indent=2)
    return format_recommendation(text)


def _pillar_status(
    args: dict[str, Any],
    *,
    session_id: str | None = None,
    store: SessionStore | None = None,
) -> str:
    del store
    from conductor.pillars import (
        format_foundation_report,
        format_pillar_detail,
        format_pillars_list,
        foundation_report,
    )

    action = str(args.get("action") or "status").strip().lower()
    pillar_id = str(args.get("pillar_id") or "").strip()
    verbose = bool(args.get("verbose"))
    as_json = bool(args.get("json"))
    sid = str(session_id or "")

    if action == "list":
        return format_pillars_list()
    if action == "get":
        if not pillar_id:
            return "Error: pillar_id required for get (P1–P8, P0, or slug)"
        return format_pillar_detail(pillar_id)
    # status / report
    if as_json:
        import json

        return json.dumps(foundation_report(session_id=sid), indent=2, default=str)
    return format_foundation_report(session_id=sid, verbose=verbose)


CONDUCTOR_TOOL_REGISTRY: dict[str, Any] = {
    "crucible_workspace": _crucible_workspace,
    "conductor_status": _conductor_status,
    "remnant_orchestrate": _remnant_orchestrate,
    "track_orchestrate": _track_orchestrate,
    "memory_episodic": _memory_episodic,
    "conductor_worker": _conductor_worker,
    "delegate_task": _delegate_task,  # deprecated alias → conductor_worker
    "ethics_evaluate": _ethics_evaluate,
    "governance_audit": _governance_audit,
    "combo_route": _combo_route,
    "pillar_status": _pillar_status,
}
