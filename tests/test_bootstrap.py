"""Third-party bootstrap: package root marker + import ensure."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.bootstrap import (
    ensure_conductor_importable,
    package_src_root,
    shared_home_default,
    write_package_root_marker,
)
from conductor.setup_ext import setup_extension


def test_package_src_root_resolves_dev_checkout() -> None:
    root = package_src_root()
    assert root is not None
    assert (root / "conductor" / "__init__.py").is_file()


def test_ensure_importable() -> None:
    assert ensure_conductor_importable() is True


def test_write_marker_and_env(conductor_home: Path) -> None:
    marker = write_package_root_marker(conductor_home)
    assert marker is not None
    assert marker.is_file()
    text = marker.read_text(encoding="utf-8").strip()
    assert "conductor" in text or Path(text).exists()
    envf = conductor_home / "conductor.env"
    assert envf.is_file()
    body = envf.read_text(encoding="utf-8")
    assert "CONDUCTOR_HOME" in body
    assert "PYTHONPATH" in body


def test_setup_writes_marker(conductor_home: Path) -> None:
    report = setup_extension(home=conductor_home)
    assert report.ok, report.errors
    assert (conductor_home / "conductor_package_root").is_file()
    assert (conductor_home / "conductor.env").is_file()
    assert (conductor_home / "plugins" / "conductor" / "plugin.yaml").is_file()


def test_shared_home_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "my-hermes"
    custom.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(custom))
    monkeypatch.delenv("CONDUCTOR_HOME", raising=False)
    monkeypatch.delenv("CONDUCTOR_HOME", raising=False)
    assert shared_home_default() == custom.resolve()
