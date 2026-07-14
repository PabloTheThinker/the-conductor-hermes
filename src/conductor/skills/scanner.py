"""Scan CONDUCTOR_HOME/skills for agentskills.io SKILL.md trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from conductor.paths import skills_dir
from conductor.skills.frontmatter import parse_frontmatter

EXCLUDED_DIRS = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", "references", "templates", "scripts", "assets"}
)


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path
    category: str = ""

    def slug(self) -> str:
        return self.name


def _is_skill_root(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def scan_skills_roots(roots: list[Path] | None = None) -> list[SkillMeta]:
    roots = roots or [skills_dir()]
    found: dict[str, SkillMeta] = {}
    for root in roots:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            if any(part in EXCLUDED_DIRS for part in skill_md.parts):
                continue
            skill_root = skill_md.parent
            if not _is_skill_root(skill_root):
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, _ = parse_frontmatter(content)
            name = str(fm.get("name", skill_root.name)).strip()
            description = str(fm.get("description", "")).strip()
            if not name or not description:
                continue
            category = ""
            try:
                category = skill_root.relative_to(root).parts[0]
            except ValueError:
                category = ""
            meta = SkillMeta(name=name, description=description[:1024], path=skill_root, category=category)
            found[name] = meta
    return sorted(found.values(), key=lambda m: m.name)
