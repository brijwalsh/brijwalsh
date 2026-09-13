---
name: eyes
description: >-
  Slack reading-queue closer for Brian Walsh. Finds messages Brian has reacted
  to with :eyes: (👁️), keeps durable dedup state in a private Slack List, and
  DMs him an age-aware reading queue. Use when Brian asks "what am I supposed
  to read?", when he says "run eyes", or on the daily 07:00 CT Cursor Cloud
  Agent schedule. Never posts anywhere except Brian's DM.
version: 0.2.0
author: Brian Walsh
license: Internal
metadata:
  hermes:
    tags: [internal, delivery-principal-ops-kit, slack, reading-queue]
    related_skills: [eod-drafter, follow-up-radar]
---

# Eyes — Slack `:eyes:` reading-queue closer (v0.2)

Brian bookmarks intent by dropping an `:eyes:` (👁️) reaction on Slack messages he
plans to re-read. That intent then rots. This skill keeps the queue in Slack,
stops repeating the same item every morning, and pushes the items Brian has
ignored longest to the top.

## v0.2 scope contract

**In scope:**
- `hasmy::eyes:` search over a configurable window, capped at 20 items
- Durable, permalink-keyed dedup state in a private Slack List
- Age-of-awareness ranking and daily suppression of previously digested items
- Item-level clearing from `:x:` or `:done:` reactions in the prior digest
- DM output only to Brian at `U0A0T8FV12B`

**Out of scope:**
- LLM classification. Regex and channel-name heuristics are enough.
- Removing Brian's reaction. The skill observes reactions but never changes one.
- Sending Slack content to the gateway, GitHub, Granola, Gmail, or any service
  outside Slack.
- Real-time Slack event handling. Clear reactions are polled on the next run.

## 1. Preflight

Set `now` once at run start. Use that same instant for filtering, ranking,
rendering, and writes. Compute dates and display times in `America/Chicago`.

Environment:
- `SLACK_LIST_ID` is required for v0.2 durable mode.
- `DEDUP_WINDOW_DAYS` is optional and defaults to `7`. If it is not a positive
  integer, DM `eyes: invalid DEDUP_WINDOW_DAYS; using 7` and use `7`.

Always-required MCP tools:
- `Slack.slack_search_public_and_private`
- `Slack.slack_send_message`

Durable-mode MCP tools:
- `Slack.slack_read_list`
- `Slack.slack_add_list_record`
- `Slack.slack_update_list_record`
- `Slack.slack_get_reactions`

If an always-required tool is missing, DM Brian one line
(`eyes: cannot run, missing <tool>`) and exit.

Missing `SLACK_LIST_ID` is the one rollout exception to durable mode's
fail-closed rule. DM Brian exactly:

```text
v0.2 dedup requires SLACK_LIST_ID; falling back to v0.1 stateless behavior for this run
```

Then run the v0.1 path: search as described in §3, rank by class, Slack age,
work-channel signal, and newest timestamp, and send the original stateless
digest. Do not call a List or reaction tool. Do not add `🆕` or `Xd on your
list`, because no durable timestamp exists.

When `SLACK_LIST_ID` is set, require every durable-mode tool. A missing tool,
unreadable list, `feature_not_enabled`, or schema mismatch must DM a clear
`eyes: cannot run, ...` line and exit. Do not silently use stateless mode after
durable state has been configured.

`--dry-run` may read and compose, but it must not DM or write List state.

## 2. Load dedup state

Call `slack_read_list` with the exact `$SLACK_LIST_ID`, `format: csv`, and
`limit: 100`. Follow every returned `next_cursor` unchanged until no cursor
remains. Never resolve the List by its title during a run.

Validate these columns before using any row:

`Permalink`, `Channel Name`, `Channel ID`, `Author`, `Text Excerpt`,
`Original TS`, `First Seen TS`, `Last Seen TS`, `State`,
`Snoozed Until TS`, `Class`, `Age At First Seen Days`,
`Last Digest Message TS`, `Last Digest Rank`, `Digest Channel ID`,
`Cleared TS`, `Clear Source`, and `Write Token`.

Build an index by `Permalink`. The permalink is the logical primary key; the
Slack `Record ID` is the physical row ID. Keep the oldest `First Seen TS` row
as canonical if duplicates exist, suppress the others, and reconcile them
after the digest.

Build these working sets:
- `recent_open`: canonical rows with `State=open` and `Last Seen TS >=
  now - DEDUP_WINDOW_DAYS`
