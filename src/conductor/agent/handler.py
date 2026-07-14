"""Shared user-input handler for CLI, dashboard, TUI gateway, and REPL."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from conductor.agent.runtime import AgentRuntime, StreamCallback
from conductor.session.store import SessionStore
from conductor.skills.commands import build_skill_invocation
from conductor.skills.loader import find_skill
from conductor.slash.goal import GoalManager
from conductor.slash.registry import SlashContext, SlashRegistry


@dataclass
class HandleResult:
    response: str
    tool_events: list[str] = field(default_factory=list)
    slash: bool = False
    skill: bool = False
    goal_messages: list[str] = field(default_factory=list)


def _dispatch_skill_slash(
    stripped: str,
    *,
    session_id: str,
    runtime: AgentRuntime,
    goals: GoalManager,
    on_token: StreamCallback | None,
    quiet: bool,
) -> HandleResult | None:
    """Run dynamic /<skill-name> invocations through the agent loop."""
    if not stripped.startswith("/"):
        return None
    parts = stripped[1:].split()
    if not parts:
        return None
    skill_name = parts[0].lower()
    if find_skill(skill_name) is None:
        return None

    instruction = " ".join(parts[1:]).strip()
    invocation = build_skill_invocation(skill_name, instruction)
    if invocation.startswith("Error:"):
        return HandleResult(response=invocation, slash=True, skill=True)

    goals.on_user_turn(session_id)
    # run_turn must stay quiet here — handler owns stdout for skill invocations
    turn = runtime.run_turn(
        session_id,
        invocation,
        on_token=on_token,
        quiet=True,
    )
    return HandleResult(
        response=turn.response,
        tool_events=turn.tool_events,
        skill=True,
    )


def handle_user_input(
    text: str,
    *,
    session_id: str,
    store: SessionStore,
    runtime: AgentRuntime,
    goals: GoalManager,
    registry: SlashRegistry | None = None,
    on_token: StreamCallback | None = None,
    on_goal: StreamCallback | None = None,
    quiet: bool = False,
    emit: Callable[[str], None] | None = None,
) -> HandleResult:
    """Route slash commands, skill invocations, user turns, and goal post-turn hooks."""
    stripped = text.strip()
    if not stripped:
        return HandleResult(response="")

    reg = registry or SlashRegistry()
    ctx = SlashContext(store=store, runtime=runtime, goals=goals, session_id=session_id)

    slash_out = reg.dispatch(stripped, ctx)
    if slash_out is not None:
        if emit:
            emit(slash_out)
        elif not quiet:
            print(slash_out)
        return HandleResult(response=slash_out, slash=True)

    skill_result = _dispatch_skill_slash(
        stripped,
        session_id=session_id,
        runtime=runtime,
        goals=goals,
        on_token=on_token,
        quiet=quiet,
    )
    if skill_result is not None:
        if emit:
            emit(skill_result.response)
        elif not quiet and skill_result.response:
            print(skill_result.response)
        return skill_result

    if stripped.startswith("/"):
        parts = stripped[1:].split()
        unknown = parts[0] if parts else ""
        msg = f"Unknown command: /{unknown}. Try /help"
        if emit:
            emit(msg)
        elif not quiet:
            print(msg)
        return HandleResult(response=msg, slash=True)

    goals.on_user_turn(session_id)
    turn = runtime.run_turn(session_id, stripped, on_token=on_token, quiet=quiet)

    goal_msgs: list[str] = []

    def hook_token(msg: str) -> None:
        stripped_msg = msg.strip()
        if "Goal achieved" in stripped_msg:
            if stripped_msg:
                goal_msgs.append(stripped_msg)
            if on_goal:
                on_goal(msg)
            return
        if on_token:
            on_token(msg)

    goals.post_turn_hook(
        session_id,
        turn.response,
        runtime,
        runtime.provider,
        tool_events=turn.tool_events,
        on_token=hook_token if (on_token or on_goal) else None,
        quiet=quiet,
    )

    return HandleResult(
        response=turn.response,
        tool_events=turn.tool_events,
        goal_messages=goal_msgs,
    )
