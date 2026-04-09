"""Tests for export.py -- bundle, markdown, html, json, archive, list-archive."""

import json
import os
import tarfile
from pathlib import Path

import pytest


# ── Content constants ─────────────────────────────────────────────────

INTERNAL_ARTICLE = """\
# Internal Article

This is the **internal** version of the article.

## Section One

Some content here with `inline code`.

```python
def hello():
    print('hello world')
```

- List item 1
- List item 2

> A blockquote here

---

End of article."""

EXTERNAL_ARTICLE = """\
# External Article

This is the **external** version.

## Introduction

Content for external readers."""

MEDIUM_ARTICLE = """\
# Medium Format Article

Written for Medium readers."""


# ── Helpers ───────────────────────────────────────────────────────────


def setup_project(run_script, tmp_path, name, topic="Test Article Topic"):
    """Create a project with initialized pipeline state. Return project path."""
    project = str(tmp_path / name)
    os.makedirs(project, exist_ok=True)
    run_script("pipeline_state", "init", project, topic)
    return project


def add_final_articles(project):
    """Write internal + external final articles into .essay-state/."""
    state = os.path.join(project, ".essay-state")
    Path(os.path.join(state, "final-internal.md")).write_text(INTERNAL_ARTICLE)
    Path(os.path.join(state, "final-external.md")).write_text(EXTERNAL_ARTICLE)


def add_medium_article(project):
    """Write a medium final article into .essay-state/."""
    state = os.path.join(project, ".essay-state")
    Path(os.path.join(state, "final-medium.md")).write_text(MEDIUM_ARTICLE)


def set_pipeline_fields(run_script, project):
    """Set quality_score and platforms on the pipeline state."""
    run_script("pipeline_state", "set-field", project, "quality_score", "8.5")
    run_script("pipeline_state", "set-field", project, "platforms", '["internal","external","medium"]')


# ── Usage and error handling ──────────────────────────────────────────


class TestUsageAndErrors:
    """Tests 1-4: argument validation and error messages."""

    def test_no_args_shows_usage(self, run_script):
        """Test 1: no args shows usage."""
        r = run_script("export")
        combined = r.stdout + r.stderr
        assert "Usage" in combined

    def test_invalid_format_shows_error(self, run_script, tmp_path, fake_home):
        """Test 2: invalid format shows error."""
        project = setup_project(run_script, tmp_path, "err1")
        r = run_script("export", project, "invalid_format")
        combined = r.stdout + r.stderr
        assert "Unknown format" in combined

    def test_missing_project_dir_errors(self, run_script, tmp_path, fake_home):
        """Test 3: missing project dir errors."""
        r = run_script("export", str(tmp_path / "nonexistent"), "bundle")
        combined = r.stdout + r.stderr
        assert "not found" in combined.lower()

    def test_no_state_dir_errors(self, run_script, tmp_path, fake_home):
        """Test 4: project without .essay-state errors."""
        no_state = str(tmp_path / "no-state")
        os.makedirs(no_state, exist_ok=True)
        r = run_script("export", no_state, "bundle")
        combined = r.stdout + r.stderr
        assert "No .essay-state" in combined or "no .essay-state" in combined.lower()


# ── Bundle format ─────────────────────────────────────────────────────


