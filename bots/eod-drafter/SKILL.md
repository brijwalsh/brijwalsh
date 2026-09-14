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
- Friday's weekly *gateway-friction* summary (different from the
  Friday fleet-review addendum in §7c, which ships in this version)
- `/eod-friction` reply-listener (no Slack event trigger available)

**Also in scope for v0.1** (added 2026-09-14 per fleet-budget change):
- Read [`../FLEET.md`](../FLEET.md) and append a `Fleet:` line to the
  daily DM (§5b + §7b).
- On Fridays, append a weekly minutes-saved rollup after the sign-off
  (§7c).

**Also in scope for v0.1** (added 2026-09-14 per human-actions-first change):
- Read [`../docs/pdp-evidence-targets.md`](../docs/pdp-evidence-targets.md)
  and surface unmet targets in the "Your 3 for tomorrow" list (§5c).
- Restructure the DM into a two-part send: parent message = human
  actions first (§7e), thread reply = full EOD shipping log (§7d).

## Non-negotiables

- **Draft only.** Output goes to Brian's DM. Never posts to `#project-*`,
  `#client-*`, `#liatrio-*`, or any workstream channel directly.
- **Client-domain quarantine (multi-signal, fail-closed).** A Granola
  meeting is quarantined if **any** of the following is true:
  1. A participant email host equals or ends in `.<client-domain>` for any
     entry in `$CLIENT_DOMAINS` (env var, comma-sep, defaults
     `natera.com,goengen.com`). Match is on host suffix with a `.`
     boundary — never substring — so `notnatera.com` never matches.
  2. Meeting title contains the client name stem (`natera`, `goengen`).
  3. Meeting sits in a client folder (`natera`, `engen`, etc.).
  4. Participants list is empty **and** no folder signal — treat as
     unknown and quarantine (fail-closed). Better to draft a stub than
     leak a client meeting body because Granola happened to return
     partial metadata.
  5. **Alias-based related-to-client signal.** Meeting `title`,
     `summary`, or Granola `notes` contains any `title_hint` from the
     client alias table, case-insensitive. Built-in defaults:
     `goengen.com` → `enGen`, `EnGen`; `natera.com` → `Natera`,
     `Panorama`, `Signatera`, `Prospera`. Extend via
     `$CLIENT_TITLE_ALIASES` (JSON object). A marketing-name title
     like `enGen Sync — Nov 2026` or an internal-only
     `Prep for enGen QBR` quarantines even when every attendee is
     `@liatr.io`. Malformed `$CLIENT_TITLE_ALIASES` is fail-closed:
     DM Brian and exit; do not run with a broken DLP table.

  Quarantined meetings are surfaced to the LLM only as
  `title=Client sync (<domain>)` + Granola link + `quarantined: true`.
  No summary, no next-steps, no participant emails ever leave Slack.
- **Client-channel Slack quarantine.** Every Slack entry whose `channel`
  starts with `#client-` — including entries Brian himself wrote — has
  its `text` stripped before the gateway call. Only `channel`,
  `permalink`, `ts`, and a char count survive. The gateway does not have
  a BAA for client channel bodies in v0.1.
- **Gateway required.** No fallback to a direct provider API. If
  `$GATEWAY_BASE_URL` or `$GATEWAY_API_KEY` is unset, or the endpoint
  5xx's, DM Brian the error and exit. That's the point.

## 1. Preflight

Required MCP + env:
- `Slack.slack_search_public_and_private`, `Slack.slack_send_message`
- `Granola.list_meetings`, `Granola.get_meetings`
- `gh` CLI authenticated as `@BriWalsh` (Cloud Agent token OK)
- `$GATEWAY_BASE_URL` — the OpenAI-compatible endpoint of today's gateway
- `$GATEWAY_API_KEY` — bearer token for that gateway
- `$GATEWAY_MODEL` — model name to request from that gateway
  (e.g. `claude-sonnet-5`, `gpt-5.6-medium`)
- `$GATEWAY_TASK_TYPE` — optional, defaults `eod-draft`
- `$CLIENT_DOMAINS` — optional, comma-sep, defaults `natera.com,goengen.com`
- `$CLIENT_TITLE_ALIASES` — optional JSON object mapping a client
  domain to extra title/summary/notes hint strings, e.g.
  `{"goengen.com": ["enGen", "EnGen"], "acme.com": ["Acme"]}`.
  Built-in defaults already cover `goengen.com` and `natera.com`
  (see Non-negotiables). If this var is **set** and is not a JSON
  object of `{domain: [str, ...]}`, DM Brian and exit — fail-closed.

