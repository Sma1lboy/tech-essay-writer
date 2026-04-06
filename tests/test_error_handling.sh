#!/usr/bin/env bash
# Tests for error handling across all scripts in scripts/
# Verifies graceful handling of: missing args, corrupt JSON, missing dirs,
# empty state, permission issues, invalid inputs
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

assert_fails() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected failure, got success)"
  else
    PASS=$((PASS + 1))
  fi
}

assert_fails_with() {
  local desc="$1" expected_msg="$2"
  shift 2
  local output
  output=$("$@" 2>&1) && true
  local rc=$?
  if [ $rc -ne 0 ] && echo "$output" | grep -qi "$expected_msg"; then
    PASS=$((PASS + 1))
  elif [ $rc -eq 0 ]; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected failure, got success)"
    echo "  output: $output"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (failed but missing expected message)"
    echo "  expected message containing: $expected_msg"
    echo "  actual: $output"
  fi
}

assert_succeeds() {
  local desc="$1"
  shift
  local output
  output=$("$@" 2>&1) && true
  local rc=$?
  if [ $rc -eq 0 ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected success, got rc=$rc)"
    echo "  output: $output"
  fi
}

# ============================================================
echo "=== pipeline-state.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" 2>&1) && true
assert_contains "no-cmd shows usage" "Usage" "$output"

echo "--- init without topic ---"
PROJECT="$TMPDIR/test-no-topic"
mkdir -p "$PROJECT"
# init requires at least a project and a topic; with just project, it inits with empty topic (not a crash)
assert_succeeds "init with project but empty topic" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" ""

echo "--- set-stage missing stage ---"
assert_fails_with "set-stage missing stage arg" "set-stage requires" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT"

echo "--- set-stage invalid stage ---"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" "badstage" 2>&1) && true
assert_contains "invalid stage error" "Invalid stage" "$output"

echo "--- get-field missing key ---"
assert_fails_with "get-field missing key" "get-field requires" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT"

echo "--- set-field missing args ---"
assert_fails_with "set-field missing args" "set-field requires" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT"

echo "--- add-review missing file ---"
assert_fails_with "add-review missing file arg" "add-review requires" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT"

# ============================================================
echo ""
echo "=== pipeline-state.sh: corrupt JSON state ==="
# ============================================================

PROJECT_CORRUPT="$TMPDIR/test-corrupt"
mkdir -p "$PROJECT_CORRUPT/.essay-state"
echo "NOT_JSON{{{" > "$PROJECT_CORRUPT/.essay-state/pipeline-state.json"

echo "--- read corrupt state file ---"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT_CORRUPT" 2>&1) && true
# Should fall back to {} and warn
assert_contains "corrupt state warns" "Corrupt\|WARNING\|{}" "$output"

echo "--- get-stage with corrupt state ---"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT_CORRUPT" 2>&1) && true
assert_contains "corrupt get-stage returns unknown" "unknown\|WARNING" "$output"

# ============================================================
echo ""
echo "=== pipeline-state.sh: missing project directory ==="
# ============================================================

echo "--- init on nonexistent parent (creates it) ---"
assert_succeeds "init on nonexistent dir" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$TMPDIR/nonexist/deep/dir" "test topic"

echo "--- read on nonexistent project (returns empty) ---"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$TMPDIR/totally-missing" 2>&1) && true
assert_eq "read missing project returns empty object" "{}" "$output"

# ============================================================
echo ""
echo "=== pipeline-state.sh: empty state file ==="
# ============================================================

PROJECT_EMPTY="$TMPDIR/test-empty-state"
mkdir -p "$PROJECT_EMPTY/.essay-state"
echo "" > "$PROJECT_EMPTY/.essay-state/pipeline-state.json"

output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT_EMPTY" 2>&1) && true
assert_contains "empty state file handled" "unknown\|WARNING\|Corrupt" "$output"

# ============================================================
echo ""
echo "=== intake-materials.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" 2>&1) && true
assert_contains "no-cmd shows usage" "Usage" "$output"

echo "--- add-url missing url ---"
assert_fails_with "add-url no url" "add-url requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-url "$TMPDIR/p1"

echo "--- add-note missing note ---"
assert_fails_with "add-note no note" "add-note requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$TMPDIR/p1"

echo "--- add-file missing file ---"
assert_fails_with "add-file no file" "add-file requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-file "$TMPDIR/p1"

