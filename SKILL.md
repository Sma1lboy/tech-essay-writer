---
name: tech-essay-writer
description: |
  End-to-end tech article writer. From raw materials to polished articles
  for internal company publication and external blog/social posting.
  Multi-agent pipeline with adversarial review and external perspective.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - WebSearch
  - WebFetch
---

# Tech Essay Writer

End-to-end pipeline: raw materials → research → outline → draft → adversarial review → polish → publish-ready articles.

## Startup

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ ! -d "$SKILL_DIR/scripts" ]; then
  for dir in ~/.claude/skills/tech-essay-writer /Users/jacksonc/i/tech-essay-writer; do
    if [ -d "$dir/scripts" ]; then SKILL_DIR="$dir"; break; fi
  done
fi
PROJECT_DIR="$(pwd)"

# Show version
bash "$SKILL_DIR/scripts/version.sh" show

echo "SKILL_DIR=$SKILL_DIR"
echo "PROJECT_DIR=$PROJECT_DIR"

# Initialize state
mkdir -p .essay-state
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" status 2>/dev/null || echo "Fresh start."

# Load user config and show defaults
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-config-summary

# For command reference: bash "$SKILL_DIR/scripts/help.sh"
```

## CRITICAL: Act Immediately

1. Run Startup block
2. If args contain a topic → confirm, begin Stage 1
3. If args say "resume" → check status, resume from current stage
4. If no args → ask ONE question: "What should we write about? Share any materials."

Once you have a direction, **stop talking and start executing**.

## Pipeline Architecture

```
INTAKE → RESEARCH → OUTLINE (3 variants) → DRAFT → REVIEW (7 agents) → REFINE (loop) → POLISH (2 formats)
```

You are the **conductor**. You don't write the article yourself — you dispatch
agents for each stage, evaluate their output, and advance the pipeline.

## How to Execute Each Stage

### Stage 1: INTAKE

Collect the user's raw materials. First, auto-detect input types:
```bash
bash "$SKILL_DIR/scripts/detect-input.sh" "<user's input text>"
```

Then process each detected item:

- **URLs**: Add, then fetch content via WebFetch:
  ```bash
  bash "$SKILL_DIR/scripts/intake-materials.sh" add-url "$PROJECT_DIR" "<url>" "<title>"
  # After fetching: bash "$SKILL_DIR/scripts/update-material.sh" "$PROJECT_DIR" "<id>" "<content>" '<["key point"]>'
  ```
- **Notes/ideas**: 
  ```bash
  bash "$SKILL_DIR/scripts/intake-materials.sh" add-note "$PROJECT_DIR" "<note text>"
  ```
- **Files**: 
  ```bash
  bash "$SKILL_DIR/scripts/intake-materials.sh" add-file "$PROJECT_DIR" "<path>"
  ```
- **Code snippets**: 
  ```bash
  bash "$SKILL_DIR/scripts/intake-materials.sh" add-code "$PROJECT_DIR" "<code>" "<lang>"
  ```

After collecting all materials, analyze them yourself to extract themes and angles:
```bash
bash "$SKILL_DIR/scripts/intake-materials.sh" add-theme "$PROJECT_DIR" "<theme>"
bash "$SKILL_DIR/scripts/intake-materials.sh" add-angle "$PROJECT_DIR" "<angle>"
```

For URLs that need fetching, use WebFetch, then update the material with key_points.

**Series support:** If the user wants this article as part of a series, associate it:
```bash
# List existing series
bash "$SKILL_DIR/scripts/series-manager.sh" list

# Create a new series if needed
bash "$SKILL_DIR/scripts/series-manager.sh" create "<series_name>" "<description>"

# Show details of a specific series
bash "$SKILL_DIR/scripts/series-manager.sh" show "<series_id>"

# Search series by keyword
bash "$SKILL_DIR/scripts/series-manager.sh" search "<query>"

# Associate current article with a series
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" series_id "<series_id>"

# Add the article to the series reading order
bash "$SKILL_DIR/scripts/series-manager.sh" add "<series_id>" "<article_id>" "<title>"

