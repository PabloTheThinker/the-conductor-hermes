"""Soul Resonance — meister + partner wavelength merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.harness import get_system_prompt, resonate_souls
from conductor.paths import soul_path
from conductor.soul.resonance import (
    build_resonance_block,
    discover_host_soul,
    load_conductor_soul,
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


def test_soul_path_prefers_partner_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared Hermes home: partner is CONDUCTOR_PARTNER_SOUL.md, not meister SOUL.md."""
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "SOUL.md").write_text(
        "You are Meister Nova — host agent only.\nNo partner markers.\n",
        encoding="utf-8",
    )
    partner = home / "CONDUCTOR_PARTNER_SOUL.md"
    partner.write_text(
        "# Partner\n\nYou are The Conductor\nSoul Resonance partner\n"
        "enhance the host agent\nEthics Decision Checklist\n"
        "immutable core identity for the Conductor\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.delenv("CONDUCTOR_PARTNER_SOUL", raising=False)
    monkeypatch.delenv("CONDUCTOR_HOST_SOUL", raising=False)
    assert soul_path().resolve() == partner.resolve()
    text, path = load_conductor_soul()
    assert path is not None
    assert path.resolve() == partner.resolve()
    assert "enhance the host" in text.casefold()
    assert "Meister Nova" not in text


def test_soul_path_env_partner_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "h"
    home.mkdir()
    (home / "SOUL.md").write_text("meister body\n", encoding="utf-8")
    (home / "CONDUCTOR_PARTNER_SOUL.md").write_text(
        "You are The Conductor\nenhance the host\n", encoding="utf-8"
    )
    explicit = tmp_path / "explicit_partner.md"
    explicit.write_text(
        "EXPLICIT partner wavelength\nenhance the host\nSoul Resonance\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.setenv("CONDUCTOR_PARTNER_SOUL", str(explicit))
    assert soul_path().resolve() == explicit.resolve()


def test_shared_home_resonate_not_double_meister(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "shared"
    home.mkdir()
    meister = home / "SOUL.md"
    meister.write_text(
        "# I am Nova\n\nI am the host meister. Unique meister marker ZYX-NOVA.\n",
        encoding="utf-8",
    )
    partner = home / "CONDUCTOR_PARTNER_SOUL.md"
    partner.write_text(
        "# Partner wavelength\n\nYou are The Conductor — Soul Resonance partner.\n"
        "You enhance the host agent — not replace it.\n"
        "Ethics Decision Checklist applies.\n"
        "immutable core identity for the Conductor.\n"
        "UNIQUE_PARTNER_MARKER_QRS\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.setenv("CONDUCTOR_HOST_SOUL", str(meister))
    monkeypatch.delenv("CONDUCTOR_PARTNER_SOUL", raising=False)
    monkeypatch.setenv("CONDUCTOR_SOUL_MODE", "resonate")
    result = resonate(search_host=True, skills_block="", research_block="")
    assert result.resonant
    assert result.conductor_path is not None
    assert result.conductor_path.resolve() == partner.resolve()
    assert result.host is not None
    assert result.host.path is not None
    assert result.host.path.resolve() == meister.resolve()
    assert result.prompt.count("ZYX-NOVA") == 1
    assert "UNIQUE_PARTNER_MARKER_QRS" in result.prompt
    assert not any(n.startswith("thrash:") for n in result.notes)


def test_host_shaped_home_soul_falls_to_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Meister-only SOUL.md without partner file → package partner, not double-host."""
    home = tmp_path / "lonely"
    home.mkdir()
    (home / "SOUL.md").write_text(
        "You are Local Host Only.\nNo conductor partner markers here.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONDUCTOR_HOME", str(home))
    monkeypatch.delenv("CONDUCTOR_PARTNER_SOUL", raising=False)
    monkeypatch.delenv("CONDUCTOR_HOST_SOUL", raising=False)
    p = soul_path()
    body = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    assert "Local Host Only" not in body
