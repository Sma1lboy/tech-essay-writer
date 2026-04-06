#!/usr/bin/env bash
# dry-run.sh — Simulate the complete pipeline without LLM agents
# Usage: bash dry-run.sh <project_dir> [skill_dir]
#
# Creates mock data at each stage to verify the pipeline infrastructure works.
# Useful for testing script changes without burning API tokens.
set -euo pipefail

PROJECT_DIR="${1:?Usage: dry-run.sh <project_dir> [skill_dir]}"
SKILL_DIR="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

STATE_DIR="$PROJECT_DIR/.essay-state"
PASS=0
FAIL=0
TOTAL=0

log() { echo "  [DRY-RUN] $*"; }
step() { echo ""; echo "=== STAGE: $1 ==="; }

check() {
  local desc="$1" file="$2"
  TOTAL=$((TOTAL + 1))
  if [ -f "$file" ]; then
    # Verify JSON is valid if .json
    if [[ "$file" == *.json ]]; then
      if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
      else
        echo "  ✗ $desc (invalid JSON)"
        FAIL=$((FAIL + 1))
      fi
    else
      echo "  ✓ $desc"
      PASS=$((PASS + 1))
    fi
  else
    echo "  ✗ $desc (missing: $file)"
    FAIL=$((FAIL + 1))
  fi
}

# Clean slate
rm -rf "$STATE_DIR"
mkdir -p "$STATE_DIR"

echo "Tech Essay Writer — Dry Run"
echo "Project: $PROJECT_DIR"
echo "Skill: $SKILL_DIR"
echo ""

# ─── Stage 1: INTAKE ───
step "INTAKE"

bash "$SKILL_DIR/scripts/pipeline-state.sh" init "$PROJECT_DIR" "Dry Run: How We Built a Multi-Agent Review System" >/dev/null
check "Pipeline initialized" "$STATE_DIR/pipeline-state.json"

bash "$SKILL_DIR/scripts/intake-materials.sh" add-url "$PROJECT_DIR" "https://example.com/agents" "Multi-Agent Systems" >/dev/null
bash "$SKILL_DIR/scripts/intake-materials.sh" add-note "$PROJECT_DIR" "Our review pipeline uses 7 independent agents" >/dev/null
bash "$SKILL_DIR/scripts/intake-materials.sh" add-code "$PROJECT_DIR" 'const reviewers = ["tech","editor","adversarial","audience","seo","external","factcheck"]' "javascript" >/dev/null
bash "$SKILL_DIR/scripts/intake-materials.sh" add-theme "$PROJECT_DIR" "adversarial AI quality" >/dev/null
bash "$SKILL_DIR/scripts/intake-materials.sh" add-angle "$PROJECT_DIR" "multi-agent consensus as quality gate" >/dev/null
check "Materials collected" "$STATE_DIR/materials.json"

log "Intake summary:"
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-intake-summary 2>/dev/null || true

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" research >/dev/null

# ─── Stage 2: RESEARCH ───
step "RESEARCH"

python3 -c "
import json
synthesis = {
    'thesis': 'Multi-agent adversarial review produces higher quality articles than single-reviewer systems',
    'thesis_expanded': 'By using 7 independent agents with different review perspectives, we catch issues that any single reviewer would miss.',
    'evidence_map': [
        {'claim': 'Independent reviewers find different issues', 'sources': ['url-1', 'note-1'], 'strength': 'strong', 'notes': ''},
        {'claim': 'Adversarial review catches logical gaps', 'sources': ['note-1'], 'strength': 'moderate', 'notes': ''}
    ],
    'knowledge_gaps': [{'gap': 'Benchmark data', 'impact': 'medium', 'resolution': 'Run comparison test'}],
    'competitive_landscape': [{'title': 'Writing with AI', 'url': 'https://example.com', 'angle': 'Single agent', 'gap': 'No adversarial review'}],
    'unique_angle': 'First deep dive into multi-agent adversarial review for tech writing',
    'recommended_depth': 'intermediate',
    'recommended_length': 'medium (1500-3000)',
    'key_terms': ['multi-agent', 'adversarial review', 'quality gate']
}
with open('$STATE_DIR/research-synthesis.json', 'w') as f:
    json.dump(synthesis, f, indent=2)
"
check "Research synthesis" "$STATE_DIR/research-synthesis.json"

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" outline >/dev/null

# ─── Stage 3: OUTLINE ───
step "OUTLINE"

for variant in A B C; do
  python3 -c "
