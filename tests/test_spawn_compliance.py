"""1.18.6 — anti-theater spawn compliance + local scaffold builders."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.core.clone_worker import run_clone_mission
from conductor.core.spawn_compliance import (
    assess_spawn_compliance,
    judgment_from_merge_insights,
)
from conductor.core.models import CloneStatus, RemnantRecord, RemnantStatus
from conductor.core.runtime import ConductorRuntime
from conductor.session.store import SessionStore


def _rec(**kwargs) -> RemnantRecord:
    base = dict(
        remnant_id="r1",
        session_id="s",
        snapshot_id="snap",
        task_objective="lane",
        status=RemnantStatus.RUNNING,
        clone_backend="host",
        clone_status=CloneStatus.AWAITING_HOST,
    )
    base.update(kwargs)
    return RemnantRecord(**base)


def test_awaiting_host_is_theater():
    v = assess_spawn_compliance(
        [_rec()], host_spawn_required=True, host_spawn_count=1
    )
    assert v["theater_risk"] is True
    assert v["ok"] is False


def test_handles_make_compliant():
    v = assess_spawn_compliance(
        [
            _rec(
                remnant_id="r1",
                clone_status=CloneStatus.REPORTED,
                clone_handle="sub-1",
            ),
            _rec(
                remnant_id="r2",
                clone_status=CloneStatus.REPORTED,
                clone_handle="sub-2",
            ),
        ],
        host_spawn_required=True,
        host_spawn_count=2,
    )
    assert v["theater_risk"] is False
    assert v["ok"] is True


def test_judgment_detects_evidence():
    j = judgment_from_merge_insights(
        ["[clone:finding] scaffold wrote: website/index.html", "vague note"]
    )
    assert j["done_proven"] is True
    j2 = judgment_from_merge_insights(["we did great work overall"])
    assert j2["done_proven"] is False


def test_local_clone_writes_scaffold(tmp_path: Path):
    scroll = run_clone_mission(
        remnant_id="scaffold-test-id",
        objective="Hero, brand system, navigation",
        work_pack={
            "role": "surface",
            "steps": ["Ship hero"],
            "acceptance": ["HTTP 200"],
        },
        work_root=tmp_path,
    )
    assert scroll["ok"] is True
    assert scroll.get("scaffold_count", 0) >= 1
    written = scroll.get("files_written") or []
    assert any("clone_scrolls" in p for p in written)
    # greenfield stub for website
    assert (tmp_path / "website" / "index.html").is_file() or any(
        "website" in p for p in written
    )


def test_host_fanout_blocks_report_and_merge_without_spawn():
    store = SessionStore()
    rt = ConductorRuntime(store)
    sid = store.create_session(source="test", title="theater").id
    out = rt.fanout_remnants(
        sid,
        objectives=["Hero brand system", "Product pillars section"],
        dispatch="host",
        parent_goal="official marketing website",
    )
    assert out.get("parent_must_spawn") is True
    ids = out["remnant_ids"]
    comp = rt.spawn_compliance(sid)
    assert comp["theater_risk"] is True

    with pytest.raises(ValueError, match="not ready|compliance|theater"):
        rt.merge_remnants_tier1(sid)

    with pytest.raises(ValueError, match="clone_handle|theater"):
        rt.report_remnant_clone(
            sid,
            remnant_id=ids[0],
            result={"ok": True, "insights": ["fake"], "findings": ["x"]},
        )


def test_happy_spawn_ack_report_merge_sets_done_proven():
    store = SessionStore()
    rt = ConductorRuntime(store)
    sid = store.create_session(source="test", title="happy").id
    out = rt.fanout_remnants(
        sid,
        objectives=["Hero brand system", "Product pillars section"],
        dispatch="host",
        parent_goal="official marketing website",
    )
    ids = out["remnant_ids"]
    rt.ack_remnant_spawns(
        sid,
        handles=[
            {"remnant_id": ids[0], "clone_handle": "sub-a"},
            {"remnant_id": ids[1], "clone_handle": "sub-b"},
        ],
    )
    for i, rid in enumerate(ids):
        rt.report_remnant_clone(
            sid,
            remnant_id=rid,
            clone_handle=f"sub-{'a' if i == 0 else 'b'}",
            result={
                "ok": True,
                "findings": [f"wrote website/s{i}.html", "HTTP 200"],
                "insights": [f"scaffold wrote: website/s{i}.html"],
            },
        )
    m = rt.merge_remnants_tier1(sid)
    assert m["success"] is True
    assert m.get("done_proven") is True
    assert m.get("judgment", {}).get("evidence_hits", 0) >= 1
