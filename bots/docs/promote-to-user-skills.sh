#!/usr/bin/env bash
#
# Promote the Delivery Principal Ops Kit from BriWalsh/brwalsh:bots/ to
# BriWalsh/cursor-user-skills, one folder per skill at the repo root plus a
# shared docs bundle under _delivery-principal-ops-kit/.
#
# Automates the "recommended (git mv-style)" recipe documented in
# bots/docs/install-notes.md. Safe to re-run: on re-run it recreates the
# target branch in the fresh clone rather than reusing stale state.
#
# This script does NOT open a pull request. Use Cursor's ManagePullRequest
# tool (or the GitHub UI) for that — never `gh pr create`.

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Defaults / flags
# ---------------------------------------------------------------------------

DRY_RUN=0
WORK_DIR="/tmp/promote-$$"
BRWALSH_REF="main"
TARGET_BRANCH="cursor/add-delivery-principal-ops-kit-0428"

SOURCE_REPO="git@github.com:BriWalsh/brwalsh.git"
TARGET_REPO="git@github.com:BriWalsh/cursor-user-skills.git"

SKILLS=(eyes eod-drafter follow-up-radar)

usage() {
  cat <<'EOF'
Usage: promote-to-user-skills.sh [options]

Options:
  --dry-run                 Print every command that would run; mutate nothing.
  --work-dir <path>         Directory to clone repos into (default: /tmp/promote-$$).
  --brwalsh-ref <ref>       Ref in BriWalsh/brwalsh to pull bots/ from (default: main).
  --target-branch <name>    Branch to create in cursor-user-skills
                             (default: cursor/add-delivery-principal-ops-kit-0428).
  -h, --help                Show this help.

Env vars:
  KEEP_WORK_DIR=1           Skip the cleanup trap and leave --work-dir on disk.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --work-dir)
      WORK_DIR="$2"
      shift 2
      ;;
    --brwalsh-ref)
      BRWALSH_REF="$2"
      shift 2
      ;;
    --target-branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

BRWALSH_CLONE="$WORK_DIR/brwalsh"
TARGET_CLONE="$WORK_DIR/cursor-user-skills"

log() {
  echo "[promote] $*" >&2
}

