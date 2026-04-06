#!/usr/bin/env bash
# Tests for taste-memory.sh — diff-learn, feedback, and suggest commands
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
    echo "FAIL: $desc -- file not found: $path"
  fi
}

assert_json_key() {
  local desc="$1" key="$2" file="$3"
  local val
  val=$(python3 -c "import json; d=json.load(open('$file')); print('yes' if '$key' in d else 'no')")
  if [ "$val" = "yes" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc -- key '$key' not found in $file"
  fi
}

# Use temp home to avoid polluting real taste memory
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

TM="$SCRIPT_DIR/scripts/taste-memory.sh"
PROJECT="$TMPDIR/test-project"
mkdir -p "$PROJECT"

TASTE_FILE="$HOME/.tech-essay-writer/taste-memory.json"

# ============================================================
echo "=== diff-learn tests ==="
# ============================================================

# Create test files for diff-learn
ORIG="$TMPDIR/original.md"
EDITED="$TMPDIR/edited.md"

# --- Test 1: basic diff-learn produces output ---
cat > "$ORIG" <<'EOF'
# Introduction

This is a basic article about testing.

## Section One

Some content here about testing stuff.
EOF

cat > "$EDITED" <<'EOF'
# Introduction

This is a comprehensive guide to software testing methodologies.

## Section One

Furthermore, testing ensures software quality and reliability.

## Section Two

Additional content about integration testing.
EOF

out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
assert_contains "diff-learn returns learned output" "Learned from diff" "$out"

# --- Test 2: diff-learn creates taste-memory.json ---
assert_file_exists "taste memory file created after diff-learn" "$TASTE_FILE"

# --- Test 3: learned_patterns key exists ---
assert_json_key "learned_patterns key exists" "learned_patterns" "$TASTE_FILE"

# --- Test 4: pattern has project field ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['project'])")
assert_eq "diff-learn stores project dir" "$PROJECT" "$val"

# --- Test 5: pattern has timestamp ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print('yes' if 'timestamp' in d['learned_patterns'][-1] else 'no')")
assert_eq "diff-learn stores timestamp" "yes" "$val"

# --- Test 6: detects section additions ---
assert_contains "diff-learn detects added sections" "section" "$out"

# --- Test 7: detects insights ---
assert_contains "diff-learn produces insights" "Insights" "$out"

# --- Test 8: diff-learn with missing original file ---
if bash "$TM" diff-learn "$PROJECT" "$TMPDIR/nonexistent.md" "$EDITED" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject missing original file"
else
  PASS=$((PASS + 1))
fi

# --- Test 9: diff-learn with missing edited file ---
if bash "$TM" diff-learn "$PROJECT" "$ORIG" "$TMPDIR/nonexistent.md" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject missing edited file"
else
  PASS=$((PASS + 1))
fi

# --- Test 10: diff-learn detects expansion ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['length_change'])")
assert_eq "diff-learn detects expansion" "expanded" "$val"

# --- Test 11: diff-learn records length_ratio ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); r=d['learned_patterns'][-1]['length_ratio']; print('yes' if r > 1.0 else 'no')")
assert_eq "diff-learn length_ratio > 1 for expanded" "yes" "$val"

# --- Test 12: diff-learn detects condensation ---
# Reset taste memory
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# A Very Long Article

This article contains a lot of unnecessary filler content that should be removed. It goes on and on about things that are not really relevant to the main point. Furthermore, it has many paragraphs that repeat the same ideas over and over again without adding new information.

## Section One

The first section has way too much text. It explains things in excruciating detail when a simple sentence would suffice. The reader would benefit from a more concise presentation.

## Section Two

The second section also suffers from verbosity. Every concept is explained three different ways when once would be enough.

## Section Three

Yet another section full of redundant content.
EOF

cat > "$EDITED" <<'EOF'
# A Concise Article

Essential content only.

## Key Points

Brief, focused explanation.
EOF

out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['length_change'])")
assert_eq "diff-learn detects condensation" "condensed" "$val"

# --- Test 13: diff-learn detects concise preference from condensation ---
assert_contains "diff-learn detects concise preference" "concise" "$out"

# --- Test 14: diff-learn with identical files ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# Same Content
Identical text.
EOF
cp "$ORIG" "$EDITED"
out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['length_change'])")
assert_eq "identical files show similar length" "similar" "$val"

# --- Test 15: diff-learn detects structure reordering ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# Title

## Alpha Section

Content A.

## Beta Section

Content B.

## Gamma Section

Content C.
EOF

