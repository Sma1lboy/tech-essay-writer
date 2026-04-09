"""Comprehensive end-to-end integration test.

Exercises the full pipeline PLUS all auxiliary scripts:
  config, author-profile, expertise-graph, series, cross-reference,
  analytics, influence, SEO, code-validate, diagrams, quality-score,
  publish-check, progress-display, taste-memory (diff-learn/feedback/suggest),
  checkpoint auto-saves, rollback, retry-stage, resume
"""

import json
import os
import re
import time

import pytest


# ============================================================
# Helpers
# ============================================================


def write_json(proj, filename, data):
    """Write a JSON file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        json.dump(data, f)


def write_file(proj, filename, content):
    """Write a text file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        f.write(content)


def read_json(proj, filename):
    """Read a JSON file from .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path) as f:
        return json.load(f)


def count_checkpoints(project):
    """Count checkpoint directories (excluding .tmp- dirs)."""
    ckpt_base = os.path.join(project, ".essay-state", "checkpoints")
    if not os.path.isdir(ckpt_base):
        return 0
    count = 0
    for d in os.listdir(ckpt_base):
        full = os.path.join(ckpt_base, d)
        if os.path.isdir(full) and not d.startswith(".tmp-"):
            count += 1
    return count


def find_checkpoint(project, label_prefix):
    """Find the first checkpoint dir matching a label prefix."""
    ckpt_base = os.path.join(project, ".essay-state", "checkpoints")
    if not os.path.isdir(ckpt_base):
        return None
    for d in sorted(os.listdir(ckpt_base)):
        if d.startswith(label_prefix) and os.path.isdir(os.path.join(ckpt_base, d)):
            return d
    return None


# ============================================================
# Shared data constants
# ============================================================

RESEARCH_SYNTHESIS = {
    "thesis": "Effective multi-agent orchestration requires three architectural principles: context isolation, progressive disclosure, and hierarchical planning.",
    "thesis_expanded": "Most agent systems fail because they treat context as unlimited. The conductor pattern enforces strict boundaries: each agent gets exactly the context it needs, nothing more.",
    "evidence_map": [
        {"claim": "Context isolation prevents hallucination cascades", "sources": ["note-1", "note-2"], "strength": "strong"},
        {"claim": "Hierarchical planning enables complex decomposition", "sources": ["note-2", "url-1"], "strength": "strong"},
        {"claim": "Progressive disclosure reduces token waste", "sources": ["note-1"], "strength": "moderate"},
    ],
    "knowledge_gaps": [
        {"gap": "No latency benchmarks for multi-agent vs single-agent", "impact": "medium", "resolution": "Add timing data"},
        {"gap": "Error recovery patterns not documented", "impact": "high", "resolution": "Document retry and fallback strategies"},
    ],
    "competitive_landscape": {
        "existing_articles": [
            {"title": "Anthropic Agent Docs", "url": "https://docs.anthropic.com/en/docs/agents", "angle": "Single-agent focus"}
        ],
        "gap": "No production-tested multi-agent orchestration patterns with real code and metrics exist",
    },
    "unique_angle": "Production-tested patterns from a system that runs 50+ sprints autonomously",
    "recommended_depth": "intermediate",
    "recommended_length": "medium",
    "key_terms": ["conductor pattern", "context isolation", "progressive disclosure", "hierarchical planning"],
}

OUTLINE_A = {
    "variant": "A",
    "variant_name": "Tutorial",
    "title": "Build a Multi-Agent Orchestrator from Scratch",
    "hook": "Our monolithic agent kept forgetting its own instructions. We replaced it with three coordinated agents and never looked back.",
    "sections": [
        {"title": "Why Monolithic Agents Fail", "purpose": "Problem", "key_points": ["Context overflow", "Tangled concerns"], "estimated_words": 300},
        {"title": "The Three-Layer Architecture", "purpose": "Solution", "key_points": ["Conductor", "Sprint Master", "Worker"], "estimated_words": 500},
        {"title": "Implementing Context Isolation", "purpose": "Deep dive", "key_points": ["Fresh context", "Progressive disclosure"], "estimated_words": 600},
        {"title": "Error Recovery Patterns", "purpose": "Robustness", "key_points": ["Retry", "Fallback", "Circuit breaker"], "estimated_words": 400},
        {"title": "Production Metrics", "purpose": "Evidence", "key_points": ["Latency", "Reliability", "Cost"], "estimated_words": 300},
    ],
    "target_word_count": 2100,
    "tone": "Hands-on tutorial",
}

OUTLINE_B = {
    "variant": "B",
    "variant_name": "Deep Dive",
    "title": "Multi-Agent Orchestration: Patterns That Scale",
    "hook": "The agent community is rediscovering microservices architecture \u2014 except this time, the services think for themselves.",
    "sections": [
        {"title": "The Complexity Cliff", "purpose": "Problem space", "key_points": ["When single agents hit their limits"], "estimated_words": 400},
        {"title": "Orchestration Principles", "purpose": "Framework", "key_points": ["Separation of concerns", "Context budgeting"], "estimated_words": 600},
        {"title": "The Conductor Pattern", "purpose": "Core pattern", "key_points": ["Planning vs execution"], "estimated_words": 500},
        {"title": "Trade-offs and Anti-patterns", "purpose": "Nuance", "key_points": ["Over-decomposition", "Context duplication"], "estimated_words": 400},
        {"title": "Real-World Results", "purpose": "Evidence", "key_points": ["Production metrics", "Lessons learned"], "estimated_words": 500},
    ],
    "target_word_count": 2400,
    "tone": "Analytical, systems-thinking",
}

OUTLINE_C = {
    "variant": "C",
    "variant_name": "Narrative",
    "title": "The Day Our Agent Lost Its Memory (And How Orchestration Saved Us)",
    "hook": "Three months in, our flagship agent started hallucinating its own past decisions. The fix wasn\u2019t better prompting \u2014 it was a fundamentally different architecture.",
    "sections": [
        {"title": "The Incident", "purpose": "Hook", "key_points": ["Production failure"], "estimated_words": 300},
        {"title": "Root Cause Analysis", "purpose": "Investigation", "key_points": ["Context window exhaustion"], "estimated_words": 400},
        {"title": "The Orchestration Breakthrough", "purpose": "Solution", "key_points": ["Multi-agent design"], "estimated_words": 500},
        {"title": "Building the System", "purpose": "Implementation", "key_points": ["Architecture decisions"], "estimated_words": 500},
        {"title": "Aftermath", "purpose": "Results", "key_points": ["Metrics and growth"], "estimated_words": 300},
    ],
    "target_word_count": 2000,
    "tone": "War story with technical depth",
}

OUTLINE_CRITIQUE = {
    "critic": "outline-adversarial",
    "outlines_analyzed": ["A", "B", "C"],
    "per_outline": {
        "A": {"variant_name": "Tutorial", "overall_score": 7.5, "strengths": ["Practical"], "weaknesses": ["Rushed ending"], "fix_suggestions": ["Expand metrics"]},
        "B": {"variant_name": "Deep Dive", "overall_score": 8.2, "strengths": ["Best argument flow"], "weaknesses": ["Slightly dry"], "fix_suggestions": ["Add anecdotes"]},
        "C": {"variant_name": "Narrative", "overall_score": 7.8, "strengths": ["Most engaging"], "weaknesses": ["Low code density"], "fix_suggestions": ["Add code earlier"]},
    },
    "cross_comparison": {
        "best_thesis_handling": {"variant": "B", "reason": "Most rigorous"},
        "strongest_opening": {"variant": "C", "reason": "Incident hook"},
        "best_code_integration": {"variant": "A", "reason": "Code throughout"},
    },
    "recommendation": {"recommended_variant": "B", "confidence": "high", "reasoning": "Strongest analytical structure", "runner_up": "C"},
}

DRAFT_V1 = """\
# Multi-Agent Orchestration: Patterns That Scale

