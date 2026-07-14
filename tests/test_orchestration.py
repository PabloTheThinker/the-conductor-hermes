"""Orchestration policy — thin vs full + axis decomposition."""

from __future__ import annotations

from conductor.core.orchestration import (
    classify_orchestration,
    decompose_axes,
    fanout_payload_from_policy,
)


def test_thin_kill_port():
    p = classify_orchestration("kill the port 5188 please")
    assert p["mode"] == "thin"
    assert p["fanout_recommended"] is False
    assert p["recipe"]["name"] == "thin"


def test_full_threejs_math():
    p = classify_orchestration(
        "Deep Three.js black hole simulation with real math and shader ray marching"
    )
    assert p["mode"] == "full"
    assert p["fanout_recommended"] is True
    assert len(p["axes"]) >= 2
    assert p["dispatch_default"] == "host"


def test_decompose_and():
    axes = decompose_axes("build API server and UI dashboard and GPU worker")
    assert len(axes) >= 2
    assert all("objective" in a for a in axes)


def test_fanout_payload():
    p = classify_orchestration(
        "implement physics math and three.js visual and GPU path",
        force_mode="full",
    )
    payload = fanout_payload_from_policy(p, parent_goal="test")
    assert payload is not None
    assert payload["action"] == "fanout"
    assert payload["dispatch"] == "host"
    assert len(payload["objectives"]) >= 2


def test_force_thin():
    p = classify_orchestration(
        "build multiversal chess and GPU and UI",
        force_mode="thin",
    )
    assert p["mode"] == "thin"


def test_assessment_and_restart_are_thin():
    assert classify_orchestration("assessment on using the conductor")["mode"] == "thin"
    assert classify_orchestration("i restarted the session check on it")["mode"] == "thin"


def test_improve_orchestration_is_full():
    p = classify_orchestration(
        "using everything improve the conductor thin and full host clones"
    )
    assert p["mode"] == "full"
    assert p["fanout_recommended"] is True
    assert p.get("confidence", 0) >= 0.65


def test_filter_insights_strips_filler():
    from conductor.core.remnant_work import SHARED_DECISION, curate_insights, filter_insights

    cleaned = filter_insights(
        [
            "preserve modular conductor boundary",
            "[surface] objective: build UI canvas",
            "plan-only (no root)",
            "unit 1 contribution: stuff",
            "[surface] deliver: Ship interactive visual/UI slice with load-safe entry",
            "Branch objective «x» has a concrete artifact (code, doc, or checklist)",
            "Return JSON-ish summary with findings",
            "[verify] focus_tokens: Verify, adaptive, tests",
            "[verify] accept: Deliverable for «x» is runnable",
            "Sibling lanes untouched (role=verify)",
            SHARED_DECISION,
            "strategy-lane: do the thing carefully",
            "[verify] adaptive learner tests honest under hashseed=0",
            "[clone:finding] 8/8 tests pass under PYTHONHASHSEED=0",
        ]
    )
    assert "preserve modular conductor boundary" not in cleaned
    assert SHARED_DECISION not in cleaned
    assert not any("objective:" in x for x in cleaned)
    assert not any("deliver:" in x for x in cleaned)
    assert not any("focus_tokens" in x for x in cleaned)
    assert not any("concrete artifact" in x for x in cleaned)
    assert not any("json-ish" in x.lower() for x in cleaned)
    assert not any("strategy-lane" in x for x in cleaned)
    # Real findings survive
    assert any("honest under hashseed" in x for x in cleaned)
    assert any("8/8 tests pass" in x for x in cleaned)


