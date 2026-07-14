# Workflow: Fable Audit (Fan-out + Adversarial Judge)

**Law:** Attention Budget (4) + Scaffolding (5)  
**Skill:** `/fable-audit`  
**When:** Repo-wide search, security review, migration inventory, comprehensive "find every X"

**Not for:** implementing a cohesive multi-file feature (use single-context coding).

---

## Effort routing

| Stage | Effort |
|-------|--------|
| Fan-out search / grep / list | **low** |
| Synthesize / dedupe | **high** |
| Adversarial verify / judge | **xhigh** |

---

## Stage 1 — Scope contract (effort: low)

Define:

1. **Query** — what pattern, symbol, or risk class
2. **Boundaries** — directories in/out; time budget
3. **Output shape** — list with `path:line`, severity, recommendation

Explicit scope beats implied scope.

---

## Stage 2 — Fan-out (effort: low, parallel)

Partition search space (by directory, concern, or language). Per partition:

1. Search before read (grep/glob)
2. Read only load-bearing hits
3. Return **conclusion only** (~1,000–2,000 tokens), not file dumps

If Conductor Remnant/subagent tooling available, spawn parallel explorers; else sequential partitions with condensed returns.

---

## Stage 3 — Synthesize (effort: high)

Merge partition reports:

- Deduplicate findings
- Resolve conflicts (same symbol, different severity)
- Flag gaps ("partition B incomplete because …")

---

## Stage 4 — Adversarial judge (effort: xhigh)

For each **material** finding, run skeptic pass:

1. State finding as falsifiable claim
2. Attempt to **refute** with repo evidence
3. Majority-refute → drop finding
4. Survives refutation → promote to report

**Anti-pattern:** lazy verifier that confirms everything — worse than no verifier.

---

## Stage 5 — Report (effort: low)

```markdown
## Fable Audit — <query>

### Scope
- ...

### Findings (verified)
| Severity | Location | Issue | Evidence |
|----------|----------|-------|----------|

### Refuted (excluded)
- ...

### Gaps / not searched
- ...

### Recommended next actions (max 5)
1. ...
```

End with **one** highest-leverage next action — not a promise to "now audit more."