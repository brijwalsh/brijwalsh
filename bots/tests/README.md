# Running the test harness

v0.1 has two automated checks. Both are local, no network, no extra
packages. Each should finish in well under 5 seconds on a Cloud Agent
VM.

```bash
# eyes: classify + rank against a frozen Slack search payload
bash bots/eyes/tests/test_ranking.sh

# follow-up-radar: regex prefilter against 20 Slack-ish lines
bash bots/follow-up-radar/tests/test_regex_classifier.sh
```

`bots/eod-drafter/` has no automated tests in v0.1 because its output
is LLM-generated. Deferred to v0.2, when a mock gateway exists.

What these cover, and what they skip, lives next to each runner:

- [`../eyes/tests/README.md`](../eyes/tests/README.md)
- [`../follow-up-radar/tests/README.md`](../follow-up-radar/tests/README.md)
