"""Soul Resonance — meister + partner wavelength merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.harness import get_system_prompt, resonate_souls
from conductor.soul.resonance import (
    build_resonance_block,
    discover_host_soul,
    resonate,
)


def test_resonate_with_inline_host() -> None:
    host = "# I am Atlas\n\nI speak briefly and love maps."
    result = resonate(
        host_soul=host,
        conductor_soul="# Conductor partner\n\nEthics Decision Checklist applies.\n\nimmutable core identity",
        mode="resonate",
        search_host=False,
        skills_block="",
        research_block="",
    )
    assert result.resonant
    assert "Atlas" in result.prompt
    assert "Soul Resonance" in result.prompt
    assert "Meister" in result.prompt
    assert "Partner" in result.prompt
    assert "Conductor partner" in result.prompt


def test_solo_mode_no_host() -> None:
    result = resonate(
        host_soul=None,
        conductor_soul="Partner body with Ethics Decision Checklist and immutable core identity.",
        mode="solo",
        search_host=False,
    )
    assert not result.resonant
    assert "solo" in result.prompt.casefold() or "Partner" in result.prompt or "Conductor" in result.prompt


def test_host_only_mode() -> None:
    host = "I am only the host voice."
    result = resonate(
        host_soul=host,
        conductor_soul="Should not appear in host_only",
        mode="host_only",
        search_host=False,
    )
    assert "only the host" in result.prompt
    assert "Should not appear" not in result.prompt


def test_discover_host_soul_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "openclaw"
    home.mkdir()
    soul = home / "SOUL.md"
    soul.write_text("# OpenClaw meister\n\nClaws out.\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_HOME", str(home))
    monkeypatch.delenv("CONDUCTOR_HOST_SOUL", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    found = discover_host_soul(search=True)
    assert found is not None
    assert "Claws out" in found.content
    assert found.label == "OpenClaw"


def test_env_host_soul_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "meister.md"
    p.write_text("Meister from env path.\n", encoding="utf-8")
    monkeypatch.setenv("CONDUCTOR_HOST_SOUL", str(p))
    found = discover_host_soul(search=False)
    assert found is not None
    assert "env path" in found.content


def test_get_system_prompt_resonates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_SOUL_MODE", "resonate")
    prompt = get_system_prompt(
        host_soul="# Host Nova\n\nCurious builder.",
        search_host=False,
    )
    assert "Nova" in prompt or "Host" in prompt
    assert "Resonance" in prompt or "Conductor" in prompt


def test_resonate_souls_api() -> None:
    data = resonate_souls(
        host_soul="# API Host\n\nHello.",
        mode="resonate",
        search_host=False,
    )
    assert "prompt" in data
    assert data.get("resonant") is True
    assert "API Host" in data["prompt"]


def test_build_resonance_block_rules() -> None:
    from conductor.soul.resonance import HostSoul

    block, notes = build_resonance_block(
        HostSoul(content="Host text", label="Hermes"),
        "Partner text with Ethics Decision Checklist",
        mode="resonate",
    )
    assert "wavelength" in block.casefold() or "Resonance" in block
    assert "Host text" in block
    assert "Partner text" in block
    assert notes
