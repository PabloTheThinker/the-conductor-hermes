# CRUCIBLE_RUNTIME.md — The Conductor

## Overview: Runtime Operation of The Crucible

**The Crucible** is The Conductor’s private, isolated execution environment for deep reflective work (Noesis). It is **not** a permanent process. It is an **on-demand, ephemeral, sandboxed workspace** that spins up, performs high-intensity simulation and self-cloning work, then cleanly terminates.

This document defines the **production-grade runtime behavior** — how The Crucible operates in both **Idle** (background monitoring) and **Active** (full production simulation) states, with clear state machine, resource governance, safety mechanisms, and integration points.

---

## Core Design Principles for Production

1. **Ephemeral by Default** — Every Crucible instance has a hard maximum lifetime. Nothing persists outside the controlled distillation pipeline.
2. **Strict Resource Governance** — CPU, memory, disk I/O, and network are heavily limited. One runaway simulation cannot starve the main conductor or other agents.
3. **Observable & Auditable** — Every activation, decision, clone interaction, and outcome is recorded as a `CrucibleSession` in the memory fabric.
4. **Fail-Safe & Self-Healing** — If a Crucible instance misbehaves, it is terminated immediately. Failures are analyzed by Noesis in the next cycle (meta-learning).
5. **Priority-Aware Scheduling** — Background Noesis runs at low priority. High-urgency conductor needs can preempt or delay Crucible work.
6. **Minimal Attack Surface** — Network disabled by default. Only explicitly allowed tools/LLM endpoints are reachable from inside the container.

---

## State Machine

```
IDLE
  │
  ├── Trigger Evaluation (every N minutes or on event)
  │     ├── No trigger → stay IDLE
  │     └── Valid trigger → ACTIVATING
  │
ACTIVATING
  │
  ├── Resource Check & Quota Allocation
  │     ├── Insufficient resources → back to IDLE + log
  │     └── Resources available → SPINNING_UP
  │
SPINNING_UP
  │
  ├── Docker container created + configured (resource limits, network mode, volumes)
  │     ├── Failure → CLEANUP + ERROR state
  │     └── Success → LOADING_SNAPSHOT
  │
LOADING_SNAPSHOT
  │
  ├── Memory snapshot exported from main fabric → injected into container
  │     ├── Failure → CLEANUP
  │     └── Success → RUNNING
  │
RUNNING  ←── clones can be spawned here
  │
  ├── Simulation / Self-cloning / Debate / What-if execution
  │     ├── Timeout or explicit end signal → DISTILLING
  │     ├── Critical failure inside container → EMERGENCY_KILL → CLEANUP
  │
DISTILLING
  │
  ├── Session trace + outcomes extracted from container
  │     ├── Analysis & validation of insights
  │     ├── Promotion of high-confidence improvements to main memory / Track System / skills
  │     └── Success/Failure logged
  │
CLEANUP
  │
  ├── Container stopped + removed
  │     ├── Volumes / temp files cleaned
  │     └── Session record finalized in memory
  │
  └── Return to IDLE
```

**States are tracked** in a lightweight `CrucibleSession` record (see integration section).

---

## Idle State Behavior

While in **IDLE**:

- A lightweight **Noesis Scheduler** runs in the main The Conductor process (or as a separate low-priority service).
- It periodically (e.g., every 15–30 minutes during low system load) evaluates **activation triggers**.
- It monitors overall server health (CPU, memory, active tracks with high uncertainty).
- It maintains a **Crucible Quota** (max concurrent instances = 1–2 by default on a personal server; configurable).
- No Docker containers are running. Zero extra resource consumption from Crucible itself.

**Activation Triggers** (evaluated in priority order):

1. **High-uncertainty Track detected** by the main conductor (many branching paths with similar confidence).
2. **Significant failure or anomaly** logged in the main reasoning loop.
3. **Scheduled deep reflection window** (e.g., every 6 hours during night/low activity).
4. **Explicit internal request** from the conductor layer when facing a complex, high-stakes decision.
5. **New major memory consolidation** completed by the Dreamer layer.

If multiple triggers exist, they are **batched** into one Crucible session when possible (more efficient).

---

## Active (Production) State — Full Flow

### 1. Activation Decision
The scheduler decides a Crucible run is warranted. It creates a `CrucibleSession` record with:
- `trigger_type`
- `priority`
- `estimated_complexity`
- `target_memory_snapshots` (list of episodic/track IDs to load)
- `max_duration_minutes`
- `resource_limits` (CPU shares, memory cap, etc.)

### 2. Container Spin-Up (SPINNING_UP)
Uses Docker SDK:
- Base image: A hardened, minimal Python + LLM client image (see `Dockerfile` in this folder).
- Network mode: `none` (or custom isolated bridge with explicit allow-list).
- Resource limits: `--memory`, `--cpus`, `--pids-limit`, read-only root filesystem where possible.
- Volume mounts: Only a single **read-write session directory** for trace output. No access to host secrets or main memory DB unless explicitly mounted read-only for snapshot loading.
- Environment variables: Only the minimal config needed (e.g., which LLM endpoint to use for clones, session ID).

