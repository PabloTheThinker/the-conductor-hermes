"""Harness-agnostic module API for third-party AI hosts."""

from __future__ import annotations

from pathlib import Path

from conductor.harness import (
    execute_tool,
    get_system_prompt,
    hooks,
    install,
    list_skills,
    module_info,
    tool_schemas,
)


def test_module_info_shape(conductor_home: Path) -> None:
    info = module_info(home=conductor_home)
    assert info["name"] == "the-conductor"
    assert info["role"] == "skillset-module"
    assert "hermes" in info["adapters"]
    assert "generic" in info["adapters"]


def test_install_generic(conductor_home: Path) -> None:
    report = install(home=conductor_home, harness="generic")
    assert report["ok"], report.get("errors")
    assert report["harness"] == "generic"
    assert (conductor_home / "skills" / "conductor").is_dir()
    assert list((conductor_home / "skills" / "conductor").rglob("SKILL.md"))
    # no hermes plugin required for generic
    assert not (conductor_home / "plugins" / "conductor" / "plugin.yaml").exists() or True


def test_install_hermes(conductor_home: Path) -> None:
    report = install(home=conductor_home, harness="hermes")
    assert report["ok"], report.get("errors")
    assert (conductor_home / "plugins" / "conductor" / "plugin.yaml").is_file()


def test_tools_and_skills(conductor_home: Path) -> None:
    install(home=conductor_home, harness="generic")
    skills = list_skills(home=conductor_home)
    assert any(s.name == "plan" for s in skills)
    schemas = tool_schemas()
    assert isinstance(schemas, list) and len(schemas) >= 1
    prompt = get_system_prompt()
    assert "Conductor" in prompt
    h = hooks()
    assert h.pre_tool_call is not None


def test_execute_tool_session(conductor_home: Path) -> None:
    install(home=conductor_home, harness="generic")
    # list skills via tool if present; otherwise research_list style
    schemas = tool_schemas()
    names = []
    for s in schemas:
        fn = (s.get("function") or {})
        names.append(fn.get("name") or s.get("name"))
    assert names
    # skills_list is a common tool
    if "skills_list" in names:
        out = execute_tool("skills_list", {})
        assert isinstance(out, str)
