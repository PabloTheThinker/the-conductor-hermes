# Lessons learned (live mistakes → product rules)

Short memory for agents and operators. Newest lessons first.

---

## L-2026-07-14 — Self-study structural mistakes (1.18.6)

**Study method:** Written codebase critique of how Conductor *actually* works → turn each weakness into a gate or builder.

**Mistakes named:**
1. **Spawn theater** — fanout returns tool_calls; parent invents report/merge without host spawn
2. **Local clones pure scouts** — scan/suggest only; no files left behind
3. **Done = narration** — merge succeeds without evidence-shaped insights
4. **Cognitive weight** — full pillar ontology with no one-page operator path
5. **Routing holes** — research/report and deploy goals weak

**Rules (1.18.6+):**
- `action=compliance` + merge/report **block** host theater (need `clone_handle` / spawn_ack)
- Override only with `force=true` **and** `accept_theater=true`
- Local clones with `work_root` write `.conductor/clone_scrolls/*` + greenfield stub
- start_pack includes `simple_path` + `judgment`; merge returns `done_proven`
- `docs/OPERATOR_FLOW.md` is the thin/full one-pager
- Self-loop study must probe theater block + scaffold write

---

## L-2026-07-14 — Self-loop pass 2: green harness ≠ no bugs

**Study method:** First `self_loop_study` was clean; expanded probes outside the harness found more mistakes. Fixed → expanded harness → re-run.

**Mistakes found:**
1. `fix chess AI…three.js` → **Combo A** (fix keyword) despite multi-lane chess product
2. Chess integrate axis labeled **surface** twice (glue ≠ second UI lane)
3. Short `landing page with 8 sections…` → **thin / 0 axes** (len&lt;48 short-default)
4. Official site without saying "pillar" → only hero+polish, **no product** lane
5. RPG without saying "character" → missing character create axis

**Rules (1.18.5+):**
- Domain full products (chess / landing / official site / RPG) never demote via short-goal thin
- Chess multi-system → **Combo C**; word-boundary chess so Combo B chessboard is safe
- Integrate role for game-loop glue; always product lane on marketing sites; always character on RPG
- Self-loop harness must keep growing with live regressions, not only re-check known cases

---

## L-2026-07-14 — Self-loop: D&D/RPG game routing + clone scan

**Study method:** Replay mission goals (game, website, thin ops, three.js parallel), inspect combo/axes/packs/clone scan, fix, re-run `scripts/self_loop_study.py`.

**Mistakes found:**
1. Full D&D sci-fi game goal → **Combo A** (no game keywords in scorer) or accidental **H** via `end-to-end`
2. Axes = sentence scraps all `implement` (no RPG domain synth)
3. Roles combat/world/character missing → packs said implement/architect
4. Clone scan on `demos/stellar-codex` returned **[]** because tokens matched file **content** not paths (`js/game.js`)

**Rules (1.18.4+):**
- Game/RPG/D&D/d20/browser-game → **Combo C** + RPG synth lanes (shell, rules, combat, world, character, meta)
- Content-aware clone scan for source suffixes; shallow entrypoint fallback
- Prefer C over H when C already strong (product multi-lane)
- Keep `scripts/self_loop_study.py` green in CI/manual self-loops

---

## L-2026-07-14 — Website run: Conductor weak as foreman

**Mistake (observed live):** Official marketing site goal scored **Combo A** (score 2) while orchestration correctly chose **full**. Axes were a raw split of the sentence (Hermes / docs CTA / luxury), not product lanes. Local clones with no `work_root` returned filler “plan-only (no root)” insights. Host did all design/code after a thin ritual.

**Root causes:**
1. Combo multi_surface tokens ignored website/landing/marketing/hermes/docs
2. No domain synth for marketing sites (unlike chess)
3. Local clone worker only file-scans; greenfield returns theater
4. Work-pack roles lacked product/docs/polish

**Rules (1.18.3+):**
- Official/marketing/multi-section site → **Combo C** + full axes: hero · product/pillars · hermes/docs · polish
- Greenfield local clones must name **deliverable paths** (e.g. `website/index.html#hero-nav`), not “plan-only”
- Parent should pass **`work_root`** for file-aware clones; local without root is a plan pack for the meister, not parallel implementation
- Design taste skills own visuals; Conductor owns lanes + evidence

---

## L-2026-07-14 — Hermes-ready false multipanel failure

**Mistake:** `conductor hermes-ready` reported NOT READY with 4–5 separate ✗ rows for the same root cause (no setup under `~/.hermes`), so the fix looked harder than it was.

**Rule:** Collapse layout into one **required** check; offer **`conductor hermes-ready --repair`**. Prefer home that already has `plugins/conductor`.

---

## L-2026-07-14 — “Stop everything” thrash panic

**Mistake:** Thrash/loop `action=stop` read as mission abort; agents abandoned goals.

**Rule:** Stop means **this failure class / fingerprint only**. Message must say NOT abort mission; continue with different args/tool.

---

## L-2026-07-14 — Meister SOUL overwrite

**Mistake:** Setup copied Conductor partner SOUL into Hermes `SOUL.md`.

**Rule:** Never overwrite meister SOUL. Write `CONDUCTOR_PARTNER_SOUL.md` only.

---

## L-2026-07-12 — Merge theater / pack chrome

**Mistake:** Fanout → merge without host spawn; work-pack template lines became “insights.”

**Rule:** Parent must SPAWN → spawn_ack → report real findings → merge. Filter filler; curate insights; verify clones write-capable.

---

## L-2026-07-12 — `delegate_task` name collision

**Mistake:** Offline Conductor worker registered as Hermes native spawn tool name.

**Rule:** Hermes owns `delegate_task`. Conductor offline worker is `conductor_worker`.

---

## L-2026-07-14 — Weak chess/game axis split

**Mistake:** Goal split into “check/checkmate” as its own lane vs rules/AI/surface.

**Rule:** Domain synth for chess/three.js games: surface + rules + AI + integrate. Coalesce rule fragments.

---

## L-2026-07-14 — config.yaml model pin

**Mistake:** Setup/example forced `model.default: gpt-4o-mini` on shared Hermes home.

**Rule:** Leave model to `hermes model`; only enable plugins + product surface tags.
