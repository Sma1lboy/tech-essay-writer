"""Tests for author_profile.py, expertise_graph.py, social-package.md prompt,
and orchestrate.py build-social-prompt / build-format-prompts."""

import json
import os

import pytest


# ============================================================
# Helpers
# ============================================================


def write_json_file(path, data):
    """Write a JSON file to the given path, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def read_file(path):
    """Read and return file contents as a string."""
    with open(path) as f:
        return f.read()


# ============================================================
# author_profile.py tests
# ============================================================


class TestAuthorProfileInit:
    """Test init and idempotent init."""

    def test_init_creates_profile(self, run_script, fake_home):
        r = run_script("author_profile", "init")
        assert "initialized" in r.stdout

    def test_init_creates_file(self, run_script, fake_home):
        run_script("author_profile", "init")
        profile_path = os.path.join(fake_home, ".tech-essay-writer", "author-profile.json")
        assert os.path.isfile(profile_path)

    def test_init_idempotent(self, run_script, fake_home):
        run_script("author_profile", "init")
        r = run_script("author_profile", "init")
        assert "already exists" in r.stdout


class TestAuthorProfileSetFields:
    """Test setting profile fields (name, role, company, bio)."""

    @pytest.fixture(autouse=True)
    def _init_profile(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("author_profile", "init")

    def test_set_name(self):
        r = self.run("author_profile", "set", "name", "Alice Chen")
        assert "Set name" in r.stdout

    def test_set_role(self):
        r = self.run("author_profile", "set", "role", "Senior Engineer")
        assert "Set role" in r.stdout

    def test_set_company(self):
        r = self.run("author_profile", "set", "company", "TechCorp")
        assert "Set company" in r.stdout

    def test_set_bio(self):
        r = self.run("author_profile", "set", "bio", "Building distributed systems")
        assert "Set bio" in r.stdout

    def test_set_invalid_field(self):
        r = self.run("author_profile", "set", "invalid", "value")
        assert r.returncode != 0


class TestAuthorProfileRead:
    """Test reading the profile shows all set fields."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("author_profile", "init")
        run_script("author_profile", "set", "name", "Alice Chen")
        run_script("author_profile", "set", "role", "Senior Engineer")
        run_script("author_profile", "set", "company", "TechCorp")

    def test_read_shows_name(self):
        r = self.run("author_profile", "read")
        assert "Alice Chen" in r.stdout

    def test_read_shows_role(self):
        r = self.run("author_profile", "read")
        assert "Senior Engineer" in r.stdout

    def test_read_shows_company(self):
        r = self.run("author_profile", "read")
        assert "TechCorp" in r.stdout


class TestAuthorProfileExpertise:
    """Test add-expertise, update, read, remove-expertise."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("author_profile", "init")

    def test_add_expertise(self):
        r = self.run("author_profile", "add-expertise", "distributed-systems", "expert")
        assert "Added expertise" in r.stdout

    def test_add_second_expertise(self):
        self.run("author_profile", "add-expertise", "distributed-systems", "expert")
        r = self.run("author_profile", "add-expertise", "kubernetes", "intermediate")
        assert "Added expertise" in r.stdout

    def test_update_expertise_level(self):
        self.run("author_profile", "add-expertise", "kubernetes", "intermediate")
        r = self.run("author_profile", "add-expertise", "kubernetes", "expert")
        assert "Added expertise" in r.stdout

    def test_read_shows_expertise_topic(self):
        self.run("author_profile", "add-expertise", "distributed-systems", "expert")
        r = self.run("author_profile", "read")
        assert "distributed-systems" in r.stdout

    def test_read_shows_expertise_level(self):
        self.run("author_profile", "add-expertise", "distributed-systems", "expert")
        r = self.run("author_profile", "read")
        assert "expert" in r.stdout

    def test_invalid_expertise_level(self):
        r = self.run("author_profile", "add-expertise", "topic", "invalid-level")
        assert r.returncode != 0

    def test_remove_expertise(self):
        self.run("author_profile", "add-expertise", "kubernetes", "intermediate")
        r = self.run("author_profile", "remove-expertise", "kubernetes")
        assert "Removed expertise" in r.stdout

    def test_removed_expertise_not_in_read(self):
        self.run("author_profile", "add-expertise", "kubernetes", "intermediate")
        self.run("author_profile", "remove-expertise", "kubernetes")
        r = self.run("author_profile", "read")
        assert "kubernetes" not in r.stdout

    def test_remove_nonexistent_expertise(self):
        r = self.run("author_profile", "remove-expertise", "nonexistent")
        assert r.returncode != 0


class TestAuthorProfileVoice:
    """Test set-voice and its presence in read output."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        run_script("author_profile", "init")

    def test_set_voice(self):
        r = self.run("author_profile", "set-voice", "Concise, technical, with dry humor")
        assert "Set writing voice" in r.stdout

    def test_read_shows_voice(self):
        self.run("author_profile", "set-voice", "Concise, technical, with dry humor")
        r = self.run("author_profile", "read")
        assert "Concise, technical" in r.stdout


