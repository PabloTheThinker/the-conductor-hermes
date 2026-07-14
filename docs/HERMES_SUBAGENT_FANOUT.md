# Research: Real subagent fan-out (Hermes + Conductor)

**Date:** 2026-07-12  
**Goal:** Make Conductor actually spawn **N parallel host subagents** (e.g. 4 for a KS-wave style multi-axis build), not only emit spawn *contracts* that the parent ignores.  
**Sources:** local hermes-agent checkout (`tools/delegate_tool.py`, `tools/async_delegation.py`, docs), Hermes public docs, X posts (Teknium, YanXbt/Tonbi masterclass, async shipping notes), Conductor 1.13 clone path.

---

## 1. Executive answer

| Layer | Who can spawn real AI children? | What Conductor does today |
|-------|----------------------------------|---------------------------|
| **Hermes runtime** | **`delegate_task`** (native tool) | Emits fake `tool: "delegate_or_subagent"` — **not a Hermes tool** |
| **Grok Build** | **`spawn_subagent`** (host tool) | Emits correct Grok `spawn_subagent` shapes — parent must invoke |
| **Conductor MCP** | **Cannot** call Hermes or Grok tools | Returns JSON contracts only |
| **Conductor `delegate_task` tool** | Offline echo/shell workers only | **Name-collides** with Hermes’ real `delegate_task` |

**Purpose of Conductor** (product line): enhance the host so the host’s **native** subagent system does the work. Success = host **executes** the contract, children run, results **report → merge**.

The KS-wave drive failed that bar: fanout succeeded; **zero** real subagents ran; parent implemented and hand-reported.

---

## 2. How Hermes actually spawns subagents

### 2.1 Tool: `delegate_task` (not `delegate_or_subagent`)

From `tools/delegate_tool.py` + [official docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation):

```python
# Single child
delegate_task(
    goal="…",           # required — child knows NOTHING else
    context="…",        # paths, constraints, remnant_id, acceptance
    # toolsets optional / inherited
    role="leaf",        # or "orchestrator" if nested allowed
)

# Parallel batch (the real 4-way fan-out)
delegate_task(tasks=[
    {"goal": "…", "context": "…"},
    {"goal": "…", "context": "…"},
    {"goal": "…", "context": "…"},
    {"goal": "…", "context": "…"},
])
```

### 2.2 Runtime mechanics

- Spawns **child `AIAgent` instances** with isolated conversation + terminal session.
- Parallelism: **`ThreadPoolExecutor`**, default **`max_concurrent_children = 3`**.
- **Batches larger than the cap return an error** (not silently truncated).
- **4 concurrent** ⇒ set in `~/.hermes/config.yaml`:

  ```yaml
  delegation:
    max_concurrent_children: 4   # or higher
    # model: "…"                 # optional cheap child model
    # max_spawn_depth: 1         # default flat (no grandchild)
    # child_timeout_seconds: 0   # 0 = no wall clock
  ```

- Children **blocked tools** (leaf): `delegate_task`, `clarify`, `memory`, `send_message`, `execute_code` (and cron).
- Parent context only receives **summaries**, not child tool traces (context isolation / cost control).
- Async path (`async_delegation.py`): `background=true` / model-path background → handle immediately; completion re-enters as a **new turn** via `process_registry.completion_queue`.
- TUI: `/agents` (alias `/tasks`) for live tree, kill, cost.

### 2.3 Critical prompt rule (Hermes + community)

**Subagents know nothing.** Goal+context must be self-contained (file paths, project root, acceptance, remnant_id).  
Bad: `goal="fix the error"`.  
Good: full path, error text, stack, definition of done.

X (YanXbt / Tonbi masterclass, 2026-06): same architecture — cheap child model, strong parent, batch via `tasks[]`, default concurrency 3, nested only with `max_spawn_depth` + `role=orchestrator`.  
X (Teknium, 2026-06): async subagents shipped so chat no longer blocks.  
X (Teknium, 2026-02): can also spawn whole Hermes/Claude Code/Codex instances — different surface than in-process `delegate_task`.

---

## 3. Gap analysis — Conductor 1.13 vs Hermes

### 3.1 Wrong tool name / wrong shape

| Field | Conductor hermes `tool_call` today | Hermes real API |
|-------|------------------------------------|-----------------|
| `tool` | `delegate_or_subagent` | **`delegate_task`** |
| body | `goal` + `prompt` + `description` | **`goal` + `context`** (not prompt/description) |
| parallel | N separate tool_calls | **One** `delegate_task(tasks=[…])` preferred |
| after | parent reports via MCP | Parent gets child **summary JSON**; must still `remnant_orchestrate report` |

