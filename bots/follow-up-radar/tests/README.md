# follow-up-radar regex tests

Checks the §4 regex prefilter against a fixed fixture set. Nothing here
talks to Slack or the gateway.

## How to run

From the repo root:

```bash
bash bots/follow-up-radar/tests/test_regex_classifier.sh
```

Needs `bash`, GNU `grep -P`, and `jq`. No other install.

Exit 0 if every fixture's `expected_match` matches the prefilter. Exit
1 if any assertion fails. Prints `N passed / N failed` and the failing
ids.

## What it covers

`fixtures/candidates.jsonl` is 20 Slack-ish message records (JSON Lines):

- 10 commitments. Mix of Brian promising, Brian waiting-on, and an
  external promise. Deadline styles include EOD, EOW, Friday, Mon,
  tomorrow, and an ISO date.
- 10 non-commitments. Aspirations (`we should`), past tense (`I sent
  it`), rhetorical (`let me tell you`), meta (`I'll circle back with
  the team`), plus decoys that still trip the regex (`I'll grab
  coffee`, `let me think`, `waiting on the AC repair`, `follow-up
  question`, `we are going to` lunch). `well, that's interesting` is
  the negative control for the `we'll` pattern.

Each line has `id`, `text`, `expected_match`, `expected_type`, and
`notes`. The runner only asserts `matches_any_pattern ==
expected_match`.

`expected_type` is documentation for a future classifier test. It is
one of the §5 `commitment_type` enums, or `null` when the line is not
a commitment.

Patterns are the runtime forms from SKILL.md §4 (unescaped `|`,
`grep -P` so `\b` / `\s` / `\d` keep their table meaning). Matching is
case-sensitive, as written in the skill.

## What it does not cover

- The classifier LLM call, confidence cutoff, or `expected_type`
- Draft language (`draft_apology` / `draft_nudge`)
- Channel exclusion, the client-channel guardrail, ranking, or the DM
- Slack MCP, gateway auth, or heartbeat text

Those stay manual until v0.2 has a mock gateway.
