# Changelog

Notable changes. Newest first.

---

## [2026-07-15] — Host tool waves + batch-for-host (1.18.9)

### Added
- `conductor.core.wave_planner` — tool classes (`safe_parallel` / `barrier` / `spawn`), waves **A→B→C**, `plan_waves`, `parallel_recipe_thin`, `hybrid_safe_preflight_pack`
- Fanout / `hermes_batch` carry advisory `waves` + `batch_id` (thrash-aware)
- Thin + full orchestration recipes: `host_batch_policy`, wave order, anti “dual-own Hermes segmentation”
- `skills/conductor/batch-for-host` — when to batch host tools vs Remnant fanout
- `hermes-ready` / doctor info checks: `delegation_concurrency`, `delegation_spawn_depth`
- Batch-aware thrash: optional `batch_id` / `wave_id` on fingerprint (Hermes `pre_tool_call`)
- Docs: ORCHESTRATION tool classes + waves; HERMES “Host tool batch vs Remnant”
- `tests/test_wave_planner.py`

### Changed
- Version **1.18.9**
- Hybrid dispatch uses shared `hybrid_safe_preflight_pack` shape

### Fixed
- Guidance: do not serialize whole turns for one barrier tool among safe reads

---

## [2026-07-14] — Public hygiene + module CLI entry (1.18.8)

### Added
- `src/conductor/__main__.py` — `python -m conductor` same as console script
- `SECURITY.md` — vulnerability reporting + host-module scope notes
- `tests/test_cli_module_entry.py`
- Expanded `.gitignore` for secrets, env files, nested operator homes
- `config.example.yaml` dual-load rule + toolset schema comments (still does **not** pin `model.default`)

### Fixed
- `scripts/install_for_hermes.sh` falls back to `python -m conductor` when console script missing from PATH

### Changed
- Version **1.18.8**
- Operators guide notes dual-load (plugin XOR MCP) and module CLI entry

---

## [2026-07-14] — Server refresh + Hermes python unwrap (1.18.7)

### Fixed
- **hermes-ready false NOT READY** — `~/.local/bin/hermes` bash wrapper shebang was `/usr/bin/env`, so pip/import checks ran against `env` not the agent venv
- Unwrap wrapper → `~/.hermes/hermes-agent/venv/bin/python`; prefer known agent layouts
- `install_into_hermes_venv` falls back to **`uv pip install --python`** when pip module missing

### Changed
- Version **1.18.7**
- Reinstalled editable into Grok MCP venv + Hermes agent venv

### Accomplished
- `conductor hermes-ready` READY; MCP `python -m conductor.mcp` serves **1.18.7** with compliance action

---

## [2026-07-14] — Anti-theater + local builders (1.18.6)

Fixes from the deep “how Conductor actually works” critique.

### Fixed
- **Spawn theater** — host `report` without `clone_handle` blocked; merge blocked while `awaiting_host` / missing handles (`force` + `accept_theater` only override)
- **Local clones as scouts only** — with `work_root`, write `.conductor/clone_scrolls/` + greenfield stub files
- **Done without proof** — merge returns `judgment` / `done_proven` from evidence-shaped insights
- **Research / deploy routing** — domain axes + combo G boosts
- **Cognitive weight** — start_pack `simple_path` + `judgment`; operator one-pager

### Added
- `src/conductor/core/spawn_compliance.py`
- `remnant_orchestrate action=compliance`
- `docs/OPERATOR_FLOW.md`
- tests: `test_spawn_compliance.py`
- self_loop_study theater + scaffold probes

### Changed
- Version **1.18.6**
- Default `CONDUCTOR_STRICT_SPAWN=1`; opt-out `CONDUCTOR_LOCAL_SCAFFOLD=0`

### Accomplished
- Happy path: fanout → spawn_ack → report → merge → done_proven
- Theater path: merge/report raise; self_loop_study clean

---

## [2026-07-14] — Self-loop pass 2 (1.18.5)

Study after 1.18.4 was green: expand probes → find new mistakes → fix → grow harness.

### Fixed
- **Chess multi-system** (`fix chess AI…three.js`) routes **Combo C**, not Daily A
- **Integrate role** for game-loop glue (no double surface axes)
- **Short landing / N-section SaaS** → full mode + product lane (not thin/0 axes)
- **Official marketing sites** always get product/pillars axis
- **RPG** always includes character creation lane

### Added
- Expanded `scripts/self_loop_study.py` (chess fix, landing sections, RPG e2e, million-site, integrate pack)
- Tests for chess-fix C, landing multi-section, RPG character, official product axis
- LESSONS.md pass-2 entry

### Changed
- Version **1.18.5**

### Accomplished
- `python scripts/self_loop_study.py` clean; focused + full pytest green

---

## [2026-07-14] — Self-loop study improvements (1.18.4)

Study loop: audit routing from website + Stellar Codex runs → fix → retest.

### Fixed
- **RPG/D&D game goals** route **Combo C** (not bare A / accidental H via end-to-end)
- **RPG domain axis synth** — shell, rules, combat, world, character, meta
- **Roles** combat/world/character/meta on packs + work steps
- **Clone scan** content-peek source files so `js/game.js` matches combat tokens
- Entrypoint fallback (index.html / game.js) when token score is zero

