"""Wave planner — tool classes + A→B→C ordering for host tool batches.

Hermes segments large mixed tool batches at the host layer. Conductor does **not**
reimplement that scheduler. This module only:

1. Classifies tools into ``safe_parallel`` | ``barrier`` | ``spawn``
2. Groups planned calls into waves (A reads → B writes → C spawns)
3. Attaches wave metadata to fanout / hermes_batch contracts so parents know order

Wave model (stable contract):
  A — reads / status / doctor / probes (safe_parallel)
  B — writes / patches / commits (barrier — serial within host segment if needed)
  C — delegate_task / remnant / spawn_subagent (spawn — prefer one batch tool)

Parent agents should still emit **one large mixed batch** when the host supports
segmented execution; waves are advisory labels + thrash/batch ids, not a second
scheduler.
"""

from __future__ import annotations

from typing import Any, Literal

ToolClass = Literal["safe_parallel", "barrier", "spawn"]
WaveId = Literal["A", "B", "C"]

# Primary tables — exact names first, then prefix heuristics.
# Keep aligned with host-safe reads; expand as Hermes adds observer tools.
_SAFE_PARALLEL: frozenset[str] = frozenset(
    {
        "read_file",
        "search_files",
        "web_search",
        "web_extract",
        "open_page",
        "open_page_with_find",
        "session_search",
        "skill_view",
        "skills_list",
        "memory_episodic",
        "conductor_status",
        "pillar_status",
        "heal_status",
        "verification_list",
        "research_list",
        "research_view",
        "combo_route",
        "x_search",
        "vision_analyze",
        # doctor / readiness (read-only probes)
        "doctor",
        "hermes_ready",
        # more Hermes / Conductor read-only probes (wave A)
        "web_search_with_find",
        "browser_snapshot",
        "browser_get_content",
        "list_directory",
        "glob_files",
        "grep_files",
        "project_list",
        "clarify",  # host UI; no FS mutation
        "combo",
        "pillars",
        "skills_search",
        "memory_search",
        "fabric_search",
        "session_browse",
        "todo_list",
        "cronjob_list",
        "process_list",
    }
)

# Public mirror for skills / docs / host recipes (same membership as classify).
HOST_PARALLEL_SAFE: frozenset[str] = _SAFE_PARALLEL

_BARRIER: frozenset[str] = frozenset(
    {
        "write_file",
        "patch",
        "terminal",
        "execute_code",
        "process",
        "skill_manage",
        "memory",
        "todo",
        "cronjob",
        "text_to_speech",
        "image_generate",
        # Conductor mutating
        "crucible_workspace",
        "heal_attempt",
        "promote_seal",
        "governance_audit",
        "ethics_evaluate",
        "track_orchestrate",
    }
)

_SPAWN: frozenset[str] = frozenset(
    {
        "delegate_task",
        "spawn_subagent",
        "Task",  # Claude
        "remnant_orchestrate",
        "hermes_batch",
    }
)

_WAVE_FOR_CLASS: dict[str, WaveId] = {
    "safe_parallel": "A",
    "barrier": "B",
    "spawn": "C",
}

WAVE_ORDER: tuple[WaveId, ...] = ("A", "B", "C")

WAVE_LABELS: dict[WaveId, str] = {
    "A": "reads / status / doctor / probes",
    "B": "writes / patches / shell mutations",
    "C": "delegate / remnant / host spawn",
}


def classify_tool(tool_name: str, args: Any = None) -> ToolClass:
    """Return tool class for wave planning.

    Unknown tools default to ``barrier`` (safer than parallelizing mutations).
    ``remnant_orchestrate`` with read-only actions stays ``safe_parallel``.
    """
    name = (tool_name or "").strip()
    if not name:
        return "barrier"

    # remnant_orchestrate: status/list/heartbeat are reads; spawn/merge mutate
    if name == "remnant_orchestrate":
        action = ""
        if isinstance(args, dict):
            action = str(args.get("action") or "").strip().lower()
        if action in {
            "status",
            "list",
            "heartbeat",
            "await",
            "protocol",
            "compliance",
        }:
            return "safe_parallel"
        return "spawn"

    if name in _SPAWN:
        return "spawn"
    if name in _SAFE_PARALLEL:
        return "safe_parallel"
    if name in _BARRIER:
        return "barrier"

    low = name.lower()
    if any(x in low for x in ("spawn", "delegate", "subagent", "fanout")):
        return "spawn"
    if any(
        x in low
        for x in (
            "read",
            "search",
            "list",
            "status",
            "probe",
            "doctor",
            "view",
            "get_",
            "fetch",
        )
    ):
        return "safe_parallel"
    if any(
        x in low
        for x in (
            "write",
            "patch",
            "edit",
            "delete",
            "kill",
            "install",
            "commit",
            "push",
            "run_",
            "exec",
        )
    ):
        return "barrier"
    return "barrier"


def wave_for_class(tool_class: ToolClass | str) -> WaveId:
    return _WAVE_FOR_CLASS.get(str(tool_class), "B")  # type: ignore[return-value]


def wave_for_tool(tool_name: str, args: Any = None) -> WaveId:
    return wave_for_class(classify_tool(tool_name, args))


def host_parallel_safe(tool_name: str, args: Any = None) -> bool:
    """True when the tool is wave-A / safe_parallel for host batch recipes."""
    return classify_tool(tool_name, args) == "safe_parallel"