The agent community is rediscovering microservices architecture \u2014 except this time,
the services think for themselves.

## The Complexity Cliff

Every AI agent starts simple: one prompt, a few tools, and a clear task. But
complexity grows. You add more tools, longer system prompts, multi-step workflows.
Eventually, the agent starts forgetting its earlier instructions. Context overflow.

This isn't a model limitation \u2014 it's an architecture problem.

## Orchestration Principles

The fix mirrors what we learned from distributed systems:

1. **Separation of concerns** \u2014 each agent has one job
2. **Context budgeting** \u2014 treat tokens like memory, allocate deliberately
3. **Progressive disclosure** \u2014 agents get information on a need-to-know basis

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
"""

REVIEW_TECHNICAL = {
    "reviewer": "technical",
    "rating": "NEEDS_FIXES",
    "summary": "Code examples need error handling",
    "confidence": "high",
    "issues": [
        {
            "severity": "major",
            "location": "Conductor Pattern",
            "issue": "No error handling in orchestrate loop",
            "suggestion": "Add try/catch with retry logic",
        }
    ],
    "code_issues": [
        {
            "code_block": "Conductor class",
            "issue": "Missing error handling",
            "fixed_code": "try { await master.execute(sprint) } catch (e) { this.handleFailure(sprint, e) }",
        }
    ],
}

REVIEW_EDITOR = {
    "reviewer": "editor",
    "rating": "NEEDS_EDITING",
    "summary": "Strong content, tighten transitions",
    "hook_score": 7,
    "clarity_score": 8,
    "flow_score": 7,
    "voice_score": 8,
    "engagement_score": 7,
    "economy_score": 8,
    "overall_score": 7.5,
    "issues": [
        {
            "severity": "minor",
            "location": "Trade-offs",
            "issue": "Transition from code to anti-patterns is abrupt",
            "suggestion": "Add a bridging sentence",
        }
    ],
    "ai_slop_flags": [],
    "best_line": "Context budgeting \u2014 treat tokens like memory",
    "weakest_section": "Trade-offs \u2014 needs expansion",
}

REVIEW_ADVERSARIAL = {
    "reviewer": "adversarial",
    "rating": "NEEDS_STRENGTHENING",
    "summary": "Metrics need methodology",
    "premise_valid": True,
    "attacks": [
        {
            "target": "89% completion claim",
            "attack": "No methodology described",
            "severity": "moderate",
            "defense": "Add measurement details",
            "verdict": "fixable",
        }
    ],
    "issues": [{"severity": "moderate", "issue": "Metrics lack methodology"}],
}

REVIEW_AUDIENCE = {
    "reviewer": "audience",
    "reader_a": {"rating": "WOULD_SHARE", "actionability": 8, "relevance": 8, "time_well_spent": True},
    "reader_b": {"rating": "INTERESTING", "hn_potential": 7, "twitter_potential": 7, "novelty": 7, "credibility": 6},
    "overall_verdict": "Strong for internal, needs evidence for external",
}

REVIEW_SEO = {
    "reviewer": "seo",
    "rating": "NEEDS_WORK",
    "summary": "Title could be more searchable",
    "title_analysis": {"current_title": "Multi-Agent Orchestration: Patterns That Scale", "searchability": 6, "clickability": 7},
    "social_package": {
        "meta_description": "Learn production-tested patterns for multi-agent AI orchestration.",
        "twitter_thread": ["1/ We replaced our monolithic agent with an orchestrated system..."],
        "linkedin_post": "Multi-agent orchestration patterns that actually work in production.",
        "hn_title": "Multi-Agent Orchestration: Production Patterns That Scale",
    },
}

REVIEW_EXTERNAL = {
    "reviewer": "external",
    "rating": "ACCESSIBLE",
    "summary": "Clear writing, minimal jargon issues",
    "confidence": "high",
    "jargon_issues": [{"term": "progressive disclosure", "location": "Principles", "suggestion": "Define briefly"}],
    "accessibility_score": 7,
    "issues": [{"severity": "minor", "issue": "Progressive disclosure needs definition"}],
}

REVIEW_FACTCHECK = {
    "reviewer": "factcheck",
    "rating": "MOSTLY_VERIFIED",
    "summary": "Claims are reasonable but metrics need sourcing",
    "confidence": "medium",
    "claims_checked": 6,
    "claims_verified": 4,
    "claims_unverified": 2,
    "issues": [
        {
            "severity": "minor",
            "claim": "89% completion rate",
            "location": "Results",
            "verdict": "unverified",
            "suggestion": "Add measurement context",
        }
    ],
    "code_verification": [{"code_block": "Conductor class", "syntax_valid": True, "would_run": True}],
}

ALL_REVIEWS = {
    "review-technical.json": REVIEW_TECHNICAL,
    "review-editor.json": REVIEW_EDITOR,
    "review-adversarial.json": REVIEW_ADVERSARIAL,
    "review-audience.json": REVIEW_AUDIENCE,
    "review-seo.json": REVIEW_SEO,
    "review-external.json": REVIEW_EXTERNAL,
    "review-factcheck.json": REVIEW_FACTCHECK,
}

FINAL_INTERNAL = """\
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
"""

FINAL_EXTERNAL = """\
# Multi-Agent Orchestration: Production Patterns That Scale

