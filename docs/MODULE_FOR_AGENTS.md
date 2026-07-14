# The Conductor as a module — guide for any AI agent

**Audience:** Hermes, OpenClaw, Claude Code, Cursor agents, custom tool loops, or any harness that can install a Python package and register tools.

**What this is:** The Conductor is a **skillset module that enhances the host agent** (Soul Resonance + skills + tools + safety hooks).  
**Also:** an **MCP server** (`conductor mcp`) so Claude, Codex, Cursor, Grok, and other MCP clients use the same tools — see [MCP.md](MCP.md).  
**What this is not:** A second chat app, a replacement identity, a Hermes fork, or a required TUI.

| | Host agent (meister) | Conductor (enhancement) |
|---|------------|---------------------------|
| Owns | Name, voice, loop, model auth, UI | Partner SOUL, skills, tool handlers, spine |
| Installs | Already your agent | `pip install` this package → `CONDUCTOR_HOME` |
| Calls | Your LLM + tool router | `conductor.harness.*` (resonates with you) |

**Repo:** https://github.com/PabloTheThinker/the-conductor-hermes  
**Package:** `the-conductor` · import name: `conductor`  
**Primary API:** `conductor.harness`

---

## 60-second path (any host)

```bash
git clone https://github.com/PabloTheThinker/the-conductor-hermes.git
cd the-conductor-hermes
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

export CONDUCTOR_HOME="${CONDUCTOR_HOME:-$HOME/.conductor}"
conductor module install --harness generic
conductor module info
```

In your agent process:

```python
from conductor.harness import (
    install,
    module_info,
    get_system_prompt,
    list_skills,
    tool_schemas,
    execute_tool,
    hooks,
)

install(home="~/.conductor", harness="generic")  # once per machine/home

info = module_info()           # discovery
# Soul Resonance: locks with host meister soul (does not replace it)
system = get_system_prompt(host_soul="~/.openclaw/SOUL.md")  # or auto-discover
tools = tool_schemas()         # OpenAI-style function schemas
skills = list_skills()         # plan, review, remnant-guide, combo, …

# On each tool call from the model:
result = execute_tool(name, arguments, session_id=session_id)

# Optional safety spine:
h = hooks()
# before tool: h.pre_tool_call(...)
# after fail:  h.transform_tool_result(...)
# before LLM:  h.pre_llm_call(session_id=..., user_message=...)
# session start: h.on_session_start(session_id=...)
```

Offline smoke (no API key):

```bash
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```

---

## Contract (what you must provide)

| Host provides | Conductor provides |
|---------------|-------------------|
| Running Python ≥ 3.11 agent process | Package `conductor` |
| Durable home path (`CONDUCTOR_HOME`) | Skills, SOUL, config, SQLite state under that home |
| Model / auth (or offline test provider) | Tool schemas + `execute_tool` |
| Tool registration + dispatch | Path-safety, thrash guard, memory inject hooks |
| Optional: slash/skill invocation UX | Progressive skills (`SKILL.md` bodies) |

**No host fork required.** Clone → install module → call API.

---

## Environment

| Variable | Purpose | Default / notes |
|----------|---------|-----------------|
| `CONDUCTOR_HOME` | Durable state (skills, SOUL, sessions, config) | `~/.conductor` (or shared with host) |
| `HERMES_HOME` | When using Hermes, set equal to Conductor home | Share config/auth with Hermes |
| `CONDUCTOR_PROVIDER` | Offline/tests: `test` | Production: host model |
| `CONDUCTOR_WORKSPACE` | Optional project root confinement | Spine blocks writes outside tree |
| `CONDUCTOR_ROOT` | Override checkout root for research specs | Auto-detected from package |

Legacy `ILO_*` names may still be accepted in a few places; prefer `CONDUCTOR_*`.

---

## Module API reference

All entry points live on **`conductor.harness`**.

### `module_info(home=None) -> dict`

Machine-readable discovery for catalogs and “is Conductor installed?” checks.

```python
{
  "name": "the-conductor",
  "version": "1.5.3",
  "role": "skillset-module",
  "description": "...",
  "home": "/path/to/home",
  "skills": ["combo", "plan", "remnant-guide", "review"],
  "adapters": ["hermes", "generic"]
}
```

### `install(home=None, harness="generic", force=True) -> dict`

Seeds skills + SOUL + config into `home`.

| `harness` | Effect |
|-----------|--------|
| `"generic"` | Skills + SOUL + config only — **use for OpenClaw / custom agents** |
| `"hermes"` | Also installs `plugins/conductor` + bootstrap for stock Hermes |

