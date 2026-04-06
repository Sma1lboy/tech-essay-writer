# tech-essay-writer

Multi-agent tech article writing skill for Claude Code. Transforms raw materials
(URLs, notes, code, files) into polished, publish-ready articles through a 7-stage
pipeline with adversarial review.

## Pipeline Architecture

```
INTAKE -> RESEARCH -> OUTLINE (3 variants) -> DRAFT -> REVIEW (7 agents) -> REFINE (loop) -> POLISH (2+ formats)
```

### Stage 1: INTAKE
Collect and classify raw user materials. Detects URLs, notes, code blocks, file
paths, themes, and angles. Optionally associates the article with a series and
detects language preference (en/zh).

### Stage 2: RESEARCH SYNTHESIS
A research agent analyzes all materials, searches the competitive landscape, and
produces a structured thesis with evidence and unique angles.

### Stage 3: OUTLINE GENERATION (Design-Shotgun Pattern)
Three outline agents run in parallel with NO cross-influence. Each produces a
different structural variant:
- Variant A: Tutorial style
- Variant B: Deep-dive style
- Variant C: Narrative / war-story style

An outline-critic agent then reads all three and recommends the strongest. The
user makes the final choice.

### Stage 4: DRAFT WRITING
A writer agent produces a complete draft from the chosen outline. Code examples
are validated (syntax, imports, fragments), readability is scored (Flesch-Kincaid
grade, passive voice, complexity), word frequency is analyzed (overuse, jargon
density, AI pattern detection), and diagram placement is suggested.

### Stage 5: ADVERSARIAL REVIEW PANEL (7 Parallel Agents)
Seven independent reviewers run in parallel with fresh context (no knowledge of
each other). Results are aggregated, scored (composite 0-10), and calibrated for
outliers and blind spots.

### Stage 6: REFINEMENT LOOP (Max 3 Rounds)
A refiner agent addresses issues from the review panel. After each round, drafts
are compared via article-compare.sh and the adversarial reviewer re-checks. The
loop exits on convergence or max rounds.

### Stage 7: DUAL-FORMAT POLISH
Two format agents run in parallel (internal company version + external blog
version). Optional platform-specific adapters then produce versions for Medium,
dev.to, Hashnode, WeChat, and Juejin. A social media package is generated with
the author's profile for Twitter threads, LinkedIn posts, and more.

Post-polish analysis computes an influence/reach score and generates SEO metadata
(OpenGraph, meta tags, JSON-LD, keyword density). A publish readiness checklist
validates the article before publishing. Analytics feedback feeds performance
data back into taste memory for future articles.

## Multi-Agent Adversarial Review (7 Reviewers)

| Reviewer | Role | Rating Scale |
|----------|------|-------------|
| `reviewer-technical.md` | Find technical errors, verify code | PASS / NEEDS_FIXES / REJECT |
| `reviewer-editor.md` | Style, flow, voice, economy of language | PUBLISH_READY / NEEDS_EDITING / REWRITE |
| `reviewer-adversarial.md` | Break the argument, find logic gaps | SOLID / VULNERABLE / WEAK |
| `reviewer-audience.md` | Two reader personas (internal + external) | WOULD_SHARE / MEH / SKIP |
| `reviewer-seo.md` | Title, discoverability, social shareability | OPTIMIZED / NEEDS_WORK / INVISIBLE |
| `reviewer-external.md` | Fresh-eyes accessibility, jargon check | CLEAR / NEEDS_CONTEXT / INACCESSIBLE |
| `reviewer-factcheck.md` | Verify every technical claim | VERIFIED / NEEDS_VERIFICATION / UNRELIABLE |

After aggregation, `calibrate-reviews.sh` normalizes scores to 1-10, detects
outliers (>1.5 std dev from panel average), identifies blind spots (topics no
reviewer covered), and measures inter-reviewer agreement.

## Script Inventory (38 scripts)

