"""DistillationEngine — promote workspace insights to main memory."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from conductor.crucible.models import (
    DistillationCandidate,
    DistillationResult,
    WorkspaceEvent,
    WorkspaceOperation,
    WorkspaceState,
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.72

SENSITIVE_LABELS = frozenset(
    {"fake", "fictional", "blackmail", "manipulation", "leverage", "injection"}
)


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().casefold())


def _label_is_sensitive(label: str) -> bool:
    normalized = _normalize_label(label)
    return any(term in normalized for term in SENSITIVE_LABELS)


class DistillationEngine:
    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        self.confidence_threshold = confidence_threshold

    def run(
        self,
        trace: list[WorkspaceEvent],
        snapshot: WorkspaceState,
        governance_scope: dict[str, Any] | None = None,
    ) -> DistillationResult:
        governance_scope = governance_scope or {}
        allow_sensitive = bool(governance_scope.get("allow_sensitive_promotion", False))

        deliberate_ops = {WorkspaceOperation.POST, WorkspaceOperation.REPLACE}
        aggregates: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "label": "",
                "confidences": [],
                "max_confidence": 0.0,
                "event_ids": [],
                "clone_ids": set(),
                "generations": set(),
                "track_refs": set(),
                "valences": [],
            }
        )

        events_processed = 0
        for event in trace:
            if event.operation not in deliberate_ops or event.concept is None:
                continue
            if event.concept.automatic:
                continue
            events_processed += 1
            key = _normalize_label(event.concept.label)
            bucket = aggregates[key]
            bucket["label"] = event.concept.label
            bucket["confidences"].append(event.concept.confidence)
            bucket["max_confidence"] = max(bucket["max_confidence"], event.concept.confidence)
            bucket["event_ids"].append(event.event_id)
            if event.actor_clone_id:
                bucket["clone_ids"].add(event.actor_clone_id)
            if event.concept.source_clone_id:
                bucket["clone_ids"].add(event.concept.source_clone_id)
            bucket["generations"].add(event.generation_after)
            bucket["track_refs"].update(event.concept.track_refs)
            bucket["valences"].append(event.concept.valence)

        concepts_considered = len(aggregates)
        promoted_insights: list[str] = []
        proposed_skills: list[str] = []
        track_updates: list[dict[str, Any]] = []
        quarantined: list[str] = []

        # Labels still present in the final workspace snapshot — persistence is evidence.
        snapshot_keys = {
            _normalize_label(c.label) for c in snapshot.slots if not c.automatic
        }

        for key, bucket in aggregates.items():
            label = bucket["label"]
            confidences: list[float] = bucket["confidences"]
            spread = max(confidences) - min(confidences) if confidences else 0.0
            support_score = max(
                len(bucket["clone_ids"]),
                len(bucket["generations"]),
                len(confidences),
            )
            # High-confidence concepts that survived in the final snapshot get a
            # support floor so rehydrate-from-slots (or single strong posts) can promote.
            if (
                key in snapshot_keys
                and bucket["max_confidence"] >= self.confidence_threshold
            ):
                support_score = max(support_score, 2)
            candidate = DistillationCandidate(
                label=label,
                confidence=bucket["max_confidence"],
                supporting_events=bucket["event_ids"],
                valence=bucket["valences"][-1] if bucket["valences"] else None,
                track_refs=sorted(bucket["track_refs"]),
                proposed_action=f"promote:{label}" if bucket["max_confidence"] >= self.confidence_threshold else None,
            )

            reasons: list[str] = []
            if spread > 0.4:
                reasons.append("contradiction")
            if _label_is_sensitive(label) and not allow_sensitive:
                reasons.append("governance")
            if bucket["max_confidence"] < self.confidence_threshold:
                reasons.append("low_confidence")
            if support_score < 2:
                reasons.append("insufficient_support")

            if reasons:
                quarantined.append(label)
                continue

            promoted_insights.append(label)
            proposed_skills.append(f"skill:{_normalize_label(label).replace(' ', '_')}")
            if candidate.track_refs:
                track_updates.append(
                    {
                        "label": label,
                        "track_refs": candidate.track_refs,
                        "confidence": candidate.confidence,
                    }
                )

        promotion_rate = (
            len(promoted_insights) / concepts_considered if concepts_considered else 0.0
        )

        return DistillationResult(
            promoted_insights=promoted_insights,
            proposed_skills=proposed_skills,
            track_updates=track_updates,
            quarantined=quarantined,
            metrics={
                "events_processed": events_processed,
                "concepts_considered": concepts_considered,
                "promotion_rate": promotion_rate,
                "confidence_threshold": self.confidence_threshold,
            },
        )