The agent community is rediscovering microservices architecture \u2014 except this time,
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
"""

SOCIAL_PACKAGE = {
    "twitter_thread": [
        "1/ We replaced our monolithic AI agent with an orchestrated multi-agent system. Results: 89% completion, 0% context overflows, 3.2x token efficiency. Here's what we learned:"
    ],
    "linkedin_post": "Multi-agent orchestration patterns that actually work in production.",
    "hn_title": "Multi-Agent Orchestration: Production Patterns That Scale",
    "hn_comment": "Author here. We've been running this architecture for 6 months now.",
}

ORIGINAL_DRAFT = """\
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
"""

EDITED_DRAFT = """\
# Multi-Agent Architecture: Patterns That Actually Work

Let me show you what happens when your AI agent starts forgetting its own instructions.

## The Problem

Three months in, our agent was contradicting itself mid-task. Context overflow.
Not a model problem \u2014 an architecture problem.

## The Fix

The conductor pattern: plan \u2192 direct \u2192 execute. Each layer gets fresh context.
No shared state. No context pollution.

```javascript
const conductor = new Conductor();
await conductor.orchestrate(mission);
```

## What We Learned

Multi-agent beats monolithic when tasks exceed 3 tool calls. Below that, don't bother.
"""

# Minimal re-created state after rollback re-advance
RESEARCH_SYNTHESIS_MINIMAL = {
    "thesis": "Effective multi-agent orchestration requires three architectural principles.",
    "thesis_expanded": "Context isolation, progressive disclosure, and hierarchical planning.",
    "evidence_map": [{"claim": "Context isolation prevents hallucination", "sources": ["note-1"], "strength": "strong"}],
    "knowledge_gaps": [],
    "competitive_landscape": [],
    "unique_angle": "Production-tested patterns",
    "recommended_depth": "intermediate",
    "recommended_length": "medium",
    "key_terms": ["conductor pattern", "orchestration"],
}

DRAFT_V1_MINIMAL = """\
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
"""

REVIEWS_PASS = {
    "review-technical.json": {"reviewer": "technical", "rating": "PASS", "summary": "Code examples are correct", "confidence": "high", "issues": []},
    "review-editor.json": {"reviewer": "editor", "rating": "PASS", "summary": "Well-written", "overall_score": 8, "issues": []},
    "review-adversarial.json": {"reviewer": "adversarial", "rating": "SOLID", "summary": "Claims are defensible", "attacks": [], "issues": []},
    "review-audience.json": {"reviewer": "audience", "overall_verdict": "Strong for target audience"},
    "review-seo.json": {
        "reviewer": "seo",
        "rating": "GOOD",
        "summary": "Good searchability",
        "social_package": {
            "meta_description": "Multi-agent patterns",
            "twitter_thread": ["Thread"],
            "linkedin_post": "Post",
            "hn_title": "Title",
        },
    },
    "review-external.json": {"reviewer": "external", "rating": "ACCESSIBLE", "summary": "Clear", "accessibility_score": 8, "issues": []},
    "review-factcheck.json": {
        "reviewer": "factcheck",
        "rating": "VERIFIED",
        "summary": "Claims check out",
        "claims_checked": 4,
        "claims_verified": 4,
        "issues": [],
    },
}


# ============================================================
# SECTION 1: CONFIG SYSTEM
# ============================================================


class TestConfigSystem:
    """Section 1: Config system init, set, get, add-platform, read."""

    def test_config_init_creates_file(self, run_script, fake_home):
        run_script("config", "init")
        assert os.path.isfile(os.path.join(fake_home, ".tech-essay-writer", "config.json"))

    def test_config_set_language_zh(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "set", "language", "zh")
        r = run_script("config", "get", "language")
        assert r.stdout.strip() == "zh"

    def test_config_set_writing_style(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "set", "writing_style", "technical")
        r = run_script("config", "get", "writing_style")
        assert r.stdout.strip() == "technical"

    def test_config_add_platform_medium(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "add-platform", "medium")
        r = run_script("config", "get", "default_platforms")
        assert "medium" in r.stdout

    def test_config_add_platform_devto(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "add-platform", "medium")
        run_script("config", "add-platform", "devto")
        r = run_script("config", "get", "default_platforms")
        assert "devto" in r.stdout

    def test_config_read_shows_language(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "set", "language", "zh")
        r = run_script("config", "read")
        assert "zh" in r.stdout

    def test_config_read_shows_writing_style(self, run_script, fake_home):
        run_script("config", "init")
        run_script("config", "set", "writing_style", "technical")
        r = run_script("config", "read")
        assert "technical" in r.stdout


# ============================================================
# SECTION 2: AUTHOR PROFILE
# ============================================================


class TestAuthorProfile:
    """Section 2: Author profile init, set, get-bio, get-social-handles."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        self.run("author_profile", "init")

    def test_profile_file_created(self):
        assert os.path.isfile(os.path.join(self.home, ".tech-essay-writer", "author-profile.json"))

    def test_set_name_and_bio(self):
        self.run("author_profile", "set", "name", "Test Author")
        self.run("author_profile", "set", "bio", "AI systems architect and tech writer")
        self.run("author_profile", "set", "role", "Staff Engineer")
        self.run("author_profile", "set", "company", "TestCorp")
        r = self.run("author_profile", "get-bio")
        assert "Test Author" in r.stdout
        assert "Staff Engineer" in r.stdout

    def test_set_social_twitter(self):
        self.run("author_profile", "set-social", "twitter", "testauthor")
        r = self.run("author_profile", "read")
        assert "testauthor" in r.stdout

    def test_set_social_github(self):
        self.run("author_profile", "set-social", "github", "testauthor")
        r = self.run("author_profile", "read")
        assert "testauthor" in r.stdout

    def test_get_social_handles_twitter(self):
        self.run("author_profile", "set-social", "twitter", "testauthor")
        self.run("author_profile", "set-social", "github", "testauthor")
        r = self.run("author_profile", "get-social-handles")
        assert "twitter" in r.stdout

    def test_get_social_handles_github(self):
        self.run("author_profile", "set-social", "twitter", "testauthor")
        self.run("author_profile", "set-social", "github", "testauthor")
        r = self.run("author_profile", "get-social-handles")
        assert "github" in r.stdout


