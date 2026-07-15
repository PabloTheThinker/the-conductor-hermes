"""Thin vs full orchestration policy + multi-axis goal decomposition.

Research-backed defaults from live Grok/Conductor use (Multiversal Chess,
Parallax Grid, black-hole sim, MCP live drives):

1. **Thin** — score sheet only: start_pack → host tools → memory.
   Skip fanout, skip pillar spam, optional track.
2. **Full** — multi-axis: fanout with **host** shadow clones (Grok
   ``spawn_subagent`` / Claude Task / Hermes subagent), report, merge.

Grok host contract (from Grok Build user-guide 16-subagents.md):
  spawn_subagent(prompt, description, subagent_type, background?,
                 capability_mode?, isolation?)
  Nested subagents cannot spawn children (depth 1).
"""

from __future__ import annotations

import re
from typing import Any


# --- Thin signals: single-path, short, ops hygiene ---
_THIN_PATTERNS = [
    r"\bkill (the )?port\b",
    r"\bstop (the )?(server|dev)\b",
    r"\bremove\b.+\bplease\b",
    r"\bdelete\b.+\b(folder|dir|project)\b",
    r"\brename\b",
    r"\btypo\b",
    r"\bone[- ]line\b",
    r"\bquick (fix|check|look)\b",
    r"\bjust (tell|show|list|explain)\b",
    r"\bhow did\b",
    r"\bassessment\b",
    r"\bwhat is\b",
    r"^fix\b",
    r"\bstatus\b only",
    r"\bcommit and push\b",
    r"\bcheck on it\b",
    r"\bi restarted\b",
]

# --- Full / multi-axis signals ---
_FULL_PATTERNS = [
    r"\band\b.+\band\b",  # A and B and C
    r"\bthree\.?js\b.+\b(math|physics|shader|engine|chess|game)\b",
    r"\b(math|physics|shader|engine|chess|game)\b.+\bthree\.?js\b",
    r"\b(frontend|ui|visual)\b.+\b(backend|api|gpu|server|ai|rules)\b",
    r"\b(backend|api|gpu|server)\b.+\b(frontend|ui|visual)\b",
    r"\bchess\b.+\b(ai|opponent|minimax|engine|rules|board|3d|three)\b",
    r"\b(ai|opponent|minimax)\b.+\bchess\b",
    r"\bgame\b.+\b(ai|rules|three\.?js|webgl|combat|quest)\b",
    r"\b(landing\s+page|marketing\s+site|official\s+(site|website)|multi[- ]?section)\b",
    r"\b\d+\s+sections?\b",
    r"\bparallel\b",
    r"\bmultiverse\b",
    r"\bfanout\b",
    r"\bshadow clone\b",
    r"\bsubagent\b",
    r"\bremnant\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\boption a\b",
    r"\boption b\b",
    r"\bmulti[- ]?(axis|surface|lane)\b",
    r"\b(implement|build|ship)\b.+\b(and|,)\b.+\b(test|deploy|visual|gpu|ai)\b",
    r"\bimprove\b.+\b(and|both|full|host|thin)\b",
    r"\bresearch\b.+\bimplement\b",
    r"\bhost clone\b",
    r"\bthin and full\b",
    r"\bthin vs full\b",
]

_AXIS_SPLIT = re.compile(
    r"\s+and\s+|\s*\+\s*|,\s*(?=[a-zA-Z])|\s*\|\s*|\s+with\s+(?=real\b|gpu\b|math\b|ui\b)",
    re.I,
)

