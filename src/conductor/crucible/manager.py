"""
CrucibleManager — Runtime skeleton for Conductor.'s The Crucible (Noesis engine).

Spins up, manages, and cleans ephemeral Crucible containers for deep
self-simulation, memory replay, and self-cloning.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from conductor.crucible.bus import WorkspaceBus
from conductor.crucible.distillation import DistillationEngine
from conductor.crucible.models import (
    CloneIdentity,
    DistillationResult,
    WorkspaceConcept,
    WorkspaceState,
)

logger = logging.getLogger(__name__)


class CrucibleState(str, Enum):
    IDLE = "idle"
    ACTIVATING = "activating"
    SPINNING_UP = "spinning_up"
    LOADING_SNAPSHOT = "loading_snapshot"
    RUNNING = "running"
    DISTILLING = "distilling"
    CLEANUP = "cleanup"


_VALID_TRANSITIONS = {
    CrucibleState.IDLE: {CrucibleState.ACTIVATING},
    CrucibleState.ACTIVATING: {
        CrucibleState.SPINNING_UP,
        CrucibleState.RUNNING,
        CrucibleState.CLEANUP,
        CrucibleState.IDLE,
    },
    CrucibleState.SPINNING_UP: {CrucibleState.LOADING_SNAPSHOT, CrucibleState.RUNNING, CrucibleState.CLEANUP},
    CrucibleState.LOADING_SNAPSHOT: {CrucibleState.RUNNING, CrucibleState.CLEANUP},
    CrucibleState.RUNNING: {CrucibleState.DISTILLING, CrucibleState.CLEANUP, CrucibleState.IDLE},
    CrucibleState.DISTILLING: {CrucibleState.CLEANUP, CrucibleState.IDLE},
    CrucibleState.CLEANUP: {CrucibleState.IDLE},
}


@dataclass
class CrucibleSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: CrucibleState = CrucibleState.IDLE
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    bus: WorkspaceBus = field(default_factory=lambda: WorkspaceBus(""))
    clones: list[CloneIdentity] = field(default_factory=list)
    distillation: DistillationResult | None = None


class CrucibleManager:
    """Lifecycle controller for ephemeral Crucible containers."""

    def __init__(self) -> None:
        self._sessions: dict[str, CrucibleSession] = {}
        self._distillation_engine = DistillationEngine()

    def create_session(self, metadata: dict[str, Any] | None = None) -> CrucibleSession:
        session_id = str(uuid.uuid4())
        bus = WorkspaceBus(session_id=session_id)
        session = CrucibleSession(
            session_id=session_id,
            state=CrucibleState.ACTIVATING,
            metadata=metadata or {},
            bus=bus,
        )
        self._sessions[session.session_id] = session
        logger.info("crucible session created", extra={"session_id": session.session_id})
        return session

    def get_session(self, session_id: str) -> CrucibleSession | None:
        return self._sessions.get(session_id)

    def restore_session(
        self,
        session_id: str,
        *,
        metadata: dict[str, Any],
        workspace_snapshot: WorkspaceState,
        clones: list[CloneIdentity] | None = None,
        state: CrucibleState = CrucibleState.RUNNING,
        events: list | None = None,
    ) -> CrucibleSession:
        """Rebuild an in-process session after process restart (from conductor meta)."""
        if state == CrucibleState.IDLE:
            raise ValueError("cannot rehydrate an IDLE crucible session")
        bus = WorkspaceBus(session_id=session_id, capacity=workspace_snapshot.capacity)
        clone_list = list(clones or [])
        bus.restore_from_state(workspace_snapshot, events=events, clones=clone_list)
        session = CrucibleSession(
            session_id=session_id,
            state=state,
            metadata=metadata,
            bus=bus,
            clones=clone_list,
        )
        self._sessions[session_id] = session
        logger.info("crucible session rehydrated", extra={"session_id": session_id})
        return session

    def list_sessions(self) -> list[CrucibleSession]:
        return list(self._sessions.values())

    def transition_state(self, session_id: str, new_state: CrucibleState) -> CrucibleSession:
        session = self._require_session(session_id)
        allowed = _VALID_TRANSITIONS.get(session.state, set())
        if new_state not in allowed:
            raise ValueError(
                f"invalid transition {session.state.value} -> {new_state.value} for session {session_id}"
            )
        session.state = new_state
        return session

    def register_clone(self, session_id: str, identity: CloneIdentity) -> CloneIdentity:
        session = self._require_session(session_id)
        session.bus.register_clone(identity)
        # Keep session.clones aligned with bus: one identity per clone_id.
        existing_idx = next(
            (i for i, c in enumerate(session.clones) if c.clone_id == identity.clone_id),
            None,
        )
        if existing_idx is None:
            session.clones.append(identity)
        else:
            session.clones[existing_idx] = identity
        if session.state == CrucibleState.ACTIVATING:
            session.state = CrucibleState.RUNNING
        return identity

    def post_concept(
        self,
        session_id: str,
        concept: WorkspaceConcept,
        actor_clone_id: str | None = None,
    ):
        session = self._require_session(session_id)
        if session.state not in {CrucibleState.RUNNING, CrucibleState.DISTILLING}:
            raise ValueError(f"post_concept not allowed in state {session.state.value}")
        return session.bus.post(concept, actor_clone_id=actor_clone_id)

    def replace_concept(
        self,
        session_id: str,
        old_label: str,
        new_concept: WorkspaceConcept,
        actor_clone_id: str | None = None,
    ):
        session = self._require_session(session_id)
        if session.state not in {CrucibleState.RUNNING, CrucibleState.DISTILLING}:
            raise ValueError(f"replace_concept not allowed in state {session.state.value}")
        return session.bus.replace(old_label, new_concept, actor_clone_id=actor_clone_id)

    def read_workspace(self, session_id: str, clone_id: str) -> WorkspaceState:
        session = self._require_session(session_id)
        return session.bus.read(clone_id)

    def distill_session(
        self,
        session_id: str,
        governance_scope: dict[str, Any] | None = None,
    ) -> DistillationResult:
        session = self._require_session(session_id)
        if session.state not in {CrucibleState.RUNNING, CrucibleState.DISTILLING}:
            raise ValueError(f"distill_session not allowed in state {session.state.value}")

        session.state = CrucibleState.DISTILLING
        snapshot = session.bus.snapshot()
        events = session.bus.trace()
        # After process restart without a stored audit trace, slots still carry
        # deliberate concepts — synthesize POST events so promotion still works.
        if not events and snapshot.slots:
            from conductor.crucible.models import WorkspaceEvent, WorkspaceOperation

            events = [
                WorkspaceEvent(
                    session_id=session_id,
                    operation=WorkspaceOperation.POST,
                    actor_clone_id=concept.source_clone_id,
                    concept=concept,
                    generation_after=snapshot.generation,
                )
                for concept in snapshot.slots
                if not concept.automatic
            ]
        result = self._distillation_engine.run(
            events,
            snapshot,
            governance_scope=governance_scope,
        )
        session.distillation = result
        session.metadata["distillation"] = result.model_dump()
        session.state = CrucibleState.CLEANUP
        session.state = CrucibleState.IDLE
        return result

    def _require_session(self, session_id: str) -> CrucibleSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown crucible session: {session_id}")
        return session
