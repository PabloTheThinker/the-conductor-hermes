"""Stock Hermes host discovery for any machine.

Production engine is **upstream Hermes** (binary on PATH or HERMES_BIN).
No fork checkout required.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def hermes_bin() -> str | None:
    """Return path to stock ``hermes`` CLI if available."""
    explicit = (os.environ.get("HERMES_BIN") or "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
    which = shutil.which("hermes")
    if which:
        return which
    # Optional local layouts (not required) — any machine
    home = Path.home()
    candidates = [
        # Prefer real agent venv over ~/.local/bin bash wrapper (1.18.7)
        home / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / ".local" / "bin" / "hermes",
        home / ".hermes" / "bin" / "hermes",
        home / "hermes-agent" / "venv" / "bin" / "hermes",
        home / "src" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / "nous" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / "praetor" / "hermes-agent" / "venv" / "bin" / "hermes",
        home / "Praetor" / "Agent-Praetor" / "hermes-agent" / "venv" / "bin" / "hermes",
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c.resolve())
    return None


def hermes_available() -> bool:
    return hermes_bin() is not None


def hermes_host_status(**_kwargs: Any) -> dict[str, Any]:
    """Host discovery diagnostics. Accepts host kwargs (ignored)."""
    from conductor.bootstrap import ensure_conductor_importable, package_src_root

    path = hermes_bin()
    py = None
    try:
        from conductor.adapters.hermes.ready import hermes_python

        py = hermes_python(path)
    except Exception:  # noqa: BLE001
        py = None
    return {
        "hermes_bin": path,
        "available": path is not None,
        "hermes_bin_env": os.environ.get("HERMES_BIN") or "",
        "hermes_python": py,
        "conductor_importable": ensure_conductor_importable(),
        "conductor_src": str(package_src_root() or ""),
        "requires_fork": False,
        "product": "The Conductor",
        "plugin": "conductor",
    }


def _pythonpath_with_conductor(env: dict[str, str]) -> str:
    from conductor.bootstrap import package_src_root

    root = package_src_root()
    parts: list[str] = []
    if root is not None:
        parts.append(str(root))
    existing = env.get("PYTHONPATH", "")
    if existing:
        parts.append(existing)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return os.pathsep.join(out)


def launch_hermes(argv: list[str] | None = None, *, env: dict[str, str] | None = None) -> int:
    """Exec/run stock hermes with shared HERMES_HOME and conductor on PYTHONPATH."""
    from conductor.bootstrap import (
        ensure_conductor_importable,
        write_package_root_marker,
    )
    from conductor.paths import conductor_home

    bin_path = hermes_bin()
    if not bin_path:
        raise FileNotFoundError(
            "Stock Hermes CLI not found.\n"
            "Install NousResearch/hermes-agent (or your distro package), put\n"
            "`hermes` on PATH, or set HERMES_BIN=/path/to/hermes.\n"
            "Then:  conductor setup && hermes model && hermes"
        )
    home = str(conductor_home())
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    run_env["CONDUCTOR_HOME"] = home
    run_env["HERMES_HOME"] = run_env.get("HERMES_HOME") or home
    run_env.setdefault("CONDUCTOR_USE_HARNESS_AUTH", "1")
    run_env.setdefault("CONDUCTOR_HOST", "hermes")
    run_env.setdefault("CONDUCTOR_SOUL_MODE", "resonate")
    run_env.setdefault("CONDUCTOR_SPINE_ON_HERMES", "1")
    partner = Path(home) / "CONDUCTOR_PARTNER_SOUL.md"
    if partner.is_file():
        run_env.setdefault("CONDUCTOR_PARTNER_SOUL", str(partner))
    meister = Path(home) / "SOUL.md"
    if meister.is_file():
        run_env.setdefault("CONDUCTOR_HOST_SOUL", str(meister))
    run_env.pop("CONDUCTOR_LEGACY_FORK", None)
    # Make plugin imports work even if Hermes uses a different venv
    ensure_conductor_importable()
    write_package_root_marker(Path(home))
    pp = _pythonpath_with_conductor(run_env)
    if pp:
        run_env["PYTHONPATH"] = pp

    cmd = [bin_path, *(argv or [])]
    try:
        os.execvpe(cmd[0], cmd, run_env)
    except OSError:
        return int(subprocess.call(cmd, env=run_env))