def test_curate_insights_ranks_and_near_dedups():
    """AgentDrive-style: high-signal first; near-dup role prefixes collapse."""
    from conductor.core.remnant_work import curate_insights

    curated = curate_insights(
        [
            "parallel branches: execute each work pack then merge once",
            "[verify] objective: Verify Grid cycle clock and laws",
            "[verify] deliver: Write failing tests against real entry points",
            "[verify] accept: Deliverable for «Verify Grid» is runnable",
            "[verify] focus_tokens: Verify, Grid, cycle",
            "[grid] cycle clock and laws tests green",
            "[clone:finding] pytest 5 passed in 0.16s on grid-runtime",
            "[verify] pytest 5 passed in 0.16s on grid-runtime",  # near-dup of finding
            "[grid] CUDA path verified on 3060 artifacts",
            "[clone:finding] wrote data/runs/sample_living.json",
        ]
    )
    assert not any("objective:" in x for x in curated)
    assert not any("focus_tokens" in x for x in curated)
    assert not any("parallel branches" in x for x in curated)
    # Findings survive and clone:finding ranks above bare restatement
    assert any("sample_living" in x for x in curated)
    assert any("5 passed" in x for x in curated)
    # Near-dedup: only one of the pytest lines
    pytest_lines = [x for x in curated if "5 passed" in x]
    assert len(pytest_lines) == 1
    # Rank: concrete evidence near the front
    assert curated[0].startswith("[clone:finding]") or "passed" in curated[0] or "sample" in curated[0]


def test_curate_compresses_white_cell_style_merge_dump():
    """61-line sibling echo → ≤16 high-signal (1.17 live lesson)."""
    from conductor.core.remnant_work import DEFAULT_MERGE_INSIGHT_LIMIT, curate_insights

    dump = [
        "[clone:finding] pytest tests/ → 40 passed",
        "[clone:finding] Full suite pytest tests/: 40 passed in 0.26s",
        "[clone:finding] pytest 40 passed in 0.26s",
        "[clone:finding] pytest tests/ 40 passed",
        "[clone:finding] run_sim SMOKE_OK 20 cycles seed=1",
        "[clone:finding] smoke pathogens_end=4 total_kills=27",
        "[clone:finding] smoke 20c pathogens 32→4 kills 27",
        "[clone:finding] web/index.html sim.js core.js live on http://127.0.0.1:8765/",
        "[clone:finding] Serves via python -m http.server 8765 from web/",
        "[clone:finding] HTTP 200 on :8765",
        "[clone:finding] mutation genomes float32[-1,1] with point+recombine",
        "[clone:finding] mature_receptor raises cosine affinity under selection",
        "[clone:finding] laws.apply_cycle chemotaxis affinity phago NETosis energy sectors",
        "alternative-path: SoA agents + pure laws apply_cycle",
        "alternative-path: Digital sectors: n_theta=8 x n_z=6 cylinder bins",
        "alternative-path: HUD with metric bars + keyboard controls",
        "alternative-path: TubeGeometry vessel with physical material",
        "alternative-path: Mirror cancer-adapt-sim CDN three.js pattern",
        "alternative-path: LocalEngine fallback when core.js absent",
        "alternative-path: Phago/NET before chemotaxis move",
        "Repo started empty; mutation.py + package init landed first",
        "web/ empty; sibling clones writing Python src/wbc",
        "[warn] report without clone_handle (spawn proof weak)",
    ]
    # Blow up with near-dups
    dump = dump + dump + dump
    curated = curate_insights(dump)
    assert len(curated) <= DEFAULT_MERGE_INSIGHT_LIMIT
    alt = [x for x in curated if x.lower().startswith("alternative-path:")]
    assert len(alt) <= 2
    assert any("8765" in x or "pytest" in x.lower() for x in curated)
    assert not any("objective:" in x for x in curated)


def test_ensure_shared_decisions_pins_alignment():
    from conductor.core.remnant_work import SHARED_DECISION, ensure_shared_decisions

    d = ensure_shared_decisions(["own only files for this axis", "lane-local: mutation.py"])
    assert d[0] == SHARED_DECISION
    assert any("mutation" in x for x in d)


