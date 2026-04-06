#!/usr/bin/env bash
# Tests for progress-display.sh and publishing-guide.sh
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

assert_json_field() {
  local desc="$1" json_str="$2" field="$3" expected="$4"
  local actual
  actual=$(echo "$json_str" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$field','MISSING'))" 2>/dev/null || echo "PARSE_ERROR")
  assert_eq "$desc" "$expected" "$actual"
}

assert_exit_zero() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — non-zero exit"
  fi
}

assert_exit_nonzero() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — expected non-zero exit but got 0"
  else
    PASS=$((PASS + 1))
  fi
}

# Helper: create a test project with pipeline state
make_project() {
  local dir="$1" stage="$2" topic="${3:-Test Article}"
  mkdir -p "$dir/.essay-state"
  python3 -c "
import json
state = {
    'topic': '$topic',
    'stage': '$stage',
    'draft_version': 2,
    'refinement_round': 1,
    'max_refinement_rounds': 3,
    'materials_count': 4,
    'language': 'en',
    'reviews': {},
    'review_panel_complete': False,
    'completed': False,
    'series_id': None,
}
if '$stage' == 'complete':
    state['completed'] = True
    state['completed_at'] = '2026-01-01T00:00:00Z'
json.dump(state, open('$dir/.essay-state/pipeline-state.json', 'w'))
"
}

# Helper: add review files
add_review() {
  local dir="$1" reviewer="$2" rating="$3"
  python3 -c "
import json
review = {
    'reviewer': '$reviewer',
    'rating': '$rating',
    'summary': 'Test review',
    'issues': [
        {'severity': 'minor', 'location': 'Section 1', 'issue': 'Test issue', 'suggestion': 'Fix it'}
    ]
}
json.dump(review, open('$dir/.essay-state/review-$reviewer.json', 'w'))
"
  # Also update pipeline state reviews
  python3 -c "
import json
with open('$dir/.essay-state/pipeline-state.json') as f:
    state = json.load(f)
state.setdefault('reviews', {})['$reviewer'] = {'rating': '$rating', 'issues_count': 1}
with open('$dir/.essay-state/pipeline-state.json', 'w') as f:
    json.dump(state, f)
"
}

# Helper: add quality score
add_quality() {
  local dir="$1" score="$2" readiness="$3"
  python3 -c "
import json
quality = {
    'composite_score': $score,
    'readiness': '$readiness',
    'dimension_scores': {'technical': 8.0, 'editor': 7.5, 'adversarial': 6.0},
    'reviews_available': 3,
    'reviews_expected': 7,
}
json.dump(quality, open('$dir/.essay-state/quality-score.json', 'w'))
"
}

# Helper: add SEO metadata
add_seo() {
  local dir="$1"
  python3 -c "
import json
seo = {
    'tags': ['react', 'javascript', 'tutorial'],
    'keywords': ['react hooks', 'state management'],
    'meta_description': 'A comprehensive guide to React hooks and state management patterns.',
}
json.dump(seo, open('$dir/.essay-state/seo-metadata.json', 'w'))
"
}

export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

# ============================================================
# PROGRESS-DISPLAY.SH TESTS
# ============================================================

echo "=== progress-display.sh: no state ==="

PROJ="$TMPDIR/proj-empty"
mkdir -p "$PROJ"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "no state — shows not initialized" "not initialized" "$out"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
assert_contains "no state json — shows error" "not_initialized" "$out"

echo "=== progress-display.sh: intake stage ==="

PROJ="$TMPDIR/proj-intake"
make_project "$PROJ" "intake"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "intake — shows INTAKE" "INTAKE" "$out"
assert_contains "intake — shows current stage" "intake" "$out"
assert_contains "intake — has progress bar" "Progress:" "$out"
assert_contains "intake — shows completion" "%" "$out"

echo "=== progress-display.sh: each stage indicator ==="

for stage in intake research outline draft review refinement polish complete; do
  PROJ="$TMPDIR/proj-$stage"
  make_project "$PROJ" "$stage"
  out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
  assert_contains "$stage — shows stage name" "$stage" "$out"
  assert_contains "$stage — has current indicator" "●\|✓" "$out"
done

echo "=== progress-display.sh: completion percentages ==="

PROJ="$TMPDIR/proj-pct-intake"
make_project "$PROJ" "intake"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
pct=$(echo "$out" | python3 -c "import json,sys; print(float(json.load(sys.stdin)['completion_pct']))")
assert_eq "intake completion is 0%" "0.0" "$pct"