echo "--- add-file nonexistent file ---"
PROJECT_MAT="$TMPDIR/test-mat"
mkdir -p "$PROJECT_MAT/.essay-state"
assert_fails_with "add-file nonexistent" "File not found" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-file "$PROJECT_MAT" "/no/such/file.txt"

echo "--- add-code missing code ---"
assert_fails_with "add-code no code" "add-code requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-code "$TMPDIR/p1"

echo "--- add-theme missing theme ---"
assert_fails_with "add-theme no theme" "add-theme requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-theme "$TMPDIR/p1"

echo "--- add-angle missing angle ---"
assert_fails_with "add-angle no angle" "add-angle requires" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-angle "$TMPDIR/p1"

# ============================================================
echo ""
echo "=== intake-materials.sh: corrupt materials.json ==="
# ============================================================

PROJECT_CORRUPT_MAT="$TMPDIR/test-corrupt-mat"
mkdir -p "$PROJECT_CORRUPT_MAT/.essay-state"
echo "BROKEN_JSON!!!" > "$PROJECT_CORRUPT_MAT/.essay-state/materials.json"

echo "--- list with corrupt materials ---"
output=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" list "$PROJECT_CORRUPT_MAT" 2>&1) && true
# Should not crash -- either warns or falls back
assert_contains "corrupt materials handled" "WARNING\|Corrupt\|Materials\|sources" "$output"

echo "--- export with corrupt materials ---"
output=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" export "$PROJECT_CORRUPT_MAT" 2>&1) && true
# Should not crash
assert_contains "corrupt materials export handled" "WARNING\|Corrupt\|sources\|{" "$output"

# ============================================================
echo ""
echo "=== quality-score.sh: missing state directory ==="
# ============================================================

echo "--- missing project dir ---"
assert_fails_with "quality-score missing state dir" "State directory not found" bash "$SCRIPT_DIR/scripts/quality-score.sh" "$TMPDIR/no-such-project"

echo "--- missing project arg ---"
assert_fails "quality-score no args" bash "$SCRIPT_DIR/scripts/quality-score.sh"

echo "--- empty state directory (no reviews) ---"
QS_PROJECT="$TMPDIR/test-qs"
mkdir -p "$QS_PROJECT/.essay-state"
output=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$QS_PROJECT" 2>&1) && true
assert_contains "no reviews returns NO_REVIEWS" "NO_REVIEWS" "$output"

echo "--- corrupt review file ---"
QS_PROJECT2="$TMPDIR/test-qs-corrupt"
mkdir -p "$QS_PROJECT2/.essay-state"
echo "NOT_JSON" > "$QS_PROJECT2/.essay-state/review-technical.json"
output=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$QS_PROJECT2" "verbose" 2>&1) && true
assert_contains "corrupt review skipped" "CORRUPT\|skipped" "$output"

# ============================================================
echo ""
echo "=== aggregate-reviews.sh: missing args/dir ==="
# ============================================================

echo "--- missing project arg ---"
assert_fails_with "aggregate-reviews no args" "project_dir required" bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh"

echo "--- missing state directory ---"
assert_fails_with "aggregate-reviews missing state dir" "State directory not found" bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$TMPDIR/no-project"

