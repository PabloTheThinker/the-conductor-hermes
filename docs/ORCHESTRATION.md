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

## Related

- [SHADOW_CLONES.md](./SHADOW_CLONES.md)
- [HERMES_SUBAGENT_FANOUT.md](./HERMES_SUBAGENT_FANOUT.md) — **how real 4-way Hermes spawn works** (research)
- [MCP.md](./MCP.md)
- Grok user-guide: Subagents (`spawn_subagent`)
- Hermes docs: `delegate_task` batch + `delegation.max_concurrent_children`
