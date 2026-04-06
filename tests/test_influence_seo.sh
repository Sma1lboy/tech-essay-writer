#!/usr/bin/env bash
# Tests for influence-score.sh and seo-metadata.sh
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

assert_json_field_gte() {
  local desc="$1" file="$2" field="$3" threshold="$4"
  local actual
  actual=$(python3 -c "import json; print(json.load(open('$file'))$field)" 2>/dev/null || echo "0")
  if python3 -c "assert float('$actual') >= float('$threshold')" 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected >= $threshold, got: $actual"
  fi
}

assert_json_field_lte() {
  local desc="$1" file="$2" field="$3" threshold="$4"
  local actual
  actual=$(python3 -c "import json; print(json.load(open('$file'))$field)" 2>/dev/null || echo "0")
  if python3 -c "assert float('$actual') <= float('$threshold')" 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected <= $threshold, got: $actual"
  fi
}

# Helper: set up a minimal project with state dir
setup_project() {
  local proj="$TMPDIR/proj-$1"
  mkdir -p "$proj/.essay-state"
  echo "$proj"
}

# ============================================================
echo "=== influence-score.sh ==="
# ============================================================

# --- Test 1: Runs with empty state dir ---
PROJ=$(setup_project "inf-empty")
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_contains "influence-score runs with empty state" "influence_score" "$out"
assert_file_exists "influence-score.json created (empty)" "$PROJ/.essay-state/influence-score.json"

# --- Test 2: Output is valid JSON ---
assert_contains "output has tier field" "tier" "$out"
assert_contains "output has dimensions" "dimensions" "$out"

# --- Test 3: Default scores are mid-range ---
assert_json_field_gte "default score >= 1" "$PROJ/.essay-state/influence-score.json" "['influence_score']" "1"
assert_json_field_lte "default score <= 10" "$PROJ/.essay-state/influence-score.json" "['influence_score']" "10"

# --- Test 4: With research-synthesis (blue ocean topic) ---
PROJ=$(setup_project "inf-novelty")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Quantum ML Pipelines","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"competitive_landscape":{"existing_articles":[]},"gap":"No articles cover quantum ML pipeline orchestration","unique_angle":"First practical guide to quantum-classical hybrid pipelines"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_file_exists "influence-score.json with novelty" "$PROJ/.essay-state/influence-score.json"
# Blue ocean (0 competitors) + gap + angle should push novelty high
assert_json_field_gte "novelty high for blue ocean" "$PROJ/.essay-state/influence-score.json" "['dimensions']['topic_novelty']" "8"

# --- Test 5: Saturated topic ---
PROJ=$(setup_project "inf-saturated")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"React Hooks","stage":"review","language":"en"}
EOF
python3 -c "
import json
articles = [{'title': f'Article {i}'} for i in range(15)]
json.dump({'competitive_landscape': {'existing_articles': articles}}, open('$PROJ/.essay-state/research-synthesis.json', 'w'))
"
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_lte "novelty lower for saturated topic" "$PROJ/.essay-state/influence-score.json" "['dimensions']['topic_novelty']" "5"

