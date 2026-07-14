"""Remnant Tier 1 (Fast) merge logic."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC
from typing import Any

from conductor.core.models import (
    EmotionalValence,
    MergeProposal,
    MergeResult,
    MergeTier,
    ProgressHeartbeat,
    RemnantRecord,
    RemnantStatus,
)


def _union_insights(heartbeats: Iterable[ProgressHeartbeat]) -> list[str]:
    """Union heartbeat insights; key_decisions stay for divergence only.

    Final list is curated (filter + signal rank). Process decisions like
    SHARED_DECISION are dropped from the merge surface (AgentDrive-style
    high-signal only).
    """
    from conductor.core.remnant_work import curate_insights

    raw: list[str] = []
    for hb in heartbeats:
        # Insights only — decisions pollute merges with ritual chrome
        for item in hb.new_insights:
            key = item.strip()
            if key:
                raw.append(key)
    return curate_insights(raw)


def _collect_remnant_insights(remnants: Iterable[RemnantRecord]) -> list[str]:
    from conductor.core.remnant_work import curate_insights

    raw: list[str] = []
    for remnant in remnants:
        for item in remnant.merge_insights or []:
            key = (item or "").strip()
            if key:
                raw.append(key)
    return curate_insights(raw)


def _normalize_decision_token(text: str) -> str | None:
    """Map decisions to divergence tokens; drop process noise.

    All ``parallel branches…`` variants collapse to one shared alignment token
    so lane-local key_decisions do not alone force Tier-2.
    """
    from conductor.core.remnant_work import SHARED_DECISION, is_filler_insight

    s = (text or "").strip()
    if not s:
        return None
    low = s.lower()
    if "parallel branches" in low or low == SHARED_DECISION.lower():
        return SHARED_DECISION.lower()
    if low.startswith("alternative-path:") or low.startswith("chosen-path:"):
        return None
    if is_filler_insight(s):
        return None
    # Lane-local ownership notes are not strategic conflicts
    if low.startswith("own only") or "sibling" in low and "lane" in low:
        return None
    return low[:160]


def _divergence_score(heartbeats: list[ProgressHeartbeat]) -> float:
    """Jaccard divergence of *normalized* key decisions (lower = more aligned).

    1.17 lessons (digital-white-cell):
    - Inject SHARED_DECISION floor so forgotten pins still align process.
    - **Lane-unique** decisions (count==1) are ownership, not strategic conflict —
      drop them before Jaccard so parallel fanout stays Tier-1 eligible.
    """
    from collections import Counter

    from conductor.core.remnant_work import SHARED_DECISION

    if len(heartbeats) < 2:
        return 0.0
    shared_token = SHARED_DECISION.lower()
    by_remnant: dict[str, set[str]] = {}
    for hb in heartbeats:
        bucket = by_remnant.setdefault(hb.remnant_id, set())
        for decision in hb.key_decisions:
            norm = _normalize_decision_token(decision)
            if norm:
                bucket.add(norm)
        bucket.add(shared_token)
    sets = [s for s in by_remnant.values() if s]
    if len(sets) < 2:
        return 0.0

    counts: Counter[str] = Counter()
    for s in sets:
        for d in s:
            counts[d] += 1
    # Keep shared pin + decisions that appear on ≥2 remnants (real multi-clone tension)
    filtered = [{d for d in s if d == shared_token or counts[d] >= 2} for s in sets]
    if not all(filtered):
        return 0.0
    shared = set.intersection(*filtered)
    union = set.union(*filtered)
    if not union:
        return 0.0
    return min(1.0, 1.0 - (len(shared) / len(union)))


def _reconcile_emotion(heartbeats: list[ProgressHeartbeat]) -> EmotionalValence:
    if not heartbeats:
        return EmotionalValence()
    last = heartbeats[-1].emotional_valence_delta
    intensities = [hb.emotional_valence_delta.intensity for hb in heartbeats]
    avg_intensity = sum(intensities) / len(intensities)
    return EmotionalValence(
        primary=last.primary,
        intensity=avg_intensity,
        notes="Tier 1 fast merge — preserved latest primary, averaged intensity",
    )


def tier1_fast_merge(
    *,
    session_id: str,
    remnants: list[RemnantRecord],
    heartbeats: list[ProgressHeartbeat],
    track_id: str,
    track_version: int,
) -> tuple[MergeProposal, MergeResult]:
    """Tier 1 fast merge — union non-conflicting insights, low divergence only."""
    remnant_ids = [r.remnant_id for r in remnants]
    divergence = _divergence_score(heartbeats)
    if divergence >= 0.2:
        raise ValueError(
            f"divergence score {divergence:.2f} exceeds Tier 1 threshold (0.2) — "
            "use reflective or deep simulation merge"
        )

    from conductor.core.remnant_work import DEFAULT_MERGE_INSIGHT_LIMIT, curate_insights

    merged_insights = curate_insights(
        _union_insights(heartbeats) + _collect_remnant_insights(remnants),
        limit=DEFAULT_MERGE_INSIGHT_LIMIT,
    )

    emotion = _reconcile_emotion(heartbeats)
    proposal_id = str(uuid.uuid4())
    proposal = MergeProposal(
        proposal_id=proposal_id,
        session_id=session_id,
        remnant_ids=remnant_ids,
        tier=MergeTier.FAST,
        summary=f"Fast merge of {len(remnant_ids)} remnant(s): {len(merged_insights)} insight(s)",
        track_deltas=[{"track_id": track_id, "version": track_version, "merge_type": "fast"}],
        memory_deltas=[{"insights": merged_insights}],
        emotional_reconciliation=emotion,
        confidence=max(0.5, 1.0 - divergence),
        divergence_score=divergence,
        next_actions=merged_insights[:3],
    )

    result = MergeResult(
        result_id=str(uuid.uuid4()),
        proposal_id=proposal_id,
        success=True,
        new_track_version=track_version,
        new_track_id=track_id,
        merged_insights=merged_insights,
        emotional_valence_final=emotion,
        governance_notes=(
            "Tier 1 fast merge — curated high-signal remnant findings "
            f"(≤{DEFAULT_MERGE_INSIGHT_LIMIT}, Jaccard near-dedup)"
        ),
    )
    return proposal, result


def apply_merge_to_remnants(remnants: list[RemnantRecord], result: MergeResult) -> list[RemnantRecord]:
    from datetime import datetime

    now = datetime.now(UTC)
    updated: list[RemnantRecord] = []
    for remnant in remnants:
        copy = remnant.model_copy(deep=True)
        copy.status = RemnantStatus.MERGED
        copy.terminated_at = now
        copy.merge_insights = list(result.merged_insights)
        updated.append(copy)
    return updated


def _conflicting_decisions(heartbeats: list[ProgressHeartbeat]) -> list[str]:
    """Return substantive decision tokens not shared by all remnants (capped)."""
    from conductor.core.remnant_work import SHARED_DECISION

    by_remnant: dict[str, set[str]] = {}
    originals: dict[str, str] = {}  # norm -> display
    for hb in heartbeats:
        bucket = by_remnant.setdefault(hb.remnant_id, set())
        for decision in hb.key_decisions:
            norm = _normalize_decision_token(decision)
            if not norm or norm == SHARED_DECISION.lower():
                continue
            bucket.add(norm)
            originals.setdefault(norm, decision.strip()[:160])
    sets = [s for s in by_remnant.values() if s]
    if len(sets) < 2:
        return []
    shared = set.intersection(*sets) if sets else set()
    all_decisions = set.union(*sets) if sets else set()
    conflicts = sorted(all_decisions - shared)
    # Prefer longer / more concrete conflict strings; cap for merge hygiene
    conflicts.sort(key=lambda n: (-len(originals.get(n, n)), n))
    return [originals.get(n, n) for n in conflicts[:3]]


def tier2_reflective_merge(
    *,
    session_id: str,
    remnants: list[RemnantRecord],
    heartbeats: list[ProgressHeartbeat],
    track_id: str,
    track_version: int,
) -> tuple[MergeProposal, MergeResult]:
    """Tier 2 reflective merge — reconcile high divergence without Deep Simulation.

    Strategy:
    - Union all non-conflicting insights/decisions
    - Tag conflicting decisions as alternatives under a structured resolution note
    - Prefer higher progress_percent remnant's decisions when scoring ties
    - Always produce durable merge evidence (never dead-end)
    """
    remnant_ids = [r.remnant_id for r in remnants]
    divergence = _divergence_score(heartbeats)
    conflicts = _conflicting_decisions(heartbeats)

    # Progress-weighted preferred remnant for conflict resolution
    progress_by_remnant: dict[str, float] = {}
    for hb in heartbeats:
        progress_by_remnant[hb.remnant_id] = max(
            progress_by_remnant.get(hb.remnant_id, 0.0),
            hb.progress_percent,
        )
    preferred_id = ""
    if progress_by_remnant:
        preferred_id = max(progress_by_remnant.items(), key=lambda kv: kv[1])[0]

    preferred_decisions: list[str] = []
    for hb in heartbeats:
        if hb.remnant_id == preferred_id:
            preferred_decisions.extend(d.strip() for d in hb.key_decisions if d.strip())

    from conductor.core.remnant_work import DEFAULT_MERGE_INSIGHT_LIMIT, curate_insights

    merged_insights = curate_insights(
        _union_insights(heartbeats) + _collect_remnant_insights(remnants),
        limit=DEFAULT_MERGE_INSIGHT_LIMIT,
    )

    resolution_notes: list[str] = []
    if conflicts:
        resolution_notes.append(
            f"reflective resolution: preferred remnant {preferred_id[:8] or 'n/a'}… "
            f"(highest progress); ≤2 alternative-path retained"
        )
        # Cap alternatives hard before re-curate (white-cell: 12-path dump)
        for c in conflicts[:2]:
            alt = f"alternative-path: {c}"
            if alt not in merged_insights:
                merged_insights.append(alt)
        chosen = 0
        for d in preferred_decisions:
            if d.strip().lower().startswith("parallel branches:"):
                continue
            if _normalize_decision_token(d) is None:
                continue
            note = f"chosen-path: {d}"
            if note not in merged_insights:
                merged_insights.append(note)
                chosen += 1
            if chosen >= 2:
                break
        merged_insights = curate_insights(
            merged_insights,
            limit=DEFAULT_MERGE_INSIGHT_LIMIT,
            max_alternative_paths=2,
        )
    else:
        resolution_notes.append("reflective merge: no hard conflicts — curated union applied")

    emotion = _reconcile_emotion(heartbeats)
    if conflicts:
        emotion = EmotionalValence(
            primary=emotion.primary,
            intensity=min(1.0, emotion.intensity + 0.1),
            secondary=list(emotion.secondary) + ["reconciled"],
            notes="Tier 2 reflective — conflicts tagged as alternatives",
        )

    proposal_id = str(uuid.uuid4())
    proposal = MergeProposal(
        proposal_id=proposal_id,
        session_id=session_id,
        remnant_ids=remnant_ids,
        tier=MergeTier.REFLECTIVE,
        summary=(
            f"Reflective merge of {len(remnant_ids)} remnant(s): "
            f"{len(merged_insights)} insight(s), {len(conflicts)} conflict(s)"
        ),
        track_deltas=[
            {
                "track_id": track_id,
                "version": track_version,
                "merge_type": "reflective",
                "conflicts": conflicts,
            }
        ],
        memory_deltas=[{"insights": merged_insights, "resolution": resolution_notes}],
        emotional_reconciliation=emotion,
        confidence=max(0.4, 0.85 - divergence * 0.4),
        divergence_score=divergence,
        next_actions=[n for n in merged_insights if n.startswith("chosen-path:")][:3]
        or merged_insights[:3],
    )

    result = MergeResult(
        result_id=str(uuid.uuid4()),
        proposal_id=proposal_id,
        success=True,
        new_track_version=track_version,
        new_track_id=track_id,
        merged_insights=merged_insights,
        emotional_valence_final=emotion,
        governance_notes="; ".join(resolution_notes),
    )
    return proposal, result


def tier3_deep_merge(
    *,
    session_id: str,
    remnants: list[RemnantRecord],
    heartbeats: list[ProgressHeartbeat],
    track_id: str,
    track_version: int,
    rbmc_result: dict[str, Any] | None = None,
) -> tuple[MergeProposal, MergeResult]:
    """Tier 3 deep simulation merge — reflective base + Crucible/RBMC evidence.

    Call after (or with) an RBMC / Crucible distill. Incorporates promoted insights
    and tags the merge as deep_simulation for governance audit.
    """
    # Start from reflective reconciliation
    proposal, result = tier2_reflective_merge(
        session_id=session_id,
        remnants=remnants,
        heartbeats=heartbeats,
        track_id=track_id,
        track_version=track_version,
    )
    proposal = proposal.model_copy(update={"tier": MergeTier.DEEP_SIMULATION})
    insights = list(result.merged_insights)
    rbmc = rbmc_result or {}
    # Absorb RBMC distilled promotions
    distilled = rbmc.get("distilled") or {}
    for key in ("promoted_insights", "promoted"):
        vals = distilled.get(key) if isinstance(distilled, dict) else None
        if isinstance(vals, list):
            for v in vals:
                s = str(v).strip()
                if s and s not in insights:
                    insights.append(f"deep-sim:{s}")
    for label in rbmc.get("concepts_posted") or []:
        s = str(label).strip()
        if s.startswith("compound:") and s not in insights:
            insights.append(f"deep-sim:{s}")
    if not any(i.startswith("deep-sim:") for i in insights):
        insights.append(
            "deep-sim: Crucible/RBMC stress-test completed — prefer chosen-path over alternatives"
        )

    emotion = result.emotional_valence_final
    emotion = EmotionalValence(
        primary=emotion.primary if emotion else "determined",
        intensity=min(1.0, (emotion.intensity if emotion else 0.6) + 0.05),
        secondary=list(emotion.secondary if emotion else []) + ["deep_sim"],
        notes="Tier 3 deep simulation — Crucible evidence folded into merge",
    )
    proposal = proposal.model_copy(
        update={
            "summary": (
                f"Deep simulation merge of {len(remnants)} remnant(s): "
                f"{len(insights)} insight(s) with RBMC/Crucible evidence"
            ),
            "confidence": max(0.55, proposal.confidence),
            "memory_deltas": [{"insights": insights, "rbmc_phases": len(rbmc.get("phases") or [])}],
            "track_deltas": [
                {
                    "track_id": track_id,
                    "version": track_version,
                    "merge_type": "deep_simulation",
                    "rbmc_objective": rbmc.get("objective"),
                }
            ],
            "next_actions": [i for i in insights if "chosen-path" in i or "compound:" in i][:3]
            or insights[:3],
        }
    )
    result = result.model_copy(
        update={
            "merged_insights": insights,
            "emotional_valence_final": emotion,
            "governance_notes": (
                (result.governance_notes or "")
                + "; Tier 3 deep_simulation with Crucible/RBMC"
            ).strip("; "),
        }
    )
    return proposal, result
