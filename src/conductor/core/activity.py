"""Crucible / Remnant activity snapshot for the TUI right rail."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from conductor.crucible.models import CloneIdentity, WorkspaceConcept, WorkspaceEvent


@dataclass(frozen=True)
class SlotSummary:
    label: str
    confidence: float
    salience: float
    clone_id: str | None
    emotion: str


@dataclass(frozen=True)
class CloneHeartbeat:
    clone_id: str
    birth_moment_label: str
    status: str
    snapshot_summary: str


@dataclass(frozen=True)
class EventSummary:
    operation: str
    actor: str | None
    label: str | None
    generation: int


@dataclass
class ActivitySnapshot:
    crucible_state: str = "idle"
    objective: str = ""
    generation: int = 0
    slot_count: int = 0
    capacity: int = 32
    slots: list[SlotSummary] = field(default_factory=list)
    clones: list[CloneHeartbeat] = field(default_factory=list)
    recent_events: list[EventSummary] = field(default_factory=list)
    promoted_last: list[str] = field(default_factory=list)
    live: bool = False


def slot_summary(concept: WorkspaceConcept) -> SlotSummary:
    return SlotSummary(
        label=concept.label,
        confidence=concept.confidence,
        salience=concept.salience,
        clone_id=concept.source_clone_id,
        emotion=concept.valence.primary,
    )


def slot_from_dict(raw: dict[str, Any]) -> SlotSummary:
    valence = raw.get("valence") or {}
    return SlotSummary(
        label=str(raw.get("label") or ""),
        confidence=float(raw.get("confidence") or 0.0),
        salience=float(raw.get("salience") or 0.0),
        clone_id=raw.get("source_clone_id"),
        emotion=str(valence.get("primary") or "neutral"),
    )


def clone_heartbeat(identity: CloneIdentity) -> CloneHeartbeat:
    return CloneHeartbeat(
        clone_id=identity.clone_id,
        birth_moment_label=identity.birth_moment_label,
        status=identity.status.value,
        snapshot_summary=identity.snapshot_summary,
    )


def event_summary(event: WorkspaceEvent) -> EventSummary:
    label = event.concept.label if event.concept else None
    if not label and event.evicted_labels:
        label = event.evicted_labels[0]
    return EventSummary(
        operation=event.operation.value,
        actor=event.actor_clone_id,
        label=label,
        generation=event.generation_after,
    )


def format_activity_rail(snapshot: ActivitySnapshot, *, width: int = 28) -> str:
    """Compact right-rail text (plain string for tests and overlay builders)."""
    lines: list[str] = []
    live_tag = "live" if snapshot.live else "cached"
    lines.append(f"Crucible · {snapshot.crucible_state} ({live_tag})")
    if snapshot.objective:
        lines.append(_truncate(snapshot.objective, width))
    lines.append(f"gen {snapshot.generation} · {snapshot.slot_count}/{snapshot.capacity} slots")

    if snapshot.clones:
        lines.append("")
        lines.append("Remnants")
        for clone in snapshot.clones[:4]:
            marker = "●" if clone.status == "active" else "○"
            lines.append(f"{marker} {clone.clone_id}")
            if clone.birth_moment_label:
                lines.append(f"  {_truncate(clone.birth_moment_label, width - 2)}")

    if snapshot.slots:
        lines.append("")
        lines.append("Workspace")
        for slot in snapshot.slots[:6]:
            conf = int(slot.confidence * 100)
            lines.append(f"· {_truncate(slot.label, width - 6)} {conf}%")
            if slot.clone_id:
                lines.append(f"  {slot.clone_id} · {slot.emotion}")

    if snapshot.recent_events:
        lines.append("")
        lines.append("Events")
        for ev in snapshot.recent_events[-4:]:
            who = ev.actor or "—"
            label = _truncate(ev.label or ev.operation, width - 8)
            lines.append(f"{ev.operation[:4]} {label}")
            lines.append(f"  {who} g{ev.generation}")

    if snapshot.promoted_last:
        lines.append("")
        lines.append("Distilled")
        for insight in snapshot.promoted_last[:3]:
            lines.append(f"✓ {_truncate(insight, width)}")

    if snapshot.crucible_state == "idle" and not snapshot.slots and not snapshot.clones:
        lines.append("")
        lines.append("No active workspace.")
        lines.append("/crucible start")

    return "\n".join(lines)


def build_remnant_overlay(snapshot: ActivitySnapshot) -> str:
    """Expanded remnant / crucible activity view (Hermes /agents analogue)."""
    lines = [
        "Remnants & Crucible Activity",
        "",
        f"State: {snapshot.crucible_state}"
        + (" (live)" if snapshot.live else " (last snapshot)"),
        f"Objective: {snapshot.objective or '(none)'}",
        f"Generation: {snapshot.generation} · Slots: {snapshot.slot_count}/{snapshot.capacity}",
        "",
    ]

    if snapshot.clones:
        lines.append("Registered clones / remnants")
        for clone in snapshot.clones:
            lines.append(f"  [{clone.status}] {clone.clone_id}")
            lines.append(f"    moment: {clone.birth_moment_label}")
            lines.append(f"    snapshot: {clone.snapshot_summary}")
        lines.append("")
    else:
        lines.append("No clones registered.")
        lines.append("")

    if snapshot.slots:
        lines.append("Workspace slots (by salience)")
        for slot in snapshot.slots:
            lines.append(
                f"  · {slot.label}  conf={slot.confidence:.2f} sal={slot.salience:.2f}"
            )
            if slot.clone_id:
                lines.append(f"    clone={slot.clone_id} emotion={slot.emotion}")
        lines.append("")

    if snapshot.recent_events:
        lines.append("Recent bus events")
        for ev in snapshot.recent_events:
            label = ev.label or "—"
            lines.append(
                f"  {ev.operation} g{ev.generation} actor={ev.actor or '—'} {label}"
            )
        lines.append("")

    if snapshot.promoted_last:
        lines.append("Last distillation")
        for insight in snapshot.promoted_last:
            lines.append(f"  ✓ {insight}")
        lines.append("")

    lines.extend(
        [
            "Ctrl+R toggle overlay · /crucible start|post|distill",
            "Esc close",
        ]
    )
    return "\n".join(lines)


def _truncate(text: str, width: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"
