# tech-essay-writer

Multi-agent tech article writing skill for Claude Code.

## Architecture

7-stage pipeline: Intake -> Research -> Outline (3 variants) -> Draft -> Review (7 agents) -> Refine (loop) -> Polish (2 formats)

Key patterns:
- **Design-shotgun** (from gstack): 3 parallel outline variants with no cross-influence
- **Adversarial review panel**: 7 independent reviewers with fresh context each
- **Refinement loop**: challenge -> fix -> re-challenge (max 3 rounds)
- **Taste memory**: persistent style preferences across sessions, with diff-learn and feedback for continuous improvement
- **Cross-reference**: track published articles for internal linking
- **Author profile**: persistent author identity + expertise areas
- **Expertise graph**: topic authority tracking based on publishing history
- **Article series**: multi-article series with narrative arc, reading order, and shared context
- **Analytics feedback**: performance tracking + taste memory integration for data-driven improvements
- **Quality scoring**: composite 0-10 quality score from review data
- **Pre-publish checks**: validation checklist before publishing

## Setup

Install the skill by symlinking components into `~/.claude/skills/`:

```bash
bash scripts/install.sh              # Install
bash scripts/install.sh --uninstall  # Uninstall
```

This creates `~/.claude/skills/tech-essay-writer/` as a real directory with symlinks to `SKILL.md`, `scripts/`, `prompts/`, and `templates/` -- keeping `.git`, `tests/`, and other dev files out of the skill directory.

## Directory Structure

```
SKILL.md                    # Main skill definition (conductor prompt)
scripts/                    # 26 scripts
  orchestrate.sh            # Pipeline orchestrator -- prompt builders + stage control
  pipeline-state.sh         # Pipeline state management (atomic writes)
  intake-materials.sh       # Material intake (URL/note/file/code/theme/angle)
  detect-input.sh           # Input type detection (URL, code, note, file, theme, angle)
  aggregate-reviews.sh      # Aggregate 7 review results into panel summary
  calibrate-reviews.sh      # Post-aggregate calibration: normalize scores, detect outliers/blind spots
  build-agent-prompt.sh     # Generic prompt builder with context injection
  taste-memory.sh           # Persistent writing style preferences (read/update/record-choice/get-preference/history/diff-learn/feedback/suggest)
  cross-reference.sh        # Published article registry
  config.sh                 # User configuration management (platforms, style, language)
  author-profile.sh         # Author identity management
  expertise-graph.sh        # Topic authority tracking
  influence-score.sh        # Influence potential predictor (novelty, SEO, social, audience)
  seo-metadata.sh           # SEO metadata generator (OG, meta, JSON-LD, keyword density)
  code-validate.sh          # Code example validator (syntax, imports, fragment detection)
  diagram-suggest.sh        # Diagram/image suggestion engine (Mermaid syntax, bilingual)
  series-manager.sh         # Article series manager (reading order, narrative arc, shared context)
  analytics-feedback.sh     # Analytics feedback loop (metrics tracking, taste memory integration)
  progress-display.sh       # Rich pipeline progress visualization (stages, %, quality, artifacts)
  publish-check.sh          # Pre-publish checklist (validates article readiness)
  publishing-guide.sh       # Per-platform publishing workflow guides with SEO tips
  quality-score.sh          # Quality score calculator (composite 0-10 from review data)
  checkpoint.sh             # State checkpoint and recovery (snapshot/rollback/latest/clean)
  install.sh                # Skill installer (symlink components into ~/.claude/skills/)
  fetch-urls.sh             # URL content fetcher
  update-material.sh        # Update material with fetched content
prompts/                    # 20 prompts
  researcher.md             # Research synthesis agent
  outliner.md               # Outline generator agent (3 variants)
  outline-critic.md         # Outline adversarial critique agent (cross-comparison)
  writer.md                 # Draft writer agent
  reviewer-technical.md     # Technical accuracy reviewer
  reviewer-editor.md        # Editor/style reviewer
  reviewer-adversarial.md   # Devil's advocate (adversarial)
  reviewer-audience.md      # Target audience proxy (internal + external)
  reviewer-seo.md           # SEO/reach optimizer
  reviewer-external.md      # External perspective (fresh-eyes accessibility)
  reviewer-factcheck.md     # Fact-checking (claim verification)
  refiner.md                # Refinement agent
  formatter-internal.md     # Internal format adapter
  formatter-external.md     # External format adapter + social
  social-package.md         # Enhanced social media package agent
  formatter-medium.md       # Medium platform adapter
  formatter-devto.md        # dev.to platform adapter
  formatter-hashnode.md     # Hashnode platform adapter
  formatter-wechat.md       # WeChat platform adapter (Chinese)
  formatter-juejin.md       # Juejin platform adapter (Chinese)
templates/                  # 10 templates
  tutorial.md               # Tutorial article structure
  deep-dive.md              # Deep dive article structure
  narrative.md              # Narrative/war-story structure
  opinion.md                # Opinion/hot-take structure
  case-study.md             # Case study structure
  comparison.md             # X vs Y comparison structure
  listicle.md               # N things/tools/tips structure
  incident-postmortem.md    # Incident post-mortem structure
  release-announcement.md   # Release notes / launch announcement structure
  adr.md                    # Architecture Decision Record structure
tests/                      # 14 test suites + runner
  test_pipeline.sh          # Unit tests for core scripts (pipeline-state, intake, taste-memory, aggregate, calibrate)
  test_orchestrate.sh       # Integration tests for orchestrator (prompt building, stage transitions)
  test_e2e_dryrun.sh        # E2E dry run simulation (full pipeline with mock data)
  test_branding.sh          # Personal branding engine tests (author-profile, expertise-graph, social-package)
  test_influence_seo.sh     # Influence score + SEO metadata tests
  test_templates_codevalidate.sh  # Template + code validation tests
  test_diagram_suggest.sh   # Diagram suggestion engine tests
  test_series_analytics.sh  # Series manager + analytics feedback tests
  test_config.sh            # Configuration system tests
  test_progress_display.sh  # Progress display visualization tests
  test_progress_publishing.sh  # Progress display + publishing guide tests
  test_checkpoint.sh        # Checkpoint, auto-snapshot, retry-stage, resume tests
  test_install.sh           # Install/uninstall script tests
  test_taste_memory.sh      # Taste memory diff-learn, feedback, and suggest tests
  run-all.sh                # Test runner
```

