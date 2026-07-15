# Soul Resonance

**The Conductor enhances the agent that uses it.**

It locks wavelength with Hermes, OpenClaw, or any host soul — it does not replace them. The host stays the meister (name, voice, personality). Conductor is the partner wavelength: tracks, tools, Remnants, Crucible, healing, Judgment.

Metaphor (Soul Eater, not copyrighted plot): **meister + partner**. Two souls, one will on the mission. Wrong wavelength = thrash. True resonance = **enhance**.

---

## Roles

| Role | Source | Keeps |
|------|--------|--------|
| **Meister** | Host SOUL / IDENTITY / AGENTS | Name, voice, personality, operator bond |
| **Partner** | Conductor `SOUL.md` | Tracks, Remnants, Crucible, healing spine, Judgment |

Shared **spine** (neither may dissolve): ethics checklist, path-safety floors, done = proven.

---

## How hosts wire it

### Python (any agent)

```python
from conductor.harness import get_system_prompt, resonate_souls

# Auto-discover host soul (HERMES_HOME, OPENCLAW_HOME, ~/.hermes, …)
system = get_system_prompt()

# Or pass meister soul explicitly (path or full text)
system = get_system_prompt(host_soul="~/.hermes/IDENTITY.md")
system = get_system_prompt(host_soul=open("my-agent-SOUL.md").read())

# Diagnostics
info = resonate_souls(host_soul="~/.openclaw/SOUL.md")
assert info["resonant"] or info["mode"] == "solo"
```

### Env

| Variable | Meaning |
|----------|---------|
| `CONDUCTOR_HOST_SOUL` | Path to meister soul file **or** inline body |
| `CONDUCTOR_PARTNER_SOUL` | Path to Conductor **partner** soul file (wavelength). Required when meister and partner share a home directory. |
| `CONDUCTOR_SOUL_MODE` | `resonate` (default) · `solo` · `host_only` |
| `HERMES_HOME` / `OPENCLAW_HOME` | Search roots for `SOUL.md`, `IDENTITY.md`, `AGENTS.md` |

Partner path resolution (``soul_path()``):

1. `CONDUCTOR_PARTNER_SOUL` env (file)  
2. `$CONDUCTOR_HOME/CONDUCTOR_PARTNER_SOUL.md`  
3. `$CONDUCTOR_HOME/SOUL.md` only when partner-shaped and not the meister path  
4. Package/canonical `SOUL.md`

### Overlay file

Place meister text at:

```text
$CONDUCTOR_HOME/HOST_SOUL.md
```

Used when auto-discovery finds no other host soul.

### Hermes

```bash
export HERMES_HOME=~/.hermes
export CONDUCTOR_HOME=$HERMES_HOME
export CONDUCTOR_HOST_SOUL="$HERMES_HOME/SOUL.md"              # meister
export CONDUCTOR_PARTNER_SOUL="$HERMES_HOME/CONDUCTOR_PARTNER_SOUL.md"  # partner
# Keep Hermes identity as meister (SOUL.md / IDENTITY.md / AGENTS.md)
# Conductor partner is seeded as CONDUCTOR_PARTNER_SOUL.md — never overwrites meister
conductor setup --harness hermes
```

When homes are **shared**, Conductor will **not** treat meister `SOUL.md` as the partner wavelength. Partner is always `CONDUCTOR_PARTNER_SOUL.md` (or `CONDUCTOR_PARTNER_SOUL` env). Prefer a distinct host file when both exist (`IDENTITY.md`, `AGENTS.md`, or `HOST_SOUL.md`).

### OpenClaw / generic

```bash
export CONDUCTOR_HOME=~/.conductor
export OPENCLAW_HOME=~/.openclaw   # if used
export CONDUCTOR_HOST_SOUL=~/.openclaw/SOUL.md
conductor module install --harness generic
```

In OpenClaw system instructions: inject `get_system_prompt()` (or the `prompt` field from `resonate_souls()`).

### Slash

```text
/soul status
/soul resonate
/soul integrity
```

---

## Modes

| Mode | Behavior |
|------|----------|
| **resonate** | Meister + Partner blocks + resonance rules (default) |
| **solo** | Conductor partner only (offline / no host) |
| **host_only** | Meister only (Conductor tools still available via API) |

---

## What the merged prompt contains

1. Resonance rules table (meister primary, partner amplifies, shared spine)  
2. Full **meister** soul text  
3. Full **partner** Conductor `SOUL.md`  
4. Skills index + research index + optional memory block  

See `src/conductor/soul/resonance.py`.

---

## Rules of engagement (product)

1. Host identity **names the self**.  
2. Conductor **enhances** — more capability, same meister face.  
3. Safety floors stay on even if the host soul is silent about them.  
4. Remnants / Crucible serve the **resonant will**, not a second ego.  
5. Operator remains sovereign.  

**One line:** plug Conductor in → the agent you already love gets conductor-grade rails.

---

## Related

- Partner SOUL text: repo root `SOUL.md`  
- Module install: [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md)  
- Pillars: [PILLAR_COMBOS.md](PILLAR_COMBOS.md)  
