# Integrating The Conductor into any AI harness

The Conductor is a **skillset module**, not a full agent product. Hosts clone this repo (or install the package) and wire it into their loop.

**Full agent-facing guide (Hermes, OpenClaw, custom loops):**  
→ **[MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md)**

## 1. Install the package

```bash
git clone https://github.com/PabloTheThinker/the-conductor-hermes.git
cd the-conductor-hermes
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 2. Install into a home directory

```python
from conductor.harness import install, module_info, list_skills, tool_schemas, hooks, get_system_prompt

# Generic: any agent (skills + SOUL + config only)
install(home="~/.conductor", harness="generic")

# Hermes: also places plugins/conductor for stock Hermes
install(home="~/.hermes", harness="hermes")
```

CLI:

```bash
export CONDUCTOR_HOME=~/.conductor
conductor module install --harness generic
conductor module info
conductor module skills
conductor module tools
```

## 3. Wire your agent loop

### System prompt

```python
from conductor.harness import get_system_prompt
system = get_system_prompt()
# prepend/append to your harness system message
```

### Tools (OpenAI-style)

```python
from conductor.harness import tool_schemas, execute_tool
tools = tool_schemas()
# register with your harness
# on tool call:
result = execute_tool(name, arguments, session_id=session_id)
```

### Safety / memory hooks (optional)

```python
from conductor.harness import hooks
h = hooks()
# before tool: h.pre_tool_call(tool_name=..., args=...)
# after fail:  h.transform_tool_result(...)
# before LLM:  h.pre_llm_call(session_id=..., user_message=...)
```

### Skills (progressive disclosure)

```python
from conductor.harness import list_skills
for s in list_skills():
    print(s.name, s.description)
# bodies: $CONDUCTOR_HOME/skills/conductor/*/SKILL.md
```

## 4. Hermes (optional adapter)

```bash
export HERMES_HOME=~/.hermes
export CONDUCTOR_HOME=$HERMES_HOME
conductor setup --harness hermes
# ensure import conductor in Hermes process:
#   hermes-venv/bin/pip install -e .
#   # or: conductor hermes
hermes model
hermes
```

## 5. Discovery

```python
from conductor.harness import module_info
print(module_info())
# name, version, role: skillset-module, skills, adapters, home
```

## Contract

| Host provides | Conductor provides |
|---------------|-------------------|
| Agent loop / TUI | SOUL + skill pack |
| Model auth (or test provider) | Tool schemas + `execute_tool` |
| Optional tool/LLM hooks | Path-safety + thrash + memory inject |
| Home directory | `install()` layout |

No host fork required. Clone → install module → call API.
