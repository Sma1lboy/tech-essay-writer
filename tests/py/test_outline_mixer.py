"""Tests for outline_mixer.py -- cherry-pick sections from outline variants."""

import json
import os

import pytest


# ── Outline fixture data ────────────────────────────────────────────────

OUTLINE_A = {
    "variant": "A",
    "variant_name": "Tutorial",
    "title": "Build a Multi-Agent System in 200 Lines",
    "hook": "A tutorial hook",
    "sections": [
        {
            "title": "The Problem with Monolithic Agents",
            "purpose": "Establish pain point",
            "key_points": ["Context overflow", "Tangled concerns"],
            "estimated_words": 300,
        },
        {
            "title": "The Three-Layer Architecture",
            "purpose": "Core concept",
            "key_points": ["Conductor", "Sprint Master", "Worker"],
            "estimated_words": 500,
        },
        {
            "title": "Building the Conductor",
            "purpose": "Implementation",
            "key_points": ["State management", "Sprint dispatch"],
            "estimated_words": 600,
        },
        {
            "title": "Context Isolation in Practice",
            "purpose": "Key insight",
            "key_points": ["Fresh context per layer"],
            "estimated_words": 400,
        },
        {
            "title": "Results and Lessons",
            "purpose": "Evidence",
            "key_points": ["Metrics", "Gotchas"],
            "estimated_words": 300,
        },
    ],
    "target_word_count": 2100,
    "tone": "Practical, code-heavy",
}

OUTLINE_B = {
    "variant": "B",
    "variant_name": "Deep Dive",
    "title": "Why Multi-Agent Architecture Beats Monolithic AI",
    "hook": "A deep dive hook",
    "sections": [
        {
            "title": "The Monolith Trap",
            "purpose": "Problem space",
            "key_points": ["Why single agents fail"],
            "estimated_words": 400,
        },
        {
            "title": "Architectural Principles",
            "purpose": "Framework",
            "key_points": ["Separation of concerns"],
            "estimated_words": 600,
        },
        {
            "title": "The Conductor Pattern",
            "purpose": "Core pattern",
            "key_points": ["Orchestration vs execution"],
            "estimated_words": 500,
        },
        {
            "title": "Trade-offs and When Not To",
            "purpose": "Nuance",
            "key_points": ["Overhead", "Simple tasks"],
            "estimated_words": 400,
        },
        {
            "title": "A Production Implementation",
            "purpose": "Evidence",
            "key_points": ["Real code", "Real metrics"],
            "estimated_words": 500,
        },
    ],
    "target_word_count": 2400,
    "tone": "Authoritative, analytical",
}

OUTLINE_C = {
    "variant": "C",
    "variant_name": "Narrative",
    "title": "The Day Our AI Agent Forgot Everything",
    "hook": "A narrative hook",
    "sections": [
        {
            "title": "The Incident",
            "purpose": "Hook/crisis",
            "key_points": ["What went wrong"],
            "estimated_words": 300,
        },
        {
            "title": "The Investigation",
            "purpose": "Journey",
            "key_points": ["Context window as root cause"],
            "estimated_words": 400,
        },
        {
            "title": "The Breakthrough",
            "purpose": "Insight",
            "key_points": ["Multi-agent as the solution"],
            "estimated_words": 500,
        },
        {
            "title": "Building It",
            "purpose": "Implementation",
            "key_points": ["Architecture decisions"],
            "estimated_words": 500,
        },
        {
            "title": "What We Learned",
            "purpose": "Takeaway",
            "key_points": ["Principles that generalize"],
            "estimated_words": 300,
        },
    ],
    "target_word_count": 2000,
    "tone": "Personal, engaging",
}


@pytest.fixture
def project_with_outlines(tmp_path):
    """Create a project directory with all three outline variants."""
    proj = tmp_path / "test-proj"
    state = proj / ".essay-state"
    state.mkdir(parents=True)

    (state / "outline-A.json").write_text(json.dumps(OUTLINE_A))
    (state / "outline-B.json").write_text(json.dumps(OUTLINE_B))
    (state / "outline-C.json").write_text(json.dumps(OUTLINE_C))

    return str(proj)


