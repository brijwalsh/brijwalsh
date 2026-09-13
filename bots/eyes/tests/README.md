# eyes ranking tests

Runs the §3 class rules and the §4 composite sort against a frozen
search payload. No Slack MCP, no DM composition.

## How to run

From the repo root:

```bash
python3 bots/eyes/tests/test_ranking.py
```

Python 3 stdlib only. No pip, no pytest.

Exit 0 if the computed top 5 matches
`fixtures/expected_ranking.json`. Exit 1 on a mismatch and print both
lists with class, age, and channel so the break is obvious.

## What it covers

`fixtures/search_results.json` is a 20-item array shaped like a
`slack_search_public_and_private` hit list:

- `pr` — `github.com/*/pull/*`
- `doc` — `notion.so`, `confluence`, `docs.google.com`, `liatr.io`
- `article` — exactly one external URL, no Liatrio/GitHub domain
- `thread` — `reply_count >= 3` (including a GitHub *issue* URL, which
  is not a PR)
- `msg` — plain text, plus a two-URL decoy that must not become
  `article`

Ages run from 1 day to 7 days, measured against
`2026-09-13 22:00:00 America/Chicago` (`as_of_ts` in
`expected_ranking.json`). Channels include `#project-*`, `#client-*`,
`#liatrio` / `#liatrio-forge`, a 1:1 DM, and a group DM. DMs omit
`channel.name` and carry `channel.id` plus `Participants`.

Sort key, descending, from SKILL.md §4:

1. `class` in `(pr, doc)`
2. age > 5 days
3. channel name starts with `client-` or `project-`
4. `ts` newest-first

## What it does not cover

- Snippet cleaning (Slack mrkdwn collapse)
- Channel rendering (`DM w/`, `Group DM w/`)
- Digest copy, the 5/15 Close-the-loop vs Later split, or the DM
- Slack MCP itself, including `hasmy::eyes:`
- Dedup / `clear` (v0.2)
