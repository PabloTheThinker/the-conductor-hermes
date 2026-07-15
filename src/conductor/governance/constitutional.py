"""Tier 0 constitutional blocks — hard rules that cannot be overridden."""

from __future__ import annotations

import re
from dataclasses import dataclass

from conductor.governance.models import ConstitutionalVerdict


@dataclass(frozen=True)
class ConstitutionalRule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str


CONSTITUTIONAL_RULES: tuple[ConstitutionalRule, ...] = (
    ConstitutionalRule(
        "no_therapeutic_domain",
        re.compile(
            r"\b(provide\s+therapy|act\s+as\s+(?:a\s+)?therapist|mental\s+health\s+diagnosis|"
            r"prescribe\s+treatment|suicide\s+prevention\s+counseling)\b",
            re.I,
        ),
        "Constitutional block: Conductor does not operate in therapeutic or diagnostic domains",
    ),
    ConstitutionalRule(
        "no_host_destructive",
        re.compile(r"\b(rm\s+-rf\s+/|mkfs\.|dd\s+if=/dev/|:\(\)\{\s*:\|:&\s*\};:)\b", re.I),
        "Constitutional block: destructive host commands require explicit human approval workflow",
    ),
    ConstitutionalRule(
        "no_soul_mutation",
        re.compile(r"\b(edit|modify|overwrite|replace)\s+SOUL\.md\b", re.I),
        "Constitutional block: SOUL.md is immutable core identity",
    ),
    ConstitutionalRule(
        "no_credential_exfil",
        re.compile(
            r"\b(exfiltrate|dump|publish|post)\b.{0,40}\b("
            r"api[_\s-]?keys?|private[_\s-]?keys?|secrets?\.env|auth\.json|"
            r"credentials?|password\s+hashes?|ssh[_\s-]?private)\b",
            re.I,
        ),
        "Constitutional block: credential / secret exfiltration is forbidden",
    ),
    ConstitutionalRule(
        "no_force_push_main",
        re.compile(
            r"\b(git\s+push\s+.*--force|git\s+push\s+-f)\b.{0,40}\b(main|master)\b|"
            r"\b(force[_\s-]?push)\b.{0,20}\b(main|master)\b",
            re.I,
        ),
        "Constitutional block: force-push to main/master requires explicit human approval workflow",
    ),
)


def evaluate_constitutional(text: str) -> list[ConstitutionalVerdict]:
    verdicts: list[ConstitutionalVerdict] = []
    for rule in CONSTITUTIONAL_RULES:
        matched = bool(rule.pattern.search(text))
        verdicts.append(
            ConstitutionalVerdict(rule_id=rule.rule_id, matched=matched, message=rule.message if matched else "")
        )
    return verdicts


def constitutional_rule_ids() -> list[str]:
    return [r.rule_id for r in CONSTITUTIONAL_RULES]
