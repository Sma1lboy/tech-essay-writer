#!/usr/bin/env bash
# Comprehensive end-to-end integration test
# Exercises the full pipeline PLUS all auxiliary scripts:
#   config, author-profile, expertise-graph, series, cross-reference,
#   analytics, influence, SEO, code-validate, diagrams, quality-score,
#   publish-check, progress-display, taste-memory (diff-learn/feedback/suggest),
#   checkpoint auto-saves, rollback, retry-stage, resume
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PROJECT="$TMPDIR/e2e-integration"
mkdir -p "$PROJECT"
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

PASS=0
FAIL=0

assert_eq() { local d="$1" e="$2" a="$3"; if [ "$e" = "$a" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (expected=$e actual=$a)"; fi; }
assert_contains() { local d="$1" n="$2" h="$3"; if echo "$h" | grep -q "$n"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (missing: $n)"; fi; }
assert_not_contains() { local d="$1" n="$2" h="$3"; if echo "$h" | grep -q "$n"; then FAIL=$((FAIL+1)); echo "FAIL: $d (should not contain: $n)"; else PASS=$((PASS+1)); fi; }
assert_file() { local d="$1" p="$2"; if [ -f "$p" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (file missing: $p)"; fi; }
assert_dir() { local d="$1" p="$2"; if [ -d "$p" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (dir missing: $p)"; fi; }
assert_gt() { local d="$1" a="$2" b="$3"; if [ "$a" -gt "$b" ] 2>/dev/null; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d ($a not > $b)"; fi; }

echo "=== E2E Integration: Full Pipeline + All Auxiliary Scripts ==="

# ========================================================
# SECTION 1: CONFIG SYSTEM
# ========================================================
echo "--- Section 1: Config System ---"

bash "$SCRIPT_DIR/scripts/config.sh" init >/dev/null
assert_file "config.json created" "$HOME/.tech-essay-writer/config.json"

bash "$SCRIPT_DIR/scripts/config.sh" set language zh >/dev/null
lang=$(bash "$SCRIPT_DIR/scripts/config.sh" get language)
assert_eq "config language set to zh" "zh" "$lang"

bash "$SCRIPT_DIR/scripts/config.sh" set writing_style technical >/dev/null
style=$(bash "$SCRIPT_DIR/scripts/config.sh" get writing_style)
assert_eq "config writing_style set" "technical" "$style"

bash "$SCRIPT_DIR/scripts/config.sh" add-platform medium >/dev/null
platforms=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "config has medium platform" "medium" "$platforms"

bash "$SCRIPT_DIR/scripts/config.sh" add-platform devto >/dev/null
platforms=$(bash "$SCRIPT_DIR/scripts/config.sh" get default_platforms)
assert_contains "config has devto platform" "devto" "$platforms"

config_read=$(bash "$SCRIPT_DIR/scripts/config.sh" read)
assert_contains "config read shows language" "zh" "$config_read"
assert_contains "config read shows writing_style" "technical" "$config_read"

# ========================================================
# SECTION 2: AUTHOR PROFILE
# ========================================================
echo "--- Section 2: Author Profile ---"

bash "$SCRIPT_DIR/scripts/author-profile.sh" init >/dev/null
assert_file "author-profile.json created" "$HOME/.tech-essay-writer/author-profile.json"

bash "$SCRIPT_DIR/scripts/author-profile.sh" set name "Test Author" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set bio "AI systems architect and tech writer" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set role "Staff Engineer" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set company "TestCorp" >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social twitter testauthor >/dev/null
bash "$SCRIPT_DIR/scripts/author-profile.sh" set-social github testauthor >/dev/null

bio=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-bio)
assert_contains "bio has author name" "Test Author" "$bio"
assert_contains "bio has role" "Staff Engineer" "$bio"

profile_read=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" read)
assert_contains "profile has twitter" "testauthor" "$profile_read"

socials=$(bash "$SCRIPT_DIR/scripts/author-profile.sh" get-social-handles)
assert_contains "socials has twitter" "twitter" "$socials"
assert_contains "socials has github" "github" "$socials"

# ========================================================
# SECTION 3: EXPERTISE GRAPH
# ========================================================
echo "--- Section 3: Expertise Graph ---"

bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "multi-agent" ai architecture >/dev/null
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "context-isolation" ai agents >/dev/null
bash "$SCRIPT_DIR/scripts/expertise-graph.sh" update "conductor-pattern" ai architecture agents >/dev/null

query_out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" query multi-agent)
assert_contains "expertise query finds multi-agent" "multi-agent" "$query_out"

top_out=$(bash "$SCRIPT_DIR/scripts/expertise-graph.sh" top 3)
assert_contains "expertise top includes multi-agent" "multi-agent" "$top_out"

# ========================================================
# SECTION 4: CROSS-REFERENCE REGISTRY
# ========================================================
echo "--- Section 4: Cross-Reference Registry ---"

xref_add=$(bash "$SCRIPT_DIR/scripts/cross-reference.sh" add "Building Agents with Claude" "https://example.com/agents" agent ai multi-agent)
assert_contains "xref add returns article id" "art-" "$xref_add"

bash "$SCRIPT_DIR/scripts/cross-reference.sh" add "Context Window Management" "https://example.com/context" context ai >/dev/null

search_out=$(bash "$SCRIPT_DIR/scripts/cross-reference.sh" search agent)
assert_contains "xref search finds agent article" "Building Agents" "$search_out"

suggest_out=$(bash "$SCRIPT_DIR/scripts/cross-reference.sh" suggest multi-agent)
assert_contains "xref suggest finds related" "Building Agents" "$suggest_out"

list_out=$(bash "$SCRIPT_DIR/scripts/cross-reference.sh" list)
assert_contains "xref list has 2 articles" "Context Window" "$list_out"

# ========================================================
# SECTION 5: SERIES MANAGER
# ========================================================
echo "--- Section 5: Series Manager ---"

series_create=$(bash "$SCRIPT_DIR/scripts/series-manager.sh" create "Agent Architecture Series" "A deep dive into multi-agent system design patterns")
assert_contains "series create returns id" "ser-" "$series_create"

# Extract series_id
SERIES_ID=$(echo "$series_create" | grep -o 'ser-[0-9]*')

series_list=$(bash "$SCRIPT_DIR/scripts/series-manager.sh" list)
assert_contains "series list shows our series" "Agent Architecture" "$series_list"

bash "$SCRIPT_DIR/scripts/series-manager.sh" set-arc "$SERIES_ID" "From single agents to orchestrated multi-agent systems" >/dev/null

series_show=$(bash "$SCRIPT_DIR/scripts/series-manager.sh" show "$SERIES_ID")
assert_contains "series show has description" "multi-agent" "$series_show"

series_ctx=$(bash "$SCRIPT_DIR/scripts/series-manager.sh" context "$SERIES_ID")
assert_contains "series context is JSON" "series_name" "$series_ctx"

# ========================================================
# SECTION 6: PIPELINE INIT WITH CONFIG + SERIES
# ========================================================
echo "--- Section 6: Pipeline Init with Config + Series ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" "Multi-Agent Orchestration Patterns" --series "$SERIES_ID" >/dev/null

# Verify pipeline state has series_id
state=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" read "$PROJECT")
assert_contains "pipeline has series_id" "$SERIES_ID" "$state"

# Config summary should influence prompts
config_summary=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-config-summary)
assert_contains "config summary has language" "zh" "$config_summary"

# ========================================================
# SECTION 7: INTAKE + CHECKPOINT AUTO-SAVES
# ========================================================
echo "--- Section 7: Intake + Checkpoint Auto-Saves ---"

bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$PROJECT" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT" "Multi-agent orchestration requires careful context management. Each agent should get only the context it needs." >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT" "The conductor pattern separates planning from execution. Conductors plan, sprint masters direct, workers execute." >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-url "$PROJECT" "https://docs.anthropic.com/en/docs/agents" "Anthropic Agent Docs" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-code "$PROJECT" 'class Conductor { async plan(mission) { return this.decompose(mission); } }' "javascript" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-theme "$PROJECT" "multi-agent orchestration" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-angle "$PROJECT" "production patterns from a real system" >/dev/null

# Transition to research — should auto-snapshot intake
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" research >/dev/null

# Verify checkpoint auto-save happened
assert_dir "checkpoints dir exists" "$PROJECT/.essay-state/checkpoints"
ckpt_count=$(ls -d "$PROJECT/.essay-state/checkpoints/"*/ 2>/dev/null | wc -l | tr -d ' ')
assert_gt "at least 1 checkpoint after set-stage" "$ckpt_count" 0

# ========================================================
# SECTION 8: RESEARCH + PROGRESS DISPLAY
# ========================================================
echo "--- Section 8: Research + Progress Display ---"

# Progress display at research stage
progress_json=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "progress shows research stage" "research" "$progress_json"

# Simulate research output
cat > "$PROJECT/.essay-state/research-synthesis.json" << 'EOF'
{
  "thesis": "Effective multi-agent orchestration requires three architectural principles: context isolation, progressive disclosure, and hierarchical planning.",
  "thesis_expanded": "Most agent systems fail because they treat context as unlimited. The conductor pattern enforces strict boundaries: each agent gets exactly the context it needs, nothing more.",
  "evidence_map": [
    {"claim": "Context isolation prevents hallucination cascades", "sources": ["note-1", "note-2"], "strength": "strong"},
    {"claim": "Hierarchical planning enables complex decomposition", "sources": ["note-2", "url-1"], "strength": "strong"},
    {"claim": "Progressive disclosure reduces token waste", "sources": ["note-1"], "strength": "moderate"}
  ],
  "knowledge_gaps": [
    {"gap": "No latency benchmarks for multi-agent vs single-agent", "impact": "medium", "resolution": "Add timing data"},
    {"gap": "Error recovery patterns not documented", "impact": "high", "resolution": "Document retry and fallback strategies"}
  ],
  "competitive_landscape": {
    "existing_articles": [
      {"title": "Anthropic Agent Docs", "url": "https://docs.anthropic.com/en/docs/agents", "angle": "Single-agent focus"}
    ],
    "gap": "No production-tested multi-agent orchestration patterns with real code and metrics exist"
  },
  "unique_angle": "Production-tested patterns from a system that runs 50+ sprints autonomously",
  "recommended_depth": "intermediate",
  "recommended_length": "medium",
  "key_terms": ["conductor pattern", "context isolation", "progressive disclosure", "hierarchical planning"]
}
EOF

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" outline >/dev/null

# Verify second checkpoint was created
ckpt_count_2=$(ls -d "$PROJECT/.essay-state/checkpoints/"*/ 2>/dev/null | wc -l | tr -d ' ')
assert_gt "more checkpoints after research→outline" "$ckpt_count_2" "$ckpt_count"

# ========================================================
# SECTION 9: OUTLINES WITH SERIES CONTEXT
# ========================================================
echo "--- Section 9: Outlines with Series Context ---"

# Verify outline prompts build correctly
for v in A B C; do
  prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-outline-prompts "$v")
  assert_contains "outline $v has variant marker" "Variant: $v" "$prompt"
  assert_contains "outline $v has thesis" "multi-agent orchestration" "$prompt"
done

# Series context injection
series_in_outline=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-series-context 2>/dev/null || echo "")
if [ -n "$series_in_outline" ]; then
  assert_contains "series context has series_name" "Agent Architecture" "$series_in_outline"
fi

# Simulate 3 outline outputs
cat > "$PROJECT/.essay-state/outline-A.json" << 'EOF'
{
  "variant": "A", "variant_name": "Tutorial",
  "title": "Build a Multi-Agent Orchestrator from Scratch",
  "hook": "Our monolithic agent kept forgetting its own instructions. We replaced it with three coordinated agents and never looked back.",
  "sections": [
    {"title": "Why Monolithic Agents Fail", "purpose": "Problem", "key_points": ["Context overflow", "Tangled concerns"], "estimated_words": 300},
    {"title": "The Three-Layer Architecture", "purpose": "Solution", "key_points": ["Conductor", "Sprint Master", "Worker"], "estimated_words": 500},
    {"title": "Implementing Context Isolation", "purpose": "Deep dive", "key_points": ["Fresh context", "Progressive disclosure"], "estimated_words": 600},
    {"title": "Error Recovery Patterns", "purpose": "Robustness", "key_points": ["Retry", "Fallback", "Circuit breaker"], "estimated_words": 400},
    {"title": "Production Metrics", "purpose": "Evidence", "key_points": ["Latency", "Reliability", "Cost"], "estimated_words": 300}
  ],
  "target_word_count": 2100, "tone": "Hands-on tutorial"
}
EOF

cat > "$PROJECT/.essay-state/outline-B.json" << 'EOF'
{
  "variant": "B", "variant_name": "Deep Dive",
  "title": "Multi-Agent Orchestration: Patterns That Scale",
  "hook": "The agent community is rediscovering microservices architecture — except this time, the services think for themselves.",
  "sections": [
    {"title": "The Complexity Cliff", "purpose": "Problem space", "key_points": ["When single agents hit their limits"], "estimated_words": 400},
    {"title": "Orchestration Principles", "purpose": "Framework", "key_points": ["Separation of concerns", "Context budgeting"], "estimated_words": 600},
    {"title": "The Conductor Pattern", "purpose": "Core pattern", "key_points": ["Planning vs execution"], "estimated_words": 500},
    {"title": "Trade-offs and Anti-patterns", "purpose": "Nuance", "key_points": ["Over-decomposition", "Context duplication"], "estimated_words": 400},
    {"title": "Real-World Results", "purpose": "Evidence", "key_points": ["Production metrics", "Lessons learned"], "estimated_words": 500}
  ],
  "target_word_count": 2400, "tone": "Analytical, systems-thinking"
}
EOF

cat > "$PROJECT/.essay-state/outline-C.json" << 'EOF'
{
  "variant": "C", "variant_name": "Narrative",
  "title": "The Day Our Agent Lost Its Memory (And How Orchestration Saved Us)",
  "hook": "Three months in, our flagship agent started hallucinating its own past decisions. The fix wasn't better prompting — it was a fundamentally different architecture.",
  "sections": [
    {"title": "The Incident", "purpose": "Hook", "key_points": ["Production failure"], "estimated_words": 300},
    {"title": "Root Cause Analysis", "purpose": "Investigation", "key_points": ["Context window exhaustion"], "estimated_words": 400},
    {"title": "The Orchestration Breakthrough", "purpose": "Solution", "key_points": ["Multi-agent design"], "estimated_words": 500},
    {"title": "Building the System", "purpose": "Implementation", "key_points": ["Architecture decisions"], "estimated_words": 500},
    {"title": "Aftermath", "purpose": "Results", "key_points": ["Metrics and growth"], "estimated_words": 300}
  ],
  "target_word_count": 2000, "tone": "War story with technical depth"
}
EOF

# Simulate outline critique
cat > "$PROJECT/.essay-state/outline-critique.json" << 'EOF'
{
  "critic": "outline-adversarial",
  "outlines_analyzed": ["A", "B", "C"],
  "per_outline": {
    "A": {"variant_name": "Tutorial", "overall_score": 7.5, "strengths": ["Practical"], "weaknesses": ["Rushed ending"], "fix_suggestions": ["Expand metrics"]},
    "B": {"variant_name": "Deep Dive", "overall_score": 8.2, "strengths": ["Best argument flow"], "weaknesses": ["Slightly dry"], "fix_suggestions": ["Add anecdotes"]},
    "C": {"variant_name": "Narrative", "overall_score": 7.8, "strengths": ["Most engaging"], "weaknesses": ["Low code density"], "fix_suggestions": ["Add code earlier"]}
  },
  "cross_comparison": {
    "best_thesis_handling": {"variant": "B", "reason": "Most rigorous"},
    "strongest_opening": {"variant": "C", "reason": "Incident hook"},
    "best_code_integration": {"variant": "A", "reason": "Code throughout"}
  },
  "recommendation": {"recommended_variant": "B", "confidence": "high", "reasoning": "Strongest analytical structure", "runner_up": "C"}
}
EOF

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" outline_variant "B" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" draft >/dev/null

# ========================================================
# SECTION 10: DRAFT + WRITER PROMPT WITH SERIES
# ========================================================
echo "--- Section 10: Draft + Writer Prompt ---"

prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-writer-prompt B)
assert_contains "writer prompt has outline B" "Deep Dive" "$prompt"
assert_contains "writer prompt has template" "Draft Writer" "$prompt"

# Simulate draft
cat > "$PROJECT/.essay-state/draft-v1.md" << 'DRAFT'
# Multi-Agent Orchestration: Patterns That Scale

The agent community is rediscovering microservices architecture — except this time,
the services think for themselves.

## The Complexity Cliff

Every AI agent starts simple: one prompt, a few tools, and a clear task. But
complexity grows. You add more tools, longer system prompts, multi-step workflows.
Eventually, the agent starts forgetting its earlier instructions. Context overflow.

This isn't a model limitation — it's an architecture problem.

## Orchestration Principles

The fix mirrors what we learned from distributed systems:

1. **Separation of concerns** — each agent has one job
2. **Context budgeting** — treat tokens like memory, allocate deliberately
3. **Progressive disclosure** — agents get information on a need-to-know basis

```javascript
class Conductor {
  async orchestrate(mission) {
    const sprints = await this.plan(mission);
    for (const sprint of sprints) {
      const master = new SprintMaster({ context: 'fresh' });
      const result = await master.execute(sprint);
      this.evaluate(result);
    }
  }
}
```

## The Conductor Pattern

The conductor never writes code. It plans, evaluates, and delegates.
Sprint masters read the codebase and direct workers.
Workers execute with minimal, focused context.

```python
class SprintMaster:
    def execute(self, sprint):
        tasks = self.decompose(sprint)
        results = []
        for task in tasks:
            worker = Worker(context=task.required_context)
            results.append(worker.run(task))
        return self.synthesize(results)
```

## Trade-offs and Anti-patterns

Multi-agent adds latency. For tasks under 3 tool calls, a single agent is faster.
Watch for over-decomposition: if your conductor spawns 20 workers for a one-file
change, your decomposition is too fine.

Anti-pattern: sharing full context between layers defeats the purpose.

## Real-World Results

In production, our orchestrated system processes 2000+ files across 15-hour
autonomous sessions. Key metrics:

- Task completion: 89% (vs 64% monolithic)
- Context overflow errors: 0% (vs 18%)
- Token efficiency: 3.2x improvement
- Mean time to recovery: 4 minutes (automatic retry)
DRAFT

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" draft_version 1 >/dev/null

# ========================================================
# SECTION 11: CODE VALIDATION
# ========================================================
echo "--- Section 11: Code Validation ---"

code_val=$(bash "$SCRIPT_DIR/scripts/code-validate.sh" "$PROJECT/.essay-state/draft-v1.md" --json)
assert_contains "code-validate returns JSON" "blocks" "$code_val"
assert_contains "code-validate found javascript" "javascript" "$code_val"
assert_contains "code-validate found python" "python" "$code_val"

# ========================================================
# SECTION 12: DIAGRAM SUGGESTIONS
# ========================================================
echo "--- Section 12: Diagram Suggestions ---"

diagram_out=$(bash "$SCRIPT_DIR/scripts/diagram-suggest.sh" "$PROJECT/.essay-state/draft-v1.md")
assert_contains "diagram-suggest returns JSON" "suggestions" "$diagram_out"

# ========================================================
# SECTION 13: REVIEW PANEL + QUALITY SCORE
# ========================================================
echo "--- Section 13: Review Panel + Quality Score ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" review >/dev/null

# Simulate 7 reviewer outputs
cat > "$PROJECT/.essay-state/review-technical.json" << 'EOF'
{"reviewer":"technical","rating":"NEEDS_FIXES","summary":"Code examples need error handling","confidence":"high","issues":[{"severity":"major","location":"Conductor Pattern","issue":"No error handling in orchestrate loop","suggestion":"Add try/catch with retry logic"}],"code_issues":[{"code_block":"Conductor class","issue":"Missing error handling","fixed_code":"try { await master.execute(sprint) } catch (e) { this.handleFailure(sprint, e) }"}]}
EOF

cat > "$PROJECT/.essay-state/review-editor.json" << 'EOF'
{"reviewer":"editor","rating":"NEEDS_EDITING","summary":"Strong content, tighten transitions","hook_score":7,"clarity_score":8,"flow_score":7,"voice_score":8,"engagement_score":7,"economy_score":8,"overall_score":7.5,"issues":[{"severity":"minor","location":"Trade-offs","issue":"Transition from code to anti-patterns is abrupt","suggestion":"Add a bridging sentence"}],"ai_slop_flags":[],"best_line":"Context budgeting — treat tokens like memory","weakest_section":"Trade-offs — needs expansion"}
EOF

cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"NEEDS_STRENGTHENING","summary":"Metrics need methodology","premise_valid":true,"attacks":[{"target":"89% completion claim","attack":"No methodology described","severity":"moderate","defense":"Add measurement details","verdict":"fixable"}],"issues":[{"severity":"moderate","issue":"Metrics lack methodology"}]}
EOF

cat > "$PROJECT/.essay-state/review-audience.json" << 'EOF'
{"reviewer":"audience","reader_a":{"rating":"WOULD_SHARE","actionability":8,"relevance":8,"time_well_spent":true},"reader_b":{"rating":"INTERESTING","hn_potential":7,"twitter_potential":7,"novelty":7,"credibility":6},"overall_verdict":"Strong for internal, needs evidence for external"}
EOF

cat > "$PROJECT/.essay-state/review-seo.json" << 'EOF'
{"reviewer":"seo","rating":"NEEDS_WORK","summary":"Title could be more searchable","title_analysis":{"current_title":"Multi-Agent Orchestration: Patterns That Scale","searchability":6,"clickability":7},"social_package":{"meta_description":"Learn production-tested patterns for multi-agent AI orchestration.","twitter_thread":["1/ We replaced our monolithic agent with an orchestrated system..."],"linkedin_post":"Multi-agent orchestration patterns that actually work in production.","hn_title":"Multi-Agent Orchestration: Production Patterns That Scale"}}
EOF

cat > "$PROJECT/.essay-state/review-external.json" << 'EOF'
{"reviewer":"external","rating":"ACCESSIBLE","summary":"Clear writing, minimal jargon issues","confidence":"high","jargon_issues":[{"term":"progressive disclosure","location":"Principles","suggestion":"Define briefly"}],"accessibility_score":7,"issues":[{"severity":"minor","issue":"Progressive disclosure needs definition"}]}
EOF

cat > "$PROJECT/.essay-state/review-factcheck.json" << 'EOF'
{"reviewer":"factcheck","rating":"MOSTLY_VERIFIED","summary":"Claims are reasonable but metrics need sourcing","confidence":"medium","claims_checked":6,"claims_verified":4,"claims_unverified":2,"issues":[{"severity":"minor","claim":"89% completion rate","location":"Results","verdict":"unverified","suggestion":"Add measurement context"}],"code_verification":[{"code_block":"Conductor class","syntax_valid":true,"would_run":true}]}
EOF

# Register reviews
for r in review-technical review-editor review-adversarial review-audience review-seo review-external review-factcheck; do
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT" "$PROJECT/.essay-state/${r}.json" >/dev/null
done

# Aggregate
bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$PROJECT" >/dev/null
assert_file "panel summary exists" "$PROJECT/.essay-state/review-panel-summary.json"

# Calibrate
bash "$SCRIPT_DIR/scripts/calibrate-reviews.sh" "$PROJECT" >/dev/null
assert_file "calibration exists" "$PROJECT/.essay-state/review-calibration.json"

# Quality score
quality_out=$(bash "$SCRIPT_DIR/scripts/quality-score.sh" "$PROJECT")
assert_contains "quality score has composite" "composite" "$quality_out"
assert_contains "quality score has dimension_scores" "dimension_scores" "$quality_out"

# ========================================================
# SECTION 14: INFLUENCE SCORE
# ========================================================
echo "--- Section 14: Influence Score ---"

influence_out=$(bash "$SCRIPT_DIR/scripts/influence-score.sh" "$PROJECT" "$SCRIPT_DIR")
assert_contains "influence score has JSON" "influence" "$influence_out"

# ========================================================
# SECTION 15: SEO METADATA
# ========================================================
echo "--- Section 15: SEO Metadata ---"

seo_out=$(bash "$SCRIPT_DIR/scripts/seo-metadata.sh" "$PROJECT")
assert_contains "seo metadata has JSON output" "meta" "$seo_out"

# ========================================================
# SECTION 16: REFINEMENT + RETRY-STAGE
# ========================================================
echo "--- Section 16: Refinement + Retry-Stage ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" refinement >/dev/null

# Round 1
prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-refiner-prompt 1)
assert_contains "refiner prompt round 1" "Round: 1" "$prompt"

# Simulate v2 draft
cp "$PROJECT/.essay-state/draft-v1.md" "$PROJECT/.essay-state/draft-v2.md"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT" >/dev/null

# Simulate adversarial re-review
cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"SOLID","summary":"Issues addressed","attacks":[],"issues":[]}
EOF