def plan_waves(
    items: list[dict[str, Any]],
    *,
    tool_key: str = "tool",
    args_key: str = "arguments",
) -> dict[str, Any]:
    """Group planned tool calls into A/B/C waves.

    Each item is typically ``{tool, arguments, …}`` (Hermes-shaped) or a spawn
    request with nested ``tool_call``.
    """
    waves: dict[WaveId, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
    annotated: list[dict[str, Any]] = []

    for idx, raw in enumerate(items or []):
        item = dict(raw or {})
        # Nested host spawn_request.tool_call
        tc = item.get("tool_call") if isinstance(item.get("tool_call"), dict) else None
        if tc:
            tool = str(tc.get("tool") or tc.get("name") or item.get(tool_key) or "")
            args = tc.get("arguments") if "arguments" in tc else tc.get("args")
        else:
            tool = str(item.get(tool_key) or item.get("name") or "")
            args = item.get(args_key) if args_key in item else item.get("args")

        tclass = classify_tool(tool, args)
        wave = wave_for_class(tclass)
        entry = {
            **item,
            "index": idx,
            "tool_class": tclass,
            "wave": wave,
            "wave_label": WAVE_LABELS[wave],
            "resolved_tool": tool,
        }
        waves[wave].append(entry)
        annotated.append(entry)

    # Preferred emit order for hosts that do not segment: A then B then C
    ordered: list[dict[str, Any]] = []
    for w in WAVE_ORDER:
        ordered.extend(waves[w])

    summary = {
        "A": len(waves["A"]),
        "B": len(waves["B"]),
        "C": len(waves["C"]),
        "total": len(annotated),
    }

    return {
        "waves": waves,
        "ordered": ordered,
        "annotated": annotated,
        "summary": summary,
        "wave_order": list(WAVE_ORDER),
        "wave_labels": dict(WAVE_LABELS),
        "guidance": _wave_guidance(summary),
        "batch_policy": {
            "prefer_single_host_batch": True,
            "host_segments": (
                "Hermes may segment large mixed batches; do not reimplement "
                "segmentation inside Conductor."
            ),
            "do_not_serialize_for_one_write": (
                "If only one barrier tool exists among many safe_parallel, still "
                "emit one mixed batch — host schedules segments."
            ),
            "spawn_preference": (
                "Wave C: prefer one hermes_batch / delegate_task(tasks=[…]) "
                "over N serial spawns."
            ),
        },
    }


def _wave_guidance(summary: dict[str, int]) -> str:
    parts = [
        f"Waves A={summary.get('A', 0)} B={summary.get('B', 0)} C={summary.get('C', 0)}."
    ]
    if summary.get("C", 0) > 1:
        parts.append(
            "Multiple spawns → use one hermes_batch / delegate_task(tasks=[…]) this turn."
        )
    if summary.get("A", 0) and summary.get("B", 0):
        parts.append(
            "Mixed reads+writes: emit one host batch; host segments. Do not "
            "serialize the whole turn because one write exists."
        )
    if summary.get("A", 0) and not summary.get("B", 0) and not summary.get("C", 0):
        parts.append("All safe_parallel — fire together.")
    return " ".join(parts)


def tool_class_table() -> list[dict[str, str]]:
    """Export class table for docs / doctor / skills."""
    rows: list[dict[str, str]] = []
    for name in sorted(_SAFE_PARALLEL):
        rows.append(
            {
                "tool": name,
                "class": "safe_parallel",
                "wave": "A",
                "label": WAVE_LABELS["A"],
            }
        )
    for name in sorted(_BARRIER):
        rows.append(
            {
                "tool": name,
                "class": "barrier",
                "wave": "B",
                "label": WAVE_LABELS["B"],
            }
        )
    for name in sorted(_SPAWN):
        rows.append(
            {
                "tool": name,
                "class": "spawn",
                "wave": "C",
                "label": WAVE_LABELS["C"],
            }
        )
    return rows


def parallel_recipe_thin(*, stuck: bool = False) -> dict[str, Any]:
    """Thin-mode parallel recipe: host tools only; fanout only if stuck.

    Extends orchestration thin recipe with explicit tool-class + wave guidance
    without inventing a second scheduler.
    """
    return {
        "name": "thin_parallel",
        "mode": "thin",
        "steps": [
            "start_pack (thin)",
            "Classify host tools → waves A/B/C (advisory)",
            "Emit one mixed host tool batch (prefer large); host may segment",
            "Wave C only if stuck and fanout truly needed",
            "optional memory",
        ],
        "forbid": [
            "remnant fanout unless stuck=true or force full",
            "pillar_status spam as ritual",
            "crucible/governance unless blocked",
            "reimplementing Hermes tool-batch segmentation inside Conductor",
            "serializing whole turn because one barrier tool exists",
        ],
        "stuck": stuck,
        "wave_order": list(WAVE_ORDER),
        "wave_labels": dict(WAVE_LABELS),
        "host_batch": {
            "prefer_single_batch": True,
            "safe_preflight": (
                "Optional hybrid: local/read preflight (wave A) then deepen — "
                "not a substitute for host spawn when multi-axis."
            ),
        },
    }


def hybrid_safe_preflight_pack(
    *,
    findings: list[str] | None = None,
    files_examined: list[str] | None = None,
    work_root: str | None = None,
) -> dict[str, Any]:
    """Compact safe-preflight pack for hybrid dispatch (local scan → host deepen).

    Already used by clone_backend hybrid mode; this is the shared shape for
    docs, thin recipe, and tests.
    """
    findings = list(findings or [])[:12]
    files = list(files_examined or [])[:16]
    return {
        "kind": "hybrid_safe_preflight",
        "wave": "A",
        "tool_class": "safe_parallel",
        "work_root": work_root,
        "findings": findings,
        "files_examined": files,
        "guidance": (
            "Local/read preflight complete. Parent should deepen via host spawn "
            "(wave C) with this pack in context — do not re-scan the same paths."
        ),
        "next_wave": "C" if True else "B",
        "host_note": (
            "Attach under work_pack.local_preflight; hybrid dispatch already "
            "enriches spawn prompts."
        ),
    }
