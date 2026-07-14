"""Agent-managed skill creation and editing under CONDUCTOR_HOME/skills/."""

from __future__ import annotations

import re
from pathlib import Path

from conductor.paths import skills_dir

MAX_NAME = 64
MAX_DESC = 1024
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _slugify(name: str) -> str:
    slug = name.lower().strip().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:MAX_NAME]


def _skill_dir(name: str) -> Path:
    slug = _slugify(name)
    return skills_dir() / slug


def learn_from_source(source: str) -> str:
    """Create a minimal skill scaffold from /learn source description."""
    source = source.strip()
    if not source:
        return "Usage: /learn <source description or topic>"
    slug = _slugify(source.split()[0] if source.split() else "learned-skill")
    if not slug:
        slug = "learned-skill"
    desc = source[:MAX_DESC]
    title = slug.replace("-", " ").title()
    body = (
        f"# {title}\n\n"
        f"Skill learned from user source:\n\n{source}\n\n"
        f"Use this skill when the user invokes `/{slug}`."
    )
    result = skill_manage("create", name=slug, description=desc, content=body)
    return f"Learned skill `/{slug}` saved.\n{result}"


def skill_manage(
    action: str,
    *,
    name: str = "",
    description: str = "",
    content: str = "",
    patch_find: str = "",
    patch_replace: str = "",
) -> str:
    action = action.strip().lower()
    skills_dir().mkdir(parents=True, exist_ok=True)

    if action == "create":
        if not name or not description or not content:
            return "Error: create requires name, description, and content"
        slug = _slugify(name)
        if not _SLUG_RE.match(slug):
            return f"Error: invalid skill name slug: {slug}"
        target = _skill_dir(slug)
        if target.exists():
            return f"Error: skill already exists: {slug}"
        target.mkdir(parents=True, exist_ok=True)
        body = content if content.startswith("#") else f"# {slug}\n\n{content}"
        md = f"---\nname: {slug}\ndescription: {description[:MAX_DESC]}\n---\n\n{body}\n"
        (target / "SKILL.md").write_text(md, encoding="utf-8")
        return f"Created skill {slug} at {target}"

    if action == "patch":
        if not name or not patch_find:
            return "Error: patch requires name and patch_find"
        target = _skill_dir(name)
        skill_md = target / "SKILL.md"
        if not skill_md.exists():
            return f"Error: skill not found: {name}"
        text = skill_md.read_text(encoding="utf-8")
        if patch_find not in text:
            return f"Error: patch_find string not found in {name}"
        skill_md.write_text(text.replace(patch_find, patch_replace, 1), encoding="utf-8")
        return f"Patched skill {name}"

    if action == "delete":
        if not name:
            return "Error: delete requires name"
        target = _skill_dir(name)
        if not target.exists():
            return f"Error: skill not found: {name}"
        skill_md = target / "SKILL.md"
        if skill_md.exists():
            skill_md.unlink()
        if target.exists() and not any(target.iterdir()):
            target.rmdir()
        return f"Deleted skill {name}"

    return f"Error: unknown action {action} (use create, patch, delete)"
