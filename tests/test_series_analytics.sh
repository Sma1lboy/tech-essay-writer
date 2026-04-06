#!/usr/bin/env bash
# Tests for series-manager.sh, analytics-feedback.sh, and orchestrator/pipeline integration
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

assert_json_field() {
  local desc="$1" file="$2" field="$3" expected="$4"
  local actual
  actual=$(python3 -c "import json; print(json.load(open('$file'))$field)" 2>/dev/null || echo "PARSE_ERROR")
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

# Override HOME to isolate tests from real user data
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME/.tech-essay-writer"

SERIES_SCRIPT="$SCRIPT_DIR/scripts/series-manager.sh"
ANALYTICS_SCRIPT="$SCRIPT_DIR/scripts/analytics-feedback.sh"
PIPELINE_SCRIPT="$SCRIPT_DIR/scripts/pipeline-state.sh"
ORCHESTRATE_SCRIPT="$SCRIPT_DIR/scripts/orchestrate.sh"

# ============================================================
echo "=== series-manager.sh ==="
# ============================================================

# Test 1: create series, verify file created
out=$(bash "$SERIES_SCRIPT" create "Building a Compiler" "A 5-part series on compilers")
assert_contains "create returns success" "Created series" "$out"
assert_file_exists "series.json created" "$HOME/.tech-essay-writer/series.json"

# Test 2: verify JSON structure
assert_json_field "series array exists" "$HOME/.tech-essay-writer/series.json" "['series'][0]['name']" "Building a Compiler"
assert_json_field "description set" "$HOME/.tech-essay-writer/series.json" "['series'][0]['description']" "A 5-part series on compilers"
assert_json_field "articles is empty list" "$HOME/.tech-essay-writer/series.json" "['series'][0]['articles']" "[]"

# Extract series ID for subsequent tests
SERIES_ID=$(python3 -c "import json; print(json.load(open('$HOME/.tech-essay-writer/series.json'))['series'][0]['id'])")

# Test 3: verify ID format
assert_contains "ID has ser- prefix" "ser-" "$SERIES_ID"

# Test 4: add article to series
out=$(bash "$SERIES_SCRIPT" add "$SERIES_ID" "art-100" "Part 1: Lexing")
assert_contains "add returns success" "Added" "$out"

# Test 5: add multiple articles, verify ordering
bash "$SERIES_SCRIPT" add "$SERIES_ID" "art-101" "Part 2: Parsing" >/dev/null
bash "$SERIES_SCRIPT" add "$SERIES_ID" "art-102" "Part 3: AST" >/dev/null
pos1=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['position'] for a in arts if a['article_id']=='art-100'))")
pos2=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['position'] for a in arts if a['article_id']=='art-101'))")
pos3=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['position'] for a in arts if a['article_id']=='art-102'))")
assert_eq "first article position is 1" "1" "$pos1"
assert_eq "second article position is 2" "2" "$pos2"
assert_eq "third article position is 3" "3" "$pos3"

# Test 6: list series
out=$(bash "$SERIES_SCRIPT" list)
assert_contains "list shows series name" "Building a Compiler" "$out"
assert_contains "list shows article count" "3 articles" "$out"

# Test 7: show series details
out=$(bash "$SERIES_SCRIPT" show "$SERIES_ID")
assert_contains "show displays name" "Building a Compiler" "$out"
assert_contains "show displays article" "Part 1: Lexing" "$out"
assert_contains "show displays article count" "Articles (3)" "$out"

# Test 8: context output for prompt injection
out=$(bash "$SERIES_SCRIPT" context "$SERIES_ID")
assert_contains "context has series_name" "series_name" "$out"
assert_contains "context has articles array" "articles" "$out"
# Verify it's valid JSON
if python3 -c "import json; json.loads('''$out''')" 2>/dev/null; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1)); echo "FAIL: context output is not valid JSON"
fi

# Test 9: set-arc
out=$(bash "$SERIES_SCRIPT" set-arc "$SERIES_ID" "From lexer to codegen, building complexity")
assert_contains "set-arc returns success" "Set arc" "$out"
arc=$(python3 -c "import json; print(json.load(open('$HOME/.tech-essay-writer/series.json'))['series'][0]['narrative_arc'])")
assert_eq "arc description stored" "From lexer to codegen, building complexity" "$arc"

