"""Tests for metrics_dashboard.py."""

import json
import os

import pytest


# ============================================================
# Helpers
# ============================================================


def setup_project(tmp_path, name):
    """Create a temp project dir with .essay-state/ and return its path."""
    proj = tmp_path / name
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".essay-state").mkdir(exist_ok=True)
    return str(proj)


def write_json(path, data):
    """Write a JSON file at the given path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def write_file(path, content):
    """Write a text file at the given path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


# ============================================================
# Shared fixtures
# ============================================================


PIPELINE_STATE = {
    "topic": "Building Reliable Microservices",
    "stage": "review",
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-06T12:00:00Z",
    "language": "en",
    "materials_count": 5,
    "outline_variant": "deep-dive",
    "draft_version": 2,
    "refinement_round": 1,
    "max_refinement_rounds": 3,
    "reviews": {
        "review-technical": {"file": "review-technical.json", "rating": "PASS", "issues_count": 1},
        "review-editor": {"file": "review-editor.json", "rating": "NEEDS_EDITING", "issues_count": 3},
    },
    "review_panel_complete": False,
    "completed": False,
    "artifacts": [],
}

REVIEW_TECHNICAL = {
    "rating": "PASS",
    "summary": "Code examples are accurate and well-tested.",
    "issues": [
        {"severity": "minor", "issue": "Missing error handling in example 3"}
    ],
}

REVIEW_EDITOR = {
    "rating": "NEEDS_EDITING",
    "summary": "Good structure but needs tightening.",
    "hook_score": 7,
    "clarity_score": 8,
    "flow_score": 6,
    "voice_score": 7,
    "engagement_score": 7,
    "economy_score": 5,
    "issues": [
        {"severity": "major", "issue": "Introduction too long", "suggestion": "Cut to 2 paragraphs"},
        {"severity": "minor", "issue": "Passive voice in section 3"},
        {"severity": "minor", "issue": "Inconsistent terminology"},
    ],
}

REVIEW_ADVERSARIAL = {
    "rating": "SOLID",
    "summary": "Arguments hold up well.",
    "issues": [],
    "attacks": [
        {"attack": "Cherry-picked benchmarks", "severity": "major", "defense": "Add methodology section"}
    ],
}

REVIEW_AUDIENCE = {
    "rating": "MEH",
    "reader_a": {"rating": "WOULD_SHARE", "feedback": "Great practical examples"},
    "reader_b": {"rating": "MEH", "feedback": "Needs more context for juniors"},
    "issues": [],
}

REVIEW_SEO = {
    "rating": "OPTIMIZED",
    "summary": "Good keyword coverage.",
    "issues": [
        {"severity": "minor", "issue": "Meta description could be shorter"}
    ],
}

QUALITY_SCORE = {
    "composite_score": 7.2,
    "readiness": "CLOSE",
    "dimension_scores": {"technical": 9.0, "editor": 6.7, "adversarial": 8.5, "audience": 7.0, "seo": 8.9},
    "reviews_available": 5,
    "reviews_expected": 7,
}

REVIEW_PANEL_SUMMARY = {
    "reviews_count": 5,
    "consensus": "NEEDS_MINOR_REVISION",
    "critical_issues": [],
    "all_issues": [
        {"severity": "major", "issue": "Introduction too long", "source_reviewer": "review-editor"},
        {"severity": "major", "issue": "Cherry-picked benchmarks", "source_reviewer": "review-adversarial"},
        {"severity": "minor", "issue": "Passive voice in section 3", "source_reviewer": "review-editor"},
    ],
}

READABILITY_DRAFT = {
    "file": "draft.md",
    "metrics": {
        "flesch_kincaid_grade": 11.5,
        "flesch_reading_ease": 45.2,
        "avg_sentence_length": 22.3,
        "avg_syllables_per_word": 1.8,
        "total_words": 2500,
        "total_sentences": 112,
        "total_paragraphs": 28,
        "total_syllables": 4500,
        "grade_interpretation": "college_prep",
    },
}

