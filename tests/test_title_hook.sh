#!/usr/bin/env bash
# Tests for title-generator.sh and hook-workshop.sh
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
echo "=== title-generator.sh ==="
# ============================================================

# --- Test 1: Runs with empty state dir ---
PROJ=$(setup_project "title-empty")
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 2>&1)
assert_contains "title-generator runs with empty state" '"titles"' "$out"
assert_file_exists "title-variations.json created (empty)" "$PROJ/.essay-state/title-variations.json"

# --- Test 2: Output is valid JSON ---
python3 -c "import json,sys; json.loads(sys.argv[1])" "$out" 2>/dev/null
assert_eq "output is valid JSON" "0" "$?"

# --- Test 3: Default generates 10 titles ---
PROJ=$(setup_project "title-default-count")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"GraphQL API Design","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "default count is 10" "10" "$count"

# --- Test 4: Custom count ---
PROJ=$(setup_project "title-custom-count")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Docker Optimization","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 5 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "custom count of 5" "5" "$count"

# --- Test 5: Titles are ranked by composite score ---
PROJ=$(setup_project "title-ranking")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Rust Memory Safety","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Rust Memory Safety","unique_angle":"Zero-cost abstractions","gap":"No practical guide","pain_points":["Borrow checker confusion"],"key_findings":["Lifetimes simplify after practice"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
ranking_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
titles = d['titles']
scores = [t['scores']['composite'] for t in titles]
print('true' if scores == sorted(scores, reverse=True) else 'false')
" "$out")
assert_eq "titles sorted by composite desc" "true" "$ranking_ok"

# --- Test 6: Each title has all score dimensions ---
dims_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
required = {'clarity','curiosity_gap','specificity','shareability','composite'}
for t in d['titles']:
    if set(t['scores'].keys()) != required:
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all score dimensions present" "true" "$dims_ok"

# --- Test 7: All scores are 1-10 ---
scores_valid=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for t in d['titles']:
    for k, v in t['scores'].items():
        if v < 1 or v > 10:
            print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all scores between 1-10" "true" "$scores_valid"

# --- Test 8: Each title has a rank ---
ranks_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
ranks = [t['rank'] for t in d['titles']]
expected = list(range(1, len(ranks)+1))
print('true' if ranks == expected else 'false')
" "$out")
assert_eq "sequential ranks 1..N" "true" "$ranks_ok"

# --- Test 9: Topic appears in output metadata ---
PROJ=$(setup_project "title-topic-meta")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"WebAssembly","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 3 2>&1)
topic_out=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['topic'])" "$out")
assert_eq "topic in metadata" "WebAssembly" "$topic_out"

# --- Test 10: Formula names are recorded ---
PROJ=$(setup_project "title-formulas")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"CI/CD Pipelines","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
has_formulas=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
formulas = set(t['formula'] for t in d['titles'])
print('true' if len(formulas) >= 5 else 'false')
" "$out")
assert_eq "at least 5 distinct formulas used" "true" "$has_formulas"

# --- Test 11: Research synthesis is used ---
PROJ=$(setup_project "title-research")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Event Sourcing","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Event Sourcing","conventional_wisdom":"CRUD is fine for everything","approach":"Event-driven architecture","result":"simplified complex domain logic","pain_points":["State management complexity"],"key_findings":["Event logs enable time travel debugging"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
inputs_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['research_synthesis'])" "$out")
assert_eq "research_synthesis marked as used" "True" "$inputs_used"

# --- Test 12: Materials file is tracked ---
PROJ=$(setup_project "title-materials")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Testing","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/materials.json" << 'EOF'
{"items":[{"title":"TDD Guide","source":"https://example.com"}]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 3 2>&1)
mat_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['materials'])" "$out")
assert_eq "materials marked as used" "True" "$mat_used"

