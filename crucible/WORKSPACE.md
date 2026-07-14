# Crucible Global Workspace — Architecture Specification

**Status**: Implementation Specification (Phase 2)  
**Version**: 0.1.0  
**Inspired by**: Anthropic J-space / Global Workspace research (July 2026)  
**Related**: `CRUCIBLE_RUNTIME.md`, `memory/NOESIS.md`, `noesis/SIMULATION_ALGORITHMS.md`, `conductor/REMNANT_DATA_MODELS.md`

---

## 1. Purpose

The Crucible runs isolated simulations where The Conductor clones debate, fork tracks, and stress-test decisions. Anthropic's **J-space** research shows that capable LLMs maintain a small **privileged workspace** for deliberate reasoning — reportable, modulatable, causally mediating multi-step thought — while most processing (fluency, parsing, tool I/O) runs automatically outside it.

This spec defines The Conductor's **explicit Global Workspace layer** inside The Crucible:

| Layer | Role | Analog |
|-------|------|--------|
| **Automatic processing** | Snapshot load, tool calls, trace I/O, grammar-level fluency | Non-J-space activations |
| **Global Workspace** | Intermediate concepts, emotional valence, track refs, clone debate | J-space |
| **Distillation** | Promote high-confidence workspace contents to main memory | Counterfactual reflection → behavior change |

The workspace is **not** chain-of-thought text. It is a structured, capacity-limited concept bus that clones read and write — the broadcast hub described in `CRUCIBLE_RUNTIME.md` §4.

---

## 2. Design Principles

1. **Selectivity** — Default capacity 32 concepts (Anthropic: "few dozen"). Posting is competitive; low-salience concepts are evicted.
2. **Verbalizability** — Each workspace concept has a human-readable `label` (the "word on the model's mind"). These are distillation targets, not raw token streams.
3. **Causal mediation** — Downstream clone reasoning reads from workspace state. Swapping a concept changes simulated conclusions (mirrors J-space intervention experiments).
4. **Automatic vs deliberate** — Concepts marked `automatic=True` are logged in the trace but never compete for workspace slots.
5. **Emotional fidelity** — Every deliberate concept carries `EmotionalValence` (aligned with Remnant data models).
6. **Auditability** — Every post, eviction, and read is recorded as a `WorkspaceEvent` for governance review.
7. **Distill-only promotion** — Main memory receives workspace-derived insights only after a distillation pass; never raw Crucible transcripts.

---

## 3. Core Data Models

### 3.1 EmotionalValence

Shared shape with Remnant Protocol (`conductor/REMNANT_DATA_MODELS.md`):

```python
class EmotionalValence(BaseModel):
    primary: str           # e.g. determined, anxious, hopeful
    intensity: float       # 0.0–1.0
    secondary: list[str] | None = None
    notes: str | None = None
```

### 3.2 WorkspaceConcept

A single verbalizable unit in the workspace (J-space analogue):

| Field | Type | Description |
|-------|------|-------------|
| `concept_id` | UUID | Stable identity |
| `label` | str | Verbalizable concept (max 120 chars) |
| `confidence` | float | 0.0–1.0; distillation weight |
| `salience` | float | Computed score for slot competition |
| `source_clone_id` | str \| None | Author clone |
| `reasoning_layer` | int | Simulated depth (0=surface, higher=deeper RBMC step) |
| `valence` | EmotionalValence | Emotional tone |
| `track_refs` | list[str] | Linked track/branch IDs |
| `reportable` | bool | Eligible for verbal report / distillation (default True) |
| `automatic` | bool | Background processing; never occupies a slot |
| `metadata` | dict | Extension point (RBMC phase, merge tier, etc.) |

**Salience formula** (default):

```
salience = confidence * (0.5 + 0.5 * valence.intensity) * (1.0 if reportable else 0.3)
```

### 3.3 WorkspaceState

Point-in-time snapshot of the global workspace:

