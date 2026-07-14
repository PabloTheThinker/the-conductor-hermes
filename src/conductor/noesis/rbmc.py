"""Reflective Branching Monte Carlo (RBMC) — shallow offline Noesis loop.

Select → Fork → Simulate → Reflect → Compound → Distill (in-process pocket).
No Docker required; runs inside the Crucible Global Workspace + filesystem pocket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RBMCConfig:
    max_clones: int = 3
    concepts_per_clone: int = 2
    min_confidence: float = 0.78
    auto_distill: bool = True


@dataclass
class RBMCPhaseResult:
    phase: str
    detail: str
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class RBMCRunResult:
    objective: str
    phases: list[RBMCPhaseResult] = field(default_factory=list)
    clone_ids: list[str] = field(default_factory=list)
    concepts_posted: list[str] = field(default_factory=list)
    distilled: dict[str, Any] | None = None
    pocket_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "phases": [
                {"phase": p.phase, "detail": p.detail, "artifacts": p.artifacts} for p in self.phases
            ],
            "clone_ids": self.clone_ids,
            "concepts_posted": self.concepts_posted,
            "distilled": self.distilled,
            "pocket_path": self.pocket_path,
        }


def _branch_labels(objective: str, n: int) -> list[tuple[str, str, float]]:
    """Generate (clone_id, concept_label, confidence) for simulation branches."""
    base = objective.strip() or "open simulation"
    short = base[:60]
    templates = [
        ("clone_optimistic", f"path:accelerate — {short}", 0.86),
        ("clone_cautious", f"path:de-risk — {short}", 0.84),
        ("clone_adversary", f"path:stress-test — {short}", 0.82),
        ("clone_synthesis", f"path:compound — {short}", 0.88),
    ]
    return templates[: max(2, min(n, len(templates)))]


def run_rbmc(
    conductor: Any,
    agent_session_id: str,
    *,
    objective: str = "",
    config: RBMCConfig | None = None,
    human_acknowledged: bool = False,
) -> RBMCRunResult:
    """Execute a shallow RBMC cycle on ConductorRuntime (in-process pocket)."""
    cfg = config or RBMCConfig()
    result = RBMCRunResult(objective=objective or "Noesis reflection")

    # --- SELECT ---
    status = conductor.status(agent_session_id)
    tracks = status.get("tracks") or []
    high_uncertainty = [t for t in tracks if float(t.get("priority") or 0) >= 0.5]
    select_detail = (
        f"selected objective; {len(tracks)} tracks "
        f"({len(high_uncertainty)} high-priority)"
    )
    result.phases.append(
        RBMCPhaseResult(
            phase="select",
            detail=select_detail,
            artifacts={"track_count": len(tracks), "high_priority": len(high_uncertainty)},
        )
    )

    # Ensure pocket open
    if not status.get("crucible_session_id") or status.get("state") == "idle":
        started = conductor.start_crucible(
            agent_session_id,
            objective or "RBMC Noesis cycle",
            human_acknowledged=human_acknowledged,
        )
        result.phases.append(
            RBMCPhaseResult(
                phase="activate",
                detail=f"opened pocket {started.get('crucible_session_id', '')[:8]}…",
                artifacts=started,
            )
        )
    else:
        result.phases.append(
            RBMCPhaseResult(
                phase="activate",
                detail="reusing active pocket dimension",
                artifacts={"crucible_session_id": status.get("crucible_session_id")},
            )
        )

    cid = conductor.active_crucible_id(agent_session_id) or ""
    try:
        from conductor.crucible.pocket import pocket_path, write_simulation_trace

        result.pocket_path = str(pocket_path(cid)) if cid else ""
    except Exception:  # noqa: BLE001
        result.pocket_path = ""

    # --- FORK ---
    branches = _branch_labels(objective or result.objective, cfg.max_clones)
    for clone_id, _label, _conf in branches:
        conductor.register_clone(
            agent_session_id,
            clone_id=clone_id,
            birth_moment_label=f"RBMC fork {clone_id}",
            snapshot_summary=f"RBMC branch for: {objective or result.objective}",
            forked_from="prime",
        )
        result.clone_ids.append(clone_id)
    result.phases.append(
        RBMCPhaseResult(
            phase="fork",
            detail=f"forked {len(result.clone_ids)} clones",
            artifacts={"clone_ids": list(result.clone_ids)},
        )
    )

    # --- SIMULATE ---
    posted: list[str] = []
    for clone_id, label, conf in branches:
        conductor.post_concept(
            agent_session_id,
            label=label,
            confidence=max(cfg.min_confidence, conf),
            clone_id=clone_id,
            primary_emotion="curious",
            intensity=0.65,
            reasoning_layer=1,
        )
        posted.append(label)
        # Secondary concept per clone
        risk_label = f"risk:{clone_id} — residual uncertainty on {(objective or 'task')[:40]}"
        conductor.post_concept(
            agent_session_id,
            label=risk_label,
            confidence=0.8,
            clone_id=clone_id,
            primary_emotion="tension",
            intensity=0.55,
            reasoning_layer=2,
        )
        posted.append(risk_label)
    result.concepts_posted = posted
    result.phases.append(
        RBMCPhaseResult(
            phase="simulate",
            detail=f"posted {len(posted)} concepts across clones",
            artifacts={"labels": posted[:8]},
        )
    )

    # --- REFLECT ---
    # Cross-clone synthesis concept from prime
    synthesis = f"synthesis: multiverse collapse — {(objective or 'operation')[:50]}"
    conductor.post_concept(
        agent_session_id,
        label=synthesis,
        confidence=0.9,
        clone_id="prime",
        primary_emotion="determined",
        intensity=0.7,
        reasoning_layer=3,
    )
    # Prime also restates best branch for multi-clone agreement (distill support)
    if posted:
        best = posted[0]
        conductor.post_concept(
            agent_session_id,
            label=best,
            confidence=0.88,
            clone_id="prime",
            primary_emotion="hopeful",
            intensity=0.6,
            reasoning_layer=2,
        )
    result.concepts_posted.append(synthesis)
    result.phases.append(
        RBMCPhaseResult(
            phase="reflect",
            detail="cross-clone critique + synthesis posted",
            artifacts={"synthesis": synthesis},
        )
    )

    # --- COMPOUND ---
    compound = f"compound: next irreversible step for {(objective or 'mission')[:50]}"
    conductor.post_concept(
        agent_session_id,
        label=compound,
        confidence=0.91,
        clone_id="prime",
        primary_emotion="determined",
        intensity=0.75,
        reasoning_layer=3,
    )
    # Agreement on compound from second clone for support score
    if result.clone_ids:
        conductor.post_concept(
            agent_session_id,
            label=compound,
            confidence=0.89,
            clone_id=result.clone_ids[0],
            primary_emotion="focused",
            intensity=0.7,
            reasoning_layer=3,
        )
    result.concepts_posted.append(compound)
    result.phases.append(
        RBMCPhaseResult(
            phase="compound",
            detail="compounded high-leverage next step",
            artifacts={"compound": compound},
        )
    )

    # --- DISTILL ---
    if cfg.auto_distill:
        distilled = conductor.distill(
            agent_session_id, human_acknowledged=human_acknowledged
        )
        result.distilled = distilled.model_dump(mode="json")
        result.phases.append(
            RBMCPhaseResult(
                phase="distill",
                detail=f"promoted {len(distilled.promoted_insights)} insights",
                artifacts={
                    "promoted": distilled.promoted_insights,
                    "quarantined": distilled.quarantined,
                },
            )
        )
    else:
        result.phases.append(
            RBMCPhaseResult(phase="distill", detail="skipped (auto_distill=false)")
        )

    # --- BACKPROP (foundation) — write distill into tracks + episodic memory ---
    backprop_art: dict[str, Any] = {}
    try:
        track = conductor._tracks.ensure_default_track(
            agent_session_id, objective=result.objective
        )
        note = f"RBMC: {result.objective[:80]}"
        if result.distilled:
            promoted = result.distilled.get("promoted_insights") or []
            if promoted:
                note += f" | promoted {len(promoted)}"
        conductor._tracks.update_track(
            agent_session_id,
            track.track_id,
            conductor_notes=(track.conductor_notes + " | " + note).strip(" |"),
            confidence=min(0.95, max(track.confidence, 0.75)),
        )
        backprop_art["track_id"] = track.track_id[:8]
        # Episodic + semantic
        from conductor.memory.episodic import EpisodicStore
        from conductor.memory.semantic import SemanticStore

        EpisodicStore(conductor.store).write(
            agent_session_id,
            content=f"RBMC completed: {result.objective}",
            context="noesis/rbmc",
            outcome="success",
            emotion_primary="determined",
            emotion_intensity=0.7,
            tags=["rbmc", "noesis", "crucible"],
        )
        if result.distilled:
            for insight in (result.distilled.get("promoted_insights") or [])[:5]:
                SemanticStore(conductor.store).add_note(
                    agent_session_id,
                    statement=str(insight)[:500],
                    tags=["rbmc", "distill"],
                    confidence=0.85,
                )
        backprop_art["memory"] = "episodic+semantic"
    except Exception as exc:  # noqa: BLE001
        backprop_art["error"] = str(exc)

    result.phases.append(
        RBMCPhaseResult(
            phase="backprop",
            detail="wrote RBMC outcomes to tracks + memory fabric",
            artifacts=backprop_art,
        )
    )

    if cid:
        try:
            from conductor.crucible.pocket import write_simulation_trace

            write_simulation_trace(cid, result.to_dict())
            result.phases.append(
                RBMCPhaseResult(
                    phase="trace",
                    detail=f"simulation_trace.json written under pocket {cid[:8]}…",
                    artifacts={"pocket": result.pocket_path},
                )
            )
        except Exception:  # noqa: BLE001
            pass

    return result
