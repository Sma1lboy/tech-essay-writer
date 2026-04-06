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
echo "SKILL_DIR=$SKILL_DIR"
echo "PROJECT_DIR=$(pwd)"

# Initialize essay state directory
mkdir -p .essay-state
echo "Tech Essay Writer ready."
```

## First Actions

When invoked, immediately:
1. Run Startup bash block
2. Check if user provided materials/direction in args
3. If yes → confirm in one sentence, begin Pipeline
4. If no → ask: "What topic should we write about? Share any materials (links, notes, code, papers)."

## Pipeline Overview

The pipeline has 7 stages. Each produces artifacts in `.essay-state/`.
The conductor (you) orchestrates agents for each stage.

```
┌─────────┐   ┌───────────┐   ┌──────────┐   ┌─────────┐
│ INTAKE   │──▶│ RESEARCH  │──▶│ OUTLINE  │──▶│  DRAFT  │
│ & PARSE  │   │ SYNTHESIS │   │ VARIANTS │   │  WRITE  │
└─────────┘   └───────────┘   └──────────┘   └─────────┘
                                                   │
                              ┌─────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────┐
│            ADVERSARIAL REVIEW PANEL                      │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────┐│
│  │TECH    │ │EDITOR  │ │DEVIL'S   │ │AUDIENCE│ │SEO/  ││
│  │REVIEW  │ │/STYLE  │ │ADVOCATE  │ │PROXY   │ │REACH ││
│  └────────┘ └────────┘ └──────────┘ └────────┘ └──────┘│
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  REFINEMENT  │◀──┐
                    │    LOOP      │───┘ (max 3 rounds)
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌────────────────┐      ┌────────────────┐
     │   INTERNAL     │      │   EXTERNAL     │
     │   VERSION      │      │   VERSION      │
     │ (company pub)  │      │ (blog/social)  │
     └────────────────┘      └────────────────┘
```

## Stage 1: INTAKE & PARSE

Collect and structure the user's raw materials.

**Input:** User provides any combination of:
- URLs (articles, docs, repos)
- Code snippets
- Personal notes / bullet points
- Academic papers
- Screenshots / diagrams
- Prior conversations or meeting notes

**Process:**
1. For URLs: use WebFetch to retrieve content, extract key sections
2. For code: analyze structure, key patterns, novel approaches
3. For notes: parse into structured themes
4. Save structured materials to `.essay-state/materials.json`

```bash
# State tracking
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$(pwd)" intake
```

**Output:** `.essay-state/materials.json` — structured, indexed materials with:
- `sources[]` — each source with type, content, key_points
- `themes[]` — extracted cross-cutting themes
- `technical_depth` — assessed complexity level
- `potential_angles[]` — initial narrative angle ideas

**User checkpoint:** Show the extracted themes and angles. Ask:
"These are the key themes I found. Any angles you want to emphasize? Any materials I missed?"

## Stage 2: RESEARCH SYNTHESIS

Deep analysis of the structured materials to find the story.

**Dispatch:** Launch a research synthesis agent (fresh context):

```markdown
Agent prompt:
You are a tech research analyst. Given these structured materials, produce:
1. A thesis statement — the ONE key insight this article should convey
2. Supporting evidence map — which materials support which claims
3. Knowledge gaps — what's missing that would strengthen the argument
4. Competitive landscape — what has already been written on this topic
5. Unique angle — what makes THIS article worth reading over existing ones

Materials: [inline from .essay-state/materials.json]

Write your analysis to .essay-state/research-synthesis.json
```

**User checkpoint:** Present the thesis and unique angle. Ask:
"Here's the core thesis and angle. Does this direction feel right?"

## Stage 3: OUTLINE GENERATION (Multi-Variant)

Generate 3 competing outline variants in parallel, like gstack's design-shotgun.

**Dispatch 3 parallel agents**, each with a different framing:

| Variant | Framing | Style |
|---------|---------|-------|
| A | **Tutorial/How-To** | Step-by-step, practical, code-heavy |
| B | **Deep Dive/Analysis** | Conceptual, architectural, opinion-rich |
| C | **Story/Narrative** | Problem→journey→solution, engaging hook |

Each agent receives the research synthesis but generates independently (no cross-influence).

**Output:** `.essay-state/outline-A.json`, `outline-B.json`, `outline-C.json`

Each outline includes:
- `title` — working title
- `hook` — opening 2-3 sentences
- `sections[]` — section title, bullet points, estimated word count
- `key_code_examples[]` — code blocks to include
- `target_word_count` — total
- `tone` — description of voice/style

**User checkpoint:** Present all 3 outlines side-by-side. Ask:
"Which outline direction do you prefer? (A/B/C, or mix elements)"

## Stage 4: DRAFT WRITING

Full article draft from the chosen outline.

**Dispatch writer agent** with:
- Chosen outline
- Research synthesis
- Raw materials for reference
- Taste memory (if exists) for style consistency

```bash
# Load taste memory if available
TASTE=""
if [ -f "$HOME/.tech-essay-writer/taste-memory.json" ]; then
  TASTE=$(cat "$HOME/.tech-essay-writer/taste-memory.json")
fi
```

**Writer agent instructions:**
- Write the COMPLETE article, not a skeleton
- Every code example must be real, runnable, tested
- Use the hook from the outline — don't generic-ify it
- Match the tone specified in the outline
- Include section transitions that maintain narrative flow
- Target word count from outline (±10%)

**Output:** `.essay-state/draft-v1.md` — full article text

## Stage 5: ADVERSARIAL REVIEW PANEL

Launch 5 independent reviewer agents in parallel. Each gets fresh context
(no knowledge of other reviewers). This is the core quality mechanism.

### Reviewer 1: Technical Accuracy
```markdown
You are a senior engineer reviewing a tech article for technical accuracy.
Your job is to find ERRORS, not to praise. Check:
- Code correctness (would it compile/run?)
- Architectural claims (are they sound?)
- Performance claims (are they benchmarked?)
- Missing caveats or edge cases
- Outdated information

