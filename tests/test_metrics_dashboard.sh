#!/usr/bin/env bash
# Tests for metrics-dashboard.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PASS=0
FAIL=0

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected to contain: $needle"
    echo "  actual (first 200 chars): ${haystack:0:200}"
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

assert_line_width() {
  local desc="$1" output="$2" max_width="$3"
  local too_wide=0
  while IFS= read -r line; do
    if [ ${#line} -gt "$max_width" ]; then
      too_wide=$((too_wide + 1))
    fi
  done <<< "$output"
  if [ "$too_wide" -eq 0 ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  $too_wide lines exceed $max_width chars"
  fi
}

# ============================================================
# Set up mock global data directory
# ============================================================
MOCK_HOME="$TMPDIR/mock_home/.tech-essay-writer"
mkdir -p "$MOCK_HOME"

# Override HOME for the dashboard to read global data from our mock
export HOME="$TMPDIR/mock_home"

# ============================================================
# Create test project with pipeline state
# ============================================================
PROJECT="$TMPDIR/test-project"
STATE="$PROJECT/.essay-state"
mkdir -p "$STATE"

# Pipeline state
cat > "$STATE/pipeline-state.json" << 'EOF'
{
  "topic": "Building Reliable Microservices",
  "stage": "review",
  "created_at": "2026-04-01T10:00:00Z",
  "updated_at": "2026-04-06T12:00:00Z",
  "language": "en",
  "materials_count": 5,
  "outline_variant": "deep-dive",
  "draft_version": 2,
  "refinement_round": 1,
  "max_refinement_rounds": 3,
  "reviews": {
    "review-technical": {"file": "review-technical.json", "rating": "PASS", "issues_count": 1},
    "review-editor": {"file": "review-editor.json", "rating": "NEEDS_EDITING", "issues_count": 3}
  },
  "review_panel_complete": false,
  "completed": false,
  "artifacts": []
}
EOF

# Review files
cat > "$STATE/review-technical.json" << 'EOF'
{
  "rating": "PASS",
  "summary": "Code examples are accurate and well-tested.",
  "issues": [
    {"severity": "minor", "issue": "Missing error handling in example 3"}
  ]
}
EOF

cat > "$STATE/review-editor.json" << 'EOF'
{
  "rating": "NEEDS_EDITING",
  "summary": "Good structure but needs tightening.",
  "hook_score": 7,
  "clarity_score": 8,
  "flow_score": 6,
  "voice_score": 7,
  "engagement_score": 7,
  "economy_score": 5,
  "issues": [
    {"severity": "major", "issue": "Introduction too long", "suggestion": "Cut to 2 paragraphs"},
    {"severity": "minor", "issue": "Passive voice in section 3"},
    {"severity": "minor", "issue": "Inconsistent terminology"}
  ]
}
EOF

cat > "$STATE/review-adversarial.json" << 'EOF'
{
  "rating": "SOLID",
  "summary": "Arguments hold up well.",
  "issues": [],
  "attacks": [
    {"attack": "Cherry-picked benchmarks", "severity": "major", "defense": "Add methodology section"}
  ]
}
EOF

cat > "$STATE/review-audience.json" << 'EOF'
{
  "rating": "MEH",
  "reader_a": {"rating": "WOULD_SHARE", "feedback": "Great practical examples"},
  "reader_b": {"rating": "MEH", "feedback": "Needs more context for juniors"},
  "issues": []
}
EOF

cat > "$STATE/review-seo.json" << 'EOF'
{
  "rating": "OPTIMIZED",
  "summary": "Good keyword coverage.",
  "issues": [
    {"severity": "minor", "issue": "Meta description could be shorter"}
  ]
}
EOF

# Quality score
cat > "$STATE/quality-score.json" << 'EOF'
{
  "composite_score": 7.2,
  "readiness": "CLOSE",
  "dimension_scores": {"technical": 9.0, "editor": 6.7, "adversarial": 8.5, "audience": 7.0, "seo": 8.9},
  "reviews_available": 5,
  "reviews_expected": 7
}
EOF

# Review panel summary
cat > "$STATE/review-panel-summary.json" << 'EOF'
{
  "reviews_count": 5,
  "consensus": "NEEDS_MINOR_REVISION",
  "critical_issues": [],
  "all_issues": [
    {"severity": "major", "issue": "Introduction too long", "source_reviewer": "review-editor"},
    {"severity": "major", "issue": "Cherry-picked benchmarks", "source_reviewer": "review-adversarial"},
    {"severity": "minor", "issue": "Passive voice in section 3", "source_reviewer": "review-editor"}
  ]
}
EOF

# Readability score file
cat > "$STATE/readability-draft.json" << 'EOF'
{
  "file": "draft.md",
  "metrics": {
    "flesch_kincaid_grade": 11.5,
    "flesch_reading_ease": 45.2,
    "avg_sentence_length": 22.3,
    "avg_syllables_per_word": 1.8,
    "total_words": 2500,
    "total_sentences": 112,
    "total_paragraphs": 28,
    "total_syllables": 4500,
    "grade_interpretation": "college_prep"
  }
}
EOF

# Create checkpoints for stage timing
CKPT_DIR="$STATE/checkpoints"
mkdir -p "$CKPT_DIR/intake-20260401T100500"
cat > "$CKPT_DIR/intake-20260401T100500/pipeline-state.json" << 'EOF'
{"stage": "intake", "updated_at": "2026-04-01T10:05:00Z"}
EOF

mkdir -p "$CKPT_DIR/research-20260401T120000"
cat > "$CKPT_DIR/research-20260401T120000/pipeline-state.json" << 'EOF'
{"stage": "research", "updated_at": "2026-04-01T12:00:00Z"}
EOF

mkdir -p "$CKPT_DIR/outline-20260402T090000"
cat > "$CKPT_DIR/outline-20260402T090000/pipeline-state.json" << 'EOF'
{"stage": "outline", "updated_at": "2026-04-02T09:00:00Z"}
EOF

mkdir -p "$CKPT_DIR/draft-20260403T140000"
cat > "$CKPT_DIR/draft-20260403T140000/pipeline-state.json" << 'EOF'
{"stage": "draft", "updated_at": "2026-04-03T14:00:00Z"}
EOF

# ============================================================
# Taste memory (multiple articles for trends)
# ============================================================
cat > "$MOCK_HOME/taste-memory.json" << 'EOF'
{
  "preferred_variant": "deep-dive",
  "tone_preferences": ["technical", "direct"],
  "structural_preferences": {"intro_length": "short", "code_first": "true"},
  "topics_written": [
    {"topic": "Intro to Kubernetes", "date": "2026-01-15T00:00:00Z", "variant": "tutorial", "refinement_rounds": 3},
    {"topic": "Docker Best Practices", "date": "2026-02-01T00:00:00Z", "variant": "deep-dive", "refinement_rounds": 2},
    {"topic": "CI/CD Pipeline Design", "date": "2026-02-20T00:00:00Z", "variant": "deep-dive", "refinement_rounds": 2},
    {"topic": "Terraform at Scale", "date": "2026-03-10T00:00:00Z", "variant": "tutorial", "refinement_rounds": 1},
    {"topic": "Observability Patterns", "date": "2026-03-25T00:00:00Z", "variant": "narrative", "refinement_rounds": 1}
  ],
  "articles_count": 5,
  "learned_patterns": [
    {"tone_shift": "more_formal", "length_change": "condensed", "code_density_change": "more_code", "insights": ["Prefers concise over verbose"]},
    {"tone_shift": "neutral", "length_change": "condensed", "code_density_change": "unchanged", "insights": ["Prefers shorter paragraphs"]},
    {"tone_shift": "more_formal", "length_change": "similar", "code_density_change": "more_code", "insights": ["Prefers concise over verbose"]}
  ],
  "updated_at": "2026-03-25T00:00:00Z"
}
EOF

# ============================================================
# Expertise graph
# ============================================================
cat > "$MOCK_HOME/expertise-graph.json" << 'EOF'
{
  "topics": {
    "Kubernetes": {"article_count": 3, "authority_score": 7.0, "tags": ["devops", "containers"], "first_article": "2025-06-01", "last_article": "2026-01-15"},
    "Docker": {"article_count": 2, "authority_score": 5.0, "tags": ["devops", "containers"], "first_article": "2025-09-01", "last_article": "2026-02-01"},
    "CI/CD": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "automation"], "first_article": "2026-02-20", "last_article": "2026-02-20"},
    "Terraform": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "iac"], "first_article": "2026-03-10", "last_article": "2026-03-10"},
    "Observability": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "monitoring"], "first_article": "2026-03-25", "last_article": "2026-03-25"}
  },
  "tag_index": {
    "devops": ["Kubernetes", "Docker", "CI/CD", "Terraform", "Observability"],
    "containers": ["Kubernetes", "Docker"],
    "automation": ["CI/CD"],
    "iac": ["Terraform"],
    "monitoring": ["Observability"]
  },
  "updated_at": "2026-03-25T00:00:00Z"
}
EOF

