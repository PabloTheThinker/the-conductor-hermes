"""Structured tool results + deterministic output-risk scanning.

Model-facing text stays readable (Hermes-class power). Meta carries ok/error/risk
without blocking ordinary successful tool use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Secret-like patterns (deterministic, high-signal only).
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic_api_key",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"
        ),
    ),
    ("private_key_pem", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
]


@dataclass
class ToolResult:
    ok: bool
    content: str = ""
    error: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def as_model_text(self) -> str:
        """LLM-facing string — keeps Hermes-style free text on success."""
        if self.ok:
            return self.content
        if self.error:
            return self.error if self.error.startswith("Error") else f"Error: {self.error}"
        return self.content or "Error: tool failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "content": self.content,
            "error": self.error,
            "meta": dict(self.meta),
        }


def scan_output_risk(text: str) -> dict[str, Any] | None:
    """Scan tool output for secret-like findings. Never redacts content."""
    if not text:
        return None
    findings: list[str] = []
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(name)
    if not findings:
        return None
    return {
        "risk": "high",
        "findings": findings,
        "redacted": False,
    }


def attach_risk_meta(result: ToolResult) -> ToolResult:
    """Add risk meta when findings present; does not change ok/content."""
    risk = scan_output_risk(result.content or result.error or "")
    if risk:
        result.meta["risk"] = risk["risk"]
        result.meta["findings"] = risk["findings"]
        result.meta["redacted"] = False
    return result


def ok_result(content: str, **meta: Any) -> ToolResult:
    return attach_risk_meta(ToolResult(ok=True, content=content, meta=dict(meta)))


def err_result(error: str, **meta: Any) -> ToolResult:
    text = error if error.startswith("Error") else f"Error: {error}"
    return attach_risk_meta(ToolResult(ok=False, content=text, error=text, meta=dict(meta)))
