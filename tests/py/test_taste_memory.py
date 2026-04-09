"""Tests for taste_memory.py — diff-learn, feedback, and suggest commands."""

import json
import os

import pytest


TASTE_REL = os.path.join(".tech-essay-writer", "taste-memory.json")


def taste_file(home):
    return os.path.join(home, TASTE_REL)


def read_taste(home):
    with open(taste_file(home)) as f:
        return json.load(f)


def write_taste(home, data):
    path = taste_file(home)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def reset_taste(home):
    write_taste(home, {})


# ============================================================
# diff-learn tests
# ============================================================


class TestDiffLearnBasic:
    """Basic diff-learn functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_basic_diff_learn_produces_output(self):
        """Test 1: basic diff-learn produces output."""
        self._write_files(
            "# Introduction\n\nThis is a basic article about testing.\n\n"
            "## Section One\n\nSome content here about testing stuff.\n",
            "# Introduction\n\nThis is a comprehensive guide to software testing methodologies.\n\n"
            "## Section One\n\nFurthermore, testing ensures software quality and reliability.\n\n"
            "## Section Two\n\nAdditional content about integration testing.\n",
        )
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "Learned from diff" in r.stdout

    def test_diff_learn_creates_taste_file(self):
        """Test 2: diff-learn creates taste-memory.json."""
        self._write_files("Original.\n", "Edited.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert os.path.isfile(taste_file(self.home))

    def test_learned_patterns_key_exists(self):
        """Test 3: learned_patterns key exists."""
        self._write_files("Original.\n", "Edited.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert "learned_patterns" in data

    def test_pattern_has_project_field(self):
        """Test 4: pattern has project field."""
        self._write_files("Original.\n", "Edited.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["project"] == self.project

    def test_pattern_has_timestamp(self):
        """Test 5: pattern has timestamp."""
        self._write_files("Original.\n", "Edited.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert "timestamp" in data["learned_patterns"][-1]

    def test_detects_section_additions(self):
        """Test 6: detects section additions."""
        self._write_files(
            "# Introduction\n\nThis is a basic article about testing.\n\n"
            "## Section One\n\nSome content here about testing stuff.\n",
            "# Introduction\n\nThis is a comprehensive guide to software testing methodologies.\n\n"
            "## Section One\n\nFurthermore, testing ensures software quality and reliability.\n\n"
            "## Section Two\n\nAdditional content about integration testing.\n",
        )
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "section" in r.stdout.lower()

    def test_detects_insights(self):
        """Test 7: detects insights."""
        self._write_files(
            "# Introduction\n\nThis is a basic article about testing.\n\n"
            "## Section One\n\nSome content here about testing stuff.\n",
            "# Introduction\n\nThis is a comprehensive guide to software testing methodologies.\n\n"
            "## Section One\n\nFurthermore, testing ensures software quality and reliability.\n\n"
            "## Section Two\n\nAdditional content about integration testing.\n",
        )
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "Insights" in r.stdout


class TestDiffLearnErrors:
    """diff-learn error handling."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")
        with open(self.edited, "w") as f:
            f.write("Some content.\n")
        with open(self.orig, "w") as f:
            f.write("Some content.\n")

    def test_missing_original_file(self, tmp_path):
        """Test 8: diff-learn with missing original file."""
        r = self.run(
            "taste_memory", "diff-learn", self.project,
            str(tmp_path / "nonexistent.md"), self.edited,
        )
        assert r.returncode != 0

    def test_missing_edited_file(self, tmp_path):
        """Test 9: diff-learn with missing edited file."""
        r = self.run(
            "taste_memory", "diff-learn", self.project,
            self.orig, str(tmp_path / "nonexistent.md"),
        )
        assert r.returncode != 0


