# Operators guide

The Conductor is a **skillset module** you attach to an AI harness — it **enhances** the host agent.

- **Hermes (full):** [HERMES.md](HERMES.md) — **start here for stock Hermes**
- **Any harness (code):** [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md) · [INTEGRATION.md](INTEGRATION.md)
- **Benchmarks:** [BENCHMARKS.md](BENCHMARKS.md)

## Hermes (any stock agent)

```bash
git clone https://github.com/PabloTheThinker/the-conductor-hermes.git
cd the-conductor-hermes
./scripts/install_for_hermes.sh

export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
source "$HERMES_HOME/conductor.env"
hermes plugins list
hermes model
hermes
```

In a Hermes session: `/pillars status` · `/combo recommend …` · `/conductor-status`

CLI is `conductor …` or **`python -m conductor …`** (same entry).

### Health

```bash
conductor hermes-ready
conductor doctor --hermes
conductor hermes-ready --install-pip   # fix: package not importable in Hermes venv
# or: python -m conductor hermes-ready
```

### Dual-load rule

Use the **in-process plugin** *or* the **MCP stdio server** for external meisters — not both in the same Hermes process. Do not add `the-conductor` to Hermes `mcp_servers` when `plugins.enabled` already includes `conductor`.

### What setup does *not* do

- Does **not** replace Hermes `SOUL.md` (meister identity stays Hermes)
- Does **not** override Hermes tools (`terminal`, `delegate_task`, files, …)
- Does **not** require a Hermes fork

## Generic host (no Hermes)

```bash
export CONDUCTOR_HOME=~/.conductor
conductor module install --harness generic
# wire conductor.harness in your agent — see MODULE_FOR_AGENTS.md
```

## Offline smoke

```bash
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```
