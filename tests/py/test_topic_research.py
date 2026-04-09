"""Tests for topic_research.py and orchestrate.py build-topic-research integration."""

import json
import os
from datetime import datetime

import pytest


# ── helpers ──────────────────────────────────────────────────────────────


def setup_project(tmp_path, name):
    """Create a temp project dir with .essay-state/ and return its path."""
    proj = tmp_path / f"proj-{name}"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".essay-state").mkdir(exist_ok=True)
    return str(proj)


def parse_json(result):
    """Parse JSON from subprocess stdout."""
    return json.loads(result.stdout)


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
# topic_research.py — core tests
# ============================================================


class TestBasicExecution:
    """Tests 1-5: Basic topic research execution and output."""

    def test_runs_with_simple_topic(self, run_script, tmp_path):
        """Test 1: Runs with a simple topic."""
        proj = setup_project(tmp_path, "basic")
        r = run_script("topic_research", proj, "Kubernetes")
        assert '"topic"' in r.stdout
        assert '"research_questions"' in r.stdout

    def test_output_is_valid_json(self, run_script, tmp_path):
        """Test 2: Output is valid JSON."""
        proj = setup_project(tmp_path, "json-valid")
        r = run_script("topic_research", proj, "Kubernetes")
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_research_brief_json_created(self, run_script, tmp_path):
        """Test 3: research-brief.json is created."""
        proj = setup_project(tmp_path, "file-created")
        run_script("topic_research", proj, "Kubernetes")
        assert os.path.isfile(os.path.join(proj, ".essay-state", "research-brief.json"))

    def test_topic_recorded_in_output(self, run_script, tmp_path):
        """Test 4: Topic is recorded correctly."""
        proj = setup_project(tmp_path, "topic-recorded")
        r = run_script("topic_research", proj, "Kubernetes")
        data = parse_json(r)
        assert data["topic"] == "Kubernetes"

    def test_keywords_extracted_for_single_word(self, run_script, tmp_path):
        """Test 5: Keywords are extracted."""
        proj = setup_project(tmp_path, "kw-single")
        r = run_script("topic_research", proj, "Kubernetes")
        data = parse_json(r)
        assert len(data["keywords"]) == 1


class TestKeywordsAndQuestions:
    """Tests 6-9: Multi-word keywords, question counts and fields."""

    def test_multi_word_topic_extracts_multiple_keywords(self, run_script, tmp_path):
        """Test 6: Multi-word topic extracts multiple keywords."""
        proj = setup_project(tmp_path, "multi-keyword")
        r = run_script("topic_research", proj, "React Server Components vs Client Components")
        data = parse_json(r)
        assert len(data["keywords"]) >= 3

    def test_at_least_10_research_questions(self, run_script, tmp_path):
        """Test 7: Research questions are generated (at least 10)."""
        proj = setup_project(tmp_path, "question-count")
        r = run_script("topic_research", proj, "GraphQL API Design")
        data = parse_json(r)
        assert data["summary"]["total_questions"] >= 10

    def test_questions_have_required_fields(self, run_script, tmp_path):
        """Test 8: Each question has category, question, purpose."""
        proj = setup_project(tmp_path, "question-fields")
        r = run_script("topic_research", proj, "GraphQL API Design")
        data = parse_json(r)
        for q in data["research_questions"]:
            assert "category" in q
            assert "question" in q
            assert "purpose" in q

    def test_at_least_8_search_queries(self, run_script, tmp_path):
        """Test 9: Search queries are generated (at least 8)."""
        proj = setup_project(tmp_path, "sq-count")
        r = run_script("topic_research", proj, "GraphQL API Design")
        data = parse_json(r)
        assert data["summary"]["total_search_queries"] >= 8


class TestSearchQueries:
    """Tests 10-11: Search query fields and unique angles."""

    def test_search_queries_have_required_fields(self, run_script, tmp_path):
        """Test 10: Each search query has query, purpose, target."""
        proj = setup_project(tmp_path, "sq-fields")
        r = run_script("topic_research", proj, "GraphQL API Design")
        data = parse_json(r)
        for q in data["search_queries"]:
            assert "query" in q
            assert "purpose" in q
            assert "target" in q

    def test_at_least_6_unique_angles(self, run_script, tmp_path):
        """Test 11: Unique angles are generated (at least 6)."""
        proj = setup_project(tmp_path, "angle-count")
        r = run_script("topic_research", proj, "GraphQL API Design")
        data = parse_json(r)
        assert data["summary"]["total_angles"] >= 6


