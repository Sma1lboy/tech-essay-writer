#!/usr/bin/env bash
# Install/uninstall tech-essay-writer skill into ~/.claude/skills/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_DIR="${HOME}/.claude/skills/tech-essay-writer"

COMPONENTS=("SKILL.md" "scripts" "prompts" "templates")

usage() {
  echo "Usage: $(basename "$0") [--uninstall]"
  echo ""
  echo "Install:   $(basename "$0")"
  echo "Uninstall: $(basename "$0") --uninstall"
}

do_install() {
  # Remove existing whole-directory symlink if present
  if [ -L "$SKILL_DIR" ]; then
    echo "Removing existing symlink: $SKILL_DIR"
    rm "$SKILL_DIR"
  fi

  # Create skill directory if it doesn't exist
  mkdir -p "$SKILL_DIR"

  # Symlink each component
  for component in "${COMPONENTS[@]}"; do
    local target="$PROJECT_DIR/$component"
    local link="$SKILL_DIR/$component"

    if [ ! -e "$target" ]; then
      echo "Warning: $target does not exist, skipping"
      continue
    fi

    # Remove stale symlink if present
    if [ -L "$link" ]; then
      rm "$link"
    fi

    ln -s "$target" "$link"
    echo "Linked: $link -> $target"
  done

  echo "Installed tech-essay-writer skill to $SKILL_DIR"
}

do_uninstall() {
  if [ ! -d "$SKILL_DIR" ] && [ ! -L "$SKILL_DIR" ]; then
    echo "Nothing to uninstall: $SKILL_DIR does not exist"
    return 0
  fi

  # If it's a whole-directory symlink, just remove it
  if [ -L "$SKILL_DIR" ]; then
    rm "$SKILL_DIR"
    echo "Removed symlink: $SKILL_DIR"
    return 0
  fi

  # Remove individual component symlinks
  for component in "${COMPONENTS[@]}"; do
    local link="$SKILL_DIR/$component"
    if [ -L "$link" ]; then
      rm "$link"
      echo "Removed: $link"
    fi
  done

  # Remove the directory if empty
  if [ -d "$SKILL_DIR" ]; then
    rmdir "$SKILL_DIR" 2>/dev/null && echo "Removed directory: $SKILL_DIR" || echo "Warning: $SKILL_DIR not empty, not removed"
  fi

  echo "Uninstalled tech-essay-writer skill"
}

case "${1:-}" in
  --uninstall)
    do_uninstall
    ;;
  --help|-h)
    usage
    ;;
  "")
    do_install
    ;;
  *)
    echo "Unknown option: $1" >&2
    usage >&2
    exit 1
    ;;
esac
