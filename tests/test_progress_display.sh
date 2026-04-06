#!/usr/bin/env bash
# Tests for progress-display.sh — pipeline progress visualization
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

assert_not_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected NOT to contain: $needle"
  else
    PASS=$((PASS + 1))
  fi
}

# Helper: create a minimal pipeline state file
create_state() {
  local project="$1" stage="$2"
  shift 2
  # Additional fields as key=value pairs
  local materials_count=0 draft_version=0 refinement_round=0 max_rounds=3
  local completed=false topic="Test Topic" completed_at=""
  while [ $# -gt 0 ]; do
    case "$1" in
      materials_count=*) materials_count="${1#*=}" ;;
      draft_version=*) draft_version="${1#*=}" ;;
      refinement_round=*) refinement_round="${1#*=}" ;;
      max_refinement_rounds=*) max_rounds="${1#*=}" ;;
      completed=*) completed="${1#*=}" ;;
      topic=*) topic="${1#*=}" ;;
      completed_at=*) completed_at="${1#*=}" ;;
    esac
    shift
  done
  mkdir -p "$project/.essay-state"
  python3 -c "
import json, sys
d = {
    'topic': sys.argv[1],
    'stage': sys.argv[2],
    'materials_count': int(sys.argv[3]),
    'draft_version': int(sys.argv[4]),
    'refinement_round': int(sys.argv[5]),
    'max_refinement_rounds': int(sys.argv[6]),
    'completed': sys.argv[7] == 'true',
    'reviews': {}
}
if sys.argv[8]:
    d['completed_at'] = sys.argv[8]
with open(sys.argv[9], 'w') as f:
    json.dump(d, f, indent=2)
" "$topic" "$stage" "$materials_count" "$draft_version" "$refinement_round" "$max_rounds" "$completed" "$completed_at" "$project/.essay-state/pipeline-state.json"
}

# Helper: create a quality-score.json
create_quality() {
  local project="$1" score="$2" readiness="$3" reviews="$4"
  python3 -c "
import json, sys
d = {
    'composite_score': float(sys.argv[1]),
    'readiness': sys.argv[2],
    'reviews_available': int(sys.argv[3]),
    'reviews_expected': 7,
    'dimension_scores': {
        'technical': 8.0,
        'editor': 7.5,
        'adversarial': 6.0
    }
}
with open(sys.argv[4], 'w') as f:
    json.dump(d, f, indent=2)
" "$score" "$readiness" "$reviews" "$project/.essay-state/quality-score.json"
}

echo "=== progress-display.sh: missing state ==="

# Test 1: Missing state directory — text mode
PROJECT="$TMPDIR/no-state"
mkdir -p "$PROJECT"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" 2>&1 || true)
assert_contains "missing state shows not initialized" "not initialized" "$out"

# Test 2: Missing state directory — json mode
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json 2>&1 || true)
assert_contains "missing state json shows error" "not_initialized" "$out"

echo "=== progress-display.sh: intake stage ==="

# Test 3: Intake stage text display
PROJECT="$TMPDIR/intake-proj"
create_state "$PROJECT" "intake" "materials_count=0"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "intake shows INTAKE label" "INTAKE" "$out"
assert_contains "intake shows current indicator" "●" "$out"
assert_contains "intake shows 0%" "0" "$out"
assert_contains "intake shows topic" "Test Topic" "$out"

# Test 4: Intake stage json
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "intake json has stage" '"intake"' "$out"

echo "=== progress-display.sh: research stage ==="

# Test 5: Research stage
PROJECT="$TMPDIR/research-proj"
create_state "$PROJECT" "research" "materials_count=5"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "research shows check for intake" "✓" "$out"
assert_contains "research shows current indicator" "●" "$out"
assert_contains "research shows 5%" "5" "$out"
assert_contains "research shows materials count 5" "5" "$out"

echo "=== progress-display.sh: outline stage ==="

# Test 6: Outline stage
PROJECT="$TMPDIR/outline-proj"
create_state "$PROJECT" "outline" "materials_count=8"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "outline shows 15%" "15" "$out"
assert_contains "outline stage label" "outline" "$out"

echo "=== progress-display.sh: draft stage ==="

# Test 7: Draft stage with draft version
PROJECT="$TMPDIR/draft-proj"
create_state "$PROJECT" "draft" "materials_count=10" "draft_version=2"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "draft shows 25%" "25" "$out"
assert_contains "draft shows draft version 2" "2" "$out"