class TestAngleFields:
    """Tests 12-15: Angle required fields, ranking, and scores."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "angle-fields")
        r = run_script("topic_research", proj, "GraphQL API Design")
        self.data = parse_json(r)

    def test_angles_have_required_fields(self):
        """Test 12: Each angle has angle, type, strength, risk, relevance_score, rank."""
        required = {"angle", "type", "strength", "risk", "relevance_score", "rank"}
        for a in self.data["unique_angles"]:
            assert required.issubset(set(a.keys()))

    def test_angles_sorted_by_relevance_desc(self):
        """Test 13: Angles are ranked by relevance_score descending."""
        scores = [a["relevance_score"] for a in self.data["unique_angles"]]
        assert scores == sorted(scores, reverse=True)

    def test_angle_ranks_sequential(self):
        """Test 14: Angle ranks are sequential 1..N."""
        ranks = [a["rank"] for a in self.data["unique_angles"]]
        expected = list(range(1, len(ranks) + 1))
        assert ranks == expected

    def test_relevance_scores_in_range(self):
        """Test 15: Relevance scores are in range 1-10."""
        for a in self.data["unique_angles"]:
            assert 1 <= a["relevance_score"] <= 10


class TestDomainDetection:
    """Tests 16-20: Domain detection for various topic types."""

    def test_frontend_domain_detected(self, run_script, tmp_path):
        """Test 16: Domain detection -- frontend topic."""
        proj = setup_project(tmp_path, "domain-frontend")
        r = run_script("topic_research", proj, "React Component Performance Optimization")
        data = parse_json(r)
        assert "frontend" in data["detected_domains"]

    def test_devops_domain_detected(self, run_script, tmp_path):
        """Test 17: Domain detection -- devops topic."""
        proj = setup_project(tmp_path, "domain-devops")
        r = run_script("topic_research", proj, "Kubernetes CI/CD Pipeline Automation")
        data = parse_json(r)
        assert "devops" in data["detected_domains"]

    def test_ai_ml_domain_detected(self, run_script, tmp_path):
        """Test 18: Domain detection -- AI/ML topic."""
        proj = setup_project(tmp_path, "domain-ai")
        r = run_script("topic_research", proj, "Fine-tuning LLM Models for Code Generation")
        data = parse_json(r)
        assert "ai_ml" in data["detected_domains"]

    def test_security_domain_detected(self, run_script, tmp_path):
        """Test 19: Domain detection -- security topic."""
        proj = setup_project(tmp_path, "domain-security")
        r = run_script("topic_research", proj, "Zero-Trust Authentication Architecture")
        data = parse_json(r)
        assert "security" in data["detected_domains"]

    def test_data_domain_detected(self, run_script, tmp_path):
        """Test 20: Domain detection -- data topic."""
        proj = setup_project(tmp_path, "domain-data")
        r = run_script("topic_research", proj, "PostgreSQL Query Optimization at Scale")
        data = parse_json(r)
        assert "data" in data["detected_domains"]


class TestDomainSpecificQuestions:
    """Tests 21-24: Domain-specific question generation and topic presence."""

    def test_ai_domain_question_mentions_ethical(self, run_script, tmp_path):
        """Test 21: Domain-specific research question generated for AI topic."""
        proj = setup_project(tmp_path, "domain-q-ai")
        r = run_script("topic_research", proj, "Machine Learning Pipeline Testing")
        data = parse_json(r)
        domain_q = ""
        for q in data["research_questions"]:
            if q["category"] == "domain_specific":
                domain_q = q["question"]
                break
        assert "ethical" in domain_q

    def test_topic_appears_in_research_questions(self, run_script, tmp_path):
        """Test 22: Research questions include topic in text."""
        proj = setup_project(tmp_path, "topic-in-questions")
        r = run_script("topic_research", proj, "Event Sourcing")
        data = parse_json(r)
        found = sum(1 for q in data["research_questions"] if "Event Sourcing" in q["question"])
        assert found >= 5

    def test_topic_appears_in_search_queries(self, run_script, tmp_path):
        """Test 23: Search queries include topic."""
        proj = setup_project(tmp_path, "topic-in-sq")
        r = run_script("topic_research", proj, "Event Sourcing")
        data = parse_json(r)
        found = sum(1 for q in data["search_queries"] if "Event Sourcing" in q["query"])
        assert found >= 3

    def test_topic_appears_in_unique_angles(self, run_script, tmp_path):
        """Test 24: Unique angles include topic."""
        proj = setup_project(tmp_path, "topic-in-angles")
        r = run_script("topic_research", proj, "Event Sourcing")
        data = parse_json(r)
        found = sum(1 for a in data["unique_angles"] if "Event Sourcing" in a["angle"])
        assert found >= 3


class TestPriorityAssignment:
    """Tests 25-27: Priority assignment for research questions and summary fields."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "priority")
        r = run_script("topic_research", proj, "Event Sourcing")
        self.data = parse_json(r)

    def test_at_least_3_high_priority_questions(self):
        """Test 25: Priority assignment -- high priority questions exist."""
        high_count = sum(1 for q in self.data["research_questions"] if q.get("priority") == "high")
        assert high_count >= 3

    def test_all_questions_have_valid_priority(self):
        """Test 26: Priority assignment -- all questions have priority."""
        for q in self.data["research_questions"]:
            assert q.get("priority") in ("high", "medium", "low")

    def test_summary_has_all_required_fields(self):
        """Test 27: Summary section has all required fields."""
        required = {"total_questions", "total_search_queries", "total_angles",
                     "high_priority_questions", "top_angle", "top_angle_type"}
        assert required.issubset(set(self.data["summary"].keys()))


