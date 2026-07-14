"""Scar ledger and integrity-cascade report models (Conductor-native)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Remediation:
    """One field repair attempted at a wound site."""

    action: str
    result: str  # success | failure | skipped
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "result": self.result, "detail": self.detail}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Remediation:
        return cls(
            action=str(data.get("action") or ""),
            result=str(data.get("result") or "skipped"),
            detail=str(data.get("detail") or ""),
        )


@dataclass
class Scar:
    """Durable wound record in the integrity cascade."""

    scar_id: str
    session_id: str
    kind: str
    severity: int
    status: str  # open | healing | healed | chronic | escalated
    summary: str
    source_tool: str = ""
    error: str = ""
    path: str = ""
    tier: str = "reflex"  # reflex | field | deep
    remediations: list[Remediation] = field(default_factory=list)
    recovered_paths: list[str] = field(default_factory=list)
    seal: str = ""  # learned seal (short rule for Memory Fabric)
    forward_step: str = ""
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scar_id": self.scar_id,
            "session_id": self.session_id,
            "kind": self.kind,
            "severity": self.severity,
            "status": self.status,
            "summary": self.summary,
            "source_tool": self.source_tool,
            "error": self.error,
            "path": self.path,
            "tier": self.tier,
            "remediations": [r.to_dict() for r in self.remediations],
            "recovered_paths": list(self.recovered_paths),
            "seal": self.seal,
            "forward_step": self.forward_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scar:
        rem = [
            Remediation.from_dict(r)
            for r in (data.get("remediations") or [])
            if isinstance(r, dict)
        ]
        # Accept legacy key "antibody" as seal
        seal = str(data.get("seal") or data.get("antibody") or "")
        return cls(
            scar_id=str(data.get("scar_id") or uuid.uuid4()),
            session_id=str(data.get("session_id") or ""),
            kind=str(data.get("kind") or "unknown"),
            severity=int(data.get("severity") or 2),
            status=str(data.get("status") or "open"),
            summary=str(data.get("summary") or ""),
            source_tool=str(data.get("source_tool") or ""),
            error=str(data.get("error") or ""),
            path=str(data.get("path") or ""),
            tier=str(data.get("tier") or "reflex"),
            remediations=rem,
            recovered_paths=[str(p) for p in (data.get("recovered_paths") or [])],
            seal=seal,
            forward_step=str(data.get("forward_step") or ""),
            created_at=str(data.get("created_at") or _utcnow()),
            updated_at=str(data.get("updated_at") or _utcnow()),
        )

    @classmethod
    def open_new(
        cls,
        *,
        session_id: str,
        kind: str,
        severity: int,
        summary: str,
        source_tool: str = "",
        error: str = "",
        path: str = "",
    ) -> Scar:
        return cls(
            scar_id=str(uuid.uuid4()),
            session_id=session_id,
            kind=kind,
            severity=max(1, min(5, severity)),
            status="open",
            summary=summary,
            source_tool=source_tool,
            error=error[:2000],
            path=path,
            tier="reflex",
        )


@dataclass
class HealReport:
    """Result of one integrity cascade pass (reflex + field repairs)."""

    scar: Scar
    healed: bool
    actions: list[str] = field(default_factory=list)
    message: str = ""
    forward_step: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "healed": self.healed,
            "scar": self.scar.to_dict(),
            "actions": list(self.actions),
            "message": self.message,
            "forward_step": self.forward_step,
        }

    def as_tool_suffix(self) -> str:
        """Append to failed tool output so the model sees integrity context."""
        lines = [
            "",
            "---",
            f"[Integrity cascade] scar={self.scar.scar_id[:8]} kind={self.scar.kind} "
            f"tier={self.scar.tier} status={self.scar.status} healed={self.healed}",
        ]
        if self.message:
            lines.append(self.message)
        if self.forward_step:
            lines.append(f"Advance: {self.forward_step}")
        if self.scar.seal:
            lines.append(f"Learned seal: {self.scar.seal}")
        return "\n".join(lines)