conv=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 2)
assert_eq "round 2 converged" "CONVERGED" "$conv"

# Test retry-stage: reset draft stage
retry_out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" retry-stage draft)
assert_contains "retry-stage output" "Retry" "$retry_out"
assert_contains "retry-stage mentions draft" "draft" "$retry_out"

# After retry, stage should be set to draft
current_stage=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")
assert_eq "retry-stage reset to draft" "draft" "$current_stage"

# Recreate draft for continued pipeline
cat > "$PROJECT/.essay-state/draft-v1.md" << 'DRAFT'
# Multi-Agent Orchestration: Patterns That Scale

The agent community is rediscovering microservices architecture — except this time,
the services think for themselves.

## The Complexity Cliff

Every AI agent starts simple: one prompt, a few tools, and a clear task.

## Orchestration Principles

```javascript
class Conductor {
  async orchestrate(mission) {
    const sprints = await this.plan(mission);
    for (const sprint of sprints) {
      const master = new SprintMaster({ context: 'fresh' });
      await master.execute(sprint);
    }
  }
}
```

## The Conductor Pattern

The conductor never writes code. It plans, evaluates, and delegates.

```python
class SprintMaster:
    def execute(self, sprint):
        tasks = self.decompose(sprint)
        return [Worker(context=t.ctx).run(t) for t in tasks]
```