class TestBundle:
    """Tests 5-9: bundle creates tar.gz with expected contents."""

    def test_bundle_creates_tar_gz(self, run_script, tmp_path, fake_home):
        """Test 5: bundle creates tar.gz."""
        project = setup_project(run_script, tmp_path, "bundle1", "My Great Article")
        add_final_articles(project)
        out_dir = str(tmp_path / "bundle-out1")
        r = run_script("export", project, "bundle", out_dir)
        assert "Bundle created" in r.stdout
        # Find the tar.gz
        tar_files = list(Path(out_dir).glob("essay-bundle-*.tar.gz"))
        assert len(tar_files) >= 1

    def test_bundle_contains_pipeline_state(self, run_script, tmp_path, fake_home):
        """Test 6: bundle contains .essay-state files."""
        project = setup_project(run_script, tmp_path, "bundle1a", "Pipeline State Check")
        add_final_articles(project)
        out_dir = str(tmp_path / "bundle-out1a")
        run_script("export", project, "bundle", out_dir)
        tar_files = list(Path(out_dir).glob("essay-bundle-*.tar.gz"))
        assert len(tar_files) >= 1
        with tarfile.open(str(tar_files[0]), "r:gz") as tar:
            names = tar.getnames()
        assert any("pipeline-state.json" in n for n in names)

    def test_bundle_contains_final_articles(self, run_script, tmp_path, fake_home):
        """Test 7: bundle contains final articles."""
        project = setup_project(run_script, tmp_path, "bundle1b", "Final Articles Check")
        add_final_articles(project)
        out_dir = str(tmp_path / "bundle-out1b")
        run_script("export", project, "bundle", out_dir)
        tar_files = list(Path(out_dir).glob("essay-bundle-*.tar.gz"))
        assert len(tar_files) >= 1
        with tarfile.open(str(tar_files[0]), "r:gz") as tar:
            names = tar.getnames()
        assert any("final-internal.md" in n for n in names)

    def test_bundle_default_output_dir_is_project(self, run_script, tmp_path, fake_home):
        """Test 8: bundle default output_dir is project dir."""
        project = setup_project(run_script, tmp_path, "bundle2", "Default Out")
        add_final_articles(project)
        run_script("export", project, "bundle")
        tar_files = list(Path(project).glob("essay-bundle-*.tar.gz"))
        assert len(tar_files) >= 1

    def test_bundle_shows_file_size(self, run_script, tmp_path, fake_home):
        """Test 9: bundle shows file size."""
        project = setup_project(run_script, tmp_path, "bundle3", "Size Check")
        add_final_articles(project)
        r = run_script("export", project, "bundle")
        assert "bytes" in r.stdout


# ── Markdown format ───────────────────────────────────────────────────


class TestMarkdown:
    """Tests 10-13: markdown export copies files."""

    def test_markdown_export_copies_files(self, run_script, tmp_path, fake_home):
        """Test 10: markdown export copies files."""
        project = setup_project(run_script, tmp_path, "md1", "Markdown Test")
        add_final_articles(project)
        out_dir = str(tmp_path / "md-out1")
        r = run_script("export", project, "markdown", out_dir)
        assert "2 markdown" in r.stdout.lower() or "2 markdown" in r.stdout
        assert Path(out_dir, "final-internal.md").exists()
        assert Path(out_dir, "final-external.md").exists()

    def test_markdown_no_finals_exits_nonzero(self, run_script, tmp_path, fake_home):
        """Test 11: markdown export with no final articles errors."""
        project = setup_project(run_script, tmp_path, "md2", "No Finals")
        r = run_script("export", project, "markdown", str(tmp_path / "md-out2"))
        assert r.returncode != 0

    def test_markdown_preserves_content(self, run_script, tmp_path, fake_home):
        """Test 12: markdown preserves content."""
        project = setup_project(run_script, tmp_path, "md3", "Content Check")
        add_final_articles(project)
        out_dir = str(tmp_path / "md-out3")
        run_script("export", project, "markdown", out_dir)
        content = Path(out_dir, "final-internal.md").read_text()
        assert "inline code" in content

    def test_markdown_with_three_articles(self, run_script, tmp_path, fake_home):
        """Test 13: markdown with three articles."""
        project = setup_project(run_script, tmp_path, "md4", "Three Articles")
        add_final_articles(project)
        add_medium_article(project)
        out_dir = str(tmp_path / "md-out4")
        r = run_script("export", project, "markdown", out_dir)
        assert "3 markdown" in r.stdout.lower() or "3 markdown" in r.stdout


# ── HTML format ───────────────────────────────────────────────────────


class TestHTML:
    """Tests 14-23: html export creates .html files with proper conversion."""

    @pytest.fixture(autouse=True)
    def _setup_html_project(self, run_script, tmp_path, fake_home):
        """Set up an HTML export project used by most tests in this class."""
        self.project = setup_project(run_script, tmp_path, "html1", "HTML Test Article")
        add_final_articles(self.project)
        self.out_dir = str(tmp_path / "html-out1")
        self.result = run_script("export", self.project, "html", self.out_dir)
        internal_path = Path(self.out_dir, "final-internal.html")
        self.html_content = internal_path.read_text() if internal_path.exists() else ""
        self.run_script = run_script
        self.tmp_path = tmp_path

    def test_html_export_creates_files(self):
        """Test 14: html export creates .html files."""
        assert "2 HTML" in self.result.stdout or "2 html" in self.result.stdout.lower()
        assert Path(self.out_dir, "final-internal.html").exists()
        assert Path(self.out_dir, "final-external.html").exists()

    def test_html_contains_doctype(self):
        """Test 15: html contains DOCTYPE."""
        assert "DOCTYPE html" in self.html_content

    def test_html_has_title_from_topic(self):
        """Test 16: html has title from topic."""
        assert "HTML Test Article" in self.html_content

    def test_html_converts_headers(self):
        """Tests 17: html converts h1 and h2."""
        assert "<h1>" in self.html_content
        assert "<h2>" in self.html_content

    def test_html_converts_code_blocks(self):
        """Test 18: html converts code blocks."""
        assert "<pre><code" in self.html_content

    def test_html_converts_bold(self):
        """Test 19: html converts inline formatting (bold)."""
        assert "<strong>" in self.html_content

    def test_html_converts_blockquotes(self):
        """Test 20: html converts blockquotes."""
        assert "<blockquote>" in self.html_content

    def test_html_converts_lists(self):
        """Test 21: html converts lists."""
        assert "<li>" in self.html_content

    def test_html_no_finals_exits_nonzero(self):
        """Test 22: html with no final articles errors."""
        project = setup_project(self.run_script, self.tmp_path, "html2", "No Finals")
        r = self.run_script("export", project, "html", str(self.tmp_path / "html-out2"))
        assert r.returncode != 0

    def test_html_has_style_tag(self):
        """Test 23: html has proper styling."""
        assert "<style>" in self.html_content