# Set the narrative arc for the series
bash "$SKILL_DIR/scripts/series-manager.sh" set-arc "<series_id>" "<arc_description>"
```
Series context is then auto-injected into outline, writer, and formatter prompts.

**Author profile check:**
```bash
bash "$SKILL_DIR/scripts/author-profile.sh" read
```
If the profile is empty or not initialized, ask: "Want to set up your author profile? (name, bio, social handles)"
This data will be used in formatting and social media package generation.

**Language detection:** After collecting materials, detect or ask the user's language preference.
If the user's materials are primarily in Chinese, or the user communicates in Chinese, set language to `zh`. Otherwise default to `en`.
```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" language "<zh|en>"
```
This setting propagates to all downstream agents — they will produce output in the chosen language.

**Checkpoint:** Show user the materials summary:
```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-intake-summary
```
Ask: "These are the themes and angles I found. Anything to add or emphasize?"

Then advance:
```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" research
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```

### Stage 2: RESEARCH SYNTHESIS

Before dispatching the research agent, generate a structured research brief (questions, competitive landscape queries, unique angles) from the topic:

```bash
bash "$SKILL_DIR/scripts/topic-research.sh" "$PROJECT_DIR" "<topic>"
```

This writes `.essay-state/topic-research.json` with research questions, landscape queries, and angle suggestions that feed into the research agent.

Dispatch a research agent with fresh context:

```bash
RESEARCH_PROMPT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-research-prompt)
```

Launch via Agent tool:
```
Agent(description="Research synthesis", prompt=RESEARCH_PROMPT)
```

The agent will write `.essay-state/research-synthesis.json`.

**Checkpoint:** Read the synthesis, present thesis + unique angle to user.
Ask: "Does this direction feel right?"

Then advance:
```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" outline
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```

### Stage 3: OUTLINE GENERATION (3 Parallel Variants)

Dispatch 3 agents in parallel — each generates a different outline style:

```bash
PROMPT_A=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-outline-prompts A)
PROMPT_B=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-outline-prompts B)
PROMPT_C=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-outline-prompts C)
```

Launch ALL THREE via Agent tool in a SINGLE message (parallel execution):
```
Agent(description="Outline variant A (Tutorial)", prompt=PROMPT_A)
Agent(description="Outline variant B (Deep Dive)", prompt=PROMPT_B)
Agent(description="Outline variant C (Narrative)", prompt=PROMPT_C)
```

**IMPORTANT:** These MUST run in parallel with no cross-influence. Each agent
gets fresh context. This is the design-shotgun pattern from gstack.

After all 3 outlines are generated, dispatch the **outline adversarial critique agent**:

```bash
CRITIQUE_PROMPT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-outline-critique-prompt)
```

Launch via Agent tool:
```
Agent(description="Outline adversarial critique", prompt=CRITIQUE_PROMPT)
```

The agent reads all 3 outlines + research synthesis, critiques each for structural
weaknesses, and recommends the strongest variant. Output: `.essay-state/outline-critique.json`

**Checkpoint:** Read all 3 outlines AND the critique. Present side-by-side summary
with the critic's recommendation to the user.
Ask: "The outline critic recommends variant X because [reason]. Which direction? (A/B/C, or mix elements)"

The critic's recommendation helps inform the user's choice but does NOT override it.

Record the choice:
```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" outline_variant "<chosen>"
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" draft
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```

### Stage 4: DRAFT WRITING

Dispatch the writer agent:

```bash
WRITER_PROMPT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-writer-prompt "<chosen_variant>")
```

Launch via Agent tool:
```
Agent(description="Draft writer", prompt=WRITER_PROMPT)
```

The agent writes `.essay-state/draft-v1.md`.

**Verify:** Read the draft. Check it exists and has reasonable length.
If < 500 words, re-dispatch with stronger instructions.

**Note:** If `series_id` is set, series context (prior articles, narrative arc) is auto-injected into the writer prompt.

```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" draft_version 1
```

#### Draft Quality Checks

Before advancing to review, validate code, analyze readability, check word frequency, and suggest diagrams:

```bash
# Validate code examples in the draft (syntax, imports, fragments)
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-code-validation

# Readability analysis: Flesch-Kincaid grade, sentence/word metrics, passive voice, complexity
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-readability-report verbose

# Word frequency: overused words, jargon density, AI-generated text pattern detection
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-word-analysis 25