def test_divergence_low_when_shared_decision_pinned():
    """Lane-local extras must not force Tier-2 if SHARED_DECISION is shared."""
    from conductor.core.merge import _divergence_score, tier1_fast_merge
    from conductor.core.models import EmotionalValence, ProgressHeartbeat, RemnantRecord, RemnantStatus
    from conductor.core.remnant_work import SHARED_DECISION

    hbs = [
        ProgressHeartbeat(
            heartbeat_id="h1",
            remnant_id="r1",
            progress_percent=100.0,
            key_decisions=[SHARED_DECISION, "lane: mutation.py only"],
            new_insights=["[clone:finding] pytest 40 passed"],
            emotional_valence_delta=EmotionalValence(primary="focused", intensity=0.5),
        ),
        ProgressHeartbeat(
            heartbeat_id="h2",
            remnant_id="r2",
            progress_percent=100.0,
            key_decisions=[SHARED_DECISION, "lane: web/sim.js only"],
            new_insights=["[clone:finding] http://127.0.0.1:8765/ live"],
            emotional_valence_delta=EmotionalValence(primary="focused", intensity=0.5),
        ),
        ProgressHeartbeat(
            heartbeat_id="h3",
            remnant_id="r3",
            progress_percent=100.0,
            # forgot SHARED_DECISION — floor inject should still align process
            key_decisions=["lane: tests only"],
            new_insights=["[clone:finding] smoke pathogens 32→4"],
            emotional_valence_delta=EmotionalValence(primary="focused", intensity=0.5),
        ),
    ]
    div = _divergence_score(hbs)
    assert div < 0.2, f"expected Tier-1 eligible divergence, got {div}"

    remnants = [
        RemnantRecord(
            remnant_id=f"r{i}",
            session_id="s",
            snapshot_id=f"s{i}",
            status=RemnantStatus.RUNNING,
            task_objective=f"lane {i}",
            merge_insights=[],
        )
        for i in range(1, 4)
    ]
    _p, result = tier1_fast_merge(
        session_id="s",
        remnants=remnants,
        heartbeats=hbs,
        track_id="t",
        track_version=1,
    )
    assert result.success
    assert len(result.merged_insights) <= 16
    assert not any(x.lower().startswith("alternative-path:") for x in result.merged_insights)


def test_tier1_merge_never_leaks_pack_chrome():
    """merge_insights leftover on remnants must be curated, not appended raw."""
    from conductor.core.merge import tier1_fast_merge
    from conductor.core.models import (
        EmotionalValence,
        ProgressHeartbeat,
        RemnantRecord,
        RemnantStatus,
    )

    remnants = [
        RemnantRecord(
            remnant_id="r1",
            session_id="s1",
            snapshot_id="snap1",
            status=RemnantStatus.RUNNING,
            task_objective="Verify tests",
            merge_insights=[
                "[verify] objective: Verify tests",
                "[verify] deliver: Write failing tests",
                "[clone:finding] 8/8 tests pass under PYTHONHASHSEED=0",
            ],
        ),
        RemnantRecord(
            remnant_id="r2",
            session_id="s1",
            snapshot_id="snap2",
            status=RemnantStatus.RUNNING,
            task_objective="Document protocol",
            merge_insights=[
                "[implement] accept: Deliverable for «docs» is runnable",
                "[docs] 1.14 protocol now project-visible",
            ],
        ),
    ]
    hbs = [
        ProgressHeartbeat(
            heartbeat_id="h1",
            remnant_id="r1",
            progress_percent=100.0,
            key_decisions=["parallel branches: execute each work pack then merge once"],
            new_insights=["[clone:finding] multi-seed gate prevents flaky theater"],
            emotional_valence_delta=EmotionalValence(primary="focused", intensity=0.5),
        ),
        ProgressHeartbeat(
            heartbeat_id="h2",
            remnant_id="r2",
            progress_percent=100.0,
            key_decisions=["parallel branches: execute each work pack then merge once"],
            new_insights=["[clone:finding] Documented Conductor host spawn protocol in README"],
            emotional_valence_delta=EmotionalValence(primary="focused", intensity=0.5),
        ),
    ]
    _prop, result = tier1_fast_merge(
        session_id="s1",
        remnants=remnants,
        heartbeats=hbs,
        track_id="t1",
        track_version=1,
    )
    assert result.success
    text = " | ".join(result.merged_insights).lower()
    assert "objective:" not in text
    assert "deliver:" not in text
    assert "accept:" not in text
    assert "focus_tokens" not in text
    assert "parallel branches" not in text
    assert any("8/8" in x or "multi-seed" in x for x in result.merged_insights)
    assert any("protocol" in x.lower() or "readme" in x.lower() for x in result.merged_insights)


