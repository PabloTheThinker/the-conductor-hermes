"""Hermes readiness diagnostics for any stock Hermes agent.

Used by ``conductor doctor``, ``conductor hermes-ready``, and ``/conductor-status``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ReadyCheck:
    id: str
    ok: bool
    message: str
    fix: str = ""
    level: str = "required"  # required | recommended | info


@dataclass
class ReadyReport:
    ok: bool
    hermes_bin: str | None
    hermes_python: str | None
    home: str
    checks: list[ReadyCheck] = field(default_factory=list)
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "hermes_bin": self.hermes_bin,
            "hermes_python": self.hermes_python,
            "home": self.home,
            "version": self.version,
            "checks": [asdict(c) for c in self.checks],
            "failed_required": [
                c.id for c in self.checks if c.level == "required" and not c.ok
            ],
        }


def _unwrap_hermes_bin(path: Path) -> Path:
    """Follow bash wrappers like ~/.local/bin/hermes → hermes-agent/venv/bin/hermes.

    Live lesson (1.18.6 server update): wrapper shebang is ``#!/usr/bin/env bash``
    which made hermes_python return /usr/bin/env and break pip/import checks.
    """
    p = path.expanduser()
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return p
    if not text.lstrip().startswith("#!"):
        return p
    # exec "/path/to/venv/bin/hermes" "$@"
    import re

    m = re.search(r'exec\s+["\']([^"\']+/hermes[^"\']*)["\']', text)
    if m:
        target = Path(m.group(1)).expanduser()
        if target.is_file():
            return target
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("exec ") and "hermes" in s:
            # exec /path/hermes "$@"
            parts = s.split()
            for tok in parts[1:]:
                tok = tok.strip("'\"")
                if tok.endswith("hermes") or "/hermes" in tok:
                    target = Path(tok).expanduser()
                    if target.is_file():
                        return target
    return p


def hermes_python(hermes_bin: str | None = None) -> str | None:
    """Python interpreter that runs the Hermes CLI (same venv preferred)."""
    from conductor.hermes_host import hermes_bin as _bin

    def _venv_python_path(py: Path) -> str:
        """Absolute path without following symlink to base CPython.

        uv venvs point bin/python → ~/.local/share/uv/python/...; if we
        ``resolve()`` that link, subprocess loses the venv site-packages and
        conductor import breaks (1.18.7 server-update lesson).
        """
        return str(py.expanduser().absolute())

    # Prefer well-known agent install layouts first
    home = Path.home()
    for cand in (
        home / ".hermes" / "hermes-agent" / "venv" / "bin" / "python",
        home / ".hermes" / "venv" / "bin" / "python",
        home / "hermes-agent" / "venv" / "bin" / "python",
    ):
        if cand.is_file() and os.access(cand, os.X_OK):
            return _venv_python_path(cand)

    path = hermes_bin or _bin()
    if not path:
        return None
    p = _unwrap_hermes_bin(Path(path))
    p = p.absolute() if p.exists() else Path(path).absolute()
    # venv/bin/hermes → venv/bin/python
    sibling = p.parent / "python"
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return _venv_python_path(sibling)
    sibling3 = p.parent / "python3"
    if sibling3.is_file() and os.access(sibling3, os.X_OK):
        return _venv_python_path(sibling3)
    # shebang (skip /usr/bin/env — not a real interpreter for -m pip)
    try:
        first = p.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
        if first and first[0].startswith("#!"):
            interp = first[0][2:].strip().split()[0]
            if interp not in {"/usr/bin/env", "env"} and Path(interp).is_file():
                # #!/path/to/python3
                if "python" in Path(interp).name:
                    return interp
    except OSError:
        pass
    return sys.executable


def conductor_importable_in(python: str | None) -> tuple[bool, str]:
    """Return (ok, detail) for ``import conductor`` under *python*."""
    if not python:
        return False, "no hermes python"
    if Path(python).name in {"env"} or str(python).endswith("/env"):
        return False, f"bad interpreter {python!r} (wrapper not unwrapped)"
    try:
        proc = subprocess.run(
            [python, "-c", "import conductor; print(conductor.__version__)"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "PYTHONNOUSERSITE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        ver = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else "?"
        return True, f"importable ({ver})"
    err = (proc.stderr or proc.stdout or "import failed").strip().splitlines()
    return False, err[-1] if err else "import failed"


def install_into_hermes_venv(
    *,
    repo_root: Path | None = None,
    python: str | None = None,
) -> tuple[bool, str]:
    """``pip install -e .`` into the Hermes interpreter (best-effort).

    Falls back to ``uv pip install --python`` when the venv has no pip module
    (common on uv-managed Hermes installs).
    """
    py = python or hermes_python()
    if not py:
        return False, "Hermes python not found — put hermes on PATH first"
    if Path(py).name in {"env"} or str(py).endswith("/env"):
        return False, f"refusing to install into bad interpreter {py!r}"
    root = repo_root
    if root is None:
        from conductor.bootstrap import package_src_root

        src = package_src_root()
        if src is None:
            return False, "cannot locate Conductor package root"
        root = src.parent if src.name == "src" else src
    root = Path(root).resolve()
    if not (root / "pyproject.toml").is_file():
        return False, f"no pyproject.toml under {root}"

    # Try python -m pip, then uv pip
    attempts: list[list[str]] = [
        [py, "-m", "pip", "install", "-e", str(root)],
    ]
    uv = shutil.which("uv")
    if uv:
        attempts.append(
            [uv, "pip", "install", "--python", py, "-e", str(root)]
        )
    last_err = ""
    for cmd in attempts:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_err = str(exc)
            continue
        if proc.returncode == 0:
            return True, f"installed editable into {py} via {cmd[0]}"
        last_err = (proc.stderr or proc.stdout or "")[-500:]
    return False, f"pip failed: {last_err}"


def hermes_ready_report(*, home: Path | None = None) -> ReadyReport:
    """Full checklist: any third-party Hermes agent can use this to self-diagnose."""
    from conductor import __version__
    from conductor.bootstrap import ensure_conductor_importable, package_src_root
    from conductor.hermes_host import hermes_bin, hermes_host_status
    from conductor.paths import conductor_home
    from conductor.setup_ext import PRODUCT_PLUGIN, assert_setup_layout

    h = Path(home) if home else conductor_home()
    h = h.expanduser().resolve()
    bin_path = hermes_bin()
    py = hermes_python(bin_path)
    checks: list[ReadyCheck] = []

    # Python version
    checks.append(
        ReadyCheck(
            id="python",
            ok=sys.version_info >= (3, 11),
            message=f"Python {sys.version_info.major}.{sys.version_info.minor}",
            fix="Use Python >= 3.11",
        )
    )

    # Hermes CLI
    checks.append(
        ReadyCheck(
            id="hermes_cli",
            ok=bin_path is not None,
            message=f"hermes binary: {bin_path or 'missing'}",
            fix="Install NousResearch/hermes-agent and put `hermes` on PATH (or set HERMES_BIN)",
        )
    )

    # Package importable in current process
    importable = ensure_conductor_importable()
    checks.append(
        ReadyCheck(
            id="package_import",
            ok=importable,
            message="conductor importable in current process"
            if importable
            else "conductor not importable here",
            fix="pip install -e /path/to/the-conductor-hermes",
        )
    )

    # Package importable in Hermes venv (critical for plugins)
    hermes_ok, hermes_detail = conductor_importable_in(py)
    checks.append(
        ReadyCheck(
            id="hermes_venv_import",
            ok=hermes_ok or bin_path is None,  # skip fail if no hermes yet
            message=f"Hermes venv: {hermes_detail}" if py else "Hermes venv: n/a",
            fix=(
                f"{py} -m pip install -e /path/to/the-conductor-hermes"
                if py
                else "Install Hermes first"
            ),
            level="required" if bin_path else "recommended",
        )
    )
    if bin_path and not hermes_ok:
        # still mark required failure
        checks[-1].ok = False

    # Shared home + plugin layout (one required check — avoid 5× NOT READY noise)
    missing = assert_setup_layout(h, harness="hermes")
    layout_detail = "; ".join(str(m) for m in missing[:4]) if missing else ""
    checks.append(
        ReadyCheck(
            id="setup_layout",
            ok=not missing,
            message=(
                "plugin+skills+config layout OK"
                if not missing
                else f"setup incomplete ({len(missing)}): {layout_detail}"
            ),
            fix="conductor hermes-ready --repair   # or: conductor setup --harness hermes",
        )
    )

    plugin_yaml = h / "plugins" / PRODUCT_PLUGIN / "plugin.yaml"
    checks.append(
        ReadyCheck(
            id="plugin_yaml",
            ok=plugin_yaml.is_file(),
            message=f"plugin at {plugin_yaml}" if plugin_yaml.is_file() else "plugin missing",
            fix="conductor hermes-ready --repair",
            level="info",  # already covered by setup_layout required
        )
    )

    skills = h / "skills" / "conductor"
    skill_n = len(list(skills.rglob("SKILL.md"))) if skills.is_dir() else 0
    checks.append(
        ReadyCheck(
            id="skills",
            ok=skill_n >= 3,
            message=f"{skill_n} conductor skills seeded",
            fix="conductor hermes-ready --repair",
            level="info" if skill_n >= 3 else "required",
        )
    )

    marker = h / "conductor_package_root"
    checks.append(
        ReadyCheck(
            id="package_root_marker",
            ok=marker.is_file() or hermes_ok,
            message="conductor_package_root present"
            if marker.is_file()
            else ("ok via hermes venv install" if hermes_ok else "no package root marker"),
            fix="conductor hermes-ready --repair",
            level="recommended",
        )
    )

    envf = h / "conductor.env"
    checks.append(
        ReadyCheck(
            id="conductor_env",
            ok=envf.is_file(),
            message=str(envf) if envf.is_file() else "conductor.env missing",
            fix="conductor hermes-ready --repair",
            level="recommended",
        )
    )

    # Do not require SOUL.md to be Conductor — Hermes owns meister SOUL
    meister = h / "SOUL.md"
    partner = h / "CONDUCTOR_PARTNER_SOUL.md"
    checks.append(
        ReadyCheck(
            id="meister_soul",
            ok=True,  # Hermes seeds SOUL on first run; never required for setup
            message=(
                "Hermes SOUL.md present (meister)"
                if meister.is_file()
                else "Hermes SOUL.md not yet (ok — hermes seeds it on first run)"
            ),
            fix="Run `hermes` once so Hermes can seed its own SOUL.md",
            level="info",
        )
    )
    checks.append(
        ReadyCheck(
            id="partner_soul",
            ok=partner.is_file() or package_src_root() is not None,
            message="partner SOUL available",
            fix="conductor hermes-ready --repair",
            level="recommended",
        )
    )

    # Config enables plugin (info if layout already failed — one required gate)
    cfg_ok = False
    cfg_msg = "config.yaml missing plugins.enabled"
    try:
        import yaml

        raw = yaml.safe_load((h / "config.yaml").read_text(encoding="utf-8")) or {}
        enabled = ((raw.get("plugins") or {}).get("enabled") or []) if isinstance(raw, dict) else []
        cfg_ok = PRODUCT_PLUGIN in [str(x) for x in enabled]
        cfg_msg = f"plugins.enabled includes {PRODUCT_PLUGIN}" if cfg_ok else f"plugins.enabled={enabled}"
    except Exception as exc:  # noqa: BLE001
        cfg_msg = f"config read: {exc}"
    checks.append(
        ReadyCheck(
            id="plugin_enabled",
            ok=cfg_ok,
            message=cfg_msg,
            fix="conductor hermes-ready --repair",
            level="info" if not missing else "info",
        )
    )

    # Spine
    try:
        from conductor.hermes_bridge import hermes_bridge_status

        spine = hermes_bridge_status()
        checks.append(
            ReadyCheck(
                id="spine",
                ok=bool(spine.get("spine_loaded")),
                message="path-safety spine loaded"
                if spine.get("spine_loaded")
                else f"spine: {spine}",
                fix="pip install the-conductor (path_safety module)",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            ReadyCheck(
                id="spine",
                ok=False,
                message=str(exc),
                fix="pip install -e .",
            )
        )

    # Host status note
    hs = hermes_host_status()
    checks.append(
        ReadyCheck(
            id="no_fork_required",
            ok=hs.get("requires_fork") is False,
            message="stock Hermes only (no fork required)",
            level="info",
        )
    )

    # 1.18.9+: delegation concurrency for hermes_batch / multi-clone fanout
    try:
        max_cc = None
        del_cfg: dict[str, Any] = {}
        try:
            import yaml

            raw = yaml.safe_load((h / "config.yaml").read_text(encoding="utf-8")) or {}
            del_cfg = (raw.get("delegation") or {}) if isinstance(raw, dict) else {}
            if isinstance(del_cfg, dict):
                raw_cc = del_cfg.get("max_concurrent_children")
                if raw_cc is not None:
                    max_cc = int(raw_cc)
        except Exception:  # noqa: BLE001
            max_cc = None
        # Hermes defaults to 3 when unset
        effective = max_cc if max_cc is not None else 3
        # Soft gate: warn when below 4 so multi-axis fanout is visible
        ok_cc = effective >= 3
        msg_cc = (
            f"delegation.max_concurrent_children={effective}"
            + ("" if max_cc is not None else " (Hermes default; unset in config)")
            + (
                " — raise for fanout n>3 (conductor batch-for-host skill)"
                if effective < 4
                else " — suitable for multi-clone hermes_batch"
            )
        )
        checks.append(
            ReadyCheck(
                id="delegation_concurrency",
                ok=ok_cc,
                message=msg_cc,
                fix=(
                    "In $HERMES_HOME/config.yaml set:\n"
                    "  delegation:\n"
                    "    max_concurrent_children: 6  # or >= planned hermes_batch size\n"
                    "See docs/HERMES.md § Host tool batch vs Remnant"
                ),
                level="info",
            )
        )
        # nested spawn depth (info)
        try:
            depth = del_cfg.get("max_spawn_depth") if isinstance(del_cfg, dict) else None
            depth_i = int(depth) if depth is not None else 1
        except (TypeError, ValueError):
            depth_i = 1
        checks.append(
            ReadyCheck(
                id="delegation_spawn_depth",
                ok=True,
                message=(
                    f"delegation.max_spawn_depth={depth_i} "
                    "(clones cannot nest when 1 — matches Grok/Hermes depth-1 contract)"
                ),
                level="info",
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            ReadyCheck(
                id="delegation_concurrency",
                ok=True,
                message=f"concurrency probe skipped: {exc}",
                level="info",
            )
        )

    required_fail = [c for c in checks if c.level == "required" and not c.ok]
    return ReadyReport(
        ok=len(required_fail) == 0,
        hermes_bin=bin_path,
        hermes_python=py,
        home=str(h),
        checks=checks,
        version=__version__,
    )


def repair_hermes_install(
    *,
    home: Path | None = None,
    install_pip: bool = False,
) -> dict[str, Any]:
    """Run setup (+ optional pip) so hermes-ready can flip NOT READY → READY.

    Lesson: agents saw multi-line layout failures and did not know the one fix
    was ``conductor setup`` against the shared Hermes home.
    """
    from conductor.setup_ext import setup_extension

    h = Path(home) if home else None
    report = setup_extension(
        home=h,
        force=True,
        harness="hermes",
        install_pip=install_pip if install_pip else False,
    )
    ready = hermes_ready_report(home=report.home)
    return {
        "setup_ok": report.ok,
        "setup_steps": list(report.steps),
        "setup_errors": list(report.errors),
        "ready": ready.to_dict(),
    }


def format_ready_report(*, verbose: bool = False, home: Path | None = None) -> str:
    rep = hermes_ready_report(home=home)
    lines = [
        f"◆ The Conductor — Hermes ready ({rep.version})",
        f"  home:   {rep.home}",
        f"  hermes: {rep.hermes_bin or '—'}",
        f"  python: {rep.hermes_python or '—'}",
        f"  status: {'READY' if rep.ok else 'NOT READY'}",
        "",
    ]
    for c in rep.checks:
        if c.level == "info" and not verbose and c.ok:
            continue
        mark = "✓" if c.ok else "✗"
        lines.append(f"  {mark} [{c.id}] {c.message}")
        if not c.ok and c.fix and (verbose or c.level == "required"):
            lines.append(f"      fix: {c.fix}")
    lines.append("")
    if rep.ok:
        lines.append("  Next: source $HERMES_HOME/conductor.env && hermes")
        lines.append("  In session: /pillars status · /combo recommend … · /conductor-status")
    else:
        lines.append("  One-shot repair: conductor hermes-ready --repair")
        lines.append("  Also:        conductor hermes-ready --install-pip")
    return "\n".join(lines)
