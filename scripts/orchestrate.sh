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
  build-series-context  Build series context for injection into writer/formatter prompts
  build-analytics-summary Show performance trends and analytics summary
  list-platforms        List all available platform format names
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

# Helper: build language directive from pipeline state
build_language_directive() {
  local lang="en"
  if [ -f "$STATE_DIR/pipeline-state.json" ]; then
    lang=$(python3 -c "import json; print(json.load(open('$STATE_DIR/pipeline-state.json')).get('language','en'))" 2>/dev/null || echo "en")
  fi
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
print(f'Reviews: {reviews}/7')
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
    has_critique = os.path.exists(f'{state_dir}/outline-critique.json')
    if has_outline and d.get('outline_variant'):
        print('draft')
    elif has_outline and has_critique:
        print('outline_choice')
    elif has_outline:
        print('outline_critique')
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
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")
  local materials
  materials=$(read_if_exists "$STATE_DIR/materials.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

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
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")
  local taste
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

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
  research=$(read_if_exists "$STATE_DIR/research-synthesis.json")

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
  taste=$(read_if_exists "$HOME/.tech-essay-writer/taste-memory.json")

  # Get author profile data
  local author_profile
  author_profile=$(bash "$SKILL_DIR/scripts/author-profile.sh" read 2>/dev/null || echo "")
  local author_bio
  author_bio=$(bash "$SKILL_DIR/scripts/author-profile.sh" get-bio 2>/dev/null || echo "")

  # Get cross-references for the topic
  local xrefs=""
  local topic
  topic=$(python3 -c "import json; print(json.load(open('$STATE_DIR/pipeline-state.json')).get('topic',''))" 2>/dev/null || echo "")
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

cmd_build_series_context() {
  # Build series context to inject into writer/formatter prompts
  # If the current article belongs to a series, provide reading order, arc, and prior synopses
  local series_file="$HOME/.tech-essay-writer/article-series.json"
  local xref_file="$HOME/.tech-essay-writer/published-articles.json"

  if [ ! -f "$series_file" ]; then
    echo "(no series data available)"
    return
  fi

  # Get current article topic from pipeline state
  local topic=""
  if [ -f "$STATE_DIR/pipeline-state.json" ]; then
    topic=$(python3 -c "import json; print(json.load(open('$STATE_DIR/pipeline-state.json')).get('topic',''))" 2>/dev/null || echo "")
  fi

  python3 -c "
import json, sys, os

series_file = sys.argv[1]
xref_file = sys.argv[2]
topic = sys.argv[3]

if not os.path.exists(series_file):
    print('(no series data available)')
    sys.exit(0)

with open(series_file) as f:
    d = json.load(f)

if not d.get('series'):
    print('(no series defined)')
    sys.exit(0)

# Load published articles for title resolution
articles_by_id = {}
if os.path.exists(xref_file):
    with open(xref_file) as f:
        xref = json.load(f)
    for a in xref.get('articles', []):
        articles_by_id[a['id']] = a

# Find series matching current topic
topic_lower = topic.lower()
topic_words = set(topic_lower.split())
matched = []

for s in d['series']:
    score = 0
    title_words = set(s['title'].lower().split())
    score += len(topic_words & title_words) * 2
    for tag in s.get('tags', []):
        if tag.lower() in topic_lower:
            score += 3
    theme = s.get('narrative_arc', {}).get('theme', '').lower()
    if theme and any(w in theme for w in topic_words):
        score += 2
    # Check if any article in the series matches
    for a in s.get('articles', []):
        syn = a.get('synopsis', '').lower()
        if any(w in syn for w in topic_words):
            score += 1
    if score > 0:
        matched.append((score, s))

matched.sort(key=lambda x: -x[0])

if not matched:
    print('(no matching series for this topic)')
    sys.exit(0)

print('## Series Context')
print()

for _, s in matched[:2]:
    print(f'### Series: {s[\"title\"]}')
    print(f'Description: {s.get(\"description\", \"\")}')
    print(f'Status: {s.get(\"status\", \"?\")}')
    arc = s.get('narrative_arc', {})
    print(f'Arc type: {arc.get(\"type\", \"?\")}')
    if arc.get('theme'):
        print(f'Theme: {arc[\"theme\"]}')
    if arc.get('progression'):
        print(f'Progression: {arc[\"progression\"]}')
    print()

    articles = sorted(s.get('articles', []), key=lambda a: a.get('order', 0))
    if articles:
        print('Reading order:')
        for a in articles:
            title = articles_by_id.get(a['article_id'], {}).get('title', a['article_id'])
            url = articles_by_id.get(a['article_id'], {}).get('url', '')
            print(f'  {a[\"order\"]}. {title} ({a.get(\"role\", \"?\")})')
            if a.get('synopsis'):
                print(f'     Synopsis: {a[\"synopsis\"]}')
            if url:
                print(f'     URL: {url}')
        print()
        print('**Writing guidance**: This article should build on the prior entries above.')
        print(f'Consider the {arc.get(\"type\", \"progressive\")} arc when structuring transitions.')
        print(f'Reference prior articles where relevant for continuity.')
    print()
" "$series_file" "$xref_file" "$topic"
}

cmd_build_analytics_summary() {
  # Show performance trends and analytics insights for context injection
  bash "$SKILL_DIR/scripts/analytics-feedback.sh" trends 2>/dev/null || echo '(no analytics data available)'
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
  build-series-context) cmd_build_series_context ;;
  build-analytics-summary) cmd_build_analytics_summary ;;
  list-platforms) cmd_list_platforms ;;
  check-convergence) cmd_check_convergence "$@" ;;
  *) usage; exit 1 ;;
esac
