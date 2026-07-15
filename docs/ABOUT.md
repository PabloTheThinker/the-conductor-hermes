# About The Conductor

Product context for operators, partners, and contributors — **module-first**, no host-identity claim.

---

## What it is

**The Conductor** is an open-source **skillset module** and **MCP server** for AI agent harnesses. It is designed to **enhance** a capable host agent — not replace the host’s identity, chat surface, or tool runtime.

| Surface | Role |
|---------|------|
| **Hermes plugin** | First-class load path under a stock Hermes Agent install |
| **stdio MCP** | Same orchestration surface for Claude, Codex, Cursor, Grok, and other MCP clients |
| **Harness API** | Embeddable module boundary for custom agent loops |

**Design principles**

- **Module, not a product fork** — hosts keep TUI, auth, and native tools  
- **Plugin XOR MCP** — pick one integration path per process; no dual scheduler  
- **Waves advisory only** — host owns tool-batch segmentation  
- **Safety spine** — path policy, healing scars, ethics, and governance as first-class structure  
- **Ship > perfect** — tested releases, documented ops, honest changelogs  

**Package:** `the-conductor` (import `conductor`) · **License:** MIT · **Language:** Python 3.11+

**Repository:** [github.com/PabloTheThinker/the-conductor-hermes](https://github.com/PabloTheThinker/the-conductor-hermes)

Primary host reference: **[Hermes Agent](https://hermes-agent.nousresearch.com/)** by [Nous Research](https://nousresearch.com) — The Conductor is an independent module, not a Hermes fork and not affiliated with Nous Research.

---

## Contact & security

- **General / product:** open a [GitHub Issue](https://github.com/PabloTheThinker/the-conductor-hermes/issues) on this repository  
- **Security:** see [SECURITY.md](../SECURITY.md) — report privately via [GitHub Security Advisories](https://github.com/PabloTheThinker/the-conductor-hermes/security/advisories/new); do not file public exploit details  

---

## Related reading

| Doc | Why |
|-----|-----|
| [README](../README.md) | Product face, install, paths |
| [MODULE_FOR_AGENTS](MODULE_FOR_AGENTS.md) | What “module” means for hosts |
| [HERMES](HERMES.md) | Hermes plugin integration |
| [MCP](MCP.md) | External meister path |
| [SECURITY](../SECURITY.md) | Disclosure policy |
| [HISTORY](HISTORY.md) | Retired naming / fork paths (historical) |

---

*MIT · The Conductor*