CLI equivalent:

```bash
conductor module install --harness generic
conductor setup --harness hermes    # Hermes operators
```

### `get_system_prompt(memory_block="", host_soul=None, mode=None, search_host=True) -> str`

**Soul Resonance** prompt: meister (host soul) + Conductor partner SOUL + skills/research index.  
Does not replace your agent’s identity — locks wavelength with it. See [SOUL_RESONANCE.md](SOUL_RESONANCE.md).

### `resonate_souls(host_soul=None, mode=None, search_host=True) -> dict`

Diagnostics + full `prompt` for hosts that compose system messages themselves.

### `list_skills(home=None) -> list[SkillInfo]`

`name`, `description`, `path` for progressive disclosure. Bodies live under:

```text
$CONDUCTOR_HOME/skills/conductor/<name>/SKILL.md
```

Bundled skills today: **`plan`**, **`review`**, **`remnant-guide`**, **`combo`**.

### `tool_schemas() -> list[dict]`

OpenAI-compatible tool definitions. Register them on your agent’s tool list.

### `execute_tool(name, arguments, *, session_id="") -> str`

Run a Conductor tool. Pass a stable `session_id` per conversation so memory/scars/tracks stick together. If empty, a new session is created.

### `hooks() -> HarnessHooks`

Optional spine for hosts that can wrap tool and LLM calls:

| Hook | When | Role |
|------|------|------|
| `pre_tool_call` | Before any host/Conductor tool | Block mass-wipe, enforce workspace |
| `transform_tool_result` | After failed tool | Integrity cascade annotations |
| `pre_llm_call` | Before model turn | Inject scars/seals/episodes |
| `on_session_start` | Session open | Bind `session_id` for healing |

---

## Minimal host loop (pseudocode)

```python
from conductor.harness import install, get_system_prompt, tool_schemas, execute_tool, hooks

install(harness="generic")
h = hooks()
session_id = "my-agent-session-001"
h.on_session_start(session_id=session_id)

messages = [
    {"role": "system", "content": get_system_prompt()},
    {"role": "user", "content": user_text},
]
tools = tool_schemas()

while True:
    # Optional: inject live memory into the user turn
    extra = h.pre_llm_call(session_id=session_id, user_message=user_text)
    # (host merges extra context if returned)

    response = your_llm.chat(messages, tools=tools)

    if not response.tool_calls:
        break

    for call in response.tool_calls:
        # Optional spine before execution
        block = h.pre_tool_call(tool_name=call.name, args=call.arguments)
        if block:
            result = block  # string deny message
        else:
            # Conductor tools go through execute_tool;
            # host-native tools you run yourself, then still can pass fail through transform
            if call.name in conductor_tool_names:
                result = execute_tool(call.name, call.arguments, session_id=session_id)
            else:
                result = run_host_tool(call)
                result = h.transform_tool_result(
                    tool_name=call.name, result=result, args=call.arguments
                ) or result

        messages.append({"role": "tool", "name": call.name, "content": result})
```

---

## Adapter: Hermes (stock)

**Full guide:** [HERMES.md](HERMES.md) · **Benchmarks:** [BENCHMARKS.md](BENCHMARKS.md)

Hermes owns TUI, auth, and the tool loop. Conductor is a **plugin + skills pack**.

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export CONDUCTOR_HOME="$HERMES_HOME"

pip install -e .                    # into the same venv that runs hermes
conductor setup --harness hermes
hermes model                        # auth / provider
hermes
```

Or launch with package bootstrap:

```bash
conductor hermes
```

Plugin source: `hermes_plugin/conductor/` → `$HERMES_HOME/plugins/conductor`.  
Hooks registered: `pre_tool_call`, `transform_tool_result`, `on_session_start`, `pre_llm_call`.

See also: [OPERATORS.md](OPERATORS.md).

---

## Adapter: OpenClaw / generic Node or Python agents

Use **`harness="generic"`**. OpenClaw (or any host) does not need the Hermes plugin tree.

**Python host (same process):** use the Module API above.

**Separate process / non-Python host:**

1. Install Conductor in a venv on the machine.
2. Expose a thin bridge (subprocess or small HTTP/RPC wrapper) that calls:

```bash
# discovery
python -c "from conductor.harness import module_info; import json; print(json.dumps(module_info()))"

