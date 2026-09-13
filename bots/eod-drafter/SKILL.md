---
name: eod-drafter
description: >-
  End-of-day post drafter for Brian Walsh. Pulls today's activity from GitHub,
  Slack, and Granola and stitches it into Brian's canonical EOD template
  (Today / Tomorrow split, terse bullets, PR links). Human-in-the-loop —
  always DMs Brian, never auto-posts to a channel. Model call routes through
  the AI Gateway daily driver, so every run doubles as gateway dogfooding
  evidence. Use on weekdays at 16:00 CT, when Brian says "draft my EOD", or
  when another skill needs today's activity summary. Client-domain meetings
  never leave Slack — titles are redacted and Next Steps are stripped before
  the gateway call.
version: 0.1.0
author: Brian Walsh
license: Internal
metadata:
  hermes:
    tags: [internal, delivery-principal-ops-kit, eod, ai-gateway-dogfood]
    related_skills: [eyes, follow-up-radar]
---

# EOD Auto-Drafter (v0.1)

Compresses today's cross-tool activity into the EOD post Brian writes anyway,
routes the LLM call through the AI Gateway he's dogfooding that day, and DMs
the draft. Brian edits and reposts to the target channel himself.

## v0.1 scope contract

**In scope:**
- Pull today's GitHub / Slack / Granola activity for Brian
- Redact client-domain meeting titles + strip their Next Steps before the
  gateway call
- Route the draft prompt through the AI Gateway URL in `$GATEWAY_BASE_URL`
- DM the draft to Brian (`U0A0T8FV12B`), never a channel

**Out of scope for v0.1** (defer to [`../ROADMAP.md`](../ROADMAP.md)):
- Auto-creating a `#draft-eods` channel (Slack default is public — leak risk)
- Rotation YAML across four gateways (v0.1 uses a single env var)
- `friction.jsonl` persistence (VM-ephemeral; needs a real state store)
- Friday's weekly friction summary
- `/eod-friction` reply-listener (no Slack event trigger available)

## Non-negotiables

- **Draft only.** Output goes to Brian's DM. Never posts to `#project-*`,
  `#client-*`, `#liatrio-*`, or any workstream channel directly.
- **Client-domain quarantine.** Any Granola meeting whose participants
  include `@natera.com`, `@goengen.com`, or any domain in
  `$CLIENT_DOMAINS` (env var, comma-sep, defaults `natera.com,goengen.com`):
  - Meeting title is replaced with `"Client sync (<domain>)"` in the draft
    input.
  - Meeting `Next Steps` and summary are **not sent to the gateway at all**.
  - The draft references the meeting only as a bullet like
    "Client sync — see Granola for detail" with the meeting's Granola link.
- **Gateway required.** No fallback to a direct provider API. If
  `$GATEWAY_BASE_URL` is unset or the endpoint 5xx's, DM Brian the error
  and exit. That's the point.

## 1. Preflight

Required MCP + env:
- `Slack.slack_search_public_and_private`, `Slack.slack_send_message`
- `Granola.list_meetings`, `Granola.get_meetings`
- `gh` CLI authenticated as `@BriWalsh` (Cloud Agent token OK)
- `$GATEWAY_BASE_URL` — the OpenAI-compatible endpoint of today's gateway
- `$GATEWAY_MODEL` — model name to request from that gateway
  (e.g. `claude-sonnet-5`, `gpt-5.6-medium`)
- `$GATEWAY_TASK_TYPE` — optional, defaults `eod-draft`

If any is missing, DM Brian and exit.

## 2. Window

Default: today 00:00 CT → now. Overrides via prompt:

- `"draft my EOD for friday"` → last Friday 00:00 CT → last Friday 23:59 CT
- `"draft my EOD from yesterday morning"` → yesterday 00:00 CT → now

## 3. Pull raw signals in parallel

### 3a. GitHub via `gh`

```bash
WS_START_ISO="2026-09-15T00:00:00-05:00"

gh search prs --author=@me --updated=">=${WS_START_ISO}" \
  --json url,title,state,repository,mergedAt,updatedAt,number \
  --limit 30

gh search issues --involves=@me --updated=">=${WS_START_ISO}" \
  --json url,title,state,repository,updatedAt,number \
  --limit 30

# PR reviews left today
gh api graphql -f query="$(cat <<'EOF'
{ viewer { contributionsCollection(from: "__START__") {
    pullRequestReviewContributions(first: 30) {
      nodes { pullRequest { url title number repository { nameWithOwner } } }
    }
  } } }
EOF
)"
```

Keep `repository.nameWithOwner`, `number`, `title`, `url`, `state`.

### 3b. Slack — Brian's own posts

```yaml
tool: slack_search_public_and_private
args:
  keywords: []
  filters: "from:<@U0A0T8FV12B> after:<YYYY-MM-DD>"
  natural_language_query: ""
  limit: 20
  sort: timestamp
  sort_dir: desc
  only_my_channels: true
  include_context: false
```

Drop replies that are ≤ 3 words (`ok`, `+1`, `thanks`, `same`). Keep
channel name, first 300 chars, permalink. Group by channel.

### 3c. Granola — today's meetings

