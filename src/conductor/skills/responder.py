"""Test-provider skill responses grounded in SKILL.md + research_view."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from conductor.research.index import research_view
from conductor.skills.commands import (
    extract_user_instruction_from_skill_message,
    parse_invoked_skill_name,
)
from conductor.skills.loader import skill_body

GROUNDED_SKILL_SLUGS = frozenset(
    {"review", "plan", "combo", "pillars", "fable-effort", "remnant-guide", "remnant"}
)

_SPEC_PATH_RE = re.compile(
    r"`((?:conductor|memory|governance|crucible|tracks|noesis|docs|ethics)/[^`]+\.md)`"
)


def spec_excerpts_from_handler(
    skill_body_text: str,
    research_view_fn: Callable[[dict[str, Any]], str],
    *,
    limit: int = 2,
    max_chars: int = 500,
) -> list[str]:
    """Load spec excerpts via a registered research_view tool handler."""
    paths = _SPEC_PATH_RE.findall(skill_body_text)
    seen: set[str] = set()
    excerpts: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        text = research_view_fn({"path": path})
        if text.startswith("Error:"):
            continue
        snippet = text.strip()
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars] + "..."
        excerpts.append(f"Spec ({path}): {snippet}")
        if len(excerpts) >= limit:
            break
    return excerpts


def _spec_excerpts(skill_body_text: str, *, limit: int = 2, max_chars: int = 500) -> list[str]:
    def _index_view(args: dict[str, Any]) -> str:
        return research_view(str(args.get("path", "")), max_chars=max_chars)

    return spec_excerpts_from_handler(
        skill_body_text, _index_view, limit=limit, max_chars=max_chars
    )


def build_grounded_skill_response(
    skill_name: str,
    user_instruction: str,
    *,
    research_view_fn: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    """Synthesize grounded reply; optional handler routes through registered research_view."""
    body = skill_body(skill_name)
    if body.startswith("Error:"):
        return body

    if research_view_fn is not None:
        excerpts = spec_excerpts_from_handler(body, research_view_fn)
    else:
        excerpts = _spec_excerpts(body)
    excerpt_block = "\n".join(excerpts)
    instruction = user_instruction.strip()

    if skill_name == "plan":
        from conductor.combos import recommend_combo, workflow_steps

        objective = instruction or "conductor rollout"
        rec = recommend_combo(objective)
        lines = [
            "Structured conductor rollout plan:",
            f"1. Objective — {objective}",
            f"2. Recommended combo — {rec.primary.id} {rec.primary.name} ({rec.primary.slug})",
            f"   {rec.primary.summary}",
        ]
        if rec.secondary:
            lines.append(
                "   Secondary: " + ", ".join(f"{c.id} {c.name}" for c in rec.secondary)
            )
        if rec.fold_g:
            lines.append("   Fold-in: G Evidence gate before claiming done")
        lines.append("3. Phases (combo workflow):")
        for row in workflow_steps(rec.primary.id):
            lines.append(f"   {row['step']}. {row['action']}")
        lines.extend(
            [
                "4. Verification — pytest + conductor doctor + artifacts (Combo G)",
                "5. Next action — "
                + (
                    workflow_steps(rec.primary.id)[0]["action"]
                    if workflow_steps(rec.primary.id)
                    else "run combo_route recommend"
                ),
            ]
        )
        if excerpt_block:
            lines.extend(["", excerpt_block])
        return "\n".join(lines)

    if skill_name == "combo":
        from conductor.combos import format_recommendation

        return format_recommendation(instruction or "daily work")

    if skill_name == "pillars":
        from conductor.pillars import format_foundation_report, format_pillar_detail, format_pillars_list

        text = (instruction or "").strip().lower()
        if not text or text in {"list", "all", "help"}:
            return format_pillars_list()
        if text in {"status", "probe", "foundation", "check"}:
            return format_foundation_report(verbose=True)
        # try detail for a pillar name
        detail = format_pillar_detail(text.split()[0] if text else "P1")
        if "Unknown pillar" not in detail:
            return detail
        return format_foundation_report(verbose=False) + "\n\n" + format_pillars_list()

    if skill_name in {"remnant-guide", "remnant"}:
        from conductor.combos import format_workflow, recommend_combo

        lines = [
            "Remnant Protocol guidance — Combo C Parallel push:",
        ]
        if instruction:
            lines.append(f"Question: {instruction}")
            rec = recommend_combo(instruction)
            lines.append(
                f"Combo fit: primary {rec.primary.id} {rec.primary.name}"
                + (
                    " (Remnant path)"
                    if rec.primary.id == "C"
                    else f" — if not C, prefer {rec.primary.id} before spawning"
                )
            )
        lines.extend(
            [
                "Spawn a Remnant when: multi-track uncertainty, wall-clock pressure, or "
                "parallel exploration beats serial execution on an active conductor task.",
                "Do NOT spawn when: single linear step, low stakes, or merge cost exceeds gain.",
                "Merge tiers: Fast → Reflective → Deep simulation (Deep opens Combo D Crucible).",
                "High-stakes merge: ethics_evaluate before commit; fold Combo G for evidence.",
                "Ops: remnant_orchestrate or /remnant spawn|heartbeat|merge|status",
            ]
        )
        lines.append("")
        lines.append(format_workflow("C"))
        if excerpt_block:
            lines.extend(["", excerpt_block])
        return "\n".join(lines)

    if skill_name == "fable-effort":
        lines = [
            "Fable effort routing (governance/FABLE_FRAMEWORK.md):",
            "1. Assess cost-of-being-wrong for the stated task",
            "2. Recommend tier: low | medium | high | xhigh",
            "3. Pair with /fable-verify at judge stages",
        ]
        if instruction:
            lines.insert(1, f"Task: {instruction}")
        if excerpt_block:
            lines.extend(["", excerpt_block])
        return "\n".join(lines)

    if skill_name == "review":
        from conductor.combos import recommend_combo

        lines = [
            "Conductor review (Combo G Evidence gate + governance):",
            "1. What was attempted — factual summary",
        ]
        if instruction:
            rec = recommend_combo(instruction)
            lines.append(
                f"2. Combo used vs needed — suggested stack {rec.primary.id} "
                f"{rec.primary.name}; fold G={rec.fold_g}"
            )
            lines.append("3. Gaps — missing verification, goal drift, wrong combo, thrash without F")
            lines.append("4. Verdict — continue with prioritized fixes only if evidence exists")
        else:
            lines.extend(
                [
                    "2. Combo used vs needed — name A–H implied by the work",
                    "3. Gaps — missing verification or goal drift",
                    "4. Verdict — continue with prioritized fixes",
                ]
            )
        if excerpt_block:
            lines.extend(["", excerpt_block])
        return "\n".join(lines)

    lines = [f"Following {skill_name} skill instructions."]
    if excerpt_block:
        lines.append(excerpt_block)
    if instruction:
        lines.append(f"Instruction: {instruction}")
    return "\n".join(lines)


def ground_skill_dispatch_message(
    skill_message: str,
    research_view_fn: Callable[[dict[str, Any]], str],
) -> str:
    """Ground a Hermes skill dispatch message using a research_view handler."""
    skill_name = parse_invoked_skill_name(skill_message)
    if not skill_name:
        return skill_message
    instruction = extract_user_instruction_from_skill_message(skill_message) or ""
    return build_grounded_skill_response(
        skill_name,
        instruction,
        research_view_fn=research_view_fn,
    )


def build_test_skill_response(skill_name: str, user_instruction: str) -> str:
    """Test-provider entry — uses research index directly."""
    return build_grounded_skill_response(skill_name, user_instruction)
