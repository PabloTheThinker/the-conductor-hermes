"""Hermes file-plugin bootstrap for The Conductor.

Hermes loads ``$HERMES_HOME/plugins/conductor/`` and calls ``register(ctx)``.
Implementation lives in ``conductor.adapters.hermes.plugin`` so pip entry-points
and the file plugin stay in sync.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("hermes.plugins.conductor")


def _ensure_import() -> None:
    """Make ``import conductor`` work when Hermes uses a different venv."""
    try:
        import conductor  # noqa: F401

        return
    except ImportError:
        pass
    home = (
        os.environ.get("HERMES_HOME", "").strip()
        or os.environ.get("CONDUCTOR_HOME", "").strip()
    )
    candidates: list[Path] = []
    if home:
        marker = Path(home).expanduser() / "conductor_package_root"
        if marker.is_file():
            try:
                line = marker.read_text(encoding="utf-8").strip().splitlines()[0].strip()
                candidates.append(Path(line))
            except OSError:
                pass
    for key in ("CONDUCTOR_ROOT", "CONDUCTOR_SRC", "CONDUCTOR_PACKAGE_ROOT"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidates.append(Path(raw).expanduser())
    for root in candidates:
        for cand in (root, root / "src"):
            if (cand / "conductor" / "__init__.py").is_file():
                s = str(cand.resolve())
                if s not in sys.path:
                    sys.path.insert(0, s)
                try:
                    import conductor  # noqa: F401

                    return
                except ImportError:
                    continue
    logger.error(
        "Conductor package not importable in this Hermes process. "
        "Install into the Hermes venv:  "
        "$(dirname $(which hermes))/python -m pip install -e /path/to/the-conductor-hermes  "
        "Or: conductor setup && conductor hermes-ready --install-pip  "
        "Or: source $HERMES_HOME/conductor.env before hermes"
    )


_ensure_import()


def register(ctx) -> None:
    """Hermes plugin entry — enhance the host agent, do not replace it."""
    try:
        from conductor.adapters.hermes.plugin import register as _register
    except ImportError as exc:
        logger.error("Conductor register failed: %s", exc)
        raise
    return _register(ctx)
