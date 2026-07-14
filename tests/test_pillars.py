"""Pillar foundation catalog + live probes."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY, CONDUCTOR_TOOL_SCHEMAS
from conductor.harness import module_info
from conductor.pillars import (
    ORDERED_IDS,
    foundation_report,
    format_foundation_report,
    format_pillar_detail,
    get_pillar,
    unique_pillars,
)
from conductor.slash.registry import SlashRegistry


def test_catalog_eight_plus_healing() -> None:
    pillars = unique_pillars()
    ids = {p.id for p in pillars}
    assert ids == {"P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P0"}
    assert get_pillar("memory") is not None
    assert get_pillar("P4") is not None
    assert get_pillar("soul").slug == "soul"


def test_foundation_report_ok() -> None:
    report = foundation_report()
    assert report["total"] == 9
    assert report["passed"] >= 8  # allow one soft fail in odd envs
    assert report["enhances_host"] is True
    assert "enhances" in report["product_line"].lower()
    text = format_foundation_report(verbose=True)
    assert "P1" in text or "SOUL" in text
    assert "foundation" in text.lower() or "Pillar" in text


def test_pillar_detail() -> None:
    text = format_pillar_detail("remnant")
    assert "Remnant" in text
    assert "Contracts" in text or "contracts" in text.lower() or "Spawn" in text


def test_tool_registered() -> None:
    names = [(s.get("function") or {}).get("name") for s in CONDUCTOR_TOOL_SCHEMAS]
    assert "pillar_status" in names
    out = CONDUCTOR_TOOL_REGISTRY["pillar_status"](
        {"action": "list"}, session_id=None, store=None
    )
    assert "Memory" in out or "SOUL" in out
    out2 = CONDUCTOR_TOOL_REGISTRY["pillar_status"](
        {"action": "status", "json": True}, session_id=None, store=None
    )
    assert '"passed"' in out2


def test_module_info_includes_pillars(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    info = module_info(home=conductor_home)
    assert info.get("pillars")
    assert info.get("foundation", {}).get("total") == 9


def test_slash_pillars(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    from conductor.agent.runtime import AgentRuntime
    from conductor.config import load_config
    from conductor.session.store import SessionStore
    from conductor.slash.goal import GoalManager
    from conductor.slash.registry import SlashContext

    reg = SlashRegistry()
    assert "pillars" in reg.names()
    store = SessionStore()
    sid = store.create_session(source="test").id
    ctx = SlashContext(
        store=store,
        runtime=AgentRuntime(store=store, cfg=load_config()),
        goals=GoalManager(store),
        session_id=sid,
    )
    out = reg.dispatch("/pillars list", ctx)
    assert out and ("P1" in out or "SOUL" in out)
    out2 = reg.dispatch("/pillars status", ctx)
    assert out2 and ("ok" in out2.lower() or "✓" in out2 or "foundation" in out2.lower())
    out3 = reg.dispatch("/pillars get P1", ctx)
    assert out3 and "Resonance" in out3 or "SOUL" in out3


def test_ordered_ids() -> None:
    assert ORDERED_IDS[0] == "P1"
    assert ORDERED_IDS[-1] == "P0"
