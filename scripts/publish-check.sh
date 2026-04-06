#!/usr/bin/env bash
# Pre-publish checklist — validates the article is ready for publication
# Usage: publish-check.sh <project_dir>
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
STATE_DIR="$PROJECT_DIR/.essay-state"

PASS=0
FAIL=0
WARN=0

check() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
    echo "  ✓ $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  ✗ $desc"
  fi
}

warn_check() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
    echo "  ✓ $desc"
  else
    WARN=$((WARN + 1))
    echo "  ⚠ $desc"
  fi
}

# Helpers for checks that need shell features (grep patterns, pipelines)
file_has_heading() { head -5 "$1" | grep -q '^#'; }
file_grep_qi() { grep -qi "$1" "$2"; }
file_grep_q() { grep -q "$1" "$2"; }
json_field_truthy() { python3 -c "import json,sys; assert json.load(open(sys.argv[1])).get(sys.argv[2])" "$1" "$2"; }
score_at_least() { python3 -c "import sys; assert float(sys.argv[1]) >= float(sys.argv[2])" "$1" "$2"; }

echo "=== Pre-Publish Checklist ==="
echo ""

echo "Pipeline Completion:"
check "Pipeline state exists" test -f "$STATE_DIR/pipeline-state.json"
check "Pipeline marked complete" json_field_truthy "$STATE_DIR/pipeline-state.json" "completed"

echo ""
echo "Content Artifacts:"
check "Internal version exists" test -f "$STATE_DIR/final-internal.md"
check "External version exists" test -f "$STATE_DIR/final-external.md"
check "Social package exists" test -f "$STATE_DIR/social-package.json"

echo ""
echo "Internal version:"
if [ -f "$STATE_DIR/final-internal.md" ]; then
  WORD_COUNT=$(wc -w < "$STATE_DIR/final-internal.md" | tr -d ' ')
  check "Internal version > 500 words ($WORD_COUNT words)" test "$WORD_COUNT" -gt 500
  check "Has title (# heading)" file_has_heading "$STATE_DIR/final-internal.md"
  warn_check "Has TL;DR section" file_grep_qi 'tl;dr\|tldr\|summary' "$STATE_DIR/final-internal.md"
fi

echo ""
echo "External version:"
if [ -f "$STATE_DIR/final-external.md" ]; then
  WORD_COUNT=$(wc -w < "$STATE_DIR/final-external.md" | tr -d ' ')
  check "External version > 500 words ($WORD_COUNT words)" test "$WORD_COUNT" -gt 500
  check "Has title (# heading)" file_has_heading "$STATE_DIR/final-external.md"
  warn_check "Has About the Author" file_grep_qi 'about the author\|about me\|bio' "$STATE_DIR/final-external.md"
  warn_check "Has code examples" file_grep_q '```' "$STATE_DIR/final-external.md"
fi

echo ""
echo "Social package:"
if [ -f "$STATE_DIR/social-package.json" ]; then
  warn_check "Has Twitter thread" json_field_truthy "$STATE_DIR/social-package.json" "twitter_thread"
  warn_check "Has LinkedIn post" json_field_truthy "$STATE_DIR/social-package.json" "linkedin_post"
  warn_check "Has HN title" json_field_truthy "$STATE_DIR/social-package.json" "hn_title"
fi

echo ""
echo "Quality Gate:"
if [ -f "$STATE_DIR/quality-score.json" ]; then
  SCORE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('composite_score', 0))" "$STATE_DIR/quality-score.json")
  READINESS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('readiness', 'UNKNOWN'))" "$STATE_DIR/quality-score.json")
  check "Quality score ≥ 6.0 (score: $SCORE, readiness: $READINESS)" score_at_least "$SCORE" "6.0"
else
  warn_check "Quality score computed" false
fi

echo ""
echo "Review Coverage:"
for reviewer in technical editor adversarial audience seo; do
  check "Review: $reviewer" test -f "$STATE_DIR/review-${reviewer}.json"
done

echo ""
echo "================================"
echo "Pass: $PASS | Fail: $FAIL | Warn: $WARN"
if [ "$FAIL" -eq 0 ]; then
  echo "READY TO PUBLISH ✅"
else
  echo "NOT READY — $FAIL checks failed ❌"
fi
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
