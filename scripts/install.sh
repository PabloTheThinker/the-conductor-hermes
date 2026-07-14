#!/usr/bin/env bash
# Install The Conductor for a normal operator machine.
# Daily driver remains stock `hermes`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Prefer Hermes-native home for third parties; allow override
if [[ -n "${CONDUCTOR_HOME:-}" ]]; then
  HOME_DIR="$CONDUCTOR_HOME"
elif [[ -n "${HERMES_HOME:-}" ]]; then
  HOME_DIR="$HERMES_HOME"
elif [[ -d "$HOME/.hermes" ]]; then
  HOME_DIR="$HOME/.hermes"
elif [[ -d "$HOME/.ilo" ]]; then
  HOME_DIR="$HOME/.ilo"
else
  HOME_DIR="$HOME/.hermes"
fi
VENV="${CONDUCTOR_VENV:-$HOME_DIR/venvs/conductor}"
LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"

echo "==> The Conductor install (third-party ready)"
echo "    repo:  $ROOT"
echo "    home:  $HOME_DIR   (HERMES_HOME = CONDUCTOR_HOME)"
echo "    daily: hermes"

mkdir -p "$HOME_DIR" "$LOCAL_BIN" "$(dirname "$VENV")"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip wheel -q
"$VENV/bin/pip" install -e "$ROOT[dev]" -q

cat > "$LOCAL_BIN/conductor" <<EOW
#!/usr/bin/env bash
set -euo pipefail
export CONDUCTOR_HOME="\${CONDUCTOR_HOME:-$HOME_DIR}"
export HERMES_HOME="\${HERMES_HOME:-\$CONDUCTOR_HOME}"
exec "$VENV/bin/conductor" "\$@"
EOW
chmod +x "$LOCAL_BIN/conductor"
rm -f "$LOCAL_BIN/ilo" 2>/dev/null || true

export CONDUCTOR_HOME="$HOME_DIR" HERMES_HOME="$HOME_DIR"
"$VENV/bin/conductor" setup

echo ""
echo "Done."
echo ""
echo "  Next for a full daily path:"
echo "    1) Install stock Hermes; put \`hermes\` on PATH"
echo "    2) Install this package into the Hermes venv too:"
echo "         /path/to/hermes/venv/bin/pip install -e $ROOT"
echo "       OR always launch with:  conductor hermes"
echo "    3) hermes model"
echo "    4) hermes"
echo ""
echo "  Offline smoke:"
echo "    CONDUCTOR_PROVIDER=test conductor chat -q 'Reply with exactly: CONDUCTOR_OK'"
echo ""
echo "  Guide: docs/OPERATORS.md"
if ! command -v hermes >/dev/null 2>&1 && [[ -z "${HERMES_BIN:-}" ]]; then
  echo "  Note: hermes not detected on PATH yet — brain CLI still works offline."
fi
