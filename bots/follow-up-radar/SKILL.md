---
name: follow-up-radar
description: >-
  Delivery Follow-up Radar for Brian Walsh. v0.1 scans yesterday's Slack
  activity in *internal* Liatrio channels only (no client channels, no
  Gmail) for commitment patterns Brian made or is owed, and DMs him a
  digest with draft follow-up language. Draft only, never sends. Client
  channels and Gmail are v0.2 material and require a DLP/BAA layer first.
  Use on the daily 08:00 CT schedule or when Brian says "what am I about
  to drop?".
version: 0.1.0
author: Brian Walsh
license: Internal
metadata:
  hermes:
    tags: [internal, delivery-principal-ops-kit, commitments, delivery]
    related_skills: [eyes, eod-drafter]
---

# Delivery Follow-up Radar (v0.1)

Brian makes and receives dozens of commitments a day across internal
Liatrio channels. Some slip. This skill surfaces the ones aging past
their sell-by date, drafts the follow-up he'd write anyway, and lets him
decide whether to send.

## v0.1 scope contract

**In scope:**
- Watched internal channels only (list below, all Liatrio-internal)
- Regex-first candidate extraction, then a single classifier call per
  candidate to reduce false positives
- Draft language for Brian's-side follow-ups only
- DM digest to Brian at `U0A0T8FV12B`

**Out of scope for v0.1** (defer to [`../ROADMAP.md`](../ROADMAP.md)):
- **Client channels** (`#client-natera*`, `#client-*engen*`) — client
  message bodies must not leave Slack MCP into any gateway until Liatrio
  has (a) a real DLP layer, (b) verified BAAs with every gateway on the
  rotation. Both are v0.2 gates.
- **Gmail** — same concern; client email bodies are the tightest data type
  in play. Deferred until the DLP gate above.
- **Granola cross-check** — meetings often carry client-adjacent content;
  same gate.
- **`send <n>` / `clear <n>` listeners** — no Slack `message.im` webhook.
- **Aging state across runs** — needs a durable store, deferred.

## Non-negotiables

- **Never** send Slack message bodies from channels starting with
  `#client-` to any gateway. Not with prompt scrubbing, not with
  "just this once." This is a hard rule enforced in `§3` below.
- **Draft only.** The digest is a DM to `U0A0T8FV12B`. Never posts, replies,
  emails, or otherwise acts as Brian.
- **No delete/edit** operations on any source. Slack read is `search` +
  `read_thread` only.

## 1. Preflight

Required:
- `Slack.slack_search_public_and_private`, `Slack.slack_read_thread`,
  `Slack.slack_send_message`
- `$GATEWAY_BASE_URL`, `$GATEWAY_API_KEY`, `$GATEWAY_MODEL`
- `$GATEWAY_TASK_TYPE` — optional, defaults `commitment-radar`

If any of the required entries is missing, DM Brian and exit. Do **not**
fall through to a direct-provider API call.

## 2. Watched channel list (hardcoded IDs)

v0.1 uses explicit channel IDs — no globs, no name lookups. Add/remove
channels only by editing this file.

```yaml
watched_internal_channels:
  - id: C0BT5J2EX32   # #project-ai-gateway
    name: project-ai-gateway
  - id: C0BML862K61   # #project-marketing-dashboard
    name: project-marketing-dashboard
  - id: C0AE9CLD7CH   # #liatrio-forge
    name: liatrio-forge
  - id: C0AUW8BSW1X   # #product-liatrio-lens  (verify id before enabling)
    name: product-liatrio-lens
  - id: C2S6MBNJH     # #liatrio
    name: liatrio

# Explicitly excluded (v0.1 hard-block):
excluded_prefixes:
  - "#client-"       # any Natera, enGen, or other client channel
```

Any accidental inclusion of a `#client-` channel is caught by the
guardrail in `§3` regardless of what this file says. Defense in depth.

## 3. Pull raw signals — internal channels only

