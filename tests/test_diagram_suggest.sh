#!/usr/bin/env bash
# Tests for diagram-suggest.sh and orchestrate.sh integration
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

# Helper: create a project with state dir and a markdown file
setup_md() {
  local name="$1"
  local proj="$TMPDIR/proj-$name"
  mkdir -p "$proj/.essay-state"
  echo "$proj"
}

# ============================================================
echo "=== diagram-suggest.sh ==="
# ============================================================

# --- Test 1: Runs with architecture content ---
PROJ=$(setup_md "arch")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# System Architecture

The frontend service connects to the backend service.
The backend communicates with the database layer.
The gateway handles all incoming requests.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects architecture" '"type": "architecture"' "$out"

# --- Test 2: Output is valid JSON ---
echo "$out" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null
assert_eq "output is valid JSON" "0" "$?"

# --- Test 3: Has suggestions array ---
assert_contains "has suggestions array" '"suggestions"' "$out"

# --- Test 4: Has summary object ---
assert_contains "has summary object" '"summary"' "$out"

# --- Test 5: Summary has total count ---
assert_contains "summary has total" '"total"' "$out"

# --- Test 6: Summary has type_breakdown ---
assert_contains "summary has type_breakdown" '"type_breakdown"' "$out"

# --- Test 7: Architecture mermaid contains graph ---
assert_contains "architecture mermaid has graph" "graph TD" "$out"

# --- Test 8: Atomic write to state dir ---
assert_file_exists "diagram-suggestions.json created" "$PROJ/.essay-state/diagram-suggestions.json"

# --- Test 9: State file is valid JSON ---
python3 -c "import json; json.load(open('$PROJ/.essay-state/diagram-suggestions.json'))" 2>/dev/null
assert_eq "state file is valid JSON" "0" "$?"

# --- Test 10: Flowchart detection (numbered steps) ---
PROJ=$(setup_md "flow")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Deployment Process

Follow these steps to deploy:

1. Build the Docker image
2. Push to the container registry
3. Deploy to Kubernetes
4. Run health checks
5. Monitor the dashboard
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects flowchart" '"type": "flowchart"' "$out"

# --- Test 11: Flowchart mermaid contains flowchart keyword ---
assert_contains "flowchart mermaid has keyword" "flowchart TD" "$out"

# --- Test 12: Flowchart extracts step labels ---
assert_contains "flowchart has step label" "Build the Docker image" "$out"

# --- Test 13: Comparison detection (vs) ---
PROJ=$(setup_md "cmp")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Redis vs Memcached

Redis offers persistence while Memcached is purely in-memory.
The advantage of Redis is richer data structures, but the trade-off is higher memory usage.
However, Memcached excels at simple key-value caching.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects comparison" '"type": "comparison_table"' "$out"

# --- Test 14: Comparison has no mermaid (tables are markdown) ---
assert_contains "comparison mermaid is null" '"mermaid": null' "$out"

# --- Test 15: State diagram detection ---
PROJ=$(setup_md "state")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Order Lifecycle

An order transitions through several states in its lifecycle.
It starts as pending, changes from pending to active when paid.
Once shipped, it moves to completed. If there's an issue, it becomes failed.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects state diagram" '"type": "state"' "$out"

# --- Test 16: State mermaid contains stateDiagram ---
assert_contains "state mermaid has keyword" "stateDiagram-v2" "$out"

# --- Test 17: State mermaid has state names ---
assert_contains "state mermaid has Pending" "Pending" "$out"

# --- Test 18: Sequence diagram detection ---
PROJ=$(setup_md "seq")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Authentication Flow

The client sends a login request to the server.
The server calls the auth database to verify credentials.
The database returns the user record.
The server responds with a JWT token.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects sequence diagram" '"type": "sequence"' "$out"

# --- Test 19: Sequence mermaid contains sequenceDiagram ---
assert_contains "sequence mermaid has keyword" "sequenceDiagram" "$out"

# --- Test 20: Sequence mermaid has actors ---
assert_contains "sequence mermaid has Client" "Client" "$out"

# --- Test 21: ER diagram detection ---
PROJ=$(setup_md "er")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Data Model

