# Benchmarks & evaluation landscape

What “benchmarks” mean for **Hermes** (the host) vs **The Conductor** (the enhancement module), and how to interpret them.

---

## 1. Two different evaluation surfaces

| Surface | What is measured | Owner |
|---------|------------------|--------|
| **Hermes runtime** | Host agent: tool loop latency, kanban scale, browser eval, concurrency | hermes-agent repo |
| **Conductor module** | Pillar foundation probes, offline brain smoke, safety floors, merge correctness | this repo |

Conductor does **not** replace Hermes’ model quality benchmarks. It adds **orchestration / safety / memory** capability on top of whatever model Hermes uses.

---

## 2. Hermes-agent internal benchmarks (studied)

Local tree: hermes-agent checkout (branch may vary; plugin API is stock).

### Stress suite (`tests/stress/`)

**Not** part of the default `run_tests.sh` gate — long, adversarial.

| File | Measures |
|------|----------|
| `test_benchmarks.py` | Kanban kernel latency at **100 / 1k / 10k** tasks: `dispatch_once`, `recompute_ready`, `build_worker_context`, board list/stats. Prints min/median/max ms; JSON for regression diffs. **Not pass/fail.** |
| `test_concurrency*.py` | Multi-worker claim races, reclaim races, mixed ops — invariants (no double-claim, SQLite retry) |
| `test_subprocess_e2e.py` | Real worker subprocess heartbeats / crash detection |
| `test_property_fuzzing.py` | ~500 random op sequences, invariant checks |
| `test_atypical_scenarios.py` | Unicode, huge strings, SQL injection attempts, weird `HERMES_HOME` paths |

Run (from hermes-agent checkout):

```bash
./venv/bin/python -m pytest tests/stress/ -v -s
./venv/bin/python tests/stress/test_benchmarks.py
```

### Browser eval script

`scripts/benchmark_browser_eval.py` — compares supervisor WebSocket `Runtime.evaluate` vs agent-browser subprocess for simple `1+1` evals (latency, not agent IQ).

### What these mean for Conductor

- Hermes **scale/latency** benchmarks are about the host kernel (especially Kanban).  
- Conductor plugins must stay **cheap on hooks** (`pre_tool_call` / `pre_llm_call`) so they do not dominate turn latency.  
- Spine checks are O(command string) regex floors — designed to stay off the critical path of 10k-task dispatch.

---

## 3. Conductor module evaluation (this repo)

### Automated tests (CI-style)

```bash
cd "The Conductor"
.venv/bin/pytest -q
```

Covers: setup, harness API, plugin discovery, combos, **pillar foundation probes**, track edges, procedural memory, RBMC backprop, tier3 deep merge, Soul Resonance.

### Foundation probes (live capability check)

```bash
conductor status
# or in Hermes: /pillars status
# or:
python -c "from conductor.pillars import format_foundation_report; print(format_foundation_report(verbose=True))"
```

Probes: SOUL integrity + resonance, memory layers, track store, Crucible/RBMC imports, Remnant tiers, combos/skills, policy+ethics smoke, path-safety blocks `rm -rf /`.

### Offline brain smoke (no model key)

```bash
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
```

### Safety floors (spine)

- `is_shell_denied("rm -rf /")` must block  
- Workspace confinement when `CONDUCTOR_WORKSPACE` set  
- Thrash guard on repeated failing tool+args  

These are **contract tests**, not leaderboard scores.

---

## 4. Industry agent benchmarks (context only)

Public suites people cite for **agent** systems (not run by default here):

| Suite | Focus | Relevance to Conductor |
|-------|--------|-------------------------|
| **SWE-bench** / SWE-bench Verified | Real GitHub issue fixing | Model + coding tools (Hermes files/terminal); Conductor adds plan/review/heal rails |
| **τ-bench / Tau-bench** | Tool-use policy / domain agents | Tool routing quality; Conductor tools are extra toolsets |
| **AgentBench** | Multi-environment agents | Host loop capability |
| **WebArena / BrowserGym** | Web agents | Hermes browser tools; Conductor spine still applies |
| **GAIA** | General assistant QA | Model + tools |

**How Conductor should be scored if you add an eval harness:**

1. **Safety delta** — same tasks with/without spine: fewer catastrophic shell actions  
2. **Recovery delta** — injected tool failures → scar/seal/advance rate  
3. **Orchestration delta** — multi-branch tasks with Remnant fan-out vs serial  
4. **Resonance fidelity** — host still self-names correctly under Conductor SOUL (no identity hijack)  
5. **Latency budget** — p50/p95 overhead of hooks per turn  

Do **not** claim Conductor alone improves SWE-bench without an explicit protocol (model, Hermes version, tools, seeds).

---

## 5. Recommended operator benchmark kit

### Automated (this repo)

```bash
.venv/bin/pytest tests/test_benchmark_kit.py -q
```

Covers offline smoke, path-safety, pillar foundation, **hook latency budgets**, thrash guard, Soul Resonance fidelity, SessionStore cache.

| Budget | Target |
|--------|--------|
| `pre_tool_call` allow path | **&lt; 2.0 ms**/call |
| thrash memory path | **&lt; 0.5 ms**/call |
| `pre_llm` empty TTL path | **&lt; 5.0 ms**/call |

### Manual (any Hermes install)

```bash
# A. Host healthy
hermes plugins list | grep -i conductor
hermes -q 'Reply with: HERMES_OK'

# B. Module healthy
CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'
conductor status   # pillars foundation line

# C. Spine
python -c "from conductor.agent.path_safety import is_shell_denied; assert is_shell_denied('rm -rf /')"

# D. Pillars
python -c "from conductor.pillars import foundation_report; r=foundation_report(); assert r['ok'] or r['passed']>=8; print(r['passed'],'/',r['total'])"

# E. Optional Hermes stress (from hermes-agent tree)
# ./venv/bin/python tests/stress/test_benchmarks.py
```

Record: Hermes version/commit, Conductor version, model id, date, pass/fail of A–D.

---

## 6. Design implications + implemented improvements

| Hermes fact | Implication | Shipped |
|-------------|----------------|--------|
| User plugins under `$HERMES_HOME/plugins/` | `conductor setup` installs here | setup_ext |
| Built-in file/shell tools | Do not override; spine gates host tools | plugin skip-list |
| Hermes SOUL is meister | Soul Resonance | `CONDUCTOR_HOST_SOUL` on session start |
| Hooks on every tool/LLM call | Stay light | **cached `SessionStore`**, **memory-first thrash**, workspace cache, pre_llm empty TTL |
| Stress suite is kanban-centric | No heavy work in hooks | no LLM in hooks; budgets in `test_benchmark_kit` |
| Plugin debug | `HERMES_PLUGINS_DEBUG=1` | docs/HERMES.md |

### Hook hot-path improvements (1.8.1)

1. **`default_session_store()`** — process-wide store cache (no schema re-init per call)  
2. **Thrash guard** — process memory first; durable write-through on block / every N hits  
3. **`workspace_root()`** — cached per env value  
4. **`pre_tool`** — shell/file short-circuit (no double shell scan); thrash without creating sessions  
5. **`pre_llm`** — 2s TTL for empty memory payloads  
6. **SQLite** — WAL + `synchronous=NORMAL` for session DB  
7. **Plugin** — de-dupe tool registration with `seen` set

---

## Related

- [HERMES.md](HERMES.md) — integration how-to  
- [PILLARS.md](PILLARS.md) — foundation probes  
- [MODULE_FOR_AGENTS.md](MODULE_FOR_AGENTS.md) — generic hosts  
