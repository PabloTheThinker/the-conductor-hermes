"""Setup places conductor plugin + conductor skills; no fable; no HERMES_AGENT_ROOT."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conductor.cli.main import main
from conductor.hermes_host import hermes_host_status
from conductor.setup_ext import assert_setup_layout, setup_extension


def test_setup_extension_installs_conductor_not_ilo(conductor_home: Path) -> None:
    report = setup_extension(home=conductor_home, install_pip=False)
    assert report.ok, report.errors
    assert report.plugin_dest == conductor_home / "plugins" / "conductor"
    assert (report.plugin_dest / "plugin.yaml").is_file()
    man = yaml.safe_load((report.plugin_dest / "plugin.yaml").read_text(encoding="utf-8"))
    assert man["name"] == "conductor"
    assert str(man.get("version", "")).startswith("1.")
    assert report.skills_seeded, "expected conductor skill trees"
    assert all("fable" not in s for s in report.skills_seeded)
    assert not (conductor_home / "skills" / "fable").exists()
    assert not (conductor_home / "plugins" / "ilo").exists()
    # Partner SOUL for Conductor; do not force Conductor SOUL as Hermes meister
    assert (conductor_home / "CONDUCTOR_PARTNER_SOUL.md").is_file()
    assert (conductor_home / "conductor.env").is_file()
    env_text = (conductor_home / "conductor.env").read_text(encoding="utf-8")
    assert "HERMES_HOME" in env_text
    assert "CONDUCTOR_HOST" in env_text
    missing = assert_setup_layout(conductor_home)
    assert missing == [], missing
    raw = yaml.safe_load((conductor_home / "config.yaml").read_text(encoding="utf-8"))
    enabled = raw["plugins"]["enabled"]
    assert "conductor" in enabled
    assert "ilo" not in enabled
    assert report.to_dict()["requires_fork"] is False
    assert report.to_dict()["fable_seeded"] is False
    assert report.to_dict()["product"] == "The Conductor"


def test_hermes_setup_does_not_overwrite_meister_soul(conductor_home: Path) -> None:
    meister = conductor_home / "SOUL.md"
    meister.write_text("# I am Hermes meister\n", encoding="utf-8")
    report = setup_extension(home=conductor_home, harness="hermes", install_pip=False)
    assert report.ok, report.errors
    assert meister.read_text(encoding="utf-8") == "# I am Hermes meister\n"
    partner = (conductor_home / "CONDUCTOR_PARTNER_SOUL.md").read_text(encoding="utf-8")
    assert "Conductor" in partner or "enhance" in partner.lower()


def test_setup_cleans_legacy_ilo_and_fable(conductor_home: Path) -> None:
    # plant legacy product artifacts
    (conductor_home / "plugins" / "ilo").mkdir(parents=True)
    (conductor_home / "plugins" / "ilo" / "plugin.yaml").write_text("name: ilo\n", encoding="utf-8")
    (conductor_home / "skills" / "fable" / "effort").mkdir(parents=True)
    (conductor_home / "skills" / "fable" / "effort" / "SKILL.md").write_text(
        "---\nname: fable-effort\n---\n# nested pack\n",
        encoding="utf-8",
    )
    (conductor_home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - ilo\n",
        encoding="utf-8",
    )
    report = setup_extension(home=conductor_home)
    assert report.ok, report.errors
    assert not (conductor_home / "plugins" / "ilo").exists()
    assert not (conductor_home / "skills" / "fable").exists()
    assert (conductor_home / "plugins" / "conductor" / "plugin.yaml").is_file()
    raw = yaml.safe_load((conductor_home / "config.yaml").read_text(encoding="utf-8"))
    assert "conductor" in raw["plugins"]["enabled"]
    assert "ilo" not in raw["plugins"]["enabled"]


def test_setup_cleans_flattened_fable_skill_dirs(conductor_home: Path) -> None:
    """Prior seed flattened skills/fable/<x> into skills/<x> with name: fable-*.

    This is the real operator-home layout the migration must remove.
    """
    from conductor.setup_ext import FABLE_FLAT_DIR_NAMES, find_fable_skill_dirs

    # plant flattened fable skills (real prior layout)
    for name in sorted(FABLE_FLAT_DIR_NAMES):
        d = conductor_home / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: fable-{name}\ndescription: Fable {name} workflow /fable-{name}\n---\n"
            f"# Fable {name}\n\nLoad governance/FABLE_FRAMEWORK.md\n",
            encoding="utf-8",
        )
    # also plant nested pack form
    nested = conductor_home / "skills" / "fable" / "effort"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        "---\nname: fable-effort\n---\n# pack form\n",
        encoding="utf-8",
    )
    # plant a non-fable skill that must survive (Hermes third-party)
    keep = conductor_home / "skills" / "weather"
    keep.mkdir(parents=True)
    (keep / "SKILL.md").write_text(
        "---\nname: weather\ndescription: weather\n---\n# Weather\n",
        encoding="utf-8",
    )

    planted = find_fable_skill_dirs(conductor_home / "skills")
    assert len(planted) >= 7, planted

    report = setup_extension(home=conductor_home)
    assert report.ok, report.errors
    leftover = find_fable_skill_dirs(conductor_home / "skills")
    assert leftover == [], leftover
    for name in FABLE_FLAT_DIR_NAMES:
        assert not (conductor_home / "skills" / name).exists(), name
    assert not (conductor_home / "skills" / "fable").exists()
    # third-party skill preserved
    assert (keep / "SKILL.md").is_file()
    assert assert_setup_layout(conductor_home) == []
    cleaned_names = " ".join(report.cleaned)
    assert "fable" in cleaned_names or "effort" in cleaned_names

def test_setup_cli(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("HERMES_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    assert main(["setup", "--json"]) == 0
    assert (conductor_home / "plugins" / "conductor" / "plugin.yaml").is_file()


def test_hermes_host_does_not_require_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERMES_AGENT_ROOT", raising=False)
    st = hermes_host_status()
    assert st.get("requires_fork") is False


def test_default_install_path_ignores_relay_env(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/nonexistent/private-hermes-fork")
    report = setup_extension(home=conductor_home)
    assert report.ok
    assert assert_setup_layout(conductor_home) == []