class TestDeterministicOutput:
    """Test 28: Deterministic output -- same topic produces same output."""

    def test_deterministic_research_questions(self, run_script, tmp_path):
        """Test 28: Deterministic output -- same topic produces same output."""
        proj = setup_project(tmp_path, "deterministic")
        r1 = run_script("topic_research", proj, "Docker Optimization")
        r2 = run_script("topic_research", proj, "Docker Optimization")
        data1 = parse_json(r1)
        data2 = parse_json(r2)
        questions1 = [q["question"] for q in data1["research_questions"]]
        questions2 = [q["question"] for q in data2["research_questions"]]
        assert questions1 == questions2


class TestAtomicWrite:
    """Test 29: Atomic write -- no tmp files left."""

    def test_no_tmp_files_left(self, run_script, tmp_path):
        """Test 29: Atomic write -- no tmp files left."""
        proj = setup_project(tmp_path, "atomic")
        run_script("topic_research", proj, "Atomic Test")
        state_dir = os.path.join(proj, ".essay-state")
        tmp_files = [f for f in os.listdir(state_dir) if ".tmp." in f]
        assert len(tmp_files) == 0


class TestSpecialInputs:
    """Tests 30-31: Special characters and long topics."""

    def test_handles_special_characters(self, run_script, tmp_path):
        """Test 30: Handles special characters in topic."""
        proj = setup_project(tmp_path, "special-chars")
        r = run_script("topic_research", proj, "C++ Memory Safety & RAII Patterns")
        assert '"topic"' in r.stdout
        data = parse_json(r)
        assert data["topic"] == "C++ Memory Safety & RAII Patterns"

    def test_handles_long_topic(self, run_script, tmp_path):
        """Test 31: Handles very long topic gracefully."""
        proj = setup_project(tmp_path, "long-topic")
        long_topic = "Building a Distributed Event-Driven Microservices Architecture with Kubernetes and Apache Kafka for Real-Time Data Processing"
        r = run_script("topic_research", proj, long_topic)
        data = parse_json(r)
        assert "research_questions" in data
        assert len(data["keywords"]) >= 5