The ranking in §6 uses `age_days >= 5` and `>= 3` gates, so the search
window has to cover at least that. v0.1 pulls the **last 7 days** per
channel; that's the smallest window where the aging buckets can ever be
populated. `<AFTER_DATE>` is computed at runtime as
`today - 7 days` in `America/Chicago` and formatted as `YYYY-MM-DD` —
Slack's `after:` operator only accepts an ISO date, never `yesterday`.

Also, before running the search, apply the excluded-prefixes filter from
§2: if a channel's name starts with any string in `excluded_prefixes`,
skip it entirely — don't just rely on the post-search guardrail. This
wires §2's exclusion list into the actual search loop instead of leaving
it as decoration.

For each watched channel ID that survives the exclusion filter, one
search:

```yaml
tool: slack_search_public_and_private
args:
  # slack_search_public_and_private lists `query` as a required field.
  query: "in:<#CHANNEL_ID> after:<AFTER_DATE>"
  keywords: []
  filters: "in:<#CHANNEL_ID> after:<AFTER_DATE>"
  natural_language_query: ""
  limit: 20
  sort: timestamp
  sort_dir: desc
  only_my_channels: true
  include_context: true
  max_context_length: 400
```

**Hard guardrail** (executed before the LLM call, defense in depth on top
of the §2 filter): for every message in the result set, if
`channel.name` starts with `client-`, drop it and increment a counter.
If the counter is non-zero at the end of the run, DM Brian a one-liner:

```
:warning: radar: <N> messages from client channels were included in
watched search results and dropped by the guardrail. Update
`follow-up-radar/SKILL.md §2` if this is unexpected.
```

Then filter to messages that either:
- Brian sent (`user == "U0A0T8FV12B"`), **or**
- mention Brian (`<@U0A0T8FV12B>` appears in the message or a nearby
  thread reply).

For every surviving message, compute `age_days` **in the skill**, not
the LLM: `age_days = floor((now_ct - message_ts_ct) / 86400)`. The
classifier never sees `age_days`, and never gets asked to reason about
dates.

## 4. Regex prefilter (before any LLM call)

Only messages matching one of these patterns proceed to classification:

| Pattern | Rough meaning |
|---------|--------------|
| `\b(I'll|I will|let me)\b` | Brian promises action |
| `\b(we'll|we will|we are going to|we're going to)\b` | Group commitment (`we'll` — with an apostrophe — not `\bwe'?ll\b`, which would also fire on "well") |
| `\b(by\|before)\s+(EOD\|EOW\|Fri\|Mon\|tomorrow\|today\|Monday\|Friday\|\d{4}-\d{2}-\d{2})\b` | Deadline |
| `\bcircl(e\|ing) back\b`, `\bfollow(-\|\s)?up\b` | Loop-closing intent |
| `\bwaiting (on\|for)\b`, `\bblocked (on\|by)\b` | Brian is owed |
| `\bdecid(e\|ing\|ed)\b` in a promise context | Decision commitment |

The pipes above are shown escaped (`\|`) only because they sit inside a
Markdown table cell; **at runtime the skill uses unescaped `|` as the
regex alternation operator**. If the skill ever runs these patterns
verbatim as written in the table, alternation breaks silently.

If no candidates, DM Brian a one-liner and exit.

## 5. Classify each candidate

Batch candidates in groups of up to **5 per gateway call** using the
classifier prompt in [`PROMPT.md`](./PROMPT.md); a 20-item working set is
then at most 4 gateway calls. The classifier prompt uses strict data
fencing so the input Slack text is never treated as instructions (see
[`PROMPT.md`](./PROMPT.md) for the exact system prompt).

The classifier returns **one JSON object per candidate** with this
schema — `age_days` is intentionally **not** in the schema, the skill
computes it in §3:

