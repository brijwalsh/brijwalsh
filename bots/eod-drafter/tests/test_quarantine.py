#!/usr/bin/env python3
"""Multi-signal quarantine tests for eod-drafter. Stdlib only.

Runs quarantine_lib.quarantine_verdict() (a transcription of SKILL.md
\u00a73d) against fixtures/granola_meetings.json and checks each meeting's
quarantined/dominant verdict against fixtures/expected_quarantine.json.

Post-PR #10 (#eod-quarantine-gaps-0428): all eight fixtures now assert
current SKILL.md behavior directly. The alias_hit signal added in PR
#10 promoted gr-1003 (summary mentions contact@natera.com) and gr-1004
(title "enGen QBR") from clear to quarantined; both fixture rows now
carry an "alias_hit" signal string.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from quarantine_lib import quarantine_verdict  # noqa: E402

FIXTURES = ROOT / "fixtures"


def load(name: str):
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    meetings = {m["meeting_id"]: m for m in load("granola_meetings.json")["meetings"]}
    expected = load("expected_quarantine.json")["meetings"]

    failures = []
    passed = 0

    for row in expected:
        mid = row["meeting_id"]
        meeting = meetings.get(mid)
        if meeting is None:
            failures.append(f"{mid}: not found in granola_meetings.json")
            continue

        verdict = quarantine_verdict(meeting)

        if verdict["quarantined"] != row["quarantined"]:
            failures.append(
                f"{mid}: quarantined={verdict['quarantined']} "
                f"want={row['quarantined']} ({row['justification']})"
            )
            continue

        if row["quarantined"] and verdict["dominant"] != row["dominant"]:
            failures.append(
                f"{mid}: dominant={verdict['dominant']!r} "
                f"want={row['dominant']!r}"
            )
            continue

        passed += 1

    print(f"{passed} passed / {len(failures)} failed ({len(expected)} fixtures)")
    if failures:
        print("failed fixtures:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    for row in expected:
        marker = "quarantined" if row["quarantined"] else "clear"
        print(f"  {row['meeting_id']}: {marker} ({row['signal']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
