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
  local desc="$1" condition="$2"
  if eval "$condition"; then
    PASS=$((PASS + 1))
    echo "  ✓ $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  ✗ $desc"
  fi
}

warn_check() {
  local desc="$1" condition="$2"
  if eval "$condition"; then
    PASS=$((PASS + 1))
    echo "  ✓ $desc"
  else
    WARN=$((WARN + 1))
    echo "  ⚠ $desc"
  fi
}

echo "=== Pre-Publish Checklist ==="
echo ""

echo "Pipeline Completion:"
check "Pipeline state exists" "[ -f '$STATE_DIR/pipeline-state.json' ]"
check "Pipeline marked complete" "python3 -c \"import json; assert json.load(open('$STATE_DIR/pipeline-state.json')).get('completed')\" 2>/dev/null"

echo ""
echo "Content Artifacts:"
check "Internal version exists" "[ -f '$STATE_DIR/final-internal.md' ]"
check "External version exists" "[ -f '$STATE_DIR/final-external.md' ]"
check "Social package exists" "[ -f '$STATE_DIR/social-package.json' ]"

echo ""
echo "Internal version:"
if [ -f "$STATE_DIR/final-internal.md" ]; then
  WORD_COUNT=$(wc -w < "$STATE_DIR/final-internal.md" | tr -d ' ')
  check "Internal version > 500 words ($WORD_COUNT words)" "[ $WORD_COUNT -gt 500 ]"
  check "Has title (# heading)" "head -5 '$STATE_DIR/final-internal.md' | grep -q '^#'"
  warn_check "Has TL;DR section" "grep -qi 'tl;dr\|tldr\|summary' '$STATE_DIR/final-internal.md'"
fi

echo ""
echo "External version:"
if [ -f "$STATE_DIR/final-external.md" ]; then
  WORD_COUNT=$(wc -w < "$STATE_DIR/final-external.md" | tr -d ' ')
  check "External version > 500 words ($WORD_COUNT words)" "[ $WORD_COUNT -gt 500 ]"
  check "Has title (# heading)" "head -5 '$STATE_DIR/final-external.md' | grep -q '^#'"
  warn_check "Has About the Author" "grep -qi 'about the author\|about me\|bio' '$STATE_DIR/final-external.md'"
  warn_check "Has code examples" "grep -q '\`\`\`' '$STATE_DIR/final-external.md'"
fi

echo ""
echo "Social package:"
if [ -f "$STATE_DIR/social-package.json" ]; then
  warn_check "Has Twitter thread" "python3 -c \"import json; assert json.load(open('$STATE_DIR/social-package.json')).get('twitter_thread')\" 2>/dev/null"
  warn_check "Has LinkedIn post" "python3 -c \"import json; assert json.load(open('$STATE_DIR/social-package.json')).get('linkedin_post')\" 2>/dev/null"
  warn_check "Has HN title" "python3 -c \"import json; assert json.load(open('$STATE_DIR/social-package.json')).get('hn_title')\" 2>/dev/null"
fi

echo ""
echo "Quality Gate:"
if [ -f "$STATE_DIR/quality-score.json" ]; then
  SCORE=$(python3 -c "import json; print(json.load(open('$STATE_DIR/quality-score.json')).get('composite_score', 0))")
  READINESS=$(python3 -c "import json; print(json.load(open('$STATE_DIR/quality-score.json')).get('readiness', 'UNKNOWN'))")
  check "Quality score ≥ 6.0 (score: $SCORE, readiness: $READINESS)" "python3 -c \"assert $SCORE >= 6.0\""
else
  warn_check "Quality score computed" "false"
fi

echo ""
echo "Review Coverage:"
for reviewer in technical editor adversarial audience seo; do
  check "Review: $reviewer" "[ -f '$STATE_DIR/review-${reviewer}.json' ]"
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