def test_verify_role_spawns_write_capable_general_purpose():
    """verify must NOT be explore/read-only (cannot run pytest)."""
    from conductor.core.clone_worker import _role_to_host_spawn, build_host_spawn_request
    from conductor.core.remnant_work import build_work_pack

    pack = build_work_pack(
        objective="Verify adaptive learner tests under PYTHONHASHSEED=0",
        index=0,
        total=2,
    )
    assert pack["role"] == "verify"
    assert pack["host_subagent_type"] == "general-purpose"
    assert pack["host_capability_mode"] == "all"
    assert pack["insights"] == []  # no template insights

    sub, cap = _role_to_host_spawn("verify", pack["objective"], pack)
    assert sub == "general-purpose"
    assert cap == "all"

    req = build_host_spawn_request(
        remnant_id="rid-v",
        objective=pack["objective"],
        work_pack=pack,
        host="grok",
    )
    args = req["tool_call"]["arguments"]
    assert args["subagent_type"] == "general-purpose"
    assert args["capability_mode"] == "all"
    assert "shell" in args["prompt"].lower() or "pytest" in args["prompt"].lower() or "tests" in args["prompt"].lower()


def test_explore_role_stays_read_only():
    from conductor.core.clone_worker import _role_to_host_spawn

    sub, cap = _role_to_host_spawn("explore", "scout codebase structure")
    assert sub == "explore"
    assert cap == "read-only"


def test_hermes_host_spawn_is_delegate_task():
    """Hermes tool_call must be native delegate_task(goal, context)."""
    from conductor.core.clone_worker import build_host_spawn_request

    req = build_host_spawn_request(
        remnant_id="rid-hermes-1",
        objective="rules engine lane",
        session_id="sess-1",
        host="hermes",
        work_pack={"role": "rules", "steps": ["map legal moves"], "acceptance": ["tests"]},
    )
    assert req["host"] == "hermes"
    assert req.get("description")  # checklist UI only
    assert req.get("context")
    tc = req["tool_call"]
    assert tc["tool"] == "delegate_task"
    args = tc["arguments"]
    assert args.get("goal")
    assert args.get("context")
    assert "prompt" not in args
    assert "description" not in args
    assert req.get("after_complete", {}).get("arguments", {}).get("action") == "report"


def test_validate_host_tool_call_hermes_and_grok():
    from conductor.core.clone_backend import _validate_host_tool_call

    _validate_host_tool_call(
        {
            "tool": "delegate_task",
            "arguments": {"goal": "x", "context": "full context for child"},
        }
    )
    _validate_host_tool_call(
        {
            "tool": "spawn_subagent",
            "arguments": {"prompt": "p", "description": "d"},
        }
    )
    try:
        _validate_host_tool_call(
            {"tool": "delegate_task", "arguments": {"goal": "x"}}
        )
        raise AssertionError("expected missing context")
    except ValueError as exc:
        assert "context" in str(exc)
    try:
        _validate_host_tool_call(
            {"tool": "spawn_subagent", "arguments": {"prompt": "p"}}
        )
        raise AssertionError("expected missing description")
    except ValueError as exc:
        assert "description" in str(exc)


