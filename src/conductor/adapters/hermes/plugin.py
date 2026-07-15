"""Hermes plugin ``register(ctx)`` — package entry for any stock Hermes agent.

Loaded by:
- ``$HERMES_HOME/plugins/conductor/`` (copied by ``conductor setup``)
- pip entry-point ``hermes_agent.plugins`` → ``conductor.adapters.hermes.plugin``

Hermes is the meister (TUI, auth, loop, SOUL.md). Conductor enhances it.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes.plugins.conductor")

# Never override these without plugins.entries.conductor.allow_tool_override.
# Spine still gates host tools via pre_tool_call.
HERMES_CORE_TOOL_NAMES = frozenset(
    {
        "terminal",
        "process",
        "read_terminal",
        "close_terminal",
        "read_file",
        "write_file",
        "run_shell",
        "patch",
        "search_files",
        "web_search",
        "web_extract",
        "browser_navigate",
        "browser_click",
        "browser_type",
        "todo",
        "skill_manage",
        "memory",
        "memory_search",
        "memory_get",
        # Native Hermes AI subagent spawn — never override with offline worker
        "delegate_task",
    }
)


def apply_hermes_host_defaults() -> None:
    """Env defaults every Hermes session should share with Conductor."""
    os.environ.setdefault("CONDUCTOR_SPINE_ON_HERMES", "1")
    os.environ.setdefault("ILO_SPINE_ON_HERMES", "1")  # legacy bridge
    os.environ.setdefault("CONDUCTOR_SOUL_MODE", "resonate")
    os.environ.setdefault("CONDUCTOR_HOST", "hermes")
    os.environ.setdefault("CONDUCTOR_USE_HARNESS_AUTH", "1")

    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        os.environ.setdefault("CONDUCTOR_HOME", hermes_home)
    home = (
        os.environ.get("HERMES_HOME", "").strip()
        or os.environ.get("CONDUCTOR_HOME", "").strip()
    )
    if not home:
        return
    h = Path(home).expanduser()
    os.environ.setdefault("CONDUCTOR_HOME", str(h))
    os.environ.setdefault("HERMES_HOME", str(h))
    meister = h / "SOUL.md"
    identity = h / "IDENTITY.md"
    partner = h / "CONDUCTOR_PARTNER_SOUL.md"
    if meister.is_file():
        os.environ.setdefault("CONDUCTOR_HOST_SOUL", str(meister.resolve()))
    elif identity.is_file():
        os.environ.setdefault("CONDUCTOR_HOST_SOUL", str(identity.resolve()))
    if partner.is_file():
        os.environ.setdefault("CONDUCTOR_PARTNER_SOUL", str(partner.resolve()))


def _session_id() -> str:
    return os.environ.get("CONDUCTOR_AGENT_SESSION_ID", "").strip()


def _store():
    from conductor.session.store import SessionStore

    return SessionStore()


def _ensure_session_id() -> str:
    sid = _session_id()
    if sid:
        return sid
    store = _store()
    sid = store.create_session(source="hermes-plugin").id
    os.environ["CONDUCTOR_AGENT_SESSION_ID"] = sid
    return sid


def _wrap_tool(fn):
    def handler(args: dict[str, Any], **kwargs: Any) -> str:
        session_id = kwargs.get("session_id") or _ensure_session_id()
        store = kwargs.get("store") or _store()
        try:
            return fn(args, session_id=session_id, store=store)
        except TypeError:
            return fn(args)

    return handler


def _slash_dispatch(handler_name: str, raw_args: str) -> str:
    """Route Hermes slash text to Conductor handlers."""
    session_id = _ensure_session_id()
    store = _store()
    args = raw_args.split() if raw_args.strip() else []
    try:
        if handler_name == "crucible":
            from conductor.core.slash import handle_crucible_slash

            return handle_crucible_slash(store, session_id, args)
        if handler_name == "pillars":
            from conductor.pillars import (
                format_foundation_report,
                format_pillar_detail,
                format_pillars_list,
            )

            if not args:
                return format_pillars_list()
            head = args[0].lower()
            if head in {"list", "ls", "help"}:
                return format_pillars_list()
            if head in {"status", "probe", "foundation", "check"}:
                return format_foundation_report(
                    session_id=session_id,
                    verbose="verbose" in {a.lower() for a in args[1:]},
                )
            if head in {"get", "show", "detail"}:
                return format_pillar_detail(" ".join(args[1:]) or "P1")
            return format_pillar_detail(head)
        if handler_name == "combo":
            from conductor.combos import (
                format_combo_list,
                format_recommendation,
                format_workflow,
                get_combo,
            )

            if not args:
                return format_combo_list()
            head = args[0].lower()
            rest = " ".join(args[1:]).strip()
            if head in {"list", "ls", "help"}:
                return format_combo_list()
            if head in {"recommend", "route", "pick"}:
                return format_recommendation(rest or "daily work")
            if head in {"workflow", "flow", "steps"}:
                return format_workflow(rest.split()[0] if rest else "A")
            if get_combo(head):
                return format_workflow(head)
            return format_recommendation(" ".join(args))
        if handler_name == "remnant":
            from conductor.core.remnant_slash import handle_remnant_slash

            return handle_remnant_slash(store, session_id, args)
        if handler_name == "track":
            from conductor.core.track_slash import handle_track_slash

            return handle_track_slash(store, session_id, args)
        if handler_name in {"conductor-status", "cstatus"}:
            from conductor.adapters.hermes.ready import format_ready_report

            return format_ready_report(verbose="verbose" in {a.lower() for a in args})
    except Exception as exc:  # noqa: BLE001
        return f"Conductor /{handler_name} error: {exc}"
    return f"Unknown slash handler {handler_name}"


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **kwargs: Any):
    from conductor.hermes_bridge import pre_tool_call_hook

    return pre_tool_call_hook(tool_name=tool_name, args=args, **kwargs)


def _on_transform_tool_result(
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    session_id: str = "",
    **kwargs: Any,
):
    from conductor.hermes_bridge import transform_failed_tool_result

    sid = session_id or kwargs.pop("session_id", None) or _session_id()
    # Drop positional-owned keys so **kwargs never double-binds.
    for k in ("tool_name", "args", "result", "session_id"):
        kwargs.pop(k, None)
    # Pass host observer fields (status / error_type / error_message) through —
    # Hermes model_tools injects them on transform_tool_result.
    return transform_failed_tool_result(
        tool_name=tool_name,
        args=args,
        result=result,
        session_id=str(sid or ""),
        **kwargs,
    )


def _on_session_start(session_id: str = "", **kwargs: Any) -> None:
    from conductor.hermes_bridge import on_session_start_hook

    apply_hermes_host_defaults()
    on_session_start_hook(session_id=session_id, **kwargs)


def _on_pre_llm_call(
    session_id: str = "",
    user_message: str = "",
    **kwargs: Any,
):
    from conductor.hermes_bridge import pre_llm_call_hook

    sid = session_id or kwargs.get("session_id") or _session_id()
    return pre_llm_call_hook(
        session_id=str(sid or ""),
        user_message=user_message,
        **kwargs,
    )


def _on_api_request_error(session_id: str = "", **kwargs: Any) -> None:
    """Observer: scar provider/API failures; Hermes owns retry/failover."""
    from conductor.hermes_bridge import api_request_error_hook

    sid = session_id or kwargs.get("session_id") or _session_id()
    try:
        api_request_error_hook(session_id=str(sid or ""), **kwargs)
    except Exception:  # noqa: BLE001
        return


def _register_tool_schemas(
    ctx,
    schemas,
    registry: dict,
    toolset: str,
    emoji: str,
    *,
    seen: set[str],
    handler_for=None,
) -> int:
    n = 0
    skipped = 0
    for schema in schemas:
        fn_spec = schema.get("function") or {}
        name = str(fn_spec.get("name") or "")
        if not name:
            continue
        if name in seen:
            continue
        if name not in registry and handler_for is None:
            continue
        if name in HERMES_CORE_TOOL_NAMES:
            skipped += 1
            logger.debug("skip Hermes core name clash: %s", name)
            continue
        try:
            handler = handler_for(name) if handler_for else _wrap_tool(registry[name])
            ctx.register_tool(
                name=name,
                toolset=toolset,
                schema=schema,
                handler=handler,
                description=str(fn_spec.get("description") or ""),
                emoji=emoji,
            )
            seen.add(name)
            n += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("conductor tool %s: %s", name, exc)
    if skipped:
        logger.info(
            "Conductor skipped %s tool name(s) that clash with Hermes built-ins "
            "(spine still gates host tools via pre_tool_call)",
            skipped,
        )
    return n


def register(ctx) -> None:
    """Hermes plugin entry — enhance the host agent, do not replace it."""
    apply_hermes_host_defaults()
    registered_tools = 0
    registered_hooks = 0
    registered_cmds = 0
    seen_tools: set[str] = set()

    # --- Conductor tools ---
    try:
        from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY, CONDUCTOR_TOOL_SCHEMAS

        registered_tools += _register_tool_schemas(
            ctx,
            CONDUCTOR_TOOL_SCHEMAS,
            CONDUCTOR_TOOL_REGISTRY,
            "conductor",
            "◆",
            seen=seen_tools,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Conductor tools unavailable: %s", exc)

    # --- Research tools ---
    try:
        from conductor.research.tools import RESEARCH_TOOL_REGISTRY, RESEARCH_TOOL_SCHEMAS

        registered_tools += _register_tool_schemas(
            ctx,
            RESEARCH_TOOL_SCHEMAS,
            RESEARCH_TOOL_REGISTRY,
            "research",
            "📚",
            seen=seen_tools,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Conductor research tools unavailable: %s", exc)

    # --- Agent tools (heal / skills / verify — skip file/shell clashes) ---
    try:
        from conductor.agent import tools as agent_tools

        schemas = getattr(agent_tools, "TOOL_SCHEMAS", []) or []

        def _make_handler(tool_name: str):
            def handler(args: dict[str, Any], **kwargs: Any) -> str:
                session_id = kwargs.get("session_id") or _ensure_session_id()
                store = kwargs.get("store") or _store()
                return agent_tools.execute_tool(
                    tool_name, args or {}, session_id=session_id, store=store
                )

            return handler

        name_set = {
            str((s.get("function") or {}).get("name") or "")
            for s in schemas
            if (s.get("function") or {}).get("name")
        }
        registered_tools += _register_tool_schemas(
            ctx,
            schemas,
            {n: None for n in name_set},
            "conductor_agent",
            "◎",
            seen=seen_tools,
            handler_for=_make_handler,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Conductor agent tools unavailable: %s", exc)

    # --- Spine hooks ---
    for hook_name, cb in (
        ("pre_tool_call", _on_pre_tool_call),
        ("transform_tool_result", _on_transform_tool_result),
        ("on_session_start", _on_session_start),
        ("pre_llm_call", _on_pre_llm_call),
        # Optional on older Hermes builds — register best-effort.
        ("api_request_error", _on_api_request_error),
    ):
        try:
            ctx.register_hook(hook_name, cb)
            registered_hooks += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Conductor failed to register hook %s: %s", hook_name, exc)

    # --- Slash commands ---
    for name, desc, hint in (
        (
            "crucible",
            "Crucible Global Workspace — start, post, distill, max_effort",
            "[start|status|post|read|distill|clone|max_effort] …",
        ),
        (
            "pillars",
            "Conductor pillar foundation — list, status probes, detail",
            "[list|status|get <P1-P8|slug>]",
        ),
        (
            "combo",
            "Recommend pillar combo A–H for an intent",
            "[list|recommend <intent>|workflow <A-H>]",
        ),
        (
            "remnant",
            "Remnant Protocol — spawn, fanout, report, merge (host clones)",
            "[spawn|fanout|status|report|merge|work] …",
        ),
        (
            "track",
            "Track System — create, list, chessboard, fork, resolve",
            "[list|create|chessboard|fork|resolve] …",
        ),
        (
            "conductor-status",
            "Hermes readiness checklist for The Conductor module",
            "[verbose]",
        ),
    ):
        try:
            ctx.register_command(
                name,
                handler=lambda raw, _n=name: _slash_dispatch(_n, raw or ""),
                description=desc,
                args_hint=hint,
            )
            registered_cmds += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Conductor /%s command: %s", name, exc)

    # Optional: namespaced plugin skills (flat skills also seeded under $HERMES_HOME)
    try:
        from conductor.paths import bundled_skills_roots

        for root in bundled_skills_roots():
            for skill_md in root.rglob("SKILL.md"):
                skill_name = skill_md.parent.name
                if not skill_name or skill_name.startswith("."):
                    continue
                try:
                    ctx.register_skill(
                        skill_name,
                        skill_md.parent,
                        description=f"Conductor skill {skill_name}",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug("register_skill %s: %s", skill_name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("plugin skills: %s", exc)

    try:
        from conductor import __version__ as _ver
    except Exception:  # noqa: BLE001
        _ver = "?"

    logger.info(
        "Conductor %s plugin registered: tools=%s hooks=%s cmds=%s "
        "(enhances Hermes; host=%s; spine=on; soul_mode=%s)",
        _ver,
        registered_tools,
        registered_hooks,
        registered_cmds,
        os.environ.get("CONDUCTOR_HOST", "hermes"),
        os.environ.get("CONDUCTOR_SOUL_MODE", "resonate"),
    )
