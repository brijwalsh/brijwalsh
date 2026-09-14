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

# FLEET.md schema — proves the parser eod-drafter §5b promises still
# matches what's in bots/FLEET.md (headers, active rows, dates)
bash bots/tests/test_fleet_parser.sh

# pdp-evidence-targets.md schema — same idea, guards eod-drafter §5c
bash bots/tests/test_pdp_parser.sh

# eod-drafter §7e — LLM-output split + PDP+LLM merge (dedup, cap,
# overdue priority)
bash bots/eod-drafter/tests/test_top3_split.sh
```

`eod-drafter`'s drafted EOD text is still untested because it's
LLM-generated — that part stays manual. Everything deterministic ahead
of the gateway call now has fixture-driven coverage.

What these cover, and what they skip, lives next to each runner:

- [`../eyes/tests/README.md`](../eyes/tests/README.md)
- [`../follow-up-radar/tests/README.md`](../follow-up-radar/tests/README.md)
- [`../eod-drafter/tests/README.md`](../eod-drafter/tests/README.md)
