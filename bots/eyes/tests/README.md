# eyes ranking tests

Runs the class rules and both ranking versions against a frozen Slack search
payload. The harness uses Python 3 stdlib only. It makes no Slack MCP or LLM
calls.

## How to run

From the repository root:

```bash
bash bots/eyes/tests/test_ranking.sh
```

The default checks both versions:

```bash
python3 bots/eyes/tests/test_ranking.py --version all
```

Run one path explicitly:

```bash
python3 bots/eyes/tests/test_ranking.py --version v0.1
python3 bots/eyes/tests/test_ranking.py --version v0.2
```

The v0.2 path accepts another dedup-state fixture:

```bash
python3 bots/eyes/tests/test_ranking.py \
  --version v0.2 \
  --dedup-state path/to/dedup_state.json
```

Exit 0 means every computed top five matches its expected fixture. Exit 1
prints expected and actual rows with class, Slack age, channel, and v0.2
awareness age.

## Fixtures

`fixtures/search_results.json` is the original 20-item
`slack_search_public_and_private` payload. It covers:
- `pr` links matching `github.com/*/pull/*`
- `doc` links from Notion, Confluence, Google Docs, and `liatr.io`
- one-link external `article` messages
- `thread` rows with at least three replies
- plain `msg` rows and a two-URL article decoy
- project, client, general, DM, and group-DM channels

`fixtures/expected_ranking.json` preserves the v0.1 top five. Its descending
key is close-the-loop class, Slack age over five days, work-channel signal,
then newest Slack timestamp.

`fixtures/dedup_state.json` is a permalink-keyed fake List index. Five items
have been open for three to six days, including fresh Slack messages with
non-`pr`/`doc` classes.

`fixtures/expected_ranking_v0_2.json` proves awareness age is the primary key.
The six-day `msg`, five-day `article`, and four-day `thread` all move above
three-day `pr` and `doc` rows despite their lower v0.1 class priority.

All fixture ages use `as_of_ts=1789354800.0`, which is
`2026-09-13 22:00:00 America/Chicago`.

## What it covers

- Regex classification
- The unchanged v0.1 ranking path
- Permalink lookup in fake dedup state
- v0.2 awareness-age promotion
- v0.1 tie-breakers after awareness age

## What it does not cover

- Snippet cleaning or DM/group-DM rendering
- Daily digest eligibility and `is_new`
- Digest copy or Slack thread replies
- Slack List pagination, upserts, reaction polling, or idempotency
- Slack MCP search behavior
