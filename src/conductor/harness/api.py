"""Harness-agnostic Module API for The Conductor.

Any AI agent harness (Hermes, OpenClaw, custom loops, etc.) can integrate by:

1. ``pip install -e .`` (or install the wheel)
2. ``conductor.harness.install(home=...)``  — skills + SOUL + config into a home dir
3. Call hooks / tools from your agent loop

Hermes is one optional adapter under ``conductor.adapters.hermes``.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillInfo:
    name: str
    description: str
    path: str


@dataclass
class HarnessHooks:
    """Callable hooks a host agent can attach to its tool/LLM loop."""

    pre_tool_call: Callable[..., Any] | None = None
    transform_tool_result: Callable[..., Any] | None = None
    pre_llm_call: Callable[..., Any] | None = None
    on_session_start: Callable[..., Any] | None = None


@dataclass
class ModuleInfo:
    name: str = "the-conductor"
    version: str = ""
    role: str = "skillset-module"
    description: str = (
        "The Conductor — sovereign orchestrator skillset for AI agent harnesses. "
        "Provides SOUL identity, progressive skills, tool schemas, and safety spine hooks."
    )
    home: str = ""
    skills: list[str] = field(default_factory=list)
    adapters: list[str] = field(default_factory=lambda: ["hermes", "generic", "mcp"])


def module_info(*, home: Path | str | None = None) -> dict[str, Any]:
    """Machine-readable module metadata for host discovery."""
    from conductor import __version__
    from conductor.paths import conductor_home

    h = Path(home).expanduser() if home else conductor_home()
    skills = [s.name for s in list_skills(home=h)]
    data = ModuleInfo(
        version=__version__,
        home=str(h),
        skills=skills,
    ).__dict__
    data["product_line"] = "The Conductor enhances the agent that uses it"
    try:
        from conductor.pillars import foundation_report, pillars_as_dicts

        data["pillars"] = pillars_as_dicts()
        report = foundation_report()
        data["foundation"] = {
            "ok": report["ok"],
            "passed": report["passed"],
            "total": report["total"],
        }
    except Exception:  # noqa: BLE001
        data["pillars"] = []
        data["foundation"] = {"ok": False}
    return data


def install(
    *,
    home: Path | str | None = None,
    harness: str = "generic",
    force: bool = True,
) -> dict[str, Any]:
    """Install Conductor skills/config into a home directory for a host harness.

    Parameters
    ----------
    home:
        Durable home for Conductor state (default: CONDUCTOR_HOME / ~/.conductor).
    harness:
        ``generic`` — skills + SOUL + config only.
        ``hermes`` — also installs Hermes plugin under home/plugins/conductor
        and writes package bootstrap files for stock Hermes.
    """
    from conductor.paths import conductor_home
    from conductor.setup_ext import setup_extension

    h = Path(home).expanduser() if home else conductor_home()
    os.environ["CONDUCTOR_HOME"] = str(h)
    # For Hermes adapter, keep HERMES_HOME aligned unless user overrode it
    if harness == "hermes":
        os.environ.setdefault("HERMES_HOME", str(h))
    report = setup_extension(home=h, force=force, harness=harness)
    out = report.to_dict()
    out["harness"] = harness
    out["module"] = module_info(home=h)
    return out


def get_system_prompt(
    *,
    memory_block: str = "",
    host_soul: str | None = None,
    mode: str | None = None,
    search_host: bool = True,
) -> str:
    """Soul Resonance system prompt for any host agent.

    Locks Conductor partner SOUL with the host meister soul (Hermes/OpenClaw/…).
    Pass ``host_soul`` as path or text, or set ``CONDUCTOR_HOST_SOUL``.
    Modes: ``resonate`` (default), ``solo``, ``host_only`` — or env ``CONDUCTOR_SOUL_MODE``.

    See docs/SOUL_RESONANCE.md and docs/MODULE_FOR_AGENTS.md.
    """
    from conductor.agent.runtime import build_system_prompt

    return build_system_prompt(
        memory_block=memory_block,
        host_soul=host_soul,
        mode=mode,
        search_host=search_host,
    )


def resonate_souls(
    *,
    host_soul: str | None = None,
    mode: str | None = None,
    search_host: bool = True,
) -> dict:
    """Return Soul Resonance diagnostics + prompt (for hosts that compose prompts themselves)."""
    from conductor.soul.resonance import SoulMode, resonate
    from conductor.skills.loader import build_skills_index_text
    from conductor.research.index import build_research_index_text

    resolved: SoulMode | None = mode if mode in {"resonate", "solo", "host_only"} else None  # type: ignore[assignment]
    result = resonate(
        host_soul=host_soul,
        mode=resolved,
        search_host=search_host,
        skills_block=build_skills_index_text(),
        research_block=build_research_index_text(),
    )
    data = result.to_dict()
    data["prompt"] = result.prompt
    return data


def list_skills(*, home: Path | str | None = None) -> list[SkillInfo]:
    """Progressive skill pack metadata (name + description)."""
    from conductor.skills.loader import skills_index

    if home is not None:
        os.environ["CONDUCTOR_HOME"] = str(Path(home).expanduser())
    # ensure skills seeded into home
    try:
        from conductor.skills.loader import ensure_skills_seeded

        ensure_skills_seeded()
    except Exception:  # noqa: BLE001
        pass
    out: list[SkillInfo] = []
    for meta in skills_index():
        out.append(
            SkillInfo(
                name=meta.name,
                description=meta.description,
                path=str(getattr(meta, "path", "") or ""),
            )
        )
    return out


def tool_schemas() -> list[dict[str, Any]]:
    """OpenAI-style tool schemas a host can register on its agent."""
    from conductor.agent.tools import TOOL_SCHEMAS

    return list(TOOL_SCHEMAS)


def execute_tool(name: str, arguments: dict[str, Any], *, session_id: str = "") -> str:
    """Run a Conductor tool by name (host bridges tool calls here)."""
    from conductor.agent.tools import execute_tool as _exec
    from conductor.session.store import SessionStore

    store = SessionStore()
    sid = session_id
    if not sid:
        sid = store.create_session(source="harness-module").id
    return _exec(name, arguments or {}, session_id=sid, store=store)


def hooks() -> HarnessHooks:
    """Spine hooks for hosts that support pre/post tool and pre-LLM injection."""
    from conductor.hermes_bridge import (
        on_session_start_hook,
        pre_llm_call_hook,
        pre_tool_call_hook,
        transform_failed_tool_result,
    )

    return HarnessHooks(
        pre_tool_call=pre_tool_call_hook,
        transform_tool_result=transform_failed_tool_result,
        pre_llm_call=pre_llm_call_hook,
        on_session_start=on_session_start_hook,
    )
