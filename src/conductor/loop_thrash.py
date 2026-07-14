"""Proactive thrash guard — same tool+args repeated → stop before more wounds.

Hot path: process-local memory first (benchmark: avoid SQLite every pre_tool).
Durable write-through on block or every N hits when a store is provided.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from conductor.session.store import SessionStore

THRASH_META_KEY = "loop_thrash"
DEFAULT_REPEAT_THRESHOLD = 3
DEFAULT_WINDOW_S = 600.0  # 10 minutes
_PERSIST_EVERY = 5  # write-through cadence when not blocked

# session_id -> thrash payload (same shape as durable meta)
_MEM: dict[str, dict[str, Any]] = {}


def _threshold() -> int:
    raw = (
        os.environ.get("CONDUCTOR_THRASH_THRESHOLD", "").strip()
        or os.environ.get("ILO_THRASH_THRESHOLD", "").strip()  # legacy
    )
    try:
        return max(2, int(raw)) if raw else DEFAULT_REPEAT_THRESHOLD
    except ValueError:
        return DEFAULT_REPEAT_THRESHOLD


def thrash_disabled() -> bool:
    return os.environ.get("CONDUCTOR_THRASH", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def fingerprint_call(tool_name: str, args: Any) -> str:
    """Stable hash of tool name + normalized args."""
    try:
        if isinstance(args, str):
            payload = args
        else:
            payload = json.dumps(args or {}, sort_keys=True, default=str)
    except (TypeError, ValueError):
        payload = str(args)
    raw = f"{tool_name or ''}|{payload}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:24]


@dataclass
class ThrashHit:
    blocked: bool
    count: int
    fingerprint: str
    tool_name: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "count": self.count,
            "fingerprint": self.fingerprint,
            "tool_name": self.tool_name,
            "message": self.message,
        }


def _load_durable(store: SessionStore, session_id: str) -> dict[str, Any]:
    raw = store.get_meta(session_id, THRASH_META_KEY, default={})
    return raw if isinstance(raw, dict) else {}


def _save_durable(store: SessionStore, session_id: str, data: dict[str, Any]) -> None:
    store.set_meta(session_id, THRASH_META_KEY, data)


def clear_thrash_memory(session_id: str | None = None) -> None:
    """Test / session-end helper."""
    if session_id is None:
        _MEM.clear()
    else:
        _MEM.pop(session_id, None)


def record_and_check(
    store: SessionStore | None,
    session_id: str,
    tool_name: str,
    args: Any = None,
    *,
    threshold: int | None = None,
    window_s: float = DEFAULT_WINDOW_S,
) -> ThrashHit:
    """Record a tool call; block when the same fingerprint repeats past threshold."""
    fp = fingerprint_call(tool_name, args)
    thr = threshold if threshold is not None else _threshold()
    if thrash_disabled() or not session_id:
        return ThrashHit(blocked=False, count=1, fingerprint=fp, tool_name=tool_name)

    now = time.time()
    data = _MEM.get(session_id)
    if data is None and store is not None:
        try:
            data = _load_durable(store, session_id)
        except Exception:  # noqa: BLE001
            data = {}
    if data is None:
        data = {}

    calls: list[dict[str, Any]] = list(data.get("calls") or [])
    # prune window
    calls = [c for c in calls if now - float(c.get("t") or 0) <= window_s]
    matching = [c for c in calls if c.get("fp") == fp]
    count = len(matching) + 1
    calls.append({"fp": fp, "tool": tool_name, "t": now})
    data["calls"] = calls[-80:]
    data["last_fp"] = fp
    data["last_count"] = count
    _MEM[session_id] = data

    blocked = count >= thr
    # Persist on block, or every N hits, so scars survive process restart
    if store is not None and (blocked or count % _PERSIST_EVERY == 0):
        try:
            _save_durable(store, session_id, data)
        except Exception:  # noqa: BLE001
            pass

    if blocked:
        msg = thrash_block_message(tool_name=tool_name, count=count, fingerprint=fp)
        return ThrashHit(
            blocked=True,
            count=count,
            fingerprint=fp,
            tool_name=tool_name,
            message=msg,
        )
    return ThrashHit(blocked=False, count=count, fingerprint=fp, tool_name=tool_name)


def thrash_block_message(
    *,
    tool_name: str,
    count: int,
    fingerprint: str = "",
) -> str:
    """Operator/agent-facing thrash block text.

    Explicitly does **not** mean abort the whole mission — only stop
    repeating the identical tool call.
    """
    thr = _threshold()
    fp_bit = f" fp={fingerprint}" if fingerprint else ""
    return (
        f"Conductor thrash guard: blocked repeated tool {tool_name!r} "
        f"({count}× same args; threshold={thr}{fp_bit}).\n"
        "THIS IS NOT 'stop everything' / abort the mission.\n"
        "Do:\n"
        "  1) Change the command, path, or arguments (new fingerprint clears the block)\n"
        "  2) Or try a different tool / smaller scope\n"
        "  3) Or heal_status / scars for that wound class, then one alternate approach\n"
        "  4) Optional deep path: /crucible max_effort\n"
        "Do not re-fire the exact same tool+args. Mission continues with a new action."
    )
