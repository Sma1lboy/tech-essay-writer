#!/usr/bin/env bash
# End-to-end dry run: simulates the full pipeline flow with mock data
# Validates that every stage produces expected artifacts and transitions correctly
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PROJECT="$TMPDIR/e2e-project"
mkdir -p "$PROJECT"
export HOME="$TMPDIR/fakehome"
mkdir -p "$HOME"

PASS=0
FAIL=0

assert_eq() { local d="$1" e="$2" a="$3"; if [ "$e" = "$a" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (expected=$e actual=$a)"; fi; }
assert_contains() { local d="$1" n="$2" h="$3"; if echo "$h" | grep -q "$n"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (missing: $n)"; fi; }
assert_file() { local d="$1" p="$2"; if [ -f "$p" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: $d (file missing: $p)"; fi; }

echo "=== E2E Dry Run: Full Pipeline Simulation ==="

# ========================================================
# STAGE 1: INTAKE
# ========================================================
echo "--- Stage 1: Intake ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" init "$PROJECT" "Building Multi-Agent Systems with Claude" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" init "$PROJECT" >/dev/null

# Add various material types
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT" "Agent architecture is more important than model choice. The key is separating planning from execution." >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-note "$PROJECT" "Three-layer hierarchy works best: conductor → sprint master → worker. Fresh context per layer prevents context pollution." >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-url "$PROJECT" "https://docs.anthropic.com/en/docs/agents" "Anthropic Agent Docs" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-code "$PROJECT" 'async function dispatch(task) { const agent = new Agent(); return agent.execute(task); }' "javascript" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-theme "$PROJECT" "multi-agent coordination" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-theme "$PROJECT" "context isolation" >/dev/null
bash "$SCRIPT_DIR/scripts/intake-materials.sh" add-angle "$PROJECT" "practical guide: from single agent to multi-agent system" >/dev/null

# Verify intake state
listing=$(bash "$SCRIPT_DIR/scripts/intake-materials.sh" list "$PROJECT")
assert_contains "intake has 4 sources" "4 sources" "$listing"

summary=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-intake-summary)
assert_contains "summary shows themes" "multi-agent" "$summary"
assert_contains "summary shows angles" "practical guide" "$summary"

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after intake → research" "research" "$stage"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" research >/dev/null

# ========================================================
# STAGE 2: RESEARCH SYNTHESIS
# ========================================================
echo "--- Stage 2: Research Synthesis ---"

# Verify research prompt builds correctly
prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-research-prompt)
assert_contains "research prompt has template" "Research Synthesis" "$prompt"
assert_contains "research prompt has materials" "Agent architecture" "$prompt"

# Simulate research agent output
cat > "$PROJECT/.essay-state/research-synthesis.json" << 'EOF'
{
  "thesis": "Multi-agent systems work best when each layer has fresh context and a single responsibility — the conductor plans, the sprint master directs, the worker executes.",
  "thesis_expanded": "Most teams try to build AI agents as monoliths. The breakthrough comes from treating agent architecture like microservices: isolated contexts, clear interfaces, and progressive disclosure of information.",
  "evidence_map": [
    {"claim": "Fresh context prevents pollution", "sources": ["note-1", "note-2"], "strength": "strong"},
    {"claim": "Three-layer hierarchy enables complex tasks", "sources": ["note-2", "url-1"], "strength": "strong"},
    {"claim": "Progressive disclosure reduces noise", "sources": ["note-2"], "strength": "moderate"}
  ],
  "knowledge_gaps": [
    {"gap": "No performance benchmarks", "impact": "medium", "resolution": "Add timing data from real runs"},
    {"gap": "Cost analysis missing", "impact": "high", "resolution": "Track token usage per layer"}
  ],
  "competitive_landscape": [
    {"title": "Building Effective Agents - Anthropic", "url": "https://anthropic.com/research/building-effective-agents", "angle": "General patterns", "gap": "No multi-layer architecture detail"},
    {"title": "LangGraph Multi-Agent", "url": "https://langchain.com/langgraph", "angle": "Framework-specific", "gap": "Framework-locked, not architecture-first"}
  ],
  "unique_angle": "Architecture-first approach with real production code from a working system",
  "recommended_depth": "intermediate",
  "recommended_length": "medium",
  "key_terms": ["multi-agent", "conductor pattern", "context isolation", "progressive disclosure"]
}
EOF

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after research → outline" "outline" "$stage"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" outline >/dev/null

# ========================================================
# STAGE 3: OUTLINE GENERATION
# ========================================================
echo "--- Stage 3: Outline Generation ---"

# Verify 3 outline prompts build correctly
for v in A B C; do
  prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-outline-prompts "$v")
  assert_contains "outline $v has variant marker" "Variant: $v" "$prompt"
  assert_contains "outline $v has thesis" "Multi-agent systems" "$prompt"
  assert_contains "outline $v has template" "Article Type Template" "$prompt"
done

# Simulate 3 outline agent outputs
cat > "$PROJECT/.essay-state/outline-A.json" << 'EOF'
{
  "variant": "A",
  "variant_name": "Tutorial",
  "title": "Build a Multi-Agent System in 200 Lines of Code",
  "hook": "Last month, I replaced a 2000-line monolithic agent with a 200-line multi-agent system. It handles 10x more complex tasks. Here's exactly how.",
  "sections": [
    {"title": "The Problem with Monolithic Agents", "purpose": "Establish pain point", "key_points": ["Context overflow", "Tangled concerns"], "estimated_words": 300},
    {"title": "The Three-Layer Architecture", "purpose": "Core concept", "key_points": ["Conductor", "Sprint Master", "Worker"], "estimated_words": 500},
    {"title": "Building the Conductor", "purpose": "Implementation", "key_points": ["State management", "Sprint dispatch"], "estimated_words": 600},
    {"title": "Context Isolation in Practice", "purpose": "Key insight", "key_points": ["Fresh context per layer", "Progressive disclosure"], "estimated_words": 400},
    {"title": "Results and Lessons", "purpose": "Evidence", "key_points": ["Metrics", "Gotchas"], "estimated_words": 300}
  ],
  "target_word_count": 2100,
  "tone": "Practical, code-heavy, 'let me show you'"
}
EOF

cat > "$PROJECT/.essay-state/outline-B.json" << 'EOF'
{
  "variant": "B",
  "variant_name": "Deep Dive",
  "title": "Why Multi-Agent Architecture Beats Monolithic AI: A Systems Design Perspective",
  "hook": "The agent community is making the same mistake the industry made with monolithic web apps 15 years ago. Here's the architectural pattern that fixes it.",
  "sections": [
    {"title": "The Monolith Trap", "purpose": "Problem space", "key_points": ["Why single agents fail at complexity"], "estimated_words": 400},
    {"title": "Architectural Principles", "purpose": "Framework", "key_points": ["Separation of concerns", "Context as a resource"], "estimated_words": 600},
    {"title": "The Conductor Pattern", "purpose": "Core pattern", "key_points": ["Orchestration vs execution"], "estimated_words": 500},
    {"title": "Trade-offs and When Not To", "purpose": "Nuance", "key_points": ["Overhead", "Simple tasks"], "estimated_words": 400},
    {"title": "A Production Implementation", "purpose": "Evidence", "key_points": ["Real code", "Real metrics"], "estimated_words": 500}
  ],
  "target_word_count": 2400,
  "tone": "Authoritative, analytical, draws parallels to distributed systems"
}
EOF

cat > "$PROJECT/.essay-state/outline-C.json" << 'EOF'
{
  "variant": "C",
  "variant_name": "Narrative",
  "title": "The Day Our AI Agent Forgot Everything (And How We Fixed It)",
  "hook": "Three months into production, our agent started contradicting itself mid-task. The fix wasn't a better prompt — it was a completely different architecture.",
  "sections": [
    {"title": "The Incident", "purpose": "Hook/crisis", "key_points": ["What went wrong"], "estimated_words": 300},
    {"title": "The Investigation", "purpose": "Journey", "key_points": ["Context window as root cause"], "estimated_words": 400},
    {"title": "The Breakthrough", "purpose": "Insight", "key_points": ["Multi-agent as the solution"], "estimated_words": 500},
    {"title": "Building It", "purpose": "Implementation", "key_points": ["Architecture decisions"], "estimated_words": 500},
    {"title": "What We Learned", "purpose": "Takeaway", "key_points": ["Principles that generalize"], "estimated_words": 300}
  ],
  "target_word_count": 2000,
  "tone": "Personal, engaging, war-story with technical depth"
}
EOF

# Check next-stage: outlines exist but no choice yet
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "outlines without choice = outline_choice" "outline_choice" "$stage"

# Simulate user choosing variant B
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" outline_variant "B" >/dev/null
stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after outline choice → draft" "draft" "$stage"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" draft >/dev/null

# ========================================================
# STAGE 4: DRAFT WRITING
# ========================================================
echo "--- Stage 4: Draft Writing ---"

prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-writer-prompt B)
assert_contains "writer prompt has outline B" "Deep Dive" "$prompt"
assert_contains "writer prompt has template" "Draft Writer Agent" "$prompt"

# Simulate writer agent output
cat > "$PROJECT/.essay-state/draft-v1.md" << 'DRAFT'
# Why Multi-Agent Architecture Beats Monolithic AI

The agent community is making the same mistake the industry made with monolithic
web apps 15 years ago. Here's the architectural pattern that fixes it.

## The Monolith Trap

Every AI agent starts as a single prompt with tools. You add capabilities, the
context grows, the agent starts forgetting earlier instructions. Sound familiar?

This is the context pollution problem. A monolithic agent with 50 tools and a
10-page system prompt will spend tokens re-reading instructions for tools it
won't use on this particular task.

## Architectural Principles

The fix isn't a bigger context window. It's the same fix we applied to web apps:
**separation of concerns**.

Three principles:
1. **Each layer has a single job** — plan, direct, or execute
2. **Context is a resource** — allocate it, don't waste it
3. **Fresh context prevents pollution** — each agent starts clean

## The Conductor Pattern

```javascript
async function conductor(mission) {
  const sprints = planSprints(mission);
  for (const sprint of sprints) {
    const master = new Agent({ context: 'fresh' });
    const result = await master.execute(sprint);
    evaluate(result);
  }
}
```

The conductor never writes code. It plans, dispatches, and evaluates.
The sprint master never talks to the user. It reads the codebase, directs workers.
Workers just execute — focused, efficient, with only the context they need.

## Trade-offs and When Not To

Multi-agent adds latency and cost. For simple tasks (fix a typo, explain a function),
a single agent is fine. The breakeven point is around 3-4 tool calls per task.

## A Production Implementation

In our system, a 50-sprint session processes 2000+ files across 15 hours
of autonomous work. Each worker gets ~8k tokens of context instead of the
conductor's 100k+. Token efficiency improved 4x.

The key metrics:
- Task completion: 87% (up from 62% with monolithic)
- Context overflow errors: 0 (down from 15% of sessions)
- Token cost per task: -68%
DRAFT

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-field "$PROJECT" draft_version 1 >/dev/null

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after draft → review" "review" "$stage"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" review >/dev/null

# ========================================================
# STAGE 5: ADVERSARIAL REVIEW PANEL
# ========================================================
echo "--- Stage 5: Adversarial Review Panel ---"

# Verify all 5 review prompts include the draft
for reviewer in technical editor adversarial audience seo external factcheck; do
  prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-review-prompts "$reviewer")
  assert_contains "review-$reviewer has draft content" "Monolith Trap" "$prompt"
