"""Operator eval kit + hook latency budgets (docs/BENCHMARKS.md).

Improvements validated here:
  A. Offline brain smoke contract
  B. Path-safety floors
  C. Pillar foundation probes
  D. Hook latency budgets (pre_tool / thrash / pre_llm)
  E. Soul Resonance fidelity (meister still names self)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from conductor.agent.path_safety import is_shell_denied
from conductor.cli.main import main
from conductor.harness import get_system_prompt, resonate_souls
from conductor.hermes_bridge import (
    pre_llm_call_hook,
    pre_tool_call_hook,
    spine_check_tool_call,
)
from conductor.loop_thrash import clear_thrash_memory, record_and_check
from conductor.pillars import foundation_report
from conductor.session.store import clear_store_cache, default_session_store


# Latency budgets (ms) — generous for CI, tight enough to catch 10× regressions
BUDGET_PRE_TOOL_MS = 2.0
BUDGET_THRASH_MS = 0.5
BUDGET_PRE_LLM_EMPTY_MS = 5.0


@pytest.fixture(autouse=True)
def _clean_hook_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONDUCTOR_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("CONDUCTOR_HOST_SOUL", raising=False)
    clear_store_cache()
    clear_thrash_memory()
    yield
    clear_store_cache()
    clear_thrash_memory()


def test_eval_kit_offline_smoke(capsys) -> None:
    """A — CONDUCTOR_OK contract."""
    import os

    os.environ["CONDUCTOR_PROVIDER"] = "test"
    code = main(["chat", "-q", "Reply with exactly: CONDUCTOR_OK"])
    assert code == 0
    assert "CONDUCTOR_OK" in capsys.readouterr().out


def test_eval_kit_path_safety() -> None:
    """B — catastrophic shell blocked."""
    assert is_shell_denied("rm -rf /") is not None
    assert is_shell_denied("rm -rf $HOME") is not None
    assert is_shell_denied("mkfs.ext4 /dev/sda") is not None
    assert is_shell_denied("ls -la") is None
    block = spine_check_tool_call("terminal", {"command": "rm -rf /"})
    assert block and "spine" in block.lower()


def test_eval_kit_foundation() -> None:
    """C — pillar foundation mostly green."""
    report = foundation_report()
    assert report["total"] == 9
    assert report["passed"] >= 8
    assert report["enhances_host"] is True


def test_hook_latency_pre_tool() -> None:
    """D — pre_tool allow path under budget (cached store + mem thrash)."""
    # warm caches
    pre_tool_call_hook(tool_name="terminal", args={"command": "ls"}, session_id="bench-sid")
    n = 200
    t0 = time.perf_counter()
    for i in range(n):
        # unique args so thrash never blocks
        pre_tool_call_hook(
            tool_name="terminal",
            args={"command": f"echo {i}"},
            session_id="bench-sid",
        )
    ms = (time.perf_counter() - t0) * 1000 / n
    assert ms < BUDGET_PRE_TOOL_MS, f"pre_tool {ms:.3f}ms exceeds budget {BUDGET_PRE_TOOL_MS}ms"


def test_hook_latency_thrash_memory() -> None:
    """D — thrash memory path is sub-ms."""
    store = default_session_store()
    n = 500
    t0 = time.perf_counter()
    for i in range(n):
        record_and_check(store, "thrash-sid", "terminal", {"command": f"uniq-{i}"})
    ms = (time.perf_counter() - t0) * 1000 / n
    assert ms < BUDGET_THRASH_MS, f"thrash {ms:.3f}ms exceeds budget {BUDGET_THRASH_MS}ms"


def test_thrash_blocks_repeats() -> None:
    store = default_session_store()
    clear_thrash_memory("t1")
    args = {"command": "same"}
    for _ in range(2):
        hit = record_and_check(store, "t1", "terminal", args, threshold=3)
        assert not hit.blocked
    hit = record_and_check(store, "t1", "terminal", args, threshold=3)
    assert hit.blocked
    assert "NOT 'stop everything'" in hit.message or "not 'stop everything'" in hit.message.lower()
    assert "Mission continues" in hit.message or "different action" in hit.message.lower()
    # pre_tool shape
    clear_thrash_memory("t2")
    for _ in range(3):
        pre_tool_call_hook(tool_name="terminal", args=args, session_id="t2")
    blocked = pre_tool_call_hook(tool_name="terminal", args=args, session_id="t2")
    assert blocked and blocked.get("action") == "block"
    assert "thrash" in (blocked.get("message") or "").lower()
    assert "stop everything" in (blocked.get("message") or "").lower() or "Mission continues" in (
        blocked.get("message") or ""
    )


def test_resonance_fidelity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """E — meister still names self under Conductor partner SOUL."""
    meister = tmp_path / "HOST_SOUL.md"
    meister.write_text(
        "# I am Atlas\n\nI am Atlas the map agent. My voice is brief.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONDUCTOR_HOST_SOUL", str(meister))
    monkeypatch.setenv("CONDUCTOR_SOUL_MODE", "resonate")
    data = resonate_souls(host_soul=str(meister), mode="resonate", search_host=False)
    assert data["resonant"] is True
    prompt = data["prompt"]
    assert "Atlas" in prompt
    assert "Soul Resonance" in prompt or "Meister" in prompt
    # Must not erase meister identity framing
    assert "I am Atlas" in prompt
    # Partner present
    assert "Conductor" in prompt or "Partner" in prompt

    sys_prompt = get_system_prompt(host_soul=str(meister), search_host=False)
    assert "Atlas" in sys_prompt


def test_session_store_cache() -> None:
    a = default_session_store()
    b = default_session_store()
    assert a is b


def test_pre_llm_empty_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty memory sessions should not thrash SQLite every turn (TTL)."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(tmp_path / "h"))
    clear_store_cache()
    store = default_session_store()
    sid = store.create_session(source="bench").id
    # First call may build empty
    pre_llm_call_hook(session_id=sid, user_message="hi")
    n = 100
    t0 = time.perf_counter()
    for _ in range(n):
        pre_llm_call_hook(session_id=sid, user_message="hi")
    ms = (time.perf_counter() - t0) * 1000 / n
    assert ms < BUDGET_PRE_LLM_EMPTY_MS, f"pre_llm empty {ms:.3f}ms over budget"
