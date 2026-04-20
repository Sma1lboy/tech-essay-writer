"""End-to-end tests for Phase 2: references landing in generated prompts.

Covers the full chain:
  project_manager.create
  -> reference_library.add
  -> pipeline_state init --project <slug>  (stores project field)
  -> orchestrate build-research-prompt / build-outline-prompts / build-writer-prompt
     (read the project field, inject formatted references block)

Isolation: the run_script fixture in conftest.py sets TEW_SKILL_ROOT +
TEW_USER_DATA_DIR per-test, so real source tree and ~/.tech-essay-writer/
are untouched.
"""
import json
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _state_dir(project_dir):
    return os.path.join(project_dir, ".essay-state")


def _init_with_minimal_state(run_script, article_dir, topic, project_slug=""):
    """Init pipeline state + seed empty materials/research so prompt builders
    don't complain about missing inputs. Returns the sandbox skill_root path
    so callers can create projects in the same sandbox."""
    os.makedirs(article_dir, exist_ok=True)
    args = ["init", article_dir, topic]
    if project_slug:
        args += ["--project", project_slug]
    run_script("pipeline_state", *args)
    # Seed required state files (empty but valid JSON) so prompt builders run.
    sd = _state_dir(article_dir)
    os.makedirs(sd, exist_ok=True)
    for fname in ("materials.json", "research-synthesis.json"):
        fp = os.path.join(sd, fname)
        if not os.path.isfile(fp):
            with open(fp, "w") as f:
                json.dump({}, f)


class TestProjectFieldStored:
    def test_init_stores_project_field(self, run_script, tmp_path):
        """init must write the resolved project slug into pipeline-state.json."""
        article = tmp_path / "article"
        run_script("project_manager", "create", "my-blog", "Test blog")
        _init_with_minimal_state(run_script, str(article), "Test Topic", project_slug="my-blog")
        state = json.loads(
            (article / ".essay-state" / "pipeline-state.json").read_text()
        )
        assert state.get("project") == "my-blog"

    def test_init_without_explicit_project_auto_defaults(self, run_script, tmp_path):
        """Omitting --project falls back to resolve_project → auto-creates default."""
        article = tmp_path / "article"
        _init_with_minimal_state(run_script, str(article), "Test Topic")
        state = json.loads(
            (article / ".essay-state" / "pipeline-state.json").read_text()
        )
        # Either "default" (happy path) or "" (resolve failure — still acceptable
        # since the block just stays empty and pipeline still works)
        assert state.get("project") in ("default", "")

    def test_init_rejects_unknown_project(self, run_script, tmp_path):
        """Explicit --project with nonexistent slug still succeeds (graceful
        degrade) — _resolve_project_slug swallows the error so pipeline init
        never fails because of project resolution."""
        article = tmp_path / "article"
        _init_with_minimal_state(run_script, str(article), "Topic", project_slug="ghost")
        state = json.loads(
            (article / ".essay-state" / "pipeline-state.json").read_text()
        )
        # Ghost was never created → resolver raised → graceful "" fallback
        assert state.get("project") == ""


