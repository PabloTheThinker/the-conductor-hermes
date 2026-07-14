"""Research list/view tools and tier-0 index for system prompt."""

from __future__ import annotations

from pathlib import Path

from conductor.paths import _repo_root
from conductor.research.scanner import RESEARCH_PILLARS, ResearchDoc, scan_research_docs


def research_list(pillar: str | None = None) -> str:
    """Return tier-0 research index (path, title, description)."""
    docs = scan_research_docs()
    if pillar:
        p = pillar.strip().lower()
        docs = [d for d in docs if d.pillar == p]
    if not docs:
        return "No research documents found."
    lines = [f"Research corpus ({len(docs)} documents):"]
    for doc in docs:
        lines.append(f"- [{doc.pillar}] {doc.path} — {doc.title}: {doc.description}")
    return "\n".join(lines)


def _resolve_research_path(rel: str) -> tuple[Path, Path] | None:
    """Return (repo_root, target) for a research spec path under the repo root."""
    root = _repo_root().resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    if target.exists():
        return root, target
    return None


def research_view(path: str, *, max_chars: int = 12000) -> str:
    """Load a research spec by repo-relative path."""
    rel = path.strip().lstrip("/")
    if not rel:
        return "Error: path required"
    resolved = _resolve_research_path(rel)
    if not resolved:
        return f"Error: not found: {rel}"
    _root, target = resolved
    if target.suffix.lower() != ".md":
        return f"Error: only .md research specs supported: {rel}"
    pillar = rel.split("/", 1)[0]
    if pillar not in RESEARCH_PILLARS and not rel.startswith("docs/"):
        return f"Error: not a research pillar path: {rel}"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error reading {rel}: {exc}"
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[truncated at {max_chars} chars — use research_view on sections]"
    return text


def build_research_index_text() -> str:
    """Compact tier-0 block for system prompt."""
    docs = scan_research_docs()
    if not docs:
        return "## Research corpus\n(none indexed)"
    by_pillar: dict[str, list[ResearchDoc]] = {}
    for doc in docs:
        by_pillar.setdefault(doc.pillar, []).append(doc)
    lines = ["## Research corpus (tier-0 index)", "Use research_list / research_view for full specs.", ""]
    for pillar in RESEARCH_PILLARS:
        group = by_pillar.get(pillar)
        if not group:
            continue
        lines.append(f"### {pillar}")
        for doc in group:
            lines.append(f"- {doc.path} — {doc.title}")
        lines.append("")
    return "\n".join(lines).strip()
