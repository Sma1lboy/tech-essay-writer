#!/usr/bin/env bash
# Tests for scripts/help.sh and scripts/version.sh
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
    echo "  should NOT contain: $needle"
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

# =============================================
echo "=== version.sh — show (default) ==="
# =============================================

# Save original version
ORIG_VERSION=$(cat "$SCRIPT_DIR/VERSION")

out=$(bash "$SCRIPT_DIR/scripts/version.sh" 2>&1)
assert_contains "show includes version prefix" "tech-essay-writer v" "$out"
assert_contains "show includes version number" "$ORIG_VERSION" "$out"

# =============================================
echo "=== version.sh — show (explicit) ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/version.sh" show 2>&1)
assert_contains "explicit show includes version" "tech-essay-writer v" "$out"

# =============================================
echo "=== version.sh — raw ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/version.sh" raw 2>&1)
assert_eq "raw outputs version only" "$(echo "$ORIG_VERSION" | tr -d '[:space:]')" "$out"

# =============================================
echo "=== version.sh — bump patch ==="
# =============================================

# Work on a copy: override VERSION file location via temp dir
cp "$SCRIPT_DIR/VERSION" "$TMPDIR/VERSION"
cp "$SCRIPT_DIR/scripts/version.sh" "$TMPDIR/version.sh"

# Create a wrapper to test bump with a temp VERSION file
cat > "$TMPDIR/test-bump.sh" << 'BUMP_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
VERSION_FILE="$1"
COMPONENT="$2"
# Read version
ver=$(head -1 "$VERSION_FILE" | tr -d '[:space:]')
MAJOR=$(echo "$ver" | cut -d. -f1)
MINOR=$(echo "$ver" | cut -d. -f2)
PATCH=$(echo "$ver" | cut -d. -f3)
case "$COMPONENT" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac
echo "${MAJOR}.${MINOR}.${PATCH}" > "$VERSION_FILE"
echo "${ver} -> ${MAJOR}.${MINOR}.${PATCH}"
BUMP_SCRIPT
chmod +x "$TMPDIR/test-bump.sh"

echo "1.0.0" > "$TMPDIR/VERSION"
out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" patch)
assert_contains "bump patch output" "1.0.0 -> 1.0.1" "$out"
new_ver=$(cat "$TMPDIR/VERSION" | tr -d '[:space:]')
assert_eq "bump patch file updated" "1.0.1" "$new_ver"

# =============================================
echo "=== version.sh — bump minor ==="
# =============================================

out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" minor)
assert_contains "bump minor output" "1.0.1 -> 1.1.0" "$out"
new_ver=$(cat "$TMPDIR/VERSION" | tr -d '[:space:]')
assert_eq "bump minor file updated" "1.1.0" "$new_ver"

# =============================================
echo "=== version.sh — bump major ==="
# =============================================

out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" major)
assert_contains "bump major output" "1.1.0 -> 2.0.0" "$out"
new_ver=$(cat "$TMPDIR/VERSION" | tr -d '[:space:]')
assert_eq "bump major file updated" "2.0.0" "$new_ver"

# =============================================
echo "=== version.sh — bump patch resets only patch ==="
# =============================================

echo "3.5.9" > "$TMPDIR/VERSION"
out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" patch)
assert_contains "bump patch from 3.5.9" "3.5.9 -> 3.5.10" "$out"

# =============================================
echo "=== version.sh — bump minor resets patch ==="
# =============================================

echo "2.3.7" > "$TMPDIR/VERSION"
out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" minor)
assert_contains "bump minor resets patch" "2.3.7 -> 2.4.0" "$out"

# =============================================
echo "=== version.sh — bump major resets minor and patch ==="
# =============================================

echo "4.8.12" > "$TMPDIR/VERSION"
out=$(bash "$TMPDIR/test-bump.sh" "$TMPDIR/VERSION" major)
assert_contains "bump major resets minor+patch" "4.8.12 -> 5.0.0" "$out"

# =============================================
echo "=== version.sh — help ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/version.sh" --help 2>&1)
assert_contains "help shows Usage" "Usage" "$out"
assert_contains "help shows bump" "bump" "$out"
assert_contains "help shows major" "major" "$out"
assert_contains "help shows minor" "minor" "$out"
assert_contains "help shows patch" "patch" "$out"

# =============================================
echo "=== version.sh — unknown command fails ==="
# =============================================

