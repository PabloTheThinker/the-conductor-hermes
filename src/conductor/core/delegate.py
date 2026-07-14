"""Generic worker delegation — conductor remains the accountability point.

Public harness profiles: ``offline`` | ``local`` (shell/echo). Operators may
register additional workers at runtime via :func:`register_worker`. No
site-specific worker brands ship in the default registry.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from conductor.memory.episodic import record_lifecycle_event
from conductor.session.store import SessionStore

DELEGATIONS_META_KEY = "delegations"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


WorkerFn = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class DelegationRecord:
    delegation_id: str
    session_id: str
    worker: str
    task: str
    status: str = "pending"  # pending | running | success | failure
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: str = field(default_factory=_utcnow)
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "session_id": self.session_id,
            "worker": self.worker,
            "task": self.task,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DelegationRecord:
        return cls(
            delegation_id=str(data.get("delegation_id", "")),
            session_id=str(data.get("session_id", "")),
            worker=str(data.get("worker", "")),
            task=str(data.get("task", "")),
            status=str(data.get("status", "pending")),
            result=dict(data.get("result") or {}),
            error=str(data.get("error", "")),
            created_at=str(data.get("created_at", "")),
            completed_at=str(data.get("completed_at", "")),
        )


def offline_worker(task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bounded offline/local worker — no network, no site topology required."""
    ctx = dict(context or {})
    mode = str(ctx.get("mode", "echo")).strip().lower()
    started = time.time()

    if mode == "shell":
        cmd = str(ctx.get("command") or task).strip()
        if not cmd:
            return {"ok": False, "error": "empty shell command", "worker": "offline"}
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=float(ctx.get("timeout", 30)),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return {
                "ok": proc.returncode == 0,
                "worker": "offline",
                "mode": "shell",
                "exit_code": proc.returncode,
                "output": out[:8000],
                "elapsed_ms": int((time.time() - started) * 1000),
                "task": task,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "worker": "offline",
                "mode": "shell",
                "error": "timeout",
                "task": task,
            }

    if mode == "fail":
        return {
            "ok": False,
            "worker": "offline",
            "mode": "fail",
            "error": str(ctx.get("error", "forced failure")),
            "task": task,
        }

    # Default echo / analysis worker
    return {
        "ok": True,
        "worker": "offline",
        "mode": "echo",
        "summary": f"Completed: {task[:500]}",
        "notes": list(ctx.get("notes") or []),
        "elapsed_ms": int((time.time() - started) * 1000),
        "task": task,
    }


_WORKER_REGISTRY: dict[str, WorkerFn] = {
    "offline": lambda task, ctx: offline_worker(task, ctx),
    "local": lambda task, ctx: offline_worker(task, ctx),
}


def register_worker(name: str, fn: WorkerFn) -> None:
    _WORKER_REGISTRY[name.strip().lower()] = fn


class DelegationLedger:
    """Parent-session durable record of delegated work."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    def _load(self, session_id: str) -> list[dict[str, Any]]:
        raw = self.store.get_meta(session_id, DELEGATIONS_META_KEY, default=[])
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
        if isinstance(raw, dict):
            items = raw.get("items") or []
            return [r for r in items if isinstance(r, dict)]
        return []

    def _save(self, session_id: str, items: list[dict[str, Any]]) -> None:
        self.store.set_meta(session_id, DELEGATIONS_META_KEY, {"items": items})

    def list_delegations(self, session_id: str, *, limit: int = 50) -> list[DelegationRecord]:
        items = self._load(session_id)
        records = [DelegationRecord.from_dict(i) for i in items]
        return list(reversed(records))[:limit]

    def get(self, session_id: str, delegation_id: str) -> DelegationRecord | None:
        for rec in self.list_delegations(session_id, limit=10_000):
            if rec.delegation_id == delegation_id:
                return rec
        return None

    def delegate(
        self,
        session_id: str,
        *,
        task: str,
        worker: str = "offline",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task = task.strip()
        if not task:
            raise ValueError("task required")
        worker_key = worker.strip().lower() or "offline"
        fn = _WORKER_REGISTRY.get(worker_key)
        if fn is None:
            raise ValueError(f"unknown worker: {worker_key} (known: {sorted(_WORKER_REGISTRY)})")

        record = DelegationRecord(
            delegation_id=str(uuid.uuid4()),
            session_id=session_id,
            worker=worker_key,
            task=task,
            status="running",
        )
        items = self._load(session_id)
        items.append(record.to_dict())
        self._save(session_id, items)

        try:
            result = fn(task, dict(context or {}))
            ok = bool(result.get("ok", True))
            record.status = "success" if ok else "failure"
            record.result = result
            if not ok:
                record.error = str(result.get("error") or "worker reported failure")
        except Exception as exc:  # noqa: BLE001 — surface to parent ledger
            record.status = "failure"
            record.error = str(exc)
            record.result = {"ok": False, "error": str(exc), "worker": worker_key}
        record.completed_at = _utcnow()

        # Replace last running entry with final
        items = self._load(session_id)
        replaced = False
        for i, row in enumerate(items):
            if row.get("delegation_id") == record.delegation_id:
                items[i] = record.to_dict()
                replaced = True
                break
        if not replaced:
            items.append(record.to_dict())
        self._save(session_id, items)

        record_lifecycle_event(
            self.store,
            session_id,
            kind="delegate",
            content=f"Delegated to {worker_key}: {task[:200]} → {record.status}",
            outcome="success" if record.status == "success" else "failure",
            emotion_primary="focused" if record.status == "success" else "concern",
            emotion_intensity=0.55,
            context=json.dumps(
                {"delegation_id": record.delegation_id, "worker": worker_key},
                sort_keys=True,
            ),
            extra_tags=[f"worker:{worker_key}", f"status:{record.status}"],
        )

        self.store.append_message(
            session_id,
            "system",
            f"[delegate_task] {worker_key} → {record.status}: {task[:120]}",
            extras={"delegation": record.to_dict()},
        )
        return record.to_dict()

    def fanout(
        self,
        session_id: str,
        *,
        tasks: list[str],
        worker: str = "offline",
        context: dict[str, Any] | None = None,
        max_workers: int = 4,
    ) -> list[dict[str, Any]]:
        """Run multiple bounded subtasks in parallel; all outcomes recorded on parent."""
        if not tasks:
            raise ValueError("tasks required")
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
            futures = {
                pool.submit(
                    self.delegate,
                    session_id,
                    task=t,
                    worker=worker,
                    context=context,
                ): t
                for t in tasks
            }
            for fut in as_completed(futures):
                results.append(fut.result())
        return results