cat > "$EDITED" <<'EOF'
# Title

## Gamma Section

Content C.

## Alpha Section

Content A.

## Beta Section

Content B.
EOF

out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); sc=d['learned_patterns'][-1].get('structure_changes',[]); types=[c['type'] for c in sc]; print('yes' if 'sections_reordered' in types else 'no')")
assert_eq "diff-learn detects section reordering" "yes" "$val"

# --- Test 16: diff-learn detects formal tone shift ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
This is basically just a really cool thing that's actually pretty awesome. You basically just do stuff and things happen.
EOF

cat > "$EDITED" <<'EOF'
This consequently represents a significant advancement. Furthermore, the methodology provides substantial benefits. Moreover, the approach yields considerable improvements. Additionally, the framework demonstrates robust capabilities. Nevertheless, further research is warranted.
EOF

out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['tone_shift'])")
assert_eq "diff-learn detects formal tone shift" "more_formal" "$val"

# --- Test 17: diff-learn records word replacements ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
Use the simple method to build the thing.
EOF
cat > "$EDITED" <<'EOF'
Use the comprehensive approach to construct the application.
EOF

out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); wr=d['learned_patterns'][-1].get('word_replacements',[]); print(len(wr))")
assert_contains "diff-learn records word replacements" "word_replacements" "$(cat "$TASTE_FILE")"

# --- Test 18: diff-learn records diff_stats ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print('yes' if 'diff_stats' in d['learned_patterns'][-1] else 'no')")
assert_eq "diff-learn records diff_stats" "yes" "$val"

# --- Test 19: diff-learn caps learned_patterns at 50 ---
echo '{}' > "$TASTE_FILE"
for i in $(seq 1 55); do
  cat > "$ORIG" <<EOF
# Article $i
Content version $i original.
EOF
  cat > "$EDITED" <<EOF
# Article $i
Content version $i edited with changes.
EOF
  bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
done
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(len(d['learned_patterns']))")
assert_eq "learned_patterns capped at 50" "50" "$val"

# --- Test 20: diff-learn records paragraph_delta ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# Title

One paragraph.
EOF
cat > "$EDITED" <<'EOF'
# Title

Paragraph one.

Paragraph two.

Paragraph three.
EOF

bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['paragraph_delta'])")
# edited has more paragraphs, so delta should be positive
result=$(python3 -c "print('yes' if int('$val') > 0 else 'no')")
assert_eq "diff-learn records positive paragraph_delta" "yes" "$result"

# ============================================================
echo "=== feedback tests ==="
# ============================================================

# Reset for feedback tests
echo '{}' > "$TASTE_FILE"

# --- Test 21: feedback stores tone ---
out=$(bash "$TM" feedback "$PROJECT" tone "prefer casual conversational tone" 2>&1)
assert_contains "feedback returns confirmation" "Feedback recorded" "$out"
assert_contains "feedback shows category" "tone" "$out"

# --- Test 22: feedback stores in explicit_preferences ---
assert_json_key "explicit_preferences key exists" "explicit_preferences" "$TASTE_FILE"

# --- Test 23: feedback has correct category ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['explicit_preferences'][-1]['category'])")
assert_eq "feedback stores correct category" "tone" "$val"

# --- Test 24: feedback has correct text ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['explicit_preferences'][-1]['feedback'])")
assert_eq "feedback stores correct text" "prefer casual conversational tone" "$val"

# --- Test 25: feedback stores project dir ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['explicit_preferences'][-1]['project'])")
assert_eq "feedback stores project dir" "$PROJECT" "$val"

# --- Test 26: feedback stores timestamp ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print('yes' if 'timestamp' in d['explicit_preferences'][-1] else 'no')")
assert_eq "feedback stores timestamp" "yes" "$val"

# --- Test 27: feedback accepts structure category ---
out=$(bash "$TM" feedback "$PROJECT" structure "use numbered lists for steps" 2>&1)
assert_contains "feedback accepts structure" "Feedback recorded" "$out"

# --- Test 28: feedback accepts vocabulary category ---
out=$(bash "$TM" feedback "$PROJECT" vocabulary "avoid jargon" 2>&1)
assert_contains "feedback accepts vocabulary" "Feedback recorded" "$out"

# --- Test 29: feedback accepts length category ---
out=$(bash "$TM" feedback "$PROJECT" length "keep articles under 2000 words" 2>&1)
assert_contains "feedback accepts length" "Feedback recorded" "$out"

