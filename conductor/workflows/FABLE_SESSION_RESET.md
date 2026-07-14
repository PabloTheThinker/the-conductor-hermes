# Workflow: Fable Session Reset (Clean Prompt > Polluted Context)

**Law:** Attention Budget (4) + Selected Persona (3)  
**Skill:** `/fable-session`  
**When:** ~2+ failed corrections, kitchen-sink session, infinite exploration, late edits inconsistent with early work

---

## Diagnose (effort: medium)

Check which anti-patterns apply:

| Anti-pattern | Signal |
|--------------|--------|
| Kitchen sink | Unrelated tasks in one thread |
| Correcting over and over | ≥2 failed fix attempts on same issue |
| Trust-then-verify gap | Claims without artifacts |
| Infinite exploration | Many reads, no commit to action |
| Context rot | Summarized-away identifiers/errors |
| Persona drift risk | Long meandering session off task |

If **none** apply, output: `SESSION OK — reset not indicated` with brief rationale.

---

## Extract lessons (effort: high)

Before discarding context, capture **durable** items only:

### Keep (generalizable)

- Rules with *why* ("modals must portal to body because …")
- Verified facts with evidence pointers
- Explicit scope constraints that worked

### Discard (incident-only)

- "Fixed modal on June 14"
- Failed attempt stack traces (unless pattern is the lesson)
- Promises and partial plans

---

## Produce fresh-session prompt (effort: medium)

Template:

```markdown
## Fresh session — <goal>

### Context (encoded lessons)
- ...

### Goal (one outcome)
...

### Constraints
- Only: ...
- Do not: ...

### Verification required
- Show: (test / screenshot / diff)

### Assumptions stated upfront
- ...
```

---

## Optional durable writes

If lesson is standing behavior:

1. Propose `feedback` memory entry (general rule + why) → see `FABLE_MEMORY_CAPTURE.md`
2. Or propose `CLAUDE.md` / project doc update for repo-local conventions

---

## Output

1. Diagnosis table (which anti-patterns fired)
2. Fresh-session prompt (copy-paste ready)
3. List of durable captures recommended (if any)

**Do not** continue third correction in the polluted session unless user explicitly overrides.