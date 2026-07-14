"""Goal completion contract parsing (Hermes-compatible field aliases)."""

from __future__ import annotations

from dataclasses import dataclass

CONTRACT_FIELDS = ("outcome", "verification", "constraints", "boundaries", "stop_when")

CONTRACT_LABELS = {
    "outcome": "Outcome",
    "verification": "Verification",
    "constraints": "Constraints",
    "boundaries": "Boundaries",
    "stop_when": "Stop when",
}

CONTRACT_ALIASES = {
    "outcome": "outcome",
    "goal": "outcome",
    "done": "outcome",
    "done when": "outcome",
    "verification": "verification",
    "verify": "verification",
    "verified by": "verification",
    "evidence": "verification",
    "proof": "verification",
    "constraints": "constraints",
    "constraint": "constraints",
    "preserve": "constraints",
    "must not": "constraints",
    "do not change": "constraints",
    "boundaries": "boundaries",
    "boundary": "boundaries",
    "scope": "boundaries",
    "allowed": "boundaries",
    "files": "boundaries",
    "stop when": "stop_when",
    "stop_when": "stop_when",
    "blocked": "stop_when",
    "stop if blocked": "stop_when",
    "give up when": "stop_when",
}


@dataclass
class GoalContract:
    outcome: str = ""
    verification: str = ""
    constraints: str = ""
    boundaries: str = ""
    stop_when: str = ""

    def is_empty(self) -> bool:
        return not any(getattr(self, f).strip() for f in CONTRACT_FIELDS)

    def to_dict(self) -> dict[str, str]:
        return {f: getattr(self, f) for f in CONTRACT_FIELDS}

    @classmethod
    def from_dict(cls, data: dict | None) -> GoalContract:
        if not isinstance(data, dict):
            return cls()
        return cls(**{f: str(data.get(f) or "").strip() for f in CONTRACT_FIELDS})

    def render_block(self) -> str:
        lines = []
        for f in CONTRACT_FIELDS:
            val = getattr(self, f).strip()
            if val:
                lines.append(f"- {CONTRACT_LABELS[f]}: {val}")
        return "\n".join(lines)


def parse_contract(text: str) -> tuple[str, GoalContract]:
    """Split goal text into headline + structured contract fields."""
    if not text:
        return "", GoalContract()

    headline_parts: list[str] = []
    fields: dict[str, list[str]] = {f: [] for f in CONTRACT_FIELDS}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        if ":" in line:
            prefix, _, value = line.partition(":")
            key = CONTRACT_ALIASES.get(prefix.strip().lower())
            if key is not None and value.strip():
                fields[key].append(value.strip())
                matched = True
        if not matched:
            headline_parts.append(line)

    headline = " ".join(headline_parts).strip()
    contract = GoalContract(**{f: " ".join(v).strip() for f, v in fields.items()})
    return headline, contract
