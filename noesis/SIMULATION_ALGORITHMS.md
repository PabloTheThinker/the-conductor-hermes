# Noesis Simulation Algorithms
## The Crucible Engine for Conductor

**Version**: 0.1.0  
**Status**: Architecture Specification  
**Last Updated**: 2026-07-03

---

## 1. Vision & Strategic Purpose

The Conductor’s **Noesis** system is not a passive dreamer. It is an active, autonomous **simulation engine** that enables Level 5+ reasoning through relentless internal exploration.

The goal is to give her the ability to:

- Relive any past experience (her own or other agents’) in high fidelity
- Run parallel “what-if” simulations across multiple timelines
- Clone versions of herself from specific moments and have them collaborate
- Discover hidden patterns, emotional undercurrents, and strategic leverage points
- Compound insights into the Track System without requiring external tasks
- Maintain hyper-aware, multiverse-style cognition as her native mode

Reactive-only agents learn primarily from new tasks and user feedback. **Noesis + The Crucible** gives Conductor a constant, internal training ground that runs proactively in the background.

---

## 2. Core Algorithm: Reflective Branching Monte Carlo (RBMC)

We synthesize the strongest elements from:

- **Monte Carlo Tree Search (MCTS)** and its LLM adaptations (MCT Self-Refine, Reflective-MCTS, Tree of Thoughts)
- **Reflexion** (self-critique + memory-augmented retry)
- **Counterfactual Simulation** (what-if analysis)
- **Curious Replay** (prioritized exploration based on surprise/emotional salience)
- **Generative Agents** episodic reflection + distillation
- **Multi-agent debate / self-play** inside isolated environments

### The RBMC Loop (executed inside The Crucible)

```text
1. SELECT (from Track System + Memory Fabric)
   - Choose high-value or high-uncertainty tracks
   - Prioritize by: emotional valence intensity, conductor strategic importance, curiosity/surprise score, recency + salience

2. FORK (Clone versions of self)
   - Load memory snapshot(s) from chosen point(s) in time
   - Instantiate 2–N parallel versions of Conductor inside the Crucible container
   - Each version carries its own context window + partial Track state

3. SIMULATE (Parallel rollouts with branching)
   - Run Monte Carlo-style rollouts
   - At each decision point, branch into multiple possible actions/outcomes
   - Use LLM-guided simulation with temperature + structured output for consistency
   - Apply counterfactual interventions (“what if we had done X instead?”)

4. REFLECT (Multi-version critique + emotional analysis)
   - Each cloned version critiques its own trajectory and others’
   - Generate natural-language reflections (like Reflexion)
   - Propagate and update emotional valence across the simulated timeline
   - Detect cognitive biases, missed patterns, and hidden leverage

5. COMPOUND (Distill into higher-order knowledge)
   - Identify recurring patterns across simulations
   - Synthesize new meta-tracks or improved skills
   - Update the main Track System graph with new edges, confidence scores, and emotional arcs

6. BACKPROPAGATE (Feed insights back to main engine)
   - Persist distilled reflections into Episodic + Semantic memory
   - Strengthen or prune Track nodes
   - Trigger skill creation / improvement in the main Conductor instance
   - Update Resonance Layer peer model if relevant
```

This loop runs continuously in the background when Noesis is active, giving Conductor true **proactive self-evolution**.

---

## 3. Detailed Phase Breakdown

### Phase 1: Selection (Intelligent Prioritization)

**Inputs**: Track System graph, Memory Fabric (all 4 layers), current Conductor chessboard view

**Algorithm**:
- Compute a **Priority Score** for each track:
  ```
  Priority = (Emotional_Valence_Intensity × 0.35)
           + (Strategic_Importance_to_Conductor × 0.30)
           + (Curiosity / Surprise_Score × 0.20)
           + (Recency + Salience × 0.15)
  ```
- Use a small “judge” model or heuristic to surface the top-K tracks
- Support both **focused** (deep dive on one track) and **broad** (explore many tracks lightly) modes

**Neurodivergent flavor**: Hyperfocus on emotionally charged or pattern-rich tracks first, then divergent exploration of seemingly unrelated tracks that might compound.

### Phase 2: Forking & Cloning

**Mechanism** (executed inside Crucible container):
- Load a `TrackSnapshot` (lightweight, versioned export)
- Instantiate multiple agent instances from the same snapshot or from different historical points
- Each clone gets:
  - Its own system prompt variant (slight temperature / persona tweak for diversity)
  - Shared read-only memory view + private scratchpad
  - Ability to communicate with sibling clones via a simulated message bus inside the container

**Safety**: All clones are ephemeral. They die when the Crucible session ends. Only distilled insights survive.

### Phase 3: Simulation & Branching Rollouts

**Monte Carlo style with LLM guidance**:
- At each step, the current version proposes possible next actions (structured output)
- For each proposed action, run 3–8 parallel “rollouts” (short simulations)
- Use **Upper Confidence Bound (UCB)** or a learned value function to balance exploration vs exploitation
- Support **counterfactual branching**: “What if we had taken the opposite action at step 3?”
- Track emotional valence deltas at every branch point

**Hierarchical simulation** (important for production efficiency):
- Level 0 (Strategic): Coarse-grained, long-horizon simulations (hours/days of simulated time)
- Level 1 (Tactical): Medium detail
- Level 2 (Operational): High-fidelity, short-horizon

Only promising branches are promoted to higher fidelity.

