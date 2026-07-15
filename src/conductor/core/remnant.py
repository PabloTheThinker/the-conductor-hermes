"""Remnant Protocol Phase 1 — snapshot, spawn, heartbeat, Tier 1 merge."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from conductor.core.merge import (
    apply_merge_to_remnants,
    tier1_fast_merge,
    tier2_reflective_merge,
    tier3_deep_merge,
)
from conductor.core.models import (
    EmotionalValence,
    MemorySlice,
    ProgressHeartbeat,
    RemnantRecord,
    RemnantSnapshot,
    RemnantStatus,
    TrackReference,
)
from conductor.core.clone_backend import dispatch_clones, resolve_dispatch_mode
from conductor.core.models import CloneStatus
from conductor.core.remnant_work import (
    SCAFFOLD_FIRST,
    SHARED_DECISION,
    build_work_pack,
    curate_insights,
    ensure_shared_decisions,
    filter_insights,
    host_playbook_from_packs,
    merge_host_playbook,
)
from conductor.memory.episodic import record_lifecycle_event
from conductor.memory.snapshot_export import export_task_scoped_slice
from conductor.session.store import SessionStore
from conductor.tracks.store import TrackStore

REMNANTS_META_KEY = "remnants"
REMNANT_SNAPSHOTS_KEY = "remnant_snapshots"
REMNANT_HEARTBEATS_KEY = "remnant_heartbeats"
MERGED_INSIGHTS_KEY = "merged_remnant_insights"
MERGE_LOG_KEY = "remnant_merge_log"
# Soft caps — keep session meta bounded under long-running fanouts
REMNANT_HEARTBEATS_MAX = 200
REMNANT_MERGE_LOG_MAX = 50
# Age (seconds) after which non-ready clones are flagged stale in readiness
REMNANT_STALE_WARNING_SECONDS = 3600


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _default_remnant_meta() -> dict[str, Any]:
    return {
        "remnant_session_id": None,
        "remnants": {},
        "remnant_snapshots": {},
        "remnant_heartbeats": [],
        "merged_remnant_insights": [],
        "remnant_merge_log": [],
    }


def resolve_remnant_id(remnants: dict[str, Any], token: str) -> str:
    """Resolve full remnant id from exact match or unique prefix (slash-friendly)."""
    needle = token.strip().rstrip("…").rstrip("...")
    if not needle:
        raise ValueError("remnant id required")
    if needle in remnants:
        return needle
    matches = [rid for rid in remnants if rid.startswith(needle)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous remnant id prefix: {needle}")
    raise ValueError(f"remnant not found: {needle}")


class RemnantLedger:
    """Durable remnant ledger bound to conductor session meta."""

    def __init__(self, store: SessionStore, conductor_meta_key: str) -> None:
        self.store = store
        self._meta_key = conductor_meta_key
        self._tracks = TrackStore(store)
        self._lock = threading.RLock()

    def _load_bundle(self, agent_session_id: str) -> dict[str, Any]:
        raw = self.store.get_meta(agent_session_id, self._meta_key, default={})
        base = _default_remnant_meta()
        if isinstance(raw, dict):
            for key in base:
                if key in raw:
                    base[key] = raw[key]
        return base

    def _save_bundle(self, agent_session_id: str, bundle: dict[str, Any], full_meta: dict[str, Any]) -> None:
        for key, value in bundle.items():
            full_meta[key] = value
        self.store.set_meta(agent_session_id, self._meta_key, full_meta)

    def _get_full_meta(self, agent_session_id: str, load_meta: Any) -> dict[str, Any]:
        return load_meta(agent_session_id)

    def create_snapshot(
        self,
        agent_session_id: str,
        *,
        objective: str,
        strategy: str = "",
        emotion_primary: str = "determined",
        emotion_intensity: float = 0.6,
        load_meta: Any,
        save_meta: Any,
    ) -> RemnantSnapshot:
        track = self._tracks.ensure_default_track(agent_session_id, objective=objective)
        memory_export = export_task_scoped_slice(
            self.store, agent_session_id, objective=objective
        )
        snapshot_id = str(uuid.uuid4())
        spawn_emotion = EmotionalValence(
            primary=emotion_primary,
            intensity=emotion_intensity,
        )
        if memory_export.get("emotional_valence_at_spawn"):
            try:
                spawn_emotion = EmotionalValence.model_validate(
                    memory_export["emotional_valence_at_spawn"]
                )
            except Exception:
                pass
        semantic_keys = list(memory_export.get("semantic_keys") or [])
        if strategy:
            semantic_keys.append(f"strategy:{strategy}")
        return RemnantSnapshot(
            snapshot_id=snapshot_id,
            parent_session_id=agent_session_id,
            task_objective=objective,
            relevant_tracks=[
                TrackReference(
                    track_id=track.track_id,
                    branch_id=track.branch_id,
                    version=track.version,
                    summary=track.summary or objective,
                )
            ],
            memory_slice=MemorySlice(
                episodic_ids=list(memory_export.get("episodic_ids") or []),
                emotional_valence_at_spawn=spawn_emotion,
                context_summary=str(memory_export.get("context_summary") or objective),
                semantic_keys=semantic_keys,
            ),
            governance_scope={"tier": "phase1_mvp"},
            tool_access_scope=["crucible_workspace", "conductor_status", "remnant_orchestrate"],
        )

    def spawn_remnant(
        self,
        agent_session_id: str,
        *,
        objective: str,
        strategy: str = "",
        auto_work: bool = True,
        work_index: int = 0,
        work_total: int = 1,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            if bundle.get("remnant_session_id") is None:
                bundle["remnant_session_id"] = str(uuid.uuid4())

            snapshot = self.create_snapshot(
                agent_session_id,
                objective=objective,
                strategy=strategy,
                load_meta=load_meta,
                save_meta=save_meta,
            )
            remnant_id = str(uuid.uuid4())
            track_ref = snapshot.relevant_tracks[0]
            pack: dict[str, Any] = {}
            if auto_work:
                pack = build_work_pack(
                    objective=objective,
                    strategy=strategy,
                    index=work_index,
                    total=max(1, work_total),
                )
            record = RemnantRecord(
                remnant_id=remnant_id,
                session_id=str(bundle["remnant_session_id"]),
                snapshot_id=snapshot.snapshot_id,
                status=RemnantStatus.RUNNING,
                strategy=strategy,
                task_objective=objective,
                forked_track_branch_id=track_ref.branch_id or track_ref.track_id,
                work_pack=pack,
                merge_insights=list(pack.get("insights") or []),
            )
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            remnants[remnant_id] = record.model_dump(mode="json")
            snapshots: dict[str, Any] = dict(bundle.get("remnant_snapshots") or {})
            snapshots[snapshot.snapshot_id] = snapshot.model_dump(mode="json")
            bundle["remnants"] = remnants
            bundle["remnant_snapshots"] = snapshots
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)
            record_lifecycle_event(
                self.store,
                agent_session_id,
                kind="remnant_spawn",
                content=f"Spawned remnant for: {objective[:200]}",
                outcome="pending",
                emotion_primary="determined",
                emotion_intensity=0.6,
                context=remnant_id,
                extra_tags=["remnant", f"strategy:{strategy or 'default'}"],
            )
            out: dict[str, Any] = {
                "remnant_id": remnant_id,
                "remnant_session_id": bundle["remnant_session_id"],
                "snapshot_id": snapshot.snapshot_id,
                "status": record.status.value,
                "track_id": track_ref.track_id,
                "track_branch_id": record.forked_track_branch_id,
                "objective": objective,
                "strategy": strategy,
                "work_pack": pack,
            }
            return out

    def run_work_pack(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """(Re)build structured work pack and heartbeat it onto an active remnant."""
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            resolved = resolve_remnant_id(remnants, remnant_id)
            raw = remnants.get(resolved)
            if not raw:
                raise ValueError(f"remnant not found: {remnant_id}")
            record = RemnantRecord.model_validate(raw)
            active = {RemnantStatus.RUNNING, RemnantStatus.SPAWNING, RemnantStatus.SYNCING}
            if record.status not in active:
                raise ValueError(
                    f"remnant {resolved} is not active (status={record.status.value})"
                )
            # Count active for total context
            total = sum(
                1
                for r in remnants.values()
                if isinstance(r, dict)
                and RemnantRecord.model_validate(r).status in active
            )
            index = 0
            for i, rid in enumerate(sorted(remnants.keys())):
                if rid == resolved:
                    index = i
                    break
            pack = build_work_pack(
                objective=record.task_objective,
                strategy=record.strategy,
                index=index,
                total=max(1, total),
            )
            record.work_pack = pack
            record.merge_insights = filter_insights(
                list(record.merge_insights) + list(pack.get("insights") or [])
            )
            remnants[resolved] = record.model_dump(mode="json")
            bundle["remnants"] = remnants
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)

        hb = self.record_heartbeat(
            agent_session_id,
            remnant_id=resolved,
            current_subtask=str(pack.get("host_instruction") or pack.get("steps", [""])[0]),
            progress_percent=float(pack.get("progress_percent") or 85.0),
            key_decisions=list(pack.get("key_decisions") or [SHARED_DECISION]),
            new_insights=list(pack.get("insights") or []),
            load_meta=load_meta,
            save_meta=save_meta,
        )
        return {"remnant_id": resolved, "work_pack": pack, "heartbeat": hb}

    def fanout_parallel(
        self,
        agent_session_id: str,
        *,
        objectives: list[str],
        strategies: list[str] | None = None,
        auto_heartbeat: bool = True,
        auto_work: bool = True,
        dispatch: str = "auto",
        parent_goal: str = "",
        work_root: str | None = None,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Spawn ≥2 Remnants as shadow clones (subagents) + work packs."""
        if len(objectives) < 2:
            raise ValueError("fanout_parallel requires at least two objectives")
        strategies = strategies or [""] * len(objectives)
        while len(strategies) < len(objectives):
            strategies.append("")

        total = len(objectives)
        mode = resolve_dispatch_mode(dispatch)
        spawned: list[dict[str, Any]] = []
        for i, (objective, strategy) in enumerate(zip(objectives, strategies, strict=False)):
            spawned.append(
                self.spawn_remnant(
                    agent_session_id,
                    objective=objective.strip(),
                    strategy=(strategy or "").strip(),
                    auto_work=auto_work,
                    work_index=i,
                    work_total=total,
                    load_meta=load_meta,
                    save_meta=save_meta,
                )
            )

        # Mark clones pending before dispatch
        for item in spawned:
            self._set_clone_fields(
                agent_session_id,
                remnant_id=str(item["remnant_id"]),
                clone_backend=mode,
                clone_status=CloneStatus.PENDING,
                load_meta=load_meta,
                save_meta=save_meta,
            )

        heartbeats: list[dict[str, Any]] = []
        packs: list[dict[str, Any]] = []
        for item in spawned:
            if item.get("work_pack"):
                packs.append(item["work_pack"])

        # Initial heartbeat from work pack (briefing)
        if auto_work or auto_heartbeat:
            for i, item in enumerate(spawned):
                pack = dict(item.get("work_pack") or {})
                # Do not seed heartbeats with pack-template insights (merge noise)
                seed_insights = filter_insights(list(pack.get("insights") or []))[:2]
                heartbeats.append(
                    self.record_heartbeat(
                        agent_session_id,
                        remnant_id=str(item["remnant_id"]),
                        current_subtask=str(
                            f"awaiting host spawn: {str(item.get('objective') or '')[:80]}"
                        ),
                        progress_percent=float(pack.get("progress_percent") or 15.0),
                        key_decisions=list(pack.get("key_decisions") or [SHARED_DECISION]),
                        new_insights=seed_insights,
                        load_meta=load_meta,
                        save_meta=save_meta,
                    )
                )

        # Shadow clone dispatch — local workers or host subagent contract
        clone_payloads = [
            {
                "remnant_id": s["remnant_id"],
                "objective": s.get("objective"),
                "strategy": s.get("strategy"),
                "work_pack": s.get("work_pack") or {},
            }
            for s in spawned
        ]
        dispatch_result = dispatch_clones(
            mode=mode,
            clones=clone_payloads,
            session_id=agent_session_id,
            parent_goal=parent_goal or "; ".join(objectives),
            work_root=work_root,
        )

        # Apply completed local clone results
        for result in dispatch_result.get("completed") or []:
            rid = str(result.get("remnant_id") or "")
            if not rid:
                continue
            self.report_clone_result(
                agent_session_id,
                remnant_id=rid,
                result=result,
                clone_handle=str(result.get("clone_handle") or f"local:{rid[:8]}"),
                load_meta=load_meta,
                save_meta=save_meta,
            )

        # Host-awaiting clones: store spawn_request
        for pending in dispatch_result.get("pending") or []:
            rid = str(pending.get("remnant_id") or "")
            if not rid:
                continue
            self._set_clone_fields(
                agent_session_id,
                remnant_id=rid,
                clone_backend=mode,
                clone_status=CloneStatus.AWAITING_HOST,
                spawn_request=dict(pending.get("spawn_request") or {}),
                load_meta=load_meta,
                save_meta=save_meta,
            )

        playbook = host_playbook_from_packs(packs) if packs else host_playbook_from_packs(
            [
                build_work_pack(objective=str(s.get("objective") or ""), index=i, total=total)
                for i, s in enumerate(spawned)
            ]
        )
        playbook["shadow_clones"] = {
            "dispatch_mode": dispatch_result.get("dispatch_mode"),
            "host": dispatch_result.get("host"),
            "metaphor": "Naruto shadow clone jutsu — parallel selves, one will, merge back",
        }

        readiness = self.clone_readiness(agent_session_id, load_meta=load_meta)

        out = {
            "count": len(spawned),
            "remnants": spawned,
            "heartbeats": heartbeats,
            "remnant_ids": [s["remnant_id"] for s in spawned],
            "work_packs": packs,
            "host_playbook": playbook,
            "shared_decision": SHARED_DECISION,
            "scaffold_first": SCAFFOLD_FIRST,
            "dispatch_mode": dispatch_result.get("dispatch_mode"),
            "host": dispatch_result.get("host"),
            "spawn_requests": dispatch_result.get("spawn_requests") or [],
            "tool_calls": dispatch_result.get("tool_calls") or [],
            "parent_checklist": dispatch_result.get("parent_checklist") or [],
            "execute_tool_calls_now": bool(
                dispatch_result.get("execute_tool_calls_now")
            ),
            "parent_must_spawn": bool(dispatch_result.get("parent_must_spawn")),
            "spawn_count": int(dispatch_result.get("spawn_count") or 0),
            "protocol": dispatch_result.get("protocol"),
            "hermes_batch": dispatch_result.get("hermes_batch"),
            "concurrency_note": dispatch_result.get("concurrency_note"),
            "anti_theater": dispatch_result.get("anti_theater"),
            "host_contract": dispatch_result.get("host_contract"),
            "mandatory_host_action": dispatch_result.get("mandatory_host_action"),
            "clone_readiness": readiness,
            "shadow_clone": True,
            "note": dispatch_result.get("note")
            or (
                "Shadow clones dispatched. Host mode: scaffold work_root if greenfield, "
                "execute tool_calls via spawn_subagent, then spawn_ack + report + merge. "
                "Local mode: clones already completed."
            ),
        }
        if out["parent_must_spawn"]:
            with self._lock:
                full_meta = self._get_full_meta(agent_session_id, load_meta)
                full_meta["host_spawn_required"] = True
                full_meta["host_spawn_count"] = out["spawn_count"]
                save_meta(agent_session_id, full_meta)
        return out

    def _set_clone_fields(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        clone_backend: str = "",
        clone_status: CloneStatus | None = None,
        spawn_request: dict[str, Any] | None = None,
        clone_handle: str | None = None,
        clone_result: dict[str, Any] | None = None,
        load_meta: Any,
        save_meta: Any,
    ) -> RemnantRecord:
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            resolved = resolve_remnant_id(remnants, remnant_id)
            raw = remnants.get(resolved)
            if not raw:
                raise ValueError(f"remnant not found: {remnant_id}")
            record = RemnantRecord.model_validate(raw)
            if clone_backend:
                record.clone_backend = clone_backend
            if clone_status is not None:
                record.clone_status = clone_status
            if spawn_request is not None:
                record.spawn_request = spawn_request
            if clone_handle is not None:
                record.clone_handle = clone_handle
            if clone_result is not None:
                record.clone_result = clone_result
            remnants[resolved] = record.model_dump(mode="json")
            bundle["remnants"] = remnants
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)
            return record

    def report_clone_result(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        result: dict[str, Any],
        clone_handle: str = "",
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Host or local worker reports shadow-clone completion (dispel → parent)."""
        res = dict(result or {})
        ok = bool(res.get("ok", True))
        insights = list(res.get("insights") or [])
        findings = list(res.get("findings") or [])
        for f in findings[:8]:
            line = f"[clone:finding] {f}" if not str(f).startswith("[") else str(f)
            if line not in insights:
                insights.append(line[:240])
        handle = (clone_handle or str(res.get("clone_handle") or "")).strip()
        # Anti-theater (1.18.6): host reports from awaiting_host need clone_handle
        import os

        strict = os.environ.get("CONDUCTOR_STRICT_SPAWN", "1").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        with self._lock:
            _bundle = self._load_bundle(agent_session_id)
            _rems = dict(_bundle.get("remnants") or {})
            try:
                _rid = resolve_remnant_id(_rems, remnant_id)
                _cur = RemnantRecord.model_validate(_rems[_rid])
            except Exception:
                _cur = None
            _full = self._get_full_meta(agent_session_id, load_meta)
            _host_req = bool(_full.get("host_spawn_required"))
        if (
            strict
            and res.get("reported_by_host")
            and not handle
            and _cur is not None
            and (
                _cur.clone_status == CloneStatus.AWAITING_HOST
                or (
                    _host_req
                    and (_cur.clone_backend or "") in {"host", "hybrid", "hermes"}
                )
            )
        ):
            raise ValueError(
                "report blocked — host clone has no clone_handle (orchestration theater). "
                "PARENT must SPAWN tool_calls first, then spawn_ack "
                "(or pass clone_handle on this report). "
                "Do NOT invent findings without a real subagent. "
                "Set CONDUCTOR_STRICT_SPAWN=0 only to bypass."
            )
        if strict and not handle and res.get("reported_by_host"):
            insights.append("[warn] report without clone_handle (spawn proof weak)")
            res["spawn_proof"] = False
            res["theater_risk"] = True
        else:
            res["spawn_proof"] = bool(handle) or not res.get("reported_by_host")
            res["theater_risk"] = False
        # Drop ritual/template noise; compress findings before heartbeat + merge
        insights = curate_insights(insights, limit=12)
        # Always pin SHARED_DECISION so Tier-1 divergence stays low (1.17)
        decisions = ensure_shared_decisions(list(res.get("key_decisions") or []))
        progress = float(res.get("progress_percent") or (100.0 if ok else 50.0))
        if not ok:
            status = CloneStatus.FAILED
        elif res.get("reported_by_host"):
            status = CloneStatus.REPORTED
        else:
            status = CloneStatus.COMPLETED

        record = self._set_clone_fields(
            agent_session_id,
            remnant_id=remnant_id,
            clone_status=status,
            clone_handle=handle,
            clone_result=res,
            load_meta=load_meta,
            save_meta=save_meta,
        )
        # Fold insights onto remnant
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            resolved = resolve_remnant_id(remnants, remnant_id)
            rec = RemnantRecord.model_validate(remnants[resolved])
            rec.merge_insights = curate_insights(
                list(rec.merge_insights) + insights, limit=16
            )
            remnants[resolved] = rec.model_dump(mode="json")
            bundle["remnants"] = remnants
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)

        hb = self.record_heartbeat(
            agent_session_id,
            remnant_id=remnant_id,
            current_subtask=str(
                res.get("host_instruction")
                or res.get("summary")
                or f"clone complete: {record.task_objective[:80]}"
            ),
            progress_percent=progress,
            key_decisions=decisions,
            new_insights=insights[:12],
            load_meta=load_meta,
            save_meta=save_meta,
        )
        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="remnant_clone_report",
            content=f"Shadow clone reported for: {record.task_objective[:160]}",
            outcome="success" if ok else "failure",
            emotion_primary="satisfaction" if ok else "tension",
            emotion_intensity=0.6,
            context=record.remnant_id,
            extra_tags=["remnant", "shadow_clone", record.clone_backend or "unknown"],
        )
        return {
            "remnant_id": record.remnant_id,
            "clone_status": status.value,
            "heartbeat": hb,
            "clone_result": res,
            "readiness": self.clone_readiness(agent_session_id, load_meta=load_meta),
        }

    def clone_readiness(
        self,
        agent_session_id: str,
        *,
        load_meta: Any,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Whether active clones are ready to merge (all completed/reported)."""
        active = self.list_remnants(agent_session_id, active_only=True, load_meta=load_meta)
        if remnant_ids:
            want = set(remnant_ids)
            active = [r for r in active if r.remnant_id in want or r.remnant_id[:8] in want]
        ready_states = {
            CloneStatus.COMPLETED,
            CloneStatus.REPORTED,
            CloneStatus.FAILED,
            CloneStatus.NONE,
        }
        # SPAWNED / AWAITING_HOST / RUNNING / PENDING = not merge-ready
        rows = []
        waiting = []
        stale: list[str] = []
        now = _utcnow()
        for r in active:
            st = r.clone_status
            is_ready = st in ready_states and st != CloneStatus.NONE
            # If never used clones (NONE) but has work_pack, treat as ready for merge
            if st == CloneStatus.NONE:
                is_ready = True
            age_s: float | None = None
            if r.spawned_at is not None:
                spawned = r.spawned_at
                if spawned.tzinfo is None:
                    spawned = spawned.replace(tzinfo=UTC)
                age_s = max(0.0, (now - spawned).total_seconds())
            is_stale = (
                not is_ready
                and age_s is not None
                and age_s >= REMNANT_STALE_WARNING_SECONDS
            )
            rows.append(
                {
                    "remnant_id": r.remnant_id,
                    "objective": r.task_objective,
                    "clone_status": st.value,
                    "clone_backend": r.clone_backend,
                    "clone_handle": r.clone_handle,
                    "ready": is_ready,
                    "has_result": bool(r.clone_result),
                    "age_seconds": int(age_s) if age_s is not None else None,
                    "stale": is_stale,
                }
            )
            if not is_ready:
                waiting.append(r.remnant_id)
            if is_stale:
                stale.append(r.remnant_id)
        # Spawn compliance attached for hosts that only poll readiness
        from conductor.core.spawn_compliance import assess_spawn_compliance

        full = self._get_full_meta(agent_session_id, load_meta)
        compliance = assess_spawn_compliance(
            active,
            host_spawn_required=bool(full.get("host_spawn_required")),
            host_spawn_count=int(full.get("host_spawn_count") or 0),
        )
        return {
            "ready": len(waiting) == 0 and len(rows) > 0,
            "total": len(rows),
            "waiting": waiting,
            "stale": stale,
            "stale_warning_seconds": REMNANT_STALE_WARNING_SECONDS,
            "clones": rows,
            "spawn_compliance": compliance,
            "theater_risk": bool(compliance.get("theater_risk")),
            "hint": (
                "terminate idle remnants or report/force-merge if clones stay awaiting_host "
                f">={REMNANT_STALE_WARNING_SECONDS}s"
                if stale
                else None
            ),
        }

    def spawn_compliance(
        self,
        agent_session_id: str,
        *,
        load_meta: Any,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Explicit theater check for hosts and self-loop study."""
        from conductor.core.spawn_compliance import assess_spawn_compliance

        active = self.list_remnants(agent_session_id, active_only=True, load_meta=load_meta)
        if remnant_ids:
            want = set(remnant_ids)
            active = [
                r
                for r in active
                if r.remnant_id in want or r.remnant_id[:8] in want
            ]
        full = self._get_full_meta(agent_session_id, load_meta)
        return assess_spawn_compliance(
            active,
            host_spawn_required=bool(full.get("host_spawn_required")),
            host_spawn_count=int(full.get("host_spawn_count") or 0),
        )

    def ack_clone_spawns(
        self,
        agent_session_id: str,
        *,
        handles: list[dict[str, Any]],
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Parent confirms host subagents were spawned (clone_handle per remnant)."""
        if not handles:
            raise ValueError("handles required: [{remnant_id, clone_handle}, …]")
        acked: list[dict[str, str]] = []
        for item in handles:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("remnant_id") or "").strip()
            handle = str(item.get("clone_handle") or item.get("handle") or "").strip()
            if not rid or not handle:
                continue
            self._set_clone_fields(
                agent_session_id,
                remnant_id=rid,
                clone_status=CloneStatus.SPAWNED,
                clone_handle=handle,
                load_meta=load_meta,
                save_meta=save_meta,
            )
            acked.append({"remnant_id": rid, "clone_handle": handle, "clone_status": "spawned"})
        if not acked:
            raise ValueError("no valid handles (need remnant_id + clone_handle each)")
        # Clear theater flag once enough handles exist
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            full_meta["host_spawn_acked"] = True
            full_meta["host_spawn_ack_count"] = int(
                full_meta.get("host_spawn_ack_count") or 0
            ) + len(acked)
            save_meta(agent_session_id, full_meta)
        readiness = self.clone_readiness(agent_session_id, load_meta=load_meta)
        compliance = self.spawn_compliance(agent_session_id, load_meta=load_meta)
        return {
            "action": "spawn_ack",
            "acked": acked,
            "count": len(acked),
            "clone_readiness": readiness,
            "spawn_compliance": compliance,
            "note": (
                "Host spawns acknowledged (status=spawned). "
                "When each child finishes: action=report, then action=merge."
            ),
        }

    def await_clones(
        self,
        agent_session_id: str,
        *,
        load_meta: Any,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Poll clone readiness (non-blocking snapshot for host loops)."""
        readiness = self.clone_readiness(
            agent_session_id, load_meta=load_meta, remnant_ids=remnant_ids
        )
        return {
            **readiness,
            "action": "await",
            "hint": (
                "If awaiting_host: SPAWN host tools from tool_calls/hermes_batch, "
                "then action=spawn_ack. If spawned: wait for children then action=report. "
                "If ready: action=merge."
            ),
        }

    def record_heartbeat(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        current_subtask: str = "",
        progress_percent: float = 0.0,
        key_decisions: list[str] | None = None,
        new_insights: list[str] | None = None,
        emotion_primary: str = "focused",
        emotion_intensity: float = 0.5,
        blocking_issues: list[str] | None = None,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            resolved_id = resolve_remnant_id(remnants, remnant_id)
            raw = remnants.get(resolved_id)
            if not raw:
                raise ValueError(f"remnant not found: {remnant_id}")
            record = RemnantRecord.model_validate(raw)
            if record.status not in {RemnantStatus.RUNNING, RemnantStatus.SPAWNING, RemnantStatus.SYNCING}:
                raise ValueError(f"remnant {remnant_id} is not active (status={record.status.value})")

            heartbeat = ProgressHeartbeat(
                heartbeat_id=str(uuid.uuid4()),
                remnant_id=resolved_id,
                current_subtask=current_subtask,
                progress_percent=progress_percent,
                key_decisions=key_decisions or [],
                new_insights=new_insights or [],
                emotional_valence_delta=EmotionalValence(
                    primary=emotion_primary,
                    intensity=emotion_intensity,
                ),
                blocking_issues=blocking_issues or [],
            )
            record.current_heartbeat = heartbeat
            record.status = RemnantStatus.RUNNING
            remnants[resolved_id] = record.model_dump(mode="json")
            heartbeats: list[Any] = list(bundle.get("remnant_heartbeats") or [])
            heartbeats.append(heartbeat.model_dump(mode="json"))
            if len(heartbeats) > REMNANT_HEARTBEATS_MAX:
                heartbeats = heartbeats[-REMNANT_HEARTBEATS_MAX:]
            bundle["remnants"] = remnants
            bundle["remnant_heartbeats"] = heartbeats
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)
            return {
                "remnant_id": resolved_id,
                "heartbeat_id": heartbeat.heartbeat_id,
                "progress_percent": progress_percent,
                "status": record.status.value,
                "insights_count": len(heartbeat.new_insights),
                "heartbeats_retained": len(heartbeats),
            }

    def list_remnants(
        self,
        agent_session_id: str,
        *,
        active_only: bool = False,
        load_meta: Any,
    ) -> list[RemnantRecord]:
        bundle = self._load_bundle(agent_session_id)
        remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
        out: list[RemnantRecord] = []
        active_statuses = {RemnantStatus.RUNNING, RemnantStatus.SPAWNING, RemnantStatus.SYNCING}
        for raw in remnants.values():
            if not isinstance(raw, dict):
                continue
            record = RemnantRecord.model_validate(raw)
            if active_only and record.status not in active_statuses:
                continue
            out.append(record)
        return sorted(out, key=lambda r: r.spawned_at)

    def terminate_remnant(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        reason: str = "",
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Mark a remnant TERMINATED (abort path; not merge)."""
        with self._lock:
            full_meta = self._get_full_meta(agent_session_id, load_meta)
            bundle = self._load_bundle(agent_session_id)
            remnants: dict[str, Any] = dict(bundle.get("remnants") or {})
            resolved_id = resolve_remnant_id(remnants, remnant_id)
            raw = remnants.get(resolved_id)
            if not raw:
                raise ValueError(f"remnant not found: {remnant_id}")
            record = RemnantRecord.model_validate(raw)
            prior_status = record.status.value
            prior_clone = record.clone_status.value
            if record.status in {RemnantStatus.MERGED, RemnantStatus.TERMINATED}:
                return {
                    "action": "terminate",
                    "remnant_id": resolved_id,
                    "status": record.status.value,
                    "clone_status": record.clone_status.value,
                    "already_closed": True,
                    "reason": reason or "",
                }
            record.status = RemnantStatus.TERMINATED
            if record.clone_status in {
                CloneStatus.AWAITING_HOST,
                CloneStatus.SPAWNED,
                CloneStatus.PENDING,
                CloneStatus.RUNNING,
            }:
                # Stop host wait loops without claiming a successful report
                record.clone_status = CloneStatus.FAILED
            remnants[resolved_id] = record.model_dump(mode="json")
            bundle["remnants"] = remnants
            self._save_bundle(agent_session_id, bundle, full_meta)
            save_meta(agent_session_id, full_meta)

        note = (reason or "operator terminate").strip()
        self.store.append_message(
            agent_session_id,
            "system",
            f"[Remnant terminate] {resolved_id[:8]}… {note}".strip(),
            extras={
                "remnant_terminate": {
                    "remnant_id": resolved_id,
                    "prior_status": prior_status,
                    "prior_clone_status": prior_clone,
                    "reason": note,
                }
            },
        )
        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="remnant_terminate",
            content=f"terminated {resolved_id[:8]} ({prior_status}→terminated): {note}"[:300],
            outcome="aborted",
            emotion_primary="tension",
            emotion_intensity=0.4,
            context=resolved_id,
            extra_tags=["remnant", "terminate"],
        )
        return {
            "action": "terminate",
            "remnant_id": resolved_id,
            "status": RemnantStatus.TERMINATED.value,
            "clone_status": record.clone_status.value,
            "prior_status": prior_status,
            "prior_clone_status": prior_clone,
            "already_closed": False,
            "reason": note,
        }

    @staticmethod
    def _active_remnant_statuses() -> set[RemnantStatus]:
        return {RemnantStatus.RUNNING, RemnantStatus.SPAWNING, RemnantStatus.SYNCING}

    def _select_merge_targets(
        self,
        remnants_map: dict[str, Any],
        *,
        remnant_ids: list[str] | None,
    ) -> list[RemnantRecord]:
        active_statuses = self._active_remnant_statuses()
        resolved_filter: set[str] | None = None
        if remnant_ids:
            resolved_filter = {resolve_remnant_id(remnants_map, token) for token in remnant_ids}

        targets: list[RemnantRecord] = []
        for rid, raw in remnants_map.items():
            if not isinstance(raw, dict):
                continue
            record = RemnantRecord.model_validate(raw)
            if resolved_filter is not None:
                if rid not in resolved_filter:
                    continue
            elif record.status not in active_statuses:
                continue
            targets.append(record)

        if not targets:
            raise ValueError(
                "no active remnants to merge — spawn first. "
                "Order: remnant_orchestrate action=fanout (or spawn) → "
                "PARENT host SPAWN (spawn_subagent / Hermes delegate_task) → "
                "action=spawn_ack → action=report each clone → action=merge. "
                "Merging without spawn is theater (no parallel work happened)."
            )
        return targets

    def _assert_merge_gates(
        self,
        agent_session_id: str,
        *,
        targets: list[RemnantRecord],
        full_meta: dict[str, Any],
        load_meta: Any,
        force: bool = False,
        accept_theater: bool = False,
    ) -> dict[str, Any]:
        """Shared Tier1/2/3 gates: clone readiness + host-spawn compliance."""
        readiness = self.clone_readiness(
            agent_session_id,
            load_meta=load_meta,
            remnant_ids=[t.remnant_id for t in targets],
        )
        if not readiness.get("ready") and not force:
            waiting = readiness.get("waiting") or []
            raise ValueError(
                "shadow clones not ready to merge — waiting on: "
                f"{', '.join(w[:8] for w in waiting)}. "
                "Do NOT stop the mission. Next: SPAWN host tools if still awaiting_host, "
                "then action=report with real findings (not pack chrome), then merge. "
                "force=true only if you accept incomplete clone evidence."
            )

        from conductor.core.spawn_compliance import (
            assess_spawn_compliance,
            merge_blocked_message,
        )

        host_req = bool(full_meta.get("host_spawn_required"))
        compliance = assess_spawn_compliance(
            targets,
            host_spawn_required=host_req,
            host_spawn_count=int(full_meta.get("host_spawn_count") or 0),
        )
        if host_req and compliance.get("theater_risk") and not (force and accept_theater):
            raise ValueError(merge_blocked_message(compliance))
        return {"readiness": readiness, "compliance": compliance}

    def _heartbeats_for_targets(
        self,
        bundle: dict[str, Any],
        targets: list[RemnantRecord],
    ) -> list[ProgressHeartbeat]:
        heartbeats_raw: list[Any] = list(bundle.get("remnant_heartbeats") or [])
        target_ids = {t.remnant_id for t in targets}
        heartbeats = [
            ProgressHeartbeat.model_validate(hb)
            for hb in heartbeats_raw
            if isinstance(hb, dict) and hb.get("remnant_id") in target_ids
        ]
        for record in targets:
            if record.current_heartbeat and record.current_heartbeat.heartbeat_id not in {
                h.heartbeat_id for h in heartbeats
            }:
                heartbeats.append(record.current_heartbeat)
        return heartbeats

    def merge_tier1(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        with self._lock:
            return self._merge_tier1_unlocked(
                agent_session_id,
                remnant_ids=remnant_ids,
                force=force,
                accept_theater=accept_theater,
                load_meta=load_meta,
                save_meta=save_meta,
            )

    def _merge_tier1_unlocked(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        full_meta = self._get_full_meta(agent_session_id, load_meta)
        bundle = self._load_bundle(agent_session_id)
        remnants_map: dict[str, Any] = dict(bundle.get("remnants") or {})
        targets = self._select_merge_targets(remnants_map, remnant_ids=remnant_ids)
        self._assert_merge_gates(
            agent_session_id,
            targets=targets,
            full_meta=full_meta,
            load_meta=load_meta,
            force=force,
            accept_theater=accept_theater,
        )
        heartbeats = self._heartbeats_for_targets(bundle, targets)

        track = self._tracks.ensure_default_track(agent_session_id)
        bumped = self._tracks.bump_version(agent_session_id, track.track_id) or track

        try:
            proposal, result = tier1_fast_merge(
                session_id=agent_session_id,
                remnants=targets,
                heartbeats=heartbeats,
                track_id=bumped.track_id,
                track_version=bumped.version,
            )
            tier_label = "Tier 1"
        except ValueError as exc:
            # Auto-escalate complementary high-divergence fanouts to reflective
            if "divergence" not in str(exc).lower():
                raise
            proposal, result = tier2_reflective_merge(
                session_id=agent_session_id,
                remnants=targets,
                heartbeats=heartbeats,
                track_id=bumped.track_id,
                track_version=bumped.version,
            )
            tier_label = "Tier 2 reflective (auto from Tier 1 divergence)"
        return self._finalize_merge(
            agent_session_id,
            remnants_map=remnants_map,
            targets=targets,
            proposal=proposal,
            result=result,
            bundle=bundle,
            full_meta=full_meta,
            save_meta=save_meta,
            tier_label=tier_label,
        )

    def merge_tier2_reflective(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Tier 2 reflective merge — handles high divergence offline."""
        with self._lock:
            return self._merge_tier2_unlocked(
                agent_session_id,
                remnant_ids=remnant_ids,
                force=force,
                accept_theater=accept_theater,
                load_meta=load_meta,
                save_meta=save_meta,
            )

    def _merge_tier2_unlocked(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        full_meta = self._get_full_meta(agent_session_id, load_meta)
        bundle = self._load_bundle(agent_session_id)
        remnants_map: dict[str, Any] = dict(bundle.get("remnants") or {})
        targets = self._select_merge_targets(remnants_map, remnant_ids=remnant_ids)
        self._assert_merge_gates(
            agent_session_id,
            targets=targets,
            full_meta=full_meta,
            load_meta=load_meta,
            force=force,
            accept_theater=accept_theater,
        )
        heartbeats = self._heartbeats_for_targets(bundle, targets)

        track = self._tracks.ensure_default_track(agent_session_id)
        bumped = self._tracks.bump_version(agent_session_id, track.track_id) or track

        proposal, result = tier2_reflective_merge(
            session_id=agent_session_id,
            remnants=targets,
            heartbeats=heartbeats,
            track_id=bumped.track_id,
            track_version=bumped.version,
        )
        return self._finalize_merge(
            agent_session_id,
            remnants_map=remnants_map,
            targets=targets,
            proposal=proposal,
            result=result,
            bundle=bundle,
            full_meta=full_meta,
            save_meta=save_meta,
            tier_label="Tier 2 reflective",
        )

    def merge_tier3_deep(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        rbmc_result: dict[str, Any] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        """Tier 3 deep merge — reflective + Crucible/RBMC evidence."""
        with self._lock:
            return self._merge_tier3_unlocked(
                agent_session_id,
                remnant_ids=remnant_ids,
                rbmc_result=rbmc_result,
                force=force,
                accept_theater=accept_theater,
                load_meta=load_meta,
                save_meta=save_meta,
            )

    def _merge_tier3_unlocked(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        rbmc_result: dict[str, Any] | None = None,
        force: bool = False,
        accept_theater: bool = False,
        load_meta: Any,
        save_meta: Any,
    ) -> dict[str, Any]:
        full_meta = self._get_full_meta(agent_session_id, load_meta)
        bundle = self._load_bundle(agent_session_id)
        remnants_map: dict[str, Any] = dict(bundle.get("remnants") or {})
        targets = self._select_merge_targets(remnants_map, remnant_ids=remnant_ids)
        self._assert_merge_gates(
            agent_session_id,
            targets=targets,
            full_meta=full_meta,
            load_meta=load_meta,
            force=force,
            accept_theater=accept_theater,
        )
        heartbeats = self._heartbeats_for_targets(bundle, targets)

        track = self._tracks.ensure_default_track(agent_session_id)
        bumped = self._tracks.bump_version(agent_session_id, track.track_id) or track

        proposal, result = tier3_deep_merge(
            session_id=agent_session_id,
            remnants=targets,
            heartbeats=heartbeats,
            track_id=bumped.track_id,
            track_version=bumped.version,
            rbmc_result=rbmc_result,
        )
        out = self._finalize_merge(
            agent_session_id,
            remnants_map=remnants_map,
            targets=targets,
            proposal=proposal,
            result=result,
            bundle=bundle,
            full_meta=full_meta,
            save_meta=save_meta,
            tier_label="Tier 3 deep_simulation",
        )
        out["rbmc"] = rbmc_result or {}
        return out

    def _finalize_merge(
        self,
        agent_session_id: str,
        *,
        remnants_map: dict[str, Any],
        targets: list[RemnantRecord],
        proposal: Any,
        result: Any,
        bundle: dict[str, Any],
        full_meta: dict[str, Any],
        save_meta: Any,
        tier_label: str,
    ) -> dict[str, Any]:
        merged_records = apply_merge_to_remnants(targets, result)
        for record in merged_records:
            remnants_map[record.remnant_id] = record.model_dump(mode="json")

        # Always curate — never keep dirty chrome when filter empties the list.
        # AgentDrive analog: high-signal only; content-near-dedup + score rank.
        from conductor.core.remnant_work import curate_insights
        from conductor.core.spawn_compliance import judgment_from_merge_insights

        raw_count = len(list(result.merged_insights or []))
        clean_insights = curate_insights(list(result.merged_insights or []))
        result.merged_insights = clean_insights
        proposal.next_actions = clean_insights[:5]
        judgment = judgment_from_merge_insights(clean_insights)

        # Durable session insight ledger also curated (not a chrome dump)
        prior = list(bundle.get("merged_remnant_insights") or [])
        merged_insights = curate_insights(prior + clean_insights)

        playbook = merge_host_playbook(targets, list(result.merged_insights))

        # Track hygiene: close the board when all remnants are inactive
        track_resolved = False
        track_resolve_status: str | None = None
        if result.success and result.new_track_id:
            active_status_values = {
                RemnantStatus.SPAWNING.value,
                RemnantStatus.RUNNING.value,
                RemnantStatus.SYNCING.value,
            }
            still_active = [
                rid
                for rid, raw in remnants_map.items()
                if isinstance(raw, dict)
                and str(raw.get("status") or "") in active_status_values
            ]
            if not still_active:
                resolved = self._tracks.resolve_track(
                    agent_session_id,
                    result.new_track_id,
                    reason=(
                        f"auto-resolved after {tier_label}: "
                        f"{len(merged_records)} remnant(s) merged, "
                        f"{len(clean_insights)} signal insight(s)"
                    ),
                )
                track_resolved = resolved is not None
                track_resolve_status = getattr(resolved, "status", None) if resolved else None

        merge_log: list[Any] = list(bundle.get("remnant_merge_log") or [])
        merge_log.append(
            {
                "proposal": proposal.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
                "host_playbook": playbook,
                "signal": {
                    "raw_count": raw_count,
                    "signal_count": len(clean_insights),
                    "chrome_dropped": max(0, raw_count - len(clean_insights)),
                    "track_resolved": track_resolved,
                },
            }
        )
        if len(merge_log) > REMNANT_MERGE_LOG_MAX:
            merge_log = merge_log[-REMNANT_MERGE_LOG_MAX:]

        bundle["remnants"] = remnants_map
        bundle["merged_remnant_insights"] = merged_insights
        bundle["remnant_merge_log"] = merge_log
        bundle["last_host_playbook"] = playbook
        self._save_bundle(agent_session_id, bundle, full_meta)
        save_meta(agent_session_id, full_meta)

        self.store.append_message(
            agent_session_id,
            "system",
            f"[Remnant merge {tier_label}] {result.merged_insights}",
            extras={
                "remnant_merge": result.model_dump(mode="json"),
                "tier": tier_label,
                "signal_count": len(clean_insights),
                "track_resolved": track_resolved,
            },
        )
        if "3" in tier_label or "deep" in tier_label.lower():
            tier_tag = "tier3"
        elif "2" in tier_label or "reflective" in tier_label.lower():
            tier_tag = "tier2"
        else:
            tier_tag = "tier1"
        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="remnant_merge",
            content=f"{tier_label} merge: {', '.join(result.merged_insights)[:300]}",
            outcome="success" if result.success else "failure",
            emotion_primary="satisfaction" if result.success else "tension",
            emotion_intensity=0.65,
            context=result.result_id,
            extra_tags=["remnant", "merge", tier_tag]
            + (["track_resolved"] if track_resolved else []),
        )

        return {
            "success": result.success,
            "proposal_id": proposal.proposal_id,
            "result_id": result.result_id,
            "merged_insights": result.merged_insights,
            "signal_count": len(clean_insights),
            "chrome_dropped": max(0, raw_count - len(clean_insights)),
            "host_playbook": playbook,
            "remnant_ids": [r.remnant_id for r in merged_records],
            "track_id": result.new_track_id,
            "track_version": result.new_track_version,
            "track_resolved": track_resolved,
            "track_status": track_resolve_status or ("resolved" if track_resolved else "active"),
            "divergence_score": proposal.divergence_score,
            "merge_log_entries": len(merge_log),
            "tier": tier_label,
            "governance_notes": getattr(result, "governance_notes", ""),
            "judgment": judgment,
            "done_proven": bool(judgment.get("done_proven")),
        }

    def get_snapshot(self, agent_session_id: str, snapshot_id: str, *, load_meta: Any) -> RemnantSnapshot | None:
        bundle = self._load_bundle(agent_session_id)
        snapshots: dict[str, Any] = dict(bundle.get("remnant_snapshots") or {})
        raw = snapshots.get(snapshot_id)
        if not isinstance(raw, dict):
            return None
        return RemnantSnapshot.model_validate(raw)

    def delegation_entries(self, agent_session_id: str, *, load_meta: Any) -> list[dict[str, Any]]:
        """Map active remnants to Hermes delegation /subagent shape."""
        import time

        now_ms = int(time.time() * 1000)
        items: list[dict[str, Any]] = []
        for idx, record in enumerate(self.list_remnants(agent_session_id, active_only=True, load_meta=load_meta)):
            hb = record.current_heartbeat
            progress = hb.progress_percent if hb else 0.0
            summary = hb.current_subtask if hb else record.task_objective
            items.append(
                {
                    "subagent_id": f"remnant:{record.remnant_id[:8]}",
                    "remnant_id": record.remnant_id,
                    "kind": "conductor_shadow_clone",
                    "task_index": idx,
                    "goal": record.task_objective,
                    "depth": 1,
                    "parent_id": "prime",
                    "status": record.status.value,
                    "clone_status": record.clone_status.value,
                    "clone_backend": record.clone_backend,
                    "spawn_request": record.spawn_request,
                    "summary": summary,
                    "strategy": record.strategy,
                    "progress_percent": progress,
                    "started_at": now_ms - 2000,
                    "duration_seconds": None,
                    "total_tools": len(hb.new_insights) if hb else 0,
                    "work_pack": record.work_pack,
                }
            )
        return items
