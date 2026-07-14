"""Offline brain smoke via real CLI entry (CONDUCTOR_PROVIDER=test)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.cli.main import main


def test_chat_query_offline(conductor_home: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("HERMES_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_PROVIDER", "test")
    monkeypatch.setenv("CONDUCTOR_PROVIDER", "test")  # compat during transition
    code = main(["chat", "-q", "Reply with exactly: CONDUCTOR_OK"])
    assert code == 0
    out = capsys.readouterr().out
    assert "CONDUCTOR_OK" in out


def test_version() -> None:
    assert main(["version"]) == 0


def test_status_conductor_brand(conductor_home: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.delenv("HERMES_AGENT_ROOT", raising=False)
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "The Conductor" in out
    assert "hermes" in out.lower()
    assert "ILO_OK" not in out
    # no product brand ILO in status
    assert "I.L.O" not in out
