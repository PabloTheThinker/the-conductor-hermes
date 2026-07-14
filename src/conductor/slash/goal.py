"""Standing goal loop — /goal command state machine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from conductor.agent.provider import LLMProvider, parse_judge_verdict
from conductor.agent.verification import (
    VerificationStore,
    evidence_satisfies_goal,
    goal_requires_evidence,
)
from conductor.memory.episodic import record_lifecycle_event
from conductor.session.store import SessionStore
from conductor.slash.contract import GoalContract, parse_contract

if TYPE_CHECKING:
    from conductor.agent.runtime import AgentRuntime

GOAL_META_KEY = "goal_state"
CONTINUATION_BANNER = "Continuing toward goal"
CONTINUATION_TEMPLATE = (
    f"{CONTINUATION_BANNER}\n"
    "Goal: {goal}\n"
    "{contract_block}"
    "{subgoals_block}\n"
    "Continue working toward this goal. Take the next concrete step."
)

StreamCallback = Callable[[str], None]


class GoalKickoffContext(Protocol):
    store: SessionStore
    runtime: AgentRuntime
    goals: GoalManager
    session_id: str


@dataclass
class GoalKickoffResult:
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class GoalState:
    goal: str = ""
    status: str = "idle"  # idle | active | paused | done
    turns_used: int = 0
    max_turns: int = 20
    last_reason: str = ""
    user_preempted: bool = False
    contract: dict[str, str] = field(default_factory=dict)
    subgoals: list[str] = field(default_factory=list)
    raw_goal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "status": self.status,
            "turns_used": self.turns_used,
            "max_turns": self.max_turns,
            "last_reason": self.last_reason,
            "user_preempted": self.user_preempted,
            "contract": self.contract,
            "subgoals": self.subgoals,
            "raw_goal": self.raw_goal,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalState:
        subgoals_raw = data.get("subgoals") or []
        subgoals = [str(s) for s in subgoals_raw] if isinstance(subgoals_raw, list) else []
        contract_raw = data.get("contract") or {}
        contract = (
            GoalContract.from_dict(contract_raw).to_dict()
            if isinstance(contract_raw, dict)
            else {}
        )
        return cls(
            goal=str(data.get("goal", "")),
            status=str(data.get("status", "idle")),
            turns_used=int(data.get("turns_used", 0)),
            max_turns=int(data.get("max_turns", 20)),
            last_reason=str(data.get("last_reason", "")),
            user_preempted=bool(data.get("user_preempted", False)),
            contract=contract,
            subgoals=subgoals,
            raw_goal=str(data.get("raw_goal", data.get("goal", ""))),
        )

    def contract_obj(self) -> GoalContract:
        return GoalContract.from_dict(self.contract)


_STUB_PHRASES = (
    "making progress toward the file goal",
    "working on the standing goal",
)


def _turn_had_substance(turn: Any) -> bool:
    response = (getattr(turn, "response", None) or "").strip()
    tool_events = getattr(turn, "tool_events", None) or []
    if response and not any(phrase in response.lower() for phrase in _STUB_PHRASES):
        return True
    return bool(tool_events)


def _response_may_satisfy_contract(state: GoalState, response: str) -> bool:
    """Hard gate: empty/stub output never counts as goal achievement (narration check)."""
    text = (response or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if any(phrase in lowered for phrase in _STUB_PHRASES):
        return False
    if lowered.startswith("i.l.o received:") and len(text) < 80:
        return False
    contract = state.contract_obj()
    verify = (contract.verification or "").strip()
    # Path-like goals / verify clauses require an artifact signal in the response.
    path_hint = ""
    for token in (state.goal, verify, state.raw_goal):
        if not token:
            continue
        for part in str(token).split():
            if part.startswith("/") and "." in part:
                path_hint = part
                break
        if path_hint:
            break
    if path_hint:
        return path_hint in text and (
            "created" in lowered
            or "wrote" in lowered
            or "written" in lowered
            or "containing" in lowered
            or "bytes to" in lowered
        )
    if verify:
        # Free-text verify: require some overlap beyond pure confidence claims
        if verify.lower() not in lowered and not any(
            w in lowered for w in verify.lower().split() if len(w) > 4
        ):
            if "complete" not in lowered and "done" not in lowered:
                return False
    return True


def _evidence_allows_done(store: SessionStore, session_id: str, state: GoalState) -> tuple[bool, str]:
    """Judgment: contract-bound goals need durable verification evidence."""
    contract = state.contract_obj()
    verify = (contract.verification or "").strip()
    if not goal_requires_evidence(state.goal, state.raw_goal, verify):
        return True, "no strict evidence contract"
    events = VerificationStore(store).list_events(session_id, limit=200)
    return evidence_satisfies_goal(
        goal=state.goal,
        raw_goal=state.raw_goal,
        verification_field=verify,
        events=events,
    )


def _append_turn_output(lines: list[str], turn: Any) -> None:
    """Assemble user-visible goal output — assistant text only, no tool traces or stubs."""
    text = (turn.response or "").strip()
    if not text:
        return
    if any(phrase in text.lower() for phrase in _STUB_PHRASES):
        return
    lines.append(text)


def _contract_block(state: GoalState) -> str:
    block = state.contract_obj().render_block()
    return f"Completion contract:\n{block}\n" if block else ""


def _subgoals_block(state: GoalState) -> str:
    if not state.subgoals:
        return ""
    lines = ["Subgoals:"]
    for sg in state.subgoals:
        lines.append(f"- {sg}")
    return "\n".join(lines) + "\n"


def _continue_if_needed(
    ctx: GoalKickoffContext,
    turn: Any,
    lines: list[str],
    *,
    on_live: StreamCallback | None = None,
    depth: int = 0,
    emit_done: bool = True,
) -> None:
    """Judge substantive turn output; banner only when judge returns continue."""
    state = ctx.goals.load(ctx.session_id)
    if state.status != "active" or not state.goal:
        return
    if depth > state.max_turns:
        return
    if not _turn_had_substance(turn):
        return

    ctx.goals.record_turn(ctx.session_id)
    verdict, reason = ctx.goals.judge_goal(
        ctx.session_id,
        turn.response or "",
        ctx.runtime.provider,
    )
    if verdict == "done":
        msg = f"Goal achieved: {reason}" if reason else "Goal achieved"
        if emit_done:
            lines.append(msg)
        ctx.goals.mark_done(ctx.session_id, reason)
        if on_live:
            on_live(msg)
        return

    if ctx.goals.clear_user_preemption(ctx.session_id):
        return

    prompt = ctx.goals.continuation_prompt(ctx.session_id)
    if not prompt:
        return

    lines.append(CONTINUATION_BANNER)
    if on_live:
        on_live(CONTINUATION_BANNER)

    cont_turn = ctx.runtime.run_turn(ctx.session_id, prompt, quiet=True)
    _append_turn_output(lines, cont_turn)
    _continue_if_needed(ctx, cont_turn, lines, on_live=on_live, depth=depth + 1)


def _last_assistant_response(store: SessionStore, session_id: str) -> str:
    rec = store.get_session(session_id)
    if not rec:
        return ""
    for msg in reversed(rec.messages):
        if msg.role == "assistant" and msg.content.strip():
            return msg.content.strip()
    return ""


@dataclass
class _TurnView:
    response: str
    tool_events: list[str] = field(default_factory=list)


def run_subgoal_kickoff(
    ctx: GoalKickoffContext,
    *,
    on_live: StreamCallback | None = None,
) -> GoalKickoffResult:
    """Re-evaluate standing goal after /subgoal — judge last output, continue if needed."""
    state = ctx.goals.load(ctx.session_id)
    if not state.goal:
        return GoalKickoffResult(lines=[])

    lines: list[str] = []
    last_response = _last_assistant_response(ctx.store, ctx.session_id)
    prior = _TurnView(response=last_response)
    _continue_if_needed(ctx, prior, lines, on_live=on_live)
    return GoalKickoffResult(lines=lines)


def run_goal_kickoff(
    ctx: GoalKickoffContext,
    goal_text: str,
    *,
    on_live: StreamCallback | None = None,
) -> GoalKickoffResult:
    """Run standing-goal kickoff + judge/continuation loop; assemble clean user-visible lines."""
    state = ctx.goals.load(ctx.session_id)
    lines: list[str] = []
    contract_block = _contract_block(state)
    subgoals_block = _subgoals_block(state)
    prompt = (
        f"Standing goal: {state.goal or goal_text}\n"
        f"{contract_block}"
        f"{subgoals_block}"
        "Take the first concrete step toward this goal now."
    )
    turn = ctx.runtime.run_turn(ctx.session_id, prompt, quiet=True)
    _append_turn_output(lines, turn)
    # Resolve response from session if run_turn ended on tool round with empty final_text
    if not (turn.response or "").strip():
        last = _last_assistant_response(ctx.store, ctx.session_id)
        if last:
            turn = type(turn)(session_id=turn.session_id, response=last, tool_events=turn.tool_events)
            _append_turn_output(lines, turn)
    _continue_if_needed(ctx, turn, lines, on_live=on_live)
    return GoalKickoffResult(lines=lines)


class GoalManager:
    def __init__(self, store: SessionStore, *, default_max_turns: int = 20) -> None:
        self.store = store
        self.default_max_turns = default_max_turns

    def load(self, session_id: str) -> GoalState:
        raw = self.store.get_meta(session_id, GOAL_META_KEY)
        if not raw:
            return GoalState(max_turns=self.default_max_turns)
        return GoalState.from_dict(raw)

    def save(self, session_id: str, state: GoalState) -> None:
        self.store.set_meta(session_id, GOAL_META_KEY, state.to_dict())

    def on_user_turn(self, session_id: str) -> None:
        """User-originated chat preempts queued goal continuations for this cycle."""
        state = self.load(session_id)
        if state.status == "active" and state.goal:
            state.user_preempted = True
            self.save(session_id, state)

    def clear_user_preemption(self, session_id: str) -> bool:
        state = self.load(session_id)
        if state.user_preempted:
            state.user_preempted = False
            self.save(session_id, state)
            return True
        return False

    def set_goal(self, session_id: str, text: str) -> GoalState:
        raw = text.strip()
        headline, contract = parse_contract(raw)
        state = GoalState(
            goal=headline or raw,
            raw_goal=raw,
            status="active",
            turns_used=0,
            max_turns=self.default_max_turns,
            user_preempted=False,
            contract=contract.to_dict(),
            subgoals=[],
        )
        self.save(session_id, state)
        record_lifecycle_event(
            self.store,
            session_id,
            kind="goal_set",
            content=f"Standing goal set: {state.goal[:300]}",
            outcome="pending",
            emotion_primary="determined",
            emotion_intensity=0.55,
            context=state.goal,
            extra_tags=["goal"],
        )
        return state

    def add_subgoal(self, session_id: str, text: str) -> GoalState:
        state = self.load(session_id)
        if not state.goal:
            state.goal = "(pending)"
        entry = text.strip()
        if entry and entry not in state.subgoals:
            state.subgoals.append(entry)
        # Mid-loop criteria reopen the standing objective for judge + continuation.
        state.status = "active"
        state.last_reason = ""
        state.user_preempted = False
        self.save(session_id, state)
        return state

    def pause(self, session_id: str) -> GoalState:
        state = self.load(session_id)
        if state.goal:
            state.status = "paused"
            self.save(session_id, state)
        return state

    def resume(self, session_id: str) -> GoalState:
        state = self.load(session_id)
        if state.goal and state.status == "paused":
            state.status = "active"
            self.save(session_id, state)
        return state

    def clear(self, session_id: str) -> GoalState:
        state = GoalState(max_turns=self.default_max_turns)
        self.save(session_id, state)
        return state

    def continuation_prompt(self, session_id: str) -> str | None:
        state = self.load(session_id)
        if state.status != "active" or not state.goal:
            return None
        if state.turns_used >= state.max_turns:
            state.status = "paused"
            state.last_reason = "turn budget exhausted"
            self.save(session_id, state)
            return None
        return CONTINUATION_TEMPLATE.format(
            goal=state.goal,
            contract_block=_contract_block(state),
            subgoals_block=_subgoals_block(state),
        )

    def record_turn(self, session_id: str) -> GoalState:
        state = self.load(session_id)
        if state.status == "active":
            state.turns_used += 1
            self.save(session_id, state)
        return state

    def mark_done(self, session_id: str, reason: str) -> GoalState:
        state = self.load(session_id)
        state.status = "done"
        state.last_reason = reason
        self.save(session_id, state)
        record_lifecycle_event(
            self.store,
            session_id,
            kind="goal_done",
            content=f"Goal achieved: {reason or state.goal[:200]}",
            outcome="success",
            emotion_primary="satisfaction",
            emotion_intensity=0.7,
            context=state.goal,
            extra_tags=["goal"],
        )
        return state

    def status_text(self, session_id: str) -> str:
        state = self.load(session_id)
        if not state.goal:
            return "No standing goal. Use /goal set <text> or /goal <text>."
        lines = [
            f"Goal ({state.status}): {state.goal}",
            f"Turns: {state.turns_used}/{state.max_turns}",
        ]
        contract_block = state.contract_obj().render_block()
        if contract_block:
            lines.append("Contract:")
            lines.append(contract_block)
        if state.subgoals:
            lines.append("Subgoals:")
            for sg in state.subgoals:
                lines.append(f"  - {sg}")
        if state.last_reason:
            lines.append(f"Last: {state.last_reason}")
        return "\n".join(lines)

    def judge_goal(
        self,
        session_id: str,
        response: str,
        provider: LLMProvider,
    ) -> tuple[str, str]:
        state = self.load(session_id)
        # Guard: empty/stub narration cannot satisfy artifact or verify contracts.
        if not _response_may_satisfy_contract(state, response):
            return "continue", "insufficient substance for contract"
        # Judgment ledger: contract-bound goals need durable tool evidence.
        ok_ev, ev_reason = _evidence_allows_done(self.store, session_id, state)
        if not ok_ev:
            return "continue", f"judgment: {ev_reason}"
        contract_block = state.contract_obj().render_block()
        subgoals_block = _subgoals_block(state).strip()
        evidence_lines = []
        for e in VerificationStore(self.store).list_events(session_id, limit=8):
            evidence_lines.append(f"- [{e.status}] {e.kind}: {e.summary[:120]}")
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "(none)"
        prompt = (
            "[goal-judge]\n"
            f"Goal: {state.goal}\n"
            + (f"Contract:\n{contract_block}\n" if contract_block else "")
            + (f"{subgoals_block}\n" if subgoals_block else "")
            + f"Verification evidence:\n{evidence_block}\n"
            + f"Response: {response}\n\n"
            'Reply with JSON: {"done": true|false, "reason": "..."}'
        )
        result = provider.chat([{"role": "user", "content": prompt}])
        verdict, reason = parse_judge_verdict(result.content)
        if verdict == "done" and not _response_may_satisfy_contract(state, response):
            return "continue", "judge done rejected: contract not evidenced"
        if verdict == "done":
            ok_ev2, ev_reason2 = _evidence_allows_done(self.store, session_id, state)
            if not ok_ev2:
                return "continue", f"judgment: {ev_reason2}"
        return verdict, reason

    def post_turn_hook(
        self,
        session_id: str,
        response: str,
        runtime: AgentRuntime,
        provider: LLMProvider,
        *,
        tool_events: list[str] | None = None,
        on_token: StreamCallback | None = None,
        quiet: bool = False,
        _depth: int = 0,
    ) -> int:
        """Judge the turn and optionally run continuation turns. Returns extra turns run."""
        state = self.load(session_id)
        if state.status != "active" or not state.goal:
            return 0
        if _depth > state.max_turns:
            return 0

        turn = _TurnView(response=response, tool_events=tool_events or [])
        if not _turn_had_substance(turn):
            return 0

        self.record_turn(session_id)
        verdict, reason = self.judge_goal(session_id, response, provider)
        if verdict == "done":
            self.mark_done(session_id, reason)
            msg = f"Goal achieved: {reason}" if reason else "Goal achieved"
            if not quiet:
                print(msg)
            if on_token:
                on_token(msg)
            return 0

        if self.clear_user_preemption(session_id):
            return 0

        prompt = self.continuation_prompt(session_id)
        if not prompt:
            return 0

        if not quiet:
            print(CONTINUATION_BANNER)
        if on_token:
            on_token(CONTINUATION_BANNER)

        cont_turn = runtime.run_turn(session_id, prompt, on_token=None, quiet=True)
        if on_token and cont_turn.response:
            on_token(cont_turn.response)

        extra = 1
        if _turn_had_substance(cont_turn):
            extra += self.post_turn_hook(
                session_id,
                cont_turn.response,
                runtime,
                provider,
                tool_events=cont_turn.tool_events,
                on_token=on_token,
                quiet=quiet,
                _depth=_depth + 1,
            )
        return extra