TASTE_MEMORY = {
    "preferred_variant": "deep-dive",
    "tone_preferences": ["technical", "direct"],
    "structural_preferences": {"intro_length": "short", "code_first": "true"},
    "topics_written": [
        {"topic": "Intro to Kubernetes", "date": "2026-01-15T00:00:00Z", "variant": "tutorial", "refinement_rounds": 3},
        {"topic": "Docker Best Practices", "date": "2026-02-01T00:00:00Z", "variant": "deep-dive", "refinement_rounds": 2},
        {"topic": "CI/CD Pipeline Design", "date": "2026-02-20T00:00:00Z", "variant": "deep-dive", "refinement_rounds": 2},
        {"topic": "Terraform at Scale", "date": "2026-03-10T00:00:00Z", "variant": "tutorial", "refinement_rounds": 1},
        {"topic": "Observability Patterns", "date": "2026-03-25T00:00:00Z", "variant": "narrative", "refinement_rounds": 1},
    ],
    "articles_count": 5,
    "learned_patterns": [
        {"tone_shift": "more_formal", "length_change": "condensed", "code_density_change": "more_code", "insights": ["Prefers concise over verbose"]},
        {"tone_shift": "neutral", "length_change": "condensed", "code_density_change": "unchanged", "insights": ["Prefers shorter paragraphs"]},
        {"tone_shift": "more_formal", "length_change": "similar", "code_density_change": "more_code", "insights": ["Prefers concise over verbose"]},
    ],
    "updated_at": "2026-03-25T00:00:00Z",
}

EXPERTISE_GRAPH = {
    "topics": {
        "Kubernetes": {"article_count": 3, "authority_score": 7.0, "tags": ["devops", "containers"], "first_article": "2025-06-01", "last_article": "2026-01-15"},
        "Docker": {"article_count": 2, "authority_score": 5.0, "tags": ["devops", "containers"], "first_article": "2025-09-01", "last_article": "2026-02-01"},
        "CI/CD": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "automation"], "first_article": "2026-02-20", "last_article": "2026-02-20"},
        "Terraform": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "iac"], "first_article": "2026-03-10", "last_article": "2026-03-10"},
        "Observability": {"article_count": 1, "authority_score": 3.0, "tags": ["devops", "monitoring"], "first_article": "2026-03-25", "last_article": "2026-03-25"},
    },
    "tag_index": {
        "devops": ["Kubernetes", "Docker", "CI/CD", "Terraform", "Observability"],
        "containers": ["Kubernetes", "Docker"],
        "automation": ["CI/CD"],
        "iac": ["Terraform"],
        "monitoring": ["Observability"],
    },
    "updated_at": "2026-03-25T00:00:00Z",
}

AUTHOR_PROFILE = {
    "name": "Jackson",
    "role": "Senior Engineer",
    "company": "TechCorp",
    "expertise_areas": [
        {"topic": "Kubernetes", "level": "expert"},
        {"topic": "Go", "level": "intermediate"},
    ],
    "updated_at": "2026-01-01T00:00:00Z",
}

ANALYTICS_DATA = {
    "articles": {
        "intro-kubernetes": {
            "metrics": {"views": 5200, "shares": 340, "comments": 45, "likes": 890, "bookmarks": 120},
            "first_recorded": "2026-01-20T00:00:00Z",
            "last_updated": "2026-02-15T00:00:00Z",
        },
        "docker-best-practices": {
            "metrics": {"views": 3100, "shares": 210, "comments": 28, "likes": 450, "bookmarks": 85},
            "first_recorded": "2026-02-05T00:00:00Z",
            "last_updated": "2026-03-01T00:00:00Z",
        },
        "cicd-pipeline-design": {
            "metrics": {"views": 1800, "shares": 95, "comments": 12, "likes": 210, "bookmarks": 40},
            "first_recorded": "2026-02-25T00:00:00Z",
            "last_updated": "2026-03-15T00:00:00Z",
        },
        "terraform-at-scale": {
            "metrics": {"views": 4500, "shares": 280, "comments": 33, "likes": 620, "bookmarks": 95},
            "first_recorded": "2026-03-15T00:00:00Z",
            "last_updated": "2026-04-01T00:00:00Z",
        },
    },
    "updated_at": "2026-04-01T00:00:00Z",
}