The User entity has many Orders. Each Order belongs to a User.
The foreign key links Order to User via user_id.
The schema defines these relationships in the database model.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects ER diagram" '"type": "er"' "$out"

# --- Test 22: ER mermaid contains erDiagram ---
assert_contains "ER mermaid has keyword" "erDiagram" "$out"

# --- Test 23: Class diagram detection ---
PROJ=$(setup_md "class")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Type Hierarchy

The base class Animal defines common behavior.
class Dog extends Animal with bark method.
The interface Serializable is implemented by both.
Polymorphism allows treating Dog as Animal.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects class diagram" '"type": "class"' "$out"

# --- Test 24: Class mermaid contains classDiagram ---
assert_contains "class mermaid has keyword" "classDiagram" "$out"

# --- Test 25: Timeline detection ---
PROJ=$(setup_md "timeline")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Project History

The timeline of releases shows steady progression.
v1.0 launched in 2020. v2.0 added major features in 2022.
v3.0 is the current milestone released in 2024.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects timeline" '"type": "timeline"' "$out"

# --- Test 26: Timeline mermaid contains gantt ---
assert_contains "timeline mermaid has gantt" "gantt" "$out"

# --- Test 27: Empty file produces zero suggestions ---
PROJ=$(setup_md "empty")
touch "$PROJ/.essay-state/test.md"
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_eq "empty file has 0 suggestions" "0" "$total"

# --- Test 28: No-suggestions file (simple prose) ---
PROJ=$(setup_md "nosug")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Introduction

Hello world. This is a simple paragraph with no technical content
that would benefit from any diagrams or visual aids whatsoever.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_eq "no-suggestion file has 0 suggestions" "0" "$total"

# --- Test 29: Chinese content detection ---
PROJ=$(setup_md "chinese")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# 系统架构

前端服务连接到后端服务。后端与数据库层通信。
微服务架构通过网关处理所有请求。
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
lang=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['language_detected'])")
assert_eq "detects Chinese language" "zh" "$lang"

# --- Test 30: Chinese descriptions when Chinese detected ---
# JSON output may have unicode escapes, so check via python
zh_desc=$(echo "$out" | python3 -c "import json,sys; s=json.load(sys.stdin)['suggestions'][0]['description']; print('架构图' in s)")
assert_eq "Chinese description for architecture" "True" "$zh_desc"

# --- Test 31: Chinese flowchart detection ---
PROJ=$(setup_md "zh-flow")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# 部署流程

部署的步骤如下：

1. 构建镜像
2. 推送到仓库
3. 部署到集群
4. 验证服务状态
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
zh_flow=$(echo "$out" | python3 -c "import json,sys; types=[s['type'] for s in json.load(sys.stdin)['suggestions']]; print('flowchart' in types)")
assert_eq "Chinese flowchart detected" "True" "$zh_flow"

# --- Test 32: Multiple suggestion types in one document ---
PROJ=$(setup_md "multi")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Architecture Overview

The frontend service connects to the backend service via the API gateway.

## Deploy Steps

1. Build the application
2. Run tests
3. Deploy to production

## Option A vs Option B

Approach A has the advantage of simplicity. However, approach B offers better performance.
The trade-off is complexity versus speed.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_json_field_gte "multi-type doc has >= 3 suggestions" <(echo "$out") "['summary']['total']" "3"

# --- Test 33: Type breakdown counts are correct ---
types=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin)['summary']['type_breakdown']; print(len(d))")
assert_json_field_gte "multiple types in breakdown" <(echo "$out") "['summary']['type_breakdown']['architecture']" "1"

# --- Test 34: Suggestion has location field ---
has_location=$(echo "$out" | python3 -c "import json,sys; s=json.load(sys.stdin)['suggestions'][0]; print('location' in s)")
assert_eq "suggestion has location field" "True" "$has_location"

# --- Test 35: Suggestion has line field ---
has_line=$(echo "$out" | python3 -c "import json,sys; s=json.load(sys.stdin)['suggestions'][0]; print('line' in s)")
assert_eq "suggestion has line field" "True" "$has_line"