## Runtime State

During execution, `.essay-state/` contains:
- `pipeline-state.json` -- current stage, config, review status
- `materials.json` -- structured input materials
- `research-synthesis.json` -- thesis, evidence, angles
- `outline-{A,B,C}.json` -- 3 outline variants
- `outline-critique.json` -- adversarial critique of all 3 outlines
- `draft-v{N}.md` -- draft versions
- `review-{reviewer}.json` -- individual review results
- `review-panel-summary.json` -- aggregated review panel
- `review-calibration.json` -- normalized scores, outliers, blind spots, agreement
- `refinement-{N}-changes.json` -- change logs per round
- `final-internal.md` -- company publication version
- `final-external.md` -- external publication version
- `final-medium.md` -- Medium platform version
- `final-devto.md` -- dev.to platform version
- `final-hashnode.md` -- Hashnode platform version
- `final-wechat.md` -- WeChat platform version
- `final-juejin.md` -- Juejin platform version
- `social-package.json` -- social media snippets
- `influence-score.json` -- predicted influence/reach potential
- `seo-metadata.json` -- OpenGraph, meta tags, JSON-LD, keyword density
- `diagram-suggestions.json` -- suggested diagrams/visuals with Mermaid syntax
- `checkpoints/` -- stage checkpoints for rollback/retry
  - `checkpoints/<label>-<YYYYMMDDTHHmmss>/` -- full state copies (auto-created on stage transitions)

Persistent data at `~/.tech-essay-writer/`:
- `taste-memory.json` -- writing style preferences, learned patterns (from diff-learn), explicit preferences (from feedback)
- `config.json` -- user configuration (platforms, language, style)
- `author-profile.json` -- author identity and bio
- `expertise.json` -- topic authority graph
- `cross-reference.json` -- published article registry
- `series.json` -- article series definitions (reading order, narrative arc)
- `analytics.json` -- article performance metrics (views, shares, etc.)

## Conventions

- All state writes are atomic (tmp + rename)
- Agent prompts are built by orchestrate.sh, not hardcoded in SKILL.md
- Each reviewer agent gets fresh context (no knowledge of other reviewers)
- Outline variants run in parallel with no cross-influence
- User checkpoints at every stage transition
- Taste memory, config, author profile, series, and analytics persist at `~/.tech-essay-writer/`
- Series context is injected into outline, writer, and formatter prompts when `series_id` is set
- Analytics `feed-taste` writes `performance_insights` into taste-memory.json
- Pipeline state accepts `--series <series_id>` at init to associate articles with a series
- `diff-learn` compares original draft with user-edited version to extract style patterns (tone, structure, vocabulary, code density)
- `feedback` records explicit user preferences by category (tone, structure, vocabulary, length, code_density, format)
- `suggest` aggregates all taste data into personalized writing recommendations

## Testing

```bash
bash tests/run-all.sh  # 1228 tests across 14 suites
```
