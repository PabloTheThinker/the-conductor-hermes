"""MCP (Model Context Protocol) server — expose Conductor tools to AI models.

Claude Desktop, Codex, Cursor, Grok, and any MCP client can call The Conductor
as a tool server. Product line: enhances the host agent; does not replace it.

Entry points:
  conductor mcp
  python -m conductor.mcp
  the-conductor-mcp  (console script)

See docs/MCP.md.
"""

from __future__ import annotations

__all__ = ["build_mcp_catalog", "run_stdio", "tool_definitions"]


def build_mcp_catalog():
    from conductor.mcp.catalog import build_mcp_catalog as _build

    return _build()


def tool_definitions():
    from conductor.mcp.catalog import tool_definitions as _defs

    return _defs()


def run_stdio() -> int:
    from conductor.mcp.server import run_stdio as _run

    return _run()
