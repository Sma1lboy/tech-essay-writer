"""Integration tests for orchestrate.py — validates full pipeline flow."""

import json
import os

import pytest


@pytest.fixture
def pipeline_project(run_script, tmp_path, monkeypatch, script_dir):
    """Set up a project with initialized pipeline and materials."""
    home = str(tmp_path / "fakehome")
    os.makedirs(home)
    monkeypatch.setenv("HOME", home)
    project = str(tmp_path / "test-project")
    os.makedirs(os.path.join(project, ".essay-state"), exist_ok=True)
    return project, script_dir


class TestOrchestrateStatus:
    def test_uninit_status(self, run_script, pipeline_project):
        project, sd = pipeline_project
        r = run_script("orchestrate", project, sd, "status")
        assert "NOT_INITIALIZED" in r.stdout

    def test_status_after_init(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        r = run_script("orchestrate", project, sd, "status")
        assert "intake" in r.stdout
        assert "Test Topic" in r.stdout


class TestOrchestrateNextStage:
    def test_next_stage_empty_materials(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "intake"

    def test_next_stage_with_materials(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "research"

    def test_next_stage_no_synthesis(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        run_script("pipeline_state", "set-stage", project, "research")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "research"

    def test_next_stage_with_synthesis(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        run_script("pipeline_state", "set-stage", project, "research")
        synth = {"thesis": "Test thesis statement", "unique_angle": "Novel perspective",
                 "evidence_map": [], "knowledge_gaps": [], "competitive_landscape": [],
                 "recommended_depth": "intermediate"}
        with open(os.path.join(project, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump(synth, f)
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "outline"

    def test_next_stage_no_outlines(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "outline")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "outline"

    def test_next_stage_outlines_no_critique(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "outline")
        for v in ["A", "B", "C"]:
            with open(os.path.join(project, ".essay-state", f"outline-{v}.json"), "w") as f:
                json.dump({"variant": v, "title": f"Title {v}"}, f)
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "outline_critique"

    def test_next_stage_outlines_critique_no_choice(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "outline")
        for v in ["A", "B", "C"]:
            with open(os.path.join(project, ".essay-state", f"outline-{v}.json"), "w") as f:
                json.dump({"variant": v, "title": f"Title {v}"}, f)
        with open(os.path.join(project, ".essay-state", "outline-critique.json"), "w") as f:
            json.dump({"recommendation": {"recommended_variant": "B"}}, f)
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "outline_choice"

    def test_next_stage_with_choice(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "outline")
        for v in ["A", "B", "C"]:
            with open(os.path.join(project, ".essay-state", f"outline-{v}.json"), "w") as f:
                json.dump({"variant": v, "title": f"Title {v}"}, f)
        with open(os.path.join(project, ".essay-state", "outline-critique.json"), "w") as f:
            json.dump({"recommendation": {"recommended_variant": "B"}}, f)
        run_script("pipeline_state", "set-field", project, "outline_variant", "B")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "draft"

    def test_next_stage_no_draft(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "draft")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert "draft" in r.stdout.strip()

    def test_next_stage_with_draft(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "draft")
        with open(os.path.join(project, ".essay-state", "draft-v1.md"), "w") as f:
            f.write("# Test Article\n\nContent.\n")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "review"


class TestOrchestrateIntakeSummary:
    def test_intake_summary(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        r = run_script("orchestrate", project, sd, "build-intake-summary")
        assert "Sources: 1" in r.stdout
        assert "Important note" in r.stdout


class TestOrchestrateResearchPrompt:
    def test_research_prompt(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        run_script("pipeline_state", "set-stage", project, "research")
        r = run_script("orchestrate", project, sd, "build-research-prompt")
        assert "Research Synthesis Agent" in r.stdout
        assert "Important note" in r.stdout


class TestOrchestrateOutlinePrompts:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, pipeline_project):
        project, sd = pipeline_project
        self.project = project
        self.sd = sd
        self.run = run_script
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("intake_materials", "add-note", project, "Important note")
        run_script("pipeline_state", "set-stage", project, "research")
        synth = {"thesis": "Test thesis statement", "unique_angle": "Novel perspective",
                 "evidence_map": [], "knowledge_gaps": [], "competitive_landscape": [],
                 "recommended_depth": "intermediate"}
        with open(os.path.join(project, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump(synth, f)
        run_script("pipeline_state", "set-stage", project, "outline")

    def test_outline_variant_a(self):
        r = self.run("orchestrate", self.project, self.sd, "build-outline-prompts", "A")
        assert "Outline Generator Agent" in r.stdout
        assert "Variant: A" in r.stdout
        assert "Test thesis" in r.stdout

    def test_outline_variant_b(self):
        r = self.run("orchestrate", self.project, self.sd, "build-outline-prompts", "B")
        assert "Variant: B" in r.stdout

    def test_outline_variant_c(self):
        r = self.run("orchestrate", self.project, self.sd, "build-outline-prompts", "C")
        assert "Variant: C" in r.stdout


class TestOrchestrateOutlineCritique:
    def test_critique_prompt(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("intake_materials", "init", project)
        run_script("pipeline_state", "set-stage", project, "outline")
        synth = {"thesis": "Test thesis statement"}
        with open(os.path.join(project, ".essay-state", "research-synthesis.json"), "w") as f:
            json.dump(synth, f)
        for v in ["A", "B", "C"]:
            with open(os.path.join(project, ".essay-state", f"outline-{v}.json"), "w") as f:
                json.dump({"variant": v, "title": f"Test Title Variant {v}",
                           "hook": f"An intriguing opening for variant {v}",
                           "sections": [{"title": "Section 1", "key_points": ["Point 1"]}],
                           "target_word_count": 2000}, f)
        r = run_script("orchestrate", project, sd, "build-outline-critique-prompt")
        assert "Outline Adversarial Critique" in r.stdout
        assert "Variant A" in r.stdout
        assert "Variant B" in r.stdout
        assert "Variant C" in r.stdout
        assert "Test thesis" in r.stdout
        assert len(r.stdout) > 0


class TestOrchestrateWriterPrompt:
    def test_writer_prompt(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "draft")
        with open(os.path.join(project, ".essay-state", "outline-B.json"), "w") as f:
            json.dump({"variant": "B", "title": "Test Title Variant B"}, f)
        r = run_script("orchestrate", project, sd, "build-writer-prompt", "B")
        assert "Draft Writer Agent" in r.stdout
        assert "Variant B" in r.stdout


class TestOrchestrateReviewPrompts:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, pipeline_project):
        project, sd = pipeline_project
        self.project = project
        self.sd = sd
        self.run = run_script
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "review")
        with open(os.path.join(project, ".essay-state", "draft-v1.md"), "w") as f:
            f.write("# Test Article\n\nThis is a test draft.\n\n```python\ndef test_example():\n    assert True\n```\n\n## Conclusion\n\nTesting is important.\n")

    @pytest.mark.parametrize("reviewer", [
        "technical", "editor", "adversarial", "audience", "seo", "external", "factcheck"
    ])
    def test_review_prompt(self, reviewer):
        r = self.run("orchestrate", self.project, self.sd, "build-review-prompts", reviewer)
        assert len(r.stdout) > 0
        assert "Test Article" in r.stdout

    def test_invalid_reviewer(self):
        r = self.run("orchestrate", self.project, self.sd, "build-review-prompts", "invalid")
        assert r.returncode != 0


class TestOrchestrateRefinement:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, pipeline_project):
        project, sd = pipeline_project
        self.project = project
        self.sd = sd
        self.run = run_script
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "review")
        with open(os.path.join(project, ".essay-state", "draft-v1.md"), "w") as f:
            f.write("# Test Article\n\nContent.\n")
        # Create mock reviews
        reviewers = {
            "technical": {"rating": "PASS", "issues": []},
            "editor": {"rating": "NEEDS_EDITING", "issues": [{"severity": "major", "issue": "Hook is weak"}]},
            "adversarial": {"rating": "VULNERABLE", "attacks": [{"target": "thesis", "attack": "N=1", "severity": "significant"}], "issues": []},
            "audience": {"rating": "MEH", "issues": []},
            "seo": {"rating": "NEEDS_WORK", "issues": [{"severity": "minor", "issue": "Title generic"}]},
            "external": {"rating": "NEEDS_CONTEXT", "issues": [{"severity": "minor", "issue": "Acronym not expanded"}]},
            "factcheck": {"rating": "VERIFIED", "issues": []},
        }
        state_dir = os.path.join(project, ".essay-state")
        for name, data in reviewers.items():
            data["reviewer"] = name
            data["summary"] = f"Summary for {name}"
            with open(os.path.join(state_dir, f"review-{name}.json"), "w") as f:
                json.dump(data, f)
            run_script("pipeline_state", "add-review", project,
                       os.path.join(state_dir, f"review-{name}.json"))
        run_script("aggregate_reviews", project)
        run_script("pipeline_state", "set-stage", project, "refinement")

    def test_refiner_prompt(self):
        r = self.run("orchestrate", self.project, self.sd, "build-refiner-prompt", "1")
        assert "Refinement Agent" in r.stdout
        assert "Test Article" in r.stdout
        assert "Round: 1" in r.stdout

    def test_convergence_continue(self):
        r = self.run("orchestrate", self.project, self.sd, "check-convergence", "1")
        assert "CONTINUE" in r.stdout

    def test_convergence_converged(self):
        # Update adversarial to SOLID
        with open(os.path.join(self.project, ".essay-state", "review-adversarial.json"), "w") as f:
            json.dump({"reviewer": "adversarial", "rating": "SOLID", "summary": "Strong", "attacks": [], "issues": []}, f)
        r = self.run("orchestrate", self.project, self.sd, "check-convergence", "2")
        assert "CONVERGED" in r.stdout


class TestOrchestrateCalibrateAndSummary:
    def test_cal_summary(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "review")
        reviewers = {
            "technical": {"rating": "PASS"}, "editor": {"rating": "NEEDS_EDITING"},
            "adversarial": {"rating": "VULNERABLE"}, "audience": {"rating": "MEH"},
            "seo": {"rating": "NEEDS_WORK"}, "external": {"rating": "NEEDS_CONTEXT"},
            "factcheck": {"rating": "VERIFIED"},
        }
        state_dir = os.path.join(project, ".essay-state")
        for name, data in reviewers.items():
            data["reviewer"] = name
            data["summary"] = f"Summary {name}"
            data.setdefault("issues", [])
            with open(os.path.join(state_dir, f"review-{name}.json"), "w") as f:
                json.dump(data, f)
        run_script("calibrate_reviews", project)
        r = run_script("orchestrate", project, sd, "build-calibration-summary")
        assert "Calibration Report" in r.stdout
        assert "Normalized Scores" in r.stdout


class TestOrchestrateFormatPrompts:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, pipeline_project):
        project, sd = pipeline_project
        self.project = project
        self.sd = sd
        self.run = run_script
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "polish")
        with open(os.path.join(project, ".essay-state", "draft-v1.md"), "w") as f:
            f.write("# Test Article\n\nContent.\n")

    @pytest.mark.parametrize("fmt", ["internal", "external"])
    def test_format_prompt_core(self, fmt):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", fmt)
        assert len(r.stdout) > 0
        assert "Test Article" in r.stdout

    @pytest.mark.parametrize("platform", ["medium", "devto", "hashnode", "wechat", "juejin"])
    def test_format_prompt_platform(self, platform):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", platform)
        assert len(r.stdout) > 0
        assert "Test Article" in r.stdout

    def test_invalid_format(self):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", "invalid")
        assert r.returncode != 0


class TestOrchestrateListPlatforms:
    def test_list_platforms(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        r = run_script("orchestrate", project, sd, "list-platforms")
        for p in ["internal", "external", "medium", "devto", "hashnode", "wechat", "juejin"]:
            assert p in r.stdout


class TestOrchestratePolishComplete:
    def test_polish_without_finals(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "polish")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "polish"

    def test_polish_with_finals(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "set-stage", project, "polish")
        state_dir = os.path.join(project, ".essay-state")
        with open(os.path.join(state_dir, "final-internal.md"), "w") as f:
            f.write("Internal version")
        with open(os.path.join(state_dir, "final-external.md"), "w") as f:
            f.write("External version")
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "complete"

    def test_complete_stays_complete(self, run_script, pipeline_project):
        project, sd = pipeline_project
        run_script("pipeline_state", "init", project, "Test Topic")
        run_script("pipeline_state", "complete", project)
        r = run_script("orchestrate", project, sd, "next-stage")
        assert r.stdout.strip() == "complete"