# ── JSON format ───────────────────────────────────────────────────────


class TestJSON:
    """Tests 24-31: json export creates file with expected structure."""

    @pytest.fixture(autouse=True)
    def _setup_json_project(self, run_script, tmp_path, fake_home):
        """Set up a JSON export project used by most tests in this class."""
        self.project = setup_project(run_script, tmp_path, "json1", "JSON Export Topic")
        add_final_articles(self.project)
        self.out_dir = str(tmp_path / "json-out1")
        self.result = run_script("export", self.project, "json", self.out_dir)
        json_files = list(Path(self.out_dir).glob("essay-export-*.json"))
        self.json_file = json_files[0] if json_files else None
        self.json_data = None
        if self.json_file:
            self.json_data = json.loads(self.json_file.read_text())

    def test_json_export_creates_file(self):
        """Test 24: json export creates file."""
        assert "JSON export" in self.result.stdout or "json export" in self.result.stdout.lower()
        assert self.json_file is not None

    def test_json_is_valid(self):
        """Test 25: json is valid JSON."""
        assert self.json_data is not None
        assert isinstance(self.json_data, dict)

    def test_json_contains_pipeline_state(self):
        """Test 26: json contains pipeline_state."""
        assert self.json_data.get("pipeline_state") is not None

    def test_json_contains_final_articles(self):
        """Test 27: json contains final_articles."""
        assert len(self.json_data.get("final_articles", {})) == 2

    def test_json_has_format_version(self):
        """Test 28: json has format_version."""
        assert self.json_data.get("format_version") == "1.0"

    def test_json_has_exported_at(self):
        """Test 29: json has exported_at timestamp."""
        assert self.json_data.get("exported_at")

    def test_json_article_has_content(self):
        """Test 30: json contains article content."""
        internal = self.json_data.get("final_articles", {}).get("internal", "")
        assert "Internal" in internal[:20]

    def test_json_shows_file_size(self):
        """Test 31: json shows file size."""
        assert "bytes" in self.result.stdout


# ── Archive format ────────────────────────────────────────────────────