# ============================================================
# Author profile
# ============================================================
cat > "$MOCK_HOME/author-profile.json" << 'EOF'
{
  "name": "Jackson",
  "role": "Senior Engineer",
  "company": "TechCorp",
  "expertise_areas": [
    {"topic": "Kubernetes", "level": "expert"},
    {"topic": "Go", "level": "intermediate"}
  ],
  "updated_at": "2026-01-01T00:00:00Z"
}
EOF

# ============================================================
# Analytics data
# ============================================================
cat > "$MOCK_HOME/analytics.json" << 'EOF'
{
  "articles": {
    "intro-kubernetes": {
      "metrics": {"views": 5200, "shares": 340, "comments": 45, "likes": 890, "bookmarks": 120},
      "first_recorded": "2026-01-20T00:00:00Z",
      "last_updated": "2026-02-15T00:00:00Z"
    },
    "docker-best-practices": {
      "metrics": {"views": 3100, "shares": 210, "comments": 28, "likes": 450, "bookmarks": 85},
      "first_recorded": "2026-02-05T00:00:00Z",
      "last_updated": "2026-03-01T00:00:00Z"
    },
    "cicd-pipeline-design": {
      "metrics": {"views": 1800, "shares": 95, "comments": 12, "likes": 210, "bookmarks": 40},
      "first_recorded": "2026-02-25T00:00:00Z",
      "last_updated": "2026-03-15T00:00:00Z"
    },
    "terraform-at-scale": {
      "metrics": {"views": 4500, "shares": 280, "comments": 33, "likes": 620, "bookmarks": 95},
      "first_recorded": "2026-03-15T00:00:00Z",
      "last_updated": "2026-04-01T00:00:00Z"
    }
  },
  "updated_at": "2026-04-01T00:00:00Z"
}
EOF

