"""Noesis scheduler — trigger evaluation + durable schedule state.

Runs shallow RBMC when:
- explicit once/force
- interval elapsed since last successful run
- high-priority tracks / high uncertainty signals present
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conductor.paths import conductor_home


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def schedule_state_path() -> Path:
    path = conductor_home() / "noesis"
    path.mkdir(parents=True, exist_ok=True)
    return path / "schedule.json"


@dataclass
class ScheduleState:
    last_run_at: str = ""
    last_status: str = "never"
    last_objective: str = ""
    last_result_summary: str = ""
    run_count: int = 0
    interval_seconds: int = 6 * 3600  # 6h default
    enabled: bool = True
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_run_at": self.last_run_at,
            "last_status": self.last_status,
            "last_objective": self.last_objective,
            "last_result_summary": self.last_result_summary,
            "run_count": self.run_count,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "history": self.history[-20:],
        }

    @classmethod
    def load(cls) -> ScheduleState:
        path = schedule_state_path()
        if not path.is_file():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        return cls(
            last_run_at=str(raw.get("last_run_at") or ""),
            last_status=str(raw.get("last_status") or "never"),
            last_objective=str(raw.get("last_objective") or ""),
            last_result_summary=str(raw.get("last_result_summary") or ""),
            run_count=int(raw.get("run_count") or 0),
            interval_seconds=int(raw.get("interval_seconds") or 6 * 3600),
            enabled=bool(raw.get("enabled", True)),
            history=list(raw.get("history") or [])[-20:],
        )

    def save(self) -> None:
        path = schedule_state_path()
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def _seconds_since(iso: str) -> float | None:
    if not iso:
        return None
    try:
        # support Z suffix
        cleaned = iso.replace("Z", "+00:00")
        then = datetime.fromisoformat(cleaned)
        if then.tzinfo is None:
            then = then.replace(tzinfo=UTC)
        return (datetime.now(UTC) - then).total_seconds()
    except ValueError:
        return None


def evaluate_triggers(
    state: ScheduleState,
    *,
    force: bool = False,
    track_signals: list[dict[str, Any]] | None = None,
    failure_signal: bool = False,
) -> dict[str, Any]:
    """Decide whether a Noesis run should fire."""
    if force:
        return {"should_run": True, "reason": "force", "priority": 1.0}
    if not state.enabled:
        return {"should_run": False, "reason": "disabled", "priority": 0.0}

    elapsed = _seconds_since(state.last_run_at)
    if elapsed is None:
        return {"should_run": True, "reason": "never_run", "priority": 0.8}

    if failure_signal:
        return {"should_run": True, "reason": "failure_signal", "priority": 0.95}

    tracks = track_signals or []
    high = [t for t in tracks if float(t.get("priority") or 0) >= 0.8]
    uncertain = [
        t
        for t in tracks
        if float(t.get("confidence") or 1.0) < 0.5 and str(t.get("status") or "") == "active"
    ]
    if high or uncertain:
        if elapsed >= min(state.interval_seconds, 1800):  # at most 30m gate for urgency
            return {
                "should_run": True,
                "reason": "high_uncertainty_tracks",
                "priority": 0.9,
                "high_priority_tracks": len(high),
                "low_confidence_tracks": len(uncertain),
            }

    if elapsed >= state.interval_seconds:
        return {
            "should_run": True,
            "reason": "interval_elapsed",
            "priority": 0.7,
            "elapsed_seconds": elapsed,
        }

    return {
        "should_run": False,
        "reason": "cooldown",
        "priority": 0.0,
        "elapsed_seconds": elapsed,
        "remaining_seconds": max(0, state.interval_seconds - elapsed),
    }


def run_scheduled_noesis(
    conductor: Any,
    agent_session_id: str,
    *,
    objective: str = "",
    force: bool = False,
    track_signals: list[dict[str, Any]] | None = None,
    failure_signal: bool = False,
    max_clones: int = 3,
) -> dict[str, Any]:
    """Evaluate triggers and optionally run Noesis; always updates schedule state."""
    state = ScheduleState.load()
    decision = evaluate_triggers(
        state,
        force=force,
        track_signals=track_signals,
        failure_signal=failure_signal,
    )
    if not decision["should_run"]:
        return {
            "ran": False,
            "decision": decision,
            "schedule": state.to_dict(),
        }

    obj = objective.strip() or f"Scheduled Noesis ({decision['reason']})"
    started = time.time()
    try:
        result = conductor.run_noesis(
            agent_session_id,
            objective=obj,
            max_clones=max_clones,
            auto_distill=True,
        )
        status = "success"
        summary = f"promoted={len((result.get('distilled') or {}).get('promoted_insights') or [])}"
    except Exception as exc:  # noqa: BLE001
        result = {"error": str(exc)}
        status = "failure"
        summary = str(exc)[:200]

    state.last_run_at = _utcnow()
    state.last_status = status
    state.last_objective = obj
    state.last_result_summary = summary
    state.run_count += 1
    state.history.append(
        {
            "at": state.last_run_at,
            "status": status,
            "objective": obj,
            "reason": decision.get("reason"),
            "elapsed_ms": int((time.time() - started) * 1000),
            "summary": summary,
        }
    )
    state.save()
    return {
        "ran": True,
        "decision": decision,
        "result": result,
        "schedule": state.to_dict(),
    }
