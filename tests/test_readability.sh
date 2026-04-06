#!/usr/bin/env bash
# Tests for readability-score.sh and word-frequency.sh
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

assert_json_key() {
  local desc="$1" json_str="$2" key_path="$3" expected="$4"
  local actual
  actual=$(echo "$json_str" | python3 -c "import json,sys; d=json.load(sys.stdin); print(eval('d' + sys.argv[1]))" "$key_path" 2>/dev/null || echo "PARSE_ERROR")
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

assert_json_gt() {
  local desc="$1" json_str="$2" key_path="$3" threshold="$4"
  local actual
  actual=$(echo "$json_str" | python3 -c "import json,sys; d=json.load(sys.stdin); print(eval('d' + sys.argv[1]))" "$key_path" 2>/dev/null || echo "0")
  if python3 -c "assert float('$actual') > float('$threshold')" 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected > $threshold, got: $actual"
  fi
}

assert_json_gte() {
  local desc="$1" json_str="$2" key_path="$3" threshold="$4"
  local actual
  actual=$(echo "$json_str" | python3 -c "import json,sys; d=json.load(sys.stdin); print(eval('d' + sys.argv[1]))" "$key_path" 2>/dev/null || echo "0")
  if python3 -c "assert float('$actual') >= float('$threshold')" 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected >= $threshold, got: $actual"
  fi
}

assert_json_lt() {
  local desc="$1" json_str="$2" key_path="$3" threshold="$4"
  local actual
  actual=$(echo "$json_str" | python3 -c "import json,sys; d=json.load(sys.stdin); print(eval('d' + sys.argv[1]))" "$key_path" 2>/dev/null || echo "999")
  if python3 -c "assert float('$actual') < float('$threshold')" 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  expected < $threshold, got: $actual"
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

# ============================================================
# Create test fixtures
# ============================================================

# Simple readable text
cat > "$TMPDIR/simple.md" << 'EOF'
# Simple Article

This is a simple test. It has short sentences. The words are easy to read. Dogs like to play. Cats like to sleep. Birds like to fly.

This is another paragraph. It is also simple. We write short sentences here.
EOF

# Complex academic text
cat > "$TMPDIR/complex.md" << 'EOF'
# Advanced Distributed Systems Architecture

The implementation of sophisticated distributed consensus algorithms necessitates a comprehensive understanding of the fundamental theoretical underpinnings that characterize Byzantine fault-tolerant systems, particularly when considering the implications of asynchronous network partitions on the availability guarantees prescribed by the CAP theorem and its subsequent refinements.

Furthermore, the reconciliation of eventually consistent replicated data structures with the stringent linearizability requirements demanded by financial transaction processing systems presents a multifaceted engineering challenge that requires careful consideration of the tradeoffs between consistency, availability, and partition tolerance.

The architectural decisions surrounding the selection of appropriate consensus protocols must account for the probabilistic guarantees offered by randomized algorithms versus the deterministic guarantees provided by classical Paxos-derived protocols.
EOF

# Text with passive voice
cat > "$TMPDIR/passive.md" << 'EOF'
# Project Update

The code was written by the team. The tests were run by the CI pipeline. The bugs were found by the QA engineers. The feature was deployed by the DevOps team. The documentation was updated by the technical writer.

The architecture was redesigned to improve performance. The database was migrated to a new cluster. The API was refactored for better usability.
EOF

# Text with AI patterns
cat > "$TMPDIR/ai-slop.md" << 'EOF'
# The Evolving Landscape

Let us delve into the comprehensive landscape of modern technology. We must leverage robust frameworks to streamline our development processes. It is essential to utilize cutting-edge tools that facilitate rapid innovation.

The ever-evolving tapestry of our digital ecosystem requires us to harness transformative paradigms. By leveraging comprehensive strategies, we can streamline operations and facilitate groundbreaking synergy across the organization.

We must delve deeper into these robust solutions. The landscape continues to shift as we leverage new comprehensive approaches to streamline and facilitate holistic transformation.
EOF

# Markdown with code blocks (should be stripped)
cat > "$TMPDIR/with-code.md" << 'EOF'
# Code Tutorial

Here is how to create a function. This is a simple example.

```python
def hello_world():
    print("Hello, world!")
    return True
```

The function above prints a greeting. It returns a boolean value. This is straightforward code.

```javascript
const add = (a, b) => a + b;
console.log(add(1, 2));
```

These examples show basic syntax. They are easy to understand.
EOF

# Empty prose (only code)
cat > "$TMPDIR/only-code.md" << 'EOF'
```python
x = 1
y = 2
```
EOF

# Text with overused word
cat > "$TMPDIR/overused.md" << 'EOF'
# Performance Analysis

Performance is critical for applications. Good performance means happy users. We measure performance with benchmarks. Performance testing reveals bottlenecks. Without performance optimization, applications suffer. Performance metrics guide our decisions. The performance team tracks performance daily. Performance improvements boost performance scores. Every performance review examines performance data. Performance goals drive performance culture.
EOF

# Minimal text
cat > "$TMPDIR/minimal.md" << 'EOF'
Hello world.
EOF

# Text with frontmatter
cat > "$TMPDIR/frontmatter.md" << 'EOF'
---
title: Test Article
author: Test
date: 2024-01-01
---

# Article Title

This is a simple article with frontmatter. The content should be analyzed without the metadata block.

A second paragraph adds more content. It has clear and direct sentences.
EOF

# Verbose test fixture
cat > "$TMPDIR/verbose-test.md" << 'EOF'
# Test

The cat sat on the mat. The dog ran in the park. Birds fly in the sky.
EOF

# Jargon-heavy text
cat > "$TMPDIR/jargon.md" << 'EOF'
# Architecture Decision

The containerization of our microservices enables greater scalability and interoperability across the organization. Our bespoke orchestration layer provides idempotent operations through non-blocking asynchronous processing.

The standardization and normalization of our API surface ensures orthogonal composability. This opinionated framework offers out-of-the-box turnkey solutions with zero boilerplate configuration.
EOF

# ============================================================
echo "=== readability-score.sh tests ==="
# ============================================================

# --- Test 1: No file argument shows error ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" 2>&1 || true)
assert_contains "T1: no file shows usage/error" "error" "$out"

# --- Test 2: Missing file returns error JSON ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/nonexistent.md" 2>&1 || true)
assert_contains "T2: missing file returns error" "file not found" "$out"

# --- Test 3: Simple text produces valid JSON ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md" 2>&1)
echo "$out" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null
assert_exit_code "T3: simple text produces valid JSON" "0" "$?"

# --- Test 4: Simple text has low grade level ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_lt "T4: simple text grade < 8" "$out" "['metrics']['flesch_kincaid_grade']" "8"

# --- Test 5: Complex text has high grade level ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/complex.md")
assert_json_gt "T5: complex text grade > 12" "$out" "['metrics']['flesch_kincaid_grade']" "12"

# --- Test 6: Word count is positive ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T6: word count > 0" "$out" "['metrics']['total_words']" "0"

# --- Test 7: Sentence count is positive ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T7: sentence count > 0" "$out" "['metrics']['total_sentences']" "0"

# --- Test 8: Paragraph count for simple text ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gte "T8: paragraph count >= 2" "$out" "['metrics']['total_paragraphs']" "2"

# --- Test 9: Complex sentences detected in complex text ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/complex.md")
assert_json_gt "T9: complex sentences > 0" "$out" "['complexity']['complex_sentence_count']" "0"

# --- Test 10: No complex sentences in simple text ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_key "T10: no complex sentences in simple text" "$out" "['complexity']['complex_sentence_count']" "0"

# --- Test 11: Passive voice detected ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/passive.md")
assert_json_gt "T11: passive voice count > 0" "$out" "['passive_voice']['passive_count']" "0"

# --- Test 12: Passive percentage is substantial for passive text ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/passive.md")
assert_json_gt "T12: passive % > 30 for passive text" "$out" "['passive_voice']['passive_percentage']" "30"

# --- Test 13: Code blocks are stripped from analysis ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/with-code.md")
assert_not_contains "T13: code blocks stripped (no 'def hello')" "def hello" "$out"

# --- Test 14: Flesch reading ease present ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_contains "T14: has flesch_reading_ease" "flesch_reading_ease" "$out"

# --- Test 15: Simple text has high reading ease ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T15: simple reading ease > 60" "$out" "['metrics']['flesch_reading_ease']" "60"

# --- Test 16: Grade interpretation present ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_contains "T16: grade_interpretation present" "grade_interpretation" "$out"

# --- Test 17: Verbose mode includes sentence_details ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/verbose-test.md" verbose)
assert_contains "T17: verbose has sentence_details" "sentence_details" "$out"

# --- Test 18: Verbose mode has per-sentence word_count ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/verbose-test.md" verbose)
assert_contains "T18: verbose has word_count per sentence" "word_count" "$out"

# --- Test 19: Non-verbose mode omits sentence_details ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/verbose-test.md")
assert_not_contains "T19: non-verbose omits sentence_details" "sentence_details" "$out"

# --- Test 20: File name present in output ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_contains "T20: file name in output" "simple.md" "$out"

# --- Test 21: Average syllables per word is reasonable ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T21: avg syllables > 1.0" "$out" "['metrics']['avg_syllables_per_word']" "0.9"
assert_json_lt "T21b: avg syllables < 3.0" "$out" "['metrics']['avg_syllables_per_word']" "3.0"

# --- Test 22: Frontmatter is stripped ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/frontmatter.md")
assert_not_contains "T22: frontmatter stripped (no 'date: 2024')" "date: 2024" "$out"

# --- Test 23: Total syllables present ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T23: total_syllables > 0" "$out" "['metrics']['total_syllables']" "0"

# ============================================================
echo ""
echo "=== word-frequency.sh tests ==="
# ============================================================

# --- Test 24: No file argument shows error ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" 2>&1 || true)
assert_contains "T24: no file shows usage/error" "error" "$out"

# --- Test 25: Missing file returns error JSON ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/nonexistent.md" 2>&1 || true)
assert_contains "T25: missing file error" "file not found" "$out"

# --- Test 26: Simple text produces valid JSON ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md" 2>&1)
echo "$out" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null
assert_exit_code "T26: valid JSON output" "0" "$?"

# --- Test 27: Top words list populated ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_json_gt "T27: has top words" "$out" "['top_words'].__len__()" "0"

# --- Test 28: Total words counted ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_json_gt "T28: total_words > 0" "$out" "['total_words']" "0"

# --- Test 29: AI patterns detected in AI-slop text ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/ai-slop.md")
assert_json_gt "T29: AI flags > 0" "$out" "['ai_patterns']['flagged_words'].__len__()" "0"

# --- Test 30: AI risk is high for slop text ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/ai-slop.md")
assert_json_key "T30: AI risk = high" "$out" "['ai_patterns']['risk_level']" "high"

# --- Test 31: No AI patterns in simple text ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_json_key "T31: no AI patterns in simple text" "$out" "['ai_patterns']['risk_level']" "none"

# --- Test 32: Overused words detected ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/overused.md")
assert_json_gt "T32: overused words found" "$out" "['overused_words'].__len__()" "0"

# --- Test 33: Overused word is 'performance' ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/overused.md")
top_word=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['overused_words'][0]['word'])" 2>/dev/null || echo "NONE")
assert_eq "T33: top overused word is 'performance'" "performance" "$top_word"

# --- Test 34: Code blocks excluded from word frequency ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/with-code.md")
# 'def' and 'console' from code blocks should not appear in top words
all_words=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(w['word'] for w in d['top_words']))" 2>/dev/null || echo "")
assert_not_contains "T34: code 'console' not in top words" "console" "$all_words"

