"""PDP evidence-targets parser smoke test.

Proves `bots/docs/pdp-evidence-targets.md` matches the schema
`eod-drafter/SKILL.md` §5c promises to parse. If a column is renamed
or the Active table is dropped, the drafter would silently omit PDP
targets from the daily DM — this test fails loudly instead.

Stdlib Python 3 only.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, timedelta


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PDP_PATH = os.path.join(REPO_ROOT, "bots", "docs", "pdp-evidence-targets.md")

EXPECTED_HEADER = [
    "ID",
    "Target",
    "Category",
    "Due",
    "Status",
    "Evidence source",
    "Notes",
]

COMPLETED_HEADER = ["ID", "Target", "Completed", "Evidence"]

ALLOWED_STATUS = {"pending", "in-progress", "blocked", "complete"}
ALLOWED_CATEGORY = {
    "Directive voice",
    "Client discovery",
    "Technical depth",
    "Peer feedback",
    "Written artifact",
    "Operating rhythm",
}


def _section(text: str, heading: str) -> str | None:
    rx = re.compile(rf"## {re.escape(heading)}\n(.*?)(?=\n##\s|\Z)", re.S)
    m = rx.search(text)
    return m.group(1) if m else None


def _first_table(section: str) -> tuple[list[str], list[list[str]]] | None:
    lines = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        return None
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    rows: list[list[str]] = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(cells)
    return header, rows


def _row(header: list[str], row: list[str]) -> dict[str, str]:
    return dict(zip(header, row))


def main() -> int:
    assert os.path.isfile(PDP_PATH), f"pdp file not found at {PDP_PATH}"
    text = open(PDP_PATH).read()

    active_section = _section(text, "Active targets")
    assert active_section, "missing '## Active targets' section"
    active = _first_table(active_section)
    assert active, "no markdown table under Active targets"
    header, rows = active
    assert header == EXPECTED_HEADER, (
        f"Active targets header drifted.\n"
        f"  expected: {EXPECTED_HEADER}\n"
        f"  got:      {header}"
    )
    assert rows, "Active targets table has no rows"

    ids_seen: set[str] = set()
    for row in rows:
        r = _row(header, row)
        assert r["ID"], f"row missing ID: {r}"
        assert re.match(r"^pdp-\d{4}-w\d{1,2}-\d{2}$", r["ID"]), (
            f"ID {r['ID']!r} doesn't match pdp-YYYY-w<isoweek>-NN"
        )
        assert r["ID"] not in ids_seen, f"duplicate ID: {r['ID']}"
        ids_seen.add(r["ID"])

        assert r["Category"] in ALLOWED_CATEGORY, (
            f"unknown Category {r['Category']!r} in {r['ID']}. "
            f"Extend ALLOWED_CATEGORY in this test AND the vocabulary "
            f"list in bots/docs/pdp-evidence-targets.md."
        )
        assert r["Status"].lower() in ALLOWED_STATUS, (
            f"unknown Status {r['Status']!r} in {r['ID']}"
        )
        try:
            date.fromisoformat(r["Due"])
        except ValueError:
            raise AssertionError(f"non-ISO Due date in {r['ID']}: {r['Due']!r}")
        assert r["Target"], f"empty Target in {r['ID']}"
        assert r["Evidence source"], f"empty Evidence source in {r['ID']}"

    completed_section = _section(text, "Completed targets")
    assert completed_section, "missing '## Completed targets' section"
    completed = _first_table(completed_section)
    if completed:
        cheader, crows = completed
        assert cheader == COMPLETED_HEADER, (
            f"Completed header drifted.\n"
            f"  expected: {COMPLETED_HEADER}\n"
            f"  got:      {cheader}"
        )
        for row in crows:
            r = _row(cheader, row)
            if r["ID"] and r["ID"] != "—":
                try:
                    date.fromisoformat(r["Completed"])
                except ValueError:
                    raise AssertionError(
                        f"non-ISO Completed date: {r['Completed']!r} in {r['ID']}"
                    )
                assert r["ID"] not in ids_seen, (
                    f"ID {r['ID']} appears in both Active and Completed tables"
                )

    today = date.today()
    horizon = today + timedelta(days=7)
    surfaceable = [
        _row(header, row) for row in rows
        if _row(header, row)["Status"].lower() != "complete"
    ]
    within = [
        r for r in surfaceable
        if date.fromisoformat(r["Due"]) <= horizon
    ]
    overdue = [r for r in within if date.fromisoformat(r["Due"]) < today]

    print(
        f"pdp-evidence-targets.md OK — "
        f"{len(rows)} active row(s), "
        f"{len(surfaceable)} unmet, "
        f"{len(within)} surfaceable (due within 7d of {today}), "
        f"{len(overdue)} overdue"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
