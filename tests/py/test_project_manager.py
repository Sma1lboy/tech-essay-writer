"""Tests for project_manager.py.

Covers slug validation (incl. path-traversal), CRUD, active-project pointer,
resolve precedence, ensure-default idempotence, and the article-dir helper.

Isolation: TEW_SKILL_ROOT + TEW_USER_DATA_DIR env vars redirect both the
projects/ tree and the active-project.txt to a per-test tmp dir, so tests
never touch the real source repo or the real ~/.tech-essay-writer/.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "py"


@pytest.fixture
def isolated_tew(tmp_path, monkeypatch):
    """Redirect skill_root + user_data_dir to a temp dir for this test."""
    skill_root = tmp_path / "skill"
    user_data = tmp_path / "user-data"
    skill_root.mkdir()
    user_data.mkdir()
    monkeypatch.setenv("TEW_SKILL_ROOT", str(skill_root))
    monkeypatch.setenv("TEW_USER_DATA_DIR", str(user_data))
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        # Re-import fresh each time to pick up env
        import importlib

        import project_manager as pm  # type: ignore
        importlib.reload(pm)
        yield pm, skill_root, user_data
    finally:
        sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture
def run_cli(tmp_path, monkeypatch):
    """Invoke project_manager.py as a subprocess with env overrides."""
    skill_root = tmp_path / "skill"
    user_data = tmp_path / "user-data"
    skill_root.mkdir()
    user_data.mkdir()

    def _run(*args, expect_rc=0):
        env = os.environ.copy()
        env["TEW_SKILL_ROOT"] = str(skill_root)
        env["TEW_USER_DATA_DIR"] = str(user_data)
        env["PYTHONPATH"] = str(SCRIPTS_DIR)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "project_manager.py"), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == expect_rc, (
            f"rc={result.returncode} stderr={result.stderr} stdout={result.stdout}"
        )
        return result

    _run.skill_root = skill_root
    _run.user_data = user_data
    return _run


# ─── slug validation ──────────────────────────────────────────────────────


class TestSlugValidation:
    @pytest.mark.parametrize(
        "slug",
        ["my-blog", "blog2", "a", "a1b2", "x" * 64, "project-with-lots-of-hyphens"],
    )
    def test_valid_slugs(self, isolated_tew, slug):
        pm, _, _ = isolated_tew
        pm.validate_slug(slug)  # should not raise

    @pytest.mark.parametrize(
        "slug",
        [
            "",                  # empty
            "MyBlog",            # uppercase
            "-leading-hyphen",   # leading hyphen
            "trailing-dot.",     # dot
            "../escape",         # path traversal
            "foo/bar",           # slash
            "x" * 65,            # too long
            ".hidden",           # leading dot
            "with space",        # space
            "with_underscore",   # underscore not allowed
        ],
    )
    def test_invalid_slugs(self, isolated_tew, slug):
        pm, _, _ = isolated_tew
        with pytest.raises(ValueError):
            pm.validate_slug(slug)

    def test_non_string_slug(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(ValueError):
            pm.validate_slug(None)  # type: ignore


# ─── CRUD ─────────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_makes_dirs_and_metadata(self, isolated_tew):
        pm, skill_root, _ = isolated_tew
        meta = pm.create_project("my-blog", "My personal blog")
        assert meta["slug"] == "my-blog"
        assert meta["description"] == "My personal blog"
        assert meta["created_at"]  # non-empty
        assert (skill_root / "projects" / "my-blog").is_dir()
        assert (skill_root / "projects" / "my-blog" / "project.json").is_file()
        assert (skill_root / "projects" / "my-blog" / "references").is_dir()
        assert (skill_root / "projects" / "my-blog" / "research").is_dir()
        assert (skill_root / "projects" / "my-blog" / "articles").is_dir()

    def test_create_seeds_references_index(self, isolated_tew):
        pm, skill_root, _ = isolated_tew
        pm.create_project("x")
        idx = json.loads(
            (skill_root / "projects" / "x" / "references" / "index.json").read_text()
        )
        assert idx == {"version": 1, "refs": []}

    def test_create_duplicate_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("dup")
        with pytest.raises(FileExistsError):
            pm.create_project("dup")

    def test_create_invalid_slug_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(ValueError):
            pm.create_project("../escape")


class TestList:
    def test_list_empty(self, isolated_tew):
        pm, _, _ = isolated_tew
        assert pm.list_projects() == []

    def test_list_sorted_and_returns_metadata(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("zeta")
        pm.create_project("alpha")
        pm.create_project("mid")
        slugs = [p["slug"] for p in pm.list_projects()]
        assert slugs == ["alpha", "mid", "zeta"]

    def test_list_ignores_stray_dirs(self, isolated_tew):
        pm, skill_root, _ = isolated_tew
        pm.create_project("real")
        (skill_root / "projects" / "not-a-project").mkdir()
        (skill_root / "projects" / "not-a-project" / "random.txt").write_text("x")
        assert [p["slug"] for p in pm.list_projects()] == ["real"]


class TestRead:
    def test_read_returns_metadata(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("foo", "About foo")
        meta = pm.read_project("foo")
        assert meta["slug"] == "foo"
        assert meta["description"] == "About foo"

    def test_read_missing_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(FileNotFoundError):
            pm.read_project("ghost")


# ─── active project ───────────────────────────────────────────────────────


class TestActiveProject:
    def test_get_active_empty_when_unset(self, isolated_tew):
        pm, _, _ = isolated_tew
        assert pm.get_active() == ""

    def test_set_active_persists(self, isolated_tew):
        pm, _, user_data = isolated_tew
        pm.create_project("one")
        pm.set_active("one")
        assert pm.get_active() == "one"
        assert (user_data / "active-project.txt").read_text().strip() == "one"

    def test_set_active_missing_project_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(FileNotFoundError):
            pm.set_active("ghost")

    def test_set_active_invalid_slug_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(ValueError):
            pm.set_active("../escape")

    def test_clear_active(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("one")
        pm.set_active("one")
        pm.clear_active()
        assert pm.get_active() == ""

    def test_get_active_returns_empty_for_stale_pointer(self, isolated_tew):
        """If active-project.txt references a now-deleted project, treat as unset."""
        pm, skill_root, user_data = isolated_tew
        pm.create_project("temp")
        pm.set_active("temp")
        # Delete the project directory outside of set_active.
        import shutil

        shutil.rmtree(skill_root / "projects" / "temp")
        assert pm.get_active() == ""

    def test_get_active_rejects_malformed_pointer(self, isolated_tew):
        pm, _, user_data = isolated_tew
        (user_data / "active-project.txt").write_text("../escape\n")
        assert pm.get_active() == ""


# ─── ensure-default + resolve ─────────────────────────────────────────────


class TestEnsureDefault:
    def test_creates_default_project(self, isolated_tew):
        pm, skill_root, _ = isolated_tew
        slug = pm.ensure_default()
        assert slug == "default"
        assert (skill_root / "projects" / "default" / "project.json").is_file()

    def test_sets_default_active_when_nothing_active(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.ensure_default()
        assert pm.get_active() == "default"

    def test_respects_existing_active(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("mine")
        pm.set_active("mine")
        pm.ensure_default()
        # default now exists but active stays on 'mine'
        assert pm.get_active() == "mine"
        assert pm.project_exists("default")

    def test_idempotent(self, isolated_tew):
        pm, _, _ = isolated_tew
        slug1 = pm.ensure_default()
        slug2 = pm.ensure_default()
        assert slug1 == slug2 == "default"


class TestResolveProject:
    def test_explicit_overrides_everything(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("alpha")
        pm.create_project("beta")
        pm.set_active("alpha")
        assert pm.resolve_project("beta") == "beta"

    def test_active_used_when_no_request(self, isolated_tew):
        pm, _, _ = isolated_tew
        pm.create_project("active-one")
        pm.set_active("active-one")
        assert pm.resolve_project() == "active-one"

    def test_falls_back_to_default(self, isolated_tew):
        pm, _, _ = isolated_tew
        slug = pm.resolve_project()
        assert slug == "default"

    def test_explicit_missing_raises(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(FileNotFoundError):
            pm.resolve_project("ghost")


# ─── article_dir ──────────────────────────────────────────────────────────


class TestArticleDir:
    def test_returns_expected_path(self, isolated_tew):
        pm, skill_root, _ = isolated_tew
        p = pm.article_dir("my-blog", "first-post")
        assert p == skill_root / "projects" / "my-blog" / "articles" / "first-post"

    def test_does_not_create_dir(self, isolated_tew):
        pm, _, _ = isolated_tew
        p = pm.article_dir("my-blog", "first-post")
        assert not p.exists()

    def test_validates_both_slugs(self, isolated_tew):
        pm, _, _ = isolated_tew
        with pytest.raises(ValueError):
            pm.article_dir("ok", "../escape")
        with pytest.raises(ValueError):
            pm.article_dir("../escape", "ok")


# ─── CLI ──────────────────────────────────────────────────────────────────


class TestCLI:
    def test_init_prints_path(self, run_cli):
        r = run_cli("init")
        assert r.stdout.strip() == str(run_cli.skill_root / "projects")
        assert (run_cli.skill_root / "projects").is_dir()

    def test_create_and_list(self, run_cli):
        run_cli("create", "my-blog", "Personal blog")
        r = run_cli("list")
        data = json.loads(r.stdout)
        assert data["active"] == ""
        assert len(data["projects"]) == 1
        assert data["projects"][0]["slug"] == "my-blog"
        assert data["projects"][0]["description"] == "Personal blog"

    def test_show(self, run_cli):
        run_cli("create", "foo")
        r = run_cli("show", "foo")
        assert json.loads(r.stdout)["slug"] == "foo"

    def test_show_missing_returns_error(self, run_cli):
        r = run_cli("show", "ghost", expect_rc=1)
        assert "not found" in r.stderr

    def test_set_and_get_active(self, run_cli):
        run_cli("create", "foo")
        run_cli("set-active", "foo")
        r = run_cli("get-active")
        assert r.stdout.strip() == "foo"

    def test_clear_active(self, run_cli):
        run_cli("create", "foo")
        run_cli("set-active", "foo")
        run_cli("clear-active")
        r = run_cli("get-active")
        assert r.stdout.strip() == ""

    def test_ensure_default_end_to_end(self, run_cli):
        r = run_cli("ensure-default")
        assert r.stdout.strip() == "default"
        r2 = run_cli("get-active")
        assert r2.stdout.strip() == "default"

    def test_resolve_explicit(self, run_cli):
        run_cli("create", "alpha")
        r = run_cli("resolve", "--project", "alpha")
        assert r.stdout.strip() == "alpha"

    def test_resolve_missing_returns_error(self, run_cli):
        r = run_cli("resolve", "--project", "ghost", expect_rc=1)
        assert "not found" in r.stderr

    def test_article_dir(self, run_cli):
        r = run_cli("article-dir", "blog", "first-post")
        expected = str(run_cli.skill_root / "projects" / "blog" / "articles" / "first-post")
        assert r.stdout.strip() == expected

    def test_create_invalid_slug_returns_error(self, run_cli):
        r = run_cli("create", "../escape", expect_rc=1)
        assert "invalid slug" in r.stderr.lower()
