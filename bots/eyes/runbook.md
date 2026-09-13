# Eyes — Runbook (v0.2)

## One-time setup

Create a private Slack List named `eyes reading queue` or `Eyes queue state`.
Use `Slack.slack_create_list` or create it in the Slack UI. Do not share the
List to a channel.

Create these columns exactly as named:

| Column | Type | Options |
|---|---|---|
| `Permalink` | text | |
| `Channel Name` | text | |
| `Channel ID` | text | |
| `Author` | text | |
| `Text Excerpt` | rich_text | |
| `Original TS` | text | |
| `First Seen TS` | text | |
| `Last Seen TS` | text | |
| `State` | select | `open`, `cleared`, `snoozed` |
| `Snoozed Until TS` | text | |
| `Class` | select | `pr`, `doc`, `article`, `thread`, `msg` |
| `Age At First Seen Days` | number | |
| `Last Digest Message TS` | text | |
| `Last Digest Rank` | number | |
| `Digest Channel ID` | text | |
| `Cleared TS` | text | |
| `Clear Source` | select | `none`, `cursor_clear`, `eyes_removed` |
| `Write Token` | text | |

The complete field semantics and creation example remain in
[`v0.2-dedup-design.md`](./v0.2-dedup-design.md#slack-list-schema).

Open the List and copy its ID from the Slack URL. In the Cloud Agents
dashboard, add the user-scoped secret:

```text
SLACK_LIST_ID=<id>
```

`DEDUP_WINDOW_DAYS` is optional and defaults to `7`.

During rollout, a run without `SLACK_LIST_ID` sends a warning and uses v0.1
stateless behavior. Once the secret is set, an unreadable or malformed List
fails closed rather than repeating the queue.

## Cursor Cloud Agent trigger

- **Repo:** `BriWalsh/cursor-user-skills` after promotion, or
  `BriWalsh/brwalsh` during staging
- **Schedule:** Daily at **07:00 America/Chicago**. Use the named timezone so
  Cursor handles DST.
- **Prompt:**

  ```text
  Run the `eyes` skill.
  ```

- **Model:** any; the skill uses no LLM.
- **Required MCP:** Slack, including Slack Lists.
- **Required secret:** `SLACK_LIST_ID`.

The README, SKILL.md, and this runbook all use 07:00 CT. Change all three if
the schedule moves.

## Manual invocation

From any Cursor chat with the skill installed:

```text
Run the eyes skill
```

Slash-command style prompts:

```text
/eyes
/eyes --all
/eyes --dry-run
```

`--all` includes previously digested open rows. `--dry-run` reads and composes
but sends no DM and writes no List state.

## First-run smoke test

1. Run `Run the eyes skill --dry-run`.
2. Confirm the List schema passes and Slack search returns expected items.
3. Confirm the proposed DM target is `U0A0T8FV12B`.
4. Run the normal path once. Verify the parent digest and item replies arrive.
5. Run it again. Previously digested items should not repeat.
6. React `:done:` to one item reply, run again, and confirm its List row changes
   to `State=cleared`.
7. Enable the schedule.

## What v0.2 does

- Stores permalink-keyed queue state in a private Slack List.
- Shows new items once in the daily digest instead of repeating them for the
  whole search window.
- Ranks `/eyes --all` by how long an item has been on Brian's list.
- Clears an item on the next run after Brian reacts `:x:` or `:done:` to that
  item's digest reply.
- Clears an open item when the source no longer has Brian's `:eyes:` reaction.
- Keeps the digest and state inside Slack.

## What v0.2 does not do

- Remove reactions from source messages.
- Send Slack content through an LLM or gateway.
- Listen for Slack events in real time. Clear reactions are polled on the next
  scheduled or manual run.
- Fetch thread context or author profiles.
- Reopen a cleared item automatically.

## Cost

LLM and gateway cost remain zero. Slack call volume is higher than v0.1 because
the skill reads and updates the List and polls reactions.
