# EOD Auto-Drafter — Runbook (v0.1)

## Cursor Cloud Agent trigger

- **Repo:** `BriWalsh/cursor-user-skills` (after moving) or `BriWalsh/brwalsh`
  (staging)
- **Schedule:** Weekdays at **16:00 America/Chicago**. Skip Sat/Sun and US
  federal holidays.
- **Prompt:**

  ```
  Run the `eod-drafter` skill for today.
  ```

- **Required MCP:** Slack, Granola.
- **Required CLI:** `gh` authenticated as `@BriWalsh`.
- **Required env vars** (set as Cloud Agent secrets):
  - `GATEWAY_BASE_URL` — e.g. `https://litellm.internal.liatrio/gateway/v1`
  - `GATEWAY_API_KEY`
  - `GATEWAY_MODEL` — e.g. `claude-sonnet-5`
  - `CLIENT_DOMAINS` — default `natera.com,goengen.com`
- **Model in the Cursor agent card:** any (the skill calls the gateway
  itself; the outer agent model just parses SKILL.md and orchestrates).

## Rotating gateways manually (v0.1)

v0.1 does not rotate through Bifrost / Agent Gateway / LiteLLM / APIM
automatically. Brian rotates by editing the `GATEWAY_BASE_URL` /
`GATEWAY_MODEL` secrets in the Cloud Agent dashboard when the team switches
daily driver.

Rotation automation is v0.2 in [`../ROADMAP.md`](../ROADMAP.md).

## First-run smoke test

1. Set the env vars to point at the current daily-driver gateway.
2. Run `"Run the eod-drafter skill for today --dry-run"` in a Cursor chat.
3. Compare against your last hand-written EOD. If the draft is missing a
   real workstream you touched today, check that channel is in the
   cluster-mapping table in `SKILL.md §4`.
4. Once it reads like you, enable the schedule.

## What v0.1 explicitly does not do

- Auto-create `#draft-eods` (public-by-default = client-leak risk; drafts
  go to your DM instead)
- Persist `friction.jsonl` across runs (VM-ephemeral)
- Emit a Friday weekly friction summary
- Listen for `/eod-friction` replies
- Retry a 5xx gateway
- Send client-domain meeting summaries or next-steps to any LLM

## Cost

Per run: target under $0.05, hard cap $0.20 (bail + DM).
Per week (5 runs): under $0.30. Per month: under $2.00.
