"""Cross-session learned seals — antibodies that survive new sessions.

Stored under CONDUCTOR_HOME/memory/global_seals.jsonl so Memory Fabric is not
session-local only.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conductor.paths import conductor_home


def global_seals_path() -> Path:
    return conductor_home() / "memory" / "global_seals.jsonl"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class GlobalSeal:
    seal_id: str
    statement: str
    kind: str = ""
    source_session: str = ""
    confidence: float = 0.75
    hits: int = 1
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seal_id": self.seal_id,
            "statement": self.statement,
            "kind": self.kind,
            "source_session": self.source_session,
            "confidence": self.confidence,
            "hits": self.hits,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalSeal:
        return cls(
            seal_id=str(data.get("seal_id") or ""),
            statement=str(data.get("statement") or ""),
            kind=str(data.get("kind") or ""),
            source_session=str(data.get("source_session") or ""),
            confidence=float(data.get("confidence") or 0.75),
            hits=int(data.get("hits") or 1),
            created_at=str(data.get("created_at") or _utcnow()),
            updated_at=str(data.get("updated_at") or _utcnow()),
        )


def _read_all(path: Path) -> list[GlobalSeal]:
    if not path.is_file():
        return []
    out: list[GlobalSeal] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(GlobalSeal.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    except OSError:
        return []
    return out


def _write_all(path: Path, seals: list[GlobalSeal]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Cap store
    seals = seals[-500:]
    body = "\n".join(json.dumps(s.to_dict(), ensure_ascii=False) for s in seals)
    if body:
        body += "\n"
    path.write_text(body, encoding="utf-8")


def list_global_seals(*, limit: int = 40, kind: str = "") -> list[GlobalSeal]:
    seals = _read_all(global_seals_path())
    if kind:
        seals = [s for s in seals if s.kind == kind]
    # newest / hottest first
    seals.sort(key=lambda s: (s.hits, s.updated_at), reverse=True)
    return seals[:limit]


def add_global_seal(
    statement: str,
    *,
    kind: str = "",
    source_session: str = "",
    confidence: float = 0.75,
) -> GlobalSeal:
    statement = (statement or "").strip()
    if not statement:
        raise ValueError("empty seal statement")
    path = global_seals_path()
    seals = _read_all(path)
    for s in seals:
        if s.statement.strip().lower() == statement.lower():
            s.hits += 1
            s.updated_at = _utcnow()
            if kind and not s.kind:
                s.kind = kind
            s.confidence = max(s.confidence, confidence)
            _write_all(path, seals)
            return s
    seal = GlobalSeal(
        seal_id=str(uuid.uuid4()),
        statement=statement,
        kind=kind,
        source_session=source_session,
        confidence=confidence,
    )
    seals.append(seal)
    _write_all(path, seals)
    return seal


def format_global_seals_block(*, max_seals: int = 6, max_chars: int = 600) -> str:
    seals = list_global_seals(limit=max_seals)
    if not seals:
        return ""
    lines = ["### Global seals (cross-session antibodies)"]
    for s in seals:
        tag = f"[{s.kind}] " if s.kind else ""
        lines.append(f"- {tag}{s.statement[:140]}")
    block = "\n".join(lines)
    if len(block) > max_chars:
        block = block[: max_chars - 3] + "..."
    return block