# --- Test 35: Custom top_n respected ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md" 3)
count=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['top_words']))" 2>/dev/null || echo "0")
assert_eq "T35: top_n=3 returns <= 3 words" "1" "$(python3 -c "print(1 if int('$count') <= 3 else 0)")"

# --- Test 36: Jargon detected in jargon-heavy text ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/jargon.md")
assert_json_gt "T36: jargon count > 0" "$out" "['jargon']['count']" "0"

# --- Test 37: Jargon density percentage present ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/jargon.md")
assert_contains "T37: jargon density_percentage present" "density_percentage" "$out"

# --- Test 38: Type-token ratio present and reasonable ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_json_gt "T38: TTR > 0" "$out" "['type_token_ratio']" "0"
assert_json_lt "T38b: TTR <= 1" "$out" "['type_token_ratio']" "1.01"

# --- Test 39: File name in output ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_contains "T39: file name in output" "simple.md" "$out"

# --- Test 40: Content words < total words (stop words filtered) ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
total=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['total_words'])")
content=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['content_words'])")
if python3 -c "assert int('$content') < int('$total')" 2>/dev/null; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: T40: content_words < total_words"
  echo "  content=$content total=$total"
fi

# --- Test 41: Unique words count present ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
assert_json_gt "T41: unique_words > 0" "$out" "['unique_words']" "0"

