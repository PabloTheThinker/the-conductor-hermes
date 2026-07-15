---
name: batch-for-host
description: Host tool batching vs Remnant fanout — wave A/B/C, hermes_batch, concurrency, anti-serial patterns.
---

# Batch for host (Conductor 1.18.10+)

**Use when:** multi-file reads, mixed edit turns, multi-axis clone spawn, or the agent is serializing tools unnecessarily.

## Two parallelisms

| | Host tool batch | Remnant / clones |
|--|-----------------|------------------|
| Mechanism | Many tools in **one turn** | `hermes_batch` → `delegate_task(tasks=[…])` or Grok `spawn_subagent` ×N |
| Scheduler | **Host** (Hermes segments large mixed batches) | Parent + `delegation.max_concurrent_children` |
| Default | Thin mode / everyday work | Full mode, multi-surface, Combo C |

Conductor **never** reimplements Hermes tool-batch segmentation.

## Waves (advisory)

| Wave | Class | Do |
|------|--------|-----|
| **A** | safe_parallel | Reads, status, doctor, search — fire together (`HOST_PARALLEL_SAFE` / `host_parallel_safe()`) |
| **B** | barrier | Writes, patch, terminal — host may segment; still emit in the **same** batch as A when possible |
| **C** | spawn | One `hermes_batch` / multi-`spawn_subagent` — not N serial parent turns |

Module: `conductor.core.wave_planner` (`classify_tool`, `plan_waves`, `host_parallel_safe`).

## Recipes

**Thin (default)**

1. `conductor_start_pack` / thin start
2. One mixed host batch (prefer large)
3. No remnant fanout unless stuck
4. Optional `memory_episodic`

**Full multi-axis**

1. Fanout → read `tool_calls` + `hermes_batch`
2. **Parent spawns this turn** (wave C) — do not only read the contract
3. `spawn_ack` → `report` → `merge`
4. Respect `mandatory_host_action`

**Hybrid**

1. Local/safe preflight (wave A findings in `local_preflight`)
2. Host deepen with preflight in context — do not re-scan the same paths

## Concurrency (Hermes)

```yaml
# $HERMES_HOME/config.yaml
delegation:
  max_concurrent_children: 6  # raise if hermes_batch size > default (often 3)
```

Check: `conductor hermes-ready` → `delegation_concurrency`.

## Thrash + host kwargs (1.18.10)

- `record_and_check(store, session_id, tool_name, args=None, *, batch_id=None, wave_id=None)`
- Failure scars need host `status`/`error_type` or structured JSON — bare `"error"` in success dumps must **not** scar

## Anti-patterns

- Serialize whole turn because one write exists among many reads
- N serial `delegate_task` when one `tasks=[…]` batch works
- Fanout on single-file / kill-the-port work
- Reimplementing host segmentation inside Conductor
- Ritual-only: reading `tool_calls` without spawning
- Scaring on content that merely contains the word “error”

## Related

- `docs/ORCHESTRATION.md` — tool classes + waves
- `docs/HERMES.md` — host batch vs Remnant
- `docs/HERMES_SUBAGENT_FANOUT.md` — real multi-clone spawn
- Skill `remnant-guide` — Combo C strategy (when to fanout)