# Suggest diagrams/images with Mermaid syntax
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-diagram-suggestions
```

If code validation finds issues, fix them in the draft before proceeding.
If readability is too high (grade > 14) or passive voice is excessive (> 20%), consider simplifying.
If AI pattern detection flags high risk, revise the draft to reduce AI-sounding language.
If diagram suggestions are compelling, note them for the refinement stage.

```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" review
```

### Stage 5: ADVERSARIAL REVIEW PANEL (7 or 8 Parallel Agents)

This is the core quality mechanism. Launch 7 independent reviewers in parallel (or 8 when language=zh, adding the Chinese writing quality reviewer).
Each gets FRESH CONTEXT — no knowledge of other reviewers.

```bash
PROMPT_TECH=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts technical)
PROMPT_EDIT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts editor)
PROMPT_ADV=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts adversarial)
PROMPT_AUD=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts audience)
PROMPT_SEO=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts seo)
PROMPT_EXT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts external)
PROMPT_FC=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts factcheck)

# When language=zh, also dispatch the Chinese writing quality reviewer (8th reviewer)
LANG=$(bash "$SKILL_DIR/scripts/pipeline-state.sh" get-field "$PROJECT_DIR" language)
if [ "$LANG" = '"zh"' ] || [ "$LANG" = 'zh' ]; then
  PROMPT_ZH=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts chinese)