PROJ="$TMPDIR/proj-pct-draft"
make_project "$PROJ" "draft"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
pct=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['completion_pct'])")
assert_eq "draft completion is 25%" "25.0" "$pct"

PROJ="$TMPDIR/proj-pct-complete"
make_project "$PROJ" "complete"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
pct=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['completion_pct'])")
assert_eq "complete is 100%" "100.0" "$pct"

echo "=== progress-display.sh: JSON format ==="

PROJ="$TMPDIR/proj-json"
make_project "$PROJ" "review" "JSON Test Topic"
add_review "$PROJ" "technical" "PASS"
add_quality "$PROJ" 7.5 "CLOSE"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
assert_json_field "json has topic" "$out" "topic" "JSON Test Topic"
assert_json_field "json has stage" "$out" "stage" "review"
assert_json_field "json has completed" "$out" "completed" "False"
assert_json_field "json has language" "$out" "language" "en"
assert_json_field "json has draft_version" "$out" "draft_version" "2"

# Check nested fields
has_stages=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['stages']))")
assert_eq "json has 8 stages" "8" "$has_stages"

has_quality=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['quality']['composite_score'])")
assert_eq "json has quality score" "7.5" "$has_quality"

has_review=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['reviews']['technical']['rating'])")
assert_eq "json has technical review" "PASS" "$has_review"

echo "=== progress-display.sh: review details ==="

PROJ="$TMPDIR/proj-reviews"
make_project "$PROJ" "review"
add_review "$PROJ" "technical" "PASS"
add_review "$PROJ" "editor" "NEEDS_EDITING"
add_review "$PROJ" "adversarial" "VULNERABLE"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "shows review dashboard" "Review Dashboard" "$out"
assert_contains "shows technical rating" "PASS" "$out"
assert_contains "shows editor rating" "NEEDS_EDITING" "$out"
assert_contains "shows adversarial rating" "VULNERABLE" "$out"
assert_contains "shows review count" "3/7" "$out"

echo "=== progress-display.sh: review progress in completion ==="

PROJ="$TMPDIR/proj-review-pct"
make_project "$PROJ" "review"
add_review "$PROJ" "technical" "PASS"
add_review "$PROJ" "editor" "NEEDS_EDITING"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
pct=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['completion_pct'])")
# review stage base = 45% (intake+research+outline+draft weights) + 2/7 of review weight (20%)
expected="50.7"
assert_eq "review with 2/7 progress" "$expected" "$pct"

echo "=== progress-display.sh: quality metrics ==="

PROJ="$TMPDIR/proj-quality"
make_project "$PROJ" "refinement"
add_quality "$PROJ" 8.5 "READY"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "shows quality score" "8.5/10" "$out"
assert_contains "shows readiness" "READY" "$out"

out_v=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --verbose 2>&1)
assert_contains "verbose shows dimension scores" "technical" "$out_v"
assert_contains "verbose shows dimension bar" "editor" "$out_v"

echo "=== progress-display.sh: verbose mode ==="

PROJ="$TMPDIR/proj-verbose"
make_project "$PROJ" "review"
add_review "$PROJ" "technical" "PASS"
add_quality "$PROJ" 7.0 "CLOSE"

out_normal=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
out_verbose=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --verbose 2>&1)

# Verbose shows pending reviewers
assert_contains "verbose shows PENDING reviewers" "PENDING" "$out_verbose"
# Verbose shows dimension scores
assert_contains "verbose shows dimensions" "Dimension Scores" "$out_verbose"

echo "=== progress-display.sh: artifacts ==="

PROJ="$TMPDIR/proj-artifacts"
make_project "$PROJ" "polish"
echo "# Test Draft" > "$PROJ/.essay-state/draft-v1.md"
echo "# Final Internal" > "$PROJ/.essay-state/final-internal.md"
echo '{"twitter_thread":"test"}' > "$PROJ/.essay-state/social-package.json"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
artifacts=$(echo "$out" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['artifacts']))")
assert_contains "artifacts has draft" "draft" "$artifacts"
assert_contains "artifacts has final-internal" "final-internal" "$artifacts"
assert_contains "artifacts has social-package" "social-package" "$artifacts"

out_v=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --verbose 2>&1)
assert_contains "verbose lists artifacts" "Artifacts:" "$out_v"

echo "=== progress-display.sh: series_id ==="

PROJ="$TMPDIR/proj-series"
make_project "$PROJ" "draft"
python3 -c "
import json
with open('$PROJ/.essay-state/pipeline-state.json') as f:
    s = json.load(f)
