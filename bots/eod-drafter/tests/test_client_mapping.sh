#!/usr/bin/env bash
# Sources the pinned CLIENT_DOMAINS fixture, then runs the mapping test.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v jq >/dev/null 2>&1; then
  jq empty "$ROOT/fixtures/granola_meetings.json" "$ROOT/fixtures/expected_client_mapping.json"
fi
set -a
# shellcheck disable=SC1091
source "$ROOT/fixtures/client_domains.env"
set +a
exec python3 "$ROOT/test_client_mapping.py" "$@"
