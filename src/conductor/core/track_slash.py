"""Slash handlers for /track conductor commands."""

from __future__ import annotations

from conductor.core.runtime import ConductorRuntime
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore


def handle_track_slash(store: SessionStore, session_id: str, args: list[str]) -> str:
    tracks = TrackStore(store)
    conductor = ConductorRuntime(store)
    if not args:
        return tracks.chessboard_text(session_id)

    sub = args[0].lower()
    rest = args[1:]

    if sub in {"chessboard", "board", "map"}:
        return tracks.chessboard_text(session_id)

    if sub == "create":
        title = " ".join(rest).strip()
        if not title:
            return "Usage: /track create <title> [summary]"
        summary = ""
        if " --summary " in f" {title} ":
            parts = title.split(" --summary ", 1)
            title = parts[0].strip()
            summary = parts[1].strip()
        track = tracks.create_track(session_id, title=title, summary=summary or title)
        return f"Track created: {track.track_id}\nTitle: {track.title}"

    if sub == "fork":
        if not rest:
            return "Usage: /track fork <parent_id> [title]"
        parent_id = rest[0]
        title = " ".join(rest[1:]).strip() or None
        try:
            child = tracks.fork_track(session_id, parent_id, title=title)
        except ValueError as exc:
            return f"Error: {exc}"
        return (
            f"Forked track: {child.track_id[:8]}…\n"
            f"Parent: {parent_id[:8]}\n"
            f"Title: {child.title}"
        )

    if sub == "prune":
        if not rest:
            return "Usage: /track prune <track_id> [reason]"
        tid = rest[0]
        reason = " ".join(rest[1:]).strip()
        pruned = tracks.prune_track(session_id, tid, reason=reason)
        if not pruned:
            return f"Track not found: {tid}"
        return f"Pruned: {pruned.track_id[:8]}… ({pruned.title})"

    if sub == "resolve":
        if not rest:
            return "Usage: /track resolve <track_id> [reason]"
        tid = rest[0]
        reason = " ".join(rest[1:]).strip()
        resolved = tracks.resolve_track(session_id, tid, reason=reason)
        if not resolved:
            return f"Track not found: {tid}"
        return f"Resolved: {resolved.track_id[:8]}… ({resolved.title})"

    if sub == "update":
        if len(rest) < 2:
            return "Usage: /track update <track_id> <field=value ...>"
        track_id = rest[0]
        fields = rest[1:]
        kwargs: dict = {}
        for field in fields:
            if "=" not in field:
                continue
            key, val = field.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if key == "priority":
                kwargs["priority"] = float(val)
            elif key == "confidence":
                kwargs["confidence"] = float(val)
            elif key == "status":
                kwargs["status"] = val
            elif key == "title":
                kwargs["title"] = val
            elif key == "summary":
                kwargs["summary"] = val
            elif key == "notes":
                kwargs["conductor_notes"] = val
            elif key == "domain":
                kwargs["domain"] = val
        updated = tracks.update_track(session_id, track_id, **kwargs)
        if not updated:
            return f"Track not found: {track_id}"
        return (
            f"Track updated: {updated.title} "
            f"(p={updated.priority:.2f} c={updated.confidence:.2f})"
        )

    if sub == "list":
        return conductor.format_json(
            [t.model_dump(mode="json") for t in tracks.list_tracks(session_id)]
        )

    if sub == "view":
        if not rest:
            return "Usage: /track view <track_id>"
        track = tracks.get_track(session_id, rest[0])
        if not track:
            return f"Track not found: {rest[0]}"
        return conductor.format_json(track.model_dump(mode="json"))

    return (
        "Usage: /track [chessboard|create|fork|prune|resolve|update|list|view]\n"
        "  /track                  — chessboard view\n"
        "  /track chessboard\n"
        "  /track create <title>\n"
        "  /track fork <id> [title]\n"
        "  /track prune <id> [reason]\n"
        "  /track resolve <id>\n"
        "  /track update <id> priority=0.9 confidence=0.6\n"
        "  /track list | view <id>"
    )
