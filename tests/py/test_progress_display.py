"""Tests for progress_display.py — pipeline progress visualization."""

import json
import os

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_state(project_dir, stage, **kwargs):
    """Create a minimal pipeline state file."""
    materials_count = kwargs.get("materials_count", 0)
    draft_version = kwargs.get("draft_version", 0)
    refinement_round = kwargs.get("refinement_round", 0)
    max_refinement_rounds = kwargs.get("max_refinement_rounds", 3)
    completed = kwargs.get("completed", False)
    topic = kwargs.get("topic", "Test Topic")
    completed_at = kwargs.get("completed_at", "")

    state_dir = os.path.join(project_dir, ".essay-state")
    os.makedirs(state_dir, exist_ok=True)

    data = {
        "topic": topic,
        "stage": stage,
        "materials_count": materials_count,
        "draft_version": draft_version,
        "refinement_round": refinement_round,
        "max_refinement_rounds": max_refinement_rounds,
        "completed": completed,
        "reviews": {},
    }
    if completed_at:
        data["completed_at"] = completed_at

    with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
        json.dump(data, f, indent=2)


def create_quality(project_dir, score, readiness, reviews):
    """Create a quality-score.json file."""
    state_dir = os.path.join(project_dir, ".essay-state")
    os.makedirs(state_dir, exist_ok=True)

    data = {
        "composite_score": float(score),
        "readiness": readiness,
        "reviews_available": int(reviews),
        "reviews_expected": 7,
        "dimension_scores": {
            "technical": 8.0,
            "editor": 7.5,
            "adversarial": 6.0,
        },
    }

    with open(os.path.join(state_dir, "quality-score.json"), "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Test: Missing state
# ---------------------------------------------------------------------------

class TestMissingState:
    """Tests for missing / uninitialized state directory."""

    def test_missing_state_shows_not_initialized(self, run_script, tmp_path):
        project = str(tmp_path / "no-state")
        os.makedirs(project, exist_ok=True)
        r = run_script("progress_display", project)
        assert "not initialized" in r.stdout.lower() or "not initialized" in r.stderr.lower()

    def test_missing_state_json_shows_error(self, run_script, tmp_path):
        project = str(tmp_path / "no-state-json")
        os.makedirs(project, exist_ok=True)
        r = run_script("progress_display", project, "--format", "json")
        combined = r.stdout + r.stderr
        assert "not_initialized" in combined


# ---------------------------------------------------------------------------
# Test: Intake stage
# ---------------------------------------------------------------------------

class TestIntakeStage:
    """Tests for the intake stage display."""

    def test_intake_shows_label(self, run_script, tmp_path):
        project = str(tmp_path / "intake-proj")
        create_state(project, "intake", materials_count=0)
        r = run_script("progress_display", project)
        assert "INTAKE" in r.stdout

    def test_intake_shows_current_indicator(self, run_script, tmp_path):
        project = str(tmp_path / "intake-proj")
        create_state(project, "intake", materials_count=0)
        r = run_script("progress_display", project)
        assert "\u25cf" in r.stdout  # ●

    def test_intake_shows_zero_percent(self, run_script, tmp_path):
        project = str(tmp_path / "intake-proj")
        create_state(project, "intake", materials_count=0)
        r = run_script("progress_display", project)
        assert "0" in r.stdout

    def test_intake_shows_topic(self, run_script, tmp_path):
        project = str(tmp_path / "intake-proj")
        create_state(project, "intake", materials_count=0)
        r = run_script("progress_display", project)
        assert "Test Topic" in r.stdout

    def test_intake_json_has_stage(self, run_script, tmp_path):
        project = str(tmp_path / "intake-proj")
        create_state(project, "intake", materials_count=0)
        r = run_script("progress_display", project, "--format", "json")
        assert '"intake"' in r.stdout


# ---------------------------------------------------------------------------
# Test: Research stage
# ---------------------------------------------------------------------------

class TestResearchStage:
    """Tests for the research stage display."""

    def test_research_shows_check_for_intake(self, run_script, tmp_path):
        project = str(tmp_path / "research-proj")
        create_state(project, "research", materials_count=5)
        r = run_script("progress_display", project)
        assert "\u2713" in r.stdout  # ✓

    def test_research_shows_current_indicator(self, run_script, tmp_path):
        project = str(tmp_path / "research-proj")
        create_state(project, "research", materials_count=5)
        r = run_script("progress_display", project)
        assert "\u25cf" in r.stdout  # ●

    def test_research_shows_five_percent(self, run_script, tmp_path):
        project = str(tmp_path / "research-proj")
        create_state(project, "research", materials_count=5)
        r = run_script("progress_display", project)
        assert "5" in r.stdout

    def test_research_shows_materials_count(self, run_script, tmp_path):
        project = str(tmp_path / "research-proj")
        create_state(project, "research", materials_count=5)
        r = run_script("progress_display", project)
        assert "5" in r.stdout


# ---------------------------------------------------------------------------
# Test: Outline stage
# ---------------------------------------------------------------------------

class TestOutlineStage:
    """Tests for the outline stage display."""

    def test_outline_shows_fifteen_percent(self, run_script, tmp_path):
        project = str(tmp_path / "outline-proj")
        create_state(project, "outline", materials_count=8)
        r = run_script("progress_display", project)
        assert "15" in r.stdout

    def test_outline_stage_label(self, run_script, tmp_path):
        project = str(tmp_path / "outline-proj")
        create_state(project, "outline", materials_count=8)
        r = run_script("progress_display", project)
        assert "outline" in r.stdout.lower()


# ---------------------------------------------------------------------------
# Test: Draft stage
# ---------------------------------------------------------------------------

class TestDraftStage:
    """Tests for the draft stage display."""

    def test_draft_shows_twenty_five_percent(self, run_script, tmp_path):
        project = str(tmp_path / "draft-proj")
        create_state(project, "draft", materials_count=10, draft_version=2)
        r = run_script("progress_display", project)
        assert "25" in r.stdout

    def test_draft_shows_draft_version(self, run_script, tmp_path):
        project = str(tmp_path / "draft-proj")
        create_state(project, "draft", materials_count=10, draft_version=2)
        r = run_script("progress_display", project)
        assert "2" in r.stdout

    def test_draft_json_has_completion(self, run_script, tmp_path):
        project = str(tmp_path / "draft-proj")
        create_state(project, "draft", materials_count=10, draft_version=2)
        r = run_script("progress_display", project, "--format", "json")
        assert "25.0" in r.stdout


# ---------------------------------------------------------------------------
# Test: Review stage
# ---------------------------------------------------------------------------

class TestReviewStage:
    """Tests for the review stage display."""

    def test_review_shows_forty_five_percent(self, run_script, tmp_path):
        project = str(tmp_path / "review-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        r = run_script("progress_display", project)
        assert "45" in r.stdout


# ---------------------------------------------------------------------------
# Test: Refinement stage
# ---------------------------------------------------------------------------

class TestRefinementStage:
    """Tests for the refinement stage display."""

    def test_refinement_shows_round_info(self, run_script, tmp_path):
        project = str(tmp_path / "refine-proj")
        create_state(project, "refinement", materials_count=10, draft_version=1,
                     refinement_round=2, max_refinement_rounds=3)
        r = run_script("progress_display", project)
        assert "2/3" in r.stdout


# ---------------------------------------------------------------------------
# Test: Polish stage
# ---------------------------------------------------------------------------

class TestPolishStage:
    """Tests for the polish stage display."""

    def test_polish_shows_eighty_five_percent(self, run_script, tmp_path):
        project = str(tmp_path / "polish-proj")
        create_state(project, "polish", materials_count=10, draft_version=3,
                     refinement_round=3)
        r = run_script("progress_display", project)
        assert "85" in r.stdout


# ---------------------------------------------------------------------------
# Test: Complete stage
# ---------------------------------------------------------------------------

class TestCompleteStage:
    """Tests for the complete stage display."""

    def test_complete_shows_one_hundred_percent(self, run_script, tmp_path):
        project = str(tmp_path / "complete-proj")
        create_state(project, "complete", materials_count=12, draft_version=3,
                     refinement_round=3, completed=True,
                     completed_at="2026-04-06T12:00:00Z")
        r = run_script("progress_display", project)
        assert "100" in r.stdout

    def test_complete_shows_all_checks(self, run_script, tmp_path):
        project = str(tmp_path / "complete-proj")
        create_state(project, "complete", materials_count=12, draft_version=3,
                     refinement_round=3, completed=True,
                     completed_at="2026-04-06T12:00:00Z")
        r = run_script("progress_display", project)
        assert "\u2713" in r.stdout  # ✓

    def test_complete_shows_completed_at(self, run_script, tmp_path):
        project = str(tmp_path / "complete-proj")
        create_state(project, "complete", materials_count=12, draft_version=3,
                     refinement_round=3, completed=True,
                     completed_at="2026-04-06T12:00:00Z")
        r = run_script("progress_display", project)
        assert "2026-04-06" in r.stdout

    def test_complete_json_shows_one_hundred(self, run_script, tmp_path):
        project = str(tmp_path / "complete-proj")
        create_state(project, "complete", materials_count=12, draft_version=3,
                     refinement_round=3, completed=True,
                     completed_at="2026-04-06T12:00:00Z")
        r = run_script("progress_display", project, "--format", "json")
        assert "100.0" in r.stdout


# ---------------------------------------------------------------------------
# Test: Quality display
# ---------------------------------------------------------------------------

class TestQualityDisplay:
    """Tests for quality score display."""

    def test_quality_shows_score(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project)
        assert "7.5" in r.stdout

    def test_quality_shows_readiness(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project)
        assert "CLOSE" in r.stdout

    def test_quality_shows_reviews_count(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project)
        assert "5/7" in r.stdout

    def test_verbose_shows_technical_dimension(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project, "--verbose")
        assert "technical" in r.stdout

    def test_verbose_shows_editor_dimension(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project, "--verbose")
        assert "editor" in r.stdout

    def test_json_shows_quality_score(self, run_script, tmp_path):
        project = str(tmp_path / "quality-proj")
        create_state(project, "review", materials_count=10, draft_version=1)
        create_quality(project, 7.5, "CLOSE", 5)
        r = run_script("progress_display", project, "--format", "json")
        assert "7.5" in r.stdout

    def test_no_quality_file_shows_no_score(self, run_script, tmp_path):
        project = str(tmp_path / "no-quality-proj")
        create_state(project, "draft", materials_count=5, draft_version=1)
        r = run_script("progress_display", project)
        assert "No score available" in r.stdout


# ---------------------------------------------------------------------------
# Test: Pipeline arrows
# ---------------------------------------------------------------------------

class TestPipelineArrows:
    """Tests for pipeline display formatting."""

    def test_display_has_arrows(self, run_script, tmp_path):
        project = str(tmp_path / "arrows-proj")
        create_state(project, "draft")
        r = run_script("progress_display", project)
        assert "\u2192" in r.stdout  # →

    def test_progress_bar_present(self, run_script, tmp_path):
        project = str(tmp_path / "arrows-proj")
        create_state(project, "draft")
        r = run_script("progress_display", project)
        assert "Progress:" in r.stdout


# ---------------------------------------------------------------------------
# Test: Empty circle indicators
# ---------------------------------------------------------------------------

class TestEmptyCircleIndicators:
    """Tests for future stage indicators."""

    def test_future_stages_show_empty_circles(self, run_script, tmp_path):
        project = str(tmp_path / "empty-circles-proj")
        create_state(project, "intake")
        r = run_script("progress_display", project)
        assert "\u25cb" in r.stdout  # ○


# ---------------------------------------------------------------------------
# Test: Custom topic display
# ---------------------------------------------------------------------------

class TestCustomTopicDisplay:
    """Tests for custom topic rendering."""

    def test_custom_topic_displayed(self, run_script, tmp_path):
        project = str(tmp_path / "custom-topic-proj")
        create_state(project, "research", topic="Building Scalable APIs")
        r = run_script("progress_display", project)
        assert "Building Scalable APIs" in r.stdout


# ---------------------------------------------------------------------------
# Test: Corrupt state file
# ---------------------------------------------------------------------------

class TestCorruptState:
    """Tests for corrupt state file handling."""

    def test_corrupt_state_shows_error(self, run_script, tmp_path):
        project = str(tmp_path / "corrupt-proj")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir, exist_ok=True)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("not json at all")
        r = run_script("progress_display", project)
        combined = r.stdout + r.stderr
        assert "ERROR" in combined

    def test_corrupt_state_json_shows_error(self, run_script, tmp_path):
        project = str(tmp_path / "corrupt-proj-json")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir, exist_ok=True)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("not json at all")
        r = run_script("progress_display", project, "--format", "json")
        combined = r.stdout + r.stderr
        assert "corrupt_state" in combined


# ---------------------------------------------------------------------------
# Test: High quality score
# ---------------------------------------------------------------------------

class TestHighQualityScore:
    """Tests for high quality score display."""

    def test_high_quality_shows_ready(self, run_script, tmp_path):
        project = str(tmp_path / "high-quality-proj")
        create_state(project, "polish", materials_count=15, draft_version=4,
                     refinement_round=3)
        create_quality(project, 9.2, "READY", 7)
        r = run_script("progress_display", project)
        assert "READY" in r.stdout

    def test_high_quality_shows_score(self, run_script, tmp_path):
        project = str(tmp_path / "high-quality-proj")
        create_state(project, "polish", materials_count=15, draft_version=4,
                     refinement_round=3)
        create_quality(project, 9.2, "READY", 7)
        r = run_script("progress_display", project)
        assert "9.2" in r.stdout

    def test_high_quality_shows_all_reviews(self, run_script, tmp_path):
        project = str(tmp_path / "high-quality-proj")
        create_state(project, "polish", materials_count=15, draft_version=4,
                     refinement_round=3)
        create_quality(project, 9.2, "READY", 7)
        r = run_script("progress_display", project)
        assert "7/7" in r.stdout
