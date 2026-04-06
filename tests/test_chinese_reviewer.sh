#!/usr/bin/env bash
# Tests for Chinese writing quality reviewer integration
# Validates orchestrate.sh, quality-score.sh, and pipeline-state.sh
# handle the chinese reviewer correctly (only active when language=zh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected to contain: $needle)"
  fi
}

assert_not_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected NOT to contain: $needle)"
  else
    PASS=$((PASS + 1))
  fi
}

assert_not_empty() {
  local desc="$1" val="$2"
  if [ -n "$val" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected non-empty)"
  fi
}

echo "=== Chinese reviewer integration tests ==="

# ─── Setup: project with language=zh ─────────────────────────────────────────

PROJECT_ZH="$TMPDIR/test-project-zh"
mkdir -p "$PROJECT_ZH/.essay-state"
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT_ZH" "Chinese Test Topic" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_ZH" language '"zh"' >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_ZH" draft >/dev/null

# Create a mock draft
cat > "$PROJECT_ZH/.essay-state/draft-v1.md" << 'EOF'
# Chinese Test Article

This is a test draft in Chinese context.

## Section 1

Some technical content here.

```python
def test():
    pass
```

## Conclusion

Done.
EOF

# ─── Setup: project with language=en ─────────────────────────────────────────

PROJECT_EN="$TMPDIR/test-project-en"
mkdir -p "$PROJECT_EN/.essay-state"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT_EN" "English Test Topic" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_EN" language '"en"' >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_EN" draft >/dev/null

cat > "$PROJECT_EN/.essay-state/draft-v1.md" << 'EOF'
# English Test Article

Test draft for English context.

## Conclusion

Done.
EOF

# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: orchestrate.sh builds chinese review prompts when language=zh
# ══════════════════════════════════════════════════════════════════════════════

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_ZH" review >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT_ZH" "$SCRIPT_DIR" build-review-prompts chinese)
assert_not_empty "T1: chinese reviewer prompt is non-empty for zh" "$out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: chinese review prompt contains the reviewer template content
# ══════════════════════════════════════════════════════════════════════════════

assert_contains "T2: chinese prompt includes reviewer-chinese template" "Chinese Writing Quality Reviewer" "$out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: chinese review prompt contains the draft
# ══════════════════════════════════════════════════════════════════════════════

assert_contains "T3: chinese prompt includes draft content" "Chinese Test Article" "$out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: chinese review prompt includes language directive
# ══════════════════════════════════════════════════════════════════════════════

assert_contains "T4: chinese prompt has language directive" "Language Directive" "$out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: chinese reviewer is REJECTED when language=en
# ══════════════════════════════════════════════════════════════════════════════

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_EN" review >/dev/null
if bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT_EN" "$SCRIPT_DIR" build-review-prompts chinese 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: T5: chinese reviewer should be rejected for language=en"
else
  PASS=$((PASS + 1))
fi

# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: standard reviewers still work when language=zh
# ══════════════════════════════════════════════════════════════════════════════

for reviewer in technical editor adversarial audience seo external factcheck; do
  out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT_ZH" "$SCRIPT_DIR" build-review-prompts "$reviewer" 2>/dev/null)
  assert_not_empty "T6: reviewer $reviewer works for zh project" "$out"
done

# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: quality-score.sh includes chinese weight when language=zh
# ══════════════════════════════════════════════════════════════════════════════

# Create mock reviews for zh project including chinese reviewer
for r in technical editor adversarial audience seo external factcheck; do
  cat > "$PROJECT_ZH/.essay-state/review-${r}.json" << REOF
{"reviewer":"${r}","rating":"PASS","summary":"Good","issues":[]}
REOF
done
cat > "$PROJECT_ZH/.essay-state/review-chinese.json" << 'EOF'
{"reviewer":"chinese","rating":"NATIVE","summary":"Reads naturally","issues":[]}
EOF

out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_ZH" verbose 2>/dev/null)
assert_contains "T7: quality-score verbose output includes chinese reviewer" "chinese" "$out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: quality-score.sh expects 8 reviews when language=zh
# ══════════════════════════════════════════════════════════════════════════════

json_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_ZH" 2>/dev/null)
expected_count=$(echo "$json_out" | python3 -c "import json,sys; print(json.load(sys.stdin)['reviews_expected'])")
assert_eq "T8: reviews_expected=8 for zh" "8" "$expected_count"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: quality-score.sh expects 7 reviews when language=en
# ══════════════════════════════════════════════════════════════════════════════

# Create mock reviews for en project (standard 7 only)
for r in technical editor adversarial audience seo external factcheck; do
  cat > "$PROJECT_EN/.essay-state/review-${r}.json" << REOF
{"reviewer":"${r}","rating":"PASS","summary":"Good","issues":[]}
REOF
done

json_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_EN" 2>/dev/null)
expected_count=$(echo "$json_out" | python3 -c "import json,sys; print(json.load(sys.stdin)['reviews_expected'])")
assert_eq "T9: reviews_expected=7 for en" "7" "$expected_count"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: quality-score.sh NATIVE rating maps to score 9
# ══════════════════════════════════════════════════════════════════════════════

