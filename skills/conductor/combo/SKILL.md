---
name: combo
description: Recommend and explain Conductor pillar combos A–H and their workflows (daily, chessboard, remnant, crucible, max-effort, heal, evidence, full-stack).
---

# Combo router

Pick which **pillar stack** to run for the current intent. Specs:

- `docs/PILLAR_COMBOS.md` — pillars + named combos
- `docs/WORKFLOWS.md` — step flows and mermaid diagrams

## Combos (short)

| ID | Name | Use |
|----|------|-----|
| **A** | Daily driver | Default work under SOUL + host tools |
| **B** | Chessboard | Track System map before fan-out |
| **C** | Parallel push | Remnant spawn/merge when parallel pays off |
| **D** | Deep forge | Crucible/Noesis simulation + distill |
| **E** | Max Effort | Ethics + four voices + 24–48h action |
| **F** | Integrity cascade | Heal wound, scar/seal, advance (no thrash) |
| **G** | Evidence gate | Plan → review → artifacts; done = proven |
| **H** | Full stack | Rare multi-pillar day |

## When invoked

1. **Intent** — restate the user goal in one line  
2. **Primary combo** — A–H with one-line why  
3. **Secondary** — up to two alternates if close  
4. **Fold G?** — yes when shipping / claiming done  
5. **Workflow** — numbered steps for the primary (from `docs/WORKFLOWS.md`)  
6. **Tools / skills** — which Conductor tools and slash skills to call next  
7. **Next action** — single concrete step  

Ops (prefer runtime helpers when available):

- `/combo recommend <intent>`
- `/combo workflow <A-H>`
- tool `combo_route` with action `recommend` | `workflow` | `list` | `get`

Do not invent combos outside A–H. Prefer **A** when signals are weak. Never skip **G** when the user wants to ship or declare done.