# execute a tool
python -c "
from conductor.harness import execute_tool
print(execute_tool('combo_route', {'action': 'recommend', 'intent': 'map risks'}))
"
```

3. Load `tool_schemas()` once and map them into OpenClaw’s tool format.
4. Load `get_system_prompt()` into the agent’s system/instructions field.
5. Point skill files at `$CONDUCTOR_HOME/skills/conductor/*/SKILL.md` if your host supports agentskills-style packs.

**Suggested env for OpenClaw operators:**

```bash
export CONDUCTOR_HOME="${CONDUCTOR_HOME:-$HOME/.conductor}"
export CONDUCTOR_PROVIDER=test   # only for offline dry-runs
```

---

## Tools you get (high level)

Registered via `tool_schemas()` / `execute_tool` (names may grow; always prefer live `tool_schemas()`):

| Area | Examples |
|------|----------|
| Files / shell (gated) | `read_file`, `write_file`, `run_shell` |
| Skills | `skills_list`, `skill_view`, `skill_manage` |
| Research specs | `research_list`, `research_view` |
| Orchestration | `conductor_status`, `delegate_task`, `combo_route` |
| Remnants | `remnant_orchestrate` |
| Tracks | `track_orchestrate` |
| Crucible / Noesis | `crucible_workspace` |
| Memory | `memory_episodic` |
| Governance / ethics | `ethics_evaluate`, `governance_audit` |
| Healing | `heal_status`, `heal_attempt`, `promote_seal`, `verification_list` |

**Combo router** (pick pillar stack A–H):

```python
execute_tool("combo_route", {
    "action": "recommend",   # or list | workflow | get
    "intent": "spawn parallel remnants to explore both approaches",
})
```

Pillar recipes: [PILLAR_COMBOS.md](PILLAR_COMBOS.md) · [WORKFLOWS.md](WORKFLOWS.md).

---

## Skills (progressive disclosure)

| Skill | Use |
|-------|-----|
| `plan` | Rollout plan + recommended combo A–H |
| `review` | Review gaps + evidence gate (Combo G) |
| `remnant-guide` | When to spawn Remnants (Combo C) |
| `combo` | Recommend / explain combos |

Invoke however your host exposes skills (slash `/plan`, skill tool, or paste `SKILL.md` body into context).

---

## CLI surfaces (optional for agents)

Useful for setup and doctor; not required inside the hot loop:

```bash
conductor module info
conductor module install --harness generic|hermes
conductor module skills
conductor module tools
conductor doctor
conductor status
conductor setup --harness hermes
```

---

## Safety spine (why hooks matter)

Even if you only call `execute_tool`, enabling hooks protects the **host’s** shell/file tools too:

- Block mass-delete of `$HOME` / `/`
- Optional `CONDUCTOR_WORKSPACE` confinement
- Thrash guard (same tool+args repeated)
- Scars / seals / recovery imprints after wounds

Without hooks, Conductor still enforces floors on tools that go through `execute_tool`, but host-native tools are unprotected.

---

## Checklist for integrating agents

- [ ] `pip install -e .` (or wheel) in the process that runs the agent  
- [ ] `CONDUCTOR_HOME` set (and `HERMES_HOME` shared if Hermes)  
- [ ] `install(harness="generic"|"hermes")` once  
- [ ] System prompt uses `get_system_prompt()` (Soul Resonance with your host SOUL)  
- [ ] Meister soul available (`CONDUCTOR_HOST_SOUL`, `IDENTITY.md`, or host home)  

- [ ] Tools from `tool_schemas()` registered; dispatch to `execute_tool`  
- [ ] Stable `session_id` per conversation  
- [ ] Optional: wire `hooks()` pre_tool / pre_llm / session_start  
- [ ] Smoke: `CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'`  
- [ ] `module_info()["role"] == "skillset-module"` for discovery  

---

## Related docs

| Doc | For |
|-----|-----|
| [INTEGRATION.md](INTEGRATION.md) | Short API cheat sheet |
| [OPERATORS.md](OPERATORS.md) | Human Hermes operators |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pillars and package layout |
| [PILLARS.md](PILLARS.md) | Pillar foundation + live probes |
| [PILLAR_COMBOS.md](PILLAR_COMBOS.md) | Combos A–H |
| [WORKFLOWS.md](WORKFLOWS.md) | Combo step flows |
| [HARNESS.md](HARNESS.md) | Portable boundary rules |

---

## One-liner for other agents

> Install package `the-conductor`, call `conductor.harness.install()`, inject `get_system_prompt(host_soul=…)` so Conductor **enhances** your agent via Soul Resonance (same meister, more power), register `tool_schemas()` and dispatch to `execute_tool(session_id=…)`, optionally attach `hooks()` for path-safety and memory inject. Hermes uses `harness="hermes"`; OpenClaw and everyone else use `harness="generic"`.
