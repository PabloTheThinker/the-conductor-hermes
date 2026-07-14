"""CLI module entry: python -m conductor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_package_has_main_module() -> None:
    import conductor

    main_path = Path(conductor.__file__).resolve().parent / "__main__.py"
    assert main_path.is_file(), "src/conductor/__main__.py required for python -m conductor"


def test_python_m_conductor_version() -> None:
    """Regression: package was not runnable as python -m conductor."""
    proc = subprocess.run(
        [sys.executable, "-m", "conductor", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = (proc.stdout or "") + (proc.stderr or "")
    assert "the-conductor" in out
    assert "1." in out