# Role heuristics for axis labeling (order matters — first match wins)
_ROLE_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("math", "physics", "schwarzschild", "metric", "geodesic", "formula"), "verify"),
    (("shader", "glsl", "ray", "lensing", "webgl"), "architect"),
    # integrate BEFORE surface: "UI vs AI" must not match ui→surface (self-loop 1.18.5)
    (("wire", "integrate", "glue", "game loop", "turn system", "ui vs ai"), "integrate"),
    (
        (
            "three",
            "ui",
            "hud",
            "visual",
            "css",
            "canvas",
            "orbit",
            "drag",
            "camera",
            "mesh",
            "render",
        ),
        "surface",
    ),
    (
        (
            "chess",
            "legal move",
            "checkmate",
            "check/",
            "castling",
            "en passant",
            "promotion",
            "fen",
            "pgn",
            "rules engine",
            "move gen",
        ),
        "rules",
    ),
    (
        ("minimax", "alpha-beta", "opponent", "ai agent", "bot", "evaluation function"),
        "ai",
    ),
    (("gpu", "ollama", "cuda", "nvidia", "inference"), "backend"),
    (("api", "server", "control surface", "http"), "backend"),
    (("test", "pytest", "unit", "playtest"), "verify"),
    (("hero", "brand", "navigation", "nav", "first-viewport", "landing"), "surface"),
    (("hud", "title screen", "game shell", "visual system"), "surface"),
    (("pillar", "product story", "capability", "feature section"), "product"),
    (("hermes", "install", "setup", "docs", "cta", "conversion"), "docs"),
    (("responsive", "a11y", "polish", "motion", "static build", "production"), "polish"),
    # character before rules so "point-buy" in create sheet ≠ pure rules engine
    (("character creation", "archetype", "inventory start", "class select", "starting inventory"), "character"),
    (("d20", "ability score", "advantage", "hp, levels", "skills, advantage"), "rules"),
    (("combat", "enemy", "enemies", "loot", "victory", "defeat", "attack"), "combat"),
    (("world", "map location", "exploration", "npc", "dialogue", "quest"), "world"),
    (("save/load", "localstorage", "settings", "meta:"), "meta"),
    (("research plan", "sources", "competitive landscape", "market"), "research"),
    (("synthesis report", "findings, recommendations", "write report"), "docs"),
    (("deploy manifest", "compose", "pipeline", "health check", "rollback"), "ops"),
]