run() {
  # Print the command always; execute it only when not in dry-run mode.
  # (printf "%s " "$@" instead of "$*" because IFS is set to $'\n\t' above,
  # which would otherwise join args with newlines instead of spaces.)
  local rendered
  rendered="$(printf '%s ' "$@")"
  log "+ ${rendered% }"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    "$@"
  fi
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

cleanup() {
  local exit_code=$?
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return
  fi
  if [[ "${KEEP_WORK_DIR:-0}" == "1" ]]; then
    log "KEEP_WORK_DIR=1 set; leaving $WORK_DIR in place."
    return
  fi
  if [[ -d "$WORK_DIR" ]]; then
    log "Cleaning up $WORK_DIR"
    rm -rf -- "$WORK_DIR"
  fi
  if [[ "$exit_code" -ne 0 ]]; then
    log "Exiting with status $exit_code"
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Step 1: prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites (git, gh, sed, find)..."
for bin in git gh sed find grep; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    fail "required binary '$bin' not found in PATH"
  fi
done

# ---------------------------------------------------------------------------
# Step 2: gh auth
# ---------------------------------------------------------------------------

log "Checking gh auth status..."
if ! gh auth status >/dev/null 2>&1; then
  fail "'gh auth status' did not return OK. Run 'gh auth login' first."
fi

# Sanity check: bots/ must exist relative to CWD-independent repo layout.
# This is a read-only check, safe even in --dry-run.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ ! -d "$BOTS_DIR" || "$(basename "$BOTS_DIR")" != "bots" ]]; then
  fail "could not locate the bots/ directory relative to this script"
fi
log "Found bots/ at $BOTS_DIR (informational; the actual source is cloned from --brwalsh-ref=$BRWALSH_REF below)."

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "--dry-run: the remaining steps below would run against WORK_DIR=$WORK_DIR"
fi

# ---------------------------------------------------------------------------
# Step 3: clone both repos
# ---------------------------------------------------------------------------

run mkdir -p "$WORK_DIR"

run git clone --depth 1 "$TARGET_REPO" "$TARGET_CLONE"
run git clone --depth 1 --branch "$BRWALSH_REF" "$SOURCE_REPO" "$BRWALSH_CLONE"

if [[ "$DRY_RUN" -eq 1 ]]; then
  # We can't actually inspect a clone that was never made; stub the paths so
  # the remaining commands still print sensibly.
  log "(dry run: skipping the rest of the pipeline against real clones)"
fi

# ---------------------------------------------------------------------------
# Step 4: cd into the cursor-user-skills clone
# ---------------------------------------------------------------------------

if [[ "$DRY_RUN" -eq 0 ]]; then
  cd "$TARGET_CLONE"
else
  log "+ cd $TARGET_CLONE"
fi

# ---------------------------------------------------------------------------
# Step 5: create the target branch (idempotent: delete + recreate if present)
# ---------------------------------------------------------------------------

if [[ "$DRY_RUN" -eq 0 ]]; then
  if git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
    log "Branch $TARGET_BRANCH already exists locally; deleting and recreating."
    run git checkout main
    run git branch -D "$TARGET_BRANCH"
  fi
fi
run git checkout -b "$TARGET_BRANCH"

# ---------------------------------------------------------------------------
# Step 6: copy the three skill folders to the repo root
# ---------------------------------------------------------------------------

for skill in "${SKILLS[@]}"; do
  run rm -rf -- "./$skill"
  run cp -r "$BRWALSH_CLONE/bots/$skill" "./$skill"
done

# ---------------------------------------------------------------------------
# Step 7: shared docs bundle
# ---------------------------------------------------------------------------

run rm -rf -- "./_delivery-principal-ops-kit"
run mkdir -p "./_delivery-principal-ops-kit"
run cp -r "$BRWALSH_CLONE/bots/docs" "./_delivery-principal-ops-kit/docs"
run cp "$BRWALSH_CLONE/bots/README.md" "./_delivery-principal-ops-kit/README.md"
run cp "$BRWALSH_CLONE/bots/ROADMAP.md" "./_delivery-principal-ops-kit/ROADMAP.md"

# ---------------------------------------------------------------------------
# Step 8: sed rewrite of relative links
# ---------------------------------------------------------------------------

rewrite_links() {
  local target="$1"
  log "Rewriting relative links under $target"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "+ find $target -type f -name '*.md' -exec sed -i.bak -E ... {} +"
    return
  fi
  find "$target" -type f -name '*.md' -exec \
    sed -i.bak -E \
      -e 's|\.\./ROADMAP\.md|../_delivery-principal-ops-kit/ROADMAP.md|g' \
      -e 's|\.\./README\.md|../_delivery-principal-ops-kit/README.md|g' \
      -e 's|\.\./docs/|../_delivery-principal-ops-kit/docs/|g' \
      {} +
  find "$target" -name '*.bak' -delete
}

for skill in "${SKILLS[@]}"; do
  rewrite_links "$skill"
done

# _delivery-principal-ops-kit/*.md may itself contain ./ROADMAP.md, ./README.md,
# or ./docs/ links (e.g. README.md linking to ./ROADMAP.md, or docs/*.md
# linking back up to ../README.md within the same folder). Those are already
# correct relative to their new home, EXCEPT any that assumed a nested
# `docs/` sibling at `./docs/` from the bots/ layout, which is unaffected by
# the move (docs/ still sits next to README.md/ROADMAP.md). This step is a
# no-op unless an internal link needs correcting; kept as an explicit,
# idempotent pass per install-notes.md.
rewrite_kit_links() {
  local target="./_delivery-principal-ops-kit"
  log "Rewriting internal links under $target"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "+ find $target -maxdepth 1 -type f -name '*.md' -exec sed -i.bak -E ... {} +"
    return
  fi
  find "$target" -maxdepth 1 -type f -name '*.md' -exec \
    sed -i.bak -E \
      -e 's|\./ROADMAP\.md|ROADMAP.md|g' \
      -e 's|\./README\.md|README.md|g' \
      -e 's|\./docs/|docs/|g' \
      {} +
  find "$target" -name '*.bak' -delete
}
rewrite_kit_links

# ---------------------------------------------------------------------------
# Step 9: verify no broken relative links remain
# ---------------------------------------------------------------------------

verify_links() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    local rendered
    rendered="$(printf '%s ' "${SKILLS[@]}")"
    log "+ grep -rn '\\.\\./\\(ROADMAP\\|README\\)\\.md' ${rendered% }"
    return
  fi
  log "Verifying no broken ../ROADMAP.md or ../README.md links remain..."
  if grep -rn '\.\./\(ROADMAP\|README\)\.md' "${SKILLS[@]}"; then
    fail "broken relative links found above; the sed rewrite in step 8 did not fully cover them"
  fi
  log "No broken links found."
}
verify_links

# ---------------------------------------------------------------------------
# Step 10-11: commit and push
# ---------------------------------------------------------------------------

run git add eyes eod-drafter follow-up-radar _delivery-principal-ops-kit
run git commit -m "Add Delivery Principal Ops Kit v0.1

Promotes eyes, eod-drafter, and follow-up-radar from BriWalsh/brwalsh:bots/
to the repo root, plus shared docs under _delivery-principal-ops-kit/.
Generated by bots/docs/promote-to-user-skills.sh."
run git push -u origin "$TARGET_BRANCH"

# ---------------------------------------------------------------------------
# Step 12: next steps
# ---------------------------------------------------------------------------

cat <<EOF

===========================================================================
Next steps
===========================================================================
The '$TARGET_BRANCH' branch has been pushed to BriWalsh/cursor-user-skills.

Do NOT run 'gh pr create'. Instead, open the pull request using Cursor's
ManagePullRequest tool (or the GitHub web UI) with:
  - Base repo:   BriWalsh/cursor-user-skills
  - Base branch: main
  - Head branch: $TARGET_BRANCH
  - PR body:     bots/docs/promotion-pr-body.md (copy verbatim)

After that PR merges, open a follow-up PR against BriWalsh/brwalsh that
deletes bots/eyes, bots/eod-drafter, and bots/follow-up-radar, leaving
bots/README.md, bots/ROADMAP.md, and bots/docs/ as the kit's documentation
home page.
===========================================================================
EOF
