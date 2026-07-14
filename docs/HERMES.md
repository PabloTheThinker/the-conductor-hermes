# Hermes + The Conductor

How **any stock Hermes agent** uses The Conductor as an enhancement module — not a fork, not a second product.

**Product line:** Conductor **enhances** the Hermes agent (Soul Resonance). Hermes remains the meister (TUI, auth, tool loop, SOUL.md). Conductor is the partner wavelength (tools, spine, pillars, skills).

**Supported Hermes:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (upstream main or release). No private fork required.

---

## One-command install (any machine)

```bash
git clone https://github.com/PabloTheThinker/the-conductor-hermes.git
cd the-conductor-hermes
./scripts/install_for_hermes.sh
# or:
# python3 -m venv .venv && source .venv/bin/activate
# pip install -e ".[dev]"
# export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
# export CONDUCTOR_HOME="$HERMES_HOME"
# conductor setup --harness hermes --install-pip
```

Then:

```bash
source "$HERMES_HOME/conductor.env"
hermes plugins list          # should show conductor
hermes model                 # auth
hermes
# In session: /pillars status · /combo recommend … · /conductor-status
```

**Health checklist**

```bash
conductor hermes-ready
# or
conductor doctor --hermes
```

---

## How Hermes discovers plugins (stock)

From Hermes `hermes_cli/plugins.py`:

| Source | Path | Priority |
|--------|------|----------|
| Bundled | `<repo>/plugins/<name>/` | lowest |
| User | `$HERMES_HOME/plugins/<name>/` | overrides bundled |
| Project | `./.hermes/plugins/<name>/` | opt-in |
| Pip | entry-point `hermes_agent.plugins` | can override |

Conductor supports **both**:

1. **User plugin** — `conductor setup` copies `hermes_plugin/conductor` → `$HERMES_HOME/plugins/conductor/`  
2. **Pip entry-point** — `pip install the-conductor` registers  
   `hermes_agent.plugins` → `conductor = conductor.adapters.hermes.plugin`

Each plugin needs `plugin.yaml` + `register(ctx)`.

### Hooks Conductor uses

| Hook | Hermes event | Conductor role |
|------|--------------|----------------|
| `pre_tool_call` | Before any tool | Path-safety / mass-wipe / thrash guard (**blocks** dangerous host tools) |
| `transform_tool_result` | After tool result | Integrity cascade on failures |
| `on_session_start` | Session open | Bind session id + Soul Resonance + `CONDUCTOR_HOST=hermes` |
| `pre_llm_call` | Before model turn | Live memory inject (scars / seals / episodes) |

### Skills on Hermes

- Flat skills: `$HERMES_HOME/skills/conductor/**/SKILL.md` (seeded by setup)  
- Plugin skills: `ctx.register_skill` → namespaced opt-in  

### Identity (Soul Resonance)

| File | Role |
|------|------|
| `$HERMES_HOME/SOUL.md` | **Meister** — Hermes identity (Hermes seeds this; Conductor never overwrites it) |
| `$HERMES_HOME/CONDUCTOR_PARTNER_SOUL.md` | **Partner** — Conductor wavelength (written by setup) |

```bash
export CONDUCTOR_HOST_SOUL="$HERMES_HOME/SOUL.md"
export CONDUCTOR_PARTNER_SOUL="$HERMES_HOME/CONDUCTOR_PARTNER_SOUL.md"
export CONDUCTOR_SOUL_MODE=resonate   # default
```

See [SOUL_RESONANCE.md](SOUL_RESONANCE.md).

---

## What `conductor setup` writes

| Artifact | Purpose |
|----------|---------|
| `$HERMES_HOME/plugins/conductor/` | Plugin package (`plugin.yaml` + bootstrap) |
| `$HERMES_HOME/skills/conductor/*` | plan, review, remnant-guide, combo, pillars |
| `$HERMES_HOME/config.yaml` | `plugins.enabled` includes `conductor` |
| `$HERMES_HOME/conductor_package_root` | Import path bootstrap if not pip-installed |
| `$HERMES_HOME/conductor.env` | Shell exports (`HERMES_HOME`, `CONDUCTOR_*`, `PYTHONPATH`) |
| `$HERMES_HOME/CONDUCTOR_PARTNER_SOUL.md` | Partner SOUL (meister SOUL left alone) |