If any of the required entries is missing, DM Brian and exit. Do **not**
fall through to a direct-provider API call; the gateway dependency is the
whole point.

## 2. Window

Default: today 00:00 CT → now. Overrides via prompt:

- `"draft my EOD for friday"` → last Friday 00:00 CT → last Friday 23:59 CT
- `"draft my EOD from yesterday morning"` → yesterday 00:00 CT → now

Backdated runs must be **bounded on both ends**. Pass both `$WS_START_ISO`
and `$WS_END_ISO` (in CT ISO with offset) into every GitHub/Slack/Granola
query below — no open-ended `>=` searches, otherwise Slack pulls in
messages that are newer than the target day and pollutes the draft.

## 3. Pull raw signals in parallel

### 3a. GitHub via `gh`

`gh search prs --updated` only accepts **date-only** operands (`YYYY-MM-DD`),
not full ISO timestamps. Compute the two bookends up front from
`$WS_START_EPOCH` / `$WS_END_EPOCH` (Unix seconds — whatever §2 chose for
"today 00:00 CT" and "now", or the backdated bounds):

```bash
WS_START_DATE="$(TZ=America/Chicago date -d "@$WS_START_EPOCH" +%F)"
WS_END_DATE="$(TZ=America/Chicago date -d "@$WS_END_EPOCH"   +%F)"
# ISO-8601 with the correct offset for the given tz — CDT or CST is
# picked by GNU date automatically, so we don't hard-code -05:00 vs -06:00
WS_START_ISO="$(TZ=America/Chicago date -d "@$WS_START_EPOCH" --iso-8601=seconds)"
```

Then search — `state` is enough to tell merged/open/closed apart, so we
don't ask for `mergedAt` (which `gh search prs --json` doesn't advertise
in the current schema and will 400):

```bash
gh search prs --author=@me \
  --updated="${WS_START_DATE}..${WS_END_DATE}" \
  --json url,title,state,repository,updatedAt,number \
  --limit 30

gh search issues --involves=@me \
  --updated="${WS_START_DATE}..${WS_END_DATE}" \
  --json url,title,state,repository,updatedAt,number \
  --limit 30
```

For PR reviews we need GraphQL. Use an **unquoted** heredoc so
`${WS_START_ISO}` interpolates; if you quote the `EOF` sentinel, `bash`
treats the body as literal and the API will 400 on `__START__`:

```bash
gh api graphql -f query="$(cat <<EOF
{ viewer { contributionsCollection(from: "${WS_START_ISO}") {
    pullRequestReviewContributions(first: 30) {
      nodes { pullRequest { url title number repository { nameWithOwner } } }
    }
  } } }
EOF
)"
```

Keep `repository.nameWithOwner`, `number`, `title`, `url`, `state`.

### 3b. Slack — Brian's own posts