### Added
- `scripts/self_loop_study.py` — regression harness for routing + clone scan
- Tests: dnd/scifi game routing; clone content scan
- LESSONS.md self-loop entry

### Changed
- Version **1.18.4**

### Accomplished
- hermes-ready READY; full pytest + self_loop_study clean after fixes

---

## [2026-07-14] — Demo: Stellar Codex (sci-fi D&D)

### Added
- **`demos/stellar-codex/`** full browser RPG (create, d20 combat, map, NPCs, quests, save/load)
- Conductor multi-lane plan: `demos/stellar-codex/CONDUCTOR_PLAN.json`
- Play: `python3 -m http.server 8770` from `demos/stellar-codex`

### Accomplished
- Fanout 6 lanes (UI/rules/combat/world/character/meta) + merge; endgame boss playable

---

## [2026-07-14] — Self-diagnose website-run limits (1.18.3)

After the official-site build: figure out why Conductor was a weak foreman and fix it.

### Fixed
- **Combo A on multi-section websites** — marketing/official/landing signals boost **Combo C**
- **Weak website axes** — domain synth: hero · product/pillars · hermes/docs · polish
- **Local greenfield theater** — clones name `website/…` deliverables instead of “plan-only (no root)”
- Work-pack roles: **product / docs / polish** with real steps

### Added
- LESSONS.md: website-run root causes + rules
- Tests: official website goal → C + domain axes; greenfield clone paths

### Changed
- Version **1.18.3**

### Accomplished
- Replayed original website goal: Combo C + 4 product lanes; greenfield reports actionable

---

## [2026-07-14] — Website: Conductor owns every section

### Added
- **`website/sections/01-*.json` … `08-*.json`** - one remnant work pack per marketing region
- **`website/CONDUCTOR_SECTIONS.json`** - index of lanes
- HTML `data-conductor-section` / `data-conductor-role` on nav, hero, product, pillars, modes, combos, install, close
- Debug mode: `?conductor=1` outlines each Conductor lane
- On-page lane map (01-08) in close section; Combo C marked as live for this build

### Changed
- Role inference: pillars/bento → product; manifesto/footer → polish (before docs/cta)

### Accomplished
- Fanout 8 section objectives (2×4), report, merge; site served with per-section ownership

---

## [2026-07-14] — Official website v2 improve pass

### Changed
- **`website/index.html`** - second design pass under Conductor Combo C + work_root fanout
- Added thin/full modes, combos A-H rail, install copy, scroll progress, a11y (skip/focus), OG meta

### Accomplished
- Conductor: Combo C, domain axes (surface/product/docs/polish), `work_root=website/`, merge
- Preview: `python3 -m http.server 8765` from `website/`

---

## [2026-07-14] — Official Conductor website (marketing)

### Added
- **`website/`** - premium official landing for The Conductor (dark ethereal glass)
- Generated brand stills: `website/assets/{hero,network,workspace}.jpg`
- Preview: `python3 -m http.server 8765` from `website/`

### Accomplished
- Conductor local fanout exercise (4 lanes) + full multi-section marketing site
- Taste dials: variance 8 / motion 6 / density 4; emerald accent; no AI purple

---

## [2026-07-14] — Lessons from mistakes (1.18.2)

Study residual errors from live hermes-ready / orchestration / merge theater.

### Fixed
- **hermes-ready multipanel panic** — one required `setup_layout` check; `conductor hermes-ready --repair`
- **Chess/game axis split** — domain lanes (surface/rules/ai/integrate); coalesce check/mate scraps
- **Merge-without-spawn errors** — full order (fanout → host SPAWN → ack → report → merge)
- **config.example / setup** — stop pinning `model.default: gpt-4o-mini` (Hermes owns models)

### Added
- **docs/LESSONS.md** — durable mistake → rule memory
- Tests: chess domain axes; repair_hermes_install

### Changed
- Version **1.18.2**

### Accomplished
- `conductor hermes-ready --repair` is the one-shot fix for empty ~/.hermes layout

---

## [2026-07-14] — Stop/thrash messaging + home resolution (1.18.1)

Self-loop quality: thrash/stop must not read as “abort everything”; hermes-ready home should track real Hermes installs.

### Fixed
- **Thrash block copy** — explicit “NOT stop everything”; recovery steps (new args/tool/scope)
- **Loop policy** — `scope=this_failure_class` on stop/escalate; suffix says mission may continue
- **Verify-on-stop** — one-nudge-only wording; Hermes write tools (`patch`, `search_replace`, …)
- **shared_home_default** — prefer `~/.hermes` when it has `plugins/conductor` over empty `~/.conductor`

### Changed
- Version **1.18.1**
- `pre_tool_call` thrash blocks attach loop-policy suffix when durable session exists

### Accomplished
- Focused pytest (hermes + thrash + stop messaging) green
- Agents get actionable “change fingerprint / continue mission” instead of hard-stop panic

---

## [2026-07-14] — Hermes-ready for any stock agent (1.18.0)

Hardening so **any** third-party Hermes agent can install and use Conductor without forks or identity hijack.