- `due_snoozed`: rows whose snooze timestamp has passed
- `last_digest`: rows associated with the latest digest metadata record
- `recyclable`: rows outside the window that are not part of `last_digest`

The fixed metadata record uses `Permalink=__eyes_metadata__`. Its
`Last Digest Message TS` stores the parent digest message timestamp,
`Digest Channel ID` stores the DM channel, and `Last Seen TS` stores the run
instant. Item replies sent after that parent have a greater Slack timestamp,
which identifies the rows in that digest. Create this fixed record
idempotently if it does not exist.

Run the primary clear check in §8 after loading the index and before searching.

## 3. Search Slack

```yaml
tool: slack_search_public_and_private
args:
  query: "hasmy::eyes: after:<YYYY-MM-DD>"
  keywords: []
  filters: "hasmy::eyes: after:<YYYY-MM-DD>"
  natural_language_query: ""
  limit: 20
  sort: timestamp
  sort_dir: desc
  only_my_channels: true
  include_context: false
```

`<YYYY-MM-DD>` is `today - DEDUP_WINDOW_DAYS` in `America/Chicago`.
Slack's `after:` operator accepts an ISO date, not `yesterday`.
`hasmy::emoji:` scopes to the caller's reactions. Keep `limit: 20`; the Slack
MCP rejects larger values.

Every digest field already exists on the search hit:

| Digest field | Search field |
|---|---|
| permalink | `permalink` |
| channel | `channel.name`, or the participant rules below |
| author | `user_name`, then `username`, then `user` |
| snippet | cleaned `text`, capped at 200 characters |
| Slack timestamp | `ts` |
| class | derived below |

**Channel rendering.**
- Named channel: `` `#<channel.name>` ``
- Two-person DM: `DM w/ <other participant display name>`
- Group DM: `Group DM w/ <other participant names>`
- Last-resort fallback: `` `<channel.id>` ``

Never show a raw DM ID when participant data is available.

**Snippet cleaning.** Apply these rules in order before truncation:
1. `<https?://…|label>` becomes `label`
2. `<https?://…>` becomes the URL
3. `<@USERID|handle>` becomes `@handle`
4. `<@USERID>` becomes `@<USERID>`
5. `<#CHANNEL_ID|name>` becomes `#name`
6. `<!channel>`, `<!here>`, and `<!everyone>` become their `@` forms
7. `<!subteam^S…|name>` becomes `@name`
8. Truncate to 200 characters and append `…` only when truncated

**Class rules, with no LLM:**
- `pr`: text matches `github\.com/[^/]+/[^/]+/pull/\d+`
- `doc`: text matches `(notion\.so|confluence|docs\.google\.com|liatr\.io)`
- `article`: exactly one external URL and no Liatrio or GitHub domain
- `thread`: `reply_count >= 3`
- `msg`: everything else

Create `fresh_by_permalink` from the search response.

## 4. Merge with dedup state

For every fresh search hit:
- No canonical row: prepare one `open` row with `First Seen TS=now`,
  `Last Seen TS=now`, `Clear Source=none`, and `is_new=true`.
- Existing `open` row: keep `First Seen TS`, prepare a narrow metadata and
  `Last Seen TS=now` update, and set `is_new=false`.
- Existing `snoozed` row not yet due: update `Last Seen TS` but do not digest.
- Existing `snoozed` row now due: move it to `open`, keep `First Seen TS`, and
  make it digest-eligible.
- Existing `cleared` row: update `Last Seen TS` only. Search never reopens it.

`First Seen TS` never changes. `Age At First Seen Days` is computed once from
`Original TS` and retained.

The scheduled digest includes new rows, due snoozed rows, and rows whose prior
digest-marker write failed. It excludes an `open` row that already has a
`Last Digest Message TS`. `/eyes --all` includes all recent open rows, capped
at 20. This eligibility rule is the dedup: updating a row without suppressing
it would repeat the same queue every day.

After search, run the source-reaction fallback in §8 for recent open rows that
are absent from `fresh_by_permalink`. Never treat absence alone as proof when
the search returns its 20-item cap.

## 5. Rank

Sort each eligible set by:
1. Awareness age, `now - First Seen TS`, longest first
2. `pr` and `doc` before other classes
3. Slack age over five days before newer messages
4. Channels beginning with `client-` or `project-`
5. Newest `Original TS` as the final tie-breaker

Awareness age is the primary signal. A message Brian first saw six days ago
beats one first seen today, even when the newer queue item points to an older
Slack message.

The v0.1 fallback omits step 1 because it has no `First Seen TS`.

