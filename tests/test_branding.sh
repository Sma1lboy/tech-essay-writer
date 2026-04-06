#!/usr/bin/env bash
# Tests for author-profile.sh, expertise-graph.sh, social-package.md, and orchestrate.sh build-social-prompt
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

# Use temp home to avoid polluting real data
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

# === author-profile.sh tests ===

echo "=== author-profile.sh ==="

# Test init
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" init)
assert_contains "init creates profile" "initialized" "$out"
assert_file_exists "profile file created" "$HOME/.tech-essay-writer/author-profile.json"

# Test init idempotent
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" init)
assert_contains "init idempotent" "already exists" "$out"

# Test set name
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set name "Alice Chen")
assert_contains "set name" "Set name" "$out"

# Test set role
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set role "Senior Engineer")
assert_contains "set role" "Set role" "$out"

# Test set company
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set company "TechCorp")
assert_contains "set company" "Set company" "$out"

# Test set bio
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set bio "Building distributed systems")
assert_contains "set bio" "Set bio" "$out"

# Test set invalid field
if bash "$SCRIPT_DIR/scripts/author-profile.sh" set invalid "value" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid field"
else
  PASS=$((PASS + 1))
fi

# Test read
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_contains "read shows name" "Alice Chen" "$out"
assert_contains "read shows role" "Senior Engineer" "$out"
assert_contains "read shows company" "TechCorp" "$out"

# Test add-expertise
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "distributed-systems" expert)
assert_contains "add expertise" "Added expertise" "$out"

out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "kubernetes" intermediate)
assert_contains "add second expertise" "Added expertise" "$out"

# Test add-expertise updates existing
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "kubernetes" expert)
assert_contains "update expertise level" "Added expertise" "$out"

# Verify expertise in read
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_contains "read shows expertise topic" "distributed-systems" "$out"
assert_contains "read shows expertise level" "expert" "$out"

# Test invalid expertise level
if bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "topic" "invalid-level" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid level"
else
  PASS=$((PASS + 1))
fi

# Test remove-expertise
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" remove-expertise "kubernetes")
assert_contains "remove expertise" "Removed expertise" "$out"

# Verify removed
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_not_contains "kubernetes removed from read" "kubernetes" "$out"

# Test remove non-existent
if bash "$SCRIPT_DIR/scripts/author-profile.sh" remove-expertise "nonexistent" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error on non-existent topic"
else
  PASS=$((PASS + 1))
fi

# Test set-voice
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set-voice "Concise, technical, with dry humor")
assert_contains "set voice" "Set writing voice" "$out"

# Verify voice in read
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_contains "read shows voice" "Concise, technical" "$out"

# Test set-social
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social twitter "@alicechen")
assert_contains "set social twitter" "Set social.twitter" "$out"

out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social github "alicechen")
assert_contains "set social github" "Set social.github" "$out"

out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social linkedin "alice-chen")
assert_contains "set social linkedin" "Set social.linkedin" "$out"

# Test invalid social platform
if bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social invalid "@handle" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid platform"
else
  PASS=$((PASS + 1))
fi

# Test get-bio
bio=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-bio)
assert_contains "bio has name" "Alice Chen" "$bio"
assert_contains "bio has role and company" "Senior Engineer at TechCorp" "$bio"
assert_contains "bio has expertise" "distributed-systems" "$bio"

# Test get-social-handles
handles=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-social-handles)
assert_contains "handles has twitter" "@alicechen" "$handles"
assert_contains "handles has github" "alicechen" "$handles"
assert_contains "handles is JSON" "{" "$handles"

# Test read on fresh profile (no init)
export HOME="$TMPDIR/fakehome2"
mkdir -p "$HOME"
out=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_contains "empty profile message" "No author profile" "$out"

# Test get-bio on empty profile
bio=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-bio)
assert_eq "empty bio returns empty" "" "$bio"

# Test get-social-handles on empty profile
handles=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-social-handles)
assert_eq "empty handles returns empty JSON" "{}" "$handles"

# === expertise-graph.sh tests ===

echo "=== expertise-graph.sh ==="

export HOME="$TMPDIR/fakehome3"
mkdir -p "$HOME"

# Test read on empty graph
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" read)
assert_contains "empty graph has topics" "topics" "$out"

# Test update
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "distributed-systems" kafka consensus)
assert_contains "update topic" "Updated topic" "$out"

# Test query
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query "distributed-systems")
assert_contains "query shows topic" "distributed-systems" "$out"
assert_contains "query shows article count" "Articles: 1" "$out"
assert_contains "query shows tags" "kafka" "$out"

# Test update increments count
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "distributed-systems" raft >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query "distributed-systems")
assert_contains "update increments count" "Articles: 2" "$out"
assert_contains "update merges tags" "raft" "$out"

