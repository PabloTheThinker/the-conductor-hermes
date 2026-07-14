# Workflow: Fable Gate (External Deterministic Gating)

**Law:** Winning Circuit (2) + Scaffolding (5)  
**Skill:** `/fable-gate`  
**When:** Designing or reviewing human gates, publish flows, permissions, evidence packs (Interegy, REN, The Conductor governance)

---

## Principle

Never rely on in-model gating for anything that matters.

Anthropic ships Fable with **classifier fallback outside the model** (>95% pass-through). Interegy uses **evidence-pack gates**. The Conductor uses **permissions + governance audit**.

---

## Gate design checklist

### 1. Classify action

| Class | Examples | Gate strength |
|-------|----------|---------------|
| Reversible local | file edit, local test | light |
| Outward / audience | push, publish, email, post | **hard** |
| Irreversible | delete prod data, send bulk | **hard + human** |

### 2. Evidence pack (before gate opens)

Required artifacts depend on claim type (see `FABLE_VERIFY.md`):

- Test output for behavior claims
- Diff for change claims
- Screenshot for UI claims
- Explicit `SKIPPED` / `UNVERIFIED` — never silent

Size gates to base rates:

- **~4.6%** dishonest summaries on failed runs
- **~0.41%** prompt injection in coding contexts
- Evaluation-awareness swing (55% vs 6%) → gate must work when agent doesn't know it's watched

### 3. Deterministic enforcement

Gate logic lives in **code/config**, not model judgment:

- `allow` / `ask` / `deny` permission rules
- CI required checks
- Human approve on publish
- Deny cannot be overridden from below

### 4. Fallback path

On gate trigger:

- Clear user notification
- Action blocked or routed to safer tier (Anthropic: Fable → Opus fallback)
- Unbilled / no silent partial publish

### 5. UX target

Gate **rarely felt, always present** — >95% pass-through for normal work; 100% coverage on irreversible paths.

---

## Interegy isomorphism

```
Research → draft → evidence pack → human gate → publish
        ≈ gather context → act → verify → gate → repeat
```

Sales + architecture thesis: **stochastic intelligence inside deterministic scaffolding.**

---

## Output template

```markdown
## Fable Gate review — <flow>

### Actions classified
| Action | Reversibility | Gate |
|--------|---------------|------|

### Evidence pack requirements
- ...

### Enforcement surface (code, not model)
- ...

### Base-rate alignment
- ...

### Gaps
- ...

### Verdict: ADEQUATE | NEEDS HARDENING
```