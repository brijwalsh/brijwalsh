#!/usr/bin/env bash
# Regex prefilter tests for follow-up-radar SKILL.md §4.
# Asserts matches_any_pattern == expected_match. Does not call an LLM.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
FIXTURES="$ROOT/fixtures/candidates.jsonl"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 2
fi

if [[ ! -f "$FIXTURES" ]]; then
  echo "missing fixtures: $FIXTURES" >&2
  exit 2
fi

# Runtime forms of SKILL.md §4. Pipes are unescaped (alternation), matching
# the note under that table. grep -P so \b / \s / \d mean what the table says.
PATTERNS=(
  '\b(I'\''ll|I will|let me)\b'
  '\b(we'\''ll|we will|we are going to|we'\''re going to)\b'
  '\b(by|before)\s+(EOD|EOW|Fri|Mon|tomorrow|today|Monday|Friday|\d{4}-\d{2}-\d{2})\b'
  '\bcircl(e|ing) back\b'
  '\bfollow(-|\s)?up\b'
  '\bwaiting (on|for)\b'
  '\bblocked (on|by)\b'
  '\bdecid(e|ing|ed)\b'
)

matches_any() {
  local text="$1"
  local pat
  for pat in "${PATTERNS[@]}"; do
    if printf '%s' "$text" | grep -Pq -- "$pat"; then
      return 0
    fi
  done
  return 1
}

passed=0
failed=0
failures=()
total=0

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  total=$((total + 1))

  id="$(printf '%s\n' "$line" | jq -r '.id')"
  text="$(printf '%s\n' "$line" | jq -r '.text')"
  expected="$(printf '%s\n' "$line" | jq -r '.expected_match')"

  if [[ "$expected" != "true" && "$expected" != "false" ]]; then
    failed=$((failed + 1))
    failures+=("$id: expected_match is '$expected', want true or false")
    continue
  fi

  if matches_any "$text"; then
    actual=true
  else
    actual=false
  fi

  if [[ "$actual" == "$expected" ]]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    failures+=("$id: matches_any_pattern=$actual expected_match=$expected text=$(printf '%s' "$text" | jq -Rs .)")
  fi
done < "$FIXTURES"

echo "$passed passed / $failed failed ($total fixtures)"

if (( failed > 0 )); then
  echo "failed fixtures:"
  for f in "${failures[@]}"; do
    echo "  - $f"
  done
  exit 1
fi
