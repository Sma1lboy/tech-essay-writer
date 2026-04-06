#!/usr/bin/env bash
# Tests for export.sh — bundle, markdown, html, json, archive, list-archive
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Temp home to avoid polluting real archive
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

assert_exit_code() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected exit code: $expected"
    echo "  actual exit code:   $actual"
  fi
}

# Helper: create a test project with initialized pipeline and final articles
setup_project() {
  local name="$1"
  local topic="${2:-Test Article Topic}"
  local project="$TMPDIR/$name"
  mkdir -p "$project"
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$project" "$topic" >/dev/null
  echo "$project"
}

# Helper: add final articles to a project
add_final_articles() {
  local project="$1"
  local state="$project/.essay-state"
  echo "# Internal Article

This is the **internal** version of the article.

## Section One

Some content here with \`inline code\`.

\`\`\`python
def hello():
    print('hello world')
\`\`\`

- List item 1
- List item 2

> A blockquote here

---

End of article." > "$state/final-internal.md"

  echo "# External Article

This is the **external** version.

## Introduction

Content for external readers." > "$state/final-external.md"
}

# Helper: add a medium final article
add_medium_article() {
  local project="$1"
  echo "# Medium Format Article

Written for Medium readers." > "$project/.essay-state/final-medium.md"
}

# Helper: set pipeline fields for richer metadata
set_pipeline_fields() {
  local project="$1"
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$project" "quality_score" "8.5" >/dev/null 2>&1 || true
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$project" "platforms" '["internal","external","medium"]' >/dev/null 2>&1 || true
}

# ============================================================
# Usage and error handling tests
# ============================================================

echo "=== export.sh usage & errors ==="

# Test 1: no args shows usage
out=$(bash "$SCRIPT_DIR/scripts/export.sh" 2>&1 || true)
assert_contains "no args shows usage" "Usage:" "$out"

# Test 2: invalid format shows error
P=$(setup_project "err1")
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "invalid_format" 2>&1 || true)
assert_contains "invalid format error" "Unknown format" "$out"

# Test 3: missing project dir errors
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$TMPDIR/nonexistent" "bundle" 2>&1 || true)
assert_contains "missing project dir error" "not found" "$out"

# Test 4: project without .essay-state errors
P="$TMPDIR/no-state"
mkdir -p "$P"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "bundle" 2>&1 || true)
assert_contains "no state dir error" "No .essay-state" "$out"

# ============================================================
# Bundle format tests
# ============================================================

echo "=== export.sh bundle ==="

# Test 5: bundle creates tar.gz
P=$(setup_project "bundle1" "My Great Article")
add_final_articles "$P"
out_dir="$TMPDIR/bundle-out1"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "bundle" "$out_dir")
assert_contains "bundle output says created" "Bundle created" "$out"
# Find the tar.gz
tarfile=$(ls "$out_dir"/essay-bundle-*.tar.gz 2>/dev/null | head -1)
if [ -n "$tarfile" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: bundle tar.gz not created"
  tarfile="/dev/null"
fi

# Test 6: bundle contains .essay-state files
file_list=$(tar -tzf "$tarfile" 2>/dev/null || echo "")
assert_contains "bundle contains pipeline-state" "pipeline-state.json" "$file_list"

# Test 7: bundle contains final articles
assert_contains "bundle contains final-internal.md" "final-internal.md" "$file_list"

# Test 8: bundle default output_dir is project dir
P=$(setup_project "bundle2" "Default Out")
add_final_articles "$P"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "bundle")
tarfile=$(ls "$P"/essay-bundle-*.tar.gz 2>/dev/null | head -1)
if [ -n "$tarfile" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: bundle not created in default project dir"
fi

# Test 9: bundle shows file size
assert_contains "bundle output shows size" "bytes" "$out"

# ============================================================
# Markdown format tests
# ============================================================

echo "=== export.sh markdown ==="

# Test 10: markdown export copies files
P=$(setup_project "md1" "Markdown Test")
add_final_articles "$P"
out_dir="$TMPDIR/md-out1"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "markdown" "$out_dir")
assert_contains "markdown output count" "2 markdown" "$out"
assert_file_exists "markdown copies final-internal" "$out_dir/final-internal.md"
assert_file_exists "markdown copies final-external" "$out_dir/final-external.md"

# Test 11: markdown export with no final articles errors
P=$(setup_project "md2" "No Finals")
rc=0
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "markdown" "$TMPDIR/md-out2" 2>/dev/null || rc=$?
assert_eq "markdown with no finals exits non-zero" "1" "$rc"

# Test 12: markdown preserves content
P=$(setup_project "md3" "Content Check")
add_final_articles "$P"
out_dir="$TMPDIR/md-out3"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "markdown" "$out_dir" >/dev/null
content=$(cat "$out_dir/final-internal.md")
assert_contains "markdown preserves content" "inline code" "$content"

# Test 13: markdown with three articles
P=$(setup_project "md4" "Three Articles")
add_final_articles "$P"
add_medium_article "$P"
out_dir="$TMPDIR/md-out4"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "markdown" "$out_dir")
assert_contains "markdown exports three" "3 markdown" "$out"

# ============================================================
# HTML format tests
# ============================================================

echo "=== export.sh html ==="

# Test 14: html export creates .html files
P=$(setup_project "html1" "HTML Test Article")
add_final_articles "$P"
out_dir="$TMPDIR/html-out1"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "html" "$out_dir")
assert_contains "html output count" "2 HTML" "$out"
assert_file_exists "html creates final-internal.html" "$out_dir/final-internal.html"
assert_file_exists "html creates final-external.html" "$out_dir/final-external.html"

# Test 15: html contains DOCTYPE
content=$(cat "$out_dir/final-internal.html")
assert_contains "html has DOCTYPE" "DOCTYPE html" "$content"

# Test 16: html has title from topic
assert_contains "html has title" "HTML Test Article" "$content"

# Test 17: html converts headers
assert_contains "html converts h1" "<h1>" "$content"
assert_contains "html converts h2" "<h2>" "$content"

# Test 18: html converts code blocks
assert_contains "html converts code blocks" "<pre><code" "$content"

# Test 19: html converts inline formatting
assert_contains "html converts bold" "<strong>" "$content"

# Test 20: html converts blockquotes
assert_contains "html converts blockquotes" "<blockquote>" "$content"

# Test 21: html converts lists
assert_contains "html converts lists" "<li>" "$content"

# Test 22: html with no final articles errors
P=$(setup_project "html2" "No Finals")
rc=0
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "html" "$TMPDIR/html-out2" 2>/dev/null || rc=$?
assert_eq "html with no finals exits non-zero" "1" "$rc"

# Test 23: html has proper styling
assert_contains "html has style tag" "<style>" "$content"

# ============================================================
# JSON format tests
# ============================================================

echo "=== export.sh json ==="

# Test 24: json export creates file
P=$(setup_project "json1" "JSON Export Topic")
add_final_articles "$P"
out_dir="$TMPDIR/json-out1"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "json" "$out_dir")
assert_contains "json output says export" "JSON export" "$out"
json_file=$(ls "$out_dir"/essay-export-*.json 2>/dev/null | head -1)
if [ -n "$json_file" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: json file not created"
  json_file="/dev/null"
fi

# Test 25: json is valid JSON
valid=$(python3 -c "import json; json.load(open('$json_file')); print('valid')" 2>/dev/null || echo "invalid")
assert_eq "json file is valid JSON" "valid" "$valid"

# Test 26: json contains pipeline_state
has_state=$(python3 -c "import json; d=json.load(open('$json_file')); print('yes' if d.get('pipeline_state') else 'no')" 2>/dev/null || echo "no")
assert_eq "json has pipeline_state" "yes" "$has_state"

# Test 27: json contains final_articles
has_articles=$(python3 -c "import json; d=json.load(open('$json_file')); print(len(d.get('final_articles', {})))" 2>/dev/null || echo "0")
assert_eq "json has 2 final articles" "2" "$has_articles"

# Test 28: json has format_version
has_version=$(python3 -c "import json; d=json.load(open('$json_file')); print(d.get('format_version','none'))" 2>/dev/null || echo "none")
assert_eq "json has format_version" "1.0" "$has_version"

# Test 29: json has exported_at timestamp
has_ts=$(python3 -c "import json; d=json.load(open('$json_file')); print('yes' if d.get('exported_at') else 'no')" 2>/dev/null || echo "no")
assert_eq "json has exported_at" "yes" "$has_ts"

# Test 30: json contains article content
article_content=$(python3 -c "import json; d=json.load(open('$json_file')); print(d['final_articles'].get('internal','')[:20])" 2>/dev/null || echo "")
assert_contains "json article has content" "Internal" "$article_content"

# Test 31: json shows file size
assert_contains "json output shows size" "bytes" "$out"

# ============================================================
# Archive format tests
# ============================================================

echo "=== export.sh archive ==="

# Test 32: archive creates directory in ~/.tech-essay-writer/articles/
P=$(setup_project "arch1" "Archive Test Article")
add_final_articles "$P"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "archive")
assert_contains "archive output says archived" "Archived" "$out"
assert_contains "archive output says metadata" "metadata.json" "$out"

# Test 33: archive directory has expected naming
archive_dir=$(ls -d "$HOME/.tech-essay-writer/articles"/*archive-test-article* 2>/dev/null | head -1)
if [ -n "$archive_dir" ] && [ -d "$archive_dir" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: archive directory not found with slug-based name"
  archive_dir="$TMPDIR/fallback-arch"
  mkdir -p "$archive_dir"
fi

# Test 34: archive contains final articles
assert_file_exists "archive has final-internal.md" "$archive_dir/final-internal.md"
assert_file_exists "archive has final-external.md" "$archive_dir/final-external.md"

# Test 35: archive contains metadata.json
assert_file_exists "archive has metadata.json" "$archive_dir/metadata.json"

# Test 36: metadata has correct topic
meta_topic=$(python3 -c "import json; print(json.load(open('$archive_dir/metadata.json')).get('topic',''))" 2>/dev/null || echo "")
assert_eq "metadata has correct topic" "Archive Test Article" "$meta_topic"

# Test 37: metadata has archived_at
meta_ts=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print('yes' if d.get('archived_at') else 'no')" 2>/dev/null || echo "no")
assert_eq "metadata has archived_at" "yes" "$meta_ts"

# Test 38: metadata has quality_score field
meta_score=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print('present' if 'quality_score' in d else 'missing')" 2>/dev/null || echo "missing")
assert_eq "metadata has quality_score field" "present" "$meta_score"

# Test 39: metadata has platforms field
meta_platforms=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print('present' if 'platforms' in d else 'missing')" 2>/dev/null || echo "missing")
assert_eq "metadata has platforms field" "present" "$meta_platforms"

# Test 40: metadata has publish_dates field
meta_pubdates=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print('present' if 'publish_dates' in d else 'missing')" 2>/dev/null || echo "missing")
assert_eq "metadata has publish_dates field" "present" "$meta_pubdates"

# Test 41: metadata has source_project field
meta_source=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print('present' if d.get('source_project') else 'missing')" 2>/dev/null || echo "missing")
assert_eq "metadata has source_project" "present" "$meta_source"

# Test 42: metadata lists files
meta_files=$(python3 -c "import json; d=json.load(open('$archive_dir/metadata.json')); print(len(d.get('files',[])))" 2>/dev/null || echo "0")
# Should have final-internal.md, final-external.md (metadata.json is written after the listing, so it may or may not be included)
if [ "$meta_files" -ge 2 ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: metadata files list should have >= 2, got $meta_files"
fi

# Test 43: archive with no final articles errors
P=$(setup_project "arch2" "No Finals Archive")
rc=0
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "archive" 2>/dev/null || rc=$?
assert_eq "archive with no finals exits non-zero" "1" "$rc"

# Test 44: duplicate archive gets numeric suffix
P=$(setup_project "arch3" "Duplicate Topic")
add_final_articles "$P"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "archive" >/dev/null
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "archive" >/dev/null
dup_count=$(ls -d "$HOME/.tech-essay-writer/articles"/*duplicate-topic* 2>/dev/null | wc -l | tr -d ' ')
assert_eq "duplicate archive creates second dir" "2" "$dup_count"

# ============================================================
# List archive tests
# ============================================================

echo "=== export.sh list-archive ==="

# Test 45: list-archive shows archived articles
out=$(bash "$SCRIPT_DIR/scripts/export.sh" list-archive)
assert_contains "list-archive shows articles" "archived article" "$out"
assert_contains "list-archive shows topic" "Archive Test Article" "$out"

# Test 46: list-archive --json produces valid JSON
out=$(bash "$SCRIPT_DIR/scripts/export.sh" list-archive --json)
valid=$(echo "$out" | python3 -c "import json,sys; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
assert_eq "list-archive --json is valid" "valid" "$valid"

# Test 47: list-archive --json contains entries
count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$count" -ge 1 ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: list-archive --json should have >= 1 entry, got $count"
fi

# Test 48: list-archive with empty archive dir
SAVE_HOME="$HOME"
export HOME="$TMPDIR/emptyhome"
mkdir -p "$HOME"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" list-archive)
assert_contains "empty list-archive says no articles" "No archived articles" "$out"
export HOME="$SAVE_HOME"

# Test 49: list-archive --json with empty archive returns []
export HOME="$TMPDIR/emptyhome2"
mkdir -p "$HOME"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" list-archive --json)
assert_eq "empty list-archive --json returns []" "[]" "$out"
export HOME="$SAVE_HOME"

# ============================================================
# Slug generation tests
# ============================================================

echo "=== export.sh slug generation ==="

# Test 50: slug handles special characters
P=$(setup_project "slug1" "My Article: A Deep Dive! (2024)")
add_final_articles "$P"
out_dir="$TMPDIR/slug-out1"
out=$(bash "$SCRIPT_DIR/scripts/export.sh" "$P" "bundle" "$out_dir")
tarfile=$(ls "$out_dir"/essay-bundle-*.tar.gz 2>/dev/null | head -1)
if [ -n "$tarfile" ]; then
  fname=$(basename "$tarfile")
  assert_not_contains "slug has no special chars" "[!@#$%^&*()]" "$fname"
  PASS=$((PASS + 1))  # Also count finding the file
else
  FAIL=$((FAIL + 1)); echo "FAIL: bundle not created for special char topic"
fi

# Test 51: slug handles spaces
P=$(setup_project "slug2" "Spaces In Topic Name")
add_final_articles "$P"
out_dir="$TMPDIR/slug-out2"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "bundle" "$out_dir" >/dev/null
tarfile=$(ls "$out_dir"/essay-bundle-*spaces-in-topic-name*.tar.gz 2>/dev/null | head -1)
if [ -n "$tarfile" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: slug should contain spaces-in-topic-name"
fi

# ============================================================
# Orchestrate.sh integration tests
# ============================================================

echo "=== orchestrate.sh export integration ==="

# Test 52: orchestrate.sh usage mentions export
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" /tmp "$SCRIPT_DIR" help 2>&1 || true)
assert_contains "orchestrate usage has export" "export" "$out"

# Test 53: orchestrate.sh usage mentions list-archive
assert_contains "orchestrate usage has list-archive" "list-archive" "$out"

# ============================================================
# Edge case tests
# ============================================================

echo "=== export.sh edge cases ==="

# Test 54: html default output_dir
P=$(setup_project "edge1" "Default HTML Dir")
add_final_articles "$P"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "html" >/dev/null
assert_dir_exists "html default dir created" "$P/export-html"
assert_file_exists "html default dir has file" "$P/export-html/final-internal.html"

# Test 55: markdown default output_dir
P=$(setup_project "edge2" "Default MD Dir")
add_final_articles "$P"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "markdown" >/dev/null
assert_dir_exists "markdown default dir created" "$P/export-markdown"

# Test 56: json default output_dir is project dir
P=$(setup_project "edge3" "Default JSON Dir")
add_final_articles "$P"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "json" >/dev/null
json_file=$(ls "$P"/essay-export-*.json 2>/dev/null | head -1)
if [ -n "$json_file" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: json default output not in project dir"
fi

# Test 57: html converts horizontal rules
P=$(setup_project "edge4" "HR Test")
add_final_articles "$P"
out_dir="$TMPDIR/hr-test"
bash "$SCRIPT_DIR/scripts/export.sh" "$P" "html" "$out_dir" >/dev/null
content=$(cat "$out_dir/final-internal.html")
assert_contains "html converts hr" "<hr>" "$content"

# ============================================================
echo ""
echo "========================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
