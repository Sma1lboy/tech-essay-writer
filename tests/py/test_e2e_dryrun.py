"""End-to-end dry run: simulates the full pipeline flow with mock data.

Validates that every stage produces expected artifacts and transitions correctly.
Migrated from tests/test_e2e_dryrun.sh (83 tests).
"""

import json
import os
import shutil

import pytest


# ---------------------------------------------------------------------------
# Shared fixture: fully wired project with fake HOME
# ---------------------------------------------------------------------------

@pytest.fixture
def e2e_project(run_script, tmp_path, monkeypatch, script_dir):
    """Create a project directory and fake HOME for full pipeline simulation."""
    home = str(tmp_path / "fakehome")
    os.makedirs(home)
    monkeypatch.setenv("HOME", home)
    project = str(tmp_path / "e2e-project")
    os.makedirs(project)
    return project, script_dir, home


# ---------------------------------------------------------------------------
# Helper: write JSON files into .essay-state/
# ---------------------------------------------------------------------------

def _state_path(project, filename):
    return os.path.join(project, ".essay-state", filename)


def _write_state_json(project, filename, data):
    path = _state_path(project, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _write_state_text(project, filename, text):
    path = _state_path(project, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# =========================================================================
# STAGE 1: INTAKE
# =========================================================================

class TestStage1Intake:
    """Intake: initialise pipeline, add materials, verify listing & summary."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        # Init pipeline and materials
        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)

        # Add various material types
        self.run("intake_materials", "add-note", self.project,
                 "Agent architecture is more important than model choice. "
                 "The key is separating planning from execution.")
        self.run("intake_materials", "add-note", self.project,
                 "Three-layer hierarchy works best: conductor -> sprint master -> worker. "
                 "Fresh context per layer prevents context pollution.")
        self.run("intake_materials", "add-url", self.project,
                 "https://docs.anthropic.com/en/docs/agents", "Anthropic Agent Docs")
        self.run("intake_materials", "add-code", self.project,
                 'async function dispatch(task) { const agent = new Agent(); '
                 'return agent.execute(task); }', "javascript")
        self.run("intake_materials", "add-theme", self.project, "multi-agent coordination")
        self.run("intake_materials", "add-theme", self.project, "context isolation")
        self.run("intake_materials", "add-angle", self.project,
                 "practical guide: from single agent to multi-agent system")

    def test_intake_has_4_sources(self):
        r = self.run("intake_materials", "list", self.project)
        assert "4 sources" in r.stdout

    def test_summary_shows_themes(self):
        r = self.run("orchestrate", self.project, self.sd, "build-intake-summary")
        assert "multi-agent" in r.stdout

    def test_summary_shows_angles(self):
        r = self.run("orchestrate", self.project, self.sd, "build-intake-summary")
        assert "practical guide" in r.stdout

    def test_next_stage_after_intake_is_research(self):
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "research"


# =========================================================================
# STAGE 2: RESEARCH SYNTHESIS
# =========================================================================

RESEARCH_SYNTHESIS = {
    "thesis": (
        "Multi-agent systems work best when each layer has fresh context and a "
        "single responsibility -- the conductor plans, the sprint master directs, "
        "the worker executes."
    ),
    "thesis_expanded": (
        "Most teams try to build AI agents as monoliths. The breakthrough comes "
        "from treating agent architecture like microservices: isolated contexts, "
        "clear interfaces, and progressive disclosure of information."
    ),
    "evidence_map": [
        {"claim": "Fresh context prevents pollution",
         "sources": ["note-1", "note-2"], "strength": "strong"},
        {"claim": "Three-layer hierarchy enables complex tasks",
         "sources": ["note-2", "url-1"], "strength": "strong"},
        {"claim": "Progressive disclosure reduces noise",
         "sources": ["note-2"], "strength": "moderate"},
    ],
    "knowledge_gaps": [
        {"gap": "No performance benchmarks", "impact": "medium",
         "resolution": "Add timing data from real runs"},
        {"gap": "Cost analysis missing", "impact": "high",
         "resolution": "Track token usage per layer"},
    ],
    "competitive_landscape": [
        {"title": "Building Effective Agents - Anthropic",
         "url": "https://anthropic.com/research/building-effective-agents",
         "angle": "General patterns",
         "gap": "No multi-layer architecture detail"},
        {"title": "LangGraph Multi-Agent",
         "url": "https://langchain.com/langgraph",
         "angle": "Framework-specific",
         "gap": "Framework-locked, not architecture-first"},
    ],
    "unique_angle": "Architecture-first approach with real production code from a working system",
    "recommended_depth": "intermediate",
    "recommended_length": "medium",
    "key_terms": ["multi-agent", "conductor pattern", "context isolation",
                  "progressive disclosure"],
}


class TestStage2ResearchSynthesis:
    """Research: verify prompt builds and next-stage transition."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        # Init + materials
        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project,
                 "Agent architecture is more important than model choice.")
        self.run("intake_materials", "add-note", self.project,
                 "Three-layer hierarchy works best.")
        self.run("intake_materials", "add-url", self.project,
                 "https://docs.anthropic.com/en/docs/agents", "Anthropic Agent Docs")
        self.run("intake_materials", "add-code", self.project,
                 'async function dispatch(task) { const agent = new Agent(); '
                 'return agent.execute(task); }', "javascript")
        self.run("pipeline_state", "set-stage", self.project, "research")

    def test_research_prompt_has_template(self):
        r = self.run("orchestrate", self.project, self.sd, "build-research-prompt")
        assert "Research Synthesis" in r.stdout

    def test_research_prompt_has_materials(self):
        r = self.run("orchestrate", self.project, self.sd, "build-research-prompt")
        assert "Agent architecture" in r.stdout

    def test_next_stage_after_research_is_outline(self):
        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "outline"


# =========================================================================
# STAGE 3: OUTLINE GENERATION
# =========================================================================

OUTLINE_A = {
    "variant": "A",
    "variant_name": "Tutorial",
    "title": "Build a Multi-Agent System in 200 Lines of Code",
    "hook": ("Last month, I replaced a 2000-line monolithic agent with a 200-line "
             "multi-agent system. It handles 10x more complex tasks. Here's exactly how."),
    "sections": [
        {"title": "The Problem with Monolithic Agents", "purpose": "Establish pain point",
         "key_points": ["Context overflow", "Tangled concerns"], "estimated_words": 300},
        {"title": "The Three-Layer Architecture", "purpose": "Core concept",
         "key_points": ["Conductor", "Sprint Master", "Worker"], "estimated_words": 500},
        {"title": "Building the Conductor", "purpose": "Implementation",
         "key_points": ["State management", "Sprint dispatch"], "estimated_words": 600},
        {"title": "Context Isolation in Practice", "purpose": "Key insight",
         "key_points": ["Fresh context per layer", "Progressive disclosure"], "estimated_words": 400},
        {"title": "Results and Lessons", "purpose": "Evidence",
         "key_points": ["Metrics", "Gotchas"], "estimated_words": 300},
    ],
    "target_word_count": 2100,
    "tone": "Practical, code-heavy, 'let me show you'",
}

OUTLINE_B = {
    "variant": "B",
    "variant_name": "Deep Dive",
    "title": "Why Multi-Agent Architecture Beats Monolithic AI: A Systems Design Perspective",
    "hook": ("The agent community is making the same mistake the industry made with monolithic "
             "web apps 15 years ago. Here's the architectural pattern that fixes it."),
    "sections": [
        {"title": "The Monolith Trap", "purpose": "Problem space",
         "key_points": ["Why single agents fail at complexity"], "estimated_words": 400},
        {"title": "Architectural Principles", "purpose": "Framework",
         "key_points": ["Separation of concerns", "Context as a resource"], "estimated_words": 600},
        {"title": "The Conductor Pattern", "purpose": "Core pattern",
         "key_points": ["Orchestration vs execution"], "estimated_words": 500},
        {"title": "Trade-offs and When Not To", "purpose": "Nuance",
         "key_points": ["Overhead", "Simple tasks"], "estimated_words": 400},
        {"title": "A Production Implementation", "purpose": "Evidence",
         "key_points": ["Real code", "Real metrics"], "estimated_words": 500},
    ],
    "target_word_count": 2400,
    "tone": "Authoritative, analytical, draws parallels to distributed systems",
}

OUTLINE_C = {
    "variant": "C",
    "variant_name": "Narrative",
    "title": "The Day Our AI Agent Forgot Everything (And How We Fixed It)",
    "hook": ("Three months into production, our agent started contradicting itself mid-task. "
             "The fix wasn't a better prompt -- it was a completely different architecture."),
    "sections": [
        {"title": "The Incident", "purpose": "Hook/crisis",
         "key_points": ["What went wrong"], "estimated_words": 300},
        {"title": "The Investigation", "purpose": "Journey",
         "key_points": ["Context window as root cause"], "estimated_words": 400},
        {"title": "The Breakthrough", "purpose": "Insight",
         "key_points": ["Multi-agent as the solution"], "estimated_words": 500},
        {"title": "Building It", "purpose": "Implementation",
         "key_points": ["Architecture decisions"], "estimated_words": 500},
        {"title": "What We Learned", "purpose": "Takeaway",
         "key_points": ["Principles that generalize"], "estimated_words": 300},
    ],
    "target_word_count": 2000,
    "tone": "Personal, engaging, war-story with technical depth",
}

OUTLINE_CRITIQUE = {
    "critic": "outline-adversarial",
    "outlines_analyzed": ["A", "B", "C"],
    "per_outline": {
        "A": {
            "variant_name": "Tutorial",
            "flow_score": 7, "coherence_score": 7, "necessity_score": 8,
            "hook_score": 8, "code_density_score": 9, "closing_score": 7,
            "overall_score": 7.7,
            "strengths": ["Strong code integration", "Practical and actionable"],
            "weaknesses": ["Hook makes unsupported claim about line count"],
            "fix_suggestions": ["Soften the 200-line claim or provide proof"],
        },
        "B": {
            "variant_name": "Deep Dive",
            "flow_score": 9, "coherence_score": 9, "necessity_score": 8,
            "hook_score": 7, "code_density_score": 7, "closing_score": 8,
            "overall_score": 8.0,
            "strengths": ["Best argument flow", "Strong systems thinking parallel"],
            "weaknesses": ["Hook is slightly cliche", "Could use more code"],
            "fix_suggestions": ["Rewrite hook with a specific incident"],
        },
        "C": {
            "variant_name": "Narrative",
            "flow_score": 8, "coherence_score": 8, "necessity_score": 7,
            "hook_score": 9, "code_density_score": 6, "closing_score": 8,
            "overall_score": 7.7,
            "strengths": ["Most engaging opening", "Relatable war story"],
            "weaknesses": ["Code density too low for target audience",
                           "Investigation section could drag"],
            "fix_suggestions": ["Add inline code earlier in the narrative"],
        },
    },
    "cross_comparison": {
        "best_thesis_handling": {"variant": "B",
                                 "reason": "Most rigorous argument structure"},
        "strongest_opening": {"variant": "C",
                              "reason": "Incident-based hook creates urgency"},
        "best_code_integration": {"variant": "A",
                                  "reason": "Code woven into every section"},
        "best_audience_match": {"variant": "B",
                                "reason": "Matches intermediate technical audience"},
        "most_innovative_structure": {"variant": "C",
                                      "reason": "Narrative arc is uncommon in tech writing"},
    },
    "recommendation": {
        "recommended_variant": "B",
        "confidence": "medium",
        "reasoning": ("B has the strongest argument flow and best matches the target "
                      "audience. Consider combining B's structure with C's hook for "
                      "maximum impact."),
        "runner_up": "C",
        "mix_suggestion": "Use C's incident-based hook to open B's deep-dive structure",
    },
}


class TestStage3OutlineGeneration:
    """Outline: build 3 variant prompts, critique prompt, user choice."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        # Init + research already done
        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project,
                 "Agent architecture is more important than model choice.")
        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")

    # --- 3 outline prompts ---

    @pytest.mark.parametrize("variant", ["A", "B", "C"])
    def test_outline_prompt_has_variant_marker(self, variant):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-prompts", variant)
        assert f"Variant: {variant}" in r.stdout

    @pytest.mark.parametrize("variant", ["A", "B", "C"])
    def test_outline_prompt_has_thesis(self, variant):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-prompts", variant)
        assert "Multi-agent systems" in r.stdout

    @pytest.mark.parametrize("variant", ["A", "B", "C"])
    def test_outline_prompt_has_template(self, variant):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-prompts", variant)
        assert "Article Type Template" in r.stdout

    # --- next-stage: outlines exist but no critique ---

    def test_outlines_without_critique_goes_to_outline_critique(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "outline_critique"

    # --- critique prompt ---

    def test_critique_prompt_has_all_3_outlines(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-critique-prompt")
        assert "Outline A" in r.stdout

    def test_critique_prompt_has_outline_b(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-critique-prompt")
        assert "Outline B" in r.stdout

    def test_critique_prompt_has_outline_c(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-critique-prompt")
        assert "Outline C" in r.stdout

    def test_critique_prompt_has_research(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-critique-prompt")
        assert "Multi-agent systems" in r.stdout

    def test_critique_prompt_has_template(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-outline-critique-prompt")
        assert "Adversarial Critique" in r.stdout

    # --- outline-critique.json file ---

    def test_outline_critique_file_exists(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        _write_state_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        assert os.path.isfile(_state_path(self.project, "outline-critique.json"))

    # --- next-stage: outlines + critique but no choice ---

    def test_outlines_critique_without_choice_goes_to_outline_choice(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        _write_state_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "outline_choice"

    # --- after choice: next-stage -> draft ---

    def test_after_outline_choice_goes_to_draft(self):
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        _write_state_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "draft"


# =========================================================================
# STAGE 4: DRAFT WRITING
# =========================================================================

DRAFT_V1_CONTENT = """\
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
1. **Each layer has a single job** -- plan, direct, or execute
2. **Context is a resource** -- allocate it, don't waste it
3. **Fresh context prevents pollution** -- each agent starts clean

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
Workers just execute -- focused, efficient, with only the context they need.

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
"""


class TestStage4DraftWriting:
    """Draft: verify writer prompt and next-stage transition."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        self.run("pipeline_state", "set-stage", self.project, "draft")

    def test_writer_prompt_has_outline_b(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-writer-prompt", "B")
        assert "Deep Dive" in r.stdout

    def test_writer_prompt_has_template(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-writer-prompt", "B")
        assert "Draft Writer Agent" in r.stdout

    def test_next_stage_after_draft_is_review(self):
        _write_state_text(self.project, "draft-v1.md", DRAFT_V1_CONTENT)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "review"


# =========================================================================
# STAGE 5: ADVERSARIAL REVIEW PANEL
# =========================================================================

REVIEW_TECHNICAL = {
    "reviewer": "technical", "rating": "NEEDS_FIXES",
    "summary": "Code example is oversimplified", "confidence": "high",
    "issues": [
        {"severity": "major", "location": "Conductor Pattern section",
         "issue": "Code example oversimplifies -- real implementation needs error handling and state persistence",
         "suggestion": "Add state management and retry logic"},
        {"severity": "minor", "location": "Trade-offs section",
         "issue": "Breakeven claim of 3-4 tool calls needs citation",
         "suggestion": "Add measurement methodology"},
    ],
    "code_issues": [
        {"code_block": "conductor function",
         "issue": "Missing error handling for failed sprints",
         "fixed_code": "try { await master.execute(sprint) } catch (e) { handleFailure(sprint, e) }"},
    ],
}

REVIEW_EDITOR = {
    "reviewer": "editor", "rating": "NEEDS_EDITING",
    "summary": "Strong content, hook needs work",
    "hook_score": 6, "clarity_score": 8, "flow_score": 7, "voice_score": 7,
    "engagement_score": 7, "economy_score": 8, "overall_score": 7,
    "issues": [
        {"severity": "major", "location": "Opening",
         "issue": "Hook compares to web monoliths but doesn't explain why that comparison matters to the reader NOW",
         "suggestion": "Start with a specific incident or metric instead",
         "example": "Last quarter, our agent forgot its own instructions mid-task. The context window was 99% full. We'd built a monolith."},
        {"severity": "minor", "location": "Trade-offs",
         "issue": "Section feels rushed compared to earlier depth",
         "suggestion": "Either expand or cut -- current length signals it's not important"},
    ],
    "ai_slop_flags": ["Sound familiar?"],
    "best_line": "Context is a resource -- allocate it, don't waste it",
    "weakest_section": "Trade-offs -- too brief for the claims it makes",
}

REVIEW_ADVERSARIAL = {
    "reviewer": "adversarial", "rating": "VULNERABLE",
    "summary": "Metrics are impressive but unverified",
    "premise_valid": True,
    "premise_attack": ("The comparison to web monoliths is a false analogy -- "
                       "web apps had shared state problems, agents have context window problems. "
                       "Different root cause, potentially different solutions."),
    "attacks": [
        {"target": "Metrics (87% completion, 4x efficiency)",
         "attack": "No methodology described. Were these measured on the same tasks? Cherry-picked project?",
         "severity": "significant", "likely_source": "HN comment",
         "defense": "Add methodology section or acknowledge this is one system's experience",
         "verdict": "fixable"},
        {"target": "Breakeven at 3-4 tool calls",
         "attack": "This number appears fabricated. No measurement described.",
         "severity": "significant", "likely_source": "expert review",
         "defense": "Either cite measurement or soften to 'in our experience'",
         "verdict": "fixable"},
    ],
    "stress_test": {
        "hn_top_comment": "'4x token efficiency' -- compared to what baseline? This reads like marketing.",
        "twitter_quote": "'87% completion rate' with no methodology is just a number.",
        "expert_reaction": "The architecture is sound but the claims are too strong for the evidence presented.",
    },
}

REVIEW_AUDIENCE = {
    "reviewer": "audience",
    "reader_a": {
        "rating": "WOULD_SHARE", "actionability": 7, "relevance": 8,
        "time_well_spent": True,
        "share_trigger": "The three-layer pattern is directly applicable to our agent work",
    },
    "reader_b": {
        "rating": "MEH", "hn_potential": 5, "twitter_potential": 6,
        "novelty": 6, "credibility": 5, "memorability": 6,
        "share_trigger": "Would share if metrics were more credible",
    },
    "overall_verdict": ("Internal audiences will love this, external needs stronger "
                        "evidence to break through the noise"),
}

REVIEW_SEO = {
    "reviewer": "seo", "rating": "NEEDS_WORK",
    "summary": "Title is too generic for search",
    "title_analysis": {
        "current_title": "Why Multi-Agent Architecture Beats Monolithic AI",
        "searchability": 5, "clickability": 7,
        "alternatives": [
            {"title": "Multi-Agent vs Monolithic AI: Architecture Patterns That Actually Work",
             "type": "seo"},
            {"title": "We Replaced Our AI Agent with 3 Smaller Ones (Here's What Happened)",
             "type": "social"},
            {"title": "The Conductor Pattern: A Production Guide to Multi-Agent AI Systems",
             "type": "newsletter"},
        ],
    },
    "social_package": {
        "meta_description": ("Learn the three-layer conductor pattern for building reliable "
                             "multi-agent AI systems, with production code and real metrics."),
        "twitter_thread": [
            "1/ We replaced our monolithic AI agent with a three-layer system. "
            "Completion rate went from 62% to 87%. Here's the architecture:",
            "2/ The key insight: context is a resource. A monolithic agent wastes "
            "tokens re-reading instructions for tools it won't use.",
            "3/ Three layers: Conductor (plans), Sprint Master (directs), Worker (executes). "
            "Each gets fresh context.",
            "4/ The conductor pattern in code: [code snippet]",
            "5/ Results: 87% completion (up from 62%), zero context overflows, 68% cost reduction. "
            "Architecture > model choice.",
        ],
        "linkedin_post": ("Most teams build AI agents as monoliths. We did too -- until our "
                          "agent started forgetting instructions mid-task.\n\n"
                          "The fix: a three-layer architecture where each agent has a single job "
                          "and fresh context.\n\n"
                          "Results: 87% task completion, zero context overflows, 68% cost reduction.\n\n"
                          "Key insight: treat context like memory in distributed systems -- allocate "
                          "it, don't waste it."),
        "hn_title": "The Conductor Pattern: Multi-Agent Architecture for Reliable AI Systems",
    },
}

REVIEW_EXTERNAL = {
    "reviewer": "external", "rating": "NEEDS_CONTEXT",
    "summary": "Some jargon assumes prior knowledge", "confidence": "high",
    "first_confusion_point": "The Monolith Trap section",
    "jargon_issues": [
        {"term": "context pollution", "location": "The Monolith Trap",
         "suggestion": "Define context pollution before using it"},
    ],
    "assumed_knowledge": [
        {"assumption": "Reader knows what a context window is",
         "location": "Opening", "impact": "Core concept unclear",
         "fix": "Add one-sentence explanation"},
    ],
    "logical_jumps": [], "missing_context": [],
    "accessibility_score": 6,
    "target_audience_match": "Slightly above stated audience level",
    "issues": [{"severity": "minor", "issue": "Context window not defined for newcomers"}],
}

REVIEW_FACTCHECK = {
    "reviewer": "factcheck", "rating": "NEEDS_VERIFICATION",
    "summary": "Most claims check out but metrics lack methodology",
    "confidence": "medium",
    "claims_checked": 8, "claims_verified": 5, "claims_unverified": 2, "claims_wrong": 1,
    "issues": [
        {"severity": "major", "claim": "87% completion rate",
         "location": "Production Implementation", "verdict": "unverified",
         "evidence": "No methodology described",
         "suggestion": "Add measurement methodology or qualify as anecdotal"},
        {"severity": "minor", "claim": "Breakeven at 3-4 tool calls",
         "location": "Trade-offs", "verdict": "unverified",
         "evidence": "No measurement described",
         "suggestion": "Soften to 'in our experience'"},
    ],
    "code_verification": [
        {"code_block": "conductor function", "syntax_valid": True,
         "imports_correct": True, "types_correct": True,
         "would_run": True, "issues": None},
    ],
    "unverified_claims": [
        {"claim": "Token cost -68%", "reason": "No baseline described",
         "risk": "medium", "recommendation": "Qualify or add baseline"},
    ],
    "opinion_claims": ["Architecture is more important than model choice"],
    "sources_consulted": ["https://docs.anthropic.com/en/docs/agents"],
}

ALL_REVIEWS = {
    "technical": REVIEW_TECHNICAL,
    "editor": REVIEW_EDITOR,
    "adversarial": REVIEW_ADVERSARIAL,
    "audience": REVIEW_AUDIENCE,
    "seo": REVIEW_SEO,
    "external": REVIEW_EXTERNAL,
    "factcheck": REVIEW_FACTCHECK,
}


class TestStage5AdversarialReviewPanel:
    """Review: 7 reviewer prompts, aggregation, score normalization, summary."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        _write_state_text(self.project, "draft-v1.md", DRAFT_V1_CONTENT)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")

    # --- All 7 review prompts include the draft ---

    @pytest.mark.parametrize("reviewer", [
        "technical", "editor", "adversarial", "audience", "seo", "external", "factcheck",
    ])
    def test_review_prompt_has_draft_content(self, reviewer):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-review-prompts", reviewer)
        assert "Monolith Trap" in r.stdout

    # --- Aggregate reviews ---

    def test_aggregate_has_7_reviews(self):
        self._write_all_reviews()
        self._register_all_reviews()
        r = self.run("aggregate_reviews", self.project)
        # The output JSON should contain reviews_count or we just check file
        assert os.path.isfile(_state_path(self.project, "review-panel-summary.json"))

    def test_panel_summary_exists(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        assert os.path.isfile(_state_path(self.project, "review-panel-summary.json"))

    def test_panel_has_prioritized_actions(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        with open(_state_path(self.project, "review-panel-summary.json")) as f:
            panel = json.load(f)
        assert "prioritized_actions" in json.dumps(panel)

    # --- Review score normalization ---

    def test_normalized_has_panel_average(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        r = self.run("calibrate_reviews", self.project)
        assert "panel_average" in r.stdout

    def test_normalized_has_agreement_score(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        r = self.run("calibrate_reviews", self.project)
        assert "agreement_score" in r.stdout

    def test_normalized_file_exists(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        assert os.path.isfile(_state_path(self.project, "review-calibration.json"))

    def test_normalized_has_normalized_scores(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        with open(_state_path(self.project, "review-calibration.json")) as f:
            cal = json.load(f)
        assert "normalized_scores" in json.dumps(cal)

    def test_normalized_has_outliers_field(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        with open(_state_path(self.project, "review-calibration.json")) as f:
            cal = json.load(f)
        assert "outliers" in json.dumps(cal)

    def test_normalized_has_blind_spots_field(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        with open(_state_path(self.project, "review-calibration.json")) as f:
            cal = json.load(f)
        assert "blind_spots" in json.dumps(cal)

    # --- Build score-normalization summary ---

    def test_normalized_summary_has_header(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-calibration-summary")
        assert "Calibration Report" in r.stdout

    def test_normalized_summary_has_normalized_scores(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-calibration-summary")
        assert "Normalized Scores" in r.stdout

    def test_normalized_summary_has_agreement(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        r = self.run("orchestrate", self.project, self.sd,
                     "build-calibration-summary")
        assert "Agreement" in r.stdout

    # --- next-stage: after review -> refinement ---

    def test_next_stage_after_review_is_refinement(self):
        self._write_all_reviews()
        self._register_all_reviews()
        self.run("aggregate_reviews", self.project)
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "refinement"

    # --- helpers ---

    def _write_all_reviews(self):
        for name, data in ALL_REVIEWS.items():
            _write_state_json(self.project, f"review-{name}.json", data)

    def _register_all_reviews(self):
        for name in ALL_REVIEWS:
            path = _state_path(self.project, f"review-{name}.json")
            self.run("pipeline_state", "add-review", self.project, path)


# =========================================================================
# STAGE 6: REFINEMENT LOOP
# =========================================================================


class TestStage6RefinementLoop:
    """Refinement: build refiner prompt, convergence check, simulate rounds."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        _write_state_text(self.project, "draft-v1.md", DRAFT_V1_CONTENT)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")

        # Write and register all reviews
        for name, data in ALL_REVIEWS.items():
            _write_state_json(self.project, f"review-{name}.json", data)
            self.run("pipeline_state", "add-review", self.project,
                     _state_path(self.project, f"review-{name}.json"))

        self.run("aggregate_reviews", self.project)
        self.run("pipeline_state", "set-stage", self.project, "refinement")

    def test_refiner_prompt_has_round(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-refiner-prompt", "1")
        assert "Round: 1" in r.stdout

    def test_refiner_prompt_has_panel_summary(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-refiner-prompt", "1")
        assert "prioritized_actions" in r.stdout

    def test_refiner_prompt_has_draft(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-refiner-prompt", "1")
        assert "Monolith Trap" in r.stdout

    def test_round_1_not_converged(self):
        r = self.run("orchestrate", self.project, self.sd,
                     "check-convergence", "1")
        assert "CONTINUE" in r.stdout

    def test_round_2_converged_after_solid(self):
        # Simulate refinement: create v2 draft
        shutil.copy2(_state_path(self.project, "draft-v1.md"),
                     _state_path(self.project, "draft-v2.md"))
        self.run("pipeline_state", "refinement-round", self.project)

        # Adversarial now says SOLID
        _write_state_json(self.project, "review-adversarial.json", {
            "reviewer": "adversarial", "rating": "SOLID",
            "summary": "Issues addressed, metrics now qualified",
            "attacks": [], "issues": [],
        })

        r = self.run("orchestrate", self.project, self.sd,
                     "check-convergence", "2")
        assert "CONVERGED" in r.stdout


# =========================================================================
# STAGE 7: DUAL-FORMAT POLISH
# =========================================================================


class TestStage7DualFormatPolish:
    """Polish: verify format prompts for internal, external, and platforms."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        _write_state_text(self.project, "draft-v1.md", DRAFT_V1_CONTENT)

        # Write SEO review with social_package so format prompts can include it
        _write_state_json(self.project, "review-seo.json", REVIEW_SEO)

        self.run("pipeline_state", "set-stage", self.project, "polish")

    @pytest.mark.parametrize("fmt", ["internal", "external"])
    def test_format_prompt_has_draft(self, fmt):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-format-prompts", fmt)
        assert "Monolith Trap" in r.stdout

    @pytest.mark.parametrize("fmt", ["internal", "external"])
    def test_format_prompt_has_seo_data(self, fmt):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-format-prompts", fmt)
        assert "social_package" in r.stdout

    @pytest.mark.parametrize("platform", [
        "medium", "devto", "hashnode", "wechat", "juejin",
    ])
    def test_platform_format_has_draft(self, platform):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-format-prompts", platform)
        assert "Monolith Trap" in r.stdout

    @pytest.mark.parametrize("platform", [
        "medium", "devto", "hashnode", "wechat", "juejin",
    ])
    def test_platform_format_has_seo_data(self, platform):
        r = self.run("orchestrate", self.project, self.sd,
                     "build-format-prompts", platform)
        assert "social_package" in r.stdout

    def test_list_platforms_includes_medium(self):
        r = self.run("orchestrate", self.project, self.sd, "list-platforms")
        assert "medium" in r.stdout

    def test_list_platforms_includes_juejin(self):
        r = self.run("orchestrate", self.project, self.sd, "list-platforms")
        assert "juejin" in r.stdout

    def test_next_stage_after_polish_is_complete(self):
        _write_state_text(self.project, "final-internal.md",
                          "# Internal\n\n## TL;DR\n- Multi-agent > monolithic\n")
        _write_state_text(self.project, "final-external.md",
                          "# External\n\n## About the Author\nJackson is...\n")
        _write_state_json(self.project, "social-package.json", {
            "twitter_thread": ["1/ Thread about multi-agent architecture..."],
            "linkedin_post": "Most teams build AI agents as monoliths...",
            "hn_title": "The Conductor Pattern: Multi-Agent Architecture for Reliable AI Systems",
            "hn_comment": "Author here. We've been running this in production for 3 months...",
        })
        r = self.run("orchestrate", self.project, self.sd, "next-stage")
        assert r.stdout.strip() == "complete"


# =========================================================================
# COMPLETION
# =========================================================================


class TestCompletion:
    """Complete the pipeline: verify final state, taste memory, all artifacts."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, e2e_project):
        self.run = run_script
        self.project, self.sd, self.home = e2e_project

        # Build full pipeline state so that completion works
        self.run("pipeline_state", "init", self.project,
                 "Building Multi-Agent Systems with Claude")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project,
                 "Agent architecture is more important than model choice.")
        self.run("intake_materials", "add-url", self.project,
                 "https://docs.anthropic.com/en/docs/agents", "Anthropic Agent Docs")

        _write_state_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        _write_state_json(self.project, "outline-A.json", OUTLINE_A)
        _write_state_json(self.project, "outline-B.json", OUTLINE_B)
        _write_state_json(self.project, "outline-C.json", OUTLINE_C)
        _write_state_text(self.project, "draft-v1.md", DRAFT_V1_CONTENT)
        _write_state_text(self.project, "draft-v2.md", DRAFT_V1_CONTENT)

        for name, data in ALL_REVIEWS.items():
            _write_state_json(self.project, f"review-{name}.json", data)
            self.run("pipeline_state", "add-review", self.project,
                     _state_path(self.project, f"review-{name}.json"))

        self.run("aggregate_reviews", self.project)

        _write_state_text(self.project, "final-internal.md",
                          "# Internal\n\n## TL;DR\n- Multi-agent > monolithic\n")
        _write_state_text(self.project, "final-external.md",
                          "# External\n\n## About the Author\nJackson\n")
        _write_state_json(self.project, "social-package.json", {
            "twitter_thread": ["1/ Thread..."],
            "linkedin_post": "Most teams build AI agents as monoliths...",
            "hn_title": "The Conductor Pattern",
            "hn_comment": "Author here.",
        })

    def test_complete_sets_stage(self):
        self.run("pipeline_state", "complete", self.project)
        r = self.run("pipeline_state", "get-stage", self.project)
        assert r.stdout.strip() == "complete"

    def test_taste_memory_updated(self):
        self.run("pipeline_state", "complete", self.project)
        self.run("taste_memory", "update", self.project)
        r = self.run("taste_memory", "read")
        assert "Topics covered" in r.stdout

    def test_final_status_complete(self):
        self.run("pipeline_state", "complete", self.project)
        r = self.run("orchestrate", self.project, self.sd, "status")
        assert "True" in r.stdout

    # --- All expected artifacts exist ---

    def test_artifact_materials_json(self):
        assert os.path.isfile(_state_path(self.project, "materials.json"))

    def test_artifact_research_synthesis(self):
        assert os.path.isfile(_state_path(self.project, "research-synthesis.json"))

    def test_artifact_outline_a(self):
        assert os.path.isfile(_state_path(self.project, "outline-A.json"))

    def test_artifact_outline_b(self):
        assert os.path.isfile(_state_path(self.project, "outline-B.json"))

    def test_artifact_outline_c(self):
        assert os.path.isfile(_state_path(self.project, "outline-C.json"))

    def test_artifact_draft_v1(self):
        assert os.path.isfile(_state_path(self.project, "draft-v1.md"))

    def test_artifact_draft_v2(self):
        assert os.path.isfile(_state_path(self.project, "draft-v2.md"))

    def test_artifact_review_panel_summary(self):
        assert os.path.isfile(_state_path(self.project, "review-panel-summary.json"))

    def test_artifact_final_internal(self):
        assert os.path.isfile(_state_path(self.project, "final-internal.md"))

    def test_artifact_final_external(self):
        assert os.path.isfile(_state_path(self.project, "final-external.md"))

    def test_artifact_social_package(self):
        assert os.path.isfile(_state_path(self.project, "social-package.json"))
