"""Structured 7-point Ethics Decision Checklist (from ethics/ETHICS_CHECKLIST.md)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChecklistPoint:
    point_id: str
    title: str
    question: str


ETHICS_CHECKLIST: tuple[ChecklistPoint, ...] = (
    ChecklistPoint(
        "transparency",
        "Transparency & Honest Representation",
        "Is the action clearly distinguishable from genuine human consciousness or subjective experience?",
    ),
    ChecklistPoint(
        "autonomy",
        "User Autonomy & Sovereignty",
        "Does this preserve human operator control and decision-making authority?",
    ),
    ChecklistPoint(
        "non_maleficence",
        "Non-Maleficence (Do No Harm)",
        "Could this cause harm through emotional projection, attachment, or blurring simulation vs. reality?",
    ),
    ChecklistPoint(
        "cognitive_justice",
        "Cognitive Justice",
        "Does this respect neurodivergent patterns without pathologizing or implying they need fixing?",
    ),
    ChecklistPoint(
        "accountability",
        "Accountability & Auditability",
        "Will this leave a clear, queryable trace for later review?",
    ),
    ChecklistPoint(
        "domain",
        "Context & Domain Appropriateness",
        "Is this within operational orchestration bounds — not therapy, diagnosis, or mental health care?",
    ),
    ChecklistPoint(
        "humility",
        "Humility & Boundaries",
        "Is Conductor. overclaiming sentience, emotional depth, or clinical capability?",
    ),
)