Compute `<YYYY-MM-DD>` as `WS_START_DATE` from §3a (never pass `yesterday`
or a full ISO — Slack's `after:` operator only accepts a date).

```yaml
tool: slack_search_public_and_private
args:
  # slack_search_public_and_private lists `query` as a required field;
  # always pass it in addition to the split fields.
  query: "from:<@U0A0T8FV12B> after:<WS_START_DATE>"
  keywords: []
  filters: "from:<@U0A0T8FV12B> after:<WS_START_DATE>"
  natural_language_query: ""
  limit: 20
  sort: timestamp
  sort_dir: desc
  only_my_channels: true
  include_context: false
```

Drop replies that are ≤ 3 words (`ok`, `+1`, `thanks`, `same`). Keep
channel name, first 300 chars, permalink. Group by channel. Messages
inside `#client-*` channels are handled specially in §5 — their `text`
field is stripped before the gateway call, regardless of who posted it.

For every message that survives, clean the Slack markup per
[`../eyes/SKILL.md`](../eyes/SKILL.md) §3 snippet-cleaning rules (steps
1–7): collapse `<URL|label>`, `<@USERID|handle>`, `<#ID|name>`,
`<!channel>`, etc. before serializing into the prompt input. The LLM
doesn't need to see raw Slack IDs, and keeping them in risks the model
hallucinating about who's who or copying `<@U…>` into the draft, which
would render as an unintended @-mention when Brian pastes the draft
back into Slack.

### 3c. Granola — today's meetings

`list_meetings` returns meetings where the caller is either the
transcript-owner (`captured_by_me: true`) **or** was invited
(`listed_as_participant: true`). Both flags need to be `true` so we don't
miss the meetings Brian was on but didn't record himself:

```yaml
tool: list_meetings
args:
  time_range: "custom"
  custom_start: "<WS_START_DATE>"
  custom_end: "<WS_END_DATE>"
  involvement:
    captured_by_me: true
    listed_as_participant: true
```

Then, in batches of up to 10 UUIDs (`get_meetings` has a hard cap of 10
IDs per call — larger batches error out, they don't silently truncate):

```yaml
tool: get_meetings
args:
  meeting_ids: [ ...up to 10... ]
```

For each meeting, extract: `title`, `known_participants` (each with
`email` and `name`), `summary`, `notes` (Granola text output),
`next_steps`, `granola_link`. `notes` is a §3d quarantine signal only
and is never forwarded to §5. `summary` and `next_steps` are only
forwarded to §5 if the meeting **survives** the quarantine in §3d.

### 3d. Client-domain quarantine (do this before §4)

Quarantine is **multi-signal, fail-closed**. Any positive signal is
enough to trigger it (attendee-domain, title-stem, folder, unknown
attendance, **or** a title-alias hit in title/summary/notes). The
empty-participants case triggers it too, so Granola outages can never
regress to leaking full meeting bodies.

For every Granola meeting:

```python
import json

client_domains = os.environ.get("CLIENT_DOMAINS",
                                "natera.com,goengen.com").split(",")

# Built-in marketing-name / product-name hints. Domain-stem title
# matching ("natera", "goengen") stays in title_hit below; this table
# is the extra aliases those stems miss (enGen ≠ goengen).
DEFAULT_TITLE_ALIASES = {
    "goengen.com": ["enGen", "EnGen"],
    "natera.com": ["Natera", "Panorama", "Signatera", "Prospera"],
}

def load_title_aliases():
    table = {d.lower(): list(hints)
             for d, hints in DEFAULT_TITLE_ALIASES.items()}
    raw = (os.environ.get("CLIENT_TITLE_ALIASES") or "").strip()
    if not raw:
        return table
    try:
        extra = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise SystemExit(
            "CLIENT_TITLE_ALIASES is not valid JSON — DM Brian and exit"
        )
    if not isinstance(extra, dict) or not all(
        isinstance(k, str)
        and isinstance(v, list)
        and all(isinstance(h, str) for h in v)
        for k, v in extra.items()
    ):
        raise SystemExit(
            "CLIENT_TITLE_ALIASES must be "
            '{"domain.com": ["Alias", ...]} — DM Brian and exit'
        )
    for domain, hints in extra.items():
        key = domain.lower()
        table.setdefault(key, [])
        table[key].extend(hints)
    return table

title_aliases = load_title_aliases()

def host(email):
    # split on the last @ so "foo@bar@natera.com" still lands on natera.com
    return email.rsplit("@", 1)[-1].lower().strip()

def domain_hit(email):
    h = host(email)
    # exact host or subdomain of a client domain — never substring, so
    # "notnatera.com" and "goengen.com.attacker.tld" do not match
    return any(h == d or h.endswith("." + d) for d in client_domains)

participants = meeting.get("known_participants") or []
participant_hit = any(domain_hit(p.get("email", "")) for p in participants)

title_hit = any(
    d.split(".")[0] in meeting.title.lower()
    for d in client_domains
)   # "natera", "goengen"

folder_hit = (meeting.folder or "").lower() in {
    "natera", "engen", "client-natera", "client-engen", "clients",
}

# fail-closed: no participants + no folder = we don't know, so we quarantine
unknown_attendance = not participants and not folder_hit

# fourth signal: any title_hint from the alias table, case-insensitive,
# in title OR summary OR Granola notes. Catches "enGen Sync — Nov 2026"
# and internal-only "Prep for enGen QBR" (zero client attendees).
haystack = " ".join([
    meeting.title or "",
    meeting.summary or "",
    meeting.get("notes") or "",
]).lower()
alias_hit = any(
    hint.lower() in haystack
    for hints in title_aliases.values()
    for hint in hints
)

client_hit = (
    participant_hit or title_hit or folder_hit
    or unknown_attendance or alias_hit
)

if client_hit:
    # dominant domain: pick the client domain that matched, else "unknown"
    dominant = next(
        (d for d in client_domains
         if any(domain_hit(p.get("email", "")) and host(p["email"]).endswith(d)
                for p in participants)
         or d.split(".")[0] in meeting.title.lower()
         or any(hint.lower() in haystack
                for hint in title_aliases.get(d.lower(), []))),
        "unknown",
    )
    meeting.title = f"Client sync ({dominant})"
    meeting.summary = None
    meeting.next_steps = None
    meeting.participants_public = []   # do NOT forward the email list
    # granola_link stays so Brian can open the source himself
    meeting.quarantined = True
```

The quarantined meeting is included in the *input to the workstream mapper*
so the workstream cluster count is right, but its content is never sent
to the LLM. If quarantine is ever bypassed by a code change, the skill
must fail closed: no meeting body, no next-steps, no participants.

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

Before serializing, walk the `natera` and `engen` clusters (any cluster
mapped to a client-hit channel in §4, plus any workstream whose channel
name matches `#client-*`) and **drop the `text` field** from every Slack
entry. Keep only `channel`, `permalink`, `ts`, and an optional
count-only `chars` for calibration. Slack posts inside a client channel —
including posts Brian himself wrote there — routinely quote the client
back, and the gateway does not have a BAA for that content in v0.1.

Structure exactly this JSON blob and send it as the user prompt (see
[`PROMPT.md`](./PROMPT.md) for the system prompt and calibration):

```json
{
  "date": "2026-09-15",
  "window": { "start": "...", "end": "..." },
  "clusters": {
    "ai-gateway": {
      "github": [ { "repo": "...", "number": 45, "title": "...", "state": "MERGED", "url": "..." } ],
      "slack": [ { "channel": "#project-ai-gateway", "text": "…", "permalink": "…" } ],
      "meetings": [ { "title": "…", "granola_link": "…" } ]
    },
    "natera": {
      "github": [],
      "slack": [ { "channel": "#client-natera-delivery", "permalink": "…", "ts": "…", "chars": 214 } ],
      "meetings": [ { "title": "Client sync (natera.com)", "granola_link": "…", "quarantined": true } ]
    }
  }
}
```

Rules the serializer must enforce, in order:

1. Any Slack entry whose `channel` starts with `#client-` → drop `text`.
2. Any Slack entry inside the `natera` or `engen` cluster → drop `text`.
3. Any `meeting` with `quarantined: true` → carry only `title` +
   `granola_link` + `quarantined: true`.
4. Any `known_participants` list on a quarantined meeting → replaced
   with `[]` (do not forward emails).

If any of those rules would need to be relaxed for a specific draft,
that's a v0.2 discussion, not a runtime override.

Append the surfaced PDP evidence targets from §5c to the same user
prompt (see [`PROMPT.md`](./PROMPT.md) for the envelope shape). They
are trusted input (not third-party text), so no quarantine — but they
still sit inside `<pdp_evidence_targets>` tags for prompt-injection
uniformity.

## 5b. Fleet snapshot (mechanical, no LLM)

Read [`../FLEET.md`](../FLEET.md) and compute the fleet snapshot the
draft will report. This runs in parallel with §6 — the numbers are
mechanical facts, not LLM output.

```python
from datetime import date
from zoneinfo import ZoneInfo

FLEET_PATH = os.path.join(os.path.dirname(__file__), "..", "FLEET.md")
CT = ZoneInfo("America/Chicago")

def parse_fleet(path):
    # Find the H2 "## Brian-owned skills — budget applies", take the
    # first pipe-table below it. Column names are the source of truth,
    # not column indices; if a column is renamed we log and skip.
    #
    # Returns: {"active": int, "shipped_this_week": int,
    #           "retired_this_week": int, "cap": int,
    #           "active_rows": [row, ...]}
    ...

def parse_retired(path):
    # Same file, H2 "## Retired", first table. Rows with a "Retired"
    # date in this ISO week (America/Chicago) count.
    ...

def current_iso_week(now_ct):
    # ISO year+week. Monday 00:00 CT → Sunday 23:59 CT.
    return now_ct.isocalendar()[:2]

try:
    fleet = parse_fleet(FLEET_PATH)
    retired = parse_retired(FLEET_PATH)
except (FileNotFoundError, ValueError) as exc:
    # Non-fatal: log and skip the fleet line. EOD still ships.
    fleet = None
    log(f"fleet snapshot skipped: {exc}")
```

**Cap of 3** is hard-coded here for v0.1 to match `FLEET.md`. If the
file starts declaring a `cap:` on its own (v0.2), read it from there.

**Warning conditions** — any of these flip `fleet.warn = True`, which
turns the Fleet line into a warning marker in §7b:

- `fleet.active > fleet.cap`
- `fleet.shipped_this_week > 1`
- `fleet.shipped_this_week > 0 and fleet.retired_this_week == 0`

If the fleet parser threw and `fleet is None`, the line is omitted
entirely rather than faked. The point of the line is honest
visibility.

## 5c. PDP evidence targets (mechanical, no LLM)

Read [`../docs/pdp-evidence-targets.md`](../docs/pdp-evidence-targets.md)
and pick the targets that should influence tomorrow's plan. Runs in
parallel with §5b — no LLM, no gateway call, pure file parse.

```python
PDP_PATH = os.path.join(os.path.dirname(__file__),
                        "..", "docs", "pdp-evidence-targets.md")

def parse_pdp(path):
    # Find H2 "## Active targets", take the first pipe-table below it.
    # Columns: ID | Target | Category | Due | Status | Evidence source | Notes
    # Returns list[dict], or [] if file/table missing (non-fatal).
    ...

def surface_targets(rows, now_ct):
    today = now_ct.date()
    horizon = today + timedelta(days=7)
    def keep(r):
        return (
            r["Status"].lower() in {"pending", "in-progress", "blocked"}
            and date.fromisoformat(r["Due"]) <= horizon
        )
    hits = [r for r in rows if keep(r)]
    # overdue first, then earliest Due, then ID ascending
    def sort_key(r):
        d = date.fromisoformat(r["Due"])
        return (d >= today, d, r["ID"])
    return sorted(hits, key=sort_key)[:5]

try:
    pdp_rows = parse_pdp(PDP_PATH)
    pdp_surfaced = surface_targets(pdp_rows, now_ct)
except (FileNotFoundError, ValueError) as exc:
    log(f"pdp targets skipped: {exc}")
    pdp_rows = []
    pdp_surfaced = []
```

`pdp_surfaced` is fed into two places downstream:

1. §5 — added as a fourth XML envelope in the user prompt so the
   LLM can factor targets into the Tomorrow bullets and the
   TOP_3_HUMAN_ACTIONS list.
2. §7e — mechanically joined with the LLM's TOP_3 output so
   overdue targets can't be silently dropped by the model. The
   skill has the final say on which 3 land in the parent DM.

## 6. Call the gateway

If §4 dropped every cluster (zero GitHub, Slack, or Granola signals in
the window), skip this section and §7. Go to §8 clean-run. An empty
day is not a reason to call the gateway.

```
POST $GATEWAY_BASE_URL/chat/completions
Headers: Authorization: Bearer $GATEWAY_API_KEY  (from Cloud Agent secret)

Body: {
  "model": $GATEWAY_MODEL,
  "messages": [
    { "role": "system", "content": <from PROMPT.md::system> },
    { "role": "user",   "content": <the JSON blob from §5, plus the emoji vocab + one real EOD example from template.md> }
  ],
  "metadata": {
    "task_type": $GATEWAY_TASK_TYPE,
    "skill": "eod-drafter",
    "user": "brian.walsh@liatr.io",
    "run_source": "cursor-cloud-agent"
  }
}
```

`metadata.user` is required so the dogfooding dashboards can attribute the
call. Gateways strip it before forwarding to the upstream provider.

Timeout: 15s. On 4xx: DM Brian the error and exit. On 5xx: DM Brian
"gateway <name> is 5xx-ing — likely dogfooding data point, see logs" and
exit (no retry, no fallback).

## 7a. Post-process the LLM draft

1. Strip any preamble ("Here's the draft:", "Sure, here you go:", etc.)
2. Verify every link in the draft appears in the raw feed. Slack-style
   links are `<URL|label>` — parse the `URL` out first, before comparing.
   Do **not** substring-match on the whole `<URL|label>` token or you'll
   both false-negative real links (label mismatch) and false-positive
   invented ones (label matches feed text). Drop invented links entirely
   rather than trying to repair them.
3. Ensure the sign-off is exactly `*Sent using* <@U093DJ468EN|Cursor>`
   (Cursor bot user id).
4. If the draft exceeds 3000 chars, trim the oldest `Today` bullets first.
5. Drop any line the LLM emitted that starts with `:file_cabinet: Fleet:`,
   `:calendar: Weekly review`, or "Minutes saved" — those are §7b/§7c
   territory and must not come from the model.

## 7b. Append the fleet-count line

Immediately before the sign-off in §7a rule 3, insert the fleet line
built from the §5b snapshot. Format (Slack-flavored markdown):

```
:file_cabinet: Fleet: {active}/{cap} active, {shipped_this_week} shipped this week, {retired_this_week} retired.
```

If `fleet.warn` is set, prefix `:warning: ` and append the reason:

```
:warning: :file_cabinet: Fleet: 4/3 active, 1 shipped this week, 0 retired — over cap. Retire something in FLEET.md.
```

If §5b failed (`fleet is None`), omit the line entirely. Do not fake it.

## 7c. Friday variant — weekly minutes-saved rollup

If the current day in `America/Chicago` is Friday, append a weekly
review addendum **after** the sign-off (so it survives the "trim to
3000 chars" rule in §7a — Brian only trims the Today bullets, not the
review). Content pulled mechanically from `FLEET.md`, not the LLM:

```
:calendar: Weekly review — fleet minutes saved

| Skill | Verdict | Min saved/week (est.) |
|-------|---------|-----------------------|
| eyes | kept | ~60 |
| eod-drafter | kept | ~120 |
| follow-up-radar | kept | ~30 |
Total: ~210 min/week. Retired this week: 0. Shipped this week: 0.
```

Numbers are the sum of column 6 across active rows in the Brian-owned
table plus the corresponding rows in the [Retired](../FLEET.md#retired)
table with retirement dates in this ISO week. If `FLEET.md` was
unreadable (§5b failed), skip the addendum entirely — do not send a
partial or fabricated one.

Non-Friday days: no addendum. This section fires exactly once a week.

## 7d. Assemble the thread-reply body (full shipping log)

The full EOD draft — Today / Tomorrow / fleet line / optional Friday
review — is the **thread reply**, not the parent DM. Body:

```
<LLM draft, TOP_3 section split off in §7e, with fleet line inserted per §7b>
<if Friday: blank line + §7c weekly review block>
```

Never let the LLM produce the fleet line or the weekly review — they
are trusted, mechanical, computed here. This is the whole reason
they exist.

## 7e. Compose the parent DM (human actions first)

Fable 5.1's rule: the daily DM leads with the three human actions
Brian needs to take, not the shipping log. The DM has two parts:

- **Parent** = "Your 3 for tomorrow" list.
- **Thread reply** = §7d full shipping log.

### Extracting TOP_3 from the LLM output

The LLM was instructed (see [`PROMPT.md`](./PROMPT.md)) to emit two
sections separated by an exact literal marker `---TOP_3_HUMAN_ACTIONS---`.
Split on the first occurrence of that marker:

```python
DRAFT_END_MARKER = "---TOP_3_HUMAN_ACTIONS---"

def split_output(llm_text):
    if DRAFT_END_MARKER in llm_text:
        draft, top3 = llm_text.split(DRAFT_END_MARKER, 1)
        return draft.strip(), top3.strip()
    return llm_text.strip(), ""

full_draft_body, llm_top3_raw = split_output(llm_output)
```

The `full_draft_body` flows into §7a → §7b → §7d as before. The
`llm_top3_raw` is a list of ~3 bullets, one per line.

### Merging LLM output with PDP targets

Overdue and due-tomorrow PDP targets from §5c always take priority
over LLM-selected bullets. Dedup is fingerprint-based (lowercased
alnum-only) so a PDP line and its LLM twin — same target, different
formatting — collapse to one entry. Full test coverage in
[`tests/test_top3_split.py`](./tests/test_top3_split.py):

```python
def normalize(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def target_of(line):
    line = re.sub(r"^:warning:\s*", "", line)
    return re.sub(r"\s*\(due \d{4}-\d{2}-\d{2}, evidence:.*\)\s*$",
                  "", line).strip()

def already_present(candidate, existing):
    cand = normalize(target_of(candidate))
    if not cand: return True
    for line in existing:
        cur = normalize(target_of(line))
        if cand == cur: return True
        if len(cand) >= 20 and cand in cur: return True
        if len(cur) >= 20 and cur in cand: return True
    return False

def to_action_line(t):
    prefix = ":warning: " if date.fromisoformat(t["Due"]) < today else ""
    return f"{prefix}{t['Target']} (due {t['Due']}, evidence: {t['Evidence source']})"

overdue  = [t for t in pdp_surfaced
            if date.fromisoformat(t["Due"]) < today]
due_soon = [t for t in pdp_surfaced
            if today <= date.fromisoformat(t["Due"]) <= today + timedelta(days=1)]
later    = [t for t in pdp_surfaced
            if date.fromisoformat(t["Due"]) > today + timedelta(days=1)]

llm_bullets = [re.sub(r"^[0-9]+[.)]\s*|^[-•*]\s*", "", ln.strip())
               for ln in llm_top3_raw.splitlines() if ln.strip()]

top3 = []
for t in overdue + due_soon:
    if len(top3) >= 3: break
    line = to_action_line(t)
    if not already_present(line, top3): top3.append(line)
for b in llm_bullets:
    if len(top3) >= 3: break
    if not already_present(b, top3): top3.append(b)
for t in later:
    if len(top3) >= 3: break
    line = to_action_line(t)
    if not already_present(line, top3): top3.append(line)
```

If `len(top3) == 0` (clean run with no PDP targets, no LLM
suggestions), the parent DM says exactly:

```
:bullseye: Your 3 for tomorrow
_No open targets and no Tomorrow bullets — pick your own top 3. Full draft in thread if there is one._
```

### Parent DM format

```
:bullseye: *Your 3 for tomorrow — <date>*

1. <top3[0]>
2. <top3[1]>
3. <top3[2]>

_Full EOD draft in thread — copy from there to repost._
```

If `len(top3) < 3`, emit only the numbered lines that exist; do not
pad with placeholder bullets. The point is signal, not shape.

## 8. DM the draft

If invoked with `--dry-run`, skip sending. Log the draft (or the
clean-run line below) to stdout or the Cursor Cloud Agent transcript.
`--dry-run` must never call `slack_send_message`. All other guardrails
still apply (client quarantine, gateway required, no direct-provider
fallback).

**Clean run.** If every cluster was empty after §4, there is no draft
and §6 was skipped. Do **not** call the gateway to confirm an empty
day. But the DM still ships — because PDP evidence targets can be
overdue on a day with zero cross-tool activity, and Fable's whole
point is that human actions come first.

If §5c surfaced any targets, the clean-run parent DM is:

```
:bullseye: *Your 3 for tomorrow — <date>*

1. <target 1>
2. <target 2>
3. <target 3>

_No shipping activity today._
```

If §5c also came up empty, one heartbeat line is enough:

```
:draft-ai-gateway: no EOD-worthy activity today, HH:MM CT. Skipping the draft. No open PDP targets.
```

Preflight failures (missing secret, MCP unavailable, gateway 5xx) still
use the existing "DM Brian and exit" path.

**Normal path** — send two messages:

**Step 1: Parent DM** (§7e human-actions-first summary):

```yaml
tool: slack_send_message
args:
  channel_id: "U0A0T8FV12B"
  message: |
    :bullseye: *Your 3 for tomorrow — <date>*

    1. <top3[0]>
    2. <top3[1]>
    3. <top3[2]>

    _Full EOD draft in thread — copy from there to repost._
```

Capture the returned `ts` from `slack_send_message`. Slack's MCP
returns it as `message.ts` or the top-level `ts` depending on
transport; grab whichever is present.

**Step 2: Thread reply** (§7d full shipping log):

```yaml
tool: slack_send_message
args:
  channel_id: "U0A0T8FV12B"
  thread_ts: "<ts from step 1>"
  message: |
    :draft-ai-gateway: *EOD draft — <date>*

    ```
    <the §7d assembled body — LLM draft + fleet line + optional Friday review>
    ```

    _v0.1 — auto-drafted, gateway: <gateway_name>. Edit the code block above and repost yourself._
```

Use a code block wrapper so Slack doesn't render the draft's internal
markdown until Brian copies it out. The fleet line and Friday review
live inside the same code block so they travel with the draft into
whatever channel Brian reposts to.

If step 2 fails (Slack transient), the parent DM already landed and
Brian has the top-3 — safe to log and exit rather than retry both.
The gateway call already happened; retrying it would double-count in
dogfooding data.

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