DRAFT_MD = """\
# Building Reliable Microservices

## Introduction

Microservices architecture has become the dominant approach for building
scalable systems. In this article we explore patterns that make services
resilient to failure. We cover circuit breakers, retries, and bulkheads.

## Circuit Breakers

The circuit breaker pattern prevents cascading failures across services.
When a downstream service fails, the circuit breaker trips and returns
a fallback response instead of propagating the error.

```go
func NewCircuitBreaker(threshold int, timeout time.Duration) *CircuitBreaker {
    return &CircuitBreaker{
        threshold: threshold,
        timeout:   timeout,
        state:     StateClosed,
    }
}

func (cb *CircuitBreaker) Call(fn func() error) error {
    if cb.state == StateOpen {
        if time.Since(cb.lastFailure) > cb.timeout {
            cb.state = StateHalfOpen
        } else {
            return ErrCircuitOpen
        }
    }
    err := fn()
    if err != nil {
        cb.failures++
        if cb.failures >= cb.threshold {
            cb.state = StateOpen
            cb.lastFailure = time.Now()
        }
        return err
    }
    cb.failures = 0
    cb.state = StateClosed
    return nil
}
```

This implementation tracks failure counts and transitions between closed,
open, and half-open states. The timeout allows periodic recovery attempts.

## Retry with Backoff

Transient failures are common in distributed systems. An exponential backoff
strategy prevents overwhelming a struggling service with retry storms.

```go
func RetryWithBackoff(fn func() error, maxRetries int) error {
    for i := 0; i < maxRetries; i++ {
        err := fn()
        if err == nil {
            return nil
        }
        wait := time.Duration(math.Pow(2, float64(i))) * time.Second
        time.Sleep(wait)
    }
    return fmt.Errorf("max retries exceeded")
}
```

## Bulkhead Pattern

Bulkheads isolate failures to prevent one slow service from consuming all
available resources. Each service gets a dedicated thread pool or connection
pool. When one pool is exhausted, other services continue operating normally.

## Conclusion

Building reliable microservices requires combining multiple resilience
patterns. Circuit breakers prevent cascading failures, retries handle
transient issues, and bulkheads provide fault isolation. Together these
patterns create systems that degrade gracefully under stress.
"""


@pytest.fixture
def full_project(tmp_path, fake_home):
    """Set up a fully populated project with all state files, global data, and draft."""
    # Project with pipeline state
    proj = str(tmp_path / "test-project")
    state = os.path.join(proj, ".essay-state")
    os.makedirs(state, exist_ok=True)

    write_json(os.path.join(state, "pipeline-state.json"), PIPELINE_STATE)
    write_json(os.path.join(state, "review-technical.json"), REVIEW_TECHNICAL)
    write_json(os.path.join(state, "review-editor.json"), REVIEW_EDITOR)
    write_json(os.path.join(state, "review-adversarial.json"), REVIEW_ADVERSARIAL)
    write_json(os.path.join(state, "review-audience.json"), REVIEW_AUDIENCE)
    write_json(os.path.join(state, "review-seo.json"), REVIEW_SEO)
    write_json(os.path.join(state, "quality-score.json"), QUALITY_SCORE)
    write_json(os.path.join(state, "review-panel-summary.json"), REVIEW_PANEL_SUMMARY)
    write_json(os.path.join(state, "readability-draft.json"), READABILITY_DRAFT)

    # Checkpoints for stage timing
    ckpt_dir = os.path.join(state, "checkpoints")
    for label, stage, ts in [
        ("intake-20260401T100500", "intake", "2026-04-01T10:05:00Z"),
        ("research-20260401T120000", "research", "2026-04-01T12:00:00Z"),
        ("outline-20260402T090000", "outline", "2026-04-02T09:00:00Z"),
        ("draft-20260403T140000", "draft", "2026-04-03T14:00:00Z"),
    ]:
        ckpt_path = os.path.join(ckpt_dir, label)
        os.makedirs(ckpt_path, exist_ok=True)
        write_json(os.path.join(ckpt_path, "pipeline-state.json"), {"stage": stage, "updated_at": ts})

    # Draft markdown file
    write_file(os.path.join(proj, "draft.md"), DRAFT_MD)

    # Global data in fake home
    global_dir = os.path.join(fake_home, ".tech-essay-writer")
    os.makedirs(global_dir, exist_ok=True)
    write_json(os.path.join(global_dir, "taste-memory.json"), TASTE_MEMORY)
    write_json(os.path.join(global_dir, "expertise-graph.json"), EXPERTISE_GRAPH)
    write_json(os.path.join(global_dir, "author-profile.json"), AUTHOR_PROFILE)
    write_json(os.path.join(global_dir, "analytics.json"), ANALYTICS_DATA)

    return proj