# ============================================================
# Create markdown article in project for writing stats
# ============================================================
cat > "$PROJECT/draft.md" << 'MDEOF'
# Building Reliable Microservices

## Introduction

Microservices architecture has become the dominant approach for building
scalable systems. In this article we explore patterns that make services
resilient to failure. We cover circuit breakers, retries, and bulkheads.

## Circuit Breakers

The circuit breaker pattern prevents cascading failures across services.
When a downstream service fails, the circuit breaker trips and returns
a fallback response instead of propagating the error.

```go
func NewCircuitBreaker(threshold int, timeout time.Duration) *CircuitBreaker {
    return &CircuitBreaker{
        threshold: threshold,
        timeout:   timeout,
        state:     StateClosed,
    }
}

func (cb *CircuitBreaker) Call(fn func() error) error {
    if cb.state == StateOpen {
        if time.Since(cb.lastFailure) > cb.timeout {
            cb.state = StateHalfOpen
        } else {
            return ErrCircuitOpen
        }
    }
    err := fn()
    if err != nil {
        cb.failures++
        if cb.failures >= cb.threshold {
            cb.state = StateOpen
            cb.lastFailure = time.Now()
        }
        return err
    }
    cb.failures = 0
    cb.state = StateClosed
    return nil
}
```

This implementation tracks failure counts and transitions between closed,
open, and half-open states. The timeout allows periodic recovery attempts.

