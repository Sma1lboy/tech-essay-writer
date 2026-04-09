"""Tests for progress_display.py and publishing_guide.py."""

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


def make_project(proj, stage, topic="Test Article"):
    """Create a pipeline state file for a project at a given stage."""
    state = {
        "topic": topic,
        "stage": stage,
        "draft_version": 2,
        "refinement_round": 1,
        "max_refinement_rounds": 3,
        "materials_count": 4,
        "language": "en",
        "reviews": {},
        "review_panel_complete": False,
        "completed": False,
        "series_id": None,
    }
    if stage == "complete":
        state["completed"] = True
        state["completed_at"] = "2026-01-01T00:00:00Z"
    write_json(proj, "pipeline-state.json", state)


def add_review(proj, reviewer, rating):
    """Add a review file and update pipeline state."""
    review = {
        "reviewer": reviewer,
        "rating": rating,
        "summary": "Test review",
        "issues": [
            {"severity": "minor", "location": "Section 1",
             "issue": "Test issue", "suggestion": "Fix it"}
        ],
    }
    write_json(proj, f"review-{reviewer}.json", review)
    # Update pipeline state reviews
    ps_path = os.path.join(proj, ".essay-state", "pipeline-state.json")
    with open(ps_path) as f:
        state = json.load(f)
    state.setdefault("reviews", {})[reviewer] = {
        "rating": rating, "issues_count": 1,
    }
    with open(ps_path, "w") as f:
        json.dump(state, f)


def add_quality(proj, score, readiness):
    """Add a quality score file."""
    quality = {
        "composite_score": score,
        "readiness": readiness,
        "dimension_scores": {"technical": 8.0, "editor": 7.5, "adversarial": 6.0},
        "reviews_available": 3,
        "reviews_expected": 7,
    }
    write_json(proj, "quality-score.json", quality)


def add_seo(proj):
    """Add SEO metadata file."""
    seo = {
        "tags": ["react", "javascript", "tutorial"],
        "keywords": ["react hooks", "state management"],
        "meta_description": "A comprehensive guide to React hooks and state management patterns.",
    }
    write_json(proj, "seo-metadata.json", seo)


def parse_json(stdout):
    """Parse JSON from stdout."""
    return json.loads(stdout)


# ============================================================
# PROGRESS-DISPLAY.PY TESTS
# ============================================================