# --- Test 42: Delve flagged as high severity ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/ai-slop.md")
delve_severity=$(echo "$out" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d['ai_patterns']['flagged_words']:
    if f['word']=='delve':
        print(f['severity'])
        break
" 2>/dev/null || echo "MISSING")
assert_eq "T42: delve is high severity" "high" "$delve_severity"

# --- Test 43: Frontmatter stripped from word frequency ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/frontmatter.md")
all_words=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(' '.join(w['word'] for w in d['top_words']))" 2>/dev/null || echo "")
assert_not_contains "T43: frontmatter key 'author' not in top words" "author" "$all_words"

# --- Test 44: Each top word has percentage field ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/simple.md")
has_pct=$(echo "$out" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('yes' if all('percentage' in w for w in d['top_words']) else 'no')
" 2>/dev/null || echo "no")
assert_eq "T44: all top words have percentage" "yes" "$has_pct"

# ============================================================
echo ""
echo "=== Integration / edge case tests ==="
# ============================================================

# --- Test 45: Minimal text does not crash readability ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/minimal.md" 2>&1 || true)
assert_contains "T45: minimal text has metrics" "metrics" "$out"

# --- Test 46: Minimal text does not crash word-frequency ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/minimal.md" 2>&1 || true)
assert_contains "T46: minimal text has total_words" "total_words" "$out"

# --- Test 47: Readability avg_sentence_length is reasonable ---
out=$(bash "$SCRIPT_DIR/scripts/readability-score.sh" "$TMPDIR/simple.md")
assert_json_gt "T47: avg_sentence_length > 2" "$out" "['metrics']['avg_sentence_length']" "2"
assert_json_lt "T47b: avg_sentence_length < 30" "$out" "['metrics']['avg_sentence_length']" "30"

# --- Test 48: Word frequency overused percentage > 2 ---
out=$(bash "$SCRIPT_DIR/scripts/word-frequency.sh" "$TMPDIR/overused.md")
pct=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['overused_words'][0]['percentage'])" 2>/dev/null || echo "0")
if python3 -c "assert float('$pct') > 2.0" 2>/dev/null; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: T48: overused word percentage > 2"
  echo "  got: $pct"
fi

# ============================================================
echo ""
echo "========================================"
echo "RESULTS: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
