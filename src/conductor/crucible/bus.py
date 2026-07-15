"""WorkspaceBus — in-process Global Workspace controller."""

from __future__ import annotations

from datetime import UTC, datetime

from conductor.crucible.models import (
    CloneIdentity,
    WorkspaceConcept,
    WorkspaceEvent,
    WorkspaceOperation,
    WorkspaceState,
)


# Cap persisted audit trace so rehydrate stays bounded.
TRACE_MAX_EVENTS = 500


class WorkspaceBus:
    def __init__(self, session_id: str, capacity: int = 32) -> None:
        self.session_id = session_id
        self.capacity = capacity
        self._generation = 0
        self._slots: list[WorkspaceConcept] = []
        self._active_clone_ids: list[str] = []
        self._clones: list[CloneIdentity] = []
        self._trace: list[WorkspaceEvent] = []
        self._automatic_trace: list[WorkspaceConcept] = []

    def _append_trace(self, event: WorkspaceEvent) -> None:
        self._trace.append(event)
        if len(self._trace) > TRACE_MAX_EVENTS:
            self._trace = self._trace[-TRACE_MAX_EVENTS:]

    def register_clone(self, identity: CloneIdentity) -> WorkspaceEvent:
        """Register a clone; re-register of the same clone_id is a no-op event."""
        existing = next((c for c in self._clones if c.clone_id == identity.clone_id), None)
        if existing is not None:
            # Keep active list honest; do not duplicate clone identity records.
            if identity.clone_id not in self._active_clone_ids:
                self._active_clone_ids.append(identity.clone_id)
            event = WorkspaceEvent(
                session_id=self.session_id,
                operation=WorkspaceOperation.CLONE_REGISTER,
                actor_clone_id=identity.clone_id,
                generation_after=self._generation,
            )
            self._append_trace(event)
            return event
        if identity.clone_id not in self._active_clone_ids:
            self._active_clone_ids.append(identity.clone_id)
        self._clones.append(identity)
        self._generation += 1
        event = WorkspaceEvent(
            session_id=self.session_id,
            operation=WorkspaceOperation.CLONE_REGISTER,
            actor_clone_id=identity.clone_id,
            generation_after=self._generation,
        )
        self._append_trace(event)
        return event

    def post(
        self,
        concept: WorkspaceConcept,
        *,
        actor_clone_id: str | None = None,
    ) -> WorkspaceEvent:
        concept = concept.model_copy(deep=True)
        concept.salience = concept.compute_salience()

        if concept.automatic:
            self._automatic_trace.append(concept)
            self._generation += 1
            event = WorkspaceEvent(
                session_id=self.session_id,
                operation=WorkspaceOperation.POST,
                actor_clone_id=actor_clone_id,
                concept=concept,
                generation_after=self._generation,
            )
            self._append_trace(event)
            return event

        evicted_labels: list[str] = []
        normalized = concept.label.casefold()
        existing_idx = next(
            (i for i, slot in enumerate(self._slots) if slot.label.casefold() == normalized),
            None,
        )

        if existing_idx is not None:
            old = self._slots[existing_idx]
            if concept.salience >= old.salience:
                self._slots[existing_idx] = concept
            else:
                event = WorkspaceEvent(
                    session_id=self.session_id,
                    operation=WorkspaceOperation.POST,
                    actor_clone_id=actor_clone_id,
                    concept=concept,
                    generation_after=self._generation,
                )
                self._append_trace(event)
                return event
        else:
            while len(self._slots) >= self.capacity:
                lowest_idx = min(range(len(self._slots)), key=lambda i: self._slots[i].salience)
                evicted = self._slots.pop(lowest_idx)
                evicted_labels.append(evicted.label)
            self._slots.append(concept)

        self._slots.sort(key=lambda c: c.salience, reverse=True)
        self._generation += 1
        operation = WorkspaceOperation.REPLACE if existing_idx is not None else WorkspaceOperation.POST
        event = WorkspaceEvent(
            session_id=self.session_id,
            operation=operation,
            actor_clone_id=actor_clone_id,
            concept=concept,
            evicted_labels=evicted_labels,
            generation_after=self._generation,
        )
        self._append_trace(event)

        for label in evicted_labels:
            self._append_trace(
                WorkspaceEvent(
                    session_id=self.session_id,
                    operation=WorkspaceOperation.EVICT,
                    actor_clone_id=actor_clone_id,
                    concept=concept,
                    evicted_labels=[label],
                    generation_after=self._generation,
                )
            )
        return event

    def replace(
        self,
        old_label: str,
        new_concept: WorkspaceConcept,
        *,
        actor_clone_id: str | None = None,
    ) -> WorkspaceEvent:
        new_concept = new_concept.model_copy(deep=True)
        new_concept.salience = new_concept.compute_salience()
        normalized = old_label.casefold()
        existing_idx = next(
            (i for i, slot in enumerate(self._slots) if slot.label.casefold() == normalized),
            None,
        )

        if existing_idx is not None:
            self._slots[existing_idx] = new_concept
            self._slots.sort(key=lambda c: c.salience, reverse=True)
        else:
            while len(self._slots) >= self.capacity:
                lowest_idx = min(range(len(self._slots)), key=lambda i: self._slots[i].salience)
                self._slots.pop(lowest_idx)
            self._slots.append(new_concept)
            self._slots.sort(key=lambda c: c.salience, reverse=True)

        self._generation += 1
        event = WorkspaceEvent(
            session_id=self.session_id,
            operation=WorkspaceOperation.REPLACE,
            actor_clone_id=actor_clone_id,
            concept=new_concept,
            evicted_labels=[old_label] if existing_idx is not None else [],
            generation_after=self._generation,
        )
        self._append_trace(event)
        return event

    def read(self, clone_id: str) -> WorkspaceState:
        state = self.snapshot()
        event = WorkspaceEvent(
            session_id=self.session_id,
            operation=WorkspaceOperation.READ,
            actor_clone_id=clone_id,
            generation_after=self._generation,
        )
        self._append_trace(event)
        return state

    def restore_from_state(
        self,
        state: WorkspaceState,
        *,
        events: list[WorkspaceEvent] | None = None,
        clones: list[CloneIdentity] | None = None,
    ) -> None:
        """Rebuild in-memory slots (and optional audit trace) from persistence."""
        self.capacity = state.capacity
        self._generation = state.generation
        self._slots = [concept.model_copy(deep=True) for concept in state.slots]
        self._active_clone_ids = list(state.active_clone_ids)
        if clones is not None:
            self._clones = [c.model_copy(deep=True) for c in clones]
        if events is not None:
            self._trace = [e.model_copy(deep=True) for e in events[-TRACE_MAX_EVENTS:]]

    def snapshot(self) -> WorkspaceState:
        ordered = sorted(self._slots, key=lambda c: c.salience, reverse=True)
        return WorkspaceState(
            generation=self._generation,
            slots=ordered,
            capacity=self.capacity,
            active_clone_ids=list(self._active_clone_ids),
            captured_at=datetime.now(UTC),
        )

    def trace(self) -> list[WorkspaceEvent]:
        return list(self._trace)

    def automatic_concepts(self) -> list[WorkspaceConcept]:
        return list(self._automatic_trace)

    def clear(self) -> WorkspaceEvent:
        self._slots.clear()
        self._generation += 1
        event = WorkspaceEvent(
            session_id=self.session_id,
            operation=WorkspaceOperation.CLEAR,
            generation_after=self._generation,
        )
        self._append_trace(event)
        return event