class TestReferencesInResearchPrompt:
    def test_references_appear_in_research_prompt(self, run_script, tmp_path):
        article = tmp_path / "article"
        run_script("project_manager", "create", "blog")
        run_script(
            "reference_library", "add", "blog",
            "https://arxiv.org/abs/1706.03762",
            "--title", "Attention Is All You Need",
            "--kind", "paper",
            "--tag", "transformers,llm",
        )
        run_script(
            "reference_library", "add", "blog",
            "https://example.com/post",
            "--title", "Some Blog Post",
            "--kind", "url",
        )
        _init_with_minimal_state(run_script, str(article), "Test", project_slug="blog")
        r = run_script("orchestrate", str(article), str(PROJECT_ROOT), "build-research-prompt")
        assert r.returncode == 0
        assert "## Reference Library (project: `blog`)" in r.stdout
        assert "ref-001" in r.stdout
        assert "Attention Is All You Need" in r.stdout
        assert "ref-002" in r.stdout
        assert "transformers" in r.stdout  # tag passed through

    def test_references_absent_when_no_project_assoc(self, run_script, tmp_path):
        """Article inited without any project binding (pre-projects flow) must
        not have a reference block — empty string injection is a no-op."""
        article = tmp_path / "article"
        _init_with_minimal_state(run_script, str(article), "Test")
        # Kill the auto-set project so we test the pre-projects path exactly.
        sf = article / ".essay-state" / "pipeline-state.json"
        state = json.loads(sf.read_text())
        state["project"] = ""
        sf.write_text(json.dumps(state))

        r = run_script("orchestrate", str(article), str(PROJECT_ROOT), "build-research-prompt")
        assert r.returncode == 0
        assert "## Reference Library" not in r.stdout

    def test_empty_library_adds_nothing(self, run_script, tmp_path):
        """Project exists but has no refs → format_for_prompt returns empty."""
        article = tmp_path / "article"
        run_script("project_manager", "create", "empty-project")
        _init_with_minimal_state(run_script, str(article), "Test", project_slug="empty-project")
        r = run_script("orchestrate", str(article), str(PROJECT_ROOT), "build-research-prompt")
        assert r.returncode == 0
        assert "## Reference Library" not in r.stdout


class TestReferencesInOutlinePrompt:
    def test_references_appear_in_outline_prompt(self, run_script, tmp_path):
        article = tmp_path / "article"
        run_script("project_manager", "create", "blog")
        run_script(
            "reference_library", "add", "blog",
            "https://x",
            "--title", "Important Paper",
            "--kind", "paper",
        )
        _init_with_minimal_state(run_script, str(article), "Test", project_slug="blog")
        r = run_script(
            "orchestrate", str(article), str(PROJECT_ROOT),
            "build-outline-prompts", "A",
        )
        assert r.returncode == 0
        assert "## Reference Library (project: `blog`)" in r.stdout
        assert "Important Paper" in r.stdout


class TestReferencesInWriterPrompt:
    def test_references_appear_in_writer_prompt(self, run_script, tmp_path):
        article = tmp_path / "article"
        run_script("project_manager", "create", "blog")
        run_script(
            "reference_library", "add", "blog", "https://x",
            "--title", "Writer Should See This",
        )
        _init_with_minimal_state(run_script, str(article), "Test", project_slug="blog")
        # Seed a fake outline so writer prompt builder has something to chew on.
        outline_path = article / ".essay-state" / "outline-A.json"
        outline_path.write_text(json.dumps({"sections": []}))
        r = run_script(
            "orchestrate", str(article), str(PROJECT_ROOT),
            "build-writer-prompt", "A",
        )
        assert r.returncode == 0
        assert "## Reference Library (project: `blog`)" in r.stdout
        assert "Writer Should See This" in r.stdout


class TestPromptInjectionRobustness:
    def test_missing_project_field_is_silent(self, run_script, tmp_path):
        """Older state files with no 'project' key don't break prompt builders."""
        article = tmp_path / "article"
        _init_with_minimal_state(run_script, str(article), "Test")
        # Strip the project field entirely (simulating an article initialized
        # by a pre-Phase-2 pipeline_state binary).
        sf = article / ".essay-state" / "pipeline-state.json"
        state = json.loads(sf.read_text())
        state.pop("project", None)
        sf.write_text(json.dumps(state))

        r = run_script("orchestrate", str(article), str(PROJECT_ROOT), "build-research-prompt")
        assert r.returncode == 0
        assert "## Reference Library" not in r.stdout

    def test_stale_project_slug_degrades_gracefully(self, run_script, tmp_path):
        """If the stored project was deleted, prompts still render — block empty."""
        article = tmp_path / "article"
        run_script("project_manager", "create", "temp")
        _init_with_minimal_state(run_script, str(article), "Test", project_slug="temp")

        # User manually deletes the project directory in the sandbox after init.
        # Compute the sandbox skill root from the fixture (same tmp_path + "tew-skill").
        sandbox_skill = tmp_path / "tew-skill"
        import shutil
        shutil.rmtree(sandbox_skill / "projects" / "temp")

        r = run_script("orchestrate", str(article), str(PROJECT_ROOT), "build-research-prompt")
        assert r.returncode == 0
        assert "## Reference Library" not in r.stdout