@pytest.fixture
def project_one_variant(tmp_path):
    """Create a project directory with only outline A."""
    proj = tmp_path / "test-proj2"
    state = proj / ".essay-state"
    state.mkdir(parents=True)

    (state / "outline-A.json").write_text(json.dumps({
        "variant": "A",
        "variant_name": "Test",
        "title": "Test",
        "sections": [
            {"title": "S1", "purpose": "p", "key_points": [], "estimated_words": 100}
        ],
    }))

    return str(proj)


@pytest.fixture
def project_no_outlines(tmp_path):
    """Create a project directory with .essay-state but no outline files."""
    proj = tmp_path / "test-proj3"
    state = proj / ".essay-state"
    state.mkdir(parents=True)
    return str(proj)


@pytest.fixture
def project_no_state(tmp_path):
    """Create a project directory with no .essay-state directory."""
    proj = tmp_path / "test-proj4"
    proj.mkdir(parents=True)
    return str(proj)


def mixed_path(project_dir):
    """Return the path to the mixed outline file."""
    return os.path.join(project_dir, ".essay-state", "outline-mixed.json")


def read_mixed(project_dir):
    """Read and parse the mixed outline JSON."""
    with open(mixed_path(project_dir)) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 1-2: List command
# ═══════════════════════════════════════════════════════════════════════════════


class TestListCommand:
    """List command shows all variants with section details."""

    def test_list_shows_all_variants(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "list")
        out = r.stdout + r.stderr
        assert "Outline A" in out
        assert "Outline B" in out
        assert "Outline C" in out
        assert "Tutorial" in out
        assert "Deep Dive" in out
        assert "Narrative" in out

    def test_list_shows_section_details(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "list")
        out = r.stdout + r.stderr
        assert "The Problem with Monolithic Agents" in out
        assert "1." in out
        assert "Purpose:" in out
        assert "words" in out
        assert "Key points:" in out
        assert "Total variants available: 3" in out


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 3-4: Basic mix
# ═══════════════════════════════════════════════════════════════════════════════


