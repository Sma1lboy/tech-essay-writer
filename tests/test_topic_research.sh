#!/usr/bin/env bash
# Tests for topic-research.sh
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

# Helper: set up a minimal project with state dir
setup_project() {
  local proj="$TMPDIR/proj-$1"
  mkdir -p "$proj/.essay-state"
  echo "$proj"
}

# ============================================================
echo "=== topic-research.sh ==="
# ============================================================

# --- Test 1: Runs with a simple topic ---
PROJ=$(setup_project "basic")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Kubernetes" 2>&1)
assert_contains "runs with simple topic" '"topic"' "$out"
assert_contains "output has research_questions" '"research_questions"' "$out"

# --- Test 2: Output is valid JSON ---
python3 -c "import json,sys; json.loads(sys.argv[1])" "$out" 2>/dev/null
assert_eq "output is valid JSON" "0" "$?"

# --- Test 3: research-brief.json is created ---
assert_file_exists "research-brief.json created" "$PROJ/.essay-state/research-brief.json"

# --- Test 4: Topic is recorded correctly ---
topic_out=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['topic'])" "$out")
assert_eq "topic recorded in output" "Kubernetes" "$topic_out"

# --- Test 5: Keywords are extracted ---
kw_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['keywords']))" "$out")
assert_eq "keywords extracted for single word" "1" "$kw_count"

# --- Test 6: Multi-word topic extracts multiple keywords ---
PROJ=$(setup_project "multi-keyword")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "React Server Components vs Client Components" 2>&1)
kw_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['keywords']))" "$out")
kw_gte=$(python3 -c "print('true' if int('$kw_count') >= 3 else 'false')")
assert_eq "multi-word topic extracts >= 3 keywords" "true" "$kw_gte"

# --- Test 7: Research questions are generated (at least 10) ---
PROJ=$(setup_project "question-count")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "GraphQL API Design" 2>&1)
q_count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['summary']['total_questions'])" "$out")
q_gte=$(python3 -c "print('true' if int('$q_count') >= 10 else 'false')")
assert_eq "at least 10 research questions generated" "true" "$q_gte"

# --- Test 8: Each question has category, question, purpose ---
fields_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for q in d['research_questions']:
    if not all(k in q for k in ['category','question','purpose']):
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all questions have category, question, purpose" "true" "$fields_ok"

# --- Test 9: Search queries are generated (at least 8) ---
sq_count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['summary']['total_search_queries'])" "$out")
sq_gte=$(python3 -c "print('true' if int('$sq_count') >= 8 else 'false')")
assert_eq "at least 8 search queries generated" "true" "$sq_gte"

# --- Test 10: Each search query has query, purpose, target ---
sq_fields_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for q in d['search_queries']:
    if not all(k in q for k in ['query','purpose','target']):
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all search queries have query, purpose, target" "true" "$sq_fields_ok"

# --- Test 11: Unique angles are generated (at least 6) ---
angle_count=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['summary']['total_angles'])" "$out")
angle_gte=$(python3 -c "print('true' if int('$angle_count') >= 6 else 'false')")
assert_eq "at least 6 unique angles generated" "true" "$angle_gte"

# --- Test 12: Each angle has angle, type, strength, risk, relevance_score, rank ---
angle_fields_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
required = {'angle','type','strength','risk','relevance_score','rank'}
for a in d['unique_angles']:
    if not required.issubset(set(a.keys())):
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all angles have required fields" "true" "$angle_fields_ok"

# --- Test 13: Angles are ranked by relevance_score descending ---
ranking_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
scores = [a['relevance_score'] for a in d['unique_angles']]
print('true' if scores == sorted(scores, reverse=True) else 'false')
" "$out")
assert_eq "angles sorted by relevance_score desc" "true" "$ranking_ok"

# --- Test 14: Angle ranks are sequential 1..N ---
ranks_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
ranks = [a['rank'] for a in d['unique_angles']]
expected = list(range(1, len(ranks)+1))
print('true' if ranks == expected else 'false')
" "$out")
assert_eq "angle ranks are sequential 1..N" "true" "$ranks_ok"