# Test update new topic
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "frontend" react typescript >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query "frontend")
assert_contains "new topic tracked" "Articles: 1" "$out"

# Test top
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" top 2)
assert_contains "top shows header" "Top 2" "$out"
assert_contains "top shows distributed-systems" "distributed-systems" "$out"

# Test top with default
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" top)
assert_contains "top default shows topics" "distributed-systems" "$out"

# Test query non-existent
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query "nonexistent")
assert_contains "query unknown topic" "No data" "$out"

# Test authority score calculation
# distributed-systems has 2 articles + recency bonus of 1.0 (just published) = min(10, 2*2 + 1.0) = 5.0
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query "distributed-systems")
assert_contains "authority score calculated" "Authority score: 5.0/10" "$out"

# Test read dumps full graph
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" read)
assert_contains "read has topics" "distributed-systems" "$out"
assert_contains "read has tag_index" "tag_index" "$out"
assert_contains "read has kafka in tags" "kafka" "$out"

# Test tag index
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" read)
assert_contains "tag index has consensus" "consensus" "$out"
assert_contains "tag index has raft" "raft" "$out"

# Test suggest with no author profile
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" suggest)
# Should not error, just show what it can
PASS=$((PASS + 1))

# Test suggest with author profile containing gap
export HOME="$TMPDIR/fakehome4"
mkdir -p "$HOME/.tech-essay-writer"
# Create a profile with expertise not in graph
python3 -c "
import json
profile = {
    'name': 'Test',
    'expertise_areas': [
        {'topic': 'machine-learning', 'level': 'expert', 'added_at': '2025-01-01'},
        {'topic': 'distributed-systems', 'level': 'authority', 'added_at': '2025-01-01'}
    ]
}
with open('$HOME/.tech-essay-writer/author-profile.json', 'w') as f:
    json.dump(profile, f)
"
# Add one article for distributed-systems
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "distributed-systems" kafka >/dev/null
out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" suggest)
assert_contains "suggest finds gap" "machine-learning" "$out"
assert_contains "suggest identifies gap type" "GAP" "$out"

# === social-package.md tests ===

echo "=== social-package.md ==="

assert_file_exists "social-package.md exists" "$SCRIPT_DIR/prompts/social-package.md"

# Verify key sections exist in prompt
prompt_content=$(cat "$SCRIPT_DIR/prompts/social-package.md")
assert_contains "prompt has twitter section" "Twitter" "$prompt_content"
assert_contains "prompt has linkedin section" "LinkedIn" "$prompt_content"
assert_contains "prompt has xiaohongshu section" "小红书" "$prompt_content"
assert_contains "prompt has HN section" "HN" "$prompt_content"
assert_contains "prompt has author positioning" "Author Positioning" "$prompt_content"
assert_contains "prompt has output format" "social-package.json" "$prompt_content"

# === orchestrate.sh build-social-prompt tests ===

echo "=== orchestrate.sh build-social-prompt ==="

export HOME="$TMPDIR/fakehome5"
mkdir -p "$HOME/.tech-essay-writer"

# Set up author profile
bash "$SCRIPT_DIR/scripts/author-profile.sh" init >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set name "Test Author" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social twitter "@testauthor" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" add-expertise "testing" expert >/dev/null

# Set up expertise graph
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "testing" unit-test integration >/dev/null

# Set up project with minimal state
PROJECT="$TMPDIR/test-social-project"
mkdir -p "$PROJECT/.essay-state"
echo '{"stage":"polish","topic":"testing best practices","language":"en"}' > "$PROJECT/.essay-state/pipeline-state.json"
echo "# Test Draft\n\nThis is a test draft about testing." > "$PROJECT/.essay-state/draft-v1.md"
echo '{"reviewer":"seo","rating":"GOOD","summary":"SEO looks fine"}' > "$PROJECT/.essay-state/review-seo.json"

# Test build-social-prompt
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-social-prompt)
assert_contains "social prompt has prompt template" "Social Media Package" "$out"
assert_contains "social prompt has draft" "Test Draft" "$out"
assert_contains "social prompt has author data" "Test Author" "$out"
assert_contains "social prompt has expertise graph" "testing" "$out"
assert_contains "social prompt has SEO data" "SEO looks fine" "$out"
assert_contains "social prompt has language directive" "Language Directive" "$out"
assert_contains "social prompt has instructions" "social-package.json" "$out"

# Test build-format-prompts includes author data
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts internal)
assert_contains "format prompt has author profile" "Author Profile" "$out"
assert_contains "format prompt has author name" "Test Author" "$out"

out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts external)
assert_contains "external format has author profile" "Author Profile" "$out"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
