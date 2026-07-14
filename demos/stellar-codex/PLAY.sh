#!/usr/bin/env bash
# Launch Stellar Codex on port 8770
set -euo pipefail
cd "$(dirname "$0")"
# free port if something else holds it
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8770/tcp 2>/dev/null || true
fi
echo "Stellar Codex → http://127.0.0.1:8770/"
echo "Dir: $(pwd)"
exec python3 -m http.server 8770 --bind 127.0.0.1