import json
outline = {
    'variant': '$variant',
    'style': {'A': 'Tutorial', 'B': 'Deep Dive', 'C': 'Narrative'}['$variant'],
    'title': 'How We Built a 7-Agent Review System for Tech Articles',
    'hook': 'What if your article had 7 expert reviewers before anyone else saw it?',
    'sections': [
        {'title': 'The Problem', 'purpose': 'Establish the pain point', 'words': 300},
        {'title': 'The Architecture', 'purpose': 'Show the multi-agent design', 'words': 600},
        {'title': 'Adversarial Review', 'purpose': 'Deep dive on the adversarial agent', 'words': 400},
        {'title': 'Results', 'purpose': 'Show quality improvements', 'words': 300}
    ],
    'target_words': 1600,
    'tone': 'technical but accessible'
}
with open('$STATE_DIR/outline-${variant}.json', 'w') as f:
    json.dump(outline, f, indent=2)
"
  check "Outline variant $variant" "$STATE_DIR/outline-${variant}.json"
done

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" outline_variant "B" >/dev/null
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" draft >/dev/null

# ─── Stage 4: DRAFT ───
step "DRAFT"

cat > "$STATE_DIR/draft-v1.md" << 'DRAFT'
# How We Built a 7-Agent Review System for Tech Articles

What if your article had 7 expert reviewers before anyone else saw it?

## The Problem

Most tech articles go through a single review pass — maybe a colleague reads it, maybe not.
The result: technical errors slip through, the tone feels off, and the SEO is an afterthought.

We built something different: a multi-agent review pipeline where 7 independent AI agents
each review your article from a completely different perspective.

## The Architecture

```javascript
const reviewers = [
  "technical",    // Catches code errors, outdated APIs
  "editor",       // Checks flow, voice, AI slop
  "adversarial",  // Tries to break your argument
  "audience",     // Would real readers share this?
  "seo",          // Search optimization
  "external",     // Fresh-eyes perspective
  "factcheck"     // Verifies all claims
];
```

Each reviewer gets fresh context — no knowledge of other reviewers' findings.
This prevents groupthink and ensures independent assessment.

## The Adversarial Agent

The adversarial reviewer is the star of the system. Its job: find the weakest point
in your article and attack it. Not to be mean — to make the article stronger.

It runs an "internet stress test": what would the top HN comment say?
What would a Twitter critic quote-tweet? What would a domain expert flag?

## Results

After implementing this system, our article quality scores improved from 5.2/10 to 8.1/10.
The adversarial reviewer alone caught issues in 73% of articles that other reviewers missed.

The key insight: independent agents with different perspectives find more issues than
a single comprehensive reviewer. The adversarial agent is the quality gate that makes
the entire system worthwhile.
DRAFT
check "Draft v1" "$STATE_DIR/draft-v1.md"

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" draft_version 1 >/dev/null

# Code validation
log "Running code validation..."
bash "$SKILL_DIR/scripts/code-validate.sh" "$STATE_DIR/draft-v1.md" 2>/dev/null || true

# Diagram suggestions
log "Running diagram suggestions..."
bash "$SKILL_DIR/scripts/diagram-suggest.sh" "$STATE_DIR/draft-v1.md" 2>/dev/null || true

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" review >/dev/null

# ─── Stage 5: REVIEW ───
step "REVIEW"

# Generate mock reviews for all 7 reviewers
for reviewer in technical editor adversarial audience seo external factcheck; do
  python3 -c "
import json
reviews = {
    'technical': {'reviewer':'technical','rating':'PASS','confidence':'high','summary':'Code examples are correct.','issues':[],'code_issues':[],'factual_errors':[],'missing_caveats':[]},
    'editor': {'reviewer':'editor','rating':'PUBLISH_READY','summary':'Well-structured article.','hook_score':8,'clarity_score':8,'flow_score':7,'voice_score':8,'engagement_score':7,'economy_score':8,'overall_score':8,'issues':[],'ai_slop_flags':[],'best_line':'Independent agents find more issues.','weakest_section':'Results could use more data','cut_candidates':[]},
    'adversarial': {'reviewer':'adversarial','rating':'SOLID','summary':'Argument is well-supported.','premise_valid':True,'premise_attack':None,'attacks':[{'target':'73% stat','attack':'Where does this come from?','severity':'minor','likely_source':'HN comment','defense':'Internal testing data','verdict':'acceptable risk'}],'cherry_picking':[],'logic_gaps':[],'missing_nuance':['Scale considerations'],'stress_test':{'hn_top_comment':'Interesting but sample size?','twitter_quote':'Good approach','expert_reaction':'Solid methodology'},'overall_vulnerability':'Low'},
    'audience': {'reviewer':'audience','reader_a':{'persona':'Internal engineer','rating':'WOULD_SHARE','actionability':8,'relevance':7,'time_well_spent':True,'share_trigger':'Multi-agent pattern is reusable','feedback':'Great practical example'},'reader_b':{'persona':'External community','rating':'WOULD_SHARE','hn_potential':7,'twitter_potential':6,'novelty':7,'credibility':7,'memorability':6,'share_trigger':'Novel approach','feedback':'Would like more benchmarks'},'discovery_analysis':{'search_terms':['multi-agent review','AI writing quality'],'social_hook':'7 agents review your article','newsletter_pitch':'Novel multi-agent approach to article quality','target_communities':['HN','r/programming']},'overall_verdict':'Strong influence-building potential'},
    'seo': {'reviewer':'seo','rating':'OPTIMIZED','summary':'Good keyword presence.','issues':[]},
    'external': {'reviewer':'external','rating':'CLEAR','summary':'Accessible to outsiders.','issues':[]},
    'factcheck': {'reviewer':'factcheck','rating':'VERIFIED','summary':'Claims are supported.','issues':[]}
}
with open('$STATE_DIR/review-${reviewer}.json', 'w') as f:
    json.dump(reviews['$reviewer'], f, indent=2)
