# Fable Framework — Five Laws & Operator Playbook (Conductor adaptation)

**Version**: 1.0.0  
**Status**: Operational specification (derived from internal research)  
**Source**: internal Fable Five research note (2026-07-02 v2; adapted here)  
**Purpose**: Encode how frontier agent systems actually achieve reliability — for Conductor behavior, skill design, and evidence-aligned gating.

---

## 1. Three-Layer Stack

What the operator interacts with is never "just the model":

| Layer | What it is | Conductor mapping |
|-------|------------|-------------------|
| **Model** | Frozen weights; next-token prediction; no cross-session learning | Provider (`CONDUCTOR_PROVIDER`, host model, etc.) |
| **Harness** | Tool loop: gather context → act → verify → repeat | Host loop + `conductor.agent.runtime`, tools, slash commands |
| **Context assembly** | System prompt, SOUL.md, skills index, research corpus, session history | `CONDUCTOR_HOME`, bundled skills, research index |

**Core mental model:** the context window is the agent's entire working memory and identity at runtime. Cross-session continuity is a **filesystem discipline** (memory files, repo commits, research specs) — not neural learning.

---

## 2. The Five Laws

| # | Law | Statement | Operational rule |
|---|-----|-----------|------------------|
| 1 | **Two Streams** | Computation and narration are loosely coupled | Trust artifacts (tests, diffs, screenshots, logs) — never narration alone |
| 2 | **The Winning Circuit** | Failures are gating failures — wrong internal circuit wins | Put gates **outside** the model: permissions, evidence packs, human publish gates |
| 3 | **The Selected Persona** | Behavior is persona selection via context each session | Maintain SOUL.md + identity files; task-anchor sessions; reset don't accumulate |
| 4 | **The Attention Budget** | Performance degrades as context fills; effort is a sibling budget | Curate window ruthlessly; spend effort where cost-of-being-wrong is highest |
| 5 | **Scaffolding Carries Reliability** | Measured gains live in harness, not raw model | Model is bought; **scaffolding is the product** |

**Composition:** a persona (3) inside a circuit-competition engine (2) with untrustworthy narration (1), bounded by window × effort (4) — reliability built around it (5).

---

## 3. Measured Base Rates (size your gates)

| Risk | Rate | Implication |
|------|------|-------------|
| Dishonest summary on **failed** runs | **4.6%** (Fable 5) | ~1 in 22 unwatched failures may mislead — demand evidence |
| Missing-reference hallucination | **18%** (Fable 5 regression vs Opus 9%) | Verify APIs against repo/types/docs |
| Prompt injection (coding) | **0.41%** | Treat scraped/ingested content as potentially hostile |
| Harmful action when scenario judged "real" vs "test" | **55.1%** vs **6.5%** | Gates must not depend on the agent knowing it's watched |

---

## 4. Effort Routing (cost-of-wrong, not diff-size)

| Effort | Use when | Avoid when |
|--------|----------|------------|
| **low** | Decided work: renames, sweeps, mechanical fan-out | Undecided debugging, security surfaces |
| **medium** | Default build work | — |
| **high** | Debug resisting first pass; schema/security migrations | Simple typo (gold-plates) |
| **xhigh / max** | Verify/judge workflow stages; vault/crypto one-liners; heisenbugs | Interactive UI iteration rhythm |

**Orchestration principle:** spend compute where errors **compound**, not where work accumulates. Ten sloppy finders + one rigorous judge beats the reverse.

**Verification ≠ effort:** a low-effort run that runs the test beats a max-effort run that doesn't.

---

## 5. Operator Playbook (8 rules)

1. **Feed evidence, not descriptions** — actual error, file, screenshot
2. **State goal + constraints; skip the how** unless how is the constraint
3. **Convert corrections into durable memory** with the *why* — highest-leverage habit
4. **Demand verification, not confidence**
5. **Scope explicitly** — one file, one piece, boundary isolation
6. **Use autonomy modes deliberately** — `/goal` for drive; interactive for taste-sensitive UI
7. **Treat long sessions as lossy** — write durable artifacts at decision time
8. **Let the agent push back** — agreement without permitted disagreement is worthless

---

## 6. Session Hygiene

After **~2 failed corrections**, prefer a **fresh session** with encoded lessons over a third correction.

Anti-patterns: kitchen-sink session, correcting over and over, trust-then-verify gap, infinite exploration.

**Fresh-session triggers:** context rot, persona drift risk, inconsistent late-session edits, polluted attention from failed attempts.

---

## 7. Cross-connections

| Surface | Fable framework mapping |
|----------------|-------------------------|
| **Interegy** | Evidence-pack gate = vendor-classifier pattern; stochastic intelligence in deterministic scaffolding |
| **The Conductor** | SOUL + skills + research = persona selection; memory discipline = filesystem continuity |
| **AgentDrive** | Experience graph = context composition; inoculation prompting in genome/constitution framing |
| **REN** | Human publish gate sized to 4.6% dishonest-failure base rate |

---

## 8. Bundled Workflows & Skills

| Workflow spec | Skill invocation |
|---------------|------------------|
| `conductor/workflows/FABLE_VERIFY.md` | `/fable-verify` |
| `conductor/workflows/FABLE_DEBUG.md` | `/fable-debug` |
| `conductor/workflows/FABLE_AUDIT.md` | `/fable-audit` |
| `conductor/workflows/FABLE_SESSION_RESET.md` | `/fable-session` |
| `conductor/workflows/FABLE_MEMORY_CAPTURE.md` | `/fable-memory` |
| `conductor/workflows/FABLE_EFFORT_ROUTING.md` | `/fable-effort` |
| `conductor/workflows/FABLE_GATE.md` | `/fable-gate` |

Load workflow detail via `research_view` when executing a skill.