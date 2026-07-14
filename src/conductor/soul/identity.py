"""SOUL.md identity loader and integrity verification."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from conductor.paths import canonical_soul_path, soul_path

_IMMUTABLE_FOOTER = "immutable core identity"


@dataclass(frozen=True)
class SoulIdentity:
    path: Path
    content: str
    content_hash: str
    tagline: str
    word_count: int
    has_ethics_directive: bool
    has_immutable_marker: bool
    runtime_path: Path | None = None
    runtime_overridden: bool = False

    @property
    def integrity_ok(self) -> bool:
        return bool(self.content.strip()) and self.has_ethics_directive and self.has_immutable_marker


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_tagline(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:120]
    return "Sovereign neurodivergent conductor"


def load_soul_identity(path: Path | None = None) -> SoulIdentity:
    resolved = path or canonical_soul_path()
    runtime = soul_path()
    runtime_overridden = runtime.resolve() != resolved.resolve() and runtime.exists()
    if not resolved.exists():
        return SoulIdentity(
            path=resolved,
            content="",
            content_hash="",
            tagline="SOUL.md not loaded",
            word_count=0,
            has_ethics_directive=False,
            has_immutable_marker=False,
            runtime_path=runtime,
            runtime_overridden=runtime_overridden,
        )
    content = resolved.read_text(encoding="utf-8", errors="replace")
    lowered = content.casefold()
    return SoulIdentity(
        path=resolved,
        content=content,
        content_hash=_sha256(content),
        tagline=_extract_tagline(content),
        word_count=len(re.findall(r"\w+", content)),
        has_ethics_directive="ethics decision checklist" in lowered,
        has_immutable_marker=_IMMUTABLE_FOOTER in lowered,
        runtime_path=runtime,
        runtime_overridden=runtime_overridden,
    )