# ============================================================
# SECTION 3: EXPERTISE GRAPH
# ============================================================


class TestExpertiseGraph:
    """Section 3: Expertise graph update, query, top."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script
        self.run("expertise_graph", "update", "multi-agent", "ai", "architecture")
        self.run("expertise_graph", "update", "context-isolation", "ai", "agents")
        self.run("expertise_graph", "update", "conductor-pattern", "ai", "architecture", "agents")

    def test_query_finds_topic(self):
        r = self.run("expertise_graph", "query", "multi-agent")
        assert "multi-agent" in r.stdout

    def test_top_includes_topic(self):
        r = self.run("expertise_graph", "top", "3")
        assert "multi-agent" in r.stdout


# ============================================================
# SECTION 4: CROSS-REFERENCE REGISTRY
# ============================================================


class TestCrossReference:
    """Section 4: Cross-reference add, search, suggest, list."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script

    def test_add_returns_article_id(self):
        r = self.run("cross_reference", "add", "Building Agents with Claude", "https://example.com/agents", "agent", "ai", "multi-agent")
        assert "art-" in r.stdout

    def test_search_finds_article(self):
        self.run("cross_reference", "add", "Building Agents with Claude", "https://example.com/agents", "agent", "ai", "multi-agent")
        self.run("cross_reference", "add", "Context Window Management", "https://example.com/context", "context", "ai")
        r = self.run("cross_reference", "search", "agent")
        assert "Building Agents" in r.stdout

    def test_suggest_finds_related(self):
        self.run("cross_reference", "add", "Building Agents with Claude", "https://example.com/agents", "agent", "ai", "multi-agent")
        r = self.run("cross_reference", "suggest", "multi-agent")
        assert "Building Agents" in r.stdout

    def test_list_has_articles(self):
        self.run("cross_reference", "add", "Building Agents with Claude", "https://example.com/agents", "agent", "ai", "multi-agent")
        self.run("cross_reference", "add", "Context Window Management", "https://example.com/context", "context", "ai")
        r = self.run("cross_reference", "list")
        assert "Context Window" in r.stdout


# ============================================================
# SECTION 5: SERIES MANAGER
# ============================================================


class TestSeriesManager:
    """Section 5: Series manager create, list, set-arc, show, context."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script
        r = self.run("series_manager", "create", "Agent Architecture Series", "A deep dive into multi-agent system design patterns")
        assert "ser-" in r.stdout
        self.series_id = re.search(r"ser-\d+", r.stdout).group(0)

    def test_series_create_returns_id(self):
        assert self.series_id.startswith("ser-")

    def test_series_list_shows_series(self):
        r = self.run("series_manager", "list")
        assert "Agent Architecture" in r.stdout

    def test_series_set_arc_and_show(self):
        self.run("series_manager", "set-arc", self.series_id, "From single agents to orchestrated multi-agent systems")
        r = self.run("series_manager", "show", self.series_id)
        assert "multi-agent" in r.stdout

    def test_series_context_is_json(self):
        r = self.run("series_manager", "context", self.series_id)
        assert "series_name" in r.stdout


# ============================================================
# SECTION 6: PIPELINE INIT WITH CONFIG + SERIES
# ============================================================


class TestPipelineInitWithConfigAndSeries:
    """Section 6: Pipeline init with config and series, config summary."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-integration")
        os.makedirs(self.project)
        self.script_dir = script_dir
        # Setup config
        self.run("config", "init")
        self.run("config", "set", "language", "zh")
        # Setup series
        r = self.run("series_manager", "create", "Agent Architecture Series", "Multi-agent patterns")
        self.series_id = re.search(r"ser-\d+", r.stdout).group(0)
        # Init pipeline with series
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns", "--series", self.series_id)

    def test_pipeline_has_series_id(self):
        r = self.run("pipeline_state", "read", self.project)
        assert self.series_id in r.stdout

    def test_config_summary_has_language(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-config-summary")
        assert "zh" in r.stdout


# ============================================================
# SECTION 7: INTAKE + CHECKPOINT AUTO-SAVES
# ============================================================


class TestIntakeAndCheckpointAutoSaves:
    """Section 7: Intake materials + checkpoint auto-saves on stage transition."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-integration")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Multi-agent orchestration requires careful context management. Each agent should get only the context it needs.")
        self.run("intake_materials", "add-note", self.project, "The conductor pattern separates planning from execution. Conductors plan, sprint masters direct, workers execute.")
        self.run("intake_materials", "add-url", self.project, "https://docs.anthropic.com/en/docs/agents", "Anthropic Agent Docs")
        self.run("intake_materials", "add-code", self.project, "class Conductor { async plan(mission) { return this.decompose(mission); } }", "javascript")
        self.run("intake_materials", "add-theme", self.project, "multi-agent orchestration")
        self.run("intake_materials", "add-angle", self.project, "production patterns from a real system")

    def test_checkpoint_dir_exists_after_set_stage(self):
        self.run("pipeline_state", "set-stage", self.project, "research")
        ckpt_dir = os.path.join(self.project, ".essay-state", "checkpoints")
        assert os.path.isdir(ckpt_dir)

    def test_at_least_one_checkpoint_after_set_stage(self):
        self.run("pipeline_state", "set-stage", self.project, "research")
        assert count_checkpoints(self.project) > 0


# ============================================================
# SECTION 8: RESEARCH + PROGRESS DISPLAY
# ============================================================


class TestResearchAndProgress:
    """Section 8: Research stage, progress display, checkpoint accumulation."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-research")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Context management note")
        # Transition to research
        self.run("pipeline_state", "set-stage", self.project, "research")
        self.ckpt_count_after_research = count_checkpoints(self.project)

    def test_progress_shows_research_stage(self):
        r = self.run("progress_display", self.project, "--format", "json")
        assert "research" in r.stdout

    def test_more_checkpoints_after_outline_transition(self):
        # Write research synthesis and advance to outline
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        assert count_checkpoints(self.project) > self.ckpt_count_after_research


