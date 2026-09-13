# Cloud Agent setup — Delivery Principal Ops Kit (v0.1)

The gap between "PR merged" and "the schedule is producing daily DMs" is
this doc. It's a walkthrough of the Cursor Cloud Agents dashboard config
for all three skills. It does not repeat `install-notes.md` (where the
code lives) or `gateway-routing.md` (which gateway to pick) — read those
first if you haven't.

## Prerequisites

Before touching the Cloud Agents dashboard, confirm:

- **Slack MCP connected** in your Cursor account (Cursor settings → MCP).
  All three skills need this; `eyes` needs nothing else.
- **Granola MCP connected**, same place. Only `eod-drafter` uses it, but
  its preflight aborts without it, so connect it now regardless.
- **`gh` CLI authenticated as `@BriWalsh`.** Cloud Agent VMs ship with this
  already; nothing to do unless you're testing locally.
- **The three skills are installed** — either the promoted copies in
  `BriWalsh/cursor-user-skills`, or the staging path (Cloud Agent VM
  pointed at `BriWalsh/brwalsh:bots/`) described in
  [`install-notes.md`](./install-notes.md). Either is fine for the steps
  below; the Cloud Agent config below just needs to know which repo.

## Secrets configuration

Set these under **Cursor dashboard → Cloud Agents → Secrets → User
scope → New secret**. One secret per row; the value goes in the "value"
field, the name in "key," exactly as written below (case-sensitive).

| Secret | Skill(s) | Required? | Where the value comes from |
|--------|----------|------------|------------------------------|
| `GATEWAY_BASE_URL` | eod-drafter, follow-up-radar | Required | Current daily-driver endpoint — see below |
| `GATEWAY_API_KEY` | eod-drafter, follow-up-radar | Required | Bearer token for that same gateway |
| `GATEWAY_MODEL` | eod-drafter, follow-up-radar | Required | Model name that gateway expects |
| `GATEWAY_TASK_TYPE` | eod-drafter, follow-up-radar | Optional | Each skill defaults this itself (`eod-draft`, `commitment-radar`) — only set if overriding |
| `CLIENT_DOMAINS` | eod-drafter | Optional | Defaults `natera.com,goengen.com` — only set if the client list changes |
| `CLIENT_TITLE_ALIASES` | eod-drafter | Optional | JSON object `{"domain.com": ["Alias1", "Alias2"]}`. Built-in defaults already cover `goengen.com` (`enGen`, `EnGen`) and `natera.com` (`Natera`, `Panorama`, `Signatera`, `Prospera`). Set only to extend that table. Malformed JSON fails closed (preflight abort). |

`eyes` needs none of these — it does zero gateway calls in v0.1.

**Where do the gateway values come from today?** The daily-driver
rotation across Bifrost / Agent Gateway / LiteLLM / Azure APIM changes
day to day and is not tracked in this repo — see
[`gateway-routing.md`](./gateway-routing.md) for the rotation mechanics
and placeholder examples. For the actual current-day `GATEWAY_BASE_URL`
/ `GATEWAY_MODEL` pair, ask Alex or check `#project-ai-gateway`. Do not
reuse yesterday's values without confirming — a stale endpoint fails
preflight or, worse, 5xx's mid-run.

Slack MCP and Granola MCP tokens are **not** Cloud Agent secrets — they
ride along with your connected Cursor account, per the Prerequisites
section above.

## Schedule configuration

Each skill gets its own Cloud Agent schedule entry. Create each under
**Cloud Agents → Schedules → New schedule**.

Common fields across all three:

| Field | Value |
|-------|-------|
| Repo | `BriWalsh/cursor-user-skills` (post-promotion) or `BriWalsh/brwalsh` (staging) |
| Branch | `main` |
| Trigger type | Scheduled |
| Timezone | `America/Chicago` (named tz, not a UTC offset — Cursor handles DST) |
| Model | Any — `eyes` uses no LLM; `eod-drafter`/`follow-up-radar` call the gateway directly, so the outer agent model just parses SKILL.md and orchestrates |

### `eyes`

- **Time:** 07:00 daily (every day, no weekday restriction)
- **Prompt:**

  ```
  Run the `eyes` skill.
  ```

- **First run:** a digest DM lands at your own Slack DM (`U0A0T8FV12B`)
  within a few seconds — this skill has no gateway dependency, so there's
  no preflight-fail mode beyond a missing Slack MCP tool. If nothing
  arrives, see Troubleshooting below.

### `eod-drafter`

