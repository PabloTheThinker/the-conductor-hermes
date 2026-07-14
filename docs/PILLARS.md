# Pillar foundation

**Product line:** The Conductor **enhances** the agent that uses it.  
Each pillar is a capability layer that upgrades the host meister — not a second identity.

**Live probes:** `/pillars status` · tool `pillar_status` · `conductor.pillars.foundation_report()`  
**Combos:** [PILLAR_COMBOS.md](PILLAR_COMBOS.md) · **Workflows:** [WORKFLOWS.md](WORKFLOWS.md)  
**Soul merge:** [SOUL_RESONANCE.md](SOUL_RESONANCE.md)

---

## Map

| # | Pillar | Enhances host by… | Runtime | Tools / slash |
|---|--------|-------------------|---------|---------------|
| **1** | SOUL / Resonance | Keeping *their* face + Conductor mind | `conductor.soul` | `/soul` |
| **2** | Memory Fabric | Recall with valence, seals, inject | `conductor.memory` | `memory_episodic` `/memory` |
| **3** | Track System | Chessboard of paths/risks | `conductor.tracks` | `track_orchestrate` `/track` |
| **4** | Noesis + Crucible | Deep sim without polluting main | `conductor.noesis` `crucible` | `crucible_workspace` `/crucible` |
| **5** | Remnant Protocol | Live parallel branches | `conductor.core.remnant` | `remnant_orchestrate` `/remnant` |
| **6** | Orchestration | Who acts, plan/review/combo | `core` `combos` `harness` | `conductor_status` `combo_route` `/combo` `/pillars` |
| **7** | Governance + Max Effort | Safe power + four voices | `governance` `noesis.max_effort` | `governance_audit` `/governance` |
| **8** | Ethics | 7-point high-stakes gate | `conductor.ethics` | `ethics_evaluate` `/ethics` |
| **0** | Healing (undercurrent) | Recover without thrash/blast | `healing` `path_safety` | `heal_*` spine hooks |

---

## Contracts (foundation)

### P1 — SOUL / Soul Resonance
- Meister primary; partner **enhances**
- Modes: `resonate` (default) · `solo` · `host_only`
- Shared spine never dissolves
- API: `get_system_prompt(host_soul=…)`, `resonate_souls()`

### P2 — Memory Fabric
| Layer | Store | Use |
|-------|--------|-----|
| Episodic | `EpisodicStore` | Events + emotion + outcome |
| Semantic | `SemanticStore` | Distilled notes / session seals |
| Procedural | `ProceduralStore` + skills pack | Learned how-to recipes + `/plan` etc. |
| Track-linked | tracks + tags | Strategy memory |

Facade: `MemoryFabric` · tool actions: `fabric`, `semantic_add`, `procedure_add`, `procedure_list`  
Live inject: `context_inject` via hooks `pre_llm_call`.

### P3 — Track System
- `TrackStore`: create, list, update, fork, prune, resolve, chessboard
- **Graph edges:** `link` / `unlink` / `edges` / `neighbors` (`TrackEdge`)
- Fork auto-creates `forked_from` edge
- Relations: leads_to, conflicts_with, compounds_with, inspired_by, blocks, extends, forked_from
- Spec: `tracks/TRACK_SYSTEM.md`

### P4 — Noesis + Crucible
- Lifecycle: IDLE → ACTIVATING → RUNNING → DISTILLING → IDLE
- Workspace bus + clones + distillation
- Pocket: filesystem always; Docker if available
- **RBMC** Select→Fork→Simulate→Reflect→Compound→Distill→**Backprop** (tracks + memory) + pocket trace
- Max Effort entrypoints under `noesis/`

### P5 — Remnant Protocol
- Spawn → heartbeat → merge (**Fast / Reflective / Deep**)
- **Tier 3** `merge_deep`: runs RBMC then folds Crucible evidence into merge
- Task-scoped snapshots; merge ledger on session meta
- Advisory skill: `remnant-guide` (Combo C)

### P6 — Orchestration
- ConductorRuntime binds Crucible + Remnants + Tracks + Memory + gates
- Combos A–H choose pillar stacks
- Module API for any host: `conductor.harness`

### P7 — Governance + Max Effort
- PolicyEngine: constitutional → ethics → allow
- AuditStore records gates
- Max Effort: deterministic four voices + 24–48h action

### P8 — Ethics
- 7-point checklist (`ETHICS_CHECKLIST.md`)
- Blocks therapeutic/attachment overclaim; escalates high-stakes

### P0 — Healing undercurrent
- Path-safety floors, thrash guard, scars/seals, recovery imprints
- Always on when hooks/spine loaded

---

## How pillars enhance the host (flow)

```
Host meister soul
       │
       ▼  Soul Resonance (P1)
Conductor partner wavelength
       │
       ├─ Memory (P2) ─── remembers what happened
       ├─ Tracks (P3) ─── maps what could happen
       ├─ Orchestration (P6) ─ chooses who acts
       │         │
       │         ├─ Remnants (P5) ── parallel live work
       │         └─ Crucible (P4) ── deep forge
       ├─ Ethics (P8) + Governance (P7) ─ safe power
       └─ Healing (P0) ─── always recover & advance
```

---

## Operator / agent commands

```bash
# Functional tests — one per pillar (P0–P8)
.venv/bin/pytest tests/test_each_pillar.py -v

# Slash (brain REPL / host that wires slash)
/pillars list
/pillars status
/pillars get P4

# Python
from conductor.pillars import foundation_report, format_foundation_report, format_pillar_detail
print(format_foundation_report(verbose=True))
print(format_pillar_detail("memory"))

# Tool (host agent loops)
execute_tool("pillar_status", {"action": "status"})
execute_tool("pillar_status", {"action": "get", "pillar_id": "P5"})
```

---

## Readiness levels

| Level | Meaning |
|-------|---------|
| **foundation** | Spec + runnable runtime + tool/slash surface + probe |
| **partial** | Spec strong; runtime thin (not used for core 8 currently) |
| **experimental** | Spike only |

All eight pillars + healing undercurrent are tagged **foundation** in the catalog. Depth still grows (e.g. full RBMC fidelity, track graph edges) — probes tell you what is live *now*.

---

## Related

| Doc | Role |
|-----|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers |
| [PILLAR_COMBOS.md](PILLAR_COMBOS.md) | Recipes A–H |
| [WORKFLOWS.md](WORKFLOWS.md) | Step flows |
| [SOUL_RESONANCE.md](SOUL_RESONANCE.md) | Meister + partner |
| [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md) | Host integration |