echo "--- empty state directory (no reviews) ---"
AGG_PROJECT="$TMPDIR/test-agg"
mkdir -p "$AGG_PROJECT/.essay-state"
output=$(bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$AGG_PROJECT" 2>&1) && true
assert_contains "aggregate with no reviews" "0\|reviews_count" "$output"

echo "--- corrupt review file in aggregate ---"
AGG_PROJECT2="$TMPDIR/test-agg-corrupt"
mkdir -p "$AGG_PROJECT2/.essay-state"
echo "{{BROKEN}}" > "$AGG_PROJECT2/.essay-state/review-technical.json"
echo '{"rating":"PASS","issues":[]}' > "$AGG_PROJECT2/.essay-state/review-editor.json"
output=$(bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$AGG_PROJECT2" 2>&1) && true
assert_contains "corrupt review in aggregate handled" "review" "$output"

# ============================================================
echo ""
echo "=== config.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/config.sh" 2>&1) && true
assert_contains "config no-cmd shows usage" "Usage" "$output"

echo "--- get without key ---"
assert_fails_with "config get no key" "get requires" bash "$SCRIPT_DIR/scripts/config.sh" get

echo "--- set without args ---"
assert_fails_with "config set no args" "set requires" bash "$SCRIPT_DIR/scripts/config.sh" set

echo "--- set with invalid key ---"
# Backup original config
ORIG_CONFIG_DIR="$HOME/.tech-essay-writer"
BACKUP_CONFIG=""
if [ -f "$ORIG_CONFIG_DIR/config.json" ]; then
  BACKUP_CONFIG=$(cat "$ORIG_CONFIG_DIR/config.json")
fi

output=$(bash "$SCRIPT_DIR/scripts/config.sh" set "bogus_key" "value" 2>&1) && true
assert_contains "config set invalid key" "Unknown config key\|ERROR" "$output"

# Restore config
if [ -n "$BACKUP_CONFIG" ]; then
  echo "$BACKUP_CONFIG" > "$ORIG_CONFIG_DIR/config.json"
fi

echo "--- add-platform without platform ---"
assert_fails_with "config add-platform no arg" "add-platform requires" bash "$SCRIPT_DIR/scripts/config.sh" add-platform

echo "--- add-platform invalid platform ---"
output=$(bash "$SCRIPT_DIR/scripts/config.sh" add-platform "fakeblog" 2>&1) && true
assert_contains "config invalid platform" "Invalid platform" "$output"

echo "--- remove-platform without arg ---"
assert_fails_with "config remove-platform no arg" "remove-platform requires" bash "$SCRIPT_DIR/scripts/config.sh" remove-platform

echo "--- add-audience without arg ---"
assert_fails_with "config add-audience no arg" "add-audience requires" bash "$SCRIPT_DIR/scripts/config.sh" add-audience

echo "--- remove-audience without arg ---"
assert_fails_with "config remove-audience no arg" "remove-audience requires" bash "$SCRIPT_DIR/scripts/config.sh" remove-audience

# ============================================================
echo ""
echo "=== cross-reference.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/cross-reference.sh" 2>&1) && true
assert_contains "xref no-cmd shows usage" "Usage" "$output"

echo "--- add without args ---"
assert_fails_with "xref add no args" "add requires" bash "$SCRIPT_DIR/scripts/cross-reference.sh" add

echo "--- search without query ---"
assert_fails_with "xref search no query" "search requires" bash "$SCRIPT_DIR/scripts/cross-reference.sh" search

echo "--- suggest without topic ---"
assert_fails_with "xref suggest no topic" "suggest requires" bash "$SCRIPT_DIR/scripts/cross-reference.sh" suggest

echo "--- remove without id ---"
assert_fails_with "xref remove no id" "remove requires" bash "$SCRIPT_DIR/scripts/cross-reference.sh" remove

# ============================================================
echo ""
echo "=== checkpoint.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" 2>&1) && true
assert_contains "checkpoint no-cmd shows usage" "Usage" "$output"

echo "--- snapshot on missing state dir ---"
output=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" snapshot "$TMPDIR/no-project" 2>&1) && true
assert_contains "snapshot missing state dir" "ERROR\|No" "$output"

echo "--- rollback missing checkpoint id ---"
CKPT_PROJECT="$TMPDIR/test-ckpt"
mkdir -p "$CKPT_PROJECT/.essay-state"
output=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$CKPT_PROJECT" 2>&1) && true
assert_contains "rollback no id" "ERROR\|checkpoint_id required" "$output"

echo "--- rollback nonexistent checkpoint ---"
output=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$CKPT_PROJECT" "fake-checkpoint-id" 2>&1) && true
assert_contains "rollback nonexistent ckpt" "not found\|ERROR" "$output"

echo "--- list with no checkpoints ---"
output=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$CKPT_PROJECT" 2>&1) && true
assert_contains "list empty checkpoints" "No checkpoints" "$output"

# ============================================================
echo ""
echo "=== series-manager.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/series-manager.sh" 2>&1) && true
assert_contains "series no-cmd shows usage" "Usage" "$output"

echo "--- create without args ---"
assert_fails_with "series create no args" "create requires" bash "$SCRIPT_DIR/scripts/series-manager.sh" create

echo "--- show without id ---"
assert_fails_with "series show no id" "show requires" bash "$SCRIPT_DIR/scripts/series-manager.sh" show

echo "--- context without id ---"
assert_fails_with "series context no id" "context requires" bash "$SCRIPT_DIR/scripts/series-manager.sh" context

echo "--- search without query ---"
assert_fails_with "series search no query" "search requires" bash "$SCRIPT_DIR/scripts/series-manager.sh" search

