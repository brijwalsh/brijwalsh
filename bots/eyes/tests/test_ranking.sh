#!/usr/bin/env bash
# Thin wrapper so the harness path in bots/tests/README.md stays a .sh.
set -euo pipefail
exec python3 "$(cd "$(dirname "$0")" && pwd)/test_ranking.py" "$@"
