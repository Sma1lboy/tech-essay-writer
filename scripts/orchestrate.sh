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
  build-outline-critique-prompt  Build outline adversarial critique prompt
  build-writer-prompt   Build writer agent prompt
  build-review-prompts  Build 7 parallel review agent prompts
  build-refiner-prompt  Build refiner agent prompt (with round number)
  build-format-prompts  Build formatter prompts (internal|external|medium|devto|hashnode|wechat|juejin)
  build-social-prompt   Build social media package agent prompt
  build-calibration-summary  Build human-readable calibration summary
  build-influence-score Compute influence score from state data (no agent needed)
  build-seo-metadata    Generate SEO metadata from article + state data (no agent needed)
  build-code-validation Validate code examples in the latest draft
  build-diagram-suggestions Suggest diagrams/images for the latest draft
  build-readability-report  Compute readability metrics (FK grade, passive voice, complexity)
  build-word-analysis       Word frequency, overuse, jargon density, AI pattern detection
  build-series-context  Build series context for injection into writer/formatter prompts
  build-analytics-insights Output performance insights from analytics for prompt injection
  build-analytics-summary Show performance trends and analytics summary
  build-config-summary  Build config context summary for prompt injection
  list-platforms        List all available platform format names
  check-convergence     Check if refinement loop should continue
  show-progress         Show rich pipeline progress visualization
  publishing-guide      Show per-platform publishing workflow guide
  list-checkpoints      List all saved state checkpoints
  rollback <id>         Restore state from a checkpoint
  retry-stage <stage>   Reset and retry a failed stage
  resume                Detect partial state and advise next action
EOF
}

PROJECT_DIR="${1:?project_dir required}"
SKILL_DIR="${2:?skill_dir required}"
CMD="${3:?command required}"
shift 3

STATE_DIR="$PROJECT_DIR/.essay-state"

# ─── Caching layer ───────────────────────────────────────────────────────────
# Frequently-read files are cached in shell variables on first access.
# This avoids re-reading the same file (and re-spawning python3) across
# multiple helper calls within a single orchestrate.sh invocation.

_CACHE_TASTE=""
_CACHE_TASTE_LOADED=false

_CACHE_LANG=""
_CACHE_LANG_LOADED=false

_CACHE_SERIES_ID=""
_CACHE_SERIES_ID_LOADED=false

_CACHE_SERIES_CTX=""
_CACHE_SERIES_CTX_LOADED=false

_CACHE_RESEARCH=""
_CACHE_RESEARCH_LOADED=false

_CACHE_MATERIALS=""
_CACHE_MATERIALS_LOADED=false

_CACHE_PIPELINE_TOPIC=""
_CACHE_PIPELINE_TOPIC_LOADED=false

# Cached taste memory reader — avoids re-reading ~/.tech-essay-writer/taste-memory.json
cached_taste_memory() {
  if [ "$_CACHE_TASTE_LOADED" = false ]; then
    _CACHE_TASTE=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")
    _CACHE_TASTE_LOADED=true
  fi
  echo "$_CACHE_TASTE"
}

# Cached language from pipeline state — avoids re-spawning python3 for every prompt
cached_language() {
  if [ "$_CACHE_LANG_LOADED" = false ]; then
    _CACHE_LANG="en"
    if [ -f "$STATE_DIR/pipeline-state.json" ]; then
      _CACHE_LANG=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('language','en'))" "$STATE_DIR/pipeline-state.json" 2>/dev/null || echo "en")
    fi
    _CACHE_LANG_LOADED=true
  fi
  echo "$_CACHE_LANG"
}

# Cached series_id from pipeline state
cached_series_id() {
  if [ "$_CACHE_SERIES_ID_LOADED" = false ]; then
    _CACHE_SERIES_ID=""
    if [ -f "$STATE_DIR/pipeline-state.json" ]; then
      _CACHE_SERIES_ID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('series_id','') or '')" "$STATE_DIR/pipeline-state.json" 2>/dev/null || echo "")
    fi
    _CACHE_SERIES_ID_LOADED=true
  fi
  echo "$_CACHE_SERIES_ID"
}

# Cached series context (calls series-manager.sh at most once)
cached_series_context() {
  if [ "$_CACHE_SERIES_CTX_LOADED" = false ]; then
    local sid
    sid=$(cached_series_id)
    if [ -n "$sid" ]; then
      _CACHE_SERIES_CTX=$(bash "$SKILL_DIR/scripts/series-manager.sh" context "$sid" 2>/dev/null || echo "")
    fi
    _CACHE_SERIES_CTX_LOADED=true
  fi
  echo "$_CACHE_SERIES_CTX"
}