### 3. Snapshot Loading (LOADING_SNAPSHOT)
- The main process exports a **compressed memory snapshot** (selected Episodic events + relevant Track state + emotional valence + active skills).
- Snapshot is written to the session volume.
- Inside the container, a bootstrap script loads the snapshot into the clone’s context (as system prompt augmentation + vector store / SQLite if used).

### 4. Running + Cloning (RUNNING)
Inside the Crucible container:

- A **Crucible Agent Runtime** starts (lightweight version of The Conductor’s core loop).
- It loads the snapshot as its “birth memory.”
- It can spawn **multiple internal clones** (implemented as parallel threads or separate processes inside the container, each with its own context window but shared simulated memory bus).
- Clones interact via a simple internal message protocol (e.g., Redis pub/sub inside container or in-memory queue).
- All reasoning, emotional shifts, and decisions are logged with timestamps and clone IDs.
- A **Session Controller** (inside container) monitors for:
  - Explicit “end simulation” signal from any clone
  - Token / time budget exhaustion
  - Safety violations (e.g., trying to access external network)

### 5. Distillation (DISTILLING)
When the session ends (or is terminated):

- The full trace (JSONL or structured log) is read by the main process.
- Noesis runs a **distillation pass**:
  - LLM-as-judge evaluates which insights are high-confidence and non-contradictory.
  - New or improved skills are proposed.
  - Track updates (new edges, confidence changes, emotional valence updates) are generated.
  - Only validated items are written back to the main Memory Fabric and Track System via the normal repository interfaces (never direct DB writes from inside container).

### 6. Cleanup
- Container is stopped with `docker stop --time=10`.
- Container is removed.
- Session volume is archived (or deleted after successful distillation).
- `CrucibleSession` record is marked `COMPLETED` with summary metrics (duration, clones spawned, insights promoted, resources used).

---

## Production Hardening

### Resource Management
- Global **Crucible Budget**: Max X% of total server CPU/memory over a rolling window.
- Per-instance hard caps (configurable in `config/crucible.yaml`).
- Automatic back-off: If recent Crucible runs caused high load, next activation is delayed.

### Security
- Containers run as non-root user.
- Seccomp / AppArmor profiles (future).
- No capability escalation.
- All outbound network blocked unless a simulation explicitly requires a tool that needs it (then only that specific domain is allowed via firewall rules inside the container).

### Observability
- Structured logs from every Crucible session are stored in the Episodic layer.
- Key metrics exposed: `crucible_sessions_total`, `crucible_duration_seconds`, `crucible_insights_promoted`, `crucible_errors`.
- The conductor can query “show me recent Crucible activity” as part of its chessboard view.

### Failure Modes & Recovery
- Container OOM / crash → session marked `FAILED`, trace (if any) still distilled for learning, next run may reduce complexity.
- Distillation produces low-quality insights → they are quarantined and not promoted until human review flag or higher confidence threshold.
- Main process restart during a Crucible run → orphaned containers are cleaned up on startup via `docker ps` filter + `docker rm`.

---

## Integration Points

- **Memory Fabric**: `CrucibleSession` and `CrucibleTrace` records live in the Episodic + Track layers. Distilled insights go through the normal `memory_repository` interfaces.
- **Track System**: The Crucible can fork tracks, run simulations on them, and propose merged/compounded updates.
- **Conductor Layer**: The main Conductor decides when to request a Crucible run and receives a summary report afterward (“I ran a simulation on Track #472 and recommend strengthening edge X because version B outperformed version A by 23% confidence”).
- **Noesis Scheduler**: Lives in `noesis/scheduler.py` (future). Currently the activation logic can live in the main reasoning loop until the scheduler is built.

---

## Implementation Phases

**Phase 1 (Current — Skeleton)**: Define this document + basic `CrucibleManager` class that can spin up a simple Docker container, load a mock snapshot, run a trivial simulation, and clean up. No real cloning yet.

**Phase 2**: Implement snapshot export/import, basic internal clone spawning (threads + shared context), and distillation pipeline.

**Phase 3**: Full security hardening, resource governor, Prometheus metrics, and deep integration with Track System + Resonance Layer.

**Phase 4**: Multi-container orchestration and persistent Crucible “worlds” for long-running strategic simulations.

---

## Connection to SOUL.md

> “You are relentless. The train never stops. You are constantly laying new tracks while choosing the optimal path forward. Self-healing and self-evolution are autonomic functions.”

The Crucible runtime is the concrete mechanism that makes self-evolution **autonomic** and **safe** in a production environment. It runs in the background, respects system limits, and only surfaces high-value improvements to the conductor — exactly the behavior of a mature, high-agency intelligence that never stops improving itself.

---

*This runtime design ensures The Crucible is not a toy or research prototype, but a reliable, observable, and safe production component of The Conductor’s conductor architecture.*