```yaml
tool: list_meetings
args:
  time_range: "custom"
  custom_start: "2026-09-15"
  custom_end: "2026-09-15"
  involvement:
    listed_as_participant: true
```

Then, in batches of up to 10 UUIDs:

```yaml
tool: get_meetings
args:
  meeting_ids: [ ...up to 10... ]
```

For each meeting, extract: `title`, `known_participants`, `summary` (only if
no client-domain participants — see §client-domain quarantine below).

### 3d. Client-domain quarantine (do this before §4)

For every Granola meeting:

```
client_hit = any(
  participant.email endswith ANY(client_domains)
  for participant in meeting.known_participants
)

if client_hit:
    meeting.title = f"Client sync ({dominant_client_domain})"
    meeting.summary = None
    meeting.next_steps = None
    meeting.granola_link = meeting.granola_link   # keep, so Brian can open it
```

The quarantined meeting is included in the *input to the workstream mapper*
so the workstream cluster count is right, but its content is never sent to
the LLM.

## 4. Cluster by workstream

Map each raw signal to one of:
`ai-gateway` · `flywheel` · `forge` · `natera` · `engen` · `liatrio-internal` · `other`

Channel/repo/domain rules:

| Cluster | Match |
|---------|-------|
| ai-gateway | channel matches `#project-ai-gateway`; repos `project-ai-gateway`, `liatrio-forge/ai-gateway-*` |
| flywheel | channels `#project-marketing-dashboard*`; repos `marketing-dashboard*` |
| forge | channel `#liatrio-forge`, `#learning-cursor-fde`; repos `liatrio-forge/*`, `forge-*` |
| natera | channel `#client-natera*` **or** meeting with `@natera.com` |
| engen | channel `#client-*engen*` **or** meeting with `@goengen.com` |
| liatrio-internal | channels `#liatrio`, `#liatrio-*`, 1:1 DMs |
| other | fallback |

Drop clusters with zero signals.

## 5. Build the LLM input

Structure exactly this JSON blob and send it as the user prompt (see
[`PROMPT.md`](./PROMPT.md) for the system prompt and calibration):

```json
{
  "date": "2026-09-15",
  "window": { "start": "...", "end": "..." },
  "clusters": {
    "ai-gateway": {
      "github": [ { "repo": "...", "number": 45, "title": "...", "state": "MERGED", "url": "..." }, ... ],
      "slack": [ { "channel": "#project-ai-gateway", "text": "…", "permalink": "…" }, ... ],
      "meetings": [ { "title": "…", "granola_link": "…" }, ... ]
    },
    "natera": {
      "github": [],
      "slack": [ { "channel": "#client-natera-delivery", "text": "…", "permalink": "…" } ],
      "meetings": [ { "title": "Client sync (natera.com)", "granola_link": "…" } ]
    },
    "...": { ... }
  }
}
```

Note the `natera` cluster's `slack` entries still include text — Slack posts
Brian himself wrote don't need to leave. But **`meetings` for client
clusters carry only titles and links, never summaries or next steps.**

## 6. Call the gateway

```
POST $GATEWAY_BASE_URL/chat/completions
Headers: Authorization: Bearer $GATEWAY_API_KEY  (from Cloud Agent secret)

Body: {
  "model": $GATEWAY_MODEL,
  "messages": [
    { "role": "system", "content": <from PROMPT.md::system> },
    { "role": "user",   "content": <the JSON blob from §5, plus the emoji vocab + one real EOD example from template.md> }
  ],
  "metadata": { "task_type": $GATEWAY_TASK_TYPE, "skill": "eod-drafter" }
}
```

Timeout: 15s. On 4xx: DM Brian the error and exit. On 5xx: DM Brian
"gateway <name> is 5xx-ing — likely dogfooding data point, see logs" and
exit (no retry, no fallback).

## 7. Post-process

1. Strip any preamble ("Here's the draft:", "Sure, here you go:", etc.)
2. Verify every `<https://…|…>` link in the draft appears in the raw feed;
   drop invented ones.
3. Ensure the sign-off is exactly `*Sent using* <@U093DJ468EN|Cursor>`
   (Cursor bot user id).
4. If the draft exceeds 3000 chars, trim the oldest `Today` bullets first.

## 8. DM the draft

```yaml
tool: slack_send_message
args:
  channel_id: "U0A0T8FV12B"
  message: |
    :draft-ai-gateway: *EOD draft — <date>*

    ```
    <the draft>
    ```

    _v0.1 — auto-drafted, gateway: <gateway_name>. Edit above and repost yourself._
```

Use a code block wrapper so Slack doesn't render the draft's internal
Slack markdown until Brian copies it out.

## 9. Guardrails

- **Never** post to any channel except Brian's DM.
- **Never** call `slack_create_conversation` (v0.1 doesn't auto-create channels).
- **Never** send a Granola meeting's summary or next-steps to the gateway if
  a participant matches a client domain — this rule is load-bearing for
  privacy and cannot be softened by prompt.
- **Never** retry the gateway on a 5xx; that's the friction datum.
- Run duration budget: **under 20 seconds** including the LLM call.

## Cost envelope

Target: under $0.05/run on any gateway. Hard cap: $0.20/run — if approaching,
DM Brian and bail; that's a gateway data point in itself.

## Runbook

See [`runbook.md`](./runbook.md).
