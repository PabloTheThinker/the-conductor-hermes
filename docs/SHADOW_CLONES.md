# Shadow clones — Remnants as host subagents

**Metaphor:** Naruto’s *Kage Bunshin* (shadow clone jutsu).  
The **parent agent** (Grok, Hermes, Claude, Codex) is the original.  
**Remnants** are clones that carry out real missions, then **dispel** back into the parent via merge.

**Product line:** clones enhance the host — they use the host’s subagent system; Conductor does not replace the meister.

---

## Lifecycle

```
fanout (dispatch=auto|local|host|hermes)
   │
   ├─ work_pack per clone (brief)
   ├─ local: run clone workers in-process → results applied
   └─ host:  spawn_requests[] for host subagents
         │
         ▼
   host spawns subagents (Grok spawn_subagent, Claude Task, Hermes subagent…)
         │
         ▼
   action=report  (each clone returns findings/insights)
         │
         ▼
   action=await   (optional poll)
         │
         ▼
   action=merge   (fold into parent — Tier 1 / reflective / deep)
```

---

## Dispatch modes

| Mode | Behavior |
|------|----------|
| **local** | Thread-pool shadow workers scan `work_root` / `CONDUCTOR_CLONE_ROOT`, return findings |
| **host** | Emit `spawn_requests` + **`tool_calls`** — parent **must** `spawn_subagent` and `report` |
| **hybrid** | Local preflight then host spawn with findings injected into the clone prompt |
| **hermes** | Hermes-shaped spawn briefs + delegation map |
| **auto** | `CONDUCTOR_CLONE_BACKEND` or: MCP → host, else local |

See also **[ORCHESTRATION.md](./ORCHESTRATION.md)** — thin vs full recipes.

MCP server sets `CONDUCTOR_MCP=1` and default `CONDUCTOR_HOST=grok`.

---

## Host contract

1. `remnant_orchestrate` `action=fanout` `objectives=[…]` `dispatch=host|hermes|…`  
2. **Parent** (not MCP) invokes host spawn **now** (parallel):
   - **Grok:** `spawn_subagent` with each `tool_calls[i].arguments`
   - **Claude:** `Task` with `description` + `prompt`
   - **Hermes:** prefer **`hermes_batch`** → one `delegate_task(tasks=[…])`; or per-clone `goal`+`context`
3. `remnant_orchestrate action=spawn_ack` with `[{remnant_id, clone_handle}, …]`
4. When a subagent finishes →  

```json
{
  "action": "report",
  "remnant_id": "<id>",
  "clone_handle": "<subagent_id>",
  "result": {
    "findings": ["…"],
    "insights": ["…"],
    "suggested_edits": [],
    "done": true
  }
}
```

5. `action=merge` when `clone_readiness.ready` (or `force=true`)

**MCP cannot spawn.** Fanout only returns contracts; Grok/Hermes parent tools launch children.

### Role → host spawn (1.15+)

| Role | Grok `subagent_type` | `capability_mode` |
|------|----------------------|-------------------|
| verify | **general-purpose** | **all** (run tests) |
| explore / scout | explore | read-only |
| architect / plan | plan | read-only |
| implement / surface / backend / … | general-purpose | all |

Override via work_pack `host_subagent_type` + `host_capability_mode` if needed.

---

## Tools

| Action | Role |
|--------|------|
| `fanout` | Summon clones |
| `report` | Clone returns scroll |
| `await` | Poll readiness |
| `status` | Includes `clone_readiness` |
| `merge` | Dispel into parent |
| `work` | Refresh work pack only |

---

## Env

```bash
export CONDUCTOR_CLONE_BACKEND=host   # or local | hermes | auto
export CONDUCTOR_HOST=grok            # grok | claude | hermes | codex
export CONDUCTOR_CLONE_ROOT=/path/to/repo   # local file-aware clones
```

---

## Related

- `docs/MCP.md` — start pack + agent loop  
- `conductor/REMNANT_PROTOCOL.md` — protocol specs  
- `docs/SOUL_RESONANCE.md` — meister primary, clones are not a second ego  
