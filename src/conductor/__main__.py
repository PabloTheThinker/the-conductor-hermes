"""python -m conductor — CLI entry (same as ``conductor`` console script)."""

from __future__ import annotations

from conductor.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
