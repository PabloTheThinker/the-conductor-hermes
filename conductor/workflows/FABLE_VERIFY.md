# Workflow: Fable Verify (Evidence Over Narration)

**Law:** Two Streams (1) + Scaffolding (5)  
**Skill:** `/fable-verify`  
**When:** Before claiming done, before merge/push, after any autonomous stretch, when report includes "verified" or "tests pass"

---

## Preconditions

- A stated claim exists (bug fixed, feature works, audit finding, deployment ready)
- Claim may be agent-generated or user-requested validation

## Stages

### Stage 1 — Extract claims (effort: low)

List every **falsifiable** assertion in the current thread:

- Functional claims ("X works", "Y is fixed")
- Negative claims ("no regressions", "nothing else broke")
- Coverage claims ("E2E verified", "all tests pass")

Reject unfalsifiable prose. If no falsifiable claims, stop: nothing to verify.

### Stage 2 — Map evidence (effort: medium)

For each claim, specify the **cheapest sufficient check**:

| Claim type | Preferred artifact |
|------------|-------------------|
| Unit behavior | Test output (specific file first) |
| Type safety | Typecheck/lint output |
| UI behavior | Screenshot or preview interaction log |
| API shape | `node_modules` types or fetched docs |
| Repo change | `git diff` showing intended delta only |

**Rule:** narration about an artifact does not substitute for the artifact.

### Stage 3 — Execute checks (effort: medium)

Run checks. Inject **actual output** into the working context.

- Red output = information, not obstacle
- Skipped check = named as skipped with reason
- Cannot run = report `unverified because X` — never imply verification

### Stage 4 — Adversarial pass (effort: high)

Ask:

1. Would a hostile reviewer accept this evidence?
2. Is any claim **letter-over-spirit** (green test, wrong fix)?
3. Any check missing for stated blast radius?

### Stage 5 — Verdict (effort: low)

Emit table:

| Claim | Evidence | Status |
|-------|----------|--------|
| ... | command/output ref | PASS / FAIL / SKIPPED / UNVERIFIED |

**End states:**

- **CLEARED** — all material claims PASS with artifacts
- **BLOCKED** — any material claim FAIL or UNVERIFIED without user waiver
- **PARTIAL** — non-material gaps only; list explicitly

## Anti-patterns (fail the workflow)

- Ending on "I verified" without tool output in context
- Running only the test that was already green before the change
- Trusting paraphrased error messages when raw error is obtainable

## Output template

```markdown
## Fable Verify — <subject>

### Claims tested
- ...

### Evidence
- `command` → outcome (paste key lines)

### Verdict: CLEARED | BLOCKED | PARTIAL
### Blockers (if any)
- ...
```