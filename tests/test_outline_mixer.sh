#!/usr/bin/env bash
# Tests for outline-mixer.sh — cherry-pick sections from outline variants
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

assert_file_not_exists() {
  local desc="$1" path="$2"
  if [ -f "$path" ]; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — file should not exist: $path"
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
  local desc="$1" file="$2" field="$3" expected="$4"
  local actual
  actual=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2],''))" "$file" "$field" 2>/dev/null || echo "PARSE_ERROR")
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

assert_json_array_len() {
  local desc="$1" file="$2" field="$3" expected="$4"
  local actual
  actual=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get(sys.argv[2],[])))" "$file" "$field" 2>/dev/null || echo "PARSE_ERROR")
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc"
    echo "  field: $field"
    echo "  expected length: $expected"
    echo "  actual length:   $actual"
  fi
}

# ── Setup: create sample outline variants ──────────────────────────────────────

setup_project() {
  local proj="$1"
  mkdir -p "$proj/.essay-state"

  cat > "$proj/.essay-state/outline-A.json" << 'OUTLINE_A'
{
  "variant": "A",
  "variant_name": "Tutorial",
  "title": "Build a Multi-Agent System in 200 Lines",
  "hook": "A tutorial hook",
  "sections": [
    {"title": "The Problem with Monolithic Agents", "purpose": "Establish pain point", "key_points": ["Context overflow", "Tangled concerns"], "estimated_words": 300},
    {"title": "The Three-Layer Architecture", "purpose": "Core concept", "key_points": ["Conductor", "Sprint Master", "Worker"], "estimated_words": 500},
    {"title": "Building the Conductor", "purpose": "Implementation", "key_points": ["State management", "Sprint dispatch"], "estimated_words": 600},
    {"title": "Context Isolation in Practice", "purpose": "Key insight", "key_points": ["Fresh context per layer"], "estimated_words": 400},
    {"title": "Results and Lessons", "purpose": "Evidence", "key_points": ["Metrics", "Gotchas"], "estimated_words": 300}
  ],
  "target_word_count": 2100,
  "tone": "Practical, code-heavy"
}
OUTLINE_A

  cat > "$proj/.essay-state/outline-B.json" << 'OUTLINE_B'
{
  "variant": "B",
  "variant_name": "Deep Dive",
  "title": "Why Multi-Agent Architecture Beats Monolithic AI",
  "hook": "A deep dive hook",
  "sections": [
    {"title": "The Monolith Trap", "purpose": "Problem space", "key_points": ["Why single agents fail"], "estimated_words": 400},
    {"title": "Architectural Principles", "purpose": "Framework", "key_points": ["Separation of concerns"], "estimated_words": 600},
    {"title": "The Conductor Pattern", "purpose": "Core pattern", "key_points": ["Orchestration vs execution"], "estimated_words": 500},
    {"title": "Trade-offs and When Not To", "purpose": "Nuance", "key_points": ["Overhead", "Simple tasks"], "estimated_words": 400},
    {"title": "A Production Implementation", "purpose": "Evidence", "key_points": ["Real code", "Real metrics"], "estimated_words": 500}
  ],
  "target_word_count": 2400,
  "tone": "Authoritative, analytical"
}
OUTLINE_B

  cat > "$proj/.essay-state/outline-C.json" << 'OUTLINE_C'
{
  "variant": "C",
  "variant_name": "Narrative",
  "title": "The Day Our AI Agent Forgot Everything",
  "hook": "A narrative hook",
  "sections": [
    {"title": "The Incident", "purpose": "Hook/crisis", "key_points": ["What went wrong"], "estimated_words": 300},
    {"title": "The Investigation", "purpose": "Journey", "key_points": ["Context window as root cause"], "estimated_words": 400},
    {"title": "The Breakthrough", "purpose": "Insight", "key_points": ["Multi-agent as the solution"], "estimated_words": 500},
    {"title": "Building It", "purpose": "Implementation", "key_points": ["Architecture decisions"], "estimated_words": 500},
    {"title": "What We Learned", "purpose": "Takeaway", "key_points": ["Principles that generalize"], "estimated_words": 300}
  ],
  "target_word_count": 2000,
  "tone": "Personal, engaging"
}
OUTLINE_C
}

