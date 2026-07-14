"""Track System — graph-ready store with chessboard views."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from conductor.session.store import SessionStore
from conductor.tracks.models import EDGE_RELATIONS, TrackEdge, TrackRecord

TRACKS_META_KEY = "tracks"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TrackStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load_all(self, agent_session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(agent_session_id, TRACKS_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save_all(self, agent_session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(agent_session_id, TRACKS_META_KEY, data)

    def list_tracks(
        self,
        agent_session_id: str,
        *,
        status: str | None = None,
        include_pruned: bool = True,
    ) -> list[TrackRecord]:
        data = self._load_all(agent_session_id)
        items = data.get("items") or []
        tracks = [TrackRecord.model_validate(item) for item in items if isinstance(item, dict)]
        if status:
            tracks = [t for t in tracks if t.status == status]
        elif not include_pruned:
            tracks = [t for t in tracks if t.status not in {"pruned", "archived"}]
        return sorted(tracks, key=lambda t: (-t.priority, t.updated_at), reverse=False)

    def get_track(self, agent_session_id: str, track_id: str) -> TrackRecord | None:
        needle = track_id.strip()
        for track in self.list_tracks(agent_session_id):
            if track.track_id == needle or track.track_id.startswith(needle):
                return track
        return None

    def ensure_default_track(
        self,
        agent_session_id: str,
        *,
        objective: str = "",
    ) -> TrackRecord:
        tracks = self.list_tracks(agent_session_id, include_pruned=False)
        if tracks:
            return tracks[0]
        return self.create_track(
            agent_session_id,
            title=objective[:120] or "conductor-active-track",
            summary=objective or "Default conductor track for remnant spawn",
            priority=0.75,
        )

    def create_track(
        self,
        agent_session_id: str,
        *,
        title: str,
        summary: str = "",
        priority: float = 0.5,
        confidence: float = 0.7,
        domain: str = "orchestration",
        conductor_notes: str = "",
        parent_id: str | None = None,
        root_id: str | None = None,
    ) -> TrackRecord:
        track_id = str(uuid.uuid4())
        parent = None
        if parent_id:
            parent = self.get_track(agent_session_id, parent_id)
        resolved_root = root_id or (parent.root_id if parent else None) or (
            parent.track_id if parent else track_id
        )
        track = TrackRecord(
            track_id=track_id,
            title=title,
            summary=summary or title,
            priority=_clamp(priority),
            confidence=_clamp(confidence),
            domain=domain,
            branch_id=str(uuid.uuid4()),
            parent_id=parent.track_id if parent else parent_id,
            root_id=resolved_root,
            conductor_notes=conductor_notes,
        )
        data = self._load_all(agent_session_id)
        items: list[Any] = list(data.get("items") or [])
        items.append(track.model_dump(mode="json"))
        data["items"] = items
        self._save_all(agent_session_id, data)
        return track

    def update_track(
        self,
        agent_session_id: str,
        track_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        priority: float | None = None,
        confidence: float | None = None,
        status: str | None = None,
        domain: str | None = None,
        conductor_notes: str | None = None,
        emotional_valence: dict[str, Any] | None = None,
    ) -> TrackRecord | None:
        data = self._load_all(agent_session_id)
        items = data.get("items") or []
        updated: list[dict[str, Any]] = []
        found: TrackRecord | None = None
        target = self.get_track(agent_session_id, track_id)
        if not target:
            return None
        real_id = target.track_id
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if raw.get("track_id") != real_id:
                updated.append(raw)
                continue
            track = TrackRecord.model_validate(raw)
            if title is not None:
                track.title = title
            if summary is not None:
                track.summary = summary
            if priority is not None:
                track.priority = _clamp(priority)
            if confidence is not None:
                track.confidence = _clamp(confidence)
            if status is not None:
                track.status = status
            if domain is not None:
                track.domain = domain
            if conductor_notes is not None:
                track.conductor_notes = conductor_notes
            if emotional_valence is not None:
                track.emotional_valence = dict(emotional_valence)
            track.updated_at = _utcnow()
            found = track
            updated.append(track.model_dump(mode="json"))
        if found:
            data["items"] = updated
            self._save_all(agent_session_id, data)
        return found

    def fork_track(
        self,
        agent_session_id: str,
        parent_id: str,
        *,
        title: str | None = None,
        summary: str = "",
        priority: float | None = None,
    ) -> TrackRecord:
        parent = self.get_track(agent_session_id, parent_id)
        if not parent:
            raise ValueError(f"parent track not found: {parent_id}")
        child = self.create_track(
            agent_session_id,
            title=title or f"fork of {parent.title}",
            summary=summary or f"Forked from {parent.track_id[:8]}: {parent.summary}",
            priority=priority if priority is not None else parent.priority,
            confidence=max(0.3, parent.confidence - 0.05),
            domain=parent.domain,
            parent_id=parent.track_id,
            root_id=parent.root_id or parent.track_id,
            conductor_notes=f"forked from {parent.track_id}",
        )
        # Mark parent as forked lineage (still active unless pruned)
        self.update_track(
            agent_session_id,
            parent.track_id,
            conductor_notes=(parent.conductor_notes + f" | forked→{child.track_id[:8]}").strip(" |"),
        )
        # Graph edge: parent → child
        try:
            self.link_tracks(
                agent_session_id,
                parent.track_id,
                child.track_id,
                relation="forked_from",
                strength=0.9,
                reason=f"fork: {child.title[:80]}",
            )
        except ValueError:
            pass
        return child

    # --- Graph edges ---

    def list_edges(self, agent_session_id: str) -> list[TrackEdge]:
        data = self._load_all(agent_session_id)
        raw = data.get("edges") or []
        return [TrackEdge.model_validate(e) for e in raw if isinstance(e, dict)]

    def link_tracks(
        self,
        agent_session_id: str,
        from_track_id: str,
        to_track_id: str,
        *,
        relation: str = "leads_to",
        strength: float = 0.7,
        reason: str = "",
        discovered_in_crucible: str | None = None,
    ) -> TrackEdge:
        src = self.get_track(agent_session_id, from_track_id)
        dst = self.get_track(agent_session_id, to_track_id)
        if not src or not dst:
            raise ValueError("both from_track_id and to_track_id must exist")
        if src.track_id == dst.track_id:
            raise ValueError("cannot link a track to itself")
        rel = (relation or "leads_to").strip()
        if rel not in EDGE_RELATIONS:
            rel = "leads_to"
        # Dedupe same directed edge+relation
        for edge in self.list_edges(agent_session_id):
            if (
                edge.from_track_id == src.track_id
                and edge.to_track_id == dst.track_id
                and edge.relation == rel
            ):
                return edge
        edge = TrackEdge(
            edge_id=str(uuid.uuid4()),
            from_track_id=src.track_id,
            to_track_id=dst.track_id,
            relation=rel,
            strength=_clamp(strength),
            reason=reason,
            discovered_in_crucible=discovered_in_crucible,
        )
        data = self._load_all(agent_session_id)
        edges = list(data.get("edges") or [])
        edges.append(edge.model_dump(mode="json"))
        data["edges"] = edges
        self._save_all(agent_session_id, data)
        return edge

    def unlink_edge(self, agent_session_id: str, edge_id: str) -> bool:
        data = self._load_all(agent_session_id)
        edges = data.get("edges") or []
        needle = edge_id.strip()
        kept: list[Any] = []
        removed = False
        for raw in edges:
            if not isinstance(raw, dict):
                continue
            eid = str(raw.get("edge_id") or "")
            if eid == needle or eid.startswith(needle):
                removed = True
                continue
            kept.append(raw)
        if removed:
            data["edges"] = kept
            self._save_all(agent_session_id, data)
        return removed

    def neighbors(
        self,
        agent_session_id: str,
        track_id: str,
    ) -> dict[str, list[dict[str, Any]]]:
        track = self.get_track(agent_session_id, track_id)
        if not track:
            return {"outbound": [], "inbound": []}
        tid = track.track_id
        outbound: list[dict[str, Any]] = []
        inbound: list[dict[str, Any]] = []
        for edge in self.list_edges(agent_session_id):
            row = edge.model_dump(mode="json")
            if edge.from_track_id == tid:
                outbound.append(row)
            if edge.to_track_id == tid:
                inbound.append(row)
        return {"outbound": outbound, "inbound": inbound}

    def prune_track(
        self,
        agent_session_id: str,
        track_id: str,
        *,
        reason: str = "",
    ) -> TrackRecord | None:
        notes = reason or "pruned by conductor"
        return self.update_track(
            agent_session_id,
            track_id,
            status="pruned",
            conductor_notes=notes,
            priority=0.1,
        )

    def resolve_track(
        self,
        agent_session_id: str,
        track_id: str,
        *,
        reason: str = "",
    ) -> TrackRecord | None:
        return self.update_track(
            agent_session_id,
            track_id,
            status="resolved",
            confidence=0.95,
            conductor_notes=reason or "resolved",
        )

    def bump_version(self, agent_session_id: str, track_id: str) -> TrackRecord | None:
        track = self.get_track(agent_session_id, track_id)
        if not track:
            return None
        data = self._load_all(agent_session_id)
        items = data.get("items") or []
        updated: list[dict[str, Any]] = []
        found: TrackRecord | None = None
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if raw.get("track_id") == track.track_id:
                rec = TrackRecord.model_validate(raw)
                rec.version += 1
                rec.updated_at = _utcnow()
                found = rec
                updated.append(rec.model_dump(mode="json"))
            else:
                updated.append(raw)
        if found:
            data["items"] = updated
            self._save_all(agent_session_id, data)
        return found

    def chessboard(self, agent_session_id: str) -> dict[str, Any]:
        """Conductor chessboard view — active branches, risks, opportunities."""
        tracks = self.list_tracks(agent_session_id)
        active = [t for t in tracks if t.status == "active"]
        pruned = [t for t in tracks if t.status == "pruned"]
        resolved = [t for t in tracks if t.status == "resolved"]
        forked = [t for t in tracks if t.parent_id]

        def _row(t: TrackRecord) -> dict[str, Any]:
            return {
                "id": t.track_id,
                "short": t.track_id[:8],
                "title": t.title,
                "priority": t.priority,
                "confidence": t.confidence,
                "status": t.status,
                "domain": t.domain,
                "parent": (t.parent_id or "")[:8] or None,
                "root": (t.root_id or t.track_id)[:8],
                "version": t.version,
                "valence": t.emotional_valence,
                "notes": t.conductor_notes[:120],
            }

        # Risk: high priority + low confidence
        risks = [
            _row(t)
            for t in active
            if t.priority >= 0.6 and t.confidence < 0.55
        ]
        opportunities = [
            _row(t)
            for t in active
            if t.priority >= 0.7 and t.confidence >= 0.7
        ]
        # Roots with children
        by_root: dict[str, list[dict[str, Any]]] = {}
        for t in tracks:
            root = t.root_id or t.track_id
            by_root.setdefault(root, []).append(_row(t))

        edges = self.list_edges(agent_session_id)
        edge_rows = [
            {
                "id": e.edge_id[:8],
                "from": e.from_track_id[:8],
                "to": e.to_track_id[:8],
                "relation": e.relation,
                "strength": e.strength,
                "reason": (e.reason or "")[:80],
            }
            for e in edges[:40]
        ]
        return {
            "summary": {
                "total": len(tracks),
                "active": len(active),
                "pruned": len(pruned),
                "resolved": len(resolved),
                "forked_nodes": len(forked),
                "edges": len(edges),
                "risks": len(risks),
                "opportunities": len(opportunities),
            },
            "active": [_row(t) for t in active[:20]],
            "risks": risks[:10],
            "opportunities": opportunities[:10],
            "edges": edge_rows,
            "lineages": [
                {"root": k[:8], "nodes": v} for k, v in list(by_root.items())[:12]
            ],
        }

    def chessboard_text(self, agent_session_id: str) -> str:
        board = self.chessboard(agent_session_id)
        s = board["summary"]
        lines = [
            "◆ Track Chessboard",
            f"  Active {s['active']} · Resolved {s['resolved']} · Pruned {s['pruned']} · "
            f"Edges {s.get('edges', 0)} · Risks {s['risks']} · Opportunities {s['opportunities']}",
            "",
        ]
        if board["active"]:
            lines.append("Active tracks:")
            for row in board["active"][:12]:
                lines.append(
                    f"  • {row['short']}  p={row['priority']:.2f} c={row['confidence']:.2f}  "
                    f"[{row['status']}] {row['title']}"
                )
        if board["risks"]:
            lines.append("Risks (high priority / low confidence):")
            for row in board["risks"][:6]:
                lines.append(f"  ⚠ {row['short']}  {row['title']}")
        if board["opportunities"]:
            lines.append("Opportunities:")
            for row in board["opportunities"][:6]:
                lines.append(f"  ★ {row['short']}  {row['title']}")
        if board.get("edges"):
            lines.append("Edges:")
            for row in board["edges"][:8]:
                lines.append(
                    f"  → {row['from']} -[{row['relation']} {row['strength']:.2f}]→ {row['to']}"
                )
        if not board["active"] and not board["risks"]:
            lines.append("  (empty — /track create <title>)")
        return "\n".join(lines)