- **Time:** 16:00, weekdays only (skip Sat/Sun in the schedule config;
  the skill itself doesn't check the day of week)
- **Prompt:**

  ```
  Run the `eod-drafter` skill for today.
  ```

- **First run:** either a draft DM, or — if a `GATEWAY_*` secret is
  missing or the endpoint is unreachable — a one-line preflight-fail DM
  naming the missing piece. See the gateway secrets table above before
  enabling this schedule.

### `follow-up-radar`

- **Time:** 08:00 daily (including weekends — Sunday runs surface Friday
  commitments that rot over the weekend)
- **Prompt:**

  ```
  Run the `follow-up-radar` skill for yesterday's window.
  ```

- **First run:** same shape as `eod-drafter` — a digest DM on success, a
  preflight-fail DM if `GATEWAY_BASE_URL`/`GATEWAY_API_KEY`/`GATEWAY_MODEL`
  aren't all set.

## First-run smoke tests

Run these in order, cheapest first, before enabling any schedule. Each
skill's `runbook.md` has the full manual-invocation and smoke-test
detail — this is just the shortest path through all three.

1. **`eyes` first.** No LLM, no gateway secrets needed — effectively
   free. In a Cursor chat with the skill installed:

   ```
   Run the eyes skill --dry-run
   ```

   Confirms Slack MCP is wired correctly end to end. If this fails,
   nothing downstream will work either — fix Slack MCP before touching
   the other two. Details: [`eyes/runbook.md`](../eyes/runbook.md).

2. **`eod-drafter` dry-run.** Confirms Slack + Granola + `gh` + gateway
   secrets are all present, without spending real gateway tokens on a
   sent message:

   ```
   Run the eod-drafter skill for today --dry-run
   ```

   `--dry-run` still calls the gateway (that's the point — you're
   checking the draft quality) but skips the `slack_send_message` step;
   the draft logs to the Cursor transcript instead. Read it like you'd
   read your own EOD: does it capture the workstreams you actually
   touched? Details: [`eod-drafter/runbook.md`](../eod-drafter/runbook.md).

3. **`follow-up-radar` dry-run.** Same idea, plus a guardrail check:

   ```
   Run the follow-up-radar skill for yesterday's window --dry-run
   ```

   The transcript should report the `channel_bypass_check` from
   SKILL.md §9 as zero — if it's non-zero, a client channel reached the
   classifier and something upstream of the guardrail is broken; don't
   enable the schedule until that's zero on two consecutive dry-runs.
   Details: [`follow-up-radar/runbook.md`](../follow-up-radar/runbook.md).

Only enable a schedule once its dry-run looks right. `eyes` has no
meaningful failure mode beyond Slack MCP being disconnected; the other
two are worth a second dry-run the next day before trusting the schedule
unattended.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No DM at all, no error either | Slack MCP disconnected | Reconnect in Cursor settings → MCP → Slack. Re-run `eyes --dry-run` to confirm. |
| `eod-drafter` preflight-fail DM naming a missing Granola tool | Granola MCP disconnected or never connected | Reconnect in Cursor settings → MCP → Granola. |
| Preflight-fail DM naming a `GATEWAY_*` var | That secret isn't set, or is set under the wrong scope (team vs. user) | Re-check Cloud Agents → Secrets → User scope against the table above. Get current values from Alex / `#project-ai-gateway`. |
| DM says "gateway `<name>` is 5xx-ing" | The daily-driver gateway is down or rotated without updating secrets | Expected behavior per [`gateway-routing.md`](./gateway-routing.md) — no retry, no fallback, by design. Confirm the current daily driver in `#project-ai-gateway` and update `GATEWAY_BASE_URL`/`GATEWAY_MODEL` if it changed. |
| A DM arrived but the content looks wrong (wrong workstream, garbled links, missing items) | Usually a data-pull or serialization bug, not a secrets problem | Open **Cloud Agents → run history** for that schedule and read the transcript — it shows the raw tool calls and the exact prompt sent to the gateway. Cross-check against the relevant skill's `SKILL.md` section (e.g. `eod-drafter/SKILL.md §4` for workstream clustering). |
| `follow-up-radar` digest includes something that looks client-adjacent | The `channel_bypass_check` guardrail should have caught this — treat as a bug, not a config issue | Check the run transcript for the bypass-check warning. If it fired, that's expected (drop happened); if it's silent and client content still leaked, stop the schedule and investigate `SKILL.md §3` before re-enabling. |

## Post-setup: promotion to `cursor-user-skills`

Everything above works with the skills still living in
`BriWalsh/brwalsh:bots/` — that's the staging path, and it's fine to run
schedules against it indefinitely. But it only works if the Cloud Agent
VM you're scheduling against has access to `bots/` in `brwalsh`. Once
you're happy with all three skills, follow the promotion flow in
[`install-notes.md`](./install-notes.md) to move them into
`BriWalsh/cursor-user-skills`, which every Cloud Agent VM picks up
automatically via `.cursor/install-skills.sh`. After promotion, update
each schedule's **Repo** field from `BriWalsh/brwalsh` to
`BriWalsh/cursor-user-skills` — everything else in this doc stays the
same.
