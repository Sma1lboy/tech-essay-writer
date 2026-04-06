#!/usr/bin/env bash
# Main orchestration engine for the tech-essay-writer pipeline
# Called by the conductor (SKILL.md) to manage pipeline progression
# Usage: orchestrate.sh <project_dir> <skill_dir> <command> [args...]
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: orchestrate.sh <project_dir> <skill_dir> <command> [args...]

Commands:
  status              Show current pipeline status
  next-stage          Determine and output the next stage to execute
  build-intake-summary  Build intake summary for user checkpoint
  build-research-prompt Build research agent prompt
  build-outline-prompts Build 3 parallel outline agent prompts
  build-writer-prompt   Build writer agent prompt
  build-review-prompts  Build 5 parallel review agent prompts
  build-refiner-prompt  Build refiner agent prompt (with round number)
  build-format-prompts  Build internal+external formatter prompts
  check-convergence     Check if refinement loop should continue
EOF
}

PROJECT_DIR="${1:?project_dir required}"
SKILL_DIR="${2:?skill_dir required}"
CMD="${3:?command required}"
shift 3

STATE_DIR="$PROJECT_DIR/.essay-state"

# Helper: read a prompt template and inline context
read_prompt() {
  local template="$1"
  if [ -f "$SKILL_DIR/prompts/$template" ]; then
    cat "$SKILL_DIR/prompts/$template"
  else
    echo "ERROR: Template not found: $template" >&2
    return 1
  fi
}

# Helper: read state file if it exists
read_if_exists() {
  local file="$1"
  if [ -f "$file" ]; then
    cat "$file"
  else
    echo ""
  fi
}

# Helper: find latest draft version
latest_draft() {
  for i in $(seq 10 -1 1); do
    if [ -f "$STATE_DIR/draft-v${i}.md" ]; then
      echo "$STATE_DIR/draft-v${i}.md"
      return
    fi
  done
  echo ""
}

latest_draft_version() {
  for i in $(seq 10 -1 1); do
    if [ -f "$STATE_DIR/draft-v${i}.md" ]; then
      echo "$i"
      return
    fi
  done
  echo "0"
}

cmd_status() {
  if [ ! -f "$STATE_DIR/pipeline-state.json" ]; then
    echo "NOT_INITIALIZED"
    return
  fi
  python3 -c "
import json
with open('$STATE_DIR/pipeline-state.json') as f:
    d = json.load(f)
stage = d.get('stage', 'unknown')
topic = d.get('topic', 'unknown')
draft_v = d.get('draft_version', 0)
ref_round = d.get('refinement_round', 0)
reviews = len(d.get('reviews', {}))
completed = d.get('completed', False)
print(f'Stage: {stage}')
print(f'Topic: {topic}')
print(f'Draft version: {draft_v}')
print(f'Refinement round: {ref_round}/3')
print(f'Reviews: {reviews}/5')
print(f'Completed: {completed}')
"
}

cmd_next_stage() {
  if [ ! -f "$STATE_DIR/pipeline-state.json" ]; then
    echo "intake"
    return
  fi
  python3 -c "
import json, os
with open('$STATE_DIR/pipeline-state.json') as f:
    d = json.load(f)
stage = d.get('stage', 'intake')
state_dir = '$STATE_DIR'

if stage == 'complete':
    print('complete')
elif stage == 'intake':
    # Check if materials exist
    if os.path.exists(f'{state_dir}/materials.json'):
        with open(f'{state_dir}/materials.json') as f:
            m = json.load(f)
        if m.get('source_count', 0) > 0:
            print('research')
        else:
            print('intake')
    else:
        print('intake')
elif stage == 'research':
    if os.path.exists(f'{state_dir}/research-synthesis.json'):
        print('outline')
    else:
        print('research')
elif stage == 'outline':
    # Check if any outline exists
    has_outline = any(os.path.exists(f'{state_dir}/outline-{v}.json') for v in ['A','B','C'])
    if has_outline and d.get('outline_variant'):
        print('draft')
    elif has_outline:
        print('outline_choice')
    else:
        print('outline')
elif stage == 'draft':
    if os.path.exists(f'{state_dir}/draft-v1.md'):
        print('review')
    else:
        print('draft')
elif stage == 'review':
    if d.get('review_panel_complete'):
        print('refinement')
    else:
        print('review')
elif stage == 'refinement':
    ref = d.get('refinement_round', 0)
    if ref >= d.get('max_refinement_rounds', 3):
        print('polish')
    else:
        print('refinement')
elif stage == 'polish':
    if os.path.exists(f'{state_dir}/final-internal.md') and os.path.exists(f'{state_dir}/final-external.md'):
        print('complete')
    else:
        print('polish')
else:
    print(stage)
"
}

