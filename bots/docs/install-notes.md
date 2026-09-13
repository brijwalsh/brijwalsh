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

mkdir -p _delivery-principal-ops-kit
cp -r ../brwalsh/bots/docs _delivery-principal-ops-kit/docs
cp    ../brwalsh/bots/README.md _delivery-principal-ops-kit/README.md
cp    ../brwalsh/bots/ROADMAP.md _delivery-principal-ops-kit/ROADMAP.md

# The skills reference ../ROADMAP.md from their SKILL.md and runbook.md
# files. Under bots/ the parent path resolves to bots/ROADMAP.md; after
# the move each skill sits at the repo root, so the parent path resolves
# to the repo root — which has no ROADMAP.md. Rewrite the links in-place
# so they point at the new home. Do this before committing.
for skill in eyes eod-drafter follow-up-radar; do
  find "$skill" -type f -name '*.md' -exec \
    sed -i.bak -E \
      -e 's|\.\./ROADMAP\.md|../_delivery-principal-ops-kit/ROADMAP.md|g' \
      -e 's|\.\./README\.md|../_delivery-principal-ops-kit/README.md|g' \
      -e 's|\.\./docs/|../_delivery-principal-ops-kit/docs/|g' \
      {} +
  find "$skill" -name '*.bak' -delete
done

git add eyes eod-drafter follow-up-radar _delivery-principal-ops-kit
git commit -m "Add Delivery Principal Ops Kit v0.1"
git push -u origin add-delivery-principal-ops-kit
```

The `sed` block is the only load-bearing part. Skills themselves don't
`require` the docs at runtime — they're for humans — but the docs must
resolve when a human reader clicks them from a skill's SKILL.md.

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
# Extend the pre-existing EXIT trap that owned $SRC — do not clobber it
_prev_trap="$(trap -p EXIT | sed "s/^trap -- '//; s/' EXIT$//")"
trap "rm -rf \"\$BOTS_SRC\"; $_prev_trap" EXIT

if [ -n "${GH_TOKEN:-}" ] && git clone --depth 1 --quiet \
    "https://x-access-token:${GH_TOKEN}@github.com/BriWalsh/brwalsh.git" \
    "$BOTS_SRC" 2>/dev/null; then
  # Strip the token from .git/config before anything (rsync, cat, cp)
  # touches the checkout. Otherwise the bearer credential persists in
  # the temp clone and, worse, can be rsynced into destinations that
  # don't --exclude '.git' correctly.
  git -C "$BOTS_SRC" remote set-url origin \
    "https://github.com/BriWalsh/brwalsh.git"
elif ! git clone --depth 1 --quiet \
       "https://github.com/BriWalsh/brwalsh.git" "$BOTS_SRC" 2>/dev/null; then
  echo "WARN: could not clone brwalsh for ops-kit skills; skipping." >&2
  BOTS_SRC=""
fi

if [ -n "$BOTS_SRC" ]; then
  for skill in eyes eod-drafter follow-up-radar; do
    if [ -d "$BOTS_SRC/bots/$skill" ]; then
      for dest in "${DESTS[@]}"; do
        # --exclude '.git' is belt-and-suspenders now that the token is
        # already stripped, but keep it in case a future edit removes
        # the remote-set-url line above.
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
| `GATEWAY_TASK_TYPE` | eod-drafter, follow-up-radar | Optional; each skill has its own default |
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