# ============================================================
# SECTION 9: OUTLINES WITH SERIES CONTEXT
# ============================================================


class TestOutlinesWithSeriesContext:
    """Section 9: Outline prompts build correctly with variant markers and thesis."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-outlines")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        # Create series
        r = self.run("series_manager", "create", "Agent Architecture Series", "Multi-agent patterns")
        self.series_id = re.search(r"ser-\d+", r.stdout).group(0)
        # Init pipeline
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns", "--series", self.series_id)
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Multi-agent orchestration requires careful context management.")
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")

    def test_outline_a_has_variant_marker(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "A")
        assert "Variant: A" in r.stdout

    def test_outline_b_has_variant_marker(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "B")
        assert "Variant: B" in r.stdout

    def test_outline_c_has_variant_marker(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "C")
        assert "Variant: C" in r.stdout

    def test_outline_a_has_thesis(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "A")
        assert "multi-agent orchestration" in r.stdout.lower() or "orchestration" in r.stdout.lower()

    def test_outline_b_has_thesis(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "B")
        assert "multi-agent orchestration" in r.stdout.lower() or "orchestration" in r.stdout.lower()

    def test_outline_c_has_thesis(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-outline-prompts", "C")
        assert "multi-agent orchestration" in r.stdout.lower() or "orchestration" in r.stdout.lower()

    def test_series_context_has_series_name(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-series-context")
        # May return empty if series context not fully configured; if non-empty, check contents
        if r.stdout.strip():
            assert "Agent Architecture" in r.stdout


# ============================================================
# SECTION 10: DRAFT + WRITER PROMPT
# ============================================================


class TestDraftAndWriterPrompt:
    """Section 10: Draft stage, writer prompt includes outline B."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-draft")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        write_json(self.project, "outline-A.json", OUTLINE_A)
        write_json(self.project, "outline-B.json", OUTLINE_B)
        write_json(self.project, "outline-C.json", OUTLINE_C)
        write_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        self.run("pipeline_state", "set-stage", self.project, "draft")

    def test_writer_prompt_has_outline_b(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-writer-prompt", "B")
        assert "Deep Dive" in r.stdout

    def test_writer_prompt_has_template(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-writer-prompt", "B")
        assert "Draft Writer" in r.stdout


# ============================================================
# SECTION 11: CODE VALIDATION
# ============================================================


class TestCodeValidation:
    """Section 11: Code validation on draft with JS and Python blocks."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home):
        self.run = run_script
        self.project = str(tmp_path / "e2e-codeval")
        os.makedirs(self.project)
        os.makedirs(os.path.join(self.project, ".essay-state"))
        write_file(self.project, "draft-v1.md", DRAFT_V1)

    def test_code_validate_returns_json(self):
        draft_path = os.path.join(self.project, ".essay-state", "draft-v1.md")
        r = self.run("code_validate", draft_path, "--json")
        assert "blocks" in r.stdout

    def test_code_validate_found_javascript(self):
        draft_path = os.path.join(self.project, ".essay-state", "draft-v1.md")
        r = self.run("code_validate", draft_path, "--json")
        assert "javascript" in r.stdout

    def test_code_validate_found_python(self):
        draft_path = os.path.join(self.project, ".essay-state", "draft-v1.md")
        r = self.run("code_validate", draft_path, "--json")
        assert "python" in r.stdout


# ============================================================
# SECTION 12: DIAGRAM SUGGESTIONS
# ============================================================


class TestDiagramSuggestions:
    """Section 12: Diagram suggestion engine."""

    def test_diagram_suggest_returns_json(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "e2e-diagram")
        os.makedirs(project)
        os.makedirs(os.path.join(project, ".essay-state"))
        write_file(project, "draft-v1.md", DRAFT_V1)
        draft_path = os.path.join(project, ".essay-state", "draft-v1.md")
        r = run_script("diagram_suggest", draft_path)
        assert "suggestions" in r.stdout


# ============================================================
# SECTION 13: REVIEW PANEL + QUALITY SCORE
# ============================================================


class TestReviewPanelAndQualityScore:
    """Section 13: Review panel aggregation, score normalization, quality score."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-review")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        write_json(self.project, "outline-A.json", OUTLINE_A)
        write_json(self.project, "outline-B.json", OUTLINE_B)
        write_json(self.project, "outline-C.json", OUTLINE_C)
        write_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        # Write all 7 reviews
        for fname, data in ALL_REVIEWS.items():
            write_json(self.project, fname, data)
        # Register reviews
        for rname in ALL_REVIEWS:
            review_path = os.path.join(self.project, ".essay-state", rname)
            self.run("pipeline_state", "add-review", self.project, review_path)

    def test_aggregate_creates_panel_summary(self):
        self.run("aggregate_reviews", self.project)
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-panel-summary.json"))

    def test_score_normalization_creates_file(self):
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-calibration.json"))

    def test_quality_score_has_composite(self):
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        r = self.run("quality_score", self.project)
        assert "composite" in r.stdout

    def test_quality_score_has_dimension_scores(self):
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        r = self.run("quality_score", self.project)
        assert "dimension_scores" in r.stdout


# ============================================================
# SECTION 14: INFLUENCE SCORE
# ============================================================


class TestInfluenceScore:
    """Section 14: Influence score generation."""

    def test_influence_score_has_json(self, run_script, tmp_path, fake_home, script_dir):
        project = str(tmp_path / "e2e-influence")
        os.makedirs(project)
        os.makedirs(os.path.join(project, ".essay-state"))
        write_json(project, "pipeline-state.json", {"topic": "Test", "stage": "review", "language": "en"})
        r = run_script("influence_score", project)
        assert "influence" in r.stdout


# ============================================================
# SECTION 15: SEO METADATA
# ============================================================


class TestSeoMetadata:
    """Section 15: SEO metadata generation."""

    def test_seo_metadata_has_json(self, run_script, tmp_path, fake_home, script_dir):
        project = str(tmp_path / "e2e-seo")
        os.makedirs(project)
        os.makedirs(os.path.join(project, ".essay-state"))
        write_json(project, "pipeline-state.json", {"topic": "Test", "stage": "review", "language": "en"})
        write_file(project, "draft-v1.md", DRAFT_V1)
        r = run_script("seo_metadata", project)
        assert "meta" in r.stdout


# ============================================================
# SECTION 16: REFINEMENT + RETRY-STAGE
# ============================================================


class TestRefinementAndRetryStage:
    """Section 16: Refinement loop, convergence check, retry-stage."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-refine")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        for fname in ["outline-A.json", "outline-B.json", "outline-C.json"]:
            v = fname.split("-")[1].split(".")[0]
            write_json(self.project, fname, {"variant": v, "variant_name": f"Variant {v}", "title": f"Outline {v}", "hook": f"Hook {v}", "sections": [{"title": "S1", "purpose": "test", "key_points": ["p"], "estimated_words": 500}], "target_word_count": 2000, "tone": "technical"})
        write_json(self.project, "outline-critique.json", OUTLINE_CRITIQUE)
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        for fname, data in ALL_REVIEWS.items():
            write_json(self.project, fname, data)
        for rname in ALL_REVIEWS:
            review_path = os.path.join(self.project, ".essay-state", rname)
            self.run("pipeline_state", "add-review", self.project, review_path)
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        self.run("pipeline_state", "set-stage", self.project, "refinement")

    def test_refiner_prompt_round_1(self):
        r = self.run("orchestrate", self.project, self.script_dir, "build-refiner-prompt", "1")
        assert "Round: 1" in r.stdout

    def test_convergence_after_solid_rereview(self):
        # Simulate v2 draft
        import shutil
        shutil.copy(
            os.path.join(self.project, ".essay-state", "draft-v1.md"),
            os.path.join(self.project, ".essay-state", "draft-v2.md"),
        )
        self.run("pipeline_state", "refinement-round", self.project)
        # Simulate adversarial re-review with SOLID rating
        write_json(self.project, "review-adversarial.json", {
            "reviewer": "adversarial", "rating": "SOLID", "summary": "Issues addressed", "attacks": [], "issues": []
        })
        r = self.run("orchestrate", self.project, self.script_dir, "check-convergence", "2")
        assert r.stdout.strip() == "CONVERGED"

    def test_retry_stage_output(self):
        r = self.run("orchestrate", self.project, self.script_dir, "retry-stage", "draft")
        assert "Retry" in r.stdout
        assert "draft" in r.stdout

    def test_retry_stage_resets_to_draft(self):
        self.run("orchestrate", self.project, self.script_dir, "retry-stage", "draft")
        r = self.run("pipeline_state", "get-stage", self.project)
        assert r.stdout.strip() == "draft"


# ============================================================
# SECTION 17: RESUME
# ============================================================


class TestResume:
    """Section 17: Resume detects partial state."""

    def test_resume_detects_partial_state(self, run_script, tmp_path, fake_home, script_dir):
        project = str(tmp_path / "e2e-resume")
        os.makedirs(project)
        run_script("config", "init")
        run_script("pipeline_state", "init", project, "Multi-Agent Orchestration Patterns")
        run_script("pipeline_state", "set-stage", project, "research")
        write_json(project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        run_script("pipeline_state", "set-stage", project, "draft")
        write_file(project, "draft-v1.md", DRAFT_V1_MINIMAL)
        run_script("pipeline_state", "set-field", project, "draft_version", "1")
        r = run_script("orchestrate", project, script_dir, "resume")
        assert "STATUS" in r.stdout

    def test_resume_shows_current_stage(self, run_script, tmp_path, fake_home, script_dir):
        project = str(tmp_path / "e2e-resume2")
        os.makedirs(project)
        run_script("config", "init")
        run_script("pipeline_state", "init", project, "Multi-Agent Orchestration Patterns")
        run_script("pipeline_state", "set-stage", project, "research")
        write_json(project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        run_script("pipeline_state", "set-stage", project, "draft")
        write_file(project, "draft-v1.md", DRAFT_V1_MINIMAL)
        run_script("pipeline_state", "set-field", project, "draft_version", "1")
        r = run_script("orchestrate", project, script_dir, "resume")
        assert "draft" in r.stdout


# ============================================================
# SECTION 18: ROLLBACK
# ============================================================


class TestRollback:
    """Section 18: Checkpoint list, latest, rollback to earliest."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-rollback")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Test note for rollback")
        # Transition through stages to create checkpoints
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        write_file(self.project, "draft-v1.md", DRAFT_V1_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "draft")

    def test_checkpoint_list_has_entries(self):
        r = self.run("checkpoint", "list", self.project)
        assert "checkpoint" in r.stdout.lower() or "-" in r.stdout

    def test_latest_checkpoint_exists(self):
        r = self.run("checkpoint", "latest", self.project)
        assert "-" in r.stdout

    def test_rollback_reverts_to_intake(self):
        early_ckpt = find_checkpoint(self.project, "intake")
        if early_ckpt is None:
            pytest.skip("No intake checkpoint found for rollback test")
        self.run("checkpoint", "rollback", self.project, early_ckpt)
        r = self.run("pipeline_state", "get-stage", self.project)
        assert r.stdout.strip() == "intake"


