# History (retired paths)

This document is **historical only**. Current install and integration:

- [INTEGRATION.md](INTEGRATION.md) — any harness  
- [OPERATORS.md](OPERATORS.md) — Hermes operators  
- [ARCHITECTURE.md](ARCHITECTURE.md) — system map  

## What was retired

| Former surface | Status |
|----------------|--------|
| Product brand **ILO** / I.L.O. | Replaced by **The Conductor** |
| Python package `ilo` | Renamed to `conductor` |
| CLI `ilo` | Removed; use `conductor` |
| Hermes plugin `plugins/ilo` | Replaced by `plugins/conductor` |
| Private Hermes fork branch | Not required; use stock Hermes |
| Dual-stack monorepo + Relay pin | Archived off this repo |
| Fable product skill pack seed | Not shipped; cleanup on `conductor setup` |

## Env / home (then → now)

| Legacy | Current |
|--------|---------|
| `ILO_HOME` / `~/.ilo` | `CONDUCTOR_HOME` / `~/.conductor` (or shared `HERMES_HOME`) |
| `ILO_PROVIDER` | `CONDUCTOR_PROVIDER` |
| `ILO_WORKSPACE` | `CONDUCTOR_WORKSPACE` |
| Offline OK token `ILO_OK` | `CONDUCTOR_OK` |

Legacy env names and `~/.ilo` are still **accepted** where noted in code for existing machines.

## Operator cutover (one-time)

If you still have an old home:

```bash
export CONDUCTOR_HOME="${HERMES_HOME:-$HOME/.hermes}"
# or: export CONDUCTOR_HOME=$HOME/.conductor
pip install -e ".[dev]"
conductor setup --harness hermes   # also removes plugins/ilo + skills/fable
hermes
```

Offline check:

```bash
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```
