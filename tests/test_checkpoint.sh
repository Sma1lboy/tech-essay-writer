#!/usr/bin/env bash
# Tests for checkpoint.sh — state checkpoint and recovery system
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

assert_file_exists() {
  local desc="$1" path="$2"
  if [ -f "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — file not found: $path"
  fi
}

assert_file_not_exists() {
  local desc="$1" path="$2"
  if [ ! -f "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — file should not exist: $path"
  fi
}

assert_dir_exists() {
  local desc="$1" path="$2"
  if [ -d "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — directory not found: $path"
  fi
}

CHECKPOINT_SCRIPT="$SCRIPT_DIR/scripts/checkpoint.sh"
PIPELINE_SCRIPT="$SCRIPT_DIR/scripts/pipeline-state.sh"

# Override HOME to isolate tests
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

echo "=== checkpoint.sh ==="

# ============================================================
# Setup: create a project with pipeline state and some files
# ============================================================
PROJECT="$TMPDIR/test-project"
mkdir -p "$PROJECT"
bash "$PIPELINE_SCRIPT" init "$PROJECT" "Checkpoint Test Topic" >/dev/null

# Add some extra state files
echo '{"sections":["intro","body","conclusion"]}' > "$PROJECT/.essay-state/outline-A.json"
echo "# Draft v1" > "$PROJECT/.essay-state/draft-v1.md"
echo '{"reviewer":"technical","rating":"PASS"}' > "$PROJECT/.essay-state/review-technical.json"

# ============================================================
# Test 1: save creates checkpoint directory
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" save "$PROJECT" "manual-save-1")
assert_contains "save returns checkpoint id" "ckpt-" "$out"
assert_dir_exists "checkpoints dir created" "$PROJECT/.essay-state/checkpoints"
assert_file_exists "index.json created" "$PROJECT/.essay-state/checkpoints/index.json"

# Extract the checkpoint id from output
CKPT_ID1=$(echo "$out" | grep -o 'ckpt-[a-z0-9-]*')

# ============================================================
# Test 2: save creates tar.gz archive
# ============================================================
assert_file_exists "archive created" "$PROJECT/.essay-state/checkpoints/${CKPT_ID1}.tar.gz"

# ============================================================
# Test 3: save output includes label
# ============================================================
assert_contains "save output includes label" "manual-save-1" "$out"

# ============================================================
# Test 4: save output includes stage
# ============================================================
assert_contains "save output includes stage" "intake" "$out"

# ============================================================
# Test 5: save output includes file count
# ============================================================
assert_contains "save output includes files count" "files" "$out"

# ============================================================
# Test 6: index.json contains correct metadata
# ============================================================
idx_label=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[0]['label'])")
assert_eq "index label matches" "manual-save-1" "$idx_label"
idx_stage=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[0]['stage'])")
assert_eq "index stage matches" "intake" "$idx_stage"
idx_id=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[0]['id'])")
assert_eq "index id matches" "$CKPT_ID1" "$idx_id"

# ============================================================
# Test 7: index entry has timestamp
# ============================================================
idx_ts=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[0]['timestamp'])")
assert_contains "index has timestamp" "T" "$idx_ts"

# ============================================================
# Test 8: index entry has files_count
# ============================================================
idx_fc=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[0]['files_count'])")
# 4 files: pipeline-state.json, outline-A.json, draft-v1.md, review-technical.json
assert_eq "index files_count is 4" "4" "$idx_fc"

# ============================================================
# Test 9: list command shows checkpoints
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" list "$PROJECT")
assert_contains "list shows checkpoint id" "$CKPT_ID1" "$out"
assert_contains "list shows label" "manual-save-1" "$out"
assert_contains "list shows stage" "intake" "$out"

# ============================================================
# Test 10: list on empty project shows no checkpoints
# ============================================================
EMPTY_PROJECT="$TMPDIR/empty-project"
mkdir -p "$EMPTY_PROJECT/.essay-state"
out=$(bash "$CHECKPOINT_SCRIPT" list "$EMPTY_PROJECT")
assert_contains "empty list message" "No checkpoints" "$out"

