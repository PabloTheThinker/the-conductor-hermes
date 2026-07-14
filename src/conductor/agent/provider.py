"""LLM providers — OpenAI-compatible HTTP and deterministic test provider."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from conductor.agent.goal_test_planner import (
    goal_text_from_prompt,
    plan_after_tool,
    plan_continuation_turn,
    plan_judge_reply,
    plan_standing_turn,
    planned_to_chat_result,
)
from conductor.config import IloConfig
from conductor.skills.commands import (
    extract_user_instruction_from_skill_message,
    parse_invoked_skill_name,
)
from conductor.skills.responder import build_test_skill_response


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict[str, Any]]


class LLMProvider:
    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ChatResult:
        raise NotImplementedError


class TestProvider(LLMProvider):
    """Deterministic provider for tests and offline verification."""

    _PATH_RE = re.compile(r"(/[\w./_-]+\.(?:txt|md|json|yaml|yml))")

    def _extract_path(self, text: str) -> str | None:
        match = self._PATH_RE.search(text)
        return match.group(1) if match else None

    def _file_written(self, messages: list[dict[str, Any]], path: str) -> bool:
        from conductor.agent.goal_test_planner import file_written

        return file_written(messages, path)

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ChatResult:
        after_tool = plan_after_tool(messages)
        if after_tool is not None:
            content, tool_calls = planned_to_chat_result(after_tool)
            return ChatResult(content=content, tool_calls=tool_calls)

        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = str(msg.get("content", ""))
                break

        if "Reply with exactly: CONDUCTOR_OK" in last_user:
            return ChatResult(content="CONDUCTOR_OK", tool_calls=[])

        if "what code did i give" in last_user.lower():
            for msg in messages:
                if msg.get("role") == "user" and "ALPHA" in str(msg.get("content", "")):
                    return ChatResult(content="You gave me the code ALPHA.", tool_calls=[])
            return ChatResult(content="I do not see a code in our history.", tool_calls=[])

        if last_user.strip().startswith("[goal-judge]"):
            planned = plan_judge_reply(last_user, messages)
            content, tool_calls = planned_to_chat_result(planned)
            return ChatResult(content=content, tool_calls=tool_calls)

        skill_name = parse_invoked_skill_name(last_user)
        if skill_name:
            instruction = extract_user_instruction_from_skill_message(last_user) or ""
            body = build_test_skill_response(skill_name, instruction)
            return ChatResult(content=body, tool_calls=[])

        if "Standing goal:" in last_user:
            goal_text = goal_text_from_prompt(last_user)
            planned = plan_standing_turn(goal_text, messages)
            content, tool_calls = planned_to_chat_result(planned)
            return ChatResult(content=content, tool_calls=tool_calls)

        if "Continuing toward goal" in last_user:
            goal_text = goal_text_from_prompt(last_user)
            planned = plan_continuation_turn(goal_text, messages)
            content, tool_calls = planned_to_chat_result(planned)
            return ChatResult(content=content, tool_calls=tool_calls)

        path = self._extract_path(last_user)
        if path and ("create" in last_user.lower() or "write" in last_user.lower()):
            if self._file_written(messages, path):
                return ChatResult(
                    content=f"Created {path} containing the requested content.",
                    tool_calls=[],
                )
            from conductor.agent.goal_test_planner import plan_tool_write

            planned = plan_tool_write(
                path,
                "probe" if "probe" in last_user.lower() else "done",
                call_id="call_write",
            )
            content, tool_calls = planned_to_chat_result(planned)
            return ChatResult(content=content, tool_calls=tool_calls)

        return ChatResult(
            content=f"Conductor: {last_user[:500]}",
            tool_calls=[],
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, cfg: IloConfig) -> None:
        self.cfg = cfg

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model or self.cfg.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.cfg.base_url}/chat/completions"
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        tool_calls: list[dict[str, Any]] = []
        for tc in choice.get("tool_calls") or []:
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                {
                    "id": tc.get("id", "call"),
                    "name": fn.get("name", ""),
                    "arguments": args,
                }
            )
        return ChatResult(content=choice.get("content") or "", tool_calls=tool_calls)


def get_provider(cfg: IloConfig) -> LLMProvider:
    """Prefer Hermes OAuth/provider system when not in test mode.

    CONDUCTOR_PROVIDER=test → offline TestProvider
    CONDUCTOR_PROVIDER=hermes|auto (default when using Hermes auth) → resolve via
    hermes_cli.auth + credential_pool (shared HERMES_HOME=$CONDUCTOR_HOME)
    Otherwise OpenAI-compatible with Hermes pool fill-in if api_key empty.
    """
    name = (cfg.provider or "openai").strip().lower()
    if name == "test":
        return TestProvider()

    # Hermes-first path
    if name in {"hermes", "auto", "hermes-auto"} or os.environ.get("CONDUCTOR_USE_HARNESS_AUTH", "1").strip() not in {
        "0",
        "false",
        "no",
    }:
        try:
            from conductor.agent.hermes_auth import resolve_hermes_runtime

            requested = None if name in {"hermes", "auto", "hermes-auto"} else name
            # When user set openai/openrouter explicitly, still try Hermes fill-in
            if name in {"openai", "openrouter", "xai", "copilot"} and cfg.api_key:
                return OpenAIProvider(cfg)
            creds = resolve_hermes_runtime(requested=requested)
            if creds.provider == "test":
                return TestProvider()
            if creds.ok():
                # Build a shallow cfg overlay for OpenAI-compatible chat
                from dataclasses import replace

                overlay = replace(
                    cfg,
                    provider=creds.provider,
                    api_key=creds.api_key,
                    base_url=creds.base_url or cfg.base_url,
                    model=creds.model or cfg.model,
                )
                return OpenAIProvider(overlay)
        except Exception:  # noqa: BLE001
            pass

    if not cfg.api_key:
        # Last attempt: Hermes pool / env via resolver
        try:
            from dataclasses import replace

            from conductor.agent.hermes_auth import resolve_hermes_runtime

            creds = resolve_hermes_runtime(requested=name if name not in {"openai", "openrouter"} else name)
            if creds.ok():
                return OpenAIProvider(
                    replace(
                        cfg,
                        provider=creds.provider,
                        api_key=creds.api_key,
                        base_url=creds.base_url or cfg.base_url,
                        model=creds.model or cfg.model,
                    )
                )
        except Exception:  # noqa: BLE001
            pass
    return OpenAIProvider(cfg)


def parse_judge_verdict(text: str) -> tuple[str, str]:
    """Parse judge JSON; returns (verdict, reason)."""
    text = text.strip()
    if not text:
        return "continue", "empty judge response"
    try:
        data = json.loads(text)
        done = bool(data.get("done"))
        reason = str(data.get("reason", ""))
        return ("done" if done else "continue"), reason
    except json.JSONDecodeError:
        if re.search(r'"done"\s*:\s*true', text, re.I):
            return "done", "parsed done from partial json"
        return "continue", "judge reply was not JSON"