## 6. Compose the digest

Send one parent DM to `U0A0T8FV12B`:

```text
:eyes: *Reading queue — <N> new from the last <window> days* _(as of <YYYY-MM-DD HH:mm CT>)_

<M> previously seen items remain open. Run `/eyes --all` to review them.
React :x: or :done: on an item reply to clear it next run.
```

Send each ranked item as a reply in that DM thread. Separate messages are
intentional: Slack reactions belong to a message, not a line inside one large
digest. Prefix the first five with `*Close the loop*`; later rows use `*Later*`.

```text
*Close the loop*
1. 🆕 [doc] `#project-ai-gateway` · Example Person — 0d on your list
   "Cleaned snippet"
   <permalink>
```

Prefix `🆕 ` only when `is_new=true`. The suffix is
`— Xd on your list`, where `X=floor((now - First Seen TS) / 86400)`.
Use the eight cleaning steps in §3 for every snippet.

Capture the parent timestamp, DM channel ID, and each item reply timestamp.
The reply timestamp is that row's `Last Digest Message TS`, so a later clear
check targets one item exactly.

## 7. Write path

Write no durable state until the parent and item DMs succeed. Once sent, run
one bounded write phase with no more than four record writes in flight:
- New permalink: use `slack_add_list_record`, unless a recyclable record is
  available for a full `slack_update_list_record`.
- Existing permalink: use `slack_update_list_record` with only changed
  observation fields. Do not include `State` in an ordinary observation update.
- Displayed row: also write its item reply timestamp, digest rank, and DM
  channel ID.
- Metadata row: write the parent timestamp, channel ID, and run instant.
- Clear operation: update only `State`, `Cleared TS`, and `Clear Source`.

Make every write retry-safe:
1. Index by permalink and update the canonical `Record ID`.
2. Before an insert, and before retrying an insert after a timeout, re-read the
   List and update the row if the permalink now exists.
3. Give each insert or recycled row the run UUID in `Write Token`.
4. Re-read touched rows after adds or recycling. Keep the oldest canonical row
   and mark duplicates `cleared`.
5. Retry a failed row once. Never resend the digest during the same run.

Slack Lists have no batch transaction or unique constraint. "Write phase"
means a bounded group of idempotent row operations, not an atomic batch.

If one or more rows still fail after retry, the digest remains valid. DM:

```text
eyes: digest sent, but <N> dedup state writes failed; the next run will recover
```

This is fail-open only after the digest has been sent. A later run can recover
state drift by permalink without leaking Slack data outside Slack.

## 8. Clear flow

Run the primary check at the start of the next scheduled durable-mode run:
1. Read the metadata record's latest parent digest timestamp and channel.
2. Select item rows whose `Last Digest Message TS` is greater than that parent
   timestamp. Those are the replies in the latest digest thread.
3. Call `slack_get_reactions` for each item reply.
4. If Brian (`U0A0T8FV12B`) added `:x:` or `:done:`, partially update that row
   to `State=cleared`, `Cleared TS=now`, and `Clear Source=cursor_clear`.
5. Repeating the check against a cleared row is a no-op.

The metadata parent timestamp is the lower bound for the latest item replies.
Do not interpret a reaction on the parent as an item command, because it cannot
identify one numbered row.

Fallback after §3: for each recent open row absent from the fresh search, call
`slack_get_reactions` on its source `Channel ID` and `Original TS`. If Brian's
`:eyes:` reaction is absent, mark the row `cleared` with
`Clear Source=eyes_removed`. If the source check fails, leave the row open and
include one warning in the DM. The skill never removes the reaction itself.

## 9. Heartbeat

If durable merge and clear processing leave zero open items, DM one line:

```text
:eyes: reading queue clean at HH:MM CT — 0 open items on your list.
```

If open items remain but none are newly digest-eligible, send the parent digest
with `0 new` and the open count. That is not a clean queue.

## Guardrails and cost

- Post only to Brian's DM, `U0A0T8FV12B`.
- Keep source excerpts, channel metadata, digest content, and durable state
  inside Slack. Nothing in this skill calls the gateway.
- Never add or remove reactions.
- Report Slack errors by code. Do not swallow partial failures.
- LLM usage is zero.
- A normal run uses one search, one to three List reads, reaction checks, one
  parent DM plus item replies, and up to 20 row writes. Do not preserve v0.1's
  five-second budget; List and reaction calls can take longer.

## Runbook

See [`runbook.md`](./runbook.md) for Slack List creation, secrets, schedule
configuration, and manual invocation.
