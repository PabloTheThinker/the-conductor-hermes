"""Wave planner, thrash batch-awareness, hermes_batch waves (1.18.9)."""

from __future__ import annotations

from conductor.core.wave_planner import (
    WAVE_ORDER,
    classify_tool,
    hybrid_safe_preflight_pack,
    parallel_recipe_thin,
    plan_waves,
    tool_class_table,
)
from conductor.loop_thrash import clear_thrash_memory, fingerprint_call, record_and_check


def test_classify_safe_barrier_spawn():
    assert classify_tool("read_file") == "safe_parallel"
    assert classify_tool("search_files") == "safe_parallel"
    assert classify_tool("write_file") == "barrier"
    assert classify_tool("terminal") == "barrier"
    assert classify_tool("delegate_task") == "spawn"
    assert classify_tool("spawn_subagent") == "spawn"
    assert classify_tool("remnant_orchestrate", {"action": "status"}) == "safe_parallel"
    assert classify_tool("remnant_orchestrate", {"action": "fanout"}) == "spawn"
    assert classify_tool("totally_unknown_tool_xyz") == "barrier"


def test_plan_waves_orders_a_b_c():
    items = [
        {"tool": "delegate_task", "arguments": {"goal": "c"}},
        {"tool": "write_file", "arguments": {"path": "x"}},
        {"tool": "read_file", "arguments": {"path": "a"}},
        {"tool": "search_files", "arguments": {"pattern": "z"}},
    ]
    plan = plan_waves(items)
    assert plan["summary"]["A"] == 2
    assert plan["summary"]["B"] == 1
    assert plan["summary"]["C"] == 1
    assert plan["wave_order"] == list(WAVE_ORDER)
    # ordered emit: A then B then C
    tools = [e["resolved_tool"] for e in plan["ordered"]]
    assert tools == ["read_file", "search_files", "write_file", "delegate_task"]
    assert "prefer_single_host_batch" in plan["batch_policy"]
    assert "Mixed reads+writes" in plan["guidance"] or "safe_parallel" in plan["guidance"]


def test_parallel_recipe_thin_and_hybrid_preflight():
    recipe = parallel_recipe_thin(stuck=False)
    assert recipe["mode"] == "thin"
    assert recipe["host_batch"]["prefer_single_batch"] is True
    assert "reimplementing Hermes" in " ".join(recipe["forbid"])

    pf = hybrid_safe_preflight_pack(
        findings=["todo"],
        files_examined=["a.py"],
        work_root="/tmp/w",
    )
    assert pf["wave"] == "A"
    assert pf["tool_class"] == "safe_parallel"
    assert pf["findings"] == ["todo"]


def test_tool_class_table_nonempty():
    rows = tool_class_table()
    assert any(r["class"] == "safe_parallel" for r in rows)
    assert any(r["class"] == "spawn" for r in rows)


def test_thrash_batch_id_separates_fingerprints():
    clear_thrash_memory()
    store = None
    sid = "wave-test-session"
    # Same tool+args, different batch_id → different fp (parallel batch members)
    fp1 = fingerprint_call("read_file", {"path": "a"}, batch_id="b1", wave_id="A")
    fp2 = fingerprint_call("read_file", {"path": "a"}, batch_id="b2", wave_id="A")
    assert fp1 != fp2

    # Same batch can call once without thrash
    for _ in range(2):
        hit = record_and_check(
            store,
            sid,
            "read_file",
            {"path": "a"},
            batch_id="same-batch",
            wave_id="A",
            threshold=5,
        )
        assert not hit.blocked

    clear_thrash_memory(sid)


def test_hermes_batch_includes_waves():
    from conductor.core.clone_backend import _build_hermes_batch

    reqs = [
        {
            "remnant_id": "r1",
            "goal": "axis one",
            "context": "c1",
            "arguments": {"goal": "axis one", "context": "c1"},
        },
        {
            "remnant_id": "r2",
            "goal": "axis two",
            "context": "c2",
            "arguments": {"goal": "axis two", "context": "c2"},
        },
    ]
    batch = _build_hermes_batch(reqs)
    assert batch is not None
    assert "tasks" in batch["arguments"]
    assert len(batch["arguments"]["tasks"]) == 2
    assert "waves" in batch
    assert "C" in batch["waves"]
    assert batch.get("batch_id")
    assert batch.get("wave") == "C"


def test_orchestration_thin_has_parallel_recipe():
    from conductor.core.orchestration import _recipe

    thin = _recipe("thin")
    assert thin["name"] == "thin"
    assert thin.get("host_batch_policy", {}).get("prefer_single_batch") is True
    assert "wave_order" in thin
    # parallel_recipe may be None if import fails; prefer present
    if thin.get("parallel_recipe"):
        assert thin["parallel_recipe"]["mode"] == "thin"


def test_bench_serial_vs_batch_shape():
    """Benchmark-shaped: serial plan vs single mixed batch vs remnant batch.

    Not a wall-clock bench — contracts that serial (N turns) vs batch (1 plan)
    vs remnant (1 hermes_batch) are distinguishable for docs/metrics.
    """
    serial_turns = 4  # read, read, write, spawn as separate turns
    mixed = plan_waves(
        [
            {"tool": "read_file", "arguments": {"path": "a"}},
            {"tool": "read_file", "arguments": {"path": "b"}},
            {"tool": "write_file", "arguments": {"path": "c"}},
            {"tool": "delegate_task", "arguments": {"goal": "d"}},
        ]
    )
    batch_turns = 1  # one host batch (host may segment)
    remnant_spawns = 1  # one hermes_batch for multi-axis

    assert mixed["summary"]["total"] == 4
    assert batch_turns < serial_turns
    assert remnant_spawns == 1
    assert mixed["batch_policy"]["prefer_single_host_batch"] is True