# --- Test 36: Suggestion has description field ---
has_desc=$(echo "$out" | python3 -c "import json,sys; s=json.load(sys.stdin)['suggestions'][0]; print('description' in s)")
assert_eq "suggestion has description field" "True" "$has_desc"

# --- Test 37: Suggestion has type field ---
has_type=$(echo "$out" | python3 -c "import json,sys; s=json.load(sys.stdin)['suggestions'][0]; print('type' in s)")
assert_eq "suggestion has type field" "True" "$has_type"

# --- Test 38: File not found returns error JSON ---
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "/nonexistent/file.md" 2>&1 || true)
assert_contains "missing file returns error" '"error"' "$out"

# --- Test 39: Verbose mode outputs formatted text ---
PROJ=$(setup_md "verbose")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# System Design

The frontend service connects to the backend service.
The gateway proxy handles all API requests.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" "--verbose" 2>&1)
assert_contains "verbose has Suggestion header" "Suggestion" "$out"

# --- Test 40: Verbose mode shows mermaid blocks ---
assert_contains "verbose has mermaid block" '```mermaid' "$out"

# --- Test 41: Code blocks are excluded from analysis ---
PROJ=$(setup_md "codeblock")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Simple Guide

Here is some sample code:

```python
class Dog(Animal):
    def bark(self):
        pass

class Cat(Animal):
    def meow(self):
        pass
```

That covers the basics of this pattern.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
# The class keywords are inside a code block, so class detection should not trigger
total=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); types=[s['type'] for s in d['suggestions']]; print('class' in types)")
assert_eq "code blocks excluded from class detection" "False" "$total"

# --- Test 42: Data pipeline detection ---
PROJ=$(setup_md "pipeline")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Data Pipeline

Our data pipeline starts with ingesting events from the producer.
The data processing stage transforms raw events into metrics.
The consumer subscribes to the output stream.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects flowchart for pipeline" '"type": "flowchart"' "$out"

# --- Test 43: Pros and cons detection ---
PROJ=$(setup_md "proscons")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Framework Choice

Let's weigh the pros and cons of each framework.
React has widespread adoption while Vue has simpler syntax.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects pros/cons comparison" '"type": "comparison_table"' "$out"

# --- Test 44: FSM keyword detection ---
PROJ=$(setup_md "fsm")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Parser Implementation

The parser uses a finite state machine approach.
States include idle, reading, and error.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects FSM state diagram" '"type": "state"' "$out"

# --- Test 45: Protocol/API flow detection ---
PROJ=$(setup_md "protocol")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# OAuth Flow

The OAuth handshake begins when the browser sends an authentication request.
The server responds with a redirect to the auth provider.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects OAuth sequence" '"type": "sequence"' "$out"

# --- Test 46: Language detected as English for English content ---
PROJ=$(setup_md "en")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Architecture

The frontend service connects to the backend service through the gateway.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
lang=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['language_detected'])")
assert_eq "detects English language" "en" "$lang"

# --- Test 47: Suggestion types are valid enum values ---
PROJ=$(setup_md "types")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# System

The frontend service connects to the backend service.

## Steps

1. First thing
2. Second thing
3. Third thing

## A vs B

Option A compared to option B. The trade-off is speed however.

## Lifecycle

The state changes from pending to active to completed.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
valid=$(echo "$out" | python3 -c "
import json,sys
data=json.load(sys.stdin)
valid_types={'flowchart','sequence','class','state','er','comparison_table','architecture','timeline'}
all_valid=all(s['type'] in valid_types for s in data['suggestions'])
print(all_valid)
")
assert_eq "all suggestion types are valid enum values" "True" "$valid"

# --- Test 48: Line numbers are positive integers ---
lines_valid=$(echo "$out" | python3 -c "
import json,sys
data=json.load(sys.stdin)
print(all(isinstance(s['line'],int) and s['line']>=1 for s in data['suggestions']))
")
assert_eq "all line numbers are positive integers" "True" "$lines_valid"

# --- Test 49: Mermaid syntax for flowchart has --> arrows ---
PROJ=$(setup_md "arrows")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Build Process

1. Compile source code
2. Run unit tests
3. Package artifacts
4. Upload to registry
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
has_arrows=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); m=[s['mermaid'] for s in d['suggestions'] if s['type']=='flowchart']; print('-->' in m[0] if m else False)")
assert_eq "flowchart mermaid has arrows" "True" "$has_arrows"

# --- Test 50: Short sections are skipped ---
PROJ=$(setup_md "short")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Title

OK.

## Conclusion

Bye.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_eq "short sections produce 0 suggestions" "0" "$total"


# ============================================================
echo ""
echo "=== orchestrate.sh integration ==="
# ============================================================

# --- Test 51: build-diagram-suggestions command exists in dispatch ---
PROJ=$(setup_md "orch")
cat > "$PROJ/.essay-state/draft-v1.md" << 'EOF'
# Architecture

The frontend service connects to the backend service via the gateway.
The middleware layer handles authentication.

## Deploy Steps

1. Build images
2. Push to registry
3. Deploy to cluster
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-diagram-suggestions 2>&1)
assert_contains "orchestrate dispatch works" '"suggestions"' "$out"

