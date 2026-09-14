# eod-drafter mock-gateway test harness

v0.1 shipped with no test coverage for `eod-drafter` because the excuse
was "the LLM output is non-deterministic." That's still true for the
drafted EOD text itself, but everything upstream of the gateway call is
plain data transformation and is fully testable behind fixtures — no
network, no LLM, no real gateway.

This harness never calls a real gateway. The four scripts below only
exercise the deterministic steps in `../SKILL.md`: clustering,
multi-signal quarantine, meeting→client mapping, and redaction of
client-domain meeting bodies before they would reach the gateway.
`fixtures/mock_gateway_response.json` is a canned Anthropic-shape
response kept here for a future harness that stubs the actual `§6`
gateway call (v0.3+); none of the four tests below invoke it.

**All fixtures use FAKE names and emails** (`alice@natera.com`,
`bob@goengen.com`, `charlie@liatrio.com`, etc.). No real client
employees, no real meeting content, no real Slack/GitHub data.

## How to run

From the repo root:

```bash
bash bots/eod-drafter/tests/test_clustering.sh
bash bots/eod-drafter/tests/test_quarantine.sh
bash bots/eod-drafter/tests/test_client_mapping.sh
bash bots/eod-drafter/tests/test_redaction.sh
```

Bash + `jq` (fixture sanity checks) + Python 3 stdlib only. No `pip
install`, no `npm install`. Each script exits 0 on success and prints a
`N passed / N failed` line; exit 1 and a list of failing fixture ids on
mismatch.

`quarantine_lib.py` holds the shared quarantine/mapping/redaction logic,
transcribed line-for-line from `SKILL.md` §"3d. Client-domain
quarantine". It is not an independent reimplementation — it's the test
harness's copy of that spec, and it's meant to break loudly if
`SKILL.md`'s algorithm ever changes underneath it.

## What each test covers

### `test_clustering.sh` / `test_clustering.py`

Given `fixtures/gh_activity.json` (6 PRs + 3 PR reviews across 3 repos:
`project-ai-gateway`, `project-marketing-dashboard`, `brwalsh`) and
`fixtures/slack_activity.json` (9 messages across 4 channels:
`#project-ai-gateway`, `#project-marketing-dashboard`,
`#liatrio-delivery`, `#client-natera-delivery`):

- PRs + reviews cluster by short repo name (last path segment of
  `repository.nameWithOwner`)
- Slack messages cluster by exact channel, each tagged with a category
  derived from the channel-name prefix (`project` / `client` / `other`)
- A repo (`project-forge-migration`) and a channel (`#liatrio-forge`)
  with zero activity in the window are both declared up front in
  `known_repos` / `known_channels` and confirmed dropped from the output
- Expected output: `fixtures/expected_clusters.json`

The `#client-natera-delivery` channel is included specifically to prove
its cluster is still identified and counted correctly — per `SKILL.md`
§5 rule 1, its message *text* gets stripped before the gateway call, but
the cluster itself (and its char/message count) survives.

### `test_quarantine.sh` / `test_quarantine.py`