def classify_orchestration(
    goal: str,
    *,
    force_mode: str | None = None,
) -> dict[str, Any]:
    """Return thin|full policy with reasons and suggested axes."""
    g = (goal or "").strip()
    gl = g.lower()

    if force_mode in {"thin", "full"}:
        mode = force_mode
        reasons = [f"forced mode={force_mode}"]
    else:
        thin_hits = [p for p in _THIN_PATTERNS if re.search(p, gl)]
        full_hits = [p for p in _FULL_PATTERNS if re.search(p, gl)]
        # Length heuristic: very short goals lean thin — but not product domains
        domain_full = _is_domain_full_product(gl)
        short = len(g) < 48 and " and " not in gl and not domain_full
        # Explicit multi-surface tokens
        multi_surface = sum(
            1
            for t in (
                "three.js",
                "threejs",
                "shader",
                "math",
                "gpu",
                "api",
                "ui",
                "ux",
                "visual",
                "physics",
                "backend",
                "frontend",
                "website",
                "landing",
                "marketing",
                "hermes",
                "pillars",
                "chess",
                "sections",
                "saas",
                "pricing",
                "manifesto",
                "rpg",
                "d20",
                "combat",
            )
            if t in gl
        )

        if thin_hits and not full_hits and not domain_full:
            mode = "thin"
            reasons = [f"thin_pattern:{p}" for p in thin_hits[:3]]
        elif full_hits or multi_surface >= 2 or domain_full:
            mode = "full"
            reasons = [f"full_pattern:{p}" for p in full_hits[:3]]
            if multi_surface >= 2:
                reasons.append(f"multi_surface_tokens={multi_surface}")
            if domain_full:
                reasons.append("domain_full_product")
        elif short:
            mode = "thin"
            reasons = ["short_goal_default_thin"]
        else:
            # Default medium goals: thin unless clearly multi-axis
            axes_preview = decompose_axes(g)
            if len(axes_preview) >= 2:
                mode = "full"
                reasons = [f"decomposed_axes={len(axes_preview)}"]
            else:
                mode = "thin"
                reasons = ["default_thin_unless_multi_axis"]

    axes = decompose_axes(g) if mode == "full" else []
    # Need ≥2 real axes for full clone path; else demote or synthesize
    if mode == "full" and len(axes) < 2:
        if any(
            k in gl
            for k in (
                "build",
                "implement",
                "ship",
                "create",
                "simulation",
                "improve",
                "research",
                "host clone",
                "orchestration",
            )
        ):
            axes = _synthesize_axes(g)
            if axes:
                reasons.append("synthesized_axes_from_multi_surface")
        if len(axes) < 2:
            mode = "thin"
            reasons.append("demoted_full_to_thin_insufficient_axes")
            axes = []

    # Prefer hybrid when work_root will be supplied by caller (hint only)
    dispatch = "host" if mode == "full" else None

    return {
        "mode": mode,
        "reasons": reasons,
        "axes": axes,
        "open_track_default": mode == "full",
        "fanout_recommended": mode == "full" and len(axes) >= 2,
        "dispatch_default": dispatch,
        "skip_ritual": mode == "thin",
        "recipe": _recipe(mode),
        "confidence": _confidence(mode, reasons, axes),
        "research_notes": {
            "grok_spawn": {
                "tool": "spawn_subagent",
                "params": [
                    "prompt",
                    "description",
                    "subagent_type",
                    "background",
                    "capability_mode",
                    "isolation",
                ],
                "depth_limit": 1,
                "types": ["general-purpose", "explore", "plan"],
            },
            "thin_is_default": (
                "Live drives showed full remnant ritual rarely accelerates "
                "coding; start_pack+memory is enough for single-path work."
            ),
            "full_uses_host_clones": (
                "When ≥2 axes, dispatch=host|hermes emits exact tool_calls "
                "(Grok spawn_subagent / Claude Task / Hermes delegate_task); "
                "parent MUST spawn in parallel, spawn_ack, report, merge."
            ),
            "mcp_cannot_spawn": (
                "MCP server cannot invoke Grok spawn_subagent or Hermes "
                "delegate_task. Fanout only returns contracts; the parent "
                "agent must execute host tools THIS turn."
            ),
            "mcp_parent_spawn": {
                "steps": [
                    "1. conductor_start_pack (full)",
                    "2. remnant_orchestrate fanout → tool_calls / hermes_batch",
                    "3. PARENT: spawn_subagent ×N (Grok) or delegate_task(tasks) (Hermes)",
                    "4. remnant_orchestrate spawn_ack with handles",
                    "5. report each child → merge",
                ],
                "anti_theater": "Do not implement all axes yourself without spawning.",
            },
            "hermes_parity": (
                "dispatch=hermes emits real delegate_task (goal+context) plus "
                "hermes_batch for one-shot parallel tasks[]; needs "
                "delegation.max_concurrent_children >= N."
            ),
        },
    }


def _confidence(mode: str, reasons: list[str], axes: list[dict[str, str]]) -> float:
    if any(r.startswith("forced") for r in reasons):
        return 1.0
    if mode == "thin" and any("thin_pattern" in r for r in reasons):
        return 0.92
    if mode == "full" and len(axes) >= 3:
        return 0.9
    if mode == "full" and any("full_pattern" in r for r in reasons):
        return 0.85
    if mode == "full" and any("synthesized" in r for r in reasons):
        return 0.7
    if mode == "thin" and any("default_thin" in r for r in reasons):
        return 0.65
    return 0.75


def _is_domain_full_product(gl: str) -> bool:
    """True when goal is clearly a multi-lane product (not short-ops thin)."""
    if any(
        t in gl
        for t in (
            "chess",
            "three.js",
            "threejs",
            "landing page",
            "landing",
            "marketing site",
            "marketing website",
            "official website",
            "official site",
            "million-dollar",
            "million dollar",
            "professional ui",
            "entire website",
            "entire official",
            "multi-section",
            "multi section",
            "d&d",
            "dnd",
            "rpg",
            "browser game",
            "sci-fi game",
            "scifi game",
            "full-fledged",
            "full fledged",
            "character creation",
            "d20",
        )
    ):
        return True
    if re.search(r"\b\d+\s+sections?\b", gl):
        return True
    if "game" in gl and any(
        t in gl for t in ("combat", "quest", "inventory", "ai", "opponent", "minimax")
    ):
        return True
    if "website" in gl and any(
        t in gl for t in ("official", "marketing", "product", "entire", "full")
    ):
        return True
    return False