# Cached research synthesis reader
cached_research() {
  if [ "$_CACHE_RESEARCH_LOADED" = false ]; then
    _CACHE_RESEARCH=$(read_if_exists "$STATE_DIR/research-synthesis.json")
    _CACHE_RESEARCH_LOADED=true
  fi
  echo "$_CACHE_RESEARCH"
}

# Cached materials reader
cached_materials() {
  if [ "$_CACHE_MATERIALS_LOADED" = false ]; then
    _CACHE_MATERIALS=$(read_if_exists "$STATE_DIR/materials.json")
    _CACHE_MATERIALS_LOADED=true
  fi
  echo "$_CACHE_MATERIALS"
}

# Cached pipeline topic
cached_pipeline_topic() {
  if [ "$_CACHE_PIPELINE_TOPIC_LOADED" = false ]; then
    _CACHE_PIPELINE_TOPIC=""
    if [ -f "$STATE_DIR/pipeline-state.json" ]; then
      _CACHE_PIPELINE_TOPIC=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('topic',''))" "$STATE_DIR/pipeline-state.json" 2>/dev/null || echo "")
    fi
    _CACHE_PIPELINE_TOPIC_LOADED=true
  fi
  echo "$_CACHE_PIPELINE_TOPIC"
}

# ─── Core helpers ────────────────────────────────────────────────────────────

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

# Helper: build language directive from pipeline state (cached)
build_language_directive() {
  local lang
  lang=$(cached_language)
  if [ "$lang" = "zh" ]; then
    cat <<'LANG_END'

## Language Directive

Write all output (article text, analysis, suggestions) in Chinese (中文). Technical terms, code, and JSON keys should remain in English. Article prose, section titles, hooks, transitions, and all reader-facing text must be in Chinese.
LANG_END
  else
    cat <<'LANG_END'

## Language Directive

Write all output (article text, analysis, suggestions) in English.
LANG_END
  fi
}

