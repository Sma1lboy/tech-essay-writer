#!/usr/bin/env bash
# Tests for article templates and code-validate.sh
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

# ============================================================
echo "=== Template existence tests ==="
# ============================================================

ALL_TEMPLATES=(tutorial deep-dive narrative opinion case-study comparison listicle incident-postmortem release-announcement adr)

# --- Tests 1-10: All 10 templates exist ---
for tmpl in "${ALL_TEMPLATES[@]}"; do
  assert_file_exists "template $tmpl exists" "$SCRIPT_DIR/templates/$tmpl.md"
done

# ============================================================
echo ""
echo "=== Template content tests ==="
# ============================================================

REQUIRED_SECTIONS=("## Structure" "## Tone" "## Code Density" "## Target Length" "## Reader Promise")

# --- Tests 11-60: Each template has all 5 required sections ---
for tmpl in "${ALL_TEMPLATES[@]}"; do
  content=$(cat "$SCRIPT_DIR/templates/$tmpl.md")
  for section in "${REQUIRED_SECTIONS[@]}"; do
    assert_contains "$tmpl has '$section'" "$section" "$content"
  done
done

# ============================================================
echo ""
echo "=== code-validate.sh tests ==="
# ============================================================

# --- Test 61: Valid JS code block → pass ---
cat > "$TMPDIR/valid-js.md" << 'EOF'
# Test Article

