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
are compared via article_compare.py and the adversarial reviewer re-checks. The
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

After aggregation, `calibrate_reviews.py` normalizes scores to 1-10, detects
outliers (>1.5 std dev from panel average), identifies blind spots (topics no
reviewer covered), and measures inter-reviewer agreement.

## Script Inventory (38 scripts)

| Script | Description |
|--------|-------------|
| `orchestrate.py` | Pipeline orchestrator -- 27 commands for prompt building, stage control, resume, checkpoint management, readability, word analysis |
| `pipeline_state.py` | Pipeline state CRUD with atomic writes (init, set-stage, get-stage, read, set-field, get-field, add-review, refinement-round, complete) |
| `intake_materials.py` | Material intake: add-url, add-note, add-file, add-code, add-theme, add-angle, list, export, clear |
| `detect_input.py` | Classify user input text into URLs, code blocks, file paths, notes, themes |
| `aggregate_reviews.py` | Aggregate 7 review JSON files into panel summary with consensus determination |
| `calibrate_reviews.py` | Post-aggregate calibration: normalize scores, detect outliers and blind spots |
| `quality_score.py` | Composite 0-10 quality score from weighted review dimensions |
| `taste_memory.py` | Persistent writing style preferences (read/update/record-choice/get-preference/history/diff-learn/feedback/suggest) |
| `cross_reference.py` | Published article registry for internal linking (add/search/list/suggest/remove) |
| `config.py` | User configuration management (init/read/get/set/add-platform/remove-platform/add-audience/remove-audience/reset/export) |
| `author_profile.py` | Author identity management (init/read/set/set-social/add-expertise/remove-expertise/set-voice/get-bio/get-social-handles) |
| `expertise_graph.py` | Topic authority tracking with recency-weighted scoring (update/query/top/suggest/read) |
| `influence_score.py` | Influence potential predictor (novelty, SEO, social, audience, timing) |
| `seo_metadata.py` | SEO metadata generator (OpenGraph, meta tags, JSON-LD, keyword density) |
| `code_validate.py` | Code example validator (syntax checking, import verification, fragment detection) |
| `diagram_suggest.py` | Diagram/image suggestion engine with Mermaid syntax output (bilingual) |
| `readability_score.py` | Readability analysis: Flesch-Kincaid grade, reading ease, sentence metrics, passive voice, complex sentences |
| `word_frequency.py` | Word frequency analysis: top-N frequencies, overused words, jargon density, AI-generated text pattern detection |
| `article_compare.py` | Side-by-side draft comparison: word count diff, structure diff, reading level diff, section changes, improvements/regressions |
| `series_manager.py` | Article series manager (create/add/list/show/context/set-arc/set-summary/next-position/search/reorder) |
| `analytics_feedback.py` | Analytics feedback loop (record/record-batch/query/top/trends/feed-taste/summary/compare) |
| `progress_display.py` | Rich pipeline progress visualization (stage map, %, quality dashboard, artifacts) |
| `publish_check.py` | Pre-publish checklist (validates article readiness across multiple dimensions) |
| `publishing_guide.py` | Per-platform publishing workflow guides with SEO tips (internal/external/medium/devto/hashnode/wechat/juejin/all) |
| `checkpoint.py` | State checkpoint and recovery (snapshot/list/rollback/latest/clean) |
| `dry_run.py` | Full pipeline simulation with mock data -- validates infrastructure without LLM agents (supports --chinese for zh mode) |
| `install.py` | Skill installer/uninstaller (symlink components into ~/.claude/skills/) |
| `fetch_urls.py` | URL content fetcher for materials intake |
| `update_material.py` | Update a specific material source with fetched content and key points |
| `export.py` | Export and archive system (bundle/markdown/html/json/archive formats, list-archive) |
| `hook_workshop.py` | Opening hook generator and scorer (story/data/question/contrast/bold styles) |
| `title_generator.py` | Title variation generator with scoring from research and materials |
| `topic_research.py` | Research question generator, competitive landscape queries, unique angles, and research brief from a topic |
| `outline_mixer.py` | Outline variant mixer: combine elements from multiple outlines |
| `metrics_dashboard.py` | Comprehensive metrics dashboard: pipeline health, quality trends, author growth |
| `summary.py` | Quick project status and capability overview |
| `help.py` | Usage reference: list all scripts with descriptions, or detailed help for a specific command |
| `version.py` | Version tracking: show current version, bump major/minor/patch |

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
| `test_pipeline.py` | 66 | Core scripts: pipeline-state, intake, taste-memory, aggregate, calibrate |
| `test_orchestrate.py` | 85 | Orchestrator: prompt building, stage transitions, resume |
| `test_e2e_dryrun.py` | 83 | Full pipeline simulation with mock data |
| `test_e2e_integration.py` | 86 | End-to-end integration tests |
| `test_error_handling.py` | 116 | Error handling and edge cases |
| `test_branding.py` | 73 | Personal branding: author-profile, expertise-graph, social-package |
| `test_influence_seo.py` | 54 | Influence score + SEO metadata |
| `test_templates_codevalidate.py` | 150 | Template loading + code validation |
| `test_diagram_suggest.py` | 97 | Diagram suggestion engine |
| `test_series_analytics.py` | 79 | Series manager + analytics feedback |
| `test_config.py` | 97 | Configuration system |
| `test_progress_display.py` | 39 | Progress display visualization |
| `test_progress_publishing.py` | 192 | Progress display + publishing guides |
| `test_checkpoint.py` | 113 | Checkpoint, auto-snapshot, retry-stage, resume |
| `test_install.py` | 35 | Install/uninstall idempotency and edge cases |
| `test_taste_memory.py` | 65 | Taste memory: diff-learn, feedback, and suggest |
| `test_readability.py` | 51 | Readability scoring + word frequency analysis |
| `test_article_compare.py` | 47 | Article draft comparison |
| `test_export.py` | 69 | Export and archive system (bundle/markdown/html/json/archive/list-archive) |
| `test_title_hook.py` | 59 | Title generator + hook workshop |
| `test_topic_research.py` | 59 | Topic research question generation and brief output |
| `test_chinese_reviewer.py` | 23 | Chinese reviewer integration (language=zh activation, quality-score, pipeline-state) |
| `test_outline_mixer.py` | — | Outline mixer tests |
| `test_metrics_dashboard.py` | — | Metrics dashboard tests |
| `test_help_version.py` | 46 | Help command listing + version tracking (show, raw, bump, help flags) |

