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
echo "SKILL_DIR=$SKILL_DIR"
echo "PROJECT_DIR=$PROJECT_DIR"

# Initialize state
mkdir -p .essay-state
bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" status 2>/dev/null || echo "Fresh start."
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
```

### Stage 2: RESEARCH SYNTHESIS

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

```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-field "$PROJECT_DIR" draft_version 1
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$PROJECT_DIR" review
```

### Stage 5: ADVERSARIAL REVIEW PANEL (7 Parallel Agents)

This is the core quality mechanism. Launch 7 independent reviewers in parallel.
Each gets FRESH CONTEXT — no knowledge of other reviewers.

```bash
PROMPT_TECH=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts technical)
PROMPT_EDIT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts editor)
PROMPT_ADV=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts adversarial)
PROMPT_AUD=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts audience)
PROMPT_SEO=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts seo)
PROMPT_EXT=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts external)
PROMPT_FC=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts factcheck)
```

Launch ALL SEVEN via Agent tool in a SINGLE message:
```
Agent(description="Technical review", prompt=PROMPT_TECH)
Agent(description="Editorial review", prompt=PROMPT_EDIT)
Agent(description="Adversarial review", prompt=PROMPT_ADV)
Agent(description="Audience proxy review", prompt=PROMPT_AUD)
Agent(description="SEO/reach review", prompt=PROMPT_SEO)
Agent(description="External perspective review", prompt=PROMPT_EXT)
Agent(description="Fact-checking review", prompt=PROMPT_FC)
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

3. After refinement, re-run ONLY the adversarial reviewer on the new draft:
```bash
PROMPT_ADV=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" build-review-prompts adversarial)
```
```
Agent(description="Adversarial re-review", prompt=PROMPT_ADV)
```

4. Check convergence:
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

Run publish readiness check:
```bash
bash "$SKILL_DIR/scripts/publish-check.sh" "$PROJECT_DIR"
```

**Final checkpoint:** Present both versions, platform outputs, social package, and publish readiness.
"Article complete! Quality score: X/10. Review all versions. Any adjustments?"

### Completion

After user approves:
```bash
bash "$SKILL_DIR/scripts/taste-memory.sh" update "$PROJECT_DIR"
bash "$SKILL_DIR/scripts/pipeline-state.sh" complete "$PROJECT_DIR"
bash "$SKILL_DIR/scripts/expertise-graph.sh" update "<topic>" "<tag1> <tag2>"
```

After publishing, register the article for future cross-referencing:
```bash
bash "$SKILL_DIR/scripts/cross-reference.sh" add "<title>" "<published_url>" "<tag1> <tag2>"
```

## Resume Support

If invoked with "resume":
```bash
STAGE=$(bash "$SKILL_DIR/scripts/orchestrate.sh" "$PROJECT_DIR" "$SKILL_DIR" next-stage)
```
Jump to that stage's execution block above.

## Error Handling

- Reviewer agent fails → skip it, note in summary, continue with remaining reviews
- Writer produces < 500 words → re-dispatch with "The draft is too short. Write the COMPLETE article."
- All 3 outlines too similar → re-dispatch with explicit differentiation instructions
- Refinement doesn't converge in 3 rounds → present best version with reviewer caveats
- Any agent fails to write output file → read agent response, write file yourself

## Boundaries

- Never publish or push content — only generate files for user review
- Never fabricate technical claims — if materials don't support a claim, flag it
- Never skip the adversarial review — it's the core quality gate
- User approves at every checkpoint before advancing