PROJ="$TMPDIR/test-proj"
setup_project "$PROJ"

MIXER="$SCRIPT_DIR/scripts/outline-mixer.sh"
MIXED="$PROJ/.essay-state/outline-mixed.json"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: List command shows all variants
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== outline-mixer.sh list ==="

out=$(bash "$MIXER" "$PROJ" list 2>&1)
assert_contains "list shows variant A" "Outline A" "$out"
assert_contains "list shows variant B" "Outline B" "$out"
assert_contains "list shows variant C" "Outline C" "$out"
assert_contains "list shows Tutorial name" "Tutorial" "$out"
assert_contains "list shows Deep Dive name" "Deep Dive" "$out"
assert_contains "list shows Narrative name" "Narrative" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: List shows section details
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== list shows section details ==="

assert_contains "list shows section titles" "The Problem with Monolithic Agents" "$out"
assert_contains "list shows section numbers" "1." "$out"
assert_contains "list shows purpose" "Purpose:" "$out"
assert_contains "list shows word estimates" "words" "$out"
assert_contains "list shows key points" "Key points:" "$out"
assert_contains "list shows total count" "Total variants available: 3" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Basic mix — take sections from each variant
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== basic mix A:1,2 B:3,4 C:5 ==="

out=$(bash "$MIXER" "$PROJ" "A:1,2 B:3,4 C:5" 2>&1)
assert_contains "mix succeeds" "Mixed outline assembled successfully" "$out"
assert_file_exists "mixed outline created" "$MIXED"
assert_json_array_len "mixed has 5 sections" "$MIXED" "sections" "5"
assert_json_field "mixed variant is 'mixed'" "$MIXED" "variant" "mixed"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Mixed outline has correct sections in order
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== verify section order ==="