# ============================================================
# Test 11: save with default label (no label arg)
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" save "$PROJECT")
CKPT_ID2=$(echo "$out" | grep -o 'ckpt-[a-z0-9-]*' | head -1)
# Default label should be the checkpoint id itself
idx_label2=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(next(e['label'] for e in entries if e['id']=='$CKPT_ID2'))")
assert_eq "default label is checkpoint id" "$CKPT_ID2" "$idx_label2"

# ============================================================
# Test 12: multiple saves accumulate in index
# ============================================================
idx_count=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.essay-state/checkpoints/index.json'))))")
assert_eq "index has 2 entries" "2" "$idx_count"

# ============================================================
# Test 13: restore overwrites current files
# ============================================================
# Modify a file after checkpoint
echo '{"sections":["modified"]}' > "$PROJECT/.essay-state/outline-A.json"
# Verify modification
modified=$(python3 -c "import json; print(json.load(open('$PROJECT/.essay-state/outline-A.json'))['sections'][0])")
assert_eq "file was modified" "modified" "$modified"
# Restore first checkpoint
out=$(bash "$CHECKPOINT_SCRIPT" restore "$PROJECT" "$CKPT_ID1")
assert_contains "restore output includes id" "$CKPT_ID1" "$out"

# ============================================================
# Test 14: restored files have original content
# ============================================================
restored=$(python3 -c "import json; print(json.load(open('$PROJECT/.essay-state/outline-A.json'))['sections'][0])")
assert_eq "outline restored to original" "intro" "$restored"

# ============================================================
# Test 15: restore output includes label
# ============================================================
assert_contains "restore output includes label" "manual-save-1" "$out"

# ============================================================
# Test 16: restore with nonexistent id fails
# ============================================================
if bash "$CHECKPOINT_SCRIPT" restore "$PROJECT" "ckpt-nonexistent" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: restore should fail for nonexistent checkpoint"
else
  PASS=$((PASS + 1))
fi

# ============================================================
# Test 17: delete removes checkpoint
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" delete "$PROJECT" "$CKPT_ID2")
assert_contains "delete output includes id" "$CKPT_ID2" "$out"
assert_file_not_exists "archive removed" "$PROJECT/.essay-state/checkpoints/${CKPT_ID2}.tar.gz"

# ============================================================
# Test 18: delete removes entry from index
# ============================================================
idx_count=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.essay-state/checkpoints/index.json'))))")
assert_eq "index has 1 entry after delete" "1" "$idx_count"

# ============================================================
# Test 19: delete with nonexistent id fails
# ============================================================
if bash "$CHECKPOINT_SCRIPT" delete "$PROJECT" "ckpt-nonexistent" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: delete should fail for nonexistent checkpoint"
else
  PASS=$((PASS + 1))
fi

# ============================================================
# Test 20: auto-save uses pre-{stage} as label
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" auto-save "$PROJECT")
assert_contains "auto-save label is pre-intake" "pre-intake" "$out"

# ============================================================
# Test 21: auto-save after stage change uses new stage
# ============================================================
bash "$PIPELINE_SCRIPT" set-stage "$PROJECT" "research" >/dev/null
# After set-stage, the stage is now "research"
out=$(bash "$CHECKPOINT_SCRIPT" auto-save "$PROJECT")
assert_contains "auto-save label is pre-research" "pre-research" "$out"

# ============================================================
# Test 22: save on project without .essay-state fails
# ============================================================
NO_STATE="$TMPDIR/no-state-project"
mkdir -p "$NO_STATE"
if bash "$CHECKPOINT_SCRIPT" save "$NO_STATE" "test" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: save should fail without .essay-state dir"
else
  PASS=$((PASS + 1))
fi

# ============================================================
# Test 23: save on empty .essay-state fails
# ============================================================
EMPTY_STATE="$TMPDIR/empty-state-project"
mkdir -p "$EMPTY_STATE/.essay-state"
if bash "$CHECKPOINT_SCRIPT" save "$EMPTY_STATE" "test" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: save should fail with empty .essay-state"
else
  PASS=$((PASS + 1))
fi