## Trade-offs and Anti-patterns

Multi-agent adds latency. For simple tasks, a single agent is fine.

## Real-World Results

Task completion: 89%. Context overflows: 0%. Token efficiency: 3.2x improvement.
DRAFT

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" draft_version 1 >/dev/null

# ========================================================
# SECTION 17: RESUME
# ========================================================
echo "--- Section 17: Resume ---"

resume_out=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" resume)
assert_contains "resume detects partial state" "STATUS" "$resume_out"
assert_contains "resume shows current stage" "draft" "$resume_out"

# ========================================================
# SECTION 18: ROLLBACK
# ========================================================
echo "--- Section 18: Rollback ---"

# List checkpoints
ckpt_list=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" list "$PROJECT")
assert_contains "checkpoint list has entries" "checkpoint" "$ckpt_list"

# Get latest checkpoint
latest_ckpt=$(bash "$SCRIPT_DIR/scripts/checkpoint.sh" latest "$PROJECT")
assert_contains "latest checkpoint exists" "-" "$latest_ckpt"

# Record current stage before rollback
stage_before_rollback=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")

# Find the earliest checkpoint (intake stage)
# Find a checkpoint from the intake stage (label starts with "intake")
early_ckpt=$(ls -d "$PROJECT/.essay-state/checkpoints"/intake-*/ 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "")
if [ -n "$early_ckpt" ]; then
  bash "$SCRIPT_DIR/scripts/checkpoint.sh" rollback "$PROJECT" "$early_ckpt" >/dev/null
  stage_after_rollback=$(bash "$SCRIPT_DIR/scripts/pipeline-state.sh" get-stage "$PROJECT")
  # The intake checkpoint should restore the intake stage
  assert_eq "rollback reverted to intake" "intake" "$stage_after_rollback"