### Added
- **`conductor.adapters.hermes.plugin`** — package-level `register(ctx)` (file plugin + pip share one implementation)
- **Pip entry-point** `hermes_agent.plugins` → `conductor = conductor.adapters.hermes.plugin`
- **`conductor.adapters.hermes.ready`** — readiness report (CLI, slash, doctor)
- **`conductor hermes-ready`** (+ `--install-pip` into Hermes venv)
- **`conductor doctor --hermes`** — full checklist by default when Hermes layout present
- **`scripts/install_for_hermes.sh`** — one-shot install for any machine
- Slash: `/remnant`, `/track`, `/conductor-status`
- Setup writes **`CONDUCTOR_PARTNER_SOUL.md`** (partner only)
- Setup **`conductor.env`** exports `HERMES_HOME`, `CONDUCTOR_HOST=hermes`, host/partner soul paths
- Optional **`setup --install-pip` / `--no-pip`** (auto-pip when hermes on PATH)

### Fixed
- Setup **no longer overwrites Hermes meister `SOUL.md`** with Conductor partner SOUL
- Broader Hermes core skip list (`delegate_task`, `skill_manage`, web/browser, …)
- Defaults: `CONDUCTOR_HOST=hermes`, spine + resonate on plugin load
- Plugin yaml version stays in sync with package version on install

### Changed
- Version **1.18.0**
- File plugin `hermes_plugin/conductor` is a thin bootstrap → package register
- Docs: HERMES.md / OPERATORS.md rewritten for third-party agents

### Accomplished
- Full pytest green; hermes contract + ready + setup isolation tests
- Path: clone → `./scripts/install_for_hermes.sh` → `source conductor.env` → `hermes`

---

## [2026-07-12] — Merge compression + Tier-1 fanout hygiene (1.17.0)

Deep dive after digital-white-cell (61-insight Tier-2 dump, file races, divergence ~0.92).
Inspired by AgentDrive growth-merge: short ranked set + token overlap near-dedup.

### Fixed
- **Jaccard near-dedup** collapses sibling echoes (`pytest 40 passed` ×N → one line)
- Default merge surface **capped at 16** high-signal insights
- **`alternative-path:`** capped (≤2); Tier-2 no longer dumps every lane decision
- **Divergence scoring**: inject SHARED_DECISION floor; **ignore lane-unique** decisions (ownership ≠ conflict) so parallel fanout stays Tier-1 eligible
- Report path always **`ensure_shared_decisions`** (clones that omit the pin no longer force Tier-2)

### Added
- `tokenize_insight` / `jaccard` / `ensure_shared_decisions` / `SCAFFOLD_FIRST`
- Fanout field **`scaffold_first`**: parent scaffolds greenfield `work_root` before write-capable clones
- Host playbook: scaffold-first how_to_use + merge limit notes
- Tests: white-cell dump compression; shared-decision pin; Tier-1 with lane-local extras

### Changed
- Version **1.17.0**
- `curate_insights(limit=16)` default; report folds use curate not raw filter only

### Accomplished
- 108 tests green; simulated white-cell decisions → **divergence 0.0** (Tier-1 path)
- Live lesson closed: pack chrome already 0 in 1.16; volume + false Tier-2 fixed in 1.17

---

## [2026-07-12] — Signal-curated merges + track auto-resolve (1.16.0)

Inspired by AgentDrive growth-merge / content-addressed high-signal hygiene.

### Fixed
- Tier-1/2 merge no longer **appends raw `remnant.merge_insights`** past the filler filter (live Grid chrome path)
- Finalize merge **always** assigns curated insights — empty filter no longer keeps dirty chrome
- Ritual decisions (`parallel branches…`, `strategy-lane:`) stripped from **final** merge surface (still used for divergence on heartbeats)
- Near-duplicate findings with different `[role]` prefixes collapse (content-address style key)

### Added
- `curate_insights()` / `signal_score()` / `normalize_insight_key()` in `remnant_work`
- Merge response: `signal_count`, `chrome_dropped`, `track_resolved`, `track_status`
- **Auto-resolve track** when merge succeeds and no active remnants remain
- Tests: curate rank+dedup; tier1 never leaks pack chrome

### Changed
- Version **1.16.0**
- Heartbeat union for merge uses **insights only** (key_decisions stay on divergence scoring)
- Playbook notes track hygiene + report-with-evidence guidance

### Accomplished
- 105 tests green; Grid-style pack chrome (objective/deliver/accept/focus_tokens) cannot survive merge

---

## [2026-07-12] — Write-capable clones + clean merges (1.15.0)

### Fixed
- **verify** host spawns are **`general-purpose` / `capability_mode=all`** (no longer `explore`/read-only — can run pytest/shell)
- Work-pack **template insights** no longer seed heartbeats/merges (`objective:`, `deliver:`, `focus_tokens:`, generic accept lines)
- Fanout initial heartbeat is “awaiting host spawn” at low progress (not 85% pack-chrome)

### Added
- `host_subagent_type` / `host_capability_mode` / `success_evidence` on work packs
- Stronger clone prompt: require real findings + shell for verify
- Filler filter covers pack chrome from 1.14 live drives
- Tests: verify spawn write-capable; explore stays RO; filler strips pack templates

