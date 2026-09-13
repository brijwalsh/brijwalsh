## What this adds

Three small, opinionated Cursor Skills that close loops a Delivery
Principal loses time on, plus the shared docs that back them:

- **`eyes/`** — finds Slack messages reacted to with `:eyes:` in the last
  7 days and DMs a ranked reading-queue digest.
- **`eod-drafter/`** — pulls today's GitHub, Slack, and Granola activity
  and drafts the end-of-day post, routed through the AI Gateway.
- **`follow-up-radar/`** — scans yesterday's internal Slack activity for
  slipping commitments and drafts the follow-up language.
- **`_delivery-principal-ops-kit/`** — the README, ROADMAP, and docs
  shared across all three skills (gateway routing, install notes, this
  kit's install/uninstall recipe).

Each skill is an agent-agnostic Cursor Skill (`SKILL.md` + supporting
docs), so any Cursor Cloud Agent, Claude Code session, or manual run can
pick it up.

## How the install works

`.cursor/install-skills.sh` in this repo already syncs every top-level
skill folder into `~/.cursor/skills/` (and `~/.agents/skills/`) on every
Cloud Agent VM. Dropping `eyes/`, `eod-drafter/`, and `follow-up-radar/`
at the repo root — no code changes to the installer — is what makes them
show up automatically the next time a VM boots.

## What ships in v0.1 vs deferred

| | v0.1 | Deferred |
|---|------|----------|
| All three skills | Digest/draft to Brian's DM only, no client-channel content, no autonomous sends | Dedup state, gateway rotation, Slack event listeners, client channels + Gmail (behind a DLP/BAA gate) |

Full breakdown, gates, and anti-features: see
[`_delivery-principal-ops-kit/ROADMAP.md`](../_delivery-principal-ops-kit/ROADMAP.md).

## Non-goals

- Anything that posts to a client channel automatically
- Anything that emails a client on Brian's behalf
- Anything that scrapes school portals, hospital sites, or Home Assistant
- Anything that automates X content for @BriJWalsh (the audience isn't there)
- Cross-platform DMs (Telegram/WhatsApp) — Brian lives in Slack

## How this got here

The kit came out of a 4-model panel review (Grok 4.6, Claude Sonnet 5,
GPT-5.6, Gemini 3.8) of Brian's X engagement and Slack workflow signals,
which converged on these three skills. A follow-up code review surfaced a
client-data leak risk in the original `follow-up-radar` design, which
pulled scope back to the safety-first v0.1 described above. It staged and
shipped as [`BriWalsh/brwalsh#4`](https://github.com/BriWalsh/brwalsh/pull/4)
before this promotion.