Until the shape matches Hermes, **no host will successfully spawn** from Conductor’s hermes contract.

### 3.2 Four tasks vs default concurrency 3

Even with a correct batch, **4 tasks fail** unless `delegation.max_concurrent_children >= 4`.  
Fanout should either:

1. Cap objectives at `max_concurrent_children` and warn, or  
2. Emit config hint + split into two batches, or  
3. Document operator config as required for 4-way.

### 3.3 Conductor’s own `delegate_task` is not Hermes

`conductor.core.delegate` / MCP tool `delegate_task`:

- Workers: **`offline` | `local`** (echo / shell).
- **No LLM children.**
- **Name collision** with Hermes’ built-in `delegate_task`.

Hermes plugin skips only a hard-coded core set (`terminal`, `read_file`, …) — **`delegate_task` is not in that skip set**. Registration may fail if Hermes refuses override without `allow_tool_override`, or confuse MCP-only clients.  
**Fix:** rename Conductor tool to e.g. `conductor_delegate_worker` and never override Hermes `delegate_task`.

### 3.4 MCP cannot spawn

MCP server has no access to:

- Hermes in-process `parent_agent` / tool registry  
- Grok `spawn_subagent` harness  

So MCP fanout **must** remain a **parent contract**.  
“Real spawn” means:

1. **Hermes TUI/CLI parent** calls native `delegate_task` with Conductor-built `tasks[]`, then reports each remnant, or  
2. **Grok parent** calls `spawn_subagent` × N with Conductor-built args, then reports, or  
3. **Optional future:** Hermes plugin hook auto-invokes `delegate_task` when fanout returns (parent still Hermes, not MCP).

### 3.5 Local vs host dispatch

| `dispatch` | Spawns AI children? |
|------------|---------------------|
| `local` | No — thread-pool file scan only |
| `host` / `hermes` | Only if **parent** runs tool_calls |
| `hybrid` | Local preflight + host contract |

There is **no** Conductor path today that calls Hermes `delegate_task` itself.

---

## 4. Target architecture (what “actually spawn 4” means)

### Path A — Hermes-native (primary for hermes host)

```
conductor_start_pack (full)
  → remnant_orchestrate fanout dispatch=hermes objectives=[4 axes]
  → response includes:
       hermes_batch_tool_call: {
         tool: "delegate_task",
         arguments: {
           tasks: [
             { goal, context }, ×4
           ]
         }
       }
       # plus per-remnant mapping remnant_id ↔ task index
  → PARENT (Hermes) executes ONE tool call: delegate_task(tasks=…)
  → 4 children run in ThreadPoolExecutor (need max_concurrent_children≥4)
  → parent receives 4 summaries
  → for each: remnant_orchestrate action=report remnant_id=… result={…}
  → remnant_orchestrate action=merge
```

**Context template per child** must include:

- `remnant_id`, `session_id`, `role`, work pack steps/acceptance  
- `work_root` absolute path  
- instruction: return JSON findings/insights/files_touched/done  
- instruction: do not edit sibling lanes  

### Path B — Grok-native (primary for Grok MCP sessions)

Unchanged intent: **4× `spawn_subagent` in one turn** (parallel), each with `prompt`+`description`, then report/merge.  
Parent must not only *read* `tool_calls`.

### Path C — Plugin auto-bridge (Hermes only, highest leverage)

Hermes plugin `pre_llm_call` or a dedicated skill:

1. Detect fanout result with `execute_tool_calls_now` + hermes host.  
2. Inject system reminder: **must call `delegate_task` with provided `tasks` this turn**.  
3. Optional: `transform` / post-hook maps child summaries → auto `report` if JSON contains `remnant_id`.

Still host-driven; Conductor does not become a second agent loop.

### Path D — In-process bridge (advanced, optional)

If Conductor ever runs **inside** Hermes tool dispatch with `parent_agent`:

```python
from tools.delegate_tool import delegate_task
delegate_task(tasks=…, parent_agent=parent_agent)
```

Only valid inside Hermes process. Not available to pure MCP.

---

## 5. Concrete contract to implement (1.14 candidate)

### 5.1 Fix hermes `build_host_spawn_request`

