# AI Gateway matrix — Brian's POV rows

> **Status:** Draft POV. Two additional scored rows for Paul Henson's
> AI Gateway evaluation matrix, per Fable 5.1's directive to
> "put the two real X ideas into the Gateway matrix today."
>
> Paul's actual matrix is a Google Sheet he owns (per Ron's Sep 1
> interview notes). This file is the source-controlled version of
> the rows Brian wants added, plus scoring rubric + initial
> hypothesis so the copy-in is deterministic instead of another
> Sunday-scroll.

## What Fable said

> "Put the two real X ideas into the Gateway matrix today, then
> stop reading the feed for tooling. Add 'spec/acceptance criteria
> per gateway' and 'cost-aware routing' as scored rows. That
> converts the likes into a client-facing POV and closes the loop
> so you're not re-litigating the same 21 posts next Sunday."

Two rows to add to Paul's matrix. Rubric shared across both. Initial
hypotheses filled from public docs and Ron's Sep 1 notes — Paul or
Brian tightens the numbers with a real evaluation pass.

## The two rows

### Row A — Spec / acceptance criteria per gateway

**What it measures:** the gateway supports declaring, per request or
per route, an *acceptance contract* the downstream call must satisfy
before the gateway considers the response valid. Examples: schema
validation, function-call shape, cost ceiling, latency budget,
groundedness score threshold, safety-filter passthrough. Fail the
contract → the gateway retries, downshifts model, or returns a typed
error, without the client authoring that logic.

**Why it matters (client-facing POV):** enGen's `AI-guided web form
replacing the email process` (Paul's v1 target, from Sep 1
interview) needs deterministic validation, not "it usually works."
A gateway that exposes acceptance criteria as first-class config
turns the LLM-judge step into a routing concern, not an app
concern. That's what a Delivery Principal wants to buy.

**Related:** OpenAI Structured Outputs, Anthropic tool-use JSON
schema, LiteLLM `response_format`, Guardrails.ai, PydanticAI
validators. This row asks whether the *gateway* orchestrates them,
not whether the model supports them.

### Row B — Cost-aware routing

**What it measures:** the gateway routes across models based on a
declared cost signal — per-token price, per-request budget,
running-total budget, or a policy like `route to cheapest model
that passes acceptance criteria`. Contrast with static routing
(`always use Claude Sonnet`) or task-type routing without cost
awareness (`code → Sonnet, chat → Haiku` regardless of price).

**Why it matters (client-facing POV):** enterprises are lighting
money on fire routing simple calls to Opus. A gateway that can
enforce `budget: $0.05 per request, cheapest first, escalate on
contract-fail` is the productization of the Flywheel POV Paul
brought in on his interview. Brian's Delivery Principal message
lands harder with a scored row than another X-liked link.

**Related:** LiteLLM router modes (`least-cost`, `simple-shuffle`),
Portkey routes, Martian model router, RouteLLM, `not-diamond`.

## Scoring rubric (0–3, per row)

| Score | Meaning |
|-------|---------|
| 0 | Feature is absent or the docs are silent |
| 1 | Feature is present but requires client-side code (i.e. not a gateway concern in practice) |
| 2 | Feature is first-class in config; happy-path works, edge cases require workarounds |
| 3 | Feature is production-grade: config-driven, observable, handles retries / escalation / typed errors natively |

## Initial hypothesis — fill from real eval

Numbers below are Brian's best-guess starting scores from public
docs + Ron's notes. Paul overwrites with real observations from the
Flywheel eval sprint. Any row where two evaluators disagree by ≥ 2
gets a comment + a re-test.

| Gateway | Spec / acceptance (Row A) | Cost-aware routing (Row B) | Notes |
|---------|---------------------------|-----------------------------|-------|
| LiteLLM (self-hosted) | 2 | 3 | `response_format` + Guardrails hook covers A; router modes cover B natively |
| Bifrost (internal Liatrio) | ? | ? | Need Paul's read — treat as unknown until eval |
| Agent Gateway (internal Liatrio) | ? | ? | Same |
| Azure APIM (AI Gateway policy) | 1 | 2 | JSON schema on the model side; APIM does budget policies but not automatic downshift |
| Google Apigee (AI-aware routes) | 1 | 1 | Newer, less docs; treat as unknown until eval |
| AWS Bedrock router | 1 | 2 | Multi-model invocation exists; acceptance-criteria story weak |
| Portkey | 2 | 3 | Strong on both if you buy their pricing |
| RouteLLM | 0 | 3 | Cost routing only; no acceptance layer |
| not-diamond | 1 | 3 | Similar to RouteLLM with a light schema check |
| Cursor Cloud Agent gateway | 1 | 1 | Not the primary use case; kept for completeness |

Two rows per gateway = 20 initial-hypothesis cells. Paul + Brian
should split the fill so no one owns more than 10 cells.

## Copy-in procedure

1. Open Paul's Gateway matrix Google Sheet
   (link lives in his notes from Sep 1 — ping him if unclear).
2. Insert two new rows under the existing scoring section:
   - **`Spec / acceptance criteria per gateway`** with the rubric
     description from this doc.
   - **`Cost-aware routing`** with the rubric description from this
     doc.
3. Paste the initial-hypothesis column into the matrix. Mark them
   as **Brian-hypothesis** until Paul evaluates.
4. Add a `Rubric` sheet-tab (or a cell note) copying the 0–3
   scoring table above.
5. Ping Paul with a link to this doc so he has the client-facing
   POV context, not just the numbers.

Once the rows are in Paul's matrix:

- Delete this file's hypothesis table.
- Keep this doc as the POV rationale + rubric reference.
- Move any `pdp-*` target that referenced "Gateway matrix" to
  `complete`.

## Closing the loop

Fable's second half: "then stop reading the feed for tooling." The
enforcement is behavioral, not code, but three anchors in this
repo help hold the line:

1. **Row A + Row B in Paul's matrix** — the two liked-but-not-
   actioned ideas are now scored inputs, not open loops.
2. **Fleet budget in [`../ROADMAP.md`](../ROADMAP.md#fleet-budget-v01)**
   — new tooling wants to displace old, not compound with it.
3. **PDP evidence targets in
   [`./pdp-evidence-targets.md`](./pdp-evidence-targets.md)** —
   growth is measured by targets closed, not links saved.

If Sunday-scroll energy keeps generating "new bot" ideas, that's a
signal a target is missing from the PDP table, not that the fleet
needs another skill.

## Why this is a doc, not a bot

The v0.1 kit does **not** write to Paul's Google Sheet. That would
need a Drive-side MCP integration and Paul's consent to schema
changes. This is a source-controlled artifact Brian pastes once,
in Paul's presence, so ownership stays with the person who
maintains the matrix.