# --- Test 30: feedback accepts code_density category ---
out=$(bash "$TM" feedback "$PROJECT" code_density "more code examples please" 2>&1)
assert_contains "feedback accepts code_density" "Feedback recorded" "$out"

# --- Test 31: feedback accepts format category ---
out=$(bash "$TM" feedback "$PROJECT" format "use callout boxes for tips" 2>&1)
assert_contains "feedback accepts format" "Feedback recorded" "$out"

# --- Test 32: feedback rejects invalid category ---
if bash "$TM" feedback "$PROJECT" invalid_cat "some text" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid category"
else
  PASS=$((PASS + 1))
fi

# --- Test 33: feedback rejects empty category ---
if bash "$TM" feedback "$PROJECT" "" "some text" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject empty category"
else
  PASS=$((PASS + 1))
fi

# --- Test 34: multiple feedback entries accumulate ---
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(len(d['explicit_preferences']))")
assert_eq "multiple feedback entries accumulated" "6" "$val"

# --- Test 35: feedback caps at 100 ---
echo '{}' > "$TASTE_FILE"
for i in $(seq 1 105); do
  bash "$TM" feedback "$PROJECT" tone "preference number $i" >/dev/null 2>&1
done
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(len(d['explicit_preferences']))")
assert_eq "explicit_preferences capped at 100" "100" "$val"

# ============================================================
echo "=== suggest tests ==="
# ============================================================

# --- Test 36: suggest with no data ---
echo '{}' > "$TASTE_FILE"
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest with no data shows message" "No taste data" "$out"

# --- Test 37: suggest with only feedback shows preferences ---
echo '{}' > "$TASTE_FILE"
bash "$TM" feedback "$PROJECT" tone "be more informal" >/dev/null 2>&1
bash "$TM" feedback "$PROJECT" structure "lead with the conclusion" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows tone feedback" "informal" "$out"
assert_contains "suggest shows structure feedback" "conclusion" "$out"

# --- Test 38: suggest shows header ---
assert_contains "suggest shows header" "Personalized Writing Suggestions" "$out"

# --- Test 39: suggest with diff-learn data shows tone shift ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
This is basically just a really cool thing. Stuff happens when you do things.
EOF
cat > "$EDITED" <<'EOF'
This consequently represents a significant advancement. Furthermore, the methodology demonstrates considerable promise. Moreover, the results are noteworthy.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows tone shift info" "formal" "$out"

# --- Test 40: suggest with condensation pattern shows action item ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
This is a very long and unnecessarily verbose piece of text that goes on and on about nothing in particular. It contains many redundant words and phrases that add no value. The reader would benefit greatly from a more concise and focused presentation of these ideas.
EOF
cat > "$EDITED" <<'EOF'
Concise text. Focused.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows condensation action" "condense\|concise\|cut" "$out"

# --- Test 41: suggest with expansion pattern shows action item ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
Brief.
EOF
cat > "$EDITED" <<'EOF'
This is a much more detailed and comprehensive explanation of the topic at hand. It includes additional context, examples, and supporting evidence to help the reader understand the nuances better.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows expansion action" "expand\|detail\|example" "$out"

# --- Test 42: suggest shows Action Items section when patterns present ---
assert_contains "suggest shows action items section" "Action Items" "$out"

# --- Test 43: suggest shows structure patterns from diff-learn ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# Title

## Only Section

Content.
EOF
cat > "$EDITED" <<'EOF'
# Title

## First Section

Content.

## Second Section

More content.

## Third Section

Even more.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows structure patterns" "Structure patterns\|sections added" "$out"

# --- Test 44: suggest shows word replacements ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
Use the simple method to build the thing.
EOF
cat > "$EDITED" <<'EOF'
Use the comprehensive approach to construct the application.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows common replacements" "replacements\|Recurring" "$out"

# --- Test 45: suggest shows code density feedback ---
echo '{}' > "$TASTE_FILE"
bash "$TM" feedback "$PROJECT" code_density "always include runnable examples" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows code density feedback" "runnable examples" "$out"

# --- Test 46: suggest shows vocabulary feedback ---
echo '{}' > "$TASTE_FILE"
bash "$TM" feedback "$PROJECT" vocabulary "use simple words, no acronyms" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows vocabulary feedback" "simple words" "$out"

# --- Test 47: suggest shows format feedback ---
echo '{}' > "$TASTE_FILE"
bash "$TM" feedback "$PROJECT" format "always use tables for comparisons" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows format feedback" "tables" "$out"