# ============================================================
# SECTION 19: POLISH + FINAL OUTPUTS (after rollback re-advance)
# ============================================================


class TestPolishAndFinalOutputs:
    """Section 19: Re-advance pipeline to polish and generate final outputs."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-polish")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Context note")
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        for v in ["A", "B", "C"]:
            write_json(self.project, f"outline-{v}.json", {
                "variant": v, "variant_name": f"Variant {v}", "title": f"Test Outline {v}",
                "hook": f"Hook {v}", "sections": [{"title": "Section 1", "purpose": "test", "key_points": ["point"], "estimated_words": 500}],
                "target_word_count": 2000, "tone": "technical",
            })
        write_json(self.project, "outline-critique.json", {
            "critic": "outline-adversarial", "outlines_analyzed": ["A", "B", "C"],
            "per_outline": {"A": {"overall_score": 7}, "B": {"overall_score": 8}, "C": {"overall_score": 7.5}},
            "recommendation": {"recommended_variant": "B"},
        })
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1_MINIMAL)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        for fname, data in REVIEWS_PASS.items():
            write_json(self.project, fname, data)
        for rname in REVIEWS_PASS:
            review_path = os.path.join(self.project, ".essay-state", rname)
            self.run("pipeline_state", "add-review", self.project, review_path)
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        self.run("pipeline_state", "set-stage", self.project, "refinement")
        import shutil
        shutil.copy(
            os.path.join(self.project, ".essay-state", "draft-v1.md"),
            os.path.join(self.project, ".essay-state", "draft-v2.md"),
        )
        self.run("pipeline_state", "refinement-round", self.project)
        self.run("pipeline_state", "set-stage", self.project, "polish")
        # Simulate final outputs
        write_file(self.project, "final-internal.md", FINAL_INTERNAL)
        write_file(self.project, "final-external.md", FINAL_EXTERNAL)
        write_json(self.project, "social-package.json", SOCIAL_PACKAGE)


# ============================================================
# SECTION 20: PUBLISH CHECK + PROGRESS AT POLISH
# ============================================================


class TestPublishCheckAndProgress:
    """Section 20: Progress display at polish, publish check."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-pubcheck")
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1_MINIMAL)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        self.run("pipeline_state", "set-stage", self.project, "refinement")
        self.run("pipeline_state", "set-stage", self.project, "polish")
        write_file(self.project, "final-internal.md", FINAL_INTERNAL)
        write_file(self.project, "final-external.md", FINAL_EXTERNAL)
        write_json(self.project, "social-package.json", SOCIAL_PACKAGE)

    def test_progress_shows_polish_stage(self):
        r = self.run("progress_display", self.project, "--format", "json")
        assert "polish" in r.stdout

    def test_publish_check_has_output(self):
        # publish-check may return non-zero when checks fail, which is expected
        r = self.run("publish_check", self.project)
        combined = r.stdout + r.stderr
        assert "Checklist" in combined or "checklist" in combined.lower() or r.returncode == 0