# --- Test 13: Titles contain topic when available ---
PROJ=$(setup_project "title-topic-in-title")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"PostgreSQL Performance","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
topic_in_any=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = any('PostgreSQL' in t['title'] for t in d['titles'])
print('true' if found else 'false')
" "$out")
assert_eq "topic appears in at least one title" "true" "$topic_in_any"

# --- Test 14: Corrupt research file handled gracefully ---
PROJ=$(setup_project "title-corrupt")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Corrupt Test","stage":"research","language":"en"}
EOF
echo "NOT JSON AT ALL" > "$PROJ/.essay-state/research-synthesis.json"
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 3 2>&1)
assert_contains "handles corrupt research" '"titles"' "$out"

# --- Test 15: Atomic write (no tmp files left) ---
PROJ=$(setup_project "title-atomic")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Atomic Test","stage":"research","language":"en"}
EOF
bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 3 >/dev/null 2>&1
tmp_count=$(find "$PROJ/.essay-state" -name "*.tmp.*" | wc -l | tr -d ' ')
assert_eq "no tmp files left" "0" "$tmp_count"

# --- Test 16: Count of 1 works ---
PROJ=$(setup_project "title-one")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Minimal","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 1 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "count of 1 works" "1" "$count"

# --- Test 17: Large count (15) generates variants ---
PROJ=$(setup_project "title-large")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Large Count","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 15 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "count of 15 works" "15" "$count"
has_variant=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = any('variant' in t['formula'] for t in d['titles'])
print('true' if found else 'false')
" "$out")
assert_eq "variant formulas used for count > 10" "true" "$has_variant"

# --- Test 18: Formulas available count ---
PROJ=$(setup_project "title-formulas-count")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Formulas","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
fa=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['formulas_available'])" "$out")
assert_eq "10 formulas available" "10" "$fa"

# ============================================================
echo ""
echo "=== hook-workshop.sh ==="
# ============================================================

# --- Test 19: Runs with empty state dir ---
PROJ=$(setup_project "hook-empty")
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
assert_contains "hook-workshop runs with empty state" '"hooks"' "$out"
assert_file_exists "hook-variations.json created (empty)" "$PROJ/.essay-state/hook-variations.json"

# --- Test 20: Default generates all 5 styles ---
PROJ=$(setup_project "hook-all")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Microservices","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "default generates 5 hooks" "5" "$count"

# --- Test 21: All 5 styles present ---
styles=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
styles = sorted(h['style'] for h in d['hooks'])
print(' '.join(styles))
" "$out")
assert_eq "all 5 styles present" "bold contrast data question story" "$styles"

# --- Test 22: Single style filter works (story) ---
PROJ=$(setup_project "hook-story-only")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Observability","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" story 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
style=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['style'])" "$out")
assert_eq "single style count is 1" "1" "$count"
assert_eq "single style is story" "story" "$style"

# --- Test 23: Single style filter works (data) ---
PROJ=$(setup_project "hook-data-only")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"ML Ops","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" data 2>&1)
style=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['style'])" "$out")
assert_eq "single style is data" "data" "$style"

# --- Test 24: Single style filter works (question) ---
PROJ=$(setup_project "hook-question-only")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"API Design","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" question 2>&1)
style=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['style'])" "$out")
assert_eq "single style is question" "question" "$style"

# --- Test 25: Single style filter works (contrast) ---
PROJ=$(setup_project "hook-contrast-only")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"DevOps","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" contrast 2>&1)
style=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['style'])" "$out")
assert_eq "single style is contrast" "contrast" "$style"

# --- Test 26: Single style filter works (bold) ---
PROJ=$(setup_project "hook-bold-only")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Monolith Architecture","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" bold 2>&1)
style=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['style'])" "$out")
assert_eq "single style is bold" "bold" "$style"

# --- Test 27: Invalid style returns error ---
PROJ=$(setup_project "hook-invalid")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" invalid_style 2>&1 || true)
assert_contains "invalid style returns error" '"error"' "$out"

