# Conductor Workflows — Fable Framework

Deterministic orchestration specs derived from the Fable Five Laws research. Each workflow is **control flow as documentation** — stages, effort levels, and gates that must not drift.

**Framework anchor:** `governance/FABLE_FRAMEWORK.md`  
**Full research:** internal Fable Five research note (adapted into `governance/FABLE_FRAMEWORK.md`)

## Workflows

| Spec | Skill | Purpose |
|------|-------|---------|
| `FABLE_VERIFY.md` | `/fable-verify` | Evidence-over-narration verification pass |
| `FABLE_DEBUG.md` | `/fable-debug` | Scientific debugging loop (reproduce → root cause) |
| `FABLE_AUDIT.md` | `/fable-audit` | Fan-out search + adversarial judge synthesis |
| `FABLE_SESSION_RESET.md` | `/fable-session` | Diagnose polluted session; produce fresh-session prompt |
| `FABLE_MEMORY_CAPTURE.md` | `/fable-memory` | Convert correction into generalizable feedback rule |
| `FABLE_EFFORT_ROUTING.md` | `/fable-effort` | Pick effort tier and per-stage allocation |
| `FABLE_GATE.md` | `/fable-gate` | External gate design / evidence-pack checklist |

## Orchestration economics

- **Fan-out / mechanical stages:** low effort; errors cheap and self-evident downstream
- **Implement / standard production:** medium effort
- **Verify / judge / synthesize:** high or xhigh — single bad judgment poisons downstream
- **Subagent return target:** ~1,000–2,000 token conclusions, not file dumps

Most **coding** tasks stay single-context. Reserve fan-out for search, review, audits, and research.