# Security Policy

## Supported versions

Security fixes land on the latest **1.18.x** line of The Conductor. Older tags are best-effort only.

## Reporting a vulnerability

Please report security issues **privately** to the maintainer (repository owner / Vektra Industries contact on the project page). Do **not** open a public issue with exploit details until a fix or coordinated disclosure plan exists.

Include:

- Affected version / commit
- Environment (OS, Python, host agent if relevant)
- Minimal reproduction
- Impact assessment (data exposure, RCE via host tools, path escape, etc.)

## Scope notes

The Conductor is a **host-agent module**. It inherits the authority of the host process and any tools the host grants (shell, files, network, MCP peers).

In-scope for product defects:

- Path-safety spine false negatives / bypasses of documented floors
- Secrets accidentally shipped in the **package tree** (examples, docs, defaults)
- Session / remnant continuity bugs that mis-route operator state across sessions
- MCP catalog exposing host-native tools that should stay host-owned

Out of scope (host / operator responsibility):

- Compromised host API keys, gateway tokens, or `HERMES_HOME` contents
- Operators binding dashboards or MCP to public interfaces without auth
- Prompt injection against the host model (mitigate at host policy layer)
- Supply-chain issues in third-party dependencies after install (report upstream too)

## Operational hygiene

- Never commit `.env`, `conductor.env`, session DBs, or host `config.yaml` with live credentials
- Prefer localhost binds for local dashboards; gate remote access explicitly
- Follow dual-load guidance: **plugin XOR MCP** in one Hermes process unless you know why you need both