s['series_id'] = 'react-series-001'
with open('$PROJ/.essay-state/pipeline-state.json','w') as f:
    json.dump(s, f)
"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "shows series id" "react-series-001" "$out"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
sid=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['series_id'])")
assert_eq "json has series_id" "react-series-001" "$sid"

echo "=== progress-display.sh: completed pipeline ==="

PROJ="$TMPDIR/proj-complete"
make_project "$PROJ" "complete"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "complete shows 100%" "100" "$out"
assert_contains "complete shows completed_at" "Completed at" "$out"
# All stages should show checkmarks
assert_not_contains "complete has no pending" "○" "$out"

echo "=== progress-display.sh: corrupt state ==="

PROJ="$TMPDIR/proj-corrupt"
mkdir -p "$PROJ/.essay-state"
echo "NOT_JSON" > "$PROJ/.essay-state/pipeline-state.json"

assert_exit_nonzero "corrupt state exits non-zero" bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ"
out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1 || true)
assert_contains "corrupt json shows error" "corrupt_state" "$out"

echo "=== progress-display.sh: invalid format option ==="

PROJ="$TMPDIR/proj-badfmt"
make_project "$PROJ" "draft"
assert_exit_nonzero "invalid format rejected" bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format xml

echo "=== progress-display.sh: draft version and refinement ==="

PROJ="$TMPDIR/proj-drafts"
make_project "$PROJ" "refinement"
python3 -c "
import json
with open('$PROJ/.essay-state/pipeline-state.json') as f:
    s = json.load(f)
s['draft_version'] = 3
s['refinement_round'] = 2
json.dump(s, open('$PROJ/.essay-state/pipeline-state.json','w'))
"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "shows draft version 3" "3" "$out"
assert_contains "shows refinement round 2/3" "2/3" "$out"

echo "=== progress-display.sh: materials count ==="

PROJ="$TMPDIR/proj-materials"
make_project "$PROJ" "research"
python3 -c "
import json
with open('$PROJ/.essay-state/pipeline-state.json') as f:
    s = json.load(f)
s['materials_count'] = 12
json.dump(s, open('$PROJ/.essay-state/pipeline-state.json','w'))
"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" 2>&1)
assert_contains "shows materials count" "12" "$out"

echo "=== progress-display.sh: stage map in JSON ==="

PROJ="$TMPDIR/proj-stagemap"
make_project "$PROJ" "outline"

out=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJ" --format json 2>&1)
# intake and research should be completed, outline should be current
intake_status=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stages'][0]['status'])")
assert_eq "intake status is completed" "completed" "$intake_status"
research_status=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stages'][1]['status'])")
assert_eq "research status is completed" "completed" "$research_status"
outline_status=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stages'][2]['status'])")
assert_eq "outline status is current" "current" "$outline_status"
draft_status=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stages'][3]['status'])")
assert_eq "draft status is pending" "pending" "$draft_status"


# ============================================================
# PUBLISHING-GUIDE.SH TESTS
# ============================================================

echo "=== publishing-guide.sh: each platform ==="

for platform in internal external medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "$platform" 2>&1)
  assert_contains "$platform — has publishing guide header" "Publishing Guide" "$out"
  assert_contains "$platform — has steps" "Steps:" "$out"
  assert_contains "$platform — has SEO tips" "SEO Tips:" "$out"
  assert_contains "$platform — has formatting" "Formatting:" "$out"
  assert_contains "$platform — has limits" "Limits:" "$out"
  assert_contains "$platform — has checklist" "Checklist:" "$out"
done

echo "=== publishing-guide.sh: all platforms ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" all 2>&1)
assert_contains "all — lists internal" "internal" "$out"
assert_contains "all — lists external" "external" "$out"
assert_contains "all — lists medium" "medium" "$out"
assert_contains "all — lists devto" "devto" "$out"
assert_contains "all — lists hashnode" "hashnode" "$out"
assert_contains "all — lists wechat" "wechat" "$out"
assert_contains "all — lists juejin" "juejin" "$out"
assert_contains "all — shows Available platforms" "Available platforms" "$out"

echo "=== publishing-guide.sh: invalid platform ==="

assert_exit_nonzero "invalid platform rejected" bash "$SCRIPT_DIR/scripts/publishing-guide.sh" twitter

echo "=== publishing-guide.sh: JSON format per platform ==="

