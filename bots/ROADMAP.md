# Delivery Principal Ops Kit — Roadmap (v0.2+)

Everything in v0.1 SKILL.md files that says "deferred" links here.
Nothing on this list ships until the corresponding gate is passed.

## v0.2 candidate features

### 1. Durable state (unlocks dedup + aging for all three skills)

**Gate:** a state store that survives Cloud Agent VM tear-down.

Options, ranked:

1. **GitHub Gist owned by @BriWalsh, secret.** One gist per skill,
   fixed gist ID recorded in the SKILL.md. Read/write via `gh gist edit`.
   Easiest and no new infra.
2. **Slack List** (Slack's structured list objects, not canvas markdown).
   `slack_create_list`, `slack_add_list_record`, etc. are already MCP tools.
   Cleaner UI, harder to script.
3. **A tiny KV service** in Brian's marketing-dashboard AWS account.
   Overkill for v0.2; only if the gist approach hits size caps.

Once state exists:
- [`eyes` v0.2 durable dedup design](./eyes/v0.2-dedup-design.md) defines the
  Slack List schema, age-aware ranking, daily suppression, and clear flow
- `eod-drafter` gets friction.jsonl + Friday summary
- `follow-up-radar` gets aging + `clear`

### 2. Automated gateway rotation

**Gate:** the state store from §1 is in place.

Add `~/.config/eod-drafter/rotation.yaml`, resolve via a resolver that
reads from state, and DM Brian on rotation-boundary days
("Today: switching from LiteLLM to Bifrost per rotation. Confirm the
new gateway is healthy before the 16:00 run.").

### 3. Slack event listeners (`clear`, `send`, `/eod-friction`)

**Gate:** either (a) Cursor Cloud Agents ships an event-driven trigger for
Slack `message.im`, or (b) Brian stands up a small always-on webhook
service (Cloud Run / Lambda / ECS-on-Marketing-Dashboard-infra) that
forwards events into a Cursor Cloud Agent invocation.

Until then, "reply to the digest" is a nice UX but not implementable
reliably. Users can still edit state manually via the gist.

### 4. Client channels in `follow-up-radar`

**Hard gate**, all four required:

- [ ] Verified BAAs with every gateway on the rotation
      (Bifrost/Agent Gateway/LiteLLM/APIM)
- [ ] A DLP layer that strips PHI/PII **before** the gateway call
      (post-call regex redaction is theater — the LLM already saw it)
- [ ] Legal / compliance sign-off documented in `bots/docs/v0.2-legal.md`
- [ ] Durable state (`§1`) — because aging matters more here than anywhere

Absent any of these, `#client-*` channels remain hard-blocked at both
the config layer and the guardrail layer.

### 5. Gmail in `follow-up-radar`

Same gate as §4. Client email bodies are the highest-sensitivity data
type in play; do not unlock without the same four checks.

### 6. Granola cross-reference in `follow-up-radar`

Same gate as §4 — client-domain participants means client-adjacent
meeting content, same quarantine rules apply. Adopt the `eod-drafter`
quarantine pattern once state is in place.

### 7. Consolidated "Delivery Principal Ops" internal artifact

**Gate:** v0.1 skills have shipped, been used for 2+ weeks, and Brian
has confirmed they're saving time (measured, not vibes).

Then package the kit as:

- A Liatrio internal skill/marketplace bundle
- A short write-up for `#liatrio-weekly-workstream-updates` on the
  pattern (not the code)
- Optional: a Forge module extending the same pattern for other
  Delivery Principals (Chelsea, Blair, Craig, Ron, etc.)

## Anti-features — not on any roadmap

Documenting these explicitly so nobody accidentally builds them later:

- **Auto-posting drafts** to any channel other than Brian's DM. The kit
  drafts; Brian sends. Full stop.
- **Cross-platform DMs** (Telegram / WhatsApp / Discord). Brian lives in
  Slack; the ROI on cross-platform is negative.
- **Content generation** for `@BriJWalsh` on X. He's a reader, not a
  creator. Automating volume for an audience of 155 is theater.
- **Home Assistant / school portal / grocery integrations.** Fragile
  scraping, zero work leverage, infinite auth headache. Not this kit.
- **Client-side auto-reply.** Never. Not even with approval.
  Not even in v0.9.

## How to promote a v0.2 feature

1. Confirm the gate for that feature is passed. If not, stop.
2. Open a PR in this repo bumping the skill's `version:` in the SKILL.md
   frontmatter and adding the new scope to the "In scope" list.
3. Add a "Migrated from v0.2 candidate §N" line to the SKILL.md.
4. Delete or update the corresponding section here.
5. Ship.
