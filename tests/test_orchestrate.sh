#!/usr/bin/env bash
# Integration tests for orchestrate.sh — validates full pipeline flow
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

assert_not_empty() {
  local desc="$1" val="$2"
  if [ -n "$val" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected non-empty)"
  fi
}

PROJECT="$TMPDIR/test-project"
mkdir -p "$PROJECT/.essay-state"
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

echo "=== orchestrate.sh integration tests ==="

# --- Status before init ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" status 2>/dev/null)
assert_contains "uninit status" "NOT_INITIALIZED" "$out"

# --- Init pipeline ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" "Test Topic" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$PROJECT" >/dev/null

# --- Status after init ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" status)
assert_contains "status shows stage" "intake" "$out"
assert_contains "status shows topic" "Test Topic" "$out"

# --- next-stage: intake with no materials → intake ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage empty materials = intake" "intake" "$stage"

# --- Add materials, check next-stage ---
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT" "Important note" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage with materials = research" "research" "$stage"

# --- Intake summary ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-intake-summary)
assert_contains "intake summary shows sources" "Sources: 1" "$out"
assert_contains "intake summary shows note" "Important note" "$out"

# --- Advance to research ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" research >/dev/null

# --- build-research-prompt ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-research-prompt)
assert_contains "research prompt has template" "Research Synthesis Agent" "$out"
assert_contains "research prompt has materials" "Important note" "$out"

# --- next-stage: research without synthesis = research ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage no synthesis = research" "research" "$stage"

# --- Create mock research synthesis ---
cat > "$PROJECT/.essay-state/research-synthesis.json" << 'EOF'
{
  "thesis": "Test thesis statement",
  "unique_angle": "Novel perspective on testing",
  "evidence_map": [],
  "knowledge_gaps": [],
  "competitive_landscape": [],
  "recommended_depth": "intermediate"
}
EOF

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage with synthesis = outline" "outline" "$stage"

# --- Advance to outline ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" outline >/dev/null

# --- build-outline-prompts for each variant ---
for v in A B C; do
  out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-outline-prompts "$v")
  assert_contains "outline $v has template" "Outline Generator Agent" "$out"
  assert_contains "outline $v has variant" "Variant: $v" "$out"
  assert_contains "outline $v has thesis" "Test thesis" "$out"
done

# --- next-stage: outline without outlines = outline ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage no outlines = outline" "outline" "$stage"

# --- Create mock outlines ---
for v in A B C; do
  cat > "$PROJECT/.essay-state/outline-${v}.json" << EOF
{
  "variant": "$v",
  "title": "Test Title Variant $v",
  "hook": "An intriguing opening for variant $v",
  "sections": [{"title": "Section 1", "key_points": ["Point 1"]}],
  "target_word_count": 2000
}
EOF
done

# --- next-stage: outlines exist but no choice = outline_choice ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage outlines but no choice = outline_choice" "outline_choice" "$stage"

# --- Set outline choice ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" outline_variant "B" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage with choice = draft" "draft" "$stage"

# --- Advance to draft ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" draft >/dev/null

# --- build-writer-prompt ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-writer-prompt B)
assert_contains "writer prompt has template" "Draft Writer Agent" "$out"
assert_contains "writer prompt has chosen outline" "Variant B" "$out"

# --- next-stage: draft without draft file = draft ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage no draft = draft" "draft" "$stage"

# --- Create mock draft ---
cat > "$PROJECT/.essay-state/draft-v1.md" << 'EOF'
# Test Article

This is a test draft with enough content to be reviewed.

## Section 1

Some technical content here about testing patterns.

```python
def test_example():
    assert True
```

## Conclusion

Testing is important.
EOF

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage with draft = review" "review" "$stage"

# --- Advance to review ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" review >/dev/null

# --- build-review-prompts for each reviewer ---
for reviewer in technical editor adversarial audience seo; do
  out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-review-prompts "$reviewer")
  assert_not_empty "review prompt $reviewer is non-empty" "$out"
  assert_contains "review prompt $reviewer has draft" "Test Article" "$out"
done

# --- Invalid reviewer ---
if bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-review-prompts "invalid" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid reviewer"
else
  PASS=$((PASS + 1))
fi

# --- Create mock reviews ---
cat > "$PROJECT/.essay-state/review-technical.json" << 'EOF'
{"reviewer":"technical","rating":"PASS","summary":"Looks good","issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-editor.json" << 'EOF'
{"reviewer":"editor","rating":"NEEDS_EDITING","summary":"Needs work","issues":[{"severity":"major","issue":"Hook is weak"}]}
EOF
cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"VULNERABLE","summary":"Weak premise","attacks":[{"target":"thesis","attack":"N=1","severity":"significant"}],"issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-audience.json" << 'EOF'
{"reviewer":"audience","rating":"MEH","summary":"Not shareable","issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-seo.json" << 'EOF'
{"reviewer":"seo","rating":"NEEDS_WORK","summary":"Title boring","issues":[{"severity":"minor","issue":"Title generic"}]}
EOF

# Mark reviews in pipeline state
for r in review-technical review-editor review-adversarial review-audience review-seo; do
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT" "$PROJECT/.essay-state/${r}.json" >/dev/null
done

# --- Aggregate reviews ---
agg_out=$(bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$PROJECT")
assert_contains "aggregate has consensus" "NEEDS" "$agg_out"

# --- next-stage: review with panel complete = refinement ---
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage panel complete = refinement" "refinement" "$stage"

# --- Advance to refinement ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" refinement >/dev/null

# --- build-refiner-prompt ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-refiner-prompt 1)
assert_contains "refiner prompt has template" "Refinement Agent" "$out"
assert_contains "refiner prompt has draft" "Test Article" "$out"
assert_contains "refiner prompt has round" "Round: 1" "$out"

# --- check-convergence: VULNERABLE = CONTINUE ---
result=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 1)
assert_eq "convergence check round 1 = CONTINUE" "CONTINUE" "$result"

# --- Simulate convergence: update adversarial to SOLID ---
cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"SOLID","summary":"Article is strong","attacks":[],"issues":[]}
EOF
result=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 2)
assert_eq "convergence SOLID = CONVERGED" "CONVERGED" "$result"

# --- Max rounds check ---
result=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 3)
assert_eq "convergence round 3 = MAX_ROUNDS (or CONVERGED)" "CONVERGED" "$result"

# --- build-format-prompts ---
for fmt in internal external; do
  out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts "$fmt")
  assert_not_empty "format prompt $fmt is non-empty" "$out"
  assert_contains "format prompt $fmt has draft" "Test Article" "$out"
done

# --- Invalid format ---
if bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts "invalid" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid format"
else
  PASS=$((PASS + 1))
fi

# --- Polish stage next-stage ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" polish >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage polish without finals = polish" "polish" "$stage"

# Create mock final files
echo "Internal version" > "$PROJECT/.essay-state/final-internal.md"
echo "External version" > "$PROJECT/.essay-state/final-external.md"
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage with finals = complete" "complete" "$stage"

# --- Complete ---
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" complete "$PROJECT" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "next-stage completed = complete" "complete" "$stage"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