# ============================================================
echo ""
echo "=== analytics-feedback.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" 2>&1) && true
assert_contains "analytics no-cmd shows usage" "Usage" "$output"

echo "--- record without args ---"
assert_fails_with "analytics record no args" "record requires" bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record

echo "--- record invalid metric ---"
output=$(bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record "art-1" "fake_metric" "100" 2>&1) && true
assert_contains "analytics invalid metric" "Invalid metric" "$output"

echo "--- record-batch without args ---"
assert_fails_with "analytics record-batch no args" "record-batch requires" bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record-batch

echo "--- query without args ---"
assert_fails_with "analytics query no args" "query requires" bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" query

echo "--- compare without args ---"
assert_fails_with "analytics compare no args" "compare requires" bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" compare

echo "--- feed-taste without args ---"
assert_fails_with "analytics feed-taste no args" "feed-taste requires" bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" feed-taste

# ============================================================
echo ""
echo "=== taste-memory.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" 2>&1) && true
assert_contains "taste no-cmd shows usage" "Usage" "$output"

echo "--- update without project ---"
assert_fails_with "taste update no project" "update requires" bash "$SCRIPT_DIR/scripts/taste-memory.sh" update

echo "--- record-choice without args ---"
assert_fails_with "taste record-choice no args" "record-choice requires" bash "$SCRIPT_DIR/scripts/taste-memory.sh" record-choice

echo "--- get-preference without key ---"
assert_fails_with "taste get-preference no key" "get-preference requires" bash "$SCRIPT_DIR/scripts/taste-memory.sh" get-preference

echo "--- feedback without args ---"
assert_fails_with "taste feedback no args" "feedback requires" bash "$SCRIPT_DIR/scripts/taste-memory.sh" feedback

echo "--- feedback invalid category ---"
output=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" feedback "$TMPDIR" "invalid_cat" "some text" 2>&1) && true
assert_contains "taste feedback invalid category" "invalid category\|Error" "$output"

echo "--- suggest without project ---"
assert_fails_with "taste suggest no project" "suggest requires" bash "$SCRIPT_DIR/scripts/taste-memory.sh" suggest

# ============================================================
echo ""
echo "=== author-profile.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" 2>&1) && true
assert_contains "author no-cmd shows usage" "Usage" "$output"

echo "--- set without args ---"
assert_fails_with "author set no args" "set requires" bash "$SCRIPT_DIR/scripts/author-profile.sh" set

echo "--- set invalid field ---"
output=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set "badfield" "val" 2>&1) && true
assert_contains "author set invalid field" "Invalid field" "$output"

echo "--- set-social without args ---"
assert_fails_with "author set-social no args" "set-social requires" bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social

echo "--- add-expertise without args ---"
assert_fails_with "author add-expertise no args" "add-expertise requires" bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise

echo "--- add-expertise invalid level ---"
output=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "Python" "godlike" 2>&1) && true
assert_contains "author invalid expertise level" "Invalid level" "$output"

echo "--- remove-expertise without topic ---"
assert_fails_with "author remove-expertise no topic" "remove-expertise requires" bash "$SCRIPT_DIR/scripts/author-profile.sh" remove-expertise

echo "--- set-voice without description ---"
assert_fails_with "author set-voice no desc" "set-voice requires" bash "$SCRIPT_DIR/scripts/author-profile.sh" set-voice

# ============================================================
echo ""
echo "=== expertise-graph.sh: missing arguments ==="
# ============================================================

echo "--- no command ---"
output=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" 2>&1) && true
assert_contains "graph no-cmd shows usage" "Usage" "$output"

echo "--- update without topic ---"
assert_fails_with "graph update no topic" "update requires" bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update

echo "--- query without topic ---"
assert_fails_with "graph query no topic" "query requires" bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query

# ============================================================
echo ""
echo "=== calibrate-reviews.sh: error handling ==="
# ============================================================

echo "--- missing project arg ---"
assert_fails_with "calibrate no args" "project_dir required" bash "$SCRIPT_DIR/scripts/calibrate-reviews.sh"

echo "--- missing state directory ---"
assert_fails_with "calibrate missing state dir" "State directory not found" bash "$SCRIPT_DIR/scripts/calibrate-reviews.sh" "$TMPDIR/no-project"

