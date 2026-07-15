"""Classify operational-field wounds for the integrity cascade."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Classification:
    kind: str
    severity: int
    path: str = ""
    recoverability: str = "unknown"  # high | medium | low | none


_MISSING_RE = re.compile(
    r"(no such file|not found|errno 2|does not exist|missing file|filenotfound)",
    re.I,
)
_PERM_RE = re.compile(r"(permission denied|errno 13|read-only|access is denied|eacces)", re.I)
_DENIED_RE = re.compile(r"(denied by path.?safety|shell denied|write denied)", re.I)
_CONN_RE = re.compile(r"(connection refused|timed out|timeout|rate.?limit|429|503|502)", re.I)


def extract_path_hint(text: str, arguments: dict[str, Any] | None = None) -> str:
    args = arguments or {}
    for key in ("path", "file", "target"):
        if args.get(key):
            return str(args[key])
    # crude path scrape
    m = re.search(r"(/[\w./_-]+\.[\w]+)", text or "")
    return m.group(1) if m else ""


def classify_tool_failure(
    tool: str,
    error: str,
    *,
    arguments: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> Classification:
    """Map a failed tool call to a scar kind + severity."""
    err = error or ""
    meta = meta or {}
    args = arguments or {}
    path = str(meta.get("path") or extract_path_hint(err, args) or args.get("path") or "")

    if _DENIED_RE.search(err) or meta.get("denied"):
        return Classification(kind="permission", severity=3, path=path, recoverability="none")

    if _PERM_RE.search(err):
        return Classification(kind="permission", severity=3, path=path, recoverability="low")

    tool_l = (tool or "").strip().lower()

    if tool_l in {"read_file", "search_files"} and (
        _MISSING_RE.search(err) or "Error reading" in err
    ):
        return Classification(kind="path_missing", severity=2, path=path, recoverability="high")

    if tool_l == "write_file" and _MISSING_RE.search(err):
        return Classification(kind="path_missing", severity=2, path=path, recoverability="medium")

    # Hermes hosts expose shell as terminal; Conductor agent uses run_shell.
    if tool_l in {"run_shell", "terminal", "bash", "shell"}:
        exit_code = meta.get("exit_code", meta.get("returncode"))
        if _MISSING_RE.search(err):
            return Classification(kind="path_missing", severity=2, path=path, recoverability="medium")
        if exit_code not in (None, 0) or err:
            return Classification(kind="shell", severity=2, path=path, recoverability="low")

    if _CONN_RE.search(err) or tool_l in {"provider", "chat"}:
        return Classification(kind="provider", severity=3, path="", recoverability="medium")

    if "unknown tool" in err.lower():
        return Classification(kind="tool_error", severity=2, recoverability="none")

    if err:
        return Classification(kind="tool_error", severity=2, path=path, recoverability="low")

    return Classification(kind="unknown", severity=1, path=path, recoverability="unknown")
