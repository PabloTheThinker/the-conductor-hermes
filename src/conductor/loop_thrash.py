"""Proactive thrash guard — same tool+args repeated → stop before more wounds.

Hot path: process-local memory first (benchmark: avoid SQLite every pre_tool).
Durable write-through on block or every N hits when a store is provided.

Batch-aware (1.18.9+): optional ``batch_id`` / ``wave_id`` fold into the
fingerprint so:

- Hermes segmented re-dispatch of the *same* host batch does not stack thrash
  when the parent tags ``_conductor_batch`` / batch_id.
- A new batch/wave is a new fingerprint (intentional re-try after wave B).
- Without batch/wave ids, behavior matches 1.18.8 (tool+args only).
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


def _extract_batch_wave(
    args: Any,
    *,
    batch_id: str | None = None,
    wave_id: str | None = None,
) -> tuple[str, str]:
    """Pull batch/wave ids from kwargs or args meta keys."""
    bid = (batch_id or "").strip()
    wid = (wave_id or "").strip()
    if isinstance(args, dict):
        if not bid:
            bid = str(
                args.get("_conductor_batch")
                or args.get("batch_id")
                or args.get("_batch_id")
                or ""
            ).strip()
        if not wid:
            wid = str(
                args.get("_conductor_wave")
                or args.get("wave_id")
                or args.get("wave")
                or args.get("_wave_id")
                or ""
            ).strip()
        # Strip meta keys from fingerprint payload so they only appear once
    return bid, wid


def _args_for_fingerprint(args: Any) -> Any:
    """Copy args without thrash meta keys (batch/wave live in outer fingerprint)."""
    if not isinstance(args, dict):
        return args
    skip = {
        "_conductor_batch",
        "_conductor_wave",
        "batch_id",
        "_batch_id",
        "wave_id",
        "_wave_id",
        # bare "wave" is ambiguous (mission wave vs thrash) — only strip if A/B/C
    }
    out = {}
    for k, v in args.items():
        if k in skip:
            continue
        if k == "wave" and str(v).strip().upper() in {"A", "B", "C"}:
            continue
        out[k] = v
    return out


def fingerprint_call(
    tool_name: str,
    args: Any = None,
    *,
    batch_id: str | None = None,
    wave_id: str | None = None,
) -> str:
    """Stable hash of tool name + normalized args + optional batch/wave."""
    bid, wid = _extract_batch_wave(args, batch_id=batch_id, wave_id=wave_id)
    payload_src = _args_for_fingerprint(args)
    try:
        if isinstance(payload_src, str):
            payload = payload_src
        else:
            payload = json.dumps(payload_src or {}, sort_keys=True, default=str)
    except (TypeError, ValueError):
        payload = str(payload_src)
    raw = f"{tool_name or ''}|{payload}|batch={bid}|wave={wid}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:24]


@dataclass
class ThrashHit:
    blocked: bool
    count: int
    fingerprint: str
    tool_name: str
    message: str = ""
    batch_id: str = ""
    wave_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "count": self.count,
            "fingerprint": self.fingerprint,
            "tool_name": self.tool_name,
            "message": self.message,
            "batch_id": self.batch_id,
            "wave_id": self.wave_id,
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
    batch_id: str | None = None,
    wave_id: str | None = None,
) -> ThrashHit:
    """Record a tool call; block when the same fingerprint repeats past threshold."""
    bid, wid = _extract_batch_wave(args, batch_id=batch_id, wave_id=wave_id)
    fp = fingerprint_call(tool_name, args, batch_id=bid or None, wave_id=wid or None)
    thr = threshold if threshold is not None else _threshold()
    if thrash_disabled() or not session_id:
        return ThrashHit(
            blocked=False,
            count=1,
            fingerprint=fp,
            tool_name=tool_name,
            batch_id=bid,
            wave_id=wid,
        )

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
    calls.append(
        {
            "fp": fp,
            "tool": tool_name,
            "t": now,
            "batch": bid,
            "wave": wid,
        }
    )
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
        msg = thrash_block_message(
            tool_name=tool_name,
            count=count,
            fingerprint=fp,
            batch_id=bid,
            wave_id=wid,
        )
        return ThrashHit(
            blocked=True,
            count=count,
            fingerprint=fp,
            tool_name=tool_name,
            message=msg,
            batch_id=bid,
            wave_id=wid,
        )
    return ThrashHit(
        blocked=False,
        count=count,
        fingerprint=fp,
        tool_name=tool_name,
        batch_id=bid,
        wave_id=wid,
    )


def thrash_block_message(
    *,
    tool_name: str,
    count: int,
    fingerprint: str = "",
    batch_id: str = "",
    wave_id: str = "",
) -> str:
    """Operator/agent-facing thrash block text.

    Explicitly does **not** mean abort the whole mission — only stop
    repeating the identical tool call.
    """
    thr = _threshold()
    fp_bit = f" fp={fingerprint}" if fingerprint else ""
    batch_bit = ""
    if batch_id or wave_id:
        batch_bit = f" batch={batch_id or '-'} wave={wave_id or '-'}"
    return (
        f"Conductor thrash guard: blocked repeated tool {tool_name!r} "
        f"({count}× same args; threshold={thr}{fp_bit}{batch_bit}).\n"
        "THIS IS NOT 'stop everything' / abort the mission.\n"
        "Do:\n"
        "  1) Change the command, path, or arguments (new fingerprint clears the block)\n"
        "  2) Or try a different tool / smaller scope\n"
        "  3) Or heal_status / scars for that wound class, then one alternate approach\n"
        "  4) Optional deep path: /crucible max_effort\n"
        "  5) New host batch/wave id also clears (segmented re-fire of a *new* batch)\n"
        "Do not re-fire the exact same tool+args. Mission continues with a new action."
    )