# Test 8: Draft stage json
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "draft json has completion" "25.0" "$out"

echo "=== progress-display.sh: review stage ==="

# Test 9: Review stage
PROJECT="$TMPDIR/review-proj"
create_state "$PROJECT" "review" "materials_count=10" "draft_version=1"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "review shows 45%" "45" "$out"

echo "=== progress-display.sh: refinement stage ==="

# Test 10: Refinement stage with round info
PROJECT="$TMPDIR/refine-proj"
create_state "$PROJECT" "refinement" "materials_count=10" "draft_version=1" "refinement_round=2" "max_refinement_rounds=3"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "refinement shows round 2/3" "2/3" "$out"

echo "=== progress-display.sh: polish stage ==="

# Test 11: Polish stage
PROJECT="$TMPDIR/polish-proj"
create_state "$PROJECT" "polish" "materials_count=10" "draft_version=3" "refinement_round=3"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "polish shows 85%" "85" "$out"

echo "=== progress-display.sh: complete stage ==="

# Test 12: Complete stage
PROJECT="$TMPDIR/complete-proj"
create_state "$PROJECT" "complete" "materials_count=12" "draft_version=3" "refinement_round=3" "completed=true" "completed_at=2026-04-06T12:00:00Z"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "complete shows 100%" "100" "$out"
assert_contains "complete shows all checks" "✓" "$out"
assert_contains "complete shows completed_at" "2026-04-06" "$out"

# Test 13: Complete stage json
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "complete json shows 100" "100.0" "$out"

echo "=== progress-display.sh: quality display ==="

# Test 14: Text display with quality score
PROJECT="$TMPDIR/quality-proj"
create_state "$PROJECT" "review" "materials_count=10" "draft_version=1"
create_quality "$PROJECT" "7.5" "CLOSE" "5"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "quality shows score" "7.5" "$out"
assert_contains "quality shows readiness" "CLOSE" "$out"
assert_contains "quality shows reviews count" "5/7" "$out"

# Test 15: Verbose shows dimension scores
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --verbose)
assert_contains "verbose shows technical dimension" "technical" "$out"
assert_contains "verbose shows editor dimension" "editor" "$out"

# Test 16: JSON mode with quality
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "json shows quality score" "7.5" "$out"

# Test 17: No quality file shows appropriate message
PROJECT="$TMPDIR/no-quality-proj"
create_state "$PROJECT" "draft" "materials_count=5" "draft_version=1"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "no quality shows no score" "No score available" "$out"

echo "=== progress-display.sh: pipeline arrows ==="

# Test 18: Pipeline display includes arrows
PROJECT="$TMPDIR/arrows-proj"
create_state "$PROJECT" "draft"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "display has arrows" "→" "$out"

echo "=== progress-display.sh: progress bar ==="

# Test 19: Progress bar is present
assert_contains "progress bar present" "Progress:" "$out"

echo "=== progress-display.sh: empty circle indicators ==="

# Test 20: Stages after current show empty circles
PROJECT="$TMPDIR/empty-circles-proj"
create_state "$PROJECT" "intake"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "future stages show empty circles" "○" "$out"

echo "=== progress-display.sh: custom topic display ==="

# Test 21: Custom topic is displayed
PROJECT="$TMPDIR/custom-topic-proj"
create_state "$PROJECT" "research" "topic=Building Scalable APIs"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "custom topic displayed" "Building Scalable APIs" "$out"

echo "=== progress-display.sh: corrupt state file ==="

# Test 22: Corrupt state file handled gracefully (text)
PROJECT="$TMPDIR/corrupt-proj"
mkdir -p "$PROJECT/.essay-state"
echo "not json at all" > "$PROJECT/.essay-state/pipeline-state.json"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" 2>&1 || true)
assert_contains "corrupt state shows error" "ERROR" "$out"

# Test 23: Corrupt state in json mode
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json 2>&1 || true)
assert_contains "corrupt json shows error" "corrupt_state" "$out"

echo "=== progress-display.sh: high quality score ==="

# Test 24: High quality score display
PROJECT="$TMPDIR/high-quality-proj"
create_state "$PROJECT" "polish" "materials_count=15" "draft_version=4" "refinement_round=3"
create_quality "$PROJECT" "9.2" "READY" "7"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT")
assert_contains "high quality shows READY" "READY" "$out"
assert_contains "high quality shows 9.2" "9.2" "$out"
assert_contains "high quality shows 7/7 reviews" "7/7" "$out"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
