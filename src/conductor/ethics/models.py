"""Ethics checklist models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EthicsPointResult(BaseModel):
    point_id: str
    title: str
    status: str  # clear | concern | blocked
    rationale: str = ""


class EthicsEvaluation(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str
    evaluated_at: datetime = Field(default_factory=_utcnow)
    points: list[EthicsPointResult] = Field(default_factory=list)
    blocked: bool = False
    requires_escalation: bool = False
    summary: str = ""
    context: dict[str, Any] = Field(default_factory=dict)

    @property
    def concern_count(self) -> int:
        return sum(1 for p in self.points if p.status in {"concern", "blocked"})
