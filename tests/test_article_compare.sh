#!/usr/bin/env bash
# Tests for article-compare.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPARE="$SCRIPT_DIR/scripts/article-compare.sh"
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
    echo "  actual: $(echo "$haystack" | head -5)"
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

assert_json_field() {
  local desc="$1" json="$2" field="$3" expected="$4"
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "PARSE_ERROR")
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  field: $field"
    echo "  expected: $expected"
    echo "  actual:   $actual"
  fi
}

assert_json_field_gt() {
  local desc="$1" json="$2" field="$3" threshold="$4"
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "0")
  result=$(python3 -c "print('yes' if float('$actual') > float('$threshold') else 'no')")
  if [ "$result" = "yes" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  field: $field = $actual, expected > $threshold"
  fi
}

assert_json_field_lt() {
  local desc="$1" json="$2" field="$3" threshold="$4"
  actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "999")
  result=$(python3 -c "print('yes' if float('$actual') < float('$threshold') else 'no')")
  if [ "$result" = "yes" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  field: $field = $actual, expected < $threshold"
  fi
}

# --- Create test fixtures ---

# Fixture: simple article v1
cat > "$TMPDIR/article-v1.md" << 'EOF'
# My Tech Article

## Introduction

This is a simple article about technology. It covers important topics that many engineers care about. The goal is to help readers understand how things work.

## Architecture

The system uses a client-server architecture. The server handles all the business logic. The client sends requests over HTTP. We chose this approach for simplicity.

## Performance

Performance is good under normal load. We measured response times averaging 50ms. The system handles about 1000 requests per second. Memory usage stays below 512MB.

## Conclusion

In conclusion, this architecture works well for our use case. We recommend it for small to medium teams. Future work includes adding caching.
EOF

# Fixture: improved article v2
cat > "$TMPDIR/article-v2.md" << 'EOF'
# My Tech Article

## Introduction

This is a comprehensive article about modern system architecture. It covers critical topics that engineers at all levels need to understand. The goal is to provide actionable guidance for building reliable systems.

## Architecture

The system uses a client-server architecture with an event-driven messaging layer. The server handles business logic through a command pattern. The client communicates via gRPC for low-latency operations. We chose this approach after evaluating three alternatives.

### Event Bus

The event bus decouples producers from consumers. It uses Apache Kafka for durability and ordering guarantees.

```python
class EventBus:
    def publish(self, event):
        self.kafka.send(event.topic, event.serialize())
```

## Performance

Performance is excellent under both normal and peak load conditions. We measured response times averaging 12ms at P50 and 45ms at P99. The system handles about 5000 requests per second with horizontal scaling. Memory usage stays below 256MB per instance.

### Benchmarks

We ran benchmarks using wrk with 100 concurrent connections. Results showed linear scaling up to 8 instances.

## Security

All communication uses mutual TLS. Authentication is handled via JWT tokens with short expiry. We follow the principle of least privilege for all service accounts.

## Conclusion

In conclusion, this architecture works well for our use case and has proven itself in production for six months. We recommend it for teams of any size with proper observability in place. Future work includes adding a caching layer with Redis and implementing circuit breakers.
EOF

# Fixture: completely different article
cat > "$TMPDIR/different.md" << 'EOF'
# Database Selection Guide

## Why Databases Matter

Choosing the right database is one of the most impactful architectural decisions. The wrong choice creates years of technical debt.

## SQL vs NoSQL

SQL databases offer ACID guarantees. NoSQL databases offer horizontal scalability. The choice depends on your consistency requirements.

## Recommendation

Use PostgreSQL unless you have specific requirements that demand otherwise.
EOF

# Fixture: empty article
cat > "$TMPDIR/empty.md" << 'EOF'
EOF

# Fixture: minimal article
cat > "$TMPDIR/minimal.md" << 'EOF'
# Title

One sentence article.
EOF

# Fixture: code-heavy article
cat > "$TMPDIR/code-heavy.md" << 'EOF'
# Code Examples

## Setup

Install dependencies first.

```bash
npm install express
npm install cors
```

## Server Code

Here is the server:

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/health', (req, res) => {
  res.json({ healthy: true });
});

