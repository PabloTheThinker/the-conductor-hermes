"""Offline remnant work packs — real structured deliverables for parallel branches.

Remnants used to only store shells + generic heartbeats. This module produces a
**work pack** the host agent can execute: role, steps, risks, acceptance, and
high-signal insights suitable for Tier-1 merge.
"""

from __future__ import annotations

import re
from typing import Any

# Shared across all remnants in a fanout so Tier-1 divergence stays low.
# Kept on heartbeats for divergence scoring; stripped from final merge insights.
SHARED_DECISION = "parallel branches: execute each work pack then merge once"

_FILLER = frozenset(
    {
        "preserve modular conductor boundary",
        "unit contribution",
        "plan-only (no root)",
        "implement minimal vertical slice first",
        "self-check: acceptance criteria below before merge",
        "inventory: list files/modules this branch owns (avoid cross-branch edits)",
        SHARED_DECISION.lower(),
    }
)

# Substrings that mark ritual / preflight noise (case-insensitive)
_FILLER_SUBSTR = (
    "preserve modular conductor boundary",
    "unit contribution:",
    "plan-only (no root)",
    "no workspace root for clone scan",
    "set conductor_clone_root",
    "proceeding with plan-only",
    "local preflight found",
    "first slice: implement minimal vertical",
    "role-lane:",
    "likely-touch:",
    "strategy-lane:",
    "…from clone…",
    "...from clone...",
    "do not expand into sibling",
    "return json-ish summary",
    "your final message must be structured",
    "placeholder insight",
    # Work-pack chrome that flooded merges on 1.14–1.15 live drives
    "focus_tokens:",
    "] objective:",
    "] deliver:",
    "] accept:",
    "sibling lanes untouched",
    "ready for parent merge after host report",
    "execute branch ",
    "scope: lock definition of done",
    "own only files for this axis",
    "stay in this lane",
    "leave sibling packs",
    "write failing tests against real entry points",  # generic step echo
    "make green; capture command output",
    "ship interactive visual/ui slice",
    "prove with manual open or paint",
    "implement core path for «",
    "implement core path for «",
    "deliverable for «",
    "parallel branches: execute each work pack",
    "awaiting host spawn",
    "host spawn:",
    "branch 1/",
    "branch 2/",
    "branch 3/",
    "branch 4/",
)

# Role prefix stripped for content-addressed near-dedup (AgentDrive spirit)
_ROLE_PREFIX_RE = re.compile(
    r"^\[(?:verify|implement|surface|rules|graph|backend|architect|safety|"
    r"product|docs|polish|ai|combat|world|character|meta|integrate|"
    r"clone:finding|clone|grid|app|warn|cancer-adapt)\]\s*",
    re.I,
)
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_./-]{2,}")

# Default merge surface size (AgentDrive growth-merge keeps a short ranked set)
DEFAULT_MERGE_INSIGHT_LIMIT = 16
# Token Jaccard above this ⇒ treat as near-duplicate (keep higher signal)
NEAR_DEDUP_JACCARD = 0.52

# Parent should scaffold empty work_root before parallel write-capable clones
SCAFFOLD_FIRST = (
    "Parent scaffold-first: create work_root layout (pkg dirs, empty modules, README) "
    "before fanout so clones do not race on greenfield files"
)