| Script | Description |
|--------|-------------|
| `orchestrate.sh` | Pipeline orchestrator -- 27 commands for prompt building, stage control, resume, checkpoint management, readability, word analysis |
| `pipeline-state.sh` | Pipeline state CRUD with atomic writes (init, set-stage, get-stage, read, set-field, get-field, add-review, refinement-round, complete) |
| `intake-materials.sh` | Material intake: add-url, add-note, add-file, add-code, add-theme, add-angle, list, export, clear |
| `detect-input.sh` | Classify user input text into URLs, code blocks, file paths, notes, themes |
| `aggregate-reviews.sh` | Aggregate 7 review JSON files into panel summary with consensus determination |
| `calibrate-reviews.sh` | Post-aggregate calibration: normalize scores, detect outliers and blind spots |
| `quality-score.sh` | Composite 0-10 quality score from weighted review dimensions |
| `taste-memory.sh` | Persistent writing style preferences (read/update/record-choice/get-preference/history/diff-learn/feedback/suggest) |
| `cross-reference.sh` | Published article registry for internal linking (add/search/list/suggest/remove) |
| `config.sh` | User configuration management (init/read/get/set/add-platform/remove-platform/add-audience/remove-audience/reset/export) |
| `author-profile.sh` | Author identity management (init/read/set/set-social/add-expertise/remove-expertise/set-voice/get-bio/get-social-handles) |
| `expertise-graph.sh` | Topic authority tracking with recency-weighted scoring (update/query/top/suggest/read) |
| `influence-score.sh` | Influence potential predictor (novelty, SEO, social, audience, timing) |
| `seo-metadata.sh` | SEO metadata generator (OpenGraph, meta tags, JSON-LD, keyword density) |
| `code-validate.sh` | Code example validator (syntax checking, import verification, fragment detection) |
| `diagram-suggest.sh` | Diagram/image suggestion engine with Mermaid syntax output (bilingual) |
| `readability-score.sh` | Readability analysis: Flesch-Kincaid grade, reading ease, sentence metrics, passive voice, complex sentences |
| `word-frequency.sh` | Word frequency analysis: top-N frequencies, overused words, jargon density, AI-generated text pattern detection |
| `article-compare.sh` | Side-by-side draft comparison: word count diff, structure diff, reading level diff, section changes, improvements/regressions |
| `series-manager.sh` | Article series manager (create/add/list/show/context/set-arc/set-summary/next-position/search/reorder) |
| `analytics-feedback.sh` | Analytics feedback loop (record/record-batch/query/top/trends/feed-taste/summary/compare) |
| `progress-display.sh` | Rich pipeline progress visualization (stage map, %, quality dashboard, artifacts) |
| `publish-check.sh` | Pre-publish checklist (validates article readiness across multiple dimensions) |
| `publishing-guide.sh` | Per-platform publishing workflow guides with SEO tips (internal/external/medium/devto/hashnode/wechat/juejin/all) |
| `checkpoint.sh` | State checkpoint and recovery (snapshot/list/rollback/latest/clean) |
| `dry-run.sh` | Full pipeline simulation with mock data -- validates infrastructure without LLM agents (supports --chinese for zh mode) |
| `install.sh` | Skill installer/uninstaller (symlink components into ~/.claude/skills/) |
| `fetch-urls.sh` | URL content fetcher for materials intake |
| `update-material.sh` | Update a specific material source with fetched content and key points |
| `export.sh` | Export and archive system (bundle/markdown/html/json/archive formats, list-archive) |
| `hook-workshop.sh` | Opening hook generator and scorer (story/data/question/contrast/bold styles) |
| `title-generator.sh` | Title variation generator with scoring from research and materials |
| `topic-research.sh` | Research question generator, competitive landscape queries, unique angles, and research brief from a topic |
| `outline-mixer.sh` | Outline variant mixer: combine elements from multiple outlines |
| `metrics-dashboard.sh` | Comprehensive metrics dashboard: pipeline health, quality trends, author growth |
| `summary.sh` | Quick project status and capability overview |
| `help.sh` | Usage reference: list all scripts with descriptions, or detailed help for a specific command |
| `version.sh` | Version tracking: show current version, bump major/minor/patch |

## Prompt Inventory (21 prompts)

| Prompt | Role |
|--------|------|
| `researcher.md` | Research synthesis agent -- finds the story in raw materials |
| `outliner.md` | Outline generator agent -- designs 3 structural variants |
| `outline-critic.md` | Outline adversarial critique -- cross-compares all 3 outlines |
| `writer.md` | Draft writer agent -- produces complete publish-ready draft |
| `reviewer-technical.md` | Technical accuracy reviewer -- finds errors in code and claims |
| `reviewer-editor.md` | Editor/style reviewer -- evaluates hook, clarity, flow, voice |
| `reviewer-adversarial.md` | Devil's advocate -- tries to break the argument |
| `reviewer-audience.md` | Target audience proxy -- two reader personas (internal + external) |
| `reviewer-seo.md` | SEO/reach optimizer -- title, discoverability, social potential |
| `reviewer-external.md` | External perspective -- fresh-eyes accessibility check |
| `reviewer-factcheck.md` | Fact-checker -- verifies every technical claim |
| `reviewer-chinese.md` | Chinese writing quality reviewer -- naturalness, terminology, style for zh articles |
| `refiner.md` | Refinement agent -- focused revision pass from review issues |
| `formatter-internal.md` | Internal format adapter -- company publication version |
| `formatter-external.md` | External format adapter -- blog/social publication + social package |
| `formatter-medium.md` | Medium platform adapter -- optimized for Medium formatting |
| `formatter-devto.md` | dev.to platform adapter -- liquid tags, frontmatter |
| `formatter-hashnode.md` | Hashnode platform adapter -- YAML frontmatter |
| `formatter-wechat.md` | WeChat platform adapter -- inline-CSS HTML, Chinese |
| `formatter-juejin.md` | Juejin platform adapter -- Chinese Markdown |
| `social-package.md` | Social media package -- Twitter thread, LinkedIn, HN, author CTAs |

