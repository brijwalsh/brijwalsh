#!/usr/bin/env python3
"""Meeting -> client mapping tests for eod-drafter. Stdlib only.

Runs quarantine_lib.map_client() against fixtures/granola_meetings.json
under CLIENT_DOMAINS=natera.com,goengen.com (fixtures/client_domains.env)
and checks each meeting's mapped client key against
fixtures/expected_client_mapping.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from quarantine_lib import map_client  # noqa: E402

FIXTURES = ROOT / "fixtures"


def load(name: str):
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def load_client_domains() -> list[str]:
    # Prefer an already-exported CLIENT_DOMAINS (e.g. the bash wrapper
    # sourcing fixtures/client_domains.env); fall back to parsing the
    # fixture file directly so `python3 test_client_mapping.py` alone
    # still exercises the pinned value, not the shell's ambient env.
    env_value = os.environ.get("CLIENT_DOMAINS")
    if env_value:
        return [d.strip() for d in env_value.split(",") if d.strip()]

    env_path = FIXTURES / "client_domains.env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key.strip() == "CLIENT_DOMAINS":
            return [d.strip() for d in value.split(",") if d.strip()]
    raise RuntimeError("CLIENT_DOMAINS not found in fixtures/client_domains.env")


def main() -> int:
    client_domains = load_client_domains()
    meetings = {m["meeting_id"]: m for m in load("granola_meetings.json")["meetings"]}
    expected_doc = load("expected_client_mapping.json")
    expected = expected_doc["meetings"]

    failures = []
    passed = 0

    for row in expected:
        mid = row["meeting_id"]
        meeting = meetings.get(mid)
        if meeting is None:
            failures.append(f"{mid}: not found in granola_meetings.json")
            continue

        got = map_client(meeting, client_domains)
        if got != row["client"]:
            failures.append(
                f"{mid}: client={got!r} want={row['client']!r} "
                f"({row['justification']})"
            )
            continue
        passed += 1

    print(f"{passed} passed / {len(failures)} failed ({len(expected)} fixtures)")
    print(f"CLIENT_DOMAINS={','.join(client_domains)}")
    print(f"tie_break_rule: {expected_doc['tie_break_rule']}")
    if failures:
        print("failed fixtures:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    for row in expected:
        print(f"  {row['meeting_id']}: {row['client']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
