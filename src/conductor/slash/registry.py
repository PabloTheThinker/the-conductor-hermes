"""Slash command registry — /help, /status, /sessions, /goal, /learn, /subgoal."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from conductor import __version__
from conductor.agent.runtime import AgentRuntime
from conductor.core.slash import (
    handle_crucible_slash,
    handle_ethics_slash,
    handle_governance_slash,
    handle_memory_slash,
    handle_remnant_slash,
    handle_soul_slash,
    handle_track_slash,
)
from conductor.session.store import SessionStore
from conductor.skills.loader import build_skills_index_text, skills_index
from conductor.skills.manager import learn_from_source
from conductor.slash.goal import GoalManager, run_goal_kickoff, run_subgoal_kickoff

BUILTIN_SLASH_NAMES = frozenset(
    {
        "help",
        "status",
        "sessions",
        "goal",
        "learn",
        "subgoal",
        "crucible",
        "remnant",
        "track",
        "memory",
        "ethics",
        "soul",
        "governance",
        "combo",
        "pillars",
    }
)


@dataclass
class SlashContext:
    store: SessionStore
    runtime: AgentRuntime
    goals: GoalManager
    session_id: str


SlashHandler = Callable[[SlashContext, list[str]], str | None]


@dataclass
class SlashCommand:
    name: str
    description: str
    handler: SlashHandler
    usage: str = ""


def _cmd_help(_ctx: SlashContext, _args: list[str]) -> str:
    lines = ["Conductor slash commands:"]
    for cmd in SlashRegistry.builtin_commands():
        lines.append(f"  /{cmd.name:<10} {cmd.description}")
        if cmd.usage:
            lines.append(f"             {cmd.usage}")
    skills = skills_index()
    if skills:
        lines.append("")
        lines.append("Installed skills (invoke as /<name>):")
        for meta in skills:
            lines.append(f"  /{meta.name:<10} {meta.description[:80]}")
    return "\n".join(lines)


def _cmd_status(ctx: SlashContext, _args: list[str]) -> str:
    state = ctx.goals.load(ctx.session_id)
    rec = ctx.store.get_session(ctx.session_id)
    title = rec.title if rec else ""
    skills_count = len(skills_index())
    conductor_block = ctx.runtime.conductor.status_text(ctx.session_id)
    return (
        f"Conductor {__version__}\n"
        f"Session: {ctx.session_id[:8]}… ({title or 'untitled'})\n"
        f"Skills: {skills_count} installed\n"
        f"Goal: {state.status} — {state.goal or '(none)'}\n"
        f"Turns: {state.turns_used}/{state.max_turns}\n"
        f"---\n"
        f"{conductor_block}"
    )


def _cmd_sessions(ctx: SlashContext, _args: list[str]) -> str:
    rows = ctx.store.list_sessions(limit=20)
    if not rows:
        return "No sessions yet."
    lines = ["Recent sessions:"]
    for rec in rows:
        marker = " *" if rec.id == ctx.session_id else ""
        preview = ""
        if rec.messages:
            preview = rec.messages[-1].content[:40].replace("\n", " ")
        lines.append(
            f"  {rec.id[:8]}… [{rec.source}] {rec.title or '(untitled)'}{marker} — {preview}"
        )
    return "\n".join(lines)


def _goal_kickoff(ctx: SlashContext, goal_text: str) -> str:
    """Run standing-goal kickoff via unified assembly path (no streaming chunks in output)."""
    return run_goal_kickoff(ctx, goal_text).text


def _cmd_goal(ctx: SlashContext, args: list[str]) -> str:
    if not args:
        return ctx.goals.status_text(ctx.session_id)

    sub = args[0].lower()
    if sub == "set":
        text = " ".join(args[1:]).strip()
        if not text:
            return "Usage: /goal set <description>"
        ctx.goals.set_goal(ctx.session_id, text)
        state = ctx.goals.load(ctx.session_id)
        display = state.goal or text
        return f"Goal set: {display}\n{_goal_kickoff(ctx, state.goal or text)}"
    if sub == "pause":
        ctx.goals.pause(ctx.session_id)
        return "Goal paused."
    if sub == "resume":
        ctx.goals.resume(ctx.session_id)
        state = ctx.goals.load(ctx.session_id)
        if state.status == "active" and state.goal:
            return f"Goal resumed.\n{_goal_kickoff(ctx, state.goal)}"
        return "Goal resumed."
    if sub == "clear":
        ctx.goals.clear(ctx.session_id)
        return "Goal cleared."
    if sub == "status":
        return ctx.goals.status_text(ctx.session_id)

    text = " ".join(args).strip()
    ctx.goals.set_goal(ctx.session_id, text)
    state = ctx.goals.load(ctx.session_id)
    display = state.goal or text
    return f"Goal set: {display}\n{_goal_kickoff(ctx, state.goal or text)}"


def _cmd_learn(_ctx: SlashContext, args: list[str]) -> str:
    source = " ".join(args).strip()
    return learn_from_source(source)


def _cmd_crucible(ctx: SlashContext, args: list[str]) -> str:
    return handle_crucible_slash(ctx.store, ctx.session_id, args)


_REMNANT_OPS = frozenset(
    {
        "spawn",
        "heartbeat",
        "merge",
        "merge_reflective",
        "reflective",
        "merge_deep",
        "deep",
        "status",
        "fanout",
        "parallel",
    }
)


def _cmd_remnant(ctx: SlashContext, args: list[str]) -> str | None:
    # Ops verbs stay on slash; advisory questions fall through to the /remnant skill.
    if args and args[0].lower() not in _REMNANT_OPS:
        return None
    return handle_remnant_slash(ctx.store, ctx.session_id, args)


def _cmd_track(ctx: SlashContext, args: list[str]) -> str:
    return handle_track_slash(ctx.store, ctx.session_id, args)


def _cmd_memory(ctx: SlashContext, args: list[str]) -> str:
    return handle_memory_slash(ctx.store, ctx.session_id, args)


def _cmd_ethics(ctx: SlashContext, args: list[str]) -> str:
    return handle_ethics_slash(ctx.store, ctx.session_id, args)


def _cmd_soul(ctx: SlashContext, args: list[str]) -> str:
    return handle_soul_slash(ctx.store, ctx.session_id, args)


def _cmd_governance(ctx: SlashContext, args: list[str]) -> str:
    return handle_governance_slash(ctx.store, ctx.session_id, args)


def _cmd_pillars(_ctx: SlashContext, args: list[str]) -> str:
    """Pillar foundation catalog + live probes."""
    from conductor.pillars import (
        format_foundation_report,
        format_pillar_detail,
        format_pillars_list,
    )

    if not args:
        return format_pillars_list()
    head = args[0].lower()
    rest = " ".join(args[1:]).strip()
    if head in {"list", "ls", "help"}:
        return format_pillars_list()
    if head in {"status", "probe", "foundation", "check"}:
        return format_foundation_report(
            session_id=_ctx.session_id,
            verbose="verbose" in {a.lower() for a in args[1:]} or rest == "verbose",
        )
    if head in {"get", "show", "detail"}:
        if not rest:
            return "Usage: /pillars get <P1-P8|P0|slug>"
        return format_pillar_detail(rest.split()[0])
    # /pillars memory  or /pillars P4
    return format_pillar_detail(head)


def _cmd_combo(_ctx: SlashContext, args: list[str]) -> str:
    """Pillar combo router — list / recommend / workflow / detail."""
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
        if not rest:
            return "Usage: /combo workflow <A-H|slug>"
        return format_workflow(rest.split()[0])
    # /combo C  or  /combo remnant
    if get_combo(head):
        return format_workflow(head)
    # free-text recommend
    return format_recommendation(" ".join(args))


def _cmd_subgoal(ctx: SlashContext, args: list[str]) -> str:
    text = " ".join(args).strip()
    if not text:
        return "Usage: /subgoal <criteria>"
    ctx.goals.add_subgoal(ctx.session_id, text)
    lines = [f"Subgoal added: {text}"]
    kickoff = run_subgoal_kickoff(ctx)
    if kickoff.lines:
        lines.extend(kickoff.lines)
    else:
        lines.append(ctx.goals.status_text(ctx.session_id))
    return "\n".join(lines)


class SlashRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}
        for cmd in self.builtin_commands():
            self.register(cmd)

    @staticmethod
    def builtin_commands() -> list[SlashCommand]:
        return [
            SlashCommand("help", "List slash commands and skills", _cmd_help, usage="/help"),
            SlashCommand("status", "Show runtime and goal status", _cmd_status, usage="/status"),
            SlashCommand(
                "sessions",
                "List recent sessions",
                _cmd_sessions,
                usage="/sessions",
            ),
            SlashCommand(
                "goal",
                "Standing goal control",
                _cmd_goal,
                usage="/goal set|pause|resume|clear|status|<text>",
            ),
            SlashCommand(
                "learn",
                "Create a skill from a source description",
                _cmd_learn,
                usage="/learn <topic or description>",
            ),
            SlashCommand(
                "subgoal",
                "Append mid-loop criteria to the active goal",
                _cmd_subgoal,
                usage="/subgoal <criteria>",
            ),
            SlashCommand(
                "crucible",
                "Crucible Global Workspace — start, post concepts, distill",
                _cmd_crucible,
                usage="/crucible start|status|post|read|distill|clone",
            ),
            SlashCommand(
                "remnant",
                "Remnant Protocol — spawn parallel clones, heartbeat, Tier 1 merge",
                _cmd_remnant,
                usage="/remnant spawn|heartbeat|merge|status",
            ),
            SlashCommand(
                "track",
                "Track System — chessboard, create, fork, prune, resolve",
                _cmd_track,
                usage="/track chessboard|create|fork|prune|resolve|list|view",
            ),
            SlashCommand(
                "memory",
                "Episodic memory — write, list, export task-scoped slices",
                _cmd_memory,
                usage="/memory write|list|export",
            ),
            SlashCommand(
                "ethics",
                "Ethics Decision Checklist — evaluate and audit high-stakes actions",
                _cmd_ethics,
                usage="/ethics check|audit|list",
            ),
            SlashCommand(
                "soul",
                "SOUL identity — status and integrity verification",
                _cmd_soul,
                usage="/soul status|resonate|integrity|hash",
            ),
            SlashCommand(
                "governance",
                "Governance layer — policy checks and decision audit trail",
                _cmd_governance,
                usage="/governance status|audit|check",
            ),
            SlashCommand(
                "combo",
                "Pillar combos A–H — recommend workflow stack for an intent",
                _cmd_combo,
                usage="/combo list|recommend <intent>|workflow <A-H>|<id>",
            ),
            SlashCommand(
                "pillars",
                "Pillar foundation — catalog + live probes (enhance the host)",
                _cmd_pillars,
                usage="/pillars list|status|get <P1-P8|slug>",
            ),
        ]

    def register(self, cmd: SlashCommand) -> None:
        self._commands[cmd.name] = cmd

    def names(self) -> list[str]:
        return sorted(self._commands.keys())

    def autocomplete(self) -> list[str]:
        base = [f"/{name}" for name in self.names()]
        skill_cmds = [f"/{m.name}" for m in skills_index()]
        extras = [
            "/goal set",
            "/goal pause",
            "/goal resume",
            "/goal clear",
            "/goal status",
            "/crucible start",
            "/crucible status",
            "/crucible post",
            "/crucible read",
            "/crucible distill",
            "/crucible clone",
            "/remnant spawn",
            "/remnant heartbeat",
            "/remnant merge",
            "/remnant status",
            "/combo list",
            "/combo recommend",
            "/combo workflow",
            "/pillars list",
            "/pillars status",
            "/pillars get",
        ]
        return sorted(set(base + skill_cmds + extras))

    def is_builtin(self, name: str) -> bool:
        return name.lower() in BUILTIN_SLASH_NAMES

    def dispatch(self, line: str, ctx: SlashContext) -> str | None:
        stripped = line.strip()
        if not stripped.startswith("/"):
            return None
        parts = stripped[1:].split()
        if not parts:
            return "Empty slash command. Try /help"
        name = parts[0].lower()
        args = parts[1:]
        cmd = self._commands.get(name)
        if not cmd:
            return None
        return cmd.handler(ctx, args)


def skills_index_text() -> str:
    """Tier-0 skills index for help surfaces."""
    return build_skills_index_text()