fi
```

Launch ALL SEVEN (or EIGHT for zh) via Agent tool in a SINGLE message:
```
Agent(description="Technical review", prompt=PROMPT_TECH)
Agent(description="Editorial review", prompt=PROMPT_EDIT)
Agent(description="Adversarial review", prompt=PROMPT_ADV)
Agent(description="Audience proxy review", prompt=PROMPT_AUD)
Agent(description="SEO/reach review", prompt=PROMPT_SEO)
Agent(description="External perspective review", prompt=PROMPT_EXT)
Agent(description="Fact-checking review", prompt=PROMPT_FC)
# Only when language=zh:
Agent(description="Chinese writing quality review", prompt=PROMPT_ZH)
```

After all complete, aggregate, score, and calibrate:
```bash
bash "$SKILL_DIR/scripts/aggregate-reviews.sh" "$PROJECT_DIR"
bash "$SKILL_DIR/scripts/quality-score.sh" "$PROJECT_DIR" verbose
bash "$SKILL_DIR/scripts/calibrate-reviews.sh" "$PROJECT_DIR"
```

Read the calibration summary for insights on reviewer agreement and blind spots:
```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-calibration-summary
```

Read the panel summary, quality score, and calibration. If score < 6.0 or any REJECT/REWRITE/WEAK:
**Checkpoint:** "Quality score: X/10. The review panel found issues: [summary]. Calibration: [agreement score, outliers, blind spots]. Proceed with refinement?"

```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" refinement
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```

### Stage 6: REFINEMENT LOOP (Max 3 Rounds)

For each round:

1. Build refiner prompt:
```bash
ROUND=1  # increment each round
REFINER_PROMPT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-refiner-prompt $ROUND)
```

2. Dispatch refiner agent:
```
Agent(description="Refinement round N", prompt=REFINER_PROMPT)
```

3. After refinement, compare the new draft against the previous version:
```bash
# Compare draft versions to see what changed (structure, reading level, word count)
bash "$SKILL_DIR/scripts/article-compare.sh" "$PROJECT_DIR/.essay-state/draft-v1.md" "$PROJECT_DIR/.essay-state/draft-v2.md" --json
```

4. Re-run ONLY the adversarial reviewer on the new draft:
```bash
PROMPT_ADV=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts adversarial)
```
```
Agent(description="Adversarial re-review", prompt=PROMPT_ADV)
```

5. Check convergence:
```bash
RESULT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" check-convergence $ROUND)
```

- `CONVERGED` → exit loop, advance to polish
- `CONTINUE` → increment round, repeat
- `MAX_ROUNDS` → exit loop with best version

```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" refinement-round "$PROJECT_DIR"
```

### Stage 7: DUAL-FORMAT POLISH

Dispatch 2 parallel format agents:

```bash
PROMPT_INT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts internal)
PROMPT_EXT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts external)
```

Launch in parallel:
```
Agent(description="Format internal version", prompt=PROMPT_INT)
Agent(description="Format external version + social", prompt=PROMPT_EXT)
```

Output files:
- `.essay-state/final-internal.md` — company publication version
- `.essay-state/final-external.md` — blog/social publication version  
- `.essay-state/social-package.json` — Twitter thread, LinkedIn post, HN title

### Platform-Specific Adapters (Optional)

After generating the internal/external versions, ask the user which publishing platforms to target:

```bash
# List available platforms:
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" list-platforms
```

Available platforms: `medium`, `devto`, `hashnode`, `wechat`, `juejin`

Ask: "Which platforms should I format for? (medium, dev.to, Hashnode, WeChat公众号, 掘金 — or skip)"

For each chosen platform, build and dispatch in parallel:
```bash
PROMPT_MEDIUM=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts medium)
PROMPT_DEVTO=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts devto)
PROMPT_HASHNODE=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts hashnode)
PROMPT_WECHAT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts wechat)
PROMPT_JUEJIN=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-format-prompts juejin)
```

Launch selected adapters via Agent tool in a SINGLE message (parallel execution):
```
Agent(description="Format Medium version", prompt=PROMPT_MEDIUM)
Agent(description="Format dev.to version", prompt=PROMPT_DEVTO)
Agent(description="Format Hashnode version", prompt=PROMPT_HASHNODE)
Agent(description="Format WeChat version", prompt=PROMPT_WECHAT)
Agent(description="Format Juejin version", prompt=PROMPT_JUEJIN)
```

Platform output files:
- `.essay-state/final-medium.md` — Medium paste-ready version
- `.essay-state/final-devto.md` — dev.to with liquid tag frontmatter
- `.essay-state/final-hashnode.md` — Hashnode with YAML frontmatter
- `.essay-state/final-wechat.md` — WeChat公众号 inline-CSS HTML version (Chinese)
- `.essay-state/final-juejin.md` — 掘金 Markdown version (Chinese)

### Social Media Package (Enhanced)

After formatting, dispatch the social package agent with author context:

```bash
SOCIAL_PROMPT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-social-prompt)
```

Launch via Agent tool:
```
Agent(description="Social media package", prompt=SOCIAL_PROMPT)
```

The agent writes `.essay-state/social-package.json` with Twitter thread, LinkedIn post, 小红书 post, HN title, and author CTAs.

**Note:** If `series_id` is set, series context (reading order, prior articles) is auto-injected into formatter prompts.

### Publishing Guides

For each chosen platform, show step-by-step publishing instructions with SEO tips:

```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" publishing-guide <platform>
```

Platforms: `medium`, `devto`, `hashnode`, `wechat`, `juejin`. Present the guide to the user alongside the formatted output.

### Post-Polish Analysis

After all formatting is complete, assess influence potential and generate SEO data:

```bash
# Predict reach/impact (0-10 across novelty, SEO, social, audience, timing)
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-influence-score verbose

# Generate OpenGraph, meta tags, JSON-LD, keyword density
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-seo-metadata verbose
```

Run publish readiness check:
```bash
bash "$SKILL_DIR/scripts/publish-check.sh" "$PROJECT_DIR"
```

```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```

**Final checkpoint:** Present all versions, social package, quality score, influence score, SEO metadata, and publish readiness.
"Article complete! Quality: X/10. Influence: Y/10. Review all versions. Any adjustments?"

### Completion

After user approves:
```bash
bash "$SKILL_DIR/scripts/taste-memory.sh" update "$PROJECT_DIR"
bash "$SKILL_DIR/scripts/pipeline-state.sh" complete "$PROJECT_DIR"
```

Export the finished article in the user's preferred format:
```bash
# Export all final articles as a bundle (tar.gz)
bash "$SKILL_DIR/scripts/export.sh" "$PROJECT_DIR" bundle ./exports