# --- Test 6: SEO review integration ---
PROJ=$(setup_project "inf-seo")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test SEO","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-seo.json" << 'EOF'
{"rating":"OPTIMIZED","keywords":["test","seo","optimization","search"],"title_score":8,"issues":[]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_gte "SEO score high for OPTIMIZED" "$PROJ/.essay-state/influence-score.json" "['dimensions']['seo_potential']" "8"

# --- Test 7: SEO with critical issues ---
PROJ=$(setup_project "inf-seo-bad")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test SEO","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-seo.json" << 'EOF'
{"rating":"INVISIBLE","issues":[{"severity":"critical"},{"severity":"critical"}]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_lte "SEO score low for INVISIBLE+critical" "$PROJ/.essay-state/influence-score.json" "['dimensions']['seo_potential']" "3"

# --- Test 8: Social package integration ---
PROJ=$(setup_project "inf-social")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Social Test","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/social-package.json" << 'EOF'
{"twitter_thread":"Thread about...","linkedin_post":"Post...","hn_title":"Show HN: Test","reddit_post":"Check this out","hashtags":["#test","#dev","#coding"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_gte "social score with full package" "$PROJ/.essay-state/influence-score.json" "['dimensions']['social_shareability']" "7"

# --- Test 9: Audience review integration ---
PROJ=$(setup_project "inf-audience")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Audience Test","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-audience.json" << 'EOF'
{"reader_a":{"rating":"WOULD_SHARE"},"reader_b":{"rating":"WOULD_SHARE"},"target_audience":"all developers","engagement_prediction":"high"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_gte "audience high for WOULD_SHARE+broad" "$PROJ/.essay-state/influence-score.json" "['dimensions']['audience_reach']" "9"

# --- Test 10: Audience MEH/SKIP ---
PROJ=$(setup_project "inf-audience-bad")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Niche Test","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-audience.json" << 'EOF'
{"reader_a":{"rating":"SKIP"},"reader_b":{"rating":"MEH"}}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field_lte "audience low for SKIP/MEH" "$PROJ/.essay-state/influence-score.json" "['dimensions']['audience_reach']" "5"

# --- Test 11: Verbose output ---
PROJ=$(setup_project "inf-verbose")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Verbose Test","stage":"review","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" verbose 2>&1)
assert_contains "verbose shows score" "Influence Score:" "$out"
assert_contains "verbose shows tier" "Tier:" "$out"

# --- Test 12: Tier classification ---
PROJ=$(setup_project "inf-tier-high")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test","stage":"review","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"competitive_landscape":{"existing_articles":[]},"gap":"Major gap in coverage","unique_angle":"Revolutionary approach"}
EOF
cat > "$PROJ/.essay-state/review-seo.json" << 'EOF'
{"rating":"OPTIMIZED","keywords":["a","b","c","d"],"title_score":9,"issues":[]}
EOF
cat > "$PROJ/.essay-state/social-package.json" << 'EOF'
{"twitter_thread":"Great thread...","linkedin_post":"Post","hn_title":"Show HN: Amazing","reddit_post":"Check out","hashtags":["#a","#b","#c"]}
EOF
cat > "$PROJ/.essay-state/review-audience.json" << 'EOF'
{"reader_a":{"rating":"WOULD_SHARE"},"reader_b":{"rating":"WOULD_SHARE"},"target_audience":"all developers","engagement_prediction":"high"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_contains "high influence has correct tier" "HIGH_INFLUENCE\|MODERATE_INFLUENCE" "$out"

# --- Test 13: Weights sum to 1.0 ---
PROJ=$(setup_project "inf-weights")
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
weights_sum=$(python3 -c "import json; d=json.load(open('$PROJ/.essay-state/influence-score.json')); print(sum(d['weights'].values()))")
assert_eq "weights sum to 1.0" "1.0" "$weights_sum"

# --- Test 14: All 5 dimensions present ---
dims=$(python3 -c "import json; d=json.load(open('$PROJ/.essay-state/influence-score.json')); print(len(d['dimensions']))")
assert_eq "5 dimensions present" "5" "$dims"

# --- Test 15: Corrupt review file handled ---
PROJ=$(setup_project "inf-corrupt")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Corrupt Test","stage":"review","language":"en"}
EOF
echo "NOT JSON" > "$PROJ/.essay-state/review-seo.json"
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_contains "handles corrupt review" "influence_score" "$out"

# ============================================================
echo ""
echo "=== seo-metadata.sh ==="
# ============================================================

# --- Test 16: Runs with empty state dir ---
PROJ=$(setup_project "seo-empty")
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_contains "seo-metadata runs with empty state" "opengraph_tags" "$out"
assert_file_exists "seo-metadata.json created (empty)" "$PROJ/.essay-state/seo-metadata.json"

# --- Test 17: Extracts title from article ---
PROJ=$(setup_project "seo-title")
cat > "$PROJ/.essay-state/final-external.md" << 'EOF'
# Building Scalable Microservices with Go

Microservices architecture has evolved significantly in recent years.
This article explores best practices for building scalable Go services.

## Introduction

Go is an excellent choice for microservices because of its concurrency model.
EOF
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Go Microservices","stage":"complete","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_json_field "title extracted from heading" "$PROJ/.essay-state/seo-metadata.json" "['title']" "Building Scalable Microservices with Go"

# --- Test 18: Description from first paragraph ---
assert_contains "description from paragraph" "Microservices architecture" "$out"

# --- Test 19: OpenGraph tags present ---
assert_contains "has og:title" "og:title" "$out"
assert_contains "has og:type" "og:type" "$out"
assert_contains "has og:description" "og:description" "$out"

# --- Test 20: Meta tags present ---
assert_contains "has meta description" '"description"' "$out"
assert_contains "has meta robots" "robots" "$out"

# --- Test 21: Twitter card tags ---
assert_contains "has twitter:card" "twitter:card" "$out"
assert_json_field "twitter card type" "$PROJ/.essay-state/seo-metadata.json" "['twitter_card']['twitter:card']" "summary_large_image"

# --- Test 22: JSON-LD structured data ---
assert_json_field "JSON-LD type is TechArticle" "$PROJ/.essay-state/seo-metadata.json" "['structured_data']['@type']" "TechArticle"
assert_json_field "JSON-LD context is schema.org" "$PROJ/.essay-state/seo-metadata.json" "['structured_data']['@context']" "https://schema.org"

# --- Test 23: Keyword density analysis ---
kd_count=$(python3 -c "import json; print(len(json.load(open('$PROJ/.essay-state/seo-metadata.json'))['keyword_density']))")
assert_eq "keyword density has entries" "true" "$([ "$kd_count" -gt 0 ] && echo true || echo false)"

# --- Test 24: Word count calculated ---
wc=$(python3 -c "import json; print(json.load(open('$PROJ/.essay-state/seo-metadata.json'))['total_words'])")
assert_eq "word count > 0" "true" "$([ "$wc" -gt 0 ] && echo true || echo false)"

# --- Test 25: Reads from draft when no final ---
PROJ=$(setup_project "seo-draft")
cat > "$PROJ/.essay-state/draft-v2.md" << 'EOF'
# Draft Article About Testing

Testing is a fundamental practice in software engineering.
This guide covers unit testing, integration testing, and end-to-end testing.

## Unit Testing

Unit tests verify individual functions work correctly.
EOF
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Software Testing","stage":"draft","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_json_field "title from draft" "$PROJ/.essay-state/seo-metadata.json" "['title']" "Draft Article About Testing"

# --- Test 26: SEO review keywords integrated ---
PROJ=$(setup_project "seo-keywords")
cat > "$PROJ/.essay-state/final-external.md" << 'EOF'
# Kubernetes Deployment Strategies

Learn about blue-green deployments, canary releases, and rolling updates for Kubernetes.

## Blue-Green Deployments

Blue-green deployment is a technique for zero-downtime releases.
EOF
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Kubernetes","stage":"complete","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-seo.json" << 'EOF'
{"rating":"OPTIMIZED","keywords":["kubernetes","deployment","blue-green","canary"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_contains "SEO keywords in meta" "kubernetes" "$out"

# --- Test 27: Chinese language metadata ---
PROJ=$(setup_project "seo-chinese")
cat > "$PROJ/.essay-state/final-external.md" << 'EOF'
# 使用Go构建微服务架构

微服务架构在近年来得到了快速发展，本文将探讨Go语言在微服务中的最佳实践。

## 简介

Go语言因其出色的并发模型而成为微服务的绝佳选择。
EOF
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Go微服务","stage":"complete","language":"zh"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_json_field "Chinese locale in OG" "$PROJ/.essay-state/seo-metadata.json" "['opengraph_tags']['og:locale']" "zh_CN"
assert_json_field "Chinese inLanguage in JSON-LD" "$PROJ/.essay-state/seo-metadata.json" "['structured_data']['inLanguage']" "zh-CN"

# --- Test 28: Verbose output ---
PROJ=$(setup_project "seo-verbose")
cat > "$PROJ/.essay-state/final-external.md" << 'EOF'
# Verbose Test Article

This is a test article for verbose output.
EOF
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Verbose","stage":"complete","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" verbose 2>&1)
assert_contains "verbose shows title" "SEO Metadata for:" "$out"
assert_contains "verbose shows word count" "Word count:" "$out"

# --- Test 29: Canonical URL placeholder ---
PROJ=$(setup_project "seo-canon")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test","stage":"complete","language":"en"}
EOF
echo "# Test" > "$PROJ/.essay-state/final-external.md"
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_json_field "canonical URL is template" "$PROJ/.essay-state/seo-metadata.json" "['canonical_url']" "{{CANONICAL_URL}}"

# --- Test 30: Code blocks excluded from keyword density ---
PROJ=$(setup_project "seo-codeblock")
cat > "$PROJ/.essay-state/final-external.md" << 'ARTICLE'
# Code Article

This article discusses JavaScript patterns.

```javascript
function unusualFunctionNameXYZ() {
  const unusualFunctionNameXYZ = true;
  return unusualFunctionNameXYZ;
}
```

JavaScript is great for web development.
ARTICLE
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"JavaScript","stage":"complete","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
# unusualFunctionNameXYZ should not appear in keywords since it's inside a code block
kd_keywords=$(python3 -c "import json; kd=json.load(open('$PROJ/.essay-state/seo-metadata.json'))['keyword_density']; print(' '.join(k['keyword'] for k in kd))")
assert_not_contains "code block content excluded" "unusualfunctionnamexyz" "$kd_keywords"

# --- Test 31: Fallback description when no paragraph ---
PROJ=$(setup_project "seo-fallback")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Fallback Topic","stage":"complete","language":"en"}
EOF
# No article file at all
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_contains "fallback description for missing article" "Fallback Topic" "$out"

# --- Test 32: Author from pipeline state ---
PROJ=$(setup_project "seo-author")
echo "# Test" > "$PROJ/.essay-state/final-external.md"
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test","stage":"complete","language":"en","author":"Jane Dev"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_json_field "author from pipeline state" "$PROJ/.essay-state/seo-metadata.json" "['meta_tags']['author']" "Jane Dev"

# --- Test 33: Atomic write (no partial files) ---
PROJ=$(setup_project "seo-atomic")
echo "# Atomic Test" > "$PROJ/.essay-state/final-external.md"
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Atomic","stage":"complete","language":"en"}
EOF
bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" >/dev/null 2>&1
# Check no .tmp files left behind
tmp_count=$(find "$PROJ/.essay-state" -name "*.tmp.*" | wc -l | tr -d ' ')
assert_eq "no tmp files left" "0" "$tmp_count"

# --- Test 34: Influence score atomic write ---
PROJ=$(setup_project "inf-atomic")
bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" >/dev/null 2>&1
tmp_count=$(find "$PROJ/.essay-state" -name "*.tmp.*" | wc -l | tr -d ' ')
assert_eq "no influence tmp files left" "0" "$tmp_count"

# --- Test 35: Headline truncated to 110 chars in JSON-LD ---
PROJ=$(setup_project "seo-long-title")
long_title="This Is An Extremely Long Title That Goes Way Beyond One Hundred And Ten Characters To Test The Truncation Logic In The Structured Data Schema Generation"
echo "# $long_title" > "$PROJ/.essay-state/final-external.md"
echo "Some paragraph text here." >> "$PROJ/.essay-state/final-external.md"
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Long Title","stage":"complete","language":"en"}
EOF
bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" >/dev/null 2>&1
headline_len=$(python3 -c "import json; print(len(json.load(open('$PROJ/.essay-state/seo-metadata.json'))['structured_data']['headline']))")
assert_eq "headline <= 110 chars" "true" "$([ "$headline_len" -le 110 ] && echo true || echo false)"

# ============================================================
echo ""
echo "=== orchestrate.sh integration ==="
# ============================================================

# --- Test 36: build-influence-score command dispatches ---
PROJ=$(setup_project "orch-influence")
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-influence-score 2>&1)
assert_contains "orchestrator dispatches influence" "influence_score" "$out"

# --- Test 37: build-seo-metadata command dispatches ---
PROJ=$(setup_project "orch-seo")
echo "# Orch Test" > "$PROJ/.essay-state/final-external.md"
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Orchestrator SEO","stage":"complete","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-seo-metadata 2>&1)
assert_contains "orchestrator dispatches seo-metadata" "opengraph_tags" "$out"

# --- Test 38: Usage shows new commands ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" x x invalid 2>&1 || true)
assert_contains "usage shows build-influence-score" "build-influence-score" "$out"
assert_contains "usage shows build-seo-metadata" "build-seo-metadata" "$out"

# --- Test 39: Influence score with no expertise graph ---
# (expertise-graph.sh read returns default when no file exists)
PROJ=$(setup_project "inf-no-expertise")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Unknown Area","stage":"review","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJ" "$SCRIPT_DIR" 2>&1)
assert_json_field "expertise defaults to 3.0 for unknown" "$PROJ/.essay-state/influence-score.json" "['dimensions']['expertise_match']" "3.0"

# --- Test 40: SEO metadata comma-separated keywords ---
PROJ=$(setup_project "seo-comma-kw")
echo "# Comma Test" > "$PROJ/.essay-state/final-external.md"
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Comma","stage":"complete","language":"en"}
EOF
cat > "$PROJ/.essay-state/review-seo.json" << 'EOF'
{"rating":"OPTIMIZED","keywords":"react, typescript, testing"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJ" 2>&1)
assert_contains "comma keywords parsed" "react" "$out"

# ============================================================
echo ""
echo "================================"
echo "Pass: $PASS | Fail: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED ✅"
else
  echo "SOME TESTS FAILED ❌"
fi
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