# --- Test 28: Hooks have all score dimensions ---
PROJ=$(setup_project "hook-scores")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Terraform","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
dims_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
required = {'engagement','relevance','authenticity','composite'}
for h in d['hooks']:
    if set(h['scores'].keys()) != required:
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all hook score dimensions present" "true" "$dims_ok"

# --- Test 29: All hook scores are 1-10 ---
scores_valid=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    for k, v in h['scores'].items():
        if v < 1 or v > 10:
            print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all hook scores between 1-10" "true" "$scores_valid"

# --- Test 30: Hooks are ranked by composite ---
ranking_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
scores = [h['scores']['composite'] for h in d['hooks']]
print('true' if scores == sorted(scores, reverse=True) else 'false')
" "$out")
assert_eq "hooks sorted by composite desc" "true" "$ranking_ok"

# --- Test 31: Hooks have word count ---
wc_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if 'word_count' not in h or h['word_count'] < 1:
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all hooks have word_count > 0" "true" "$wc_ok"

# --- Test 32: Research data enriches hooks ---
PROJ=$(setup_project "hook-research")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Kubernetes Autoscaling","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Kubernetes Autoscaling","unique_angle":"Event-driven scaling","gap":"No guide covers event-driven autoscaling","conventional_wisdom":"HPA is sufficient for most workloads","approach":"Event-driven autoscaling with KEDA","result":"reduced infrastructure costs by 40%","pain_points":["Manual scaling is error-prone"],"statistics":["67% of teams over-provision by 3x"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
# Data hook should use the statistic
data_hook=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if h['style'] == 'data':
        print(h['hook']); break
" "$out")
assert_contains "data hook uses statistic" "67%" "$data_hook"

# Bold hook should use conventional wisdom
bold_hook=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if h['style'] == 'bold':
        print(h['hook']); break
" "$out")
assert_contains "bold hook uses conventional wisdom" "HPA" "$bold_hook"

# --- Test 33: Story hook mentions topic ---
story_hook=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if h['style'] == 'story':
        print(h['hook']); break
" "$out")
assert_contains "story hook mentions topic" "Kubernetes Autoscaling" "$story_hook"

# --- Test 34: Question hook with conventional wisdom ---
question_hook=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if h['style'] == 'question':
        print(h['hook']); break
" "$out")
assert_contains "question hook references conventional wisdom" "HPA" "$question_hook"

# --- Test 35: Corrupt research handled ---
PROJ=$(setup_project "hook-corrupt")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Corrupt Hook","stage":"research","language":"en"}
EOF
echo "BROKEN JSON {{{{ " > "$PROJ/.essay-state/research-synthesis.json"
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
assert_contains "handles corrupt research" '"hooks"' "$out"

# --- Test 36: Atomic write for hooks ---
PROJ=$(setup_project "hook-atomic")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Atomic Hook","stage":"research","language":"en"}
EOF
bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" >/dev/null 2>&1
tmp_count=$(find "$PROJ/.essay-state" -name "*.tmp.*" | wc -l | tr -d ' ')
assert_eq "no hook tmp files left" "0" "$tmp_count"

# --- Test 37: requested_style recorded in output ---
PROJ=$(setup_project "hook-style-meta")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Meta Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" bold 2>&1)
rs=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['requested_style'])" "$out")
assert_eq "requested_style recorded" "bold" "$rs"

# --- Test 38: inputs_used tracking ---
PROJ=$(setup_project "hook-inputs")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Inputs Test","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Inputs Test"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
rs_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['research_synthesis'])" "$out")
ps_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['pipeline_state'])" "$out")
assert_eq "research marked as used" "True" "$rs_used"
assert_eq "pipeline_state marked as used" "True" "$ps_used"

# --- Test 39: Hook descriptions present ---
PROJ=$(setup_project "hook-descs")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Descriptions","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
descs_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for h in d['hooks']:
    if not h.get('description'):
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all hooks have descriptions" "true" "$descs_ok"