```json
{
  "source_channel": "project-ai-gateway",
  "source_id": "C0BT5J2EX32:1789166553.113029",
  "permalink": "https://liatrio.slack.com/…",
  "commitment_text": "verbatim quote",
  "commitment_type":
    "brian_promised_to_send" |
    "brian_promised_to_check" |
    "brian_promised_to_decide" |
    "brian_waiting_on_someone" |
    "external_promised_to_brian",
  "owner": "brian" | "<name>" | "unknown",
  "deadline": "2026-09-16" | "today" | "this_week" | "no_deadline",
  "confidence": 0.0 - 1.0
}
```

After the call, the skill splices the pre-computed `age_days` back onto
each item by matching on `source_id`. Drop items with `confidence < 0.7`.
Cap the working set at 20 candidates per run.

Before sending each candidate's `context` and `focus` to the classifier,
clean the Slack markup per the rules in
[`../eyes/SKILL.md`](../eyes/SKILL.md) §3 (steps 1–7 of the snippet
cleaning table): collapse `<URL|label>`, `<@USERID|handle>`, `<#ID|name>`,
`<!channel>`, and subteam mentions. Feeding the LLM raw Slack IDs
degrades classification and risks the LLM hallucinating about who's who.

## 6. Rank

Sort descending:

1. `owner == brian` **and** `deadline == today` or overdue — top
2. `owner == brian` **and** `age_days >= 5` — aging
3. `external_promised_to_brian` **and** `age_days >= 3` — nudge candidates
4. Recency ties broken by newest-first

Cap the digest at 10 items.

## 7. Draft follow-up language

For each `owner == brian` item, one small gateway call for a
Brian-voice one-liner using the `draft_apology` variant in
[`PROMPT.md`](./PROMPT.md). For `external_promised_to_brian`, use the
`draft_nudge` variant — it's a *different* prompt, tuned for polite
pressure rather than apology; do not reuse the apology prompt.

If the run was invoked with `--dry-run`, skip §7 and §8 entirely — the
skill exits after logging the digest it would have sent. `--dry-run`
must never call `slack_send_message`.

## 8. Compose the digest

Before rendering `commitment_text` into the digest, clean the Slack
markup per [`../eyes/SKILL.md`](../eyes/SKILL.md) §3 snippet-cleaning
rules. Otherwise `<@USERID>` mentions in the quoted text render as
clickable @-links when Brian scrolls the DM. `<channel>` uses the same
channel-rendering rules from §3 (public/private/`DM w/`/`Group DM w/`).

DM Brian at `U0A0T8FV12B`:

```
:radar: *Follow-up radar — <N> items* _(as of <YYYY-MM-DD HH:mm CT>)_

*You owe (today / overdue)*
1. <channel> · <age>
   "<commitment_text>"
   Draft: "<one-line follow-up>"
   Source: <permalink>
...

*Aging (5d+, still open)*
4. ...

*They owe you (nudge?)*
7. ...

_v0.1 — internal channels only. Client channels + Gmail unlock in v0.2 after DLP._
_No dedup across runs yet. Items may repeat if you haven't acted on them._
```

## 9. Guardrails (in addition to §3)

- **Never** post to any channel except Brian's DM.
- **Never** send Slack messages, emails, or any external comms on Brian's
  behalf. All drafts are copy-paste-only.
- **Never** call any Gmail or Granola tool from this skill in v0.1.
- **Client channel bypass check**: at run end, verify no message with
  `channel.name.startswith("client-")` reached the classifier step. If any
  did (indicating the guardrail in §3 was bypassed), abort the DM and log
  a critical warning to stderr.
- Run duration budget: **under 30 seconds**.

## Cost envelope

Per run:
- Slack API: ~5 calls (one per watched channel)
- LLM classifier: up to 20 candidates × ~1500 in / 300 out — target
  under $0.10/run on the gateway
- LLM draft: up to 10 items × ~500 in / 60 out — under $0.03
- Total target: **under $0.15/run**, hard cap $0.40 (bail + DM)

## Runbook

See [`runbook.md`](./runbook.md).