class TestDiffLearnLengthDetection:
    """diff-learn length change detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_detects_expansion(self):
        """Test 10: diff-learn detects expansion."""
        self._write_files(
            "# Introduction\n\nThis is a basic article about testing.\n\n"
            "## Section One\n\nSome content here about testing stuff.\n",
            "# Introduction\n\nThis is a comprehensive guide to software testing methodologies.\n\n"
            "## Section One\n\nFurthermore, testing ensures software quality and reliability.\n\n"
            "## Section Two\n\nAdditional content about integration testing.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["length_change"] == "expanded"

    def test_length_ratio_above_one_for_expanded(self):
        """Test 11: diff-learn length_ratio > 1 for expanded."""
        self._write_files(
            "# Introduction\n\nThis is a basic article about testing.\n\n"
            "## Section One\n\nSome content here about testing stuff.\n",
            "# Introduction\n\nThis is a comprehensive guide to software testing methodologies.\n\n"
            "## Section One\n\nFurthermore, testing ensures software quality and reliability.\n\n"
            "## Section Two\n\nAdditional content about integration testing.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["length_ratio"] > 1.0

    def test_detects_condensation(self):
        """Test 12: diff-learn detects condensation."""
        reset_taste(self.home)
        self._write_files(
            "# A Very Long Article\n\n"
            "This article contains a lot of unnecessary filler content that should be removed. "
            "It goes on and on about things that are not really relevant to the main point. "
            "Furthermore, it has many paragraphs that repeat the same ideas over and over again "
            "without adding new information.\n\n"
            "## Section One\n\n"
            "The first section has way too much text. It explains things in excruciating detail "
            "when a simple sentence would suffice. The reader would benefit from a more concise "
            "presentation.\n\n"
            "## Section Two\n\n"
            "The second section also suffers from verbosity. Every concept is explained three "
            "different ways when once would be enough.\n\n"
            "## Section Three\n\n"
            "Yet another section full of redundant content.\n",
            "# A Concise Article\n\nEssential content only.\n\n## Key Points\n\nBrief, focused explanation.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["length_change"] == "condensed"

    def test_condensation_detects_concise_preference(self):
        """Test 13: diff-learn detects concise preference from condensation."""
        reset_taste(self.home)
        self._write_files(
            "# A Very Long Article\n\n"
            "This article contains a lot of unnecessary filler content that should be removed. "
            "It goes on and on about things that are not really relevant to the main point. "
            "Furthermore, it has many paragraphs that repeat the same ideas over and over again "
            "without adding new information.\n\n"
            "## Section One\n\n"
            "The first section has way too much text. It explains things in excruciating detail "
            "when a simple sentence would suffice. The reader would benefit from a more concise "
            "presentation.\n\n"
            "## Section Two\n\n"
            "The second section also suffers from verbosity. Every concept is explained three "
            "different ways when once would be enough.\n\n"
            "## Section Three\n\n"
            "Yet another section full of redundant content.\n",
            "# A Concise Article\n\nEssential content only.\n\n## Key Points\n\nBrief, focused explanation.\n",
        )
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "concise" in r.stdout.lower()

    def test_identical_files_show_similar(self):
        """Test 14: diff-learn with identical files."""
        reset_taste(self.home)
        content = "# Same Content\nIdentical text.\n"
        self._write_files(content, content)
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["length_change"] == "similar"


class TestDiffLearnStructure:
    """diff-learn structure and tone detection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_detects_section_reordering(self):
        """Test 15: diff-learn detects structure reordering."""
        reset_taste(self.home)
        self._write_files(
            "# Title\n\n## Alpha Section\n\nContent A.\n\n"
            "## Beta Section\n\nContent B.\n\n"
            "## Gamma Section\n\nContent C.\n",
            "# Title\n\n## Gamma Section\n\nContent C.\n\n"
            "## Alpha Section\n\nContent A.\n\n"
            "## Beta Section\n\nContent B.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        sc = data["learned_patterns"][-1].get("structure_changes", [])
        types = [c["type"] for c in sc]
        assert "sections_reordered" in types

    def test_detects_formal_tone_shift(self):
        """Test 16: diff-learn detects formal tone shift."""
        reset_taste(self.home)
        self._write_files(
            "This is basically just a really cool thing that's actually pretty awesome. "
            "You basically just do stuff and things happen.\n",
            "This consequently represents a significant advancement. Furthermore, the methodology "
            "provides substantial benefits. Moreover, the approach yields considerable improvements. "
            "Additionally, the framework demonstrates robust capabilities. Nevertheless, further "
            "research is warranted.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["tone_shift"] == "more_formal"

    def test_records_word_replacements(self):
        """Test 17: diff-learn records word replacements."""
        reset_taste(self.home)
        self._write_files(
            "Use the simple method to build the thing.\n",
            "Use the comprehensive approach to construct the application.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert "word_replacements" in json.dumps(data)

    def test_records_diff_stats(self):
        """Test 18: diff-learn records diff_stats."""
        reset_taste(self.home)
        self._write_files(
            "Use the simple method to build the thing.\n",
            "Use the comprehensive approach to construct the application.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert "diff_stats" in data["learned_patterns"][-1]


class TestDiffLearnCapping:
    """diff-learn entry capping and paragraph tracking."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_caps_learned_patterns_at_50(self):
        """Test 19: diff-learn caps learned_patterns at 50."""
        reset_taste(self.home)
        for i in range(55):
            self._write_files(
                f"# Article {i}\nContent version {i} original.\n",
                f"# Article {i}\nContent version {i} edited with changes.\n",
            )
            self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert len(data["learned_patterns"]) == 50

    def test_records_positive_paragraph_delta(self):
        """Test 20: diff-learn records paragraph_delta."""
        reset_taste(self.home)
        self._write_files(
            "# Title\n\nOne paragraph.\n",
            "# Title\n\nParagraph one.\n\nParagraph two.\n\nParagraph three.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["paragraph_delta"] > 0


# ============================================================
# feedback tests
# ============================================================


class TestFeedbackBasic:
    """Basic feedback functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        reset_taste(self.home)

    def test_feedback_stores_tone(self):
        """Test 21: feedback stores tone."""
        r = self.run("taste_memory", "feedback", self.project, "tone",
                      "prefer casual conversational tone")
        assert "Feedback recorded" in r.stdout
        assert "tone" in r.stdout

    def test_feedback_stores_in_explicit_preferences(self):
        """Test 22: feedback stores in explicit_preferences."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        data = read_taste(self.home)
        assert "explicit_preferences" in data

    def test_feedback_has_correct_category(self):
        """Test 23: feedback has correct category."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        data = read_taste(self.home)
        assert data["explicit_preferences"][-1]["category"] == "tone"

    def test_feedback_has_correct_text(self):
        """Test 24: feedback has correct text."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        data = read_taste(self.home)
        assert data["explicit_preferences"][-1]["feedback"] == "prefer casual conversational tone"

    def test_feedback_stores_project_dir(self):
        """Test 25: feedback stores project dir."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        data = read_taste(self.home)
        assert data["explicit_preferences"][-1]["project"] == self.project

    def test_feedback_stores_timestamp(self):
        """Test 26: feedback stores timestamp."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        data = read_taste(self.home)
        assert "timestamp" in data["explicit_preferences"][-1]


class TestFeedbackCategories:
    """Feedback category acceptance and rejection."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        reset_taste(self.home)

    def test_accepts_structure_category(self):
        """Test 27: feedback accepts structure category."""
        r = self.run("taste_memory", "feedback", self.project, "structure",
                      "use numbered lists for steps")
        assert "Feedback recorded" in r.stdout

    def test_accepts_vocabulary_category(self):
        """Test 28: feedback accepts vocabulary category."""
        r = self.run("taste_memory", "feedback", self.project, "vocabulary",
                      "avoid jargon")
        assert "Feedback recorded" in r.stdout

    def test_accepts_length_category(self):
        """Test 29: feedback accepts length category."""
        r = self.run("taste_memory", "feedback", self.project, "length",
                      "keep articles under 2000 words")
        assert "Feedback recorded" in r.stdout

    def test_accepts_code_density_category(self):
        """Test 30: feedback accepts code_density category."""
        r = self.run("taste_memory", "feedback", self.project, "code_density",
                      "more code examples please")
        assert "Feedback recorded" in r.stdout

    def test_accepts_format_category(self):
        """Test 31: feedback accepts format category."""
        r = self.run("taste_memory", "feedback", self.project, "format",
                      "use callout boxes for tips")
        assert "Feedback recorded" in r.stdout

    def test_rejects_invalid_category(self):
        """Test 32: feedback rejects invalid category."""
        r = self.run("taste_memory", "feedback", self.project, "invalid_cat",
                      "some text")
        assert r.returncode != 0

    def test_rejects_empty_category(self):
        """Test 33: feedback rejects empty category."""
        r = self.run("taste_memory", "feedback", self.project, "", "some text")
        assert r.returncode != 0


class TestFeedbackAccumulation:
    """Feedback accumulation and capping."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        reset_taste(self.home)

    def test_multiple_feedback_entries_accumulate(self):
        """Test 34: multiple feedback entries accumulate."""
        self.run("taste_memory", "feedback", self.project, "tone",
                 "prefer casual conversational tone")
        self.run("taste_memory", "feedback", self.project, "structure",
                 "use numbered lists for steps")
        self.run("taste_memory", "feedback", self.project, "vocabulary",
                 "avoid jargon")
        self.run("taste_memory", "feedback", self.project, "length",
                 "keep articles under 2000 words")
        self.run("taste_memory", "feedback", self.project, "code_density",
                 "more code examples please")
        self.run("taste_memory", "feedback", self.project, "format",
                 "use callout boxes for tips")
        data = read_taste(self.home)
        assert len(data["explicit_preferences"]) == 6

    def test_feedback_caps_at_100(self):
        """Test 35: feedback caps at 100."""
        reset_taste(self.home)
        for i in range(105):
            self.run("taste_memory", "feedback", self.project, "tone",
                     f"preference number {i}")
        data = read_taste(self.home)
        assert len(data["explicit_preferences"]) == 100


# ============================================================
# suggest tests
# ============================================================


class TestSuggestEmpty:
    """Suggest with no or minimal data."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)

    def test_suggest_with_no_data(self):
        """Test 36: suggest with no data."""
        reset_taste(self.home)
        r = self.run("taste_memory", "suggest", self.project)
        assert "No taste data" in r.stdout


class TestSuggestWithFeedback:
    """Suggest output from explicit feedback."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)

    def test_suggest_with_only_feedback_shows_preferences(self):
        """Test 37: suggest with only feedback shows preferences."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "tone", "be more informal")
        self.run("taste_memory", "feedback", self.project, "structure",
                 "lead with the conclusion")
        r = self.run("taste_memory", "suggest", self.project)
        assert "informal" in r.stdout
        assert "conclusion" in r.stdout

    def test_suggest_shows_header(self):
        """Test 38: suggest shows header."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "tone", "be more informal")
        r = self.run("taste_memory", "suggest", self.project)
        assert "Personalized Writing Suggestions" in r.stdout

    def test_suggest_shows_code_density_feedback(self):
        """Test 45: suggest shows code density feedback."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "code_density",
                 "always include runnable examples")
        r = self.run("taste_memory", "suggest", self.project)
        assert "runnable examples" in r.stdout

    def test_suggest_shows_vocabulary_feedback(self):
        """Test 46: suggest shows vocabulary feedback."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "vocabulary",
                 "use simple words, no acronyms")
        r = self.run("taste_memory", "suggest", self.project)
        assert "simple words" in r.stdout

    def test_suggest_shows_format_feedback(self):
        """Test 47: suggest shows format feedback."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "format",
                 "always use tables for comparisons")
        r = self.run("taste_memory", "suggest", self.project)
        assert "tables" in r.stdout

    def test_suggest_shows_length_feedback(self):
        """Test 48: suggest shows length feedback."""
        reset_taste(self.home)
        self.run("taste_memory", "feedback", self.project, "length", "max 1500 words")
        r = self.run("taste_memory", "suggest", self.project)
        assert "1500" in r.stdout


class TestSuggestWithDiffLearn:
    """Suggest output from diff-learn patterns."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_suggest_shows_tone_shift(self):
        """Test 39: suggest with diff-learn data shows tone shift."""
        reset_taste(self.home)
        self._write_files(
            "This is basically just a really cool thing. Stuff happens when you do things.\n",
            "This consequently represents a significant advancement. Furthermore, the methodology "
            "demonstrates considerable promise. Moreover, the results are noteworthy.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        assert "formal" in r.stdout

    def test_suggest_shows_condensation_action(self):
        """Test 40: suggest with condensation pattern shows action item."""
        reset_taste(self.home)
        self._write_files(
            "This is a very long and unnecessarily verbose piece of text that goes on and on "
            "about nothing in particular. It contains many redundant words and phrases that add "
            "no value. The reader would benefit greatly from a more concise and focused "
            "presentation of these ideas.\n",
            "Concise text. Focused.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        output = r.stdout.lower()
        assert "condense" in output or "concise" in output or "cut" in output

    def test_suggest_shows_expansion_action(self):
        """Test 41: suggest with expansion pattern shows action item."""
        reset_taste(self.home)
        self._write_files(
            "Brief.\n",
            "This is a much more detailed and comprehensive explanation of the topic at hand. "
            "It includes additional context, examples, and supporting evidence to help the "
            "reader understand the nuances better.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        output = r.stdout.lower()
        assert "expand" in output or "detail" in output or "example" in output

    def test_suggest_shows_action_items_section(self):
        """Test 42: suggest shows Action Items section when patterns present."""
        reset_taste(self.home)
        self._write_files(
            "Brief.\n",
            "This is a much more detailed and comprehensive explanation of the topic at hand. "
            "It includes additional context, examples, and supporting evidence to help the "
            "reader understand the nuances better.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        assert "Action Items" in r.stdout

    def test_suggest_shows_structure_patterns(self):
        """Test 43: suggest shows structure patterns from diff-learn."""
        reset_taste(self.home)
        self._write_files(
            "# Title\n\n## Only Section\n\nContent.\n",
            "# Title\n\n## First Section\n\nContent.\n\n"
            "## Second Section\n\nMore content.\n\n"
            "## Third Section\n\nEven more.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        output = r.stdout
        assert "Structure patterns" in output or "sections added" in output

    def test_suggest_shows_word_replacements(self):
        """Test 44: suggest shows word replacements."""
        reset_taste(self.home)
        self._write_files(
            "Use the simple method to build the thing.\n",
            "Use the comprehensive approach to construct the application.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        output = r.stdout
        assert "replacements" in output or "Recurring" in output


class TestSuggestCombined:
    """Suggest output combining diff-learn and feedback data."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_suggest_combines_diff_learn_and_feedback(self):
        """Test 49: suggest combines learned patterns and explicit preferences."""
        reset_taste(self.home)
        self._write_files(
            "This is basically just a test.\n",
            "This consequently represents a thorough examination. Furthermore, the analysis "
            "is comprehensive. Moreover, the findings are significant.\n",
        )
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        self.run("taste_memory", "feedback", self.project, "tone",
                 "always be authoritative")
        self.run("taste_memory", "feedback", self.project, "structure",
                 "put TL;DR first")
        r = self.run("taste_memory", "suggest", self.project)
        assert "authoritative" in r.stdout
        assert "TL;DR" in r.stdout

    def test_suggest_with_record_choice_structural_prefs(self):
        """Test 50: suggest with record-choice structural prefs."""
        reset_taste(self.home)
        self.run("taste_memory", "record-choice", "code_density", "high")
        r = self.run("taste_memory", "suggest", self.project)
        assert "code_density" in r.stdout

    def test_suggest_shows_recurring_insights(self):
        """Test 51: suggest shows recurring insights."""
        reset_taste(self.home)
        for i in range(1, 4):
            self._write_files(
                f"# Article {i}\n\nThis is basically just some really cool stuff.\n",
                f"# Article {i}\n\nComprehensive analysis of the subject matter.\n\n"
                f"## Additional Section {i}\n\nMore details here.\n",
            )
            self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "suggest", self.project)
        assert "Recurring insights" in r.stdout


# ============================================================
# read integration tests
# ============================================================


class TestReadIntegration:
    """Integration tests for the read command."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")
        reset_taste(self.home)

    def test_read_shows_learned_patterns(self):
        """Test 52: read shows learned patterns."""
        with open(self.orig, "w") as f:
            f.write("Original text.\n")
        with open(self.edited, "w") as f:
            f.write("Edited text with changes.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        r = self.run("taste_memory", "read")
        assert "Learned patterns" in r.stdout

    def test_read_shows_explicit_preferences(self):
        """Test 53: read shows explicit preferences."""
        with open(self.orig, "w") as f:
            f.write("Original text.\n")
        with open(self.edited, "w") as f:
            f.write("Edited text with changes.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        self.run("taste_memory", "feedback", self.project, "tone", "conversational")
        r = self.run("taste_memory", "read")
        assert "Explicit preferences" in r.stdout

    def test_read_shows_project_in_learned_patterns(self):
        """Test 54: read shows project in learned patterns."""
        with open(self.orig, "w") as f:
            f.write("Original text.\n")
        with open(self.edited, "w") as f:
            f.write("Edited text with changes.\n")
        self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        self.run("taste_memory", "feedback", self.project, "tone", "conversational")
        r = self.run("taste_memory", "read")
        assert "project:" in r.stdout


# ============================================================
# edge case tests
# ============================================================


class TestEdgeCases:
    """Edge case tests for taste memory."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home, tmp_path):
        self.run = run_script
        self.home = fake_home
        self.project = str(tmp_path / "test-project")
        os.makedirs(self.project, exist_ok=True)
        self.orig = str(tmp_path / "original.md")
        self.edited = str(tmp_path / "edited.md")

    def _write_files(self, orig_content, edited_content):
        with open(self.orig, "w") as f:
            f.write(orig_content)
        with open(self.edited, "w") as f:
            f.write(edited_content)

    def test_diff_learn_with_empty_original(self):
        """Test 55: diff-learn with empty original."""
        reset_taste(self.home)
        self._write_files("", "# New Content\nBrand new article.\n")
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "Learned from diff" in r.stdout

    def test_diff_learn_with_empty_edited(self):
        """Test 56: diff-learn with empty edited."""
        reset_taste(self.home)
        self._write_files("# Content\nSome content.\n", "")
        r = self.run("taste_memory", "diff-learn", self.project, self.orig, self.edited)
        assert "Learned from diff" in r.stdout
        data = read_taste(self.home)
        assert data["learned_patterns"][-1]["length_change"] == "condensed"

    def test_feedback_with_long_text(self):
        """Test 57: feedback with long text."""
        reset_taste(self.home)
        long_text = (
            "This is a very long feedback message that contains more than a hundred "
            "characters and should still be stored correctly without truncation or "
            "corruption in the taste memory JSON file."
        )
        r = self.run("taste_memory", "feedback", self.project, "tone", long_text)
        assert "Feedback recorded" in r.stdout
        data = read_taste(self.home)
        assert data["explicit_preferences"][-1]["feedback"] == long_text

    def test_feedback_with_special_characters(self):
        """Test 58: feedback with special characters."""
        reset_taste(self.home)
        r = self.run("taste_memory", "feedback", self.project, "tone",
                      "use em-dashes -- not hyphens")
        assert "Feedback recorded" in r.stdout

    def test_suggest_with_only_record_choice_tone(self):
        """Test 59: suggest with only record-choice tone."""
        reset_taste(self.home)
        self.run("taste_memory", "record-choice", "tone", "technical")
        r = self.run("taste_memory", "suggest", self.project)
        assert "technical" in r.stdout

    def test_suggest_with_legacy_feedback_patterns(self):
        """Test 60: suggest with legacy feedback_patterns."""
        reset_taste(self.home)
        self.run("taste_memory", "record-choice", "feedback", "legacy pattern")
        r = self.run("taste_memory", "suggest", self.project)
        assert "legacy pattern" in r.stdout
