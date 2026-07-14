"""Research corpus tools — shared by native agent and Relay gateway registration."""

from __future__ import annotations

from typing import Any

from conductor.research.index import research_list, research_view

RESEARCH_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "research_list",
            "description": "List Conductor research specs (conductor, memory, governance, crucible, tracks, noesis, docs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pillar": {
                        "type": "string",
                        "description": "Optional pillar filter (e.g. conductor, memory)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_view",
            "description": "Read a research spec by repo-relative path (e.g. conductor/REMNANT_PROTOCOL.md).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repo-relative .md path"},
                },
                "required": ["path"],
            },
        },
    },
]


def research_list_tool(args: dict[str, Any]) -> str:
    pillar = args.get("pillar")
    p = str(pillar).strip() if pillar else None
    return research_list(p)


def research_view_tool(args: dict[str, Any]) -> str:
    path = str(args.get("path", "")).strip()
    if not path:
        return "Error: path required"
    return research_view(path)


RESEARCH_TOOL_REGISTRY: dict[str, Any] = {
    "research_list": research_list_tool,
    "research_view": research_view_tool,
}
