"""Chat entry — single-turn query or interactive REPL."""

from __future__ import annotations

import argparse

from conductor.agent.handler import handle_user_input
from conductor.agent.runtime import AgentRuntime
from conductor.config import load_config
from conductor.session.store import SessionStore
from conductor.slash.goal import GoalManager
from conductor.slash.registry import SlashRegistry


def run_chat(args: argparse.Namespace) -> int:
    if getattr(args, "tui", False):
        from conductor.hermes_host import launch_hermes

        try:
            return launch_hermes([])
        except FileNotFoundError as exc:
            print(f"Error: {exc}")
            return 1

    if getattr(args, "query", None):
        return _run_single_query(args)

    from conductor.cli.repl import run_repl

    return run_repl(
        continue_last=getattr(args, "continue_last", False),
        resume=getattr(args, "resume", None),
    )


def _run_single_query(args: argparse.Namespace) -> int:
    cfg = load_config()
    store = SessionStore()
    runtime = AgentRuntime(store=store, cfg=cfg)
    goals = GoalManager(store, default_max_turns=cfg.goal_max_turns)
    registry = SlashRegistry()

    try:
        sid = runtime.ensure_session(
            resume=getattr(args, "resume", None),
            continue_last=getattr(args, "continue_last", False),
            source="cli",
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    handle_user_input(
        args.query,
        session_id=sid,
        store=store,
        runtime=runtime,
        goals=goals,
        registry=registry,
    )
    return 0
