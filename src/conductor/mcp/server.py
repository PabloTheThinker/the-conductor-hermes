"""MCP stdio server — tools, resources, and prompts for AI models.

Transport: stdio (Claude Desktop, Codex, Cursor, Grok MCP clients).
Logs always go to stderr (stdout is the MCP wire).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("conductor.mcp")


def _ensure_home() -> None:
    home = (
        os.environ.get("CONDUCTOR_HOME", "").strip()
        or os.environ.get("HERMES_HOME", "").strip()
    )
    if home:
        os.environ.setdefault("CONDUCTOR_HOME", home)
        os.environ.setdefault("HERMES_HOME", home)
    # MCP clients are host agents — shadow clones default to host subagent contract
    os.environ.setdefault("CONDUCTOR_MCP", "1")
    os.environ.setdefault("CONDUCTOR_HOST", os.environ.get("CONDUCTOR_HOST", "grok"))


def build_server() -> Any:
    """Create a low-level MCP Server with Conductor tools + resources + prompts."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import (
            GetPromptResult,
            Prompt,
            PromptArgument,
            PromptMessage,
            Resource,
            TextContent,
            Tool,
        )
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Conductor MCP server requires the 'mcp' package. "
            "Install with: pip install 'the-conductor[mcp]'   or   pip install mcp"
        ) from exc

    from conductor import __version__
    from conductor.mcp.catalog import dispatch_tool, is_tool_error_payload, tool_definitions

    _ensure_home()
    defs = tool_definitions()
    server = Server("the-conductor")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=d.name,
                description=d.description,
                inputSchema=d.input_schema,
            )
            for d in defs
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> Any:
        """Dispatch Conductor tools; mark soft failures with isError for MCP clients."""
        from mcp.types import CallToolResult

        args = dict(arguments or {})
        session_id = str(args.get("session_id") or os.environ.get("CONDUCTOR_MCP_SESSION") or "")
        is_error = False
        try:
            text = dispatch_tool(name, args, session_id=session_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool %s failed", name)
            text = json.dumps({"error": str(exc), "tool": name})
            is_error = True
        if not isinstance(text, str):
            text = json.dumps(text, default=str)
        if not is_error and is_tool_error_payload(text):
            is_error = True
            logger.info("tool %s soft-error isError=true: %s", name, text[:200])
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            isError=is_error,
        )

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="conductor://module",  # type: ignore[arg-type]
                name="Module info",
                description="Conductor version, skills, foundation status",
                mimeType="application/json",
            ),
            Resource(
                uri="conductor://pillars",  # type: ignore[arg-type]
                name="Pillars",
                description="P0–P8 foundation catalog + live probes",
                mimeType="application/json",
            ),
            Resource(
                uri="conductor://soul",  # type: ignore[arg-type]
                name="Conductor partner SOUL",
                description="Partner wavelength SOUL.md (enhances host; does not replace)",
                mimeType="text/markdown",
            ),
            Resource(
                uri="conductor://skills",  # type: ignore[arg-type]
                name="Skills index",
                description="plan, review, remnant-guide, combo, pillars",
                mimeType="application/json",
            ),
            Resource(
                uri="conductor://combos",  # type: ignore[arg-type]
                name="Combos A–H",
                description="Named pillar stacks and workflows",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: Any) -> str:
        u = str(uri)
        if u.endswith("module") or u == "conductor://module":
            from conductor.harness import module_info

            return json.dumps(module_info(), indent=2, default=str)
        if "pillars" in u:
            from conductor.pillars import foundation_report, pillars_as_dicts

            return json.dumps(
                {"catalog": pillars_as_dicts(), "foundation": foundation_report()},
                indent=2,
                default=str,
            )
        if "soul" in u:
            from conductor.soul.resonance import load_conductor_soul

            text, path = load_conductor_soul()
            return text or f"(SOUL empty; path={path})"
        if "skills" in u:
            from conductor.harness import list_skills

            rows = [{"name": s.name, "description": s.description, "path": s.path} for s in list_skills()]
            return json.dumps(rows, indent=2)
        if "combos" in u:
            from conductor.combos import COMBOS, workflow_steps

            rows = []
            for cid, c in sorted(COMBOS.items()):
                rows.append(
                    {
                        "id": c.id,
                        "slug": c.slug,
                        "name": c.name,
                        "summary": c.summary,
                        "when": c.when,
                        "workflow": workflow_steps(c.id),
                    }
                )
            return json.dumps(rows, indent=2)
        return json.dumps({"error": f"unknown resource {u}"})

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="system",
                description="Soul Resonance system prompt for the host agent",
                arguments=[
                    PromptArgument(
                        name="host_soul",
                        description="Optional path or text of host meister SOUL",
                        required=False,
                    ),
                    PromptArgument(
                        name="mode",
                        description="resonate | solo | host_only",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="resonate",
                description="Diagnostics + rules for Soul Resonance with a host agent",
                arguments=[
                    PromptArgument(
                        name="host_soul",
                        description="Path or text of host SOUL",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="plan",
                description="Invoke Conductor plan skill framing for a goal",
                arguments=[
                    PromptArgument(name="goal", description="What to plan", required=True),
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
        args = dict(arguments or {})
        if name == "system":
            from conductor.harness import get_system_prompt

            text = get_system_prompt(
                host_soul=args.get("host_soul") or None,
                mode=args.get("mode") or None,
                search_host=not bool(args.get("host_soul")),
            )
            return GetPromptResult(
                description="Conductor Soul Resonance system prompt",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=text),
                    )
                ],
            )
        if name == "resonate":
            from conductor.harness import resonate_souls

            data = resonate_souls(
                host_soul=args.get("host_soul") or None,
                search_host=not bool(args.get("host_soul")),
            )
            body = (
                f"Resonant: {data.get('resonant')}\n"
                f"Mode: {data.get('mode')}\n"
                f"Notes: {data.get('notes')}\n\n"
                f"{data.get('prompt', '')}"
            )
            return GetPromptResult(
                description="Soul Resonance diagnostics",
                messages=[
                    PromptMessage(role="user", content=TextContent(type="text", text=body))
                ],
            )
        if name == "plan":
            from conductor.skills.responder import build_grounded_skill_response

            goal = args.get("goal") or "conductor rollout"
            text = build_grounded_skill_response("plan", goal)
            return GetPromptResult(
                description=f"Plan for: {goal[:80]}",
                messages=[
                    PromptMessage(role="user", content=TextContent(type="text", text=text))
                ],
            )
        return GetPromptResult(
            description="unknown",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=f"Unknown prompt: {name}"),
                )
            ],
        )

    # attach version for logging
    server._conductor_version = __version__  # type: ignore[attr-defined]
    server._stdio_server = stdio_server  # type: ignore[attr-defined]
    return server


def run_stdio() -> int:
    """Run MCP server on stdin/stdout (logs on stderr)."""
    import anyio

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] conductor.mcp: %(message)s",
    )
    try:
        server = build_server()
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    from mcp.server.stdio import stdio_server
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions

    async def _main() -> None:
        version = getattr(server, "_conductor_version", "unknown")
        logger.info("starting the-conductor MCP server v%s (stdio)", version)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="the-conductor",
                    server_version=str(version),
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    anyio.run(_main)
    return 0