## Template Inventory (10 templates)

| Template | Article Type |
|----------|-------------|
| `tutorial.md` | Step-by-step tutorial with prerequisites, implementation, verification |
| `deep-dive.md` | Technical deep-dive with architecture analysis and tradeoffs |
| `narrative.md` | Narrative / war-story with timeline and lessons learned |
| `opinion.md` | Opinion / hot-take with thesis, evidence, counterarguments |
| `case-study.md` | Case study with problem, approach, results, metrics |
| `comparison.md` | X vs Y comparison with criteria matrix and recommendation |
| `listicle.md` | N things/tools/tips with consistent structure per item |
| `incident-postmortem.md` | Incident post-mortem with timeline, root cause, action items |
| `release-announcement.md` | Release notes / launch announcement with migration guide |
| `adr.md` | Architecture Decision Record with context, options, decision |

## Test Inventory (25 suites)

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_pipeline.sh` | 66 | Core scripts: pipeline-state, intake, taste-memory, aggregate, calibrate |
| `test_orchestrate.sh` | 85 | Orchestrator: prompt building, stage transitions, resume |
| `test_e2e_dryrun.sh` | 83 | Full pipeline simulation with mock data |
| `test_e2e_integration.sh` | 86 | End-to-end integration tests |
| `test_error_handling.sh` | 116 | Error handling and edge cases |
| `test_branding.sh` | 73 | Personal branding: author-profile, expertise-graph, social-package |
| `test_influence_seo.sh` | 54 | Influence score + SEO metadata |
| `test_templates_codevalidate.sh` | 150 | Template loading + code validation |
| `test_diagram_suggest.sh` | 97 | Diagram suggestion engine |
| `test_series_analytics.sh` | 79 | Series manager + analytics feedback |
| `test_config.sh` | 97 | Configuration system |
| `test_progress_display.sh` | 39 | Progress display visualization |
| `test_progress_publishing.sh` | 192 | Progress display + publishing guides |
| `test_checkpoint.sh` | 113 | Checkpoint, auto-snapshot, retry-stage, resume |
| `test_install.sh` | 35 | Install/uninstall idempotency and edge cases |
| `test_taste_memory.sh` | 65 | Taste memory: diff-learn, feedback, and suggest |
| `test_readability.sh` | 51 | Readability scoring + word frequency analysis |
| `test_article_compare.sh` | 47 | Article draft comparison |
| `test_export.sh` | 69 | Export and archive system (bundle/markdown/html/json/archive/list-archive) |
| `test_title_hook.sh` | 59 | Title generator + hook workshop |
| `test_topic_research.sh` | 59 | Topic research question generation and brief output |
| `test_chinese_reviewer.sh` | 23 | Chinese reviewer integration (language=zh activation, quality-score, pipeline-state) |
| `test_outline_mixer.sh` | — | Outline mixer tests |
| `test_metrics_dashboard.sh` | — | Metrics dashboard tests |
| `test_help_version.sh` | 46 | Help command listing + version tracking (show, raw, bump, help flags) |

Run all tests:
```bash
bash tests/run-all.sh                    # All test suites
bash tests/run-all.sh --filter readab    # Filter by pattern
bash tests/run-all.sh --verbose --timing # Show all output + timing
```

## State Management

### Pipeline State (`.essay-state/`)

Created per-project during execution. Contains all pipeline artifacts:

```
.essay-state/
  pipeline-state.json        # Current stage, config, review status, series_id
  materials.json             # Structured input materials (sources, themes, angles)
  research-synthesis.json    # Thesis, evidence, unique angles
  outline-{A,B,C}.json      # 3 outline variants
  outline-critique.json      # Adversarial critique of all 3 outlines
  draft-v{N}.md             # Draft versions (v1, v2, etc.)
  review-{reviewer}.json     # Individual review results (7 files)
  review-panel-summary.json  # Aggregated review panel
  review-calibration.json    # Normalized scores, outliers, blind spots, agreement
  refinement-{N}-changes.json # Change logs per refinement round
  quality-score.json         # Composite 0-10 quality score
  final-internal.md          # Company publication version
  final-external.md          # External blog version
  final-medium.md            # Medium platform version
  final-devto.md             # dev.to platform version
  final-hashnode.md          # Hashnode platform version
  final-wechat.md            # WeChat platform version (Chinese)
  final-juejin.md            # Juejin platform version (Chinese)
  social-package.json        # Social media snippets (Twitter, LinkedIn, HN, etc.)
  influence-score.json       # Predicted influence/reach potential
  seo-metadata.json          # OpenGraph, meta tags, JSON-LD, keyword density
  diagram-suggestions.json   # Suggested diagrams/visuals with Mermaid syntax
  checkpoints/               # Stage checkpoints for rollback/retry
    <label>-<YYYYMMDDTHHmmss>/  # Full state copies (auto-created on stage transitions)
