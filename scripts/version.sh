#!/usr/bin/env bash
# Version tracking for tech-essay-writer
# Reads VERSION file, displays version, supports bump (major/minor/patch)
# Usage: version.sh [show|bump <major|minor|patch>]
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$SKILL_DIR/VERSION"

usage() {
  cat <<'EOF'
Usage: version.sh [command]

Commands:
  show                  Display current version (default)
  bump <major|minor|patch>  Bump the version number
  raw                   Output version string only (no label)

Examples:
  bash scripts/version.sh              # Show version
  bash scripts/version.sh show         # Show version
  bash scripts/version.sh bump patch   # 1.0.0 -> 1.0.1
  bash scripts/version.sh bump minor   # 1.0.0 -> 1.1.0
  bash scripts/version.sh bump major   # 1.0.0 -> 2.0.0
EOF
}

ensure_version_file() {
  if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
  fi
}

read_version() {
  ensure_version_file
  # Read first line, strip whitespace
  head -1 "$VERSION_FILE" | tr -d '[:space:]'
}

parse_version() {
  local ver="$1"
  # Validate format: N.N.N
  if ! echo "$ver" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: Invalid version format '$ver' (expected N.N.N)" >&2
    return 1
  fi
  MAJOR=$(echo "$ver" | cut -d. -f1)
  MINOR=$(echo "$ver" | cut -d. -f2)
  PATCH=$(echo "$ver" | cut -d. -f3)
}

cmd_show() {
  local ver
  ver=$(read_version)
  echo "tech-essay-writer v${ver}"
}

cmd_raw() {
  read_version
}

cmd_bump() {
  local component="${1:-}"
  if [ -z "$component" ]; then
    echo "ERROR: specify major, minor, or patch" >&2
    usage >&2
    return 1
  fi

  local old_ver
  old_ver=$(read_version)
  parse_version "$old_ver"

  case "$component" in
    major)
      MAJOR=$((MAJOR + 1))
      MINOR=0
      PATCH=0
      ;;
    minor)
      MINOR=$((MINOR + 1))
      PATCH=0
      ;;
    patch)
      PATCH=$((PATCH + 1))
      ;;
    *)
      echo "ERROR: unknown component '$component' (use major, minor, or patch)" >&2
      return 1
      ;;
  esac

  local new_ver="${MAJOR}.${MINOR}.${PATCH}"

  # Atomic write
  local tmp_file="${VERSION_FILE}.tmp.$$"
  echo "$new_ver" > "$tmp_file"
  mv "$tmp_file" "$VERSION_FILE"

  echo "${old_ver} -> ${new_ver}"
}

# Main dispatch
CMD="${1:-show}"
shift || true

case "$CMD" in
  show) cmd_show ;;
  raw) cmd_raw ;;
  bump) cmd_bump "${1:-}" ;;
  --help|-h|help) usage ;;
  *) echo "ERROR: unknown command '$CMD'" >&2; usage >&2; exit 1 ;;
esac
