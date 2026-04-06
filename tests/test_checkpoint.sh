#!/usr/bin/env bash
# Tests for checkpoint.sh, pipeline-state.sh auto-snapshot, and orchestrate.sh retry/resume
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Temp home to avoid polluting real config
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME/.tech-essay-writer"

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

# Helper: create a test project with initialized pipeline
setup_project() {
  local name="$1" topic="${2:-Test Topic}"
  local project="$TMPDIR/$name"
  mkdir -p "$project"
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$project" "$topic" >/dev/null
  echo "$project"
}

# Count checkpoint directories (excluding .tmp- dirs)
count_checkpoints() {
  local project="$1"
  local ckpt_base="$project/.essay-state/checkpoints"
  if [ ! -d "$ckpt_base" ]; then
    echo "0"
    return
  fi
  local count=0
  for d in "$ckpt_base"/*/; do
    [ -d "$d" ] || continue
    local name
    name=$(basename "$d")
    [[ "$name" == .tmp-* ]] && continue
    count=$((count + 1))
  done
  echo "$count"
}

# ============================================================
# checkpoint.sh snapshot tests
# ============================================================

echo "=== checkpoint.sh snapshot ==="

# Test 1: snapshot creates checkpoint dir
P=$(setup_project "snap1")
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P")
assert_contains "snapshot output has Checkpoint" "Checkpoint:" "$out"
assert_dir_exists "checkpoints dir created" "$P/.essay-state/checkpoints"
n=$(count_checkpoints "$P")
assert_eq "one checkpoint created" "1" "$n"

# Test 2: snapshot with explicit label
P=$(setup_project "snap2")
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "my-label")
assert_contains "snapshot uses label" "my-label" "$out"

# Test 3: snapshot with no label uses current stage
P=$(setup_project "snap3")
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P")
assert_contains "snapshot uses stage as label" "intake" "$out"

# Test 4: snapshot copies pipeline-state.json
P=$(setup_project "snap4")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test" >/dev/null
ckpt_dir=$(ls -d "$P/.essay-state/checkpoints"/test-* 2>/dev/null | head -1)
assert_file_exists "checkpoint has pipeline-state.json" "$ckpt_dir/pipeline-state.json"

# Test 5: snapshot doesn't copy checkpoints/ subdir
P=$(setup_project "snap5")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "first" >/dev/null
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "second" >/dev/null
ckpt_dir=$(ls -d "$P/.essay-state/checkpoints"/second-* 2>/dev/null | head -1)
if [ -d "$ckpt_dir/checkpoints" ]; then
  FAIL=$((FAIL + 1)); echo "FAIL: checkpoint should not contain checkpoints/ subdir"
else
  PASS=$((PASS + 1))
fi

# Test 6: snapshot with no state dir returns error
P="$TMPDIR/snap6-nostate"
mkdir -p "$P"
if bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error with no state dir"
else
  PASS=$((PASS + 1))
fi

# Test 7: snapshot with empty state dir returns error
P="$TMPDIR/snap7-empty"
mkdir -p "$P/.essay-state"
if bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error with empty state dir"
else
  PASS=$((PASS + 1))
fi

# Test 8: multiple snapshots create separate directories
P=$(setup_project "snap8")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "a" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "b" >/dev/null
n=$(count_checkpoints "$P")
assert_eq "two checkpoints created" "2" "$n"

# Test 9: snapshot preserves file contents exactly
P=$(setup_project "snap9")
echo '{"extra":"data"}' > "$P/.essay-state/extra.json"
original_state=$(cat "$P/.essay-state/pipeline-state.json")
original_extra=$(cat "$P/.essay-state/extra.json")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "preserve" >/dev/null
ckpt_dir=$(ls -d "$P/.essay-state/checkpoints"/preserve-* 2>/dev/null | head -1)
ckpt_state=$(cat "$ckpt_dir/pipeline-state.json")
ckpt_extra=$(cat "$ckpt_dir/extra.json")
assert_eq "state preserved exactly" "$original_state" "$ckpt_state"
assert_eq "extra preserved exactly" "$original_extra" "$ckpt_extra"

# Test 10: snapshot output includes file count
P=$(setup_project "snap10")
echo '{"test":true}' > "$P/.essay-state/materials.json"
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "count")
assert_contains "output has file count" "2 files" "$out"

# ============================================================
# checkpoint.sh list tests
# ============================================================

echo "=== checkpoint.sh list ==="

# Test 11: list with no checkpoints dir
P="$TMPDIR/list1"
mkdir -p "$P/.essay-state"
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list no dir shows no checkpoints" "No checkpoints" "$out"

# Test 12: list with empty checkpoints dir
P="$TMPDIR/list2"
mkdir -p "$P/.essay-state/checkpoints"
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list empty dir shows no checkpoints" "No checkpoints" "$out"

# Test 13: list with one checkpoint
P=$(setup_project "list3")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list shows 1 checkpoint" "1 checkpoint" "$out"
assert_contains "list shows label" "label:test" "$out"

# Test 14: list with multiple checkpoints
P=$(setup_project "list4")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "first" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "second" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list shows 2 checkpoints" "2 checkpoint" "$out"
assert_contains "list has first" "label:first" "$out"
assert_contains "list has second" "label:second" "$out"

# Test 15: list shows stage from pipeline-state.json
P=$(setup_project "list5")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list shows stage" "[intake]" "$out"

# Test 16: list shows file count
P=$(setup_project "list6")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "list shows files" "files" "$out"

# ============================================================
# checkpoint.sh rollback tests
# ============================================================

echo "=== checkpoint.sh rollback ==="

# Test 17: rollback restores pipeline-state.json
P=$(setup_project "rb1")
original_state=$(cat "$P/.essay-state/pipeline-state.json")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "before" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^before-" | head -1)
# Modify state
python3 -c "
import json
with open('$P/.essay-state/pipeline-state.json') as f:
    d = json.load(f)
d['topic'] = 'Modified'
with open('$P/.essay-state/pipeline-state.json','w') as f:
    json.dump(d, f)
"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id" >/dev/null
restored_state=$(cat "$P/.essay-state/pipeline-state.json")
assert_eq "rollback restores state" "$original_state" "$restored_state"

# Test 18: rollback removes files not in checkpoint
P=$(setup_project "rb2")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "clean" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^clean-" | head -1)
echo '{"new":true}' > "$P/.essay-state/review-technical.json"
assert_file_exists "new file added" "$P/.essay-state/review-technical.json"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id" >/dev/null
assert_file_not_exists "new file removed after rollback" "$P/.essay-state/review-technical.json"

# Test 19: rollback preserves checkpoints/ directory
P=$(setup_project "rb3")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "keep" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^keep-" | head -1)
bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id" >/dev/null
assert_dir_exists "checkpoints dir preserved" "$P/.essay-state/checkpoints"
n=$(count_checkpoints "$P")
assert_eq "checkpoint still exists after rollback" "1" "$n"

# Test 20: rollback with invalid checkpoint ID
P=$(setup_project "rb4")
if bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "nonexistent" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error on invalid checkpoint"
else
  PASS=$((PASS + 1))
fi

# Test 21: rollback with empty checkpoint ID
P=$(setup_project "rb5")
if bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error on empty checkpoint ID"
else
  PASS=$((PASS + 1))
fi

# Test 22: rollback restores deleted file
P=$(setup_project "rb6")
echo '{"materials":true}' > "$P/.essay-state/materials.json"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "with-mats" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^with-mats-" | head -1)
rm "$P/.essay-state/materials.json"
assert_file_not_exists "materials removed" "$P/.essay-state/materials.json"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id" >/dev/null
assert_file_exists "materials restored" "$P/.essay-state/materials.json"

# Test 23: rollback output shows file count
P=$(setup_project "rb7")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^test-" | head -1)
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id")
assert_contains "rollback output has files restored" "files restored" "$out"

# ============================================================
# checkpoint.sh latest tests
# ============================================================

echo "=== checkpoint.sh latest ==="

# Test 24: latest with no checkpoints dir
P="$TMPDIR/lat1"
mkdir -p "$P/.essay-state"
if out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$P" 2>&1); then
  assert_contains "latest no checkpoints msg" "No checkpoints" "$out"
else
  PASS=$((PASS + 1))  # returning error is also valid
fi

# Test 25: latest with one checkpoint
P=$(setup_project "lat2")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "only" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$P")
assert_contains "latest shows only checkpoint" "label:only" "$out"

# Test 26: latest with multiple shows most recent
P=$(setup_project "lat3")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "older" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "newer" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$P")
assert_contains "latest shows newest" "label:newer" "$out"

# Test 27: latest shows stage and file count
P=$(setup_project "lat4")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "stage-check" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$P")
assert_contains "latest shows stage" "[intake]" "$out"
assert_contains "latest shows file count" "files" "$out"

# ============================================================
# checkpoint.sh clean tests
# ============================================================

echo "=== checkpoint.sh clean ==="

# Test 28: clean with no checkpoints dir
P="$TMPDIR/cln1"
mkdir -p "$P/.essay-state"
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P")
assert_contains "clean empty" "No checkpoints" "$out"

# Test 29: clean with fewer than threshold keeps all
P=$(setup_project "cln2")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "a" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "b" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" --keep 5)
assert_contains "clean keeps all" "keeping all" "$out"
n=$(count_checkpoints "$P")
assert_eq "all checkpoints preserved" "2" "$n"

# Test 30: clean removes oldest, keeps N
P=$(setup_project "cln3")
for label in a b c d e f; do
  bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "$label" >/dev/null
  sleep 1
done
n=$(count_checkpoints "$P")
assert_eq "6 checkpoints before clean" "6" "$n"
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" --keep 3)
assert_contains "clean removes 3" "Cleaned 3" "$out"
n=$(count_checkpoints "$P")
assert_eq "3 checkpoints after clean" "3" "$n"

# Test 31: clean --keep 1
P=$(setup_project "cln4")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "a" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "b" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "c" >/dev/null
bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" --keep 1 >/dev/null
n=$(count_checkpoints "$P")
assert_eq "clean --keep 1 leaves 1" "1" "$n"

# Test 32: clean default keep (5)
P=$(setup_project "cln5")
for label in a b c d e f g; do
  bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "$label" >/dev/null
  sleep 1
done
bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" >/dev/null
n=$(count_checkpoints "$P")
assert_eq "clean default keeps 5" "5" "$n"

# Test 33: clean --keep 0 removes all
P=$(setup_project "cln6")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "a" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "b" >/dev/null
bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" --keep 0 >/dev/null
n=$(count_checkpoints "$P")
assert_eq "clean --keep 0 removes all" "0" "$n"

# ============================================================
# pipeline-state.sh auto-snapshot integration
# ============================================================

echo "=== pipeline-state.sh auto-snapshot ==="

# Test 34: set-stage creates auto checkpoint
P=$(setup_project "auto1")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
n=$(count_checkpoints "$P")
assert_eq "auto checkpoint created on set-stage" "1" "$n"

# Test 35: auto checkpoint label is current stage (before transition)
P=$(setup_project "auto2")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "auto checkpoint labeled intake" "label:intake" "$out"

# Test 36: auto checkpoint pipeline-state.json has pre-transition stage
P=$(setup_project "auto3")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
ckpt_dir=$(ls -d "$P/.essay-state/checkpoints"/intake-* 2>/dev/null | head -1)
ckpt_stage=$(python3 -c "import json; print(json.load(open('$ckpt_dir/pipeline-state.json')).get('stage',''))")
assert_eq "checkpoint stage is intake (pre-transition)" "intake" "$ckpt_stage"

# Test 37: multiple transitions create multiple checkpoints
P=$(setup_project "auto4")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "outline" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "draft" >/dev/null
n=$(count_checkpoints "$P")
assert_eq "3 auto checkpoints from 3 transitions" "3" "$n"

# Test 38: auto checkpoint is non-fatal (set-stage still works)
P=$(setup_project "auto5")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$P")
assert_eq "stage updates correctly" "research" "$stage"

# ============================================================
# orchestrate.sh retry-stage tests
# ============================================================

echo "=== orchestrate.sh retry-stage ==="

# Test 39: retry-stage review clears review files
P=$(setup_project "retry1")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "review" >/dev/null
echo '{"reviewer":"technical"}' > "$P/.essay-state/review-technical.json"
echo '{"reviewer":"editor"}' > "$P/.essay-state/review-editor.json"
echo '{"panel":"summary"}' > "$P/.essay-state/review-panel-summary.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage review >/dev/null
assert_file_not_exists "review-technical cleared" "$P/.essay-state/review-technical.json"
assert_file_not_exists "review-editor cleared" "$P/.essay-state/review-editor.json"
assert_file_not_exists "review-panel-summary cleared" "$P/.essay-state/review-panel-summary.json"

# Test 40: retry-stage sets stage correctly
P=$(setup_project "retry2")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "refinement" >/dev/null
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage review >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$P")
assert_eq "stage reset to review" "review" "$stage"

# Test 41: retry-stage review resets tracking fields
P=$(setup_project "retry3")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "review" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "reviews" '{"technical":{"rating":"PASS"}}' >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "review_panel_complete" "true" >/dev/null
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage review >/dev/null
reviews=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$P" "reviews")
panel=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$P" "review_panel_complete")
assert_eq "reviews reset to empty" "{}" "$reviews"
assert_eq "review_panel_complete reset" "false" "$panel"

# Test 42: retry-stage draft clears draft files
P=$(setup_project "retry4")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "draft" >/dev/null
echo "# Draft v1" > "$P/.essay-state/draft-v1.md"
echo "# Draft v2" > "$P/.essay-state/draft-v2.md"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage draft >/dev/null
assert_file_not_exists "draft-v1 cleared" "$P/.essay-state/draft-v1.md"
assert_file_not_exists "draft-v2 cleared" "$P/.essay-state/draft-v2.md"

# Test 43: retry-stage outline clears outline + critique
P=$(setup_project "retry5")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "outline" >/dev/null
echo '{"outline":"A"}' > "$P/.essay-state/outline-A.json"
echo '{"outline":"B"}' > "$P/.essay-state/outline-B.json"
echo '{"critique":true}' > "$P/.essay-state/outline-critique.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage outline >/dev/null
assert_file_not_exists "outline-A cleared" "$P/.essay-state/outline-A.json"
assert_file_not_exists "outline-B cleared" "$P/.essay-state/outline-B.json"
assert_file_not_exists "outline-critique cleared" "$P/.essay-state/outline-critique.json"

# Test 44: retry-stage research clears synthesis
P=$(setup_project "retry6")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "research" >/dev/null
echo '{"thesis":"test"}' > "$P/.essay-state/research-synthesis.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage research >/dev/null
assert_file_not_exists "research cleared" "$P/.essay-state/research-synthesis.json"

# Test 45: retry-stage refinement keeps draft-v1, removes later drafts
P=$(setup_project "retry7")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "refinement" >/dev/null
echo "# Draft v1" > "$P/.essay-state/draft-v1.md"
echo "# Draft v2" > "$P/.essay-state/draft-v2.md"
echo "# Draft v3" > "$P/.essay-state/draft-v3.md"
echo '{"changes":[]}' > "$P/.essay-state/refinement-1-changes.json"
echo '{"changes":[]}' > "$P/.essay-state/refinement-2-changes.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage refinement >/dev/null
assert_file_exists "draft-v1 kept" "$P/.essay-state/draft-v1.md"
assert_file_not_exists "draft-v2 removed" "$P/.essay-state/draft-v2.md"
assert_file_not_exists "draft-v3 removed" "$P/.essay-state/draft-v3.md"
assert_file_not_exists "refinement-1-changes removed" "$P/.essay-state/refinement-1-changes.json"

# Test 46: retry-stage polish clears all final outputs
P=$(setup_project "retry8")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "polish" >/dev/null
echo "# Internal" > "$P/.essay-state/final-internal.md"
echo "# External" > "$P/.essay-state/final-external.md"
echo '{"social":true}' > "$P/.essay-state/social-package.json"
echo '{"score":5}' > "$P/.essay-state/influence-score.json"
echo '{"seo":true}' > "$P/.essay-state/seo-metadata.json"
echo '{"diagrams":[]}' > "$P/.essay-state/diagram-suggestions.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage polish >/dev/null
assert_file_not_exists "final-internal cleared" "$P/.essay-state/final-internal.md"
assert_file_not_exists "final-external cleared" "$P/.essay-state/final-external.md"
assert_file_not_exists "social-package cleared" "$P/.essay-state/social-package.json"
assert_file_not_exists "influence-score cleared" "$P/.essay-state/influence-score.json"
assert_file_not_exists "seo-metadata cleared" "$P/.essay-state/seo-metadata.json"
assert_file_not_exists "diagram-suggestions cleared" "$P/.essay-state/diagram-suggestions.json"

# Test 47: retry-stage intake clears materials
P=$(setup_project "retry9")
echo '{"sources":[]}' > "$P/.essay-state/materials.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage intake >/dev/null
assert_file_not_exists "materials cleared" "$P/.essay-state/materials.json"

# Test 48: retry-stage invalid stage returns error
P=$(setup_project "retry10")
if bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage "invalid" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid stage"
else
  PASS=$((PASS + 1))
fi

# Test 49: retry-stage complete returns error
P=$(setup_project "retry11")
if bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage "complete" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject complete stage"
else
  PASS=$((PASS + 1))
fi

# Test 50: retry-stage rolls back to preceding stage checkpoint
P=$(setup_project "retry-rb1")
# Advance through stages (creates checkpoints at each transition)
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
echo '{"thesis":"original"}' > "$P/.essay-state/research-synthesis.json"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "outline" >/dev/null
echo '{"outline":"A"}' > "$P/.essay-state/outline-A.json"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "draft" >/dev/null
echo "# Draft" > "$P/.essay-state/draft-v1.md"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "review" >/dev/null
echo '{"reviewer":"technical"}' > "$P/.essay-state/review-technical.json"
# Retry review — should rollback to draft checkpoint
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage review)
assert_contains "retry mentions rollback" "Rolling back" "$out"
# Pipeline-state.json should exist (restored from checkpoint or set)
assert_file_exists "pipeline state still exists" "$P/.essay-state/pipeline-state.json"

# Test 51: retry-stage without checkpoint still resets
P=$(setup_project "retry-norb")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "review" >/dev/null
echo '{"reviewer":"editor"}' > "$P/.essay-state/review-editor.json"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage review)
assert_contains "retry without checkpoint mentions no checkpoint" "No checkpoint" "$out"
assert_file_not_exists "review file cleared" "$P/.essay-state/review-editor.json"
stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$P")
assert_eq "stage set to review" "review" "$stage"

# Test 52: retry-stage refinement resets round counter
P=$(setup_project "retry-round")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "refinement" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "refinement_round" "2" >/dev/null
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage refinement >/dev/null
round=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$P" "refinement_round")
assert_eq "refinement round reset to 0" "0" "$round"

# ============================================================
# orchestrate.sh resume tests
# ============================================================

echo "=== orchestrate.sh resume ==="

# Test 53: resume with no pipeline state file
P="$TMPDIR/resume1"
mkdir -p "$P/.essay-state"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume no pipeline" "not_initialized" "$out"

# Test 54: resume at intake (no materials)
P=$(setup_project "resume2")
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume intake status" "STATUS: intake" "$out"
assert_contains "resume intake has action" "ACTION:" "$out"

# Test 55: resume at intake with materials
P=$(setup_project "resume3")
echo '{"source_count":2,"sources":[{"type":"url"},{"type":"note"}]}' > "$P/.essay-state/materials.json"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume intake with materials" "2 material" "$out"

# Test 56: resume at research (no synthesis)
P=$(setup_project "resume4")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume research status" "STATUS: research" "$out"
assert_contains "resume research not done" "not started" "$out"

# Test 57: resume at research (synthesis done)
P=$(setup_project "resume5")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "research" >/dev/null
echo '{"thesis":"test"}' > "$P/.essay-state/research-synthesis.json"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume research complete" "complete" "$out"
assert_contains "resume research advance" "outline" "$out"

# Test 58: resume at outline (partial)
P=$(setup_project "resume6")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "outline" >/dev/null
echo '{"outline":"A"}' > "$P/.essay-state/outline-A.json"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume outline partial" "1/3" "$out"

# Test 59: resume at review (partial reviews)
P=$(setup_project "resume7")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "review" >/dev/null
echo '{"reviewer":"technical"}' > "$P/.essay-state/review-technical.json"
echo '{"reviewer":"editor"}' > "$P/.essay-state/review-editor.json"
echo '{"reviewer":"seo"}' > "$P/.essay-state/review-seo.json"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume review progress" "3/7" "$out"
assert_contains "resume review has missing" "MISSING" "$out"

# Test 60: resume at refinement
P=$(setup_project "resume8")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "refinement" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "refinement_round" "1" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume refinement round" "Round 1" "$out"

# Test 61: resume at polish (partial)
P=$(setup_project "resume9")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$P" "polish" >/dev/null
echo "# Internal" > "$P/.essay-state/final-internal.md"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume polish status" "STATUS: polish" "$out"
assert_contains "resume polish internal done" "internal=True" "$out"

# Test 62: resume at complete
P=$(setup_project "resume10")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" complete "$P" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" resume)
assert_contains "resume complete" "STATUS: complete" "$out"

# ============================================================
# orchestrate.sh list-checkpoints and rollback delegation
# ============================================================

echo "=== orchestrate.sh delegation ==="

# Test 63: list-checkpoints delegates correctly
P=$(setup_project "deleg1")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "test-deleg" >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" list-checkpoints)
assert_contains "list-checkpoints shows checkpoint" "test-deleg" "$out"

# Test 64: rollback via orchestrate delegates correctly
P=$(setup_project "deleg2")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "snap" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^snap-" | head -1)
echo '{"extra":true}' > "$P/.essay-state/extra-file.json"
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" rollback "$ckpt_id" >/dev/null
assert_file_not_exists "rollback via orchestrate removes extra file" "$P/.essay-state/extra-file.json"

# ============================================================
# Edge case tests
# ============================================================

echo "=== edge cases ==="

# Test 65: snapshot → rollback → snapshot cycle
P=$(setup_project "edge1")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "first" >/dev/null
ckpt_id=$(ls "$P/.essay-state/checkpoints" | grep "^first-" | head -1)
echo '{"new":"data"}' > "$P/.essay-state/new-data.json"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$P" "$ckpt_id" >/dev/null
assert_file_not_exists "new data removed after rollback" "$P/.essay-state/new-data.json"
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "after-rollback" >/dev/null
n=$(count_checkpoints "$P")
assert_eq "two checkpoints after cycle" "2" "$n"

# Test 66: clean preserves most recent by timestamp
P=$(setup_project "edge2")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "older" >/dev/null
sleep 1
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "newest" >/dev/null
bash "$SCRIPT_DIR/scripts/checkpoint.sh" clean "$P" --keep 1 >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$P")
assert_contains "newest checkpoint preserved" "label:newest" "$out"

# Test 67: snapshot with hyphenated label
P=$(setup_project "edge3")
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "pre-review")
assert_contains "hyphenated label works" "pre-review" "$out"
list_out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$P")
assert_contains "hyphenated label in list" "pre-review" "$list_out"

# Test 68: usage text shows correct commands
out=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" 2>&1 || true)
assert_contains "usage has snapshot" "snapshot" "$out"
assert_contains "usage has list" "list" "$out"
assert_contains "usage has rollback" "rollback" "$out"
assert_contains "usage has latest" "latest" "$out"
assert_contains "usage has clean" "clean" "$out"

# Test 69: no tmp dirs left after snapshot
P=$(setup_project "edge4")
bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$P" "clean" >/dev/null
tmp_count=$(find "$P/.essay-state/checkpoints" -name ".tmp-*" -type d 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no tmp dirs after snapshot" "0" "$tmp_count"

# Test 70: retry-stage output mentions ready
P=$(setup_project "edge5")
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage intake)
assert_contains "retry output mentions ready" "ready" "$out"

# Test 71: retry-stage outline resets outline_variant
P=$(setup_project "edge6")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "outline" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "outline_variant" '"A"' >/dev/null
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage outline >/dev/null
variant=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$P" "outline_variant")
assert_eq "outline_variant reset to null" "" "$variant"

# Test 72: retry-stage draft resets draft_version
P=$(setup_project "edge7")
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "stage" "draft" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$P" "draft_version" "3" >/dev/null
bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$P" "$SCRIPT_DIR" retry-stage draft >/dev/null
ver=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$P" "draft_version")
assert_eq "draft_version reset to 0" "0" "$ver"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
