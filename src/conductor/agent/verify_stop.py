"""Verify-on-stop — nudge when the model stops after code edits without verify evidence."""

from __future__ import annotations

from collections.abc import Iterable

from conductor.agent.verification import VerificationStore, is_verification_shell
from conductor.session.store import SessionStore

# Hermes + offline-brain write surfaces
CODE_WRITE_TOOLS = frozenset(
    {
        "write_file",
        "create_file",
        "edit_file",
        "search_replace",
        "str_replace",
        "apply_patch",
        "patch",
        "write_to_file",
    }
)
# Only nudge for source/code-like artifacts — not prose/path goals (*.txt, *.md, …)
_CODE_SUFFIXES = (
    ".py",
    ".pyi",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".vala",
    ".vue",
    ".svelte",
)
VERIFY_NUDGE = (
    "[Verify-on-stop] You edited code this turn but there is no fresh "
    "verification-style evidence (e.g. pytest / test command, or shell_verify).\n"
    "ONE nudge only — this is not an infinite loop and not 'stop everything'.\n"
    "Do one of:\n"
    "  A) Run a scoped verify command now (preferred), then you may stop if green\n"
    "  B) Explicitly state why verification is N/A for this change, then stop\n"
    "Do not claim done without A or B. After one verify attempt (or N/A), stop cleanly."
)


def path_looks_like_code(path: str) -> bool:
    p = (path or "").lower().strip()
    return any(p.endswith(sfx) for sfx in _CODE_SUFFIXES)


def turn_had_code_writes(
    tool_events: Iterable[str] | None,
    tool_names: Iterable[str] | None = None,
    *,
    written_paths: Iterable[str] | None = None,
) -> bool:
    names = list(tool_names or [])
    if not names and tool_events:
        for ev in tool_events:
            part = str(ev).split(":", 1)[0].strip()
            if part:
                names.append(part)
    if not any(n in CODE_WRITE_TOOLS for n in names):
        return False
    paths = [str(p) for p in (written_paths or []) if p]
    if not paths:
        # Unknown paths: do not force nudge (avoids false continues on path goals)
        return False
    return any(path_looks_like_code(p) for p in paths)


def has_fresh_verify_evidence(
    store: SessionStore | None,
    session_id: str | None,
    *,
    since_count: int = 8,
) -> bool:
    """True if recent successful evidence includes shell_verify or verification-like shell."""
    if not store or not session_id:
        return False
    events = VerificationStore(store).list_events(session_id, limit=since_count)
    for e in events:
        if e.status != "success":
            continue
        if e.kind == "shell_verify":
            return True
        if e.kind == "run_shell" and is_verification_shell(e.command or ""):
            return True
    return False


def should_nudge_verify_on_stop(
    *,
    tool_names_this_turn: list[str],
    store: SessionStore | None,
    session_id: str | None,
    already_nudged: bool,
    written_paths: list[str] | None = None,
) -> bool:
    """Issue at most one nudge per turn when code writes lack verify evidence."""
    if already_nudged:
        return False
    if not turn_had_code_writes(None, tool_names_this_turn, written_paths=written_paths):
        return False
    if has_fresh_verify_evidence(store, session_id):
        return False
    return True


def verify_nudge_message() -> str:
    return VERIFY_NUDGE