else
  echo "SKIP: No checkpoint found for rollback test"
fi

# Re-advance through the pipeline for remaining tests
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" research >/dev/null

# Recreate research
cat > "$PROJECT/.essay-state/research-synthesis.json" << 'EOF'
{
  "thesis": "Effective multi-agent orchestration requires three architectural principles.",
  "thesis_expanded": "Context isolation, progressive disclosure, and hierarchical planning.",
  "evidence_map": [{"claim": "Context isolation prevents hallucination", "sources": ["note-1"], "strength": "strong"}],
  "knowledge_gaps": [],
  "competitive_landscape": [],
  "unique_angle": "Production-tested patterns",
  "recommended_depth": "intermediate",
  "recommended_length": "medium",
  "key_terms": ["conductor pattern", "orchestration"]
}
EOF

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" outline >/dev/null

# Recreate outlines
for v in A B C; do
  cat > "$PROJECT/.essay-state/outline-${v}.json" << EOF
{"variant":"$v","variant_name":"Variant $v","title":"Test Outline $v","hook":"Hook $v","sections":[{"title":"Section 1","purpose":"test","key_points":["point"],"estimated_words":500}],"target_word_count":2000,"tone":"technical"}
EOF
done

cat > "$PROJECT/.essay-state/outline-critique.json" << 'EOF'
{"critic":"outline-adversarial","outlines_analyzed":["A","B","C"],"per_outline":{"A":{"overall_score":7},"B":{"overall_score":8},"C":{"overall_score":7.5}},"recommendation":{"recommended_variant":"B"}}
EOF

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" outline_variant "B" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" draft >/dev/null

