"""Conductor runtime — Crucible workspace orchestration bound to agent sessions."""

from __future__ import annotations

import json
from typing import Any

from conductor.core.activity import (
    ActivitySnapshot,
    clone_heartbeat,
    event_summary,
    slot_from_dict,
    slot_summary,
)
from conductor.core.remnant import RemnantLedger
from conductor.crucible import (
    CloneIdentity,
    CrucibleManager,
    CrucibleState,
    DistillationResult,
    WorkspaceConcept,
)
from conductor.crucible.models import EmotionalValence, WorkspaceState
from conductor.crucible.task_snapshot import (
    TaskScopedSnapshot,
    export_crucible_task_snapshot,
    snapshot_summary,
)
from conductor.governance.audit import AuditStore
from conductor.governance.models import AuditRecord, GateResult
from conductor.governance.policy import PolicyEngine
from conductor.memory.episodic import EpisodicStore
from conductor.session.store import SessionStore
from conductor.soul.identity import load_soul_identity
from conductor.tracks.store import TrackStore

CONDUCTOR_META_KEY = "conductor"

_CRUCIBLE: CrucibleManager | None = None


def get_crucible_manager() -> CrucibleManager:
    """Process-wide Crucible session registry (shared across conductor surfaces)."""
    global _CRUCIBLE
    if _CRUCIBLE is None:
        _CRUCIBLE = CrucibleManager()
    return _CRUCIBLE


def _default_conductor_meta() -> dict[str, Any]:
    return {
        "crucible_session_id": None,
        "objective": "",
        "state": CrucibleState.IDLE.value,
        "clone_count": 0,
        "workspace_generation": 0,
        "last_snapshot": None,
        "last_distillation": None,
        "remnant_session_id": None,
        "remnants": {},
        "remnant_snapshots": {},
        "remnant_heartbeats": [],
        "merged_remnant_insights": [],
        "remnant_merge_log": [],
        "crucible_task_snapshot": None,
        "crucible_clones": [],
        "crucible_promoted_insights": [],
    }


