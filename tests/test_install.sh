#!/usr/bin/env bash
# Tests for scripts/install.sh
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

assert_file_exists() {
  local desc="$1" path="$2"
  if [ -f "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — file not found: $path"
  fi
}

assert_dir_exists() {
  local desc="$1" path="$2"
  if [ -d "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — directory not found: $path"
  fi
}

assert_symlink() {
  local desc="$1" path="$2"
  if [ -L "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — not a symlink: $path"
  fi
}

assert_not_exists() {
  local desc="$1" path="$2"
  if [ ! -e "$path" ] && [ ! -L "$path" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — should not exist: $path"
  fi
}

assert_symlink_target() {
  local desc="$1" link="$2" expected_target="$3"
  if [ -L "$link" ]; then
    local actual_target
    actual_target=$(readlink "$link")
    if [ "$actual_target" = "$expected_target" ]; then
      PASS=$((PASS + 1))
    else
      FAIL=$((FAIL + 1))
      echo "FAIL: $desc"
      echo "  expected target: $expected_target"
      echo "  actual target:   $actual_target"
    fi
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc — not a symlink: $link"
  fi
}

# --- Helper: create a fake project structure ---
setup_fake_project() {
  local project_dir="$1"
  mkdir -p "$project_dir/scripts"
  mkdir -p "$project_dir/prompts"
  mkdir -p "$project_dir/templates"
  echo "# Skill" > "$project_dir/SKILL.md"
  echo "#!/bin/bash" > "$project_dir/scripts/orchestrate.sh"
  echo "# Prompt" > "$project_dir/prompts/researcher.md"
  echo "# Template" > "$project_dir/templates/tutorial.md"

  # Copy install.sh into the fake project
  cp "$SCRIPT_DIR/scripts/install.sh" "$project_dir/scripts/install.sh"
  chmod +x "$project_dir/scripts/install.sh"
}

# --- Helper: run install.sh with overridden HOME ---
run_install() {
  local project_dir="$1"
  shift
  HOME="$TMPDIR/home" bash "$project_dir/scripts/install.sh" "$@" 2>&1
}

# =============================================
echo "=== install.sh — fresh install ==="
# =============================================

FAKE_PROJECT="$TMPDIR/project1"
setup_fake_project "$FAKE_PROJECT"
mkdir -p "$TMPDIR/home/.claude/skills"

out=$(run_install "$FAKE_PROJECT")
SKILL_DIR="$TMPDIR/home/.claude/skills/tech-essay-writer"

assert_contains "install prints success" "Installed" "$out"
assert_dir_exists "skill directory created" "$SKILL_DIR"
assert_symlink "SKILL.md is symlink" "$SKILL_DIR/SKILL.md"
assert_symlink "scripts is symlink" "$SKILL_DIR/scripts"
assert_symlink "prompts is symlink" "$SKILL_DIR/prompts"
assert_symlink "templates is symlink" "$SKILL_DIR/templates"

assert_symlink_target "SKILL.md points to project" "$SKILL_DIR/SKILL.md" "$FAKE_PROJECT/SKILL.md"
assert_symlink_target "scripts points to project" "$SKILL_DIR/scripts" "$FAKE_PROJECT/scripts"
assert_symlink_target "prompts points to project" "$SKILL_DIR/prompts" "$FAKE_PROJECT/prompts"
assert_symlink_target "templates points to project" "$SKILL_DIR/templates" "$FAKE_PROJECT/templates"

# Verify symlinks resolve to real content
assert_file_exists "SKILL.md readable through symlink" "$SKILL_DIR/SKILL.md"

# =============================================
echo "=== install.sh — replaces whole-directory symlink ==="
# =============================================

FAKE_PROJECT2="$TMPDIR/project2"
setup_fake_project "$FAKE_PROJECT2"
SKILL_DIR2="$TMPDIR/home2/.claude/skills/tech-essay-writer"
mkdir -p "$TMPDIR/home2/.claude/skills"

# Create a whole-directory symlink (old install method)
ln -s "$FAKE_PROJECT2" "$SKILL_DIR2"
assert_symlink "precondition: whole-dir symlink exists" "$SKILL_DIR2"

out=$(HOME="$TMPDIR/home2" bash "$FAKE_PROJECT2/scripts/install.sh" 2>&1)
assert_contains "install mentions removing existing symlink" "Removing existing symlink" "$out"
assert_dir_exists "skill dir is now a real directory" "$SKILL_DIR2"

# Verify it's NOT a symlink (it's a real directory)
if [ -L "$SKILL_DIR2" ]; then
  FAIL=$((FAIL + 1))
  echo "FAIL: skill dir should be real directory, not symlink"
else
  PASS=$((PASS + 1))
fi

assert_symlink "SKILL.md symlink created after replacing" "$SKILL_DIR2/SKILL.md"

# =============================================
echo "=== install.sh — idempotent reinstall ==="
# =============================================

# Run install again on project1 — should succeed and update symlinks
out=$(run_install "$FAKE_PROJECT")
assert_contains "reinstall prints success" "Installed" "$out"
assert_symlink "SKILL.md still symlink after reinstall" "$SKILL_DIR/SKILL.md"
assert_symlink_target "SKILL.md target correct after reinstall" "$SKILL_DIR/SKILL.md" "$FAKE_PROJECT/SKILL.md"

# =============================================
echo "=== install.sh --uninstall ==="
# =============================================

out=$(run_install "$FAKE_PROJECT" --uninstall)
assert_contains "uninstall prints success" "Uninstalled" "$out"
assert_not_exists "SKILL.md removed" "$SKILL_DIR/SKILL.md"
assert_not_exists "scripts removed" "$SKILL_DIR/scripts"
assert_not_exists "prompts removed" "$SKILL_DIR/prompts"
assert_not_exists "templates removed" "$SKILL_DIR/templates"
assert_not_exists "skill directory removed" "$SKILL_DIR"

# =============================================
echo "=== install.sh --uninstall — removes whole-directory symlink ==="
# =============================================

SKILL_DIR3="$TMPDIR/home3/.claude/skills/tech-essay-writer"
mkdir -p "$TMPDIR/home3/.claude/skills"
ln -s "$FAKE_PROJECT" "$SKILL_DIR3"

out=$(HOME="$TMPDIR/home3" bash "$FAKE_PROJECT/scripts/install.sh" --uninstall 2>&1)
assert_contains "uninstall removes whole-dir symlink" "Removed symlink" "$out"
assert_not_exists "whole-dir symlink gone" "$SKILL_DIR3"

# =============================================
echo "=== install.sh --uninstall — noop when nothing installed ==="
# =============================================

SKILL_DIR4="$TMPDIR/home4/.claude/skills/tech-essay-writer"
mkdir -p "$TMPDIR/home4/.claude/skills"

out=$(HOME="$TMPDIR/home4" bash "$FAKE_PROJECT/scripts/install.sh" --uninstall 2>&1)
assert_contains "uninstall noop message" "Nothing to uninstall" "$out"

# =============================================
echo "=== install.sh — unknown option ==="
# =============================================

if HOME="$TMPDIR/home" bash "$FAKE_PROJECT/scripts/install.sh" --bogus 2>/dev/null; then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject unknown option"
else
  PASS=$((PASS + 1))
fi

# =============================================
echo "=== install.sh --help ==="
# =============================================

out=$(run_install "$FAKE_PROJECT" --help)
assert_contains "help shows usage" "Usage" "$out"
assert_contains "help mentions uninstall" "uninstall" "$out"

# =============================================
echo "=== install.sh — missing component gracefully skipped ==="
# =============================================

FAKE_PROJECT3="$TMPDIR/project3"
setup_fake_project "$FAKE_PROJECT3"
# Remove templates dir to test warning
rm -rf "$FAKE_PROJECT3/templates"

SKILL_DIR5="$TMPDIR/home5/.claude/skills/tech-essay-writer"
mkdir -p "$TMPDIR/home5/.claude/skills"

out=$(HOME="$TMPDIR/home5" bash "$FAKE_PROJECT3/scripts/install.sh" 2>&1)
assert_contains "warns about missing component" "Warning" "$out"
assert_contains "warns about templates" "templates" "$out"
assert_symlink "SKILL.md still installed" "$SKILL_DIR5/SKILL.md"
assert_not_exists "templates not installed" "$SKILL_DIR5/templates"

# --- Summary ---
echo ""
echo "Pass: $PASS | Fail: $FAIL"
