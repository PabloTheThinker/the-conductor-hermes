"""Judgment layer — durable verification evidence for goals.

Inspired by Hermes verification_evidence: record what tools actually proved,
then let the goal judge require evidence for contract-bound goals.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from conductor.session.store import SessionStore

EVIDENCE_META_KEY = "verification_evidence"

_PATH_RE = re.compile(r"(/[\w./_-]+\.(?:txt|md|json|yaml|yml|py|toml|sh))")
_VERIFY_SHELL_RE = re.compile(
    r"\b(pytest|python\s+-m\s+pytest|npm\s+test|cargo\s+test|go\s+test|"
    r"ruff|mypy|make\s+test|unittest|conductor\s+doctor|ilo\s+doctor)\b",
    re.I,
)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class VerificationEvent:
    event_id: str
    session_id: str
    kind: str  # write_file | run_shell | shell_verify | tool
    status: str  # success | failure
    tool: str
    summary: str
    path: str = ""
    command: str = ""
    exit_code: int | None = None
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "kind": self.kind,
            "status": self.status,
            "tool": self.tool,
            "summary": self.summary,
            "path": self.path,
            "command": self.command,
            "exit_code": self.exit_code,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationEvent:
        return cls(
            event_id=str(data.get("event_id") or ""),
            session_id=str(data.get("session_id") or ""),
            kind=str(data.get("kind") or "tool"),
            status=str(data.get("status") or "failure"),
            tool=str(data.get("tool") or ""),
            summary=str(data.get("summary") or ""),
            path=str(data.get("path") or ""),
            command=str(data.get("command") or ""),
            exit_code=data.get("exit_code") if data.get("exit_code") is not None else None,
            created_at=str(data.get("created_at") or _utcnow()),
        )


def extract_path_hints(*texts: str) -> list[str]:
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in _PATH_RE.findall(text):
            if match not in found:
                found.append(match)
        # also bare path tokens starting with /
        for part in str(text).split():
            if part.startswith("/") and ("." in part or part.endswith("/")) and part not in found:
                # skip pure dirs without extension unless long enough
                if "." in part:
                    found.append(part)
    return found


def is_verification_shell(command: str) -> bool:
    return bool(_VERIFY_SHELL_RE.search(command or ""))


def classify_write_evidence(path: str, *, ok: bool) -> VerificationEvent | None:
    if not path:
        return None
    return VerificationEvent(
        event_id=str(uuid.uuid4()),
        session_id="",
        kind="write_file",
        status="success" if ok else "failure",
        tool="write_file",
        summary=f"{'Wrote' if ok else 'Failed write'} {path}",
        path=str(path),
    )


# Shell that actually creates/writes a file (not mere path mention).
_SHELL_CREATE_RE = re.compile(
    r"""(?ix)
    (?:
        \btouch\s+(?P<touch>(?:'[^']+'|"[^"]+"|\S+))
      | (?:echo|printf)\b.+\s>>?\s*(?P<redir>(?:'[^']+'|"[^"]+"|\S+))
      | \btee\s+(?P<tee>(?:'[^']+'|"[^"]+"|\S+))
      | \bcp\s+\S+\s+(?P<cp>(?:'[^']+'|"[^"]+"|\S+))
    )
    """
)


def extract_shell_create_path(command: str) -> str | None:
    """Return destination path if command is a clear create/write, else None."""
    cmd = (command or "").strip()
    if not cmd:
        return None
    match = _SHELL_CREATE_RE.search(cmd)
    if not match:
        return None
    raw = match.group("touch") or match.group("redir") or match.group("tee") or match.group("cp")
    if not raw:
        return None
    return raw.strip().strip("'\"")


def classify_shell_evidence(command: str, *, ok: bool, exit_code: int | None = None) -> VerificationEvent | None:
    cmd = (command or "").strip()
    if not cmd:
        return None
    create_path = extract_shell_create_path(cmd)
    if is_verification_shell(cmd):
        kind = "shell_verify"
    elif create_path:
        kind = "shell_create"
    else:
        kind = "run_shell"
    return VerificationEvent(
        event_id=str(uuid.uuid4()),
        session_id="",
        kind=kind,
        status="success" if ok else "failure",
        tool="run_shell",
        summary=f"shell exit {exit_code if exit_code is not None else ('0' if ok else '1')}: {cmd[:120]}",
        command=cmd,
        path=create_path or "",
        exit_code=exit_code if exit_code is not None else (0 if ok else 1),
    )


class VerificationStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load(self, session_id: str) -> list[dict[str, Any]]:
        raw = self._store.get_meta(session_id, EVIDENCE_META_KEY, default={})
        if isinstance(raw, dict):
            items = raw.get("events") or []
            return [i for i in items if isinstance(i, dict)]
        if isinstance(raw, list):
            return [i for i in raw if isinstance(i, dict)]
        return []

    def _save(self, session_id: str, events: list[dict[str, Any]]) -> None:
        self._store.set_meta(session_id, EVIDENCE_META_KEY, {"events": events[-200:]})

    def record(self, session_id: str, event: VerificationEvent) -> VerificationEvent:
        event.session_id = session_id
        events = self._load(session_id)
        events.append(event.to_dict())
        self._save(session_id, events)
        return event

    def list_events(self, session_id: str, *, limit: int = 50) -> list[VerificationEvent]:
        events = [VerificationEvent.from_dict(e) for e in self._load(session_id)]
        return list(reversed(events))[:limit]

    def successful(self, session_id: str) -> list[VerificationEvent]:
        return [e for e in self.list_events(session_id, limit=200) if e.status == "success"]


def _path_matches(required: str, candidate: str) -> bool:
    if not required or not candidate:
        return False
    return (
        required == candidate
        or candidate.endswith(required)
        or required.endswith(candidate)
    )


def evidence_satisfies_goal(
    *,
    goal: str,
    raw_goal: str,
    verification_field: str,
    events: list[VerificationEvent],
) -> tuple[bool, str]:
    """Pure decision: do durable events satisfy a contract-bound goal?

    Path create goals require write_file or shell_create evidence for that path —
    not bare path substring in arbitrary shell (e.g. ``echo /tmp/x.txt``).
    """
    success = [e for e in events if e.status == "success"]
    if not success:
        return False, "no successful verification evidence recorded"

    paths = extract_path_hints(goal, raw_goal, verification_field)
    if paths:
        # Only proven creates: write_file tool or shell_create classification
        creates = [
            e
            for e in success
            if e.kind in {"write_file", "shell_create"} and e.path
        ]
        for path in paths:
            if any(_path_matches(path, e.path) for e in creates):
                matched = next(e for e in creates if _path_matches(path, e.path))
                return True, f"{matched.kind} evidence for {path}"
        return False, f"missing write/create evidence for required path(s): {', '.join(paths)}"

    verify = (verification_field or "").strip().lower()
    if verify:
        # Strict kinds only — not generic run_shell that happens to share words
        for e in success:
            if e.kind == "shell_verify":
                return True, "shell verification command succeeded"
            if e.kind in {"write_file", "shell_create"}:
                blob = f"{e.summary} {e.path}".lower()
                if any(tok in blob for tok in verify.split() if len(tok) > 3):
                    return True, f"{e.kind} evidence matches verification contract"
        return False, "verification contract not matched by evidence"

    # No path and no verify field → narration may suffice (non-contract goal)
    return True, "no strict contract — evidence optional"


_CODE_DONE_RE = re.compile(
    r"\b(implement|fix|refactor|ship|merge|deploy|pytest|test suite|unit test|"
    r"write code|code change|patch|commit|pr\b|pull request)\b",
    re.I,
)


def goal_requires_evidence(goal: str, raw_goal: str, verification_field: str) -> bool:
    """True when narration alone cannot prove done (Judgment / Hermes-style)."""
    if (verification_field or "").strip():
        return True
    if extract_path_hints(goal, raw_goal):
        return True
    blob = f"{goal or ''} {raw_goal or ''}"
    # Code-ish goals always need durable tool evidence
    if _CODE_DONE_RE.search(blob):
        return True
    return False


# Strong whole-goal claims only — not "Step one complete" / partial progress.
_DONE_CLAIM_RE = re.compile(
    r"(?is)"
    r"("
    r"\bgoal\s+(achieved|complete|completed|done)\b"
    r"|\ball\s+(phases?\s+)?(done|complete|completed|finished)\b"
    r"|\b(task|mission)\s+(is\s+)?(done|complete|completed|finished)\b"
    r"|\bi(?:'m|\s+am)\s+done\b"
    r"|\bfinished\s+the\s+(goal|task|mission)\b"
    r"|(?:^|\n)\s*done\s*[.!]?\s*$"
    r")"
)


def claims_done_without_evidence(
    response: str,
    *,
    store: SessionStore | None,
    session_id: str | None,
) -> bool:
    """True if model claims the *whole* goal done but ledger has no success evidence."""
    text = response or ""
    if not _DONE_CLAIM_RE.search(text):
        return False
    # Intermediate step language is not a final claim
    if re.search(r"\bstep\s+\w+\s+complete", text, re.I):
        return False
    if not store or not session_id:
        return True
    events = VerificationStore(store).list_events(session_id, limit=30)
    return not any(e.status == "success" for e in events)
