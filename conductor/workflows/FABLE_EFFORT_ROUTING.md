# Workflow: Fable Effort Routing

**Law:** Attention Budget (4)  
**Skill:** `/fable-effort`  
**When:** Choosing deliberation depth, workflow stage effort, or debugging strategy

---

## Core rule

**Effort scales with cost of being wrong — not size of diff.**

Same model at every tier. Effort = scratchpad depth per step.

---

## Decision tree

```
What is the cost of being wrong?
│
├── Mechanical / already decided (rename sweep, apply pattern, grep fan-out)
│   └── LOW
│
├── Standard scoped feature in known area
│   └── MEDIUM (default)
│
├── Debug resisted first pass; security; schema migration; symptom ≠ root cause
│   └── HIGH (prefer ONE high pass over three medium retries)
│
├── Heisenbug; cross-system; architecture blast radius; workflow judge stage
│   └── XHIGH / MAX
│
└── Interactive UI taste iteration needing fast round-trips?
    └── LOW–MEDIUM (max between tweaks kills rhythm)
```

---

## Per-stage allocation (orchestration)

| Stage kind | Effort |
|------------|--------|
| Fan-out grep/list/extract | low |
| Standard implement | medium |
| Verify / judge / synthesize | high–xhigh |

**Principle:** spend compute where errors **compound**.

---

## Overthinking guardrails (high/max on simple work)

Watch for:

- Gold-plating (abstractions nobody asked for)
- Edge-case paranoia for impossible scenarios in this codebase
- Scope expansion disguised as robustness
- Latency breaking UI iteration rhythm

---

## What effort does NOT fix

- Knowledge cutoff gaps → web/research
- Hallucinated APIs → read types/docs (verification, not pondering)
- Polluted long session → fresh session (`FABLE_SESSION_RESET.md`)

---

## Output template

```markdown
## Effort routing — <task>

**Recommended tier:** low | medium | high | xhigh | max
**Rationale (cost-of-wrong):** ...
**Per-stage plan (if orchestration):**
| Stage | Effort |
|-------|--------|
| ... | ... |

**Verification requirement:** ...
**Overthinking risk:** low | medium | high
```