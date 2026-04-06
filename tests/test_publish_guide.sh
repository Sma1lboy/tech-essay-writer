#!/usr/bin/env bash
# Tests for publish-guide.sh — platform publishing instructions
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

# === usage tests ===

echo "=== publish-guide.sh usage ==="

# 1. No arguments shows usage
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" 2>&1 || true)
assert_contains "no args shows usage" "Usage" "$out"

# 2. Help flag shows usage
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" --help 2>&1 || true)
assert_contains "help flag shows usage" "Usage" "$out"

# 3. Unknown platform exits with error
if out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" fakePlatform 2>&1); then
  FAIL=$((FAIL + 1)); echo "FAIL: should reject unknown platform"
else
  PASS=$((PASS + 1))
  assert_contains "unknown platform error message" "Unknown platform" "$out"
fi

# === list command ===

echo "=== publish-guide.sh list ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" list)

# 4. List shows all five platforms
assert_contains "list shows medium" "medium" "$out"

# 5.
assert_contains "list shows devto" "devto" "$out"

# 6.
assert_contains "list shows hashnode" "hashnode" "$out"

# 7.
assert_contains "list shows wechat" "wechat" "$out"

# 8.
assert_contains "list shows juejin" "juejin" "$out"

# 9. List shows URLs
assert_contains "list shows medium URL" "medium.com" "$out"

# === medium guide ===

echo "=== publish-guide.sh medium ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" medium)

# 10. Medium guide has platform name and URL
assert_contains "medium has platform header" "MEDIUM" "$out"
assert_contains "medium has URL" "medium.com" "$out"

# 11. Medium pre-publish checklist includes image requirements
assert_contains "medium has image dimensions" "1500x750" "$out"

# 12. Medium mentions frontmatter fields
assert_contains "medium mentions subtitle" "Subtitle" "$out"

# 13. Medium has step-by-step instructions
assert_contains "medium has publishing steps" "STEP-BY-STEP" "$out"

# 14. Medium has SEO tips
assert_contains "medium has SEO section" "SEO TIPS" "$out"

# 15. Medium has post-publish checklist
assert_contains "medium has post-publish" "POST-PUBLISH" "$out"

# 16. Medium mentions Gist for long code blocks
assert_contains "medium mentions Gist" "Gist" "$out"

# === devto guide ===

echo "=== publish-guide.sh devto ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" devto)

# 17. devto has liquid tags section
assert_contains "devto mentions liquid tags" "Liquid" "$out"

# 18. devto mentions YAML frontmatter
assert_contains "devto mentions frontmatter" "Frontmatter" "$out"

# 19. devto cover image dimensions
assert_contains "devto cover image size" "1000x420" "$out"

# 20. devto mentions canonical_url
assert_contains "devto mentions canonical" "canonical" "$out"

# === hashnode guide ===

echo "=== publish-guide.sh hashnode ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" hashnode)

# 21. Hashnode has ToC mention
assert_contains "hashnode mentions ToC" "Table of Contents" "$out"

# 22. Hashnode cover image dimensions
assert_contains "hashnode cover image size" "1600x840" "$out"

# 23. Hashnode mentions series support
assert_contains "hashnode mentions series" "series" "$out"

# 24. Hashnode mentions newsletter
assert_contains "hashnode mentions newsletter" "newsletter" "$out"

# === wechat guide ===

echo "=== publish-guide.sh wechat ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" wechat)

# 25. WeChat mentions no external links
assert_contains "wechat warns about external links" "external" "$out"

# 26. WeChat mentions CDN requirement
assert_contains "wechat mentions CDN" "CDN" "$out"

# 27. WeChat mentions inline CSS
assert_contains "wechat mentions inline CSS" "inline CSS" "$out"

# 28. WeChat mentions QR code
assert_contains "wechat mentions QR code" "QR" "$out"

# 29. WeChat mentions Chinese content requirement
assert_contains "wechat requires Chinese" "Chinese" "$out"

# 30. WeChat mentions 阅读原文
assert_contains "wechat mentions Read Original link" "阅读原文" "$out"

# === juejin guide ===

echo "=== publish-guide.sh juejin ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" juejin)

# 31. Juejin mentions category selection
assert_contains "juejin mentions categories" "分类" "$out"

# 32. Juejin cover image dimensions
assert_contains "juejin cover image size" "800x450" "$out"

# 33. Juejin mentions column support
assert_contains "juejin mentions column" "专栏" "$out"

# 34. Juejin mentions Chinese content
assert_contains "juejin requires Chinese" "Chinese" "$out"

# 35. Juejin mentions summary section
assert_contains "juejin mentions summary" "总结" "$out"

# === all command ===

echo "=== publish-guide.sh all ==="

out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" all)

# 36. All command includes all platforms
assert_contains "all includes MEDIUM" "MEDIUM" "$out"
assert_contains "all includes DEV.TO" "DEV.TO" "$out"
assert_contains "all includes HASHNODE" "HASHNODE" "$out"
assert_contains "all includes WECHAT" "WECHAT" "$out"
assert_contains "all includes JUEJIN" "JUEJIN" "$out"

# === project_dir integration ===

echo "=== publish-guide.sh project_dir integration ==="

# Set up a fake project with some formatted drafts
PROJECT="$TMPDIR/test-project"
mkdir -p "$PROJECT/.essay-state"
echo "# Test Medium Draft" > "$PROJECT/.essay-state/final-medium.md"
echo "# Test Hashnode Draft" > "$PROJECT/.essay-state/final-hashnode.md"

# 37. Medium guide shows note when draft exists
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" medium "$PROJECT")
assert_contains "medium shows draft note" "final-medium.md" "$out"

# 38. Hashnode guide shows note when draft exists
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" hashnode "$PROJECT")
assert_contains "hashnode shows draft note" "final-hashnode.md" "$out"

# 39. devto guide does NOT show note when draft missing
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" devto "$PROJECT")
assert_not_contains "devto no draft note when missing" "final-devto.md" "$out"

# 40. All command with project_dir shows existing drafts
out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" all "$PROJECT")
assert_contains "all with project shows medium draft" "final-medium.md" "$out"
assert_contains "all with project shows hashnode draft" "final-hashnode.md" "$out"
assert_not_contains "all with project no devto draft" "final-devto.md" "$out"

# === structure tests ===

echo "=== publish-guide.sh structure ==="

# 41. Every platform guide has all 5 required sections
for platform in medium devto hashnode wechat juejin; do
  out=$(bash "$SCRIPT_DIR/scripts/publish-guide.sh" "$platform")
  assert_contains "$platform has PRE-PUBLISH" "PRE-PUBLISH" "$out"
  assert_contains "$platform has STEP-BY-STEP" "STEP-BY-STEP" "$out"
  assert_contains "$platform has SEO TIPS" "SEO TIPS" "$out"
  assert_contains "$platform has POST-PUBLISH" "POST-PUBLISH" "$out"
done

# --- Results ---
echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