# ============================================================
# Full dashboard output tests (T1-T29)
# ============================================================


class TestDashboardBasic:
    """T1-T6: Dashboard runs and shows pipeline health."""

    def test_exits_zero(self, run_script, full_project):
        """T1: Dashboard runs without errors."""
        r = run_script("metrics_dashboard", full_project)
        assert r.returncode == 0

    def test_header_shows_project_path(self, run_script, full_project):
        """T2: Shows header with project path."""
        r = run_script("metrics_dashboard", full_project)
        assert full_project in r.stdout

    def test_pipeline_health_section(self, run_script, full_project):
        """T3: Shows Pipeline Health section."""
        r = run_script("metrics_dashboard", full_project)
        assert "PIPELINE HEALTH" in r.stdout

    def test_shows_current_stage(self, run_script, full_project):
        """T4: Shows current stage REVIEW."""
        r = run_script("metrics_dashboard", full_project)
        assert "REVIEW" in r.stdout

    def test_shows_topic(self, run_script, full_project):
        """T5: Shows topic."""
        r = run_script("metrics_dashboard", full_project)
        assert "Building Reliable Microservices" in r.stdout

    def test_shows_refinement_round(self, run_script, full_project):
        """T6: Shows refinement round."""
        r = run_script("metrics_dashboard", full_project)
        assert "1/3" in r.stdout


class TestDashboardQualityTrends:
    """T7-T9: Quality trends section."""

    def test_quality_trends_section(self, run_script, full_project):
        """T7: Shows Quality Trends section."""
        r = run_script("metrics_dashboard", full_project)
        assert "QUALITY TRENDS" in r.stdout

    def test_shows_articles_count(self, run_script, full_project):
        """T8: Shows articles in taste memory."""
        r = run_script("metrics_dashboard", full_project)
        assert "Articles in taste memory: 5" in r.stdout

    def test_shows_trend_direction(self, run_script, full_project):
        """T9: Shows refinement rounds trend."""
        r = run_script("metrics_dashboard", full_project)
        assert "IMPROVING" in r.stdout


class TestDashboardReviewPanel:
    """T10-T14: Review panel stats section."""

    def test_review_panel_section(self, run_script, full_project):
        """T10: Shows Review Panel Stats section."""
        r = run_script("metrics_dashboard", full_project)
        assert "REVIEW PANEL STATS" in r.stdout

    def test_shows_technical_reviewer(self, run_script, full_project):
        """T11: Shows reviewer names."""
        r = run_script("metrics_dashboard", full_project)
        assert "technical" in r.stdout

    def test_shows_average_score(self, run_script, full_project):
        """T12: Shows average score."""
        r = run_script("metrics_dashboard", full_project)
        assert "Average score" in r.stdout

    def test_shows_reviewer_agreement(self, run_script, full_project):
        """T13: Shows reviewer agreement."""
        r = run_script("metrics_dashboard", full_project)
        assert "Reviewer agreement" in r.stdout

    def test_shows_composite_quality(self, run_script, full_project):
        """T14: Shows composite quality."""
        r = run_script("metrics_dashboard", full_project)
        assert "7.2/10" in r.stdout


class TestDashboardAuthorGrowth:
    """T15-T18: Author growth section."""

    def test_author_growth_section(self, run_script, full_project):
        """T15: Shows Author Growth section."""
        r = run_script("metrics_dashboard", full_project)
        assert "AUTHOR GROWTH" in r.stdout

    def test_shows_kubernetes_topic(self, run_script, full_project):
        """T16: Shows expertise topics."""
        r = run_script("metrics_dashboard", full_project)
        assert "Kubernetes" in r.stdout

    def test_shows_total_topics(self, run_script, full_project):
        """T17: Shows total topics count."""
        r = run_script("metrics_dashboard", full_project)
        assert "Total topics" in r.stdout

    def test_shows_authority_distribution(self, run_script, full_project):
        """T18: Shows authority distribution."""
        r = run_script("metrics_dashboard", full_project)
        assert "Authority Distribution" in r.stdout