# --- Test 15: Relevance scores are in range 1-10 ---
scores_valid=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for a in d['unique_angles']:
    if a['relevance_score'] < 1 or a['relevance_score'] > 10:
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all relevance scores between 1-10" "true" "$scores_valid"

# --- Test 16: Domain detection — frontend topic ---
PROJ=$(setup_project "domain-frontend")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "React Component Performance Optimization" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "frontend domain detected for React topic" "frontend" "$domains"

# --- Test 17: Domain detection — devops topic ---
PROJ=$(setup_project "domain-devops")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Kubernetes CI/CD Pipeline Automation" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "devops domain detected for K8s CI/CD topic" "devops" "$domains"

# --- Test 18: Domain detection — AI/ML topic ---
PROJ=$(setup_project "domain-ai")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Fine-tuning LLM Models for Code Generation" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "ai_ml domain detected for LLM topic" "ai_ml" "$domains"

# --- Test 19: Domain detection — security topic ---
PROJ=$(setup_project "domain-security")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Zero-Trust Authentication Architecture" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "security domain detected" "security" "$domains"

# --- Test 20: Domain detection — data topic ---
PROJ=$(setup_project "domain-data")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "PostgreSQL Query Optimization at Scale" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "data domain detected for PostgreSQL topic" "data" "$domains"

# --- Test 21: Domain-specific research question generated for AI topic ---
PROJ=$(setup_project "domain-q-ai")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Machine Learning Pipeline Testing" 2>&1)
domain_q=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for q in d['research_questions']:
    if q['category'] == 'domain_specific':
        print(q['question']); sys.exit()
print('')
" "$out")
assert_contains "AI domain question mentions ethical" "ethical" "$domain_q"

# --- Test 22: Research questions include topic in text ---
PROJ=$(setup_project "topic-in-questions")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Event Sourcing" 2>&1)
topic_in_q=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = sum(1 for q in d['research_questions'] if 'Event Sourcing' in q['question'])
print('true' if found >= 5 else 'false')
" "$out")
assert_eq "topic appears in most research questions" "true" "$topic_in_q"

# --- Test 23: Search queries include topic ---
topic_in_sq=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = sum(1 for q in d['search_queries'] if 'Event Sourcing' in q['query'])
print('true' if found >= 3 else 'false')
" "$out")
assert_eq "topic appears in multiple search queries" "true" "$topic_in_sq"

# --- Test 24: Unique angles include topic ---
topic_in_angles=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = sum(1 for a in d['unique_angles'] if 'Event Sourcing' in a['angle'])
print('true' if found >= 3 else 'false')
" "$out")
assert_eq "topic appears in multiple unique angles" "true" "$topic_in_angles"

# --- Test 25: Priority assignment — high priority questions exist ---
high_count=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
count = sum(1 for q in d['research_questions'] if q.get('priority') == 'high')
print(count)
" "$out")
high_gte=$(python3 -c "print('true' if int('$high_count') >= 3 else 'false')")
assert_eq "at least 3 high-priority questions" "true" "$high_gte"

# --- Test 26: Priority assignment — all questions have priority ---
priority_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
for q in d['research_questions']:
    if q.get('priority') not in ('high','medium','low'):
        print('false'); sys.exit()
print('true')
" "$out")
assert_eq "all questions have valid priority" "true" "$priority_ok"

# --- Test 27: Summary section has all required fields ---
summary_ok=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
s = d['summary']
required = {'total_questions','total_search_queries','total_angles','high_priority_questions','top_angle','top_angle_type'}
print('true' if required.issubset(set(s.keys())) else 'false')
" "$out")
assert_eq "summary has all required fields" "true" "$summary_ok"

# --- Test 28: Deterministic output — same topic produces same output ---
PROJ=$(setup_project "deterministic")
out1=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Docker Optimization" 2>&1)
out2=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Docker Optimization" 2>&1)
# Compare everything except generated_at timestamp
questions1=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print([q['question'] for q in d['research_questions']])" "$out1")
questions2=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print([q['question'] for q in d['research_questions']])" "$out2")
assert_eq "deterministic research questions" "$questions1" "$questions2"