class TestAuthorProfileSocial:
    """Test set-social for various platforms."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        run_script("author_profile", "init")

    def test_set_social_twitter(self):
        r = self.run("author_profile", "set-social", "twitter", "@alicechen")
        assert "Set social.twitter" in r.stdout

    def test_set_social_github(self):
        r = self.run("author_profile", "set-social", "github", "alicechen")
        assert "Set social.github" in r.stdout

    def test_set_social_linkedin(self):
        r = self.run("author_profile", "set-social", "linkedin", "alice-chen")
        assert "Set social.linkedin" in r.stdout

    def test_set_social_invalid_platform(self):
        r = self.run("author_profile", "set-social", "invalid", "@handle")
        assert r.returncode != 0


class TestAuthorProfileGetBio:
    """Test get-bio output."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        run_script("author_profile", "init")
        run_script("author_profile", "set", "name", "Alice Chen")
        run_script("author_profile", "set", "role", "Senior Engineer")
        run_script("author_profile", "set", "company", "TechCorp")
        run_script("author_profile", "set", "bio", "Building distributed systems")
        run_script("author_profile", "add-expertise", "distributed-systems", "expert")

    def test_bio_has_name(self):
        r = self.run("author_profile", "get-bio")
        assert "Alice Chen" in r.stdout

    def test_bio_has_role_and_company(self):
        r = self.run("author_profile", "get-bio")
        assert "Senior Engineer at TechCorp" in r.stdout

    def test_bio_has_expertise(self):
        r = self.run("author_profile", "get-bio")
        assert "distributed-systems" in r.stdout


class TestAuthorProfileGetSocialHandles:
    """Test get-social-handles output."""

    @pytest.fixture(autouse=True)
    def _setup_profile(self, run_script, fake_home):
        self.run = run_script
        run_script("author_profile", "init")
        run_script("author_profile", "set-social", "twitter", "@alicechen")
        run_script("author_profile", "set-social", "github", "alicechen")

    def test_handles_has_twitter(self):
        r = self.run("author_profile", "get-social-handles")
        assert "@alicechen" in r.stdout

    def test_handles_has_github(self):
        r = self.run("author_profile", "get-social-handles")
        assert "alicechen" in r.stdout

    def test_handles_is_json(self):
        r = self.run("author_profile", "get-social-handles")
        assert "{" in r.stdout


