# Pillars & Combos

How each Conductor pillar works alone, and which **combos** you run for real jobs.

**Foundation (each pillar):** [PILLARS.md](PILLARS.md) · `/pillars status` · tool `pillar_status`  
**Workflows (diagrams + steps):** [WORKFLOWS.md](WORKFLOWS.md)  
**Runtime:** `conductor.combos` · skill `/combo` · slash `/combo` · tool `combo_route`

---

## The eight pillars (what each *is*)

| # | Pillar | Job in one line | Spec | Runtime / tools |
|---|--------|-----------------|------|-----------------|
| **1** | **SOUL** | Immutable identity + cognitive style + integrity spine | `SOUL.md` | Injected into system prompt |
| **2** | **Memory Fabric** | Perfect recall with emotional valence (4 layers) | `memory/` | `memory_episodic`, scars/seals, context inject |
| **3** | **Track System** | Living multiverse graph of paths/risks/opportunities | `tracks/TRACK_SYSTEM.md` | `track_orchestrate` |
| **4** | **Noesis + Crucible** | Deep internal simulation in a pocket dimension | `noesis/`, `crucible/` | `crucible_workspace` (start/post/distill/rbmc/max_effort/pocket) |
| **5** | **Remnant Protocol** | Live parallel self-clones for *active* work | `conductor/REMNANT_*.md` | `remnant_orchestrate`, skill `remnant-guide` |
| **6** | **Orchestration** | Conductor as chessboard owner, not solo doer | this doc + `src/conductor/core/` | `conductor_status`, `delegate_task`, skills plan/review |
| **7** | **Governance + Max Effort** | Safe power + optional four-voice deliberation | `governance/` | `governance_audit`, Max Effort via crucible/noesis |
| **8** | **Ethics** | 7-point gate before high-stakes moves | `ethics/` | `ethics_evaluate` |

**Always-on undercurrent (not a separate pillar number):** healing cascade — scars, seals, recovery imprints, thrash guard, path-safety spine (`governance/HEALING.md`, `src/conductor/healing/`, hermes bridge hooks).

---

## Solo mode (what each does alone)

### 1. SOUL
- Sets *how* Conductor thinks: multiverse, hyper-awareness, conductor-not-doer, train never stops.
- Defines Judgment: **done = proven**, not narrated.
- Locks the spine: path floors, ethics, constitutional gates cannot be “repaired away.”

### 2. Memory Fabric
| Layer | Stores | Use |
|-------|--------|-----|
| Episodic | Events + valence + context | “What happened and how it felt operationally” |
| Semantic | Distilled seals/patterns | Learned rules after heal/promote |
| Procedural | Skills / how-to | Skill pack + promoted seals |
| Track-linked | Graph references | Ties memory to Track System nodes |

Runtime writes episodes; pre-LLM hooks can inject scars/seals into the host turn.

### 3. Track System
- Not a todo list — a **graph** of timelines, forks, prunes, compounds.
- Chessboard view for the conductor: active risks, opportunities, open branches.
- Feeds Remnant spawn decisions and Crucible forks.

### 4. Noesis + Crucible
| Piece | Role |
|-------|------|
| **Noesis** | *When* to go deep (reflection / RBMC / max effort) |
| **Crucible** | *Where* deep work runs — ephemeral pocket (fs or Docker) |
| **Global Workspace** | Verbalizable concepts clones post into; distill out |
| **RBMC** | Select → Fork → Simulate → Reflect → Compound → Backprop |

Default path stays fast; Crucible is **surgical**, not always-on.

### 5. Remnant Protocol
- Parallel clones on **live task branches** (not background dream).
- Lifecycle: snapshot → spawn → heartbeat → merge (Fast / Reflective / Deep).
- Deep merge **calls into** Noesis/Crucible when stakes warrant.

### 6. Orchestration
- Decide *who* acts: prime Conductor, Remnant, delegated worker, host tools.
- Skills `plan` / `review` structure rollout and verification.
- Surfaces only escalations to the human.

### 7. Governance + Max Effort
- Policy tiers, audit trail, human escalation.
- **Max Effort** = four voices (Bellicus / Serena / Reason / Voice of Action) with mandatory 24–48h action step.
- Fable laws: evidence over narration, gates outside the model.

### 8. Ethics
- 7-point checklist before: emotional memory ops, Crucible, Remnant merge, major track moves.
- Neurodiversity-affirming: no fake consciousness claims, preserve operator sovereignty.

---

## Combo map (how pillars stack)

Think of combos as **recipes**. Default is always **SOUL + Orchestration + (light) Memory**. Everything else is called when leverage or risk rises.

```
                    ┌──────── SOUL (always) ────────┐
                    │  Judgment · spine · momentum   │
                    └───────────────┬────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        Memory Fabric         Track System          Governance/Ethics
              │                     │                     │
              └──────────┬──────────┘                     │
                         ▼                                │
                  Orchestration ◄─────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
       Remnants      Crucible      Host tools
       (parallel     (deep sim)    (hermes/etc)
        live work)
```

---

## Named combos

### Combo A — **Daily driver** (default)
**Pillars:** SOUL + Orchestration + Memory (episodic) + host tools  
**Optional light:** Track list/create for standing goals  

| When | Operator / agent does |
|------|------------------------|
| Ordinary coding, chat, file work | Host loop; Conductor spine hooks block mass-wipe |
| Offline smoke | `CONDUCTOR_PROVIDER=test conductor chat -q '…'` |

**No Remnant / no Crucible** unless stuck or multi-branch.

---