### Changed
- Version **1.15.0**
- Playbook `spawn_guidance` + next_actions prefer real findings over instruction strings

### Accomplished
- 103 tests green; smoke: 4× general-purpose/all + merge without focus_tokens noise

---

## [2026-07-12] — Real host spawn protocol for MCP parents (1.14.0)

### Added
- Fanout fields: **`parent_must_spawn`**, **`spawn_count`**, **`protocol`** (`mcp_cannot_spawn`), **`anti_theater`**, **`hermes_batch`**
- **`action=spawn_ack`** — parent posts `[{remnant_id, clone_handle}]` after host spawn; status **`spawned`**
- Hermes **`hermes_batch`**: one native `delegate_task(tasks=[…])` with index-aligned `remnant_ids`
- Start-pack / full recipe steps document parent-native spawn (Grok `spawn_subagent` / Hermes `delegate_task`)
- Offline tool **`conductor_worker`** (echo|shell); Hermes core skip list includes **`delegate_task`**

### Changed
- Version **1.14.0**
- Hermes tool_call is real **`delegate_task`** with **`goal` + `context`** (removed fake `delegate_or_subagent`)
- Host contract / mandatory_host_action: spawn → spawn_ack → report → merge
- Clone readiness: **`spawned`** is not merge-ready (waits report)

### Fixed
- Name collision risk: Conductor no longer presents offline worker as Hermes `delegate_task` in schemas/plugin
- MCP parents had no ack step to prove real host spawn before merge theater

### Accomplished
- 101 tests green; path: fanout → spawn_ack → report → merge
- Docs: ORCHESTRATION / SHADOW_CLONES / MCP / HERMES_SUBAGENT_FANOUT updated for MCP+parent spawn

---

## [2026-07-12] — Research: real Hermes subagent fan-out

### Added
- **docs/HERMES_SUBAGENT_FANOUT.md** — deep dive: Hermes `delegate_task` batch API vs Conductor contracts; why 4 clones never actually spawned; 1.14 design (correct tool name, batch `tasks[]`, concurrency≥4, rename offline worker tool)

### Accomplished
- Mapped hermes-agent `delegate_tool.py` + async_delegation + public docs + X (Teknium async, Tonbi/YanXbt masterclass)
- Identified critical mismatch: Conductor emits `delegate_or_subagent` (not real); Hermes needs `delegate_task(tasks=[…])` with `goal`+`context`
- Identified name collision: Conductor MCP `delegate_task` is offline echo, not Hermes children

---

## [2026-07-12] — Multi-host spawn parity + hermes fix (1.13.0)

### Fixed
- **`dispatch=hermes` / ILO fanout** no longer raises `host tool_call missing prompt or description`
- Hermes `tool_call.arguments` now always include **`description`** (plus goal, prompt, remnant_id)
- Generic host spawn also carries top-level `description` + `after_complete`

### Added
- Host-aware `_validate_host_tool_call` + `_normalize_spawn_request` (defensive completeness)
- Multi-host **host_contract** schemas: Grok `spawn_subagent`, Claude `Task`, Hermes `delegate_or_subagent`
- Host-specific `mandatory_host_action` text
- `parent_checklist[].label` for quick parent UI
- Hermes/ILO `after_complete` report template (same report→merge loop as Grok)
- Start-pack `remnant_policy.hosts` map
- Regression tests: hermes spawn shape, validation, MCP `dispatch=hermes` fanout

### Changed
- Version **1.13.0**
- Report path filters filler insights/decisions before heartbeat + merge fold
- Stronger filler substrings (JSON-ish templates, sibling territory ritual lines)
- Full recipe forbids reading tool_calls without spawning

### Accomplished
- Hermès parity with Grok host contract (description required everywhere)
- pytest orchestration + MCP host/hermes paths green

---

## [2026-07-12] — Conductor quality pass from live drives (1.12.0)

### Added
- Orchestration **confidence** score; expanded thin/full patterns (assessment, restart, improve, research+implement)
- Fanout **`parent_checklist`**, **`execute_tool_calls_now`**; hybrid when `work_root` on fanout_ready
- Stronger **filler filtering** on merge insights (plan-only, unit contribution, generic templates)

### Changed
- Version **1.12.0**
- Work packs: role-specific steps (surface/rules/verify/backend/architect) instead of one generic template
- Merge `_union_insights` routes through `filter_insights`

### Fixed
- Ritual merge noise from local clone preflight lines
- False thin/full edges for restart/assessment vs multi-axis improve goals

### Accomplished
- pytest MCP+orchestration+full suite green
- Scratch smoke: start-thin/full, fanout-host, merge-host

---

## [2026-07-12] — Thin vs full orchestration + host clones that run (1.11.0)

### Added
- **`conductor.core.orchestration`** — classify thin|full, decompose axes, fanout_ready payload
- Start pack: `orchestration`, `fanout_ready`, thin/full **recipes**, mode force `auto|thin|full`
- Host spawn **`tool_call`** exact Grok `spawn_subagent` args (background, capability_mode, types)
- Fanout returns **`tool_calls`** + **`mandatory_host_action`**
- Dispatch mode **`hybrid`** — local preflight then host deepen
- **docs/ORCHESTRATION.md** — research + contracts

