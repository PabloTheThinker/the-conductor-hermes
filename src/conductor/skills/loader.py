"""Progressive disclosure: tier-0 index, tier-1/2 skill_view."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from conductor.paths import bundled_skills_roots, skills_dir
from conductor.skills.frontmatter import parse_frontmatter
from conductor.skills.scanner import SkillMeta, scan_skills_roots


def _conductor_skill_dest_prefix(src: Path) -> str:
    """Normalize conductor skill trees under CONDUCTOR_HOME/skills/conductor/."""
    name = src.name
    if name in {"conductor", "ilo-conductor"}:  # ilo-conductor: legacy home alias
        return "conductor"
    # Fable skill pack is not part of The Conductor product seed.
    return ""


def refresh_conductor_skills() -> int:
    """Sync bundled Conductor skills into CONDUCTOR_HOME/skills/ (always overwrite)."""
    dest = skills_dir()
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in bundled_skills_roots():
        if not src.exists():
            continue
        prefix = _conductor_skill_dest_prefix(src)
        for skill_md in src.rglob("SKILL.md"):
            rel = skill_md.parent.relative_to(src)
            target = (dest / prefix / rel) if prefix else (dest / rel)
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_md, target / "SKILL.md")
            copied += 1
    return copied


def ensure_skills_seeded() -> Path:
    """Seed or refresh bundled Conductor skills under CONDUCTOR_HOME/skills/."""
    refresh_conductor_skills()
    return skills_dir()


def skills_index() -> list[SkillMeta]:
    ensure_skills_seeded()
    return scan_skills_roots([skills_dir()])


def build_skills_index_text() -> str:
    """Tier-0 compact index for system prompt (name + description only)."""
    rows = skills_index()
    if not rows:
        return "No skills installed. Use /learn to create skills."
    lines = ["Available skills (invoke with /<name>):"]
    for meta in rows:
        lines.append(f"- /{meta.name}: {meta.description}")
    return "\n".join(lines)


# Advisory skill aliases — /remnant <question> maps to remnant-guide without colliding with ops slash.
_SKILL_ALIASES = {
    "remnant": "remnant-guide",
}


def find_skill(name: str) -> SkillMeta | None:
    needle = name.strip().lower()
    needle = _SKILL_ALIASES.get(needle, needle)
    for meta in skills_index():
        if meta.name == needle or meta.name == name:
            return meta
    return None


_find_skill = find_skill


def skills_list(category: str | None = None) -> str:
    rows = skills_index()
    if category:
        rows = [m for m in rows if m.category == category]
    payload = [
        {"name": m.name, "description": m.description, "category": m.category, "path": str(m.path)}
        for m in rows
    ]
    return json.dumps({"skills": payload, "count": len(payload)}, indent=2)


def skill_view(name: str, file_path: str | None = None) -> str:
    meta = _find_skill(name)
    if not meta:
        return f"Error: skill not found: {name}"
    if file_path:
        target = (meta.path / file_path).resolve()
        if not str(target).startswith(str(meta.path.resolve())):
            return f"Error: path escapes skill directory: {file_path}"
        if not target.exists():
            return f"Error: file not found: {file_path}"
        try:
            return target.read_text(encoding="utf-8", errors="replace")[:50000]
        except OSError as exc:
            return f"Error reading {file_path}: {exc}"
    skill_md = meta.path / "SKILL.md"
    try:
        return skill_md.read_text(encoding="utf-8", errors="replace")[:50000]
    except OSError as exc:
        return f"Error reading skill: {exc}"


def skill_body(name: str) -> str:
    """Return markdown body (without frontmatter) for invocation."""
    raw = skill_view(name)
    if raw.startswith("Error:"):
        return raw
    _, body = parse_frontmatter(raw)
    return body.strip()