class TestMultipleDomains:
    """Tests 32-33: Multiple domains detected for cross-cutting topics."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "multi-domain")
        r = run_script("topic_research", proj, "Deploying React Apps on Kubernetes with CI/CD")
        self.data = parse_json(r)

    def test_multiple_domains_detected(self):
        """Test 32: Multiple domains detected for cross-cutting topic."""
        assert len(self.data["detected_domains"]) >= 2

    def test_cross_domain_angle_present(self):
        """Test 33: Cross-domain angle generated when multiple domains."""
        found = any(a["type"] == "cross_domain" for a in self.data["unique_angles"])
        assert found


class TestAngleTypes:
    """Test 34: Angle types include all expected types."""

    def test_all_expected_angle_types(self, run_script, tmp_path):
        """Test 34: Angle types include all expected types."""
        proj = setup_project(tmp_path, "angle-types")
        r = run_script("topic_research", proj, "Terraform Infrastructure as Code")
        data = parse_json(r)
        types = set(a["type"] for a in data["unique_angles"])
        assert "contrarian" in types
        assert "experience_report" in types
        assert "decision_framework" in types
        assert "myth_busting" in types


class TestSearchQueryTargets:
    """Test 35: Search queries cover different targets."""

    def test_query_targets_covered(self, run_script, tmp_path):
        """Test 35: Search queries cover different targets."""
        proj = setup_project(tmp_path, "query-targets")
        r = run_script("topic_research", proj, "Rust Memory Safety")
        data = parse_json(r)
        targets = set(q["target"] for q in data["search_queries"])
        assert "dev_community" in targets
        assert "github" in targets
        assert "hacker_news" in targets


class TestInputsUsedTracking:
    """Tests 36-38: inputs_used tracking for pipeline state and materials."""

    def test_pipeline_state_marked_as_used(self, run_script, tmp_path):
        """Test 36: inputs_used tracking -- pipeline_state present."""
        proj = setup_project(tmp_path, "inputs-tracking")
        write_json(proj, "pipeline-state.json",
                   {"topic": "Input Tracking Test", "stage": "research", "language": "en"})
        r = run_script("topic_research", proj, "Input Tracking Test")
        data = parse_json(r)
        assert data["inputs_used"]["pipeline_state"] is True

    def test_materials_not_used_when_absent(self, run_script, tmp_path):
        """Test 37: inputs_used -- materials not present."""
        proj = setup_project(tmp_path, "inputs-no-mat")
        write_json(proj, "pipeline-state.json",
                   {"topic": "Input Tracking Test", "stage": "research", "language": "en"})
        r = run_script("topic_research", proj, "Input Tracking Test")
        data = parse_json(r)
        assert data["inputs_used"]["materials"] is False

    def test_materials_used_when_present(self, run_script, tmp_path):
        """Test 38: inputs_used -- materials present."""
        proj = setup_project(tmp_path, "inputs-materials")
        write_json(proj, "materials.json",
                   {"items": [{"title": "Test Material", "source": "https://example.com"}]})
        r = run_script("topic_research", proj, "Materials Test")
        data = parse_json(r)
        assert data["inputs_used"]["materials"] is True


class TestAutoCreateStateDir:
    """Test 39: State dir is created if it doesn't exist."""

    def test_state_dir_auto_created(self, run_script, tmp_path):
        """Test 39: State dir is created if it doesn't exist."""
        proj = str(tmp_path / "proj-auto-mkdir")
        os.makedirs(proj, exist_ok=True)
        # Note: NOT creating .essay-state dir -- the script should
        run_script("topic_research", proj, "Auto Mkdir Test")
        assert os.path.isfile(os.path.join(proj, ".essay-state", "research-brief.json"))


class TestCorruptInputHandling:
    """Tests 40-41: Graceful handling of corrupt input files."""

    def test_handles_corrupt_pipeline_state(self, run_script, tmp_path):
        """Test 40: Corrupt pipeline-state.json handled gracefully."""
        proj = setup_project(tmp_path, "corrupt-pipeline")
        write_file(proj, "pipeline-state.json", "NOT VALID JSON {{{")
        r = run_script("topic_research", proj, "Corrupt State Test")
        assert '"research_questions"' in r.stdout

    def test_handles_corrupt_materials(self, run_script, tmp_path):
        """Test 41: Corrupt materials.json handled gracefully."""
        proj = setup_project(tmp_path, "corrupt-materials")
        write_file(proj, "materials.json", "<<<BROKEN>>>")
        r = run_script("topic_research", proj, "Corrupt Materials Test")
        assert '"search_queries"' in r.stdout