class TestArchive:
    """Tests 32-44: archive creates directory with metadata."""

    def test_archive_creates_directory(self, run_script, tmp_path, fake_home):
        """Test 32: archive creates directory in ~/.tech-essay-writer/articles/."""
        project = setup_project(run_script, tmp_path, "arch1", "Archive Test Article")
        add_final_articles(project)
        r = run_script("export", project, "archive")
        assert "Archived" in r.stdout or "archived" in r.stdout.lower()
        assert "metadata.json" in r.stdout

    def _get_archive_dir(self, fake_home, slug_part):
        """Find an archive directory matching slug_part."""
        articles_dir = Path(fake_home, ".tech-essay-writer", "articles")
        if not articles_dir.exists():
            return None
        matches = [d for d in articles_dir.iterdir() if d.is_dir() and slug_part in d.name]
        return str(matches[0]) if matches else None

    def test_archive_has_slug_based_name(self, run_script, tmp_path, fake_home):
        """Test 33: archive directory has expected naming."""
        project = setup_project(run_script, tmp_path, "arch1a", "Archive Test Article")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "archive-test-article")
        assert archive_dir is not None

    def test_archive_contains_final_articles(self, run_script, tmp_path, fake_home):
        """Test 34: archive contains final articles."""
        project = setup_project(run_script, tmp_path, "arch1b", "Archive Final Check")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "archive-final-check")
        assert archive_dir is not None
        assert Path(archive_dir, "final-internal.md").exists()
        assert Path(archive_dir, "final-external.md").exists()

    def test_archive_contains_metadata_json(self, run_script, tmp_path, fake_home):
        """Test 35: archive contains metadata.json."""
        project = setup_project(run_script, tmp_path, "arch1c", "Archive Meta Check")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "archive-meta-check")
        assert archive_dir is not None
        assert Path(archive_dir, "metadata.json").exists()

    def test_metadata_has_correct_topic(self, run_script, tmp_path, fake_home):
        """Test 36: metadata has correct topic."""
        project = setup_project(run_script, tmp_path, "arch1d", "Metadata Topic Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "metadata-topic-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert meta.get("topic") == "Metadata Topic Test"

    def test_metadata_has_archived_at(self, run_script, tmp_path, fake_home):
        """Test 37: metadata has archived_at."""
        project = setup_project(run_script, tmp_path, "arch1e", "Archived At Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "archived-at-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert meta.get("archived_at")

    def test_metadata_has_quality_score_field(self, run_script, tmp_path, fake_home):
        """Test 38: metadata has quality_score field."""
        project = setup_project(run_script, tmp_path, "arch1f", "Quality Score Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "quality-score-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert "quality_score" in meta

    def test_metadata_has_platforms_field(self, run_script, tmp_path, fake_home):
        """Test 39: metadata has platforms field."""
        project = setup_project(run_script, tmp_path, "arch1g", "Platforms Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "platforms-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert "platforms" in meta

    def test_metadata_has_publish_dates_field(self, run_script, tmp_path, fake_home):
        """Test 40: metadata has publish_dates field."""
        project = setup_project(run_script, tmp_path, "arch1h", "Publish Dates Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "publish-dates-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert "publish_dates" in meta

    def test_metadata_has_source_project(self, run_script, tmp_path, fake_home):
        """Test 41: metadata has source_project field."""
        project = setup_project(run_script, tmp_path, "arch1i", "Source Project Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "source-project-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert meta.get("source_project")

    def test_metadata_lists_files(self, run_script, tmp_path, fake_home):
        """Test 42: metadata lists files (at least 2)."""
        project = setup_project(run_script, tmp_path, "arch1j", "Files List Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        archive_dir = self._get_archive_dir(fake_home, "files-list-test")
        assert archive_dir is not None
        meta = json.loads(Path(archive_dir, "metadata.json").read_text())
        assert len(meta.get("files", [])) >= 2

    def test_archive_no_finals_exits_nonzero(self, run_script, tmp_path, fake_home):
        """Test 43: archive with no final articles errors."""
        project = setup_project(run_script, tmp_path, "arch2", "No Finals Archive")
        r = run_script("export", project, "archive")
        assert r.returncode != 0

    def test_duplicate_archive_gets_numeric_suffix(self, run_script, tmp_path, fake_home):
        """Test 44: duplicate archive gets numeric suffix."""
        project = setup_project(run_script, tmp_path, "arch3", "Duplicate Topic")
        add_final_articles(project)
        run_script("export", project, "archive")
        run_script("export", project, "archive")
        articles_dir = Path(fake_home, ".tech-essay-writer", "articles")
        matches = [d for d in articles_dir.iterdir() if d.is_dir() and "duplicate-topic" in d.name]
        assert len(matches) == 2


# ── List archive ──────────────────────────────────────────────────────


class TestListArchive:
    """Tests 45-49: list-archive shows archived articles."""

    def test_list_archive_shows_articles(self, run_script, tmp_path, fake_home):
        """Test 45: list-archive shows archived articles."""
        # First archive something
        project = setup_project(run_script, tmp_path, "la1", "Archive Test Article")
        add_final_articles(project)
        run_script("export", project, "archive")
        # Now list
        r = run_script("export", "list-archive")
        assert "archived article" in r.stdout.lower() or "archived" in r.stdout.lower()
        assert "Archive Test Article" in r.stdout

    def test_list_archive_json_is_valid(self, run_script, tmp_path, fake_home):
        """Test 46: list-archive --json produces valid JSON."""
        project = setup_project(run_script, tmp_path, "la2", "JSON List Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        r = run_script("export", "list-archive", "--json")
        data = json.loads(r.stdout)
        assert isinstance(data, list)

    def test_list_archive_json_has_entries(self, run_script, tmp_path, fake_home):
        """Test 47: list-archive --json contains entries."""
        project = setup_project(run_script, tmp_path, "la3", "Entries Test")
        add_final_articles(project)
        run_script("export", project, "archive")
        r = run_script("export", "list-archive", "--json")
        data = json.loads(r.stdout)
        assert len(data) >= 1

    def test_list_archive_empty_shows_no_articles(self, run_script, tmp_path, monkeypatch):
        """Test 48: list-archive with empty archive dir."""
        empty_home = str(tmp_path / "emptyhome")
        os.makedirs(empty_home, exist_ok=True)
        monkeypatch.setenv("HOME", empty_home)
        r = run_script("export", "list-archive")
        assert "No archived articles" in r.stdout

    def test_list_archive_empty_json_returns_empty_list(self, run_script, tmp_path, monkeypatch):
        """Test 49: list-archive --json with empty archive returns []."""
        empty_home = str(tmp_path / "emptyhome2")
        os.makedirs(empty_home, exist_ok=True)
        monkeypatch.setenv("HOME", empty_home)
        r = run_script("export", "list-archive", "--json")
        assert r.stdout.strip() == "[]"


# ── Slug generation ───────────────────────────────────────────────────


class TestSlugGeneration:
    """Tests 50-51: slug handles special characters and spaces."""

    def test_slug_handles_special_characters(self, run_script, tmp_path, fake_home):
        """Test 50: slug handles special characters."""
        project = setup_project(run_script, tmp_path, "slug1", "My Article: A Deep Dive! (2024)")
        add_final_articles(project)
        out_dir = str(tmp_path / "slug-out1")
        run_script("export", project, "bundle", out_dir)
        tar_files = list(Path(out_dir).glob("essay-bundle-*.tar.gz"))
        assert len(tar_files) >= 1
        fname = tar_files[0].name
        # No special characters in the filename
        for ch in "!@#$%^&*()":
            assert ch not in fname

    def test_slug_handles_spaces(self, run_script, tmp_path, fake_home):
        """Test 51: slug handles spaces."""
        project = setup_project(run_script, tmp_path, "slug2", "Spaces In Topic Name")
        add_final_articles(project)
        out_dir = str(tmp_path / "slug-out2")
        run_script("export", project, "bundle", out_dir)
        tar_files = list(Path(out_dir).glob("essay-bundle-*spaces-in-topic-name*.tar.gz"))
        assert len(tar_files) >= 1


# ── Orchestrate integration ───────────────────────────────────────────


class TestOrchestrateIntegration:
    """Tests 52-53: orchestrate.sh usage mentions export commands."""

    def test_orchestrate_usage_mentions_export(self, run_script, tmp_path, script_dir):
        """Test 52: orchestrate.sh usage mentions export."""
        r = run_script("orchestrate", str(tmp_path), script_dir, "help")
        combined = r.stdout + r.stderr
        assert "export" in combined.lower()

    def test_orchestrate_usage_mentions_list_archive(self, run_script, tmp_path, script_dir):
        """Test 53: orchestrate.sh usage mentions list-archive."""
        r = run_script("orchestrate", str(tmp_path), script_dir, "help")
        combined = r.stdout + r.stderr
        assert "list-archive" in combined.lower()


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests 54-57: default output dirs and html conversion edge cases."""

    def test_html_default_output_dir(self, run_script, tmp_path, fake_home):
        """Test 54: html default output_dir."""
        project = setup_project(run_script, tmp_path, "edge1", "Default HTML Dir")
        add_final_articles(project)
        run_script("export", project, "html")
        assert Path(project, "export-html").is_dir()
        assert Path(project, "export-html", "final-internal.html").exists()

    def test_markdown_default_output_dir(self, run_script, tmp_path, fake_home):
        """Test 55: markdown default output_dir."""
        project = setup_project(run_script, tmp_path, "edge2", "Default MD Dir")
        add_final_articles(project)
        run_script("export", project, "markdown")
        assert Path(project, "export-markdown").is_dir()

    def test_json_default_output_dir(self, run_script, tmp_path, fake_home):
        """Test 56: json default output_dir is project dir."""
        project = setup_project(run_script, tmp_path, "edge3", "Default JSON Dir")
        add_final_articles(project)
        run_script("export", project, "json")
        json_files = list(Path(project).glob("essay-export-*.json"))
        assert len(json_files) >= 1

    def test_html_converts_horizontal_rules(self, run_script, tmp_path, fake_home):
        """Test 57: html converts horizontal rules."""
        project = setup_project(run_script, tmp_path, "edge4", "HR Test")
        add_final_articles(project)
        out_dir = str(tmp_path / "hr-test")
        run_script("export", project, "html", out_dir)
        content = Path(out_dir, "final-internal.html").read_text()
        assert "<hr>" in content