"
  check "Review: $reviewer" "$STATE_DIR/review-${reviewer}.json"
done

# Aggregate and score
log "Aggregating reviews..."
bash "$SKILL_DIR/scripts/aggregate-reviews.sh" "$PROJECT_DIR" 2>/dev/null || true
check "Review panel summary" "$STATE_DIR/review-panel-summary.json"

log "Computing quality score..."
bash "$SKILL_DIR/scripts/quality-score.sh" "$PROJECT_DIR" verbose 2>/dev/null || true
check "Quality score" "$STATE_DIR/quality-score.json"

# Calibrate
log "Calibrating reviews..."
bash "$SKILL_DIR/scripts/calibrate-reviews.sh" "$PROJECT_DIR" 2>/dev/null || true

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" refinement >/dev/null

# ─── Stage 6: REFINEMENT ───
step "REFINEMENT"

cp "$STATE_DIR/draft-v1.md" "$STATE_DIR/draft-v2.md"
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" draft_version 2 >/dev/null
bash "$SKILL_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT_DIR" >/dev/null
check "Refined draft v2" "$STATE_DIR/draft-v2.md"

bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" polish >/dev/null

# ─── Stage 7: POLISH ───
step "POLISH"

cp "$STATE_DIR/draft-v2.md" "$STATE_DIR/final-internal.md"
cp "$STATE_DIR/draft-v2.md" "$STATE_DIR/final-external.md"
check "Final internal" "$STATE_DIR/final-internal.md"
check "Final external" "$STATE_DIR/final-external.md"

# Social package
python3 -c "
import json
pkg = {
    'twitter_thread': ['1/ We built a 7-agent review system for tech articles.','2/ Each agent reviews independently — no groupthink.','3/ The adversarial agent alone caught issues in 73% of articles.'],
    'linkedin_post': 'Excited to share how multi-agent AI review improved our article quality from 5.2 to 8.1/10.',
    'hn_title': 'How We Built a 7-Agent Review System for Tech Articles',
    'xiaohongshu_post': '分享：我们如何用7个AI Agent来审查技术文章'
}
with open('$STATE_DIR/social-package.json', 'w') as f:
    json.dump(pkg, f, indent=2)
"
check "Social package" "$STATE_DIR/social-package.json"

# Influence score
log "Computing influence score..."
bash "$SKILL_DIR/scripts/influence-score.sh" "$PROJECT_DIR" verbose 2>/dev/null || true

# SEO metadata
log "Generating SEO metadata..."
bash "$SKILL_DIR/scripts/seo-metadata.sh" "$PROJECT_DIR" 2>/dev/null || true

# Publish check
log "Running publish readiness check..."
bash "$SKILL_DIR/scripts/publish-check.sh" "$PROJECT_DIR" 2>/dev/null || true

# Progress display
log "Pipeline progress:"
bash "$SKILL_DIR/scripts/progress-display.sh" "$PROJECT_DIR" 2>/dev/null || true

# ─── COMPLETION ───
step "COMPLETION"

bash "$SKILL_DIR/scripts/pipeline-state.sh" complete "$PROJECT_DIR" >/dev/null
check "Pipeline complete" "$STATE_DIR/pipeline-state.json"

# Verify final state
FINAL_STAGE=$(bash "$SKILL_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT_DIR")
TOTAL=$((TOTAL + 1))
if [ "$FINAL_STAGE" = "complete" ]; then
  echo "  ✓ Final stage is 'complete'"
  PASS=$((PASS + 1))
else
  echo "  ✗ Final stage is '$FINAL_STAGE' (expected 'complete')"
  FAIL=$((FAIL + 1))
fi

# ─── SUMMARY ───
echo ""
echo "========================================"
echo "DRY RUN: $TOTAL checks | Pass: $PASS | Fail: $FAIL"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  echo "⚠  Some checks failed. Review output above."
  exit 1
else
  echo "✅ All pipeline stages completed successfully."
  exit 0
fi
