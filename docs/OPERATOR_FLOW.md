# Operator flow — thin vs full (one page)

**Product truth:** Conductor is a foreman + score. The **host** is the orchestra.
MCP **cannot** spawn Grok/Hermes children. Ceremony without spawn is theater.

---

## Thin (default)

```
conductor_start_pack(goal)
  → host tools (edit / shell / test)
  → optional memory_episodic
```

**When:** typo, kill port, status, Q&A, single-path fix.  
**Skip:** remnant fanout, pillar_status spam, crucible.

---

## Full (multi-axis product)

```
1. conductor_start_pack(goal, work_root=…)
   → mode=full, axes[], fanout_ready, simple_path, judgment

2. remnant_orchestrate action=fanout  (use fanout_ready args)
   → tool_calls[] / hermes_batch / parent_must_spawn=true

3. PARENT (not MCP): spawn in parallel
   · Grok:   spawn_subagent(**tool_calls[i].arguments)
   · Claude: Task(...)
   · Hermes: delegate_task / hermes_batch.tasks[]

4. remnant_orchestrate action=spawn_ack
   handles=[{remnant_id, clone_handle}, …]

5. When each child finishes:
   remnant_orchestrate action=report
   remnant_id=… clone_handle=… result={findings, insights, done}

6. remnant_orchestrate action=merge
   → merged_insights + judgment.done_proven

7. memory_episodic write outcome + tags
```

**Optional checks:**

| Action | Purpose |
|--------|---------|
| `action=status` | clone_readiness + theater_risk |
| `action=compliance` | explicit spawn theater verdict |
| `action=await` | poll without merging |

---

## Anti-theater rules (1.18.6+)

| Bad | What Conductor does |
|-----|---------------------|
| Merge while clones `awaiting_host` | **Blocked** |
| Host `report` without `clone_handle` | **Blocked** (strict default) |
| Merge after fake reports / no handles | **Blocked** unless `force` + `accept_theater` |
| Local clones with `work_root` | Write **scaffold files** under `.conductor/clone_scrolls/` + stub if greenfield |

`CONDUCTOR_STRICT_SPAWN=0` disables report/merge hard gates (not recommended).  
`CONDUCTOR_LOCAL_SCAFFOLD=0` disables local scaffold writes.

---

## Done = proven (Combo G)

Do **not** claim done from narration. Need at least one of:

- pytest / shell verify evidence  
- served URL + HTTP 200  
- real paths written (host tools or clone `scaffold wrote:`)  
- merge `judgment.done_proven` + host confirmation  

---

## Cognitive weight — what to ignore by default

| Use | Skip unless stuck |
|-----|-------------------|
| start_pack, remnant fanout/ack/report/merge, memory | pillar_status, crucible, ethics, heal, governance_audit |

Full pillar ontology lives in `docs/PILLARS.md`. Daily path is **thin** or **C + G**.

---

## Self-loop study

```bash
PYTHONPATH=src python scripts/self_loop_study.py
```

Must stay clean after routing or theater-gate changes.