### Changed
- Version **1.11.0**
- Combo scoring: multi-surface → C; ops/assessment → A; full mode can override A→C
- Thin mode skips track-by-default and forbids remnant ritual

### Research basis
- Live drives: ritual fanout rarely accelerates coding; start_pack+memory enough for single-path
- Grok Build subagents: depth-1 spawn_subagent; parallel spawn; report/merge loop

### Accomplished
- Tests: thin/full start pack, orchestration policy, host tool_calls schema

---

## [2026-07-12] — Shadow clones = host subagents (1.10.0)

### Added
- **Shadow clone system** — remnants dispatch as real parallel missions (Naruto Kage Bunshin model)
- `conductor.core.clone_backend` + `clone_worker` — local thread-pool workers + host spawn contracts
- Fanout `dispatch`: `auto` | `local` | `host` | `hermes`
- Actions **`report`**, **`await`**; status includes **`clone_readiness`**
- Merge blocks until clones complete (unless `force=true`)
- Host spawn_request shapes for Grok / Claude / Hermes / generic
- **docs/SHADOW_CLONES.md**
- MCP server defaults `CONDUCTOR_MCP=1`, `CONDUCTOR_HOST=grok` for host clone contract

### Changed
- Version **1.10.0**
- Combo C / start pack remnant policy describe host subagent loop
- Hermes delegation map uses `conductor_shadow_clone` + spawn_request

### Accomplished
- Local clones: fanout → automatic missions → merge
- Host clones: fanout → spawn_requests → report → merge
- Tests: local fanout + host report path

---

## [2026-07-12] — Remnant work packs + start pack (1.9.2)

### Added
- **`conductor_start_pack`** MCP tool — preferred first call: session + combo + optional track + high-signal tool loop + remnant policy (skip pillar spam)
- **`conductor.core.remnant_work`** — structured work packs (role, steps, risks, acceptance, insights)
- Remnant **`action=work`** — (re)build work pack + heartbeat on one remnant
- Fanout returns **`work_packs` + `host_playbook`**; merge returns **`host_playbook`** with filtered insights

### Changed
- Version **1.9.2**
- Fanout default: real work packs instead of filler heartbeats (`preserve modular conductor boundary`)
- Combo C workflow text: execute playbook then merge
- docs/MCP.md — start-pack-first loop + remnant policy

### Fixed
- Remnants felt like empty ritual; now produce host-executable phases and cleaner merges

### Accomplished
- Kill multiversal-chess :5177 done earlier in session
- `pytest` green for start pack + fanout work packs + merge playbook

---

## [2026-07-12] — MCP live-drive improvements (1.9.1)

### Added
- **MCP arg normalization** (`_normalize_mcp_args`) — `goal`→`intent`, `name`→`title`, `search`→search, `proposal`→`description`, `add_edge`→`link`, …
- **`is_tool_error_payload` + CallToolResult.isError** — soft `"Error: …"` / JSON `{error}` surface as MCP failures
- **`session_id` injected** into every Continuity tool schema (MCP discoverability)
- **memory_episodic `tags`/`tag` on write** + **`action=search`** (content + tags substring)
- Remnant merge error text: *spawn first* guidance
- Grok: `[mcp_servers.the-conductor]` in `~/.grok/config.toml` → `CONDUCTOR_HOME=~/.conductor`
- tests: aliases, error payload, tags/search, session_id schema, remnant guidance

### Changed
- Version **1.9.1**
- docs/MCP.md — Grok toml snippet, aliases, isError, agent loop (spawn before merge)

### Fixed
- Models inventing param names no longer dead-end on soft string errors
- Soft failures no longer look like successful tool calls to MCP clients
- Memory tags dropped on write; search was `unknown action`

### Accomplished
- Live MCP drive: foundation 9/9; second pass after aliases (combo C, track, remnant spawn→merge, ethics)
- `grok mcp doctor the-conductor` — healthy, 22 tools
- Reload Grok session to load native `the-conductor` tools

---

## [2026-07-12] — MCP server for Claude / Codex / Cursor / Grok (1.9.0)

### Added
- **`conductor.mcp`** — MCP stdio server: tools, resources (`conductor://…`), prompts (`system`, `resonate`, `plan`)
- **`conductor mcp`** CLI (`serve` · `catalog` · `tools`)
- Console scripts: `the-conductor-mcp`, `conductor-mcp`
- Optional dep: `pip install -e ".[mcp]"`
- **docs/MCP.md** — config snippets for Claude Desktop, Codex, Cursor, Grok
- tests/test_mcp.py

### Changed
- Module adapters list includes `mcp`
- README / MODULE_FOR_AGENTS point at MCP path

### Accomplished
- AI models call pillar tools without embedding Hermes
- Meta tools: `conductor_module_info`, `conductor_session`, `conductor_system_prompt`
- Version **1.9.0**

---

## [2026-07-12] — Per-pillar functional tests

### Added
- **tests/test_each_pillar.py** — one functional test per pillar P1–P8 + healing P0
  - P1 Soul Resonance · P2 Memory fabric · P3 Tracks+edges · P4 Crucible/RBMC
  - P5 Remnant spawn/merge · P6 Orchestration tools · P7 Governance+Max Effort
  - P8 Ethics checklist · P0 Path floors+heal · cross-check all probes

