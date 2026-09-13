# Delivery Principal Ops Kit

Three small, opinionated Cursor Skills that close the loops a Delivery
Principal actually loses time on: reading debt, daily synthesis, and dropped
commitments. All three ship as **v0.1** — the smallest shape that solves
the wound safely, with the rest deferred to [`ROADMAP.md`](./ROADMAP.md).

Each subfolder is an **agent-agnostic Cursor Skill** (SKILL.md + supporting
docs), so any Cursor Cloud Agent, Claude Code session, or manual run can
pick it up.

## The three bots

| Skill | The wound it closes | Trigger | Human-in-the-loop? |
|-------|---------------------|---------|---------------------|
| [`eyes/`](./eyes/SKILL.md) | Slack `:eyes:` reactions rot forever; the reading queue never gets closed | Daily 07:00 CT + on-demand | Digest to Brian's DM; no external posts |
| [`eod-drafter/`](./eod-drafter/SKILL.md) | 20–30 min/day writing EOD posts across six workstreams | Weekdays 16:00 CT + on-demand | Draft to Brian's DM; Brian reviews and reposts |
| [`follow-up-radar/`](./follow-up-radar/SKILL.md) | Internal Liatrio commitments slip because nothing watches them | Daily 08:00 CT | Draft-only DM to Brian; **never** auto-sends |

## v0.1 hard rules

1. **All output goes to Brian's DM (`U0A0T8FV12B`).** No public channel, no
   client channel, no email. Ever.
2. **No `#client-*` channel content leaves Slack MCP.** `follow-up-radar`
   is internal-only in v0.1; `eod-drafter` redacts client-domain Granola
   meetings and strips their next-steps before the gateway call.
3. **No fallback if the gateway is down.** DM Brian and exit; the whole
   point is to generate dogfooding data for `project-ai-gateway#125`.
4. **No autonomous action on Brian's behalf.** The kit drafts; Brian sends.

## What ships in v0.1 vs later

| Feature | v0.1 | Deferred to [`ROADMAP.md`](./ROADMAP.md) |
|---------|------|-------|
| Digest DM to Brian | ✅ (all three) | — |
| Regex + gateway-classified commitments (internal channels only) | ✅ (radar) | Client channels → v0.2 §4 |
| EOD draft from GH+Slack+Granola | ✅ | Rotation YAML, friction.jsonl → v0.2 §1–2 |
| `:eyes:` reading queue via `hasmy::eyes:` | ✅ | Dedup + `clear` state → v0.2 §1 |
| Gmail in radar | ❌ | v0.2 §5 (BAA + DLP gate) |
| Slack `message.im` listeners (`clear`/`send`) | ❌ | v0.2 §3 |
| Weekly gateway-friction summary → `#125` | ❌ | v0.2 §2 |
| Auto gateway rotation across 4 endpoints | ❌ | v0.2 §2 |

## The shared plumbing

- **Slack MCP** — `slack_search_public_and_private`, `slack_send_message`,
  `slack_read_thread` (radar only)
- **Granola MCP** — `list_meetings`, `get_meetings` (`eod-drafter` only,
  with client-domain quarantine)
- **GitHub** — `gh` CLI, authenticated as `@BriWalsh` (`eod-drafter` only)
- **AI Gateway** — every LLM call goes through `$GATEWAY_BASE_URL`;
  see [`docs/gateway-routing.md`](./docs/gateway-routing.md).

## Where these live

**Staging (this PR):** `BriWalsh/brwalsh:bots/*` for review.

**Production (post-merge):** move each skill folder to
`BriWalsh/cursor-user-skills` so `.cursor/install-skills.sh` picks them
up on every Cloud Agent VM. Details in
[`docs/install-notes.md`](./docs/install-notes.md).

## Sequenced roll-out

1. **This weekend** — ship [`eyes/`](./eyes/SKILL.md) v0.1. Weekend build,
   near-zero cost, prove the loop.
2. **Mon–Wed next week** — ship [`eod-drafter/`](./eod-drafter/SKILL.md)
   v0.1 through the current daily-driver gateway. Track: minutes saved,
   edits per draft, gateway friction. That data feeds
   `project-ai-gateway#125` for free.
3. **The week after** — ship [`follow-up-radar/`](./follow-up-radar/SKILL.md)
   v0.1 (internal channels only).
4. **Weeks 3–4** — measure. If all three are used and saving time, promote
   the whole thing to the "Delivery Principal Ops" pattern for
   `#liatrio-weekly-workstream-updates`. Not "I built three bots" — the
   *reusable pattern* that any Delivery Principal can pick up.

## Non-goals (never in any version)

- Anything that posts to a client channel automatically
- Anything that emails a client on Brian's behalf
- Anything that scrapes school portals, hospital sites, or Home Assistant
- Anything that automates X content for @BriJWalsh (the audience isn't there)
- Cross-platform DMs (Telegram/WhatsApp) — Brian lives in Slack

## How this got here

- 4-model panel review (Grok 4.6, Claude Sonnet 5, GPT-5.6, Gemini 3.8) of
  Brian's X engagement + Slack workflow signals → converged on these three
- Grok 4.6 code review of the v0.2 design surfaced show-stopping bugs and
  a serious client-data leak risk in the original radar design → pulled
  scope back to safe v0.1 above
- All shipped changes live under this PR's branch
