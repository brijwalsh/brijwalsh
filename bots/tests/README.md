# Running the test harness

Local checks only. All are bash/Python stdlib, no network, no extra
packages. Each should finish in well under 5 seconds on a Cloud Agent
VM.

```bash
# eyes: classify + rank against a frozen Slack search payload
bash bots/eyes/tests/test_ranking.sh

# follow-up-radar: regex prefilter against 20 Slack-ish lines
bash bots/follow-up-radar/tests/test_regex_classifier.sh

# eod-drafter: clustering, multi-signal quarantine, meeting->client
# mapping, and gateway-bound redaction against a mock-gateway harness
# (never calls a real gateway)
bash bots/eod-drafter/tests/test_clustering.sh
bash bots/eod-drafter/tests/test_quarantine.sh
bash bots/eod-drafter/tests/test_client_mapping.sh
bash bots/eod-drafter/tests/test_redaction.sh
```

`eod-drafter`'s drafted EOD text is still untested because it's
LLM-generated — that part stays manual. Everything deterministic ahead
of the gateway call now has fixture-driven coverage.

What these cover, and what they skip, lives next to each runner:

- [`../eyes/tests/README.md`](../eyes/tests/README.md)
- [`../follow-up-radar/tests/README.md`](../follow-up-radar/tests/README.md)
- [`../eod-drafter/tests/README.md`](../eod-drafter/tests/README.md)