# Helper: get series context section if series_id is set in pipeline state (cached)
get_series_context_section() {
  local ctx
  ctx=$(cached_series_context)
  if [ -n "$ctx" ]; then
    cat << SERIES_END

## Series Context

This article is part of a series. Consider the series arc and previous articles when writing.

\`\`\`json
${ctx}
\`\`\`
SERIES_END
  fi
}

# Helper: get series navigation for formatter prompts (cached)
get_series_nav_section() {
  local ctx
  ctx=$(cached_series_context)
  if [ -n "$ctx" ]; then
    cat << NAV_END

## Series Navigation

Include series navigation links (previous/next article) where the format supports it.

\`\`\`json
${ctx}
\`\`\`
NAV_END
  fi
}

cmd_status() {
  if [ ! -f "$STATE_DIR/pipeline-state.json" ]; then
    echo "NOT_INITIALIZED"
    return
  fi
  python3 -c "
import json, sys
with open(sys.argv[1]) as f:
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
print(f'Reviews: {reviews}/7')
print(f'Completed: {completed}')
" "$STATE_DIR/pipeline-state.json"
}

cmd_next_stage() {
  if [ ! -f "$STATE_DIR/pipeline-state.json" ]; then
    echo "intake"
    return
  fi
  python3 -c "
import json, os, sys
state_dir = sys.argv[1]
with open(os.path.join(state_dir, 'pipeline-state.json')) as f:
    d = json.load(f)
stage = d.get('stage', 'intake')

if stage == 'complete':
    print('complete')
elif stage == 'intake':
    # Check if materials exist
    if os.path.exists(os.path.join(state_dir, 'materials.json')):
        with open(os.path.join(state_dir, 'materials.json')) as f:
            m = json.load(f)
        if m.get('source_count', 0) > 0:
            print('research')
        else:
            print('intake')
    else:
        print('intake')
elif stage == 'research':
    if os.path.exists(os.path.join(state_dir, 'research-synthesis.json')):
        print('outline')
    else:
        print('research')
elif stage == 'outline':
    # Check if any outline exists
    has_outline = any(os.path.exists(os.path.join(state_dir, f'outline-{v}.json')) for v in ['A','B','C'])
    has_critique = os.path.exists(os.path.join(state_dir, 'outline-critique.json'))
    if has_outline and d.get('outline_variant'):
        print('draft')
    elif has_outline and has_critique:
        print('outline_choice')
    elif has_outline:
        print('outline_critique')
    else:
        print('outline')
elif stage == 'draft':
    if os.path.exists(os.path.join(state_dir, 'draft-v1.md')):
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
    if os.path.exists(os.path.join(state_dir, 'final-internal.md')) and os.path.exists(os.path.join(state_dir, 'final-external.md')):
        print('complete')
    else:
        print('polish')
else:
    print(stage)
" "$STATE_DIR"
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
  materials=$(cached_materials)
  local taste
  taste=$(cached_taste_memory)

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
$(build_language_directive)

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
  research=$(cached_research)
  local materials
  materials=$(cached_materials)
  local taste
  taste=$(cached_taste_memory)

  # Map variant to article template
  local template_name=""
  case "$variant" in
    A) template_name="tutorial.md" ;;
    B) template_name="deep-dive.md" ;;
    C) template_name="narrative.md" ;;
  esac
  local template_content=""
  if [ -n "$template_name" ] && [ -f "$SKILL_DIR/templates/$template_name" ]; then
    template_content=$(cat "$SKILL_DIR/templates/$template_name")
  fi

  cat << PROMPT_END
$(read_prompt "outliner.md")

## Your Assigned Variant: $variant

Generate outline variant $variant as described in the variant styles above.

## Article Type Template Reference

${template_content:-"(no template available)"}

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
$(get_series_context_section)
$(build_language_directive)

## Instructions

1. Read the research synthesis carefully — your outline must serve the thesis
2. Generate outline variant $variant following the style guide above
3. Write your outline to \`.essay-state/outline-${variant}.json\`
4. Make the hook SPECIFIC and SURPRISING — not generic
5. Every section needs a clear purpose and transition
PROMPT_END
}

cmd_build_outline_critique_prompt() {
  local outline_a outline_b outline_c
  outline_a=$(read_if_exists "$STATE_DIR/outline-A.json")
  outline_b=$(read_if_exists "$STATE_DIR/outline-B.json")
  outline_c=$(read_if_exists "$STATE_DIR/outline-C.json")
  local research
  research=$(cached_research)
  local taste
  taste=$(cached_taste_memory)

  cat << PROMPT_END
$(read_prompt "outline-critic.md")

## Outline A

\`\`\`json
${outline_a:-"{}"}
\`\`\`

## Outline B

\`\`\`json
${outline_b:-"{}"}
\`\`\`

## Outline C

\`\`\`json
${outline_c:-"{}"}
\`\`\`

## Research Synthesis

\`\`\`json
${research:-"{}"}
\`\`\`

## Taste Memory

\`\`\`json
${taste:-"{}"}
\`\`\`
$(build_language_directive)

## Instructions

1. Read all 3 outlines and the research synthesis carefully
2. Analyze each outline for structural strengths and weaknesses
3. Compare the outlines across all dimensions
4. Write your critique to \`.essay-state/outline-critique.json\`
5. Be specific — reference exact section names, not vague observations
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
  research=$(cached_research)
  local materials
  materials=$(cached_materials)
  local taste
  taste=$(cached_taste_memory)

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
$(get_series_context_section)
$(build_language_directive)

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
    "external:reviewer-external.md"
    "factcheck:reviewer-factcheck.md"
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
  research=$(cached_research)

  cat << PROMPT_END
$(read_prompt "$template")

## Article Draft to Review

${draft_content:-"(no draft available)"}

## Research Context (for reference only — review the ARTICLE, not this)

\`\`\`json
${research:-"{}"}
\`\`\`
$(build_language_directive)

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
$(build_language_directive)

## Instructions

1. Read ALL review feedback in the panel summary
2. Address issues in priority order (critical → major → minor)
3. Write refined draft to \`.essay-state/draft-v${next_version}.md\`
4. Write change log to \`.essay-state/refinement-${round}-changes.json\`
5. Do NOT rewrite sections that weren't flagged
PROMPT_END
}

cmd_list_platforms() {
  echo "internal"
  echo "external"
  echo "medium"
  echo "devto"
  echo "hashnode"
  echo "wechat"
  echo "juejin"
}

cmd_build_format_prompts() {
  local format="${1:?format internal|external|medium|devto|hashnode|wechat|juejin required}"
  local draft_path
  draft_path=$(latest_draft)
  local draft_content=""
  if [ -n "$draft_path" ]; then
    draft_content=$(cat "$draft_path")
  fi

  local template
  case "$format" in
    internal)  template="formatter-internal.md" ;;
    external)  template="formatter-external.md" ;;
    medium)    template="formatter-medium.md" ;;
    devto)     template="formatter-devto.md" ;;
    hashnode)   template="formatter-hashnode.md" ;;
    wechat)    template="formatter-wechat.md" ;;
    juejin)    template="formatter-juejin.md" ;;
    *)
      echo "ERROR: Unknown format: $format" >&2
      return 1
      ;;
  esac

  local seo_review
  seo_review=$(read_if_exists "$STATE_DIR/review-seo.json")
  local audience_review
  audience_review=$(read_if_exists "$STATE_DIR/review-audience.json")
  local taste
  taste=$(cached_taste_memory)

  # Get author profile data
  local author_profile
  author_profile=$(bash "$SKILL_DIR/scripts/author-profile.sh" read 2>/dev/null || echo "")
  local author_bio
  author_bio=$(bash "$SKILL_DIR/scripts/author-profile.sh" get-bio 2>/dev/null || echo "")

  # Get cross-references for the topic
  local xrefs=""
  local topic
  topic=$(cached_pipeline_topic)
  if [ -n "$topic" ] && [ -f "$HOME/.tech-essay-writer/published-articles.json" ]; then
    xrefs=$(bash "$SKILL_DIR/scripts/cross-reference.sh" suggest "$topic" 2>/dev/null || echo "")
  fi

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

## Author Profile

${author_profile:-"(no author profile configured)"}

Author bio line: ${author_bio:-"(not set)"}

## Previously Published Articles (for cross-referencing)

${xrefs:-"(no published articles to cross-reference)"}
$(get_series_nav_section)
$(build_language_directive)

## Instructions

Write the ${format} version to \`.essay-state/final-${format}.md\`
Where relevant, cross-reference the author's previously published articles listed above.
Include author bio/expertise where the format supports it.
$([ "$format" = "external" ] && echo "Also write social media package to \`.essay-state/social-package.json\`")
PROMPT_END
}

cmd_build_social_prompt() {
  local draft_path
  draft_path=$(latest_draft)
  local draft_content=""
  if [ -n "$draft_path" ]; then
    draft_content=$(cat "$draft_path")
  fi

  # Author profile
  local author_profile_json
  author_profile_json=$(bash "$SKILL_DIR/scripts/author-profile.sh" read 2>/dev/null || echo "(no author profile)")

  # Expertise graph
  local expertise_graph_json
  expertise_graph_json=$(bash "$SKILL_DIR/scripts/expertise-graph.sh" read 2>/dev/null || echo "{}")

  # SEO review
  local seo_review
  seo_review=$(read_if_exists "$STATE_DIR/review-seo.json")

  cat << PROMPT_END
$(read_prompt "social-package.md")

## Refined Draft

${draft_content:-"(no draft available)"}

## Author Profile Data

${author_profile_json}

## Expertise Graph Data

\`\`\`json
${expertise_graph_json}
\`\`\`

## SEO Review Data

\`\`\`json
${seo_review:-"{}"}
\`\`\`
$(build_language_directive)

## Instructions

1. Read the article draft and understand its key points, unique angle, and target audience
2. Generate the complete social media package following the format specification above
3. Use the author profile to write authentic CTAs with correct handles
4. Use the expertise graph to position the author's authority on this topic
5. Write the package to \`.essay-state/social-package.json\`
PROMPT_END
}

cmd_build_calibration_summary() {
  local calibration
  calibration=$(read_if_exists "$STATE_DIR/review-calibration.json")
  if [ -z "$calibration" ]; then
    echo "No calibration data available. Run calibrate-reviews.sh first."
    return
  fi

  python3 -c "
import json, sys
cal = json.loads(sys.argv[1])

print('## Review Panel Calibration Report')
print()

# Panel average
avg = cal.get('panel_average', 0)
agreement = cal.get('agreement_score', 0)
print(f'**Panel Average Score:** {avg}/10')
print(f'**Inter-Reviewer Agreement:** {agreement}/10')
print()

# Normalized scores
print('### Normalized Scores')
for name, data in cal.get('normalized_scores', {}).items():
    orig = data.get('original_rating', '?')
    score = data.get('numeric_score', '?')
    print(f'- {name}: {orig} → {score}/10')
print()

# Outliers
outliers = cal.get('outliers', [])
if outliers:
    print('### Outlier Reviewers')
    for o in outliers:
        print(f'- **{o[\"reviewer\"]}** ({o[\"direction\"]}): scored {o[\"score\"]}/10 vs panel avg {o[\"panel_average\"]}/10')
    print()

# Blind spots
spots = cal.get('blind_spots', [])
if spots:
    print('### Blind Spots (Uncovered Topics)')
    for s in spots:
        print(f'- **{s[\"topic\"]}**: {s[\"description\"]}')
        expected = ', '.join(s['expected_reviewers'])
    print(f'  Expected from: {expected}')
    print()

# Disagreements
disag = cal.get('disagreements', [])
if disag:
    print('### Disagreements')
    for d in disag:
        print(f'- Rating spread: {d[\"spread\"]} points ({d[\"highest\"][\"reviewers\"]} high vs {d[\"lowest\"][\"reviewers\"]} low)')
    print()

# Notes
notes = cal.get('calibration_notes', [])
if notes:
    print('### Calibration Notes')
    for n in notes:
        print(f'- {n}')
" "$calibration"
}

cmd_build_influence_score() {
  local verbose="${1:-}"
  bash "$SKILL_DIR/scripts/influence-score.sh" "$PROJECT_DIR" "$SKILL_DIR" "$verbose"
}

cmd_build_seo_metadata() {
  local verbose="${1:-}"
  bash "$SKILL_DIR/scripts/seo-metadata.sh" "$PROJECT_DIR" "$verbose"
}

cmd_build_code_validation() {
  local draft_path
  draft_path=$(latest_draft)
  if [ -z "$draft_path" ]; then
    # Try final-external, then final-internal
    for f in "$STATE_DIR/final-external.md" "$STATE_DIR/final-internal.md"; do
      if [ -f "$f" ]; then
        draft_path="$f"
        break
      fi
    done
  fi
  if [ -z "$draft_path" ]; then
    echo '{"error":"no draft or final article found to validate"}'
    return 1
  fi
  bash "$SKILL_DIR/scripts/code-validate.sh" "$draft_path"
}

cmd_build_diagram_suggestions() {
  local verbose="${1:-}"
  local draft_path
  draft_path=$(latest_draft)
  if [ -z "$draft_path" ]; then
    # Try final-external, then final-internal
    for f in "$STATE_DIR/final-external.md" "$STATE_DIR/final-internal.md"; do
      if [ -f "$f" ]; then
        draft_path="$f"
        break
      fi
    done
  fi
  if [ -z "$draft_path" ]; then
    echo '{"error":"no draft or final article found for diagram suggestions"}'
    return 1
  fi
  bash "$SKILL_DIR/scripts/diagram-suggest.sh" "$draft_path" "$verbose"
}

cmd_build_readability_report() {
  local verbose="${1:-}"
  local draft_path
  draft_path=$(latest_draft)
  if [ -z "$draft_path" ]; then
    for f in "$STATE_DIR/final-external.md" "$STATE_DIR/final-internal.md"; do
      if [ -f "$f" ]; then
        draft_path="$f"
        break
      fi
    done
  fi
  if [ -z "$draft_path" ]; then
    echo '{"error":"no draft or final article found for readability analysis"}'
    return 1
  fi
  bash "$SKILL_DIR/scripts/readability-score.sh" "$draft_path" "$verbose"
}

cmd_build_word_analysis() {
  local top_n="${1:-25}"
  local draft_path
  draft_path=$(latest_draft)
  if [ -z "$draft_path" ]; then
    for f in "$STATE_DIR/final-external.md" "$STATE_DIR/final-internal.md"; do
      if [ -f "$f" ]; then
        draft_path="$f"
        break
      fi
    done
  fi
  if [ -z "$draft_path" ]; then
    echo '{"error":"no draft or final article found for word analysis"}'
    return 1
  fi
  bash "$SKILL_DIR/scripts/word-frequency.sh" "$draft_path" "$top_n"
}

cmd_build_series_context() {
  # Build series context for prompt injection
  # If pipeline state has series_id, use series-manager.sh context (cached)
  local series_id
  series_id=$(cached_series_id)

  if [ -n "$series_id" ]; then
    local context
    context=$(cached_series_context)
    if [ -n "$context" ]; then
      echo "## Series Context"
      echo ""
      echo "This article is part of a series. Here is the series context:"
      echo ""
      echo '```json'
      echo "$context"
      echo '```'
      echo ""
      echo "**Writing guidance**: Build on previous articles in the series. Reference prior entries where relevant for continuity."
    else
      echo "(series $series_id not found)"
    fi
  else
    echo "(no series associated with this article)"
  fi
}