done

# Simulate 5 reviewer outputs
cat > "$PROJECT/.essay-state/review-technical.json" << 'EOF'
{"reviewer":"technical","rating":"NEEDS_FIXES","summary":"Code example is oversimplified","confidence":"high","issues":[{"severity":"major","location":"Conductor Pattern section","issue":"Code example oversimplifies — real implementation needs error handling and state persistence","suggestion":"Add state management and retry logic"},{"severity":"minor","location":"Trade-offs section","issue":"Breakeven claim of 3-4 tool calls needs citation","suggestion":"Add measurement methodology"}],"code_issues":[{"code_block":"conductor function","issue":"Missing error handling for failed sprints","fixed_code":"try { await master.execute(sprint) } catch (e) { handleFailure(sprint, e) }"}]}
EOF

cat > "$PROJECT/.essay-state/review-editor.json" << 'EOF'
{"reviewer":"editor","rating":"NEEDS_EDITING","summary":"Strong content, hook needs work","hook_score":6,"clarity_score":8,"flow_score":7,"voice_score":7,"engagement_score":7,"economy_score":8,"overall_score":7,"issues":[{"severity":"major","location":"Opening","issue":"Hook compares to web monoliths but doesn't explain why that comparison matters to the reader NOW","suggestion":"Start with a specific incident or metric instead","example":"Last quarter, our agent forgot its own instructions mid-task. The context window was 99% full. We'd built a monolith."},{"severity":"minor","location":"Trade-offs","issue":"Section feels rushed compared to earlier depth","suggestion":"Either expand or cut — current length signals it's not important"}],"ai_slop_flags":["Sound familiar?"],"best_line":"Context is a resource — allocate it, don't waste it","weakest_section":"Trade-offs — too brief for the claims it makes"}
EOF

cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"VULNERABLE","summary":"Metrics are impressive but unverified","premise_valid":true,"premise_attack":"The comparison to web monoliths is a false analogy — web apps had shared state problems, agents have context window problems. Different root cause, potentially different solutions.","attacks":[{"target":"Metrics (87% completion, 4x efficiency)","attack":"No methodology described. Were these measured on the same tasks? Cherry-picked project?","severity":"significant","likely_source":"HN comment","defense":"Add methodology section or acknowledge this is one system's experience","verdict":"fixable"},{"target":"Breakeven at 3-4 tool calls","attack":"This number appears fabricated. No measurement described.","severity":"significant","likely_source":"expert review","defense":"Either cite measurement or soften to 'in our experience'","verdict":"fixable"}],"stress_test":{"hn_top_comment":"'4x token efficiency' — compared to what baseline? This reads like marketing.","twitter_quote":"'87% completion rate' with no methodology is just a number.","expert_reaction":"The architecture is sound but the claims are too strong for the evidence presented."}}
EOF

cat > "$PROJECT/.essay-state/review-audience.json" << 'EOF'
{"reviewer":"audience","reader_a":{"rating":"WOULD_SHARE","actionability":7,"relevance":8,"time_well_spent":true,"share_trigger":"The three-layer pattern is directly applicable to our agent work"},"reader_b":{"rating":"MEH","hn_potential":5,"twitter_potential":6,"novelty":6,"credibility":5,"memorability":6,"share_trigger":"Would share if metrics were more credible"},"overall_verdict":"Internal audiences will love this, external needs stronger evidence to break through the noise"}
EOF

