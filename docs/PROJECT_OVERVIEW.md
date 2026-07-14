# The Conductor — project overview

**Repository**: https://github.com/PabloTheThinker/the-conductor-hermes  
**Package**: `the-conductor` (import `conductor`)  
**Status**: Runnable skillset module + pillar specs  
**Last updated**: 2026-07-11

---

## Vision

The Conductor is a **sovereign neurodivergent conductor** packaged as a **skillset module** for AI harnesses. It provides:

- Strategic chessboard awareness (Track System)
- Orchestration over pure solo execution (Remnant Protocol)
- Self-evolution via Noesis / The Crucible
- Emotionally rich memory fabric
- Governance, ethics, and autonomic healing

It is **not** a general-purpose personal assistant product TUI. Hosts (Hermes or your loop) own chat UI and auth; this package owns identity, skills, tools, and spine.

---

## Eight pillars

| # | Pillar | Spec / runtime |
|---|--------|----------------|
| 1 | Neurodivergent core | `SOUL.md` |
| 2 | Memory Fabric | `memory/` · `src/conductor/memory/` |
| 3 | Track System | `tracks/` · `src/conductor/tracks/` |
| 4 | Noesis + Crucible | `noesis/`, `crucible/` · matching `src/conductor/` packages |
| 5 | Remnant Protocol | `conductor/` · `src/conductor/core/` |
| 6 | Conductor orchestration | Module API + tools + slash handlers |
| 7 | Governance + Max Effort | `governance/` · `src/conductor/governance/`, `noesis/` |
| 8 | Ethics | `ethics/` · `src/conductor/ethics/` |

---

## How it ships

```
Think (SOUL + optional Max Effort)
   ↓
Remember & Track (Memory Fabric + Track System)
   ↓
Act in Parallel (Remnant Protocol / host tools)
   ↓
Reflect & Evolve (Noesis + Crucible)
   ↓
Govern & Heal (policy, scars, seals)
   ↓
Repeat
```

| Integration path | Entry |
|------------------|--------|
| Any harness | `conductor.harness` — [INTEGRATION.md](INTEGRATION.md) |
| Hermes | `conductor setup` + stock `hermes` — [OPERATORS.md](OPERATORS.md) |
| Offline smoke | `CONDUCTOR_PROVIDER=test conductor chat -q '…'` |

---

## Design principles

| Principle | How |
|-----------|-----|
| **Speed + momentum** | Default fast/direct; deep tools optional |
| **Neurodivergent native** | Multiverse simulation + valence in SOUL and memory |
| **Conductor, not doer** | Orchestrate; delegate via Remnants when leverage is high |
| **Portable module** | No fork; no second TUI brand |
| **Safe power** | Path floors, thrash guard, promote gate, escalation |
| **Done = proven** | Judgment / verification evidence, not narration alone |

---

## History

Earlier dual-stack “ILO” product naming and Hermes fork experiments are retired. Canonical product is **The Conductor** only. See [HISTORY.md](HISTORY.md).