class TestProgressDisplayNoState:
    """progress-display: no state directory."""

    def test_no_state_shows_not_initialized(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-empty")
        r = run_script("progress_display", proj)
        assert "not initialized" in r.stdout.lower()

    def test_no_state_json_shows_error(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-empty-json")
        r = run_script("progress_display", proj, "--format", "json")
        assert "not_initialized" in r.stdout


class TestProgressDisplayIntakeStage:
    """progress-display: intake stage display."""

    def test_shows_intake(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-intake")
        make_project(proj, "intake")
        r = run_script("progress_display", proj)
        assert "INTAKE" in r.stdout

    def test_shows_current_stage(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-intake2")
        make_project(proj, "intake")
        r = run_script("progress_display", proj)
        assert "intake" in r.stdout

    def test_has_progress_bar(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-intake3")
        make_project(proj, "intake")
        r = run_script("progress_display", proj)
        assert "Progress:" in r.stdout

    def test_shows_completion_pct(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-intake4")
        make_project(proj, "intake")
        r = run_script("progress_display", proj)
        assert "%" in r.stdout


class TestProgressDisplayEachStageIndicator:
    """progress-display: each stage shows its name and a current indicator."""

    @pytest.mark.parametrize("stage", [
        "intake", "research", "outline", "draft",
        "review", "refinement", "polish", "complete",
    ])
    def test_stage_shows_name(self, run_script, tmp_path, fake_home, stage):
        proj = setup_project(tmp_path, f"proj-{stage}")
        make_project(proj, stage)
        r = run_script("progress_display", proj)
        assert stage in r.stdout

    @pytest.mark.parametrize("stage", [
        "intake", "research", "outline", "draft",
        "review", "refinement", "polish", "complete",
    ])
    def test_stage_has_current_indicator(self, run_script, tmp_path, fake_home, stage):
        proj = setup_project(tmp_path, f"proj-ind-{stage}")
        make_project(proj, stage)
        r = run_script("progress_display", proj)
        # Should have either current (bullet) or completed (checkmark)
        assert "\u25cf" in r.stdout or "\u2713" in r.stdout


class TestProgressDisplayCompletionPercentages:
    """progress-display: completion percentages at different stages."""

    def test_intake_completion_is_0(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-pct-intake")
        make_project(proj, "intake")
        r = run_script("progress_display", proj, "--format", "json")
        data = parse_json(r.stdout)
        assert float(data["completion_pct"]) == 0.0

    def test_draft_completion_is_25(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-pct-draft")
        make_project(proj, "draft")
        r = run_script("progress_display", proj, "--format", "json")
        data = parse_json(r.stdout)
        assert data["completion_pct"] == 25.0

    def test_complete_is_100(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-pct-complete")
        make_project(proj, "complete")
        r = run_script("progress_display", proj, "--format", "json")
        data = parse_json(r.stdout)
        assert data["completion_pct"] == 100.0


class TestProgressDisplayJSONFormat:
    """progress-display: JSON format output fields."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-json")
        make_project(self.proj, "review", "JSON Test Topic")
        add_review(self.proj, "technical", "PASS")
        add_quality(self.proj, 7.5, "CLOSE")
        r = run_script("progress_display", self.proj, "--format", "json")
        self.data = parse_json(r.stdout)

    def test_json_has_topic(self):
        assert self.data["topic"] == "JSON Test Topic"

    def test_json_has_stage(self):
        assert self.data["stage"] == "review"

    def test_json_has_completed(self):
        assert self.data["completed"] is False

    def test_json_has_language(self):
        assert self.data["language"] == "en"

    def test_json_has_draft_version(self):
        assert self.data["draft_version"] == 2

    def test_json_has_8_stages(self):
        assert len(self.data["stages"]) == 8

    def test_json_has_quality_score(self):
        assert self.data["quality"]["composite_score"] == 7.5

    def test_json_has_technical_review(self):
        assert self.data["reviews"]["technical"]["rating"] == "PASS"


class TestProgressDisplayReviewDetails:
    """progress-display: review dashboard display."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-reviews")
        make_project(self.proj, "review")
        add_review(self.proj, "technical", "PASS")
        add_review(self.proj, "editor", "NEEDS_EDITING")
        add_review(self.proj, "adversarial", "VULNERABLE")
        self.result = run_script("progress_display", self.proj)

    def test_shows_review_dashboard(self):
        assert "Review Dashboard" in self.result.stdout

    def test_shows_technical_rating(self):
        assert "PASS" in self.result.stdout

    def test_shows_editor_rating(self):
        assert "NEEDS_EDITING" in self.result.stdout

    def test_shows_adversarial_rating(self):
        assert "VULNERABLE" in self.result.stdout

    def test_shows_review_count(self):
        assert "3/7" in self.result.stdout


class TestProgressDisplayReviewProgressInCompletion:
    """progress-display: review progress affects completion percentage."""

    def test_review_with_2_of_7_progress(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-review-pct")
        make_project(proj, "review")
        add_review(proj, "technical", "PASS")
        add_review(proj, "editor", "NEEDS_EDITING")
        r = run_script("progress_display", proj, "--format", "json")
        data = parse_json(r.stdout)
        # review stage base = 45% (intake+research+outline+draft weights) + 2/7 of review weight (20%)
        assert data["completion_pct"] == 50.7


class TestProgressDisplayQualityMetrics:
    """progress-display: quality score display."""

    def test_shows_quality_score(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-quality")
        make_project(proj, "refinement")
        add_quality(proj, 8.5, "READY")
        r = run_script("progress_display", proj)
        assert "8.5/10" in r.stdout

    def test_shows_readiness(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-quality2")
        make_project(proj, "refinement")
        add_quality(proj, 8.5, "READY")
        r = run_script("progress_display", proj)
        assert "READY" in r.stdout

    def test_verbose_shows_dimension_scores_technical(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-quality3")
        make_project(proj, "refinement")
        add_quality(proj, 8.5, "READY")
        r = run_script("progress_display", proj, "--verbose")
        assert "technical" in r.stdout

    def test_verbose_shows_dimension_bar_editor(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-quality4")
        make_project(proj, "refinement")
        add_quality(proj, 8.5, "READY")
        r = run_script("progress_display", proj, "--verbose")
        assert "editor" in r.stdout


class TestProgressDisplayVerboseMode:
    """progress-display: verbose output."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-verbose")
        make_project(self.proj, "review")
        add_review(self.proj, "technical", "PASS")
        add_quality(self.proj, 7.0, "CLOSE")

    def test_verbose_shows_pending_reviewers(self, run_script):
        r = run_script("progress_display", self.proj, "--verbose")
        assert "PENDING" in r.stdout

    def test_verbose_shows_dimensions(self, run_script):
        r = run_script("progress_display", self.proj, "--verbose")
        assert "Dimension Scores" in r.stdout


class TestProgressDisplayArtifacts:
    """progress-display: artifact listing."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-artifacts")
        make_project(self.proj, "polish")
        write_file(self.proj, "draft-v1.md", "# Test Draft")
        write_file(self.proj, "final-internal.md", "# Final Internal")
        write_json(self.proj, "social-package.json", {"twitter_thread": "test"})

    def test_json_artifacts_has_draft(self, run_script):
        r = run_script("progress_display", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        assert "draft" in data["artifacts"]

    def test_json_artifacts_has_final_internal(self, run_script):
        r = run_script("progress_display", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        assert "final-internal" in data["artifacts"]

    def test_json_artifacts_has_social_package(self, run_script):
        r = run_script("progress_display", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        assert "social-package" in data["artifacts"]

    def test_verbose_lists_artifacts(self, run_script):
        r = run_script("progress_display", self.proj, "--verbose")
        assert "Artifacts:" in r.stdout


class TestProgressDisplaySeriesId:
    """progress-display: series_id display."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-series")
        make_project(self.proj, "draft")
        ps_path = os.path.join(self.proj, ".essay-state", "pipeline-state.json")
        with open(ps_path) as f:
            s = json.load(f)
        s["series_id"] = "react-series-001"
        with open(ps_path, "w") as f:
            json.dump(s, f)

    def test_text_shows_series_id(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "react-series-001" in r.stdout

    def test_json_has_series_id(self, run_script):
        r = run_script("progress_display", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        assert data["series_id"] == "react-series-001"


class TestProgressDisplayCompletedPipeline:
    """progress-display: completed pipeline display."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-complete")
        make_project(self.proj, "complete")

    def test_complete_shows_100(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "100" in r.stdout

    def test_complete_shows_completed_at(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "Completed at" in r.stdout

    def test_complete_has_no_pending(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "\u25cb" not in r.stdout


class TestProgressDisplayCorruptState:
    """progress-display: corrupt state handling."""

    def test_corrupt_state_exits_nonzero(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-corrupt")
        ps_path = os.path.join(proj, ".essay-state", "pipeline-state.json")
        with open(ps_path, "w") as f:
            f.write("NOT_JSON")
        r = run_script("progress_display", proj)
        assert r.returncode != 0

    def test_corrupt_json_shows_error(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-corrupt2")
        ps_path = os.path.join(proj, ".essay-state", "pipeline-state.json")
        with open(ps_path, "w") as f:
            f.write("NOT_JSON")
        r = run_script("progress_display", proj, "--format", "json")
        combined = r.stdout + r.stderr
        assert "corrupt_state" in combined


class TestProgressDisplayInvalidFormat:
    """progress-display: invalid format option rejected."""

    def test_invalid_format_rejected(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-badfmt")
        make_project(proj, "draft")
        r = run_script("progress_display", proj, "--format", "xml")
        assert r.returncode != 0


class TestProgressDisplayDraftVersionRefinement:
    """progress-display: draft version and refinement round."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-drafts")
        make_project(self.proj, "refinement")
        ps_path = os.path.join(self.proj, ".essay-state", "pipeline-state.json")
        with open(ps_path) as f:
            s = json.load(f)
        s["draft_version"] = 3
        s["refinement_round"] = 2
        with open(ps_path, "w") as f:
            json.dump(s, f)

    def test_shows_draft_version_3(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "3" in r.stdout

    def test_shows_refinement_round_2_of_3(self, run_script):
        r = run_script("progress_display", self.proj)
        assert "2/3" in r.stdout


class TestProgressDisplayMaterialsCount:
    """progress-display: materials count display."""

    def test_shows_materials_count(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "proj-materials")
        make_project(proj, "research")
        ps_path = os.path.join(proj, ".essay-state", "pipeline-state.json")
        with open(ps_path) as f:
            s = json.load(f)
        s["materials_count"] = 12
        with open(ps_path, "w") as f:
            json.dump(s, f)
        r = run_script("progress_display", proj)
        assert "12" in r.stdout


class TestProgressDisplayStageMapJSON:
    """progress-display: stage map statuses in JSON output."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-stagemap")
        make_project(self.proj, "outline")
        r = run_script("progress_display", self.proj, "--format", "json")
        self.data = parse_json(r.stdout)

    def test_intake_status_completed(self):
        assert self.data["stages"][0]["status"] == "completed"

    def test_research_status_completed(self):
        assert self.data["stages"][1]["status"] == "completed"

    def test_outline_status_current(self):
        assert self.data["stages"][2]["status"] == "current"

    def test_draft_status_pending(self):
        assert self.data["stages"][3]["status"] == "pending"


# ============================================================
# PUBLISHING-GUIDE.PY TESTS
# ============================================================


class TestPublishingGuideEachPlatform:
    """publishing-guide: each platform has expected sections."""

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_publishing_guide_header(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Publishing Guide" in r.stdout

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_steps(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Steps:" in r.stdout

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_seo_tips(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "SEO Tips:" in r.stdout

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_formatting(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Formatting:" in r.stdout

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_limits(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Limits:" in r.stdout

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_checklist(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Checklist:" in r.stdout


class TestPublishingGuideAllPlatforms:
    """publishing-guide: 'all' lists all platforms."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.result = run_script("publishing_guide", "all")

    def test_all_lists_internal(self):
        assert "internal" in self.result.stdout

    def test_all_lists_external(self):
        assert "external" in self.result.stdout

    def test_all_lists_medium(self):
        assert "medium" in self.result.stdout

    def test_all_lists_devto(self):
        assert "devto" in self.result.stdout

    def test_all_lists_hashnode(self):
        assert "hashnode" in self.result.stdout

    def test_all_lists_wechat(self):
        assert "wechat" in self.result.stdout

    def test_all_lists_juejin(self):
        assert "juejin" in self.result.stdout

    def test_all_shows_available_platforms(self):
        assert "Available platforms" in self.result.stdout


class TestPublishingGuideInvalidPlatform:
    """publishing-guide: invalid platform rejected."""

    def test_invalid_platform_rejected(self, run_script, fake_home):
        r = run_script("publishing_guide", "twitter")
        assert r.returncode != 0


class TestPublishingGuideJSONFormatPerPlatform:
    """publishing-guide: JSON format per platform has required fields."""

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_json_platform_field(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert data["platform"] == platform

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_json_has_steps(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert len(data["steps"]) > 0

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_json_has_seo_tips(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert len(data["seo_tips"]) > 0

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_json_has_checklist(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert len(data["checklist"]) > 0


class TestPublishingGuideAllJSONFormat:
    """publishing-guide: 'all' JSON format."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        r = run_script("publishing_guide", "all", "--format", "json")
        self.data = parse_json(r.stdout)

    def test_all_json_has_7_platforms(self):
        assert len(self.data) == 7

    def test_all_json_first_is_internal(self):
        assert self.data[0]["platform"] == "internal"


class TestPublishingGuideWithArticleMetadata:
    """publishing-guide: with article metadata from project dir."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, fake_home):
        self.proj = setup_project(tmp_path, "proj-meta")
        make_project(self.proj, "complete", "React Hooks Deep Dive")
        add_seo(self.proj)

    def test_metadata_shows_article_title(self, run_script):
        r = run_script("publishing_guide", "medium", self.proj)
        assert "React Hooks Deep Dive" in r.stdout

    def test_metadata_shows_suggested_tags(self, run_script):
        r = run_script("publishing_guide", "medium", self.proj)
        assert "react" in r.stdout

    def test_json_metadata_has_title(self, run_script):
        r = run_script("publishing_guide", "medium", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        assert data.get("article_metadata", {}).get("article_title") == "React Hooks Deep Dive"

    def test_json_metadata_has_tags(self, run_script):
        r = run_script("publishing_guide", "medium", self.proj, "--format", "json")
        data = parse_json(r.stdout)
        tags = data.get("article_metadata", {}).get("suggested_tags", [])
        assert "react" in ",".join(tags)


class TestPublishingGuideWithoutProjectDir:
    """publishing-guide: without project dir still shows guide."""

    def test_no_project_still_shows_guide(self, run_script, fake_home):
        r = run_script("publishing_guide", "devto")
        assert "Publishing Guide" in r.stdout

    def test_no_project_no_article_metadata(self, run_script, fake_home):
        r = run_script("publishing_guide", "devto")
        assert "Article:" not in r.stdout


class TestPublishingGuideChinesePlatforms:
    """publishing-guide: Chinese platforms use Chinese text."""

    def test_wechat_tips_in_chinese_title(self, run_script, fake_home):
        r = run_script("publishing_guide", "wechat")
        assert "\u6807\u9898" in r.stdout

    def test_wechat_steps_in_chinese_confirm(self, run_script, fake_home):
        r = run_script("publishing_guide", "wechat")
        assert "\u786e\u8ba4" in r.stdout

    def test_juejin_tips_in_chinese_title(self, run_script, fake_home):
        r = run_script("publishing_guide", "juejin")
        assert "\u6807\u9898" in r.stdout

    def test_juejin_steps_in_chinese_confirm(self, run_script, fake_home):
        r = run_script("publishing_guide", "juejin")
        assert "\u786e\u8ba4" in r.stdout


class TestPublishingGuidePlatformSpecificContent:
    """publishing-guide: platform-specific content details."""

    def test_medium_mentions_subtitle(self, run_script, fake_home):
        r = run_script("publishing_guide", "medium")
        assert "subtitle" in r.stdout.lower()

    def test_medium_mentions_publications(self, run_script, fake_home):
        r = run_script("publishing_guide", "medium")
        assert "publication" in r.stdout.lower()

    def test_devto_mentions_front_matter(self, run_script, fake_home):
        r = run_script("publishing_guide", "devto")
        assert "front matter" in r.stdout.lower()

    def test_devto_mentions_canonical(self, run_script, fake_home):
        r = run_script("publishing_guide", "devto")
        assert "canonical" in r.stdout.lower()

    def test_hashnode_mentions_custom_domain(self, run_script, fake_home):
        r = run_script("publishing_guide", "hashnode")
        assert "custom domain" in r.stdout.lower()


class TestPublishingGuideLimitsInJSON:
    """publishing-guide: limits in JSON output."""

    def test_medium_title_limit(self, run_script, fake_home):
        r = run_script("publishing_guide", "medium", "--format", "json")
        data = parse_json(r.stdout)
        assert "100" in str(data["limits"]["title_max"])

    def test_medium_tags_limit(self, run_script, fake_home):
        r = run_script("publishing_guide", "medium", "--format", "json")
        data = parse_json(r.stdout)
        assert "5" in str(data["limits"]["tags_max"])

    def test_devto_tags_limit(self, run_script, fake_home):
        r = run_script("publishing_guide", "devto", "--format", "json")
        data = parse_json(r.stdout)
        assert "4" in str(data["limits"]["tags_max"])


class TestPublishingGuideInvalidFormat:
    """publishing-guide: invalid format rejected."""

    def test_invalid_format_rejected(self, run_script, fake_home):
        r = run_script("publishing_guide", "medium", "--format", "yaml")
        assert r.returncode != 0


class TestPublishingGuideTagsAdvice:
    """publishing-guide: each platform has tags advice."""

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_has_tags_advice(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform)
        assert "Tags:" in r.stdout


class TestPublishingGuideAllJSONStructure:
    """publishing-guide: 'all' json items have name field."""

    @pytest.mark.parametrize("idx", [0, 1, 2, 3, 4, 5, 6])
    def test_all_json_item_has_name(self, run_script, fake_home, idx):
        r = run_script("publishing_guide", "all", "--format", "json")
        data = parse_json(r.stdout)
        assert len(data[idx].get("name", "")) > 0


class TestPublishingGuideSEOTipsCount:
    """publishing-guide: each platform has >= 5 SEO tips."""

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_platform_has_at_least_5_seo_tips(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert len(data["seo_tips"]) >= 5


class TestPublishingGuideChecklistCount:
    """publishing-guide: each platform has >= 6 checklist items."""

    @pytest.mark.parametrize("platform", [
        "internal", "external", "medium", "devto",
        "hashnode", "wechat", "juejin",
    ])
    def test_platform_has_at_least_6_checklist_items(self, run_script, fake_home, platform):
        r = run_script("publishing_guide", platform, "--format", "json")
        data = parse_json(r.stdout)
        assert len(data["checklist"]) >= 6
