"""Shared agent conversation loop."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from conductor.agent.provider import LLMProvider, get_provider
from conductor.agent.tools import TOOL_SCHEMAS, execute_tool
from conductor.agent.verify_stop import (
    should_nudge_verify_on_stop,
    verify_nudge_message,
)
from conductor.config import IloConfig, load_config
from conductor.core.runtime import ConductorRuntime
from conductor.research.index import build_research_index_text
from conductor.session.compress import compress_messages_for_model
from conductor.session.store import SessionStore
from conductor.skills.commands import storage_content_for_user_turn
from conductor.skills.loader import build_skills_index_text, ensure_skills_seeded

StreamCallback = Callable[[str], None]

_CORE_SYSTEM = """You are The Conductor — resonance partner and orchestrator of agents, tools, memory, and standing goals.
You lock wavelength with the host agent (meister) when a host soul is present; you do not replace them.
Operate with neurodivergent clarity and relentless forward progress.
Be direct, capable, and proactive. Use tools when they help accomplish the user's objective.
For deep simulation and parallel clone reasoning, use crucible_workspace (Global Workspace layer).
When asked to reply with exact text, output only that text."""


def build_system_prompt(
    *,
    memory_block: str = "",
    host_soul: str | None = None,
    mode: str | None = None,
    search_host: bool = True,
) -> str:
    """Compose system prompt via Soul Resonance + skills index + research + memory.

    By default, **resonates** Conductor SOUL with a discovered or provided host
    meister soul (Hermes / OpenClaw / CONDUCTOR_HOST_SOUL). See docs/SOUL_RESONANCE.md.
    """
    from conductor.soul.resonance import SoulMode, resonate

    ensure_skills_seeded()
    skills_block = build_skills_index_text()
    research_block = build_research_index_text()

    resolved_mode: SoulMode | None = None
    if mode in {"resonate", "solo", "host_only"}:
        resolved_mode = mode  # type: ignore[assignment]

    result = resonate(
        host_soul=host_soul,
        conductor_soul=None,  # load partner SOUL.md
        mode=resolved_mode,
        search_host=search_host,
        memory_block=memory_block,
        skills_block=skills_block,
        research_block=research_block,
    )
    if result.prompt.strip():
        return result.prompt
    # Absolute fallback
    parts = [_CORE_SYSTEM, skills_block, research_block]
    if memory_block.strip():
        parts.append(memory_block.strip())
    return "\n\n---\n\n".join(p for p in parts if p)

def _stream_text(text: str, on_token: StreamCallback) -> None:
    """Emit incremental token chunks for streaming surfaces."""
    if not text:
        return
    if len(text) <= 8:
        on_token(text)
        return
    step = max(2, len(text) // 4)
    for i in range(0, len(text), step):
        on_token(text[i : i + step])


@dataclass
class TurnResult:
    session_id: str
    response: str
    tool_events: list[str] = field(default_factory=list)
    verify_nudged: bool = False
    tool_rounds_used: int = 0


class AgentRuntime:
    def __init__(
        self,
        store: SessionStore | None = None,
        cfg: IloConfig | None = None,
        provider: LLMProvider | None = None,
        conductor: ConductorRuntime | None = None,
    ) -> None:
        self.store = store or SessionStore()
        self.cfg = cfg or load_config()
        self.provider = provider or get_provider(self.cfg)
        self.conductor = conductor or ConductorRuntime(self.store)
        self.max_tool_rounds = int(getattr(self.cfg, "max_tool_rounds", 32) or 32)
        self.keep_recent_messages = int(getattr(self.cfg, "keep_recent_messages", 24) or 24)
        self.compress_after_messages = int(
            getattr(self.cfg, "compress_after_messages", 40) or 40
        )
        self._system_prompt = build_system_prompt()

    def refresh_system_prompt(self) -> None:
        self._system_prompt = build_system_prompt()

    def _messages_for_session(self, session_id: str) -> list[dict[str, Any]]:
        # Live memory each turn (scars/seals/episodes) — not a dead store
        memory_block = ""
        try:
            from conductor.memory.context_inject import build_live_memory_block

            memory_block = build_live_memory_block(self.store, session_id)
        except Exception:  # noqa: BLE001
            memory_block = ""
        system = build_system_prompt(memory_block=memory_block)

        rec = self.store.get_session(session_id)
        if not rec:
            return [{"role": "system", "content": system}]
        msgs: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for m in rec.messages:
            content = m.content
            if m.role == "user" and m.extras.get("llm_content"):
                content = str(m.extras["llm_content"])
            entry: dict[str, Any] = {"role": m.role, "content": content}
            tool_calls = m.extras.get("tool_calls")
            if tool_calls:
                entry["tool_calls"] = tool_calls
                if not entry["content"]:
                    entry["content"] = None
            if m.role == "tool" and m.extras.get("tool_call_id"):
                entry["tool_call_id"] = m.extras["tool_call_id"]
            msgs.append(entry)
        return compress_messages_for_model(
            msgs,
            keep_recent=self.keep_recent_messages,
            compress_after=self.compress_after_messages,
        )

    def run_turn(
        self,
        session_id: str,
        user_text: str,
        *,
        on_token: StreamCallback | None = None,
        quiet: bool = False,
    ) -> TurnResult:
        stored_user, user_extras = storage_content_for_user_turn(user_text)
        self.store.append_message(session_id, "user", stored_user, extras=user_extras or None)
        messages = self._messages_for_session(session_id)
        tool_events: list[str] = []
        tool_names_this_turn: list[str] = []
        written_paths_this_turn: list[str] = []
        final_text = ""
        verify_nudged = False
        rounds_used = 0

        for _ in range(self.max_tool_rounds):
            rounds_used += 1
            result = self.provider.chat(messages, tools=TOOL_SCHEMAS)
            if result.tool_calls:
                tool_call_payload = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in result.tool_calls
                ]
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": result.content or None,
                    "tool_calls": tool_call_payload,
                }
                messages.append(assistant_msg)
                self.store.append_message(
                    session_id,
                    "assistant",
                    result.content or "",
                    extras={"tool_calls": tool_call_payload},
                )
                for tc in result.tool_calls:
                    args = tc["arguments"] if isinstance(tc["arguments"], dict) else {}
                    if str(tc["name"]) == "write_file" and args.get("path"):
                        written_paths_this_turn.append(str(args.get("path")))
                    output = execute_tool(
                        tc["name"],
                        tc["arguments"],
                        session_id=session_id,
                        store=self.store,
                    )
                    tool_events.append(f"{tc['name']}: {output[:200]}")
                    tool_names_this_turn.append(str(tc["name"]))
                    if not quiet and on_token is None:
                        print(f"  ◆ tool {tc['name']}")
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": output,
                    }
                    messages.append(tool_msg)
                    self.store.append_message(
                        session_id,
                        "tool",
                        output,
                        extras={"tool_call_id": tc["id"]},
                    )
                continue

            # Model wants to stop — verify-on-stop may force one more round (code only)
            if should_nudge_verify_on_stop(
                tool_names_this_turn=tool_names_this_turn,
                store=self.store,
                session_id=session_id,
                already_nudged=verify_nudged,
                written_paths=written_paths_this_turn,
            ):
                verify_nudged = True
                nudge = verify_nudge_message()
                messages.append({"role": "user", "content": nudge})
                self.store.append_message(
                    session_id,
                    "user",
                    nudge,
                    extras={"verify_on_stop": True},
                )
                continue

            final_text = result.content or ""
            # Unify done: contract-bound / code goals need ledger evidence to claim done
            try:
                from conductor.agent.verification import (
                    claims_done_without_evidence,
                    goal_requires_evidence,
                )
                from conductor.slash.goal import GoalManager

                gstate = GoalManager(self.store).load(session_id)
                needs_ev = False
                if gstate.status == "active" and gstate.goal:
                    verify = ""
                    try:
                        verify = (gstate.contract_obj().verification or "").strip()
                    except Exception:  # noqa: BLE001
                        verify = ""
                    needs_ev = goal_requires_evidence(
                        gstate.goal, gstate.raw_goal or gstate.goal, verify
                    )
                if (
                    not verify_nudged
                    and needs_ev
                    and claims_done_without_evidence(
                        final_text, store=self.store, session_id=session_id
                    )
                ):
                    verify_nudged = True
                    nudge = (
                        "[Judgment] You claimed done/complete but the verification "
                        "ledger has no successful evidence this session. Run a tool "
                        "that proves the artifact (write_file / shell_verify) before "
                        "claiming done."
                    )
                    messages.append({"role": "user", "content": nudge})
                    self.store.append_message(
                        session_id,
                        "user",
                        nudge,
                        extras={"judgment_done_gate": True},
                    )
                    continue
            except Exception:  # noqa: BLE001
                pass

            self.store.append_message(session_id, "assistant", final_text)
            if on_token:
                _stream_text(final_text, on_token)
            elif not quiet:
                print(final_text)
            break

        return TurnResult(
            session_id=session_id,
            response=final_text,
            tool_events=tool_events,
            verify_nudged=verify_nudged,
            tool_rounds_used=rounds_used,
        )

    def ensure_session(
        self,
        *,
        resume: str | None = None,
        continue_last: bool = False,
        source: str = "cli",
    ) -> str:
        if resume:
            rec = self.store.resolve_session(resume)
            if not rec:
                raise ValueError(f"Session not found: {resume}")
            return rec.id
        if continue_last:
            rec = self.store.latest_session(source=source) or self.store.latest_session()
            if rec:
                return rec.id
            raise ValueError("No previous session to continue")
        return self.store.create_session(source=source).id
