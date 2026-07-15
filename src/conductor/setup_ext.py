"""Install The Conductor plugin + skill pack into shared HERMES_HOME / CONDUCTOR_HOME.

Default path never requires a Hermes fork checkout.
Product plugin id: **conductor**. Fable skill pack is not seeded.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PRODUCT_PLUGIN = "conductor"
LEGACY_PLUGIN = "ilo"


@dataclass
class SetupReport:
    home: Path
    plugin_dest: Path | None = None
    skills_seeded: list[str] = field(default_factory=list)
    config_path: Path | None = None
    plugin_enabled: bool = False
    cleaned: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    hermes_pip: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "home": str(self.home),
            "product": "The Conductor",
            "plugin_name": PRODUCT_PLUGIN,
            "plugin_dest": str(self.plugin_dest) if self.plugin_dest else None,
            "skills_seeded": list(self.skills_seeded),
            "config_path": str(self.config_path) if self.config_path else None,
            "plugin_enabled": self.plugin_enabled,
            "cleaned": list(self.cleaned),
            "steps": list(self.steps),
            "ok": self.ok,
            "errors": list(self.errors),
            "hermes_pip": self.hermes_pip,
            "requires_fork": False,
            "fable_seeded": False,
        }


def repo_root() -> Path:
    """Repo root when running from a checkout; else package parent heuristics."""
    here = Path(__file__).resolve()
    cand = here.parents[2]
    if (cand / "hermes_plugin" / PRODUCT_PLUGIN).is_dir() and (cand / "skills").is_dir():
        return cand
    bundle = here.parent / "_bundle"
    if (bundle / "hermes_plugin" / PRODUCT_PLUGIN).is_dir():
        return bundle
    return cand


def plugin_source() -> Path | None:
    root = repo_root()
    for p in (
        root / "hermes_plugin" / PRODUCT_PLUGIN,
        Path(__file__).resolve().parent / "_bundle" / "hermes_plugin" / PRODUCT_PLUGIN,
    ):
        if (p / "plugin.yaml").is_file() and (p / "__init__.py").is_file():
            return p
    return None


def skills_source() -> Path | None:
    """Return skills root that contains conductor trees (never require fable)."""
    root = repo_root()
    for p in (
        root / "skills",
        Path(__file__).resolve().parent / "_bundle" / "skills",
    ):
        if not p.is_dir():
            continue
        conductor = p / "conductor"
        if conductor.is_dir() and any(conductor.rglob("SKILL.md")):
            return p
        if any(p.rglob("SKILL.md")):
            return p
    return None


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def _ensure_plugin_enabled(config_path: Path) -> bool:
    """Ensure plugins.enabled includes conductor and drops legacy product plugin ilo."""
    try:
        import yaml
    except ImportError:
        return False

    raw: dict[str, Any] = {}
    if config_path.is_file():
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                raw = loaded
        except Exception:  # noqa: BLE001
            raw = {}

    plugins = raw.get("plugins") if isinstance(raw.get("plugins"), dict) else {}
    if not isinstance(plugins, dict):
        plugins = {}
    enabled = plugins.get("enabled")
    if not isinstance(enabled, list):
        enabled = []
    names = [str(x).strip() for x in enabled if str(x).strip()]
    # drop legacy product plugin name
    names = [n for n in names if n != LEGACY_PLUGIN]
    if PRODUCT_PLUGIN not in names:
        names.append(PRODUCT_PLUGIN)
    plugins["enabled"] = names
    raw["plugins"] = plugins

    surface = raw.get("surface") if isinstance(raw.get("surface"), dict) else {}
    if not isinstance(surface, dict):
        surface = {}
    surface["default"] = "production"
    surface["product"] = "The Conductor"
    raw["surface"] = surface

    # Do not invent model.default — Hermes owns auth/model via `hermes model`.
    # Only preserve an existing model block if the operator already set one.
    if isinstance(raw.get("model"), dict) and raw["model"]:
        pass  # leave operator config untouched
    # else: omit model section (lesson: gpt-4o-mini defaults confused third parties)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(raw, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return PRODUCT_PLUGIN in names and LEGACY_PLUGIN not in names


def _seed_conductor_skills(src: Path, dest_skills: Path) -> list[str]:
    """Copy only conductor skill trees (skip fable and other packs)."""
    seeded: list[str] = []
    dest_skills.mkdir(parents=True, exist_ok=True)

    conductor_src = src / "conductor"
    if not conductor_src.is_dir():
        # flat skill.md under src?
        for skill_md in src.rglob("SKILL.md"):
            # skip any path containing fable
            if "fable" in skill_md.parts:
                continue
            rel = skill_md.parent.relative_to(src)
            target = dest_skills / rel
            target.mkdir(parents=True, exist_ok=True)
            for item in skill_md.parent.iterdir():
                if item.name == "__pycache__":
                    continue
                dest_item = target / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)
            seeded.append(str(rel).replace("\\", "/"))
        return sorted(set(seeded))

    # Seed skills/conductor/* only
    for skill_md in conductor_src.rglob("SKILL.md"):
        if "fable" in skill_md.parts:
            continue
        rel = skill_md.parent.relative_to(src)  # conductor/plan etc.
        target = dest_skills / rel
        target.mkdir(parents=True, exist_ok=True)
        for item in skill_md.parent.iterdir():
            if item.name == "__pycache__":
                continue
            dest_item = target / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(item, dest_item)
            else:
                shutil.copy2(item, dest_item)
        seeded.append(str(rel).replace("\\", "/"))
    return sorted(set(seeded))


# Prior seed sometimes flattened skills/fable/<name>/ into skills/<name>/
# with frontmatter name: fable-<name>. These must be removed on setup.
FABLE_FLAT_DIR_NAMES: frozenset[str] = frozenset(
    {"effort", "gate", "verify", "memory", "session", "audit", "debug"}
)


def _skill_frontmatter_name(skill_md: Path) -> str:
    """Return YAML frontmatter ``name`` from a SKILL.md, or empty string."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    for line in parts[1].splitlines():
        line = line.strip()
        if line.lower().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _is_fable_skill_dir(path: Path) -> bool:
    """True if this directory is a Fable product skill (pack tree or flattened)."""
    if not path.is_dir():
        return False
    if path.name == "fable" or "fable" in path.parts:
        # skills/fable or any nested path under fable/
        if path.name == "fable":
            return True
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        return False
    name = _skill_frontmatter_name(skill_md).lower()
    if name.startswith("fable-") or name == "fable":
        return True
    # Known flattened dir names only when frontmatter confirms Fable content
    if path.name in FABLE_FLAT_DIR_NAMES:
        try:
            body = skill_md.read_text(encoding="utf-8")[:800].lower()
        except OSError:
            body = ""
        if "fable" in body or name.startswith("fable"):
            return True
    return False