# Test 10: set-summary for article
out=$(bash "$SERIES_SCRIPT" set-summary "$SERIES_ID" "art-100" "We built a tokenizer that handles Unicode")
assert_contains "set-summary returns success" "Set summary" "$out"
summary=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['summary'] for a in arts if a['article_id']=='art-100'))")
assert_eq "summary stored" "We built a tokenizer that handles Unicode" "$summary"

# Test 11: next-position returns correct number
next=$(bash "$SERIES_SCRIPT" next-position "$SERIES_ID")
assert_eq "next position is 4" "4" "$next"

# Test 12: search by name
out=$(bash "$SERIES_SCRIPT" search "compiler")
assert_contains "search finds by name" "Building a Compiler" "$out"

# Test 13: search by description
out=$(bash "$SERIES_SCRIPT" search "5-part")
assert_contains "search finds by description" "Building a Compiler" "$out"

# Test 14: reorder article
bash "$SERIES_SCRIPT" reorder "$SERIES_ID" "art-102" 1 >/dev/null
new_pos=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['position'] for a in arts if a['article_id']=='art-102'))")
assert_eq "reorder moves article to position 1" "1" "$new_pos"

# Test 15: add article with explicit position
bash "$SERIES_SCRIPT" add "$SERIES_ID" "art-103" "Interlude: Theory" 2 >/dev/null
epos=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/series.json')); arts=d['series'][0]['articles']; print(next(a['position'] for a in arts if a['article_id']=='art-103'))")
assert_eq "explicit position respected" "2" "$epos"

# Test 16: duplicate series names allowed
out=$(bash "$SERIES_SCRIPT" create "Building a Compiler" "Different description")
assert_contains "duplicate name allowed" "Created series" "$out"
count=$(python3 -c "import json; print(len(json.load(open('$HOME/.tech-essay-writer/series.json'))['series']))")
assert_eq "two series exist" "2" "$count"

# Test 17: empty series handling
SERIES_ID2=$(python3 -c "import json; print(json.load(open('$HOME/.tech-essay-writer/series.json'))['series'][1]['id'])")
out=$(bash "$SERIES_SCRIPT" show "$SERIES_ID2")
assert_contains "show empty series" "Articles (0)" "$out"
next=$(bash "$SERIES_SCRIPT" next-position "$SERIES_ID2")
assert_eq "next position for empty series is 1" "1" "$next"

# Test 18: search with no results
out=$(bash "$SERIES_SCRIPT" search "nonexistent-xyz-topic")
assert_contains "search no results" "No matching" "$out"

# Test 19: context includes narrative_arc
ctx=$(bash "$SERIES_SCRIPT" context "$SERIES_ID")
assert_contains "context includes narrative_arc" "narrative_arc" "$ctx"

# Test 20: set-summary for nonexistent article fails
if bash "$SERIES_SCRIPT" set-summary "$SERIES_ID" "art-999" "some summary" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: set-summary should fail for nonexistent article"
else
  PASS=$((PASS + 1))
fi

# ============================================================
echo ""
echo "=== analytics-feedback.sh ==="
# ============================================================

# Clean analytics state
rm -f "$HOME/.tech-essay-writer/analytics.json"

# Test 21: record single metric
out=$(bash "$ANALYTICS_SCRIPT" record "art-200" "views" "1500")
assert_contains "record returns success" "Recorded" "$out"

# Test 22: analytics file created with correct structure
assert_file_exists "analytics.json created" "$HOME/.tech-essay-writer/analytics.json"
assert_json_field "article entry exists" "$HOME/.tech-essay-writer/analytics.json" "['articles']['art-200']['metrics']['views']" "1500"

# Test 23: record-batch multiple metrics
out=$(bash "$ANALYTICS_SCRIPT" record-batch "art-201" '{"views":800,"shares":30,"comments":5}')
assert_contains "record-batch returns success" "Recorded 3 metrics" "$out"
assert_json_field "batch views stored" "$HOME/.tech-essay-writer/analytics.json" "['articles']['art-201']['metrics']['views']" "800"
assert_json_field "batch shares stored" "$HOME/.tech-essay-writer/analytics.json" "['articles']['art-201']['metrics']['shares']" "30"

# Test 24: query article metrics
out=$(bash "$ANALYTICS_SCRIPT" query "art-200")
assert_contains "query shows views value" "1500" "$out"
assert_contains "query shows views" "views" "$out"

