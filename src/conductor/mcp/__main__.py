"""python -m conductor.mcp  — start stdio MCP server."""

from __future__ import annotations


from conductor.mcp.server import run_stdio


def main() -> None:
    raise SystemExit(run_stdio())


if __name__ == "__main__":
    main()