def test_dispatch_hermes_fanout_batch(monkeypatch, tmp_path):
    """dispatch=hermes returns hermes_batch + protocol; parent_must_spawn."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(tmp_path / "c-home"))
    monkeypatch.setenv("CONDUCTOR_HOST", "hermes")
    from conductor.core.clone_backend import dispatch_clones

    out = dispatch_clones(
        mode="hermes",
        clones=[
            {
                "remnant_id": "r1",
                "objective": "surface lane UI",
                "strategy": "",
                "work_pack": {"role": "surface"},
            },
            {
                "remnant_id": "r2",
                "objective": "backend API lane",
                "strategy": "",
                "work_pack": {"role": "backend"},
            },
        ],
        session_id="s1",
        parent_goal="ship hermes clones",
    )
    assert out["dispatch_mode"] == "hermes"
    assert out["host"] == "hermes"
    assert out.get("parent_must_spawn") is True
    assert out.get("spawn_count") == 2
    assert out.get("protocol", {}).get("mcp_cannot_spawn") is True
    assert len(out["tool_calls"]) == 2
    for tc in out["tool_calls"]:
        assert tc["tool"] == "delegate_task"
        assert tc["arguments"].get("goal")
        assert tc["arguments"].get("context")
    batch = out.get("hermes_batch") or {}
    assert batch.get("tool") == "delegate_task"
    assert len(batch.get("arguments", {}).get("tasks") or []) == 2
    assert batch.get("remnant_ids") == ["r1", "r2"]
    assert out.get("execute_tool_calls_now") is True
    assert out["host_contract"].get("hermes_delegate_schema", {}).get("tool") == "delegate_task"
    assert "delegate_task" in (out.get("mandatory_host_action") or "")


def test_chess_threejs_ai_uses_domain_axes():
    """Lesson: don't split check/checkmate as a lonely axis — use product lanes."""
    goal = (
        "Build a fully functional Three.js chess game with drag-and-drop, "
        "legal moves, checkmate, and an AI opponent with minimax"
    )
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert len(pol["axes"]) >= 3
    assert "rules" in roles or "rules" in objs
    assert "ai" in roles or "minimax" in objs
    assert "surface" in roles or "three" in objs
    # Weak scrap axis should not appear alone
    for a in pol["axes"]:
        assert a["objective"].strip().lower() not in {"check/checkmate", "checkmate"}


def test_repair_hermes_install_creates_layout(tmp_path, monkeypatch):
    from conductor.adapters.hermes.ready import hermes_ready_report, repair_hermes_install

    home = tmp_path / "hh"
    home.mkdir()
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home))
    result = repair_hermes_install(home=home, install_pip=False)
    assert result["setup_ok"] is True
    rep = hermes_ready_report(home=home)
    assert any(c.id == "setup_layout" and c.ok for c in rep.checks)


def test_official_website_goal_is_combo_c_and_domain_axes():
    """Website live-run: was Combo A + weak sentence split — must be C + product lanes."""
    from conductor.combos import recommend_combo

    goal = (
        "Build entire official million-dollar professional UI/UX website for The Conductor "
        "product: marketing landing, pillars, Hermes integration, docs CTA, dark editorial luxury"
    )
    rec = recommend_combo(goal)
    assert rec.primary.id == "C", rec.scores
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert len(pol["axes"]) >= 3
    assert "hero" in objs or "surface" in roles
    assert "pillar" in objs or "product" in roles or "product" in objs
    assert "hermes" in objs or "install" in objs or "docs" in roles
    # No lone luxury fragment as whole axis
    for a in pol["axes"]:
        assert a["objective"].strip().lower() not in {"dark editorial luxury", "docs cta"}


def test_greenfield_local_clone_names_website_deliverable():
    from conductor.core.clone_worker import run_clone_mission

    scroll = run_clone_mission(
        remnant_id="r-web",
        objective="Hero, brand system, navigation for official site",
        work_pack={"role": "surface", "steps": ["Ship hero", "Nav island"], "acceptance": []},
        work_root=None,
    )
    assert scroll["ok"] is True
    findings = " ".join(scroll["findings"]).lower()
    assert "greenfield" in findings
    assert "plan-only (no root)" not in " ".join(scroll.get("insights") or []).lower()
    paths = [e["path"] for e in scroll["suggested_edits"]]
    assert any("website" in p for p in paths)


