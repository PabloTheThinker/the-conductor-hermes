"""Governance audit and policy models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from conductor.ethics.models import EthicsEvaluation


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ConstitutionalVerdict(BaseModel):
    rule_id: str
    matched: bool
    message: str = ""


class GateResult(BaseModel):
    gate_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str
    tier: str  # constitutional | policy | ethics
    allowed: bool = True
    requires_escalation: bool = False
    blocked: bool = False
    summary: str = ""
    constitutional: list[ConstitutionalVerdict] = Field(default_factory=list)
    ethics: EthicsEvaluation | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=_utcnow)


class AuditRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    action_type: str
    gate: GateResult
    outcome: str  # allowed | blocked | escalated
    created_at: datetime = Field(default_factory=_utcnow)