class TestBasicMix:
    """Basic mix -- take sections from each variant."""

    def test_mix_succeeds(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:1,2 B:3,4 C:5")
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out
        assert os.path.isfile(mixed_path(project_with_outlines))

        data = read_mixed(project_with_outlines)
        assert len(data["sections"]) == 5
        assert data["variant"] == "mixed"

    def test_mixed_section_order(self, run_script, project_with_outlines):
        """Verify section order after mixing A:1,2 B:3,4 C:5."""
        run_script("outline_mixer", project_with_outlines, "A:1,2 B:3,4 C:5")
        data = read_mixed(project_with_outlines)
        titles = [s["title"] for s in data["sections"]]
        assert titles[0] == "The Problem with Monolithic Agents"
        assert titles[1] == "The Three-Layer Architecture"
        assert titles[2] == "The Conductor Pattern"
        assert titles[3] == "Trade-offs and When Not To"
        assert titles[4] == "What We Learned"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 5-7: Source map, word count, mix spec
# ═══════════════════════════════════════════════════════════════════════════════


class TestMixMetadata:
    """Source map, word count, and mix spec are recorded correctly."""

    @pytest.fixture(autouse=True)
    def _do_mix(self, run_script, project_with_outlines):
        self.proj = project_with_outlines
        run_script("outline_mixer", project_with_outlines, "A:1,2 B:3,4 C:5")
        self.data = read_mixed(project_with_outlines)

    def test_source_map_length(self):
        assert len(self.data["source_map"]) == 5

    def test_source_map_entries(self):
        entries = [
            f'{sm["variant"]}:{sm["original_section"]}'
            for sm in self.data["source_map"]
        ]
        assert "A:1" in entries
        assert "A:2" in entries
        assert "B:3" in entries
        assert "B:4" in entries
        assert "C:5" in entries

    def test_word_count_sums_correctly(self):
        # A:1=300, A:2=500, B:3=500, B:4=400, C:5=300 => 2000
        assert self.data["target_word_count"] == 2000

    def test_mix_spec_recorded(self):
        assert self.data["mix_spec"] == "A:1,2 B:3,4 C:5"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Summary output shows mapping
# ═══════════════════════════════════════════════════════════════════════════════


class TestSummaryOutput:
    """Summary output shows section mapping details."""

    def test_summary_shows_mapping(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:1 B:2 C:3")
        out = r.stdout + r.stderr
        assert "[A:1]" in out
        assert "[B:2]" in out
        assert "[C:3]" in out
        assert "Sections: 3" in out


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 9-10: Single variant and single section
# ═══════════════════════════════════════════════════════════════════════════════


class TestSingleVariantAndSection:
    """Mix all sections from one variant or just one section."""

    def test_all_sections_from_single_variant(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:1,2,3,4,5")
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out

        data = read_mixed(project_with_outlines)
        assert len(data["sections"]) == 5
        # A total: 300+500+600+400+300 = 2100
        assert data["target_word_count"] == 2100

    def test_single_section_only(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "C:3")
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out

        data = read_mixed(project_with_outlines)
        assert len(data["sections"]) == 1
        assert data["sections"][0]["title"] == "The Breakthrough"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 11-20: Error handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrors:
    """Error handling for invalid inputs."""

    def test_invalid_variant_letter(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "D:1,2")
        combined = r.stdout + r.stderr
        assert "Invalid spec token" in combined

    def test_section_out_of_range(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:6")
        combined = r.stdout + r.stderr
        assert "out of range" in combined

    def test_section_zero(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:0")
        combined = r.stdout + r.stderr
        assert "out of range" in combined

    def test_negative_section(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:-1")
        combined = r.stdout + r.stderr
        assert "ERROR" in combined

    def test_non_numeric_section(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:foo")
        combined = r.stdout + r.stderr
        assert "Invalid section number" in combined

    def test_missing_variant_file(self, run_script, project_one_variant):
        r = run_script("outline_mixer", project_one_variant, "B:1")
        combined = r.stdout + r.stderr
        assert "not found" in combined.lower()

    def test_no_outlines_at_all(self, run_script, project_no_outlines):
        r = run_script("outline_mixer", project_no_outlines, "A:1")
        combined = r.stdout + r.stderr
        assert "No outline variants found" in combined

    def test_no_state_directory(self, run_script, project_no_state):
        r = run_script("outline_mixer", project_no_state, "A:1")
        combined = r.stdout + r.stderr
        assert "State directory not found" in combined

    def test_empty_spec(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "")
        combined = r.stdout + r.stderr
        assert "Usage" in combined or "ERROR" in combined or "sections_spec" in combined

    def test_duplicate_section_reference(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:1 A:1")
        combined = r.stdout + r.stderr
        assert "Duplicate section reference" in combined


# ═══════════════════════════════════════════════════════════════════════════════
# Test 21: Lowercase variant letter
# ═══════════════════════════════════════════════════════════════════════════════


class TestLowercaseVariant:
    """Lowercase variant letters are accepted."""

    def test_lowercase_variant_accepted(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "a:1 b:2 c:3")
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out

        data = read_mixed(project_with_outlines)
        assert len(data["sections"]) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 22-23: List with partial/no variants
# ═══════════════════════════════════════════════════════════════════════════════


class TestListEdgeCases:
    """List command with one variant or no variants."""

    def test_list_with_one_variant(self, run_script, project_one_variant):
        r = run_script("outline_mixer", project_one_variant, "list")
        out = r.stdout + r.stderr
        assert "Outline A" in out
        assert "Outline B" not in out
        assert "Total variants available: 1" in out

    def test_list_with_no_variants(self, run_script, project_no_outlines):
        r = run_script("outline_mixer", project_no_outlines, "list")
        combined = r.stdout + r.stderr
        assert "No outline variants found" in combined


# ═══════════════════════════════════════════════════════════════════════════════
# Test 24: Mix preserves key_points and purpose
# ═══════════════════════════════════════════════════════════════════════════════


class TestPreserveSectionData:
    """Mix preserves key_points and purpose in sections."""

    def test_preserves_key_points(self, run_script, project_with_outlines):
        run_script("outline_mixer", project_with_outlines, "A:1 B:2")
        data = read_mixed(project_with_outlines)

        kp = data["sections"][0]["key_points"]
        assert "Context overflow" in kp
        assert "Tangled concerns" in kp

    def test_preserves_purpose(self, run_script, project_with_outlines):
        run_script("outline_mixer", project_with_outlines, "A:1 B:2")
        data = read_mixed(project_with_outlines)
        assert data["sections"][1]["purpose"] == "Framework"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 25: Non-contiguous sections
# ═══════════════════════════════════════════════════════════════════════════════


class TestNonContiguousSections:
    """Mix with non-contiguous section numbers."""

    def test_non_contiguous_sections(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "A:1,5 B:2,4")
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out

        data = read_mixed(project_with_outlines)
        assert len(data["sections"]) == 4

        titles = [s["title"] for s in data["sections"]]
        assert "The Problem with Monolithic Agents" in titles
        assert "Results and Lessons" in titles
        assert "Architectural Principles" in titles
        assert "Trade-offs and When Not To" in titles


# ═══════════════════════════════════════════════════════════════════════════════
# Test 26: Help flag
# ═══════════════════════════════════════════════════════════════════════════════


class TestHelpFlag:
    """Help flag shows usage information."""

    def test_help_shows_usage(self, run_script, project_with_outlines):
        r = run_script("outline_mixer", project_with_outlines, "--help")
        out = r.stdout + r.stderr
        assert "Usage:" in out
        assert "VARIANT:SECTIONS" in out


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 27-28: Orchestrate integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrchestrateIntegration:
    """Orchestrate build-outline-mix integration."""

    def test_orchestrate_list(self, run_script, project_with_outlines, script_dir):
        r = run_script(
            "orchestrate",
            project_with_outlines,
            script_dir,
            "build-outline-mix",
            "list",
        )
        out = r.stdout + r.stderr
        assert "Outline A" in out
        assert "Total variants available" in out

    def test_orchestrate_mix(self, run_script, project_with_outlines, script_dir):
        # Remove any existing mixed file first
        mp = mixed_path(project_with_outlines)
        if os.path.isfile(mp):
            os.remove(mp)

        r = run_script(
            "orchestrate",
            project_with_outlines,
            script_dir,
            "build-outline-mix",
            "A:1 B:2 C:3",
        )
        out = r.stdout + r.stderr
        assert "Mixed outline assembled successfully" in out
        assert os.path.isfile(mp)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 29: Overwrite previous mixed outline
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverwrite:
    """Overwriting a previous mixed outline."""

    def test_overwrite_previous_mix(self, run_script, project_with_outlines):
        run_script("outline_mixer", project_with_outlines, "A:1,2,3")
        data1 = read_mixed(project_with_outlines)
        assert len(data1["sections"]) == 3

        run_script("outline_mixer", project_with_outlines, "B:1,2")
        data2 = read_mixed(project_with_outlines)
        assert len(data2["sections"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Test 30: Placeholder fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestPlaceholderFields:
    """Mixed outline has placeholder fields for title, hook, variant_name."""

    def test_placeholder_fields(self, run_script, project_with_outlines):
        run_script("outline_mixer", project_with_outlines, "A:1 C:5")
        data = read_mixed(project_with_outlines)

        assert data["variant_name"] == "Mixed (cherry-picked)"
        assert "mixed" in data["title"].lower()
        assert "mixed" in data["hook"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 31: No arguments shows usage
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoArguments:
    """No arguments shows usage information."""

    def test_no_args_shows_usage(self, run_script):
        r = run_script("outline_mixer")
        combined = r.stdout + r.stderr
        assert "Usage:" in combined
