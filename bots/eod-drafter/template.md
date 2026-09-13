# Brian's canonical EOD template

Extracted from real EOD posts across `#liatrio-forge`, `#project-marketing-dashboard`,
and `#project-ai-gateway`. The drafter must produce output that looks like it
was written by Brian, not by an LLM defaulting to bland structure.

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
```

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

## Example — real EOD from 2026-08-10

```
Today
• Posted Goals for the Week: CI/CD gates for app + infra repos, Slackbot for CSV ingestion, AI-Native repos, more data visualized in the live environment
• Reviewed and merged Ben's repo-managed Cloud Agent environment PR #45, then merged the AI-native agent harness (#39 + #45) into my prototype branch via #52 — Bugbot caught the DB-backup hook failing closed without jq; fixed
• Ran a multi-model review of the infra OpenTofu/ECS Fargate PR (marketing-dashboard-infra #1) and opened draft PR #54 with the review doc; started reviewing Anmol's local=CI task check gate PR #53
• Tightened up the infra repo: Ben made marketing-dashboard-infra Internal and added Anmol, Brad, and me as admins
• Confirmed the smallest demo-able metric slice with Masele — LinkedIn organic + Google Analytics from the All Marketing Data canvas is the right cut
• Dug into Cursor cloud agents with Liatrio Brain — how the Forge team actually runs background agents and what we can reuse here (per Kevin's suggestion)
• Marked the engineering handoff point: automation built + data flowing in a format Metabase can consume

Tomorrow
• Finish review and land Anmol's CI quality-gate PR #53; keep the linting CI/CD workflow moving
• Push the infra PR #1 multi-model review findings to resolution with Anmol
• Teach / share how to build views in Metabase — shape of the data
• Start building against the confirmed LinkedIn organic + GA slice
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
