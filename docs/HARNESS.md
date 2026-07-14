# Portable skillset module

The Conductor is a **portable skillset module** — installable on any machine, with **no site-specific infrastructure required**.

## Surfaces

```
The Conductor/          ← this repository
├── src/conductor/      package (import conductor)
├── skills/conductor/   skill pack
├── hermes_plugin/      optional Hermes adapter
├── SOUL.md · pillar docs · tests
└── docs/               INTEGRATION · OPERATORS · ARCHITECTURE
```

| Anyone can… | Nobody is forced to… |
|-------------|----------------------|
| `pip install -e .` and use `conductor` | Run Hermes |
| Use their own `CONDUCTOR_HOME` (`~/.conductor`) | Share a private mesh or VPN |
| Wire `conductor.harness` into any agent loop | Adopt a second product TUI |
| Run offline with `CONDUCTOR_PROVIDER=test` | Import operator topology or accounts |

## What ships

- `src/conductor/` — module runtime + offline brain helpers
- `SOUL.md` — portable conductor identity
- `skills/conductor/` — plan, review, remnant-guide
- Pillar docs, governance, ethics, tests
- Optional Hermes plugin under `hermes_plugin/conductor/`

## What does not ship

| Content | Where it belongs |
|---------|------------------|
| Host topology, Tailscale, accounts | Operator machine / private packs only |
| API keys | `$CONDUCTOR_HOME/.env` or host secrets |
| Site-specific skills | Outside this repo unless you add them |

## Install

**Any harness:**

```bash
cd the-conductor-hermes
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export CONDUCTOR_HOME="${CONDUCTOR_HOME:-$HOME/.conductor}"
conductor module install --harness generic
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```

**Hermes host:**

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export CONDUCTOR_HOME="$HERMES_HOME"
conductor setup --harness hermes
hermes model && hermes
```

Full guides: [INTEGRATION.md](INTEGRATION.md), [OPERATORS.md](OPERATORS.md).

## Design rules

1. Portable by default  
2. One SOUL — no dual product identity  
3. Site data is user data  
4. Offline tests without VPN/GPU  
5. Done = proven (Judgment)  
