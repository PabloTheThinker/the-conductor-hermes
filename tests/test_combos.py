"""Pillar combo catalog, recommender, tool, and slash wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.combos import (
    COMBOS,
    format_combo_list,
    format_recommendation,
    format_workflow,
    get_combo,
    recommend_combo,
    workflow_steps,
)
from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY, CONDUCTOR_TOOL_SCHEMAS
from conductor.slash.registry import SlashRegistry


def test_catalog_complete() -> None:
    assert set(COMBOS) == {"A", "B", "C", "D", "E", "F", "G", "H"}
    for cid, combo in COMBOS.items():
        assert combo.id == cid
        assert workflow_steps(cid)
        assert get_combo(cid) is combo
        assert get_combo(combo.slug) is combo


def test_recommend_defaults_to_daily() -> None:
    rec = recommend_combo("")
    assert rec.primary.id == "A"


def test_recommend_remnant_parallel() -> None:
    rec = recommend_combo("explore both approaches in parallel with remnants")
    assert rec.primary.id == "C"


def test_recommend_heal() -> None:
    rec = recommend_combo("repair thrash after repeated tool failure and missing state")
    assert rec.primary.id == "F"


def test_recommend_explicit_combo_letter() -> None:
    rec = recommend_combo("please use combo E for this irreversible decision")
    assert rec.primary.id == "E"


def test_recommend_ship_folds_g() -> None:
    rec = recommend_combo("implement the feature then ship and verify with pytest")
    assert rec.fold_g or rec.primary.id == "G"


def test_formatters() -> None:
    assert "Daily driver" in format_combo_list()
    assert "Workflow" in format_workflow("C")
    assert "Combo recommendation" in format_recommendation("map risks on the chessboard")
    rec = recommend_combo("chessboard roadmap risks")
    assert rec.primary.id in {"B", "A"}  # B preferred
    assert rec.to_dict()["primary"] == rec.primary.id


def test_tool_registered() -> None:
    names = [
        (s.get("function") or {}).get("name") for s in CONDUCTOR_TOOL_SCHEMAS
    ]
    assert "combo_route" in names
    assert "combo_route" in CONDUCTOR_TOOL_REGISTRY
    out = CONDUCTOR_TOOL_REGISTRY["combo_route"](
        {"action": "list"}, session_id=None, store=None
    )
    assert "Combo" in out or "combo" in out.lower()
    rec = CONDUCTOR_TOOL_REGISTRY["combo_route"](
        {"action": "recommend", "intent": "spawn parallel remnants", "json": True},
        session_id=None,
        store=None,
    )
    assert '"primary"' in rec
    wf = CONDUCTOR_TOOL_REGISTRY["combo_route"](
        {"action": "workflow", "combo_id": "D"},
        session_id=None,
        store=None,
    )
    assert "Deep forge" in wf or "Crucible" in wf or "crucible" in wf.lower()


def test_slash_combo(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    reg = SlashRegistry()
    assert "combo" in reg.names()
    from conductor.agent.runtime import AgentRuntime
    from conductor.config import load_config
    from conductor.session.store import SessionStore
    from conductor.slash.goal import GoalManager
    from conductor.slash.registry import SlashContext

    store = SessionStore()
    sid = store.create_session(source="test").id
    ctx = SlashContext(
        store=store,
        runtime=AgentRuntime(store=store, cfg=load_config()),
        goals=GoalManager(store),
        session_id=sid,
    )
    out = reg.dispatch("/combo list", ctx)
    assert out and ("A" in out or "Daily" in out)
    out2 = reg.dispatch("/combo recommend irreversible high-stakes decision", ctx)
    assert out2 and "E" in out2
    out3 = reg.dispatch("/combo workflow C", ctx)
    assert out3 and ("Remnant" in out3 or "Parallel" in out3)