cmd_build_analytics_insights() {
  # Output performance insights from taste memory for prompt injection
  local taste
  taste=$(cached_taste_memory)
  if [ -z "$taste" ]; then
    echo "(no performance insights available)"
    return
  fi
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
insights = taste.get('performance_insights')
if not insights:
    print('(no performance insights available)')
else:
    print('## Performance Insights')
    print()
    print('Based on analytics from published articles:')
    print()
    tags = insights.get('best_performing_tags', [])
    if tags:
        print(f'Best performing tags: {\", \".join(tags[:5])}')
    fmt = insights.get('best_performing_format', '')
    if fmt and fmt != 'unknown':
        print(f'Best performing format: {fmt}')
    avg_v = insights.get('avg_views', 0)
    if avg_v:
        print(f'Average views: {avg_v}')
    for i in insights.get('insights', []):
        print(f'- {i}')
" "$taste"
}

cmd_build_analytics_summary() {
  # Show performance trends and analytics summary
  bash "$SKILL_DIR/scripts/analytics-feedback.sh" trends 2>/dev/null || echo '(no analytics data available)'
}

cmd_build_config_summary() {
  # Build config context summary for prompt injection
  local config_file="$HOME/.tech-essay-writer/config.json"
  if [ ! -f "$config_file" ]; then
    echo "(no user config — using defaults)"
    return
  fi
  python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    config = json.load(f)
print('## User Configuration')
print()
platforms = config.get('default_platforms', [])
print(f\"Default platforms: {', '.join(platforms)}\")
print(f\"Writing style: {config.get('writing_style', 'technical')}\")
audiences = config.get('target_audiences', [])
print(f\"Target audiences: {', '.join(audiences)}\")
print(f\"Language: {config.get('language', 'en')}\")
print(f\"Use author profile: {config.get('use_author_profile', True)}\")
print(f\"Max refinement rounds: {config.get('max_refinement_rounds', 3)}\")
" "$config_file"
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
    # Check if meaningful issues persist
    attacks = review.get('attacks', [])
    serious = [a for a in attacks if a.get('severity') in ('devastating', 'significant')]
    if len(serious) == 0:
        print('CONVERGED')
    else:
        print('CONTINUE')
" "$adv_review" "$round"
}

cmd_show_progress() {
  bash "$SKILL_DIR/scripts/progress-display.sh" "$PROJECT_DIR" "$@"
}

cmd_publishing_guide() {
  local platform="${1:?platform required}"
  shift
  bash "$SKILL_DIR/scripts/publishing-guide.sh" "$platform" "$PROJECT_DIR" "$@"
}

cmd_list_checkpoints() {
  bash "$SKILL_DIR/scripts/checkpoint.sh" list "$PROJECT_DIR"
}

cmd_rollback() {
  local ckpt_id="${1:?checkpoint id required}"
  bash "$SKILL_DIR/scripts/checkpoint.sh" rollback "$PROJECT_DIR" "$ckpt_id"
}

cmd_retry_stage() {
  local stage="${1:?stage required}"
  local valid_stages="intake research outline draft review refinement polish"
  if ! echo "$valid_stages" | grep -qw "$stage"; then
    echo "ERROR: Cannot retry stage '$stage'. Valid: $valid_stages" >&2
    return 1
  fi

  # Map target stage to preceding stage for checkpoint lookup
  local preceding=""
  case "$stage" in
    research) preceding="intake" ;;
    outline) preceding="research" ;;
    draft) preceding="outline" ;;
    review) preceding="draft" ;;
    refinement) preceding="review" ;;
    polish) preceding="refinement" ;;
  esac

  # Try to rollback to the preceding stage's checkpoint
  if [ -n "$preceding" ]; then
    local found_ckpt
    found_ckpt=$(python3 -c "
import os, sys

ckpt_base = sys.argv[1]
prefix = sys.argv[2]

if not os.path.isdir(ckpt_base):
    sys.exit(0)

matches = []
for name in os.listdir(ckpt_base):
    full = os.path.join(ckpt_base, name)
    if not os.path.isdir(full) or name.startswith('.'):
        continue
    parts = name.rsplit('-', 1)
    label = parts[0] if len(parts) == 2 else name
    ts = parts[1] if len(parts) == 2 else ''
    if label == prefix:
        matches.append((name, ts))

matches.sort(key=lambda x: x[1])
if matches:
    print(matches[-1][0])
" "$STATE_DIR/checkpoints" "$preceding" 2>/dev/null || echo "")

    if [ -n "$found_ckpt" ]; then
      echo "Rolling back to checkpoint: $found_ckpt"
      bash "$SKILL_DIR/scripts/checkpoint.sh" rollback "$PROJECT_DIR" "$found_ckpt"
    else
      echo "No checkpoint found for '$preceding'. Resetting stage only."
    fi
  fi

  # Set stage directly (use set-field to avoid triggering another auto-snapshot)
  bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "stage" "$stage" >/dev/null

  # Clear artifacts for the target stage
  case "$stage" in
    intake)
      rm -f "$STATE_DIR/materials.json"
      ;;
    research)
      rm -f "$STATE_DIR/research-synthesis.json"
      ;;
    outline)
      rm -f "$STATE_DIR/outline-A.json" "$STATE_DIR/outline-B.json" "$STATE_DIR/outline-C.json"
      rm -f "$STATE_DIR/outline-critique.json"
      bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "outline_variant" "null" >/dev/null
      ;;
    draft)
      rm -f "$STATE_DIR"/draft-v*.md
      bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "draft_version" "0" >/dev/null
      ;;
    review)
      rm -f "$STATE_DIR"/review-*.json
      bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "reviews" "{}" >/dev/null
      bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "review_panel_complete" "false" >/dev/null
      ;;
    refinement)
      rm -f "$STATE_DIR"/refinement-*-changes.json
      # Remove subsequent draft versions (keep v1)
      for i in $(seq 10 -1 2); do
        rm -f "$STATE_DIR/draft-v${i}.md"
      done
      bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" "refinement_round" "0" >/dev/null
      ;;
    polish)
      rm -f "$STATE_DIR"/final-*.md
      rm -f "$STATE_DIR/social-package.json"
      rm -f "$STATE_DIR/influence-score.json"
      rm -f "$STATE_DIR/seo-metadata.json"
      rm -f "$STATE_DIR/diagram-suggestions.json"
      ;;
  esac

  echo "Retry: stage reset to '$stage', ready for re-execution."
}

