"""Shared fixtures for The Conductor tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.session.store import SessionStore


@pytest.fixture
def conductor_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "conductor-home"
    home.mkdir()
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("CONDUCTOR_PROVIDER", "test")
    monkeypatch.delenv("HERMES_AGENT_ROOT", raising=False)
    return home


@pytest.fixture
def store(conductor_home: Path) -> SessionStore:
    return SessionStore()
