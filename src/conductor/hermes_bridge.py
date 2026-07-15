"""Hermes engine ↔ Conductor brain bridge.

When Hermes is the TUI/tool loop, this module is the **spine wire**:
mass-wipe / path safety / optional workspace allowlist on pre_tool_call,
integrity cascade annotations on failed results.

Pure helpers so brain tests do not need a Hermes process.
Hermes plugin ``plugins/conductor`` imports these callables at runtime.

Performance (docs/BENCHMARKS.md): hooks stay light —
cached SessionStore, memory-first thrash, cached workspace root, lazy path_safety.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

# Hermes + Conductor tool names that carry shell commands or filesystem paths
_SHELL_TOOLS = frozenset(
    {
        "terminal",
        "run_shell",
        "run_command",
        "shell",
        "bash",
        "execute_code",
        "process",
        "run_pty",
    }
)
_WRITE_TOOLS = frozenset(
    {
        "write_file",
        "create_file",
        "edit_file",
        "search_replace",
        "str_replace",
        "apply_patch",
        "write_to_file",
        "patch",
        "insert_edit",
    }
)
_READ_TOOLS = frozenset(
    {
        "read_file",
        "read",
        "cat",
        "view_file",
        "open_file",
        "search_files",
    }
)


def _as_dict(args: Any) -> dict[str, Any]:
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def extract_command(tool_name: str, args: dict[str, Any]) -> str:
    for key in ("command", "cmd", "script", "code", "input", "shell"):
        val = args.get(key)
        if val is not None and str(val).strip():
            return str(val)
    return ""


def extract_path(tool_name: str, args: dict[str, Any]) -> str:
    for key in (
        "path",
        "file_path",
        "file",
        "target",
        "filename",
        "dest",
        "destination",
        "filepath",
    ):
        val = args.get(key)
        if val is not None and str(val).strip():
            return str(val)
    return ""


_WS_CACHE: tuple[str, Path | None] | None = None
_RM_ABS_RE = re.compile(r"(/(?:[\w.-]+/)*[\w.-]+)")


def workspace_root() -> Path | None:
    """Optional project root confinement (CONDUCTOR_WORKSPACE / legacy ILO_*)."""
    global _WS_CACHE
    raw = (
        os.environ.get("CONDUCTOR_WORKSPACE", "").strip()
        or os.environ.get("CONDUCTOR_PROJECT_ROOT", "").strip()
        or os.environ.get("ILO_WORKSPACE", "").strip()  # legacy
        or os.environ.get("ILO_PROJECT_ROOT", "").strip()  # legacy
    )
    if _WS_CACHE is not None and _WS_CACHE[0] == raw:
        return _WS_CACHE[1]
    path: Path | None = None
    if raw:
        try:
            path = Path(raw).expanduser().resolve()
        except (OSError, RuntimeError):
            path = None
    _WS_CACHE = (raw, path)
    return path


def clear_workspace_cache() -> None:
    """Test helper when env workspace changes mid-process."""
    global _WS_CACHE
    _WS_CACHE = None


def path_outside_workspace(path: str) -> str | None:
    """If workspace is set and path resolves outside it (and not under CONDUCTOR_HOME), deny."""
    root = workspace_root()
    if root is None or not path:
        return None
    try:
        p = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return f"unresolvable path outside workspace: {path}"
    try:
        p.relative_to(root)
        return None
    except ValueError:
        pass
    # Allow CONDUCTOR_HOME (sessions, recovery imprints, skills)
    try:
        from conductor.paths import conductor_home

        home = conductor_home().resolve()
        p.relative_to(home)
        return None
    except Exception:  # noqa: BLE001
        pass
    # Allow /tmp for ephemeral artifacts
    try:
        p.relative_to(Path("/tmp").resolve())
        return None
    except ValueError:
        pass
    return (
        f"path outside CONDUCTOR_WORKSPACE ({root}): {p}. "
        "Set CONDUCTOR_WORKSPACE to the project root or write under that tree / CONDUCTOR_HOME /tmp."
    )


def ensure_session_id(session_id: str = "", *, create: bool = True) -> str:
    """Return a durable session id for integrity scars; optionally create if missing."""
    sid = (session_id or os.environ.get("CONDUCTOR_AGENT_SESSION_ID") or "").strip()
    if sid:
        os.environ["CONDUCTOR_AGENT_SESSION_ID"] = sid
        return sid
    if not create:
        return ""
    try:
        from conductor.session.store import default_session_store

        sid = default_session_store().create_session(source="hermes-engine").id
        os.environ["CONDUCTOR_AGENT_SESSION_ID"] = sid
        return sid
    except Exception:  # noqa: BLE001
        return ""


def spine_check_tool_call(
    tool_name: str,
    args: Any = None,
) -> str | None:
    """Return a block message if the call violates conductor spine, else None."""
    name = (tool_name or "").strip()
    a = _as_dict(args)

    try:
        from conductor.agent.path_safety import is_shell_denied, is_write_denied
    except Exception:  # noqa: BLE001
        return None

    is_shell = name in _SHELL_TOOLS or name.endswith("_shell") or name == "terminal"
    is_file = (
        name in _WRITE_TOOLS
        or name in _READ_TOOLS
        or "write" in name
        or "edit" in name
        or name == "patch"
    )

    # Shell / terminal
    if is_shell:
        cmd = extract_command(name, a)
        if cmd:
            deny = is_shell_denied(cmd)
            if deny:
                return (
                    f"Conductor spine blocked tool {name!r}: {deny}. "
                    "Mass-delete of home/root and catastrophic shell are forbidden. "
                    "Scope work to the project; use recovery imprints instead of broad rm."
                )
            # Workspace: block recursive rm of absolute paths outside workspace
            root = workspace_root()
            if root and "rm" in cmd and ("-r" in cmd or "-R" in cmd):
                for token in _RM_ABS_RE.findall(cmd):
                    if token.startswith("/tmp"):
                        continue
                    if path_outside_workspace(token):
                        return (
                            f"Conductor workspace spine blocked recursive rm involving {token!r} "
                            f"(outside CONDUCTOR_WORKSPACE={root})."
                        )
        return None  # pure shell path done — avoid second generic scan

    # File write/read
    if is_file:
        path = extract_path(name, a)
        if path:
            deny = is_write_denied(path)
            if deny:
                return (
                    f"Conductor spine blocked tool {name!r}: {deny}. "
                    "Secret/system paths are not rewritten under the guise of repair."
                )
            if name in _WRITE_TOOLS or "write" in name or name == "patch":
                outside = path_outside_workspace(path)
                if outside:
                    return f"Conductor spine blocked tool {name!r}: {outside}"
        return None

    # Generic command field on other tools
    cmd = extract_command(name, a)
    if cmd:
        deny = is_shell_denied(cmd)
        if deny:
            return f"Conductor spine blocked tool {name!r}: {deny}."

    return None


def pre_tool_call_hook(
    tool_name: str = "",
    args: Any = None,
    session_id: str = "",
    **kwargs: Any,
) -> dict[str, str] | None:
    """Hermes plugin shape: block with action/message or return None.

    Order: mass-wipe/spine → thrash (same tool+args N times) → allow.
    """
    msg = spine_check_tool_call(tool_name, args)
    if msg:
        return {"action": "block", "message": msg}

    # Proactive thrash guard (memory-first; optional durable store)
    try:
        from conductor.loop_thrash import record_and_check, thrash_disabled
        from conductor.session.store import default_session_store

        if thrash_disabled():
            return None
        sid = (
            session_id
            or kwargs.get("session_id")
            or os.environ.get("CONDUCTOR_AGENT_SESSION_ID", "")
        )
        sid = ensure_session_id(str(sid or ""), create=False) or "ephemeral"
        # Durable store only for real sessions — ephemeral stays memory-only
        store = default_session_store() if sid != "ephemeral" else None
        batch_id = None
        wave_id = None
        if isinstance(args, dict):
            batch_id = (
                args.get("_conductor_batch")
                or args.get("batch_id")
                or kwargs.get("batch_id")
            )
            wave_id = (
                args.get("_conductor_wave")
                or args.get("wave_id")
                or kwargs.get("wave_id")
            )
        hit = record_and_check(
            store,
            sid,
            tool_name,
            args,
            batch_id=str(batch_id) if batch_id else None,
            wave_id=str(wave_id) if wave_id else None,
        )
        if hit.blocked:
            msg = hit.message
            # Attach loop policy scope: stop this fingerprint, not the mission
            try:
                from conductor.loop_policy import evaluate_loop, loop_decision_suffix

                if store is not None and sid and sid != "ephemeral":
                    decision = evaluate_loop(store, sid, thrash=True)
                    suffix = loop_decision_suffix(decision)
                    if suffix:
                        msg = msg.rstrip() + suffix
            except Exception:  # noqa: BLE001
                pass
            return {"action": "block", "message": msg}
    except Exception:  # noqa: BLE001
        pass
    return None


def transform_failed_tool_result(
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    session_id: str = "",
    **_: Any,
) -> str | None:
    """On failed Hermes tool results, run integrity cascade annotation when possible."""
    if not isinstance(result, str) or not result.strip():
        return None
    low = result[:800].lower()
    if not any(
        x in low
        for x in (
            "error",
            "failed",
            "denied",
            "not found",
            "no such file",
            "exit code",
            "traceback",
            "errno",
            "blocked",
        )
    ):
        return None

    # Don't re-annotate blocks we already issued
    if "conductor spine blocked" in low or "integrity cascade" in low:
        return None

    sid = ensure_session_id(session_id, create=True)
    if not sid:
        # Lightweight note without store
        return (
            result.rstrip()
            + "\n\n---\n[Conductor spine] Failure observed. Set session continuity "
            "for full integrity cascade (scars/seals)."
        )

    try:
        from conductor.healing.factor import heal_moment
        from conductor.session.store import default_session_store
    except Exception:  # noqa: BLE001
        return None

    a = _as_dict(args)
    path = extract_path(tool_name, a)
    cmd = extract_command(tool_name, a)
    try:
        store = default_session_store()
        report = heal_moment(
            store,
            sid,
            tool=tool_name or "hermes_tool",
            error=result[:2000],
            arguments={**a, "path": path, "command": cmd},
            meta={"path": path, "command": cmd, "source": "hermes_engine"},
        )
        suffix = report.as_tool_suffix()
        if suffix and suffix not in result:
            return result.rstrip() + suffix
    except Exception:  # noqa: BLE001
        return None
    return None


def on_session_start_hook(session_id: str = "", **_: Any) -> None:
    """Bind Hermes session id into Conductor for scars/evidence."""
    if session_id:
        os.environ["CONDUCTOR_AGENT_SESSION_ID"] = str(session_id)
    else:
        ensure_session_id("", create=True)


# Short TTL cache for empty pre_llm payloads (hot path when no scars yet)
_PRE_LLM_EMPTY_UNTIL: dict[str, float] = {}
_PRE_LLM_EMPTY_TTL_S = 2.0


def pre_llm_call_hook(
    session_id: str = "",
    user_message: str = "",
    **kwargs: Any,
) -> dict[str, str] | str | None:
    """Inject live Memory Fabric (scars/seals/episodes) into the Hermes turn.

    Hermes injects ``{"context": "..."}`` into the *user* message (not system)
    so the prompt cache prefix stays stable.
    """
    del user_message  # available for future relevance filtering
    sid = ensure_session_id(
        session_id or kwargs.get("session_id") or "", create=False
    )
    if not sid:
        return None
    now = time.time()
    empty_until = _PRE_LLM_EMPTY_UNTIL.get(sid, 0.0)
    if empty_until > now:
        return None
    try:
        from conductor.memory.context_inject import pre_llm_context_payload
        from conductor.session.store import default_session_store

        payload = pre_llm_context_payload(default_session_store(), sid)
        if not payload:
            _PRE_LLM_EMPTY_UNTIL[sid] = now + _PRE_LLM_EMPTY_TTL_S
        else:
            _PRE_LLM_EMPTY_UNTIL.pop(sid, None)
        return payload
    except Exception:  # noqa: BLE001
        return None


def hermes_bridge_status() -> dict[str, Any]:
    """Diagnostics for doctor/status."""
    try:
        from conductor.agent.path_safety import is_shell_denied

        spine_ok = is_shell_denied("rm -rf /") is not None
        home_ok = is_shell_denied("rm -rf $HOME") is not None
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "spine_loaded": False}
    ws = workspace_root()
    return {
        "ok": True,
        "spine_loaded": spine_ok and home_ok,
        "blocks_root_wipe": spine_ok,
        "blocks_home_wipe": home_ok,
        "workspace": str(ws) if ws else None,
        "legacy_fork": os.environ.get("CONDUCTOR_LEGACY_FORK", ""),
        "conductor_home": os.environ.get("CONDUCTOR_HOME", ""),
        "hermes_home": os.environ.get("HERMES_HOME", ""),
        "session_id": os.environ.get("CONDUCTOR_AGENT_SESSION_ID", ""),
        "spine_on_hermes": (
            os.environ.get("CONDUCTOR_SPINE_ON_HERMES", "")
            or os.environ.get("ILO_SPINE_ON_HERMES", "")
        ),
        "live_memory_inject": True,
        "loop_policy": True,
        "regression_promote": True,
        "thrash_guard": True,
        "global_seals": True,
        "hermes_oauth": True,
    }
