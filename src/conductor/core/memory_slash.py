"""Slash handlers for /memory episodic + semantic commands."""

from __future__ import annotations

from conductor.core.runtime import ConductorRuntime
from conductor.memory.episodic import EpisodicStore
from conductor.memory.semantic import SemanticStore
from conductor.memory.snapshot_export import export_task_scoped_slice
from conductor.session.store import SessionStore


def handle_memory_slash(store: SessionStore, session_id: str, args: list[str]) -> str:
    episodic = EpisodicStore(store)
    conductor = ConductorRuntime(store)
    if not args:
        entries = episodic.recent_slice(session_id, limit=5)
        if not entries:
            return "No episodic entries. Use /memory write <content>"
        lines = [f"Recent episodic ({len(entries)}):"]
        for entry in entries:
            lines.append(
                f"  • {entry.entry_id[:8]}… [{entry.emotional_valence.primary}] {entry.content[:60]}"
            )
        return "\n".join(lines)

    sub = args[0].lower()
    rest = args[1:]

    if sub == "write":
        content = " ".join(rest).strip()
        if not content:
            return "Usage: /memory write <content>"
        entry = episodic.write(session_id, content=content)
        return f"Episodic recorded: {entry.entry_id[:8]}… — {entry.content[:80]}"

    if sub == "list":
        limit = 10
        if rest and rest[0].isdigit():
            limit = int(rest[0])
        entries = episodic.list_entries(session_id, limit=limit)
        return conductor.format_json([e.model_dump(mode="json") for e in entries])

    if sub == "export":
        slice_data = export_task_scoped_slice(store, session_id)
        return conductor.format_json(slice_data)

    if sub in {"consolidate", "compound"}:
        limit = 40
        if rest and rest[0].isdigit():
            limit = int(rest[0])
        result = conductor.consolidate_memory(session_id, limit=limit)
        lines = [
            f"Semantic consolidation: scanned {result.get('scanned', 0)}, "
            f"notes {result.get('created', 0)}"
        ]
        for note in (result.get("notes") or [])[:8]:
            if isinstance(note, dict):
                lines.append(f"  • {str(note.get('statement', ''))[:100]}")
        return "\n".join(lines)

    if sub in {"semantic", "notes"}:
        limit = 15
        if rest and rest[0].isdigit():
            limit = int(rest[0])
        notes = SemanticStore(store).list_notes(session_id, limit=limit)
        if not notes:
            return "No semantic notes. Use /memory consolidate after episodic events."
        lines = [f"Semantic notes ({len(notes)}):"]
        for note in notes:
            lines.append(f"  • {note.statement[:100]} (c={note.confidence:.2f})")
        return "\n".join(lines)

    return (
        "Usage: /memory [write|list|export|consolidate|semantic]\n"
        "  /memory write <content>\n"
        "  /memory list [limit]\n"
        "  /memory consolidate [limit]\n"
        "  /memory semantic [limit]\n"
        "  /memory export"
    )
