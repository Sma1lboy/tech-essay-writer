# tech-essay-writer

Multi-agent tech article writing skill for Claude Code.

## Architecture

7-stage pipeline: Intake → Research → Outline (3 variants) → Draft → Review (5 agents) → Refine (loop) → Polish (2 formats)

Key patterns:
- **Design-shotgun** (from gstack): 3 parallel outline variants with no cross-influence
- **Adversarial review panel**: 5 independent reviewers with fresh context each
- **Refinement loop**: challenge → fix → re-challenge (max 3 rounds)
- **Taste memory**: persistent style preferences across sessions
- **Cross-reference**: track published articles for internal linking

## Directory Structure

```
SKILL.md                    # Main skill definition (conductor prompt)
scripts/
  orchestrate.sh            # Pipeline orchestrator — prompt builders + stage control
  pipeline-state.sh         # Pipeline state management (atomic writes)
  intake-materials.sh       # Material intake (URL/note/file/code/theme/angle)
  aggregate-reviews.sh      # Aggregate 5 review results into panel summary
  build-agent-prompt.sh     # Generic prompt builder with context injection
  taste-memory.sh           # Persistent writing style preferences
  cross-reference.sh        # Published article registry
  fetch-urls.sh             # URL content fetcher
  update-material.sh        # Update material with fetched content
prompts/
  researcher.md             # Research synthesis agent
  outliner.md               # Outline generator agent (3 variants)
  writer.md                 # Draft writer agent
  reviewer-technical.md     # Technical accuracy reviewer
  reviewer-editor.md        # Editor/style reviewer
  reviewer-adversarial.md   # Devil's advocate (adversarial)
  reviewer-audience.md      # Target audience proxy (internal + external)
  reviewer-seo.md           # SEO/reach optimizer
  refiner.md                # Refinement agent
  formatter-internal.md     # Internal format adapter
  formatter-external.md     # External format adapter + social
  formatter-medium.md       # Medium platform adapter
  formatter-devto.md        # dev.to platform adapter
  formatter-hashnode.md     # Hashnode platform adapter
  formatter-wechat.md       # WeChat公众号 platform adapter (Chinese)
  formatter-juejin.md       # 掘金 platform adapter (Chinese)
templates/
  tutorial.md               # Tutorial article structure
  deep-dive.md              # Deep dive article structure
  narrative.md              # Narrative/war-story structure
  opinion.md                # Opinion/hot-take structure
  case-study.md             # Case study structure
tests/
  test_pipeline.sh          # Unit tests for core scripts (29 tests)
  test_orchestrate.sh       # Integration tests for orchestrator (54 tests)
  test_e2e_dryrun.sh        # E2E dry run simulation (53 tests)
  run-all.sh                # Test runner (136 total tests)
```

## Runtime State

During execution, `.essay-state/` contains:
- `pipeline-state.json` — current stage, config, review status
- `materials.json` — structured input materials
- `research-synthesis.json` — thesis, evidence, angles
- `outline-{A,B,C}.json` — 3 outline variants
- `draft-v{N}.md` — draft versions
- `review-{reviewer}.json` — individual review results
- `review-panel-summary.json` — aggregated review panel
- `refinement-{N}-changes.json` — change logs per round
- `final-internal.md` — company publication version
- `final-external.md` — external publication version
- `final-medium.md` — Medium platform version
- `final-devto.md` — dev.to platform version
- `final-hashnode.md` — Hashnode platform version
- `final-wechat.md` — WeChat公众号 platform version
- `final-juejin.md` — 掘金 platform version
- `social-package.json` — social media snippets

## Conventions

- All state writes are atomic (tmp + rename)
- Agent prompts are built by orchestrate.sh, not hardcoded in SKILL.md
- Each reviewer agent gets fresh context (no knowledge of other reviewers)
- Outline variants run in parallel with no cross-influence
- User checkpoints at every stage transition
- Taste memory persists at `~/.tech-essay-writer/`

## Testing

```bash
bash tests/run-all.sh  # 136 tests across 3 suites
```