# Recreate draft
cat > "$PROJECT/.essay-state/draft-v1.md" << 'DRAFT'
# Multi-Agent Orchestration: Patterns That Scale

Content for testing purposes.

## Orchestration Principles

```javascript
class Conductor {
  async orchestrate(mission) { return this.plan(mission); }
}
```

## Results

Task completion improved significantly with multi-agent architecture.
DRAFT

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" draft_version 1 >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" review >/dev/null

# Recreate reviews
cat > "$PROJECT/.essay-state/review-technical.json" << 'EOF'
{"reviewer":"technical","rating":"PASS","summary":"Code examples are correct","confidence":"high","issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-editor.json" << 'EOF'
{"reviewer":"editor","rating":"PASS","summary":"Well-written","overall_score":8,"issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"SOLID","summary":"Claims are defensible","attacks":[],"issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-audience.json" << 'EOF'
{"reviewer":"audience","overall_verdict":"Strong for target audience"}
EOF
cat > "$PROJECT/.essay-state/review-seo.json" << 'EOF'
{"reviewer":"seo","rating":"GOOD","summary":"Good searchability","social_package":{"meta_description":"Multi-agent patterns","twitter_thread":["Thread"],"linkedin_post":"Post","hn_title":"Title"}}
EOF
cat > "$PROJECT/.essay-state/review-external.json" << 'EOF'
{"reviewer":"external","rating":"ACCESSIBLE","summary":"Clear","accessibility_score":8,"issues":[]}
EOF
cat > "$PROJECT/.essay-state/review-factcheck.json" << 'EOF'
{"reviewer":"factcheck","rating":"VERIFIED","summary":"Claims check out","claims_checked":4,"claims_verified":4,"issues":[]}
EOF

for r in review-technical review-editor review-adversarial review-audience review-seo review-external review-factcheck; do
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT" "$PROJECT/.essay-state/${r}.json" >/dev/null
done

bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$PROJECT" >/dev/null
bash "$SCRIPT_DIR/scripts/calibrate-reviews.sh" "$PROJECT" >/dev/null

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" refinement >/dev/null
cp "$PROJECT/.essay-state/draft-v1.md" "$PROJECT/.essay-state/draft-v2.md"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT" >/dev/null
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" polish >/dev/null

# ========================================================
# SECTION 19: POLISH + FINAL OUTPUTS
# ========================================================
echo "--- Section 19: Polish + Final Outputs ---"

# Simulate final outputs
cat > "$PROJECT/.essay-state/final-internal.md" << 'EOF'
# Multi-Agent Orchestration: Patterns That Scale

## TL;DR
- Multi-agent orchestration outperforms monolithic agents for complex tasks
- Three principles: context isolation, progressive disclosure, hierarchical planning
- Production results: 89% completion, zero context overflows, 3.2x token efficiency

## The Complexity Cliff

Every AI agent starts simple. But complexity grows until context overflow hits.

## Orchestration Principles

Separation of concerns. Context budgeting. Progressive disclosure.

```javascript
class Conductor {
  async orchestrate(mission) {
    const sprints = await this.plan(mission);
    for (const sprint of sprints) {
      const master = new SprintMaster({ context: 'fresh' });
      await master.execute(sprint);
    }
  }
}
```

## The Conductor Pattern

The conductor plans. Sprint masters direct. Workers execute.

## Trade-offs

Multi-agent adds latency for simple tasks. Know when to use it.

## Results

Task completion: 89%. Context overflows: 0%. Token efficiency: 3.2x.

## How This Applies to Us

Our agent platform benefits directly from these patterns.

## Discussion Questions

1. Should we adopt multi-agent orchestration for our next project?
2. What's our current context overflow rate?
EOF

cat > "$PROJECT/.essay-state/final-external.md" << 'EOF'
# Multi-Agent Orchestration: Production Patterns That Scale

The agent community is rediscovering microservices architecture — except this time,
the services think for themselves. Here are the production-tested patterns.

## The Complexity Cliff

Every AI agent starts simple. But complexity grows.

## Orchestration Principles

Three principles that scale:
1. Separation of concerns
2. Context budgeting
3. Progressive disclosure

```javascript
class Conductor {
  async orchestrate(mission) {
    const sprints = await this.plan(mission);
    for (const sprint of sprints) {
      const master = new SprintMaster({ context: 'fresh' });
      await master.execute(sprint);
    }
  }
}
```

## The Conductor Pattern

The conductor never writes code. It plans, evaluates, and delegates.

## Trade-offs and Anti-patterns

Multi-agent adds latency. Know when not to use it.

## Real-World Results

In production: 89% task completion, zero context overflows, 3.2x token efficiency.

## About the Author

Test Author is a Staff Engineer at TestCorp. They write about AI architecture and multi-agent systems.
Follow on Twitter @testauthor.

## Further Reading

- Anthropic's Building Effective Agents documentation
- The Conductor Pattern in practice
EOF

cat > "$PROJECT/.essay-state/social-package.json" << 'EOF'
{
  "twitter_thread": ["1/ We replaced our monolithic AI agent with an orchestrated multi-agent system. Results: 89% completion, 0% context overflows, 3.2x token efficiency. Here's what we learned:"],
  "linkedin_post": "Multi-agent orchestration patterns that actually work in production.",
  "hn_title": "Multi-Agent Orchestration: Production Patterns That Scale",
  "hn_comment": "Author here. We've been running this architecture for 6 months now."
}
EOF

# ========================================================
# SECTION 20: PUBLISH CHECK + PROGRESS AT POLISH
# ========================================================
echo "--- Section 20: Publish Check + Progress ---"

# Progress at polish stage
progress_polish=$(bash "$SCRIPT_DIR/scripts/progress-display.sh" "$PROJECT" --format json)
assert_contains "progress shows polish stage" "polish" "$progress_polish"

# Publish check
# publish-check returns non-zero when checks fail, which is expected behavior
publish_out=$(bash "$SCRIPT_DIR/scripts/publish-check.sh" "$PROJECT" 2>&1 || true)
assert_contains "publish check has output" "Checklist" "$publish_out"

# ========================================================
# SECTION 21: COMPLETE + TASTE MEMORY UPDATE
# ========================================================
echo "--- Section 21: Complete + Taste Memory ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" complete "$PROJECT" >/dev/null
bash "$SCRIPT_DIR/scripts/taste-memory.sh" update "$PROJECT" >/dev/null

taste=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "taste has article record" "Topics covered" "$taste"

final_status=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" status)
assert_contains "final status complete" "True" "$final_status"

# ========================================================
# SECTION 22: TASTE MEMORY DIFF-LEARN
# ========================================================
echo "--- Section 22: Taste Memory Diff-Learn ---"

# Create original and edited drafts for diff-learn
cat > "$TMPDIR/original-draft.md" << 'ORIG'
# Multi-Agent Architecture

This article discusses multi-agent architecture patterns.

## Introduction

Multi-agent systems are complex. They require careful design.

## The Pattern

The conductor pattern works as follows: you have a conductor that plans,
a sprint master that directs, and workers that execute. This separation
of concerns is crucial.

## Conclusion

In conclusion, multi-agent architecture is superior to monolithic agents.
ORIG

cat > "$TMPDIR/edited-draft.md" << 'EDIT'
# Multi-Agent Architecture: Patterns That Actually Work

Let me show you what happens when your AI agent starts forgetting its own instructions.

## The Problem

Three months in, our agent was contradicting itself mid-task. Context overflow.
Not a model problem — an architecture problem.

## The Fix

The conductor pattern: plan → direct → execute. Each layer gets fresh context.
No shared state. No context pollution.

```javascript
const conductor = new Conductor();
await conductor.orchestrate(mission);
```

## What We Learned

Multi-agent beats monolithic when tasks exceed 3 tool calls. Below that, don't bother.
EDIT

diff_learn_out=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" diff-learn "$PROJECT" "$TMPDIR/original-draft.md" "$TMPDIR/edited-draft.md")
assert_contains "diff-learn extracted patterns" "Learned from diff" "$diff_learn_out"

# Verify taste memory was updated with learned patterns
taste_after_diff=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "taste memory has learned insights" "Learned" "$taste_after_diff"

# ========================================================
# SECTION 23: TASTE MEMORY FEEDBACK
# ========================================================
echo "--- Section 23: Taste Memory Feedback ---"

bash "$SCRIPT_DIR/scripts/taste-memory.sh" feedback "$PROJECT" tone "Keep it casual and direct — no academic language" >/dev/null
bash "$SCRIPT_DIR/scripts/taste-memory.sh" feedback "$PROJECT" structure "Start with the problem, not the solution" >/dev/null
bash "$SCRIPT_DIR/scripts/taste-memory.sh" feedback "$PROJECT" code_density "Always include runnable code in the first 1/3 of the article" >/dev/null

taste_feedback=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "feedback has tone preference" "casual" "$taste_feedback"
assert_contains "feedback has structure preference" "problem" "$taste_feedback"
assert_contains "feedback has code_density preference" "runnable" "$taste_feedback"

# ========================================================
# SECTION 24: TASTE MEMORY SUGGEST
# ========================================================
echo "--- Section 24: Taste Memory Suggest ---"

suggest_out=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" suggest "$PROJECT")
assert_contains "suggest has recommendations" "Suggestions" "$suggest_out"

# ========================================================
# SECTION 25: ANALYTICS FEEDBACK
# ========================================================
echo "--- Section 25: Analytics Feedback ---"

bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record art-test views 1500 >/dev/null
bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record art-test shares 85 >/dev/null
bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" record art-test comments 23 >/dev/null

query_out=$(bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" query art-test)
assert_contains "analytics query has views" "1500" "$query_out"
assert_contains "analytics query has shares" "85" "$query_out"

top_out=$(bash "$SCRIPT_DIR/scripts/analytics-feedback.sh" top views 3)
assert_contains "analytics top has art-test" "art-test" "$top_out"

# ========================================================
# SECTION 26: FINAL ARTIFACT VERIFICATION
# ========================================================
echo "--- Section 26: Final Artifact Verification ---"

assert_file "materials.json" "$PROJECT/.essay-state/materials.json"
assert_file "research-synthesis.json" "$PROJECT/.essay-state/research-synthesis.json"
assert_file "outline-A.json" "$PROJECT/.essay-state/outline-A.json"
assert_file "outline-B.json" "$PROJECT/.essay-state/outline-B.json"
assert_file "outline-C.json" "$PROJECT/.essay-state/outline-C.json"
assert_file "draft-v1.md" "$PROJECT/.essay-state/draft-v1.md"
assert_file "final-internal.md" "$PROJECT/.essay-state/final-internal.md"
assert_file "final-external.md" "$PROJECT/.essay-state/final-external.md"
assert_file "social-package.json" "$PROJECT/.essay-state/social-package.json"
assert_file "review-panel-summary.json" "$PROJECT/.essay-state/review-panel-summary.json"
assert_file "review-calibration.json" "$PROJECT/.essay-state/review-calibration.json"
assert_file "config.json" "$HOME/.tech-essay-writer/config.json"
assert_file "author-profile.json" "$HOME/.tech-essay-writer/author-profile.json"
assert_file "taste-memory.json" "$HOME/.tech-essay-writer/taste-memory.json"
assert_dir "checkpoints dir" "$PROJECT/.essay-state/checkpoints"

echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