def decompose_axes(goal: str) -> list[dict[str, str]]:
    """Split a goal into parallel work axes (objectives for fanout)."""
    g = (goal or "").strip()
    if not g:
        return []
    # Prefer domain lanes when the goal is clearly multi-surface product work
    # (avoids weak splits like "check/checkmate" as its own axis).
    synth = _synthesize_axes(g)
    if len(synth) >= 2 and _prefer_synth_over_split(g):
        return synth
    parts = [p.strip() for p in _AXIS_SPLIT.split(g) if p and p.strip()]
    # Filter tiny fragments
    parts = [p for p in parts if len(p) >= 8]
    if len(parts) < 2:
        return synth if len(synth) >= 2 else []
    # Merge rule-ish fragments so legal moves + check/mate stay one rules lane
    parts = _coalesce_rule_fragments(parts)
    parts = parts[:4]
    axes: list[dict[str, str]] = []
    for i, p in enumerate(parts):
        axes.append(
            {
                "objective": p[:200],
                "role": _infer_role(p),
                "index": str(i),
            }
        )
    return axes


def _prefer_synth_over_split(goal: str) -> bool:
    gl = goal.lower()
    if _is_domain_full_product(gl):
        return True
    return any(
        t in gl
        for t in (
            "minimax",
            "alpha-beta",
            "game with",
            "play against",
            "saas",
            "sections",
        )
    )


def _coalesce_rule_fragments(parts: list[str]) -> list[str]:
    """Fold check/checkmate-style scraps into a rules objective."""
    rules_bits: list[str] = []
    out: list[str] = []
    for p in parts:
        pl = p.lower()
        if any(
            k in pl
            for k in (
                "legal move",
                "checkmate",
                "check/",
                "castling",
                "stalemate",
                "promotion",
                "rules",
                "fen",
            )
        ) and len(p) < 48:
            rules_bits.append(p)
            continue
        out.append(p)
    if rules_bits:
        out.insert(
            min(1, len(out)),
            "Chess rules engine: " + "; ".join(rules_bits),
        )
    return out


