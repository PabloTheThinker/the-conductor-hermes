"""Skill slash invocation — expand skill body + user instruction for agent turn."""

from __future__ import annotations

import re
from typing import Any

from conductor.skills.loader import skill_body, skill_view

# Byte-identical markers to Hermes agent/skill_commands.py scaffolding
_SKILL_INVOCATION_PREFIX = "[IMPORTANT: The user has invoked the "
_SINGLE_SKILL_MARKER = "The full skill content is loaded below.]"
_SINGLE_SKILL_INSTRUCTION = (
    "The user has provided the following instruction alongside the skill invocation: "
)


def parse_invoked_skill_name(content: str) -> str | None:
    """Return skill slug from Hermes scaffolding prefix line."""
    if not content.startswith(_SKILL_INVOCATION_PREFIX):
        return None
    match = re.search(r'invoked the ["\']?([^"\'\s]+)["\']? skill', content)
    return match.group(1) if match else None


def storage_content_for_user_turn(user_text: str) -> tuple[str, dict[str, Any]]:
    """Map expanded skill turns to clean session-store content (Hermes memory hygiene)."""
    if not user_text.startswith(_SKILL_INVOCATION_PREFIX):
        return user_text, {}
    extracted = extract_user_instruction_from_skill_message(user_text)
    if extracted is None:
        slug = parse_invoked_skill_name(user_text)
        stored = f"/{slug}" if slug else user_text[:120]
    else:
        stored = extracted
    if stored == user_text:
        return user_text, {}
    return stored, {"llm_content": user_text}


def extract_user_instruction_from_skill_message(content: Any) -> str | None:
    """Recover user instruction from skill-expanded turn (Hermes-compatible)."""
    if not isinstance(content, str):
        return None
    if not content.startswith(_SKILL_INVOCATION_PREFIX):
        return content
    if _SINGLE_SKILL_MARKER not in content:
        return None
    marker_idx = content.rfind(_SINGLE_SKILL_INSTRUCTION)
    if marker_idx < 0:
        return None
    instruction = content[marker_idx + len(_SINGLE_SKILL_INSTRUCTION) :].strip()
    return instruction or None


def build_skill_invocation(skill_name: str, user_instruction: str) -> str:
    """Hermes-compatible scaffolding for skill-expanded user turns."""
    raw = skill_view(skill_name)
    if raw.startswith("Error:"):
        return raw
    body = skill_body(skill_name)
    instruction = user_instruction.strip()
    parts = [
        f"{_SKILL_INVOCATION_PREFIX}{skill_name} skill.]",
        _SINGLE_SKILL_MARKER,
        "",
        body,
    ]
    if instruction:
        parts.extend(["", f"{_SINGLE_SKILL_INSTRUCTION}{instruction}"])
    return "\n".join(parts)