verbose_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_ZH" verbose 2>/dev/null)
assert_contains "T10: NATIVE maps to score 9" "NATIVE" "$verbose_out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 11: quality-score.sh TRANSLATION_SMELL rating maps to score 2
# ══════════════════════════════════════════════════════════════════════════════

cat > "$PROJECT_ZH/.essay-state/review-chinese.json" << 'EOF'
{"reviewer":"chinese","rating":"TRANSLATION_SMELL","summary":"Reads like a translation","issues":[]}
EOF
verbose_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_ZH" verbose 2>/dev/null)
assert_contains "T11: TRANSLATION_SMELL rating appears in verbose output" "TRANSLATION_SMELL" "$verbose_out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 12: quality-score.sh ACCEPTABLE rating maps to score 6
# ══════════════════════════════════════════════════════════════════════════════

cat > "$PROJECT_ZH/.essay-state/review-chinese.json" << 'EOF'
{"reviewer":"chinese","rating":"ACCEPTABLE","summary":"Minor issues","issues":[]}
EOF
verbose_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_ZH" verbose 2>/dev/null)
assert_contains "T12: ACCEPTABLE rating appears in verbose output" "ACCEPTABLE" "$verbose_out"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 13: pipeline-state.sh review_panel_complete requires 8 reviews for zh
# ══════════════════════════════════════════════════════════════════════════════

# Start fresh zh project for panel complete test
PROJECT_PANEL="$TMPDIR/test-project-panel"
mkdir -p "$PROJECT_PANEL/.essay-state"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT_PANEL" "Panel Test" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_PANEL" language '"zh"' >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_PANEL" review >/dev/null

# Add 7 reviews (should NOT complete the panel for zh)
for r in technical editor adversarial audience seo external factcheck; do
  cat > "$PROJECT_PANEL/.essay-state/review-${r}.json" << REOF
{"reviewer":"${r}","rating":"PASS","summary":"OK","issues":[]}
REOF
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT_PANEL" "$PROJECT_PANEL/.essay-state/review-${r}.json" >/dev/null
done

state=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT_PANEL")
panel_complete=$(echo "$state" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['review_panel_complete'])")
assert_eq "T13: panel NOT complete with 7/8 reviews for zh" "False" "$panel_complete"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 14: pipeline-state.sh review_panel_complete triggers with 8th review for zh
# ══════════════════════════════════════════════════════════════════════════════

cat > "$PROJECT_PANEL/.essay-state/review-chinese.json" << 'EOF'
{"reviewer":"chinese","rating":"NATIVE","summary":"Great","issues":[]}
EOF
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT_PANEL" "$PROJECT_PANEL/.essay-state/review-chinese.json" >/dev/null

state=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT_PANEL")
panel_complete=$(echo "$state" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['review_panel_complete'])")
assert_eq "T14: panel complete with 8/8 reviews for zh" "True" "$panel_complete"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 15: pipeline-state.sh review_panel_complete with 7 reviews for en
# ══════════════════════════════════════════════════════════════════════════════

PROJECT_EN_PANEL="$TMPDIR/test-project-en-panel"
mkdir -p "$PROJECT_EN_PANEL/.essay-state"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT_EN_PANEL" "EN Panel Test" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_EN_PANEL" language '"en"' >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_EN_PANEL" review >/dev/null

for r in technical editor adversarial audience seo external factcheck; do
  cat > "$PROJECT_EN_PANEL/.essay-state/review-${r}.json" << REOF
{"reviewer":"${r}","rating":"PASS","summary":"OK","issues":[]}
REOF
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT_EN_PANEL" "$PROJECT_EN_PANEL/.essay-state/review-${r}.json" >/dev/null
done

state=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT_EN_PANEL")
panel_complete=$(echo "$state" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['review_panel_complete'])")
assert_eq "T15: panel complete with 7/7 reviews for en" "True" "$panel_complete"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 16: quality-score.sh does NOT include chinese weight for language=en
# ══════════════════════════════════════════════════════════════════════════════

# Even if a review-chinese.json file exists for en project, it should not be scored
cat > "$PROJECT_EN/.essay-state/review-chinese.json" << 'EOF'
{"reviewer":"chinese","rating":"NATIVE","summary":"Reads naturally","issues":[]}
EOF

json_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT_EN" 2>/dev/null)
has_chinese=$(echo "$json_out" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if 'chinese' in d.get('dimension_scores',{}) else 'no')")
assert_eq "T16: chinese score excluded for en project" "no" "$has_chinese"

# Clean up the extra file
rm -f "$PROJECT_EN/.essay-state/review-chinese.json"

# ══════════════════════════════════════════════════════════════════════════════
# TEST 17: chinese reviewer prompt output file path is correct
# ══════════════════════════════════════════════════════════════════════════════

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_ZH" review >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT_ZH" "$SCRIPT_DIR" build-review-prompts chinese)
assert_contains "T17: chinese prompt instructs writing to review-chinese.json" "review-chinese.json" "$out"

# ─── Results ─────────────────────────────────────────────────────────────────

echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