def _synthesize_axes(goal: str) -> list[dict[str, str]]:
    """When multi-surface signals exist but split failed, invent standard lanes."""
    gl = goal.lower()
    axes: list[str] = []
    if any(t in gl for t in ("math", "physics", "schwarzschild", "metric", "formula")):
        axes.append("Pure math / physics module + unit tests")
    if any(t in gl for t in ("shader", "ray", "lensing", "glsl", "webgl")):
        axes.append("Ray-march / shader / GPU visual core")
    # Chess / board game product (live scoring lesson: surface + rules + AI + glue)
    _is_chess = "chess" in gl or (
        "game" in gl
        and any(t in gl for t in ("ai", "opponent", "minimax", "three"))
        and not any(t in gl for t in ("d&d", "dnd", "rpg", "d20", "combat", "quest"))
    )
    if _is_chess and not any(t in gl for t in ("d&d", "dnd", "rpg", "d20", "sci-fi", "scifi")):
        if any(t in gl for t in ("three", "webgl", "browser", "visual", "drag", "3d", "render")):
            axes.append("Three.js board, pieces, camera, drag-drop UX")
        elif "board" in gl:
            axes.append("Board surface: squares, pieces, selection UX")
        axes.append(
            "Rules engine: legal moves, check, checkmate, castling, promotions"
        )
        if any(t in gl for t in ("ai", "opponent", "minimax", "bot", "play against")):
            axes.append("AI opponent: minimax/alpha-beta + evaluation")
        axes.append("Integrate playable game loop, turns, UI vs AI")
    # D&D / RPG / sci-fi browser game (stellar-codex self-loop lesson)
    _is_rpg = any(
        t in gl
        for t in (
            "d&d",
            "dnd",
            "dungeons",
            "rpg",
            "d20",
            "character creation",
            "tabletop",
            "sci-fi game",
            "scifi game",
            "browser game",
            "full-fledged",
            "full fledged",
        )
    ) or (
        "game" in gl
        and any(t in gl for t in ("combat", "quest", "inventory", "exploration", "npc"))
    )
    if _is_rpg and not _is_chess:
        axes.append("Game shell UI: title, HUD, panels, dark sci-fi visual system")
        axes.append("Rules engine: d20 rolls, stats, skills, advantage, HP, levels")
        axes.append("Combat system: turns, enemies, actions, loot, victory/defeat")
        axes.append("World: map locations, exploration, NPCs, dialogue, quests")
        # Always ship character lane for full RPG products (self-loop 1.18.5)
        axes.append(
            "Character creation: races/archetypes, point-buy, starting inventory"
        )
        axes.append("Meta: save/load, settings, help, polish a11y")
    # Official / marketing website (live Conductor website run: was weak split)
    _is_site = any(
        t in gl
        for t in (
            "website",
            "landing page",
            "landing",
            "marketing site",
            "marketing website",
            "official site",
            "official website",
            "million-dollar",
            "million dollar",
            "professional ui",
        )
    ) or bool(re.search(r"\b\d+\s+sections?\b", gl))
    if _is_site and not _is_chess and not _is_rpg:
        axes.append("Hero, brand system, navigation, and first-viewport story")
        # Always product lane for marketing/official sites (was missing when no "pillar")
        axes.append("Product story and pillars / capability sections")
        if any(
            t in gl
            for t in (
                "hermes",
                "install",
                "setup",
                "docs",
                "cta",
                "pricing",
                "manifesto",
                "saas",
            )
        ) or "conductor" in gl:
            axes.append("Hermes install path, docs links, and conversion CTAs")
        axes.append(
            "Responsive polish, a11y, motion, assets, and production static build"
        )
    if (
        any(t in gl for t in ("three", "ui", "hud", "visual", "scene"))
        and "chess" not in gl
        and "website" not in gl
        and "landing" not in gl
    ):
        axes.append("Three.js scene, controls, and HUD")
    if any(t in gl for t in ("gpu", "ollama", "cuda", "nova", "inference")):
        axes.append("GPU runtime invoke path + evidence")
    if any(t in gl for t in ("api", "server", "control surface", "tailscale")):
        axes.append("Control surface / API over network")
    if any(t in gl for t in ("thin", "full", "orchestration", "host clone", "shadow")):
        axes.append("Orchestration policy / host clone contract")
        axes.append("Tests + docs for thin vs full paths")
    # Research / report product (self-study: was two bare implement scraps)
    if any(t in gl for t in ("research", "competitors", "market analysis", "write report")) and not _is_chess and not _is_rpg and not _is_site:
        axes.append("Research plan: sources, questions, scope boundaries")
        axes.append("Synthesis report: findings, recommendations, evidence links")
        if any(t in gl for t in ("competitor", "market", "landscape")):
            axes.append("Competitive landscape table + differentiation notes")
    # Deploy / ops multi-surface
    if any(t in gl for t in ("docker compose", "kubernetes", "deploy production", "ci/cd")):
        axes.append("Deploy manifests / compose / pipeline config")
        axes.append("Verification: health check, logs, rollback note")
    if len(axes) < 2 and any(t in gl for t in ("build", "implement", "create", "ship", "improve")):
        axes = [
            f"Core implementation: {goal[:80]}",
            f"Verification + docs: {goal[:60]}",
        ]
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for a in axes:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    # RPG / multi-system products need more than 4 lanes (self-loop lesson)
    cap = 6 if len(uniq) > 4 else 4
    return [
        {"objective": a, "role": _infer_role(a), "index": str(i)}
        for i, a in enumerate(uniq[:cap])
    ]


