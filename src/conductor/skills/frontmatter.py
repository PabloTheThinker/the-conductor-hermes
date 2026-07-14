"""YAML frontmatter parsing for SKILL.md (agentskills.io compatible)."""

from __future__ import annotations

import re
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter dict, markdown body)."""
    if not content.startswith("---"):
        return {}, content

    match = re.search(r"\n---\s*\n", content[3:])
    if not match:
        return {}, content

    yaml_block = content[3 : match.start() + 3]
    body = content[match.end() + 3 :]
    try:
        parsed = yaml.safe_load(yaml_block)
        if isinstance(parsed, dict):
            return parsed, body
    except yaml.YAMLError:
        pass

    fallback: dict[str, Any] = {}
    for line in yaml_block.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fallback[key.strip()] = value.strip()
    return fallback, body
