"""Pure standing-goal turn planning for TestProvider (no I/O)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_PATH_RE = re.compile(r"(/[\w./_-]+\.(?:txt|md|json|yaml|yml))")


@dataclass
class PlannedTurn:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def extract_path(text: str) -> str | None:
    match = _PATH_RE.search(text)
    return match.group(1) if match else None


def file_written(messages: list[dict[str, Any]], path: str) -> bool:
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        content = str(msg.get("content", ""))
        if path in content and "Wrote" in content:
            return True
    return False


def goal_text_from_prompt(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Goal:"):
            return line[5:].strip()
        if line.startswith("Standing goal:"):
            return line[14:].strip()
    return text


def subgoals_from_prompt(text: str) -> list[str]:
    subgoals: list[str] = []
    in_subgoals = False
    for line in text.splitlines():
        if line.strip() == "Subgoals:":
            in_subgoals = True
            continue
        if in_subgoals and line.startswith("- "):
            subgoals.append(line[2:].strip())
        elif in_subgoals and line.strip() and not line.startswith("- "):
            in_subgoals = False
    return subgoals


def subgoal_satisfied(subgoal: str, response: str) -> bool:
    sg = subgoal.lower().strip()
    resp = response.lower()
    if sg in resp:
        return True
    if "readable" in sg and "readable" in resp:
        return True
    return False


def synthesize_file_created(path: str, *, subgoals: list[str] | None = None) -> str:
    base = f"Created {path} containing the requested content."
    if subgoals and any("readable" in sg.lower() for sg in subgoals):
        return f"{base} File is readable."
    return base


def looks_complete(goal: str, response: str, messages: list[dict[str, Any]]) -> bool:
    path = extract_path(goal)
    if path:
        if file_written(messages, path):
            return True
        lowered = response.lower()
        if path in response and ("created" in lowered or "containing" in lowered):
            return True
        return False
    if is_multi_step_goal(goal):
        return "goal complete" in response.lower()
    return "goal complete" in response.lower()


def plan_tool_write(
    path: str,
    content: str,
    *,
    call_id: str = "call_goal_write",
) -> PlannedTurn:
    return PlannedTurn(
        content="",
        tool_calls=[
            {
                "id": call_id,
                "name": "write_file",
                "arguments": {"path": path, "content": content},
            }
        ],
    )


def plan_after_tool(messages: list[dict[str, Any]]) -> PlannedTurn | None:
    if not messages or messages[-1].get("role") != "tool":
        return None
    tool_out = str(messages[-1].get("content", ""))
    if "Wrote" not in tool_out:
        return None
    goal_user = ""
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = str(msg.get("content", ""))
        if "Standing goal:" in content or "Continuing toward goal" in content:
            goal_user = content
            break
    if not goal_user:
        return None
    goal_text = goal_text_from_prompt(goal_user)
    path = extract_path(goal_text)
    if not path or path not in tool_out:
        return None
    subgoals = subgoals_from_prompt(goal_user)
    return PlannedTurn(content=synthesize_file_created(path, subgoals=subgoals))


def plan_judge_reply(judge_prompt: str, messages: list[dict[str, Any]]) -> PlannedTurn:
    goal = ""
    response = ""
    subgoals: list[str] = []
    in_subgoals = False
    for line in judge_prompt.splitlines():
        stripped = line.strip()
        if line.startswith("Goal:"):
            goal = line[5:].strip()
            in_subgoals = False
        elif stripped == "Subgoals:":
            in_subgoals = True
        elif stripped.startswith("Verification evidence:") or stripped == "Contract:":
            in_subgoals = False
        elif in_subgoals and line.startswith("- "):
            # Real subgoal lines, not evidence rows that also use "- "
            item = line[2:].strip()
            if item.startswith("["):
                in_subgoals = False
            else:
                subgoals.append(item)
        elif line.startswith("Response:"):
            response = line[9:].strip()
            in_subgoals = False
    if subgoals:
        missing = [sg for sg in subgoals if not subgoal_satisfied(sg, response)]
        if missing:
            return PlannedTurn(content='{"done": false, "reason": "subgoals pending"}')
    if looks_complete(goal, response, messages):
        return PlannedTurn(content='{"done": true, "reason": "goal satisfied"}')
    return PlannedTurn(content='{"done": false, "reason": "still working"}')


def is_multi_step_goal(goal_text: str) -> bool:
    return "multi-step-goal" in goal_text.lower()


def plan_standing_turn(goal_text: str, messages: list[dict[str, Any]]) -> PlannedTurn:
    if is_multi_step_goal(goal_text):
        return PlannedTurn(content="Step one complete, more work remains.")
    path = extract_path(goal_text)
    if path and not file_written(messages, path):
        content = "probe" if "probe" in goal_text.lower() else "done"
        return plan_tool_write(path, content, call_id="call_standing_write")
    return PlannedTurn(content="")


def plan_continuation_turn(goal_text: str, messages: list[dict[str, Any]]) -> PlannedTurn:
    path = extract_path(goal_text)
    subgoals = subgoals_from_prompt(
        next(
            (
                str(m.get("content", ""))
                for m in reversed(messages)
                if m.get("role") == "user" and "Continuing toward goal" in str(m.get("content", ""))
            ),
            goal_text,
        )
    )
    if path:
        if file_written(messages, path):
            return PlannedTurn(content=synthesize_file_created(path, subgoals=subgoals))
        content = "probe" if "probe" in goal_text.lower() else "done"
        return plan_tool_write(path, content, call_id="call_goal_write")
    if is_multi_step_goal(goal_text):
        return PlannedTurn(content="Goal complete: multi-step task finished.")
    return PlannedTurn(content="Goal complete: standing objective finished.")


def planned_to_chat_result(planned: PlannedTurn) -> tuple[str, list[dict[str, Any]]]:
    return planned.content, planned.tool_calls