def _infer_role(text: str) -> str:
    """Map objective text → role. Short keys use word boundaries (ui⊂build bug)."""
    tl = text.lower()
    for keys, role in _ROLE_HINTS:
        for k in keys:
            if len(k) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", tl):
                    return role
            elif k in tl:
                return role
    return "implement"


def _recipe(mode: str) -> dict[str, Any]:
    if mode == "thin":
        try:
            from conductor.core.wave_planner import parallel_recipe_thin

            thin_parallel = parallel_recipe_thin(stuck=False)
        except Exception:  # noqa: BLE001
            thin_parallel = None
        return {
            "name": "thin",
            "steps": [
                "1. conductor_start_pack (done) — keep session_id",
                "2. Host tools only: prefer ONE large mixed batch (reads+writes); "
                "host may segment — do not reimplement Hermes scheduler",
                "3. Wave advisory: A reads/status → B writes → C spawn (only if stuck)",
                "4. memory_episodic write outcome with tags (optional but preferred)",
                "5. Do NOT fanout remnants, pillar_status, or governance unless blocked",
            ],
            "forbidden_unless_stuck": [
                "remnant_orchestrate fanout",
                "pillar_status",
                "crucible_workspace",
                "governance_audit",
                "serializing whole turn because one barrier tool exists",
            ],
            "parallel_recipe": thin_parallel,
            "wave_order": ["A", "B", "C"],
            "host_batch_policy": {
                "prefer_single_batch": True,
                "do_not_dual_own_hermes_segmentation": True,
            },
        }
    return {
        "name": "full",
        "steps": [
            "1. conductor_start_pack (done) — note axes + fanout_ready",
            "2. remnant_orchestrate action=fanout dispatch=host|hermes objectives=axes",
            "3. PARENT (not MCP): SPAWN host tools THIS turn — Grok spawn_subagent "
            "×N from tool_calls[i].arguments OR Hermes hermes_batch delegate_task(tasks) "
            "(wave C; waves field on fanout payload)",
            "4. remnant_orchestrate action=spawn_ack handles=[{remnant_id, clone_handle}]",
            "5. When each clone finishes: remnant_orchestrate action=report",
            "6. remnant_orchestrate action=merge when await ready "
            "(force+accept_theater only when host never spawned / theater)",
            "7. terminate abandoned remnants (action=terminate) instead of "
            "leaving awaiting_host forever",
            "8. memory_episodic + track resolve",
        ],
        "forbidden_unless_needed": [
            "pillar_status spam",
            "dispatch=local when host can spawn (local is fallback only)",
            "reading tool_calls without spawning (ritual without clones)",
            "implementing all axes yourself while tool_calls sit unread",
            "reimplementing Hermes tool-batch segmentation inside Conductor",
        ],
        "wave_order": ["A", "B", "C"],
        "host_batch_policy": {
            "prefer_single_batch": True,
            "spawn_preference": "hermes_batch / delegate_task(tasks=[…])",
            "do_not_dual_own_hermes_segmentation": True,
        },
    }


def fanout_payload_from_policy(
    policy: dict[str, Any],
    *,
    parent_goal: str = "",
    work_root: str | None = None,
) -> dict[str, Any] | None:
    """Ready-to-send remnant_orchestrate fanout args for full mode."""
    if not policy.get("fanout_recommended"):
        return None
    axes = policy.get("axes") or []
    if len(axes) < 2:
        return None
    dispatch = policy.get("dispatch_default") or "host"
    # work_root present → hybrid preflight then host deepen
    if work_root and dispatch == "host":
        dispatch = "hybrid"
    return {
        "action": "fanout",
        "dispatch": dispatch,
        "parent_goal": parent_goal or "",
        "work_root": work_root,
        "objectives": [a["objective"] for a in axes],
        "auto_work": True,
    }
