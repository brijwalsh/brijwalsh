# Eyes — Runbook (v0.1)

## Cursor Cloud Agent trigger

- **Repo:** `BriWalsh/cursor-user-skills` (after moving) or `BriWalsh/brwalsh`
  (during staging)
- **Schedule:** Daily at **07:00 America/Chicago** (12:00 UTC in CDT,
  13:00 UTC in CST). Cursor Cloud Agents accept named tz, so configure the
  cron as `America/Chicago` and let it handle DST; do not hard-code a UTC
  offset. The README, SKILL.md, and this runbook all agree on 07:00 CT — if
  you change one, change all three.
- **Prompt:**

  ```
  Run the `eyes` skill.
  ```

- **Model:** any; the skill uses no LLM in v0.1.
- **Required MCP:** Slack.

## Manual invocation

From any Cursor chat with the skill installed:

```
Run the eyes skill
```

Or, if invoked via a slash-command style prompt in your chat:

```
/eyes            # normal digest
/eyes --dry-run  # compose but do not DM
```

## First-run smoke test

1. Open the skill in a Cursor chat and say **"Run the eyes skill --dry-run"**.
   Confirm the search returns items and the digest formats cleanly.
2. Verify the DM would go to `U0A0T8FV12B` (your own user id).
3. Once clean, enable the schedule.

## What v0.1 explicitly does not do

- Track which items you've already seen (same items may reappear every run)
- React to `clear` commands (Cursor Cloud Agents don't have Slack event
  triggers for DMs; wiring a real listener is v0.2 work)
- Classify items with an LLM
- Fetch thread context or author profiles

If any of that starts to matter, promote to v0.2 per [`../ROADMAP.md`](../ROADMAP.md).

## Cost

Under $0.001 per run. Even a year of daily runs is a rounding error.