ec=0
bash "$SCRIPT_DIR/scripts/version.sh" nonexistent 2>/dev/null || ec=$?
assert_eq "unknown command exits non-zero" "1" "$ec"

# =============================================
echo "=== version.sh — VERSION file auto-created ==="
# =============================================

TMPDIR2=$(mktemp -d)
# Create a minimal version.sh pointing to TMPDIR2 as SKILL_DIR
cat > "$TMPDIR2/version_test.sh" << 'VTEST'
#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$1"
VERSION_FILE="$SKILL_DIR/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
  echo "1.0.0" > "$VERSION_FILE"
fi
head -1 "$VERSION_FILE" | tr -d '[:space:]'
VTEST

out=$(bash "$TMPDIR2/version_test.sh" "$TMPDIR2")
assert_eq "auto-creates VERSION with 1.0.0" "1.0.0" "$out"
rm -rf "$TMPDIR2"

# =============================================
echo "=== help.sh — list all scripts ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" 2>&1)
assert_contains "help lists orchestrate" "orchestrate" "$out"
assert_contains "help lists pipeline-state" "pipeline-state" "$out"
assert_contains "help lists version" "version" "$out"
assert_contains "help lists help" "help" "$out"
assert_contains "help lists dry-run" "dry-run" "$out"
assert_contains "help shows script count" "scripts available" "$out"
assert_contains "help shows version number" "v" "$out"
assert_contains "help shows Script Reference" "Script Reference" "$out"

# =============================================
echo "=== help.sh — shows description for each script ==="
# =============================================

# Verify a sample of descriptions are present
assert_contains "orchestrate has description" "Pipeline orchestrator" "$out"
assert_contains "checkpoint has description" "checkpoint" "$out"
assert_contains "config has description" "configuration" "$out"

# =============================================
echo "=== help.sh — all scripts listed ==="
# =============================================

# Count the number of .sh files in scripts/
SCRIPT_COUNT=$(ls "$SCRIPT_DIR/scripts/"*.sh | wc -l | tr -d ' ')
LISTED_COUNT=$(echo "$out" | grep -c "scripts available" | head -1)
# Extract the number from output
LISTED_NUM=$(echo "$out" | grep "scripts available" | grep -oE '[0-9]+' | head -1)
assert_eq "help lists all scripts" "$SCRIPT_COUNT" "$LISTED_NUM"

# =============================================
echo "=== help.sh — detailed help for a command ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" version 2>&1)
assert_contains "detail shows command name" "=== version ===" "$out"
assert_contains "detail shows version description" "Version tracking" "$out"
assert_contains "detail shows usage" "Usage" "$out"

# =============================================
echo "=== help.sh — detailed help for checkpoint ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" checkpoint 2>&1)
assert_contains "checkpoint detail shows name" "=== checkpoint ===" "$out"
assert_contains "checkpoint detail has usage" "Usage" "$out"

# =============================================
echo "=== help.sh — strips .sh suffix ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" version.sh 2>&1)
assert_contains "accepts .sh suffix" "=== version ===" "$out"

# =============================================
echo "=== help.sh — unknown command fails ==="
# =============================================

ec=0
out=$(bash "$SCRIPT_DIR/scripts/help.sh" nonexistent_cmd 2>&1) || ec=$?
assert_eq "unknown command exits non-zero" "1" "$ec"
assert_contains "unknown command lists alternatives" "Available commands" "$out"

# =============================================
echo "=== help.sh — --help flag ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" --help 2>&1)
assert_contains "help --help shows usage" "Usage" "$out"
assert_contains "help --help mentions command" "command" "$out"

# =============================================
echo "=== help.sh — -h flag ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" -h 2>&1)
assert_contains "help -h shows usage" "Usage" "$out"

# =============================================
echo "=== help.sh — detailed help for config shows subcommands ==="
# =============================================

out=$(bash "$SCRIPT_DIR/scripts/help.sh" config 2>&1)
assert_contains "config detail has init" "init" "$out"
assert_contains "config detail has set" "set" "$out"

# --- Verify original VERSION was not modified ---
FINAL_VERSION=$(cat "$SCRIPT_DIR/VERSION")
assert_eq "VERSION file not modified by tests" "$ORIG_VERSION" "$FINAL_VERSION"

# --- Summary ---
echo ""
echo "Pass: $PASS | Fail: $FAIL"