## Retry with Backoff

Transient failures are common in distributed systems. An exponential backoff
strategy prevents overwhelming a struggling service with retry storms.

```go
func RetryWithBackoff(fn func() error, maxRetries int) error {
    for i := 0; i < maxRetries; i++ {
        err := fn()
        if err == nil {
            return nil
        }
        wait := time.Duration(math.Pow(2, float64(i))) * time.Second
        time.Sleep(wait)
    }
    return fmt.Errorf("max retries exceeded")
}
```

## Bulkhead Pattern

Bulkheads isolate failures to prevent one slow service from consuming all
available resources. Each service gets a dedicated thread pool or connection
pool. When one pool is exhausted, other services continue operating normally.

## Conclusion

Building reliable microservices requires combining multiple resilience
patterns. Circuit breakers prevent cascading failures, retries handle
transient issues, and bulkheads provide fault isolation. Together these
patterns create systems that degrade gracefully under stress.
MDEOF

# ============================================================
echo "=== metrics-dashboard.sh tests ==="
# ============================================================

# --- Test 1: Dashboard runs without errors ---
out=$(bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$PROJECT" 2>&1)
rc=$?
assert_exit_code "T1: dashboard exits 0" "0" "$rc"

# --- Test 2: Shows header with project path ---
assert_contains "T2: header shows project path" "$PROJECT" "$out"

# --- Test 3: Shows Pipeline Health section ---
assert_contains "T3: pipeline health section" "PIPELINE HEALTH" "$out"

# --- Test 4: Shows current stage ---
assert_contains "T4: shows current stage REVIEW" "REVIEW" "$out"

# --- Test 5: Shows topic ---
assert_contains "T5: shows topic" "Building Reliable Microservices" "$out"

# --- Test 6: Shows refinement round ---
assert_contains "T6: shows refinement rounds" "1/3" "$out"

# --- Test 7: Shows Quality Trends section ---
assert_contains "T7: quality trends section" "QUALITY TRENDS" "$out"

# --- Test 8: Shows articles in taste memory ---
assert_contains "T8: shows articles count" "Articles in taste memory: 5" "$out"

# --- Test 9: Shows refinement rounds trend ---
assert_contains "T9: shows trend direction" "IMPROVING" "$out"

# --- Test 10: Shows Review Panel Stats section ---
assert_contains "T10: review panel section" "REVIEW PANEL STATS" "$out"

# --- Test 11: Shows reviewer names ---
assert_contains "T11: shows technical reviewer" "technical" "$out"

# --- Test 12: Shows average score ---
assert_contains "T12: shows average score" "Average score" "$out"

# --- Test 13: Shows reviewer agreement ---
assert_contains "T13: shows reviewer agreement" "Reviewer agreement" "$out"

# --- Test 14: Shows composite quality ---
assert_contains "T14: shows composite quality" "7.2/10" "$out"

# --- Test 15: Shows Author Growth section ---
assert_contains "T15: author growth section" "AUTHOR GROWTH" "$out"

# --- Test 16: Shows expertise topics ---
assert_contains "T16: shows Kubernetes topic" "Kubernetes" "$out"

# --- Test 17: Shows total topics count ---
assert_contains "T17: shows total topics" "Total topics" "$out"

# --- Test 18: Shows authority distribution ---
assert_contains "T18: shows authority distribution" "Authority Distribution" "$out"

# --- Test 19: Shows Platform Performance section ---
assert_contains "T19: platform performance section" "PLATFORM PERFORMANCE" "$out"

# --- Test 20: Shows aggregate views ---
assert_contains "T20: shows Views metric" "Views" "$out"

# --- Test 21: Shows articles tracked count ---
assert_contains "T21: shows articles tracked" "Articles tracked: 4" "$out"

# --- Test 22: Shows engagement rate ---
assert_contains "T22: shows engagement rate" "Engagement rate" "$out"

# --- Test 23: Shows Writing Stats section ---
assert_contains "T23: writing stats section" "WRITING STATS" "$out"

# --- Test 24: Shows word count ---
assert_contains "T24: shows word count stats" "Word Count" "$out"

# --- Test 25: Shows code density ---
assert_contains "T25: shows code density" "Code Density" "$out"

# --- Test 26: Shows readability data ---
assert_contains "T26: shows readability" "Readability Scores" "$out"

# --- Test 27: Shows Flesch-Kincaid grade ---
assert_contains "T27: shows FK grade" "Flesch-Kincaid grade" "$out"

# --- Test 28: Output is terminal-friendly width ---
assert_line_width "T28: line width <= 100" "$out" 100

# --- Test 29: Shows footer with timestamp ---
assert_contains "T29: footer has timestamp" "Dashboard generated" "$out"

# ============================================================
# Edge case: empty project with no state
# ============================================================

EMPTY_PROJECT="$TMPDIR/empty-project"
mkdir -p "$EMPTY_PROJECT"

# --- Test 30: Empty project does not crash ---
out_empty=$(bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$EMPTY_PROJECT" 2>&1)
rc_empty=$?
assert_exit_code "T30: empty project exits 0" "0" "$rc_empty"

# --- Test 31: Empty project shows not initialized ---
assert_contains "T31: empty project shows not initialized" "not initialized" "$out_empty"

# --- Test 32: Empty project shows all sections ---
assert_contains "T32: empty project has all 6 sections" "WRITING STATS" "$out_empty"

# ============================================================
# Edge case: project with state but no reviews
# ============================================================

NOREVIEW_PROJECT="$TMPDIR/noreview-project"
NOREVIEW_STATE="$NOREVIEW_PROJECT/.essay-state"
mkdir -p "$NOREVIEW_STATE"

cat > "$NOREVIEW_STATE/pipeline-state.json" << 'EOF'
{
  "topic": "Testing Article",
  "stage": "draft",
  "created_at": "2026-04-05T10:00:00Z",
  "updated_at": "2026-04-05T14:00:00Z",
  "language": "en",
  "refinement_round": 0,
  "max_refinement_rounds": 3,
  "reviews": {},
  "completed": false
}
EOF

# --- Test 33: No reviews shows appropriate message ---
out_nr=$(bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$NOREVIEW_PROJECT" 2>&1)
assert_contains "T33: no reviews shows message" "No review data" "$out_nr"

# --- Test 34: Draft stage displayed ---
assert_contains "T34: draft stage shown" "DRAFT" "$out_nr"

# ============================================================
# Edge case: completed project
# ============================================================

COMPLETE_PROJECT="$TMPDIR/complete-project"
COMPLETE_STATE="$COMPLETE_PROJECT/.essay-state"
mkdir -p "$COMPLETE_STATE"

cat > "$COMPLETE_STATE/pipeline-state.json" << 'EOF'
{
  "topic": "Completed Article",
  "stage": "complete",
  "created_at": "2026-04-01T10:00:00Z",
  "updated_at": "2026-04-04T16:00:00Z",
  "language": "en",
  "refinement_round": 2,
  "max_refinement_rounds": 3,
  "reviews": {},
  "completed": true,
  "completed_at": "2026-04-04T16:00:00Z"
}
EOF

# --- Test 35: Completed project shows COMPLETE ---
out_comp=$(bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$COMPLETE_PROJECT" 2>&1)
assert_contains "T35: shows COMPLETE" "COMPLETE" "$out_comp"

# ============================================================
# Edge case: no global data (clean HOME)
# ============================================================

CLEAN_HOME="$TMPDIR/clean_home"
mkdir -p "$CLEAN_HOME"

# --- Test 36: No global data does not crash ---
out_clean=$(HOME="$CLEAN_HOME" bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$PROJECT" 2>&1)
rc_clean=$?
assert_exit_code "T36: no global data exits 0" "0" "$rc_clean"

# --- Test 37: No global data still shows review panel from local state ---
assert_contains "T37: local reviews still shown without global data" "technical" "$out_clean"

# ============================================================
# Edge case: taste memory with only 1 article
# ============================================================

SINGLE_HOME="$TMPDIR/single_home/.tech-essay-writer"
mkdir -p "$SINGLE_HOME"
cat > "$SINGLE_HOME/taste-memory.json" << 'EOF'
{
  "topics_written": [
    {"topic": "Solo Article", "date": "2026-04-01T00:00:00Z", "variant": "tutorial", "refinement_rounds": 2}
  ],
  "articles_count": 1
}
EOF

# --- Test 38: Single article shows appropriate message ---
out_single=$(HOME="$TMPDIR/single_home" bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" "$EMPTY_PROJECT" 2>&1)
assert_contains "T38: single article message" "Only 1 article" "$out_single"

# ============================================================
# Verify section ordering
# ============================================================

# --- Test 39: Sections appear in correct order ---
pos_pipeline=$(echo "$out" | grep -n "PIPELINE HEALTH" | head -1 | cut -d: -f1)
pos_quality=$(echo "$out" | grep -n "QUALITY TRENDS" | head -1 | cut -d: -f1)
pos_review=$(echo "$out" | grep -n "REVIEW PANEL STATS" | head -1 | cut -d: -f1)
pos_author=$(echo "$out" | grep -n "AUTHOR GROWTH" | head -1 | cut -d: -f1)
pos_platform=$(echo "$out" | grep -n "PLATFORM PERFORMANCE" | head -1 | cut -d: -f1)
pos_writing=$(echo "$out" | grep -n "WRITING STATS" | head -1 | cut -d: -f1)

if [ "$pos_pipeline" -lt "$pos_quality" ] && \
   [ "$pos_quality" -lt "$pos_review" ] && \
   [ "$pos_review" -lt "$pos_author" ] && \
   [ "$pos_author" -lt "$pos_platform" ] && \
   [ "$pos_platform" -lt "$pos_writing" ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: T39: sections not in correct order"
  echo "  pipeline=$pos_pipeline quality=$pos_quality review=$pos_review author=$pos_author platform=$pos_platform writing=$pos_writing"
fi

# ============================================================
# Verify visual elements
# ============================================================

# --- Test 40: Contains bar chart characters ---
assert_contains "T40: contains bar chart chars" "█" "$out"

# --- Test 41: Contains horizontal rules ---
assert_contains "T41: contains horizontal rules" "═" "$out"

# --- Test 42: Shows top tags ---
assert_contains "T42: shows top tags" "Top Tags" "$out"

# ============================================================
# Edge case: analytics with engagement metrics
# ============================================================

# --- Test 43: Shows shares in platform section ---
assert_contains "T43: shows Shares metric" "Shares" "$out"

# --- Test 44: Shows top articles by views ---
assert_contains "T44: shows top articles" "Top Articles" "$out"

# --- Test 45: Shows style variant distribution ---
assert_contains "T45: shows variant distribution" "deep-dive" "$out"

# ============================================================
# Test with default directory (cwd)
# ============================================================

# --- Test 46: Runs with default project_dir (cwd) ---
out_cwd=$(cd "$PROJECT" && bash "$SCRIPT_DIR/scripts/metrics-dashboard.sh" 2>&1)
rc_cwd=$?
assert_exit_code "T46: default cwd exits 0" "0" "$rc_cwd"

# --- Test 47: Shows editing patterns from taste memory ---
assert_contains "T47: shows editing patterns" "Editing Patterns" "$out"

# --- Test 48: Shows issue breakdown ---
assert_contains "T48: shows issue breakdown" "Issue Breakdown" "$out"

# ============================================================
echo ""
echo "========================================"
echo "RESULTS: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