# --- Test 52: Orchestrate finds latest draft ---
assert_contains "orchestrate finds draft content" '"architecture"' "$out"

# --- Test 53: Orchestrate falls back to final-external ---
PROJ=$(setup_md "orch-fallback")
cat > "$PROJ/.essay-state/final-external.md" << 'EOF'
# System Design

The client sends a request to the server. The server calls the database.
The database returns results. The server responds to the client.
EOF
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-diagram-suggestions 2>&1)
assert_contains "orchestrate falls back to final-external" '"suggestions"' "$out"

# --- Test 54: Orchestrate returns error with no draft ---
PROJ=$(setup_md "orch-empty")
out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" build-diagram-suggestions 2>&1 || true)
assert_contains "orchestrate returns error with no draft" '"error"' "$out"

# --- Test 55: build-diagram-suggestions in usage text ---
usage_out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJ" "$SCRIPT_DIR" help 2>&1 || true)
assert_contains "help text mentions diagram-suggestions" "build-diagram-suggestions" "$usage_out"

# ============================================================
echo ""
echo "=== edge cases ==="
# ============================================================

# --- Test 56: Mixed English and Chinese ---
PROJ=$(setup_md "mixed")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Mixed Content

The system architecture 系统架构 includes:

The frontend service connects to the backend.
前端服务连接后端微服务网关。
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "mixed content produces suggestions" '"suggestions"' "$out"

# --- Test 57: Markdown with only headings ---
PROJ=$(setup_md "headings")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Title
## Section A
## Section B
## Section C
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_eq "headings-only file has 0 suggestions" "0" "$total"

# --- Test 58: Large document with many sections ---
PROJ=$(setup_md "large")
{
  echo "# Big Article"
  for i in $(seq 1 10); do
    echo ""
    echo "## Section $i"
    echo ""
    echo "This section describes step $i of the process."
    echo "First we configure, then we deploy, finally we verify."
  done
} > "$PROJ/.essay-state/test.md"
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
total=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['total'])")
assert_json_field_gte "large doc has multiple suggestions" <(echo "$out") "['summary']['total']" "1"

# --- Test 59: Hierarchy/tree detection via class diagram (inheritance) ---
PROJ=$(setup_md "hierarchy")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# Type System

The base class defines shared behavior.
Each subclass inherits from the parent class.
Polymorphism allows treating the subclass as the base class.
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "detects class diagram for inheritance" '"type": "class"' "$out"

# --- Test 60: Chinese ER detection ---
PROJ=$(setup_md "zh-er")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# 数据模型

用户实体与订单实体之间存在关系。
每个订单通过外键关联到用户。
数据模型定义了主键和索引。
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "Chinese ER detected" '"type": "er"' "$out"

# --- Test 61: Chinese state detection ---
PROJ=$(setup_md "zh-state")
cat > "$PROJ/.essay-state/test.md" << 'EOF'
# 订单生命周期

订单经历完整的状态转换过程。
从 pending 创建后变为 active 状态。
最终变为 completed 或 failed。
EOF
out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJ/.essay-state/test.md" 2>&1)
assert_contains "Chinese state detected" '"type": "state"' "$out"

# ============================================================
echo ""
echo "========================================"
echo "diagram-suggest tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