class TestAuthorProfileEmptyProfile:
    """Test read, get-bio, get-social-handles on a fresh home with no profile."""

    def test_empty_profile_message(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome2")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("author_profile", "read")
        assert "No author profile" in r.stdout

    def test_empty_bio_returns_empty(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome2")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("author_profile", "get-bio")
        assert r.stdout.strip() == ""

    def test_empty_handles_returns_empty_json(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome2")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("author_profile", "get-social-handles")
        assert r.stdout.strip() == "{}"


# ============================================================
# expertise_graph.py tests
# ============================================================


class TestExpertiseGraphEmpty:
    """Test reading an empty graph."""

    def test_empty_graph_has_topics(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("expertise_graph", "read")
        assert "topics" in r.stdout


class TestExpertiseGraphUpdate:
    """Test update and query."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.home = home

    def test_update_topic(self):
        r = self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        assert "Updated topic" in r.stdout

    def test_query_shows_topic(self):
        self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "distributed-systems" in r.stdout

    def test_query_shows_article_count(self):
        self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "Articles: 1" in r.stdout

    def test_query_shows_tags(self):
        self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "kafka" in r.stdout

    def test_update_increments_count(self):
        self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        self.run("expertise_graph", "update", "distributed-systems", "raft")
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "Articles: 2" in r.stdout

    def test_update_merges_tags(self):
        self.run("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        self.run("expertise_graph", "update", "distributed-systems", "raft")
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "raft" in r.stdout

    def test_new_topic_tracked(self):
        self.run("expertise_graph", "update", "frontend", "react", "typescript")
        r = self.run("expertise_graph", "query", "frontend")
        assert "Articles: 1" in r.stdout


class TestExpertiseGraphTop:
    """Test top command."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        # Populate some data
        run_script("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        run_script("expertise_graph", "update", "distributed-systems", "raft")
        run_script("expertise_graph", "update", "frontend", "react", "typescript")

    def test_top_shows_header(self):
        r = self.run("expertise_graph", "top", "2")
        assert "Top 2" in r.stdout

    def test_top_shows_distributed_systems(self):
        r = self.run("expertise_graph", "top", "2")
        assert "distributed-systems" in r.stdout

    def test_top_default_shows_topics(self):
        r = self.run("expertise_graph", "top")
        assert "distributed-systems" in r.stdout


class TestExpertiseGraphQuery:
    """Test query edge cases and authority score."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        run_script("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        run_script("expertise_graph", "update", "distributed-systems", "raft")

    def test_query_nonexistent(self):
        r = self.run("expertise_graph", "query", "nonexistent")
        assert "No data" in r.stdout

    def test_authority_score_calculated(self):
        r = self.run("expertise_graph", "query", "distributed-systems")
        assert "Authority score: 5.0/10" in r.stdout


class TestExpertiseGraphRead:
    """Test full graph read output."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        run_script("expertise_graph", "update", "distributed-systems", "kafka", "consensus")
        run_script("expertise_graph", "update", "distributed-systems", "raft")
        run_script("expertise_graph", "update", "frontend", "react", "typescript")

    def test_read_has_topics(self):
        r = self.run("expertise_graph", "read")
        assert "distributed-systems" in r.stdout

    def test_read_has_tag_index(self):
        r = self.run("expertise_graph", "read")
        assert "tag_index" in r.stdout

    def test_read_has_kafka_in_tags(self):
        r = self.run("expertise_graph", "read")
        assert "kafka" in r.stdout

    def test_tag_index_has_consensus(self):
        r = self.run("expertise_graph", "read")
        assert "consensus" in r.stdout

    def test_tag_index_has_raft(self):
        r = self.run("expertise_graph", "read")
        assert "raft" in r.stdout


class TestExpertiseGraphSuggest:
    """Test suggest command (no profile and with profile gap)."""

    def test_suggest_no_profile_does_not_error(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        # Add some data so graph is not empty
        run_script("expertise_graph", "update", "distributed-systems", "kafka")
        r = run_script("expertise_graph", "suggest")
        # Should not error
        assert r.returncode == 0

    def test_suggest_finds_gap(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome4")
        os.makedirs(os.path.join(home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", home)
        # Create a profile with expertise not in graph
        profile = {
            "name": "Test",
            "expertise_areas": [
                {"topic": "machine-learning", "level": "expert", "added_at": "2025-01-01"},
                {"topic": "distributed-systems", "level": "authority", "added_at": "2025-01-01"},
            ],
        }
        write_json_file(
            os.path.join(home, ".tech-essay-writer", "author-profile.json"), profile
        )
        # Add one article for distributed-systems
        run_script("expertise_graph", "update", "distributed-systems", "kafka")
        r = run_script("expertise_graph", "suggest")
        assert "machine-learning" in r.stdout

    def test_suggest_identifies_gap_type(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "fakehome4b")
        os.makedirs(os.path.join(home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", home)
        profile = {
            "name": "Test",
            "expertise_areas": [
                {"topic": "machine-learning", "level": "expert", "added_at": "2025-01-01"},
                {"topic": "distributed-systems", "level": "authority", "added_at": "2025-01-01"},
            ],
        }
        write_json_file(
            os.path.join(home, ".tech-essay-writer", "author-profile.json"), profile
        )
        run_script("expertise_graph", "update", "distributed-systems", "kafka")
        r = run_script("expertise_graph", "suggest")
        assert "GAP" in r.stdout


# ============================================================
# social-package.md prompt tests
# ============================================================


class TestSocialPackagePrompt:
    """Verify key sections exist in the social-package.md prompt."""

    @pytest.fixture(autouse=True)
    def _load_prompt(self, script_dir):
        self.prompt_path = os.path.join(script_dir, "prompts", "social-package.md")
        with open(self.prompt_path) as f:
            self.prompt_content = f.read()

    def test_prompt_file_exists(self):
        assert os.path.isfile(self.prompt_path)

    def test_prompt_has_twitter_section(self):
        assert "Twitter" in self.prompt_content

    def test_prompt_has_linkedin_section(self):
        assert "LinkedIn" in self.prompt_content

    def test_prompt_has_xiaohongshu_section(self):
        assert "\u5c0f\u7ea2\u4e66" in self.prompt_content

    def test_prompt_has_hn_section(self):
        assert "HN" in self.prompt_content

    def test_prompt_has_author_positioning(self):
        assert "Author Positioning" in self.prompt_content

    def test_prompt_has_output_format(self):
        assert "social-package.json" in self.prompt_content


# ============================================================
# orchestrate.py build-social-prompt and build-format-prompts tests
# ============================================================


class TestBuildSocialPrompt:
    """Test orchestrate.py build-social-prompt with author profile and expertise."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch, script_dir):
        home = str(tmp_path / "fakehome5")
        os.makedirs(os.path.join(home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.sd = script_dir

        # Set up author profile
        run_script("author_profile", "init")
        run_script("author_profile", "set", "name", "Test Author")
        run_script("author_profile", "set-social", "twitter", "@testauthor")
        run_script("author_profile", "add-expertise", "testing", "expert")

        # Set up expertise graph
        run_script("expertise_graph", "update", "testing", "unit-test", "integration")

        # Set up project with minimal state
        project = str(tmp_path / "test-social-project")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir, exist_ok=True)
        write_json_file(
            os.path.join(state_dir, "pipeline-state.json"),
            {"stage": "polish", "topic": "testing best practices", "language": "en"},
        )
        with open(os.path.join(state_dir, "draft-v1.md"), "w") as f:
            f.write("# Test Draft\n\nThis is a test draft about testing.")
        write_json_file(
            os.path.join(state_dir, "review-seo.json"),
            {"reviewer": "seo", "rating": "GOOD", "summary": "SEO looks fine"},
        )
        self.project = project

    def test_social_prompt_has_template(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "Social Media Package" in r.stdout

    def test_social_prompt_has_draft(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "Test Draft" in r.stdout

    def test_social_prompt_has_author_data(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "Test Author" in r.stdout

    def test_social_prompt_has_expertise_graph(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "testing" in r.stdout

    def test_social_prompt_has_seo_data(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "SEO looks fine" in r.stdout

    def test_social_prompt_has_language_directive(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "Language Directive" in r.stdout

    def test_social_prompt_has_instructions(self):
        r = self.run("orchestrate", self.project, self.sd, "build-social-prompt")
        assert "social-package.json" in r.stdout


class TestBuildFormatPromptsWithAuthor:
    """Test orchestrate.py build-format-prompts includes author data."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path, monkeypatch, script_dir):
        home = str(tmp_path / "fakehome5")
        os.makedirs(os.path.join(home, ".tech-essay-writer"), exist_ok=True)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.sd = script_dir

        # Set up author profile
        run_script("author_profile", "init")
        run_script("author_profile", "set", "name", "Test Author")
        run_script("author_profile", "set-social", "twitter", "@testauthor")
        run_script("author_profile", "add-expertise", "testing", "expert")

        # Set up expertise graph
        run_script("expertise_graph", "update", "testing", "unit-test", "integration")

        # Set up project with minimal state
        project = str(tmp_path / "test-social-project")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir, exist_ok=True)
        write_json_file(
            os.path.join(state_dir, "pipeline-state.json"),
            {"stage": "polish", "topic": "testing best practices", "language": "en"},
        )
        with open(os.path.join(state_dir, "draft-v1.md"), "w") as f:
            f.write("# Test Draft\n\nThis is a test draft about testing.")
        write_json_file(
            os.path.join(state_dir, "review-seo.json"),
            {"reviewer": "seo", "rating": "GOOD", "summary": "SEO looks fine"},
        )
        self.project = project

    def test_internal_format_has_author_profile(self):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", "internal")
        assert "Author Profile" in r.stdout

    def test_internal_format_has_author_name(self):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", "internal")
        assert "Test Author" in r.stdout

    def test_external_format_has_author_profile(self):
        r = self.run("orchestrate", self.project, self.sd, "build-format-prompts", "external")
        assert "Author Profile" in r.stdout