Given `fixtures/granola_meetings.json` (8 meetings), verifies each
meeting's quarantine verdict against `SKILL.md`'s literal 5-signal,
fail-closed algorithm (post-PR #10):

| Meeting | Signal | Verdict |
|---|---|---|
| `gr-1001` | client-domain participant (`alice@natera.com`) | quarantined |
| `gr-1002` | client-domain participant who happens to be the host (`dave@natera.com`) | quarantined |
| `gr-1003` | all-internal, summary/next_steps mention `contact@natera.com` | quarantined via `alias_hit` (built-in `natera` alias matches `natera.com` substring in summary) |
| `gr-1004` | all-internal, title `enGen QBR` | quarantined via `alias_hit` (built-in `enGen` alias for `goengen.com`) |
| `gr-1005` | all-internal, no client signal anywhere | not quarantined (clean-run control) |
| `gr-1006` | malformed: `known_participants` key missing entirely | quarantined (fail-closed) |
| `gr-1007` | client-domain participant + client folder (`folder: "engen"`) | quarantined (double-hit) |
| `gr-1008` | participants span both client domains | quarantined (ambiguous) |

Expected output: `fixtures/expected_quarantine.json`, with a
`justification` string per row.

### `test_client_mapping.sh` / `test_client_mapping.py`

Given `fixtures/granola_meetings.json` and the pinned
`fixtures/client_domains.env` (`CLIENT_DOMAINS=natera.com,goengen.com`),
maps each meeting to a client key based **only** on
`known_participants` email domains (narrower than quarantine
eligibility — a meeting can be quarantined by title/summary/notes
scanning yet still map to `none` here because it has no client-domain
participant, e.g. `gr-1003`/`gr-1004`/`gr-1006`):

- `@natera.com` participant → `natera`
- `@goengen.com` participant → `engen`
- No client-domain participant → `none`
- Both domains present (`gr-1008`) → ambiguous. **Pinned rule:** take
  the alphabetically-first matching domain *string*, then map that
  domain to its client key. `"goengen.com" < "natera.com"`
  alphabetically, so a dual-domain meeting maps to `engen`. This is an
  arbitrary but deterministic tie-break, pinned in
  `quarantine_lib.map_client()` and documented in
  `expected_client_mapping.json`.

Note this tie-break is intentionally different from the "dominant"
domain `SKILL.md` §3d picks for a quarantined meeting's redacted title
(which walks `CLIENT_DOMAINS` in *declared* order — `natera.com` first —
not alphabetical order). `gr-1008` maps to client `engen` here but
redacts to `"Client sync (natera.com)"` in `expected_redaction.json`.
Both are correct; they're answering different questions.

Expected output: `fixtures/expected_client_mapping.json`.

### `test_redaction.sh` / `test_redaction.py`

Given every meeting in `fixtures/granola_meetings.json`, verifies the
"stripped for gateway" transform (`quarantine_lib.redact_for_gateway()`,
per `SKILL.md` §3d) for the five that get quarantined
(`gr-1001`, `gr-1002`, `gr-1006`, `gr-1007`, `gr-1008`):

- `title` is **unconditionally** replaced with `"Client sync
  (<dominant>)"` — `SKILL.md` has no "keep the title if it doesn't
  contain client hints" branch; every quarantined meeting's title gets
  this same templated treatment regardless of the original wording
- `summary` / `next_steps` replaced with `"[redacted: client-domain
  meeting]"` (`SKILL.md` sets these to `None`; the test renders that as
  a readable placeholder string for review purposes)
- `known_participants` collapses to an `attendees` **count**, not the
  list — no names or emails survive
- `duration_minutes`, `start_time`, `end_time`, `meeting_id`, and
  `granola_link` are preserved untouched, because `SKILL.md` §3d never
  touches them — this is what lets the drafter still say "5 client
  calls totaling 2h20m" (see the `aggregate_example` block in
  `fixtures/expected_redaction.json`) without a single meeting body or
  participant email in play
- The single non-quarantined meeting (`gr-1005`) is checked to pass
  through completely unmodified. Post-PR #10 both `gr-1003` and
  `gr-1004` now quarantine via `alias_hit` and go through the redaction
  transform instead of the pass-through path.

Expected output: `fixtures/expected_redaction.json`.

## Fixture inventory

All under `fixtures/`, all synthetic:

| File | Contents |
|---|---|
| `gh_activity.json` | 6 PRs + 3 reviews across 3 fake-owner repos, plus a `known_repos` list (including one deliberately-empty repo) |
| `slack_activity.json` | 9 messages across 4 channels, plus a `known_channels` list (including one deliberately-empty channel) |
| `granola_meetings.json` | 8 meetings covering every quarantine signal + one malformed case |
| `client_domains.env` | Pinned `CLIENT_DOMAINS=natera.com,goengen.com` |
| `expected_clusters.json` | Expected `test_clustering.py` output, with per-row `justification` |
| `expected_quarantine.json` | Expected `test_quarantine.py` verdicts, with per-row `justification` |
| `expected_client_mapping.json` | Expected `test_client_mapping.py` output + the pinned tie-break rule |
| `expected_redaction.json` | Expected `test_redaction.py` output, with per-row `justification` and an aggregate-stat example |
| `mock_gateway_response.json` | Canned Anthropic-messages-shape response, for a future v0.3 harness that stubs `SKILL.md` §6. Not invoked by any test here. |

## What this does not cover

- The actual gateway call (`SKILL.md` §6) — never invoked, real or
  mocked, by these tests
- The drafted EOD text itself, voice-matching, emoji vocabulary, or the
  post-processing link-verification / trim rules in §7 — these depend on
  LLM output and stay manual, same as v0.1's stated position
- Slack markup cleaning (`../eyes/SKILL.md` §3, reused by `eod-drafter`
  §3b) — covered by `../../eyes/tests/`
  ([`README`](../../eyes/tests/README.md)), not duplicated here
- The full §4 workstream-mapping table (`ai-gateway` / `flywheel` /
  `forge` / `natera` / `engen` / `liatrio-internal` / `other`) — the
  clustering test here checks the simpler repo/channel-prefix grouping
  primitive that table's inputs come from, not the table's exact
  match-string patterns (e.g. `marketing-dashboard*` as a repo prefix)
- Wiring into CI — that's v0.3, per the task that produced this harness
- `gh` CLI, Slack MCP, or Granola MCP themselves — everything here reads
  static fixtures shaped like their outputs