### Accomplished
- `pytest tests/test_each_pillar.py` — 11 passed
- Full suite green with per-pillar coverage

---

## [2026-07-11] — Benchmark-driven hook performance (1.8.1)

### Added
- **tests/test_benchmark_kit.py** — operator eval kit + latency budgets + resonance fidelity
- `default_session_store()` process cache; thrash memory-first path

### Changed
- **pre_tool / thrash / pre_llm** hot paths: store cache, thrash in-memory, workspace cache, empty pre_llm TTL
- SQLite session store: WAL + NORMAL sync; index on messages
- Hermes plugin: de-dupe tool registration (`seen` set)
- docs/BENCHMARKS.md — budgets + shipped improvements table

### Fixed
- Creating `SessionStore()` every hook call (~1ms+ re-init) — main regression from microbench
- Double registration of Conductor tools on FakeCtx / re-entry

### Accomplished
- pre_tool allow path target **&lt; 2 ms**; thrash **&lt; 0.5 ms** (asserted in CI)
- Version **1.8.1**

---

## [2026-07-11] — Hermes study + benchmarks map

### Added
- **docs/HERMES.md** — stock Hermes plugin API study, install path, tools/hooks/skills, verify
- **docs/BENCHMARKS.md** — Hermes stress/kanban/browser benches vs Conductor probes vs industry suites

### Changed
- **hermes_plugin/conductor** — skip Hermes core tool name clashes (`read_file`/`write_file`/`run_shell`…); spine still gates host tools; Soul Resonance sets `CONDUCTOR_HOST_SOUL` from Hermes SOUL; slash `/pillars` + `/combo`; optional `register_skill`
- plugin.yaml 1.8.0 — enhance framing, homepage

### Accomplished
- Any stock Hermes agent can enable Conductor without fork or built-in tool override
- Clear eval kit: plugins list + CONDUCTOR_OK + pillars foundation + path-safety assert

---

## [2026-07-11] — All pillars depth (1.8.0)

### Added
- **P2 Procedural memory** — `ProceduralStore` + `MemoryFabric` facade; tool actions `fabric`, `semantic_add`, `procedure_add`, `procedure_list`
- **P3 Track edges** — `TrackEdge` graph; `link`/`unlink`/`edges`/`neighbors`; fork auto-edge; chessboard shows edges
- **P4 RBMC backprop** — after distill, writes tracks + episodic/semantic + pocket `simulation_trace`
- **P5 Tier 3 deep merge** — `merge_deep` / `/remnant merge_deep` runs RBMC then folds Crucible evidence
- tests/test_pillar_depth.py

### Changed
- docs/PILLARS.md contracts updated for fabric, edges, RBMC phases, tier3
- Remnant merge tags tier1/2/3 in lifecycle events

### Accomplished
- End-to-end: tracks graph · memory four layers · RBMC→memory · remnant deep merge
- Version **1.8.0** · 51+ tests

---

## [2026-07-11] — Pillar foundation layer (1.7.0)

### Added
- **docs/PILLARS.md** — foundation contracts, runtime map, enhance-host flow for P1–P8 + healing
- **`conductor.pillars`** — catalog + live `foundation_report()` probes
- Tool **`pillar_status`**, slash **`/pillars`**, skill **`pillars`**
- `module_info()` includes pillars + foundation pass count
- `conductor status` shows pillar foundation probe
- tests/test_pillars.py

### Changed
- PILLAR_COMBOS / README link to foundation doc
- Product framing: each pillar **enhances** the host meister

### Accomplished
- `/pillars status` and `pillar_status` verify imports, SOUL resonance, memory layers, path floors, ethics checklist, combos
- Version **1.7.0**

---

## [2026-07-11] — Soul Resonance (1.6.0)

### Added
- **Soul Resonance** — Conductor **enhances** the host agent (Hermes/OpenClaw/…); locks wavelength with meister soul, does not replace it
- `conductor.soul.resonance` — discover host SOUL/IDENTITY, `resonate()`, modes `resonate|solo|host_only`
- `get_system_prompt(host_soul=…)` + `resonate_souls()` on harness API
- `/soul resonate` slash diagnostics
- **docs/SOUL_RESONANCE.md**
- tests/test_soul_resonance.py

### Changed
- Root **SOUL.md** rewritten as resonance partner (meister primary, partner amplifies, shared spine)
- `build_system_prompt` composes dual-wavelength prompt by default

### Accomplished
- Env: `CONDUCTOR_HOST_SOUL`, `CONDUCTOR_SOUL_MODE`
- Version **1.6.0**

---

## [2026-07-11] — Module guide for any agent

### Added
- **docs/MODULE_FOR_AGENTS.md** — how Hermes, OpenClaw, and any harness use Conductor as a module (API, env, loop, checklist)

### Changed
- README + INTEGRATION.md point at MODULE_FOR_AGENTS as the primary agent handoff doc

### Accomplished
- Third-party agents have a single copy-paste integration contract

---

## [2026-07-11] — Combo workflows + runtime wiring (1.5.3)

