#!/usr/bin/env bash
# Build agent prompt by inlining a prompt template with context
# Usage: build-agent-prompt.sh <project_dir> <skill_dir> <prompt_template> <output_file> [extra_context...]
set -euo pipefail

PROJECT_DIR="$1"
SKILL_DIR="$2"
TEMPLATE="$3"
OUTPUT="$4"
shift 4
EXTRA_CONTEXT="$*"

STATE_DIR="$PROJECT_DIR/.essay-state"

# Read the template
if [ ! -f "$SKILL_DIR/prompts/$TEMPLATE" ]; then
  echo "ERROR: Template not found: $SKILL_DIR/prompts/$TEMPLATE" >&2
  exit 1
fi

TEMPLATE_CONTENT=$(cat "$SKILL_DIR/prompts/$TEMPLATE")

# Gather context files
MATERIALS=""
if [ -f "$STATE_DIR/materials.json" ]; then
  MATERIALS=$(cat "$STATE_DIR/materials.json")
fi

RESEARCH=""
if [ -f "$STATE_DIR/research-synthesis.json" ]; then
  RESEARCH=$(cat "$STATE_DIR/research-synthesis.json")
fi

OUTLINE=""
for variant in A B C; do
  if [ -f "$STATE_DIR/outline-${variant}.json" ]; then
    OUTLINE="$OUTLINE
--- Outline Variant $variant ---
$(cat "$STATE_DIR/outline-${variant}.json")"
  fi
done

# Find latest draft
LATEST_DRAFT=""
for i in $(seq 10 -1 1); do
  if [ -f "$STATE_DIR/draft-v${i}.md" ]; then
    LATEST_DRAFT=$(cat "$STATE_DIR/draft-v${i}.md")
    break
  fi
done

# Gather review results
REVIEWS=""
for review_file in "$STATE_DIR"/review-*.json; do
  if [ -f "$review_file" ]; then
    REVIEWS="$REVIEWS
--- $(basename "$review_file" .json) ---
$(cat "$review_file")"
  fi
done

# Load taste memory
TASTE=""
if [ -f "$HOME/.tech-essay-writer/taste-memory.json" ]; then
  TASTE=$(cat "$HOME/.tech-essay-writer/taste-memory.json")
fi

# Pipeline state
PIPELINE_STATE=""
if [ -f "$STATE_DIR/pipeline-state.json" ]; then
  PIPELINE_STATE=$(cat "$STATE_DIR/pipeline-state.json")
fi

# Build the full prompt
cat > "$OUTPUT" <<PROMPT_EOF
# Agent Task

Project directory: $PROJECT_DIR
State directory: $STATE_DIR

$TEMPLATE_CONTENT

## Available Context

### Pipeline State
\`\`\`json
${PIPELINE_STATE:-"(not initialized)"}
\`\`\`

### Materials
\`\`\`json
${MATERIALS:-"(none)"}
\`\`\`

### Research Synthesis
\`\`\`json
${RESEARCH:-"(none)"}
\`\`\`

### Outlines
${OUTLINE:-"(none generated yet)"}

### Current Draft
${LATEST_DRAFT:-"(no draft yet)"}

### Review Results
${REVIEWS:-"(no reviews yet)"}

### Taste Memory
\`\`\`json
${TASTE:-"(no taste memory)"}
\`\`\`

${EXTRA_CONTEXT:+"### Extra Context
$EXTRA_CONTEXT"}
PROMPT_EOF

echo "Prompt built: $OUTPUT ($(wc -l < "$OUTPUT") lines)"