Optional: `--install-pip` installs the package into the **Hermes venv** so plugins import without PYTHONPATH.

---

## What the Hermes agent gets

### Tools (Conductor-native — no clash with Hermes core)

| Toolset | Examples |
|---------|----------|
| `conductor` | `crucible_workspace`, `remnant_orchestrate`, `track_orchestrate`, `memory_episodic`, `combo_route`, `pillar_status`, `ethics_evaluate`, `governance_audit`, `conductor_status`, `conductor_worker` |
| `research` | `research_list`, `research_view` |
| `conductor_agent` | `skills_*`, `heal_*`, `promote_seal`, `verification_list` |

**Not registered (by design):** Hermes already owns these — Conductor **never** overrides them:

- `read_file`, `write_file`, `terminal`, `process`, `patch`, `search_files`
- `web_search`, browser tools, `todo`, `skill_manage`
- **`delegate_task`** — native Hermes subagent spawn (use this for real clones)

Offline shell helper is named **`conductor_worker`** (not `delegate_task`) to avoid name collision.

**Spine still gates** Hermes host tools via `pre_tool_call` (blocks mass-wipe / catastrophic shell).

### Slash commands

| Command | Role |
|---------|------|
| `/crucible` | Global Workspace / Noesis |
| `/pillars` | Foundation catalog + probes |
| `/combo` | Recommend pillar stack A–H |
| `/remnant` | Spawn / fanout / merge |
| `/track` | Chessboard / create / fork |
| `/conductor-status` | Hermes readiness checklist |

### Parallel work (full orchestration)

When goals need multiple axes, use start pack → fanout with `dispatch=hermes` (or `auto` when `CONDUCTOR_HOST=hermes`):

1. Fanout returns **`hermes_batch`** / exact `delegate_task(goal, context)` payloads  
2. **You** (the Hermes agent) call native **`delegate_task`** (prefer one batch `tasks[]`)  
3. Report findings via `remnant_orchestrate action=report`  
4. Merge via `remnant_orchestrate action=merge`  

See [ORCHESTRATION.md](ORCHESTRATION.md) · [HERMES_SUBAGENT_FANOUT.md](HERMES_SUBAGENT_FANOUT.md).

---

## Architecture (roles)

```
┌─────────────────────────────────────────────┐
│  Operator                                   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Hermes (meister) — any stock agent         │
│  TUI · auth · model · tool loop · SOUL.md   │
│  plugins.enabled: [conductor, …]            │
│  native: terminal, files, delegate_task     │
└──────────────────┬──────────────────────────┘
                   │ register(ctx)
┌──────────────────▼──────────────────────────┐
│  Conductor plugin (partner)                 │
│  tools · hooks · slash · skills · spine     │
│  Soul Resonance · pillars · Remnants        │
└─────────────────────────────────────────────┘
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Plugin missing | `conductor setup --harness hermes` |
| `import conductor` fails inside Hermes | `conductor hermes-ready --install-pip` or install into Hermes venv |
| Tools missing | `hermes plugins list` · `plugins.enabled` · `HERMES_PLUGINS_DEBUG=1 hermes` |
| SOUL conflict | Keep Hermes `SOUL.md` as meister; partner is `CONDUCTOR_PARTNER_SOUL.md` |
| Fanout without clones | Must call native `delegate_task` — reading tool_calls alone is theater |

```bash
# Offline Conductor brain (no Hermes UI)
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```

---

## Related

| Doc | Role |
|-----|------|
| [OPERATORS.md](OPERATORS.md) | Short operator steps |
| [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md) | Any harness |
| [SOUL_RESONANCE.md](SOUL_RESONANCE.md) | Meister + partner |
| [ORCHESTRATION.md](ORCHESTRATION.md) | Thin/full + spawn |
| [BENCHMARKS.md](BENCHMARKS.md) | Hermes stress vs probes |