| Field | Type | Description |
|-------|------|-------------|
| `generation` | int | Monotonic version; increments on every mutation |
| `slots` | list[WorkspaceConcept] | Ordered by salience descending |
| `capacity` | int | Max deliberate concepts (default 32) |
| `active_clone_ids` | list[str] | Clones registered in this session |
| `captured_at` | datetime | UTC timestamp |

### 3.4 WorkspaceEvent

Audit log entry for the workspace bus:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | |
| `session_id` | str | Crucible session |
| `timestamp` | datetime | |
| `operation` | enum | `POST`, `REPLACE`, `EVICT`, `READ`, `CLEAR`, `CLONE_REGISTER` |
| `actor_clone_id` | str \| None | |
| `concept` | WorkspaceConcept \| None | Primary concept involved |
| `evicted_labels` | list[str] | Labels removed to make room |
| `generation_after` | int | Workspace generation after event |

### 3.5 CloneIdentity

A Crucible-internal clone (RBMC fork):

| Field | Type | Description |
|-------|------|-------------|
| `clone_id` | str | |
| `birth_moment_label` | str | e.g. "Project Phoenix day 14 setback" |
| `snapshot_summary` | str | Task-scoped memory slice summary |
| `forked_from` | str \| None | Parent clone or `prime` |
| `status` | enum | `active`, `paused`, `terminated` |

### 3.6 DistillationCandidate / DistillationResult

Post-session promotion pipeline:

**DistillationCandidate** — extracted from workspace trace:
- `label`, `confidence`, `supporting_events`, `valence`, `track_refs`, `proposed_action`

**DistillationResult**:
- `promoted_insights: list[str]` — high-confidence (≥ threshold)
- `proposed_skills: list[str]`
- `track_updates: list[dict]`
- `quarantined: list[str]` — low-confidence or contradictory
- `metrics: dict` — events processed, concepts considered, promotion rate

Default promotion threshold: `confidence >= 0.72` and seen in ≥2 workspace generations or ≥2 clones.

---

## 4. WorkspaceBus — Global Workspace Controller

In-process implementation (Phase 2). Future: Redis pub/sub inside Docker container per `CRUCIBLE_RUNTIME.md`.

### 4.1 API

```python
class WorkspaceBus:
    def __init__(self, session_id: str, capacity: int = 32): ...

    def register_clone(self, identity: CloneIdentity) -> None: ...

    def post(self, concept: WorkspaceConcept, *, actor_clone_id: str | None = None) -> WorkspaceEvent:
        """Compete for slot; evict lowest salience if at capacity."""

    def replace(self, old_label: str, new_concept: WorkspaceConcept, ...) -> WorkspaceEvent:
        """J-space swap analogue — redirect silent reasoning."""

    def read(self, clone_id: str) -> WorkspaceState:
        """Clone reads broadcast workspace; logged as READ event."""

    def snapshot(self) -> WorkspaceState: ...

    def trace(self) -> list[WorkspaceEvent]: ...

    def clear(self) -> WorkspaceEvent: ...
```

### 4.2 Slot Competition (Ignition)

When `post` is called with a deliberate (`automatic=False`) concept:

1. Recompute salience for incoming concept.
2. If an existing slot has the same `label` (case-insensitive), replace in place if new salience ≥ old.
3. Else if `len(slots) < capacity`, append.
4. Else evict the lowest-salience slot(s) until room exists.
5. Increment `generation`; append `WorkspaceEvent`.

Automatic concepts: append to `automatic_trace` only; never touch slots.

### 4.3 Read Semantics

`read(clone_id)` returns current `WorkspaceState` without mutation. Every read is logged — supports governance "who consulted what concept when."

---

## 5. CrucibleManager Integration

Upgrade `CrucibleManager` to own session-scoped `WorkspaceBus` instances.

### 5.1 Session Lifecycle + Workspace

```
create_session()
  → CrucibleSession + WorkspaceBus
  → state: ACTIVATING

register_clone(session_id, CloneIdentity)
  → bus.register_clone()
  → state: RUNNING (when first clone)

post_concept(session_id, concept, actor_clone_id)
  → bus.post()
  → only valid in RUNNING | DISTILLING (read-only distill)

distill_session(session_id)
  → state: DISTILLING
  → DistillationEngine.run(bus.trace(), bus.snapshot())
  → attach result to session.metadata["distillation"]
  → state: CLEANUP → IDLE
```