# ============================================================
echo ""
echo "=== orchestrate.sh integration ==="
# ============================================================

# --- Test 40: build-title-variations dispatches ---
PROJ=$(setup_project "orch-title")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Orchestrator Title Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-title-variations 3 2>&1)
assert_contains "orchestrator dispatches titles" '"titles"' "$out"
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "orchestrator passes count arg" "3" "$count"

# --- Test 41: build-hook-variations dispatches ---
PROJ=$(setup_project "orch-hook")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Orchestrator Hook Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-hook-variations story 2>&1)
assert_contains "orchestrator dispatches hooks" '"hooks"' "$out"
hook_count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "orchestrator passes style arg" "1" "$hook_count"

# --- Test 42: build-hook-variations default is all ---
PROJ=$(setup_project "orch-hook-default")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Default Hook","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-hook-variations 2>&1)
hook_count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "orchestrator default hook count is 5" "5" "$hook_count"

# --- Test 43: Usage shows new commands ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" x x invalid 2>&1 || true)
assert_contains "usage shows build-title-variations" "build-title-variations" "$out"
assert_contains "usage shows build-hook-variations" "build-hook-variations" "$out"

# --- Test 44: Title generator deterministic ---
PROJ=$(setup_project "title-deterministic")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Determinism Test","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Determinism Test","unique_angle":"Consistent output","gap":"Reproducibility"}
EOF
out1=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 5 2>&1)
out2=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 5 2>&1)
titles1=$(python3 -c "import json,sys; print([t['title'] for t in json.loads(sys.argv[1])['titles']])" "$out1")
titles2=$(python3 -c "import json,sys; print([t['title'] for t in json.loads(sys.argv[1])['titles']])" "$out2")
assert_eq "title generation is deterministic" "$titles1" "$titles2"

# --- Test 45: Contrast hook uses gap when available ---
PROJ=$(setup_project "hook-contrast-gap")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Gap Testing","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Gap Testing","gap":"Nobody covers performance profiling at scale"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" contrast 2>&1)
contrast_hook=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['hook'])" "$out")
assert_contains "contrast hook uses gap" "missed" "$contrast_hook"

# --- Test 46: Story hook uses approach when available ---
PROJ=$(setup_project "hook-story-approach")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Approach Test","stage":"research","language":"en"}
EOF
cat > "$PROJ/.essay-state/research-synthesis.json" << 'EOF'
{"topic":"Approach Test","approach":"progressive delivery with feature flags","pain_points":["Deployments cause downtime"]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" story 2>&1)
story_text=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['hook'])" "$out")
assert_contains "story hook uses approach" "progressive delivery" "$story_text"

# --- Test 47: Hooks without any research still produce output ---
PROJ=$(setup_project "hook-no-research")
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "hooks without research produce 5" "5" "$count"

# --- Test 48: Titles without any state files still produce output ---
PROJ=$(setup_project "title-no-state")
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 3 2>&1)
count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['count'])" "$out")
assert_eq "titles without state produce 3" "3" "$count"

# --- Test 49: Title scores vary across formulas ---
PROJ=$(setup_project "title-score-variation")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Score Variance","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/title-generator.sh" "$PROJ" 10 2>&1)
score_variety=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
composites = set(t['scores']['composite'] for t in d['titles'])
print('true' if len(composites) > 1 else 'false')
" "$out")
assert_eq "scores vary across titles" "true" "$score_variety"

# --- Test 50: Hook engagement score for story > 0 ---
PROJ=$(setup_project "hook-eng-story")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Engagement Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/hook-workshop.sh" "$PROJ" story 2>&1)
eng=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['hooks'][0]['scores']['engagement'])" "$out")
assert_eq "story engagement score > 0" "true" "$(python3 -c "print('true' if float('$eng') > 0 else 'false')")"

# ============================================================
echo ""
echo "================================"
echo "Pass: $PASS | Fail: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "SOME TESTS FAILED"
fi
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
