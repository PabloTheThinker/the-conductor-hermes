"""Filesystem pocket dimension — durable sandbox for a Crucible session.

Offline-first: no Docker required. Each Crucible session gets a directory under
CONDUCTOR_HOME/crucible/<session_id>/ with workspace dumps, clone notes, and distill
artifacts. This is the operational “pocket dimension” surface.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conductor.paths import conductor_home


def crucible_root() -> Path:
    root = conductor_home() / "crucible"
    root.mkdir(parents=True, exist_ok=True)
    return root


def pocket_path(crucible_session_id: str) -> Path:
    path = crucible_root() / crucible_session_id
    path.mkdir(parents=True, exist_ok=True)
    (path / "clones").mkdir(exist_ok=True)
    (path / "workspace").mkdir(exist_ok=True)
    (path / "distill").mkdir(exist_ok=True)
    return path


def write_manifest(
    crucible_session_id: str,
    *,
    objective: str,
    agent_session_id: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    path = pocket_path(crucible_session_id)
    manifest = {
        "crucible_session_id": crucible_session_id,
        "agent_session_id": agent_session_id,
        "objective": objective,
        "opened_at": datetime.now(UTC).isoformat(),
        "kind": "pocket_dimension",
        "isolation": "filesystem",
        **(extra or {}),
    }
    target = path / "MANIFEST.json"
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def write_workspace_snapshot(crucible_session_id: str, snapshot: dict[str, Any]) -> Path:
    path = pocket_path(crucible_session_id)
    gen = snapshot.get("generation", 0)
    target = path / "workspace" / f"gen-{gen:05d}.json"
    target.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    latest = path / "workspace" / "latest.json"
    latest.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    return target


def write_clone_note(
    crucible_session_id: str,
    clone_id: str,
    *,
    birth_moment_label: str,
    summary: str,
    notes: list[str] | None = None,
) -> Path:
    path = pocket_path(crucible_session_id) / "clones" / f"{clone_id}.md"
    lines = [
        f"# Clone `{clone_id}`",
        "",
        f"- Birth: {birth_moment_label}",
        f"- Snapshot: {summary}",
        "",
        "## Notes",
        "",
    ]
    for note in notes or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_distill_result(crucible_session_id: str, result: dict[str, Any]) -> Path:
    path = pocket_path(crucible_session_id)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = path / "distill" / f"distill-{stamp}.json"
    target.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (path / "distill" / "latest.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    return target


def write_simulation_trace(crucible_session_id: str, trace: dict[str, Any]) -> Path:
    path = pocket_path(crucible_session_id)
    target = path / "simulation_trace.json"
    target.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
    return target


def pocket_status(crucible_session_id: str) -> dict[str, Any]:
    path = pocket_path(crucible_session_id)
    return {
        "path": str(path),
        "exists": path.is_dir(),
        "has_manifest": (path / "MANIFEST.json").is_file(),
        "workspace_files": len(list((path / "workspace").glob("*.json"))),
        "clone_notes": len(list((path / "clones").glob("*.md"))),
        "distill_files": len(list((path / "distill").glob("*.json"))),
    }