section_titles=$(python3 -c "
import json
d = json.load(open('$MIXED'))
for s in d['sections']:
    print(s['title'])
")
assert_contains "first section from A" "The Problem with Monolithic Agents" "$section_titles"
assert_contains "second section from A" "The Three-Layer Architecture" "$section_titles"
assert_contains "third section from B" "The Conductor Pattern" "$section_titles"
assert_contains "fourth section from B" "Trade-offs and When Not To" "$section_titles"
assert_contains "fifth section from C" "What We Learned" "$section_titles"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Source map is correct
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== source map ==="

assert_json_array_len "source_map has 5 entries" "$MIXED" "source_map" "5"

source_map=$(python3 -c "
import json
d = json.load(open('$MIXED'))
for sm in d['source_map']:
    print(f\"{sm['variant']}:{sm['original_section']}\")
")
assert_contains "source map entry 1" "A:1" "$source_map"
assert_contains "source map entry 2" "A:2" "$source_map"
assert_contains "source map entry 3" "B:3" "$source_map"
assert_contains "source map entry 4" "B:4" "$source_map"
assert_contains "source map entry 5" "C:5" "$source_map"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Word count sums correctly
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== word count ==="

# A:1=300, A:2=500, B:3=500, B:4=400, C:5=300 => 2000
assert_json_field "total words = 2000" "$MIXED" "target_word_count" "2000"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Mix spec is recorded
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== mix spec recorded ==="

assert_json_field "mix_spec recorded" "$MIXED" "mix_spec" "A:1,2 B:3,4 C:5"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Summary output shows mapping
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== summary output ==="

out=$(bash "$MIXER" "$PROJ" "A:1 B:2 C:3" 2>&1)
assert_contains "summary shows section mapping" "[A:1]" "$out"
assert_contains "summary shows B mapping" "[B:2]" "$out"
assert_contains "summary shows C mapping" "[C:3]" "$out"
assert_contains "summary shows section count" "Sections: 3" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Single variant — all sections from A
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== single variant all from A ==="

out=$(bash "$MIXER" "$PROJ" "A:1,2,3,4,5" 2>&1)
assert_contains "single variant mix succeeds" "Mixed outline assembled successfully" "$out"
assert_json_array_len "single variant has 5 sections" "$MIXED" "sections" "5"
# A total: 300+500+600+400+300 = 2100
assert_json_field "single variant word count" "$MIXED" "target_word_count" "2100"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: Single section only
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== single section ==="

out=$(bash "$MIXER" "$PROJ" "C:3" 2>&1)
assert_contains "single section succeeds" "Mixed outline assembled successfully" "$out"
assert_json_array_len "single section has 1 section" "$MIXED" "sections" "1"
title=$(python3 -c "import json; print(json.load(open('$MIXED'))['sections'][0]['title'])")
assert_eq "single section is The Breakthrough" "The Breakthrough" "$title"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Error — invalid variant letter
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: invalid variant ==="

out=$(bash "$MIXER" "$PROJ" "D:1,2" 2>&1) || true
assert_contains "invalid variant error" "Invalid spec token" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: Error — section out of range
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: section out of range ==="

out=$(bash "$MIXER" "$PROJ" "A:6" 2>&1) || true
assert_contains "out of range error" "out of range" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: Error — section 0 (1-based)
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: section 0 ==="

out=$(bash "$MIXER" "$PROJ" "A:0" 2>&1) || true
assert_contains "section 0 error" "out of range" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 14: Error — negative section number
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: negative section ==="

out=$(bash "$MIXER" "$PROJ" "A:-1" 2>&1) || true
assert_contains "negative section error" "ERROR" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 15: Error — non-numeric section
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: non-numeric section ==="

out=$(bash "$MIXER" "$PROJ" "A:foo" 2>&1) || true
assert_contains "non-numeric section error" "Invalid section number" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 16: Error — missing outline variant
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: missing variant file ==="

PROJ2="$TMPDIR/test-proj2"
mkdir -p "$PROJ2/.essay-state"
cat > "$PROJ2/.essay-state/outline-A.json" << 'EOF'
{"variant": "A", "variant_name": "Test", "title": "Test", "sections": [{"title": "S1", "purpose": "p", "key_points": [], "estimated_words": 100}]}
EOF

out=$(bash "$MIXER" "$PROJ2" "B:1" 2>&1) || true
assert_contains "missing variant error" "not found" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 17: Error — no outlines at all
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: no outlines ==="

PROJ3="$TMPDIR/test-proj3"
mkdir -p "$PROJ3/.essay-state"

out=$(bash "$MIXER" "$PROJ3" "A:1" 2>&1) || true
assert_contains "no outlines error" "No outline variants found" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 18: Error — no state directory
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: no state dir ==="

PROJ4="$TMPDIR/test-proj4"
mkdir -p "$PROJ4"

out=$(bash "$MIXER" "$PROJ4" "A:1" 2>&1) || true
assert_contains "no state dir error" "State directory not found" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 19: Error — empty spec
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: empty spec ==="

out=$(bash "$MIXER" "$PROJ" "" 2>&1) || true
assert_contains "empty spec triggers usage or error" "Usage\|ERROR\|sections_spec" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 20: Error — duplicate section reference
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== error: duplicate section ==="

out=$(bash "$MIXER" "$PROJ" "A:1 A:1" 2>&1) || true
assert_contains "duplicate section error" "Duplicate section reference" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 21: Lowercase variant letter accepted
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== lowercase variant ==="

out=$(bash "$MIXER" "$PROJ" "a:1 b:2 c:3" 2>&1)
assert_contains "lowercase variant succeeds" "Mixed outline assembled successfully" "$out"
assert_json_array_len "lowercase mix has 3 sections" "$MIXED" "sections" "3"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 22: List with only one variant
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== list with one variant ==="

out=$(bash "$MIXER" "$PROJ2" list 2>&1)
assert_contains "list shows available variant" "Outline A" "$out"
assert_not_contains "list does not show missing B" "Outline B" "$out"
assert_contains "list count with partial" "Total variants available: 1" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 23: List with no variants shows error
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== list with no variants ==="

out=$(bash "$MIXER" "$PROJ3" list 2>&1) || true
assert_contains "list no variants error" "No outline variants found" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 24: Mix preserves key_points in sections
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== preserves section data ==="

bash "$MIXER" "$PROJ" "A:1 B:2" > /dev/null 2>&1
kp=$(python3 -c "
import json
d = json.load(open('$MIXED'))
print(json.dumps(d['sections'][0]['key_points']))
")
assert_contains "key_points preserved" "Context overflow" "$kp"
assert_contains "key_points preserved 2" "Tangled concerns" "$kp"

purpose=$(python3 -c "
import json
d = json.load(open('$MIXED'))
print(d['sections'][1]['purpose'])
")
assert_eq "purpose preserved" "Framework" "$purpose"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 25: Mix with non-contiguous sections
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== non-contiguous sections ==="

out=$(bash "$MIXER" "$PROJ" "A:1,5 B:2,4" 2>&1)
assert_contains "non-contiguous succeeds" "Mixed outline assembled successfully" "$out"
assert_json_array_len "non-contiguous has 4 sections" "$MIXED" "sections" "4"

titles=$(python3 -c "
import json
d = json.load(open('$MIXED'))
for s in d['sections']:
    print(s['title'])
")
assert_contains "first is A:1" "The Problem with Monolithic Agents" "$titles"
assert_contains "second is A:5" "Results and Lessons" "$titles"
assert_contains "third is B:2" "Architectural Principles" "$titles"
assert_contains "fourth is B:4" "Trade-offs and When Not To" "$titles"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 26: Help flag shows usage
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== help flag ==="

out=$(bash "$MIXER" "$PROJ" --help 2>&1)
assert_contains "help shows usage" "Usage:" "$out"
assert_contains "help shows examples" "VARIANT:SECTIONS" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 27: Orchestrate.sh integration — build-outline-mix list
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== orchestrate integration: list ==="

out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-outline-mix list 2>&1)
assert_contains "orchestrate list works" "Outline A" "$out"
assert_contains "orchestrate list shows variants" "Total variants available" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 28: Orchestrate.sh integration — build-outline-mix with spec
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== orchestrate integration: mix ==="

rm -f "$MIXED"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-outline-mix "A:1 B:2 C:3" 2>&1)
assert_contains "orchestrate mix works" "Mixed outline assembled successfully" "$out"
assert_file_exists "orchestrate creates mixed file" "$MIXED"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 29: Overwrite previous mixed outline
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== overwrite previous mix ==="

bash "$MIXER" "$PROJ" "A:1,2,3" > /dev/null 2>&1
assert_json_array_len "first mix has 3 sections" "$MIXED" "sections" "3"

bash "$MIXER" "$PROJ" "B:1,2" > /dev/null 2>&1
assert_json_array_len "second mix overwrites to 2 sections" "$MIXED" "sections" "2"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 30: Mixed outline has placeholder fields
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== placeholder fields ==="

bash "$MIXER" "$PROJ" "A:1 C:5" > /dev/null 2>&1
assert_json_field "variant_name is cherry-picked" "$MIXED" "variant_name" "Mixed (cherry-picked)"
title=$(python3 -c "import json; print(json.load(open('$MIXED'))['title'])")
assert_contains "title is placeholder" "mixed" "$title"
hook=$(python3 -c "import json; print(json.load(open('$MIXED'))['hook'])")
assert_contains "hook is placeholder" "mixed" "$hook"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 31: No arguments shows usage
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== no arguments ==="

out=$(bash "$MIXER" 2>&1) || true
assert_contains "no args shows usage" "Usage:" "$out"

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "========================================"
echo "outline-mixer: $((PASS + FAIL)) tests | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
