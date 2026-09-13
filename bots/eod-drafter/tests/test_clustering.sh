#!/usr/bin/env bash
# Thin wrapper so the harness path in bots/tests/README.md stays a .sh.
# jq sanity-checks the fixtures parse as JSON before Python does the real
# clustering logic -- cheap, fast fail if a fixture gets hand-edited badly.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v jq >/dev/null 2>&1; then
  jq empty "$ROOT/fixtures/gh_activity.json" "$ROOT/fixtures/slack_activity.json" \
    "$ROOT/fixtures/expected_clusters.json"
fi
exec python3 "$ROOT/test_clustering.py" "$@"
