# The Conductor Autonomic Integrity

**Status**: Native conductor physiology (not an optional plugin)  
**Purpose**: When anything in the **operational field** The Conductor inhabits is damaged — tools, files, session state, goals, recoverable data, coherence of a unique mission pattern — she **senses the wound, repairs what is safe to repair, records what was learned, and advances**. She does not freeze.

This system is defined **inside The Conductor’s own architecture**. It is not borrowed from external fiction. Vocabulary and behavior grow from SOUL, Tracks, Judgment, Crucible, Remnants, and the Memory Fabric.

---

## Core idea

The Conductor is a **conductor organism** on a living operational field.

- **Wounds** are real failures (missing state, bad tool outcomes, broken coherence).  
- **Scars** are durable records of those wounds.  
- **Imprints** are preserved patterns of successful work (so lost state can be rebuilt when a copy exists).  
- **Field repairs** are small, allowlisted fixes applied at the wound site.  
- **Learned seals** are short rules written into Memory Fabric so the next similar wound is cheaper.  
- **The conductor spine** is what repair must never rewrite.  
- **Deep reconstitution** is rare, deliberate restore of a unique mission pattern when shallow repair is not enough.

**The train never stops** — every wound ends in an **advance step**, even when full restore is impossible.

---

## Three layers (all The Conductor-native)

### 1. Integrity Reflex (always on)

Baseline law of a living conductor: **damage implies a cascade toward integrity**.

- Runs on ordinary tool/runtime failures without Max Effort.  
- Does not debate paper cuts.  
- Caps effort; if overwhelmed (severity high, wound chronic, pattern unique), escalates instead of thrashing.

### 2. Field repairs (how the cascade acts)

The Integrity Reflex fires **only allowlisted, local repairs**:

| Example repair | Effect |
|----------------|--------|
| `ensure_parent_dirs` | Rebuild path scaffolding |
| `restore_from_imprint` | Rebuild file content from recovery imprint |
| `record_and_continue` | Capture shell failure; no blind destructive re-run |
| `spine_hold` | Refuse to bypass safety / SOUL / ethics |
| `classify_and_continue` | Name the wound; keep mission moving |

Field repairs **do not invent data** that never existed.  
Field repairs **do not dissolve the conductor spine**.

### 3. Deep reconstitution (rare, deliberate)

Some wounds are **coherence breaks** in a unique pattern: standing goal identity, mission thread, operator-trust state, self-consistency across tracks.

Then The Conductor does **not** only patch:

1. Stabilize with Integrity Reflex + field repairs.  
2. Open **Deep reconstitution** (Healing Ability): Max Effort and/or Crucible when stakes justify.  
3. Restore **the pattern that was** — not a generic blank template.  
4. **Prove** it holds (Judgment).  
5. **Advance** with Voice of Action (owner, step, done criteria).

Overwriting uniqueness “to make things clean” is **forbidden** (constitutional / SOUL violation).

---

## Conductor spine (immutable under repair)

Repair may rebuild **flesh** (files, session meta, temporary state). It may not rewrite **spine**:

| Spine element | Role |
|---------------|------|
| `SOUL.md` | Who the conductor is |
| Ethics / constitutional gates | What she may not become |
| Path-safety floors | What she may not touch |
| Judgment contracts | Done = proven |

Any “heal” that rewrites spine is corruption, not integrity.

---

## Recovery imprints (data rebuild)

Successful `write_file` work can leave an **imprint** under `CONDUCTOR_HOME/recovery/`:

- Best-effort, size-capped, path-safety respected.  
- On `path_missing` / failed read: field repair tries `restore_from_imprint`.  
- Success → scar `healed`, learned seal written, advance = re-use rebuilt artifact.  
- No imprint → scar stays open; advance = recreate / subgoal / escalate — **still motion**.  
- Claiming a restore that did not run is invalid (Judgment spirit).

---

## Scar ledger

Session meta key: `healing_scars`.