### 5.2 CrucibleSession Fields (extended)

```python
@dataclass
class CrucibleSession:
    session_id: str
    state: CrucibleState
    started_at: datetime
    metadata: dict[str, Any]
    bus: WorkspaceBus          # session-scoped workspace
    clones: list[CloneIdentity]
    distillation: DistillationResult | None = None
```

---

## 6. DistillationEngine

Mirrors Anthropic **counterfactual reflection training**: shape internal workspace → behavior changes without training on full transcripts.

### 6.1 Pipeline

1. **Collect** all deliberate concepts from `bus.trace()` POST/REPLACE events.
2. **Aggregate** by normalized `label` — max confidence, merged track_refs, valence union.
3. **Score** support: count distinct clones, generation span, event count.
4. **Promote** if `confidence >= threshold` AND `support_score >= 2`.
5. **Quarantine** contradictions (same label, confidence spread > 0.4).
6. **Emit** `DistillationResult` for main conductor consumption.

### 6.2 Governance Hooks

Flag workspace labels matching safety patterns before promotion:
- `fake`, `fictional`, `blackmail`, `manipulation`, `leverage`, `injection`
- Quarantine unless `governance_scope.allow_sensitive_promotion` is set.

---

## 7. RBMC Phase Mapping

| RBMC Phase | Workspace behavior |
|------------|-------------------|
| SELECT | Post track IDs + uncertainty labels |
| FORK | Register clones; each posts birth_moment_label |
| SIMULATE | Clones post intermediate concepts (automatic=False) |
| REFLECT | Clones post critique labels; high valence intensity |
| COMPOUND | DistillationEngine runs on accumulated trace |
| BACKPROPAGATE | DistillationResult attached to session; conductor merges |

---

## 8. Remnant Protocol Alignment

| Remnant (live) | Crucible Workspace (offline) |
|----------------|------------------------------|
| ProgressHeartbeat.key_decisions | WorkspaceConcept.label |
| EmotionalValence | Same model |
| Fast merge tier | Single-generation workspace snapshot diff |
| Reflective merge | Multi-clone workspace trace comparison |
| Deep Simulation merge | Full RBMC session + distillation |

Future: Remnant merge logic can accept `WorkspaceState` exports as merge proposals.

---

## 9. Implementation Layout

```
src/conductor/crucible/
├── models.py        # Pydantic models (this spec §3)
├── bus.py           # WorkspaceBus (§4)
├── distillation.py  # DistillationEngine (§6)
├── manager.py       # CrucibleManager integration (§5)
└── __init__.py      # Public exports

tests/
└── test_crucible_workspace.py
```

---

## 10. Test Scenarios

1. **Capacity eviction** — post 33 concepts; lowest salience evicted.
2. **Label replace** — same label with higher confidence wins slot.
3. **J-space swap** — `replace("spider", ant_concept)` changes readable state.
4. **Automatic bypass** — automatic concepts never occupy slots.
5. **Read audit** — reads appear in trace with clone_id.
6. **Distillation promote** — multi-clone agreement promotes insight.
7. **Distillation quarantine** — contradictory labels quarantined.
8. **Governance flag** — sensitive labels quarantined by default.
9. **Manager lifecycle** — create → clone → post → distill → result attached.

---

## 11. Future Work (Phase 3+)

- Redis pub/sub bus for multi-process Crucible containers
- LLM-as-judge distillation (provider call inside DISTILLING state)
- J-lens-inspired salience from provider logprobs (when API exposes activations)
- Export `WorkspaceState` JSONL alongside Docker session volumes
- Wire `research_view` indexing for this spec in agent turns

---

*The Global Workspace makes The Crucible's pocket dimension cognitively real — not just an isolated container, but a selective broadcast channel where The Conductor's clones think together and distill only what matters.*