def find_fable_skill_dirs(skills_root: Path) -> list[Path]:
    """Locate Fable product skill directories under a skills home (for cleanup + tests)."""
    if not skills_root.is_dir():
        return []
    found: list[Path] = []
    # Nested pack
    pack = skills_root / "fable"
    if pack.is_dir():
        found.append(pack)
    # Flattened top-level dirs and any dir with fable-* frontmatter
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name == "fable":
            continue  # already added
        if _is_fable_skill_dir(child):
            found.append(child)
            continue
        # one level of nesting (e.g. rare layouts)
        for sub in child.iterdir() if child.is_dir() else []:
            if sub.is_dir() and _is_fable_skill_dir(sub):
                found.append(sub)
    # Dedup preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _clean_legacy(home: Path, report: SetupReport) -> None:
    """Remove product-legacy ilo plugin and all Fable product skills (pack + flattened)."""
    legacy_plugin = home / "plugins" / LEGACY_PLUGIN
    if legacy_plugin.exists():
        shutil.rmtree(legacy_plugin)
        report.cleaned.append(str(legacy_plugin))
        report.steps.append(f"removed legacy plugin {legacy_plugin}")

    skills_root = home / "skills"
    for fable_dir in find_fable_skill_dirs(skills_root):
        try:
            shutil.rmtree(fable_dir)
            report.cleaned.append(str(fable_dir))
            report.steps.append(f"removed fable skill {fable_dir}")
        except OSError as exc:
            report.errors.append(f"failed to remove {fable_dir}: {exc}")
            report.ok = False

    # old alias tree from previous setup
    alias = home / "skills" / "ilo-conductor"
    if alias.exists():
        shutil.rmtree(alias)
        report.cleaned.append(str(alias))
        report.steps.append(f"removed legacy alias {alias}")