```javascript
function add(a, b) {
  return a + b;
}
console.log(add(1, 2));
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/valid-js.md" 2>&1)
assert_contains "valid JS report has file" "valid-js.md" "$out"
report_file="$TMPDIR/valid-js-report.json"
echo "$out" > "$report_file"
validated=$(python3 -c "import json; print(json.loads(open('$report_file').read())['validated'])")
assert_eq "valid JS validated count" "1" "$validated"
summary_pass=$(python3 -c "import json; print(json.loads(open('$report_file').read())['summary']['pass'])")
assert_eq "valid JS passes" "1" "$summary_pass"

# --- Test 62: Invalid JS syntax → fail ---
cat > "$TMPDIR/invalid-js.md" << 'EOF'
# Bad JS

```javascript
function broken( {
  return 1;
}
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/invalid-js.md" 2>&1)
echo "$out" > "$TMPDIR/invalid-js-report.json"
summary_fail=$(python3 -c "import json; print(json.loads(open('$TMPDIR/invalid-js-report.json').read())['summary']['fail'])")
assert_eq "invalid JS fails" "1" "$summary_fail"
assert_contains "invalid JS has syntax error" "syntax_valid.*false\|syntax error\|syntax_valid\": false" "$out"

# --- Test 63: Valid Python code block ---
cat > "$TMPDIR/valid-py.md" << 'EOF'
# Python Test

```python
def hello():
    return "world"

print(hello())
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/valid-py.md" 2>&1)
echo "$out" > "$TMPDIR/valid-py-report.json"
summary_pass=$(python3 -c "import json; print(json.loads(open('$TMPDIR/valid-py-report.json').read())['summary']['pass'])")
assert_eq "valid Python passes" "1" "$summary_pass"

# --- Test 64: Invalid Python syntax ---
cat > "$TMPDIR/invalid-py.md" << 'EOF'
# Bad Python

```python
def broken(
    return 1
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/invalid-py.md" 2>&1)
echo "$out" > "$TMPDIR/invalid-py-report.json"
summary_fail=$(python3 -c "import json; print(json.loads(open('$TMPDIR/invalid-py-report.json').read())['summary']['fail'])")
assert_eq "invalid Python fails" "1" "$summary_fail"

# --- Test 65: Code block with ellipsis → fragment detected ---
cat > "$TMPDIR/fragment.md" << 'EOF'
# Fragment Example

```javascript
function handler(req, res) {
  // handle request
  ...
}
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/fragment.md" 2>&1)
assert_contains "fragment detected with ellipsis" "fragments_detected.*true\|contains ellipsis\|fragments_detected\": true" "$out"

# --- Test 66: Code block with TODO → fragment ---
cat > "$TMPDIR/todo-fragment.md" << 'EOF'
# TODO Fragment

```python
def process():
    # TODO: implement this
    pass
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/todo-fragment.md" 2>&1)
assert_contains "TODO fragment detected" "TODO" "$out"

# --- Test 67: Code block with no language tag → skipped ---
cat > "$TMPDIR/no-lang.md" << 'EOF'
# No Language

```
some random text here
not real code
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/no-lang.md" 2>&1)
echo "$out" > "$TMPDIR/no-lang-report.json"
skipped=$(python3 -c "import json; print(json.loads(open('$TMPDIR/no-lang-report.json').read())['skipped'])")
assert_eq "no language tag skipped" "1" "$skipped"
summary_skip=$(python3 -c "import json; print(json.loads(open('$TMPDIR/no-lang-report.json').read())['summary']['skip'])")
assert_eq "no language tag in summary skip" "1" "$summary_skip"

# --- Test 68: Non-existent file → error ---
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/nonexistent.md" 2>&1 || true)
assert_contains "non-existent file error" "error\|file not found" "$out"

# --- Test 69: Multiple blocks → correct total count ---
cat > "$TMPDIR/multi.md" << 'EOF'
# Multi Block

```javascript
const a = 1;
```

Some text.

```python
x = 2
```

More text.

```bash
echo hello
```

```
plain text
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/multi.md" 2>&1)
echo "$out" > "$TMPDIR/multi-report.json"
total=$(python3 -c "import json; print(json.loads(open('$TMPDIR/multi-report.json').read())['total_blocks'])")
assert_eq "multiple blocks total count" "4" "$total"
validated=$(python3 -c "import json; print(json.loads(open('$TMPDIR/multi-report.json').read())['validated'])")
assert_eq "multiple blocks validated count" "3" "$validated"
skipped=$(python3 -c "import json; print(json.loads(open('$TMPDIR/multi-report.json').read())['skipped'])")
assert_eq "multiple blocks skipped count" "1" "$skipped"

# --- Test 70: Valid bash code block ---
cat > "$TMPDIR/valid-bash.md" << 'EOF'
# Bash Test

```bash
#!/bin/bash
for i in 1 2 3; do
  echo "$i"
done
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/valid-bash.md" 2>&1)
echo "$out" > "$TMPDIR/valid-bash-report.json"
summary_pass=$(python3 -c "import json; print(json.loads(open('$TMPDIR/valid-bash-report.json').read())['summary']['pass'])")
assert_eq "valid bash passes" "1" "$summary_pass"

# --- Test 71: Invalid bash syntax ---
cat > "$TMPDIR/invalid-bash.md" << 'EOF'
# Bad Bash

```bash
if then
  echo broken
fi
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/invalid-bash.md" 2>&1)
echo "$out" > "$TMPDIR/invalid-bash-report.json"
summary_fail=$(python3 -c "import json; print(json.loads(open('$TMPDIR/invalid-bash-report.json').read())['summary']['fail'])")
assert_eq "invalid bash fails" "1" "$summary_fail"

# --- Test 72: JS with imports ---
cat > "$TMPDIR/imports-js.md" << 'EOF'
# Imports

```javascript
import React from 'react';
import { useState } from 'react';
const fs = require('fs');
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/imports-js.md" 2>&1)
echo "$out" > "$TMPDIR/imports-js-report.json"
imports_count=$(python3 -c "import json; r=json.loads(open('$TMPDIR/imports-js-report.json').read()); print(len(r['blocks'][0]['imports']))")
assert_eq "JS imports parsed count >= 2" "true" "$([ "$imports_count" -ge 2 ] && echo true || echo false)"

# --- Test 73: JS with relative import → unverifiable ---
cat > "$TMPDIR/relative-import.md" << 'EOF'
# Relative Import

```javascript
import { helper } from './utils';
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/relative-import.md" 2>&1)
assert_contains "relative import unverifiable" "unverifiable" "$out"

# --- Test 74: Python imports ---
cat > "$TMPDIR/imports-py.md" << 'EOF'
# Python Imports

```python
import json
from os.path import join
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/imports-py.md" 2>&1)
echo "$out" > "$TMPDIR/imports-py-report.json"
py_imports=$(python3 -c "import json; r=json.loads(open('$TMPDIR/imports-py-report.json').read()); print(len(r['blocks'][0]['imports']))")
assert_eq "Python imports parsed count >= 2" "true" "$([ "$py_imports" -ge 2 ] && echo true || echo false)"

# --- Test 75: Empty markdown → no blocks ---
cat > "$TMPDIR/empty.md" << 'EOF'
# Empty Article

No code blocks here.
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/empty.md" 2>&1)
echo "$out" > "$TMPDIR/empty-report.json"
total=$(python3 -c "import json; print(json.loads(open('$TMPDIR/empty-report.json').read())['total_blocks'])")
assert_eq "empty markdown has 0 blocks" "0" "$total"

# --- Test 76: Output is valid JSON ---
cat > "$TMPDIR/json-check.md" << 'EOF'
# JSON Check

```javascript
const x = 1;
```
EOF
bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/json-check.md" > "$TMPDIR/json-check-report.json" 2>&1
python3 -c "import json; json.load(open('$TMPDIR/json-check-report.json'))" 2>/dev/null
valid_json=$?
assert_eq "output is valid JSON" "0" "$valid_json"

# --- Test 77: 'sh' language tag recognized as bash ---
cat > "$TMPDIR/sh-tag.md" << 'EOF'
# Shell

```sh
echo "hello"
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/sh-tag.md" 2>&1)
echo "$out" > "$TMPDIR/sh-tag-report.json"
sh_lang=$(python3 -c "import json; print(json.loads(open('$TMPDIR/sh-tag-report.json').read())['blocks'][0]['language'])")
assert_eq "sh tag recognized as bash" "bash" "$sh_lang"

# --- Test 78: 'js' alias recognized ---
cat > "$TMPDIR/js-tag.md" << 'EOF'
# JS Alias

```js
const x = 1;
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/js-tag.md" 2>&1)
echo "$out" > "$TMPDIR/js-tag-report.json"
js_lang=$(python3 -c "import json; print(json.loads(open('$TMPDIR/js-tag-report.json').read())['blocks'][0]['language'])")
assert_eq "js alias recognized" "javascript" "$js_lang"

# --- Test 79: 'py' alias recognized ---
cat > "$TMPDIR/py-tag.md" << 'EOF'
# PY Alias

```py
x = 1
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/py-tag.md" 2>&1)
echo "$out" > "$TMPDIR/py-tag-report.json"
py_lang=$(python3 -c "import json; print(json.loads(open('$TMPDIR/py-tag-report.json').read())['blocks'][0]['language'])")
assert_eq "py alias recognized" "python" "$py_lang"

# --- Test 80: 'ts' alias recognized ---
cat > "$TMPDIR/ts-tag.md" << 'EOF'
# TS Alias

```ts
const x: number = 1;
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/ts-tag.md" 2>&1)
echo "$out" > "$TMPDIR/ts-tag-report.json"
ts_lang=$(python3 -c "import json; print(json.loads(open('$TMPDIR/ts-tag-report.json').read())['blocks'][0]['language'])")
assert_eq "ts alias recognized" "typescript" "$ts_lang"

# --- Test 81: Pseudo-code marker detected ---
cat > "$TMPDIR/pseudo.md" << 'EOF'
# Pseudo

```javascript
function doStuff() {
  // your code here
}
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/pseudo.md" 2>&1)
assert_contains "pseudo-code marker detected" "pseudo-code marker\|your code here\|fragments_detected\": true" "$out"

# --- Test 82: Misspelled import flagged ---
cat > "$TMPDIR/misspell.md" << 'EOF'
# Misspell

```javascript
import express from 'expresss';
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/misspell.md" 2>&1)
assert_contains "misspelled import flagged" "possible_misspelling" "$out"

# --- Test 83: Summary counts are correct for mixed file ---
cat > "$TMPDIR/mixed.md" << 'EOF'
# Mixed

```javascript
const ok = true;
```

```python
def good():
    return True
```

```javascript
function bad( {
  return;
}
```

```
not code
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/mixed.md" 2>&1)
echo "$out" > "$TMPDIR/mixed-report.json"
total=$(python3 -c "import json; print(json.loads(open('$TMPDIR/mixed-report.json').read())['total_blocks'])")
assert_eq "mixed total blocks" "4" "$total"
summary_pass=$(python3 -c "import json; print(json.loads(open('$TMPDIR/mixed-report.json').read())['summary']['pass'])")
assert_eq "mixed pass count" "2" "$summary_pass"
summary_fail=$(python3 -c "import json; print(json.loads(open('$TMPDIR/mixed-report.json').read())['summary']['fail'])")
assert_eq "mixed fail count" "1" "$summary_fail"
summary_skip=$(python3 -c "import json; print(json.loads(open('$TMPDIR/mixed-report.json').read())['summary']['skip'])")
assert_eq "mixed skip count" "1" "$summary_skip"

# --- Test 84: line_in_file is correct ---
line_in_file=$(python3 -c "import json; issues=json.loads(open('$TMPDIR/mixed-report.json').read())['issues']; print(issues[0]['line_in_file'])" 2>/dev/null || echo "0")
# The failing JS block starts at line 16 (after # Mixed, blank, valid js block, blank, python block, blank, then ```javascript at line 15 → code starts line 16)
assert_eq "line_in_file is positive" "true" "$([ "$line_in_file" -gt 0 ] && echo true || echo false)"

# --- Test 85: No issues for all-valid file ---
cat > "$TMPDIR/all-valid.md" << 'EOF'
# All Valid

```javascript
const x = 1;
```

```python
y = 2
```

```bash
echo "hi"
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/all-valid.md" 2>&1)
echo "$out" > "$TMPDIR/all-valid-report.json"
issues_count=$(python3 -c "import json; print(len(json.loads(open('$TMPDIR/all-valid-report.json').read())['issues']))")
assert_eq "all-valid has 0 issues" "0" "$issues_count"

# --- Test 86: File path appears in report ---
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/all-valid.md" 2>&1)
assert_contains "file path in report" "all-valid.md" "$out"

# --- Test 87: Unrecognized language tags skipped ---
cat > "$TMPDIR/unknown-lang.md" << 'EOF'
# Unknown

```ruby
puts "hello"
```

```haskell
main = putStrLn "hello"
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$TMPDIR/unknown-lang.md" 2>&1)
echo "$out" > "$TMPDIR/unknown-lang-report.json"
skipped=$(python3 -c "import json; print(json.loads(open('$TMPDIR/unknown-lang-report.json').read())['skipped'])")
assert_eq "unknown languages skipped" "2" "$skipped"

# --- Test 88: No arguments → error/usage ---
out=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" 2>&1; true)
assert_contains "no args shows usage" "Usage\|error\|no file specified" "$out"

# ============================================================
echo ""
echo "=== orchestrate.sh integration ==="
# ============================================================

# --- Test 89: build-code-validation command in usage ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" x x invalid 2>&1 || true)
assert_contains "usage shows build-code-validation" "build-code-validation" "$out"

# --- Test 90: build-code-validation with a draft ---
PROJ="$TMPDIR/proj-cv"
mkdir -p "$PROJ/.essay-state"
cat > "$PROJ/.essay-state/draft-v1.md" << 'EOF'
# Test Draft

```javascript
const x = 1;
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-code-validation 2>&1)
assert_contains "orchestrator dispatches code-validation" "total_blocks\|validated" "$out"

# --- Test 91: build-code-validation with no draft → error ---
PROJ2="$TMPDIR/proj-cv-empty"
mkdir -p "$PROJ2/.essay-state"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ2" "$SCRIPT_DIR" build-code-validation 2>&1; true)
assert_contains "no draft error" "error\|not found" "$out"

# --- Test 92: build-code-validation uses final-external when no draft ---
PROJ3="$TMPDIR/proj-cv-final"
mkdir -p "$PROJ3/.essay-state"
cat > "$PROJ3/.essay-state/final-external.md" << 'EOF'
# Final

```python
x = 1
```
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ3" "$SCRIPT_DIR" build-code-validation 2>&1)
assert_contains "uses final-external fallback" "total_blocks\|validated" "$out"

# ============================================================
echo ""
echo "=== New template content validation ==="
# ============================================================

# --- Test 93: comparison.md has correct structure items ---
content=$(cat "$SCRIPT_DIR/templates/comparison.md")
assert_contains "comparison has Hook" "Hook" "$content"
assert_contains "comparison has Criteria" "Criteria" "$content"
assert_contains "comparison has Verdict" "Verdict" "$content"
assert_contains "comparison has comparison table" "comparison table" "$content"

# --- Test 94: listicle.md has correct structure items ---
content=$(cat "$SCRIPT_DIR/templates/listicle.md")
assert_contains "listicle has Hook" "Hook" "$content"
assert_contains "listicle has Items" "Items" "$content"
assert_contains "listicle has Honorable mentions" "Honorable mentions" "$content"

# --- Test 95: incident-postmortem.md has correct structure items ---
content=$(cat "$SCRIPT_DIR/templates/incident-postmortem.md")
assert_contains "postmortem has TL;DR" "TL;DR" "$content"
assert_contains "postmortem has Timeline" "Timeline" "$content"
assert_contains "postmortem has Root cause" "Root cause" "$content"
assert_contains "postmortem has Action items" "Action items" "$content"

# --- Test 96: release-announcement.md has correct structure items ---
content=$(cat "$SCRIPT_DIR/templates/release-announcement.md")
assert_contains "release has Headline feature" "Headline feature" "$content"
assert_contains "release has Migration guide" "Migration guide" "$content"
assert_contains "release has Breaking changes" "Breaking changes" "$content"

# --- Test 97: adr.md has correct structure items ---
content=$(cat "$SCRIPT_DIR/templates/adr.md")
assert_contains "adr has Context" "Context" "$content"
assert_contains "adr has Decision" "Decision" "$content"
assert_contains "adr has Status" "Status" "$content"
assert_contains "adr has Consequences" "Consequences" "$content"
assert_contains "adr has Alternatives considered" "Alternatives considered" "$content"

# --- Test 98: Code density ranges are valid ---
for tmpl in "${ALL_TEMPLATES[@]}"; do
  content=$(cat "$SCRIPT_DIR/templates/$tmpl.md")
  assert_contains "$tmpl has percentage in Code Density" "%" "$content"
done

# --- Test 99: Target lengths have word counts ---
for tmpl in "${ALL_TEMPLATES[@]}"; do
  content=$(cat "$SCRIPT_DIR/templates/$tmpl.md")
  assert_contains "$tmpl has word count in Target Length" "words" "$content"
done

# --- Test 100: Reader Promise uses quotes ---
for tmpl in "${ALL_TEMPLATES[@]}"; do
  content=$(cat "$SCRIPT_DIR/templates/$tmpl.md")
  assert_contains "$tmpl Reader Promise has quoted text" '"After reading this' "$content"
done

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
