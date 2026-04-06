#!/usr/bin/env bash
# Usage reference for all tech-essay-writer scripts
# Usage: bash scripts/help.sh [command]
# Without args: list all scripts with one-line descriptions
# With command: show detailed help for that script
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$SKILL_DIR/scripts"

get_description() {
  # Returns one-line description for a script name (without .sh)
  local name="$1"
  python3 -c "
descs = {
    'aggregate-reviews': 'Aggregate 7 review JSON files into panel summary with consensus',
    'analytics-feedback': 'Analytics feedback loop: record, track, query, trends, feed-taste',
    'article-compare': 'Side-by-side draft comparison: word count, structure, reading level',
    'author-profile': 'Author identity management: name, bio, social handles, expertise',
    'calibrate-reviews': 'Post-aggregate calibration: normalize scores, detect outliers',
    'checkpoint': 'State checkpoint and recovery: snapshot, list, rollback, clean',
    'code-validate': 'Code example validator: syntax checking, imports, fragment detection',
    'config': 'User configuration management: language, style, platforms, audiences',
    'cross-reference': 'Published article registry for internal linking',
    'detect-input': 'Classify user input into URLs, code blocks, file paths, notes',
    'diagram-suggest': 'Diagram/image suggestion engine with Mermaid syntax output',
    'dry-run': 'Full pipeline simulation with mock data (no LLM agents)',
    'expertise-graph': 'Topic authority tracking with recency-weighted scoring',
    'export': 'Export and archive: bundle, markdown, html, json, archive formats',
    'fetch-urls': 'URL content fetcher for materials intake',
    'help': 'Show this help listing, or detailed help for a specific command',
    'hook-workshop': 'Opening hook generator and scorer (5 styles)',
    'influence-score': 'Influence potential predictor: novelty, SEO, social, audience',
    'install': 'Skill installer/uninstaller (symlink to ~/.claude/skills/)',
    'intake-materials': 'Material intake: add-url, add-note, add-file, add-code, add-theme',
    'metrics-dashboard': 'Comprehensive metrics dashboard: health, quality, growth',
    'orchestrate': 'Pipeline orchestrator: 27 commands for prompt building, stage control',
    'outline-mixer': 'Outline variant mixer: combine elements from multiple outlines',
    'pipeline-state': 'Pipeline state CRUD with atomic writes',
    'progress-display': 'Rich pipeline progress visualization with quality dashboard',
    'publish-check': 'Pre-publish readiness checklist across multiple dimensions',
    'publishing-guide': 'Per-platform publishing workflow guides with SEO tips',
    'quality-score': 'Composite 0-10 quality score from weighted review dimensions',
    'readability-score': 'Readability analysis: Flesch-Kincaid, passive voice, complexity',
    'seo-metadata': 'SEO metadata generator: OpenGraph, meta tags, JSON-LD',
    'series-manager': 'Article series manager: create, add, list, show, reorder',
    'summary': 'Quick project status and capability overview',
    'taste-memory': 'Persistent writing style preferences and learned patterns',
    'title-generator': 'Title variation generator with scoring',
    'topic-research': 'Research question generator, competitive landscape, unique angles',
    'update-material': 'Update a specific material source with fetched content',
    'version': 'Show or bump the project version (major/minor/patch)',
    'word-frequency': 'Word frequency analysis: top-N, overused words, jargon, AI patterns',
}
import sys
name = sys.argv[1]
print(descs.get(name, ''))
" "$name"
}

list_all() {
  local ver=""
  if [ -f "$SKILL_DIR/scripts/version.sh" ]; then
    ver=$(bash "$SKILL_DIR/scripts/version.sh" raw 2>/dev/null || echo "?")
  fi

  echo "tech-essay-writer v${ver} -- Script Reference"
  echo "============================================="
  echo ""
  echo "Usage: bash scripts/help.sh [command]"
  echo ""

  # Collect all scripts and find max name length
  local max_len=0
  local names=()
  for f in "$SCRIPTS_DIR"/*.sh; do
    local name
    name=$(basename "$f" .sh)
    names+=("$name")
    local len=${#name}
    if [ "$len" -gt "$max_len" ]; then
      max_len=$len
    fi
  done

  # Sort and display
  local count=0
  for name in $(printf '%s\n' "${names[@]}" | sort); do
    local desc
    desc=$(get_description "$name")
    if [ -z "$desc" ]; then
      # Fallback: extract from file's second line comment
      desc=$(sed -n '2s/^# *//p' "$SCRIPTS_DIR/${name}.sh" 2>/dev/null || echo "")
    fi
    printf "  %-${max_len}s  %s\n" "$name" "$desc"
    count=$((count + 1))
  done

  echo ""
  echo "${count} scripts available."
  echo ""
  echo "For detailed help: bash scripts/help.sh <command>"
}

show_help() {
  local cmd="$1"

  # Strip .sh if user appended it
  cmd="${cmd%.sh}"

  local script_path="$SCRIPTS_DIR/${cmd}.sh"

  if [ ! -f "$script_path" ]; then
    echo "ERROR: Unknown command '$cmd'" >&2
    echo "" >&2
    echo "Available commands:" >&2
    for f in "$SCRIPTS_DIR"/*.sh; do
      echo "  $(basename "$f" .sh)" >&2
    done
    return 1
  fi

  echo "=== $cmd ==="
  echo ""

  # Extract the usage comment block (lines starting with # at the top of the file)
  while IFS= read -r line; do
    # Skip shebang
    if [[ "$line" == "#!/"* ]]; then
      continue
    fi
    # Stop at first non-comment, non-empty line
    if [[ "$line" != "#"* ]] && [[ "$line" != "" ]]; then
      break
    fi
    # Stop at set -euo pipefail
    if [[ "$line" == "set "* ]]; then
      break
    fi
    # Print comment lines (strip leading "# ")
    if [[ "$line" == "#"* ]]; then
      # Remove leading "# " or just "#"
      local stripped="${line#\# }"
      if [ "$stripped" = "#" ]; then
        stripped=""
      fi
      echo "$stripped"
    fi
  done < "$script_path"

  echo ""

  # If script has a usage() function, try to extract its content
  if grep -q "^usage()" "$script_path" 2>/dev/null; then
    echo "--- Detailed Usage ---"
    echo ""
    # Run the script with --help to get usage output
    local usage_output=""
    usage_output=$(bash "$script_path" --help 2>&1) || \
    usage_output=$(bash "$script_path" -h 2>&1) || \
    usage_output=$(bash "$script_path" 2>&1) || true

    if [ -n "$usage_output" ]; then
      echo "$usage_output"
    fi
  fi
}

# Main dispatch
CMD="${1:-}"

if [ -z "$CMD" ]; then
  list_all
elif [ "$CMD" = "--help" ] || [ "$CMD" = "-h" ]; then
  echo "Usage: bash scripts/help.sh [command]"
  echo ""
  echo "Without arguments: list all available scripts"
  echo "With a command name: show detailed help for that script"
else
  show_help "$CMD"
fi