class ConductorRuntime:
    """Session-scoped conductor layer over the Crucible Global Workspace."""

    def __init__(self, store: SessionStore, crucible: CrucibleManager | None = None) -> None:
        self.store = store
        self._crucible = crucible or get_crucible_manager()
        self._remnants = RemnantLedger(store, CONDUCTOR_META_KEY)
        self._tracks = TrackStore(store)
        self._episodic = EpisodicStore(store)
        self._policy = PolicyEngine()
        self._audit = AuditStore(store)

    def evaluate_governance(self, action_type: str, context: dict[str, Any] | None = None) -> GateResult:
        return self._policy.evaluate(action_type, context)

    def record_governance_gate(
        self,
        agent_session_id: str,
        *,
        action_type: str,
        context: dict[str, Any],
        gate: GateResult,
    ) -> AuditRecord:
        return self._audit.record(agent_session_id, action_type=action_type, gate=gate)

    def _govern(
        self,
        agent_session_id: str,
        action_type: str,
        context: dict[str, Any] | None = None,
    ) -> GateResult:
        ctx = dict(context or {})
        gate = self.evaluate_governance(action_type, ctx)
        self.record_governance_gate(agent_session_id, action_type=action_type, context=ctx, gate=gate)
        if gate.blocked:
            raise ValueError(gate.summary)
        if gate.requires_escalation:
            raise ValueError(
                f"{gate.summary} — re-run with human_acknowledged=true after operator review"
            )
        return gate

    def list_audit_records(self, agent_session_id: str, *, limit: int = 20) -> list[AuditRecord]:
        return self._audit.list_records(agent_session_id, limit=limit)

    def soul_status(self) -> dict[str, Any]:
        identity = load_soul_identity()
        out: dict[str, Any] = {
            "path": str(identity.path),
            "tagline": identity.tagline,
            "content_hash": identity.content_hash,
            "integrity_ok": identity.integrity_ok,
            "has_ethics_directive": identity.has_ethics_directive,
            "word_count": identity.word_count,
            "runtime_overridden": identity.runtime_overridden,
            "runtime_path": str(identity.runtime_path) if identity.runtime_path else None,
        }
        try:
            from conductor.soul.resonance import resonate

            res = resonate(search_host=True)
            out["resonance"] = res.to_dict()
        except Exception:  # noqa: BLE001
            out["resonance"] = {"resonant": False}
        return out

    def load_meta(self, agent_session_id: str) -> dict[str, Any]:
        raw = self.store.get_meta(agent_session_id, CONDUCTOR_META_KEY)
        if not isinstance(raw, dict):
            return _default_conductor_meta()
        base = _default_conductor_meta()
        base.update(raw)
        return base

    def save_meta(self, agent_session_id: str, meta: dict[str, Any]) -> None:
        self.store.set_meta(agent_session_id, CONDUCTOR_META_KEY, meta)

    def _load_snapshot_into_workspace(
        self,
        crucible_session_id: str,
        task_snap: TaskScopedSnapshot,
        *,
        actor_clone_id: str = "prime",
    ) -> dict[str, int]:
        """Post episodic entries and track refs as real workspace slots (non-automatic)."""
        episodic_slots = 0
        track_slots = 0

        for raw in task_snap.memory_slice.get("episodic_entries") or []:
            if not isinstance(raw, dict):
                continue
            content = str(raw.get("content") or "").strip()[:120]
            if not content:
                continue
            valence_raw = raw.get("emotional_valence") or {}
            self._crucible.post_concept(
                crucible_session_id,
                WorkspaceConcept(
                    label=content,
                    confidence=0.72,
                    valence=EmotionalValence(
                        primary=str(valence_raw.get("primary") or "recalled"),
                        intensity=float(valence_raw.get("intensity") or 0.5),
                    ),
                    source_clone_id=actor_clone_id,
                    automatic=False,
                    metadata={"episodic_entry_id": raw.get("entry_id")},
                ),
                actor_clone_id=actor_clone_id,
            )
            episodic_slots += 1

        for raw in task_snap.track_refs or []:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()[:100]
            if not title:
                continue
            track_id = str(raw.get("track_id") or "")
            priority = float(raw.get("priority") or 0.5)
            self._crucible.post_concept(
                crucible_session_id,
                WorkspaceConcept(
                    label=f"track:{title}",
                    confidence=max(0.5, min(0.95, priority)),
                    valence=EmotionalValence(primary="focused", intensity=0.6),
                    source_clone_id=actor_clone_id,
                    track_refs=[track_id] if track_id else [],
                    automatic=False,
                    metadata={"track_id": track_id},
                ),
                actor_clone_id=actor_clone_id,
            )
            track_slots += 1

        return {"episodic_slots": episodic_slots, "track_slots": track_slots}

    def _persist_snapshot(self, agent_session_id: str, crucible_session_id: str) -> None:
        session = self._crucible.get_session(crucible_session_id)
        if session is None:
            return
        snapshot = session.bus.snapshot()
        meta = self.load_meta(agent_session_id)
        meta["workspace_generation"] = snapshot.generation
        meta["clone_count"] = len(session.clones)
        meta["state"] = session.state.value
        meta["last_snapshot"] = snapshot.model_dump(mode="json")
        meta["crucible_clones"] = [c.model_dump(mode="json") for c in session.clones]
        self.save_meta(agent_session_id, meta)
        try:
            from conductor.crucible.pocket import write_workspace_snapshot

            write_workspace_snapshot(crucible_session_id, snapshot.model_dump(mode="json"))
        except OSError:
            pass

    def _rehydrate_crucible(self, agent_session_id: str) -> bool:
        """Restore in-process Crucible state from persisted conductor meta."""
        meta = self.load_meta(agent_session_id)
        cid = meta.get("crucible_session_id")
        if not cid:
            return False
        state_raw = str(meta.get("state") or CrucibleState.IDLE.value)
        if state_raw == CrucibleState.IDLE.value:
            return False
        last_snap = meta.get("last_snapshot")
        if not isinstance(last_snap, dict):
            return False
        try:
            crucible_state = CrucibleState(state_raw)
        except ValueError:
            crucible_state = CrucibleState.RUNNING
        workspace = WorkspaceState.model_validate(last_snap)
        clones_raw = meta.get("crucible_clones") or []
        clones = [
            CloneIdentity.model_validate(item)
            for item in clones_raw
            if isinstance(item, dict)
        ]
        task_snap = meta.get("crucible_task_snapshot") or {}
        self._crucible.restore_session(
            str(cid),
            metadata={
                "agent_session_id": agent_session_id,
                "objective": meta.get("objective", ""),
                "task_snapshot": task_snap,
                "rehydrated": True,
            },
            workspace_snapshot=workspace,
            clones=clones,
            state=crucible_state,
        )
        return True

    def active_crucible_id(self, agent_session_id: str) -> str | None:
        meta = self.load_meta(agent_session_id)
        cid = meta.get("crucible_session_id")
        return str(cid) if cid else None

    def _require_active(self, agent_session_id: str) -> str:
        cid = self.active_crucible_id(agent_session_id)
        if not cid:
            raise ValueError("no active Crucible session — use start first")
        session = self._crucible.get_session(cid)
        if session is None:
            self._rehydrate_crucible(agent_session_id)
            session = self._crucible.get_session(cid)
        if session is None:
            raise ValueError(
                "Crucible session stale (process restarted) — use start to open a new workspace"
            )
        if session.state == CrucibleState.IDLE:
            raise ValueError("Crucible session ended — use start to open a new workspace")
        return cid

    def start_crucible(
        self,
        agent_session_id: str,
        objective: str = "",
        *,
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        self._govern(
            agent_session_id,
            "crucible_start",
            {"objective": objective, "human_acknowledged": human_acknowledged},
        )
        meta = self.load_meta(agent_session_id)
        existing = meta.get("crucible_session_id")
        if existing:
            session = self._crucible.get_session(str(existing))
            if session and session.state != CrucibleState.IDLE:
                return {
                    "crucible_session_id": existing,
                    "state": session.state.value,
                    "message": "Crucible already active for this conductor session",
                }

        task_snap = export_crucible_task_snapshot(
            self.store, agent_session_id, objective=objective, conductor_meta=meta
        )
        crucible = self._crucible.create_session(
            metadata={
                "agent_session_id": agent_session_id,
                "objective": objective,
                "task_snapshot": task_snap.model_dump(mode="json"),
            }
        )
        summary = snapshot_summary(task_snap)
        self._crucible.register_clone(
            crucible.session_id,
            CloneIdentity(
                clone_id="prime",
                birth_moment_label="pocket dimension open",
                snapshot_summary=summary,
                forked_from=None,
            ),
        )
        loaded = self._load_snapshot_into_workspace(
            crucible.session_id, task_snap, actor_clone_id="prime"
        )
        for label in task_snap.workspace_seed_labels:
            self._crucible.post_concept(
                crucible.session_id,
                WorkspaceConcept(
                    label=label,
                    confidence=0.75,
                    valence=EmotionalValence(primary="recalled", intensity=0.5),
                    source_clone_id="prime",
                    automatic=True,
                ),
                actor_clone_id="prime",
            )
        meta["crucible_session_id"] = crucible.session_id
        meta["objective"] = objective
        meta["crucible_task_snapshot"] = task_snap.model_dump(mode="json")
        session = self._crucible.get_session(crucible.session_id)
        meta["state"] = session.state.value if session else CrucibleState.RUNNING.value
        meta["clone_count"] = 1
        meta["workspace_generation"] = 0
        meta["last_snapshot"] = crucible.bus.snapshot().model_dump(mode="json")
        meta["crucible_clones"] = [
            c.model_dump(mode="json") for c in (session.clones if session else [])
        ]
        meta["last_distillation"] = None
        self.save_meta(agent_session_id, meta)
        pocket_dir = ""
        isolation: dict[str, Any] = {}
        try:
            from conductor.crucible.docker_isolation import isolate_pocket
            from conductor.crucible.pocket import (
                pocket_path,
                write_clone_note,
                write_manifest,
                write_workspace_snapshot,
            )

            write_manifest(
                crucible.session_id,
                objective=objective,
                agent_session_id=agent_session_id,
                extra={"task_snapshot_id": task_snap.snapshot_id},
            )
            write_clone_note(
                crucible.session_id,
                "prime",
                birth_moment_label="pocket dimension open",
                summary=summary,
                notes=["Prime conductor entered the pocket dimension."],
            )
            write_workspace_snapshot(
                crucible.session_id, crucible.bus.snapshot().model_dump(mode="json")
            )
            pocket_dir = str(pocket_path(crucible.session_id))
            iso = isolate_pocket(
                pocket_path(crucible.session_id),
                session_id=crucible.session_id,
                objective=objective,
            )
            isolation = iso.to_dict()
            meta["isolation"] = isolation
            self.save_meta(agent_session_id, meta)
        except OSError:
            pass
        from conductor.memory.episodic import record_lifecycle_event

        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="crucible_start",
            content=f"Pocket dimension opened: {objective or 'open simulation'}"
            + (f" [{isolation.get('mode', 'filesystem')}]" if isolation else ""),
            outcome="pending",
            emotion_primary="curious",
            emotion_intensity=0.6,
            context=crucible.session_id,
            extra_tags=["crucible", "pocket"],
        )
        return {
            "crucible_session_id": crucible.session_id,
            "state": crucible.state.value,
            "objective": objective,
            "capacity": crucible.bus.capacity,
            "task_snapshot_id": task_snap.snapshot_id,
            "snapshot_summary": summary,
            "episodic_loaded": len(task_snap.memory_slice.get("episodic_entries") or []),
            "workspace_slots_loaded": loaded,
            "pocket_path": pocket_dir,
            "isolation": isolation,
        }

    def fork_clone_from_snapshot(
        self,
        agent_session_id: str,
        *,
        clone_id: str,
        birth_moment_label: str,
        forked_from: str = "prime",
    ) -> dict[str, Any]:
        """Register a clone forked from the loaded Crucible task snapshot."""
        cid = self._require_active(agent_session_id)
        meta = self.load_meta(agent_session_id)
        raw_snap = meta.get("crucible_task_snapshot")
        if not isinstance(raw_snap, dict):
            raise ValueError("no crucible task snapshot — start crucible first")
        task_snap = TaskScopedSnapshot.model_validate(raw_snap)
        summary = snapshot_summary(task_snap)
        identity = CloneIdentity(
            clone_id=clone_id,
            birth_moment_label=birth_moment_label,
            snapshot_summary=summary,
            forked_from=forked_from,
        )
        self._crucible.register_clone(cid, identity)
        seeded = 0
        for label in task_snap.workspace_seed_labels[:4]:
            self.post_concept(
                agent_session_id,
                label=label,
                confidence=0.7,
                clone_id=clone_id,
                primary_emotion="forked",
                automatic=True,
            )
            seeded += 1
        self._persist_snapshot(agent_session_id, cid)
        meta = self.load_meta(agent_session_id)
        return {
            "clone_id": clone_id,
            "forked_from": forked_from,
            "snapshot_summary": summary,
            "episodic_in_snapshot": len(task_snap.memory_slice.get("episodic_entries") or []),
            "concepts_seeded": seeded,
            "clone_count": meta.get("clone_count", 0),
        }

    def register_clone(
        self,
        agent_session_id: str,
        *,
        clone_id: str,
        birth_moment_label: str,
        snapshot_summary: str,
        forked_from: str | None = None,
    ) -> dict[str, Any]:
        cid = self._require_active(agent_session_id)
        identity = CloneIdentity(
            clone_id=clone_id,
            birth_moment_label=birth_moment_label,
            snapshot_summary=snapshot_summary,
            forked_from=forked_from,
        )
        self._crucible.register_clone(cid, identity)
        self._persist_snapshot(agent_session_id, cid)
        try:
            from conductor.crucible.pocket import write_clone_note

            write_clone_note(
                cid,
                clone_id,
                birth_moment_label=birth_moment_label,
                summary=snapshot_summary,
                notes=[f"forked_from={forked_from}"] if forked_from else None,
            )
        except OSError:
            pass
        meta = self.load_meta(agent_session_id)
        return {
            "clone_id": clone_id,
            "crucible_session_id": cid,
            "clone_count": meta.get("clone_count", 0),
        }

    def post_concept(
        self,
        agent_session_id: str,
        *,
        label: str,
        confidence: float = 0.8,
        primary_emotion: str = "neutral",
        intensity: float = 0.5,
        automatic: bool = False,
        clone_id: str | None = None,
        track_refs: list[str] | None = None,
        reasoning_layer: int = 0,
    ) -> dict[str, Any]:
        cid = self._require_active(agent_session_id)
        concept = WorkspaceConcept(
            label=label,
            confidence=confidence,
            valence=EmotionalValence(primary=primary_emotion, intensity=intensity),
            automatic=automatic,
            source_clone_id=clone_id,
            track_refs=track_refs or [],
            reasoning_layer=reasoning_layer,
        )
        event = self._crucible.post_concept(cid, concept, actor_clone_id=clone_id)
        self._persist_snapshot(agent_session_id, cid)
        snapshot = self._crucible.get_session(cid).bus.snapshot()  # type: ignore[union-attr]
        return {
            "operation": event.operation.value,
            "label": label,
            "generation": snapshot.generation,
            "slot_labels": [c.label for c in snapshot.slots[:8]],
            "evicted": event.evicted_labels,
        }

    def replace_concept(
        self,
        agent_session_id: str,
        *,
        old_label: str,
        new_label: str,
        confidence: float = 0.85,
        primary_emotion: str = "neutral",
        intensity: float = 0.5,
        clone_id: str | None = None,
    ) -> dict[str, Any]:
        cid = self._require_active(agent_session_id)
        concept = WorkspaceConcept(
            label=new_label,
            confidence=confidence,
            valence=EmotionalValence(primary=primary_emotion, intensity=intensity),
            source_clone_id=clone_id,
        )
        event = self._crucible.replace_concept(cid, old_label, concept, actor_clone_id=clone_id)
        self._persist_snapshot(agent_session_id, cid)
        snapshot = self._crucible.get_session(cid).bus.snapshot()  # type: ignore[union-attr]
        return {
            "operation": event.operation.value,
            "old_label": old_label,
            "new_label": new_label,
            "generation": snapshot.generation,
            "slot_labels": [c.label for c in snapshot.slots[:8]],
        }

    def read_workspace(self, agent_session_id: str, clone_id: str = "prime") -> WorkspaceState:
        cid = self._require_active(agent_session_id)
        state = self._crucible.read_workspace(cid, clone_id)
        self._persist_snapshot(agent_session_id, cid)
        return state

    def distill(
        self,
        agent_session_id: str,
        *,
        human_acknowledged: bool = False,
    ) -> DistillationResult:
        meta_pre = self.load_meta(agent_session_id)
        self._govern(
            agent_session_id,
            "crucible_distill",
            {
                "objective": str(meta_pre.get("objective") or ""),
                "human_acknowledged": human_acknowledged,
            },
        )
        cid = self._require_active(agent_session_id)
        result = self._crucible.distill_session(cid)
        meta = self.load_meta(agent_session_id)
        meta["state"] = CrucibleState.IDLE.value
        meta["last_distillation"] = result.model_dump(mode="json")
        meta["crucible_session_id"] = None
        promoted: list[str] = list(meta.get("crucible_promoted_insights") or [])
        for insight in result.promoted_insights:
            if insight not in promoted:
                promoted.append(insight)
        meta["crucible_promoted_insights"] = promoted
        self.save_meta(agent_session_id, meta)
        try:
            from conductor.crucible.pocket import write_distill_result

            write_distill_result(cid, result.model_dump(mode="json"))
        except OSError:
            pass
        from conductor.memory.episodic import record_lifecycle_event

        for insight in result.promoted_insights:
            self._episodic.write(
                agent_session_id,
                content=f"[distilled] {insight}",
                context="crucible_distill",
                outcome="success",
                emotion_primary="satisfaction",
                emotion_intensity=0.65,
                tags=["crucible", "distill", "promoted"],
            )
            # Promote into track notes when track store available
            try:
                track = self._tracks.ensure_default_track(
                    agent_session_id, objective=str(meta_pre.get("objective") or insight)
                )
                self._tracks.update_track(
                    agent_session_id,
                    track.track_id,
                    conductor_notes=f"Crucible distill: {insight}",
                )
            except Exception:  # noqa: BLE001
                pass
        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="crucible_distill",
            content=f"Distilled {len(result.promoted_insights)} insights; "
            f"quarantined {len(result.quarantined)}",
            outcome="success" if result.promoted_insights else "info",
            emotion_primary="satisfaction",
            emotion_intensity=0.6,
            context=cid,
            extra_tags=["crucible", "distill"],
        )
        if result.promoted_insights:
            self.store.append_message(
                agent_session_id,
                "system",
                f"[Crucible distill] {result.promoted_insights}",
                extras={"crucible_distill": result.model_dump(mode="json")},
            )
        return result

    def run_noesis(
        self,
        agent_session_id: str,
        *,
        objective: str = "",
        max_clones: int = 3,
        auto_distill: bool = True,
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        """Run shallow RBMC Noesis cycle inside the pocket dimension."""
        from conductor.noesis.rbmc import RBMCConfig, run_rbmc

        self._govern(
            agent_session_id,
            "crucible_start",
            {
                "objective": objective or "Noesis RBMC",
                "human_acknowledged": human_acknowledged,
            },
        )
        result = run_rbmc(
            self,
            agent_session_id,
            objective=objective,
            config=RBMCConfig(max_clones=max_clones, auto_distill=auto_distill),
            human_acknowledged=human_acknowledged,
        )
        return result.to_dict()

    def run_max_effort(
        self,
        agent_session_id: str,
        *,
        decision: str,
        human_acknowledged: bool = False,
        auto_distill: bool = True,
    ) -> dict[str, Any]:
        """Four Voices Max Effort deliberation inside the pocket."""
        from conductor.noesis.max_effort import run_max_effort

        self._govern(
            agent_session_id,
            "crucible_start",
            {
                "objective": f"Max Effort: {decision[:80]}",
                "human_acknowledged": human_acknowledged,
            },
        )
        result = run_max_effort(
            self,
            agent_session_id,
            decision=decision,
            human_acknowledged=human_acknowledged,
            auto_distill=auto_distill,
        )
        return result.to_dict()

    def run_scheduled_noesis(
        self,
        agent_session_id: str,
        *,
        objective: str = "",
        force: bool = False,
        failure_signal: bool = False,
        max_clones: int = 3,
    ) -> dict[str, Any]:
        """Evaluate Noesis schedule triggers and run if due."""
        from conductor.noesis.scheduler import run_scheduled_noesis

        tracks = [t.model_dump(mode="json") for t in self._tracks.list_tracks(agent_session_id)]
        return run_scheduled_noesis(
            self,
            agent_session_id,
            objective=objective,
            force=force,
            track_signals=tracks,
            failure_signal=failure_signal,
            max_clones=max_clones,
        )

    def chessboard(self, agent_session_id: str) -> dict[str, Any]:
        return self._tracks.chessboard(agent_session_id)

    def chessboard_text(self, agent_session_id: str) -> str:
        return self._tracks.chessboard_text(agent_session_id)

    def spawn_remnant(
        self,
        agent_session_id: str,
        *,
        objective: str,
        strategy: str = "",
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        self._govern(
            agent_session_id,
            "remnant_spawn",
            {"objective": objective, "strategy": strategy, "human_acknowledged": human_acknowledged},
        )
        return self._remnants.spawn_remnant(
            agent_session_id,
            objective=objective,
            strategy=strategy,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def fanout_remnants(
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
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        self._govern(
            agent_session_id,
            "remnant_spawn",
            {
                "objective": "; ".join(objectives),
                "strategy": "fanout_parallel",
                "human_acknowledged": human_acknowledged,
            },
        )
        return self._remnants.fanout_parallel(
            agent_session_id,
            objectives=objectives,
            strategies=strategies,
            auto_heartbeat=auto_heartbeat,
            auto_work=auto_work,
            dispatch=dispatch,
            parent_goal=parent_goal,
            work_root=work_root,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def run_remnant_work(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
    ) -> dict[str, Any]:
        """(Re)generate structured work pack + heartbeat for one remnant."""
        return self._remnants.run_work_pack(
            agent_session_id,
            remnant_id=remnant_id,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def report_remnant_clone(
        self,
        agent_session_id: str,
        *,
        remnant_id: str,
        result: dict[str, Any],
        clone_handle: str = "",
    ) -> dict[str, Any]:
        """Host subagent reports shadow-clone completion."""
        payload = dict(result or {})
        payload.setdefault("reported_by_host", True)
        return self._remnants.report_clone_result(
            agent_session_id,
            remnant_id=remnant_id,
            result=payload,
            clone_handle=clone_handle,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def await_remnant_clones(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._remnants.await_clones(
            agent_session_id,
            remnant_ids=remnant_ids,
            load_meta=self.load_meta,
        )

    def ack_remnant_spawns(
        self,
        agent_session_id: str,
        *,
        handles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Parent confirms host subagents were spawned (anti-theater)."""
        return self._remnants.ack_clone_spawns(
            agent_session_id,
            handles=handles,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def clone_readiness(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._remnants.clone_readiness(
            agent_session_id,
            remnant_ids=remnant_ids,
            load_meta=self.load_meta,
        )

    def conductor_worker(
        self,
        agent_session_id: str,
        *,
        task: str,
        worker: str = "offline",
        context: dict[str, Any] | None = None,
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        """Offline/local echo|shell worker — not Hermes AI subagents."""
        from conductor.core.delegate import DelegationLedger

        self._govern(
            agent_session_id,
            "conductor_worker",
            {
                "description": task,
                "worker": worker,
                "human_acknowledged": human_acknowledged,
            },
        )
        return DelegationLedger(self.store).delegate(
            agent_session_id,
            task=task,
            worker=worker,
            context=context,
        )

    def delegate_task(
        self,
        agent_session_id: str,
        *,
        task: str,
        worker: str = "offline",
        context: dict[str, Any] | None = None,
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        """Deprecated alias for :meth:`conductor_worker` (avoids Hermes name clash)."""
        out = self.conductor_worker(
            agent_session_id,
            task=task,
            worker=worker,
            context=context,
            human_acknowledged=human_acknowledged,
        )
        if isinstance(out, dict):
            out = {
                **out,
                "deprecated_tool": "delegate_task",
                "use_instead": "conductor_worker",
                "note": (
                    "Conductor offline worker renamed to conductor_worker. "
                    "Hermes AI subagents use native host tool delegate_task."
                ),
            }
        return out

    def record_remnant_heartbeat(
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
    ) -> dict[str, Any]:
        return self._remnants.record_heartbeat(
            agent_session_id,
            remnant_id=remnant_id,
            current_subtask=current_subtask,
            progress_percent=progress_percent,
            key_decisions=key_decisions,
            new_insights=new_insights,
            emotion_primary=emotion_primary,
            emotion_intensity=emotion_intensity,
            blocking_issues=blocking_issues,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def list_remnants(self, agent_session_id: str, *, active_only: bool = False) -> list[dict[str, Any]]:
        records = self._remnants.list_remnants(
            agent_session_id, active_only=active_only, load_meta=self.load_meta
        )
        return [r.model_dump(mode="json") for r in records]

    def merge_remnants_tier1(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        human_acknowledged: bool = False,
        force: bool = False,
        accept_theater: bool = False,
    ) -> dict[str, Any]:
        self._govern(
            agent_session_id,
            "remnant_merge",
            {"description": "tier1 merge", "human_acknowledged": human_acknowledged},
        )
        return self._remnants.merge_tier1(
            agent_session_id,
            remnant_ids=remnant_ids,
            force=force,
            accept_theater=accept_theater,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def spawn_compliance(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Theater / host-spawn compliance snapshot."""
        return self._remnants.spawn_compliance(
            agent_session_id,
            load_meta=self.load_meta,
            remnant_ids=remnant_ids,
        )

    def merge_remnants_reflective(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        human_acknowledged: bool = False,
    ) -> dict[str, Any]:
        """Tier-2 reflective merge for high-divergence remnants."""
        self._govern(
            agent_session_id,
            "remnant_merge",
            {"description": "tier2 reflective merge", "human_acknowledged": human_acknowledged},
        )
        return self._remnants.merge_tier2_reflective(
            agent_session_id,
            remnant_ids=remnant_ids,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def merge_remnants_deep(
        self,
        agent_session_id: str,
        *,
        remnant_ids: list[str] | None = None,
        objective: str = "",
        human_acknowledged: bool = False,
        run_rbmc: bool = True,
    ) -> dict[str, Any]:
        """Tier-3 deep merge: optional RBMC in Crucible, then fold evidence into merge."""
        self._govern(
            agent_session_id,
            "remnant_merge",
            {
                "description": "tier3 deep simulation merge",
                "human_acknowledged": human_acknowledged,
            },
        )
        rbmc_payload: dict[str, Any] = {}
        if run_rbmc:
            from conductor.noesis.rbmc import RBMCConfig, run_rbmc

            obj = objective.strip()
            if not obj:
                # Derive from active remnant snapshot objective if present
                remnants = self.list_remnants(agent_session_id, active_only=True)
                if remnants:
                    obj = str(remnants[0].get("task_objective") or remnants[0].get("objective") or "")
                if not obj:
                    obj = "deep merge stress-test"
            rbmc = run_rbmc(
                self,
                agent_session_id,
                objective=obj,
                config=RBMCConfig(max_clones=3, auto_distill=True),
                human_acknowledged=human_acknowledged,
            )
            rbmc_payload = rbmc.to_dict()
            # Promote compound insights onto track notes
            try:
                track = self._tracks.ensure_default_track(agent_session_id, objective=obj)
                self._tracks.update_track(
                    agent_session_id,
                    track.track_id,
                    conductor_notes=(
                        (track.conductor_notes + f" | deep_merge RBMC: {obj[:60]}").strip(" |")
                    ),
                )
            except Exception:  # noqa: BLE001
                pass
        return self._remnants.merge_tier3_deep(
            agent_session_id,
            remnant_ids=remnant_ids,
            rbmc_result=rbmc_payload,
            load_meta=self.load_meta,
            save_meta=self.save_meta,
        )

    def consolidate_memory(self, agent_session_id: str, *, limit: int = 40) -> dict[str, Any]:
        from conductor.memory.semantic import consolidate_episodic

        result = consolidate_episodic(self.store, agent_session_id, limit=limit)
        from conductor.memory.episodic import record_lifecycle_event

        record_lifecycle_event(
            self.store,
            agent_session_id,
            kind="semantic_consolidate",
            content=f"Consolidated {result.get('created', 0)} semantic notes from "
            f"{result.get('scanned', 0)} episodic events",
            outcome="success" if result.get("created") else "info",
            emotion_primary="focused",
            emotion_intensity=0.55,
            extra_tags=["semantic", "consolidate"],
        )
        return result

    def remnant_delegation_entries(self, agent_session_id: str) -> list[dict[str, Any]]:
        return self._remnants.delegation_entries(agent_session_id, load_meta=self.load_meta)

    def status(self, agent_session_id: str) -> dict[str, Any]:
        meta = self.load_meta(agent_session_id)
        cid = meta.get("crucible_session_id")
        live: dict[str, Any] | None = None
        if cid:
            session = self._crucible.get_session(str(cid))
            if session:
                snap = session.bus.snapshot()
                live = {
                    "state": session.state.value,
                    "generation": snap.generation,
                    "slot_count": len(snap.slots),
                    "top_labels": [c.label for c in snap.slots[:6]],
                    "clones": [c.clone_id for c in session.clones],
                }
        active_remnants = self.list_remnants(agent_session_id, active_only=True)
        tracks = [t.model_dump(mode="json") for t in self._tracks.list_tracks(agent_session_id)]
        episodic = [e.model_dump(mode="json") for e in self._episodic.recent_slice(agent_session_id, limit=5)]
        task_snap = meta.get("crucible_task_snapshot")
        return {
            "crucible_session_id": cid,
            "objective": meta.get("objective", ""),
            "state": meta.get("state", CrucibleState.IDLE.value),
            "clone_count": meta.get("clone_count", 0),
            "workspace_generation": meta.get("workspace_generation", 0),
            "live": live,
            "last_distillation": meta.get("last_distillation"),
            "remnant_session_id": meta.get("remnant_session_id"),
            "active_remnants": active_remnants,
            "active_remnant_count": len(active_remnants),
            "merged_remnant_insights": meta.get("merged_remnant_insights") or [],
            "crucible_promoted_insights": meta.get("crucible_promoted_insights") or [],
            "crucible_task_snapshot_id": (
                task_snap.get("snapshot_id") if isinstance(task_snap, dict) else None
            ),
            "tracks": tracks,
            "track_count": len(tracks),
            "chessboard_summary": self._tracks.chessboard(agent_session_id).get("summary"),
            "isolation": meta.get("isolation") or {},
            "recent_episodic": episodic,
            "episodic_count": len(self._episodic.list_entries(agent_session_id, limit=10_000)),
            "soul": self.soul_status(),
            "governance_audit_count": len(self.list_audit_records(agent_session_id, limit=10_000)),
            "recent_governance_audits": [
                r.model_dump(mode="json") for r in self.list_audit_records(agent_session_id, limit=3)
            ],
        }

    def activity_snapshot(self, agent_session_id: str) -> ActivitySnapshot:
        meta = self.load_meta(agent_session_id)
        objective = str(meta.get("objective") or "")
        state = str(meta.get("state") or "idle")
        generation = int(meta.get("workspace_generation") or 0)
        promoted: list[str] = []
        dist = meta.get("last_distillation")
        if isinstance(dist, dict):
            promoted = list(dist.get("promoted_insights") or [])[:6]

        cid = meta.get("crucible_session_id")
        if cid:
            session = self._crucible.get_session(str(cid))
            if session:
                snap = session.bus.snapshot()
                trace = session.bus.trace()
                return ActivitySnapshot(
                    crucible_state=session.state.value,
                    objective=objective,
                    generation=snap.generation,
                    slot_count=len(snap.slots),
                    capacity=snap.capacity,
                    slots=[slot_summary(c) for c in snap.slots[:8]],
                    clones=[clone_heartbeat(c) for c in session.clones],
                    recent_events=[event_summary(e) for e in trace[-6:]],
                    promoted_last=promoted,
                    live=True,
                )

        last_snapshot = meta.get("last_snapshot")
        if isinstance(last_snapshot, dict):
            slots_raw = last_snapshot.get("slots") or []
            slots = [slot_from_dict(s) for s in slots_raw[:8]]
            return ActivitySnapshot(
                crucible_state=state,
                objective=objective,
                generation=int(last_snapshot.get("generation") or generation),
                slot_count=len(slots_raw),
                capacity=int(last_snapshot.get("capacity") or 32),
                slots=slots,
                clones=[],
                recent_events=[],
                promoted_last=promoted,
                live=False,
            )

        return ActivitySnapshot(
            crucible_state=state,
            objective=objective,
            generation=generation,
            promoted_last=promoted,
            live=False,
        )

    def status_text(self, agent_session_id: str) -> str:
        data = self.status(agent_session_id)
        lines = [
            f"Crucible: {data['state']}",
            f"Objective: {data['objective'] or '(none)'}",
        ]
        if data.get("crucible_session_id"):
            lines.append(f"Session: {str(data['crucible_session_id'])[:8]}…")
        live = data.get("live")
        if live:
            labels = ", ".join(live.get("top_labels") or []) or "(empty)"
            lines.append(f"Workspace gen {live.get('generation', 0)} — {labels}")
            clones = live.get("clones") or []
            if clones:
                lines.append(f"Clones: {', '.join(clones)}")
        dist = data.get("last_distillation")
        if dist and isinstance(dist, dict):
            promoted = dist.get("promoted_insights") or []
            if promoted:
                lines.append(f"Last distill: {', '.join(promoted[:4])}")
        remnants = data.get("active_remnants") or []
        if remnants:
            lines.append(f"Remnants: {len(remnants)} active")
            for rem in remnants[:4]:
                if isinstance(rem, dict):
                    rid = str(rem.get("remnant_id", ""))[:8]
                    obj = str(rem.get("task_objective", ""))[:40]
                    lines.append(f"  • {rid}… {obj}")
        merged = data.get("merged_remnant_insights") or []
        if merged:
            lines.append(f"Merged insights: {', '.join(str(m) for m in merged[:3])}")
        promoted = data.get("crucible_promoted_insights") or []
        if promoted:
            lines.append(f"Crucible promoted: {', '.join(str(p) for p in promoted[:3])}")
        if data.get("track_count", 0):
            board = self._tracks.chessboard(agent_session_id)
            s = board.get("summary") or {}
            lines.append(
                f"Tracks: {data['track_count']} "
                f"(active={s.get('active', 0)} risks={s.get('risks', 0)} "
                f"opps={s.get('opportunities', 0)})"
            )
            for tr in (data.get("tracks") or [])[:3]:
                if isinstance(tr, dict):
                    lines.append(
                        f"  • {tr.get('title', '')} "
                        f"(p={tr.get('priority', 0):.2f} c={tr.get('confidence', 0):.2f})"
                    )
        isolation = data.get("isolation") or self.load_meta(agent_session_id).get("isolation")
        if isinstance(isolation, dict) and isolation.get("mode"):
            lines.append(f"Isolation: {isolation.get('mode')} ok={isolation.get('ok')}")
        if data.get("episodic_count", 0):
            lines.append(f"Episodic memory: {data['episodic_count']} entries")
        soul = data.get("soul") or {}
        if soul:
            integrity = "ok" if soul.get("integrity_ok") else "check"
            lines.append(f"SOUL: {soul.get('tagline', '')[:60]} ({integrity})")
        audit_count = data.get("governance_audit_count", 0)
        if audit_count:
            lines.append(f"Governance audits: {audit_count}")
        return "\n".join(lines)

    def format_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, default=str)