# Test 25: top articles by views
bash "$ANALYTICS_SCRIPT" record "art-200" "shares" "45" >/dev/null
out=$(bash "$ANALYTICS_SCRIPT" top views 5)
assert_contains "top shows art-200 first" "art-200" "$out"

# Test 26: top articles by shares
out=$(bash "$ANALYTICS_SCRIPT" top shares 5)
assert_contains "top by shares shows art-200" "art-200" "$out"

# Test 27: record updates existing metric (overwrites)
bash "$ANALYTICS_SCRIPT" record "art-200" "views" "2000" >/dev/null
val=$(python3 -c "import json; print(json.load(open('$HOME/.tech-essay-writer/analytics.json'))['articles']['art-200']['metrics']['views'])")
assert_eq "metric updated to new value" "2000" "$val"

# Test 28: trends with increasing data
bash "$ANALYTICS_SCRIPT" record "art-202" "views" "500" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-203" "views" "3000" >/dev/null
out=$(bash "$ANALYTICS_SCRIPT" trends)
assert_contains "trends output exists" "trends" "$out"

# Test 29: feed-taste writes performance_insights to taste memory
rm -f "$HOME/.tech-essay-writer/taste-memory.json"
echo '{}' > "$HOME/.tech-essay-writer/taste-memory.json"
out=$(bash "$ANALYTICS_SCRIPT" feed-taste "$TMPDIR")
assert_contains "feed-taste returns success" "Performance insights updated" "$out"
assert_file_exists "taste memory exists" "$HOME/.tech-essay-writer/taste-memory.json"
has_insights=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/taste-memory.json')); print('yes' if 'performance_insights' in d else 'no')")
assert_eq "taste has performance_insights" "yes" "$has_insights"

# Test 30: performance_insights structure
has_tags=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/taste-memory.json')); print(type(d['performance_insights']['best_performing_tags']).__name__)")
assert_eq "best_performing_tags is list" "list" "$has_tags"
has_avg=$(python3 -c "import json; d=json.load(open('$HOME/.tech-essay-writer/taste-memory.json')); print(type(d['performance_insights']['avg_views']).__name__)")
assert_eq "avg_views is numeric" "float" "$has_avg"

# Test 31: feed-taste with no data gracefully handles empty
rm -f "$HOME/.tech-essay-writer/analytics.json"
echo '{}' > "$HOME/.tech-essay-writer/taste-memory.json"
out=$(bash "$ANALYTICS_SCRIPT" feed-taste "$TMPDIR")
assert_contains "feed-taste no data handled" "No analytics data" "$out"

# Recreate analytics data for remaining tests
bash "$ANALYTICS_SCRIPT" record "art-300" "views" "1000" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-300" "shares" "50" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-301" "views" "500" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-301" "shares" "20" >/dev/null

# Test 32: summary output formatting
out=$(bash "$ANALYTICS_SCRIPT" summary)
assert_contains "summary shows article count" "2 articles" "$out"
assert_contains "summary shows views metric" "views" "$out"

# Test 33: compare two articles
out=$(bash "$ANALYTICS_SCRIPT" compare "art-300" "art-301")
assert_contains "compare shows both IDs" "art-300" "$out"
assert_contains "compare shows metric names" "views" "$out"

# Test 34: compare with missing article
out=$(bash "$ANALYTICS_SCRIPT" compare "art-300" "art-999")
assert_contains "compare missing article handled" "No data" "$out"

# Test 35: record invalid metric name rejected
if bash "$ANALYTICS_SCRIPT" record "art-300" "invalid_metric" "100" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid metric"
else
  PASS=$((PASS + 1))
fi

# Test 36: valid metrics list (7 metrics)
for m in views shares comments likes bookmarks read_time_avg bounce_rate; do
  if bash "$ANALYTICS_SCRIPT" record "art-valid" "$m" "1" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: metric '$m' should be valid"
  fi
done

# Test 37: top with custom N
bash "$ANALYTICS_SCRIPT" record "art-t1" "views" "100" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-t2" "views" "200" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-t3" "views" "300" >/dev/null
out=$(bash "$ANALYTICS_SCRIPT" top views 2)
assert_contains "top with n=2 shows Top 2" "Top 2" "$out"

