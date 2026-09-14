# Fleet inventory

Canonical list of every Cursor Skill in Brian Walsh's fleet. Two
sections: **Brian-owned** (the fleet budget in
[`ROADMAP.md`](./ROADMAP.md#fleet-budget-v01) applies here) and
**Curated / imported** (info only — external skills installed via
`.cursor/install-skills.sh`, not counted against the budget).

The `eod-drafter` reads this file at run time, counts active and
shipped-this-week rows in the Brian-owned table, and appends a fleet
line to the daily DM. On Fridays it also appends a weekly-review
addendum with minutes-saved-per-week rollups.

## Brian-owned skills — budget applies

| Skill | Source | Status | Shipped | Replaces | Est. min saved/week | Verdict |
|-------|--------|--------|---------|----------|---------------------|---------|
| eyes | brwalsh:bots/eyes | active | 2026-09-13 | — | 60 | kept |
| eod-drafter | brwalsh:bots/eod-drafter | active | 2026-09-13 | Manual daily EOD (~20-30 min/day) | 120 | kept |
| follow-up-radar | brwalsh:bots/follow-up-radar | active | 2026-09-13 | — | 30 | kept |

### Cap policy

- **Baseline:** 3 active Brian-owned skills (the current row count).
- **Rate:** at most +1 new Brian-owned skill per ISO week
  (Monday 00:00 America/Chicago → Sunday 23:59).
- **Constraint:** every net-new skill must move at least one existing
  Brian-owned row to `retired`. If the fleet is at cap and no
  retirement is queued, the new skill does not ship.
- **Enforcer:** `eod-drafter` reads this file every run. When
  `active > cap`, or `shipped_this_week > 1`, or `shipped_this_week >
  retired_this_week`, the daily DM includes a warning line and Brian
  decides whether to retire something. There is no automatic block —
  the point is visibility, not paternalism.
- **Cap changes:** raising or lowering the cap is a manual edit to
  this file, PR-reviewed like anything else.

### How to add a new skill

1. **Retire first.** Move a row from the active table down to
   [Retired](#retired), set `Status` to `retired`, fill in
   `Verdict` (`killed`, `merged into <skill>`, `superseded by
   <skill>`).
2. Add the new row with `Status: active` and today's date in the
   `Shipped` column.
3. Ship the code — SKILL.md, runbook, tests.
4. Delete the retired skill's code (or mark it archived under the
   folder's README) if the verdict is `killed`.

If you'd rather ship the new skill without retiring anything: don't.
That's the whole point of the cap. Change the cap in a separate PR
first, with a real reason.

## Curated / imported — info only, not counted

Sourced from [`BriWalsh/cursor-user-skills`](https://github.com/BriWalsh/cursor-user-skills)
(~35 skills). External or adapted; not counted against the fleet
budget. Move a row up to the Brian-owned table only if Brian
materially authored or maintains it.

<!-- Refresh candidate for v0.2: `bots/docs/refresh-fleet-inventory.sh` -->

`agent-browser` · `ask-matt` · `code-review` · `codebase-design` ·
`diagnosing-bugs` · `domain-modeling` · `find-skills` ·
`frontend-design` · `grill-me` · `grill-with-docs` · `grilling` ·
`handoff` · `herdr` · `implement` ·
`improve-codebase-architecture` · `lavish` · `merge-pr` ·
`multi-model-review` · `prototype` · `refining-ideas` · `research` ·
`resolving-merge-conflicts` · `review-triage` · `sdd` ·
`setup-matt-pocock-skills` · `tdd` · `teach` · `to-spec` ·
`to-tickets` · `tracking` · `triage` · `unslop` · `wayfinder` ·
`web-design-guidelines` · `writing-great-skills`

## Retired

_(none yet — cap in effect from 2026-09-14)_

| Skill | Retired | Verdict | Replaced by | Notes |
|-------|---------|---------|-------------|-------|
| — | — | — | — | — |

## How the drafter parses this file

- Read the file, find the H2 heading `## Brian-owned skills — budget
  applies`, take the first Markdown table under it.
- A row counts as **active** if column 3 is exactly `active`.
- A row counts as **shipped this week** if column 4 parses as a date
  and falls within the current ISO week in `America/Chicago`.
- A row counts as **retired this week** if it appears in the
  [Retired](#retired) table with a `Retired` date in the current
  ISO week.
- Minutes-saved rollup on Fridays: sum of column 6 across all
  `active` rows.

If the parser can't find the table (file missing, heading renamed,
schema drift), it does **not** fail the run — it logs a warning and
omits the fleet line. The EOD still ships. Non-fatal by design.

## Why this exists

"No new bots" is a rule with no enforcer. On 2026-09-13 the fleet went
from zero to three in a weekend; the anti-rule failed within hours.
A visible count with a documented cap turns the discipline into
something reviewable — every run, in Brian's DM, in front of him.
