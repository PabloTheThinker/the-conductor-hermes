# MCP server — Claude, Codex, Cursor, Grok, and any MCP client

The Conductor exposes its **tool system** over the [Model Context Protocol](https://modelcontextprotocol.io) so AI models can call tracks, Remnants, Crucible, memory, ethics, combos, and pillars **without** embedding Hermes.

**Product line:** MCP clients stay the meister; Conductor **enhances** them.

```
Claude / Codex / Cursor / Grok
        │  MCP stdio
        ▼
the-conductor MCP server
        │
        ▼
tools · resources · prompts  (pillars, resonance, skills)
```

---

## Install

```bash
cd the-conductor-hermes   # this repo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[mcp]"   # or: pip install -e ".[dev]"
```

Optional env:

```bash
export CONDUCTOR_HOME="${CONDUCTOR_HOME:-$HOME/.conductor}"
export CONDUCTOR_HOST_SOUL=~/.hermes/SOUL.md   # optional meister soul for resonance
# Sessions live in $CONDUCTOR_HOME/conductor_state.db (never Hermes state.db)
```

When sharing a home with Hermes (`CONDUCTOR_HOME=$HERMES_HOME`), Conductor still
uses **`conductor_state.db`** so it never collides with Hermes session schema.

---

## Run

```bash
conductor mcp                 # stdio server (default)
conductor mcp catalog         # human summary
conductor mcp tools           # list tool names
conductor mcp catalog --json  # full catalog JSON
python -m conductor.mcp       # same as conductor mcp
the-conductor-mcp             # console script
```

Logs go to **stderr**; **stdout** is the MCP wire.

---

## Client config snippets

### Claude Desktop / Claude Code

`claude_desktop_config.json` (or Claude Code MCP settings):

```json
{
  "mcpServers": {
    "the-conductor": {
      "command": "/path/to/The Conductor/.venv/bin/python",
      "args": ["-m", "conductor.mcp"],
      "env": {
        "CONDUCTOR_HOME": "/home/you/.conductor",
        "CONDUCTOR_SOUL_MODE": "resonate"
      }
    }
  }
}
```

### Codex (OpenAI)

`~/.codex/config.toml`:

```toml
[mcp_servers.the-conductor]
command = "/path/to/The Conductor/.venv/bin/python"
args = ["-m", "conductor.mcp"]

[mcp_servers.the-conductor.env]
CONDUCTOR_HOME = "/home/you/.conductor"
```

### Cursor

Settings → MCP → Add server:

```json
{
  "the-conductor": {
    "command": "/path/to/The Conductor/.venv/bin/python",
    "args": ["-m", "conductor.mcp"],
    "env": { "CONDUCTOR_HOME": "/home/you/.conductor" }
  }
}
```

### Grok / Grok Build TUI

`~/.grok/config.toml` (stdio; restart session or reload MCP to pick up):

```toml
[mcp_servers.the-conductor]
command = "/path/to/The Conductor/.venv/bin/python"
args = ["-m", "conductor.mcp"]
enabled = true
startup_timeout_sec = 45

[mcp_servers.the-conductor.env]
CONDUCTOR_HOME = "/home/you/.conductor"
CONDUCTOR_SOUL_MODE = "resonate"
PYTHONUNBUFFERED = "1"
```

CLI: `grok mcp add the-conductor -e CONDUCTOR_HOME=$HOME/.conductor -- /path/to/.venv/bin/python -m conductor.mcp`

**Sessions:** always `$CONDUCTOR_HOME/conductor_state.db` (never Hermes `state.db`).

**MCP arg aliases** (model-friendly): `goal`/`task` → `intent` on `combo_route`; `name` → `title` on tracks; `search`/`find` → memory search; `proposal` → `description` on ethics. Prefer canonical schema fields when you know them.

**Soft errors:** tools that fail with `"Error: …"` strings (or JSON `{error}`) are returned with MCP `CallToolResult.isError=true` so clients can treat them as failures, not success.

**Memory:** `memory_episodic` supports `tags`/`tag` on **write** and `action=search` with `query` (content + tags, case-insensitive).

**Remnants:** merge requires prior `action=spawn` (error text tells you this).

---

## Tools exposed

| Group | Examples |
|-------|----------|
| **Meta** | `conductor_module_info`, `conductor_system_prompt`, `conductor_session` |
| **Orchestration** | `conductor_status`, `combo_route`, `pillar_status`, `conductor_worker` |
| **Pillars** | `track_orchestrate`, `memory_episodic`, `remnant_orchestrate`, `crucible_workspace` |
| **Governance** | `ethics_evaluate`, `governance_audit` |
| **Research** | `research_list`, `research_view` |
| **Agent** | `skills_list`, `skill_view`, `heal_status`, `heal_attempt`, `promote_seal`, … |

**Not exposed** (hosts already have them): `read_file`, `write_file`, `run_shell` / terminal.

Pass **`session_id`** on tools that need continuity (tracks, remnants, memory). Create one with `conductor_session`.

---

## Resources

| URI | Content |
|-----|---------|
| `conductor://module` | version, skills, foundation |
| `conductor://pillars` | catalog + live probes |
| `conductor://soul` | partner SOUL.md |
| `conductor://skills` | skill index JSON |
| `conductor://combos` | combos A–H + workflows |

---

## Prompts

| Name | Purpose |
|------|---------|
| `system` | Soul Resonance system prompt (optional `host_soul`, `mode`) |
| `resonate` | Diagnostics + dual-wavelength prompt |
| `plan` | Grounded plan skill for a `goal` |

---

## Suggested agent loop

### Preferred: start pack (1.11+; parent spawn protocol 1.14+)

**MCP cannot spawn subagents.** Only the host (Grok `spawn_subagent`, Hermes `delegate_task`) can.

1. **`conductor_start_pack`** with `goal`  
   - **`orchestration.mode`**: `thin` | `full` (default thin unless multi-axis)  
   - **thin** → host tools only + optional memory (no fanout)  
   - **full** → `fanout_ready` with `dispatch=host` + axes  
2. If **full**: `remnant_orchestrate` with `fanout_ready` args  
   - Response includes `parent_must_spawn`, `tool_calls[]`, optional `hermes_batch`  
   - **Parent (not MCP):** execute **every** Grok `spawn_subagent(**tool_calls[i].arguments)` in parallel  
     (Hermes: prefer one `delegate_task` with `hermes_batch.arguments`)  
   - **`spawn_ack`** with `[{remnant_id, clone_handle}, …]`  
   - **`report`** each → **`merge`**  
3. If **thin**: skip remnants; ship with host tools; memory write  
4. See **docs/ORCHESTRATION.md**, **docs/SHADOW_CLONES.md**, **docs/HERMES_SUBAGENT_FANOUT.md**  


### Skip by default

`pillar_status`, full `conductor_module_info`, `governance_audit`, `research_list` — only when you need them.

### Remnant policy

| Use | Skip |
|-----|------|
| True parallel axes (UI + rules + graph, A vs B) | Single linear path, <~30 min toy, one-file fix |

---

## Verify

```bash
pip install -e ".[mcp]"
conductor mcp catalog
conductor mcp tools

# Smoke dispatch without stdio client
python -c "
from conductor.mcp.catalog import dispatch_tool, tool_definitions
print(len(tool_definitions()), 'tools')
print(dispatch_tool('conductor_module_info', {})[:200])
print(dispatch_tool('pillar_status', {'action': 'list'})[:300])
"
```

---

## Related

| Doc | Role |
|-----|------|
| [HERMES.md](HERMES.md) | Hermes plugin (in-process) |
| [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md) | Python harness API |
| [SOUL_RESONANCE.md](SOUL_RESONANCE.md) | Meister + partner |
| [PILLARS.md](PILLARS.md) | Pillar foundation |
