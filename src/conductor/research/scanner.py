"""Scan Conductor research spec trees for agent discoverability."""

from __future__ import annotations

import re
from dataclasses import dataclass

from conductor.paths import research_root


RESEARCH_PILLARS = (
    "conductor",
    "memory",
    "governance",
    "crucible",
    "tracks",
    "noesis",
    "docs",
    "ethics",
)


@dataclass(frozen=True)
class ResearchDoc:
    path: str
    pillar: str
    title: str
    description: str


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _description_from_markdown(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            break
        if stripped.startswith("**") and stripped.endswith("**"):
            lines.append(stripped.strip("*"))
            continue
        lines.append(stripped)
        if len(" ".join(lines)) >= 120:
            break
    desc = " ".join(lines)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc[:200] if desc else "Conductor research specification"


def scan_research_docs() -> list[ResearchDoc]:
    """Enumerate markdown research specs under pillar directories."""
    corpus = research_root()
    docs: list[ResearchDoc] = []
    for pillar in RESEARCH_PILLARS:
        pillar_dir = corpus / pillar
        if not pillar_dir.is_dir():
            continue
        for path in sorted(pillar_dir.rglob("*.md")):
            rel = path.relative_to(corpus).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            title = _title_from_markdown(text, path.stem.replace("_", " "))
            docs.append(
                ResearchDoc(
                    path=rel,
                    pillar=pillar,
                    title=title,
                    description=_description_from_markdown(text),
                )
            )
    return docs