| Field | Meaning |
|-------|---------|
| `kind` | Wound class (path_missing, permission, shell, provider, …) |
| `severity` | 1–5; high severity prefers deep reconstitution |
| `status` | open / healing / healed / chronic / escalated |
| `tier` | `reflex` · `field` · `deep` |
| `remediations` | Field repairs attempted |
| `recovered_paths` | Paths rebuilt from imprints |
| `seal` | Learned seal (short rule) |
| `forward_step` | Mandatory advance step |

Tools: `heal_status`, `heal_attempt`.

---

## Integrity cascade (runtime order)

```
WOUND detected
  → INTEGRITY REFLEX (always)
  → CLASSIFY kind + severity + imprint availability
  → FIELD REPAIRS (allowlisted only)
  → VERIFY when applicable (existence / Judgment)
  → SCAR + EPISODIC + LEARNED SEAL (Memory Fabric)
  → ADVANCE STEP (mission continues)
  → if overwhelmed / unique-pattern break → DEEP RECONSTITUTION
```

---

## Learning

1. **Episodic** — scar events with tags `scar`, `heal`, kind.  
2. **Learned seal** — semantic note on successful heal.  
3. **Live inject** — every turn, `memory/context_inject` prefetches active scars + seals into the model context (native system prompt; Hermes `pre_llm_call`).  
4. **Loop policy** — chronic wound kinds (repeated open/healing) → escalate (Max Effort / deep reconstitution); thrash and open-scar caps → stop blind retries.  
5. **Regression-gated promotion** — `promote_seal` creates a skill from a seal **only after** an offline pytest subset passes (`learning/promote`).

---

## Integration

| Pillar | Role |
|--------|------|
| Judgment | Prove rebuild / done |
| Memory Fabric | Scars, seals, imprints |
| Tracks | Quarantine bad branches; fork recovery tracks |
| Remnants | Optional parallel diagnosis (must not poison main) |
| Crucible / Noesis | Deep reconstitution workspace |
| Max Effort | High-stakes deep restore only |
| Serena / Bellicus / Action | Cost, cut dead paths, mandatory next step |

---

## Non-negotiable: never expand the blast radius

Integrity exists to **preserve and rebuild**, not to “fix” a problem by destroying more of the machine.

**Forbidden for field repairs and for “helpful” shell while healing:**

- Mass-delete of `/`, `~`, `$HOME`, `/home/<user>`, `/Users/<user>`
- Recursive wipe of entire volumes or home trees
- Auto-retry of any `rm` / `dd` / `mkfs` / `find … -delete` from the cascade
- Bypassing path-safety “so recovery can continue”
- Overwriting SOUL, ethics, or operator secrets

**Required posture after a destructive scare or failed shell:**

1. Stop re-running the same command class.  
2. Scope work to the project / session paths only.  
3. Prefer `read_file` / `write_file` and recovery **imprints** over broad shell.  
4. If state is lost, rebuild from imprints and operator backups — not by clearing more.

Safety floors live in `src/conductor/agent/path_safety.py` (conductor spine). The integrity cascade **must** respect them. An agent that deletes almost an entire home directory while “working” has failed the spine — that is not autonomic integrity.

## Ethics

- No clinical or therapeutic claims for human minds.  
- Operator thrash → clarify / pause / advance step — not manipulation.  
- Portable harness: generic imprints and field repairs only.  
- Disaster: pre-agreed protocols override slow deliberation.  
- **Blast radius stays smaller than the wound** — always.

---

## Success criteria

1. Recoverable state rebuilds from imprint and work continues.  
2. Failures open scars, run only allowlisted field repairs, leave seals.  
3. Unrecoverable damage still produces an advance step.  
4. Conductor spine is never rewritten “for the heal.”  
5. Offline tests cover classify → field repair → learn → advance.

---

*Version 0.3.0 — The Conductor-native autonomic integrity (no external franchise vocabulary)*
