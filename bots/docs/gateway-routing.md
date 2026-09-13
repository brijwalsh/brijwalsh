# AI Gateway routing — for the ops kit (v0.1)

v0.1 uses one gateway per skill run, picked by env vars set on the
Cursor Cloud Agent. The daily-driver rotation across
Bifrost / Agent Gateway / LiteLLM / Azure APIM is done manually today
(Brian edits the secrets) and automated in v0.2
(see [`../ROADMAP.md`](../ROADMAP.md)).

## Env vars every skill respects

```
GATEWAY_BASE_URL    OpenAI-compatible endpoint of the current daily-driver
GATEWAY_API_KEY     Bearer token
GATEWAY_MODEL       Model name to request (e.g. claude-sonnet-5)
GATEWAY_TASK_TYPE   Optional; skill-specific default if unset
CLIENT_DOMAINS      Comma-sep, defaults "natera.com,goengen.com"
```

Where does the value come from?

| Gateway | Example `GATEWAY_BASE_URL` | Example `GATEWAY_MODEL` |
|---------|----------------------------|-------------------------|
| LiteLLM auto-router (Alex's) | `https://litellm.internal.liatrio/gateway/v1` | `claude-sonnet-5` |
| Bifrost (AWS) | `https://bifrost.aws.liatrio/v1` | `anthropic.claude-sonnet-5` |
| Agent Gateway | `https://agentgw.internal.liatrio/v1` | `sonnet-5` |
| Azure APIM (Foundry) | `https://apim.azure.liatrio.com/openai/v1` | `gpt-5.6-medium` |

Confirm each URL and model name against the current
`project-ai-gateway` runbooks before setting the secrets. The values
above are placeholders based on Brian's Slack context; the source of
truth is `project-ai-gateway` DevEx docs.

## The `metadata` block on the LLM call

Every gateway call from the ops kit sets:

```json
"metadata": {
  "task_type": "<eod-draft | commitment-classification | commitment-draft>",
  "skill":     "<eyes | eod-drafter | follow-up-radar>",
  "user":      "brian.walsh@liatrio.com"
}
```

Some gateways ignore this; some (LiteLLM auto-routers) use it for
routing. Setting it uniformly means the routers get consistent signal
across the kit.

## Client-domain quarantine (all skills)

Before any gateway call, every skill applies this rule:

```
if any(participant_domain in $CLIENT_DOMAINS
       for participant_domain in current_input.participants):
    strip_summary_and_next_steps(current_input)
    replace_title(current_input, f"Client sync ({dominant_domain})")
```

For `follow-up-radar`, the equivalent rule is even stricter: if
`current_input.channel_name` starts with `client-`, the message is
dropped entirely before the classifier ever sees it.

## Never fall back to a direct provider

If `$GATEWAY_BASE_URL` is unset, or returns 5xx, or times out: **DM Brian
and exit.** Do not call `api.anthropic.com` or `api.openai.com` directly.
The whole point of routing through the gateway is to produce dogfooding
data for `project-ai-gateway#125` — a silent fallback is a missed data
point.

## Local dev

If you're testing the skills on your laptop without a real gateway:

```
export GATEWAY_BASE_URL=http://localhost:4000/v1
export GATEWAY_MODEL=any-local-model
```

Point that at a local LiteLLM proxy or an OpenAI-compatible shim. Local
runs never contribute friction data to `#125` — they're dev-only by
convention.