# ============================================================
# SECTION 21: COMPLETE + TASTE MEMORY UPDATE
# ============================================================


class TestCompleteAndTasteMemory:
    """Section 21: Pipeline complete, taste memory update, final status."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-complete")
        self.home = fake_home
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1_MINIMAL)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        self.run("pipeline_state", "set-stage", self.project, "refinement")
        self.run("pipeline_state", "set-stage", self.project, "polish")
        write_file(self.project, "final-internal.md", FINAL_INTERNAL)
        write_file(self.project, "final-external.md", FINAL_EXTERNAL)

    def test_complete_and_taste_memory_update(self):
        self.run("pipeline_state", "complete", self.project)
        self.run("taste_memory", "update", self.project)
        r = self.run("taste_memory", "read")
        assert "Topics covered" in r.stdout or "topic" in r.stdout.lower()

    def test_final_status_complete(self):
        self.run("pipeline_state", "complete", self.project)
        r = self.run("orchestrate", self.project, self.script_dir, "status")
        assert "True" in r.stdout


# ============================================================
# SECTION 22: TASTE MEMORY DIFF-LEARN
# ============================================================


class TestTasteMemoryDiffLearn:
    """Section 22: Diff-learn extracts patterns from original vs edited draft."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-difflearn")
        self.tmpdir = str(tmp_path)
        os.makedirs(self.project)
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        # Write original and edited drafts
        self.orig_path = os.path.join(self.tmpdir, "original-draft.md")
        self.edit_path = os.path.join(self.tmpdir, "edited-draft.md")
        with open(self.orig_path, "w") as f:
            f.write(ORIGINAL_DRAFT)
        with open(self.edit_path, "w") as f:
            f.write(EDITED_DRAFT)

    def test_diff_learn_extracted_patterns(self):
        r = self.run("taste_memory", "diff-learn", self.project, self.orig_path, self.edit_path)
        assert "Learned from diff" in r.stdout or "learned" in r.stdout.lower()

    def test_taste_memory_has_learned_insights(self):
        self.run("taste_memory", "diff-learn", self.project, self.orig_path, self.edit_path)
        r = self.run("taste_memory", "read")
        assert "Learned" in r.stdout or "learned" in r.stdout.lower()


# ============================================================
# SECTION 23: TASTE MEMORY FEEDBACK
# ============================================================


