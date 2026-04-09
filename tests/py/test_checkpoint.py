"""Tests for checkpoint.py, pipeline_state auto-snapshot, and orchestrate retry/resume."""

import json
import os
import time

import pytest


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


def get_checkpoint_dir(project, label_prefix):
    """Get the first checkpoint dir matching a label prefix."""
    ckpt_base = os.path.join(project, ".essay-state", "checkpoints")
    for d in sorted(os.listdir(ckpt_base)):
        if d.startswith(label_prefix + "-") and os.path.isdir(os.path.join(ckpt_base, d)):
            return os.path.join(ckpt_base, d)
    return None


def setup_project(run_script, tmp_path, name, topic="Test Topic"):
    """Create a test project with initialized pipeline."""
    project = str(tmp_path / name)
    os.makedirs(project)
    run_script("pipeline_state", "init", project, topic)
    return project


# ── checkpoint snapshot tests ─────────────────────────────────────────


class TestCheckpointSnapshot:
    def test_snapshot_creates_checkpoint(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap1")
        r = run_script("checkpoint", "snapshot", p)
        assert "Checkpoint:" in r.stdout
        assert os.path.isdir(os.path.join(p, ".essay-state", "checkpoints"))
        assert count_checkpoints(p) == 1

    def test_snapshot_with_label(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap2")
        r = run_script("checkpoint", "snapshot", p, "my-label")
        assert "my-label" in r.stdout

    def test_snapshot_uses_stage_as_label(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap3")
        r = run_script("checkpoint", "snapshot", p)
        assert "intake" in r.stdout

    def test_snapshot_copies_state(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap4")
        run_script("checkpoint", "snapshot", p, "test")
        ckpt = get_checkpoint_dir(p, "test")
        assert ckpt is not None
        assert os.path.isfile(os.path.join(ckpt, "pipeline-state.json"))

    def test_snapshot_no_nested_checkpoints(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap5")
        run_script("checkpoint", "snapshot", p, "first")
        run_script("checkpoint", "snapshot", p, "second")
        ckpt = get_checkpoint_dir(p, "second")
        assert not os.path.isdir(os.path.join(ckpt, "checkpoints"))

    def test_snapshot_no_state_dir_errors(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "snap6")
        os.makedirs(p)
        r = run_script("checkpoint", "snapshot", p)
        assert r.returncode != 0

    def test_snapshot_empty_state_dir_errors(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "snap7")
        os.makedirs(os.path.join(p, ".essay-state"))
        r = run_script("checkpoint", "snapshot", p)
        assert r.returncode != 0

    def test_multiple_snapshots(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap8")
        run_script("checkpoint", "snapshot", p, "a")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "b")
        assert count_checkpoints(p) == 2

    def test_snapshot_preserves_contents(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap9")
        extra_path = os.path.join(p, ".essay-state", "extra.json")
        with open(extra_path, "w") as f:
            json.dump({"extra": "data"}, f)
        with open(os.path.join(p, ".essay-state", "pipeline-state.json")) as f:
            original_state = f.read()
        with open(extra_path) as f:
            original_extra = f.read()
        run_script("checkpoint", "snapshot", p, "preserve")
        ckpt = get_checkpoint_dir(p, "preserve")
        with open(os.path.join(ckpt, "pipeline-state.json")) as f:
            assert f.read() == original_state
        with open(os.path.join(ckpt, "extra.json")) as f:
            assert f.read() == original_extra

    def test_snapshot_output_file_count(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "snap10")
        with open(os.path.join(p, ".essay-state", "materials.json"), "w") as f:
            json.dump({"test": True}, f)
        r = run_script("checkpoint", "snapshot", p, "count")
        assert "2 files" in r.stdout


# ── checkpoint list tests ─────────────────────────────────────────────


class TestCheckpointList:
    def test_list_no_checkpoints_dir(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "list1")
        os.makedirs(os.path.join(p, ".essay-state"))
        r = run_script("checkpoint", "list", p)
        assert "No checkpoints" in r.stdout

    def test_list_empty_checkpoints(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "list2")
        os.makedirs(os.path.join(p, ".essay-state", "checkpoints"))
        r = run_script("checkpoint", "list", p)
        assert "No checkpoints" in r.stdout

    def test_list_one_checkpoint(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "list3")
        run_script("checkpoint", "snapshot", p, "test")
        r = run_script("checkpoint", "list", p)
        assert "1 checkpoint" in r.stdout
        assert "label:test" in r.stdout

    def test_list_multiple(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "list4")
        run_script("checkpoint", "snapshot", p, "first")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "second")
        r = run_script("checkpoint", "list", p)
        assert "2 checkpoint" in r.stdout
        assert "label:first" in r.stdout
        assert "label:second" in r.stdout

    def test_list_shows_stage(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "list5")
        run_script("checkpoint", "snapshot", p, "test")
        r = run_script("checkpoint", "list", p)
        assert "[intake]" in r.stdout

    def test_list_shows_file_count(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "list6")
        run_script("checkpoint", "snapshot", p, "test")
        r = run_script("checkpoint", "list", p)
        assert "files" in r.stdout


# ── checkpoint rollback tests ─────────────────────────────────────────


class TestCheckpointRollback:
    def test_rollback_restores_state(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb1")
        with open(os.path.join(p, ".essay-state", "pipeline-state.json")) as f:
            original = f.read()
        run_script("checkpoint", "snapshot", p, "before")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("before-")][0]
        # Modify state
        state_path = os.path.join(p, ".essay-state", "pipeline-state.json")
        with open(state_path) as f:
            data = json.load(f)
        data["topic"] = "Modified"
        with open(state_path, "w") as f:
            json.dump(data, f)
        run_script("checkpoint", "rollback", p, ckpt_id)
        with open(state_path) as f:
            assert f.read() == original

    def test_rollback_removes_new_files(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb2")
        run_script("checkpoint", "snapshot", p, "clean")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("clean-")][0]
        new_file = os.path.join(p, ".essay-state", "review-technical.json")
        with open(new_file, "w") as f:
            json.dump({"new": True}, f)
        assert os.path.isfile(new_file)
        run_script("checkpoint", "rollback", p, ckpt_id)
        assert not os.path.isfile(new_file)

    def test_rollback_preserves_checkpoints_dir(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb3")
        run_script("checkpoint", "snapshot", p, "keep")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("keep-")][0]
        run_script("checkpoint", "rollback", p, ckpt_id)
        assert os.path.isdir(os.path.join(p, ".essay-state", "checkpoints"))
        assert count_checkpoints(p) == 1

    def test_rollback_invalid_id(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb4")
        r = run_script("checkpoint", "rollback", p, "nonexistent")
        assert r.returncode != 0

    def test_rollback_empty_id(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb5")
        r = run_script("checkpoint", "rollback", p, "")
        assert r.returncode != 0

    def test_rollback_restores_deleted_file(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb6")
        mat_path = os.path.join(p, ".essay-state", "materials.json")
        with open(mat_path, "w") as f:
            json.dump({"materials": True}, f)
        run_script("checkpoint", "snapshot", p, "with-mats")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("with-mats-")][0]
        os.remove(mat_path)
        assert not os.path.isfile(mat_path)
        run_script("checkpoint", "rollback", p, ckpt_id)
        assert os.path.isfile(mat_path)

    def test_rollback_output_files_restored(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "rb7")
        run_script("checkpoint", "snapshot", p, "test")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("test-")][0]
        r = run_script("checkpoint", "rollback", p, ckpt_id)
        assert "files restored" in r.stdout


# ── checkpoint latest tests ───────────────────────────────────────────


class TestCheckpointLatest:
    def test_latest_no_checkpoints(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "lat1")
        os.makedirs(os.path.join(p, ".essay-state"))
        r = run_script("checkpoint", "latest", p)
        assert "No checkpoints" in r.stdout or r.returncode != 0

    def test_latest_one_checkpoint(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "lat2")
        run_script("checkpoint", "snapshot", p, "only")
        r = run_script("checkpoint", "latest", p)
        assert "label:only" in r.stdout

    def test_latest_multiple_shows_newest(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "lat3")
        run_script("checkpoint", "snapshot", p, "older")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "newer")
        r = run_script("checkpoint", "latest", p)
        assert "label:newer" in r.stdout

    def test_latest_shows_stage_and_files(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "lat4")
        run_script("checkpoint", "snapshot", p, "stage-check")
        r = run_script("checkpoint", "latest", p)
        assert "[intake]" in r.stdout
        assert "files" in r.stdout


# ── checkpoint clean tests ────────────────────────────────────────────


class TestCheckpointClean:
    def test_clean_empty(self, run_script, tmp_path, fake_home):
        p = str(tmp_path / "cln1")
        os.makedirs(os.path.join(p, ".essay-state"))
        r = run_script("checkpoint", "clean", p)
        assert "No checkpoints" in r.stdout

    def test_clean_keeps_all_below_threshold(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "cln2")
        run_script("checkpoint", "snapshot", p, "a")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "b")
        r = run_script("checkpoint", "clean", p, "--keep", "5")
        assert "keeping all" in r.stdout
        assert count_checkpoints(p) == 2

    def test_clean_removes_oldest(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "cln3")
        for label in ["a", "b", "c", "d", "e", "f"]:
            run_script("checkpoint", "snapshot", p, label)
            time.sleep(1)
        assert count_checkpoints(p) == 6
        r = run_script("checkpoint", "clean", p, "--keep", "3")
        assert "Cleaned 3" in r.stdout
        assert count_checkpoints(p) == 3

    def test_clean_keep_1(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "cln4")
        run_script("checkpoint", "snapshot", p, "a")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "b")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "c")
        run_script("checkpoint", "clean", p, "--keep", "1")
        assert count_checkpoints(p) == 1

    def test_clean_default_keep_5(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "cln5")
        for label in ["a", "b", "c", "d", "e", "f", "g"]:
            run_script("checkpoint", "snapshot", p, label)
            time.sleep(1)
        run_script("checkpoint", "clean", p)
        assert count_checkpoints(p) == 5

    def test_clean_keep_0(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "cln6")
        run_script("checkpoint", "snapshot", p, "a")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "b")
        run_script("checkpoint", "clean", p, "--keep", "0")
        assert count_checkpoints(p) == 0


# ── pipeline_state auto-snapshot ──────────────────────────────────────


class TestAutoSnapshot:
    def test_set_stage_creates_checkpoint(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "auto1")
        run_script("pipeline_state", "set-stage", p, "research")
        assert count_checkpoints(p) == 1

    def test_auto_checkpoint_label_is_pre_stage(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "auto2")
        run_script("pipeline_state", "set-stage", p, "research")
        r = run_script("checkpoint", "list", p)
        assert "label:intake" in r.stdout

    def test_auto_checkpoint_has_pre_transition_stage(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "auto3")
        run_script("pipeline_state", "set-stage", p, "research")
        ckpt = get_checkpoint_dir(p, "intake")
        assert ckpt is not None
        with open(os.path.join(ckpt, "pipeline-state.json")) as f:
            data = json.load(f)
        assert data.get("stage") == "intake"

    def test_multiple_transitions(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "auto4")
        run_script("pipeline_state", "set-stage", p, "research")
        run_script("pipeline_state", "set-stage", p, "outline")
        run_script("pipeline_state", "set-stage", p, "draft")
        assert count_checkpoints(p) == 3

    def test_set_stage_still_works(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "auto5")
        run_script("pipeline_state", "set-stage", p, "research")
        r = run_script("pipeline_state", "get-stage", p)
        assert r.stdout.strip() == "research"


# ── orchestrate retry-stage tests ─────────────────────────────────────


class TestRetryStage:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch, script_dir):
        self.home = str(tmp_path / "fakehome")
        os.makedirs(self.home, exist_ok=True)
        os.makedirs(os.path.join(self.home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.tmp_path = tmp_path
        self.sd = script_dir

    def _setup(self, name, topic="Test Topic"):
        return setup_project(self.run, self.tmp_path, name, topic)

    def test_retry_review_clears_files(self):
        p = self._setup("retry1")
        self.run("pipeline_state", "set-field", p, "stage", "review")
        state_dir = os.path.join(p, ".essay-state")
        for f in ["review-technical.json", "review-editor.json", "review-panel-summary.json"]:
            with open(os.path.join(state_dir, f), "w") as fh:
                json.dump({"reviewer": "test"}, fh)
        self.run("orchestrate", p, self.sd, "retry-stage", "review")
        assert not os.path.isfile(os.path.join(state_dir, "review-technical.json"))
        assert not os.path.isfile(os.path.join(state_dir, "review-editor.json"))
        assert not os.path.isfile(os.path.join(state_dir, "review-panel-summary.json"))

    def test_retry_sets_stage(self):
        p = self._setup("retry2")
        self.run("pipeline_state", "set-field", p, "stage", "refinement")
        self.run("orchestrate", p, self.sd, "retry-stage", "review")
        r = self.run("pipeline_state", "get-stage", p)
        assert r.stdout.strip() == "review"

    def test_retry_review_resets_tracking(self):
        p = self._setup("retry3")
        self.run("pipeline_state", "set-field", p, "stage", "review")
        self.run("pipeline_state", "set-field", p, "reviews", '{"technical":{"rating":"PASS"}}')
        self.run("pipeline_state", "set-field", p, "review_panel_complete", "true")
        self.run("orchestrate", p, self.sd, "retry-stage", "review")
        r = self.run("pipeline_state", "get-field", p, "reviews")
        assert r.stdout.strip() == "{}"
        r = self.run("pipeline_state", "get-field", p, "review_panel_complete")
        assert r.stdout.strip() == "false"

    def test_retry_draft_clears_drafts(self):
        p = self._setup("retry4")
        self.run("pipeline_state", "set-field", p, "stage", "draft")
        state_dir = os.path.join(p, ".essay-state")
        for v in ["draft-v1.md", "draft-v2.md"]:
            with open(os.path.join(state_dir, v), "w") as f:
                f.write(f"# {v}")
        self.run("orchestrate", p, self.sd, "retry-stage", "draft")
        assert not os.path.isfile(os.path.join(state_dir, "draft-v1.md"))
        assert not os.path.isfile(os.path.join(state_dir, "draft-v2.md"))

    def test_retry_outline_clears_outlines(self):
        p = self._setup("retry5")
        self.run("pipeline_state", "set-field", p, "stage", "outline")
        state_dir = os.path.join(p, ".essay-state")
        for f in ["outline-A.json", "outline-B.json", "outline-critique.json"]:
            with open(os.path.join(state_dir, f), "w") as fh:
                json.dump({"outline": True}, fh)
        self.run("orchestrate", p, self.sd, "retry-stage", "outline")
        assert not os.path.isfile(os.path.join(state_dir, "outline-A.json"))
        assert not os.path.isfile(os.path.join(state_dir, "outline-B.json"))
        assert not os.path.isfile(os.path.join(state_dir, "outline-critique.json"))

    def test_retry_research_clears_synthesis(self):
        p = self._setup("retry6")
        self.run("pipeline_state", "set-field", p, "stage", "research")
        with open(os.path.join(p, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump({"thesis": "test"}, f)
        self.run("orchestrate", p, self.sd, "retry-stage", "research")
        assert not os.path.isfile(os.path.join(p, ".essay-state", "research-synthesis.json"))

    def test_retry_refinement_keeps_v1(self):
        p = self._setup("retry7")
        self.run("pipeline_state", "set-field", p, "stage", "refinement")
        state_dir = os.path.join(p, ".essay-state")
        for v in ["draft-v1.md", "draft-v2.md", "draft-v3.md"]:
            with open(os.path.join(state_dir, v), "w") as f:
                f.write(f"# {v}")
        for f in ["refinement-1-changes.json", "refinement-2-changes.json"]:
            with open(os.path.join(state_dir, f), "w") as fh:
                json.dump({"changes": []}, fh)
        self.run("orchestrate", p, self.sd, "retry-stage", "refinement")
        assert os.path.isfile(os.path.join(state_dir, "draft-v1.md"))
        assert not os.path.isfile(os.path.join(state_dir, "draft-v2.md"))
        assert not os.path.isfile(os.path.join(state_dir, "draft-v3.md"))
        assert not os.path.isfile(os.path.join(state_dir, "refinement-1-changes.json"))

    def test_retry_polish_clears_finals(self):
        p = self._setup("retry8")
        self.run("pipeline_state", "set-field", p, "stage", "polish")
        state_dir = os.path.join(p, ".essay-state")
        files = ["final-internal.md", "final-external.md", "social-package.json",
                 "influence-score.json", "seo-metadata.json", "diagram-suggestions.json"]
        for fn in files:
            with open(os.path.join(state_dir, fn), "w") as f:
                f.write("{}" if fn.endswith(".json") else "# Content")
        self.run("orchestrate", p, self.sd, "retry-stage", "polish")
        for fn in files:
            assert not os.path.isfile(os.path.join(state_dir, fn))

    def test_retry_intake_clears_materials(self):
        p = self._setup("retry9")
        with open(os.path.join(p, ".essay-state", "materials.json"), "w") as f:
            json.dump({"sources": []}, f)
        self.run("orchestrate", p, self.sd, "retry-stage", "intake")
        assert not os.path.isfile(os.path.join(p, ".essay-state", "materials.json"))

    def test_retry_invalid_stage(self):
        p = self._setup("retry10")
        r = self.run("orchestrate", p, self.sd, "retry-stage", "invalid")
        assert r.returncode != 0

    def test_retry_complete_errors(self):
        p = self._setup("retry11")
        r = self.run("orchestrate", p, self.sd, "retry-stage", "complete")
        assert r.returncode != 0

    def test_retry_with_checkpoint_rollback(self):
        p = self._setup("retry-rb1")
        self.run("pipeline_state", "set-stage", p, "research")
        with open(os.path.join(p, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump({"thesis": "original"}, f)
        self.run("pipeline_state", "set-stage", p, "outline")
        with open(os.path.join(p, ".essay-state", "outline-A.json"), "w") as f:
            json.dump({"outline": "A"}, f)
        self.run("pipeline_state", "set-stage", p, "draft")
        with open(os.path.join(p, ".essay-state", "draft-v1.md"), "w") as f:
            f.write("# Draft")
        self.run("pipeline_state", "set-stage", p, "review")
        with open(os.path.join(p, ".essay-state", "review-technical.json"), "w") as f:
            json.dump({"reviewer": "technical"}, f)
        r = self.run("orchestrate", p, self.sd, "retry-stage", "review")
        assert "Rolling back" in r.stdout
        assert os.path.isfile(os.path.join(p, ".essay-state", "pipeline-state.json"))

    def test_retry_without_checkpoint(self):
        p = self._setup("retry-norb")
        self.run("pipeline_state", "set-field", p, "stage", "review")
        with open(os.path.join(p, ".essay-state", "review-editor.json"), "w") as f:
            json.dump({"reviewer": "editor"}, f)
        r = self.run("orchestrate", p, self.sd, "retry-stage", "review")
        assert "No checkpoint" in r.stdout
        assert not os.path.isfile(os.path.join(p, ".essay-state", "review-editor.json"))
        r2 = self.run("pipeline_state", "get-stage", p)
        assert r2.stdout.strip() == "review"

    def test_retry_refinement_resets_round(self):
        p = self._setup("retry-round")
        self.run("pipeline_state", "set-field", p, "stage", "refinement")
        self.run("pipeline_state", "set-field", p, "refinement_round", "2")
        self.run("orchestrate", p, self.sd, "retry-stage", "refinement")
        r = self.run("pipeline_state", "get-field", p, "refinement_round")
        assert r.stdout.strip() == "0"


# ── orchestrate resume tests ─────────────────────────────────────────


class TestResume:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch, script_dir):
        self.home = str(tmp_path / "fakehome")
        os.makedirs(self.home, exist_ok=True)
        os.makedirs(os.path.join(self.home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.tmp_path = tmp_path
        self.sd = script_dir

    def _setup(self, name, topic="Test Topic"):
        return setup_project(self.run, self.tmp_path, name, topic)

    def test_resume_no_pipeline(self):
        p = str(self.tmp_path / "resume1")
        os.makedirs(os.path.join(p, ".essay-state"))
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "not_initialized" in r.stdout

    def test_resume_intake_no_materials(self):
        p = self._setup("resume2")
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "STATUS: intake" in r.stdout
        assert "ACTION:" in r.stdout

    def test_resume_intake_with_materials(self):
        p = self._setup("resume3")
        with open(os.path.join(p, ".essay-state", "materials.json"), "w") as f:
            json.dump({"source_count": 2, "sources": [{"type": "url"}, {"type": "note"}]}, f)
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "2 material" in r.stdout

    def test_resume_research_not_started(self):
        p = self._setup("resume4")
        self.run("pipeline_state", "set-stage", p, "research")
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "STATUS: research" in r.stdout
        assert "not started" in r.stdout

    def test_resume_research_done(self):
        p = self._setup("resume5")
        self.run("pipeline_state", "set-stage", p, "research")
        with open(os.path.join(p, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump({"thesis": "test"}, f)
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "complete" in r.stdout
        assert "outline" in r.stdout

    def test_resume_outline_partial(self):
        p = self._setup("resume6")
        self.run("pipeline_state", "set-stage", p, "outline")
        with open(os.path.join(p, ".essay-state", "outline-A.json"), "w") as f:
            json.dump({"outline": "A"}, f)
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "1/3" in r.stdout

    def test_resume_review_partial(self):
        p = self._setup("resume7")
        self.run("pipeline_state", "set-stage", p, "review")
        state_dir = os.path.join(p, ".essay-state")
        for name in ["technical", "editor", "seo"]:
            with open(os.path.join(state_dir, f"review-{name}.json"), "w") as f:
                json.dump({"reviewer": name}, f)
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "3/7" in r.stdout
        assert "MISSING" in r.stdout

    def test_resume_refinement(self):
        p = self._setup("resume8")
        self.run("pipeline_state", "set-stage", p, "refinement")
        self.run("pipeline_state", "set-field", p, "refinement_round", "1")
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "Round 1" in r.stdout

    def test_resume_polish_partial(self):
        p = self._setup("resume9")
        self.run("pipeline_state", "set-stage", p, "polish")
        with open(os.path.join(p, ".essay-state", "final-internal.md"), "w") as f:
            f.write("# Internal")
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "STATUS: polish" in r.stdout
        assert "internal=True" in r.stdout

    def test_resume_complete(self):
        p = self._setup("resume10")
        self.run("pipeline_state", "complete", p)
        r = self.run("orchestrate", p, self.sd, "resume")
        assert "STATUS: complete" in r.stdout


# ── orchestrate delegation tests ──────────────────────────────────────


class TestDelegation:
    def test_list_checkpoints(self, run_script, tmp_path, fake_home, script_dir):
        p = setup_project(run_script, tmp_path, "deleg1")
        run_script("checkpoint", "snapshot", p, "test-deleg")
        r = run_script("orchestrate", p, script_dir, "list-checkpoints")
        assert "test-deleg" in r.stdout

    def test_rollback_via_orchestrate(self, run_script, tmp_path, fake_home, script_dir):
        p = setup_project(run_script, tmp_path, "deleg2")
        run_script("checkpoint", "snapshot", p, "snap")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("snap-")][0]
        with open(os.path.join(p, ".essay-state", "extra-file.json"), "w") as f:
            json.dump({"extra": True}, f)
        run_script("orchestrate", p, script_dir, "rollback", ckpt_id)
        assert not os.path.isfile(os.path.join(p, ".essay-state", "extra-file.json"))


# ── edge case tests ──────────────────────────────────────────────────


class TestEdgeCases:
    def test_snapshot_rollback_snapshot_cycle(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "edge1")
        run_script("checkpoint", "snapshot", p, "first")
        ckpt_id = [d for d in os.listdir(os.path.join(p, ".essay-state", "checkpoints"))
                   if d.startswith("first-")][0]
        with open(os.path.join(p, ".essay-state", "new-data.json"), "w") as f:
            json.dump({"new": "data"}, f)
        run_script("checkpoint", "rollback", p, ckpt_id)
        assert not os.path.isfile(os.path.join(p, ".essay-state", "new-data.json"))
        run_script("checkpoint", "snapshot", p, "after-rollback")
        assert count_checkpoints(p) == 2

    def test_clean_preserves_newest(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "edge2")
        run_script("checkpoint", "snapshot", p, "older")
        time.sleep(1)
        run_script("checkpoint", "snapshot", p, "newest")
        run_script("checkpoint", "clean", p, "--keep", "1")
        r = run_script("checkpoint", "latest", p)
        assert "label:newest" in r.stdout

    def test_hyphenated_label(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "edge3")
        r = run_script("checkpoint", "snapshot", p, "pre-review")
        assert "pre-review" in r.stdout
        r = run_script("checkpoint", "list", p)
        assert "pre-review" in r.stdout

    def test_usage_text(self, run_script, tmp_path, fake_home):
        r = run_script("checkpoint")
        output = r.stdout + r.stderr
        for cmd in ["snapshot", "list", "rollback", "latest", "clean"]:
            assert cmd in output

    def test_no_tmp_dirs_after_snapshot(self, run_script, tmp_path, fake_home):
        p = setup_project(run_script, tmp_path, "edge4")
        run_script("checkpoint", "snapshot", p, "clean")
        ckpt_base = os.path.join(p, ".essay-state", "checkpoints")
        tmp_dirs = [d for d in os.listdir(ckpt_base) if d.startswith(".tmp-")]
        assert len(tmp_dirs) == 0

    def test_retry_mentions_ready(self, run_script, tmp_path, fake_home, script_dir):
        p = setup_project(run_script, tmp_path, "edge5")
        r = run_script("orchestrate", p, script_dir, "retry-stage", "intake")
        assert "ready" in r.stdout

    def test_retry_outline_resets_variant(self, run_script, tmp_path, fake_home, script_dir):
        p = setup_project(run_script, tmp_path, "edge6")
        run_script("pipeline_state", "set-field", p, "stage", "outline")
        run_script("pipeline_state", "set-field", p, "outline_variant", '"A"')
        run_script("orchestrate", p, script_dir, "retry-stage", "outline")
        r = run_script("pipeline_state", "get-field", p, "outline_variant")
        assert r.stdout.strip() == ""

    def test_retry_draft_resets_version(self, run_script, tmp_path, fake_home, script_dir):
        p = setup_project(run_script, tmp_path, "edge7")
        run_script("pipeline_state", "set-field", p, "stage", "draft")
        run_script("pipeline_state", "set-field", p, "draft_version", "3")
        run_script("orchestrate", p, script_dir, "retry-stage", "draft")
        r = run_script("pipeline_state", "get-field", p, "draft_version")
        assert r.stdout.strip() == "0"
