"""Tests for error handling across all scripts.

Verifies graceful handling of: missing args, corrupt JSON, missing dirs,
empty state, permission issues, invalid inputs, paths with spaces.
"""

import json
import os
import stat

import pytest


# ── pipeline_state.sh: missing arguments ────────────────────────────────


class TestPipelineStateMissingArgs:
    def test_no_command_shows_usage(self, run_script):
        r = run_script("pipeline_state")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_init_with_empty_topic(self, run_script, tmp_path):
        project = str(tmp_path / "test-no-topic")
        os.makedirs(project)
        r = run_script("pipeline_state", "init", project, "")
        assert r.returncode == 0

    def test_set_stage_missing_stage_arg(self, run_script, tmp_path):
        project = str(tmp_path / "test-set-stage")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "")
        r = run_script("pipeline_state", "set-stage", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set-stage requires" in output.lower() or "set-stage" in output

    def test_set_stage_invalid_stage(self, run_script, tmp_path):
        project = str(tmp_path / "test-badstage")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "topic")
        r = run_script("pipeline_state", "set-stage", project, "badstage")
        output = r.stdout + r.stderr
        assert "Invalid stage" in output or "invalid" in output.lower()

    def test_get_field_missing_key(self, run_script, tmp_path):
        project = str(tmp_path / "test-getfield")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "topic")
        r = run_script("pipeline_state", "get-field", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "get-field requires" in output.lower() or "get-field" in output

    def test_set_field_missing_args(self, run_script, tmp_path):
        project = str(tmp_path / "test-setfield")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "topic")
        r = run_script("pipeline_state", "set-field", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set-field requires" in output.lower() or "set-field" in output

    def test_add_review_missing_file_arg(self, run_script, tmp_path):
        project = str(tmp_path / "test-addreview")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "topic")
        r = run_script("pipeline_state", "add-review", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-review requires" in output.lower() or "add-review" in output


# ── pipeline_state.sh: corrupt JSON state ────────────────────────────────


class TestPipelineStateCorruptJSON:
    def test_read_corrupt_state_file(self, run_script, tmp_path):
        project = str(tmp_path / "test-corrupt")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("NOT_JSON{{{")
        r = run_script("pipeline_state", "read", project)
        output = r.stdout + r.stderr
        assert "Corrupt" in output or "WARNING" in output or "{}" in output

    def test_get_stage_with_corrupt_state(self, run_script, tmp_path):
        project = str(tmp_path / "test-corrupt2")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("NOT_JSON{{{")
        r = run_script("pipeline_state", "get-stage", project)
        output = r.stdout + r.stderr
        assert "unknown" in output.lower() or "WARNING" in output


# ── pipeline_state.sh: missing project directory ─────────────────────────


class TestPipelineStateMissingProject:
    def test_init_on_nonexistent_dir(self, run_script, tmp_path):
        project = str(tmp_path / "nonexist" / "deep" / "dir")
        r = run_script("pipeline_state", "init", project, "test topic")
        assert r.returncode == 0

    def test_read_on_nonexistent_project_returns_empty(self, run_script, tmp_path):
        project = str(tmp_path / "totally-missing")
        r = run_script("pipeline_state", "read", project)
        assert r.stdout.strip() == "{}"


# ── pipeline_state.sh: empty state file ──────────────────────────────────


class TestPipelineStateEmptyFile:
    def test_empty_state_file_handled(self, run_script, tmp_path):
        project = str(tmp_path / "test-empty-state")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("")
        r = run_script("pipeline_state", "get-stage", project)
        output = r.stdout + r.stderr
        assert "unknown" in output.lower() or "WARNING" in output or "Corrupt" in output


# ── intake_materials.sh: missing arguments ───────────────────────────────


class TestIntakeMissingArgs:
    def test_no_command_shows_usage(self, run_script):
        r = run_script("intake_materials")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_add_url_missing_url(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-url", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-url requires" in output.lower() or "add-url" in output

    def test_add_note_missing_note(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-note", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-note requires" in output.lower() or "add-note" in output

    def test_add_file_missing_file(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-file", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-file requires" in output.lower() or "add-file" in output

    def test_add_file_nonexistent_file(self, run_script, tmp_path):
        project = str(tmp_path / "test-mat")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        r = run_script("intake_materials", "add-file", project, "/no/such/file.txt")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "File not found" in output or "not found" in output.lower()

    def test_add_code_missing_code(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-code", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-code requires" in output.lower() or "add-code" in output

    def test_add_theme_missing_theme(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-theme", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-theme requires" in output.lower() or "add-theme" in output

    def test_add_angle_missing_angle(self, run_script, tmp_path):
        project = str(tmp_path / "p1")
        r = run_script("intake_materials", "add-angle", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-angle requires" in output.lower() or "add-angle" in output


# ── intake_materials.sh: corrupt materials.json ──────────────────────────


class TestIntakeCorruptMaterials:
    def test_list_with_corrupt_materials(self, run_script, tmp_path):
        project = str(tmp_path / "test-corrupt-mat")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "materials.json"), "w") as f:
            f.write("BROKEN_JSON!!!")
        r = run_script("intake_materials", "list", project)
        output = r.stdout + r.stderr
        # Should not crash -- either warns or falls back
        assert ("WARNING" in output or "Corrupt" in output
                or "Materials" in output or "sources" in output)

    def test_export_with_corrupt_materials(self, run_script, tmp_path):
        project = str(tmp_path / "test-corrupt-mat2")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "materials.json"), "w") as f:
            f.write("BROKEN_JSON!!!")
        r = run_script("intake_materials", "export", project)
        output = r.stdout + r.stderr
        # Should not crash
        assert ("WARNING" in output or "Corrupt" in output
                or "sources" in output or "{" in output)


# ── quality_score.sh: missing state directory ────────────────────────────


class TestQualityScoreErrors:
    def test_missing_state_dir(self, run_script, tmp_path):
        project = str(tmp_path / "no-such-project")
        r = run_script("quality_score", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "State directory not found" in output or "not found" in output.lower()

    def test_missing_project_arg(self, run_script):
        r = run_script("quality_score")
        assert r.returncode != 0

    def test_empty_state_directory_no_reviews(self, run_script, tmp_path):
        project = str(tmp_path / "test-qs")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("quality_score", project)
        output = r.stdout + r.stderr
        assert "NO_REVIEWS" in output

    def test_corrupt_review_file(self, run_script, tmp_path):
        project = str(tmp_path / "test-qs-corrupt")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "review-technical.json"), "w") as f:
            f.write("NOT_JSON")
        r = run_script("quality_score", project, "verbose")
        output = r.stdout + r.stderr
        assert "CORRUPT" in output or "skipped" in output.lower() or "corrupt" in output.lower()


# ── aggregate_reviews.sh: missing args/dir ───────────────────────────────


class TestAggregateReviewsErrors:
    def test_missing_project_arg(self, run_script):
        r = run_script("aggregate_reviews")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "project_dir required" in output.lower() or "required" in output.lower()

    def test_missing_state_directory(self, run_script, tmp_path):
        project = str(tmp_path / "no-project")
        r = run_script("aggregate_reviews", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "State directory not found" in output or "not found" in output.lower()

    def test_empty_state_directory_no_reviews(self, run_script, tmp_path):
        project = str(tmp_path / "test-agg")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("aggregate_reviews", project)
        output = r.stdout + r.stderr
        assert "0" in output or "reviews_count" in output

    def test_corrupt_review_file_in_aggregate(self, run_script, tmp_path):
        project = str(tmp_path / "test-agg-corrupt")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "review-technical.json"), "w") as f:
            f.write("{{BROKEN}}")
        with open(os.path.join(state_dir, "review-editor.json"), "w") as f:
            json.dump({"rating": "PASS", "issues": []}, f)
        r = run_script("aggregate_reviews", project)
        output = r.stdout + r.stderr
        assert "review" in output.lower()


# ── config.sh: missing arguments ─────────────────────────────────────────


class TestConfigMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("config")
        output = r.stdout + r.stderr
        assert "Usage" in output or "init" in output

    def test_get_without_key(self, run_script, fake_home):
        r = run_script("config", "get")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "get requires" in output.lower() or "get" in output

    def test_set_without_args(self, run_script, fake_home):
        r = run_script("config", "set")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set requires" in output.lower() or "set" in output

    def test_set_with_invalid_key(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "set", "bogus_key", "value")
        output = r.stdout + r.stderr
        assert r.returncode != 0 or "Unknown config key" in output or "ERROR" in output

    def test_add_platform_without_platform(self, run_script, fake_home):
        r = run_script("config", "add-platform")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-platform requires" in output.lower() or "add-platform" in output

    def test_add_platform_invalid_platform(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "add-platform", "fakeblog")
        output = r.stdout + r.stderr
        assert r.returncode != 0 or "Invalid platform" in output

    def test_remove_platform_without_arg(self, run_script, fake_home):
        r = run_script("config", "remove-platform")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "remove-platform requires" in output.lower() or "remove-platform" in output

    def test_add_audience_without_arg(self, run_script, fake_home):
        r = run_script("config", "add-audience")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-audience requires" in output.lower() or "add-audience" in output

    def test_remove_audience_without_arg(self, run_script, fake_home):
        r = run_script("config", "remove-audience")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "remove-audience requires" in output.lower() or "remove-audience" in output


# ── cross_reference.sh: missing arguments ────────────────────────────────


class TestCrossReferenceMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("cross_reference")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_add_without_args(self, run_script, fake_home):
        r = run_script("cross_reference", "add")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add requires" in output.lower() or "add" in output

    def test_search_without_query(self, run_script, fake_home):
        r = run_script("cross_reference", "search")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "search requires" in output.lower() or "search" in output

    def test_suggest_without_topic(self, run_script, fake_home):
        r = run_script("cross_reference", "suggest")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "suggest requires" in output.lower() or "suggest" in output

    def test_remove_without_id(self, run_script, fake_home):
        r = run_script("cross_reference", "remove")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "remove requires" in output.lower() or "remove" in output


# ── checkpoint.sh: missing arguments ─────────────────────────────────────


class TestCheckpointMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("checkpoint")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_snapshot_on_missing_state_dir(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "no-project")
        r = run_script("checkpoint", "snapshot", project)
        output = r.stdout + r.stderr
        assert "ERROR" in output or "No" in output

    def test_rollback_missing_checkpoint_id(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "test-ckpt")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("checkpoint", "rollback", project)
        output = r.stdout + r.stderr
        assert "ERROR" in output or "checkpoint_id required" in output.lower() or "required" in output.lower()

    def test_rollback_nonexistent_checkpoint(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "test-ckpt2")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("checkpoint", "rollback", project, "fake-checkpoint-id")
        output = r.stdout + r.stderr
        assert "not found" in output.lower() or "ERROR" in output

    def test_list_with_no_checkpoints(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "test-ckpt3")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("checkpoint", "list", project)
        output = r.stdout + r.stderr
        assert "No checkpoints" in output or "no checkpoint" in output.lower()


# ── series_manager.sh: missing arguments ─────────────────────────────────


class TestSeriesManagerMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("series_manager")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_create_without_args(self, run_script, fake_home):
        r = run_script("series_manager", "create")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "create requires" in output.lower() or "create" in output

    def test_show_without_id(self, run_script, fake_home):
        r = run_script("series_manager", "show")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "show requires" in output.lower() or "show" in output

    def test_context_without_id(self, run_script, fake_home):
        r = run_script("series_manager", "context")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "context requires" in output.lower() or "context" in output

    def test_search_without_query(self, run_script, fake_home):
        r = run_script("series_manager", "search")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "search requires" in output.lower() or "search" in output


# ── analytics_feedback.sh: missing arguments ─────────────────────────────


class TestAnalyticsFeedbackMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("analytics_feedback")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_record_without_args(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "record requires" in output.lower() or "record" in output

    def test_record_invalid_metric(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record", "art-1", "fake_metric", "100")
        output = r.stdout + r.stderr
        assert "Invalid metric" in output or "invalid" in output.lower()

    def test_record_batch_without_args(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record-batch")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "record-batch requires" in output.lower() or "record-batch" in output

    def test_query_without_args(self, run_script, fake_home):
        r = run_script("analytics_feedback", "query")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "query requires" in output.lower() or "query" in output

    def test_compare_without_args(self, run_script, fake_home):
        r = run_script("analytics_feedback", "compare")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "compare requires" in output.lower() or "compare" in output

    def test_feed_taste_without_args(self, run_script, fake_home):
        r = run_script("analytics_feedback", "feed-taste")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "feed-taste requires" in output.lower() or "feed-taste" in output


# ── taste_memory.sh: missing arguments ───────────────────────────────────


class TestTasteMemoryMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("taste_memory")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_update_without_project(self, run_script, fake_home):
        r = run_script("taste_memory", "update")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "update requires" in output.lower() or "update" in output

    def test_record_choice_without_args(self, run_script, fake_home):
        r = run_script("taste_memory", "record-choice")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "record-choice requires" in output.lower() or "record-choice" in output

    def test_get_preference_without_key(self, run_script, fake_home):
        r = run_script("taste_memory", "get-preference")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "get-preference requires" in output.lower() or "get-preference" in output

    def test_feedback_without_args(self, run_script, fake_home):
        r = run_script("taste_memory", "feedback")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "feedback requires" in output.lower() or "feedback" in output

    def test_feedback_invalid_category(self, run_script, tmp_path, fake_home):
        project = str(tmp_path / "taste-proj")
        r = run_script("taste_memory", "feedback", project, "invalid_cat", "some text")
        output = r.stdout + r.stderr
        assert "invalid category" in output.lower() or "Error" in output or "error" in output.lower()

    def test_suggest_without_project(self, run_script, fake_home):
        r = run_script("taste_memory", "suggest")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "suggest requires" in output.lower() or "suggest" in output


# ── author_profile.sh: missing arguments ─────────────────────────────────


class TestAuthorProfileMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("author_profile")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_set_without_args(self, run_script, fake_home):
        r = run_script("author_profile", "set")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set requires" in output.lower() or "set" in output

    def test_set_invalid_field(self, run_script, fake_home):
        r = run_script("author_profile", "set", "badfield", "val")
        output = r.stdout + r.stderr
        assert "Invalid field" in output or "invalid" in output.lower()

    def test_set_social_without_args(self, run_script, fake_home):
        r = run_script("author_profile", "set-social")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set-social requires" in output.lower() or "set-social" in output

    def test_add_expertise_without_args(self, run_script, fake_home):
        r = run_script("author_profile", "add-expertise")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "add-expertise requires" in output.lower() or "add-expertise" in output

    def test_add_expertise_invalid_level(self, run_script, fake_home):
        r = run_script("author_profile", "add-expertise", "Python", "godlike")
        output = r.stdout + r.stderr
        assert "Invalid level" in output or "invalid" in output.lower()

    def test_remove_expertise_without_topic(self, run_script, fake_home):
        r = run_script("author_profile", "remove-expertise")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "remove-expertise requires" in output.lower() or "remove-expertise" in output

    def test_set_voice_without_description(self, run_script, fake_home):
        r = run_script("author_profile", "set-voice")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "set-voice requires" in output.lower() or "set-voice" in output


# ── expertise_graph.sh: missing arguments ────────────────────────────────


class TestExpertiseGraphMissingArgs:
    def test_no_command_shows_usage(self, run_script, fake_home):
        r = run_script("expertise_graph")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_update_without_topic(self, run_script, fake_home):
        r = run_script("expertise_graph", "update")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "update requires" in output.lower() or "update" in output

    def test_query_without_topic(self, run_script, fake_home):
        r = run_script("expertise_graph", "query")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "query requires" in output.lower() or "query" in output


# ── calibrate_reviews.sh: error handling ─────────────────────────────────


class TestCalibrateReviewsErrors:
    def test_missing_project_arg(self, run_script):
        r = run_script("calibrate_reviews")
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "project_dir required" in output.lower() or "required" in output.lower()

    def test_missing_state_directory(self, run_script, tmp_path):
        project = str(tmp_path / "no-project")
        r = run_script("calibrate_reviews", project)
        assert r.returncode != 0
        output = r.stdout + r.stderr
        assert "State directory not found" in output or "not found" in output.lower()

    def test_empty_state_directory(self, run_script, tmp_path):
        project = str(tmp_path / "test-cal-empty")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("calibrate_reviews", project)
        output = r.stdout + r.stderr
        assert "No review" in output or "error" in output.lower() or "no review" in output.lower()


# ── code_validate.sh: error handling ─────────────────────────────────────


class TestCodeValidateErrors:
    def test_no_file_arg(self, run_script):
        r = run_script("code_validate")
        output = r.stdout + r.stderr
        assert ("error" in output.lower() or "no file" in output.lower()
                or "Usage" in output)

    def test_nonexistent_file(self, run_script):
        r = run_script("code_validate", "/tmp/no-such-file-1234.md")
        output = r.stdout + r.stderr
        assert "file not found" in output.lower() or "error" in output.lower()

    def test_empty_markdown_file(self, run_script, tmp_path):
        empty_md = str(tmp_path / "empty.md")
        with open(empty_md, "w") as f:
            f.write("")
        r = run_script("code_validate", empty_md)
        output = r.stdout + r.stderr
        assert "total_blocks" in output


# ── diagram_suggest.sh: error handling ───────────────────────────────────


class TestDiagramSuggestErrors:
    def test_no_file_arg(self, run_script):
        r = run_script("diagram_suggest")
        output = r.stdout + r.stderr
        assert "Usage" in output

    def test_nonexistent_file(self, run_script):
        r = run_script("diagram_suggest", "/tmp/no-such-file-5678.md")
        output = r.stdout + r.stderr
        assert "file not found" in output.lower() or "error" in output.lower()


# ── detect_input.sh: error handling ──────────────────────────────────────


class TestDetectInputErrors:
    def test_no_text_arg(self, run_script):
        r = run_script("detect_input")
        assert r.returncode != 0

    def test_short_text(self, run_script):
        r = run_script("detect_input", "hi")
        output = r.stdout + r.stderr
        assert "item_count" in output


# ── publish_check.sh: error handling ─────────────────────────────────────


class TestPublishCheckErrors:
    def test_missing_project_arg(self, run_script):
        r = run_script("publish_check")
        assert r.returncode != 0

    def test_nonexistent_project(self, run_script, tmp_path):
        project = str(tmp_path / "no-project")
        r = run_script("publish_check", project)
        output = r.stdout + r.stderr
        # Should get check failures not crashes
        assert "FAIL" in output or "Fail" in output or "NOT READY" in output


# ── publishing_guide.sh: error handling ──────────────────────────────────


class TestPublishingGuideErrors:
    def test_missing_platform_arg(self, run_script):
        r = run_script("publishing_guide")
        assert r.returncode != 0

    def test_invalid_platform(self, run_script):
        r = run_script("publishing_guide", "fakplatform")
        output = r.stdout + r.stderr
        assert "Invalid platform" in output or "ERROR" in output

    def test_valid_platform_with_missing_project(self, run_script):
        r = run_script("publishing_guide", "medium")
        output = r.stdout + r.stderr
        assert "Medium" in output or "Steps" in output or "steps" in output


# ── permission issues ────────────────────────────────────────────────────


class TestPermissionIssues:
    def test_write_to_readonly_state_directory(self, run_script, tmp_path):
        project = str(tmp_path / "test-readonly")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        run_script("pipeline_state", "init", project, "test topic")
        # Make state dir read-only
        os.chmod(state_dir, stat.S_IRUSR | stat.S_IXUSR)
        try:
            r = run_script("pipeline_state", "set-stage", project, "research")
            assert r.returncode != 0
        finally:
            # Restore permissions so cleanup works
            os.chmod(state_dir, stat.S_IRWXU)

    def test_write_materials_to_readonly_dir(self, run_script, tmp_path):
        project = str(tmp_path / "test-readonly-mat")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        run_script("intake_materials", "init", project)
        # Make state dir read-only
        os.chmod(state_dir, stat.S_IRUSR | stat.S_IXUSR)
        try:
            r = run_script("intake_materials", "add-note", project, "test note")
            assert r.returncode != 0
        finally:
            # Restore permissions so cleanup works
            os.chmod(state_dir, stat.S_IRWXU)


# ── paths with spaces ───────────────────────────────────────────────────


class TestPathsWithSpaces:
    def test_pipeline_state_init_with_spaces(self, run_script, tmp_path):
        project = str(tmp_path / "my project dir")
        os.makedirs(project)
        r = run_script("pipeline_state", "init", project, "test topic")
        assert r.returncode == 0

    def test_get_stage_with_spaces(self, run_script, tmp_path):
        project = str(tmp_path / "my project dir2")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "test topic")
        r = run_script("pipeline_state", "get-stage", project)
        assert r.stdout.strip() == "intake"

    def test_intake_init_with_spaces(self, run_script, tmp_path):
        project = str(tmp_path / "my project dir3")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "test topic")
        r = run_script("intake_materials", "init", project)
        assert r.returncode == 0

    def test_add_note_with_spaces(self, run_script, tmp_path):
        project = str(tmp_path / "my project dir4")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "test topic")
        run_script("intake_materials", "init", project)
        r = run_script("intake_materials", "add-note", project, "a note")
        assert r.returncode == 0


# ── update_material.sh: error handling ───────────────────────────────────


class TestUpdateMaterialErrors:
    def test_missing_args(self, run_script):
        r = run_script("update_material")
        assert r.returncode != 0

    def test_missing_materials_json(self, run_script, tmp_path):
        project = str(tmp_path / "test-upd")
        os.makedirs(os.path.join(project, ".essay-state"))
        r = run_script("update_material", project, "src-123", "content")
        output = r.stdout + r.stderr
        assert "No materials.json" in output or "not found" in output.lower()

    def test_nonexistent_source_id(self, run_script, tmp_path):
        project = str(tmp_path / "test-upd2")
        os.makedirs(os.path.join(project, ".essay-state"))
        run_script("intake_materials", "init", project)
        r = run_script("update_material", project, "src-nonexist", "content")
        output = r.stdout + r.stderr
        assert "not found" in output.lower()


# ── fetch_urls.sh: error handling ────────────────────────────────────────


class TestFetchUrlsErrors:
    def test_missing_project_arg(self, run_script):
        r = run_script("fetch_urls")
        assert r.returncode != 0

    def test_missing_materials_file(self, run_script, tmp_path):
        project = str(tmp_path / "no-project")
        r = run_script("fetch_urls", project)
        output = r.stdout + r.stderr
        assert "No materials.json" in output or "not found" in output.lower()


# ── orchestrate.sh: missing required args ────────────────────────────────


class TestOrchestrateMissingArgs:
    def test_no_args(self, run_script):
        r = run_script("orchestrate")
        assert r.returncode != 0

    def test_missing_skill_dir(self, run_script, tmp_path):
        r = run_script("orchestrate", str(tmp_path))
        assert r.returncode != 0

    def test_missing_command(self, run_script, tmp_path, script_dir):
        r = run_script("orchestrate", str(tmp_path), script_dir)
        assert r.returncode != 0

    def test_invalid_command(self, run_script, tmp_path, script_dir):
        r = run_script("orchestrate", str(tmp_path), script_dir, "bogus_cmd")
        output = r.stdout + r.stderr
        assert "Usage" in output or "Unknown" in output or "usage" in output.lower()

    def test_status_on_uninitialized_project(self, run_script, tmp_path, script_dir):
        project = str(tmp_path / "fresh")
        r = run_script("orchestrate", project, script_dir, "status")
        output = r.stdout + r.stderr
        assert "NOT_INITIALIZED" in output or "not_initialized" in output.lower()

    def test_next_stage_on_uninitialized(self, run_script, tmp_path, script_dir):
        project = str(tmp_path / "fresh2")
        r = run_script("orchestrate", project, script_dir, "next-stage")
        assert r.stdout.strip() == "intake"

    def test_resume_on_uninitialized(self, run_script, tmp_path, script_dir):
        project = str(tmp_path / "fresh3")
        r = run_script("orchestrate", project, script_dir, "resume")
        output = r.stdout + r.stderr
        assert "not_initialized" in output.lower() or "intake" in output


# ── progress_display.sh: error handling ──────────────────────────────────


class TestProgressDisplayErrors:
    def test_missing_project_arg(self, run_script):
        r = run_script("progress_display")
        assert r.returncode != 0

    def test_uninitialized_project(self, run_script, tmp_path):
        project = str(tmp_path / "no-init")
        r = run_script("progress_display", project)
        output = r.stdout + r.stderr
        assert "not initialized" in output.lower() or "not_initialized" in output.lower()

    def test_invalid_format_flag(self, run_script, tmp_path):
        project = str(tmp_path / "no-init2")
        r = run_script("progress_display", project, "--format", "xml")
        output = r.stdout + r.stderr
        assert "ERROR" in output or "format must be" in output.lower() or "error" in output.lower()

    def test_corrupt_pipeline_state_for_progress(self, run_script, tmp_path):
        project = str(tmp_path / "test-prog-corrupt")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            f.write("{{{BROKEN")
        r = run_script("progress_display", project)
        output = r.stdout + r.stderr
        assert ("ERROR" in output or "corrupt" in output.lower()
                or "Cannot read" in output)
