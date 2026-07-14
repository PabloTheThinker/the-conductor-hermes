# Workflow: Fable Memory Capture (Corrections That Compound)

**Law:** Scaffolding (5) — Fable tier converts notes to capability ~3× better than prior models  
**Skill:** `/fable-memory`  
**When:** User corrects behavior, confirms approach, or states a standing rule

---

## Rule

In-session correction dies at session end. **Filesystem memory compounds.**

Capture the **generalizable rule with the why** — not the incident.

| Bad capture | Good capture |
|-------------|--------------|
| "Fixed modal June 14" | "Modals: portal to `document.body` AND wrap in `.dsr-dark` — otherwise z-index breaks on mobile nav" |
| "Don't use emerald" | "UI palette: no emerald — brand uses slate + accent copper per design-system law" |
| "Run tests" | "Before push: run full CI locally — red on GitHub is trust withdrawal" |

---

## Stages

### 1. Classify (effort: low)

| Type | Purpose |
|------|---------|
| `user` | Operator preferences, identity, voice |
| `feedback` | Corrections + confirmed approaches (**with why**) |
| `project` | State not derivable from repo |
| `reference` | Pointers to docs, patterns, external specs |

### 2. Generalize (effort: medium)

Rewrite user correction into:

- **Rule** — imperative, reusable
- **Why** — failure mode prevented
- **Verify** — how to check rule still applies before acting (memory drifts; repos move)

### 3. Dedupe (effort: low)

- Update stale entry rather than duplicate
- Delete wrong entries explicitly
- One fact per memory artifact when possible

### 4. Index discipline (effort: low)

Memory index must stay lean:

- Claude Code loads only **first 200 lines or 25KB** of MEMORY.md-class indexes
- Index: one line per memory file; details live in file body

### 5. Emit artifact (effort: low)

```markdown
## Memory capture proposal

**Type:** user | feedback | project | reference
**Title:** ...
**Rule:** ...
**Why:** ...
**Verify before acting:** ...
**Index line:** `- [title](path/to/file.md) — one-line summary`
```

If user approves, write to agreed path (`CONDUCTOR_HOME`, repo `memory/`, or operator memory system).

---

## The Conductor note

Conductor four-layer memory (`memory/MEMORY_ARCHITECTURE.md`) is the long-term target. Until full fabric ships, prefer **repo docs + research specs + skills** as durable scaffolding.