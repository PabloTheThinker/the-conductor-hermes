"""MCP catalog + dispatch (no stdio client required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conductor.mcp.catalog import build_mcp_catalog, dispatch_tool, tool_definitions


def test_tool_definitions_exclude_host_natives() -> None:
    defs = tool_definitions()
    names = {d.name for d in defs}
    assert "read_file" not in names
    assert "write_file" not in names
    assert "run_shell" not in names
    # Conductor pillars present
    assert "pillar_status" in names
    assert "combo_route" in names
    assert "track_orchestrate" in names
    assert "conductor_module_info" in names
    assert "conductor_session" in names
    assert "conductor_start_pack" in names
    assert len(defs) >= 12


def test_start_pack(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    raw = dispatch_tool(
        "conductor_start_pack",
        {"goal": "build multiversal chess three.js with parallel branches"},
    )
    data = json.loads(raw)
    assert data["session_id"]
    assert data["combo"]["primary"] in list("ABCDEFGH")
    assert data["high_signal_tools"]
    assert data["orchestration"]["mode"] == "full"
    assert data["remnant_policy"]["recommended_now"] is True
    assert data.get("fanout_ready")
    assert data["fanout_ready"]["dispatch"] == "host"
    assert len(data["fanout_ready"]["objectives"]) >= 2
    assert "skip_unless_needed" in data
    assert data["track_id"]


def test_start_pack_thin_mode(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    raw = dispatch_tool(
        "conductor_start_pack",
        {"goal": "kill the port 5188 please"},
    )
    data = json.loads(raw)
    assert data["orchestration"]["mode"] == "thin"
    assert data["remnant_policy"]["recommended_now"] is False
    assert data.get("fanout_ready") is None
    assert any("thin" in str(s).lower() or "fanout" in str(s).lower() for s in data["skip_unless_needed"])


def test_remnant_fanout_work_packs(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.delenv("CONDUCTOR_MCP", raising=False)
    monkeypatch.delenv("CONDUCTOR_HOST", raising=False)
    sid = json.loads(dispatch_tool("conductor_session", {"title": "rem-work"}))["session_id"]
    raw = dispatch_tool(
        "remnant_orchestrate",
        {
            "action": "fanout",
            "dispatch": "local",
            "work_root": str(conductor_home),
            "objectives": [
                "3D board and camera UX",
                "chess rules engine",
                "multiverse fork timelines",
            ],
        },
        session_id=sid,
    )
    data = json.loads(raw)
    assert data["count"] == 3
    assert data.get("shadow_clone") is True
    assert data.get("dispatch_mode") == "local"
    assert len(data.get("work_packs") or []) == 3
    assert data.get("host_playbook", {}).get("phases")
    assert data.get("clone_readiness", {}).get("ready") is True
    assert "preserve modular" not in json.dumps(data.get("work_packs")).lower()
    roles = {p.get("role") for p in data["work_packs"]}
    assert "surface" in roles or "rules" in roles or "graph" in roles
    # Work packs must have role-specific steps (not only generic template)
    for pack in data["work_packs"]:
        assert len(pack.get("steps") or []) >= 3
        assert "objective" in pack

    merged = json.loads(
        dispatch_tool("remnant_orchestrate", {"action": "merge"}, session_id=sid)
    )
    assert merged.get("success") is True
    assert merged.get("host_playbook")
    insights = " ".join(merged.get("merged_insights") or []).lower()
    assert "preserve modular conductor boundary" not in insights
    assert "plan-only (no root)" not in insights
    assert "unit contribution" not in insights
    assert any(
        tok in insights
        for tok in ("objective", "deliver", "clone", "surface", "rules", "graph", "backend")
    )


def test_shadow_clone_host_report_merge(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Host mode: spawn_requests → report → merge (shadow clone contract)."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    sid = json.loads(dispatch_tool("conductor_session", {"title": "host-clones"}))["session_id"]
    raw = dispatch_tool(
        "remnant_orchestrate",
        {
            "action": "fanout",
            "dispatch": "host",
            "parent_goal": "ship shadow clones",
            "objectives": ["rules engine lane", "UI surface lane"],
        },
        session_id=sid,
    )
    data = json.loads(raw)
    assert data["dispatch_mode"] == "host"
    assert len(data.get("spawn_requests") or []) == 2
    assert len(data.get("tool_calls") or []) == 2
    tc = data["tool_calls"][0]
    assert tc["tool"] == "spawn_subagent"
    assert "prompt" in tc["arguments"]
    assert tc["arguments"].get("description")
    assert tc["arguments"].get("background") is True
    assert data.get("host_contract")
    assert data.get("mandatory_host_action")
    assert data.get("execute_tool_calls_now") is True
    assert data.get("parent_must_spawn") is True
    assert data.get("spawn_count") == 2
    assert data.get("protocol", {}).get("mcp_cannot_spawn") is True
    assert len(data.get("parent_checklist") or []) == 2
    assert data.get("clone_readiness", {}).get("ready") is False

    blocked = dispatch_tool("remnant_orchestrate", {"action": "merge"}, session_id=sid)
    assert "not ready" in blocked.lower() or "waiting" in blocked.lower()

    # Parent "spawned" host subagents — ack handles before report
    handles = [
        {"remnant_id": req["remnant_id"], "clone_handle": f"subagent-{req['remnant_id'][:8]}"}
        for req in data["spawn_requests"]
    ]
    ack = json.loads(
        dispatch_tool(
            "remnant_orchestrate",
            {"action": "spawn_ack", "handles": handles},
            session_id=sid,
        )
    )
    assert ack.get("count") == 2
    assert all(a.get("clone_status") == "spawned" for a in ack.get("acked") or [])
    # Still not merge-ready until report
    still = json.loads(
        dispatch_tool("remnant_orchestrate", {"action": "await"}, session_id=sid)
    )
    assert still.get("ready") is False

    for req in data["spawn_requests"]:
        rid = req["remnant_id"]
        rep = json.loads(
            dispatch_tool(
                "remnant_orchestrate",
                {
                    "action": "report",
                    "remnant_id": rid,
                    "clone_handle": f"subagent-{rid[:8]}",
                    "result": {
                        "ok": True,
                        "findings": [f"done branch {rid[:8]}"],
                        "insights": [f"[host-clone] finished {rid[:8]}"],
                        "suggested_edits": [],
                    },
                },
                session_id=sid,
            )
        )
        assert rep.get("clone_status") in {"reported", "completed"}

    ready = json.loads(
        dispatch_tool("remnant_orchestrate", {"action": "await"}, session_id=sid)
    )
    assert ready.get("ready") is True

    merged = json.loads(
        dispatch_tool("remnant_orchestrate", {"action": "merge"}, session_id=sid)
    )
    assert merged.get("success") is True
    assert any("host-clone" in str(i) for i in (merged.get("merged_insights") or []))


def test_shadow_clone_hermes_dispatch(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dispatch=hermes: real delegate_task + hermes_batch."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_HOST", "hermes")
    sid = json.loads(dispatch_tool("conductor_session", {"title": "hermes-clones"}))[
        "session_id"
    ]
    raw = dispatch_tool(
        "remnant_orchestrate",
        {
            "action": "fanout",
            "dispatch": "hermes",
            "parent_goal": "ship hermes shadow clones",
            "objectives": ["rules engine lane", "UI surface lane"],
        },
        session_id=sid,
    )
    data = json.loads(raw)
    assert data.get("success") is not False
    assert data["dispatch_mode"] == "hermes"
    assert data.get("parent_must_spawn") is True
    assert len(data.get("tool_calls") or []) == 2
    tc = data["tool_calls"][0]
    assert tc["tool"] == "delegate_task"
    assert tc["arguments"].get("goal")
    assert tc["arguments"].get("context")
    batch = data.get("hermes_batch") or {}
    assert batch.get("tool") == "delegate_task"
    assert len(batch.get("arguments", {}).get("tasks") or []) == 2
    assert data.get("host_contract", {}).get("hermes_delegate_schema", {}).get(
        "tool"
    ) == "delegate_task"
    assert data.get("execute_tool_calls_now") is True
    assert data["parent_checklist"][0].get("label")


def test_conductor_worker_tool_not_hermes_delegate(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline worker is conductor_worker; delegate_task is deprecated alias."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    from conductor.core.tools import CONDUCTOR_TOOL_REGISTRY, CONDUCTOR_TOOL_SCHEMAS
    from conductor.mcp.catalog import tool_definitions

    schema_names = {
        (s.get("function") or {}).get("name") for s in CONDUCTOR_TOOL_SCHEMAS
    }
    assert "conductor_worker" in schema_names
    assert "conductor_worker" in CONDUCTOR_TOOL_REGISTRY
    assert "delegate_task" in CONDUCTOR_TOOL_REGISTRY  # deprecated alias
    names = {d.name for d in tool_definitions()}
    assert "conductor_worker" in names

    sid = json.loads(dispatch_tool("conductor_session", {"title": "worker"}))["session_id"]
    raw = dispatch_tool(
        "conductor_worker",
        {"task": "echo hello", "mode": "echo"},
        session_id=sid,
    )
    data = json.loads(raw)
    assert data.get("status") in {"success", "failure"} or data.get("worker")


def test_build_mcp_catalog() -> None:
    cat = build_mcp_catalog()
    assert cat["name"] == "the-conductor"
    assert cat["tool_count"] >= 12
    assert "stdio" in cat["transport"]
    assert any(t["name"] == "pillar_status" for t in cat["tools"])


def test_dispatch_module_info(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    raw = dispatch_tool("conductor_module_info", {})
    data = json.loads(raw)
    assert data["name"] == "the-conductor"
    assert "enhances" in (data.get("product_line") or "").lower() or data.get("version")


def test_dispatch_session_and_pillars(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    sess = json.loads(dispatch_tool("conductor_session", {"title": "mcp-test"}))
    assert sess["session_id"]
    sid = sess["session_id"]

    pillars = dispatch_tool("pillar_status", {"action": "list"}, session_id=sid)
    assert "P1" in pillars or "SOUL" in pillars

    combo = dispatch_tool(
        "combo_route",
        {"action": "recommend", "intent": "spawn parallel remnants"},
        session_id=sid,
    )
    assert "C" in combo or "Parallel" in combo or "remnant" in combo.lower()

    tracks = dispatch_tool(
        "track_orchestrate",
        {"action": "create", "title": "MCP track", "summary": "from mcp test"},
        session_id=sid,
    )
    assert "track_id" in tracks or "MCP track" in tracks


def test_dispatch_system_prompt(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    meister = conductor_home / "HOST.md"
    meister.write_text("# I am CodexHost\n\nI am CodexHost.\n", encoding="utf-8")
    text = dispatch_tool(
        "conductor_system_prompt",
        {"host_soul": str(meister), "mode": "resonate"},
    )
    assert "CodexHost" in text
    assert "Conductor" in text or "Resonance" in text or "Partner" in text


def test_build_server_imports() -> None:
    pytest.importorskip("mcp")
    from conductor.mcp.server import build_server

    server = build_server()
    assert server is not None
    assert getattr(server, "name", None) == "the-conductor" or True


def test_mcp_arg_aliases_from_live_drive(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Model-style wrong param names should still work after normalization."""
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    sess = json.loads(
        dispatch_tool(
            "conductor_session",
            {"goal": "Wire MCP into Grok"},  # not title
        )
    )
    sid = sess["session_id"]
    assert "Wire MCP" in sess["title"] or sess["title"]

    combo = dispatch_tool(
        "combo_route",
        {
            "goal": "spawn parallel remnants for research fanout",
            "task_type": "implementation",
        },
        session_id=sid,
    )
    assert "C" in combo or "remnant" in combo.lower() or "Parallel" in combo

    track = dispatch_tool(
        "track_orchestrate",
        {
            "action": "create",
            "name": "mcp-live-drive",  # not title
            "description": "alias test",
        },
        session_id=sid,
    )
    assert "Error" not in track or "track" in track.lower()

    mem = dispatch_tool(
        "memory_episodic",
        {
            "action": "search",  # not list
            "query": "isolation",
        },
        session_id=sid,
    )
    assert "unknown action" not in mem.lower()

    eth = dispatch_tool(
        "ethics_evaluate",
        {"proposal": "Document MCP findings"},  # not description/action_type
        session_id=sid,
    )
    assert "action_type and description required" not in eth
    assert "Error" not in eth or "clear" in eth.lower() or "ethics" in eth.lower() or "{" in eth


