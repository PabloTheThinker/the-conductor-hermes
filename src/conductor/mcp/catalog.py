"""Build MCP tool catalog from Conductor OpenAI-style tool schemas.

Excludes host file/shell tools that Claude/Codex/Grok already provide natively.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# Clients (Claude Code, Codex, Cursor) already have these — avoid clashing.
_HOST_NATIVE_SKIP = frozenset(
    {
        "read_file",
        "write_file",
        "run_shell",
        "terminal",
        "process",
        "patch",
        "search_files",
        "bash",
        "shell",
    }
)


@dataclass(frozen=True)
class McpToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]
    source: str  # conductor | research | agent


def _inject_session_id(params: dict[str, Any]) -> dict[str, Any]:
    """Ensure session_id is discoverable on every Continuity-bearing tool schema."""
    props = dict(params.get("properties") or {})
    if "session_id" not in props:
        props["session_id"] = {
            "type": "string",
            "description": (
                "Session id from conductor_session. Pass the same id across "
                "tracks, memory, remnants, crucible, and ethics for continuity."
            ),
        }
    out = {**params, "type": params.get("type") or "object", "properties": props}
    return out


def _from_openai_schema(schema: dict[str, Any], *, source: str) -> McpToolDef | None:
    fn = schema.get("function") if schema.get("type") == "function" else schema
    if not isinstance(fn, dict):
        return None
    name = str(fn.get("name") or "").strip()
    if not name or name in _HOST_NATIVE_SKIP:
        return None
    params = fn.get("parameters") or {"type": "object", "properties": {}}
    if not isinstance(params, dict):
        params = {"type": "object", "properties": {}}
    # Ensure JSON-schema object shape
    if "type" not in params:
        params = {**params, "type": "object"}
    params = _inject_session_id(params)
    return McpToolDef(
        name=name,
        description=str(fn.get("description") or f"Conductor tool {name}"),
        input_schema=params,
        source=source,
    )


def tool_definitions(*, include_agent: bool = True) -> list[McpToolDef]:
    """All MCP-exposed Conductor tools (deduped by name)."""
    from conductor.core.tools import CONDUCTOR_TOOL_SCHEMAS
    from conductor.research.tools import RESEARCH_TOOL_SCHEMAS

    seen: set[str] = set()
    out: list[McpToolDef] = []

    for schema, source in (
        *[(s, "conductor") for s in CONDUCTOR_TOOL_SCHEMAS],
        *[(s, "research") for s in RESEARCH_TOOL_SCHEMAS],
    ):
        d = _from_openai_schema(schema, source=source)
        if d and d.name not in seen:
            seen.add(d.name)
            out.append(d)

    if include_agent:
        try:
            from conductor.agent.tools import TOOL_SCHEMAS

            for schema in TOOL_SCHEMAS:
                d = _from_openai_schema(schema, source="agent")
                if d and d.name not in seen:
                    # Prefer non-host-native agent tools (skills, heal, verify)
                    if d.name in _HOST_NATIVE_SKIP:
                        continue
                    seen.add(d.name)
                    out.append(d)
        except Exception:  # noqa: BLE001
            pass

    # Meta tools always available
    for meta in _meta_tools():
        if meta.name not in seen:
            seen.add(meta.name)
            out.append(meta)
    return out


def _meta_tools() -> list[McpToolDef]:
    """MCP-native helpers (module info, session, resonance, start pack)."""
    return [
        McpToolDef(
            name="conductor_start_pack",
            description=(
                "PREFERRED first call. Returns orchestration mode thin|full, session_id, "
                "combo, axes, fanout_ready (host clones), and the exact recipe. "
                "Thin = no remnant ritual. Full = host spawn_subagent shadow clones."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "What you are about to build or fix",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional session title (defaults from goal)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Reuse existing session if known",
                    },
                    "open_track": {
                        "type": "boolean",
                        "description": "Create track (default: true only in full mode)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "thin", "full"],
                        "description": "Force thin/full or auto-classify (default auto)",
                    },
                    "work_root": {
                        "type": "string",
                        "description": "Optional repo root for hybrid/local clone preflight",
                    },
                },
            },
            source="mcp",
        ),
        McpToolDef(
            name="conductor_module_info",
            description=(
                "Full module metadata + pillar catalog. Prefer conductor_start_pack "
                "for task start; use this for deep discovery."
            ),
            input_schema={"type": "object", "properties": {}},
            source="mcp",
        ),
        McpToolDef(
            name="conductor_system_prompt",
            description=(
                "Build Soul Resonance system prompt (meister host soul + Conductor "
                "partner). Optional host_soul path or text."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "host_soul": {
                        "type": "string",
                        "description": "Path to host SOUL.md or inline text",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["resonate", "solo", "host_only"],
                        "description": "Soul mode (default resonate)",
                    },
                },
            },
            source="mcp",
        ),
        McpToolDef(
            name="conductor_session",
            description=(
                "Get or create a durable Conductor session id for tool continuity "
                "(memory, tracks, remnants). Prefer conductor_start_pack which includes this."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Existing session id (optional)",
                    },
                    "title": {"type": "string"},
                },
            },
            source="mcp",
        ),
    ]


def build_mcp_catalog() -> dict[str, Any]:
    """Machine-readable catalog for docs / discovery."""
    from conductor import __version__

    tools = tool_definitions()
    return {
        "name": "the-conductor",
        "version": __version__,
        "product_line": "The Conductor enhances the agent that uses it",
        "protocol": "mcp",
        "transport": ["stdio"],
        "tool_count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "source": t.source,
                "input_schema": t.input_schema,
            }
            for t in tools
        ],
        "resources": [
            "conductor://module",
            "conductor://pillars",
            "conductor://soul",
            "conductor://skills",
            "conductor://combos",
        ],
        "prompts": ["system", "resonate", "plan"],
    }


def _normalize_mcp_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Map common model mistakes to canonical tool args (MCP live-drive DX).

    Models often invent ``goal``/``name``/``search`` from natural language.
    Soft string errors ("title required") look like success to clients that only
    check for exceptions — normalize here so the first call works.
    """
    out = dict(args)

    # Universal free-text → intent/title helpers
    if name == "combo_route":
        if not str(out.get("intent") or "").strip():
            for key in ("goal", "task", "query", "task_type", "prompt"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["intent"] = str(val).strip()
                    break
        # task_type alone is weak — if both goal+task_type present, prefer goal
        if out.get("goal") and out.get("task_type"):
            out["intent"] = str(out["goal"]).strip()

    if name == "conductor_session":
        if not str(out.get("title") or "").strip():
            for key in ("goal", "name", "description", "objective"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["title"] = str(val).strip()[:200]
                    break
        # action: create is implied when no session_id

    if name == "track_orchestrate":
        action = str(out.get("action") or "").strip().lower()
        if not str(out.get("title") or "").strip():
            for key in ("name", "goal", "label"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["title"] = str(val).strip()
                    break
        if not str(out.get("summary") or "").strip():
            for key in ("description", "desc", "objective"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["summary"] = str(val).strip()
                    break
        # Graph aliases: add_edge / connect → link
        if action in {"add_edge", "connect", "edge"}:
            out["action"] = "link"
            if out.get("from_node") and not out.get("from_track_id"):
                out["from_track_id"] = out.get("from_node")
            if out.get("to_node") and not out.get("to_track_id"):
                out["to_track_id"] = out.get("to_node")
            if out.get("edge_type") and not out.get("relation"):
                out["relation"] = out.get("edge_type")

    if name == "memory_episodic":
        action = str(out.get("action") or "").strip().lower()
        # search / find / query → native search (content + tag match)
        if action in {"search", "find", "query", "read"}:
            out["action"] = "search"
            if not out.get("query"):
                q = out.get("q") or out.get("content")
                if q is not None and str(q).strip():
                    out["query"] = str(q).strip()
        # tags list → tag filter for list; write path also accepts tags
        tags = out.get("tags")
        if isinstance(tags, list) and tags and not out.get("tag"):
            out["tag"] = str(tags[0])

    if name == "ethics_evaluate":
        if not str(out.get("description") or "").strip():
            for key in ("proposal", "action", "goal", "content", "text"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["description"] = str(val).strip()
                    break
        if not str(out.get("action_type") or "").strip():
            # action: evaluate is not the ethics action_type
            at = out.get("action")
            if at and str(at).strip().lower() not in {"evaluate", "check", "audit"}:
                out["action_type"] = str(at).strip()
            else:
                out["action_type"] = "general"

    if name == "remnant_orchestrate":
        if not str(out.get("objective") or "").strip():
            for key in ("content", "goal", "task", "description"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["objective"] = str(val).strip()
                    break
        # tier alone with merge and content: still need spawn first — leave merge as-is

    if name in {"delegate_task", "conductor_worker"}:
        if not str(out.get("task") or "").strip():
            for key in ("goal", "objective", "description", "prompt"):
                val = out.get(key)
                if val is not None and str(val).strip():
                    out["task"] = str(val).strip()
                    break
        # Always route alias to conductor_worker handler via registry name
        if name == "delegate_task":
            # leave name as-is for registry alias; payload is worker task
            pass

    return out


def _dispatch_start_pack(args: dict[str, Any], *, sid: str) -> str:
    """Compact onboarding pack — thin vs full orchestration (research-backed)."""
    from conductor import __version__
    from conductor.combos import recommend_combo, workflow_steps
    from conductor.core.orchestration import (
        classify_orchestration,
        fanout_payload_from_policy,
    )
    from conductor.session.store import default_session_store

    goal = str(args.get("goal") or args.get("intent") or args.get("task") or "").strip()
    title = str(args.get("title") or "").strip() or (goal[:80] if goal else "conductor-session")
    force = str(args.get("mode") or "auto").strip().lower()
    force_mode = force if force in {"thin", "full"} else None
    work_root = str(args.get("work_root") or "").strip() or None

    policy = classify_orchestration(goal, force_mode=force_mode)
    mode = policy["mode"]

    open_track = args.get("open_track")
    if open_track is None:
        open_track = bool(goal) and policy.get("open_track_default", False)

    store = default_session_store()
    if sid:
        rec = store.get_session(sid) or store.resolve_session(sid)
        if not rec:
            rec = store.create_session(source="mcp", title=title)
    else:
        rec = store.create_session(source="mcp", title=title)
    session_id = rec.id

    rec_combo = recommend_combo(goal) if goal else recommend_combo("daily coding")
    # Align combo with full multi-axis when policy says full
    if mode == "full" and rec_combo.primary.id == "A":
        from conductor.combos.catalog import COMBOS

        rec_combo.primary = COMBOS["C"]
        rec_combo.rationale = [
            "Overrode A→C: orchestration policy full multi-axis (host shadow clones).",
            *list(rec_combo.rationale)[:3],
        ]
    combo_id = rec_combo.primary.id
    workflow = workflow_steps(combo_id)

    track_id = None
    if open_track and goal:
        from conductor.tracks.store import TrackStore

        tr = TrackStore(store).create_track(
            session_id,
            title=title[:120] or "Work",
            summary=goal[:500],
            priority=0.7 if mode == "full" else 0.5,
            confidence=0.6,
        )
        track_id = tr.track_id

    foundation: dict[str, Any] = {"ok": None}
    try:
        from conductor.pillars import foundation_report

        report = foundation_report()
        foundation = {
            "ok": report.get("ok"),
            "passed": report.get("passed"),
            "total": report.get("total"),
        }
    except Exception:  # noqa: BLE001
        pass

    fanout_ready = fanout_payload_from_policy(
        policy, parent_goal=goal, work_root=work_root
    )
    if fanout_ready:
        fanout_ready["session_id"] = session_id

    if mode == "thin":
        loop = list(policy["recipe"]["steps"])
        high_signal = [
            {"name": "conductor_start_pack", "when": "session start (done)"},
            {
                "name": "memory_episodic",
                "when": "after ship — tags preferred",
            },
        ]
        if track_id:
            high_signal.append(
                {"name": "track_orchestrate", "when": "optional resolve only"}
            )
        skip = [
            "remnant_orchestrate fanout — thin mode forbids ritual",
            "pillar_status",
            "conductor_module_info",
            "governance_audit",
            "crucible_workspace",
            "heal_*",
        ]
        next_step = (
            "THIN MODE: use host tools only. Skip remnants. "
            "Optional memory_episodic when done."
        )
    else:
        loop = list(policy["recipe"]["steps"])
        high_signal = [
            {"name": "conductor_start_pack", "when": "done"},
            {
                "name": "remnant_orchestrate",
                "when": "NOW — fanout with dispatch=host (see fanout_ready)",
                "args": fanout_ready,
                "note": (
                    "MCP cannot spawn. After fanout: PARENT calls spawn_subagent "
                    "(Grok) or hermes_batch delegate_task (Hermes), then "
                    "spawn_ack → report → merge"
                ),
            },
            {
                "name": "spawn_subagent",
                "when": "PARENT-NATIVE (not MCP) — after fanout, parallel for each tool_calls[i]",
                "note": "Grok host tool only; use exact tool_calls[i].arguments",
            },
            {
                "name": "memory_episodic",
                "when": "after merge",
            },
            {
                "name": "track_orchestrate",
                "when": "resolve when done",
            },
        ]
        skip = [
            "pillar_status spam",
            "dispatch=local unless host cannot spawn",
            "governance_audit unless high-stakes",
            "implementing all axes yourself without spawning tool_calls",
        ]
        next_step = (
            "FULL MODE: remnant_orchestrate fanout → PARENT spawns host tools "
            "THIS turn (not MCP) → spawn_ack → report each → merge."
        )

    pack = {
        "name": "the-conductor",
        "version": __version__,
        "product_line": "The Conductor enhances the agent that uses it",
        "session_id": session_id,
        "title": rec.title,
        "goal": goal or None,
        "track_id": track_id,
        "foundation": foundation,
        "orchestration": policy,
        "combo": {
            "primary": combo_id,
            "name": rec_combo.primary.name,
            "summary": rec_combo.primary.summary,
            "secondary": [c.id for c in rec_combo.secondary],
            "workflow": workflow,
            "rationale": list(rec_combo.rationale)[:5],
        },
        "loop": loop,
        "high_signal_tools": high_signal,
        "skip_unless_needed": skip,
        "fanout_ready": fanout_ready,
        "remnant_policy": {
            "mode": mode,
            "use_when": "full multi-axis — host shadow clones (spawn_subagent / Task / hermes)",
            "skip_when": "thin mode — single path, ops, Q&A, quick fix",
            "fanout_gives": (
                "work_packs + tool_calls + parent_must_spawn + protocol + "
                "hermes_batch (Hermes) + parent_checklist"
            ),
            "merge_gives": "merged_insights (filler-stripped) + host_playbook",
            "host_loop": (
                "fanout → PARENT spawns host tools (not MCP) → spawn_ack → report → merge"
            ),
            "mcp_cannot_spawn": True,
            "hosts": {
                "grok": "spawn_subagent(prompt, description, subagent_type, background)",
                "claude": "Task(description, prompt)",
                "hermes": "delegate_task(goal, context) or hermes_batch tasks[]",
            },
            "metaphor": "Naruto shadow clone jutsu — one will, many bodies, merge back",
            "recommended_now": bool(policy.get("fanout_recommended")),
            "dispatch_default": policy.get("dispatch_default"),
        },
        "next": next_step,
        # Cognitive weight reducer (1.18.6): one path, not the whole ontology
        "simple_path": (
            "thin: host tools → optional memory_episodic"
            if mode == "thin"
            else (
                "full: fanout → PARENT spawn tool_calls → spawn_ack → report → merge → "
                "memory_episodic (skip pillars/crucible unless blocked)"
            )
        ),
        "judgment": {
            "done_equals_proven": True,
            "fold_combo_g": bool(rec_combo.fold_g) or mode == "full",
            "require_for_done": (
                [
                    "real host spawn handles (not invented report)",
                    "merge insights with paths/tests/URLs or host pytest/serve",
                    "memory_episodic outcome with tags",
                ]
                if mode == "full"
                else ["host tool evidence (path write / shell verify) for code goals"]
            ),
            "note": (
                "Claiming done without evidence is false Judgment. "
                "Use remnant action=compliance to detect spawn theater."
            ),
        },
        "operator_flow": "docs/OPERATOR_FLOW.md",
    }
    return json.dumps(pack, indent=2, default=str)


def is_tool_error_payload(text: str) -> bool:
    """True when a tool result is a soft failure (string Error: or JSON error).

    MCP clients that only check transport exceptions miss these — the server
    should surface them with CallToolResult.isError=True.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    if raw.startswith("Error:") or raw.startswith("Error "):
        return True
    if raw.lower().startswith("unknown tool"):
        return True
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("error"):
        return True
    if data.get("ok") is False or data.get("success") is False:
        # merge with success:false and empty remnant guidance
        msg = str(data.get("message") or data.get("summary") or data.get("error") or "")
        if data.get("error") or "no active remnant" in msg.lower():
            return True
        # success:false without explicit error is still a failure
        if data.get("success") is False:
            return True
    return False


def dispatch_tool(
    name: str,
    arguments: dict[str, Any] | None,
    *,
    session_id: str = "",
) -> str:
    """Execute a Conductor tool by name for MCP call_tool."""
    args = _normalize_mcp_args(name, dict(arguments or {}))
    # Allow session_id in args or explicit param
    sid = str(args.pop("session_id", "") or session_id or "").strip()

    if name == "conductor_start_pack":
        return _dispatch_start_pack(args, sid=sid)

    if name == "conductor_module_info":
        from conductor.harness import module_info

        return json.dumps(module_info(), indent=2, default=str)

    if name == "conductor_system_prompt":
        from conductor.harness import get_system_prompt

        mode = args.get("mode")
        host = args.get("host_soul")
        return get_system_prompt(
            host_soul=str(host) if host else None,
            mode=str(mode) if mode else None,
            search_host=not bool(host),
        )

    if name == "conductor_session":
        from conductor.session.store import default_session_store

        store = default_session_store()
        if sid:
            rec = store.get_session(sid) or store.resolve_session(sid)
            if rec:
                return json.dumps({"session_id": rec.id, "title": rec.title, "existing": True})
        rec = store.create_session(
            source="mcp",
            title=str(args.get("title") or "mcp-session"),
        )
        return json.dumps({"session_id": rec.id, "title": rec.title, "existing": False})

    # Core + research registries
    from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY
    from conductor.research.tools import RESEARCH_TOOL_REGISTRY
    from conductor.session.store import default_session_store

    store = default_session_store()
    if not sid:
        sid = store.create_session(source="mcp").id

    if name in CONDUCTOR_TOOL_REGISTRY:
        fn = CONDUCTOR_TOOL_REGISTRY[name]
        try:
            return str(fn(args, session_id=sid, store=store))
        except TypeError:
            return str(fn(args))

    if name in RESEARCH_TOOL_REGISTRY:
        fn = RESEARCH_TOOL_REGISTRY[name]
        return str(fn(args))

    # Agent tools (heal, skills, etc.)
    try:
        from conductor.agent import tools as agent_tools

        return agent_tools.execute_tool(name, args, session_id=sid, store=store)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "tool": name})
