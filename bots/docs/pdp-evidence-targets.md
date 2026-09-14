# PDP evidence targets

Named, dated evidence targets for Brian's Personal Development Plan.
The `eod-drafter` reads this file at run time (`SKILL.md` §5c) and
promotes unmet targets to the top of the daily DM's "Your 3 for
tomorrow" list until they hit `complete`.

Fable 5.1's directive: "Move enGen staffing into the scoring loop.
The Paul conversation with Ron and Chelsea is the highest-value
directive-voice rep you have this month, and no bot is tracking it.
Add it as a named PDP evidence target with a date (this week) so
Coach scores it like a meeting."

There's no separate `Coach` bot in v0.1 — the "scoring loop" here is
simply `eod-drafter` reading this file every day and reminding Brian.
If a bigger scoring engine gets built later, it consumes the same
table.

## Active targets

| ID | Target | Category | Due | Status | Evidence source | Notes |
|----|--------|----------|-----|--------|-----------------|-------|
| pdp-2026-w38-01 | Deliver directive-voice decision on Paul + Ron + Chelsea enGen staffing (thumb-up/thumb-down + role) | Directive voice | 2026-09-19 | in-progress | Slack `#the-staffing-conversation` (`C05GV2F8AJ0`) and Group DM `C0BV2NEV7U0` | Ron's Sep 1 interview notes + Chelsea's Sep 1 note that Kevin locks in on Cursor partnership if Natera MOVE progresses. |
| pdp-2026-w38-02 | Schedule Kevin ↔ Chelsea sync as prerequisite for the enGen onsite (kickoff / VSM / chartering) | Directive voice | 2026-09-17 | pending | Slack DM to Chelsea (drafted in `bots/docs/chelsea-monday-logistics-dm.md`) | Depends on Chelsea's calendar. Sync must land before the onsite date is locked. |

## Completed targets

_(none yet — table exists so the parser has a target to find)_

| ID | Target | Completed | Evidence |
|----|--------|-----------|----------|
| — | — | — | — |

## Schema

Each active target has:

- **ID** — stable, `pdp-YYYY-w<isoweek>-NN`. Never reused after a
  target moves to `Completed`.
- **Target** — one sentence, action-first, unambiguous.
- **Category** — one of: `Directive voice`, `Client discovery`,
  `Technical depth`, `Peer feedback`, `Written artifact`,
  `Operating rhythm`. Extend the vocabulary in a PR that also
  updates the `eod-drafter` prompt so the model knows how to phrase
  each type.
- **Due** — ISO date, `America/Chicago`. Overdue targets get a
  `:warning:` prefix in the DM.
- **Status** — one of: `pending`, `in-progress`, `blocked`,
  `complete`. `complete` moves the row to the Completed table.
- **Evidence source** — the Slack channel, Granola meeting, doc, or
  PR that will hold the artifact proving the target was met. This
  is what a coach or manager would ask to see.
- **Notes** — free-form context. Optional.

## How the drafter parses this file

- Read the file, find the H2 heading `## Active targets`, take the
  first Markdown table under it.
- A row is **surfaced to Brian** when `Status ∈ {pending,
  in-progress, blocked}` and `Due <= today + 7 days` (or is
  overdue). Row rank: overdue first, then `Due` ascending, then ID
  ascending.
- Cap at 5 surfaced rows to keep the LLM input small; the top 3
  land in the parent DM's "Your 3 for tomorrow" list.
- If the parser can't find the table (file missing, heading
  renamed), the drafter logs a warning and skips PDP surfacing.
  Non-fatal.

## Editing this file

Add a new row when a target is agreed with a mentor / manager /
peer. Move rows to `Completed` promptly — the point is a shrinking
active list, not a growing one. Delete a target only if it was
mis-stated; otherwise complete it and keep the audit trail.

## v0.2 candidates

- Auto-generate the `pdp-YYYY-w<isoweek>-NN` ID.
- A weekly Friday recap of moved-to-complete targets, sourced from
  git diff on this file.
- Coach as a real skill: read this file, correlate with Granola
  meeting outcomes, propose new evidence targets in a draft DM.
  Gated on durable state — see `ROADMAP.md` v0.2 §1.
