"""Interactive prompt_toolkit REPL for Conductor."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory

from conductor.agent.handler import handle_user_input
from conductor.agent.runtime import AgentRuntime
from conductor.config import load_config
from conductor.session.store import SessionStore
from conductor.slash.goal import GoalManager
from conductor.slash.registry import SlashRegistry


def run_repl(
    *,
    session_id: str | None = None,
    continue_last: bool = False,
    resume: str | None = None,
) -> int:
    cfg = load_config()
    store = SessionStore()
    runtime = AgentRuntime(store=store, cfg=cfg)
    goals = GoalManager(store, default_max_turns=cfg.goal_max_turns)
    registry = SlashRegistry()

    try:
        sid = runtime.ensure_session(
            resume=resume,
            continue_last=continue_last,
            source="cli",
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if session_id:
        rec = store.resolve_session(session_id)
        if not rec:
            print(f"Error: Session not found: {session_id}")
            return 1
        sid = rec.id

    completer = WordCompleter(registry.autocomplete(), ignore_case=True)
    session = PromptSession(history=InMemoryHistory(), completer=completer)

    print("◆ Conductor — type /help for commands, Ctrl-D or /exit to quit")
    print(f"  Session: {sid[:8]}…")
    print()

    while True:
        try:
            line = session.prompt("conductor> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        text = line.strip()
        if not text:
            continue
        if text in {"/exit", "/quit"}:
            print("Bye.")
            return 0

        handle_user_input(
            text,
            session_id=sid,
            store=store,
            runtime=runtime,
            goals=goals,
            registry=registry,
        )