for platform in internal external medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "$platform" --format json 2>&1)
  p_name=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['platform'])" 2>/dev/null)
  assert_eq "$platform json — platform field" "$platform" "$p_name"

  has_steps=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['steps']) > 0)")
  assert_eq "$platform json — has steps" "True" "$has_steps"

  has_tips=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['seo_tips']) > 0)")
  assert_eq "$platform json — has seo_tips" "True" "$has_tips"

  has_checklist=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['checklist']) > 0)")
  assert_eq "$platform json — has checklist" "True" "$has_checklist"
done

echo "=== publishing-guide.sh: all JSON format ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" all --format json 2>&1)
count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
assert_eq "all json has 7 platforms" "7" "$count"

first_platform=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['platform'])")
assert_eq "all json first is internal" "internal" "$first_platform"

echo "=== publishing-guide.sh: with article metadata ==="

PROJ="$TMPDIR/proj-meta"
make_project "$PROJ" "complete" "React Hooks Deep Dive"
add_seo "$PROJ"

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" medium "$PROJ" 2>&1)
assert_contains "metadata — shows article title" "React Hooks Deep Dive" "$out"
assert_contains "metadata — shows suggested tags" "react" "$out"

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" medium "$PROJ" --format json 2>&1)
meta_title=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin).get('article_metadata',{}).get('article_title','MISSING'))")
assert_eq "json metadata has title" "React Hooks Deep Dive" "$meta_title"

meta_tags=$(echo "$out" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin).get('article_metadata',{}).get('suggested_tags',[])))")
assert_contains "json metadata has tags" "react" "$meta_tags"

echo "=== publishing-guide.sh: without project dir ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" devto 2>&1)
assert_contains "no project — still shows guide" "Publishing Guide" "$out"
assert_not_contains "no project — no article metadata" "Article:" "$out"

echo "=== publishing-guide.sh: Chinese platforms in Chinese ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" wechat 2>&1)
assert_contains "wechat tips in Chinese" "标题" "$out"
assert_contains "wechat steps in Chinese" "确认" "$out"

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" juejin 2>&1)
assert_contains "juejin tips in Chinese" "标题" "$out"
assert_contains "juejin steps in Chinese" "确认" "$out"

echo "=== publishing-guide.sh: platform-specific content ==="

# Medium should mention subtitles
out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" medium 2>&1)
assert_contains "medium mentions subtitle" "subtitle" "$out"
assert_contains "medium mentions publications" "publication" "$out"

# dev.to should mention front matter
out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" devto 2>&1)
assert_contains "devto mentions front matter" "front matter" "$out"
assert_contains "devto mentions canonical" "canonical" "$out"

# Hashnode should mention custom domain
out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" hashnode 2>&1)
assert_contains "hashnode mentions custom domain" "custom domain" "$out"

echo "=== publishing-guide.sh: limits in JSON ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" medium --format json 2>&1)
title_max=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['limits']['title_max'])")
assert_contains "medium title limit" "100" "$title_max"
tags_max=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['limits']['tags_max'])")
assert_contains "medium tags limit" "5" "$tags_max"

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" devto --format json 2>&1)
tags_max=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['limits']['tags_max'])")
assert_contains "devto tags limit" "4" "$tags_max"

echo "=== publishing-guide.sh: invalid format ==="

assert_exit_nonzero "invalid format rejected" bash "$SCRIPT_DIR/scripts/publishing-guide.sh" medium --format yaml

echo "=== publishing-guide.sh: tags advice ==="

for platform in internal external medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "$platform" 2>&1)
  assert_contains "$platform — has tags advice" "Tags:" "$out"
done

echo "=== publishing-guide.sh: all json structure ==="

out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" all --format json 2>&1)
for i in 0 1 2 3 4 5 6; do
  has_name=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d[$i].get('name','')) > 0)")
  assert_eq "all json item $i has name" "True" "$has_name"
done

echo "=== publishing-guide.sh: SEO tips count ==="

# Each platform should have at least 5 SEO tips
for platform in internal external medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "$platform" --format json 2>&1)
  tip_count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['seo_tips']))")
  at_least_5=$(python3 -c "print('True' if int('$tip_count') >= 5 else 'False')")
  assert_eq "$platform has >= 5 SEO tips" "True" "$at_least_5"
done

echo "=== publishing-guide.sh: checklist count ==="

# Each platform should have at least 6 checklist items
for platform in internal external medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publishing-guide.sh" "$platform" --format json 2>&1)
  cl_count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['checklist']))")
  at_least_6=$(python3 -c "print('True' if int('$cl_count') >= 6 else 'False')")
  assert_eq "$platform has >= 6 checklist items" "True" "$at_least_6"
done


# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "========================================"
echo "Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