# --- Test 48: suggest shows length feedback ---
echo '{}' > "$TASTE_FILE"
bash "$TM" feedback "$PROJECT" length "max 1500 words" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows length feedback" "1500" "$out"

# --- Test 49: suggest combines learned patterns and explicit preferences ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
This is basically just a test.
EOF
cat > "$EDITED" <<'EOF'
This consequently represents a thorough examination. Furthermore, the analysis is comprehensive. Moreover, the findings are significant.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
bash "$TM" feedback "$PROJECT" tone "always be authoritative" >/dev/null 2>&1
bash "$TM" feedback "$PROJECT" structure "put TL;DR first" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest combines diff-learn and feedback - tone" "authoritative" "$out"
assert_contains "suggest combines diff-learn and feedback - structure" "TL;DR" "$out"

# --- Test 50: suggest with record-choice structural prefs ---
echo '{}' > "$TASTE_FILE"
bash "$TM" record-choice code_density "high" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows structural prefs from record-choice" "code_density" "$out"

# --- Test 51: suggest shows recurring insights ---
echo '{}' > "$TASTE_FILE"
for i in 1 2 3; do
  cat > "$ORIG" <<EOF
# Article $i

This is basically just some really cool stuff.
EOF
  cat > "$EDITED" <<EOF
# Article $i

Comprehensive analysis of the subject matter.

## Additional Section $i

More details here.
EOF
  bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
done
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows recurring insights" "Recurring insights" "$out"

# ============================================================
echo "=== read integration tests ==="
# ============================================================

# --- Test 52: read shows learned patterns ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
Original text.
EOF
cat > "$EDITED" <<'EOF'
Edited text with changes.
EOF
bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" >/dev/null 2>&1
out=$(bash "$TM" read 2>&1)
assert_contains "read shows learned patterns" "Learned patterns" "$out"

# --- Test 53: read shows explicit preferences ---
bash "$TM" feedback "$PROJECT" tone "conversational" >/dev/null 2>&1
out=$(bash "$TM" read 2>&1)
assert_contains "read shows explicit preferences" "Explicit preferences" "$out"

# --- Test 54: read shows project in learned patterns ---
assert_contains "read shows project info" "project:" "$out"

# ============================================================
echo "=== edge case tests ==="
# ============================================================

# --- Test 55: diff-learn with empty original ---
echo '{}' > "$TASTE_FILE"
echo -n "" > "$ORIG"
cat > "$EDITED" <<'EOF'
# New Content
Brand new article.
EOF
out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
assert_contains "diff-learn handles empty original" "Learned from diff" "$out"

# --- Test 56: diff-learn with empty edited ---
echo '{}' > "$TASTE_FILE"
cat > "$ORIG" <<'EOF'
# Content
Some content.
EOF
echo -n "" > "$EDITED"
out=$(bash "$TM" diff-learn "$PROJECT" "$ORIG" "$EDITED" 2>&1)
assert_contains "diff-learn handles empty edited" "Learned from diff" "$out"
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['learned_patterns'][-1]['length_change'])")
assert_eq "empty edited detected as condensed" "condensed" "$val"

# --- Test 57: feedback with long text ---
long_text="This is a very long feedback message that contains more than a hundred characters and should still be stored correctly without truncation or corruption in the taste memory JSON file."
out=$(bash "$TM" feedback "$PROJECT" tone "$long_text" 2>&1)
assert_contains "feedback handles long text" "Feedback recorded" "$out"
val=$(python3 -c "import json; d=json.load(open('$TASTE_FILE')); print(d['explicit_preferences'][-1]['feedback'])")
assert_eq "long feedback text preserved" "$long_text" "$val"

# --- Test 58: feedback with special characters ---
echo '{}' > "$TASTE_FILE"
out=$(bash "$TM" feedback "$PROJECT" tone "use em-dashes -- not hyphens" 2>&1)
assert_contains "feedback handles special characters" "Feedback recorded" "$out"

# --- Test 59: suggest with only record-choice tone ---
echo '{}' > "$TASTE_FILE"
bash "$TM" record-choice tone "technical" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows record-choice tone" "technical" "$out"

# --- Test 60: suggest with legacy feedback_patterns ---
echo '{}' > "$TASTE_FILE"
bash "$TM" record-choice feedback "legacy pattern" >/dev/null 2>&1
out=$(bash "$TM" suggest "$PROJECT" 2>&1)
assert_contains "suggest shows legacy feedback" "legacy pattern" "$out"

# ============================================================
echo ""
echo "========================================"
echo "taste-memory tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