echo "--- empty state directory ---"
CAL_PROJECT="$TMPDIR/test-cal-empty"
mkdir -p "$CAL_PROJECT/.essay-state"
output=$(bash "$SCRIPT_DIR/scripts/calibrate-reviews.sh" "$CAL_PROJECT" 2>&1) && true
assert_contains "calibrate with no reviews" "No review\|error" "$output"

# ============================================================
echo ""
echo "=== code-validate.sh: error handling ==="
# ============================================================

echo "--- no file arg ---"
output=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" 2>&1) && true
assert_contains "code-validate no file" "error\|no file\|Usage" "$output"

echo "--- nonexistent file ---"
output=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "/tmp/no-such-file-1234.md" 2>&1) && true
assert_contains "code-validate missing file" "file not found\|error" "$output"

echo "--- empty markdown file ---"
EMPTY_MD="$TMPDIR/empty.md"
echo "" > "$EMPTY_MD"
output=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$EMPTY_MD" 2>&1) && true
assert_contains "code-validate empty file" "total_blocks" "$output"

# ============================================================
echo ""
echo "=== diagram-suggest.sh: error handling ==="
# ============================================================

echo "--- no file arg ---"
output=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" 2>&1) && true
assert_contains "diagram-suggest no file" "Usage" "$output"

echo "--- nonexistent file ---"
output=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "/tmp/no-such-file-5678.md" 2>&1) && true
assert_contains "diagram-suggest missing file" "file not found\|error" "$output"

# ============================================================
echo ""
echo "=== detect-input.sh: error handling ==="
# ============================================================

echo "--- no text arg ---"
assert_fails "detect-input no args" bash "$SCRIPT_DIR/scripts/detect-input.sh"

echo "--- empty-ish text ---"
output=$(bash "$SCRIPT_DIR/scripts/detect-input.sh" "hi" 2>&1) && true
assert_contains "detect-input short text" "item_count" "$output"

# ============================================================
echo ""
echo "=== publish-check.sh: error handling ==="
# ============================================================

echo "--- missing project arg ---"
assert_fails "publish-check no args" bash "$SCRIPT_DIR/scripts/publish-check.sh"

echo "--- nonexistent project ---"
output=$(bash "$SCRIPT_DIR/scripts/publish-check.sh" "$TMPDIR/no-project" 2>&1) && true
# Should get check failures not crashes
assert_contains "publish-check missing project" "FAIL\|Fail\|NOT READY" "$output"

# ============================================================
echo ""
echo "=== publishing-guide.sh: error handling ==="
# ============================================================

echo "--- missing platform arg ---"
assert_fails "publishing-guide no args" bash "$SCRIPT_DIR/scripts/publishing-guide.sh"

echo "--- invalid platform ---"
output=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "fakplatform" 2>&1) && true
assert_contains "publishing-guide invalid platform" "Invalid platform\|ERROR" "$output"

echo "--- valid platform with missing project ---"
output=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "medium" 2>&1) && true
assert_contains "publishing-guide medium no project" "Medium\|Steps\|steps" "$output"

# ============================================================
echo ""
echo "=== permission issues ==="
# ============================================================

echo "--- write to read-only state directory ---"
RO_PROJECT="$TMPDIR/test-readonly"
mkdir -p "$RO_PROJECT/.essay-state"
# Initialize first so the state file exists
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$RO_PROJECT" "test topic" >/dev/null 2>&1
# Make state dir read-only
chmod 555 "$RO_PROJECT/.essay-state"

