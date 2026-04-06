#!/usr/bin/env bash
# Tests for config.sh — configuration management
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

# Use temp home to avoid polluting real config
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

# === init tests ===

echo "=== config.sh init ==="

out=$(bash "$SCRIPT_DIR/scripts/config.sh" init)
assert_contains "init creates config" "initialized" "$out"
assert_file_exists "config file created" "$HOME/.tech-essay-writer/config.json"

# Verify default values
config=$(cat "$HOME/.tech-essay-writer/config.json")
assert_contains "default has internal platform" "internal" "$config"
assert_contains "default has external platform" "external" "$config"
assert_contains "default writing_style" "technical" "$config"
assert_contains "default language" '"en"' "$config"
assert_contains "default use_author_profile" "true" "$config"
assert_contains "default max_refinement_rounds" "3" "$config"
assert_contains "default has target_audiences" "software engineers" "$config"
assert_contains "default has updated_at" "updated_at" "$config"

# Init idempotent
out=$(bash "$SCRIPT_DIR/scripts/config.sh" init)
assert_contains "init idempotent" "already exists" "$out"

# === read tests ===

echo "=== config.sh read ==="

out=$(bash "$SCRIPT_DIR/scripts/config.sh" read)
assert_contains "read shows platforms" "internal" "$out"
assert_contains "read shows style" "technical" "$out"
assert_contains "read shows audiences" "software engineers" "$out"
assert_contains "read shows language" "en" "$out"
assert_contains "read shows author profile toggle" "True" "$out"
assert_contains "read shows max rounds" "3" "$out"

# Read on empty config
export HOME="$TMPDIR/emptyhome"
mkdir -p "$HOME"
out=$(bash "$SCRIPT_DIR/scripts/config.sh" read)
assert_contains "empty config message" "No config yet" "$out"

# === get tests ===

echo "=== config.sh get ==="

export HOME="$TMPDIR/fakehome"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "get platforms returns JSON array" "internal" "$val"
assert_contains "get platforms has external" "external" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
assert_eq "get writing_style" "technical" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "get language" "en" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get use_author_profile)
assert_eq "get use_author_profile" "true" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get max_refinement_rounds)
assert_eq "get max_refinement_rounds" "3" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get target_audiences)
assert_contains "get audiences" "software engineers" "$val"

# Get non-existent key
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get nonexistent)
assert_eq "get nonexistent returns empty" "" "$val"

# Get on empty config
export HOME="$TMPDIR/emptyhome2"
mkdir -p "$HOME"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "get on empty config returns empty" "" "$val"

# === set tests ===

echo "=== config.sh set ==="

export HOME="$TMPDIR/sethome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

# Set writing_style
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set writing_style conversational)
assert_contains "set writing_style" "Set writing_style" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
assert_eq "writing_style updated" "conversational" "$val"

# Set language
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set language zh)
assert_contains "set language" "Set language" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "language updated to zh" "zh" "$val"

# Set use_author_profile
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set use_author_profile false)
assert_contains "set use_author_profile" "Set use_author_profile" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get use_author_profile)
assert_eq "use_author_profile set to false" "false" "$val"

# Set use_author_profile back to true
bash "$SCRIPT_DIR/scripts/config.sh" set use_author_profile true >/dev/null
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get use_author_profile)
assert_eq "use_author_profile set back to true" "true" "$val"

# Set max_refinement_rounds
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set max_refinement_rounds 5)
assert_contains "set max_refinement_rounds" "Set max_refinement_rounds" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get max_refinement_rounds)
assert_eq "max_refinement_rounds updated" "5" "$val"

# Set default_platforms as JSON array
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set default_platforms '["internal","medium","wechat"]')
assert_contains "set platforms" "Set default_platforms" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "platforms has medium" "medium" "$val"
assert_contains "platforms has wechat" "wechat" "$val"

# Set target_audiences as JSON array
out=$(bash "$SCRIPT_DIR/scripts/config.sh" set target_audiences '["backend engineers","CTOs"]')
assert_contains "set audiences" "Set target_audiences" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get target_audiences)
assert_contains "audiences has CTOs" "CTOs" "$val"

# === set validation tests ===

echo "=== config.sh set validation ==="

# Invalid writing style
if bash "$SCRIPT_DIR/scripts/config.sh" set writing_style "invalid-style" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid style"
else
  PASS=$((PASS + 1))
fi

# Invalid language
if bash "$SCRIPT_DIR/scripts/config.sh" set language "fr" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid language"
else
  PASS=$((PASS + 1))
fi

# Invalid platform in array
if bash "$SCRIPT_DIR/scripts/config.sh" set default_platforms '["internal","fakePlatform"]' 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid platform"
else
  PASS=$((PASS + 1))