def _sync_plugin_manifest(dest: Path) -> None:
    """Keep installed plugin.yaml name/version in sync with the package."""
    try:
        import yaml
        from conductor import __version__
    except Exception:  # noqa: BLE001
        return
    man_path = dest / "plugin.yaml"
    if not man_path.is_file():
        return
    try:
        man = yaml.safe_load(man_path.read_text(encoding="utf-8")) or {}
        if not isinstance(man, dict):
            man = {}
        man["name"] = PRODUCT_PLUGIN
        man["version"] = str(__version__)
        man.setdefault(
            "description",
            "The Conductor — enhances Hermes (Soul Resonance, pillars, Remnants, spine).",
        )
        man.setdefault("author", "The Conductor")
        man.setdefault("kind", "standalone")
        man.setdefault("homepage", "https://github.com/PabloTheThinker/the-conductor-hermes")
        man["hooks"] = [
            "pre_tool_call",
            "transform_tool_result",
            "on_session_start",
            "pre_llm_call",
        ]
        man_path.write_text(
            yaml.safe_dump(man, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


def _seed_partner_soul(home_path: Path, report: SetupReport) -> None:
    """Write Conductor partner SOUL — never overwrite Hermes meister SOUL.md."""
    partner = home_path / "CONDUCTOR_PARTNER_SOUL.md"
    for soul_src in (
        repo_root() / "SOUL.md",
        Path(__file__).resolve().parent / "_bundle" / "SOUL.md",
    ):
        if soul_src.is_file():
            try:
                shutil.copy2(soul_src, partner)
                report.steps.append(f"partner SOUL → {partner}")
            except OSError as exc:
                report.errors.append(f"partner SOUL: {exc}")
            break


def setup_extension(
    *,
    home: Path | None = None,
    force: bool = True,
    harness: str = "hermes",
    install_pip: bool | None = None,
) -> SetupReport:
    """Install Conductor skills (+ optional host plugin) into a durable home.

    harness:
      - ``generic`` — skills, partner SOUL, config, package marker (any AI harness)
      - ``hermes`` — also install Hermes plugins/conductor and enable it

    install_pip:
      - ``True`` — try ``pip install -e`` into Hermes venv
      - ``False`` — never
      - ``None`` — auto when hermes binary found
    """
    from conductor.paths import conductor_home

    harness = (harness or "hermes").strip().lower()
    home_path = Path(home) if home else conductor_home()
    home_path = home_path.expanduser().resolve()
    home_path.mkdir(parents=True, exist_ok=True)
    os.environ["CONDUCTOR_HOME"] = str(home_path)
    if harness == "hermes":
        os.environ["HERMES_HOME"] = str(home_path)

    report = SetupReport(home=home_path)
    report.steps.append(f"harness={harness}")

    _clean_legacy(home_path, report)

    # Host-specific plugin packaging (Hermes)
    if harness == "hermes":
        psrc = plugin_source()
        if psrc is None:
            report.ok = False
            report.errors.append("hermes_plugin/conductor not found in package/repo")
        else:
            dest = home_path / "plugins" / PRODUCT_PLUGIN
            try:
                _copy_tree(psrc, dest)
                _sync_plugin_manifest(dest)
                report.plugin_dest = dest
                report.steps.append(f"hermes plugin → {dest}")
            except OSError as exc:
                report.ok = False
                report.errors.append(f"plugin copy failed: {exc}")
    else:
        report.steps.append("generic harness — skills/SOUL only (no Hermes plugin tree)")

    # Skills — conductor only
    ssrc = skills_source()
    if ssrc is None:
        report.ok = False
        report.errors.append("skills/conductor pack not found in package/repo")
    else:
        try:
            report.skills_seeded = _seed_conductor_skills(ssrc, home_path / "skills")
            # refuse fable in seed list
            if any("fable" in s for s in report.skills_seeded):
                report.ok = False
                report.errors.append("fable appeared in seed list — must not ship")
            report.steps.append(
                f"skills → {home_path / 'skills'} "
                f"({len(report.skills_seeded)} conductor trees; fable not seeded)"
            )
        except OSError as exc:
            report.ok = False
            report.errors.append(f"skills seed failed: {exc}")

    # Config
    cfg = home_path / "config.yaml"
    try:
        if not cfg.is_file():
            example = repo_root() / "config.example.yaml"
            if example.is_file():
                shutil.copy2(example, cfg)
                report.steps.append(f"config from example → {cfg}")
        if harness == "hermes":
            report.plugin_enabled = _ensure_plugin_enabled(cfg)
            report.steps.append(
                f"plugins.enabled includes {PRODUCT_PLUGIN} → {report.plugin_enabled}"
            )
        else:
            report.plugin_enabled = False
            # still ensure config exists with product tag
            try:
                import yaml

                raw = {}
                if cfg.is_file():
                    raw = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
                if not isinstance(raw, dict):
                    raw = {}
                surface = raw.get("surface") if isinstance(raw.get("surface"), dict) else {}
                surface = dict(surface or {})
                surface["product"] = "The Conductor"
                surface["harness"] = harness
                raw["surface"] = surface
                cfg.write_text(
                    yaml.safe_dump(raw, default_flow_style=False, sort_keys=False),
                    encoding="utf-8",
                )
            except Exception:  # noqa: BLE001
                pass
        report.config_path = cfg
    except OSError as exc:
        report.ok = False
        report.errors.append(f"config update failed: {exc}")

    # Partner SOUL for Conductor (always). Hermes meister SOUL.md is Hermes-owned.
    _seed_partner_soul(home_path, report)
    if harness == "generic":
        # Generic hosts may use SOUL.md as the only identity file.
        soul_dest = home_path / "SOUL.md"
        if not soul_dest.is_file():
            partner = home_path / "CONDUCTOR_PARTNER_SOUL.md"
            if partner.is_file():
                try:
                    shutil.copy2(partner, soul_dest)
                    report.steps.append(f"generic SOUL.md ← partner → {soul_dest}")
                except OSError as exc:
                    report.errors.append(f"SOUL.md: {exc}")
    elif harness == "hermes":
        soul_dest = home_path / "SOUL.md"
        if soul_dest.is_file():
            report.steps.append(
                f"left Hermes meister SOUL.md untouched → {soul_dest}"
            )
        else:
            report.steps.append(
                "no SOUL.md yet — Hermes will seed meister identity on first run "
                "(Conductor partner is CONDUCTOR_PARTNER_SOUL.md)"
            )

    # Package root marker so stock Hermes (any venv) can import conductor
    try:
        from conductor.bootstrap import write_package_root_marker

        marker = write_package_root_marker(home_path, hermes_mode=(harness == "hermes"))
        if marker is not None:
            report.steps.append(f"package root marker → {marker}")
            report.steps.append(
                f"shell env → {home_path / 'conductor.env'}  (source before hermes)"
            )
        else:
            report.steps.append(
                "○ package root marker not written — pip install -e this repo into Hermes venv"
            )
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"package marker: {exc}")

    # Optional: install package into Hermes interpreter
    do_pip = install_pip
    if do_pip is None and harness == "hermes":
        from conductor.hermes_host import hermes_available

        do_pip = hermes_available()
    if do_pip and harness == "hermes":
        try:
            from conductor.adapters.hermes.ready import install_into_hermes_venv

            ok_pip, detail = install_into_hermes_venv(repo_root=repo_root())
            report.hermes_pip = detail
            if ok_pip:
                report.steps.append(f"hermes venv pip: {detail}")
            else:
                report.steps.append(f"○ hermes venv pip skipped/failed: {detail}")
        except Exception as exc:  # noqa: BLE001
            report.steps.append(f"○ hermes venv pip: {exc}")

    return report


def assert_setup_layout(home: Path, *, harness: str = "hermes") -> list[str]:
    """Return list of missing/invalid paths after setup (empty = good)."""
    home = Path(home)
    harness = (harness or "hermes").strip().lower()
    missing: list[str] = []
    if not (home / "config.yaml").is_file():
        missing.append(str(home / "config.yaml"))
    if harness == "hermes":
        for p in (
            home / "plugins" / PRODUCT_PLUGIN / "plugin.yaml",
            home / "plugins" / PRODUCT_PLUGIN / "__init__.py",
        ):
            if not p.is_file():
                missing.append(str(p))
        if (home / "plugins" / LEGACY_PLUGIN / "plugin.yaml").is_file() and not (
            home / "plugins" / PRODUCT_PLUGIN / "plugin.yaml"
        ).is_file():
            missing.append("legacy plugins/ilo without plugins/conductor")

    skills = home / "skills" / "conductor"
    if not skills.is_dir() or not any(skills.rglob("SKILL.md")):
        missing.append(str(skills / "**/SKILL.md"))

    leftover = find_fable_skill_dirs(home / "skills")
    if leftover:
        missing.append(
            "fable skills still present: " + ", ".join(str(p) for p in leftover)
        )

    if harness == "hermes":
        try:
            import yaml

            raw = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8")) or {}
            enabled = (
                ((raw.get("plugins") or {}).get("enabled") or []) if isinstance(raw, dict) else []
            )
            enabled_s = [str(x) for x in enabled]
            if PRODUCT_PLUGIN not in enabled_s:
                missing.append(f"config.yaml plugins.enabled missing {PRODUCT_PLUGIN}")
            if LEGACY_PLUGIN in enabled_s:
                missing.append(f"config.yaml still enables legacy plugin {LEGACY_PLUGIN}")
            man = yaml.safe_load(
                (home / "plugins" / PRODUCT_PLUGIN / "plugin.yaml").read_text(encoding="utf-8")
            )
            if isinstance(man, dict) and str(man.get("name")) != PRODUCT_PLUGIN:
                missing.append(f"plugin.yaml name is {man.get('name')!r}, want {PRODUCT_PLUGIN}")
        except Exception as exc:  # noqa: BLE001
            missing.append(f"config/plugin read: {exc}")
    return missing
