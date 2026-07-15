"""Built-in agent tools — Judgment-aware (structured results + evidence + safety floors)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from conductor.agent.path_safety import is_shell_denied, is_write_denied
from conductor.agent.tool_result import ToolResult, err_result, ok_result
from conductor.agent.verification import (
    VerificationStore,
    classify_shell_evidence,
    classify_write_evidence,
)
from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY, CONDUCTOR_TOOL_SCHEMAS
from conductor.research.tools import (
    RESEARCH_TOOL_SCHEMAS,
    research_list_tool,
    research_view_tool,
)
from conductor.session.store import SessionStore
from conductor.skills.loader import skill_view, skills_list
from conductor.skills.manager import skill_manage

ToolFn = Callable[[dict[str, Any]], str]
ToolFnDetailed = Callable[[dict[str, Any]], ToolResult]

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from disk.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and return stdout+stderr.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skills_list",
            "description": "List installed Conductor skills (tier-0 metadata only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. conductor)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_view",
            "description": "Load full SKILL.md or a file inside a skill directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill slug/name"},
                    "file_path": {
                        "type": "string",
                        "description": "Optional relative path inside the skill tree",
                    },
                },
                "required": ["name"],
            },
        },
    },
    *RESEARCH_TOOL_SCHEMAS,
    {
        "type": "function",
        "function": {
            "name": "skill_manage",
            "description": "Create, patch, or delete a skill under CONDUCTOR_HOME/skills/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "patch", "delete"],
                    },
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "content": {"type": "string"},
                    "patch_find": {"type": "string"},
                    "patch_replace": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    *CONDUCTOR_TOOL_SCHEMAS,
    {
        "type": "function",
        "function": {
            "name": "verification_list",
            "description": "List durable verification evidence for the current session (Judgment ledger).",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "heal_status",
            "description": (
                "List integrity-cascade scars for this session "
                "(open wounds, healed recoveries, learned seals)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "description": "Optional filter: open | healing | healed | escalated",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "heal_attempt",
            "description": (
                "Manually run the integrity cascade on a described system issue "
                "(classify, field repairs including recovery imprints, learn, advance)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "What failed"},
                    "summary": {"type": "string"},
                    "tool": {"type": "string", "description": "Optional tool name context"},
                    "path": {
                        "type": "string",
                        "description": "Optional path for imprint rebuild",
                    },
                },
                "required": ["error"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "promote_seal",
            "description": (
                "Promote a learned integrity seal into a durable skill only after "
                "the regression gate (offline pytest subset) passes. "
                "Self-improve without silently degrading the harness."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seal_statement": {
                        "type": "string",
                        "description": "Seal text to promote (optional if note_id set)",
                    },
                    "note_id": {
                        "type": "string",
                        "description": "Semantic note id of a seal-tagged note",
                    },
                },
            },
        },
    },
]


def _read_file_detailed(args: dict[str, Any]) -> ToolResult:
    path = Path(args["path"]).expanduser()
    deny = is_write_denied(path)  # same floor for sensitive secret paths
    if deny and any(s in str(path) for s in (".ssh", ".gnupg", ".aws", "/etc/shadow")):
        return err_result(deny, denied=True, path=str(path))
    if not path.exists():
        return err_result(f"file not found: {path}", path=str(path))
    try:
        content = path.read_text(encoding="utf-8", errors="replace")[:20000]
        return ok_result(content, path=str(path), tool="read_file")
    except OSError as exc:
        return err_result(f"reading {path}: {exc}", path=str(path))


def _write_file_detailed(args: dict[str, Any]) -> ToolResult:
    path = Path(args["path"]).expanduser()
    deny = is_write_denied(path)
    if deny:
        return err_result(deny, denied=True, path=str(path), tool="write_file")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get("content", ""))
        path.write_text(content, encoding="utf-8")
        result = ok_result(
            f"Wrote {len(content)} bytes to {path}",
            path=str(path.resolve()) if path.exists() else str(path),
            tool="write_file",
            bytes=len(content),
        )
        # Scan payload for secret-like patterns (advisory; does not block write)
        from conductor.agent.tool_result import scan_output_risk

        risk = scan_output_risk(content)
        if risk:
            result.meta["risk"] = risk["risk"]
            result.meta["findings"] = risk["findings"]
            result.meta["redacted"] = False
        return result
    except OSError as exc:
        return err_result(f"writing {path}: {exc}", path=str(path), tool="write_file")


def _run_shell_detailed(args: dict[str, Any]) -> ToolResult:
    cmd = str(args.get("command", "")).strip()
    if not cmd:
        return err_result("empty command", tool="run_shell")
    deny = is_shell_denied(cmd)
    if deny:
        return err_result(deny, denied=True, tool="run_shell", command=cmd)
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        text = out[:20000] or f"(exit {proc.returncode}, no output)"
        ok = proc.returncode == 0
        if ok:
            return ok_result(
                text,
                tool="run_shell",
                command=cmd,
                exit_code=proc.returncode,
            )
        return ToolResult(
            ok=False,
            content=text,
            error=f"Error: command exited {proc.returncode}",
            meta={"tool": "run_shell", "command": cmd, "exit_code": proc.returncode},
        )
    except subprocess.TimeoutExpired:
        return err_result("command timed out after 120s", tool="run_shell", command=cmd)
    except OSError as exc:
        return err_result(f"running command: {exc}", tool="run_shell", command=cmd)


def _skills_list_detailed(args: dict[str, Any]) -> ToolResult:
    category = args.get("category")
    cat = str(category).strip() if category else None
    return ok_result(skills_list(cat), tool="skills_list")


def _skill_view_detailed(args: dict[str, Any]) -> ToolResult:
    name = str(args.get("name", "")).strip()
    if not name:
        return err_result("name required", tool="skill_view")
    file_path = args.get("file_path")
    fp = str(file_path).strip() if file_path else None
    out = skill_view(name, fp)
    if out.startswith("Error:"):
        return err_result(out, tool="skill_view")
    return ok_result(out, tool="skill_view")


def _skill_manage_detailed(args: dict[str, Any]) -> ToolResult:
    action = str(args.get("action", "")).strip()
    out = skill_manage(
        action,
        name=str(args.get("name", "")).strip(),
        description=str(args.get("description", "")).strip(),
        content=str(args.get("content", "")).strip(),
        patch_find=str(args.get("patch_find", "")).strip(),
        patch_replace=str(args.get("patch_replace", "")).strip(),
    )
    if out.startswith("Error:"):
        return err_result(out, tool="skill_manage")
    return ok_result(out, tool="skill_manage")


def _research_list_detailed(args: dict[str, Any]) -> ToolResult:
    out = research_list_tool(args)
    if isinstance(out, str) and out.startswith("Error:"):
        return err_result(out, tool="research_list")
    return ok_result(str(out), tool="research_list")


def _research_view_detailed(args: dict[str, Any]) -> ToolResult:
    out = research_view_tool(args)
    if isinstance(out, str) and out.startswith("Error:"):
        return err_result(out, tool="research_view")
    return ok_result(str(out), tool="research_view")


TOOL_REGISTRY_DETAILED: dict[str, ToolFnDetailed] = {
    "read_file": _read_file_detailed,
    "write_file": _write_file_detailed,
    "run_shell": _run_shell_detailed,
    "skills_list": _skills_list_detailed,
    "skill_view": _skill_view_detailed,
    "research_list": _research_list_detailed,
    "research_view": _research_view_detailed,
    "skill_manage": _skill_manage_detailed,
}

# Back-compat string registry for callers that expect ToolFn
TOOL_REGISTRY: dict[str, ToolFn] = {
    name: (lambda args, _n=name: TOOL_REGISTRY_DETAILED[_n](args).as_model_text())
    for name in TOOL_REGISTRY_DETAILED
}


def _record_evidence(
    name: str,
    arguments: dict[str, Any],
    result: ToolResult,
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> None:
    if not session_id or store is None:
        return
    event = None
    if name == "write_file":
        path = str(result.meta.get("path") or arguments.get("path") or "")
        event = classify_write_evidence(path, ok=result.ok)
    elif name == "run_shell":
        cmd = str(arguments.get("command") or result.meta.get("command") or "")
        exit_code = result.meta.get("exit_code")
        event = classify_shell_evidence(
            cmd,
            ok=result.ok,
            exit_code=int(exit_code) if exit_code is not None else None,
        )
    if event is None:
        return
    VerificationStore(store).record(session_id, event)


def _maybe_heal(
    name: str,
    arguments: dict[str, Any],
    result: ToolResult,
    *,
    session_id: str | None,
    store: SessionStore | None,
) -> ToolResult:
    """Integrity cascade: on failure, classify → field repair → learn → advance."""
    if result.ok or not session_id or store is None:
        # Leave recovery imprints on successful writes
        if result.ok and name == "write_file" and session_id:
            try:
                from conductor.healing.factor import maybe_mirror_write

                path = str(result.meta.get("path") or arguments.get("path") or "")
                content = str(arguments.get("content") or "")
                maybe_mirror_write(path, content, session_id=session_id, ok=True)
            except Exception:  # noqa: BLE001 — never break success path
                pass
        return result
    try:
        from conductor.healing.factor import apply_healing_to_result, heal_moment

        report = heal_moment(
            store,
            session_id,
            tool=name,
            error=result.error or result.content or "tool failed",
            arguments=arguments,
            meta=dict(result.meta or {}),
        )
        return apply_healing_to_result(result, report)
    except Exception as exc:  # noqa: BLE001 — integrity cascade must not mask original error
        result.meta["healing_error"] = str(exc)
        return result


def execute_tool_detailed(
    name: str,
    arguments: dict[str, Any],
    *,
    session_id: str | None = None,
    store: SessionStore | None = None,
) -> ToolResult:
    """Run a tool and return structured ToolResult (ok/content/error/meta)."""
    # Proactive thrash guard (native tool loop)
    if store is not None and session_id:
        try:
            from conductor.loop_thrash import record_and_check

            batch_id = None
            wave_id = None
            if isinstance(arguments, dict):
                batch_id = arguments.get("_conductor_batch") or arguments.get("batch_id")
                wave_id = arguments.get("_conductor_wave") or arguments.get("wave_id")
            hit = record_and_check(
                store,
                session_id,
                name,
                arguments,
                batch_id=str(batch_id) if batch_id else None,
                wave_id=str(wave_id) if wave_id else None,
            )
            if hit.blocked:
                return err_result(hit.message, tool=name, thrash=True, denied=True)
        except Exception:  # noqa: BLE001
            pass

    if name == "verification_list":
        if not session_id or store is None:
            return err_result("verification_list requires session context")
        limit = int(arguments.get("limit", 20))
        events = VerificationStore(store).list_events(session_id, limit=limit)
        import json

        payload = [e.to_dict() for e in events]
        return ok_result(json.dumps(payload, indent=2), tool="verification_list", count=len(payload))

    if name == "heal_status":
        if not session_id or store is None:
            return err_result("heal_status requires session context")
        import json

        from conductor.healing.store import ScarStore

        limit = int(arguments.get("limit", 20))
        status = str(arguments.get("status") or "").strip() or None
        scars = ScarStore(store).list_scars(session_id, limit=limit, status=status)
        payload = [s.to_dict() for s in scars]
        return ok_result(
            json.dumps(payload, indent=2),
            tool="heal_status",
            count=len(payload),
            open=sum(1 for s in scars if s.status in {"open", "healing"}),
        )

    if name == "heal_attempt":
        if not session_id or store is None:
            return err_result("heal_attempt requires session context")
        import json

        from conductor.healing.factor import heal_moment

        tool = str(arguments.get("tool") or "manual")
        error = str(arguments.get("error") or arguments.get("summary") or "manual heal")
        path = str(arguments.get("path") or "")
        report = heal_moment(
            store,
            session_id,
            tool=tool,
            error=error,
            arguments={"path": path} if path else {},
            meta={"path": path} if path else {},
        )
        return ok_result(json.dumps(report.to_dict(), indent=2), tool="heal_attempt", healed=report.healed)

    if name == "promote_seal":
        if not session_id or store is None:
            return err_result("promote_seal requires session context")
        import json
        import os

        from conductor.learning.promote import promote_seal_to_skill

        # Production always runs the gate; CONDUCTOR_PROMOTE_SKIP_GATE=1 only for unit tests.
        skip = (
            os.environ.get("CONDUCTOR_PROMOTE_SKIP_GATE", "").strip()
            or os.environ.get("ILO_PROMOTE_SKIP_GATE", "").strip()  # legacy
        ) in {"1", "true", "yes"}
        result = promote_seal_to_skill(
            store,
            session_id,
            seal_statement=str(arguments.get("seal_statement") or ""),
            note_id=str(arguments.get("note_id") or ""),
            skip_gate=skip,
        )
        payload = result.to_dict()
        if not result.ok:
            return err_result(
                json.dumps(payload, indent=2),
                tool="promote_seal",
                promoted=False,
                reason=result.reason,
            )
        return ok_result(
            json.dumps(payload, indent=2),
            tool="promote_seal",
            promoted=result.promoted,
            skill_name=result.skill_name,
        )

    conductor_fn = CONDUCTOR_TOOL_REGISTRY.get(name)
    if conductor_fn is not None:
        try:
            text = conductor_fn(arguments, session_id=session_id, store=store)
        except Exception as exc:  # noqa: BLE001
            result = err_result(str(exc), tool=name)
            return _maybe_heal(name, arguments, result, session_id=session_id, store=store)
        if isinstance(text, str) and text.startswith("Error:"):
            result = err_result(text, tool=name)
        else:
            result = ok_result(str(text), tool=name)
        # still scan risk on conductor tool output
        from conductor.agent.tool_result import attach_risk_meta

        result = attach_risk_meta(result)
        return _maybe_heal(name, arguments, result, session_id=session_id, store=store)

    fn = TOOL_REGISTRY_DETAILED.get(name)
    if fn is None:
        result = err_result(f"unknown tool {name}", tool=name)
        return _maybe_heal(name, arguments, result, session_id=session_id, store=store)
    result = fn(arguments)
    _record_evidence(name, arguments, result, session_id=session_id, store=store)
    return _maybe_heal(name, arguments, result, session_id=session_id, store=store)


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    session_id: str | None = None,
    store: SessionStore | None = None,
) -> str:
    """Model-facing entry — returns readable text; records evidence + risk meta."""
    return execute_tool_detailed(
        name, arguments, session_id=session_id, store=store
    ).as_model_text()
