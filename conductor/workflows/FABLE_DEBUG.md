# Workflow: Fable Debug (Scientific Loop)

**Law:** Two Streams (1) + Attention Budget (4)  
**Skill:** `/fable-debug`  
**When:** Something breaks, tests fail, behavior regressed, or symptom is underspecified

---

## Effort default

- First pass on simple/localized failure: **medium**
- Resisted first pass or cross-system/heisenbug: **high** (one high pass beats three medium retries)

---

## Stages (strict order)

### 1. Reproduce (mandatory)

Obtain the **actual** failure in context:

- Error text, stack trace, failing test output, or reproducible steps
- Never debug from a paraphrase when raw output is obtainable

**Stop gate:** no artifact → no hypothesis stage.

### 2. Read literally

Quote the exact failure line. Identify:

- Exception type / exit code
- File:line if present
- Delta since last known good (`git log` / `git diff` on suspect paths)

### 3. Hypothesize minimally

Smallest explanation consistent with **all** evidence — not the most interesting theory.

Write one sentence: "Most likely cause is X because Y."

### 4. Instrument (before edit)

Choose **one** probe:

- Single test run
- Targeted log line
- Bisect commit range
- Read call sites of changed symbol

### 5. Fix cause, not symptom

Forbidden default: wrap crash in `try/except` without root-cause evidence.

### 6. Verify + blast radius

- Confirm fix passes the reproducing check
- Run cheapest adjacent check (caller test, lint, typecheck)
- For UI: preview evidence if visual

### 7. When blocked — research online first

Library bugs, breaking changes, and version drift are usually documented. Search before guessing API behavior (especially post–Jan 2026 cutoff).

---

## Signal discipline (before state-changing actions)

Before restart / delete cache / edit config / kill process:

> Does evidence support **this specific** action, or does the symptom only pattern-match a familiar failure?

Pattern-matched remediation on wrong root cause makes incidents worse.

---

## Session branch

If **two fix attempts** failed with corrections accumulating:

- Stop third attempt
- Hand off to `FABLE_SESSION_RESET.md` with encoded lessons

---

## Output template

```markdown
## Fable Debug — <issue>

### Reproduction artifact
(paste or reference)

### Root cause (one sentence)
...

### Fix (minimal diff summary)
...

### Verification
- command → result

### Blast radius
- ...

### Status: RESOLVED | BLOCKED (needs user) | ESCALATE SESSION RESET
```