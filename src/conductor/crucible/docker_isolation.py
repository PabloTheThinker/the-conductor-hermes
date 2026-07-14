"""Optional Docker isolation for Crucible pocket dimension.

When Docker is available, spin a network-isolated container that mounts the
filesystem pocket and writes an isolation proof. When Docker is unavailable
(or CONDUCTOR_CRUCIBLE_DOCKER=0), fall back to pure filesystem pocket isolation.

This keeps offline/test paths green while enabling real container isolation
in production when docker is installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def docker_available() -> bool:
    flag = (
        os.environ.get("CONDUCTOR_CRUCIBLE_DOCKER", "").strip()
        or os.environ.get("ILO_CRUCIBLE_DOCKER", "1").strip()  # legacy default on
    )
    if flag in {"0", "false", "no"}:
        return False
    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@dataclass
class IsolationResult:
    mode: str  # docker | filesystem
    ok: bool
    container_id: str = ""
    image: str = ""
    detail: str = ""
    proof_path: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "ok": self.ok,
            "container_id": self.container_id,
            "image": self.image,
            "detail": self.detail,
            "proof_path": self.proof_path,
            "started_at": self.started_at,
        }


def _write_proof(pocket: Path, payload: dict[str, Any]) -> Path:
    pocket.mkdir(parents=True, exist_ok=True)
    path = pocket / "isolation_proof.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def isolate_filesystem(pocket: Path, *, session_id: str, objective: str = "") -> IsolationResult:
    """Filesystem-only isolation (always available)."""
    proof = _write_proof(
        pocket,
        {
            "mode": "filesystem",
            "session_id": session_id,
            "objective": objective,
            "network": "host-process",
            "note": "In-process pocket; Docker unavailable or disabled",
            "at": datetime.now(UTC).isoformat(),
        },
    )
    return IsolationResult(
        mode="filesystem",
        ok=True,
        detail="filesystem pocket isolation",
        proof_path=str(proof),
    )


def isolate_docker(
    pocket: Path,
    *,
    session_id: str,
    objective: str = "",
    image: str | None = None,
    memory: str = "256m",
    cpus: str = "0.5",
    timeout_sec: int = 60,
) -> IsolationResult:
    """Run a hardened one-shot container with pocket mounted at /crucible."""
    image = image or (
        os.environ.get("CONDUCTOR_CRUCIBLE_IMAGE", "").strip()
        or os.environ.get("ILO_CRUCIBLE_IMAGE", "").strip()  # legacy
        or "python:3.11-slim-bookworm"
    )
    pocket = pocket.resolve()
    pocket.mkdir(parents=True, exist_ok=True)

    # Bootstrap script written into the pocket so container needs no custom image.
    bootstrap = pocket / "_docker_bootstrap.py"
    bootstrap.write_text(
        """
import json, os, socket, datetime
from pathlib import Path
root = Path("/crucible")
proof = {
    "mode": "docker",
    "session_id": os.environ.get("CRUCIBLE_SESSION_ID", ""),
    "objective": os.environ.get("CRUCIBLE_OBJECTIVE", ""),
    "hostname": socket.gethostname(),
    "network_probe": "blocked_or_none",
    "at": datetime.datetime.utcnow().isoformat() + "Z",
    "uid": os.getuid() if hasattr(os, "getuid") else None,
}
# Prove write to mounted volume
(root / "isolation_proof.json").write_text(json.dumps(proof, indent=2))
(root / "docker_ok").write_text("ok\\n")
print("crucible_docker_ok")
""".lstrip(),
        encoding="utf-8",
    )

    name = f"conductor-crucible-{session_id[:8]}-{int(time.time())}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        memory,
        "--cpus",
        cpus,
        "--pids-limit",
        "128",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "-v",
        f"{pocket}:/crucible:rw",
        "-e",
        f"CRUCIBLE_SESSION_ID={session_id}",
        "-e",
        f"CRUCIBLE_OBJECTIVE={objective[:200]}",
        "-w",
        "/crucible",
        image,
        "python",
        "/crucible/_docker_bootstrap.py",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return IsolationResult(
            mode="docker",
            ok=False,
            image=image,
            detail=f"docker run timed out after {timeout_sec}s",
        )
    except OSError as exc:
        return IsolationResult(
            mode="docker",
            ok=False,
            image=image,
            detail=f"docker run failed: {exc}",
        )

    proof_path = pocket / "isolation_proof.json"
    ok = proc.returncode == 0 and proof_path.is_file()
    detail = (proc.stdout or proc.stderr or "").strip()[:500]
    if not ok:
        detail = f"exit={proc.returncode} {detail}"
        # Fall back proof for audit trail
        if not proof_path.is_file():
            proof_path = _write_proof(
                pocket,
                {
                    "mode": "docker",
                    "ok": False,
                    "detail": detail,
                    "session_id": session_id,
                },
            )
    return IsolationResult(
        mode="docker",
        ok=ok,
        container_id=name,
        image=image,
        detail=detail or "docker isolation complete",
        proof_path=str(proof_path),
    )


def isolate_pocket(
    pocket: Path,
    *,
    session_id: str,
    objective: str = "",
    prefer_docker: bool = True,
) -> IsolationResult:
    """Best available isolation for a Crucible pocket."""
    if prefer_docker and docker_available():
        result = isolate_docker(pocket, session_id=session_id, objective=objective)
        if result.ok:
            return result
        # Soft fall-through if docker failed mid-run
        fs = isolate_filesystem(pocket, session_id=session_id, objective=objective)
        fs.detail = f"docker failed ({result.detail}); fell back to filesystem"
        return fs
    return isolate_filesystem(pocket, session_id=session_id, objective=objective)
