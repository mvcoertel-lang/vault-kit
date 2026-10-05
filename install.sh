#!/usr/bin/env bash
# vault-kit für macOS und Linux: sucht Python 3 und startet install.py (die eigentliche Logik,
# dieselbe wie unter Windows).
#
#   ./install.sh                         # Vault: ~/Claude
#   ./install.sh ~/MeinVault --live      # eigener Ort, laufende Sitzungen im Graphen
#   ./install.sh --no-graphify           # ohne Graphify und markitdown
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "Python 3 fehlt. macOS: xcode-select --install  |  Linux: über den Paketmanager installieren" >&2
  exit 1
fi
exec "$PY" "$KIT/install.py" "$@"