```python
# Per remnant
{
  "host": "hermes",
  "api": "delegate_task",
  "remnant_id": rid,
  "goal": objective,
  "context": hermes_context,   # not "prompt"
  "description": desc,         # for parent checklist UI only
  "tool_call": {
    "tool": "delegate_task",
    "arguments": {
      "goal": objective,
      "context": hermes_context,
    },
  },
  "after_complete": { "tool": "remnant_orchestrate", "arguments": { "action": "report", ... } },
}
```

### 5.2 Add batch aggregate on fanout

```python
"hermes_batch": {
  "tool": "delegate_task",
  "arguments": {
    "tasks": [
      {"goal": …, "context": …},  # index-aligned with remnant_ids
    ]
  },
  "remnant_ids": [...],
  "requires_config": {
    "delegation.max_concurrent_children": ">= len(tasks)"
  },
  "mandatory_host_action": "Call native Hermes tool delegate_task ONCE with tasks[] NOW"
}
```

Prefer **one batch call** over four separate `delegate_task` singles (cleaner + true parallel batch path).

### 5.3 Rename Conductor offline worker tool

- `delegate_task` → `conductor_worker` / `conductor_delegate_worker`  
- Add `delegate_task` to `_HERMES_CORE_TOOL_NAMES` skip list so we never override Hermes.

### 5.4 Parent spawn receipt (anti-theater)

After fanout, merge blocked until:

- `report` with `clone_handle` **and** optional proof fields, **or**  
- New action `spawn_ack` with host handle ids  

Document: hand-filled report without real spawn is a failed audit (optional strict mode).

### 5.5 Tests

- `build_host_spawn_request(host="hermes")` → tool name `delegate_task`, args have `goal`+`context`  
- Fanout with 4 objectives → `hermes_batch.tasks` length 4 + config hint  
- No registration of Conductor tool named `delegate_task` when Hermes core present  
- Grok path still requires `prompt`+`description`

---

## 6. Recommended operator config (Hermes host)

```yaml
# ~/.hermes/config.yaml  (or HERMES_HOME)
delegation:
  max_concurrent_children: 4
  max_iterations: 40
  # optional cheap children:
  # model: "google/gemini-2.0-flash"
  # provider: "openrouter"
  child_timeout_seconds: 0
  max_spawn_depth: 1
  subagent_auto_approve: false   # keep safe; true only for unattended
```

Raise to 4 **before** expecting a 4-remnant hermes batch to succeed.

---

## 7. What “done” looks like (acceptance)

For a 4-axis full goal (e.g. pro-surfer-wave):

1. `conductor_start_pack` → full + fanout_ready  
2. `remnant_orchestrate fanout dispatch=hermes` → returns valid **`delegate_task` batch**  
3. Hermes parent **calls** that tool (visible in `/agents` as 4 children)  
4. Four children run tools (file/terminal), return summaries  
5. Parent **reports** four remnants with real findings (not invented)  
6. **Merge** succeeds with non-filler insights  
7. Wall-clock shows parallel overlap (not 4× serial parent work)

Until step 3 is true, Conductor is a **ledger**, not a **spawner**.

---

## 8. Research sources (local + web + X)

| Source | Relevance |
|--------|-----------|
| `tools/delegate_tool.py` (hermes-agent) | Canonical spawn implementation |
| `tools/async_delegation.py` (hermes-agent) | Background / completion queue |
| `website/docs/user-guide/features/delegation.md` | Schema, concurrency, depth |
| hermes-agent.nousresearch.com/docs/guides/delegation-patterns | Patterns + config |
| X @Teknium async subagents (2026-06-15) | Non-blocking fan-out product signal |
| X @IBuzovskyi / Tonbi module 8 | Cost, batch, nested depth, “subagents know nothing” |
| Conductor `clone_worker.py` hermes branch | Current wrong tool name |
| Conductor `delegate.py` | Offline workers only |

---

## 9. Implementation status (1.14.0)

| Item | Status |
|------|--------|
| Hermes `delegate_task` + `context` | **Done** |
| `hermes_batch` one-shot `tasks[]` | **Done** |
| `parent_must_spawn` / `protocol` / anti-theater | **Done** |
| `spawn_ack` + `CloneStatus.SPAWNED` | **Done** |
| Rename offline worker → `conductor_worker` | **Done** |
| Plugin skip Hermes `delegate_task` | **Done** |
| Live Hermes TUI 4-way smoke | Operator / next session |
| Plugin auto-reminder / auto-report | Future |

**MCP rule (unchanged):** server cannot call Grok/Hermes spawn tools. Parent executes contracts.