class TestDashboardPlatformPerformance:
    """T19-T22: Platform performance section."""

    def test_platform_performance_section(self, run_script, full_project):
        """T19: Shows Platform Performance section."""
        r = run_script("metrics_dashboard", full_project)
        assert "PLATFORM PERFORMANCE" in r.stdout

    def test_shows_views_metric(self, run_script, full_project):
        """T20: Shows aggregate views."""
        r = run_script("metrics_dashboard", full_project)
        assert "Views" in r.stdout

    def test_shows_articles_tracked(self, run_script, full_project):
        """T21: Shows articles tracked count."""
        r = run_script("metrics_dashboard", full_project)
        assert "Articles tracked: 4" in r.stdout

    def test_shows_engagement_rate(self, run_script, full_project):
        """T22: Shows engagement rate."""
        r = run_script("metrics_dashboard", full_project)
        assert "Engagement rate" in r.stdout


class TestDashboardWritingStats:
    """T23-T27: Writing stats section."""

    def test_writing_stats_section(self, run_script, full_project):
        """T23: Shows Writing Stats section."""
        r = run_script("metrics_dashboard", full_project)
        assert "WRITING STATS" in r.stdout

    def test_shows_word_count(self, run_script, full_project):
        """T24: Shows word count stats."""
        r = run_script("metrics_dashboard", full_project)
        assert "Word Count" in r.stdout

    def test_shows_code_density(self, run_script, full_project):
        """T25: Shows code density."""
        r = run_script("metrics_dashboard", full_project)
        assert "Code Density" in r.stdout

    def test_shows_readability(self, run_script, full_project):
        """T26: Shows readability data."""
        r = run_script("metrics_dashboard", full_project)
        assert "Readability Scores" in r.stdout

    def test_shows_fk_grade(self, run_script, full_project):
        """T27: Shows Flesch-Kincaid grade."""
        r = run_script("metrics_dashboard", full_project)
        assert "Flesch-Kincaid grade" in r.stdout


class TestDashboardFormatting:
    """T28-T29: Output formatting."""

    def test_line_width(self, run_script, full_project):
        """T28: Output is terminal-friendly width (<= 100 chars).

        Lines containing the project path are excluded since pytest temp paths
        can be longer than the short paths used in the bash test suite.
        """
        r = run_script("metrics_dashboard", full_project)
        too_wide = sum(
            1
            for line in r.stdout.splitlines()
            if len(line) > 100 and full_project not in line
        )
        assert too_wide == 0, f"{too_wide} lines exceed 100 chars"

    def test_footer_timestamp(self, run_script, full_project):
        """T29: Shows footer with timestamp."""
        r = run_script("metrics_dashboard", full_project)
        assert "Dashboard generated" in r.stdout


# ============================================================
# Edge case: empty project with no state (T30-T32)
# ============================================================


class TestDashboardEmptyProject:
    """T30-T32: Empty project with no state."""

    def test_empty_project_exits_zero(self, run_script, tmp_path, fake_home):
        """T30: Empty project does not crash."""
        proj = str(tmp_path / "empty-project")
        os.makedirs(proj, exist_ok=True)
        r = run_script("metrics_dashboard", proj)
        assert r.returncode == 0

    def test_empty_project_shows_not_initialized(self, run_script, tmp_path, fake_home):
        """T31: Empty project shows not initialized."""
        proj = str(tmp_path / "empty-project")
        os.makedirs(proj, exist_ok=True)
        r = run_script("metrics_dashboard", proj)
        assert "not initialized" in r.stdout

    def test_empty_project_shows_all_sections(self, run_script, tmp_path, fake_home):
        """T32: Empty project shows all sections."""
        proj = str(tmp_path / "empty-project")
        os.makedirs(proj, exist_ok=True)
        r = run_script("metrics_dashboard", proj)
        assert "WRITING STATS" in r.stdout


# ============================================================
# Edge case: project with state but no reviews (T33-T34)
# ============================================================