fi

# Invalid max_refinement_rounds (too high)
if bash "$SCRIPT_DIR/scripts/config.sh" set max_refinement_rounds 99 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject rounds > 10"
else
  PASS=$((PASS + 1))
fi

# Invalid max_refinement_rounds (zero)
if bash "$SCRIPT_DIR/scripts/config.sh" set max_refinement_rounds 0 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject rounds < 1"
else
  PASS=$((PASS + 1))
fi

# Invalid max_refinement_rounds (not a number)
if bash "$SCRIPT_DIR/scripts/config.sh" set max_refinement_rounds abc 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject non-integer rounds"
else
  PASS=$((PASS + 1))
fi

# Invalid use_author_profile
if bash "$SCRIPT_DIR/scripts/config.sh" set use_author_profile "maybe" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid boolean"
else
  PASS=$((PASS + 1))
fi

# Unknown key
if bash "$SCRIPT_DIR/scripts/config.sh" set unknown_key "value" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject unknown key"
else
  PASS=$((PASS + 1))
fi

# Invalid JSON for platforms
if bash "$SCRIPT_DIR/scripts/config.sh" set default_platforms "not-json" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject non-JSON platforms"
else
  PASS=$((PASS + 1))
fi

# === add-platform / remove-platform tests ===

echo "=== config.sh add-platform / remove-platform ==="

export HOME="$TMPDIR/platformhome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

# Add platform
out=$(bash "$SCRIPT_DIR/scripts/config.sh" add-platform medium)
assert_contains "add medium" "Added platform: medium" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "platforms now has medium" "medium" "$val"

# Add duplicate platform
out=$(bash "$SCRIPT_DIR/scripts/config.sh" add-platform medium)
assert_contains "duplicate platform message" "already" "$out"

# Add invalid platform
if bash "$SCRIPT_DIR/scripts/config.sh" add-platform "fakePlatform" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject invalid platform"
else
  PASS=$((PASS + 1))
fi

# Remove platform
out=$(bash "$SCRIPT_DIR/scripts/config.sh" remove-platform medium)
assert_contains "remove medium" "Removed platform: medium" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_not_contains "medium removed" "medium" "$val"

# Remove non-existent platform
if bash "$SCRIPT_DIR/scripts/config.sh" remove-platform hashnode 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error on non-existent platform"
else
  PASS=$((PASS + 1))
fi

# === add-audience / remove-audience tests ===

echo "=== config.sh add-audience / remove-audience ==="

out=$(bash "$SCRIPT_DIR/scripts/config.sh" add-audience "DevOps engineers")
assert_contains "add audience" "Added audience: DevOps engineers" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get target_audiences)
assert_contains "audiences has DevOps" "DevOps" "$val"

# Add duplicate audience
out=$(bash "$SCRIPT_DIR/scripts/config.sh" add-audience "DevOps engineers")
assert_contains "duplicate audience message" "already" "$out"

# Remove audience
out=$(bash "$SCRIPT_DIR/scripts/config.sh" remove-audience "DevOps engineers")
assert_contains "remove audience" "Removed audience: DevOps engineers" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get target_audiences)
assert_not_contains "DevOps removed" "DevOps" "$val"

# Remove non-existent audience
if bash "$SCRIPT_DIR/scripts/config.sh" remove-audience "nonexistent" 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should error on non-existent audience"
else
  PASS=$((PASS + 1))
fi

# === reset tests ===

echo "=== config.sh reset ==="

# Modify some values first
bash "$SCRIPT_DIR/scripts/config.sh" set language zh >/dev/null
bash "$SCRIPT_DIR/scripts/config.sh" set writing_style narrative >/dev/null

out=$(bash "$SCRIPT_DIR/scripts/config.sh" reset)
assert_contains "reset message" "reset to defaults" "$out"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "reset restores language" "en" "$val"

val=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
assert_eq "reset restores style" "technical" "$val"

# === export tests ===

echo "=== config.sh export ==="

out=$(bash "$SCRIPT_DIR/scripts/config.sh" export)
assert_contains "export is JSON" "default_platforms" "$out"
assert_contains "export has writing_style" "writing_style" "$out"
assert_contains "export has language" "language" "$out"

# Export on empty config auto-initializes
export HOME="$TMPDIR/exporthome"
mkdir -p "$HOME"
out=$(bash "$SCRIPT_DIR/scripts/config.sh" export)
assert_contains "export auto-inits" "default_platforms" "$out"
assert_file_exists "export creates config file" "$HOME/.tech-essay-writer/config.json"

# === usage tests ===

echo "=== config.sh usage ==="

