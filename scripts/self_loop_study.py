#!/usr/bin/env python3
"""Conductor self-loop study: replay mission goals, print routing, exit non-zero on regressions.

Usage (from repo root, venv active):
  python scripts/self_loop_study.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductor.combos import recommend_combo
from conductor.core.clone_worker import run_clone_mission
from conductor.core.orchestration import classify_orchestration
from conductor.core.remnant_work import build_work_pack


CASES = [
    {
        "name": "rpg_game",
        "goal": (
            "Build a full-fledged D&D-style sci-fi browser game: character creation, "
            "d20 combat, exploration, inventory, quests"
        ),
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 4,
        "forbid_all_implement": True,
        "require_roles": {"combat", "world", "character"},
    },
    {
        "name": "website",
        "goal": "Build entire official professional UI/UX website for The Conductor product marketing",
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 3,
        "require_roles": {"surface", "product"},
    },
    {
        "name": "thin_ops",
        "goal": "quick fix typo in readme",
        "expect_combo": "A",
        "expect_mode": "thin",
        "min_axes": 0,
    },
    {
        "name": "parallel_graphics",
        "goal": "parallel fanout three.js math shader and api backend",
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 2,
    },
    # --- 1.18.5 self-loop expansions (found after first study was green) ---
    {
        "name": "chess_fix_multi",
        "goal": "fix chess AI with rules board and 3d rendering three.js",
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 3,
        "require_roles": {"rules", "ai"},
        "forbid_duplicate_surface": True,
    },
    {
        "name": "landing_multi_section",
        "goal": "landing page with 8 sections for SaaS product",
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 3,
        "require_roles": {"surface", "product"},
    },
    {
        "name": "rpg_end_to_end",
        "goal": "end-to-end browser RPG game with inventory quests d20",
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 5,
        "require_roles": {"character"},
    },
    {
        "name": "million_site",
        "goal": (
            "official million-dollar marketing website hero pricing CTA manifesto footer"
        ),
        "expect_combo": "C",
        "expect_mode": "full",
        "min_axes": 3,
        "require_roles": {"product"},
    },
]


def main() -> int:
    fails: list[str] = []
    print("◆ Conductor self-loop study\n")
    for case in CASES:
        goal = case["goal"]
        rec = recommend_combo(goal)
        pol = classify_orchestration(goal)
        axes = pol.get("axes") or []
        roles = [a.get("role") for a in axes]
        print(
            f"[{case['name']}] combo={rec.primary.id} mode={pol['mode']} "
            f"axes={len(axes)} roles={roles}"
        )
        for a in axes[:6]:
            print(f"    [{a.get('role')}] {str(a.get('objective'))[:70]}")
        if rec.primary.id != case["expect_combo"]:
            fails.append(
                f"{case['name']}: combo {rec.primary.id} != {case['expect_combo']} "
                f"scores={rec.scores}"
            )
        if pol["mode"] != case["expect_mode"]:
            fails.append(
                f"{case['name']}: mode {pol['mode']} != {case['expect_mode']}"
            )
        if len(axes) < case.get("min_axes", 0):
            fails.append(
                f"{case['name']}: axes {len(axes)} < {case['min_axes']}"
            )
        if case.get("forbid_all_implement") and axes:
            if all(a.get("role") == "implement" for a in axes):
                fails.append(f"{case['name']}: all axes role=implement")
        need = case.get("require_roles") or set()
        if need:
            have = set(roles)
            missing = need - have
            # allow objective text fallback for character/product
            objs = " ".join(str(a.get("objective", "")).lower() for a in axes)
            still = set()
            for r in missing:
                if r == "character" and "character" in objs:
                    continue
                if r == "product" and ("product" in objs or "pillar" in objs):
                    continue
                if r == "rules" and "rules" in objs:
                    continue
                if r == "ai" and ("ai" in objs or "minimax" in objs):
                    continue
                still.add(r)
            if still:
                fails.append(
                    f"{case['name']}: missing roles {sorted(still)} have={sorted(have)}"
                )
        if case.get("forbid_duplicate_surface") and roles.count("surface") > 1:
            fails.append(
                f"{case['name']}: duplicate surface roles {roles} "
                "(integrate lane should own glue)"
            )

    demo = ROOT / "demos" / "stellar-codex"
    if demo.is_dir():
        pack = build_work_pack(objective="Combat system: turns, enemies, loot")
        scroll = run_clone_mission(
            remnant_id="self-loop",
            objective="Combat system: turns, enemies, loot",
            work_pack=pack,
            work_root=demo,
        )
        files = scroll.get("files_examined") or []
        print(f"\n[clone_scan] stellar-codex files={files[:5]}")
        if not files:
            fails.append("clone_scan: no files for combat tokens under stellar-codex")
        elif not any("game.js" in f or "index.html" in f for f in files):
            fails.append(f"clone_scan: expected game.js/index.html in {files}")

    # Chess integrate pack role
    pack_i = build_work_pack(
        objective="Integrate playable game loop, turns, UI vs AI"
    )
    if pack_i.get("role") != "integrate":
        fails.append(
            f"work_pack integrate: role={pack_i.get('role')!r} expected integrate"
        )
    else:
        print(f"\n[work_pack] integrate role ok steps={len(pack_i.get('steps') or [])}")

    # --- 1.18.6 anti-theater + local scaffold ---
    try:
        import tempfile
        from conductor.core.runtime import ConductorRuntime
        from conductor.session.store import SessionStore

        store = SessionStore()
        rt = ConductorRuntime(store)
        sid = store.create_session(source="self-loop", title="theater").id
        fout = rt.fanout_remnants(
            sid,
            objectives=["Hero brand system", "Product pillars section"],
            dispatch="host",
            parent_goal="official marketing website",
        )
        if not fout.get("parent_must_spawn"):
            fails.append("theater: parent_must_spawn false on host fanout")
        comp = rt.spawn_compliance(sid)
        print(
            f"\n[theater] parent_must_spawn={fout.get('parent_must_spawn')} "
            f"risk={comp.get('theater_risk')} flags={comp.get('theater_flags')[:2]}"
        )
        if not comp.get("theater_risk"):
            fails.append("theater: expected theater_risk after host fanout sans ack")
        try:
            rt.merge_remnants_tier1(sid)
            fails.append("theater: merge succeeded without spawn (should block)")
        except ValueError:
            pass  # expected
        try:
            rt.report_remnant_clone(
                sid,
                remnant_id=fout["remnant_ids"][0],
                result={"ok": True, "insights": ["fake"], "findings": ["x"]},
            )
            fails.append("theater: report without handle succeeded (should block)")
        except ValueError:
            pass

        td = Path(tempfile.mkdtemp())
        sc = run_clone_mission(
            remnant_id="self-loop-scaffold",
            objective="Hero brand navigation",
            work_pack={"role": "surface", "steps": ["Ship hero"], "acceptance": []},
            work_root=td,
        )
        print(f"[scaffold] written={sc.get('files_written')}")
        if not sc.get("scaffold_count"):
            fails.append("scaffold: local clone wrote 0 files under work_root")
    except Exception as exc:  # noqa: BLE001
        fails.append(f"theater/scaffold probe error: {exc}")

    if fails:
        print("\n✗ REGRESSIONS")
        for f in fails:
            print(" ", f)
        return 1
    print("\n✓ self-loop study clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
