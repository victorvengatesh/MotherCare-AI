#!/usr/bin/env bash
# generate_certs.sh — Generate self-signed SSL certificates using Python

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/../backend/.venv/bin/python"

if [ -f "$PYTHON_BIN" ]; then
    "$PYTHON_BIN" "$SCRIPT_DIR/generate_certs.py"
else
    python3 "$SCRIPT_DIR/generate_certs.py" || python "$SCRIPT_DIR/generate_certs.py"
fi