# --- Test 29: Atomic write — no tmp files left ---
PROJ=$(setup_project "atomic")
bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Atomic Test" >/dev/null 2>&1
tmp_count=$(find "$PROJ/.essay-state" -name "*.tmp.*" | wc -l | tr -d ' ')
assert_eq "no tmp files left" "0" "$tmp_count"

# --- Test 30: Handles special characters in topic ---
PROJ=$(setup_project "special-chars")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "C++ Memory Safety & RAII Patterns" 2>&1)
assert_contains "handles special chars" '"topic"' "$out"
topic_out=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['topic'])" "$out")
assert_eq "special chars preserved in topic" "C++ Memory Safety & RAII Patterns" "$topic_out"

# --- Test 31: Handles very long topic gracefully ---
PROJ=$(setup_project "long-topic")
long_topic="Building a Distributed Event-Driven Microservices Architecture with Kubernetes and Apache Kafka for Real-Time Data Processing"
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "$long_topic" 2>&1)
assert_contains "handles long topic" '"research_questions"' "$out"
kw_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['keywords']))" "$out")
kw_many=$(python3 -c "print('true' if int('$kw_count') >= 5 else 'false')")
assert_eq "many keywords from long topic" "true" "$kw_many"

# --- Test 32: Multiple domains detected for cross-cutting topic ---
PROJ=$(setup_project "multi-domain")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Deploying React Apps on Kubernetes with CI/CD" 2>&1)
domain_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])['detected_domains']))" "$out")
multi_domain=$(python3 -c "print('true' if int('$domain_count') >= 2 else 'false')")
assert_eq "multiple domains detected for cross-cutting topic" "true" "$multi_domain"

# --- Test 33: Cross-domain angle generated when multiple domains ---
cross_angle=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
found = any(a['type'] == 'cross_domain' for a in d['unique_angles'])
print('true' if found else 'false')
" "$out")
assert_eq "cross-domain angle present" "true" "$cross_angle"

# --- Test 34: Angle types include all expected types ---
PROJ=$(setup_project "angle-types")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Terraform Infrastructure as Code" 2>&1)
angle_types=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
types = sorted(set(a['type'] for a in d['unique_angles']))
print(' '.join(types))
" "$out")
assert_contains "contrarian angle type present" "contrarian" "$angle_types"
assert_contains "experience_report angle type present" "experience_report" "$angle_types"
assert_contains "decision_framework angle type present" "decision_framework" "$angle_types"
assert_contains "myth_busting angle type present" "myth_busting" "$angle_types"

# --- Test 35: Search queries cover different targets ---
PROJ=$(setup_project "query-targets")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Rust Memory Safety" 2>&1)
targets=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
targets = sorted(set(q['target'] for q in d['search_queries']))
print(' '.join(targets))
" "$out")
assert_contains "dev_community target present" "dev_community" "$targets"
assert_contains "github target present" "github" "$targets"
assert_contains "hacker_news target present" "hacker_news" "$targets"

# --- Test 36: inputs_used tracking ---
PROJ=$(setup_project "inputs-tracking")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Input Tracking Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Input Tracking Test" 2>&1)
ps_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['pipeline_state'])" "$out")
assert_eq "pipeline_state marked as used" "True" "$ps_used"

# --- Test 37: inputs_used — materials not present ---
mat_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['materials'])" "$out")
assert_eq "materials marked as not used when absent" "False" "$mat_used"

# --- Test 38: inputs_used — materials present ---
PROJ=$(setup_project "inputs-materials")
cat > "$PROJ/.essay-state/materials.json" << 'EOF'
{"items":[{"title":"Test Material","source":"https://example.com"}]}
EOF
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Materials Test" 2>&1)
mat_used=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['inputs_used']['materials'])" "$out")
assert_eq "materials marked as used when present" "True" "$mat_used"