def is_filler_insight(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t or len(t) < 8:
        return True
    if t in _FILLER:
        return True
    if t.startswith("unit ") and "contribution:" in t:
        return True
    for sub in _FILLER_SUBSTR:
        if sub in t:
            return True
    # Bracket role tags that only restate the pack (no concrete artifact)
    if re.match(
        r"^\[(verify|implement|surface|rules|graph|backend|architect|safety)\]\s+"
        r"(objective|deliver|accept|focus_tokens)\s*:",
        t,
    ):
        return True
    # Generic template acceptance lines without concrete artifact names
    if t.startswith("[") and "has a concrete artifact" in t and len(t) < 160:
        return True
    if "branch objective" in t and "concrete artifact" in t:
        return True
    # Pure restatement of role without evidence (short)
    if re.match(r"^\[(verify|implement|surface)\]\s+\S", t) and len(t) < 40:
        return True
    return False


def normalize_insight_key(text: str) -> str:
    """Content-address style key: strip role tags + collapse whitespace.

    Inspired by AgentDrive content-addressed dedup — identical meaning converges
    even when clones wrap the same finding in different ``[role]`` prefixes.
    """
    s = (text or "").strip()
    s = _ROLE_PREFIX_RE.sub("", s)
    # Drop common process prefixes that create false uniques
    s = re.sub(r"^(alternative-path|chosen-path):\s*", "", s, flags=re.I)
    s = _WS_RE.sub(" ", s).strip().lower()
    return s


def tokenize_insight(text: str) -> set[str]:
    """AgentDrive-style token set for overlap / Jaccard near-dedup."""
    key = normalize_insight_key(text)
    return set(_TOKEN_RE.findall(key))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / float(len(a | b))


def signal_score(text: str) -> float:
    """Rank insight by evidence strength (AgentDrive growth-merge axis idea).

    Higher = more worth keeping in Tier-1 merge / memory.
    """
    t = (text or "").strip()
    if not t:
        return 0.0
    low = t.lower()
    score = 1.0
    # Strong evidence markers
    if "[clone:finding]" in low or low.startswith("[clone:finding]"):
        score += 4.0
    if any(tag in low for tag in ("[grid]", "[app]", "[docs]", "[verify]", "[surface]")):
        # Role tags alone are weak; boost only with substance below
        score += 0.5
    # Concrete artifacts
    if re.search(r"\b\d+/\d+\b", t):  # 5/5, 8/8 tests
        score += 2.5
    if re.search(r"\b\d+(\.\d+)?\s*(s|sec|seconds|ms|cycles?|ticks?)\b", low):
        score += 2.0
    if re.search(r"\b(pytest|passed|failed|cuda|rtx|gpu|torch)\b", low):
        score += 2.0
    if re.search(r"[\w./-]+\.(py|md|json|ts|tsx|js|toml|yml|yaml)\b", low):
        score += 2.5
    if re.search(r"(wrote|created|shipped|documented|verified|green)\b", low):
        score += 1.5
    if re.search(r"\bhttps?://\S+", low):  # live URL evidence
        score += 2.0
    if re.search(r"\b[a-f0-9]{8}-[a-f0-9]{4}-", low):  # session / uuid evidence
        score += 1.0
    # Process chrome (should already be filler; demote if leaked)
    if "parallel branches" in low or "strategy-lane" in low:
        score -= 5.0
    if "objective:" in low or "deliver:" in low or "focus_tokens" in low:
        score -= 5.0
    # Reflective dump noise from Tier-2 (live white-cell: 12 alternative-path lines)
    if low.startswith("alternative-path:"):
        score -= 3.5
    if low.startswith("chosen-path:"):
        score -= 1.5
    if low.startswith("[warn]"):
        score -= 1.0
    # Prefer moderate length findings over slogans
    if 24 <= len(t) <= 220:
        score += 0.5
    elif len(t) > 400:
        score -= 0.5
    return score


def filter_insights(items: list[str]) -> list[str]:
    """Drop filler and exact-duplicate insights (order-preserving)."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = (raw or "").strip()
        if not s or is_filler_insight(s):
            continue
        key = normalize_insight_key(s) or s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _is_near_duplicate(candidate: str, kept: list[str], *, threshold: float) -> bool:
    ct = tokenize_insight(candidate)
    if not ct:
        return False
    ckey = normalize_insight_key(candidate)
    for prev in kept:
        if ckey == normalize_insight_key(prev):
            return True
        # Shared distinctive fingerprint (pytest N passed, same path, same kill counts)
        pt = tokenize_insight(prev)
        if jaccard(ct, pt) >= threshold:
            return True
        # Substring containment of substantial cores
        pk = normalize_insight_key(prev)
        if len(ckey) >= 24 and len(pk) >= 24:
            if ckey in pk or pk in ckey:
                return True
    return False


def curate_insights(
    items: list[str],
    *,
    limit: int | None = DEFAULT_MERGE_INSIGHT_LIMIT,
    near_dedup: float = NEAR_DEDUP_JACCARD,
    max_alternative_paths: int = 2,
) -> list[str]:
    """Filter + Jaccard near-dedup + rank + cap (final merge / memory surface).

    AgentDrive analog: growth merge keeps a short ranked compound set, not every
    overlapping clone echo. Live white-cell lesson: 61 lines → ≤16 high-signal.
    """
    cleaned = filter_insights(list(items or []))
    ranked = sorted(
        enumerate(cleaned),
        key=lambda iv: (-signal_score(iv[1]), iv[0]),
    )
    out: list[str] = []
    alt_count = 0
    for _, s in ranked:
        if signal_score(s) <= 0.0:
            continue
        low = s.lower().strip()
        if low.startswith("alternative-path:"):
            if alt_count >= max_alternative_paths:
                continue
            alt_count += 1
        if _is_near_duplicate(s, out, threshold=near_dedup):
            continue
        out.append(s)
        if limit is not None and limit >= 0 and len(out) >= limit:
            break
    return out


def ensure_shared_decisions(decisions: list[str] | None) -> list[str]:
    """Always pin SHARED_DECISION first so Tier-1 divergence stays low.

    Clones that send only lane-local key_decisions previously blew divergence
    to ~0.9 and forced Tier-2 (digital-white-cell lesson).
    """
    out: list[str] = [SHARED_DECISION]
    seen = {SHARED_DECISION.lower()}
    for raw in decisions or []:
        s = (raw or "").strip()
        if not s:
            continue
        low = s.lower()
        if low in seen or "parallel branches" in low:
            continue
        # Drop process chrome from decision channel
        if is_filler_insight(s):
            continue
        if low.startswith("alternative-path:") or low.startswith("chosen-path:"):
            continue
        seen.add(low)
        out.append(s[:200])
        if len(out) >= 6:
            break
    return out


def _infer_role(objective: str, strategy: str = "") -> str:
    text = f"{objective} {strategy}".lower()
    rules = [
        # integrate before surface (chess glue was double-surface, self-loop 1.18.5)
        (("integrate", "game loop", "ui vs ai", "wire", "glue"), "integrate"),
        (("3d", "three", "render", "mesh", "camera", "webgl", "scene"), "surface"),
        (("hero", "brand", "navigation", "nav", "landing", "first-viewport"), "surface"),
        # product before generic "visual" so pillars bento is not surface
        (("pillar", "product story", "capability", "feature section", "bento"), "product"),
        (("combo", "combos a", "thin vs", "thin by", "full mode", "orchestration contract"), "product"),
        (("ux", "ui", "css", "visual", "editorial"), "surface"),
        (("minimax", "alpha-beta", "ai opponent", "evaluation"), "ai"),
        (("rule", "engine", "legal", "checkmate", "chess", "logic", "validator", "d20", "stats"), "rules"),
        (("combat", "enemy", "enemies", "loot", "victory", "defeat", "turns"), "combat"),
        (("world", "map location", "exploration", "npc", "dialogue", "quest"), "world"),
        (("character creation", "archetype", "point-buy", "inventory start", "starting inventory"), "character"),
        (("hud", "title screen", "game shell", "visual system"), "surface"),
        (
            (
                "responsive",
                "a11y",
                "polish",
                "motion",
                "static build",
                "production",
                "manifesto",
                "footer",
                "og meta",
                "skip link",
                "focus",
                "save/load",
                "localstorage",
                "settings",
            ),
            "polish",
        ),
        (("hermes", "install", "setup", "docs", "cta", "conversion", "readme", "terminal"), "docs"),
        (("multiverse", "timeline", "fork", "branch", "collapse", "graph", "track"), "graph"),
        (("test", "pytest", "verify", "evidence", "ci"), "verify"),
        (("api", "server", "backend", "db", "schema"), "backend"),
        (("design", "arch", "plan", "spec"), "architect"),
        (("security", "auth", "ethics", "policy"), "safety"),
    ]
    for keys, role in rules:
        for k in keys:
            # Short tokens need word boundaries (e.g. "ui" ⊂ "build")
            if len(k) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text):
                    return role
            elif k in text:
                return role
    return "implement"


def _tokenize_tokens(objective: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", objective)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        low = t.lower()
        if low in seen or low in {"the", "and", "for", "with", "from"}:
            continue
        seen.add(low)
        out.append(t)
        if len(out) >= 8:
            break
    return out


def build_work_pack(
    *,
    objective: str,
    strategy: str = "",
    index: int = 0,
    total: int = 1,
) -> dict[str, Any]:
    """Build a structured work pack for one remnant objective."""
    obj = (objective or "").strip() or "unspecified branch"
    strat = (strategy or "").strip()
    role = _infer_role(obj, strat)
    tokens = _tokenize_tokens(obj)

    steps = [
        f"Scope: lock definition of done for «{obj[:80]}»",
        f"Own only files for this axis ({role}); do not edit sibling lanes",
    ]
    if role == "surface":
        steps.extend(
            [
                "Ship interactive visual/UI slice with load-safe entry",
                "Prove with manual open or paint/DOM smoke",
            ]
        )
    elif role == "product":
        steps.extend(
            [
                "Write product truth sections (pillars/capabilities) with real names not filler",
                "Vary layout family from hero; no three equal cards",
            ]
        )
    elif role == "docs":
        steps.extend(
            [
                "Land install path + docs links that match real repo commands",
                "Primary CTA + one secondary with distinct intent only",
            ]
        )
    elif role == "polish":
        steps.extend(
            [
                "Responsive collapse, contrast, reduced-motion, asset paths",
                "Serve locally and capture URL / HTTP 200 as evidence",
            ]
        )
    elif role == "rules":
        steps.extend(
            [
                "Implement pure logic module with exported formulas/state",
                "Add unit tests that call shipped functions",
            ]
        )
    elif role == "combat":
        steps.extend(
            [
                "Implement turn loop, attack resolution, HP, win/lose",
                "Prove with a scripted encounter or manual fight smoke",
            ]
        )
    elif role == "world":
        steps.extend(
            [
                "Ship map/locations graph + at least one NPC dialogue or quest flag",
                "Wire travel between locations without soft-locks",
            ]
        )
    elif role == "character":
        steps.extend(
            [
                "Character create UI: archetype/stats/start kit",
                "Persist sheet into the play state machine",
            ]
        )
    elif role == "integrate":
        steps.extend(
            [
                "Wire surface + rules + AI/systems into one playable loop",
                "Prove turn order, win/lose, and no soft-lock on happy path",
            ]
        )
    elif role == "ai":
        steps.extend(
            [
                "Implement opponent search (minimax/α-β or equivalent) behind a pure API",
                "Bench a few plies; return move + eval evidence in report",
            ]
        )
    elif role == "research":
        steps.extend(
            [
                "List sources + open questions; capture links in findings",
                "Do not invent citations; mark confidence per claim",
            ]
        )
    elif role == "ops":
        steps.extend(
            [
                "Land deploy config (compose/k8s/CI) with real service names",
                "Prove health check or dry-run; note rollback path",
            ]
        )
    elif role == "graph":
        steps.extend(
            [
                "Implement fork/switch/collapse or edge graph API first",
                "Wire one parent consumer of the graph",
            ]
        )
    elif role == "verify":
        steps.extend(
            [
                "Run shipped tests/CLI against real entry points (shell allowed)",
                "Capture command output + assert non-empty evidence in report findings",
                "If red: fix only this lane's code or note blockers with repro",
            ]
        )
    elif role == "backend":
        steps.extend(
            [
                "Implement invoke/API path against real runtime (not stub)",
                "Return non-empty result + runtime evidence",
            ]
        )
    elif role == "architect":
        steps.extend(
            [
                "Design module boundaries and public contracts",
                "Land one vertical slice implementing the contract",
            ]
        )
    elif role == "safety":
        steps.extend(
            [
                "Enumerate high-stakes actions and gates",
                "Wire checklist/policy on the real tool path",
            ]
        )
    else:
        steps.extend(
            [
                f"Implement core path for «{obj[:60]}»",
                "Verify with a real run (test, CLI, or HTTP)",
            ]
        )

    risks = [
        "scope creep into sibling remnant territory",
        "generic insights without executable steps",
    ]
    if total > 1:
        risks.append(f"merge conflict with {total - 1} parallel branch(es)")

    acceptance = [
        f"Deliverable for «{obj[:70]}» is runnable or test-backed on the real path",
        f"Sibling lanes untouched (role={role})",
        "Ready for parent merge after host report",
    ]

    files_hint = []
    if tokens:
        files_hint = [f"likely-touch: *{t.lower()}*" for t in tokens[:4]]

    # Keep key_decisions aligned across fanout siblings so Tier-1 merge
    # stays available. Do NOT seed template insights — they polluted merges.
    decisions = [SHARED_DECISION]
    if strat:
        decisions.append(f"strategy-lane: {strat[:80]}")

    # Host spawn capability hints (consumed by clone_worker.build_host_spawn_request)
    # verify must be write/shell-capable so pytest can actually run (1.14 live lesson)
    if role == "verify":
        host_subagent_type = "general-purpose"
        host_capability_mode = "all"
    elif role in {"explore", "scout"}:
        host_subagent_type = "explore"
        host_capability_mode = "read-only"
    elif role in {"architect", "plan"}:
        host_subagent_type = "plan"
        host_capability_mode = "read-only"
    else:
        host_subagent_type = "general-purpose"
        host_capability_mode = "all"

    pack = {
        "role": role,
        "objective": obj,
        "strategy": strat,
        "index": index,
        "total": total,
        "steps": steps,
        "risks": risks,
        "acceptance": acceptance,
        "files_hint": files_hint,
        "key_decisions": decisions,
        # Empty until the host reports real findings (avoids merge chrome)
        "insights": [],
        "progress_percent": 15.0 if total > 1 else 20.0,
        "host_subagent_type": host_subagent_type,
        "host_capability_mode": host_capability_mode,
        "success_evidence": [
            "report findings[] with concrete commands/paths/results",
            "clone_handle set via spawn_ack",
            "no sibling-lane file edits",
        ],
        "host_instruction": (
            f"Branch {index + 1}/{total} ({role}) — {obj[:120]}. "
            f"Host spawn: {host_subagent_type}/{host_capability_mode}. "
            "Do real work in this lane only; report evidence, not pack templates."
        ),
    }
    return pack


def host_playbook_from_packs(packs: list[dict[str, Any]]) -> dict[str, Any]:
    """Ordered guide for the parent agent after fanout or merge."""
    ordered = sorted(packs, key=lambda p: int(p.get("index") or 0))
    phases = []
    for p in ordered:
        phases.append(
            {
                "order": int(p.get("index") or 0) + 1,
                "role": p.get("role"),
                "objective": p.get("objective"),
                "host_instruction": p.get("host_instruction"),
                "steps": list(p.get("steps") or [])[:4],
                "acceptance": list(p.get("acceptance") or [])[:3],
            }
        )
    return {
        "title": "Parallel host playbook",
        "shared_decision": SHARED_DECISION,
        "scaffold_first": SCAFFOLD_FIRST,
        "how_to_use": (
            "1) Parent scaffolds work_root (dirs + stub modules) if greenfield. "
            "2) Spawn host clones with non-overlapping file ownership. "
            "3) spawn_ack → report findings (not pack templates) → merge. "
            "Do not heartbeat empty progress — real decisions/insights only."
        ),
        "phases": phases,
        "merge_when": "all phases have artifacts or blockers recorded",
        "skip_remnants_next_time_if": (
            "single linear task under ~30 minutes with one clear path"
        ),
    }


def merge_host_playbook(
    remnants: list[Any],
    merged_insights: list[str],
) -> dict[str, Any]:
    """Build playbook from remnant records (with optional work_pack) + insights."""
    packs: list[dict[str, Any]] = []
    for i, r in enumerate(remnants):
        wp = getattr(r, "work_pack", None)
        if isinstance(wp, dict) and wp.get("objective"):
            packs.append(wp)
        else:
            packs.append(
                build_work_pack(
                    objective=getattr(r, "task_objective", "") or "branch",
                    strategy=getattr(r, "strategy", "") or "",
                    index=i,
                    total=len(remnants),
                )
            )
    playbook = host_playbook_from_packs(packs)
    clean = curate_insights(list(merged_insights), limit=DEFAULT_MERGE_INSIGHT_LIMIT)
    playbook["merged_insights"] = clean
    playbook["signal_count"] = len(clean)
    # Prefer real findings over host_instruction chrome
    nexts = [
        c
        for c in clean
        if not str(c).lower().startswith("branch ")
        and not str(c).lower().startswith("alternative-path:")
    ][:5]
    if not nexts:
        nexts = [
            f"Complete phase {p.get('order')}: {str(p.get('objective') or '')[:80]}"
            for p in playbook["phases"][:3]
        ]
    playbook["next_actions"] = nexts
    playbook["spawn_guidance"] = (
        "verify lanes use general-purpose/all (shell ok). "
        "explore/scout stay read-only. Always spawn_ack with real handles. "
        "Report findings with paths/commands — pack templates are stripped on merge. "
        + SCAFFOLD_FIRST
    )
    playbook["track_hygiene"] = (
        "On successful merge with no active remnants, Conductor auto-resolves the track."
    )
    playbook["scaffold_first"] = SCAFFOLD_FIRST
    playbook["merge_insight_limit"] = DEFAULT_MERGE_INSIGHT_LIMIT
    return playbook
