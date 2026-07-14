"""Decision audit trail — persisted per agent session."""

from __future__ import annotations

from typing import Any

from conductor.governance.models import AuditRecord, GateResult
from conductor.session.store import SessionStore

AUDIT_META_KEY = "governance_audit"


class AuditStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load(self, agent_session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(agent_session_id, AUDIT_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save(self, agent_session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(agent_session_id, AUDIT_META_KEY, data)

    def record(
        self,
        agent_session_id: str,
        *,
        action_type: str,
        gate: GateResult,
    ) -> AuditRecord:
        if gate.blocked:
            outcome = "blocked"
        elif gate.requires_escalation:
            outcome = "escalated"
        else:
            outcome = "allowed"
        record = AuditRecord(
            session_id=agent_session_id,
            action_type=action_type,
            gate=gate,
            outcome=outcome,
        )
        data = self._load(agent_session_id)
        items: list[Any] = list(data.get("items") or [])
        items.append(record.model_dump(mode="json"))
        data["items"] = items[-100:]
        self._save(agent_session_id, data)
        return record

    def list_records(self, agent_session_id: str, *, limit: int = 20) -> list[AuditRecord]:
        data = self._load(agent_session_id)
        items = data.get("items") or []
        records = [AuditRecord.model_validate(item) for item in items if isinstance(item, dict)]
        return list(reversed(records[-limit:]))