cmd_resume() {
  if [ ! -f "$STATE_DIR/pipeline-state.json" ]; then
    echo "STATUS: not_initialized"
    echo "ACTION: Run intake to start a new pipeline"
    return
  fi

  python3 -c "
import json, os, sys

state_dir = sys.argv[1]
with open(f'{state_dir}/pipeline-state.json') as f:
    d = json.load(f)

stage = d.get('stage', 'unknown')
completed = d.get('completed', False)

if completed:
    print('STATUS: complete')
    print('ACTION: Pipeline already complete. Start a new one or rollback to modify.')
    sys.exit(0)

print(f'STATUS: {stage}')

# Detect partial completion per stage
if stage == 'intake':
    has_materials = os.path.exists(f'{state_dir}/materials.json')
    if has_materials:
        with open(f'{state_dir}/materials.json') as f:
            m = json.load(f)
        count = m.get('source_count', 0)
        print(f'PROGRESS: {count} material(s) collected')
        if count > 0:
            print('ACTION: Materials ready. Advance to research stage.')
        else:
            print('ACTION: Add materials before advancing.')
    else:
        print('PROGRESS: No materials yet')
        print('ACTION: Add materials (URLs, notes, files, code).')

elif stage == 'research':
    has_research = os.path.exists(f'{state_dir}/research-synthesis.json')
    if has_research:
        print('PROGRESS: Research synthesis complete')
        print('ACTION: Advance to outline stage.')
    else:
        print('PROGRESS: Research not started')
        print('ACTION: Run research agent.')

elif stage == 'outline':
    outlines = [v for v in ['A','B','C'] if os.path.exists(f'{state_dir}/outline-{v}.json')]
    has_critique = os.path.exists(f'{state_dir}/outline-critique.json')
    chosen = d.get('outline_variant')
    print(f'PROGRESS: {len(outlines)}/3 outlines, critique={has_critique}, chosen={chosen}')
    if chosen:
        print('ACTION: Advance to draft stage.')
    elif has_critique:
        print('ACTION: Choose an outline variant (A/B/C).')
    elif len(outlines) == 3:
        print('ACTION: Run outline critique agent.')
    elif len(outlines) > 0:
        missing = [v for v in ['A','B','C'] if v not in outlines]
        print(f'ACTION: Generate missing outline(s): {missing}')
    else:
        print('ACTION: Generate 3 outline variants.')

elif stage == 'draft':
    drafts = [f for f in os.listdir(state_dir) if f.startswith('draft-v') and f.endswith('.md')]
    if drafts:
        latest = sorted(drafts)[-1]
        print(f'PROGRESS: Draft exists ({latest})')
        print('ACTION: Advance to review stage.')
    else:
        print('PROGRESS: No draft written yet')
        print('ACTION: Run writer agent.')

elif stage == 'review':
    reviews = d.get('reviews', {})
    panel_done = d.get('review_panel_complete', False)
    has_summary = os.path.exists(f'{state_dir}/review-panel-summary.json')
    expected = ['technical','editor','adversarial','audience','seo','external','factcheck']
    done = [r for r in expected if r in reviews or os.path.exists(f'{state_dir}/review-{r}.json')]
    missing = [r for r in expected if r not in done]
    print(f'PROGRESS: {len(done)}/7 reviews complete')
    if missing:
        print(f'MISSING: {missing}')
        print(f'ACTION: Run missing reviewer(s): {missing}')
    elif not has_summary:
        print('ACTION: Aggregate reviews (run aggregate-reviews.sh).')
    else:
        print('ACTION: Advance to refinement stage.')

elif stage == 'refinement':
    ref_round = d.get('refinement_round', 0)
    max_rounds = d.get('max_refinement_rounds', 3)
    print(f'PROGRESS: Round {ref_round}/{max_rounds}')
    if ref_round >= max_rounds:
        print('ACTION: Max rounds reached. Advance to polish stage.')
    else:
        print(f'ACTION: Run refinement round {ref_round + 1}.')

elif stage == 'polish':
    has_internal = os.path.exists(f'{state_dir}/final-internal.md')
    has_external = os.path.exists(f'{state_dir}/final-external.md')
    print(f'PROGRESS: internal={has_internal}, external={has_external}')
    if has_internal and has_external:
        print('ACTION: Both formats ready. Complete the pipeline.')
    elif has_internal:
        print('ACTION: Generate external format.')
    elif has_external:
        print('ACTION: Generate internal format.')
    else:
        print('ACTION: Generate internal and external formats.')
else:
    print(f'ACTION: Unknown state. Check pipeline-state.json manually.')
" "$STATE_DIR"
}