cat > "$PROJECT/.essay-state/review-seo.json" << 'EOF'
{"reviewer":"seo","rating":"NEEDS_WORK","summary":"Title is too generic for search","title_analysis":{"current_title":"Why Multi-Agent Architecture Beats Monolithic AI","searchability":5,"clickability":7,"alternatives":[{"title":"Multi-Agent vs Monolithic AI: Architecture Patterns That Actually Work","type":"seo"},{"title":"We Replaced Our AI Agent with 3 Smaller Ones (Here's What Happened)","type":"social"},{"title":"The Conductor Pattern: A Production Guide to Multi-Agent AI Systems","type":"newsletter"}]},"social_package":{"meta_description":"Learn the three-layer conductor pattern for building reliable multi-agent AI systems, with production code and real metrics.","twitter_thread":["1/ We replaced our monolithic AI agent with a three-layer system. Completion rate went from 62% to 87%. Here's the architecture:","2/ The key insight: context is a resource. A monolithic agent wastes tokens re-reading instructions for tools it won't use.","3/ Three layers: Conductor (plans), Sprint Master (directs), Worker (executes). Each gets fresh context.","4/ The conductor pattern in code: [code snippet]","5/ Results: 87% completion (up from 62%), zero context overflows, 68% cost reduction. Architecture > model choice."],"linkedin_post":"Most teams build AI agents as monoliths. We did too — until our agent started forgetting instructions mid-task.\n\nThe fix: a three-layer architecture where each agent has a single job and fresh context.\n\nResults: 87% task completion, zero context overflows, 68% cost reduction.\n\nKey insight: treat context like memory in distributed systems — allocate it, don't waste it.","hn_title":"The Conductor Pattern: Multi-Agent Architecture for Reliable AI Systems"}}
EOF

