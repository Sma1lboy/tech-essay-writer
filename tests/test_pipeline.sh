#!/usr/bin/env bash
# Tests for pipeline-state.sh, intake-materials.sh, taste-memory.sh, aggregate-reviews.sh
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
    echo "FAIL: $desc"
    echo "  expected to contain: $needle"
    echo "  actual: $haystack"
  fi
}

assert_file_exists() {
  local desc="$1" path="$2"
  if [ -f "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — file not found: $path"
  fi
}

# --- pipeline-state.sh tests ---

echo "=== pipeline-state.sh ==="

# Test init
PROJECT="$TMPDIR/test-project"
mkdir -p "$PROJECT"
out=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" "Test Topic")
assert_contains "init returns success" "initialized" "$out"
assert_file_exists "state file created" "$PROJECT/.essay-state/pipeline-state.json"

# Test get-stage
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")
assert_eq "initial stage is intake" "intake" "$stage"

# Test set-stage
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" "research" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")
assert_eq "stage updated to research" "research" "$stage"

# Test invalid stage
if bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" "invalid" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid stage"
else
  PASS=$((PASS + 1))
fi

# Test set-field / get-field
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" "outline_variant" "A" >/dev/null
val=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT" "outline_variant")
assert_eq "set/get field" '"A"' "$val"

# Test read
full=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT")
assert_contains "read contains topic" "Test Topic" "$full"
assert_contains "read contains stage" "research" "$full"

# Test refinement-round
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT" >/dev/null
val=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT" "refinement_round")
assert_eq "refinement round incremented" "1" "$val"

# Test complete
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" complete "$PROJECT" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")
assert_eq "complete sets stage" "complete" "$stage"

# --- intake-materials.sh tests ---

echo "=== intake-materials.sh ==="

PROJECT2="$TMPDIR/test-project-2"
mkdir -p "$PROJECT2"

bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$PROJECT2" >/dev/null
assert_file_exists "materials file created" "$PROJECT2/.essay-state/materials.json"

# Add URL
out=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-url "$PROJECT2" "https://example.com" "Example")
assert_contains "add-url returns id" "src-" "$out"

# Add note
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT2" "My important note" >/dev/null

# Add theme
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-theme "$PROJECT2" "scalability" >/dev/null

# Add angle
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-angle "$PROJECT2" "contrarian view" >/dev/null

# List
listing=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" list "$PROJECT2")
assert_contains "list shows URL" "example.com" "$listing"
assert_contains "list shows note" "My important" "$listing"
assert_contains "list shows theme" "scalability" "$listing"
assert_contains "list shows angle" "contrarian" "$listing"
assert_contains "list shows 2 sources" "2 sources" "$listing"

# Export
exported=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" export "$PROJECT2")
assert_contains "export is valid JSON" "sources" "$exported"

# Clear
bash "$SCRIPT_DIR/scripts/intake-materials.sh" clear "$PROJECT2" >/dev/null
listing=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" list "$PROJECT2")
assert_contains "clear removes sources" "0 sources" "$listing"

# --- taste-memory.sh tests ---

echo "=== taste-memory.sh ==="

# Use a temp home dir to avoid polluting real taste memory
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

out=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "empty taste memory" "No taste memory" "$out"

bash "$SCRIPT_DIR/scripts/taste-memory.sh" record-choice tone "casual" >/dev/null
bash "$SCRIPT_DIR/scripts/taste-memory.sh" record-choice code_density "medium" >/dev/null

out=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "taste shows tone" "casual" "$out"
assert_contains "taste shows code_density" "medium" "$out"

# Get preference
pref=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" get-preference tone)
assert_contains "get-preference returns tone" "casual" "$pref"

# History (empty)
out=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" history)
assert_contains "empty history" "No articles" "$out"

# --- aggregate-reviews.sh tests ---

echo "=== aggregate-reviews.sh ==="

PROJECT3="$TMPDIR/test-project-3"
mkdir -p "$PROJECT3/.essay-state"

# Create mock review files
cat > "$PROJECT3/.essay-state/review-technical.json" << 'EOF'
{
  "reviewer": "technical",
  "rating": "NEEDS_FIXES",
  "summary": "Code examples have issues",
  "issues": [
    {"severity": "critical", "location": "Section 2", "issue": "Code won't compile", "suggestion": "Fix import"},
    {"severity": "minor", "location": "Section 4", "issue": "Typo in variable name", "suggestion": "Rename"}
  ]
}
EOF

cat > "$PROJECT3/.essay-state/review-editor.json" << 'EOF'
{
  "reviewer": "editor",
  "rating": "NEEDS_EDITING",
  "summary": "Good content, flow needs work",
  "issues": [
    {"severity": "major", "location": "Introduction", "issue": "Hook is generic", "suggestion": "Start with the specific problem"}
  ]
}
EOF

cat > "$PROJECT3/.essay-state/review-adversarial.json" << 'EOF'
{
  "reviewer": "adversarial",
  "rating": "VULNERABLE",
  "summary": "Premise is shaky",
  "issues": [
    {"severity": "major", "issue": "Author generalizes from N=1", "suggestion": "Add more data points"}
  ],
  "attacks": [
    {"target": "Main thesis", "attack": "Only works for startups", "severity": "significant", "defense": "Add enterprise examples"}
  ]
}
EOF

cat > "$PROJECT3/.essay-state/review-audience.json" << 'EOF'
{
  "reviewer": "audience",
  "rating": "MEH",
  "summary": "Okay but not shareable"
}
EOF

cat > "$PROJECT3/.essay-state/review-seo.json" << 'EOF'
{
  "reviewer": "seo",
  "rating": "NEEDS_WORK",
  "summary": "Title needs work",
  "issues": [
    {"severity": "minor", "issue": "Title too generic", "suggestion": "Add specific tech name"}
  ]
}
EOF

out=$(bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$PROJECT3")
assert_contains "aggregate shows consensus" "NEEDS" "$out"
assert_contains "aggregate shows critical count" "critical" "$out"
assert_file_exists "panel summary created" "$PROJECT3/.essay-state/review-panel-summary.json"

# Verify panel summary content
summary=$(cat "$PROJECT3/.essay-state/review-panel-summary.json")
assert_contains "summary has ratings" "ratings" "$summary"
assert_contains "summary has prioritized actions" "prioritized_actions" "$summary"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
