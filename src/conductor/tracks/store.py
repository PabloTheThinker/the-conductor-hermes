"""Track System — graph-ready store with chessboard views."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from conductor.session.store import SessionStore
from conductor.tracks.models import EDGE_RELATIONS, TrackEdge, TrackRecord

TRACKS_META_KEY = "tracks"
# Soft cap — drop oldest pruned/archived first, then oldest low-priority actives.
TRACK_MAX_ITEMS = 200


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _updated_ts(track: TrackRecord) -> float:
    try:
        return track.updated_at.timestamp()
    except Exception:  # noqa: BLE001
        return 0.0


class TrackStore:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def _load_all(self, agent_session_id: str) -> dict[str, Any]:
        raw = self._store.get_meta(agent_session_id, TRACKS_META_KEY, default={})
        return raw if isinstance(raw, dict) else {}

    def _save_all(self, agent_session_id: str, data: dict[str, Any]) -> None:
        self._store.set_meta(agent_session_id, TRACKS_META_KEY, data)

    def _enforce_cap(self, data: dict[str, Any]) -> dict[str, Any]:
        """Keep graph under TRACK_MAX_ITEMS without discarding active high-priority work."""
        items = [i for i in (data.get("items") or []) if isinstance(i, dict)]
        if len(items) <= TRACK_MAX_ITEMS:
            return data
        records = [TrackRecord.model_validate(i) for i in items]
        # Prefer dropping pruned/archived first (oldest first), then lowest priority + oldest.
        def drop_key(t: TrackRecord) -> tuple[int, float, float]:
            tier = 0 if t.status in {"pruned", "archived"} else 1 if t.status == "resolved" else 2
            return (tier, t.priority, _updated_ts(t))

        keep_sorted = sorted(records, key=drop_key, reverse=True)
        kept = keep_sorted[:TRACK_MAX_ITEMS]
        keep_ids = {t.track_id for t in kept}
        data["items"] = [t.model_dump(mode="json") for t in kept]
        # Drop edges that reference removed nodes
        edges = [e for e in (data.get("edges") or []) if isinstance(e, dict)]
        data["edges"] = [
            e
            for e in edges
            if e.get("from_track_id") in keep_ids and e.get("to_track_id") in keep_ids
        ]
        return data

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
        # High priority first; among ties, newest updated first
        return sorted(tracks, key=lambda t: (-t.priority, -_updated_ts(t)))

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
        data = self._enforce_cap(data)
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
        # Graph edge: child -[forked_from]→ parent (child was forked from parent)
        try:
            self.link_tracks(
                agent_session_id,
                child.track_id,
                parent.track_id,
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
        by_id = {t.track_id: t for t in tracks}
        edges = self.list_edges(agent_session_id)

        def _row(t: TrackRecord, **extra: Any) -> dict[str, Any]:
            row = {
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
            row.update(extra)
            return row

        # Graph pressure: who is blocked / who conflicts
        blocked_ids: dict[str, list[str]] = {}  # target ← blockers
        conflict_pairs: list[tuple[str, str, float]] = []
        for e in edges:
            if e.relation == "blocks":
                blocked_ids.setdefault(e.to_track_id, []).append(e.from_track_id)
            elif e.relation == "conflicts_with":
                conflict_pairs.append((e.from_track_id, e.to_track_id, e.strength))

        # Risk: high priority + low confidence OR actively blocked
        risk_rows: list[dict[str, Any]] = []
        for t in active:
            reasons: list[str] = []
            if t.priority >= 0.6 and t.confidence < 0.55:
                reasons.append("high_priority_low_confidence")
            if t.track_id in blocked_ids:
                reasons.append("blocked")
            if not reasons:
                continue
            risk_rows.append(
                _row(
                    t,
                    risk_reasons=reasons,
                    blocked_by=[bid[:8] for bid in blocked_ids.get(t.track_id, [])[:4]],
                )
            )
        risk_rows.sort(key=lambda r: (-float(r["priority"]), float(r["confidence"])))

        opportunities = [
            _row(t)
            for t in active
            if t.priority >= 0.7 and t.confidence >= 0.7 and t.track_id not in blocked_ids
        ]
        opportunities.sort(key=lambda r: (-float(r["priority"]), -float(r["confidence"])))

        blocked = [
            _row(by_id[tid], blocked_by=[b[:8] for b in blockers[:4]])
            for tid, blockers in blocked_ids.items()
            if tid in by_id and by_id[tid].status == "active"
        ]
        conflicts = [
            {
                "a": a[:8],
                "b": b[:8],
                "strength": strength,
                "titles": [
                    (by_id[a].title if a in by_id else a[:8]),
                    (by_id[b].title if b in by_id else b[:8]),
                ],
            }
            for a, b, strength in conflict_pairs[:12]
        ]

        # Roots with children
        by_root: dict[str, list[dict[str, Any]]] = {}
        for t in tracks:
            root = t.root_id or t.track_id
            by_root.setdefault(root, []).append(_row(t))

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
                "risks": len(risk_rows),
                "opportunities": len(opportunities),
                "blocked": len(blocked),
                "conflicts": len(conflicts),
                "max_items": TRACK_MAX_ITEMS,
            },
            "active": [_row(t) for t in active[:20]],
            "risks": risk_rows[:10],
            "opportunities": opportunities[:10],
            "blocked": blocked[:10],
            "conflicts": conflicts[:10],
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
            f"Edges {s.get('edges', 0)} · Risks {s['risks']} · Blocked {s.get('blocked', 0)} · "
            f"Opportunities {s['opportunities']}",
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
            lines.append("Risks (priority/confidence + blocked):")
            for row in board["risks"][:6]:
                why = ",".join(row.get("risk_reasons") or []) or "risk"
                lines.append(f"  ⚠ {row['short']}  {row['title']}  ({why})")
        if board.get("blocked"):
            lines.append("Blocked:")
            for row in board["blocked"][:6]:
                by = ",".join(row.get("blocked_by") or []) or "?"
                lines.append(f"  ⛔ {row['short']}  {row['title']}  ← {by}")
        if board.get("conflicts"):
            lines.append("Conflicts:")
            for row in board["conflicts"][:6]:
                lines.append(
                    f"  ⚔ {row['a']} ↔ {row['b']}  s={row['strength']:.2f}  "
                    f"{row['titles'][0][:40]} / {row['titles'][1][:40]}"
                )
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