app.listen(3000);
```

## Client Code

Here is the client:

```javascript
const response = await fetch('http://localhost:3000');
const data = await response.json();
console.log(data);
```

## Summary

That is all.
EOF

# Fixture: identical copy
cp "$TMPDIR/article-v1.md" "$TMPDIR/article-v1-copy.md"

# === Tests ===

echo "=== article-compare.sh usage and errors ==="

# Test 1: No arguments shows usage
out=$(bash "$COMPARE" 2>&1 || true)
assert_contains "no args shows usage" "Usage" "$out"

# Test 2: Missing file1 errors
rc=0
out=$(bash "$COMPARE" "$TMPDIR/nonexistent.md" "$TMPDIR/article-v1.md" 2>&1) || rc=$?
assert_exit_code "missing file1 exits with error" "1" "$rc"
assert_contains "missing file1 error message" "not found" "$out"

# Test 3: Missing file2 errors
rc=0
out=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/nonexistent.md" 2>&1) || rc=$?
assert_exit_code "missing file2 exits with error" "1" "$rc"
assert_contains "missing file2 error message" "not found" "$out"

echo "=== article-compare.sh basic comparison ==="

# Test 4: Basic comparison runs successfully
rc=0
out=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --no-color 2>&1) || rc=$?
assert_exit_code "basic comparison exits 0" "0" "$rc"

# Test 5: Output contains word count section
assert_contains "output has word count" "WORD COUNT" "$out"

# Test 6: Output contains structure section
assert_contains "output has structure" "STRUCTURE" "$out"

# Test 7: Output contains reading level section
assert_contains "output has reading level" "READING LEVEL" "$out"

# Test 8: Output contains summary section
assert_contains "output has summary" "SUMMARY" "$out"

# Test 9: Output shows file names
assert_contains "output shows file1 name" "article-v1.md" "$out"
assert_contains "output shows file2 name" "article-v2.md" "$out"

echo "=== article-compare.sh JSON output ==="

# Test 10: JSON output is valid JSON
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --json 2>&1)
valid=$(echo "$json" | python3 -c "import sys,json; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
assert_eq "JSON output is valid" "valid" "$valid"

# Test 11: JSON has required top-level fields
assert_json_field "JSON has file1" "$json" "['file1']" "article-v1.md"
assert_json_field "JSON has file2" "$json" "['file2']" "article-v2.md"

# Test 12: JSON has metrics for both files
assert_json_field_gt "JSON file1 word count > 0" "$json" "['metrics']['file1']['word_count']" "0"
assert_json_field_gt "JSON file2 word count > 0" "$json" "['metrics']['file2']['word_count']" "0"

# Test 13: v2 has more words than v1
v2_words=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['metrics']['file2']['word_count'])")
v1_words=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['metrics']['file1']['word_count'])")
result=$(python3 -c "print('yes' if int('$v2_words') > int('$v1_words') else 'no')")
assert_eq "v2 has more words than v1" "yes" "$result"

echo "=== article-compare.sh identical files ==="

# Test 14: Identical files show 100% similarity
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v1-copy.md" --json 2>&1)
assert_json_field "identical files 100% similar" "$json" "['overall_similarity']" "100.0"

# Test 15: Identical files have no improvements or regressions
improvements=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['improvements']))")
regressions=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['regressions']))")
assert_eq "identical files no improvements" "0" "$improvements"
assert_eq "identical files no regressions" "0" "$regressions"

echo "=== article-compare.sh structure detection ==="

# Test 16: Detects added sections (Security added in v2)
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --json 2>&1)
has_added=$(echo "$json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
added = [c for c in d['section_changes'] if c['type'] == 'added']
print('yes' if any('Security' in c['heading'] for c in added) else 'no')
")
assert_eq "detects added Security section" "yes" "$has_added"

# Test 17: Detects added subsections (Event Bus, Benchmarks)
has_subsections=$(echo "$json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
added = [c for c in d['section_changes'] if c['type'] == 'added']
headings = [c['heading'] for c in added]
print('yes' if 'Event Bus' in headings or 'Benchmarks' in headings else 'no')
")
assert_eq "detects added subsections" "yes" "$has_subsections"

# Test 18: v2 has more headings than v1
h1=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['headings']['file1']))")
h2=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['headings']['file2']))")
result=$(python3 -c "print('yes' if int('$h2') > int('$h1') else 'no')")
assert_eq "v2 has more headings" "yes" "$result"

echo "=== article-compare.sh reading level ==="

# Test 19: Both files have reading level metrics
assert_json_field_gt "file1 has FK grade" "$json" "['metrics']['file1']['flesch_kincaid_grade']" "0"
assert_json_field_gt "file2 has FK grade" "$json" "['metrics']['file2']['flesch_kincaid_grade']" "0"

# Test 20: Reading ease is within valid range (0-100ish)
assert_json_field_gt "file1 reading ease > 0" "$json" "['metrics']['file1']['flesch_reading_ease']" "0"
assert_json_field_lt "file1 reading ease < 100" "$json" "['metrics']['file1']['flesch_reading_ease']" "100"

echo "=== article-compare.sh completely different files ==="

# Test 21: Very different files have low similarity
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/different.md" --json 2>&1)
assert_json_field_lt "different files low similarity" "$json" "['overall_similarity']" "40"

# Test 22: Different files have section changes
changes=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['section_changes']))")
result=$(python3 -c "print('yes' if int('$changes') > 0 else 'no')")
assert_eq "different files have section changes" "yes" "$result"

echo "=== article-compare.sh edge cases ==="

# Test 23: Empty file vs non-empty
json=$(bash "$COMPARE" "$TMPDIR/empty.md" "$TMPDIR/article-v1.md" --json 2>&1)
valid=$(echo "$json" | python3 -c "import sys,json; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
assert_eq "empty vs non-empty produces valid JSON" "valid" "$valid"

# Test 24: Minimal file comparison works
json=$(bash "$COMPARE" "$TMPDIR/minimal.md" "$TMPDIR/article-v1.md" --json 2>&1)
valid=$(echo "$json" | python3 -c "import sys,json; json.load(sys.stdin); print('valid')" 2>/dev/null || echo "invalid")
assert_eq "minimal vs full produces valid JSON" "valid" "$valid"

# Test 25: Code-heavy file has high code density
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/code-heavy.md" --json 2>&1)
assert_json_field_gt "code-heavy file has high code density" "$json" "['metrics']['file2']['code_density']" "30"

# Test 26: Non-code file has low code density
assert_json_field_lt "article-v1 has low code density" "$json" "['metrics']['file1']['code_density']" "5"

echo "=== article-compare.sh improvements/regressions ==="

# Test 27: v1->v2 detects improvements (v2 has more content and sections)
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --json 2>&1)
improvement_count=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['improvements']))")
result=$(python3 -c "print('yes' if int('$improvement_count') > 0 else 'no')")
assert_eq "v1->v2 has improvements" "yes" "$result"

# Test 28: v2->v1 detects regressions (going backwards loses content)
json=$(bash "$COMPARE" "$TMPDIR/article-v2.md" "$TMPDIR/article-v1.md" --json 2>&1)
regression_count=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['regressions']))")
result=$(python3 -c "print('yes' if int('$regression_count') > 0 else 'no')")
assert_eq "v2->v1 has regressions" "yes" "$result"

echo "=== article-compare.sh section similarity ==="

# Test 29: Shared sections have similarity scores
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --json 2>&1)
has_similarity=$(echo "$json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
shared = [c for c in d['section_changes'] if 'similarity' in c]
print('yes' if len(shared) > 0 else 'no')
")
assert_eq "shared sections have similarity" "yes" "$has_similarity"

# Test 30: Introduction section was significantly edited
intro_type=$(echo "$json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
intro = [c for c in d['section_changes'] if c['heading'] == 'Introduction']
print(intro[0]['type'] if intro else 'missing')
")
# Intro was changed but kept the same heading
result=$(python3 -c "print('yes' if '$intro_type' in ('significant_edit', 'major_rewrite', 'minor_edit') else 'no')")
assert_eq "introduction section was edited" "yes" "$result"

echo "=== article-compare.sh --no-color flag ==="

# Test 31: --no-color output has no ANSI escape codes
out=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --no-color 2>&1)
has_ansi=$(echo "$out" | grep -c $'\033' || true)
assert_eq "no-color has no ANSI codes" "0" "$has_ansi"

echo "=== article-compare.sh paragraph and sentence metrics ==="

# Test 32: Sentence count is positive for real articles
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v2.md" --json 2>&1)
assert_json_field_gt "v1 has sentences" "$json" "['metrics']['file1']['sentence_count']" "3"
assert_json_field_gt "v2 has sentences" "$json" "['metrics']['file2']['sentence_count']" "3"

# Test 33: Paragraph count is positive
assert_json_field_gt "v1 has paragraphs" "$json" "['metrics']['file1']['paragraph_count']" "2"
assert_json_field_gt "v2 has paragraphs" "$json" "['metrics']['file2']['paragraph_count']" "2"

# Test 34: Code blocks detected in code-heavy file
json=$(bash "$COMPARE" "$TMPDIR/code-heavy.md" "$TMPDIR/article-v1.md" --json 2>&1)
assert_json_field_gt "code-heavy has code blocks" "$json" "['metrics']['file1']['code_block_count']" "2"

echo "=== article-compare.sh link detection ==="

# Fixture with links
cat > "$TMPDIR/with-links.md" << 'EOF'
# Article with Links

Read the [official docs](https://example.com/docs) for more info.
Also see [this guide](https://example.com/guide) and [the FAQ](https://example.com/faq).
EOF

# Test 35: Link count detection
json=$(bash "$COMPARE" "$TMPDIR/with-links.md" "$TMPDIR/article-v1.md" --json 2>&1)
assert_json_field "with-links has 3 links" "$json" "['metrics']['file1']['link_count']" "3"
assert_json_field "article-v1 has 0 links" "$json" "['metrics']['file2']['link_count']" "0"

echo "=== article-compare.sh self-comparison ==="

# Test 36: File compared to itself is 100% similar
json=$(bash "$COMPARE" "$TMPDIR/article-v1.md" "$TMPDIR/article-v1.md" --json 2>&1)
assert_json_field "self-comparison 100% similar" "$json" "['overall_similarity']" "100.0"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