# Main dispatch
case "$CMD" in
  status) cmd_status ;;
  next-stage) cmd_next_stage ;;
  build-intake-summary) cmd_build_intake_summary ;;
  build-research-prompt) cmd_build_research_prompt ;;
  build-outline-prompts) cmd_build_outline_prompts "$@" ;;
  build-outline-critique-prompt) cmd_build_outline_critique_prompt ;;
  build-writer-prompt) cmd_build_writer_prompt "$@" ;;
  build-review-prompts) cmd_build_review_prompts "$@" ;;
  build-refiner-prompt) cmd_build_refiner_prompt "$@" ;;
  build-format-prompts) cmd_build_format_prompts "$@" ;;
  build-social-prompt) cmd_build_social_prompt ;;
  build-calibration-summary) cmd_build_calibration_summary ;;
  build-influence-score) cmd_build_influence_score "$@" ;;
  build-seo-metadata) cmd_build_seo_metadata "$@" ;;
  build-code-validation) cmd_build_code_validation "$@" ;;
  build-diagram-suggestions) cmd_build_diagram_suggestions "$@" ;;
  build-readability-report) cmd_build_readability_report "$@" ;;
  build-word-analysis) cmd_build_word_analysis "$@" ;;
  build-series-context) cmd_build_series_context ;;
  build-analytics-insights) cmd_build_analytics_insights ;;
  build-analytics-summary) cmd_build_analytics_summary ;;
  build-config-summary) cmd_build_config_summary ;;
  list-platforms) cmd_list_platforms ;;
  check-convergence) cmd_check_convergence "$@" ;;
  show-progress) cmd_show_progress "$@" ;;
  publishing-guide) cmd_publishing_guide "$@" ;;
  list-checkpoints) cmd_list_checkpoints ;;
  rollback) cmd_rollback "$@" ;;
  retry-stage) cmd_retry_stage "$@" ;;
  resume) cmd_resume ;;
  *) usage; exit 1 ;;
esac