class TestDashboardNoReviews:
    """T33-T34: Project with state but no reviews."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = str(tmp_path / "noreview-project")
        state = os.path.join(self.proj, ".essay-state")
        os.makedirs(state, exist_ok=True)
        write_json(os.path.join(state, "pipeline-state.json"), {
            "topic": "Testing Article",
            "stage": "draft",
            "created_at": "2026-04-05T10:00:00Z",
            "updated_at": "2026-04-05T14:00:00Z",
            "language": "en",
            "refinement_round": 0,
            "max_refinement_rounds": 3,
            "reviews": {},
            "completed": False,
        })

    def test_no_reviews_shows_message(self, run_script):
        """T33: No reviews shows appropriate message."""
        r = run_script("metrics_dashboard", self.proj)
        assert "No review data" in r.stdout

    def test_draft_stage_displayed(self, run_script):
        """T34: Draft stage displayed."""
        r = run_script("metrics_dashboard", self.proj)
        assert "DRAFT" in r.stdout


# ============================================================
# Edge case: completed project (T35)
# ============================================================


class TestDashboardCompletedProject:
    """T35: Completed project shows COMPLETE."""

    def test_shows_complete(self, run_script, tmp_path, fake_home):
        """T35: Completed project shows COMPLETE."""
        proj = str(tmp_path / "complete-project")
        state = os.path.join(proj, ".essay-state")
        os.makedirs(state, exist_ok=True)
        write_json(os.path.join(state, "pipeline-state.json"), {
            "topic": "Completed Article",
            "stage": "complete",
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-04T16:00:00Z",
            "language": "en",
            "refinement_round": 2,
            "max_refinement_rounds": 3,
            "reviews": {},
            "completed": True,
            "completed_at": "2026-04-04T16:00:00Z",
        })
        r = run_script("metrics_dashboard", proj)
        assert "COMPLETE" in r.stdout


# ============================================================
# Edge case: no global data / clean HOME (T36-T37)
# ============================================================


class TestDashboardNoGlobalData:
    """T36-T37: No global data (clean HOME)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        """Set up a project with full local state but empty HOME."""
        self.clean_home = str(tmp_path / "clean_home")
        os.makedirs(self.clean_home, exist_ok=True)
        monkeypatch.setenv("HOME", self.clean_home)

        self.proj = str(tmp_path / "test-project-clean")
        state = os.path.join(self.proj, ".essay-state")
        os.makedirs(state, exist_ok=True)

        write_json(os.path.join(state, "pipeline-state.json"), PIPELINE_STATE)
        write_json(os.path.join(state, "review-technical.json"), REVIEW_TECHNICAL)
        write_json(os.path.join(state, "review-editor.json"), REVIEW_EDITOR)
        write_json(os.path.join(state, "review-adversarial.json"), REVIEW_ADVERSARIAL)
        write_json(os.path.join(state, "review-audience.json"), REVIEW_AUDIENCE)
        write_json(os.path.join(state, "review-seo.json"), REVIEW_SEO)
        write_json(os.path.join(state, "quality-score.json"), QUALITY_SCORE)
        write_json(os.path.join(state, "review-panel-summary.json"), REVIEW_PANEL_SUMMARY)
        write_json(os.path.join(state, "readability-draft.json"), READABILITY_DRAFT)

        # Checkpoints
        ckpt_dir = os.path.join(state, "checkpoints")
        for label, stg, ts in [
            ("intake-20260401T100500", "intake", "2026-04-01T10:05:00Z"),
            ("research-20260401T120000", "research", "2026-04-01T12:00:00Z"),
            ("outline-20260402T090000", "outline", "2026-04-02T09:00:00Z"),
            ("draft-20260403T140000", "draft", "2026-04-03T14:00:00Z"),
        ]:
            ckpt_path = os.path.join(ckpt_dir, label)
            os.makedirs(ckpt_path, exist_ok=True)
            write_json(os.path.join(ckpt_path, "pipeline-state.json"), {"stage": stg, "updated_at": ts})

        write_file(os.path.join(self.proj, "draft.md"), DRAFT_MD)

    def test_no_global_data_exits_zero(self, run_script):
        """T36: No global data does not crash."""
        r = run_script("metrics_dashboard", self.proj)
        assert r.returncode == 0

    def test_local_reviews_shown_without_global_data(self, run_script):
        """T37: Local reviews still shown without global data."""
        r = run_script("metrics_dashboard", self.proj)
        assert "technical" in r.stdout


# ============================================================
# Edge case: taste memory with only 1 article (T38)
# ============================================================


