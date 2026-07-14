"""Promote learned seals → skills only if regression gate (pytest) passes.

Self-improve the harness without silently degrading prior capability.
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from conductor.memory.semantic import SemanticStore
from conductor.session.store import SessionStore
from conductor.skills.manager import skill_manage


@dataclass
class PromoteResult:
    ok: bool
    promoted: bool
    skill_name: str = ""
    reason: str = ""
    gate_output: str = ""
    gate_ran: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "promoted": self.promoted,
            "skill_name": self.skill_name,
            "reason": self.reason,
            "gate_ran": self.gate_ran,
            "gate_output": self.gate_output[:2000],
        }


def _slug(text: str, *, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:max_len] or "seal").strip("-")


def find_repo_root() -> Path | None:
    """Locate The Conductor package root for pytest regression gate."""
    env = (
        os.environ.get("CONDUCTOR_REPO", "").strip()
        or os.environ.get("ILO_REPO", "").strip()  # legacy
    )
    if env:
        p = Path(env).expanduser()
        if (p / "pyproject.toml").is_file():
            return p.resolve()
    # Walk from this file
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "conductor" / "_NATIVE_BRAIN").is_file():
            return parent
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "conductor").is_dir():
            return parent
    return None


def run_regression_gate(
    *,
    repo: Path | None = None,
    tests: list[str] | None = None,
    timeout_s: float = 120.0,
) -> tuple[bool, str]:
    """Run offline pytest subset. Returns (passed, output)."""
    root = repo or find_repo_root()
    if root is None:
        return False, "no repo root for regression gate (set CONDUCTOR_REPO)"

    default_tests = tests or [
        "tests/test_hermes_bridge.py",
        "tests/test_healing.py",
        "tests/test_judgment.py",
        "tests/test_public_harness_boundary.py",
        "tests/test_brain_smoke.py",
        "tests/test_setup_ext.py",
        "tests/test_harness_api.py",
    ]
    # Only include tests that exist
    chosen = [t for t in default_tests if (root / t).is_file()]
    if not chosen:
        chosen = ["tests/"]

    env = os.environ.copy()
    env.setdefault("CONDUCTOR_PROVIDER", "test")
    env["PYTHONPATH"] = str(root / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    py = (
        env.get("CONDUCTOR_PYTHON")
        or env.get("ILO_PYTHON")  # legacy
        or "python3"
    )
    cmd = [
        py,
        "-m",
        "pytest",
        "-q",
        "--tb=line",
        *chosen,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out[-4000:]
    except subprocess.TimeoutExpired:
        return False, "regression gate timed out"
    except OSError as exc:
        return False, f"regression gate failed to run: {exc}"


def promote_seal_to_skill(
    store: SessionStore,
    session_id: str,
    *,
    seal_statement: str = "",
    note_id: str = "",
    skip_gate: bool = False,
    force_gate: bool = True,
) -> PromoteResult:
    """Create a skill from a learned seal only if regression tests pass.

    ``skip_gate`` is for unit tests that mock the gate; production should keep gate on.
    """
    statement = (seal_statement or "").strip()
    if not statement and note_id:
        for n in SemanticStore(store).list_notes(session_id, limit=100):
            if n.note_id == note_id or n.note_id.startswith(note_id):
                statement = n.statement
                break
    if not statement:
        # latest seal-tagged note
        for n in SemanticStore(store).list_notes(session_id, limit=20):
            if "seal" in (n.tags or []) or "heal" in (n.tags or []):
                statement = n.statement
                break
    if not statement:
        return PromoteResult(ok=False, promoted=False, reason="no seal statement found")

    gate_out = ""
    gate_ran = False
    if force_gate and not skip_gate:
        gate_ran = True
        passed, gate_out = run_regression_gate()
        if not passed:
            return PromoteResult(
                ok=False,
                promoted=False,
                reason="regression gate failed — seal not promoted",
                gate_output=gate_out,
                gate_ran=True,
            )

    name = f"seal-{_slug(statement)}-{uuid.uuid4().hex[:6]}"
    description = f"Learned seal (regression-gated): {statement[:120]}"
    content = (
        f"# {name}\n\n"
        f"## Learned seal\n\n{statement}\n\n"
        "## When to use\n\n"
        "Apply this remediation when a similar wound appears "
        "(see integrity scars / heal_status).\n\n"
        "## Safety\n\n"
        "Never bypass path-safety or mass-wipe floors. "
        "Never expand blast radius.\n"
    )
    result_text = skill_manage(
        "create",
        name=name,
        description=description,
        content=content,
    )
    if result_text.startswith("Error"):
        return PromoteResult(
            ok=False,
            promoted=False,
            reason=result_text,
            gate_output=gate_out,
            gate_ran=gate_ran,
        )
    return PromoteResult(
        ok=True,
        promoted=True,
        skill_name=name,
        reason="promoted after regression gate" if gate_ran else "promoted (gate skipped)",
        gate_output=gate_out,
        gate_ran=gate_ran,
    )
