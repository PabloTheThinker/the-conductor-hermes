"""Stop/thrash/verify messaging — stop ≠ abort mission."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.agent.verify_stop import (
    CODE_WRITE_TOOLS,
    should_nudge_verify_on_stop,
    verify_nudge_message,
)
from conductor.loop_policy import evaluate_loop, loop_decision_suffix
from conductor.loop_thrash import clear_thrash_memory, record_and_check, thrash_block_message
from conductor.session.store import SessionStore


def test_thrash_message_not_abort_mission() -> None:
    msg = thrash_block_message(tool_name="terminal", count=3, fingerprint="abc")
    assert "NOT 'stop everything'" in msg
    assert "Mission continues" in msg
    assert "terminal" in msg


def test_loop_policy_thrash_scope(conductor_home: Path) -> None:
    store = SessionStore()
    sid = store.create_session(source="t").id
    d = evaluate_loop(store, sid, thrash=True)
    assert d.action == "stop"
    assert d.scope == "this_failure_class"
    assert "not" in d.escalate_hint.lower() or "NOT" in d.escalate_hint
    suffix = loop_decision_suffix(d)
    assert "this_failure_class" in suffix
    assert "whole mission" in suffix


def test_verify_nudge_is_one_shot_not_infinite() -> None:
    text = verify_nudge_message()
    assert "ONE nudge only" in text
    assert "stop everything" in text.lower() or "not an infinite" in text.lower()
    assert "patch" in CODE_WRITE_TOOLS or "write_file" in CODE_WRITE_TOOLS
    # After already_nudged, no more nudge
    assert (
        should_nudge_verify_on_stop(
            tool_names_this_turn=["write_file"],
            store=None,
            session_id=None,
            already_nudged=True,
            written_paths=["foo.py"],
        )
        is False
    )


def test_shared_home_prefers_hermes_with_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conductor.bootstrap import shared_home_default

    home = tmp_path / "user"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    # incomplete .conductor
    c = home / ".conductor"
    c.mkdir()
    # hermes with plugin
    h = home / ".hermes"
    (h / "plugins" / "conductor").mkdir(parents=True)
    (h / "plugins" / "conductor" / "plugin.yaml").write_text("name: conductor\n", encoding="utf-8")
    monkeypatch.delenv("CONDUCTOR_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    got = shared_home_default()
    assert got == h.resolve()


def test_thrash_then_new_args_allows(conductor_home: Path) -> None:
    clear_thrash_memory("tx")
    store = SessionStore()
    args = {"command": "echo a"}
    for _ in range(3):
        record_and_check(store, "tx", "terminal", args, threshold=3)
    blocked = record_and_check(store, "tx", "terminal", args, threshold=3)
    assert blocked.blocked
    # Different args → not blocked
    ok = record_and_check(store, "tx", "terminal", {"command": "echo b"}, threshold=3)
    assert not ok.blocked
