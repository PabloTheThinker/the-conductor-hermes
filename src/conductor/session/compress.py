"""Session history compression — keep recent turns full, summarize older ones.

Pure helpers for testability under CONDUCTOR_PROVIDER=test (no LLM required).
"""

from __future__ import annotations

from typing import Any

DEFAULT_KEEP_RECENT = 24
DEFAULT_COMPRESS_AFTER = 40


def _role_label(role: str) -> str:
    return (role or "unknown").strip() or "unknown"


def summarize_message_block(messages: list[dict[str, Any]], *, max_chars: int = 1200) -> str:
    """Deterministic compact summary of older messages (no LLM)."""
    if not messages:
        return "(no earlier messages)"
    lines: list[str] = []
    tool_names: list[str] = []
    for m in messages:
        role = _role_label(str(m.get("role") or ""))
        content = m.get("content")
        if content is None:
            content = ""
        text = str(content).replace("\n", " ").strip()
        if len(text) > 160:
            text = text[:157] + "..."
        tcs = m.get("tool_calls")
        if tcs and isinstance(tcs, list):
            for tc in tcs:
                if isinstance(tc, dict):
                    fn = tc.get("function") or {}
                    name = fn.get("name") if isinstance(fn, dict) else None
                    if name:
                        tool_names.append(str(name))
        if text:
            lines.append(f"- [{role}] {text}")
    head = f"Compressed prior context ({len(messages)} messages"
    if tool_names:
        uniq = sorted(set(tool_names))[:12]
        head += f"; tools: {', '.join(uniq)}"
    head += "):\n"
    body = "\n".join(lines)
    out = head + body
    if len(out) > max_chars:
        out = out[: max_chars - 3] + "..."
    return out


def compress_messages_for_model(
    messages: list[dict[str, Any]],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    compress_after: int = DEFAULT_COMPRESS_AFTER,
) -> list[dict[str, Any]]:
    """If history exceeds compress_after, fold older non-system messages into one system note.

    Always preserves the first system message (if any) and the last keep_recent messages.
    """
    if not messages:
        return []
    keep_recent = max(4, int(keep_recent))
    compress_after = max(keep_recent + 2, int(compress_after))

    if len(messages) <= compress_after:
        return list(messages)

    system: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "system" and not rest and not system:
            system.append(m)
        else:
            rest.append(m)

    if len(rest) <= keep_recent:
        return system + rest

    older = rest[: -keep_recent]
    recent = rest[-keep_recent:]
    summary = summarize_message_block(older)
    compact = {
        "role": "system",
        "content": (
            "[Session compression] Older turns were folded to protect context budget.\n"
            + summary
        ),
    }
    return system + [compact] + recent