# ============================================================
# Test 24: archive does not contain checkpoints/ directory
# ============================================================
# List archive contents and verify no checkpoints/ entries
archive_contents=$(tar -tzf "$PROJECT/.essay-state/checkpoints/${CKPT_ID1}.tar.gz")
if echo "$archive_contents" | grep -q "checkpoints"; then
  FAIL=$((FAIL + 1)); echo "FAIL: archive should not contain checkpoints dir"
else
  PASS=$((PASS + 1))
fi

# ============================================================
# Test 25: archive contains expected files
# ============================================================
assert_contains "archive has pipeline-state.json" "pipeline-state.json" "$archive_contents"
assert_contains "archive has outline-A.json" "outline-A.json" "$archive_contents"
assert_contains "archive has draft-v1.md" "draft-v1.md" "$archive_contents"

# ============================================================
# Test 26: usage displayed with no args
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" 2>&1 || true)
assert_contains "usage shown with no args" "Usage" "$out"

# ============================================================
# Test 27: usage displayed with invalid command
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" invalid-cmd "$PROJECT" 2>&1 || true)
assert_contains "usage shown with invalid command" "Usage" "$out"

# ============================================================
# Test 28: pipeline-state set-stage triggers auto-save
# ============================================================
# Count checkpoints before stage change
before_count=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.essay-state/checkpoints/index.json'))))")
bash "$PIPELINE_SCRIPT" set-stage "$PROJECT" "outline" >/dev/null
after_count=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.essay-state/checkpoints/index.json'))))")
assert_eq "set-stage created a new checkpoint" "$((before_count + 1))" "$after_count"

# ============================================================
# Test 29: auto-save checkpoint from set-stage has pre-{stage} label
# ============================================================
# The auto-save happens BEFORE the stage transition, so the label should reflect
# the stage at the time of save (research), not the new stage (outline)
last_label=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(entries[-1]['label'])")
assert_eq "auto-save from set-stage has pre-research label" "pre-research" "$last_label"

# ============================================================
# Test 30: restore then re-save round-trip preserves data
# ============================================================
# Save current state
bash "$CHECKPOINT_SCRIPT" save "$PROJECT" "round-trip-test" >/dev/null
# Get current pipeline topic
topic_before=$(python3 -c "import json; print(json.load(open('$PROJECT/.essay-state/pipeline-state.json'))['topic'])")
# Modify the topic
bash "$PIPELINE_SCRIPT" set-field "$PROJECT" "topic" "Modified Topic" >/dev/null
topic_modified=$(python3 -c "import json; print(json.load(open('$PROJECT/.essay-state/pipeline-state.json'))['topic'])")
assert_eq "topic was modified" "Modified Topic" "$topic_modified"
# Get the round-trip checkpoint id
RT_ID=$(python3 -c "import json; entries=json.load(open('$PROJECT/.essay-state/checkpoints/index.json')); print(next(e['id'] for e in entries if e['label']=='round-trip-test'))")
# Restore
bash "$CHECKPOINT_SCRIPT" restore "$PROJECT" "$RT_ID" >/dev/null
topic_after=$(python3 -c "import json; print(json.load(open('$PROJECT/.essay-state/pipeline-state.json'))['topic'])")
assert_eq "topic restored to original after round-trip" "$topic_before" "$topic_after"

# ============================================================
# Test 31: list shows correct count of checkpoints
# ============================================================
out=$(bash "$CHECKPOINT_SCRIPT" list "$PROJECT")
total_count=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.essay-state/checkpoints/index.json'))))")
assert_contains "list shows checkpoint count" "${total_count} checkpoint(s)" "$out"

# ============================================================
# Test 32: checkpoint id format is ckpt-{timestamp}-{suffix}
# ============================================================
id_format_ok=$(python3 -c "
import re
id = '$CKPT_ID1'
print('yes' if re.match(r'ckpt-\d+-[a-z0-9]{6}', id) else 'no')
")
assert_eq "checkpoint id has correct format" "yes" "$id_format_ok"

# ============================================================
# Summary
# ============================================================

echo ""
echo "========================================"
echo "test_checkpoint: $((PASS + FAIL)) tests | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
