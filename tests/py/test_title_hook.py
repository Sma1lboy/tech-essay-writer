"""Tests for title_generator.py and hook_workshop.py."""

import glob
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


def read_result_json(proj, filename):
    """Read a JSON file from .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path) as f:
        return json.load(f)


# ============================================================
# title_generator.py tests
# ============================================================


class TestTitleGeneratorEmptyState:
    """Test 1-2: Runs with empty state dir, creates file, valid JSON."""

    def test_runs_with_empty_state(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-empty")
        r = run_script("title_generator", proj)
        assert '"titles"' in r.stdout

    def test_creates_json_file(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-empty2")
        run_script("title_generator", proj)
        assert os.path.isfile(
            os.path.join(proj, ".essay-state", "title-variations.json")
        )

    def test_output_is_valid_json(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-empty3")
        r = run_script("title_generator", proj)
        data = json.loads(r.stdout)
        assert isinstance(data, dict)


class TestTitleGeneratorDefaultCount:
    """Test 3: Default generates 10 titles."""

    def test_default_count_is_10(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-default-count")
        write_json(proj, "pipeline-state.json", {
            "topic": "GraphQL API Design",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj)
        data = json.loads(r.stdout)
        assert data["count"] == 10


class TestTitleGeneratorCustomCount:
    """Test 4: Custom count."""

    def test_custom_count_of_5(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-custom-count")
        write_json(proj, "pipeline-state.json", {
            "topic": "Docker Optimization",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "5")
        data = json.loads(r.stdout)
        assert data["count"] == 5


class TestTitleGeneratorRanking:
    """Test 5-8: Titles ranked by composite, score dimensions, score range, sequential ranks."""

    def test_titles_sorted_by_composite_desc(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-ranking")
        write_json(proj, "pipeline-state.json", {
            "topic": "Rust Memory Safety",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Rust Memory Safety",
            "unique_angle": "Zero-cost abstractions",
            "gap": "No practical guide",
            "pain_points": ["Borrow checker confusion"],
            "key_findings": ["Lifetimes simplify after practice"],
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        scores = [t["scores"]["composite"] for t in data["titles"]]
        assert scores == sorted(scores, reverse=True)

    def test_all_score_dimensions_present(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-dims")
        write_json(proj, "pipeline-state.json", {
            "topic": "Rust Memory Safety",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Rust Memory Safety",
            "unique_angle": "Zero-cost abstractions",
            "gap": "No practical guide",
            "pain_points": ["Borrow checker confusion"],
            "key_findings": ["Lifetimes simplify after practice"],
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        required = {"clarity", "curiosity_gap", "specificity", "shareability", "composite"}
        for t in data["titles"]:
            assert set(t["scores"].keys()) == required

    def test_all_scores_between_1_and_10(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-score-range")
        write_json(proj, "pipeline-state.json", {
            "topic": "Rust Memory Safety",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Rust Memory Safety",
            "unique_angle": "Zero-cost abstractions",
            "gap": "No practical guide",
            "pain_points": ["Borrow checker confusion"],
            "key_findings": ["Lifetimes simplify after practice"],
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        for t in data["titles"]:
            for k, v in t["scores"].items():
                assert 1 <= v <= 10, f"Score {k}={v} out of range for title: {t['title']}"

    def test_sequential_ranks(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-ranks")
        write_json(proj, "pipeline-state.json", {
            "topic": "Rust Memory Safety",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Rust Memory Safety",
            "unique_angle": "Zero-cost abstractions",
            "gap": "No practical guide",
            "pain_points": ["Borrow checker confusion"],
            "key_findings": ["Lifetimes simplify after practice"],
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        ranks = [t["rank"] for t in data["titles"]]
        expected = list(range(1, len(ranks) + 1))
        assert ranks == expected


class TestTitleGeneratorMetadata:
    """Test 9-10: Topic in metadata, formula names recorded."""

    def test_topic_in_metadata(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-topic-meta")
        write_json(proj, "pipeline-state.json", {
            "topic": "WebAssembly",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "3")
        data = json.loads(r.stdout)
        assert data["topic"] == "WebAssembly"

    def test_at_least_5_distinct_formulas(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-formulas")
        write_json(proj, "pipeline-state.json", {
            "topic": "CI/CD Pipelines",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        formulas = set(t["formula"] for t in data["titles"])
        assert len(formulas) >= 5


class TestTitleGeneratorInputsUsed:
    """Test 11-12: Research synthesis and materials tracked in inputs_used."""

    def test_research_synthesis_marked_as_used(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-research")
        write_json(proj, "pipeline-state.json", {
            "topic": "Event Sourcing",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Event Sourcing",
            "conventional_wisdom": "CRUD is fine for everything",
            "approach": "Event-driven architecture",
            "result": "simplified complex domain logic",
            "pain_points": ["State management complexity"],
            "key_findings": ["Event logs enable time travel debugging"],
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        assert data["inputs_used"]["research_synthesis"] is True

    def test_materials_marked_as_used(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-materials")
        write_json(proj, "pipeline-state.json", {
            "topic": "Testing",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "materials.json", {
            "items": [{"title": "TDD Guide", "source": "https://example.com"}],
        })
        r = run_script("title_generator", proj, "3")
        data = json.loads(r.stdout)
        assert data["inputs_used"]["materials"] is True


class TestTitleGeneratorTopicInTitle:
    """Test 13: At least one title contains the topic."""

    def test_topic_appears_in_at_least_one_title(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-topic-in-title")
        write_json(proj, "pipeline-state.json", {
            "topic": "PostgreSQL Performance",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        found = any("PostgreSQL" in t["title"] for t in data["titles"])
        assert found, "Expected at least one title to contain 'PostgreSQL'"


class TestTitleGeneratorCorruptResearch:
    """Test 14: Corrupt research file handled gracefully."""

    def test_handles_corrupt_research(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-corrupt")
        write_json(proj, "pipeline-state.json", {
            "topic": "Corrupt Test",
            "stage": "research",
            "language": "en",
        })
        write_file(proj, "research-synthesis.json", "NOT JSON AT ALL")
        r = run_script("title_generator", proj, "3")
        assert '"titles"' in r.stdout


class TestTitleGeneratorAtomicWrite:
    """Test 15: No tmp files left after run."""

    def test_no_tmp_files_left(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-atomic")
        write_json(proj, "pipeline-state.json", {
            "topic": "Atomic Test",
            "stage": "research",
            "language": "en",
        })
        run_script("title_generator", proj, "3")
        tmp_files = glob.glob(os.path.join(proj, ".essay-state", "*.tmp.*"))
        assert len(tmp_files) == 0


class TestTitleGeneratorEdgeCounts:
    """Test 16-17: Count of 1 works, large count (15) generates variants."""

    def test_count_of_1_works(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-one")
        write_json(proj, "pipeline-state.json", {
            "topic": "Minimal",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "1")
        data = json.loads(r.stdout)
        assert data["count"] == 1

    def test_count_of_15_works(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-large")
        write_json(proj, "pipeline-state.json", {
            "topic": "Large Count",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "15")
        data = json.loads(r.stdout)
        assert data["count"] == 15

    def test_variant_formulas_used_for_large_count(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-large-variant")
        write_json(proj, "pipeline-state.json", {
            "topic": "Large Count",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "15")
        data = json.loads(r.stdout)
        found = any("variant" in t["formula"] for t in data["titles"])
        assert found, "Expected variant formulas for count > 10"


class TestTitleGeneratorFormulasAvailable:
    """Test 18: formulas_available count."""

    def test_10_formulas_available(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-formulas-count")
        write_json(proj, "pipeline-state.json", {
            "topic": "Formulas",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        assert data["formulas_available"] == 10


# ============================================================
# hook_workshop.py tests
# ============================================================


class TestHookWorkshopEmptyState:
    """Test 19: Runs with empty state dir, creates file."""

    def test_runs_with_empty_state(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-empty")
        r = run_script("hook_workshop", proj)
        assert '"hooks"' in r.stdout

    def test_creates_json_file(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-empty2")
        run_script("hook_workshop", proj)
        assert os.path.isfile(
            os.path.join(proj, ".essay-state", "hook-variations.json")
        )


class TestHookWorkshopDefaultStyles:
    """Test 20-21: Default generates all 5 styles."""

    def test_default_generates_5_hooks(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-all")
        write_json(proj, "pipeline-state.json", {
            "topic": "Microservices",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        assert data["count"] == 5

    def test_all_5_styles_present(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-all-styles")
        write_json(proj, "pipeline-state.json", {
            "topic": "Microservices",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        styles = sorted(h["style"] for h in data["hooks"])
        assert styles == ["bold", "contrast", "data", "question", "story"]


class TestHookWorkshopSingleStyleFilters:
    """Test 22-26: Single style filter works for each style."""

    def test_story_filter(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-story-only")
        write_json(proj, "pipeline-state.json", {
            "topic": "Observability",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "story")
        data = json.loads(r.stdout)
        assert data["count"] == 1
        assert data["hooks"][0]["style"] == "story"

    def test_data_filter(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-data-only")
        write_json(proj, "pipeline-state.json", {
            "topic": "ML Ops",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "data")
        data = json.loads(r.stdout)
        assert data["hooks"][0]["style"] == "data"

    def test_question_filter(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-question-only")
        write_json(proj, "pipeline-state.json", {
            "topic": "API Design",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "question")
        data = json.loads(r.stdout)
        assert data["hooks"][0]["style"] == "question"

    def test_contrast_filter(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-contrast-only")
        write_json(proj, "pipeline-state.json", {
            "topic": "DevOps",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "contrast")
        data = json.loads(r.stdout)
        assert data["hooks"][0]["style"] == "contrast"

    def test_bold_filter(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-bold-only")
        write_json(proj, "pipeline-state.json", {
            "topic": "Monolith Architecture",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "bold")
        data = json.loads(r.stdout)
        assert data["hooks"][0]["style"] == "bold"


class TestHookWorkshopInvalidStyle:
    """Test 27: Invalid style returns error."""

    def test_invalid_style_returns_error(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-invalid")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "invalid_style")
        combined = r.stdout + r.stderr
        assert '"error"' in combined


class TestHookWorkshopScores:
    """Test 28-31: Score dimensions, range, ranking, word count."""

    def test_all_hook_score_dimensions_present(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-scores")
        write_json(proj, "pipeline-state.json", {
            "topic": "Terraform",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        required = {"engagement", "relevance", "authenticity", "composite"}
        for h in data["hooks"]:
            assert set(h["scores"].keys()) == required

    def test_all_hook_scores_between_1_and_10(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-score-range")
        write_json(proj, "pipeline-state.json", {
            "topic": "Terraform",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        for h in data["hooks"]:
            for k, v in h["scores"].items():
                assert 1 <= v <= 10, f"Score {k}={v} out of range for hook style: {h['style']}"

    def test_hooks_sorted_by_composite_desc(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-ranking")
        write_json(proj, "pipeline-state.json", {
            "topic": "Terraform",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        scores = [h["scores"]["composite"] for h in data["hooks"]]
        assert scores == sorted(scores, reverse=True)

    def test_all_hooks_have_word_count(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-wc")
        write_json(proj, "pipeline-state.json", {
            "topic": "Terraform",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        for h in data["hooks"]:
            assert "word_count" in h
            assert h["word_count"] >= 1


class TestHookWorkshopResearchEnrichment:
    """Test 32-34: Research data enriches hooks (data, bold, story, question)."""

    @pytest.fixture(autouse=True)
    def setup_research_project(self, run_script, tmp_path):
        self.run_script = run_script
        self.proj = setup_project(tmp_path, "hook-research")
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Kubernetes Autoscaling",
            "stage": "research",
            "language": "en",
        })
        write_json(self.proj, "research-synthesis.json", {
            "topic": "Kubernetes Autoscaling",
            "unique_angle": "Event-driven scaling",
            "gap": "No guide covers event-driven autoscaling",
            "conventional_wisdom": "HPA is sufficient for most workloads",
            "approach": "Event-driven autoscaling with KEDA",
            "result": "reduced infrastructure costs by 40%",
            "pain_points": ["Manual scaling is error-prone"],
            "statistics": ["67% of teams over-provision by 3x"],
        })
        r = self.run_script("hook_workshop", self.proj)
        self.data = json.loads(r.stdout)

    def _get_hook_by_style(self, style):
        for h in self.data["hooks"]:
            if h["style"] == style:
                return h
        return None

    def test_data_hook_uses_statistic(self):
        h = self._get_hook_by_style("data")
        assert h is not None
        assert "67%" in h["hook"]

    def test_bold_hook_uses_conventional_wisdom(self):
        h = self._get_hook_by_style("bold")
        assert h is not None
        assert "HPA" in h["hook"]

    def test_story_hook_mentions_topic(self):
        h = self._get_hook_by_style("story")
        assert h is not None
        assert "Kubernetes Autoscaling" in h["hook"]

    def test_question_hook_references_conventional_wisdom(self):
        h = self._get_hook_by_style("question")
        assert h is not None
        assert "HPA" in h["hook"]


class TestHookWorkshopCorruptResearch:
    """Test 35: Corrupt research handled gracefully."""

    def test_handles_corrupt_research(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-corrupt")
        write_json(proj, "pipeline-state.json", {
            "topic": "Corrupt Hook",
            "stage": "research",
            "language": "en",
        })
        write_file(proj, "research-synthesis.json", "BROKEN JSON {{{{ ")
        r = run_script("hook_workshop", proj)
        assert '"hooks"' in r.stdout


class TestHookWorkshopAtomicWrite:
    """Test 36: No tmp files left after run."""

    def test_no_hook_tmp_files_left(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-atomic")
        write_json(proj, "pipeline-state.json", {
            "topic": "Atomic Hook",
            "stage": "research",
            "language": "en",
        })
        run_script("hook_workshop", proj)
        tmp_files = glob.glob(os.path.join(proj, ".essay-state", "*.tmp.*"))
        assert len(tmp_files) == 0


class TestHookWorkshopMetadata:
    """Test 37-38: requested_style recorded, inputs_used tracking."""

    def test_requested_style_recorded(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-style-meta")
        write_json(proj, "pipeline-state.json", {
            "topic": "Meta Test",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "bold")
        data = json.loads(r.stdout)
        assert data["requested_style"] == "bold"

    def test_inputs_used_tracking(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-inputs")
        write_json(proj, "pipeline-state.json", {
            "topic": "Inputs Test",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {"topic": "Inputs Test"})
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        assert data["inputs_used"]["research_synthesis"] is True
        assert data["inputs_used"]["pipeline_state"] is True


class TestHookWorkshopDescriptions:
    """Test 39: All hooks have descriptions."""

    def test_all_hooks_have_descriptions(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-descs")
        write_json(proj, "pipeline-state.json", {
            "topic": "Descriptions",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        for h in data["hooks"]:
            assert h.get("description"), f"Hook style '{h['style']}' missing description"


# ============================================================
# orchestrate.py integration tests
# ============================================================


class TestOrchestrateIntegration:
    """Test 40-43: Orchestrator dispatches title and hook commands."""

    def test_build_title_variations_dispatches(self, run_script, tmp_path, script_dir):
        proj = setup_project(tmp_path, "orch-title")
        write_json(proj, "pipeline-state.json", {
            "topic": "Orchestrator Title Test",
            "stage": "research",
            "language": "en",
        })
        r = run_script("orchestrate", proj, script_dir, "build-title-variations", "3")
        assert '"titles"' in r.stdout
        data = json.loads(r.stdout)
        assert data["count"] == 3

    def test_build_hook_variations_dispatches_single_style(
        self, run_script, tmp_path, script_dir
    ):
        proj = setup_project(tmp_path, "orch-hook")
        write_json(proj, "pipeline-state.json", {
            "topic": "Orchestrator Hook Test",
            "stage": "research",
            "language": "en",
        })
        r = run_script("orchestrate", proj, script_dir, "build-hook-variations", "story")
        assert '"hooks"' in r.stdout
        data = json.loads(r.stdout)
        assert data["count"] == 1

    def test_build_hook_variations_default_is_all(
        self, run_script, tmp_path, script_dir
    ):
        proj = setup_project(tmp_path, "orch-hook-default")
        write_json(proj, "pipeline-state.json", {
            "topic": "Default Hook",
            "stage": "research",
            "language": "en",
        })
        r = run_script("orchestrate", proj, script_dir, "build-hook-variations")
        data = json.loads(r.stdout)
        assert data["count"] == 5

    def test_usage_shows_new_commands(self, run_script, script_dir):
        r = run_script("orchestrate", "x", "x", "invalid")
        combined = r.stdout + r.stderr
        assert "build-title-variations" in combined
        assert "build-hook-variations" in combined


# ============================================================
# Determinism and enrichment tests
# ============================================================


class TestTitleGeneratorDeterminism:
    """Test 44: Title generation is deterministic."""

    def test_title_generation_is_deterministic(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-deterministic")
        write_json(proj, "pipeline-state.json", {
            "topic": "Determinism Test",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Determinism Test",
            "unique_angle": "Consistent output",
            "gap": "Reproducibility",
        })
        r1 = run_script("title_generator", proj, "5")
        r2 = run_script("title_generator", proj, "5")
        data1 = json.loads(r1.stdout)
        data2 = json.loads(r2.stdout)
        titles1 = [t["title"] for t in data1["titles"]]
        titles2 = [t["title"] for t in data2["titles"]]
        assert titles1 == titles2


class TestHookWorkshopEnrichment:
    """Test 45-46: Contrast hook uses gap, story hook uses approach."""

    def test_contrast_hook_uses_gap(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-contrast-gap")
        write_json(proj, "pipeline-state.json", {
            "topic": "Gap Testing",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Gap Testing",
            "gap": "Nobody covers performance profiling at scale",
        })
        r = run_script("hook_workshop", proj, "contrast")
        data = json.loads(r.stdout)
        assert "missed" in data["hooks"][0]["hook"]

    def test_story_hook_uses_approach(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-story-approach")
        write_json(proj, "pipeline-state.json", {
            "topic": "Approach Test",
            "stage": "research",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "topic": "Approach Test",
            "approach": "progressive delivery with feature flags",
            "pain_points": ["Deployments cause downtime"],
        })
        r = run_script("hook_workshop", proj, "story")
        data = json.loads(r.stdout)
        assert "progressive delivery" in data["hooks"][0]["hook"]


class TestWithoutResearchOrState:
    """Test 47-48: Scripts produce output without research or state files."""

    def test_hooks_without_research_produce_5(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-no-research")
        r = run_script("hook_workshop", proj)
        data = json.loads(r.stdout)
        assert data["count"] == 5

    def test_titles_without_state_produce_requested_count(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-no-state")
        r = run_script("title_generator", proj, "3")
        data = json.loads(r.stdout)
        assert data["count"] == 3


class TestTitleScoreVariation:
    """Test 49: Scores vary across titles."""

    def test_scores_vary_across_titles(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "title-score-variation")
        write_json(proj, "pipeline-state.json", {
            "topic": "Score Variance",
            "stage": "research",
            "language": "en",
        })
        r = run_script("title_generator", proj, "10")
        data = json.loads(r.stdout)
        composites = set(t["scores"]["composite"] for t in data["titles"])
        assert len(composites) > 1, "Expected varied composite scores across titles"


class TestHookEngagementScore:
    """Test 50: Story hook engagement score > 0."""

    def test_story_engagement_score_positive(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "hook-eng-story")
        write_json(proj, "pipeline-state.json", {
            "topic": "Engagement Test",
            "stage": "research",
            "language": "en",
        })
        r = run_script("hook_workshop", proj, "story")
        data = json.loads(r.stdout)
        assert data["hooks"][0]["scores"]["engagement"] > 0
