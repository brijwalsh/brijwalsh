#!/usr/bin/env python3
"""Redaction tests for eod-drafter. Stdlib only.

Runs quarantine_lib.redact_for_gateway() against every quarantined
meeting in fixtures/granola_meetings.json and checks the result against
fixtures/expected_redaction.json. Non-quarantined meetings are checked
to pass through completely unmodified (no redaction applied).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from quarantine_lib import quarantine_verdict, redact_for_gateway  # noqa: E402

FIXTURES = ROOT / "fixtures"


def load(name: str):
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    meetings = load("granola_meetings.json")["meetings"]
    expected_doc = load("expected_redaction.json")
    expected_by_id = {row["meeting_id"]: row["redacted"] for row in expected_doc["meetings"]}
    expected_quarantine = {
        row["meeting_id"]: row["quarantined"]
        for row in load("expected_quarantine.json")["meetings"]
    }

    failures = []
    passed = 0
    checked = 0

    for meeting in meetings:
        mid = meeting["meeting_id"]
        verdict = quarantine_verdict(meeting)
        want_quarantined = expected_quarantine.get(mid, verdict["quarantined"])

        if verdict["quarantined"] != want_quarantined:
            failures.append(
                f"{mid}: quarantine verdict drifted from expected_quarantine.json "
                f"(got {verdict['quarantined']}, want {want_quarantined}) -- "
                "run test_quarantine.sh first, it owns that contract"
            )
            continue

        redacted = redact_for_gateway(meeting)
        checked += 1

        if mid in expected_by_id:
            want = expected_by_id[mid]
            if redacted != want:
                failures.append(f"{mid}: redacted mismatch\n    got={redacted}\n    want={want}")
                continue
            passed += 1
        else:
            # Not quarantined -> must pass through unmodified.
            if verdict["quarantined"]:
                failures.append(
                    f"{mid}: quarantined but has no row in expected_redaction.json"
                )
                continue
            if redacted != meeting:
                failures.append(
                    f"{mid}: non-quarantined meeting was modified by redact_for_gateway "
                    f"(should pass through unchanged)"
                )
                continue
            passed += 1

    print(f"{passed} passed / {len(failures)} failed ({checked} meetings checked)")
    if failures:
        print("failed fixtures:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    quarantined_ids = [m["meeting_id"] for m in meetings if quarantine_verdict(m)["quarantined"]]
    print(f"  quarantined + redacted: {quarantined_ids}")
    print(
        "  pass-through (not quarantined): "
        f"{[m['meeting_id'] for m in meetings if m['meeting_id'] not in quarantined_ids]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