# Test 38: analytics file initialization
rm -f "$HOME/.tech-essay-writer/analytics.json"
out=$(bash "$ANALYTICS_SCRIPT" summary)
assert_contains "summary works on fresh init" "No analytics data" "$out"
assert_file_exists "analytics.json auto-created" "$HOME/.tech-essay-writer/analytics.json"

# Test 39: record-batch validates invalid metrics
if bash "$ANALYTICS_SCRIPT" record-batch "art-300" '{"bad_metric":100}' 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: record-batch should reject invalid metric"
else
  PASS=$((PASS + 1))
fi

# Test 40: record-batch rejects invalid JSON
if bash "$ANALYTICS_SCRIPT" record-batch "art-300" 'not json' 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: record-batch should reject invalid JSON"
else
  PASS=$((PASS + 1))
fi

# ============================================================
echo ""
echo "=== Integration tests ==="
# ============================================================

# Setup a project for orchestrator tests
PROJ="$TMPDIR/int-project"
mkdir -p "$PROJ/.essay-state"

# Test 41: pipeline-state init with --series flag
out=$(bash "$PIPELINE_SCRIPT" init "$PROJ" "Compiler Part 1" --series "$SERIES_ID")
assert_contains "init with --series returns success" "initialized" "$out"
sid=$(python3 -c "import json; print(json.load(open('$PROJ/.essay-state/pipeline-state.json')).get('series_id',''))")
assert_eq "series_id stored in pipeline state" "$SERIES_ID" "$sid"

# Test 42: pipeline-state init without --series has no series_id
PROJ2="$TMPDIR/int-project2"
mkdir -p "$PROJ2"
bash "$PIPELINE_SCRIPT" init "$PROJ2" "Standalone Article" >/dev/null
has_sid=$(python3 -c "import json; d=json.load(open('$PROJ2/.essay-state/pipeline-state.json')); print('yes' if 'series_id' in d else 'no')")
assert_eq "no series_id when not specified" "no" "$has_sid"

# Test 43: orchestrator build-series-context with valid series
out=$(bash "$ORCHESTRATE_SCRIPT" "$PROJ" "$SCRIPT_DIR" build-series-context)
assert_contains "build-series-context shows series context" "Series Context" "$out"
assert_contains "build-series-context includes series data" "Building a Compiler" "$out"

# Test 44: orchestrator build-series-context without series
out=$(bash "$ORCHESTRATE_SCRIPT" "$PROJ2" "$SCRIPT_DIR" build-series-context)
assert_contains "build-series-context no series" "no series" "$out"

# Test 45: orchestrator build-analytics-insights
# Set up taste memory with performance_insights
echo '{}' > "$HOME/.tech-essay-writer/taste-memory.json"
rm -f "$HOME/.tech-essay-writer/analytics.json"
bash "$ANALYTICS_SCRIPT" record "art-400" "views" "1000" >/dev/null
bash "$ANALYTICS_SCRIPT" record "art-400" "shares" "50" >/dev/null
bash "$ANALYTICS_SCRIPT" feed-taste "$TMPDIR" >/dev/null
out=$(bash "$ORCHESTRATE_SCRIPT" "$PROJ" "$SCRIPT_DIR" build-analytics-insights)
assert_contains "build-analytics-insights output" "Performance Insights" "$out"

# Test 46: series context appears in writer prompt when series_id set
# Create minimal outline so writer prompt can build
echo '{"sections":[]}' > "$PROJ/.essay-state/outline-A.json"
bash "$PIPELINE_SCRIPT" set-field "$PROJ" "outline_variant" "A" >/dev/null
out=$(bash "$ORCHESTRATE_SCRIPT" "$PROJ" "$SCRIPT_DIR" build-writer-prompt "A")
assert_contains "writer prompt includes series context" "Series Context" "$out"

# Test 47: series nav appears in format prompts when series_id set
# Create minimal draft so format prompt can build
echo "# Test Draft" > "$PROJ/.essay-state/draft-v1.md"
out=$(bash "$ORCHESTRATE_SCRIPT" "$PROJ" "$SCRIPT_DIR" build-format-prompts "internal")
assert_contains "format prompt includes series navigation" "Series Navigation" "$out"

# ============================================================
# Summary
# ============================================================

echo ""
echo "========================================"
echo "test_series_analytics: $((PASS + FAIL)) tests | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
