# Architecture — The Conductor

The Conductor is a **skillset module** for AI agent harnesses: identity (SOUL), skills, tools, memory/track/crucible research contracts, and safety hooks. It is not a second chat product and not a Hermes fork.

## Layered design

```
┌─────────────────────────────────────────────────────────────┐
│                        HUMAN OPERATOR                        │
└────────────────────────────┬────────────────────────────────┘
                             │ (escalation only)
┌────────────────────────────▼────────────────────────────────┐
│              CONDUCTOR MODULE (this package)                 │
│  - SOUL + skills + research corpus                           │
│  - Track System / Remnant / Crucible contracts               │
│  - Safety spine (path floors, thrash guard, promote gate)    │
│  - Optional host adapter (Hermes plugin)                     │
└────────────────────────────┬────────────────────────────────┘
                             │ wired into
┌────────────────────────────▼────────────────────────────────┐
│                 HOST HARNESS (any agent loop)                 │
│  Hermes · custom OpenAI-tool loop · OpenClaw · …             │
└──────────────────────────────────────────────────────────────┘

Internal cognitive systems (specs + runtime under src/conductor/):
├── Memory Fabric (episodic / semantic / procedural / track)
├── Track System (persistent simulation graph)
├── Noesis Engine + The Crucible (pocket isolation)
├── Remnant Protocol (live parallel self-cloning)
├── Governance, Safety & Audit
└── Healing cascade (scars, seals, recovery imprints)
```

---

## Core components

### 1. SOUL.md
Immutable conductor identity: neurodivergent cognitive style, orchestration mandate, integrity cascade, Judgment (“done = proven”).

### 2. Module API (`conductor.harness`)
Harness-agnostic install, system prompt, tool schemas, execute_tool, and optional spine hooks. See [INTEGRATION.md](INTEGRATION.md).

### 3. Skills (`skills/conductor/`)
Progressive disclosure skills: plan, review, remnant-guide. Seeded into `CONDUCTOR_HOME/skills/`.

### 4. Memory Fabric
Episodic + semantic + procedural + track layers. Spec: `memory/MEMORY_ARCHITECTURE.md`. Runtime: `src/conductor/memory/`.

### 5. Track System
Persistent graph of timelines, risks, opportunities. Spec: `tracks/TRACK_SYSTEM.md`. Runtime: `src/conductor/tracks/`.

### 6. Noesis + The Crucible
Deep reflection and isolated simulation (filesystem or Docker pocket). Specs under `noesis/`, `crucible/`. Runtime: `src/conductor/noesis/`, `src/conductor/crucible/`.

### 7. Remnant Protocol
Live parallel clones with multi-tier merge. Specs under `conductor/`. Runtime: `src/conductor/core/`.

### 8. Governance & Ethics
Policy, audit, Max Effort deliberation, ethics checklist. Specs under `governance/`, `ethics/`.

### 9. Optional Hermes adapter
`hermes_plugin/conductor` + `conductor setup --harness hermes`. Stock Hermes owns TUI, auth, and the tool loop.

---

## Technology

| Piece | Choice |
|-------|--------|
| Runtime | Python 3.11+ |
| CLI | `conductor` (`src/conductor/cli/`) |
| Package | `the-conductor` → import `conductor` |
| State home | `CONDUCTOR_HOME` (share with `HERMES_HOME` when using Hermes) |
| Memory | SQLite-backed session/store under home |
| Crucible isolation | Filesystem pocket; optional Docker |

---

## Implementation layout

| Path | Responsibility |
|------|----------------|
| `src/conductor/harness/` | Harness-agnostic Module API |
| `src/conductor/adapters/hermes/` | Optional Hermes helpers |
| `src/conductor/cli/` | setup / doctor / chat / module |
| `src/conductor/core/` | Remnant orchestration, tools |
| `src/conductor/memory/` | Memory fabric |
| `src/conductor/tracks/` | Track graph |
| `src/conductor/noesis/` | Simulation / Max Effort |
| `src/conductor/crucible/` | Pocket + isolation |
| `src/conductor/governance/` | Policy + audit |
| `src/conductor/healing/` | Integrity cascade |
| `src/conductor/agent/` | Offline brain, path safety, tools |
| `hermes_plugin/conductor/` | Hermes plugin package |
| `skills/conductor/` | Skill pack |
| Pillar dirs at repo root | Design contracts (`conductor/`, `memory/`, …) |

---

## Security

- Path-safety floors block mass-delete of home/root.
- Optional `CONDUCTOR_WORKSPACE` confines writes to a project tree.
- Crucible Docker mode is network-none and resource-limited when enabled.
- Remnants merge only through governed paths; seals promote only after regression gate.