def test_dnd_scifi_game_routes_combo_c_and_rpg_axes():
    """Self-loop: full D&D sci-fi game must not be Combo A / sentence scraps."""
    from conductor.combos import recommend_combo

    goal = (
        "Build a full-fledged D&D-style sci-fi browser game: character creation, "
        "d20 combat, exploration, inventory, quests, enemies, save/load"
    )
    rec = recommend_combo(goal)
    assert rec.primary.id == "C", rec.scores
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert len(pol["axes"]) >= 5
    assert "rules" in roles or "d20" in objs
    assert "combat" in roles or "combat" in objs
    assert "world" in roles or "quest" in objs or "map" in objs
    # not a single blob implement axis only
    assert not all(a["role"] == "implement" for a in pol["axes"])
    # character/meta present when full-fledged RPG
    assert any(a["role"] in {"character", "meta", "polish"} or "character" in a["objective"].lower() or "save" in a["objective"].lower() for a in pol["axes"])


def test_chess_fix_is_combo_c_not_daily_a():
    """Self-loop 1.18.5: bare 'fix chess AI…three.js' was Combo A."""
    from conductor.combos import recommend_combo

    goal = "fix chess AI with rules board and 3d rendering three.js"
    rec = recommend_combo(goal)
    assert rec.primary.id == "C", rec.scores
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = [a["role"] for a in pol["axes"]]
    assert roles.count("surface") <= 1, roles
    assert "integrate" in roles or any(
        "integrate" in a["objective"].lower() for a in pol["axes"]
    )
    assert "rules" in roles
    assert "ai" in roles


def test_landing_multi_section_is_full_with_product_lane():
    """Self-loop 1.18.5: short landing+N sections was thin with 0 axes."""
    from conductor.combos import recommend_combo

    goal = "landing page with 8 sections for SaaS product"
    rec = recommend_combo(goal)
    assert rec.primary.id == "C", rec.scores
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert len(pol["axes"]) >= 3
    assert "surface" in roles or "hero" in objs
    assert "product" in roles or "pillar" in objs or "product" in objs


def test_rpg_always_includes_character_lane():
    """Self-loop 1.18.5: end-to-end RPG without saying 'character' still needs create sheet."""
    goal = "end-to-end browser RPG game with inventory quests d20"
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert "character" in roles or "character" in objs
    assert len(pol["axes"]) >= 5


def test_official_site_always_has_product_axis():
    """Self-loop 1.18.5: official site without 'pillar' still gets product lane."""
    goal = "Build entire official professional UI/UX website for The Conductor"
    pol = classify_orchestration(goal)
    assert pol["mode"] == "full"
    roles = {a["role"] for a in pol["axes"]}
    objs = " ".join(a["objective"].lower() for a in pol["axes"])
    assert "product" in roles or "pillar" in objs or "product" in objs
    assert len(pol["axes"]) >= 3


def test_clone_scan_finds_game_js_by_content():
    """Path-only scan missed demos/stellar-codex/js/game.js for combat tokens."""
    from pathlib import Path
    from conductor.core.clone_worker import run_clone_mission
    from conductor.core.remnant_work import build_work_pack

    root = Path(__file__).resolve().parents[1] / "demos" / "stellar-codex"
    if not root.is_dir():
        return  # demo optional in slim checkouts
    pack = build_work_pack(objective="Combat system: turns, enemies, actions, loot")
    scroll = run_clone_mission(
        remnant_id="t-combat",
        objective="Combat system: turns, enemies, actions, loot",
        work_pack=pack,
        work_root=root,
    )
    files = scroll.get("files_examined") or []
    assert files, scroll.get("findings")
    assert any("game.js" in f or "index.html" in f for f in files)