output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$RO_PROJECT" "research" 2>&1) && true
rc=$?
# Should fail (can't write), not crash with an internal python traceback that's unreadable
# Restore permissions before asserting (so cleanup works)
chmod 755 "$RO_PROJECT/.essay-state"
if [ $rc -ne 0 ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: write to read-only dir should fail"
fi

echo "--- write materials to read-only dir ---"
RO_MAT_PROJECT="$TMPDIR/test-readonly-mat"
mkdir -p "$RO_MAT_PROJECT/.essay-state"
bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$RO_MAT_PROJECT" >/dev/null 2>&1
chmod 555 "$RO_MAT_PROJECT/.essay-state"

output=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$RO_MAT_PROJECT" "test note" 2>&1) && true
rc=$?
chmod 755 "$RO_MAT_PROJECT/.essay-state"
if [ $rc -ne 0 ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: write materials to read-only dir should fail"
fi

# ============================================================
echo ""
echo "=== paths with spaces ==="
# ============================================================

echo "--- pipeline-state with spaces in path ---"
SPACE_PROJECT="$TMPDIR/my project dir"
mkdir -p "$SPACE_PROJECT"
assert_succeeds "init with spaces in path" bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$SPACE_PROJECT" "test topic"
output=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$SPACE_PROJECT" 2>&1) && true
assert_eq "get-stage with spaces" "intake" "$output"

echo "--- intake with spaces in path ---"
assert_succeeds "intake init with spaces" bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$SPACE_PROJECT"
assert_succeeds "add-note with spaces" bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$SPACE_PROJECT" "a note"

# ============================================================
echo ""
echo "=== update-material.sh: error handling ==="
# ============================================================

echo "--- missing args ---"
assert_fails "update-material no args" bash "$SCRIPT_DIR/scripts/update-material.sh"

echo "--- missing materials.json ---"
UPD_PROJECT="$TMPDIR/test-upd"
mkdir -p "$UPD_PROJECT/.essay-state"
output=$(bash "$SCRIPT_DIR/scripts/update-material.sh" "$UPD_PROJECT" "src-123" "content" 2>&1) && true
assert_contains "update-material no materials file" "No materials.json\|not found" "$output"

echo "--- nonexistent source id ---"
bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$UPD_PROJECT" >/dev/null 2>&1
output=$(bash "$SCRIPT_DIR/scripts/update-material.sh" "$UPD_PROJECT" "src-nonexist" "content" 2>&1) && true
assert_contains "update-material nonexistent source" "not found" "$output"

# ============================================================
echo ""
echo "=== fetch-urls.sh: error handling ==="
# ============================================================

echo "--- missing project arg ---"
assert_fails "fetch-urls no args" bash "$SCRIPT_DIR/scripts/fetch-urls.sh"

echo "--- missing materials file ---"
output=$(bash "$SCRIPT_DIR/scripts/fetch-urls.sh" "$TMPDIR/no-project" 2>&1) && true
assert_contains "fetch-urls no materials" "No materials.json" "$output"

# ============================================================
echo ""
echo "=== orchestrate.sh: missing required args ==="
# ============================================================

echo "--- no args ---"
assert_fails "orchestrate no args" bash "$SCRIPT_DIR/scripts/orchestrate.sh"

echo "--- missing skill_dir ---"
assert_fails "orchestrate no skill_dir" bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR"

echo "--- missing command ---"
assert_fails "orchestrate no command" bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR" "$SCRIPT_DIR"

echo "--- invalid command ---"
output=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR" "$SCRIPT_DIR" "bogus_cmd" 2>&1) && true
assert_contains "orchestrate invalid cmd shows usage" "Usage" "$output"

echo "--- status on uninitialized project ---"
output=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR/fresh" "$SCRIPT_DIR" "status" 2>&1) && true
assert_contains "orchestrate status uninitialized" "NOT_INITIALIZED" "$output"

echo "--- next-stage on uninitialized ---"
output=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR/fresh2" "$SCRIPT_DIR" "next-stage" 2>&1) && true
assert_eq "orchestrate next-stage uninitialized" "intake" "$output"

echo "--- resume on uninitialized ---"
output=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$TMPDIR/fresh3" "$SCRIPT_DIR" "resume" 2>&1) && true
assert_contains "orchestrate resume uninitialized" "not_initialized\|intake" "$output"

# ============================================================
echo ""
echo "=== progress-display.sh: error handling ==="
# ============================================================

echo "--- missing project arg ---"
assert_fails "progress-display no args" bash "$SCRIPT_DIR/scripts/progress-display.sh"

echo "--- uninitialized project ---"
output=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$TMPDIR/no-init" 2>&1) && true
assert_contains "progress-display uninitialized" "not initialized\|not_initialized" "$output"

echo "--- invalid format flag ---"
output=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$TMPDIR/no-init" --format "xml" 2>&1) && true
assert_contains "progress-display invalid format" "ERROR\|format must be" "$output"

echo "--- corrupt pipeline state for progress ---"
PROG_PROJECT="$TMPDIR/test-prog-corrupt"
mkdir -p "$PROG_PROJECT/.essay-state"
echo "{{{BROKEN" > "$PROG_PROJECT/.essay-state/pipeline-state.json"
output=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROG_PROJECT" 2>&1) && true
assert_contains "progress-display corrupt state" "ERROR\|corrupt\|Cannot read" "$output"

# ============================================================
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