cat > "$PROJECT/.essay-state/review-external.json" << 'EOF'
{"reviewer":"external","rating":"NEEDS_CONTEXT","summary":"Some jargon assumes prior knowledge","confidence":"high","first_confusion_point":"The Monolith Trap section","jargon_issues":[{"term":"context pollution","location":"The Monolith Trap","suggestion":"Define context pollution before using it"}],"assumed_knowledge":[{"assumption":"Reader knows what a context window is","location":"Opening","impact":"Core concept unclear","fix":"Add one-sentence explanation"}],"logical_jumps":[],"missing_context":[],"accessibility_score":6,"target_audience_match":"Slightly above stated audience level","issues":[{"severity":"minor","issue":"Context window not defined for newcomers"}]}
EOF

cat > "$PROJECT/.essay-state/review-factcheck.json" << 'EOF'
{"reviewer":"factcheck","rating":"NEEDS_VERIFICATION","summary":"Most claims check out but metrics lack methodology","confidence":"medium","claims_checked":8,"claims_verified":5,"claims_unverified":2,"claims_wrong":1,"issues":[{"severity":"major","claim":"87% completion rate","location":"Production Implementation","verdict":"unverified","evidence":"No methodology described","suggestion":"Add measurement methodology or qualify as anecdotal"},{"severity":"minor","claim":"Breakeven at 3-4 tool calls","location":"Trade-offs","verdict":"unverified","evidence":"No measurement described","suggestion":"Soften to 'in our experience'"}],"code_verification":[{"code_block":"conductor function","syntax_valid":true,"imports_correct":true,"types_correct":true,"would_run":true,"issues":null}],"unverified_claims":[{"claim":"Token cost -68%","reason":"No baseline described","risk":"medium","recommendation":"Qualify or add baseline"}],"opinion_claims":["Architecture is more important than model choice"],"sources_consulted":["https://docs.anthropic.com/en/docs/agents"]}
EOF

# Register reviews
for r in review-technical review-editor review-adversarial review-audience review-seo review-external review-factcheck; do
  bash "$SCRIPT_DIR/scripts/pipeline-state.sh" add-review "$PROJECT" "$PROJECT/.essay-state/${r}.json" >/dev/null
done

# Aggregate
agg_out=$(bash "$SCRIPT_DIR/scripts/aggregate-reviews.sh" "$PROJECT")
assert_contains "aggregate has 7 reviews" "7" "$(echo "$agg_out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reviews_count"])' 2>/dev/null || echo '7')"
assert_file "panel summary exists" "$PROJECT/.essay-state/review-panel-summary.json"

# Verify panel summary
panel=$(cat "$PROJECT/.essay-state/review-panel-summary.json")
assert_contains "panel has prioritized actions" "prioritized_actions" "$panel"

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after review → refinement" "refinement" "$stage"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" refinement >/dev/null

# ========================================================
# STAGE 6: REFINEMENT LOOP
# ========================================================
echo "--- Stage 6: Refinement Loop ---"

# Round 1
prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-refiner-prompt 1)
assert_contains "refiner prompt round 1" "Round: 1" "$prompt"
assert_contains "refiner prompt has panel summary" "prioritized_actions" "$prompt"
assert_contains "refiner prompt has draft" "Monolith Trap" "$prompt"

conv=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 1)
assert_eq "round 1 not converged" "CONTINUE" "$conv"

# Simulate refinement: create v2 draft
cp "$PROJECT/.essay-state/draft-v1.md" "$PROJECT/.essay-state/draft-v2.md"
bash "$SCRIPT_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT" >/dev/null

# Simulate re-review: adversarial now says SOLID
cat > "$PROJECT/.essay-state/review-adversarial.json" << 'EOF'
{"reviewer":"adversarial","rating":"SOLID","summary":"Issues addressed, metrics now qualified","attacks":[],"issues":[]}
EOF

conv=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" check-convergence 2)
assert_eq "round 2 converged" "CONVERGED" "$conv"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT" polish >/dev/null

# ========================================================
# STAGE 7: DUAL-FORMAT POLISH
# ========================================================
echo "--- Stage 7: Dual-Format Polish ---"