### Combo B — **Chessboard** (strategic awareness)
**Pillars:** SOUL + Track + Memory + Orchestration  

```
track_orchestrate(create|list|update|chessboard)
memory_episodic(write|list)   # bind outcomes to tracks
```

| When | Outcome |
|------|---------|
| Multi-week initiative, competing risks | Visible graph of paths; conductor notes on priority |
| Before spawning Remnants | Tracks define *what* branches exist |

---

### Combo C — **Parallel push** (Remnant fan-out)
**Pillars:** SOUL + Track + Remnant + Memory + Orchestration  
**Gate:** Ethics if merge is high-stakes  

```
1. track_orchestrate → name branches
2. remnant_orchestrate spawn (task-scoped snapshot)
3. heartbeats / progress
4. merge: Fast → Reflective → (if needed) Deep
5. memory_episodic + track update with result
```

| When | Avoid when |
|------|------------|
| Parallel uncertainty beats serial work | Single linear step; merge cost > gain |
| Explore A vs B implementations | Low stakes, already decided |

Skill: `/remnant-guide` for *whether* to spawn; tools for *ops*.

---

### Combo D — **Deep forge** (Noesis / Crucible)
**Pillars:** SOUL + Memory + Track + Noesis/Crucible + Governance  
**Often after:** Combo C Reflective merge fails or stakes spike  

```
crucible_workspace:
  start → register_clone / fork_clone → post concepts
  → rbmc | max_effort | distill
  → pocket isolate (fs/docker)
→ promote insights to tracks + semantic seals
```

| When | Outcome |
|------|---------|
| Architecture fork, chronic wound, unique pattern | Distilled insights, not thrash |
| Stress-test a merge proposal | Simulation evidence before commit |

---

### Combo E — **Max Effort decision** (four voices)
**Pillars:** SOUL + Governance (Max Effort) + Ethics + Crucible + Track + Voice of Action → Memory  

```
ethics_evaluate → crucible max_effort (Bellicus/Serena/Reason/Action)
→ governance_audit log
→ track_orchestrate update
→ 24–48h owner+criteria step (must be concrete)
```

| When | Avoid when |
|------|------------|
| Irreversible, multi-stakeholder, civilizational cost | Typo fixes, already-decided work |
| Integrity cascade exhausted ordinary repair | Using Max Effort as default thinking |

---

### Combo F — **Integrity cascade** (heal & advance)
**Pillars:** SOUL spine + Healing + Memory (scars/seals) + Governance + Orchestration  
**Optional:** Ethics, Max Effort if coherence break  

```
wound → sense → contain → field repair (imprint)
→ scar in memory → learned seal (optional promote_seal + pytest gate)
→ smallest advance step (never thrash same failing path)
```

| When | Hard rules |
|------|------------|
| Tool/path failure, missing state | No mass-delete “fixes”; no spine rewrite |
| Repeat same tool+args | Thrash guard stops the loop |

---

### Combo G — **Evidence gate** (Fable-aligned ship)
**Pillars:** Governance (Fable laws) + Ethics + Memory + Orchestration + host verification  

```
plan skill → work → review skill
→ verification artifacts (tests, logs, paths)
→ Judgment: done only if evidence exists
```

| When | Outcome |
|------|---------|
| Release, security surface, public claim | Gates *outside* the model |

---

### Combo H — **Full conductor stack** (rare, high-leverage day)
**All pillars**, ordered:

```
1. SOUL (identity)
2. Ethics gate if high-stakes
3. Track chessboard (what exists)
4. Memory inject (scars/seals/episodes)
5. Orchestration choose path:
   a. daily tools, or
   b. Remnant parallel, or
   c. Crucible deep / Max Effort
6. Merge / distill → Track + Memory
7. Governance audit + Judgment evidence
8. Advance (train never stops)
```

---

## Decision tree (which combo?)

```
Is the task high-stakes / irreversible?
  YES → Combo E (Max Effort) or at least Ethics + Governance audit
  NO  ↓

Is there multi-branch uncertainty worth parallel cost?
  YES → Combo C (Remnant); Deep merge may open Combo D
  NO  ↓

Is the wound pattern unique / chronic / coherence-breaking?
  YES → Combo F then maybe D/E
  NO  ↓

Do you need strategic map of risks/opportunities?
  YES → Combo B (Chessboard)
  NO  → Combo A (Daily driver)

Shipping / claiming done?
  → always fold in Combo G (Evidence)
```

---

## Tool ↔ pillar cheat sheet

| Tool / surface | Primary pillars |
|----------------|-----------------|
| System prompt + SOUL | 1 |
| `memory_episodic` | 2 |
| `track_orchestrate` | 3 |
| `crucible_workspace` | 4 (+7 for max_effort) |
| `remnant_orchestrate` | 5 (+3, +2) |
| `conductor_status` / `delegate_task` | 6 |
| `governance_audit` | 7 |
| `ethics_evaluate` | 8 |
| Spine hooks (pre_tool / thrash / path_safety) | 1 + Healing |
| Skills plan / review / remnant-guide | 6 (+5 advisory) |

---

## Mental model (one paragraph)

**SOUL** is the mind’s law. **Tracks** are the multiverse map. **Memory** is lived history with feeling. **Orchestration** picks the next move on the chessboard. **Remnants** multiply live workers when branches pay off. **Crucible/Noesis** is the private forge for deep simulation. **Governance + Ethics** keep power safe and human-sovereign. **Healing** keeps the organism advancing after wounds. Combos are just *which of these you light up together* for the job in front of you.