### Added
- **docs/WORKFLOWS.md** — mermaid flows for combos A–H + decision tree
- **`conductor.combos`** — catalog, `recommend_combo`, `workflow_steps`, formatters
- **Skill `combo`** — recommend / explain A–H
- **Slash `/combo`** — list · recommend · workflow · detail
- **Tool `combo_route`** — same for host agent loops
- **tests/test_combos.py**

### Changed
- Skills **plan**, **review**, **remnant-guide** wired to combos (decision tree + Combo C/D/G)
- Offline skill responder emits recommended combo + workflow steps
- README / PILLAR_COMBOS link to workflows + runtime surfaces

### Accomplished
- `pytest` 31 passed; version **1.5.3**
- Example: `/combo recommend spawn parallel remnants` → C; `combo_route` in tool schemas

---

## [2026-07-11] — Pillar combos map

### Added
- **docs/PILLAR_COMBOS.md** — eight pillars solo modes + named combos A–H + decision tree + tool cheat sheet
- README docs index link

### Accomplished
- Operators can pick Daily / Chessboard / Remnant / Crucible / Max Effort / Heal / Evidence / Full stack recipes

---

## [2026-07-11] — Doc & residual cleanup (1.5.2)

### Changed
- Rewrote product docs: `ARCHITECTURE`, `HARNESS`, `PROJECT_OVERVIEW` for Conductor skillset module
- Replaced obsolete `MIGRATION.md` + `CUTOVER.md` with compact `docs/HISTORY.md`
- Pillar specs (Noesis, ethics, Max Effort, Fable workflows, tracks, crucible) de-ILO’d
- Skills loader: `refresh_conductor_skills` (was `refresh_ilowned_skills`)
- Research index: drop dead `research/ilo/` path layout
- Setup only installs `hermes_plugin/conductor` (no legacy plugin source path)
- README docs index points at ARCHITECTURE / HISTORY

### Removed
- `docs/MIGRATION.md`, `docs/CUTOVER.md` (superseded by HISTORY)

### Accomplished
- Product-facing surface is Conductor-only; legacy paths documented only in HISTORY
- `pytest` green; version **1.5.2**

---

## [2026-07-11] — Code polish (1.5.1)

### Changed
- CLI `prog` is **`conductor`** (was `ilo`); REPL prompt **`conductor>`**
- User-facing setup/status strings fully Conductor-branded
- Env vars primary names: `CONDUCTOR_WORKSPACE`, `CONDUCTOR_SHELL_STRICT`, `CONDUCTOR_THRASH_THRESHOLD`, `CONDUCTOR_PROMOTE_SKIP_GATE`, `CONDUCTOR_CRUCIBLE_*`, `CONDUCTOR_REPO`, `CONDUCTOR_SPINE_ON_HERMES` (legacy `ILO_*` still accepted)
- Tool descriptions: Track System + episodic memory say Conductor (not ILO)
- Plugin logs/toolset `conductor_agent`; spine flag `CONDUCTOR_SPINE_ON_HERMES`
- `learning/promote` finds `src/conductor` roots; regression defaults include current tests
- SOUL/home defaults, plan skill verification, config.example, install wrapper cleanup
- Ruff safe auto-fixes (imports, EOF newlines, UTC timezone style)

### Fixed
- Dead `ilo.crucible.pocket` import path in core runtime
- Doubled “Conductor conductor” messaging in spine + REPL

### Accomplished
- `pytest` 22 passed; version **1.5.1**
- `conductor --help` / `conductor status` show clean Conductor product surface

---

## [2026-07-11] — Skillset module for any AI harness

### Added
- **`conductor.harness`** Module API: install, skills, tools, hooks, system prompt, module_info
- **`conductor.adapters.hermes`** optional Hermes packaging
- **`conductor module`** CLI (info / install / skills / tools)
- **docs/INTEGRATION.md** — how any agent clones and wires the module
- setup `--harness generic|hermes`

### Changed
- Product framed as **skillset module**, not Hermes-only product
- Default home **`~/.conductor`** (or share HERMES_HOME when set)
- Removed remaining **ILO_*** env / `ilo_home` naming from runtime paths

### Accomplished
Any host: `pip install -e .` → `conductor.harness.install()` → tools/hooks/skills.
Hermes: `conductor setup --harness hermes` → `hermes`.

---

## [2026-07-11] — Third-party operator path

### Added
- **docs/OPERATORS.md** — install, shared home, Hermes import, troubleshooting
- **bootstrap.py** — package root marker + conductor.env
- Plugin + `conductor hermes` PYTHONPATH bootstrap for stock Hermes venvs
- tests/test_bootstrap.py

### Changed
- Default home for new machines prefers ~/.hermes when unset
- README for third parties

---

## [2026-07-11] — Product surface is Conductor-only

### Changed
- Offline smoke contract: **`CONDUCTOR_OK`** (was `ILO_OK`)
- Primary env: **`CONDUCTOR_HOME`**, **`CONDUCTOR_PROVIDER`** (legacy `ILO_*` still accepted)
- CLI entry: **`conductor` only** — removed `ilo` console script / wrapper
- README, SOUL, research pillars, install script: I.L.O product brand → **The Conductor**

### Removed
- Product-facing “ILO” / `ILO_OK` operator path

