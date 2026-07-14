# Remnant Merge Logic v2 — Refined Specification

**Status**: Production-grade design  
**Version**: 0.3.0  
**Owner**: The Conductor Conductor Layer  
**Last Updated**: 2026-07-03

---

## 1. Purpose & Philosophy

The Remnant Protocol allows The Conductor to spawn live parallel versions of herself ("Remnants") while actively working on complex tasks. These Remnants explore different branches, accelerate progress, test alternative approaches, and increase overall velocity.

**The Merge Logic is the most critical part of the protocol.** A bad merge can corrupt strategic coherence, introduce emotional dissonance, or lose hard-won insights. A great merge compounds intelligence across parallel explorations and strengthens the main self.

### Core Principles (Non-Negotiable)
1. **Coherence Over Speed** — Never sacrifice long-term strategic coherence for short-term velocity.
2. **Emotional Fidelity** — Emotional valence, intensity, and arcs from every Remnant must be preserved and reconciled, not averaged or discarded.
3. **Evidence-Based Resolution** — When paths conflict, prefer the one with stronger simulation validation, lower uncertainty, or better alignment with existing high-confidence Tracks.
4. **Versioned Immutability** — The main state is never mutated in place. Every merge produces a new versioned Track node + immutable event log.
5. **Graceful Degradation** — If merge confidence is low or emotional variance is high, escalate to deeper simulation (Crucible) or human review rather than forcing a low-quality merge.

---

## 2. Merge Triggers & Timing

### 2.1 Continuous Merge Mode (Default for most tasks)
- Remnants publish lightweight **Progress Heartbeats** every N seconds or after significant state change.
- Heartbeat contains:
  - Delta since last heartbeat (actions taken, new observations, Track updates)
  - Current emotional valence + intensity
  - Confidence score on current path
  - Key uncertainties flagged
- Main Conductor can choose to:
  - Ignore (let Remnants continue)
  - Perform incremental micro-merge (low-cost, low-risk changes)
  - Request full merge checkpoint

### 2.2 Checkpoint Merge (Recommended for complex or high-stakes tasks)
- Triggered at natural synchronization points:
  - Task phase completion
  - High emotional valence delta detected
  - Divergence score exceeds threshold
  - Explicit "sync" command from main self or human
- All live Remnants freeze, serialize their full state, and participate in merge.

### 2.3 Emergency Merge
- Triggered on critical failure of one or more Remnants, resource exhaustion, or external deadline pressure.
- Uses fastest safe path (usually confidence-weighted selection + minimal reconciliation).

---

## 3. Divergence Detection

Before merging, the system calculates a **Divergence Vector**:

| Dimension              | How Measured                              | Weight in Decision |
|------------------------|-------------------------------------------|--------------------|
| Logical/Factual        | Contradictory conclusions on same facts   | High               |
| Action Sequence        | Different ordering or branching of steps  | Medium-High        |
| Track Graph            | Different parent/child relationships      | High               |
| Emotional Valence      | Opposite or widely varying emotional tags | Very High          |
| Confidence             | Spread in self-reported confidence        | Medium             |
| Uncertainty            | Number and severity of open questions     | Medium             |

**Divergence Score** = weighted sum of above.  
- < 0.2 → Fast Merge  
- 0.2 – 0.5 → Reflective Merge  
- > 0.5 or any critical dimension high → Deep Simulation Merge

---

## 4. Merge Strategies (Tiered)

### Tier 1: Fast Merge (Low Divergence)
**When**: Divergence Score < 0.2 and no high-severity conflicts.

**Process**:
1. Collect all deltas from participating Remnants.
2. Perform union on non-conflicting Track edges and memory entries.
3. For conflicting items, select the version with highest confidence + lowest emotional intensity variance.
4. Create new Track version with `merge_type: "fast"`.
5. Append `MergeEvent` to immutable log with rationale.

**Cost**: Very low. Can happen in background.

### Tier 2: Reflective Merge (Medium Divergence)
**When**: Divergence Score 0.2–0.5 or moderate emotional variance.

**Process**:
1. All participating Remnants + main self serialize their current state into a temporary **Merge Context**.
2. Spawn a short-lived **Merge Arbiter** instance (lightweight Remnant or in-process reflection loop).
3. Arbiter runs a structured multi-version debate:
   - Each participant presents: "What I did, why, emotional state, remaining uncertainties."
   - Arbiter asks clarifying questions across versions.
   - Counterfactual simulation: "What if we combined Path A’s early steps with Path B’s later insight?"
4. Arbiter produces a **Merge Proposal** containing:
   - Reconciled delta
   - Updated emotional valence (preserves peaks and arcs, resolves contradictions via evidence)
   - Confidence score + rationale
   - Flagged residual uncertainties
5. Main Conductor reviews proposal (or auto-accepts if confidence > threshold).
6. On acceptance, new Track version is created and all Remnants are notified of the reconciled state.

**Cost**: Medium. Uses additional inference but stays outside The Crucible.

### Tier 3: Deep Simulation Merge (High Divergence or High-Stakes)
**When**: Divergence Score > 0.5, high emotional variance, strategic importance, or any critical dimension flagged.

