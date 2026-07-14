"""CLI for The Conductor pack — setup/doctor/offline brain; daily TUI is stock hermes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CONDUCTOR_PACKAGE_LAYOUT", "native")

from conductor import __version__
from conductor.cli.chat import run_chat
from conductor.config import doctor_issues, load_config
from conductor.paths import conductor_home


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"the-conductor {__version__}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    home = conductor_home()
    print()
    print("┌─────────────────────────────────────────────────────────┐")
    print("│            ◆ The Conductor — status                     │")
    print("└─────────────────────────────────────────────────────────┘")
    print()
    print(f"  Version:     {__version__}")
    print("  Product:     enhances the agent that uses it (Soul Resonance module)")
    print("  Hosts:       hermes adapter · generic module API")
    print(f"  Home:        {home}")
    print(f"  HERMES_HOME: {os.environ.get('HERMES_HOME') or home}")
    print(f"  Config:      {'✓' if (home / 'config.yaml').exists() else '○'}")
    print(f"  SOUL:        {'✓' if (home / 'SOUL.md').exists() else '○'}")
    try:
        from conductor.pillars import foundation_report

        fr = foundation_report()
        mark = "✓" if fr.get("ok") else "○"
        print(f"  Pillars:     {mark} {fr.get('passed')}/{fr.get('total')} foundation ok")
    except Exception:  # noqa: BLE001
        print("  Pillars:     ○ (probe unavailable)")
    print()
    print("  Surface:     Hermes plugin + skills (no fork)")
    try:
        from conductor.hermes_host import hermes_host_status

        hs = hermes_host_status()
        mark = "✓" if hs.get("available") else "○"
        print(f"  Hermes CLI:  {mark} {hs.get('hermes_bin') or 'not found'}")
        print(f"               path={hs.get('hermes_bin') or '—'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  Hermes CLI:  ○ ({exc})")
    plugin = home / "plugins" / "conductor" / "plugin.yaml"
    skills = home / "skills" / "conductor"
    skill_n = len(list(skills.rglob("SKILL.md"))) if skills.is_dir() else 0
    fable = home / "skills" / "fable"
    print(f"  Plugin:      {'✓' if plugin.is_file() else '○ run: conductor setup'} {plugin.parent}")
    print(f"  Skills:      {skill_n} under {skills}")
    if fable.is_dir():
        print("  Legacy:      fable skills still present — re-run conductor setup")
    try:
        from conductor.agent.hermes_auth import hermes_auth_status
        from conductor.bootstrap import ensure_conductor_importable

        print(
            f"  Package:     {'✓ importable' if ensure_conductor_importable() else '○ pip install -e . (into Hermes venv too)'}"
        )
        ha = hermes_auth_status()
        rt = ha.get("runtime") or {}
        print(
            f"  Provider:    {rt.get('provider') or '—'} via {rt.get('source') or '—'} "
            f"({'ok' if rt.get('ok') else 'need: hermes model'})"
        )
    except Exception:  # noqa: BLE001
        pass
    print()
    print("  Docs:        docs/PILLARS.md · docs/SOUL_RESONANCE.md · docs/MODULE_FOR_AGENTS.md")
    print("  Launch:      conductor hermes   # or: source $HOME/.hermes/conductor.env && hermes")
    print("  Setup:       conductor setup")
    print("  Offline:     conductor chat / conductor doctor")
    print("  Pillars:     conductor chat → /pillars status")
    print()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    home = conductor_home()
    # Full Hermes readiness when --hermes or Hermes home layout present
    use_ready = bool(getattr(args, "hermes", False)) or (
        (home / "plugins" / "conductor").is_dir()
        or os.environ.get("HERMES_HOME", "").strip()
    )
    if use_ready and not getattr(args, "legacy", False):
        from conductor.adapters.hermes.ready import format_ready_report, hermes_ready_report

        if getattr(args, "json", False):
            print(json.dumps(hermes_ready_report(home=home).to_dict(), indent=2))
            return 0 if hermes_ready_report(home=home).ok else 1
        print()
        print(format_ready_report(verbose=bool(getattr(args, "verbose", False)), home=home))
        print()
        # Also surface provider/config soft issues
        cfg = load_config()
        soft = doctor_issues(cfg)
        if soft:
            print("  Config notes:")
            for item in soft:
                print(f"    · {item}")
            print()
        return 0 if hermes_ready_report(home=home).ok else 1

    issues: list[str] = []
    if sys.version_info < (3, 11):
        issues.append(f"Python {sys.version_info.major}.{sys.version_info.minor} — require >= 3.11")
    if not home.exists():
        issues.append(f"shared home missing — run: conductor setup  ({home})")
    cfg = load_config()
    issues.extend(doctor_issues(cfg))
    from conductor.bootstrap import ensure_conductor_importable
    from conductor.setup_ext import assert_setup_layout

    if (home / "config.yaml").exists() or (home / "plugins").exists():
        for m in assert_setup_layout(home):
            issues.append(f"setup incomplete: {m}")
    if not ensure_conductor_importable():
        issues.append(
            "Python package 'conductor' not importable — pip install -e . "
            "(also into the venv that runs `hermes`)"
        )
    if not (home / "plugins" / "conductor" / "plugin.yaml").is_file():
        issues.append("plugin not installed — run: conductor setup")
    from conductor.hermes_host import hermes_available

    if not hermes_available():
        issues.append(
            "stock hermes CLI not on PATH — install hermes-agent and put `hermes` on PATH "
            "(or set HERMES_BIN). Daily TUI will not work until then."
        )

    print()
    print("◆ The Conductor — doctor")
    print()
    if issues:
        for item in issues:
            print(f"  ✗ {item}")
        print()
        print("  Guide: docs/HERMES.md · docs/OPERATORS.md")
        print("  Full checklist: conductor doctor --hermes")
    else:
        print("  ✓ Core OK")
        print(f"  ✓ Home {home}")
        print(f"  ✓ Provider {cfg.provider}")
    from conductor.hermes_host import hermes_host_status

    hs = hermes_host_status()
    print(f"  {'✓' if hs['available'] else '○'} Stock hermes: {hs.get('hermes_bin') or 'missing'}")
    print(f"  {'✓' if hs.get('conductor_importable') else '○'} Package importable")
    print("  ✓ Product plugin name: conductor")
    print()
    return 1 if issues else 0


def cmd_hermes_ready(args: argparse.Namespace) -> int:
    """Third-party Hermes readiness + optional pip / auto-repair."""
    from conductor.adapters.hermes.ready import (
        format_ready_report,
        hermes_ready_report,
        install_into_hermes_venv,
        repair_hermes_install,
    )

    home = conductor_home()
    if getattr(args, "repair", False):
        result = repair_hermes_install(
            home=home,
            install_pip=bool(getattr(args, "install_pip", False)),
        )
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2, default=str))
        else:
            print()
            print("◆ hermes-ready --repair")
            for s in result.get("setup_steps") or []:
                print(f"  ✓ {s}" if not str(s).startswith("○") else f"  {s}")
            for e in result.get("setup_errors") or []:
                print(f"  ✗ {e}")
            print()
            print(format_ready_report(verbose=True, home=home))
            print()
        ready = hermes_ready_report(home=home)
        return 0 if result.get("setup_ok") and ready.ok else 1
    if getattr(args, "install_pip", False):
        ok, detail = install_into_hermes_venv()
        print(f"{'✓' if ok else '✗'} hermes venv: {detail}")
        if not ok and not getattr(args, "json", False):
            return 1
    if getattr(args, "json", False):
        print(json.dumps(hermes_ready_report(home=home).to_dict(), indent=2))
        return 0 if hermes_ready_report(home=home).ok else 1
    print()
    print(format_ready_report(verbose=True, home=home))
    print()
    return 0 if hermes_ready_report(home=home).ok else 1



def cmd_module(args: argparse.Namespace) -> int:
    """Expose Conductor as a harness-agnostic skillset module."""
    import json

    from conductor.harness import (
        install,
        list_skills,
        module_info,
        tool_schemas,
    )

    if getattr(args, "home", None):
        os.environ["CONDUCTOR_HOME"] = str(Path(args.home).expanduser())
    action = getattr(args, "action", "info") or "info"
    if action == "info":
        data = module_info()
        if getattr(args, "json", False):
            print(json.dumps(data, indent=2))
        else:
            print("◆ The Conductor — module")
            for k, v in data.items():
                print(f"  {k}: {v}")
        return 0
    if action == "install":
        report = install(harness=getattr(args, "harness", "generic") or "generic")
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            print("◆ install", report.get("harness"), "→", report.get("home"))
            for s in report.get("steps") or []:
                print("  ✓", s)
            for e in report.get("errors") or []:
                print("  ✗", e)
        return 0 if report.get("ok") else 1
    if action == "skills":
        rows = [{"name": s.name, "description": s.description, "path": s.path} for s in list_skills()]
        print(json.dumps(rows, indent=2))
        return 0
    if action == "tools":
        print(json.dumps(tool_schemas(), indent=2))
        return 0
    return 1


def cmd_setup(args: argparse.Namespace) -> int:
    from conductor.setup_ext import assert_setup_layout, setup_extension

    if getattr(args, "home", None):
        h = str(Path(args.home).expanduser())
        os.environ["CONDUCTOR_HOME"] = h
        os.environ["HERMES_HOME"] = h
    home = conductor_home()

    install_pip = None
    if getattr(args, "install_pip", False):
        install_pip = True
    if getattr(args, "no_pip", False):
        install_pip = False

    report = setup_extension(
        home=home,
        force=True,
        harness=getattr(args, "harness", "hermes") or "hermes",
        install_pip=install_pip,
    )
    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print()
        print("◆ The Conductor — setup (plugin + skills → shared home)")
        print(f"  HERMES_HOME / CONDUCTOR_HOME = {report.home}")
        for step in report.steps:
            mark = "○" if step.startswith("○") else "✓"
            text = step[1:].lstrip() if step.startswith("○") else step
            print(f"  {mark} {text}")
        for err in report.errors:
            print(f"  ✗ {err}")
        print()
        if report.ok:
            print("  Ready check:  conductor hermes-ready")
            print("  Daily:        source $HERMES_HOME/conductor.env && hermes")
            print("  Auth:         hermes model")
            print("  Offline:      CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'")
            print("  Docs:         docs/HERMES.md")
        print()
    hname = getattr(args, "harness", "hermes") or "hermes"
    missing = assert_setup_layout(report.home, harness=hname) if report.ok else report.errors
    return 0 if report.ok and not missing else 1


def cmd_auth(args: argparse.Namespace) -> int:
    from conductor.agent.hermes_auth import ensure_hermes_home, hermes_auth_status
    from conductor.hermes_host import hermes_bin, launch_hermes

    ensure_hermes_home()
    extra = list(getattr(args, "auth_args", None) or [])
    if getattr(args, "status", False) or not extra or extra == ["status"] or extra[0] == "status":
        st = hermes_auth_status()
        if getattr(args, "json", False):
            print(json.dumps(st, indent=2))
        else:
            rt = st.get("runtime") or {}
            print()
            print("◆ Auth (shared HERMES_HOME — stock Hermes owns login)")
            print(f"  HERMES_HOME: {st.get('hermes_home')}")
            print(f"  Provider:    {rt.get('provider')} via {rt.get('source')}")
            print(f"  Ready:       {'yes' if rt.get('ok') else 'no — run: hermes model'}")
            print()
            print("  hermes model")
            print("  hermes auth add xai-oauth --type oauth")
            print()
        return 0 if (st.get("runtime") or {}).get("ok") else 1

    if hermes_bin() is None:
        print("Stock hermes not found — install Hermes and put `hermes` on PATH.", file=sys.stderr)
        return 1
    head = extra[0]
    if head == "model":
        return launch_hermes(["model", *extra[1:]])
    if head in {"login", "add"}:
        rest = extra[1:]
        if head == "login" and rest and "--type" not in rest:
            return launch_hermes(["auth", "add", rest[0], "--type", "oauth", *rest[1:]])
        return launch_hermes(["auth", "add", *rest])
    return launch_hermes(["auth", *extra])


def cmd_mcp(args: argparse.Namespace) -> int:
    """MCP server / catalog for AI model hosts (Claude, Codex, Cursor, Grok)."""
    action = getattr(args, "mcp_action", "serve") or "serve"
    if action in {"catalog", "tools"}:
        from conductor.mcp.catalog import build_mcp_catalog, tool_definitions

        if action == "tools":
            rows = [
                {"name": t.name, "description": t.description, "source": t.source}
                for t in tool_definitions()
            ]
            if getattr(args, "json", False):
                print(json.dumps(rows, indent=2))
            else:
                print(f"◆ Conductor MCP tools ({len(rows)})")
                for r in rows:
                    print(f"  {r['name']:<28} [{r['source']}] {r['description'][:70]}")
            return 0
        cat = build_mcp_catalog()
        if getattr(args, "json", False):
            print(json.dumps(cat, indent=2, default=str))
        else:
            print("◆ Conductor MCP catalog")
            print(f"  name:    {cat['name']}")
            print(f"  version: {cat['version']}")
            print(f"  tools:   {cat['tool_count']}")
            print(f"  product: {cat['product_line']}")
            print("  run:     conductor mcp")
            print("  docs:    docs/MCP.md")
        return 0
    # serve — stdio (blocks)
    from conductor.mcp.server import run_stdio

    return run_stdio()


def cmd_hermes(args: argparse.Namespace) -> int:
    from conductor.hermes_host import launch_hermes
    from conductor.setup_ext import assert_setup_layout, setup_extension

    home = conductor_home()
    os.environ.setdefault("HERMES_HOME", str(home))
    if assert_setup_layout(home) and not getattr(args, "no_setup", False):
        print("◆ Conductor not fully installed — running setup…")
        setup_extension(home=home)
    try:
        return launch_hermes(list(getattr(args, "hermes_args", None) or []))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _add_chat_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-q", "--query", help="Single-turn query (non-interactive)")
    parser.add_argument("--continue", dest="continue_last", action="store_true")
    parser.add_argument("--resume", metavar="ID")
    parser.add_argument("--tui", action="store_true", help="Alias: launch stock hermes")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conductor",
        description=(
            "The Conductor — skillset module helpers (setup/doctor/offline brain). "
            "Daily driver is stock `hermes` with plugin `conductor`."
        ),
    )
    parser.add_argument("--version", "-V", action="store_true")
    _add_chat_flags(parser)
    sub = parser.add_subparsers(dest="command")

    chat = sub.add_parser("chat", help="Native brain REPL / one-shot (-q)")
    _add_chat_flags(chat)
    chat.set_defaults(func=run_chat)

    sub.add_parser("status", help="Conductor + Hermes host status").set_defaults(func=cmd_status)
    doc = sub.add_parser("doctor", help="Environment checks (Hermes readiness by default)")
    doc.add_argument("--hermes", action="store_true", help="Full Hermes readiness checklist")
    doc.add_argument("--legacy", action="store_true", help="Simple issue list only")
    doc.add_argument("--verbose", "-v", action="store_true")
    doc.add_argument("--json", action="store_true")
    doc.set_defaults(func=cmd_doctor)
    sub.add_parser("version", help="Show version").set_defaults(func=cmd_version)

    ready = sub.add_parser(
        "hermes-ready",
        help="Hermes readiness for any stock Hermes agent (+ optional pip into Hermes venv)",
    )
    ready.add_argument("--install-pip", action="store_true", help="pip install -e into Hermes python")
    ready.add_argument(
        "--repair",
        action="store_true",
        help="Run conductor setup into HERMES_HOME/CONDUCTOR_HOME then re-check",
    )
    ready.add_argument("--json", action="store_true")
    ready.set_defaults(func=cmd_hermes_ready)

    setup = sub.add_parser("setup", help="Install conductor plugin + skills into HERMES_HOME")
    setup.add_argument("--home", help="Override CONDUCTOR_HOME for this run")
    setup.add_argument("--json", action="store_true")
    setup.add_argument(
        "--harness",
        choices=["hermes", "generic"],
        default="hermes",
        help="Host harness: hermes installs plugin; generic is skills-only module",
    )
    setup.add_argument(
        "--install-pip",
        action="store_true",
        help="Force pip install -e into Hermes venv",
    )
    setup.add_argument(
        "--no-pip",
        action="store_true",
        help="Skip pip into Hermes venv (file plugin + PYTHONPATH only)",
    )
    setup.set_defaults(func=cmd_setup)

    auth = sub.add_parser("auth", help="Auth status / delegate to stock hermes")
    auth.add_argument("auth_args", nargs="*")
    auth.add_argument("--status", action="store_true")
    auth.add_argument("--json", action="store_true")
    auth.set_defaults(func=cmd_auth)

    mod = sub.add_parser("module", help="Harness-agnostic module info / install API")
    mod.add_argument("action", nargs="?", default="info", choices=["info", "install", "skills", "tools"])
    mod.add_argument("--harness", default="generic", choices=["generic", "hermes"])
    mod.add_argument("--home", help="Override CONDUCTOR_HOME")
    mod.add_argument("--json", action="store_true")
    mod.set_defaults(func=cmd_module)

    hermes_p = sub.add_parser("hermes", help="Launch stock Hermes (optional host)")
    hermes_p.add_argument("hermes_args", nargs="*")
    hermes_p.add_argument("--no-setup", action="store_true")
    hermes_p.set_defaults(func=cmd_hermes)

    mcp_p = sub.add_parser(
        "mcp",
        help="MCP server for Claude / Codex / Cursor / Grok (stdio tools+resources)",
    )
    mcp_p.add_argument(
        "mcp_action",
        nargs="?",
        default="serve",
        choices=["serve", "catalog", "tools"],
        help="serve (default stdio) | catalog | tools",
    )
    mcp_p.add_argument("--json", action="store_true")
    mcp_p.set_defaults(func=cmd_mcp)
    return parser


def _default_entry(args: argparse.Namespace) -> int:
    if getattr(args, "query", None) or getattr(args, "gateway", False) or getattr(args, "dev", False):
        return run_chat(args)
    if getattr(args, "tui", False):
        args.hermes_args = []
        args.no_setup = False
        return cmd_hermes(args)

    from conductor.hermes_host import hermes_available

    if hermes_available() and sys.stdin.isatty() and sys.stdout.isatty():
        args.hermes_args = []
        args.no_setup = False
        return cmd_hermes(args)

    print("◆ The Conductor — no stock Hermes on PATH (brain helpers only).")
    print("  Daily path: install Hermes, then: hermes")
    print("  Setup:      conductor setup")
    print()
    return cmd_status(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        return cmd_version(args)
    home = str(conductor_home())
    os.environ.setdefault("CONDUCTOR_HOME", home)
    os.environ.setdefault("HERMES_HOME", home)
    if args.command is None:
        return _default_entry(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
