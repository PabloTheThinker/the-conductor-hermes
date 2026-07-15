# Orchestration: thin vs full (+ host shadow clones)

Research from live Grok drives (MCP, Multiversal Chess, Parallax Grid, black-hole sim)
and Grok Build subagent docs.

## Two recipes (not one ritual)

| Mode | When | What the host does |
|------|------|---------------------|
| **thin** | Single path, ops, Q&A, quick fix, assessment, restart checks | start_pack → host tools → optional memory |
| **full** | ≥2 real axes (math+shader+UI, API+GPU+visual, A vs B, improve thin+full) | start_pack → fanout **host** → **spawn_subagent** all tool_calls → report → merge → memory |

Default is **thin**. Full is opt-in by goal structure, not by habit.

**1.12+:** fanout returns `execute_tool_calls_now`, `parent_checklist`, and cleaned merge insights (filler stripped). With `work_root`, `fanout_ready` prefers **hybrid** (local preflight + host deepen).

**1.13+:** every host `tool_call` includes **description** where the host requires it. Host contract documents Grok / Claude / Hermes schemas; `parent_checklist[].label` for quick UI.

**1.14+ (MCP + real spawn):** MCP **cannot** call `spawn_subagent` / Hermes `delegate_task`. Fanout returns `parent_must_spawn`, `protocol`, and (Hermes) `hermes_batch`. Parent must SPAWN host tools THIS turn → `spawn_ack` → `report` → `merge`. Hermes tool is real **`delegate_task(goal, context)`**.

**1.15+:** **verify** clones spawn as **`general-purpose`/`all`** (shell/pytest). Work-pack template insights no longer pollute merges. Prefer real `findings[]` evidence only.

## Start pack fields (1.11+)

```json
{
  "orchestration": {
    "mode": "thin|full",
    "axes": [{"objective":"…","role":"…"}],
    "fanout_recommended": true,
    "dispatch_default": "host",
    "recipe": { "steps": ["…"] },
    "research_notes": { "grok_spawn": {…} }
  },
  "fanout_ready": {
    "action": "fanout",
    "dispatch": "host",
    "objectives": ["…", "…"],
    "session_id": "…"
  },
  "next": "THIN MODE: … | FULL MODE: …"
}
```

Force with `mode: "thin" | "full" | "auto"`.

## Host clones that actually run

MCP **cannot** call Grok’s tools itself. Full mode therefore returns **exact**
`spawn_requests[].tool_call` payloads. The parent agent **must** invoke them:

```text
Grok tool: spawn_subagent
arguments:
  prompt: <clone brief>
  description: clone role: objective
  subagent_type: general-purpose | explore | plan
  background: true
  capability_mode: all | read-only
  isolation: none
```

Then for each finished clone:

```text
remnant_orchestrate action=report remnant_id=… clone_handle=<subagent_id>
  result={ findings, insights, done: true }
remnant_orchestrate action=merge
```

### Dispatch modes

| Mode | Behavior |
|------|----------|
| `host` | Spawn requests only (parent spawns; Grok/Claude shape by `CONDUCTOR_HOST`) |
| `local` | In-process workers (no host spawn) |
| `hybrid` | Local preflight + host spawn with findings in prompt |
| `hermes` | Hermes/ILO `delegate_or_subagent` tool_calls (goal+prompt+description) |
| `auto` | MCP/Grok → host; `CONDUCTOR_HOST=hermes` → hermes; else local |

### Multi-host spawn shapes (1.13)

| Host | tool | Required args |
|------|------|----------------|
| Grok | `spawn_subagent` | `prompt`, `description` (+ type, background, capability_mode) |
| Claude | `Task` | `description`, `prompt` |
| Hermes/ILO | `delegate_task` | `goal`, `context` (prefer one-shot `hermes_batch.tasks[]`) |

### Tool classes + waves (1.18.9 → 1.18.10)

Conductor **does not** reimplement Hermes tool-batch segmentation. It classifies tools and labels **waves** so parents emit better batches:

| Wave | Class | Examples | Rule |
|------|--------|----------|------|
| **A** | `safe_parallel` | `read_file`, `search_files`, `web_search`, `web_extract`, `session_search`, `skill_view`, status/doctor probes | Fire together (`HOST_PARALLEL_SAFE` / `host_parallel_safe()`) |
| **B** | `barrier` | `write_file`, `patch`, `terminal`, `memory`, `track_orchestrate` | Host may serial-segment; do **not** serialize the whole turn because one write exists |
| **C** | `spawn` | `delegate_task`, `spawn_subagent`, `remnant_orchestrate` (mutate), `hermes_batch` | Prefer **one** batch tool (`hermes_batch` / `delegate_task(tasks=[…])`) |

**Prefer one large mixed host batch.** Host owns scheduling. Wave fields on fanout / `hermes_batch` are advisory (`waves.A|B|C`, `batch_id` for thrash).

Module: `conductor.core.wave_planner` — `classify_tool`, `host_parallel_safe`, `plan_waves`, `parallel_recipe_thin`, `hybrid_safe_preflight_pack`.

**1.18.12+ remnant action classes + plan cap:**

| `remnant_orchestrate` action | Class | Wave |
|------------------------------|-------|------|
| status, list, heartbeat, await, protocol, compliance | `safe_parallel` | A |
| report, merge, merge_reflective, merge_deep, spawn_ack, terminate | `barrier` | B |
| fanout, spawn | `spawn` | C |

`plan_waves` truncates input at `MAX_WAVE_ITEMS` (default 64) and sets `summary.truncated`. Waves remain **advisory labels** — do not reimplement Hermes segmentation.

Full-mode recipe adds: terminate abandoned remnants; merge with `force`/`accept_theater` only for theater/host-never-spawned paths.

**1.18.10–1.18.11 failure detection:** scars only on host `status`/`error_type`, JSON truthy `error` / non-zero `exit_code`/`returncode`, or strong plain-text markers — never bare substring `error` in success dumps. JSON **arrays** do not body-scan. Status **`completed`/`done`** count as ok. After any detector ship, **restart hermes-serve** so live modules match disk.

### Constraints (Grok)

- Subagent nesting depth **1** (clones cannot spawn clones)
- Prefer **parallel** `spawn_subagent` calls in one turn
- Do not only *read* tool_calls — that is ritual without clones

## Combo scoring

Multi-surface goals (three.js + math + shader, etc.) boost **Combo C** (Parallel push).
Ops / assessment language boosts **Combo A** (Daily). Full mode may override A→C.

## Anti-patterns

- Fanout on “kill the port”
- Full remnant ritual on single-file edits
- `dispatch=local` when the host can spawn and work is multi-axis
- Ignoring `mandatory_host_action` after host fanout
- Reimplementing Hermes tool-batch segmentation inside Conductor
- Serializing an entire turn because one barrier tool exists among many reads
- N serial `delegate_task` calls when one `hermes_batch.tasks[]` works

## Related

- [SHADOW_CLONES.md](./SHADOW_CLONES.md)
- [HERMES_SUBAGENT_FANOUT.md](./HERMES_SUBAGENT_FANOUT.md) — **how real 4-way Hermes spawn works** (research)
- [HERMES.md](./HERMES.md) — host batch vs Remnant
- [MCP.md](./MCP.md)
- Grok user-guide: Subagents (`spawn_subagent`)
- Hermes docs: `delegate_task` batch + `delegation.max_concurrent_children`
