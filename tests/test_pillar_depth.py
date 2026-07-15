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
    # fork adds forked_from edge: child → parent
    fork_edges = [e for e in tracks.list_edges(sid) if e.relation == "forked_from"]
    assert any(
        e.from_track_id == child.track_id and e.to_track_id == a.track_id for e in fork_edges
    )
    board = tracks.chessboard(sid)
    assert board["summary"]["edges"] >= 2
    assert board["edges"]
    assert board["summary"].get("conflicts", 0) >= 1
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



def test_remnant_terminate_lifecycle(session: tuple[SessionStore, str]) -> None:
    """P5: terminate removes remnant from active merge set without merge."""
    store, sid = session
    rt = ConductorRuntime(store)
    r1 = rt.spawn_remnant(sid, objective="keep", strategy="fast", human_acknowledged=True)
    r2 = rt.spawn_remnant(sid, objective="drop", strategy="safe", human_acknowledged=True)
    rid1, rid2 = r1["remnant_id"], r2["remnant_id"]
    out = rt.terminate_remnant(sid, remnant_id=rid2, reason="stale path")
    assert out["status"] == "terminated"
    assert out["already_closed"] is False
    active = rt.list_remnants(sid, active_only=True)
    active_ids = {r["remnant_id"] if isinstance(r, dict) else r.remnant_id for r in active}
    assert rid2 not in active_ids
    assert rid1 in active_ids
    # second terminate is idempotent
    again = rt.terminate_remnant(sid, remnant_id=rid2, reason="again")
    assert again["already_closed"] is True


def test_tier2_and_tier3_gates_require_force_when_not_ready(
    session: tuple[SessionStore, str],
) -> None:
    """P5: reflective/deep share Tier1 readiness gates (force bypass)."""
    from conductor.core.models import CloneStatus

    store, sid = session
    rt = ConductorRuntime(store)
    r1 = rt.spawn_remnant(sid, objective="gate A", strategy="fast", human_acknowledged=True)
    rid = r1["remnant_id"]
    rt.record_remnant_heartbeat(
        sid,
        remnant_id=rid,
        current_subtask="partial",
        progress_percent=40,
        key_decisions=["hold"],
        new_insights=["partial signal"],
    )
    # Force clone into non-ready host-awaiting state via ledger helper
    rt._remnants._set_clone_fields(
        sid,
        remnant_id=rid,
        clone_status=CloneStatus.AWAITING_HOST,
        clone_handle="",
        load_meta=rt.load_meta,
        save_meta=rt.save_meta,
    )
    with pytest.raises(ValueError, match="not ready"):
        rt.merge_remnants_reflective(sid, remnant_ids=[rid], human_acknowledged=True)
    with pytest.raises(ValueError, match="not ready"):
        rt.merge_remnants_deep(
            sid, remnant_ids=[rid], objective="x", human_acknowledged=True, run_rbmc=False
        )
    forced = rt.merge_remnants_reflective(
        sid, remnant_ids=[rid], human_acknowledged=True, force=True
    )
    assert forced.get("success") is True or "merged_insights" in forced


def test_merge_still_active_ignores_terminated(
    session: tuple[SessionStore, str],
) -> None:
    """P5: terminated sibling does not block track resolve after merge."""
    store, sid = session
    rt = ConductorRuntime(store)
    r1 = rt.spawn_remnant(sid, objective="main path", strategy="fast", human_acknowledged=True)
    r2 = rt.spawn_remnant(sid, objective="side path", strategy="safe", human_acknowledged=True)
    rid1, rid2 = r1["remnant_id"], r2["remnant_id"]
    rt.record_remnant_heartbeat(
        sid,
        remnant_id=rid1,
        current_subtask="work",
        progress_percent=90,
        key_decisions=["keep main"],
        new_insights=["main viable"],
    )
    rt.terminate_remnant(sid, remnant_id=rid2, reason="abandon side")
    merged = rt.merge_remnants_tier1(sid, remnant_ids=[rid1], human_acknowledged=True)
    assert merged.get("success")
    # With only merged + terminated left, track should resolve
    assert merged.get("track_resolved") is True