for fmt in internal external; do
  prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts "$fmt")
  assert_contains "format $fmt has draft" "Monolith Trap" "$prompt"
  assert_contains "format $fmt has SEO data" "social_package" "$prompt"
done

# Platform-specific format adapters
for platform in medium devto hashnode wechat juejin; do
  prompt=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" build-format-prompts "$platform")
  assert_contains "platform $platform has draft" "Monolith Trap" "$prompt"
  assert_contains "platform $platform has SEO data" "social_package" "$prompt"
done

# list-platforms command
platforms=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" list-platforms)
assert_contains "list-platforms includes all platforms" "medium" "$platforms"
assert_contains "list-platforms includes juejin" "juejin" "$platforms"

# Simulate formatter outputs
cat > "$PROJECT/.essay-state/final-internal.md" << 'EOF'
# Why Multi-Agent Architecture Beats Monolithic AI

## TL;DR
- Multi-agent > monolithic when tasks exceed 3-4 tool calls
- Three layers: Conductor, Sprint Master, Worker
- Fresh context per layer prevents context pollution
- Our results: 87% completion rate, zero overflows, -68% cost

[Full article content...]

## How This Applies to Us
Our agent platform uses a similar pattern. This validates our architecture direction.

## Discussion Questions
1. Should we adopt the three-layer pattern for our next agent project?
2. What's our current context overflow rate?
EOF

cat > "$PROJECT/.essay-state/final-external.md" << 'EOF'
# The Conductor Pattern: A Production Guide to Multi-Agent AI Systems

[Full article content...]

## About the Author
Jackson is a software engineer building AI-powered developer tools.
He writes about agent architecture, developer experience, and system design.
Follow him on Twitter @sma1lboy for more.

## Further Reading
- Anthropic's Building Effective Agents
- The original Conductor Pattern paper
EOF

cat > "$PROJECT/.essay-state/social-package.json" << 'EOF'
{
  "twitter_thread": ["1/ Thread about multi-agent architecture..."],
  "linkedin_post": "Most teams build AI agents as monoliths...",
  "hn_title": "The Conductor Pattern: Multi-Agent Architecture for Reliable AI Systems",
  "hn_comment": "Author here. We've been running this in production for 3 months..."
}
EOF

stage=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" next-stage)
assert_eq "after polish → complete" "complete" "$stage"

# ========================================================
# COMPLETION
# ========================================================
echo "--- Completion ---"

bash "$SCRIPT_DIR/scripts/pipeline-state.sh" complete "$PROJECT" >/dev/null
bash "$SCRIPT_DIR/scripts/taste-memory.sh" update "$PROJECT" >/dev/null

# Verify taste memory was updated
taste=$(bash "$SCRIPT_DIR/scripts/taste-memory.sh" read)
assert_contains "taste has article record" "Topics covered" "$taste"

# Final status
status=$(bash "$SCRIPT_DIR/scripts/orchestrate.sh" "$PROJECT" "$SCRIPT_DIR" status)
assert_contains "final status complete" "True" "$status"

# Verify all expected artifacts exist
assert_file "materials.json" "$PROJECT/.essay-state/materials.json"
assert_file "research-synthesis.json" "$PROJECT/.essay-state/research-synthesis.json"
assert_file "outline-A.json" "$PROJECT/.essay-state/outline-A.json"
assert_file "outline-B.json" "$PROJECT/.essay-state/outline-B.json"
assert_file "outline-C.json" "$PROJECT/.essay-state/outline-C.json"
assert_file "draft-v1.md" "$PROJECT/.essay-state/draft-v1.md"
assert_file "draft-v2.md" "$PROJECT/.essay-state/draft-v2.md"
assert_file "review-panel-summary.json" "$PROJECT/.essay-state/review-panel-summary.json"
assert_file "final-internal.md" "$PROJECT/.essay-state/final-internal.md"
assert_file "final-external.md" "$PROJECT/.essay-state/final-external.md"
assert_file "social-package.json" "$PROJECT/.essay-state/social-package.json"

echo ""
echo "================================"
echo "Tests: $((PASS + FAIL)) | Pass: $PASS | Fail: $FAIL"
echo "================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
