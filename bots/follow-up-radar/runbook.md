# Follow-up Radar — Runbook (v0.1)

## Cursor Cloud Agent trigger

- **Repo:** `BriWalsh/cursor-user-skills` (after moving) or `BriWalsh/brwalsh`
  (staging)
- **Schedule:** Daily at **08:00 America/Chicago**, including weekends
  (Sundays surface Friday commitments that rot over the weekend).
- **Prompt:**

  ```
  Run the `follow-up-radar` skill for yesterday's window.
  ```

- **Required MCP:** Slack.
- **Required env vars** (Cloud Agent secrets):
  - `GATEWAY_BASE_URL`
  - `GATEWAY_API_KEY`
  - `GATEWAY_MODEL`

## Watched channels

Managed by editing `SKILL.md §2` and committing. **Never** add a
`#client-*` channel — the §3 guardrail will drop them regardless, but
don't rely on the safety net.

To add a new *internal* channel to the watch list:

1. Get the channel ID (`Cxxxxxxx`) via `slack_search_channels`.
2. Add to `watched_internal_channels` in `SKILL.md §2`.
3. Confirm it's internal (`#project-*`, `#liatrio*`, `#product-liatrio-*`).
4. Dry-run once; verify no client-domain content leaked into the classifier.

## First-run smoke test

1. Dry-run against yesterday's window.
2. Verify `channel_bypass_check` reports zero client channels reached
   the classifier.
3. Verify the drafts sound like Brian, not corporate.
4. Confirm the digest DMs to `U0A0T8FV12B` and nowhere else.
5. Enable the schedule only after two consecutive clean dry-runs.

## What v0.1 explicitly does not do

- Read **any** message from `#client-*` channels — hard-blocked in `§3`
- Read Gmail (deferred until v0.2 DLP gate)
- Cross-reference Granola meetings (same reason)
- Listen for `clear` / `send` replies
- Persist aging state across runs (dupes are expected until v0.2)

## Monthly privacy audit (5 min)

- [ ] `grep -R "client-" ~/.cache/follow-up-radar/` returns nothing
- [ ] Digest DMs from the last 30 days have no client identifiers
- [ ] No gateway logs (if available) reference Natera / enGen content
- [ ] Watched channels list still contains only internal channels

## v0.2 gate — client channels + Gmail

Do not unlock client channels or Gmail without all of:

- [ ] Verified BAAs with every gateway on the rotation
  (Bifrost/Agent Gateway/LiteLLM/APIM)
- [ ] A DLP layer that strips PHI/PII **before** the gateway call,
  not after (post-call redaction on DM output is theater)
- [ ] Legal sign-off documented in this repo (`bots/docs/v0.2-legal.md`)
- [ ] A durable state store so aging + dedup actually work

Absent any of the above, v0.1 is the ceiling.

## Cost

Per run: target under $0.15, hard cap $0.40 (bail + DM).
Per week: under $1.00. Per month: under $4.00.