Run all tests:
```bash
pytest tests/py/                         # All test suites
pytest tests/py/ -k readab              # Filter by pattern
pytest tests/py/ -v                      # Verbose output
```

Python dependencies and pytest configuration are defined in `pyproject.toml`.

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
created at every stage transition via `pipeline_state.py set-stage`.

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
python3 scripts/py/config.py init                        # Create default config
python3 scripts/py/config.py set language zh             # Set language preference (en|zh)
python3 scripts/py/config.py set writing_style narrative # Set style (technical|conversational|narrative|formal|casual|academic)
python3 scripts/py/config.py add-platform medium         # Add default platform
python3 scripts/py/config.py remove-platform medium      # Remove a platform
python3 scripts/py/config.py add-audience "senior devs"  # Add target audience
python3 scripts/py/config.py set max_refinement_rounds 5 # Set max refinement rounds (1-10)
python3 scripts/py/config.py read                        # Show current config
python3 scripts/py/config.py export                      # Output full JSON
python3 scripts/py/config.py reset                       # Reset to defaults
```

Config keys: `default_platforms`, `writing_style`, `target_audiences`, `language`,
`use_author_profile`, `max_refinement_rounds`.

## Setup

Install the skill by symlinking components into `~/.claude/skills/`:

```bash
python3 scripts/py/install.py              # Install
python3 scripts/py/install.py --uninstall  # Uninstall
```

Creates `~/.claude/skills/tech-essay-writer/` as a real directory with symlinks
pointing to `SKILL.md`, `scripts/py/`, `prompts/`, and `templates/` in the source
repo. Running install twice is safe (idempotent). Old whole-directory symlinks
from prior install methods are automatically replaced.

## Conventions

- All state writes are atomic (tmp + rename)
- Agent prompts are built by `orchestrate.py`, not hardcoded in SKILL.md
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
- `readability_score.py` and `word_frequency.py` run during draft analysis before review
- `article_compare.py` runs during refinement to track improvements between draft versions
- `dry_run.py` validates the full pipeline without LLM agents (useful after script changes)