def test_heartbeat_cap_trims_history(session: tuple[SessionStore, str], monkeypatch: pytest.MonkeyPatch) -> None:
    """P5: remnant heartbeat ledger respects soft cap."""
    import conductor.core.remnant as remnant_mod

    monkeypatch.setattr(remnant_mod, "REMNANT_HEARTBEATS_MAX", 5)
    store, sid = session
    rt = ConductorRuntime(store)
    r = rt.spawn_remnant(sid, objective="cap probe", strategy="fast", human_acknowledged=True)
    rid = r["remnant_id"]
    for i in range(8):
        out = rt.record_remnant_heartbeat(
            sid,
            remnant_id=rid,
            current_subtask=f"step-{i}",
            progress_percent=float(i * 10),
            new_insights=[f"insight-{i}"],
        )
    assert out["heartbeats_retained"] == 5
    meta = rt.load_meta(sid)
    hbs = (meta.get("remnant_heartbeats") or meta.get("remnants") or {})
    # bundle may nest under remnants meta key
    if isinstance(hbs, dict) and "remnant_heartbeats" not in str(type(hbs)):
        bundle_hbs = meta.get("remnant_heartbeats")
        if bundle_hbs is None:
            # inspect via ledger bundle
            bundle = rt._remnants._load_bundle(sid)
            assert len(bundle.get("remnant_heartbeats") or []) == 5
        else:
            assert len(bundle_hbs) == 5
    else:
        bundle = rt._remnants._load_bundle(sid)
        assert len(bundle.get("remnant_heartbeats") or []) == 5


def test_clone_register_idempotent(session: tuple[SessionStore, str]) -> None:
    """P4: re-register same clone_id does not duplicate bus/session lists."""
    from conductor.crucible.manager import CrucibleManager
    from conductor.crucible.models import CloneIdentity

    store, sid = session
    rt = ConductorRuntime(store, crucible=CrucibleManager())
    started = rt.start_crucible(sid, "clone dedupe", human_acknowledged=True)
    cid = started["crucible_session_id"]
    identity = CloneIdentity(
        clone_id="fork_a",
        birth_moment_label="t0",
        snapshot_summary="fork A identity",
    )
    rt._crucible.register_clone(cid, identity)
    rt._crucible.register_clone(cid, identity)
    sess = rt._crucible.get_session(cid)
    assert sess is not None
    assert sum(1 for c in sess.clones if c.clone_id == "fork_a") == 1
    assert sum(1 for c in sess.bus._clones if c.clone_id == "fork_a") == 1
    assert sess.bus._active_clone_ids.count("fork_a") == 1


def test_rbmc_concepts_per_clone(session: tuple[SessionStore, str]) -> None:
    store, sid = session
    rt = ConductorRuntime(store)
    result = run_rbmc(
        rt,
        sid,
        objective="concepts-per-clone gate",
        config=RBMCConfig(max_clones=2, concepts_per_clone=1, auto_distill=False),
        human_acknowledged=True,
    )
    sim = next(p for p in result.phases if p.phase == "simulate")
    # 2 clones × 1 concept each (reflect/compound posts are extra, not simulated)
    labels = sim.artifacts.get("labels") or []
    assert len(labels) == 2
    assert sim.artifacts.get("concepts_per_clone") == 1


def test_crucible_rehydrate_trace_and_distill(session: tuple[SessionStore, str]) -> None:
    """P4: workspace_events + snapshot survive process boundary; distill promotes."""
    from conductor.crucible.manager import CrucibleManager

    store, sid = session
    rt = ConductorRuntime(store, crucible=CrucibleManager())
    rt.start_crucible(sid, "rehydrate distill", human_acknowledged=True)
    rt.post_concept(
        sid,
        label="durable hypothesis: rails hold under restart",
        confidence=0.9,
        clone_id="prime",
        primary_emotion="curious",
        intensity=0.7,
    )
    meta = rt.load_meta(sid)
    assert meta.get("workspace_events")
    assert meta.get("last_snapshot")

    # Simulate process restart: new runtime + empty manager → rehydrate path
    rt2 = ConductorRuntime(store, crucible=CrucibleManager())
    assert rt2._crucible.get_session(meta["crucible_session_id"]) is None
    result = rt2.distill(sid, human_acknowledged=True)
    assert result.promoted_insights
    assert any("rails hold" in i or "durable" in i for i in result.promoted_insights)


def test_distill_appends_track_notes(session: tuple[SessionStore, str]) -> None:
    from conductor.crucible.manager import CrucibleManager

    store, sid = session
    rt = ConductorRuntime(store, crucible=CrucibleManager())
    tracks = TrackStore(store)
    track = tracks.ensure_default_track(sid, objective="keep notes")
    tracks.update_track(sid, track.track_id, conductor_notes="prior operator note")
    rt.start_crucible(sid, "note append", human_acknowledged=True)
    # Two high-confidence posts of same label → strong promote signal
    for conf in (0.88, 0.91):
        rt.post_concept(
            sid,
            label="promote: append-safe insight",
            confidence=conf,
            clone_id="prime",
            primary_emotion="focused",
            intensity=0.6,
        )
    distilled = rt.distill(sid, human_acknowledged=True)
    assert distilled.promoted_insights
    refreshed = tracks.get_track(sid, track.track_id)
    assert refreshed is not None
    assert "prior operator note" in refreshed.conductor_notes
    assert "Crucible distill:" in refreshed.conductor_notes