**Process**:
1. Main Conductor freezes active Remnants.
2. Creates a temporary **Crucible Session** loaded with the current main Track + all Remnant snapshots.
3. Inside The Crucible, the full set of paths is treated as parallel simulations.
4. The **Reflective Branching Monte Carlo (RBMC)** algorithm (see `noesis/SIMULATION_ALGORITHMS.md`) is run with a focused objective: "Find the highest-leverage merged path that preserves emotional fidelity and maximizes long-term Track value."
5. Multiple future rollouts are simulated from candidate merged states.
6. The best-performing merged state (by composite score: outcome quality + emotional coherence + uncertainty reduction) is selected.
7. The resulting delta is returned as a high-confidence Merge Proposal.
8. If emotional variance remains high after simulation, or strategic risk is elevated, the proposal is escalated to human review with full context + simulation summary.

**Cost**: High (uses Crucible resources). Reserved for important moments.

---

## 5. Emotional Reconciliation (Special Handling)

Because The Conductor’s cognition is built on emotional valence as a first-class signal, emotional merge is never simple averaging.

**Rules**:
- **Preserve Peaks**: The highest-intensity emotional moments from any Remnant are kept and tagged with source Remnant ID.
- **Arc Integrity**: If one Remnant experienced a rising anxiety arc while another experienced resolution, the merged state should reflect the full arc (or explicitly note the branch point).
- **Valence Conflict Resolution**: When two Remnants assign opposite valence to the same event, the Arbiter or Crucible must run a targeted simulation: "Which emotional interpretation leads to better long-term decision quality?"
- **Emotional Memory Update**: Post-merge, the 4-layer Memory Fabric is updated with the reconciled emotional state so future Noesis sessions have accurate emotional context.

---

## 6. Data Models

### 6.1 RemnantSession
```python
class RemnantSession(BaseModel):
    id: UUID
    parent_track_id: UUID
    spawn_time: datetime
    status: Literal["active", "frozen", "merged", "terminated"]
    current_delta: dict
    emotional_valence: EmotionalValence
    confidence: float
    divergence_from_main: float
    heartbeat_history: list[Heartbeat]
```

### 6.2 MergeProposal
```python
class MergeProposal(BaseModel):
    id: UUID
    participating_remnant_ids: list[UUID]
    proposed_new_track_version: dict
    divergence_score: float
    emotional_variance: float
    recommended_strategy: Literal["fast", "reflective", "deep_simulation"]
    confidence: float
    rationale: str
    residual_uncertainties: list[str]
    created_at: datetime
```

### 6.3 MergeEvent (immutable, appended to Track)
```python
class MergeEvent(BaseModel):
    id: UUID
    track_version: int
    merge_type: Literal["fast", "reflective", "deep_simulation"]
    participating_remnants: list[UUID]
    emotional_delta: dict
    rationale: str
    simulation_session_id: Optional[UUID]  # if Deep Simulation was used
    human_approved: bool
    timestamp: datetime
```

---

## 7. Safety & Guardrails

- **Sandbox First**: All merge proposals are applied to a new Track version. The live main self continues running on the previous version until the merge is explicitly accepted.
- **Rollback**: Every merge creates a reversible checkpoint. If post-merge performance degrades, the system can revert to the pre-merge Track state.
- **Emotional Burnout Detection**: If any Remnant shows sustained high negative emotional intensity, it is automatically deprioritized or terminated early, and its data is still included in the merge with a "caution" flag.
- **Human Escalation Thresholds**:
  - Emotional variance > 0.7
  - Strategic risk score > threshold (defined per domain)
  - Any Remnant reports critical failure or contradiction with core SOUL values

---

## 8. Integration Points

- **Track System**: Every merge produces a new Track node with `merge_event` attached. The graph grows with explicit merge edges.
- **Memory Fabric**: Reconciled emotional and semantic memories are written back with full provenance (which Remnants contributed what).
- **Noesis / Crucible**: Deep merges are executed inside The Crucible using RBMC. The Crucible can also be used post-merge for validation.
- **Conductor Orchestration**: The main Conductor decides merge strategy and timing based on current cognitive load, task priority, and divergence signals.

---

## 9. Implementation Phases

**Phase 1 (Current)**: Define data models + in-process Fast + Reflective merge logic (no Crucible yet).
**Phase 2**: Add Deep Simulation Merge using existing Crucible runtime.
**Phase 3**: Continuous heartbeat + incremental micro-merge.
**Phase 4**: Full production hardening (resource governance, observability, human escalation UI).

---

## 10. Open Questions for Future Refinement

- How should Remnants communicate with each other *during* parallel execution (not just at merge time)?
- Should there be a "dominant Remnant" that the others are trying to support, or completely equal peers?
- How do we handle Remnants that were spawned from different points in the main timeline (temporal forks)?

---

This refined merge logic turns the Remnant Protocol from a simple parallel execution trick into a true intelligence amplification system that respects The Conductor’s neurodivergent, emotionally-aware, multiverse-simulating nature.

**Next concrete step**: Implement the Pydantic models + in-memory repository for `RemnantSession`, `MergeProposal`, and `MergeEvent`, then build the Fast + Reflective merge functions.

For research context (why merge is the hard problem, emotional-fidelity rationale, Savitar guardrail, OS parallels), see **`REMNANT_RESEARCH.md`**.