out=$(bash "$SCRIPT_DIR/scripts/config.sh" 2>&1 || true)
assert_contains "usage shows init" "init" "$out"
assert_contains "usage shows read" "read" "$out"
assert_contains "usage shows get" "get" "$out"
assert_contains "usage shows set" "set" "$out"

# === set without prior init (auto-creates defaults) ===

echo "=== config.sh set without init ==="

export HOME="$TMPDIR/noinithome"
mkdir -p "$HOME"

out=$(bash "$SCRIPT_DIR/scripts/config.sh" set language zh)
assert_contains "set without init succeeds" "Set language" "$out"
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "set without init stores value" "zh" "$val"
# Other defaults should exist
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
assert_eq "set without init has defaults" "technical" "$val"

# === pipeline-state.sh integration test ===

echo "=== pipeline-state.sh config integration ==="

export HOME="$TMPDIR/integhome"
mkdir -p "$HOME"

# Set config language to zh
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null
bash "$SCRIPT_DIR/scripts/config.sh" set language zh >/dev/null

# Init a pipeline — should pick up zh from config
PROJECT="$TMPDIR/test-config-project"
mkdir -p "$PROJECT"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" "Config Test Topic" >/dev/null

# Verify language was set from config
lang=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT" "language")
assert_eq "pipeline init uses config language" '"zh"' "$lang"

# Test with config language = en
export HOME="$TMPDIR/integhome2"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

PROJECT2="$TMPDIR/test-config-project-2"
mkdir -p "$PROJECT2"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT2" "Config Test EN" >/dev/null

lang=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT2" "language")
assert_eq "pipeline init uses config language en" '"en"' "$lang"

# Test with no config (fallback to en)
export HOME="$TMPDIR/noconfighome"
mkdir -p "$HOME"

PROJECT3="$TMPDIR/test-config-project-3"
mkdir -p "$PROJECT3"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT3" "No Config Topic" >/dev/null

lang=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT3" "language")
assert_eq "pipeline init falls back to en without config" '"en"' "$lang"

# Test max_refinement_rounds from config
export HOME="$TMPDIR/integhome3"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null
bash "$SCRIPT_DIR/scripts/config.sh" set max_refinement_rounds 5 >/dev/null

PROJECT4="$TMPDIR/test-config-project-4"
mkdir -p "$PROJECT4"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT4" "Rounds Test" >/dev/null

rounds=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-field "$PROJECT4" "max_refinement_rounds")
assert_eq "pipeline init uses config max_refinement_rounds" "5" "$rounds"

# === orchestrate.sh config integration test ===

echo "=== orchestrate.sh build-config-summary ==="

export HOME="$TMPDIR/orchhome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null
bash "$SCRIPT_DIR/scripts/config.sh" set writing_style narrative >/dev/null
bash "$SCRIPT_DIR/scripts/config.sh" add-platform medium >/dev/null

PROJECT5="$TMPDIR/test-orch-project"
mkdir -p "$PROJECT5/.essay-state"
echo '{"stage":"intake","topic":"test","language":"en"}' > "$PROJECT5/.essay-state/pipeline-state.json"

out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT5" "$SCRIPT_DIR" build-config-summary)
assert_contains "config summary has platforms" "internal" "$out"
assert_contains "config summary has medium" "medium" "$out"
assert_contains "config summary has style" "narrative" "$out"
assert_contains "config summary has audiences" "software engineers" "$out"
assert_contains "config summary has language" "en" "$out"

# === atomic write test ===

echo "=== config.sh atomic write ==="

export HOME="$TMPDIR/atomichome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

# Verify no tmp files left
tmp_count=$(find "$HOME/.tech-essay-writer" -name "*.tmp.*" 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no tmp files after write" "0" "$tmp_count"

# === all valid styles test ===

echo "=== config.sh all valid styles ==="

export HOME="$TMPDIR/stylehome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

for style in technical conversational narrative formal casual academic; do
  bash "$SCRIPT_DIR/scripts/config.sh" set writing_style "$style" >/dev/null
  val=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
  assert_eq "style $style accepted" "$style" "$val"
done

# === all valid platforms test ===

echo "=== config.sh all valid platforms ==="

export HOME="$TMPDIR/allplathome"
mkdir -p "$HOME"
bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null

# Set all platforms
bash "$SCRIPT_DIR/scripts/config.sh" set default_platforms '["internal","external","medium","devto","hashnode","wechat","juejin"]' >/dev/null
val=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "all platforms includes juejin" "juejin" "$val"
assert_contains "all platforms includes hashnode" "hashnode" "$val"
assert_contains "all platforms includes wechat" "wechat" "$val"

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