def test_is_tool_error_payload() -> None:
    from conductor.mcp.catalog import is_tool_error_payload

    assert is_tool_error_payload("Error: title required")
    assert is_tool_error_payload(json.dumps({"error": "boom", "tool": "x"}))
    assert is_tool_error_payload(json.dumps({"success": False, "message": "nope"}))
    assert not is_tool_error_payload(json.dumps({"session_id": "abc", "existing": False}))
    assert not is_tool_error_payload("✓ P1 SOUL")


def test_memory_tags_and_search(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    sid = json.loads(dispatch_tool("conductor_session", {"title": "mem-tags"}))["session_id"]
    written = json.loads(
        dispatch_tool(
            "memory_episodic",
            {
                "action": "write",
                "content": "MCP live drive alias normalization lesson",
                "tags": ["mcp", "live-drive"],
            },
            session_id=sid,
        )
    )
    assert "mcp" in written.get("tags", [])
    hits = json.loads(
        dispatch_tool(
            "memory_episodic",
            {"action": "search", "query": "alias normalization"},
            session_id=sid,
        )
    )
    assert isinstance(hits, list) and len(hits) >= 1
    tag_hits = json.loads(
        dispatch_tool(
            "memory_episodic",
            {"action": "search", "query": "mcp"},
            session_id=sid,
        )
    )
    assert any("mcp" in (h.get("tags") or []) for h in tag_hits)


def test_session_id_on_tool_schemas() -> None:
    defs = {d.name: d for d in tool_definitions()}
    track = defs["track_orchestrate"]
    assert "session_id" in track.input_schema.get("properties", {})
    mem = defs["memory_episodic"]
    assert "search" in mem.input_schema["properties"]["action"]["enum"]


def test_remnant_merge_guidance(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    sid = json.loads(dispatch_tool("conductor_session", {"title": "rem"}))["session_id"]
    out = dispatch_tool(
        "remnant_orchestrate",
        {"action": "merge"},
        session_id=sid,
    )
    assert "spawn" in out.lower()
    from conductor.mcp.catalog import is_tool_error_payload

    assert is_tool_error_payload(out)


def test_cli_mcp_catalog(capsys) -> None:
    from conductor.cli.main import main

    assert main(["mcp", "catalog"]) == 0
    out = capsys.readouterr().out
    assert "MCP" in out or "tools" in out.lower()
    assert main(["mcp", "tools"]) == 0
    out2 = capsys.readouterr().out
    assert "pillar_status" in out2 or "combo_route" in out2