# Or export as markdown, html, json, or archive to ~/.tech-essay-writer/articles/
bash "$SKILL_DIR/scripts/export.sh" "$PROJECT_DIR" markdown ./output
bash "$SKILL_DIR/scripts/export.sh" "$PROJECT_DIR" archive
```

If the user edited the draft manually, learn from their changes:
```bash
bash "$SKILL_DIR/scripts/taste-memory.sh" diff-learn "$PROJECT_DIR/.essay-state/draft-v1.md" "$PROJECT_DIR/.essay-state/draft-v1-edited.md"
```

Record explicit user feedback with category tagging:
```bash
bash "$SKILL_DIR/scripts/taste-memory.sh" feedback <category> "<text>"
# Categories: tone, structure, vocabulary, length, code_density, format
```

```bash
bash "$SKILL_DIR/scripts/expertise-graph.sh" update "<topic>" "<tag1> <tag2>"
```

Show publishing guides for chosen platforms:
```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" publishing-guide <platform>
```

After publishing, register the article and record analytics:
```bash
bash "$SKILL_DIR/scripts/cross-reference.sh" add "<title>" "<published_url>" "<tag1> <tag2>"
bash "$SKILL_DIR/scripts/analytics-feedback.sh" record "$PROJECT_DIR" "<url>" "<platform>"
```

**Analytics feedback loop:** When the user shares performance data later, track it and feed insights back into taste memory:
```bash
# Record metrics (views, shares, comments, etc.)
bash "$SKILL_DIR/scripts/analytics-feedback.sh" track "<article_id>" views=N shares=N

# Feed performance insights into taste memory for future articles
bash "$SKILL_DIR/scripts/analytics-feedback.sh" feed-taste

# Show performance trends and analytics summary
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-analytics-summary
```
Analytics insights are auto-injected into writer and reviewer prompts via `build-analytics-insights`.

## Help & Version

Show all available scripts with descriptions:
```bash
bash "$SKILL_DIR/scripts/help.sh"                  # List all 38 scripts
bash "$SKILL_DIR/scripts/help.sh" <command>         # Detailed help for a script
bash "$SKILL_DIR/scripts/version.sh"                # Show current version
bash "$SKILL_DIR/scripts/version.sh" bump patch     # Bump version (major/minor/patch)
```

## Dry-Run Mode

Simulate the complete pipeline without LLM agents — useful for testing infrastructure
changes without burning API tokens:

```bash
bash "$SKILL_DIR/scripts/dry-run.sh" "$PROJECT_DIR" "$SKILL_DIR"
bash "$SKILL_DIR/scripts/dry-run.sh" "$PROJECT_DIR" "$SKILL_DIR" --chinese  # zh language mode
```

The dry-run creates mock data at each stage, exercises every script (pipeline-state,
intake, orchestrate prompt builders, reviews, aggregate, calibrate, quality-score,
formatting, social package, checkpoint save/restore, code validation with bad code
detection, etc.), and reports pass/fail per checkpoint. Use `--chinese` to test the
zh language mode which activates the Chinese writing quality reviewer. Use this to
validate that script changes haven't broken the pipeline infrastructure.

## Series Support

For multi-article series:
```bash
# Create a new series
bash "$SKILL_DIR/scripts/series-manager.sh" create "<series_name>" "<description>"

# List all series
bash "$SKILL_DIR/scripts/series-manager.sh" list

# Show series details
bash "$SKILL_DIR/scripts/series-manager.sh" show "<series_id>"

# Add current article to a series
bash "$SKILL_DIR/scripts/series-manager.sh" add "<series_id>" "<article_id>" "<title>"
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" series_id "<series_id>"

# Set the narrative arc
bash "$SKILL_DIR/scripts/series-manager.sh" set-arc "<series_id>" "<arc_description>"

# Set article summary within series
bash "$SKILL_DIR/scripts/series-manager.sh" set-summary "<series_id>" "<article_id>" "<summary>"

# Get next position in the series
bash "$SKILL_DIR/scripts/series-manager.sh" next-position "<series_id>"

# Reorder an article within the series
bash "$SKILL_DIR/scripts/series-manager.sh" reorder "<series_id>" "<article_id>" "<new_position>"

# Search series by keyword
bash "$SKILL_DIR/scripts/series-manager.sh" search "<query>"

# Get series context JSON for prompt injection
bash "$SKILL_DIR/scripts/series-manager.sh" context "<series_id>"

