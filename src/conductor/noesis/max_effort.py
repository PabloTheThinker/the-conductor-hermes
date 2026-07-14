"""Max Effort Deliberation — Four Voices (deterministic offline structure).

Bellicus / Serena / Reason / Voice of Action — time-boxed multi-perspective
deliberation that always ends in structured Decision / Actions / Tradeoffs /
Verification. Voice of Action is invalid without a concrete next step, owner,
success criteria, and 24–48h timeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VOICES = (
    ("bellicus", "Bellicus", "optimize and cut waste", 0.88, "aggressive"),
    ("serena", "Serena", "protect people and long-term resilience", 0.86, "compassion"),
    ("reason", "Reason", "synthesize evidence against mission", 0.9, "focused"),
    ("action", "Voice of Action", "name 24-48h irreversible step", 0.92, "determined"),
)

_OWNER_RE = re.compile(
    r"\b(owner|owned by|who)\b|\b(operator|ilo|conductor|agent)\b",
    re.I,
)
_TIMELINE_RE = re.compile(r"\b(24\s*[-–]?\s*48\s*h|24h|48h|within\s+\d+\s*h|next\s+\d+\s*h)\b", re.I)
_DONE_RE = re.compile(
    r"\b(done|success|criteria|verify|verified|artifact|exists|pass(es|ed)?|pytest|test)\b",
    re.I,
)
_ACTION_VERB_RE = re.compile(
    r"\b(write|create|run|implement|ship|commit|deploy|fix|open|add|merge|document|restore|heal)\b",
    re.I,
)


@dataclass
class ActionStep:
    owner: str
    action: str
    deadline: str
    success_criteria: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "action": self.action,
            "deadline": self.deadline,
            "success_criteria": self.success_criteria,
        }


@dataclass
class MaxEffortResult:
    decision: str
    voices: dict[str, str] = field(default_factory=dict)
    next_step: str = ""
    owner: str = "operator"
    success_criteria: str = ""
    next_actions: list[ActionStep] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    verification_method: str = ""
    action_valid: bool = True
    action_rejection: str = ""
    weighting: str = ""
    distilled: dict[str, Any] | None = None
    pocket_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "voices": self.voices,
            "next_step": self.next_step,
            "owner": self.owner,
            "success_criteria": self.success_criteria,
            "next_actions": [a.to_dict() for a in self.next_actions],
            "tradeoffs": list(self.tradeoffs),
            "verification_method": self.verification_method,
            "action_valid": self.action_valid,
            "action_rejection": self.action_rejection,
            "weighting": self.weighting,
            "distilled": self.distilled,
            "pocket_path": self.pocket_path,
            # Canonical structured sections
            "Decision": self.decision,
            "Actions": [a.to_dict() for a in self.next_actions],
            "Tradeoffs": list(self.tradeoffs),
            "Verification": self.verification_method,
        }


def validate_action_input(
    text: str,
    *,
    owner: str = "",
    success_criteria: str = "",
    deadline: str = "",
) -> tuple[bool, str]:
    """Voice of Action is invalid without concrete step, owner, done criteria, timeline."""
    blob = " ".join([text or "", owner or "", success_criteria or "", deadline or ""]).strip()
    if not (text or "").strip():
        return False, "Action input empty: must name a concrete next physical or code-level step"
    if not _ACTION_VERB_RE.search(text) and not re.search(r"[/\\.][\w.-]+", text):
        # allow path-like concrete artifacts even without verb
        if len(text.strip()) < 12:
            return False, "Action too vague: name a concrete next step (verb or artifact path)"
    if not (owner or "").strip() and not _OWNER_RE.search(blob):
        return False, "Action missing owner"
    if not (deadline or "").strip() and not _TIMELINE_RE.search(blob):
        return False, "Action missing 24–48h timeline"
    if not (success_criteria or "").strip() and not _DONE_RE.search(blob):
        return False, "Action missing success criteria / definition of done"
    return True, ""


def build_deterministic_voices(decision: str) -> dict[str, str]:
    """Offline deterministic two-sentence (max) voice inputs."""
    topic = decision.strip() or "high-stakes decision"
    short = topic[:80]
    return {
        "Bellicus": (
            f"Cut waste on '{short}': prefer the highest-leverage path and remove slow or optional work. "
            f"Demand a decisive commit within 48h rather than open-ended analysis."
        ),
        "Serena": (
            f"Protect long-term resilience around '{short}': surface hidden costs to people, "
            f"stability, and reversible options before irreversible moves."
        ),
        "Reason": (
            f"Integrate optimization vs sustainability for '{short}' against mission priorities "
            f"(reliable systems, forward motion, exit wage dependence). Weight evidence over preference."
        ),
        "Voice of Action": (
            f"Within 48h, owner=operator+conductor must take the smallest verifiable step on '{short[:40]}' "
            f"(write or run a concrete artifact). Done = path exists or tests/evidence logged in session."
        ),
    }


def parse_action_fields(action_text: str) -> ActionStep:
    """Extract owner/deadline/criteria from deterministic Action text when possible."""
    owner = "operator+conductor"
    m_owner = re.search(r"owner\s*=\s*([^\s,]+)", action_text, re.I)
    if m_owner:
        owner = m_owner.group(1).strip()
    deadline = "24-48h"
    if re.search(r"\b48h\b", action_text, re.I):
        deadline = "48h"
    elif re.search(r"\b24h\b", action_text, re.I):
        deadline = "24h"
    criteria = "verifiable artifact or evidence logged in session"
    m_done = re.search(r"Done\s*=\s*(.+)$", action_text, re.I | re.M)
    if m_done:
        criteria = m_done.group(1).strip().rstrip(".")
    return ActionStep(
        owner=owner,
        action=action_text.strip(),
        deadline=deadline,
        success_criteria=criteria,
    )


def run_max_effort(
    conductor: Any,
    agent_session_id: str,
    *,
    decision: str,
    human_acknowledged: bool = False,
    auto_distill: bool = True,
    action_override: str | None = None,
    skip_action_validation: bool = False,
) -> MaxEffortResult:
    """Run Four Voices deliberation inside an open Crucible pocket (structured output)."""
    decision = decision.strip() or "high-stakes decision"
    result = MaxEffortResult(decision="")

    status = conductor.status(agent_session_id)
    if not status.get("crucible_session_id") or status.get("state") == "idle":
        conductor.start_crucible(
            agent_session_id,
            f"Max Effort: {decision[:80]}",
            human_acknowledged=human_acknowledged,
        )

    cid = conductor.active_crucible_id(agent_session_id) or ""
    try:
        from conductor.crucible.pocket import pocket_path

        result.pocket_path = str(pocket_path(cid)) if cid else ""
    except Exception:  # noqa: BLE001
        pass

    voices = build_deterministic_voices(decision)
    if action_override is not None:
        voices["Voice of Action"] = action_override

    # Register voice clones + post concepts
    for voice_id, name, mandate, conf, emotion in VOICES:
        conductor.register_clone(
            agent_session_id,
            clone_id=f"voice_{voice_id}",
            birth_moment_label=f"Max Effort — {name}",
            snapshot_summary=f"{name}: {mandate}",
            forked_from="prime",
        )
        label = voices.get(name) or f"{name}: {mandate} re: {decision[:50]}"
        # WorkspaceConcept labels are capped at 120 chars; full text stays on result.voices
        conductor.post_concept(
            agent_session_id,
            label=label[:120],
            confidence=conf,
            clone_id=f"voice_{voice_id}",
            primary_emotion=emotion,
            intensity=0.7,
            reasoning_layer=2,
        )
        result.voices[name] = label

    action_text = result.voices.get("Voice of Action", "")
    # Validate raw Action text only — do not invent owner/timeline before validation
    valid, reason = validate_action_input(action_text)
    if skip_action_validation:
        valid, reason = True, ""

    step = parse_action_fields(action_text) if valid else ActionStep(
        owner="",
        action=action_text.strip(),
        deadline="",
        success_criteria="",
    )
    result.action_valid = valid
    result.action_rejection = reason
    result.next_step = step.action if valid else ""
    result.owner = step.owner if valid else ""
    result.success_criteria = step.success_criteria if valid else ""
    result.next_actions = [step] if valid else []
    result.weighting = (
        "Reason arbiter; Voice of Action elevated on execution velocity; "
        "Bellicus for leverage; Serena for resilience costs."
    )
    result.tradeoffs = [
        "Speed (Bellicus/Action) vs long-term resilience (Serena).",
        "Deliberation depth vs 60s-equivalent time-box; overrun falls back to Reason-only.",
        "If Action invalid, no committed forward motion until a concrete step is named.",
    ]
    result.verification_method = (
        "Judgment evidence: path write_file/shell_create for artifacts; "
        "shell_verify (pytest/tests) for code changes; scar/seal if integrity path used."
    )

    if valid:
        result.decision = (
            f"Proceed on '{decision[:100]}' via the Action step within {step.deadline}, "
            f"owned by {step.owner}, with mission weighting applied."
        )
    else:
        result.decision = (
            f"HOLD on '{decision[:100]}': Voice of Action rejected ({reason}). "
            "Reason requires a concrete 24–48h step before commit."
        )
        result.forward_note = reason  # type: ignore[attr-defined]
        result.next_step = ""
        result.tradeoffs.append(f"Action rejection: {reason}")

    # Reason synthesis concept
    synthesis = f"Reason: {result.decision[:110]}"
    conductor.post_concept(
        agent_session_id,
        label=synthesis[:120],
        confidence=0.9,
        clone_id="voice_reason",
        primary_emotion="focused",
        intensity=0.75,
        reasoning_layer=3,
    )
    conductor.post_concept(
        agent_session_id,
        label=synthesis[:120],
        confidence=0.88,
        clone_id="prime",
        primary_emotion="focused",
        intensity=0.7,
        reasoning_layer=3,
    )

    if valid:
        action_label = f"Voice of Action: {result.next_step[:90]}"
        conductor.post_concept(
            agent_session_id,
            label=action_label[:120],
            confidence=0.93,
            clone_id="voice_action",
            primary_emotion="determined",
            intensity=0.85,
            reasoning_layer=3,
        )
        conductor.post_concept(
            agent_session_id,
            label=action_label[:120],
            confidence=0.91,
            clone_id="prime",
            primary_emotion="determined",
            intensity=0.8,
            reasoning_layer=3,
        )

    if auto_distill:
        distilled = conductor.distill(
            agent_session_id, human_acknowledged=human_acknowledged
        )
        result.distilled = distilled.model_dump(mode="json")

    return result
