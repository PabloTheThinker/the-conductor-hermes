---
name: plan
description: Structure a conductor rollout with phases, recommended pillar combo A–H, and verification surfaces.
---

# Conductor Planning

Reference specs (use `research_view` for detail):

- `docs/PILLAR_COMBOS.md` — eight pillars + named combos
- `docs/WORKFLOWS.md` — combo workflows
- `docs/ARCHITECTURE.md` — system map
- `tracks/TRACK_SYSTEM.md` — tracks / chessboard
- `governance/GOVERNANCE_SAFETY_AUDIT.md` — policy gates

When invoked, produce a structured orchestration plan:

1. **Objective** — one sentence outcome  
2. **Recommended combo** — primary A–H (+ secondary if useful) using the decision tree in `docs/PILLAR_COMBOS.md`  
   - High-stakes / irreversible → **E** (ethics first)  
   - Multi-branch uncertainty → **C** (maybe **D** for deep merge)  
   - Chronic wound → **F** then maybe **D**  
   - Strategic map → **B**  
   - Else → **A**; fold **G** when shipping  
3. **Phases** — ordered steps aligned to that combo’s workflow (`docs/WORKFLOWS.md`)  
4. **Verification** — how each phase is proven (pytest, `conductor doctor`, artifacts)  
5. **Risks** — blockers + mitigations  
6. **Next action** — single concrete step (tools: `combo_route`, `track_orchestrate`, `remnant_orchestrate`, …)

Write for Conductor context: neurodivergent clarity, forward momentum, no fluff.
