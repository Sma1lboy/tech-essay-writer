"""Tests for diagram_suggest.py and orchestrate.py integration."""

import json
import os

import pytest


# ── helpers ──────────────────────────────────────────────────────────────


def setup_md(tmp_path, name):
    """Create a project dir with .essay-state/ and return the project path."""
    proj = tmp_path / f"proj-{name}"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".essay-state").mkdir(exist_ok=True)
    return str(proj)


def write_md(proj, filename, content):
    """Write a markdown file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        f.write(content)
    return path


def run_diagram(run_script, md_path, *extra_args):
    """Run diagram_suggest.py on a markdown file and return the result."""
    return run_script("diagram_suggest", md_path, *extra_args)


def parse_json(result):
    """Parse JSON from stdout."""
    return json.loads(result.stdout)


def suggestion_types(data):
    """Return list of suggestion types."""
    return [s["type"] for s in data["suggestions"]]


# ── diagram-suggest.sh — core detection ──────────────────────────────────


class TestArchitectureDetection:
    """Tests 1-9: Architecture content detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        self.proj = setup_md(tmp_path, "arch")
        self.md = write_md(self.proj, "test.md", """\
# System Architecture

The frontend service connects to the backend service.
The backend communicates with the database layer.
The gateway handles all incoming requests.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_architecture(self):
        """Test 1: Runs with architecture content."""
        assert "architecture" in suggestion_types(self.data)

    def test_output_is_valid_json(self):
        """Test 2: Output is valid JSON."""
        # parse_json already validates; just confirm data is a dict
        assert isinstance(self.data, dict)

    def test_has_suggestions_array(self):
        """Test 3: Has suggestions array."""
        assert "suggestions" in self.data
        assert isinstance(self.data["suggestions"], list)

    def test_has_summary_object(self):
        """Test 4: Has summary object."""
        assert "summary" in self.data

    def test_summary_has_total_count(self):
        """Test 5: Summary has total count."""
        assert "total" in self.data["summary"]

    def test_summary_has_type_breakdown(self):
        """Test 6: Summary has type_breakdown."""
        assert "type_breakdown" in self.data["summary"]

    def test_architecture_mermaid_has_graph(self):
        """Test 7: Architecture mermaid contains graph."""
        assert "graph TD" in self.out

    def test_atomic_write_to_state_dir(self):
        """Test 8: Atomic write to state dir."""
        path = os.path.join(self.proj, ".essay-state", "diagram-suggestions.json")
        assert os.path.isfile(path)

    def test_state_file_is_valid_json(self):
        """Test 9: State file is valid JSON."""
        path = os.path.join(self.proj, ".essay-state", "diagram-suggestions.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)


class TestFlowchartDetection:
    """Tests 10-12: Flowchart detection with numbered steps."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "flow")
        self.md = write_md(proj, "test.md", """\
# Deployment Process

Follow these steps to deploy:

1. Build the Docker image
2. Push to the container registry
3. Deploy to Kubernetes
4. Run health checks
5. Monitor the dashboard
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_flowchart(self):
        """Test 10: Flowchart detection (numbered steps)."""
        assert "flowchart" in suggestion_types(self.data)

    def test_flowchart_mermaid_has_keyword(self):
        """Test 11: Flowchart mermaid contains flowchart keyword."""
        assert "flowchart TD" in self.out

    def test_flowchart_has_step_label(self):
        """Test 12: Flowchart extracts step labels."""
        assert "Build the Docker image" in self.out


class TestComparisonDetection:
    """Tests 13-14: Comparison detection (vs)."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "cmp")
        self.md = write_md(proj, "test.md", """\
# Redis vs Memcached

Redis offers persistence while Memcached is purely in-memory.
The advantage of Redis is richer data structures, but the trade-off is higher memory usage.
However, Memcached excels at simple key-value caching.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_comparison(self):
        """Test 13: Comparison detection (vs)."""
        assert "comparison_table" in suggestion_types(self.data)

    def test_comparison_mermaid_is_null(self):
        """Test 14: Comparison has no mermaid (tables are markdown)."""
        assert '"mermaid": null' in self.out


class TestStateDiagramDetection:
    """Tests 15-17: State diagram detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "state")
        self.md = write_md(proj, "test.md", """\
# Order Lifecycle

An order transitions through several states in its lifecycle.
It starts as pending, changes from pending to active when paid.
Once shipped, it moves to completed. If there's an issue, it becomes failed.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_state_diagram(self):
        """Test 15: State diagram detection."""
        assert "state" in suggestion_types(self.data)

    def test_state_mermaid_has_keyword(self):
        """Test 16: State mermaid contains stateDiagram."""
        assert "stateDiagram-v2" in self.out

    def test_state_mermaid_has_state_names(self):
        """Test 17: State mermaid has state names."""
        assert "Pending" in self.out


class TestSequenceDiagramDetection:
    """Tests 18-20: Sequence diagram detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "seq")
        self.md = write_md(proj, "test.md", """\
# Authentication Flow

The client sends a login request to the server.
The server calls the auth database to verify credentials.
The database returns the user record.
The server responds with a JWT token.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_sequence_diagram(self):
        """Test 18: Sequence diagram detection."""
        assert "sequence" in suggestion_types(self.data)

    def test_sequence_mermaid_has_keyword(self):
        """Test 19: Sequence mermaid contains sequenceDiagram."""
        assert "sequenceDiagram" in self.out

    def test_sequence_mermaid_has_actors(self):
        """Test 20: Sequence mermaid has actors."""
        assert "Client" in self.out


class TestERDiagramDetection:
    """Tests 21-22: ER diagram detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "er")
        self.md = write_md(proj, "test.md", """\
# Data Model

The User entity has many Orders. Each Order belongs to a User.
The foreign key links Order to User via user_id.
The schema defines these relationships in the database model.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_er_diagram(self):
        """Test 21: ER diagram detection."""
        assert "er" in suggestion_types(self.data)

    def test_er_mermaid_has_keyword(self):
        """Test 22: ER mermaid contains erDiagram."""
        assert "erDiagram" in self.out


class TestClassDiagramDetection:
    """Tests 23-24: Class diagram detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "class")
        self.md = write_md(proj, "test.md", """\
# Type Hierarchy

The base class Animal defines common behavior.
class Dog extends Animal with bark method.
The interface Serializable is implemented by both.
Polymorphism allows treating Dog as Animal.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_class_diagram(self):
        """Test 23: Class diagram detection."""
        assert "class" in suggestion_types(self.data)

    def test_class_mermaid_has_keyword(self):
        """Test 24: Class mermaid contains classDiagram."""
        assert "classDiagram" in self.out


class TestTimelineDetection:
    """Tests 25-26: Timeline detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "timeline")
        self.md = write_md(proj, "test.md", """\
# Project History

The timeline of releases shows steady progression.
v1.0 launched in 2020. v2.0 added major features in 2022.
v3.0 is the current milestone released in 2024.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)
        self.out = r.stdout

    def test_detects_timeline(self):
        """Test 25: Timeline detection."""
        assert "timeline" in suggestion_types(self.data)

    def test_timeline_mermaid_has_gantt(self):
        """Test 26: Timeline mermaid contains gantt."""
        assert "gantt" in self.out


# ── empty / no-suggestion files ──────────────────────────────────────────


class TestEmptyAndNoSuggestion:
    """Tests 27-28: Empty file and simple prose produce zero suggestions."""

    def test_empty_file_zero_suggestions(self, run_script, tmp_path):
        """Test 27: Empty file produces zero suggestions."""
        proj = setup_md(tmp_path, "empty")
        md = write_md(proj, "test.md", "")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["total"] == 0

    def test_no_suggestion_file_zero(self, run_script, tmp_path):
        """Test 28: No-suggestions file (simple prose)."""
        proj = setup_md(tmp_path, "nosug")
        md = write_md(proj, "test.md", """\
# Introduction

Hello world. This is a simple paragraph with no technical content
that would benefit from any diagrams or visual aids whatsoever.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["total"] == 0


# ── Chinese / bilingual tests ───────────────────────────────────────────


class TestChineseDetection:
    """Tests 29-31: Chinese content detection and bilingual support."""

    def test_detects_chinese_language(self, run_script, tmp_path):
        """Test 29: Chinese content detection."""
        proj = setup_md(tmp_path, "chinese")
        md = write_md(proj, "test.md", """\
# 系统架构

前端服务连接到后端服务。后端与数据库层通信。
微服务架构通过网关处理所有请求。
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["language_detected"] == "zh"

    def test_chinese_description_for_architecture(self, run_script, tmp_path):
        """Test 30: Chinese descriptions when Chinese detected."""
        proj = setup_md(tmp_path, "chinese-desc")
        md = write_md(proj, "test.md", """\
# 系统架构

前端服务连接到后端服务。后端与数据库层通信。
微服务架构通过网关处理所有请求。
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        desc = data["suggestions"][0]["description"]
        assert "架构图" in desc

    def test_chinese_flowchart_detected(self, run_script, tmp_path):
        """Test 31: Chinese flowchart detection."""
        proj = setup_md(tmp_path, "zh-flow")
        md = write_md(proj, "test.md", """\
# 部署流程

部署的步骤如下：

1. 构建镜像
2. 推送到仓库
3. 部署到集群
4. 验证服务状态
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        types = suggestion_types(data)
        assert "flowchart" in types


# ── multi-type document ──────────────────────────────────────────────────


class TestMultiTypeDocument:
    """Tests 32-37: Multiple suggestion types in one document."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "multi")
        self.md = write_md(proj, "test.md", """\
# Architecture Overview

The frontend service connects to the backend service via the API gateway.

## Deploy Steps

1. Build the application
2. Run tests
3. Deploy to production

## Option A vs Option B

Approach A has the advantage of simplicity. However, approach B offers better performance.
The trade-off is complexity versus speed.
""")
        r = run_diagram(run_script, self.md)
        self.data = parse_json(r)

    def test_multi_type_has_at_least_3(self):
        """Test 32: Multiple suggestion types in one document."""
        assert self.data["summary"]["total"] >= 3

    def test_type_breakdown_has_architecture(self):
        """Test 33: Type breakdown counts are correct."""
        assert self.data["summary"]["type_breakdown"].get("architecture", 0) >= 1

    def test_suggestion_has_location_field(self):
        """Test 34: Suggestion has location field."""
        assert "location" in self.data["suggestions"][0]

    def test_suggestion_has_line_field(self):
        """Test 35: Suggestion has line field."""
        assert "line" in self.data["suggestions"][0]

    def test_suggestion_has_description_field(self):
        """Test 36: Suggestion has description field."""
        assert "description" in self.data["suggestions"][0]

    def test_suggestion_has_type_field(self):
        """Test 37: Suggestion has type field."""
        assert "type" in self.data["suggestions"][0]


# ── error handling ───────────────────────────────────────────────────────


class TestErrorHandling:
    """Test 38: File not found returns error JSON."""

    def test_missing_file_returns_error(self, run_script):
        """Test 38: File not found returns error JSON."""
        r = run_script("diagram_suggest", "/nonexistent/file.md")
        assert '"error"' in r.stdout


# ── verbose mode ─────────────────────────────────────────────────────────


class TestVerboseMode:
    """Tests 39-40: Verbose mode output."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "verbose")
        md = write_md(proj, "test.md", """\
# System Design

The frontend service connects to the backend service.
The gateway proxy handles all API requests.
""")
        r = run_diagram(run_script, md, "--verbose")
        self.out = r.stdout

    def test_verbose_has_suggestion_header(self):
        """Test 39: Verbose mode outputs formatted text."""
        assert "Suggestion" in self.out

    def test_verbose_has_mermaid_block(self):
        """Test 40: Verbose mode shows mermaid blocks."""
        assert "```mermaid" in self.out


# ── code block exclusion ─────────────────────────────────────────────────


class TestCodeBlockExclusion:
    """Test 41: Code blocks are excluded from analysis."""

    def test_code_blocks_excluded_from_class_detection(self, run_script, tmp_path):
        """Test 41: Code blocks are excluded from analysis."""
        proj = setup_md(tmp_path, "codeblock")
        md = write_md(proj, "test.md", """\
# Simple Guide

Here is some sample code:

```python
class Dog(Animal):
    def bark(self):
        pass

class Cat(Animal):
    def meow(self):
        pass
```

That covers the basics of this pattern.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        types = suggestion_types(data)
        assert "class" not in types


# ── additional detection heuristic tests ─────────────────────────────────


class TestAdditionalDetection:
    """Tests 42-50: Additional detection heuristics."""

    def test_data_pipeline_detects_flowchart(self, run_script, tmp_path):
        """Test 42: Data pipeline detection."""
        proj = setup_md(tmp_path, "pipeline")
        md = write_md(proj, "test.md", """\
# Data Pipeline

Our data pipeline starts with ingesting events from the producer.
The data processing stage transforms raw events into metrics.
The consumer subscribes to the output stream.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "flowchart" in suggestion_types(data)

    def test_pros_and_cons_detects_comparison(self, run_script, tmp_path):
        """Test 43: Pros and cons detection."""
        proj = setup_md(tmp_path, "proscons")
        md = write_md(proj, "test.md", """\
# Framework Choice

Let's weigh the pros and cons of each framework.
React has widespread adoption while Vue has simpler syntax.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "comparison_table" in suggestion_types(data)

    def test_fsm_keyword_detects_state(self, run_script, tmp_path):
        """Test 44: FSM keyword detection."""
        proj = setup_md(tmp_path, "fsm")
        md = write_md(proj, "test.md", """\
# Parser Implementation

The parser uses a finite state machine approach.
States include idle, reading, and error.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "state" in suggestion_types(data)

    def test_oauth_flow_detects_sequence(self, run_script, tmp_path):
        """Test 45: Protocol/API flow detection."""
        proj = setup_md(tmp_path, "protocol")
        md = write_md(proj, "test.md", """\
# OAuth Flow

The OAuth handshake begins when the browser sends an authentication request.
The server responds with a redirect to the auth provider.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "sequence" in suggestion_types(data)

    def test_english_language_detected(self, run_script, tmp_path):
        """Test 46: Language detected as English for English content."""
        proj = setup_md(tmp_path, "en")
        md = write_md(proj, "test.md", """\
# Architecture

The frontend service connects to the backend service through the gateway.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["language_detected"] == "en"

    def test_all_suggestion_types_valid_enum(self, run_script, tmp_path):
        """Test 47: Suggestion types are valid enum values."""
        proj = setup_md(tmp_path, "types")
        md = write_md(proj, "test.md", """\
# System

The frontend service connects to the backend service.

## Steps

1. First thing
2. Second thing
3. Third thing

## A vs B

Option A compared to option B. The trade-off is speed however.

## Lifecycle

The state changes from pending to active to completed.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        valid_types = {
            "flowchart", "sequence", "class", "state", "er",
            "comparison_table", "architecture", "timeline",
        }
        for s in data["suggestions"]:
            assert s["type"] in valid_types

    def test_line_numbers_are_positive_integers(self, run_script, tmp_path):
        """Test 48: Line numbers are positive integers."""
        proj = setup_md(tmp_path, "types2")
        md = write_md(proj, "test.md", """\
# System

The frontend service connects to the backend service.

## Steps

1. First thing
2. Second thing
3. Third thing

## A vs B

Option A compared to option B. The trade-off is speed however.

## Lifecycle

The state changes from pending to active to completed.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        for s in data["suggestions"]:
            assert isinstance(s["line"], int)
            assert s["line"] >= 1

    def test_flowchart_mermaid_has_arrows(self, run_script, tmp_path):
        """Test 49: Mermaid syntax for flowchart has --> arrows."""
        proj = setup_md(tmp_path, "arrows")
        md = write_md(proj, "test.md", """\
# Build Process

1. Compile source code
2. Run unit tests
3. Package artifacts
4. Upload to registry
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        flowcharts = [s["mermaid"] for s in data["suggestions"] if s["type"] == "flowchart"]
        assert flowcharts
        assert "-->" in flowcharts[0]

    def test_short_sections_skipped(self, run_script, tmp_path):
        """Test 50: Short sections are skipped."""
        proj = setup_md(tmp_path, "short")
        md = write_md(proj, "test.md", """\
# Title

OK.

## Conclusion

Bye.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["total"] == 0


# ── orchestrate.py integration ───────────────────────────────────────────


class TestOrchestrateIntegration:
    """Tests 51-55, 87-90: Orchestrate build-diagram-suggestions."""

    def test_orchestrate_dispatch_works(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 51: build-diagram-suggestions command exists in dispatch."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch")
        write_md(proj, "draft-v1.md", """\
# Architecture

The frontend service connects to the backend service via the gateway.
The middleware layer handles authentication.

## Deploy Steps

1. Build images
2. Push to registry
3. Deploy to cluster
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        assert '"suggestions"' in r.stdout

    def test_orchestrate_finds_draft_content(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 52: Orchestrate finds latest draft."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch2")
        write_md(proj, "draft-v1.md", """\
# Architecture

The frontend service connects to the backend service via the gateway.
The middleware layer handles authentication.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        assert '"architecture"' in r.stdout

    def test_orchestrate_falls_back_to_final_external(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 53: Orchestrate falls back to final-external."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-fallback")
        write_md(proj, "final-external.md", """\
# System Design

The client sends a request to the server. The server calls the database.
The database returns results. The server responds to the client.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        assert '"suggestions"' in r.stdout

    def test_orchestrate_returns_error_with_no_draft(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 54: Orchestrate returns error with no draft."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-empty")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        assert '"error"' in r.stdout

    def test_help_mentions_diagram_suggestions(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 55: build-diagram-suggestions in usage text."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-help")
        (tmp_path / "proj-orch-help" / ".essay-state").mkdir(exist_ok=True)
        r = run_script("orchestrate", proj, script_dir, "help")
        assert "build-diagram-suggestions" in r.stdout

    def test_orchestrate_falls_back_to_final_internal(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 87: orchestrate uses final-internal as fallback."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-internal")
        write_md(proj, "final-internal.md", """\
# Internal Article
The service layer communicates with the database module and the cache component.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        assert '"suggestions"' in r.stdout

    def test_orchestrate_uses_latest_draft_v2(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 88: orchestrate uses latest draft (v2 over v1)."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-v2")
        write_md(proj, "draft-v1.md", """\
# V1
Nothing here.
""")
        write_md(proj, "draft-v2.md", """\
# V2
The frontend service connects to the backend module and the gateway component for the database layer.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        data = parse_json(r)
        assert data["summary"]["total"] >= 1

    def test_orchestrate_output_is_valid_json(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 89: orchestrate output is valid JSON."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-json")
        write_md(proj, "draft-v1.md", """\
# Test
The frontend service connects to the backend module and the gateway component.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions")
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_orchestrate_verbose_mode(self, run_script, tmp_path, script_dir, monkeypatch):
        """Test 90: orchestrate verbose mode."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home, exist_ok=True)
        monkeypatch.setenv("HOME", home)
        proj = setup_md(tmp_path, "orch-verb")
        write_md(proj, "draft-v1.md", """\
# Verbose Test
The frontend service connects to the backend module and database layer component.
""")
        r = run_script("orchestrate", proj, script_dir, "build-diagram-suggestions", "--verbose")
        assert "Suggestion" in r.stdout or "suggestions" in r.stdout


# ── edge cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests 56-61: Edge cases."""

    def test_mixed_english_and_chinese(self, run_script, tmp_path):
        """Test 56: Mixed English and Chinese."""
        proj = setup_md(tmp_path, "mixed")
        md = write_md(proj, "test.md", """\
# Mixed Content

The system architecture 系统架构 includes:

The frontend service connects to the backend.
前端服务连接后端微服务网关。
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "suggestions" in data

    def test_markdown_with_only_headings(self, run_script, tmp_path):
        """Test 57: Markdown with only headings."""
        proj = setup_md(tmp_path, "headings")
        md = write_md(proj, "test.md", """\
# Title
## Section A
## Section B
## Section C
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["total"] == 0

    def test_large_document_with_many_sections(self, run_script, tmp_path):
        """Test 58: Large document with many sections."""
        proj = setup_md(tmp_path, "large")
        lines = ["# Big Article"]
        for i in range(1, 11):
            lines.append("")
            lines.append(f"## Section {i}")
            lines.append("")
            lines.append(f"This section describes step {i} of the process.")
            lines.append("First we configure, then we deploy, finally we verify.")
        md = write_md(proj, "test.md", "\n".join(lines))
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert data["summary"]["total"] >= 1

    def test_hierarchy_tree_class_detection(self, run_script, tmp_path):
        """Test 59: Hierarchy/tree detection via class diagram (inheritance)."""
        proj = setup_md(tmp_path, "hierarchy")
        md = write_md(proj, "test.md", """\
# Type System

The base class defines shared behavior.
Each subclass inherits from the parent class.
Polymorphism allows treating the subclass as the base class.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "class" in suggestion_types(data)

    def test_chinese_er_detection(self, run_script, tmp_path):
        """Test 60: Chinese ER detection."""
        proj = setup_md(tmp_path, "zh-er")
        md = write_md(proj, "test.md", """\
# 数据模型

用户实体与订单实体之间存在关系。
每个订单通过外键关联到用户。
数据模型定义了主键和索引。
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "er" in suggestion_types(data)

    def test_chinese_state_detection(self, run_script, tmp_path):
        """Test 61: Chinese state detection."""
        proj = setup_md(tmp_path, "zh-state")
        md = write_md(proj, "test.md", """\
# 订单生命周期

订单经历完整的状态转换过程。
从 pending 创建后变为 active 状态。
最终变为 completed 或 failed。
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "state" in suggestion_types(data)


# ── additional detection heuristic tests ─────────────────────────────────


class TestDetectionHeuristics:
    """Tests 62-73: Additional detection heuristic tests."""

    def test_on_the_other_hand_triggers_comparison(self, run_script, tmp_path):
        """Test 62: 'on the other hand' triggers comparison."""
        proj = setup_md(tmp_path, "othhand")
        md = write_md(proj, "test.md", """\
# Database Choice
PostgreSQL has great JSON support. On the other hand, MySQL is simpler to set up and operate.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "comparison_table" in suggestion_types(data)

    def test_option_abc_triggers_comparison(self, run_script, tmp_path):
        """Test 63: 'option A/B/C' triggers comparison."""
        proj = setup_md(tmp_path, "optabc")
        md = write_md(proj, "test.md", """\
# Hosting
Option A uses Docker containers for reproducible builds. Option B uses bare metal VMs for lower overhead and latency.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        ct = sum(1 for s in data["suggestions"] if s["type"] == "comparison_table")
        assert ct >= 1

    def test_differences_between_triggers_comparison(self, run_script, tmp_path):
        """Test 64: 'differences between' triggers comparison."""
        proj = setup_md(tmp_path, "diffbetween")
        md = write_md(proj, "test.md", """\
# Approaches
The differences between REST and GraphQL are significant when considering developer experience.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "comparison_table" in suggestion_types(data)

    def test_benefit_drawback_triggers_comparison(self, run_script, tmp_path):
        """Test 65: benefit/drawback + however triggers comparison."""
        proj = setup_md(tmp_path, "benefit")
        md = write_md(proj, "test.md", """\
# Storage
The advantage of SSD is speed. However, the drawback is higher cost per gigabyte for storage.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "comparison_table" in suggestion_types(data)

    def test_depends_on_triggers_architecture(self, run_script, tmp_path):
        """Test 66: 'depends on' triggers architecture."""
        proj = setup_md(tmp_path, "depends")
        md = write_md(proj, "test.md", """\
# Dependencies
The auth module depends on the user service. The notification service integrates with the queue layer.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "architecture" in suggestion_types(data)

    def test_websocket_triggers_sequence(self, run_script, tmp_path):
        """Test 67: websocket triggers sequence."""
        proj = setup_md(tmp_path, "ws")
        md = write_md(proj, "test.md", """\
# Real-time
The websocket connection allows the server to push events. The client receives messages and the browser renders updates.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "sequence" in suggestion_types(data)

    def test_grpc_triggers_sequence(self, run_script, tmp_path):
        """Test 68: grpc triggers sequence."""
        proj = setup_md(tmp_path, "grpc")
        md = write_md(proj, "test.md", """\
# Services
The gRPC call from the client sends data. The server processes the request and returns a response.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "sequence" in suggestion_types(data)

    def test_explicit_state_change_pattern(self, run_script, tmp_path):
        """Test 69: explicit state change pattern."""
        proj = setup_md(tmp_path, "stchg")
        md = write_md(proj, "test.md", """\
# Task Status
The task changes from draft to published when the author submits it for review.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "state" in suggestion_types(data)

    def test_version_progression_triggers_timeline(self, run_script, tmp_path):
        """Test 70: version progression triggers timeline."""
        proj = setup_md(tmp_path, "versions")
        md = write_md(proj, "test.md", """\
# Releases
The evolution from v1.0 to v2.0 brought breaking changes. Then v3.0 added the most requested features.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "timeline" in suggestion_types(data)

    def test_milestone_roadmap_triggers_timeline(self, run_script, tmp_path):
        """Test 71: milestone/roadmap triggers timeline."""
        proj = setup_md(tmp_path, "roadmap")
        md = write_md(proj, "test.md", """\
# Product Plan
The roadmap includes a key milestone for Q1 2024 and another milestone for Q3 2024 delivery.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "timeline" in suggestion_types(data)

    def test_message_passing_events_triggers_sequence(self, run_script, tmp_path):
        """Test 72: message passing with events triggers sequence."""
        proj = setup_md(tmp_path, "msgpass")
        md = write_md(proj, "test.md", """\
# Event Bus
When an event is emitted, the subscriber processes the callback. Each message triggers a webhook notification.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "sequence" in suggestion_types(data)

    def test_one_to_many_triggers_er(self, run_script, tmp_path):
        """Test 73: one-to-many triggers ER."""
        proj = setup_md(tmp_path, "onetomany")
        md = write_md(proj, "test.md", """\
# Data Design
The one-to-many relationship between users and their orders is defined by the entity model schema.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        assert "er" in suggestion_types(data)


# ── mermaid validity tests ───────────────────────────────────────────────


class TestMermaidValidity:
    """Tests 74-80: Mermaid syntax validity."""

    def test_architecture_mermaid_has_node_definitions(self, run_script, tmp_path):
        """Test 74: architecture mermaid has node definitions."""
        proj = setup_md(tmp_path, "archnodes")
        md = write_md(proj, "test.md", """\
# System
The frontend service connects to the API gateway and the backend module handles data.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        arch_mermaids = [s["mermaid"] for s in data["suggestions"] if s["type"] == "architecture"]
        assert arch_mermaids
        assert '["' in arch_mermaids[0]

    def test_sequence_mermaid_has_request_arrow(self, run_script, tmp_path):
        """Test 75: sequence mermaid has ->>+ arrows."""
        proj = setup_md(tmp_path, "seqarrows")
        md = write_md(proj, "test.md", """\
# API
The client sends a request to the server. The server returns a response with data.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        seq_mermaids = [s["mermaid"] for s in data["suggestions"] if s["type"] == "sequence"]
        assert seq_mermaids
        assert "->>+" in seq_mermaids[0]

    def test_sequence_mermaid_has_response_arrow(self, run_script, tmp_path):
        """Test 76: sequence mermaid has -->>- arrows."""
        proj = setup_md(tmp_path, "seqarrows2")
        md = write_md(proj, "test.md", """\
# API
The client sends a request to the server. The server returns a response with data.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        seq_mermaids = [s["mermaid"] for s in data["suggestions"] if s["type"] == "sequence"]
        assert seq_mermaids
        assert "-->>-" in seq_mermaids[0]

    def test_state_mermaid_has_initial_marker(self, run_script, tmp_path):
        """Test 77: state mermaid has initial marker [*]."""
        proj = setup_md(tmp_path, "stateinit")
        md = write_md(proj, "test.md", """\
# Workflow
Jobs can be pending, active, completed, or failed. The state machine processes each.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        state_mermaids = [s["mermaid"] for s in data["suggestions"] if s["type"] == "state"]
        assert state_mermaids
        assert "[*]" in state_mermaids[0]

    def test_state_mermaid_has_transition_arrows(self, run_script, tmp_path):
        """Test 78: state mermaid has transition arrows."""
        proj = setup_md(tmp_path, "statetrans")
        md = write_md(proj, "test.md", """\
# Workflow
Jobs can be pending, active, completed, or failed. The state machine processes each.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        state_mermaids = [s["mermaid"] for s in data["suggestions"] if s["type"] == "state"]
        assert state_mermaids
        assert "-->" in state_mermaids[0]

    def test_er_mermaid_has_relationship(self, run_script, tmp_path):
        """Test 79: ER mermaid has relationship syntax."""
        proj = setup_md(tmp_path, "errel")
        md = write_md(proj, "test.md", """\
# Schema
The User entity has many Order records. The foreign key links them.
""")
        r = run_diagram(run_script, md)
        assert "||--o{" in r.stdout

    def test_class_mermaid_has_inheritance(self, run_script, tmp_path):
        """Test 80: class mermaid has inheritance."""
        proj = setup_md(tmp_path, "classinh")
        md = write_md(proj, "test.md", """\
# Design
The class Animal defines behavior. The class Dog extends Animal with new features.
""")
        r = run_diagram(run_script, md)
        assert "<|--" in r.stdout


# ── field validation tests ───────────────────────────────────────────────


class TestFieldValidation:
    """Tests 81-86: Field validation tests."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path):
        proj = setup_md(tmp_path, "descs")
        md = write_md(proj, "test.md", """\
# Full Test
The frontend service connects to the backend module and database layer.

## Steps
First, build the app. Then, test it. Finally, deploy to production.
""")
        r = run_diagram(run_script, md)
        self.data = parse_json(r)

    def test_all_descriptions_non_empty(self):
        """Test 81: all suggestions have non-empty description."""
        for s in self.data["suggestions"]:
            assert isinstance(s["description"], str)
            assert len(s["description"]) > 0

    def test_all_rationales_non_empty(self):
        """Test 82: all suggestions have non-empty rationale."""
        for s in self.data["suggestions"]:
            assert isinstance(s["rationale"], str)
            assert len(s["rationale"]) > 0

    def test_all_locations_non_empty(self):
        """Test 83: all suggestions have non-empty location."""
        for s in self.data["suggestions"]:
            assert isinstance(s["location"], str)
            assert len(s["location"]) > 0

    def test_mermaid_is_string_or_null(self):
        """Test 84: mermaid is string or null for all suggestions."""
        for s in self.data["suggestions"]:
            assert s["mermaid"] is None or isinstance(s["mermaid"], str)

    def test_diagram_types_have_mermaid_content(self):
        """Test 85: diagram types have non-null mermaid."""
        mermaid_types = {"flowchart", "architecture", "state", "sequence", "er", "class", "timeline"}
        for s in self.data["suggestions"]:
            if s["type"] in mermaid_types:
                assert s["mermaid"] is not None
                assert len(s["mermaid"]) > 0

    def test_type_breakdown_matches_actual_counts(self):
        """Test 86: type_breakdown counts match actual."""
        from collections import Counter
        actual = Counter(s["type"] for s in self.data["suggestions"])
        tb = self.data["summary"]["type_breakdown"]
        all_types = set(list(actual.keys()) + list(tb.keys()))
        for t in all_types:
            assert tb.get(t, 0) == actual.get(t, 0)


# ── single-keyword threshold tests ───────────────────────────────────────


class TestSingleKeywordThreshold:
    """Tests 91-94: Single keyword insufficient for detection."""

    def test_single_architecture_keyword_not_enough(self, run_script, tmp_path):
        """Test 91: single architecture keyword insufficient."""
        proj = setup_md(tmp_path, "singlearch")
        md = write_md(proj, "test.md", """\
# Overview
This service handles user authentication and processes their login requests efficiently.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        arch_ct = sum(1 for s in data["suggestions"] if s["type"] == "architecture")
        assert arch_ct == 0

    def test_single_state_word_not_enough(self, run_script, tmp_path):
        """Test 92: single state word insufficient."""
        proj = setup_md(tmp_path, "singlestate")
        md = write_md(proj, "test.md", """\
# Tasks
All pending tasks are listed in the main dashboard view for the team to review and prioritize.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        state_ct = sum(1 for s in data["suggestions"] if s["type"] == "state")
        assert state_ct == 0

    def test_two_item_ordered_list_not_enough(self, run_script, tmp_path):
        """Test 93: two-item ordered list not enough for flowchart."""
        proj = setup_md(tmp_path, "twoitem")
        md = write_md(proj, "test.md", """\
# Short List
1. Install the tool.
2. Run the command.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        fc_ct = sum(1 for s in data["suggestions"] if s["type"] == "flowchart")
        assert fc_ct == 0

    def test_generic_prose_no_sequence(self, run_script, tmp_path):
        """Test 94: generic prose without actor interaction insufficient for sequence."""
        proj = setup_md(tmp_path, "singleseq")
        md = write_md(proj, "test.md", """\
# Notes
The application formats the output data for display in a tabular layout for end users.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        seq_ct = sum(1 for s in data["suggestions"] if s["type"] == "sequence")
        assert seq_ct == 0


# ── section parsing tests ────────────────────────────────────────────────


class TestSectionParsing:
    """Tests 95-97: Section parsing and location assignment."""

    def test_intro_section_has_introduction_location(self, run_script, tmp_path):
        """Test 95: intro section gets correct location."""
        proj = setup_md(tmp_path, "introloc")
        md = write_md(proj, "test.md", """\
The client sends a request to the server and receives a response via HTTP.

# Main
Some content here.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        found = False
        for s in data["suggestions"]:
            if "intro" in s["location"].lower() or "Introduction" in s["location"]:
                found = True
                break
        assert found

    def test_nested_headings_produce_distinct_locations(self, run_script, tmp_path):
        """Test 96: nested headings produce distinct locations."""
        proj = setup_md(tmp_path, "nested")
        md = write_md(proj, "test.md", """\
# Top

## Sub Section
The client sends a request and the server returns a response via HTTP.

### Deep Section
First install, then configure, finally deploy to the production pipeline stage.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        locs = [s["location"] for s in data["suggestions"]]
        loc_str = "\n".join(locs)
        assert "Sub Section" in loc_str or "Deep Section" in loc_str

    def test_multiple_sections_produce_distinct_locations(self, run_script, tmp_path):
        """Test 97: multiple sections produce multiple distinct locations."""
        proj = setup_md(tmp_path, "multloc")
        md = write_md(proj, "test.md", """\
# Article

## Architecture
The frontend service connects to the backend module and the database layer.

## API Flow
The client sends a request to the server. The server calls the database and returns data.
""")
        r = run_diagram(run_script, md)
        data = parse_json(r)
        distinct_locs = set(s["location"] for s in data["suggestions"])
        assert len(distinct_locs) >= 2