# Series context is auto-injected into outline, writer, and formatter prompts
```

## Configuration

User preferences stored at `~/.tech-essay-writer/config.json`:
```bash
bash "$SKILL_DIR/scripts/config.sh" init            # Initialize defaults
bash "$SKILL_DIR/scripts/config.sh" set language zh  # Set language preference
bash "$SKILL_DIR/scripts/config.sh" add-platform medium  # Add default platform
bash "$SKILL_DIR/scripts/config.sh" read             # Show all config
```

Config values auto-apply to new pipelines (language, max refinement rounds, default platforms).

## Resume Support

If invoked with "resume":
```bash
STAGE=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" resume)
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" show-progress
```
The `resume` command detects the current pipeline state, reports the stage and what's completed, and tells you what to do next. Show progress, then jump to that stage's execution block above.

## Orchestrate.sh Command Reference

All orchestrate.sh commands follow the pattern:
```bash
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" <command> [args...]
```

| Command | Description |
|---------|-------------|
| `status` | Show current pipeline status (stage, topic, draft version, review count) |
| `next-stage` | Determine and output the next stage to execute |
| `build-intake-summary` | Build intake summary for user checkpoint |
| `build-research-prompt` | Build research agent prompt with materials + taste memory |
| `build-outline-prompts <A\|B\|C>` | Build outline agent prompt for a specific variant |
| `build-outline-critique-prompt` | Build outline adversarial critique prompt |
| `build-writer-prompt [variant]` | Build writer agent prompt with chosen outline |
| `build-review-prompts <reviewer>` | Build review prompt (technical/editor/adversarial/audience/seo/external/factcheck) |
| `build-refiner-prompt <round>` | Build refiner agent prompt with round number |
| `build-format-prompts <format>` | Build formatter prompt (internal/external/medium/devto/hashnode/wechat/juejin) |
| `build-social-prompt` | Build social media package agent prompt |
| `build-calibration-summary` | Build human-readable calibration summary |
| `build-influence-score [verbose]` | Compute influence/reach score from state data |
| `build-seo-metadata [verbose]` | Generate SEO metadata (OpenGraph, meta tags, JSON-LD) |
| `build-code-validation` | Validate code examples in the latest draft |
| `build-diagram-suggestions [verbose]` | Suggest diagrams/images with Mermaid syntax |
| `build-readability-report [verbose]` | Compute readability metrics (FK grade, passive voice, complexity) |
| `build-word-analysis [top_n]` | Word frequency, overuse detection, jargon density, AI pattern detection |
| `build-series-context` | Build series context for prompt injection |
| `build-analytics-insights` | Output performance insights from analytics for prompt injection |
| `build-analytics-summary` | Show performance trends and analytics summary |
| `build-config-summary` | Build config context summary for prompt injection |
| `list-platforms` | List all available platform format names |
| `check-convergence <round>` | Check if refinement loop should continue (CONVERGED/CONTINUE/MAX_ROUNDS) |
| `show-progress` | Show rich pipeline progress visualization |
| `publishing-guide <platform>` | Show per-platform publishing workflow guide |
| `list-checkpoints` | List all saved state checkpoints |
| `rollback <id>` | Restore state from a checkpoint |
| `retry-stage <stage>` | Reset and retry a failed stage |
| `resume` | Detect partial state and advise next action |

## Error Handling

- Reviewer agent fails → skip it, note in summary, continue with remaining reviews
- Writer produces < 500 words → re-dispatch with "The draft is too short. Write the COMPLETE article."
- All 3 outlines too similar → re-dispatch with explicit differentiation instructions
- Refinement doesn't converge in 3 rounds → present best version with reviewer caveats
- Any agent fails to write output file → read agent response, write file yourself
- Code validation fails → fix code blocks before advancing to review
- Pipeline interrupted → use checkpoint system to recover:

**Checkpoint system:** State is saved automatically at every stage transition via `pipeline-state.sh`.
```bash
# List all saved checkpoints
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" list-checkpoints

# Rollback to a specific checkpoint
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" rollback <checkpoint_id>

# Retry a failed stage from scratch
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" retry-stage <stage>
```

## Boundaries

- Never publish or push content — only generate files for user review
- Never fabricate technical claims — if materials don't support a claim, flag it
- Never skip the adversarial review — it's the core quality gate
- User approves at every checkpoint before advancing
