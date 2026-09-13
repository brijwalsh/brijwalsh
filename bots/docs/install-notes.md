# Install notes — Delivery Principal Ops Kit (v0.1)

## Where these skills live

**Staging (this PR):** `BriWalsh/brwalsh:bots/`. Fine for review and
dry-run testing.

**Production (post-merge):** `BriWalsh/cursor-user-skills`, one folder per
skill at the repo root. That way `.cursor/install-skills.sh` in
`brwalsh` picks them up on every Cloud Agent VM with no code changes.

## Moving them — recommended (git mv-style)

Once this PR is merged, do a follow-up in `cursor-user-skills`:

```bash
git clone git@github.com:BriWalsh/cursor-user-skills.git
git clone git@github.com:BriWalsh/brwalsh.git

cd cursor-user-skills
git checkout -b add-delivery-principal-ops-kit

cp -r ../brwalsh/bots/eyes .
cp -r ../brwalsh/bots/eod-drafter .
cp -r ../brwalsh/bots/follow-up-radar .

# Docs live alongside the skills so they don't 404 after the move
mkdir -p _delivery-principal-ops-kit
cp -r ../brwalsh/bots/docs _delivery-principal-ops-kit/docs
cp    ../brwalsh/bots/README.md _delivery-principal-ops-kit/README.md
cp    ../brwalsh/bots/ROADMAP.md _delivery-principal-ops-kit/ROADMAP.md

git add eyes eod-drafter follow-up-radar _delivery-principal-ops-kit
git commit -m "Add Delivery Principal Ops Kit v0.1"
git push -u origin add-delivery-principal-ops-kit
```

Note: after the move, the skills reference their docs via a relative
`../_delivery-principal-ops-kit/docs/...` path, or you can just leave the
`bots/docs/` links pointing at `brwalsh` (still resolves for a human
reader). Skills themselves don't `require` the docs at runtime; they're
for humans.

Then, in a follow-up PR to `brwalsh`, delete the skill folders (leaving
`bots/README.md`, `bots/ROADMAP.md`, and `bots/docs/` as the kit's
documentation home page).

## Alternative — install-skills.sh pulls from both

If Brian prefers a single source of truth in `brwalsh` (iterate here,
promote to `cursor-user-skills` only when stable), extend
`.cursor/install-skills.sh`:

```bash
# After the existing rsync of $SRC (cursor-user-skills):
BOTS_SRC="$(mktemp -d)"
trap 'rm -rf "$SRC" "$BOTS_SRC"' EXIT

if [ -n "${GH_TOKEN:-}" ] && git clone --depth 1 --quiet \
    "https://x-access-token:${GH_TOKEN}@github.com/BriWalsh/brwalsh.git" "$BOTS_SRC" 2>/dev/null; then
  :
elif ! git clone --depth 1 --quiet "https://github.com/BriWalsh/brwalsh.git" "$BOTS_SRC" 2>/dev/null; then
  echo "WARN: could not clone brwalsh for ops-kit skills; skipping." >&2
  BOTS_SRC=""
fi

if [ -n "$BOTS_SRC" ]; then
  for skill in eyes eod-drafter follow-up-radar; do
    if [ -d "$BOTS_SRC/bots/$skill" ]; then
      for dest in "${DESTS[@]}"; do
        rsync -a --exclude '.git' "$BOTS_SRC/bots/$skill/" "$dest/$skill/"
      done
    fi
  done
fi
```

Either option is fine. The recommended path is cleaner; the alternative
is faster iteration.

## Cursor Cloud Agent secrets

Set under **Cloud Agents > Secrets** (user scope):

| Secret | Skills that use it | Notes |
|--------|-------------------|-------|
| `GATEWAY_BASE_URL` | eod-drafter, follow-up-radar | OpenAI-compatible endpoint |
| `GATEWAY_API_KEY` | eod-drafter, follow-up-radar | Bearer token |
| `GATEWAY_MODEL` | eod-drafter, follow-up-radar | Model name to request |
| `CLIENT_DOMAINS` | eod-drafter | Optional; defaults `natera.com,goengen.com` |

Slack MCP token, Granola MCP token, and Gmail MCP token are managed by
Cursor's built-in MCP config — no additional secrets needed if those
MCPs are already connected in your Cursor session.

## Non-Cursor runtimes

Skills are agent-agnostic (SKILL.md format).

- **Claude Code:** point `~/.claude/skills/` at the same install directory
  as `~/.cursor/skills/`. The `allowed-tools` frontmatter field is not set
  in this kit, so any Claude Code tool profile works.
- **Manual:** each skill's `runbook.md` documents the CLI invocation
  patterns. Nothing daemonizes; each run is stateless in v0.1.

## Uninstall

```bash
rm -rf ~/.cursor/skills/eyes ~/.cursor/skills/eod-drafter ~/.cursor/skills/follow-up-radar
rm -rf ~/.agents/skills/eyes ~/.agents/skills/eod-drafter ~/.agents/skills/follow-up-radar
```

No caches / config files to worry about in v0.1 — everything is
stateless. State stores show up in v0.2 (see [`../ROADMAP.md`](../ROADMAP.md)).
