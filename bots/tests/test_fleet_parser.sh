#!/usr/bin/env bash
# Smoke test for FLEET.md schema. Wraps test_fleet_parser.py so the
# runner is uniform with the rest of the harness.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/test_fleet_parser.py"