# --- Test 39: State dir is created if it doesn't exist ---
PROJ="$TMPDIR/proj-auto-mkdir"
mkdir -p "$PROJ"
# Note: NOT creating .essay-state dir — the script should
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Auto Mkdir Test" 2>&1)
assert_file_exists "state dir auto-created" "$PROJ/.essay-state/research-brief.json"

# --- Test 40: Corrupt pipeline-state.json handled gracefully ---
PROJ=$(setup_project "corrupt-pipeline")
echo "NOT VALID JSON {{{" > "$PROJ/.essay-state/pipeline-state.json"
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Corrupt State Test" 2>&1)
assert_contains "handles corrupt pipeline state" '"research_questions"' "$out"

# --- Test 41: Corrupt materials.json handled gracefully ---
PROJ=$(setup_project "corrupt-materials")
echo "<<<BROKEN>>>" > "$PROJ/.essay-state/materials.json"
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Corrupt Materials Test" 2>&1)
assert_contains "handles corrupt materials" '"search_queries"' "$out"

# --- Test 42: generated_at timestamp is present and valid ---
PROJ=$(setup_project "timestamp")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Timestamp Test" 2>&1)
ts_valid=$(python3 -c "
import json,sys
from datetime import datetime
d = json.loads(sys.argv[1])
ts = d.get('generated_at','')
try:
    datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')
    print('true')
except:
    print('false')
" "$out")
assert_eq "generated_at is valid ISO timestamp" "true" "$ts_valid"

# --- Test 43: Research question categories are all unique ---
PROJ=$(setup_project "unique-cats")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Event Driven Architecture" 2>&1)
cats_unique=$(python3 -c "
import json,sys
d = json.loads(sys.argv[1])
cats = [q['category'] for q in d['research_questions']]
print('true' if len(cats) == len(set(cats)) else 'false')
" "$out")
assert_eq "research question categories are all unique" "true" "$cats_unique"

# --- Test 44: file on disk matches stdout output ---
PROJ=$(setup_project "file-match")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "File Match Test" 2>&1)
file_topic=$(python3 -c "import json; print(json.load(open('$PROJ/.essay-state/research-brief.json'))['topic'])")
assert_eq "file on disk matches stdout topic" "File Match Test" "$file_topic"

# --- Test 45: Missing topic argument fails ---
PROJ=$(setup_project "missing-topic")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" 2>&1 || true)
assert_contains "missing topic fails" "required" "$out"

# ============================================================
echo ""
echo "=== orchestrate.sh integration ==="
# ============================================================

# --- Test 46: build-topic-research dispatches with explicit topic ---
PROJ=$(setup_project "orch-explicit")
mkdir -p "$PROJ/.essay-state"
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-topic-research "Microservices" 2>&1)
assert_contains "orchestrator dispatches topic research" '"research_questions"' "$out"
topic_out=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['topic'])" "$out")
assert_eq "orchestrator passes topic arg" "Microservices" "$topic_out"

# --- Test 47: build-topic-research reads topic from pipeline-state ---
PROJ=$(setup_project "orch-pipeline")
cat > "$PROJ/.essay-state/pipeline-state.json" << 'EOF'
{"topic":"Pipeline Topic Test","stage":"research","language":"en"}
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-topic-research 2>&1)
topic_out=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['topic'])" "$out")
assert_eq "orchestrator reads topic from pipeline state" "Pipeline Topic Test" "$topic_out"

# --- Test 48: build-topic-research fails without topic or pipeline state ---
PROJ=$(setup_project "orch-no-topic")
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-topic-research 2>&1 || true)
assert_contains "orchestrator fails without topic" "error" "$out"

# --- Test 49: Usage shows build-topic-research ---
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" x x invalid 2>&1 || true)
assert_contains "usage shows build-topic-research" "build-topic-research" "$out"

# --- Test 50: General domain fallback for unknown topic ---
PROJ=$(setup_project "general-domain")
out=$(bash "$SCRIPT_DIR/scripts/topic-research.sh" "$PROJ" "Productivity Hacks for Remote Teams" 2>&1)
domains=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['detected_domains'])" "$out")
assert_contains "general domain for non-tech topic" "general" "$domains"

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
