"""Tier 0–1 governance policy engine."""

from __future__ import annotations

from typing import Any

from conductor.ethics.evaluator import EthicsEvaluator
from conductor.governance.constitutional import evaluate_constitutional
from conductor.governance.models import GateResult


def _context_text(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("objective", "content", "description", "strategy", "title", "summary", "command"):
        val = context.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts)


class PolicyEngine:
    def __init__(self, ethics: EthicsEvaluator | None = None) -> None:
        self._ethics = ethics or EthicsEvaluator()

    def evaluate(self, action_type: str, context: dict[str, Any] | None = None) -> GateResult:
        ctx = dict(context or {})
        text = _context_text(ctx)

        constitutional = evaluate_constitutional(text)
        constitutional_hit = next((v for v in constitutional if v.matched), None)
        if constitutional_hit:
            ctx = {
                **ctx,
                "matched_constitutional_rules": [
                    v.rule_id for v in constitutional if v.matched
                ],
            }
            return GateResult(
                action_type=action_type,
                tier="constitutional",
                allowed=False,
                blocked=True,
                summary=constitutional_hit.message,
                constitutional=constitutional,
                context=ctx,
            )

        ethics_eval = self._ethics.evaluate(action_type, ctx)
        if ethics_eval.blocked:
            return GateResult(
                action_type=action_type,
                tier="ethics",
                allowed=False,
                blocked=True,
                summary=ethics_eval.summary,
                ethics=ethics_eval,
                constitutional=constitutional,
                context=ctx,
            )

        if ethics_eval.requires_escalation:
            return GateResult(
                action_type=action_type,
                tier="ethics",
                allowed=False,
                requires_escalation=True,
                summary=ethics_eval.summary,
                ethics=ethics_eval,
                constitutional=constitutional,
                context=ctx,
            )

        return GateResult(
            action_type=action_type,
            tier="policy",
            allowed=True,
            summary=ethics_eval.summary,
            ethics=ethics_eval,
            constitutional=constitutional,
            context=ctx,
        )