### Accomplished
```bash
conductor version
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
hermes
```

---

## [2026-07-11] — Cleanup: flatten core, drop legacy modules

### Changed
- Nested package `conductor.conductor` → **`conductor.core`**
- Default clone id `ilo_prime` → **`prime`**

### Removed
- Dual-stack Hermes update (`update.py`, `cli/update_cmd.py`)
- Old onboard CLI + `onboarding.py` (replaced by `conductor setup`)
- Unused `cli/auth_cmd.py` (auth lives in `cli/main.py`)
- Goal **harness** package (classifier-era)
- Web **dashboard** package (not on product CLI)
- Native **tui/** package (Hermes is the TUI; `activity` lives in `core/`)
- `tools_overlay.py`

### Accomplished
```bash
conductor version   # 1.3.0+
conductor setup && hermes
pytest tests/ -q    # green
```

---

## [2026-07-11] — Package rename: `ilo` → `conductor`

### Changed
- Python package directory `src/ilo` → **`src/conductor`**
- Imports: `from conductor...` / `import conductor`
- PyPI/project name: **`the-conductor`** v1.3.0
- Console scripts: **`conductor`** (primary) and **`ilo`** (compat alias)
- Home resolution: `CONDUCTOR_HOME` → `ILO_HOME` → `~/.ilo`
- Repo root detection: `src/conductor/_NATIVE_BRAIN` + `hermes_plugin/conductor`

### Accomplished
```bash
pip install -e ".[dev]"
conductor version   # the-conductor 1.3.0
conductor setup
hermes              # daily
```

---

## [2026-07-11] — New repository: The Conductor

### Added
- Fresh git repo for The Conductor (canonical product tree)
- Product: **The Conductor** on stock Hermes — plugin `conductor`, skills `conductor/*` only

### Changed
- Supersedes the previous Hermes extension live path (archived offline)

### Accomplished
```bash
cd The Conductor && pip install -e ".[dev]" && ilo setup && hermes
```

---


## [2026-07-11] — Remove flattened Fable skills from home

### Fixed
- `ilo setup` only removed `skills/fable/`; prior seed had flattened
  `skills/{effort,gate,verify,memory,session,audit,debug}` with `name: fable-*`
- Cleanup now detects pack + flattened Fable dirs (frontmatter `fable-*`) and removes them
- Tests plant flattened layout and assert cleanup; operator home re-setup verified

### Accomplished
- `find_fable_skill_dirs` + setup clean; no Hermes-visible `fable-*` skills under `~/.ilo/skills`

---

## [2026-07-11] — The Conductor product; Fable skill pack removed

### Changed
- Operator brand: **The Conductor** on stock **Hermes** (daily path: `hermes`)
- Hermes plugin id: **`conductor`** (was `ilo`)
- README / SOUL / status / setup copy rebranded
- `ilo setup` enables `conductor`, drops `ilo` from `plugins.enabled`

### Removed
- **`skills/fable/*`** skill pack from ship/setup/bundle (not seeded)
- Setup cleans home `plugins/ilo` and `skills/fable` when re-run

### Accomplished
```bash
ilo setup
hermes                 # daily
hermes plugins list    # conductor enabled
```

Internal package import path may remain `ilo` temporarily.

---

## [2026-07-11] — Archive legacy dual-stack monorepo

### Removed
- Legacy dual-stack monorepo archived off the live product path
- Removed fork launchers (`ilo-relay`, `ilo-tui`)

### Changed
- Canonical product path is the Hermes extension repo only

### Accomplished
- One live product path; legacy preserved offline under archive storage

---

## [2026-07-11] — New canonical repo: Hermes extension pivot

### Added
- **New repository** for the Hermes extension product boundary:
  brain + Hermes plugin + skill pack; **stock Hermes** = TUI/auth/engine
- `docs/MIGRATION.md` — current → target → cutover → retire list → post-pivot auth/launch
- `docs/CUTOVER.md` — canonical vs legacy operator note
- `hermes_plugin/ilo/` — Hermes plugin source of truth (no fork sync)
- `src/ilo/setup_ext.py` + `ilo setup` — install plugin/skills into `HERMES_HOME=$ILO_HOME`
- `src/ilo/hermes_host.py` — stock `hermes` discovery (`HERMES_BIN` / PATH); **no `ILO_RELAY_ROOT` required**
- `scripts/install.sh` — venv + editable install + setup
- Tests: setup layout, plugin register, offline brain smoke

### Changed
- Production path: stock `hermes` (not a private Hermes fork)
- Auth docs point at `hermes model` / `hermes auth …`
- Version **1.0.0** for the extension product line

### Retired (as production path)
- Private Hermes fork as required engine
- Dual-stack `ilo update` + monorepo fork sync
- Default install depending on `ILO_RELAY_ROOT`

### Accomplished
```bash
pip install -e ".[dev]"
export ILO_HOME=~/.ilo HERMES_HOME=$ILO_HOME
ilo setup
ILO_PROVIDER=test ilo chat -q 'Reply with exactly: ILO_OK'
hermes   # when stock Hermes installed
```

Legacy dual-stack / private-fork trees may remain on operator machines but are **non-canonical**.