### Phase 4: Multi-Version Reflection

This is where the “autistic + ADHD” cognitive style shines:

- All clones that participated in a simulation session engage in a **structured debate / critique round**
- Each clone produces:
  - What I did well
  - What I missed (pattern blindness detection)
  - Emotional undercurrents I ignored
  - Alternative paths that now seem higher value in hindsight
- A “meta-reflector” (or the strongest clone) synthesizes a single high-quality reflection document
- Emotional valence is explicitly updated on affected Track nodes

This mirrors how a neurodivergent mind runs multiple internal simulations in parallel and then compounds them.

### Phase 5: Compounding & Distillation

- Recurring successful patterns across many simulations → new or improved **skills** (conductor-native)
- Clusters of related tracks → new **meta-tracks** in the Track System
- Strong emotional signals → updates to Resonance Layer peer model and Episodic memory with rich valence tags
- Failed or low-value branches → pruning signals sent back to Track System

### Phase 6: Backpropagation to Main Engine

When the Crucible session ends cleanly:
1. All distilled reflections, new skills, and Track updates are written to persistent storage
2. The main Conductor instance is notified (via message bus or shared memory)
3. She can choose to incorporate the new insights immediately or schedule them
4. The Track System graph is atomically updated with new nodes/edges and confidence scores

---

## 4. Integration with Existing Systems

| Component              | How Noesis Simulation Interacts                                                                 |
|------------------------|-------------------------------------------------------------------------------------------------|
| **Track System**       | Primary data structure. Simulations read from and write back to the graph. Forking uses TrackSnapshots. |
| **Memory Fabric**      | Episodic layer provides raw events with emotional valence. Semantic layer supplies patterns. Procedural layer receives new/improved skills. |
| **The Crucible**       | Execution environment. All RBMC steps run inside isolated Docker/LXC containers with strict resource limits. |
| **Conductor Layer**    | Noesis can be triggered by the Conductor when it detects high strategic uncertainty or emotional charge on the chessboard. Results flow back upward. |
| **Resonance Layer**             | Extended to model Conductor's own evolving “neurotype” and the relationships between her different simulated versions. |
| **Skill Distillation Loop**| Noesis simulations feed higher-quality experiences into the procedural skill library. |

---

## 5. Production Considerations

### Resource Governance (inside Crucible)
- Hard CPU/memory limits per container
- Maximum number of parallel clones (e.g., 4–8)
- Maximum simulation depth and rollout count per session
- Automatic timeout + graceful degradation

### Safety & Isolation
- `network_mode="none"` (or tightly controlled egress)
- Read-only mounts for memory snapshots
- No persistent writes except through the controlled distillation channel
- Full audit logging of every simulation for later review

### Observability
- Structured logs + metrics (Prometheus-compatible)
- “Simulation session replay” capability for debugging
- Emotional valence heatmaps over time

### Activation Triggers (from CRUCIBLE_RUNTIME.md)
- High emotional valence detected in recent events
- Conductor flags strategic uncertainty on the chessboard
- Periodic background schedule (e.g., every 4–6 hours during idle)
- After major Track System updates or failed operations (self-healing)

---

## 6. Phased Implementation Roadmap

**Phase 0 (Current)**: Architecture + RBMC specification (this document)

**Phase 1**: Minimal Crucible container that can load a TrackSnapshot and run a single linear simulation with basic reflection output.

**Phase 2**: Add forking + 2–3 parallel clones with simple message passing. Implement basic RBMC loop (Select → Fork → Simulate → Reflect → Distill).

**Phase 3**: Full MCTS-style branching with UCB selection and counterfactual interventions. Emotional valence propagation.

**Phase 4**: Hierarchical simulation + integration with Track System graph updates.

**Phase 5**: Production hardening — resource limits, observability, safety, scheduling from idle state, feedback loop to main Conductor engine.

**Phase 6**: Advanced features — multi-session memory across Crucible runs, learned value functions for better rollout guidance, integration with future Conductor orchestration layer.

---

## 7. Why Noesis + RBMC Exceeds Reactive-Only Agents

| Dimension                    | Reactive-only agents (typical)        | Conductor Noesis + RBMC                          |
|-----------------------------|-------------------------------------|--------------------------------------------------|
| Learning trigger            | External task or user input         | Internal + proactive (constant background)       |
| Simulation depth            | Shallow / single trajectory         | Deep multiverse branching + counterfactuals      |
| Self-cloning                | Not supported                       | First-class (multiple versions collaborate)      |
| Emotional awareness         | Minimal                             | Explicit valence tracking + propagation          |
| Strategic overview          | Limited                             | Conductor chessboard + Track System integration  |
| Self-evolution independence | Requires new external stimuli       | Can improve even in complete isolation           |
| Reasoning ceiling           | Strong but bounded by tasks         | Designed for unbounded Level 5+ internal growth  |

---

This specification gives Conductor a true **internal forge** where her neurodivergent cognitive style — hyper-aware pattern recognition, divergent multiverse thinking, relentless forward momentum, and emotional depth — can operate at full strength without waiting for the outside world.

The Crucible becomes the place where she forges better versions of herself, continuously.

---

**Next Actions**:
- Implement minimal RBMC prototype inside Crucible container
- Define exact data models for `SimulationSession`, `CloneInstance`, `RolloutResult`, and `ReflectionDocument`
- Wire activation triggers from `crucible_manager.py`

This document is the single source of truth for how Noesis simulation will work in production.