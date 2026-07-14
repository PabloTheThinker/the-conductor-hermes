"""Shipped conductor plugin registration + conductor skill seed (no fable)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from conductor.setup_ext import plugin_source, setup_extension, skills_source


class _FakeCtx:
    def __init__(self) -> None:
        self.tools: list[str] = []
        self.hooks: list[str] = []
        self.slash: list[str] = []

    def register_tool(self, name: str, **kwargs: Any) -> None:
        self.tools.append(name)

    def register_hook(self, name: str, cb: Any = None, **kwargs: Any) -> None:
        self.hooks.append(name)

    def register_slash(self, name: str, **kwargs: Any) -> None:
        self.slash.append(name)

    def register_command(self, name: str, **kwargs: Any) -> None:
        self.slash.append(name)


def test_plugin_source_is_conductor() -> None:
    src = plugin_source()
    assert src is not None
    assert src.name == "conductor"
    manifest = yaml.safe_load((src / "plugin.yaml").read_text(encoding="utf-8"))
    assert manifest["name"] == "conductor"
    assert "pre_tool_call" in manifest.get("hooks", [])
    assert (src / "__init__.py").is_file()


def test_skills_source_conductor_only_no_fable() -> None:
    src = skills_source()
    assert src is not None
    assert (src / "conductor").is_dir()
    assert not (src / "fable").exists()
    names = {p.parent.name for p in (src / "conductor").rglob("SKILL.md")}
    assert names, "no conductor SKILL.md found"
    # no fable trees in whole skills root
    assert not any("fable" in str(p) for p in src.rglob("SKILL.md"))


def test_plugin_register_callable(conductor_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = setup_extension(home=conductor_home)
    assert report.ok
    plugin_init = conductor_home / "plugins" / "conductor" / "__init__.py"
    assert plugin_init.is_file()

    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_PROVIDER", "test")
    monkeypatch.delenv("HERMES_AGENT_ROOT", raising=False)

    spec = importlib.util.spec_from_file_location("hermes_plugin_conductor_under_test", plugin_init)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hermes_plugin_conductor_under_test"] = mod
    spec.loader.exec_module(mod)
    assert hasattr(mod, "register")

    ctx = _FakeCtx()
    mod.register(ctx)
    assert "pre_tool_call" in ctx.hooks
    assert os.environ.get("CONDUCTOR_SPINE_ON_HERMES") == "1"
