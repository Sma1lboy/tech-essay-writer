"""Tests for pipeline_state, intake_materials, taste_memory, aggregate_reviews, calibrate_reviews."""

import json
import os

import pytest


# ── pipeline_state tests ──────────────────────────────────────────────


class TestPipelineStateInit:
    def test_init_returns_success(self, run_script, tmp_project):
        r = run_script("pipeline_state", "init", tmp_project, "Test Topic")
        assert "initialized" in r.stdout

    def test_state_file_created(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        assert os.path.isfile(os.path.join(tmp_project, ".essay-state", "pipeline-state.json"))

    def test_initial_stage_is_intake(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        r = run_script("pipeline_state", "get-stage", tmp_project)
        assert r.stdout.strip() == "intake"


class TestPipelineStateStage:
    def test_set_stage(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        run_script("pipeline_state", "set-stage", tmp_project, "research")
        r = run_script("pipeline_state", "get-stage", tmp_project)
        assert r.stdout.strip() == "research"

    def test_reject_invalid_stage(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        r = run_script("pipeline_state", "set-stage", tmp_project, "invalid")
        assert r.returncode != 0


class TestPipelineStateFields:
    def test_set_get_field(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        run_script("pipeline_state", "set-field", tmp_project, "outline_variant", "A")
        r = run_script("pipeline_state", "get-field", tmp_project, "outline_variant")
        assert "A" in r.stdout

    def test_read_contains_topic(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        r = run_script("pipeline_state", "read", tmp_project)
        assert "Test Topic" in r.stdout

    def test_read_contains_stage(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        run_script("pipeline_state", "set-stage", tmp_project, "research")
        r = run_script("pipeline_state", "read", tmp_project)
        assert "research" in r.stdout


class TestPipelineStateRefinement:
    def test_refinement_round_incremented(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        run_script("pipeline_state", "refinement-round", tmp_project)
        r = run_script("pipeline_state", "get-field", tmp_project, "refinement_round")
        assert "1" in r.stdout


class TestPipelineStateComplete:
    def test_complete_sets_stage(self, run_script, tmp_project):
        run_script("pipeline_state", "init", tmp_project, "Test Topic")
        run_script("pipeline_state", "complete", tmp_project)
        r = run_script("pipeline_state", "get-stage", tmp_project)
        assert r.stdout.strip() == "complete"


# ── intake_materials tests ────────────────────────────────────────────


class TestIntakeMaterials:
    @pytest.fixture(autouse=True)
    def setup_project(self, run_script, tmp_path):
        self.project = str(tmp_path / "intake-proj")
        os.makedirs(self.project)
        run_script("intake_materials", "init", self.project)
        self.run = run_script

    def test_materials_file_created(self):
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "materials.json"))

    def test_add_url_returns_id(self):
        r = self.run("intake_materials", "add-url", self.project, "https://example.com", "Example")
        assert "src-" in r.stdout

    def test_add_note(self):
        self.run("intake_materials", "add-note", self.project, "My important note")
        r = self.run("intake_materials", "list", self.project)
        assert "My important" in r.stdout

    def test_add_theme(self):
        self.run("intake_materials", "add-theme", self.project, "scalability")
        r = self.run("intake_materials", "list", self.project)
        assert "scalability" in r.stdout

    def test_add_angle(self):
        self.run("intake_materials", "add-angle", self.project, "contrarian view")
        r = self.run("intake_materials", "list", self.project)
        assert "contrarian" in r.stdout

    def test_list_shows_all(self):
        self.run("intake_materials", "add-url", self.project, "https://example.com", "Example")
        self.run("intake_materials", "add-note", self.project, "My important note")
        self.run("intake_materials", "add-theme", self.project, "scalability")
        self.run("intake_materials", "add-angle", self.project, "contrarian view")
        r = self.run("intake_materials", "list", self.project)
        assert "example.com" in r.stdout
        assert "My important" in r.stdout
        assert "scalability" in r.stdout
        assert "contrarian" in r.stdout
        assert "2 sources" in r.stdout

    def test_export_is_json(self):
        self.run("intake_materials", "add-url", self.project, "https://example.com", "Example")
        r = self.run("intake_materials", "export", self.project)
        assert "sources" in r.stdout

    def test_clear(self):
        self.run("intake_materials", "add-url", self.project, "https://example.com", "Example")
        self.run("intake_materials", "clear", self.project)
        r = self.run("intake_materials", "list", self.project)
        assert "0 sources" in r.stdout


# ── taste_memory tests ────────────────────────────────────────────────


class TestTasteMemory:
    @pytest.fixture(autouse=True)
    def setup_home(self, run_script, tmp_path, monkeypatch):
        self.home = str(tmp_path / "fakehome")
        os.makedirs(self.home)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.tmp_path = tmp_path

    def test_empty_taste_memory(self):
        r = self.run("taste_memory", "read")
        assert "No taste memory" in r.stdout

    def test_record_choice_tone(self):
        self.run("taste_memory", "record-choice", "tone", "casual")
        r = self.run("taste_memory", "read")
        assert "casual" in r.stdout

    def test_record_choice_code_density(self):
        self.run("taste_memory", "record-choice", "code_density", "medium")
        r = self.run("taste_memory", "read")
        assert "medium" in r.stdout

    def test_get_preference(self):
        self.run("taste_memory", "record-choice", "tone", "casual")
        r = self.run("taste_memory", "get-preference", "tone")
        assert "casual" in r.stdout

    def test_empty_history(self):
        r = self.run("taste_memory", "history")
        assert "No articles" in r.stdout


class TestTasteMemoryDiffLearn:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        self.home = str(tmp_path / "fakehome")
        os.makedirs(self.home)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.tmp_path = tmp_path

        self.draft_file = str(tmp_path / "draft.md")
        self.edited_file = str(tmp_path / "edited.md")

        with open(self.draft_file, "w") as f:
            f.write("""# Introduction

This is a very long and verbose introduction that goes on and on about the topic at hand.
It contains many unnecessary words and filler content that does not add value.

## Technical Details

The system utilizes a microservices architecture paradigm.
One must consider the implications of distributed computing.

## Conclusion

In conclusion, we have demonstrated the key points.
""")

        with open(self.edited_file, "w") as f:
            f.write("""# Introduction

This intro gets straight to the point.

## Technical Details

The system uses microservices.

## How It Works

Step-by-step breakdown here.

## Conclusion

We covered the key points. Try it yourself.
""")

        self.diff_project = str(tmp_path / "diff-project")
        os.makedirs(self.diff_project)

    def test_diff_learn_shows_deletions(self):
        r = self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        assert "deletion" in r.stdout.lower() or "-" in r.stdout

    def test_diff_learn_shows_additions(self):
        r = self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        assert "addition" in r.stdout.lower() or "+" in r.stdout

    def test_diff_learn_shows_replacements(self):
        r = self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        assert "replacement" in r.stdout.lower() or "~" in r.stdout

    def test_learned_patterns_stored(self):
        self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        taste_path = os.path.join(self.home, ".tech-essay-writer", "taste-memory.json")
        with open(taste_path) as f:
            taste = json.load(f)
        assert "learned_patterns" in json.dumps(taste)
        assert self.diff_project in json.dumps(taste)
        assert "insights" in json.dumps(taste)
        assert "diff_stats" in json.dumps(taste)

    def test_detects_concise_preference(self):
        self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        taste_path = os.path.join(self.home, ".tech-essay-writer", "taste-memory.json")
        with open(taste_path) as f:
            taste_json = f.read()
        assert "concise" in taste_json

    def test_detects_heading_change(self):
        self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        taste_path = os.path.join(self.home, ".tech-essay-writer", "taste-memory.json")
        with open(taste_path) as f:
            taste_json = f.read()
        assert "section" in taste_json

    def test_read_shows_learned_patterns(self):
        self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        r = self.run("taste_memory", "read")
        assert "Learned patterns" in r.stdout

    def test_read_shows_insight(self):
        self.run("taste_memory", "diff-learn", self.diff_project, self.draft_file, self.edited_file)
        r = self.run("taste_memory", "read")
        assert "concise" in r.stdout or "project" in r.stdout

    def test_error_missing_file(self):
        r = self.run("taste_memory", "diff-learn", self.diff_project, "/nonexistent/file", self.edited_file)
        assert "not found" in (r.stdout + r.stderr).lower() or r.returncode != 0


class TestTasteMemoryFeedback:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        self.home = str(tmp_path / "fakehome")
        os.makedirs(self.home)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.project = str(tmp_path / "fb-project")
        os.makedirs(self.project)

    def test_feedback_confirms_recording(self):
        r = self.run("taste_memory", "feedback", self.project, "structure", "shorter paragraphs")
        assert "Feedback recorded" in r.stdout
        assert "structure" in r.stdout

    def test_feedback_stored_in_json(self):
        self.run("taste_memory", "feedback", self.project, "tone", "prefer conversational over formal")
        self.run("taste_memory", "feedback", self.project, "structure", "shorter paragraphs")
        self.run("taste_memory", "feedback", self.project, "vocabulary", "avoid jargon")
        taste_path = os.path.join(self.home, ".tech-essay-writer", "taste-memory.json")
        with open(taste_path) as f:
            taste_json = f.read()
        assert "explicit_preferences" in taste_json
        assert "conversational" in taste_json
        assert "shorter paragraphs" in taste_json
        assert "avoid jargon" in taste_json
        assert '"category"' in taste_json
        assert "timestamp" in taste_json

    def test_read_shows_explicit_preferences(self):
        self.run("taste_memory", "feedback", self.project, "tone", "prefer conversational over formal")
        self.run("taste_memory", "feedback", self.project, "structure", "shorter paragraphs")
        self.run("taste_memory", "feedback", self.project, "vocabulary", "avoid jargon")
        r = self.run("taste_memory", "read")
        assert "Explicit preferences" in r.stdout
        assert "tone" in r.stdout
        assert "structure" in r.stdout
        assert "vocabulary" in r.stdout
        assert "conversational" in r.stdout


# ── aggregate_reviews tests ───────────────────────────────────────────


class TestAggregateReviews:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        self.project = str(tmp_path / "agg-proj")
        state_dir = os.path.join(self.project, ".essay-state")
        os.makedirs(state_dir)
        self.run = run_script

        reviews = {
            "review-technical.json": {
                "reviewer": "technical",
                "rating": "NEEDS_FIXES",
                "summary": "Code examples have issues",
                "issues": [
                    {"severity": "critical", "location": "Section 2", "issue": "Code won't compile", "suggestion": "Fix import"},
                    {"severity": "minor", "location": "Section 4", "issue": "Typo in variable name", "suggestion": "Rename"},
                ],
            },
            "review-editor.json": {
                "reviewer": "editor",
                "rating": "NEEDS_EDITING",
                "summary": "Good content, flow needs work",
                "issues": [
                    {"severity": "major", "location": "Introduction", "issue": "Hook is generic", "suggestion": "Start with the specific problem"},
                ],
            },
            "review-adversarial.json": {
                "reviewer": "adversarial",
                "rating": "VULNERABLE",
                "summary": "Premise is shaky",
                "issues": [
                    {"severity": "major", "issue": "Author generalizes from N=1", "suggestion": "Add more data points"},
                ],
                "attacks": [
                    {"target": "Main thesis", "attack": "Only works for startups", "severity": "significant", "defense": "Add enterprise examples"},
                ],
            },
            "review-audience.json": {
                "reviewer": "audience",
                "rating": "MEH",
                "summary": "Okay but not shareable",
            },
            "review-seo.json": {
                "reviewer": "seo",
                "rating": "NEEDS_WORK",
                "summary": "Title needs work",
                "issues": [
                    {"severity": "minor", "issue": "Title too generic", "suggestion": "Add specific tech name"},
                ],
            },
        }
        for fname, data in reviews.items():
            with open(os.path.join(state_dir, fname), "w") as f:
                json.dump(data, f)

    def test_aggregate_shows_consensus(self):
        r = self.run("aggregate_reviews", self.project)
        assert "NEEDS" in r.stdout

    def test_aggregate_shows_critical(self):
        r = self.run("aggregate_reviews", self.project)
        assert "critical" in r.stdout

    def test_panel_summary_created(self):
        self.run("aggregate_reviews", self.project)
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-panel-summary.json"))

    def test_panel_summary_content(self):
        self.run("aggregate_reviews", self.project)
        with open(os.path.join(self.project, ".essay-state", "review-panel-summary.json")) as f:
            summary = json.load(f)
        assert "ratings" in json.dumps(summary)
        assert "prioritized_actions" in json.dumps(summary)


# ── calibrate_reviews tests ──────────────────────────────────────────


class TestCalibrateReviews:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        self.project = str(tmp_path / "cal-proj")
        state_dir = os.path.join(self.project, ".essay-state")
        os.makedirs(state_dir)
        self.run = run_script

        reviews = {
            "review-technical.json": {
                "reviewer": "technical", "rating": "PASS", "summary": "Looks good",
                "issues": [], "code_issues": [{"code_block": "example 1", "issue": "minor typo"}],
            },
            "review-editor.json": {
                "reviewer": "editor", "rating": "NEEDS_EDITING", "summary": "Needs polish",
                "issues": [{"severity": "major", "issue": "Hook is weak"}],
            },
            "review-adversarial.json": {
                "reviewer": "adversarial", "rating": "WEAK", "summary": "Premise is fundamentally flawed",
                "attacks": [{"target": "thesis", "attack": "No evidence", "severity": "devastating"}],
                "logic_gaps": ["Main argument unsupported"],
                "premise_valid": False, "premise_attack": "Thesis contradicts known results",
            },
            "review-audience.json": {
                "reviewer": "audience", "rating": "WOULD_SHARE", "summary": "Great for target audience",
                "issues": [],
            },
            "review-seo.json": {
                "reviewer": "seo", "rating": "NEEDS_WORK", "summary": "Title needs improvement",
                "title_analysis": {"searchability": 4},
                "social_package": {"hn_title": "test"},
                "issues": [{"severity": "minor", "issue": "Title too generic"}],
            },
            "review-external.json": {
                "reviewer": "external", "rating": "NEEDS_CONTEXT", "summary": "Jargon not explained",
                "jargon_issues": [{"term": "context window", "suggestion": "define it"}],
                "assumed_knowledge": [{"assumption": "knows ML basics"}],
                "issues": [{"severity": "minor", "issue": "Jargon unclear"}],
            },
            "review-factcheck.json": {
                "reviewer": "factcheck", "rating": "VERIFIED", "summary": "Claims check out",
                "claims_checked": 5, "claims_verified": 4,
                "code_verification": [{"code_block": "example", "syntax_valid": True}],
                "issues": [],
            },
        }
        for fname, data in reviews.items():
            with open(os.path.join(state_dir, fname), "w") as f:
                json.dump(data, f)

    def test_calibrate_has_panel_average(self):
        r = self.run("calibrate_reviews", self.project)
        assert "panel_average" in r.stdout

    def test_calibrate_has_agreement_score(self):
        r = self.run("calibrate_reviews", self.project)
        assert "agreement_score" in r.stdout

    def test_cal_file_created(self):
        r = self.run("calibrate_reviews", self.project)
        assert os.path.isfile(os.path.join(self.project, ".essay-state", "review-calibration.json")), \
            f"rc={r.returncode} stdout={r.stdout[:200]}"

    def test_cal_content(self):
        self.run("calibrate_reviews", self.project)
        with open(os.path.join(self.project, ".essay-state", "review-calibration.json")) as f:
            cal = json.load(f)
        cal_str = json.dumps(cal)
        assert "normalized_scores" in cal_str
        assert "outliers" in cal_str
        assert "blind_spots" in cal_str
        assert "agreement_score" in cal_str
        assert "disagreements" in cal_str

    def test_outlier_detection(self):
        self.run("calibrate_reviews", self.project)
        with open(os.path.join(self.project, ".essay-state", "review-calibration.json")) as f:
            cal = json.load(f)
        assert len(cal.get("outliers", [])) >= 1

    def test_adversarial_weak_maps_to_3(self):
        self.run("calibrate_reviews", self.project)
        with open(os.path.join(self.project, ".essay-state", "review-calibration.json")) as f:
            cal = json.load(f)
        assert cal["normalized_scores"]["adversarial"]["numeric_score"] == 3

    def test_audience_would_share_maps_to_8(self):
        self.run("calibrate_reviews", self.project)
        with open(os.path.join(self.project, ".essay-state", "review-calibration.json")) as f:
            cal = json.load(f)
        assert cal["normalized_scores"]["audience"]["numeric_score"] == 8

    def test_empty_project_returns_error(self, tmp_path):
        empty = str(tmp_path / "empty-proj")
        os.makedirs(os.path.join(empty, ".essay-state"))
        r = self.run("calibrate_reviews", empty)
        assert "error" in (r.stdout + r.stderr).lower()