```

All state writes are atomic (write to temp file + rename). Auto-snapshots are
created at every stage transition via `pipeline-state.sh set-stage`.

### Persistent Data (`~/.tech-essay-writer/`)

Persists across sessions and projects:

| File | Purpose |
|------|---------|
| `taste-memory.json` | Writing style preferences, learned patterns (from diff-learn), explicit preferences (from feedback), performance insights |
| `config.json` | User configuration (platforms, language, style, max refinement rounds, audiences) |
| `author-profile.json` | Author identity, bio, social handles, expertise areas, writing voice |
| `expertise-graph.json` | Topic authority graph with recency-weighted scoring |
| `published-articles.json` | Published article registry for cross-referencing |
| `series.json` | Article series definitions (reading order, narrative arc, shared context) |
| `analytics.json` | Article performance metrics (views, shares, comments, bookmarks, read_time_avg, bounce_rate) |

## Configuration System

User preferences at `~/.tech-essay-writer/config.json`. Auto-applies to new pipelines.

```bash
bash scripts/config.sh init                        # Create default config
bash scripts/config.sh set language zh             # Set language preference (en|zh)
bash scripts/config.sh set writing_style narrative # Set style (technical|conversational|narrative|formal|casual|academic)
bash scripts/config.sh add-platform medium         # Add default platform
bash scripts/config.sh remove-platform medium      # Remove a platform
bash scripts/config.sh add-audience "senior devs"  # Add target audience
bash scripts/config.sh set max_refinement_rounds 5 # Set max refinement rounds (1-10)
bash scripts/config.sh read                        # Show current config
bash scripts/config.sh export                      # Output full JSON
bash scripts/config.sh reset                       # Reset to defaults
```

Config keys: `default_platforms`, `writing_style`, `target_audiences`, `language`,
`use_author_profile`, `max_refinement_rounds`.

## Setup

Install the skill by symlinking components into `~/.claude/skills/`:

```bash
bash scripts/install.sh              # Install
bash scripts/install.sh --uninstall  # Uninstall
```

Creates `~/.claude/skills/tech-essay-writer/` as a real directory with symlinks
pointing to `SKILL.md`, `scripts/`, `prompts/`, and `templates/` in the source
repo. Running install twice is safe (idempotent). Old whole-directory symlinks
from prior install methods are automatically replaced.

## Conventions

- All state writes are atomic (tmp + rename)
- Agent prompts are built by `orchestrate.sh`, not hardcoded in SKILL.md
- Each reviewer agent gets fresh context (no knowledge of other reviewers)
- Outline variants run in parallel with no cross-influence (design-shotgun pattern)
- User checkpoints at every stage transition
- Taste memory, config, author profile, series, and analytics persist at `~/.tech-essay-writer/`
- Series context auto-injects into outline, writer, and formatter prompts when `series_id` is set
- `diff-learn` compares original draft with user-edited version to extract style patterns
- `feedback` records explicit user preferences by category (tone, structure, vocabulary, length, code_density, format)
- `suggest` aggregates all taste data into personalized writing recommendations
- Analytics `feed-taste` writes `performance_insights` into taste-memory.json
- Pipeline state accepts `--series <series_id>` at init to associate articles with a series
- Language directive (en/zh) propagates to all downstream agents
- `readability-score.sh` and `word-frequency.sh` run during draft analysis before review
- `article-compare.sh` runs during refinement to track improvements between draft versions
- `dry-run.sh` validates the full pipeline without LLM agents (useful after script changes)
