"""Fleet parser smoke test.

Proves `bots/FLEET.md` matches the schema `eod-drafter/SKILL.md` §5b
promises to parse (table headers, active-row count, shipped-this-week
detection, minutes-saved rollup). If the FLEET.md schema drifts, this
test fails before the eod-drafter starts silently omitting the fleet
line in production.

Runs in stdlib Python 3. No pytest, no fixtures — the FLEET.md file is
the fixture.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date
from typing import Any


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FLEET_PATH = os.path.join(REPO_ROOT, "bots", "FLEET.md")

EXPECTED_HEADER = [
    "Skill",
    "Source",
    "Status",
    "Shipped",
    "Replaces",
    "Est. min saved/week",
    "Verdict",
]

RETIRED_HEADER = ["Skill", "Retired", "Verdict", "Replaced by", "Notes"]


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


def _section(text: str, heading: str) -> str | None:
    rx = re.compile(rf"## {re.escape(heading)}\n(.*?)(?=\n##\s|\Z)", re.S)
    m = rx.search(text)
    return m.group(1) if m else None


def _parse_min(s: str) -> int:
    m = re.match(r"^\s*(\d+)", s)
    return int(m.group(1)) if m else 0


def _row_to_dict(header: list[str], row: list[str]) -> dict[str, str]:
    return dict(zip(header, row))


def _in_iso_week(d_str: str, iso_yw: tuple[int, int]) -> bool:
    try:
        d = date.fromisoformat(d_str)
    except ValueError:
        return False
    return d.isocalendar()[:2] == iso_yw


def main() -> int:
    assert os.path.isfile(FLEET_PATH), f"FLEET.md not found at {FLEET_PATH}"
    text = open(FLEET_PATH).read()

    owned_section = _section(text, "Brian-owned skills — budget applies")
    assert owned_section, "missing '## Brian-owned skills — budget applies' section"

    owned = _first_table(owned_section)
    assert owned, "no markdown table under Brian-owned section"
    header, rows = owned
    assert header == EXPECTED_HEADER, (
        f"Brian-owned table header drifted.\n"
        f"  expected: {EXPECTED_HEADER}\n"
        f"  got:      {header}"
    )
    assert rows, "Brian-owned table has no rows"

    parsed = [_row_to_dict(header, r) for r in rows]
    active = [r for r in parsed if r["Status"].lower() == "active"]
    assert active, "no active rows — cap policy assumes >= 1"

    baseline_cap = 3
    assert len(active) <= baseline_cap, (
        f"{len(active)} active rows but cap in FLEET.md is {baseline_cap} — "
        "raise the cap in a PR before shipping more skills"
    )

    for r in active:
        assert r["Shipped"] not in ("", "—"), f"active row missing Shipped date: {r}"
        try:
            date.fromisoformat(r["Shipped"])
        except ValueError:
            raise AssertionError(f"non-ISO Shipped date: {r['Shipped']!r} in row {r}")

    total = sum(_parse_min(r["Est. min saved/week"]) for r in active)
    assert total > 0, "minutes-saved rollup is 0 — misparse or nothing shipped"

    retired_section = _section(text, "Retired")
    assert retired_section, "missing '## Retired' section"
    retired = _first_table(retired_section)
    if retired:
        rheader, rrows = retired
        assert rheader == RETIRED_HEADER, (
            f"Retired table header drifted.\n"
            f"  expected: {RETIRED_HEADER}\n"
            f"  got:      {rheader}"
        )
        for row in rrows:
            r = _row_to_dict(rheader, row)
            if r["Skill"] and r["Skill"] != "—":
                try:
                    date.fromisoformat(r["Retired"])
                except ValueError:
                    raise AssertionError(
                        f"non-ISO Retired date: {r['Retired']!r} in row {r}"
                    )

    active_names = {r["Skill"] for r in active}
    expected_v01 = {"eyes", "eod-drafter", "follow-up-radar"}
    missing = expected_v01 - active_names
    assert not missing, (
        f"active fleet missing v0.1 skills {missing}; "
        f"expected all three v0.1 skills to be tracked here"
    )

    today = date.today()
    iso_yw = today.isocalendar()[:2]
    shipped_this_week = [r for r in active if _in_iso_week(r["Shipped"], iso_yw)]

    print(f"FLEET.md OK — {len(active)} active, cap {baseline_cap}, "
          f"total ~{total} min/week saved, shipped this week: "
          f"{len(shipped_this_week)}, retired rows: "
          f"{sum(1 for row in (retired[1] if retired else []) if row and row[0] not in ('', '—'))}")

    if len(shipped_this_week) > 1:
        print(
            f"::warning:: {len(shipped_this_week)} skills shipped this ISO "
            f"week (cap is +1/week). eod-drafter will surface this in the DM."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