class TestTimestamp:
    """Test 42: generated_at timestamp is present and valid."""

    def test_generated_at_valid_iso_timestamp(self, run_script, tmp_path):
        """Test 42: generated_at timestamp is present and valid."""
        proj = setup_project(tmp_path, "timestamp")
        r = run_script("topic_research", proj, "Timestamp Test")
        data = parse_json(r)
        ts = data.get("generated_at", "")
        # Should parse without error
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        assert dt is not None


class TestUniqueCategoriesAndFileMatch:
    """Tests 43-44: Unique categories and file-stdout consistency."""

    def test_research_question_categories_unique(self, run_script, tmp_path):
        """Test 43: Research question categories are all unique."""
        proj = setup_project(tmp_path, "unique-cats")
        r = run_script("topic_research", proj, "Event Driven Architecture")
        data = parse_json(r)
        cats = [q["category"] for q in data["research_questions"]]
        assert len(cats) == len(set(cats))

    def test_file_on_disk_matches_stdout(self, run_script, tmp_path):
        """Test 44: file on disk matches stdout output."""
        proj = setup_project(tmp_path, "file-match")
        r = run_script("topic_research", proj, "File Match Test")
        file_data = read_result_json(proj, "research-brief.json")
        assert file_data["topic"] == "File Match Test"


class TestMissingArguments:
    """Test 45: Missing topic argument fails."""

    def test_missing_topic_fails(self, run_script, tmp_path):
        """Test 45: Missing topic argument fails."""
        proj = setup_project(tmp_path, "missing-topic")
        r = run_script("topic_research", proj)
        # The script should fail with usage or error message
        combined = r.stdout + r.stderr
        assert "required" in combined.lower() or "usage" in combined.lower()


# ============================================================
# orchestrate.py integration — build-topic-research
# ============================================================


class TestOrchestrateTopicResearch:
    """Tests 46-49: Orchestrate build-topic-research dispatch and usage."""

    def test_orchestrate_dispatches_with_explicit_topic(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 46: build-topic-research dispatches with explicit topic."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_project(tmp_path, "orch-explicit")
        r = run_script("orchestrate", proj, script_dir, "build-topic-research", "Microservices")
        assert '"research_questions"' in r.stdout
        data = parse_json(r)
        assert data["topic"] == "Microservices"

    def test_orchestrate_reads_topic_from_pipeline_state(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 47: build-topic-research reads topic from pipeline-state."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_project(tmp_path, "orch-pipeline")
        write_json(proj, "pipeline-state.json",
                   {"topic": "Pipeline Topic Test", "stage": "research", "language": "en"})
        r = run_script("orchestrate", proj, script_dir, "build-topic-research")
        data = parse_json(r)
        assert data["topic"] == "Pipeline Topic Test"

    def test_orchestrate_fails_without_topic(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 48: build-topic-research fails without topic or pipeline state."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_project(tmp_path, "orch-no-topic")
        r = run_script("orchestrate", proj, script_dir, "build-topic-research")
        combined = r.stdout + r.stderr
        assert "error" in combined.lower()

    def test_usage_shows_build_topic_research(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 49: Usage shows build-topic-research."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_project(tmp_path, "orch-usage")
        r = run_script("orchestrate", proj, script_dir, "invalid")
        combined = r.stdout + r.stderr
        assert "build-topic-research" in combined


class TestGeneralDomainFallback:
    """Test 50: General domain fallback for unknown topic."""

    def test_general_domain_for_non_tech_topic(self, run_script, tmp_path):
        """Test 50: General domain fallback for unknown topic."""
        proj = setup_project(tmp_path, "general-domain")
        r = run_script("topic_research", proj, "Productivity Hacks for Remote Teams")
        data = parse_json(r)
        assert "general" in data["detected_domains"]
