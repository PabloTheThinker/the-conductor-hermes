"""Depth tests: track edges, procedural memory, RBMC backprop, deep merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.core.merge import tier3_deep_merge
from conductor.core.models import (
    EmotionalValence,
    ProgressHeartbeat,
    RemnantRecord,
    RemnantStatus,
)
from conductor.core.runtime import ConductorRuntime
from conductor.memory.fabric import MemoryFabric
from conductor.memory.procedural import ProceduralStore
from conductor.noesis.rbmc import RBMCConfig, run_rbmc
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore


@pytest.fixture
def session(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[SessionStore, str]:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    store = SessionStore()
    sid = store.create_session(source="test").id
    return store, sid


def test_track_edges_and_chessboard(session: tuple[SessionStore, str]) -> None:
    store, sid = session
    tracks = TrackStore(store)
    a = tracks.create_track(sid, title="Path A", priority=0.8, confidence=0.5)
    b = tracks.create_track(sid, title="Path B", priority=0.9, confidence=0.8)
    edge = tracks.link_tracks(
        sid, a.track_id, b.track_id, relation="conflicts_with", strength=0.85, reason="compete"
    )
    assert edge.relation == "conflicts_with"
    edges = tracks.list_edges(sid)
    assert len(edges) >= 1
    child = tracks.fork_track(sid, a.track_id, title="Path A.1")
    assert child.parent_id == a.track_id
    # fork adds forked_from edge
    assert any(e.relation == "forked_from" for e in tracks.list_edges(sid))
    board = tracks.chessboard(sid)
    assert board["summary"]["edges"] >= 2
    assert board["edges"]
    nb = tracks.neighbors(sid, a.track_id)
    assert nb["outbound"] or nb["inbound"]
    assert tracks.unlink_edge(sid, edge.edge_id)


def test_procedural_and_fabric(session: tuple[SessionStore, str]) -> None:
    store, sid = session
    fabric = MemoryFabric(store)
    fabric.write_episode(sid, content="did a thing", outcome="success")
    fabric.add_semantic(sid, statement="patterns compound")
    proc = fabric.add_procedure(
        sid,
        name="ship-check",
        steps=["pytest", "doctor", "review"],
        when_to_use="before release",
    )
    assert proc["name"] == "ship-check"
    assert len(ProceduralStore(store).list_entries(sid)) >= 1
    status = fabric.status(sid)
    assert status["session"]["episodic"] >= 1
    assert status["session"]["semantic"] >= 1
    assert status["session"]["procedural"] >= 1


def test_rbmc_backprop(session: tuple[SessionStore, str]) -> None:
    store, sid = session
    rt = ConductorRuntime(store)
    result = run_rbmc(
        rt,
        sid,
        objective="stabilize foundation rails",
        config=RBMCConfig(max_clones=2, auto_distill=True),
        human_acknowledged=True,
    )
    phases = [p.phase for p in result.phases]
    assert "select" in phases
    assert "backprop" in phases
    assert result.clone_ids
    # memory written
    from conductor.memory.episodic import EpisodicStore

    entries = EpisodicStore(store).list_entries(sid, limit=20)
    assert any("RBMC" in e.content for e in entries)


def test_tier3_deep_merge_logic() -> None:
    remnants = [
        RemnantRecord(
            remnant_id="r1",
            session_id="s",
            snapshot_id="snap",
            status=RemnantStatus.RUNNING,
            task_objective="explore",
            merge_insights=["insight-a"],
        ),
        RemnantRecord(
            remnant_id="r2",
            session_id="s",
            snapshot_id="snap",
            status=RemnantStatus.RUNNING,
            task_objective="explore",
            merge_insights=["insight-b"],
        ),
    ]
    hbs = [
        ProgressHeartbeat(
            heartbeat_id="h1",
            remnant_id="r1",
            progress_percent=80,
            key_decisions=["go left"],
            new_insights=["fast path"],
            emotional_valence_delta=EmotionalValence(primary="hopeful", intensity=0.6),
        ),
        ProgressHeartbeat(
            heartbeat_id="h2",
            remnant_id="r2",
            progress_percent=40,
            key_decisions=["go right"],
            new_insights=["safe path"],
            emotional_valence_delta=EmotionalValence(primary="tension", intensity=0.5),
        ),
    ]
    proposal, result = tier3_deep_merge(
        session_id="s",
        remnants=remnants,
        heartbeats=hbs,
        track_id="t1",
        track_version=2,
        rbmc_result={
            "objective": "explore",
            "phases": [{"phase": "distill"}],
            "distilled": {"promoted_insights": ["use compound step"]},
            "concepts_posted": ["compound: next irreversible step"],
        },
    )
    assert proposal.tier.value == "deep_simulation" or "deep" in str(proposal.tier)
    assert any("deep-sim" in i for i in result.merged_insights)
    assert result.success


def test_merge_deep_end_to_end(session: tuple[SessionStore, str]) -> None:
    store, sid = session
    rt = ConductorRuntime(store)
    r1 = rt.spawn_remnant(sid, objective="branch alpha", strategy="fast", human_acknowledged=True)
    r2 = rt.spawn_remnant(sid, objective="branch beta", strategy="safe", human_acknowledged=True)
    rid1 = r1["remnant_id"]
    rid2 = r2["remnant_id"]
    rt.record_remnant_heartbeat(
        sid,
        remnant_id=rid1,
        current_subtask="a",
        progress_percent=70,
        key_decisions=["alpha"],
        new_insights=["a-ok"],
    )
    rt.record_remnant_heartbeat(
        sid,
        remnant_id=rid2,
        current_subtask="b",
        progress_percent=50,
        key_decisions=["beta"],
        new_insights=["b-ok"],
    )
    out = rt.merge_remnants_deep(
        sid,
        remnant_ids=[rid1, rid2],
        objective="choose branch",
        human_acknowledged=True,
        run_rbmc=True,
    )
    assert out.get("success")
    assert out.get("merged_insights")
    assert "tier" in out
