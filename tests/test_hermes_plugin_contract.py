"""Hermes plugin contract — no core tool clashes; register surface exists."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "hermes_plugin" / "conductor" / "__init__.py"


def _load_file_plugin():
    spec = importlib.util.spec_from_file_location("hermes_plugin_conductor_contract", PLUGIN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeCtx:
    def __init__(self) -> None:
        self.tools: list[str] = []
        self.hooks: list[str] = []
        self.commands: list[str] = []
        self.skills: list[str] = []

    def register_tool(self, name: str, **kwargs) -> None:
        self.tools.append(name)

    def register_hook(self, name: str, cb) -> None:
        self.hooks.append(name)

    def register_command(self, name: str, **kwargs) -> None:
        self.commands.append(name)

    def register_skill(self, name: str, path, description: str = "") -> None:
        self.skills.append(name)


def test_plugin_yaml_exists() -> None:
    yml = ROOT / "hermes_plugin" / "conductor" / "plugin.yaml"
    assert yml.is_file()
    text = yml.read_text(encoding="utf-8")
    assert "name: conductor" in text
    assert "pre_tool_call" in text
    assert "transform_tool_result" in text
    assert "api_request_error" in text
    assert "version:" in text
    assert "1.18.12" in text


def test_register_skips_hermes_core_names(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("HERMES_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_HOST", "hermes")
    from conductor.adapters.hermes.plugin import register

    ctx = _FakeCtx()
    register(ctx)
    for banned in (
        "read_file",
        "write_file",
        "run_shell",
        "terminal",
        "delegate_task",
        "skill_manage",
        "web_search",
    ):
        assert banned not in ctx.tools
    assert any(
        t in ctx.tools
        for t in (
            "pillar_status",
            "combo_route",
            "track_orchestrate",
            "crucible_workspace",
        )
    )
    assert "conductor_worker" in ctx.tools
    assert "pre_tool_call" in ctx.hooks
    assert "pre_llm_call" in ctx.hooks
    assert "on_session_start" in ctx.hooks
    assert "transform_tool_result" in ctx.hooks
    assert "api_request_error" in ctx.hooks
    for cmd in ("crucible", "pillars", "combo", "remnant", "track", "conductor-status"):
        assert cmd in ctx.commands
    assert os.environ.get("CONDUCTOR_HOST") == "hermes"


def test_file_plugin_bootstrap_register(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("HERMES_HOME", str(conductor_home))
    monkeypatch.setenv("CONDUCTOR_HOST", "hermes")
    mod = _load_file_plugin()
    ctx = _FakeCtx()
    mod.register(ctx)
    assert "pillar_status" in ctx.tools or "combo_route" in ctx.tools
    assert "pre_tool_call" in ctx.hooks


def test_hermes_ready_report_structure(
    conductor_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conductor.adapters.hermes.ready import hermes_ready_report
    from conductor.setup_ext import setup_extension

    monkeypatch.setenv("CONDUCTOR_HOME", str(conductor_home))
    monkeypatch.setenv("HERMES_HOME", str(conductor_home))
    setup_extension(home=conductor_home, harness="hermes", install_pip=False)
    rep = hermes_ready_report(home=conductor_home)
    assert rep.version
    assert rep.home == str(conductor_home.resolve())
    ids = {c.id for c in rep.checks}
    assert "setup_layout" in ids
    assert "plugin_enabled" in ids
    assert "skills" in ids
    assert all(c.ok for c in rep.checks if c.id == "setup_layout")
    assert not any(c.id.startswith("layout:") for c in rep.checks)
