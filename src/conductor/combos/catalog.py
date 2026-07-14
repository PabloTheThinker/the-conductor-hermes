"""Named pillar combos A–H: catalog, recommendation, and workflow steps.

Spec: docs/PILLAR_COMBOS.md · docs/WORKFLOWS.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Combo:
    id: str  # A … H
    slug: str
    name: str
    summary: str
    pillars: tuple[str, ...]
    tools: tuple[str, ...]
    skills: tuple[str, ...]
    when: str
    avoid: str
    keywords: tuple[str, ...] = ()


COMBOS: dict[str, Combo] = {
    "A": Combo(
        id="A",
        slug="daily",
        name="Daily driver",
        summary="SOUL + Orchestration + Memory + host tools — default fast path.",
        pillars=("SOUL", "Orchestration", "Memory", "Host tools"),
        tools=("conductor_status", "memory_episodic"),
        skills=("plan", "review"),
        when="Ordinary coding, chat, file work, offline smoke.",
        avoid="Multi-branch uncertainty or irreversible stakes (use C/E).",
        keywords=(
            "fix",
            "implement",
            "edit",
            "file",
            "simple",
            "daily",
            "quick",
            "chat",
            "smoke",
            "refactor small",
        ),
    ),
    "B": Combo(
        id="B",
        slug="chessboard",
        name="Chessboard",
        summary="Tracks + Memory map risks/opportunities before fan-out.",
        pillars=("SOUL", "Track System", "Memory", "Orchestration"),
        tools=("track_orchestrate", "memory_episodic", "conductor_status"),
        skills=("plan",),
        when="Multi-week initiative, competing risks, standing strategic goals.",
        avoid="Single linear step already decided.",
        keywords=(
            "track",
            "strategy",
            "roadmap",
            "risk",
            "opportunity",
            "chessboard",
            "timeline",
            "initiative",
            "multi-week",
            "portfolio",
        ),
    ),
    "C": Combo(
        id="C",
        slug="remnant",
        name="Parallel push",
        summary="Remnant Protocol fan-out on live branches; merge Fast→Reflective→Deep.",
        pillars=("SOUL", "Track System", "Remnant", "Memory", "Orchestration"),
        tools=("remnant_orchestrate", "track_orchestrate", "memory_episodic"),
        skills=("remnant-guide", "plan"),
        when="Parallel uncertainty beats serial cost; A vs B exploration.",
        avoid="Single path; merge cost exceeds gain; low stakes.",
        keywords=(
            "parallel",
            "remnant",
            "branch",
            "fanout",
            "fan-out",
            "explore both",
            "a vs b",
            "vs",
            "spawn",
            "clone",
            "concurrent",
            # multi-surface product work (website live-run lesson)
            "website",
            "landing",
            "marketing",
            "multi-section",
            "official site",
            # note: do not add bare "chess" — matches Combo B "chessboard"
            "three.js",
            "threejs",
            "minimax",
        ),
    ),
    "D": Combo(
        id="D",
        slug="crucible",
        name="Deep forge",
        summary="Noesis/Crucible pocket for deep simulation and distillation.",
        pillars=("SOUL", "Memory", "Track System", "Noesis+Crucible", "Governance"),
        tools=("crucible_workspace", "track_orchestrate", "memory_episodic"),
        skills=("plan", "remnant-guide"),
        when="Architecture fork, chronic wound, stress-test merge proposals.",
        avoid="Typo fixes; default thinking (use A).",
        keywords=(
            "crucible",
            "noesis",
            "simulate",
            "simulation",
            "architecture",
            "deep",
            "rbmc",
            "distill",
            "stress-test",
            "pocket",
        ),
    ),
    "E": Combo(
        id="E",
        slug="max-effort",
        name="Max Effort decision",
        summary="Ethics + four voices + mandatory 24–48h Voice of Action.",
        pillars=("SOUL", "Governance", "Ethics", "Crucible", "Track System", "Memory"),
        tools=("ethics_evaluate", "crucible_workspace", "governance_audit", "track_orchestrate"),
        skills=("review", "plan"),
        when="Irreversible, multi-stakeholder, or civilizational cost decisions.",
        avoid="Already-decided work; mechanical edits.",
        keywords=(
            "irreversible",
            "high-stakes",
            "high stakes",
            "max effort",
            "max-effort",
            "ethics",
            "disaster",
            "deliberation",
            "four voices",
            "policy",
        ),
    ),
    "F": Combo(
        id="F",
        slug="heal",
        name="Integrity cascade",
        summary="Sense wound → field repair → scar/seal → advance (no thrash).",
        pillars=("SOUL spine", "Healing", "Memory", "Governance", "Orchestration"),
        tools=("memory_episodic", "conductor_status", "governance_audit"),
        skills=("review",),
        when="Tool/path failure, missing state, repeated same failing call.",
        avoid="Mass-delete 'fixes'; rewriting SOUL/path floors.",
        keywords=(
            "heal",
            "broken",
            "failed",
            "failure",
            "error",
            "wound",
            "repair",
            "thrash",
            "scar",
            "seal",
            "integrity",
            "crash",
            "missing",
        ),
    ),
    "G": Combo(
        id="G",
        slug="evidence",
        name="Evidence gate",
        summary="Plan → work → review → verification artifacts; done = proven.",
        pillars=("Governance/Fable", "Ethics", "Memory", "Orchestration"),
        tools=("ethics_evaluate", "governance_audit", "memory_episodic"),
        skills=("plan", "review"),
        when="Release, security surface, public claim of completion.",
        avoid="Skipping tests/logs and claiming done from narration.",
        keywords=(
            "ship",
            "release",
            "done",
            "verify",
            "verification",
            "evidence",
            "pytest",
            "review",
            "gate",
            "publish",
            "judgment",
        ),
    ),
    "H": Combo(
        id="H",
        slug="full-stack",
        name="Full conductor stack",
        summary="All pillars ordered: ethics → tracks → memory → path pick → merge → audit.",
        pillars=(
            "SOUL",
            "Ethics",
            "Tracks",
            "Memory",
            "Orchestration",
            "Remnant|Crucible|tools",
            "Governance",
            "Judgment",
        ),
        tools=(
            "ethics_evaluate",
            "track_orchestrate",
            "memory_episodic",
            "remnant_orchestrate",
            "crucible_workspace",
            "governance_audit",
        ),
        skills=("plan", "remnant-guide", "review", "combo"),
        when="Rare high-leverage day spanning strategy + parallel + deep work.",
        avoid="Routine single-file tasks (use A).",
        keywords=(
            "full stack",
            "full-stack",
            "all pillars",
            "end-to-end",
            "campaign",
            "multi-pillar",
            "conductor stack",
        ),
    ),
}


# Explicit id / slug aliases
_ID_ALIASES = {
    "a": "A",
    "b": "B",
    "c": "C",
    "d": "D",
    "e": "E",
    "f": "F",
    "g": "G",
    "h": "H",
}
for _c in COMBOS.values():
    _ID_ALIASES[_c.slug.lower()] = _c.id
    _ID_ALIASES[_c.name.lower()] = _c.id


def get_combo(key: str) -> Combo | None:
    k = (key or "").strip()
    if not k:
        return None
    if k in COMBOS:
        return COMBOS[k]
    return COMBOS.get(_ID_ALIASES.get(k.lower(), ""))


@dataclass
class Recommendation:
    primary: Combo
    secondary: list[Combo] = field(default_factory=list)
    fold_g: bool = False
    rationale: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary.id,
            "primary_name": self.primary.name,
            "secondary": [c.id for c in self.secondary],
            "fold_evidence_gate": self.fold_g,
            "rationale": list(self.rationale),
            "scores": dict(self.scores),
            "workflow": workflow_steps(self.primary.id),
        }


def recommend_combo(text: str) -> Recommendation:
    """Heuristic combo picker from free-text intent."""
    raw = (text or "").strip().lower()
    scores: dict[str, int] = {cid: 0 for cid in COMBOS}

    # Explicit mention: "combo C", "use remnant", etc.
    m = re.search(r"\bcombo\s*([a-h])\b", raw)
    if m:
        cid = m.group(1).upper()
        scores[cid] += 100
    for cid, combo in COMBOS.items():
        if f"combo {cid.lower()}" in raw or combo.slug in raw:
            scores[cid] += 40
        for kw in combo.keywords:
            if kw in raw:
                scores[cid] += 3 if len(kw) > 4 else 2

    # Structural signals
    if re.search(r"\b(vs\.?|versus|option a|option b|two approaches)\b", raw):
        scores["C"] += 8
    if re.search(r"\b(rm -rf|mass.?delet|wiped|corrupted)\b", raw):
        scores["F"] += 12
    if re.search(r"\b(ship|release|merge to main|production)\b", raw):
        scores["G"] += 6
    if re.search(r"\b(irreversible|cannot undo|one-way)\b", raw):
        scores["E"] += 10

    # Multi-axis / multi-surface → Parallel push (C) — research from live drives
    multi_surface = sum(
        1
        for t in (
            "three.js",
            "threejs",
            "shader",
            "math",
            "physics",
            "gpu",
            "ui",
            "ux",
            "visual",
            "backend",
            "frontend",
            "api",
            "ray",
            "lensing",
            "website",
            "landing",
            "marketing",
            "pillars",
            "hermes",
            "install",
            "docs",
            "hero",
            "footer",
            "brand",
        )
        if t in raw
    )
    if multi_surface >= 2:
        scores["C"] += 12
        scores["B"] += 4
    # Entire product marketing site = multi-lane (website live-run: was wrongly A)
    if re.search(
        r"\b(official\s+site|official\s+website|marketing\s+site|landing\s+page|"
        r"entire\s+(website|site)|full\s+(website|site)|million[- ]dollar|"
        r"professional\s+ui)\b",
        raw,
    ):
        scores["C"] += 14
        scores["B"] += 3
        scores["G"] += 2  # ship with evidence (serve URL / screenshots)
    # Full game / RPG / D&D (stellar-codex: was A or weak H via end-to-end keyword)
    if re.search(
        r"\b(d&d|dnd|dungeons|rpg|d20|browser\s+game|sci-?fi\s+game|"
        r"full[- ]fledged|character\s+creation|tabletop)\b",
        raw,
    ) or (
        "game" in raw
        and re.search(r"\b(combat|quest|inventory|exploration|npc|enemy)\b", raw)
    ):
        scores["C"] += 16
        scores["B"] += 2
        scores["G"] += 3
        # Prefer C over accidental H from "end-to-end" alone on games
        scores["H"] = max(0, scores.get("H", 0) - 4)
    # Chess / multi-system board game (self-loop: "fix chess AI…three.js" was A)
    # Use word-boundary \bchess\b so Combo B "chessboard" is not stolen
    if re.search(r"\bchess\b", raw) and not re.search(r"\bchessboard\b", raw):
        if re.search(
            r"\b(ai|opponent|minimax|rules|board|three|3d|game|render)\b",
            raw,
        ):
            scores["C"] += 14
            scores["G"] += 2
            scores["A"] = max(0, scores.get("A", 0) - 6)
    # Multi-section landing / SaaS marketing (self-loop: short "landing page…8 sections" thin+weak)
    if re.search(
        r"\b(\d+\s+sections?|multi[- ]?section|saas\s+product|landing\s+page)\b",
        raw,
    ):
        scores["C"] += 10
        scores["B"] += 2
    # "end-to-end" alone should not dominate multi-lane product work
    if "end-to-end" in raw or "end to end" in raw:
        if scores.get("C", 0) >= 10:
            scores["H"] = max(0, scores.get("H", 0) - 6)
    if re.search(r"\b(parallel|fanout|shadow clone|subagent|multiverse)\b", raw):
        scores["C"] += 10
    if re.search(r"\b(and|,)\b.+\b(and|,)\b", raw) and len(raw) > 40:
        scores["C"] += 6
    if re.search(r"\b(deep sim|stress-test|architecture fork|crucible)\b", raw):
        scores["D"] += 8
    # Research report → evidence gate + light parallel gather
    if re.search(r"\b(research|competitors|market analysis)\b", raw) and re.search(
        r"\b(report|write|summar)\b", raw
    ):
        scores["G"] += 8
        scores["B"] += 4
        scores["C"] += 4
    # Deploy production → evidence + integrity
    if re.search(r"\b(deploy|docker compose|production|kubernetes|ci/cd)\b", raw):
        scores["G"] += 8
        scores["F"] += 2
    # Thin / ops → keep A high (but not when multi-lane product signals dominate)
    if re.search(r"\b(kill port|quick fix|typo|assessment|how did)\b", raw):
        scores["A"] += 15
        scores["C"] = max(0, scores.get("C", 0) - 5)
    # Bare "fix …" without kill-port/typo: do not demote multi-lane C products
    elif re.search(r"\bfix\b", raw) and scores.get("C", 0) < 10:
        scores["A"] += 4

    if not raw:
        scores["A"] += 1

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best_id, best_score = ranked[0]
    if best_score <= 0:
        best_id = "A"
    primary = COMBOS[best_id]
    secondary = [COMBOS[cid] for cid, sc in ranked[1:3] if sc > 0 and cid != best_id][:2]

    fold_g = best_id != "G" and (
        scores["G"] > 0
        or bool(re.search(r"\b(done|ship|release|verify|pytest)\b", raw))
    )

    rationale: list[str] = []
    if best_score <= 0:
        rationale.append("No strong signals — default Daily driver (A).")
    else:
        rationale.append(f"Primary {primary.id} ({primary.name}): score={scores[primary.id]}.")
        rationale.append(f"When: {primary.when}")
    if secondary:
        rationale.append(
            "Also consider: "
            + ", ".join(f"{c.id} {c.name}" for c in secondary)
        )
    if fold_g:
        rationale.append("Fold Combo G (Evidence gate) before claiming done.")

    return Recommendation(
        primary=primary,
        secondary=secondary,
        fold_g=fold_g,
        rationale=rationale,
        scores={k: v for k, v in scores.items() if v > 0},
    )


def workflow_steps(combo_id: str) -> list[dict[str, str]]:
    """Ordered workflow steps for a combo (for agents and /combo workflow)."""
    steps: dict[str, list[dict[str, str]]] = {
        "A": [
            {"step": "1", "action": "Load SOUL + skills index (host system prompt)"},
            {"step": "2", "action": "Execute with host tools under path-safety spine"},
            {"step": "3", "action": "Optional: memory_episodic write for outcomes"},
            {"step": "4", "action": "Judgment: done only with evidence (tests/paths)"},
        ],
        "B": [
            {"step": "1", "action": "track_orchestrate list|chessboard — map field"},
            {"step": "2", "action": "track_orchestrate create|update — name risks/opportunities"},
            {"step": "3", "action": "memory_episodic write — bind outcomes to tracks"},
            {"step": "4", "action": "Orchestrate next move from chessboard priority"},
        ],
        "C": [
            {"step": "1", "action": "Combo B light: name branches on Track System"},
            {"step": "2", "action": "ethics_evaluate if merge is high-stakes"},
            {"step": "3", "action": "remnant_orchestrate fanout → shadow clones (spawn_requests or local workers)"},
            {"step": "4", "action": "host spawns subagents from spawn_requests; clones report results"},
            {"step": "5", "action": "merge when clone_readiness.ready → host_playbook + insights"},
            {"step": "6", "action": "memory_episodic + track resolve with merge artifact"},
        ],
        "D": [
            {"step": "1", "action": "crucible_workspace start — open pocket + objective"},
            {"step": "2", "action": "register_clone / fork_clone — birth moments"},
            {"step": "3", "action": "post concepts into Global Workspace"},
            {"step": "4", "action": "rbmc | max_effort | distill as needed"},
            {"step": "5", "action": "pocket isolate (fs/docker); promote insights to tracks"},
            {"step": "6", "action": "memory + governance_audit for session trace"},
        ],
        "E": [
            {"step": "1", "action": "ethics_evaluate — 7-point checklist"},
            {"step": "2", "action": "crucible_workspace max_effort — four voices"},
            {"step": "3", "action": "Extract Voice of Action: owner + 24–48h + criteria"},
            {"step": "4", "action": "governance_audit log + track_orchestrate update"},
            {"step": "5", "action": "Execute smallest verifiable step; record evidence"},
        ],
        "F": [
            {"step": "1", "action": "Sense wound — stop re-running same failing path"},
            {"step": "2", "action": "Contain blast radius (path floors already on)"},
            {"step": "3", "action": "Field repair from recovery imprint if available"},
            {"step": "4", "action": "Open scar in memory; mint learned seal if healed"},
            {"step": "5", "action": "Optional promote_seal after regression gate"},
            {"step": "6", "action": "Advance: smallest alternate verifiable step"},
        ],
        "G": [
            {"step": "1", "action": "plan skill — objective, phases, verification surfaces"},
            {"step": "2", "action": "Execute work under Combo A/B/C as needed"},
            {"step": "3", "action": "review skill — gaps, goal drift, unfinished checks"},
            {"step": "4", "action": "Collect artifacts: pytest, logs, paths, screenshots"},
            {"step": "5", "action": "Judgment: claim done only if evidence exists"},
        ],
        "H": [
            {"step": "1", "action": "SOUL + ethics_evaluate if high-stakes"},
            {"step": "2", "action": "Track chessboard (Combo B)"},
            {"step": "3", "action": "Memory inject scars/seals/episodes"},
            {"step": "4", "action": "Pick path: A tools | C Remnants | D Crucible / E Max Effort"},
            {"step": "5", "action": "Merge/distill → Track + Memory"},
            {"step": "6", "action": "governance_audit + Combo G evidence"},
            {"step": "7", "action": "Advance — train never stops"},
        ],
    }
    combo = get_combo(combo_id)
    if not combo:
        return [{"step": "?", "action": f"Unknown combo: {combo_id}"}]
    return steps.get(combo.id, [])


def format_combo_list() -> str:
    lines = [
        "◆ Conductor pillar combos (docs/PILLAR_COMBOS.md · docs/WORKFLOWS.md)",
        "",
    ]
    for cid in sorted(COMBOS.keys()):
        c = COMBOS[cid]
        lines.append(f"  {c.id}  {c.name:<22}  {c.summary}")
        lines.append(f"     when: {c.when}")
    lines.append("")
    lines.append("  /combo recommend <intent>   — pick A–H")
    lines.append("  /combo workflow <id>        — step list")
    lines.append("  /combo <id>                 — detail")
    return "\n".join(lines)


def format_workflow(combo_id: str) -> str:
    combo = get_combo(combo_id)
    if not combo:
        return f"Unknown combo {combo_id!r}. Try /combo list"
    lines = [
        f"◆ Combo {combo.id} — {combo.name} ({combo.slug})",
        f"  {combo.summary}",
        f"  Pillars: {', '.join(combo.pillars)}",
        f"  Tools:   {', '.join(combo.tools)}",
        f"  Skills:  {', '.join(combo.skills) if combo.skills else '—'}",
        f"  When:    {combo.when}",
        f"  Avoid:   {combo.avoid}",
        "",
        "  Workflow:",
    ]
    for row in workflow_steps(combo.id):
        lines.append(f"    {row['step']}. {row['action']}")
    lines.append("")
    lines.append("  Spec: docs/WORKFLOWS.md")
    return "\n".join(lines)


def format_recommendation(text: str) -> str:
    rec = recommend_combo(text)
    lines = [
        "◆ Combo recommendation",
        f"  Intent: {text.strip() or '(empty → default A)'}",
        f"  Primary: {rec.primary.id} — {rec.primary.name} ({rec.primary.slug})",
        f"  {rec.primary.summary}",
    ]
    if rec.secondary:
        lines.append(
            "  Secondary: "
            + ", ".join(f"{c.id} {c.name}" for c in rec.secondary)
        )
    if rec.fold_g:
        lines.append("  Fold-in: G Evidence gate before claiming done")
    lines.append("")
    lines.append("  Rationale:")
    for r in rec.rationale:
        lines.append(f"    · {r}")
    lines.append("")
    lines.append(f"  Workflow ({rec.primary.id}):")
    for row in workflow_steps(rec.primary.id):
        lines.append(f"    {row['step']}. {row['action']}")
    lines.append("")
    lines.append("  Next: /combo workflow " + rec.primary.id)
    return "\n".join(lines)
