# Brian's canonical EOD template

Extracted from real EOD posts across `#liatrio-forge`, `#project-marketing-dashboard`,
and `#project-ai-gateway`. The drafter must produce output that looks like it
was written by Brian, not by an LLM defaulting to bland structure.

## How the DM is shaped (v0.1 human-actions-first)

The daily DM is **two messages**, sent to `U0A0T8FV12B` in this order
(see `SKILL.md` §7e + §8):

1. **Parent** — "Your 3 for tomorrow." Signal-only, no shipping log.
   This is what Brian sees first when the DM lights up his phone. If
   his manager Ryan would care, it's up here.
2. **Thread reply** — the full Today / Tomorrow / fleet / (Friday
   review) block, in a code fence, ready to copy into whatever
   channel it belongs in.

```
:bullseye: *Your 3 for tomorrow — 2026-09-15*

1. Deliver directive-voice decision on Paul + Ron + Chelsea enGen staffing (due 2026-09-19, evidence: #the-staffing-conversation)
2. Finish review and land Anmol's CI quality-gate <https://…|#53>
3. Push the infra <https://…|#1> multi-model review findings to resolution with Anmol

_Full EOD draft in thread — copy from there to repost._
```

The thread reply contains everything below.

## Structure

```
Today
• <outcome 1, tied to a workstream>
• <outcome 2, PR/issue numbers linked>
• ...
Non-Forge   (optional, only if Forge + another cluster both have signals)
• <outcome>

Tomorrow
• <planned item, ideally tied to an open PR / meeting Next Step>
• ...
Non-Forge   (optional, same rule)
• <planned item>

:file_cabinet: Fleet: <N>/<CAP> active, <shipped_this_week> shipped this week, <retired_this_week> retired.

*Sent using* <@U093DJ468EN|Cursor>
```

The fleet line is inserted **mechanically** by `eod-drafter/SKILL.md`
§7b from [`../FLEET.md`](../FLEET.md); the LLM does not generate it.
If it's ever off, fix `FLEET.md`, not the model prompt.

### Friday variant

On Fridays only, `eod-drafter/SKILL.md` §7c appends a weekly review
after the sign-off. Same code-block, so Brian can copy the entire
thing into a channel:

```
Today
• ...
Tomorrow
• ...

:file_cabinet: Fleet: 3/3 active, 0 shipped this week, 0 retired.

*Sent using* <@U093DJ468EN|Cursor>

:calendar: Weekly review — fleet minutes saved

| Skill | Verdict | Min saved/week (est.) |
|-------|---------|-----------------------|
| eyes | kept | ~60 |
| eod-drafter | kept | ~120 |
| follow-up-radar | kept | ~30 |
Total: ~210 min/week. Retired this week: 0. Shipped this week: 0.
```

The table is pulled from the "Brian-owned skills" table in
`FLEET.md` (columns 1, 7, 6). Retired-this-week rows come from the
`Retired` table on the same file. The total is the sum of column 6
across active rows.

## Voice rules

- **Terse bullets.** Never a paragraph. If a bullet needs a sub-detail, use a
  nested bullet, not a sentence run-on.
- **Outcomes, not activities.** "Landed #45 (Google T1)" not "worked on Google
  T1 PR" — the state matters more than the effort.
- **Number and link everything.** PR numbers, issue numbers, meeting names.
  Use `<https://…|#45>` Slack link format, not bare URLs.
- **Emoji as section markers, not decoration.** `:test_tube:` for Labs/DevEx,
  `:dog-food:` for dogfooding, `:draft-ai-gateway:` for AI Gateway,
  `:building_construction:` for infra work. See emoji vocab below.
- **Callouts inline, not bolded headers.** Brian uses `:bulb:`, `:point_right:`,
  `:heart_hands:` as bullet-prefixes for asides. Never `**Bold Section**`.
- **Sign off** with `*Sent using* <@U093DJ468EN|Cursor>` when the post is
  agent-drafted. Do not fake human authorship.

