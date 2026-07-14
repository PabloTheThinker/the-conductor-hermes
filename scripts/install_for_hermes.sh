#!/usr/bin/env bash
# Install The Conductor for any stock Hermes agent (no fork).
# Usage:
#   ./scripts/install_for_hermes.sh
#   HERMES_HOME=~/.hermes ./scripts/install_for_hermes.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
export CONDUCTOR_HOME="${CONDUCTOR_HOME:-$HERMES_HOME}"

echo "◆ The Conductor → Hermes install"
echo "  repo:         $ROOT"
echo "  HERMES_HOME:  $HERMES_HOME"

# Prefer active venv, else create local .venv for conductor CLI
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ ! -d "$ROOT/.venv" ]]; then
    python3 -m venv "$ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

python -m pip install -U pip -q
python -m pip install -e "$ROOT" -q

# Prefer console script; fall back to module entry (same CLI).
run_conductor() {
  if command -v conductor >/dev/null 2>&1; then
    conductor "$@"
  else
    python -m conductor "$@"
  fi
}

run_conductor setup --harness hermes --home "$HERMES_HOME" --install-pip || \
  run_conductor setup --harness hermes --home "$HERMES_HOME" --no-pip

run_conductor hermes-ready || true

echo
echo "  Next:"
echo "    source \"$HERMES_HOME/conductor.env\""
echo "    hermes plugins list    # should list conductor"
echo "    hermes model"
echo "    hermes"
echo "  CLI: conductor …  or  python -m conductor …"
echo "  In session: /pillars status · /combo recommend … · /conductor-status"
echo