cmd_build_intake_summary() {
  local materials
  materials=$(read_if_exists "$STATE_DIR/materials.json")
  if [ -z "$materials" ]; then
    echo "No materials collected yet."
    return
  fi
  python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print(f\"## Materials Summary\")
print(f\"Sources: {d.get('source_count', 0)}\")
for s in d.get('sources', []):
    t = s.get('type', '?')
    if t == 'url':
        print(f\"- URL: {s.get('title', s.get('url', '?'))}\")
    elif t == 'note':
        print(f\"- Note: {s.get('content', '')[:80]}...\")
    elif t == 'file':
        print(f\"- File: {s.get('path', '?')}\")
    elif t == 'code':
        print(f\"- Code: {s.get('language', '?')} snippet\")
if d.get('themes'):
    print(f\"\nThemes: {', '.join(d['themes'])}\")
if d.get('potential_angles'):
    print(f\"Angles: {', '.join(d['potential_angles'])}\")
" "$materials"
}

cmd_build_research_prompt() {
  local materials
  materials=$(read_if_exists "$STATE_DIR/materials.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

  cat << PROMPT_END
$(read_prompt "researcher.md")

## Materials Data

\`\`\`json
${materials:-"{}"}
\`\`\`

## Taste Memory (style preferences from prior articles)

\`\`\`json
${taste:-"{}"}
\`\`\`

## Instructions

1. Analyze all provided materials thoroughly
2. Use WebSearch to check the competitive landscape for this topic
3. Write your complete analysis to \`.essay-state/research-synthesis.json\`
4. Be specific — no generic observations. Ground everything in the actual materials.
PROMPT_END
}

cmd_build_outline_prompts() {
  local variant="${1:?variant A|B|C required}"
  local research
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")
  local materials
  materials=$(read_if_exists "$STATE_DIR/materials.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

  cat << PROMPT_END
$(read_prompt "outliner.md")

## Your Assigned Variant: $variant

Generate outline variant $variant as described in the variant styles above.

## Research Synthesis

\`\`\`json
${research:-"{}"}
\`\`\`

## Raw Materials (for reference)

\`\`\`json
${materials:-"{}"}
\`\`\`

## Taste Memory

\`\`\`json
${taste:-"{}"}
\`\`\`

## Instructions

1. Read the research synthesis carefully — your outline must serve the thesis
2. Generate outline variant $variant following the style guide above
3. Write your outline to \`.essay-state/outline-${variant}.json\`
4. Make the hook SPECIFIC and SURPRISING — not generic
5. Every section needs a clear purpose and transition
PROMPT_END
}

cmd_build_writer_prompt() {
  local chosen_outline="${1:-}"
  local outline_content=""

  if [ -n "$chosen_outline" ] && [ -f "$STATE_DIR/outline-${chosen_outline}.json" ]; then
    outline_content=$(cat "$STATE_DIR/outline-${chosen_outline}.json")
  else
    # Try to find any outline
    for v in A B C; do
      if [ -f "$STATE_DIR/outline-${v}.json" ]; then
        outline_content=$(cat "$STATE_DIR/outline-${v}.json")
        break
      fi
    done
  fi

  local research
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")
  local materials
  materials=$(read_if_exists "$STATE_DIR/materials.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

  cat << PROMPT_END
$(read_prompt "writer.md")

## Chosen Outline

\`\`\`json
${outline_content:-"{}"}
\`\`\`

## Research Synthesis

\`\`\`json
${research:-"{}"}
\`\`\`

## Raw Materials (for code examples and details)

\`\`\`json
${materials:-"{}"}
\`\`\`

## Taste Memory (match this style)

\`\`\`json
${taste:-"{}"}
\`\`\`

## Instructions

1. Write the COMPLETE article following the outline exactly
2. Use real, runnable code examples from the materials
3. Match the tone and voice specified in the outline
4. Hit the target word count (±10%)
5. Output to \`.essay-state/draft-v1.md\`
PROMPT_END
}

cmd_build_review_prompts() {
  local reviewer="${1:?reviewer name required}"
  local draft_path
  draft_path=$(latest_draft)
  local draft_content=""
  if [ -n "$draft_path" ]; then
    draft_content=$(cat "$draft_path")
  fi

  local template_map=(
    "technical:reviewer-technical.md"
    "editor:reviewer-editor.md"
    "adversarial:reviewer-adversarial.md"
    "audience:reviewer-audience.md"
    "seo:reviewer-seo.md"
  )

  local template=""
  for mapping in "${template_map[@]}"; do
    local key="${mapping%%:*}"
    local val="${mapping##*:}"
    if [ "$key" = "$reviewer" ]; then
      template="$val"
      break
    fi
  done

  if [ -z "$template" ]; then
    echo "ERROR: Unknown reviewer: $reviewer" >&2
    return 1
  fi

  local research
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")

  cat << PROMPT_END
$(read_prompt "$template")

## Article Draft to Review

${draft_content:-"(no draft available)"}

## Research Context (for reference only — review the ARTICLE, not this)

\`\`\`json
${research:-"{}"}
\`\`\`

## Instructions

1. Review the article thoroughly according to your role above
2. Be specific — reference exact sections, paragraphs, code blocks
3. Write your review to \`.essay-state/review-${reviewer}.json\`
4. If you can't find real issues, say so — don't manufacture criticism
PROMPT_END
}

cmd_build_refiner_prompt() {
  local round="${1:-1}"
  local draft_path
  draft_path=$(latest_draft)
  local draft_content=""
  if [ -n "$draft_path" ]; then
    draft_content=$(cat "$draft_path")
  fi

  local panel_summary
  panel_summary=$(read_if_exists "$STATE_DIR/review-panel-summary.json")
  local outline=""
  for v in A B C; do
    if [ -f "$STATE_DIR/outline-${v}.json" ]; then
      outline=$(cat "$STATE_DIR/outline-${v}.json")
      break
    fi
  done

  local draft_version
  draft_version=$(latest_draft_version)
  local next_version=$((draft_version + 1))

  cat << PROMPT_END
$(read_prompt "refiner.md")

## Current Draft (v${draft_version})

${draft_content:-"(no draft available)"}

## Review Panel Summary

\`\`\`json
${panel_summary:-"{}"}
\`\`\`

## Original Outline (to prevent scope drift)

\`\`\`json
${outline:-"{}"}
\`\`\`

## Refinement Round: $round / 3

## Instructions

1. Read ALL review feedback in the panel summary
2. Address issues in priority order (critical → major → minor)
3. Write refined draft to \`.essay-state/draft-v${next_version}.md\`
4. Write change log to \`.essay-state/refinement-${round}-changes.json\`
5. Do NOT rewrite sections that weren't flagged
PROMPT_END
}

cmd_build_format_prompts() {
  local format="${1:?format internal|external required}"
  local draft_path
  draft_path=$(latest_draft)
  local draft_content=""
  if [ -n "$draft_path" ]; then
    draft_content=$(cat "$draft_path")
  fi

  local template
  if [ "$format" = "internal" ]; then
    template="formatter-internal.md"
  elif [ "$format" = "external" ]; then
    template="formatter-external.md"
  else
    echo "ERROR: Unknown format: $format" >&2
    return 1
  fi

  local seo_review
  seo_review=$(read_if_exists "$STATE_DIR/review-seo.json")
  local audience_review
  audience_review=$(read_if_exists "$STATE_DIR/review-audience.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

  cat << PROMPT_END
$(read_prompt "$template")

## Refined Draft

${draft_content:-"(no draft available)"}

## SEO Review Data

\`\`\`json
${seo_review:-"{}"}
\`\`\`

## Audience Review Data

\`\`\`json
${audience_review:-"{}"}
\`\`\`

## Taste Memory

\`\`\`json
${taste:-"{}"}
\`\`\`

## Instructions

Write the ${format} version to \`.essay-state/final-${format}.md\`
$([ "$format" = "external" ] && echo "Also write social media package to \`.essay-state/social-package.json\`")
PROMPT_END
}

cmd_check_convergence() {
  local round="${1:-1}"
  local adv_review
  adv_review=$(read_if_exists "$STATE_DIR/review-adversarial.json")

  if [ -z "$adv_review" ]; then
    echo "NO_REVIEW"
    return
  fi

  python3 -c "
import json, sys
review = json.loads(sys.argv[1])
round_num = int(sys.argv[2])
rating = review.get('rating', 'UNKNOWN')

if rating == 'SOLID':
    print('CONVERGED')
elif round_num >= 3:
    print('MAX_ROUNDS')
else:
    # Check if same issues persist
    attacks = review.get('attacks', [])
    devastating = [a for a in attacks if a.get('severity') == 'devastating']
    if len(devastating) == 0:
        print('CONVERGED')
    else:
        print('CONTINUE')
" "$adv_review" "$round"
}

# Main dispatch
case "$CMD" in
  status) cmd_status ;;
  next-stage) cmd_next_stage ;;
  build-intake-summary) cmd_build_intake_summary ;;
  build-research-prompt) cmd_build_research_prompt ;;
  build-outline-prompts) cmd_build_outline_prompts "$@" ;;
  build-writer-prompt) cmd_build_writer_prompt "$@" ;;
  build-review-prompts) cmd_build_review_prompts "$@" ;;
  build-refiner-prompt) cmd_build_refiner_prompt "$@" ;;
  build-format-prompts) cmd_build_format_prompts "$@" ;;
  check-convergence) cmd_check_convergence "$@" ;;
  *) usage; exit 1 ;;
esac