class TestDashboardSingleArticle:
    """T38: Single article shows appropriate message."""

    def test_single_article_message(self, run_script, tmp_path, fake_home):
        """T38: Single article shows appropriate message."""
        # Set up global data with only 1 article
        global_dir = os.path.join(fake_home, ".tech-essay-writer")
        os.makedirs(global_dir, exist_ok=True)
        write_json(os.path.join(global_dir, "taste-memory.json"), {
            "topics_written": [
                {"topic": "Solo Article", "date": "2026-04-01T00:00:00Z", "variant": "tutorial", "refinement_rounds": 2}
            ],
            "articles_count": 1,
        })
        # Use an empty project
        proj = str(tmp_path / "empty-project")
        os.makedirs(proj, exist_ok=True)
        r = run_script("metrics_dashboard", proj)
        assert "Only 1 article" in r.stdout


# ============================================================
# Section ordering (T39)
# ============================================================


class TestDashboardSectionOrder:
    """T39: Sections appear in correct order."""

    def test_sections_in_correct_order(self, run_script, full_project):
        """T39: Sections appear in correct order."""
        r = run_script("metrics_dashboard", full_project)
        out = r.stdout
        lines = out.splitlines()

        def find_line(needle):
            for i, line in enumerate(lines):
                if needle in line:
                    return i
            return -1

        pos_pipeline = find_line("PIPELINE HEALTH")
        pos_quality = find_line("QUALITY TRENDS")
        pos_review = find_line("REVIEW PANEL STATS")
        pos_author = find_line("AUTHOR GROWTH")
        pos_platform = find_line("PLATFORM PERFORMANCE")
        pos_writing = find_line("WRITING STATS")

        assert pos_pipeline < pos_quality < pos_review < pos_author < pos_platform < pos_writing, (
            f"Sections out of order: pipeline={pos_pipeline} quality={pos_quality} "
            f"review={pos_review} author={pos_author} platform={pos_platform} writing={pos_writing}"
        )


# ============================================================
# Visual elements (T40-T42)
# ============================================================


class TestDashboardVisualElements:
    """T40-T42: Visual elements in output."""

    def test_contains_bar_chart_chars(self, run_script, full_project):
        """T40: Contains bar chart characters."""
        r = run_script("metrics_dashboard", full_project)
        assert "\u2588" in r.stdout

    def test_contains_horizontal_rules(self, run_script, full_project):
        """T41: Contains horizontal rules."""
        r = run_script("metrics_dashboard", full_project)
        assert "\u2550" in r.stdout

    def test_shows_top_tags(self, run_script, full_project):
        """T42: Shows top tags."""
        r = run_script("metrics_dashboard", full_project)
        assert "Top Tags" in r.stdout


# ============================================================
# Analytics engagement metrics (T43-T45)
# ============================================================


class TestDashboardAnalytics:
    """T43-T45: Analytics and engagement metrics."""

    def test_shows_shares_metric(self, run_script, full_project):
        """T43: Shows shares in platform section."""
        r = run_script("metrics_dashboard", full_project)
        assert "Shares" in r.stdout

    def test_shows_top_articles(self, run_script, full_project):
        """T44: Shows top articles by views."""
        r = run_script("metrics_dashboard", full_project)
        assert "Top Articles" in r.stdout

    def test_shows_variant_distribution(self, run_script, full_project):
        """T45: Shows style variant distribution."""
        r = run_script("metrics_dashboard", full_project)
        assert "deep-dive" in r.stdout


# ============================================================
# Default directory / cwd (T46)
# ============================================================


class TestDashboardDefaultCwd:
    """T46: Runs with default project_dir (cwd)."""

    def test_default_cwd_exits_zero(self, run_script, full_project):
        """T46: Runs with default project_dir (cwd)."""
        r = run_script("metrics_dashboard", cwd=full_project)
        assert r.returncode == 0


# ============================================================
# Editing patterns and issue breakdown (T47-T48)
# ============================================================


class TestDashboardAdditionalSections:
    """T47-T48: Editing patterns and issue breakdown."""

    def test_shows_editing_patterns(self, run_script, full_project):
        """T47: Shows editing patterns from taste memory."""
        r = run_script("metrics_dashboard", full_project)
        assert "Editing Patterns" in r.stdout

    def test_shows_issue_breakdown(self, run_script, full_project):
        """T48: Shows issue breakdown."""
        r = run_script("metrics_dashboard", full_project)
        assert "Issue Breakdown" in r.stdout