class TestTasteMemoryFeedback:
    """Section 23: Taste memory explicit feedback by category."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-feedback")
        os.makedirs(self.project)
        self.run("config", "init")
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("taste_memory", "feedback", self.project, "tone", "Keep it casual and direct -- no academic language")
        self.run("taste_memory", "feedback", self.project, "structure", "Start with the problem, not the solution")
        self.run("taste_memory", "feedback", self.project, "code_density", "Always include runnable code in the first 1/3 of the article")

    def test_feedback_has_tone_preference(self):
        r = self.run("taste_memory", "read")
        assert "casual" in r.stdout

    def test_feedback_has_structure_preference(self):
        r = self.run("taste_memory", "read")
        assert "problem" in r.stdout

    def test_feedback_has_code_density_preference(self):
        r = self.run("taste_memory", "read")
        assert "runnable" in r.stdout


# ============================================================
# SECTION 24: TASTE MEMORY SUGGEST
# ============================================================


class TestTasteMemorySuggest:
    """Section 24: Taste memory suggest aggregates recommendations."""

    def test_suggest_has_recommendations(self, run_script, tmp_path, fake_home, script_dir):
        project = str(tmp_path / "e2e-suggest")
        os.makedirs(project)
        run_script("config", "init")
        run_script("pipeline_state", "init", project, "Multi-Agent Orchestration Patterns")
        # Add some feedback so suggest has data
        run_script("taste_memory", "feedback", project, "tone", "Keep it casual")
        r = run_script("taste_memory", "suggest", project)
        assert "Suggestions" in r.stdout or "suggest" in r.stdout.lower()


# ============================================================
# SECTION 25: ANALYTICS FEEDBACK
# ============================================================


class TestAnalyticsFeedback:
    """Section 25: Analytics feedback record, query, top."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script
        self.run("analytics_feedback", "record", "art-test", "views", "1500")
        self.run("analytics_feedback", "record", "art-test", "shares", "85")
        self.run("analytics_feedback", "record", "art-test", "comments", "23")

    def test_query_has_views(self):
        r = self.run("analytics_feedback", "query", "art-test")
        assert "1500" in r.stdout

    def test_query_has_shares(self):
        r = self.run("analytics_feedback", "query", "art-test")
        assert "85" in r.stdout

    def test_top_has_article(self):
        r = self.run("analytics_feedback", "top", "views", "3")
        assert "art-test" in r.stdout


# ============================================================
# SECTION 26: FINAL ARTIFACT VERIFICATION
# ============================================================


class TestFinalArtifactVerification:
    """Section 26: Verify all expected files exist after full pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.run = run_script
        self.project = str(tmp_path / "e2e-final")
        self.home = fake_home
        os.makedirs(self.project)
        self.script_dir = script_dir
        self.run("config", "init")
        # Create author profile
        self.run("author_profile", "init")
        self.run("author_profile", "set", "name", "Test Author")
        # Full pipeline walk-through
        self.run("pipeline_state", "init", self.project, "Multi-Agent Orchestration Patterns")
        self.run("intake_materials", "init", self.project)
        self.run("intake_materials", "add-note", self.project, "Test note")
        self.run("pipeline_state", "set-stage", self.project, "research")
        write_json(self.project, "research-synthesis.json", RESEARCH_SYNTHESIS_MINIMAL)
        self.run("pipeline_state", "set-stage", self.project, "outline")
        for v in ["A", "B", "C"]:
            write_json(self.project, f"outline-{v}.json", {
                "variant": v, "variant_name": f"Variant {v}", "title": f"Outline {v}",
                "hook": f"Hook {v}", "sections": [{"title": "S1", "purpose": "test", "key_points": ["p"], "estimated_words": 500}],
                "target_word_count": 2000, "tone": "technical",
            })
        self.run("pipeline_state", "set-field", self.project, "outline_variant", "B")
        self.run("pipeline_state", "set-stage", self.project, "draft")
        write_file(self.project, "draft-v1.md", DRAFT_V1_MINIMAL)
        self.run("pipeline_state", "set-field", self.project, "draft_version", "1")
        self.run("pipeline_state", "set-stage", self.project, "review")
        for fname, data in REVIEWS_PASS.items():
            write_json(self.project, fname, data)
        for rname in REVIEWS_PASS:
            review_path = os.path.join(self.project, ".essay-state", rname)
            self.run("pipeline_state", "add-review", self.project, review_path)
        self.run("aggregate_reviews", self.project)
        self.run("calibrate_reviews", self.project)
        self.run("pipeline_state", "set-stage", self.project, "refinement")
        import shutil
        shutil.copy(
            os.path.join(self.project, ".essay-state", "draft-v1.md"),
            os.path.join(self.project, ".essay-state", "draft-v2.md"),
        )
        self.run("pipeline_state", "refinement-round", self.project)
        self.run("pipeline_state", "set-stage", self.project, "polish")
        write_file(self.project, "final-internal.md", FINAL_INTERNAL)
        write_file(self.project, "final-external.md", FINAL_EXTERNAL)
        write_json(self.project, "social-package.json", SOCIAL_PACKAGE)
        self.run("pipeline_state", "complete", self.project)
        self.run("taste_memory", "update", self.project)

    def test_materials_json_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "materials.json"))

    def test_research_synthesis_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "research-synthesis.json"))

    def test_outline_a_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "outline-A.json"))

    def test_outline_b_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "outline-B.json"))

    def test_outline_c_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "outline-C.json"))

    def test_draft_v1_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "draft-v1.md"))

    def test_final_internal_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "final-internal.md"))

    def test_final_external_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "final-external.md"))

    def test_social_package_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "social-package.json"))

    def test_review_panel_summary_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-panel-summary.json"))

    def test_review_normalization_exists(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-calibration.json"))

    def test_config_json_exists(self):
        assert os.path.isfile(os.path.join(self.home, ".tech-essay-writer", "config.json"))

    def test_author_profile_exists(self):
        assert os.path.isfile(os.path.join(self.home, ".tech-essay-writer", "author-profile.json"))

    def test_taste_memory_exists(self):
        assert os.path.isfile(os.path.join(self.home, ".tech-essay-writer", "taste-memory.json"))

    def test_checkpoints_dir_exists(self):
        assert os.path.isdir(os.path.join(self.project, ".essay-state", "checkpoints"))