## Emoji vocabulary (use these, not others)

| Emoji | Meaning |
|-------|---------|
| `:draft-ai-gateway:` | AI Gateway workstream |
| `:test_tube:` | Labs / DevEx |
| `:dog-food:` | Dogfooding block |
| `:building_construction:` | Infra / cutover |
| `:bullseye:` | Priority |
| `:handshake:` | Decisions |
| `:next_button:` | Next steps |
| `:tldr:` | tl;dr line |
| `:dashboard:` | Board hygiene |
| `:charter:` | Scope / recharter |
| `:pullreq:` | PR |
| `:bulb:` | Idea / note |
| `:point_right:` | Because / therefore |
| `:heart_hands:` | Endorsement |
| `:approved_stamp:` | Approval |

## Example — real EOD from 2026-08-10 (emoji-annotated for calibration)

The real post used the emoji vocabulary from the table above; this
calibration example keeps those markers in place so the LLM sees where
they live. If the drafter emits an EOD with *zero* emoji, that's a
calibration failure — Brian's posts always use at least two.

```
Today
:bullseye: Posted Goals for the Week: CI/CD gates for app + infra repos, Slackbot for CSV ingestion, AI-Native repos, more data visualized in the live environment
:pullreq: Reviewed and merged Ben's repo-managed Cloud Agent environment <https://github.com/liatrio-labs/marketing-dashboard/pull/45|#45>, then merged the AI-native agent harness (<https://github.com/liatrio-labs/marketing-dashboard/pull/39|#39> + <https://github.com/liatrio-labs/marketing-dashboard/pull/45|#45>) into my prototype branch via <https://github.com/liatrio-labs/marketing-dashboard/pull/52|#52> — :bulb: Bugbot caught the DB-backup hook failing closed without jq; fixed
:test_tube: Ran a multi-model review of the infra OpenTofu/ECS Fargate PR (marketing-dashboard-infra <https://github.com/liatrio-labs/marketing-dashboard-infra/pull/1|#1>) and opened draft <https://github.com/liatrio-labs/marketing-dashboard-infra/pull/54|#54> with the review doc; started reviewing Anmol's local=CI task check gate <https://github.com/liatrio-labs/marketing-dashboard/pull/53|#53>
:building_construction: Tightened up the infra repo: Ben made marketing-dashboard-infra Internal and added Anmol, Brad, and me as admins
:handshake: Confirmed the smallest demo-able metric slice with Masele — LinkedIn organic + Google Analytics from the All Marketing Data canvas is the right cut
:dog-food: Dug into Cursor cloud agents with Liatrio Brain — how the Forge team actually runs background agents and what we can reuse here (per Kevin's suggestion)
:next_button: Marked the engineering handoff point: automation built + data flowing in a format Metabase can consume

Tomorrow
:pullreq: Finish review and land Anmol's CI quality-gate <https://github.com/liatrio-labs/marketing-dashboard/pull/53|#53>; keep the linting CI/CD workflow moving
:test_tube: Push the infra <https://github.com/liatrio-labs/marketing-dashboard-infra/pull/1|#1> multi-model review findings to resolution with Anmol
:dashboard: Teach / share how to build views in Metabase — shape of the data
:bullseye: Start building against the confirmed LinkedIn organic + GA slice

*Sent using* <@U093DJ468EN|Cursor>
```

## Anti-patterns (avoid these)

- Long paragraph summaries. This isn't a status update, it's a delta.
- "Highlights" / "Lowlights" sections. Not Brian's structure.
- `**Bold**` markdown headers. Brian uses `\`code-quotes\`` for section names
  (e.g. `` `Today` `` `` `Tomorrow` ``) in some channels; plain "Today" is fine.
- Bland corporate voice ("continued to progress the initiative"). Brian's
  writing is direct, engineering-flavored, and outcome-focused.
- Fabricating PR numbers or meeting outcomes. If a signal isn't in GitHub /
  Slack / Granola, don't invent it — the draft is a memory aid, not fiction.
