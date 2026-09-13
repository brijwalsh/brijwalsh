---
name: eyes
description: >-
  Slack reading-queue closer for Brian Walsh. Finds messages Brian has reacted
  to with :eyes: (👁️) in the last 7 days and DMs him a ranked list with
  permalinks and snippets. v0.1 has no dedup state, no LLM, no clear-command
  listener — just the digest. Use when Brian asks "what am I supposed to
  read?", when he says "run eyes", or on the daily 07:00 CT Cursor Cloud
  Agent schedule. Never posts anywhere except Brian's DM.
version: 0.1.0
author: Brian Walsh
license: Internal
metadata:
  hermes:
    tags: [internal, delivery-principal-ops-kit, slack, reading-queue]
    related_skills: [eod-drafter, follow-up-radar]
---

# Eyes — Slack `:eyes:` reading-queue closer (v0.1)

Brian bookmarks intent by dropping an `:eyes:` (👁️) reaction on Slack messages he
plans to re-read. That intent then rots. This skill closes the loop by DM'ing him
a digest of the last 7 days of `:eyes:`-reacted messages.

## v0.1 scope contract

**In scope:**
- `hasmy::eyes:` search over the last 7 days, cap 20 items
- Rank by age + channel type
- DM the digest to Brian at `U0A0T8FV12B`

**Out of scope for v0.1** (defer to [`../ROADMAP.md`](../ROADMAP.md)):
- Dedup state across runs (v0.1 shows the last 7 days every time — Brian
  mentally handles overlap)
- `clear <n>` listener (Cursor Cloud Agents have no Slack `message.im`
  webhook trigger, so this can't be wired reliably)
- LLM classification of items (regex + channel-name heuristics are enough
  for a 20-item digest)
- Removing the reaction on Brian's behalf (never, in any version)

## 1. Preflight

Confirm the runtime has these MCP tools before starting; if any is missing,
DM Brian one line (`eyes: cannot run, missing <tool>`) and exit.

Required:
- `Slack.slack_search_public_and_private`
- `Slack.slack_send_message`

That's it. No canvas, no Granola, no GitHub, no LLM in v0.1.

## 2. Find the messages

```yaml
tool: slack_search_public_and_private
args:
  # query mirrors the filter string; slack_search_public_and_private lists
  # `query` as a required field, so pass it in addition to the split fields.
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

Notes:
- `<YYYY-MM-DD>` is computed at runtime as `today - 7 days` in
  `America/Chicago`. Slack's `after:` operator only accepts an
  ISO date, never a natural token like `yesterday`.
- `hasmy::emoji:` is confirmed in the Slack MCP tool contract — it scopes
  to the caller's own reactions.
- `limit` max is 20, not 50. Don't ask for more; Slack will 400.
- `only_my_channels: true` prevents shared/bot-hosted false positives.
- If the search returns 0 items, DM Brian one line
  (`:eyes: nothing in the queue — inbox zero on reading debt.`) and exit.

## 3. Enrich each item — no extra API calls

Every field the digest needs is already on the search result:

| Digest field | Source in the search response |
|--------------|-------------------------------|
| permalink | `permalink` |
| channel name | `channel.name` (fallback: `channel.id`) |
| author name | `user_name` (fallback: `username` or `user`) |
| snippet | `text`, first 200 chars, `<https://…\|label>` collapsed to `label` |
| age | now − `ts` (humanize to `Xd` / `Xw`) |
| class | derived, see below |

**Class** (regex-only, no LLM):
- `pr` — text matches `github\.com/[^/]+/[^/]+/pull/\d+`
- `doc` — text matches any of `notion.so`, `confluence`, `docs.google.com`,
  `liatr.io` (regex `(notion\.so|confluence|docs\.google\.com|liatr\.io)` —
  unescaped pipes; `\|` is a literal pipe in POSIX-ish flavors and would
  never match)
- `article` — text has exactly one external URL and no Liatrio/GitHub domain
- `thread` — `reply_count >= 3`
- `msg` — everything else

No `slack_get_reactions` calls, no permalink API calls, no `slack_read_thread`.
`hasmy::eyes:` already guarantees Brian reacted; we don't need to re-verify.

## 4. Rank

Sort descending by this composite key:

1. `class in (pr, doc)` first — close-the-loop kinds
2. Age > 5 days — older = more rotten
3. Channel starts with `client-` or `project-` — work signal
4. Newest-first ties broken by `ts` desc

## 5. Compose the digest

DM Brian at `U0A0T8FV12B`. Slack markdown, no blockquotes (they hide
permalinks in previews):

```
:eyes: *Reading queue — <N> from the last 7 days* _(as of <YYYY-MM-DD HH:mm CT>)_

*Close the loop*
1. [<class>] <channel> · <author> · <age>
   "<snippet>"
   <permalink>
...

*Later*
6. ...

_v0.1 — no dedup across runs yet. Same items may reappear if you haven't cleared the reaction._
```

Split at 5: top 5 → `*Close the loop*`, rest → `*Later*`. Total cap 20 (search limit).

## 6. Guardrails

- **Never** post to any channel other than `U0A0T8FV12B`.
- **Never** add or remove reactions on any message.
- **Never** call any other MCP surface in v0.1 — if you're calling Granola,
  Gmail, or GitHub, you're in the wrong skill.
- On any Slack API error, DM Brian one line with the error code
  (`eyes: <slack_error>`), never swallow silently.
- Run duration budget: **under 5 seconds**. If it runs longer, log it and
  investigate; something is wrong.

## 7. Cost envelope

Per run:
- Slack API: 1 call (the search itself)
- LLM: 0 tokens (no LLM in v0.1)
- Total: **effectively free**

If v0.1 works and Brian wants dedup/clear/aging, that's v0.2 in
[`../ROADMAP.md`](../ROADMAP.md).

## Runbook

See [`runbook.md`](./runbook.md) for the Cursor Cloud Agent schedule config
and manual invocation.