Rate: PASS / NEEDS_FIXES / REJECT
Output: .essay-state/review-technical.json
```

### Reviewer 2: Editor / Style
```markdown
You are a professional tech editor. Check:
- Clarity: can a mid-level engineer follow this?
- Flow: do sections connect logically?
- Hook: does the opening grab attention?
- Conclusion: does it land with impact?
- Jargon: is technical language explained or justified?
- Length: is every paragraph earning its place?

Rate: PUBLISH_READY / NEEDS_EDITING / REWRITE
Output: .essay-state/review-editor.json
```

### Reviewer 3: Devil's Advocate (Adversarial)
```markdown
You are an adversarial reviewer. Your ONLY job is to challenge and attack.
- What's the weakest argument in this article?
- Where would a skeptic push back?
- What counterexamples exist?
- Is the author cherry-picking evidence?
- Does the conclusion follow from the evidence?
- Would an expert in this field find anything naive?

You are NOT here to be helpful. You are here to break the article.
If you can't find real issues, say so — don't manufacture fake ones.

Rate: SOLID / VULNERABLE / WEAK
Output: .essay-state/review-adversarial.json
```

### Reviewer 4: Target Audience Proxy
```markdown
You are two readers in one:

READER A — Internal (company engineer):
- Would I forward this to my team?
- Does it teach me something actionable?
- Is it relevant to our tech stack / problems?

READER B — External (tech community):
- Would I upvote this on HN/Reddit?
- Would I share it on Twitter/LinkedIn?
- Does it add to the conversation or just rehash?
- Is the author's credibility established?

Rate each reader: WOULD_SHARE / MEH / SKIP
Output: .essay-state/review-audience.json
```

### Reviewer 5: SEO / Reach Optimizer
```markdown
You are a tech content strategist. Evaluate:
- Title: is it searchable AND clickable? (not clickbait)
- Keywords: are target terms naturally woven in?
- Structure: does it have scannable headers, code blocks, lists?
- Meta description: can you write a compelling 160-char summary?
- Social hooks: what would the tweet/LinkedIn post look like?
- Backlink potential: would other articles link to this?

Generate: 3 alternative title options, meta description, social snippets
Output: .essay-state/review-seo.json
```

**After all 5 complete:** Aggregate reviews into `.essay-state/review-panel-summary.json`

**User checkpoint (if any REJECT/REWRITE/WEAK):**
"The review panel found significant issues: [summary]. Should we proceed with refinement or would you like to adjust the direction?"

## Stage 6: REFINEMENT LOOP

Iterative improvement based on review panel feedback.

**Max 3 rounds.** Each round:

1. **Synthesize** all review feedback into prioritized action items
2. **Dispatch refinement agent** with:
   - Current draft
   - Prioritized issues (most critical first)
   - Original outline (to prevent scope drift)
3. **Re-run adversarial reviewer** (Reviewer 3 only) on refined draft
4. **Check convergence:**
   - If adversarial reviewer says SOLID → done
   - If same issues persist after 2 rounds → flag to user, stop loop
   - If new issues found → another round

```bash
bash "$SKILL_DIR/scripts/pipeline-state.sh" set-stage "$(pwd)" refinement
ROUND=1
MAX_ROUNDS=3
```

**Output:** `.essay-state/draft-v{N}.md` for each round, `.essay-state/refinement-log.json`

## Stage 7: DUAL-FORMAT POLISH & OUTPUT

Generate two publication-ready versions from the refined draft.

### Internal Version
- Add company-specific context where relevant
- Reference internal tools/systems/processes
- Include "how this applies to us" callouts
- Format: clean Markdown suitable for internal wiki/docs/Confluence

### External Version
- Remove any company-specific references
- Add author bio section
- Ensure code examples are self-contained
- Add "About the Author" footer
- Format: Markdown suitable for dev.to, Medium, personal blog

### Social Media Package
- Twitter/X thread (5-7 tweets breaking down key insights)
- LinkedIn post (professional framing, 1-2 paragraphs)
- HN submission title + comment
- One-line description for email newsletters

**Output files:**
- `.essay-state/final-internal.md`
- `.essay-state/final-external.md`
- `.essay-state/social-package.json`

**Final user checkpoint:**
"Article complete! Here are both versions and the social media package.
Review and let me know if you want any adjustments."

## Taste Memory

After the user approves the final article, update taste memory:

```bash
mkdir -p "$HOME/.tech-essay-writer"
bash "$SKILL_DIR/scripts/taste-memory.sh" update "$(pwd)" "$HOME/.tech-essay-writer/taste-memory.json"
```

Record:
- Preferred outline variant (A/B/C) and why
- Feedback patterns (what the user consistently changes)
- Tone preferences
- Structural preferences (long sections vs short, code-heavy vs narrative)
- Topics written about (to avoid repetition, build on expertise)

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/tech-essay-writer` | Start new article from scratch |
| `/tech-essay-writer <topic>` | Start with a topic direction |
| `/tech-essay-writer resume` | Resume in-progress article from `.essay-state/` |

## Error Handling

- If a reviewer agent fails → skip it, note in summary, continue
- If writer agent produces < 50% target word count → re-dispatch with stronger instructions
- If all 3 outline variants are too similar → re-dispatch with more divergent framings
- If refinement loop doesn't converge in 3 rounds → present best version to user with caveats
