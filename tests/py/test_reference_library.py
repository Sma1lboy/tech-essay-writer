"""Tests for reference_library.py (Phase 1: placeholder cards, CRUD).

Isolation: same TEW_SKILL_ROOT + TEW_USER_DATA_DIR pattern as
test_project_manager.py. Every test starts with a fresh skill root.
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "py"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """Yield (reference_library, project_manager, skill_root, user_data_dir)."""
    skill_root = tmp_path / "skill"
    user_data = tmp_path / "user-data"
    skill_root.mkdir()
    user_data.mkdir()
    monkeypatch.setenv("TEW_SKILL_ROOT", str(skill_root))
    monkeypatch.setenv("TEW_USER_DATA_DIR", str(user_data))
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import project_manager as pm  # type: ignore
        import reference_library as rl  # type: ignore
        importlib.reload(pm)
        importlib.reload(rl)
        # Precondition: a project to work inside.
        pm.create_project("blog", "Test project")
        yield rl, pm, skill_root, user_data
    finally:
        sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture
def run_cli(tmp_path):
    skill_root = tmp_path / "skill"
    user_data = tmp_path / "user-data"
    skill_root.mkdir()
    user_data.mkdir()

    def _run(*args, expect_rc=0, script="reference_library"):
        env = os.environ.copy()
        env["TEW_SKILL_ROOT"] = str(skill_root)
        env["TEW_USER_DATA_DIR"] = str(user_data)
        env["PYTHONPATH"] = str(SCRIPTS_DIR)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / f"{script}.py"), *args],
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


# ─── add ──────────────────────────────────────────────────────────────────


class TestAdd:
    def test_add_url_auto_detects_kind(self, lib):
        rl, _, skill_root, _ = lib
        meta = rl.add_reference("blog", "https://arxiv.org/abs/1706.03762")
        assert meta["kind"] == "url"
        assert meta["id"] == "ref-001"
        assert meta["title"] == "https://arxiv.org/abs/1706.03762"  # default title
        card = skill_root / "projects" / "blog" / "references" / "ref-001.md"
        side = skill_root / "projects" / "blog" / "references" / "ref-001.json"
        assert card.is_file()
        assert side.is_file()

    def test_add_existing_file_detects_kind_file(self, lib, tmp_path):
        rl, _, _, _ = lib
        src = tmp_path / "note.txt"
        src.write_text("hello")
        meta = rl.add_reference("blog", str(src))
        assert meta["kind"] == "file"

    def test_add_plain_text_defaults_to_note(self, lib):
        rl, _, _, _ = lib
        meta = rl.add_reference("blog", "some random thought")
        assert meta["kind"] == "note"

    def test_add_explicit_kind_overrides_detection(self, lib):
        rl, _, _, _ = lib
        meta = rl.add_reference("blog", "https://example.com", kind="paper")
        assert meta["kind"] == "paper"

    def test_add_invalid_kind_raises(self, lib):
        rl, _, _, _ = lib
        with pytest.raises(ValueError):
            rl.add_reference("blog", "https://x", kind="not-a-kind")

    def test_add_tags_are_deduped_sorted(self, lib):
        rl, _, _, _ = lib
        meta = rl.add_reference(
            "blog", "https://x", tags=["transformers", "llm", "transformers"]
        )
        assert meta["tags"] == ["llm", "transformers"]

    def test_add_ref_ids_increment(self, lib):
        rl, _, _, _ = lib
        m1 = rl.add_reference("blog", "https://one")
        m2 = rl.add_reference("blog", "https://two")
        m3 = rl.add_reference("blog", "https://three")
        assert [m1["id"], m2["id"], m3["id"]] == ["ref-001", "ref-002", "ref-003"]

    def test_add_to_missing_project_raises(self, lib):
        rl, _, _, _ = lib
        with pytest.raises(FileNotFoundError):
            rl.add_reference("ghost", "https://x")

    def test_add_empty_source_raises(self, lib):
        rl, _, _, _ = lib
        with pytest.raises(ValueError):
            rl.add_reference("blog", "")

    def test_add_updates_index(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one", tags=["llm"])
        rl.add_reference("blog", "https://two")
        idx = json.loads(
            (skill_root / "projects" / "blog" / "references" / "index.json").read_text()
        )
        assert len(idx["refs"]) == 2
        assert idx["refs"][0]["tags"] == ["llm"]

    def test_card_contains_metadata(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference(
            "blog", "https://arxiv.org/abs/1706.03762",
            title="Attention Is All You Need",
            tags=["transformers", "paper"],
        )
        card_text = (
            skill_root / "projects" / "blog" / "references" / "ref-001.md"
        ).read_text()
        assert "Attention Is All You Need" in card_text
        assert "https://arxiv.org/abs/1706.03762" in card_text
        assert "transformers" in card_text


# ─── list / show ──────────────────────────────────────────────────────────


class TestListAndShow:
    def test_list_empty(self, lib):
        rl, _, _, _ = lib
        assert rl.list_references("blog") == []

    def test_list_returns_all(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one")
        rl.add_reference("blog", "https://two")
        refs = rl.list_references("blog")
        assert len(refs) == 2
        assert {r["id"] for r in refs} == {"ref-001", "ref-002"}

    def test_show_returns_meta_and_card(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", title="Paper 1")
        result = rl.show_reference("blog", "ref-001")
        assert result["meta"]["title"] == "Paper 1"
        assert "Paper 1" in result["card"]

    def test_show_missing_raises(self, lib):
        rl, _, _, _ = lib
        with pytest.raises(FileNotFoundError):
            rl.show_reference("blog", "ref-999")


# ─── tag / untag ──────────────────────────────────────────────────────────


class TestTagUntag:
    def test_tag_appends_and_dedups(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", tags=["llm"])
        tags = rl.tag_reference("blog", "ref-001", "transformers")
        assert tags == ["llm", "transformers"]
        # Idempotent
        tags2 = rl.tag_reference("blog", "ref-001", "transformers")
        assert tags2 == ["llm", "transformers"]

    def test_tag_propagates_to_index(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one")
        rl.tag_reference("blog", "ref-001", "important")
        idx = json.loads(
            (skill_root / "projects" / "blog" / "references" / "index.json").read_text()
        )
        assert idx["refs"][0]["tags"] == ["important"]

    def test_untag_removes(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", tags=["a", "b", "c"])
        tags = rl.untag_reference("blog", "ref-001", "b")
        assert tags == ["a", "c"]

    def test_untag_missing_tag_is_noop(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", tags=["a"])
        tags = rl.untag_reference("blog", "ref-001", "nonexistent")
        assert tags == ["a"]

    def test_tag_empty_raises(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one")
        with pytest.raises(ValueError):
            rl.tag_reference("blog", "ref-001", "")


# ─── remove ───────────────────────────────────────────────────────────────


class TestRemove:
    def test_remove_deletes_files_and_index_entry(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one")
        rl.remove_reference("blog", "ref-001")
        refs_dir = skill_root / "projects" / "blog" / "references"
        assert not (refs_dir / "ref-001.md").exists()
        assert not (refs_dir / "ref-001.json").exists()
        idx = json.loads((refs_dir / "index.json").read_text())
        assert idx["refs"] == []

    def test_remove_missing_raises(self, lib):
        rl, _, _, _ = lib
        with pytest.raises(FileNotFoundError):
            rl.remove_reference("blog", "ref-999")

    def test_remove_then_add_does_not_reuse_id(self, lib):
        """After deletion, new refs keep climbing — no id collision."""
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one")
        rl.add_reference("blog", "https://two")
        rl.remove_reference("blog", "ref-001")
        m3 = rl.add_reference("blog", "https://three")
        assert m3["id"] == "ref-003"


# ─── path ─────────────────────────────────────────────────────────────────


class TestFormatForPrompt:
    def test_empty_project_returns_empty_string(self, lib):
        rl, _, _, _ = lib
        # blog project exists but has no refs
        assert rl.format_for_prompt("blog") == ""

    def test_missing_project_returns_empty_string(self, lib):
        rl, _, _, _ = lib
        assert rl.format_for_prompt("ghost") == ""

    def test_malformed_slug_returns_empty_string(self, lib):
        rl, _, _, _ = lib
        # Graceful — callers inject this unconditionally.
        assert rl.format_for_prompt("../escape") == ""

    def test_single_ref_renders_expected_block(self, lib):
        rl, _, _, _ = lib
        rl.add_reference(
            "blog", "https://arxiv.org/abs/1706.03762",
            title="Attention Is All You Need",
            kind="paper",
            tags=["transformers", "llm"],
        )
        out = rl.format_for_prompt("blog")
        assert "## Reference Library (project: `blog`)" in out
        assert "1 reference(s)" in out
        assert "`ref-001`" in out
        assert "Attention Is All You Need" in out
        assert "https://arxiv.org/abs/1706.03762" in out
        # Tags sorted alphabetically by add_reference
        assert "Tags: llm, transformers" in out
        # No "Notes:" because parsed_at is empty (Phase 1 placeholder)
        assert "Notes:" not in out

    def test_multiple_refs(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", title="One")
        rl.add_reference("blog", "https://two", title="Two")
        rl.add_reference("blog", "https://three", title="Three")
        out = rl.format_for_prompt("blog")
        assert "3 reference(s)" in out
        assert "`ref-001`" in out
        assert "`ref-002`" in out
        assert "`ref-003`" in out
        # Headers kept in index order (matches add order)
        assert out.index("`ref-001`") < out.index("`ref-002`") < out.index("`ref-003`")

    def test_notes_shown_when_parsed(self, lib, tmp_path):
        """When the Phase 3 summarizer populates parsed_at + key_points,
        include a Notes line. `parsed_at` is the timestamp marker that
        distinguishes a summarized sidecar from a placeholder."""
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one", title="Paper 1")
        # Simulate a parser populating the sidecar.
        from pathlib import Path as _P
        import json as _j
        meta_file = skill_root / "projects" / "blog" / "references" / "ref-001.json"
        meta = _j.loads(meta_file.read_text())
        meta["parsed_at"] = "2026-01-01T00:00:00Z"
        meta["key_points"] = "Self-attention beats recurrence for long contexts."
        meta_file.write_text(_j.dumps(meta))
        out = rl.format_for_prompt("blog")
        assert "Notes: Self-attention beats recurrence" in out

    def test_no_tags_renders_underscore_none(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one", title="No tags here")
        out = rl.format_for_prompt("blog")
        assert "Tags: _none_" in out

    def test_cli_format_command(self, run_cli):
        # Use the run_cli fixture's skill/user-data dirs
        self._create_project(run_cli, "blog")
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "reference_library.py"),
                "add", "blog", "https://x", "--title", "T", "--tag", "a,b",
            ],
            env={
                **os.environ,
                "TEW_SKILL_ROOT": str(run_cli.skill_root),
                "TEW_USER_DATA_DIR": str(run_cli.user_data),
                "PYTHONPATH": str(SCRIPTS_DIR),
            },
            check=True,
            capture_output=True,
        )
        r = run_cli("format", "blog")
        assert "## Reference Library" in r.stdout
        assert "`ref-001` — T" in r.stdout

    def test_cli_format_missing_project_is_empty(self, run_cli):
        r = run_cli("format", "ghost")
        assert r.stdout == ""

    # Hoist the helper from TestCLI so we can call it here.
    def _create_project(self, run_cli, slug):
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "project_manager.py"),
                "create",
                slug,
            ],
            env={
                **os.environ,
                "TEW_SKILL_ROOT": str(run_cli.skill_root),
                "TEW_USER_DATA_DIR": str(run_cli.user_data),
                "PYTHONPATH": str(SCRIPTS_DIR),
            },
            check=True,
            capture_output=True,
        )


class TestPath:
    def test_path_md(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one")
        p = rl.ref_path("blog", "ref-001", "md")
        assert p == skill_root / "projects" / "blog" / "references" / "ref-001.md"

    def test_path_json(self, lib):
        rl, _, skill_root, _ = lib
        rl.add_reference("blog", "https://one")
        p = rl.ref_path("blog", "ref-001", "json")
        assert p == skill_root / "projects" / "blog" / "references" / "ref-001.json"

    def test_path_invalid_kind_raises(self, lib):
        rl, _, _, _ = lib
        rl.add_reference("blog", "https://one")
        with pytest.raises(ValueError):
            rl.ref_path("blog", "ref-001", "pdf")


# ─── CLI ──────────────────────────────────────────────────────────────────


class TestCLI:
    def _create_project(self, run_cli, slug):
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "project_manager.py"),
                "create",
                slug,
            ],
            env={
                **os.environ,
                "TEW_SKILL_ROOT": str(run_cli.skill_root),
                "TEW_USER_DATA_DIR": str(run_cli.user_data),
                "PYTHONPATH": str(SCRIPTS_DIR),
            },
            check=True,
            capture_output=True,
        )

    def test_add_and_list_round_trip(self, run_cli):
        self._create_project(run_cli, "blog")
        run_cli(
            "add", "blog", "https://arxiv.org/abs/1706.03762",
            "--title", "Attention",
            "--tag", "llm,transformers",
        )
        r = run_cli("list", "blog")
        data = json.loads(r.stdout)
        assert data["project"] == "blog"
        assert len(data["refs"]) == 1
        assert data["refs"][0]["title"] == "Attention"
        assert data["refs"][0]["tags"] == ["llm", "transformers"]

    def test_show_outputs_meta_and_card(self, run_cli):
        self._create_project(run_cli, "blog")
        run_cli("add", "blog", "https://x", "--title", "T")
        r = run_cli("show", "blog", "ref-001")
        data = json.loads(r.stdout)
        assert data["meta"]["title"] == "T"
        assert "T" in data["card"]

    def test_tag_and_untag(self, run_cli):
        self._create_project(run_cli, "blog")
        run_cli("add", "blog", "https://x")
        r1 = run_cli("tag", "blog", "ref-001", "important")
        assert json.loads(r1.stdout) == ["important"]
        r2 = run_cli("untag", "blog", "ref-001", "important")
        assert json.loads(r2.stdout) == []

    def test_remove(self, run_cli):
        self._create_project(run_cli, "blog")
        run_cli("add", "blog", "https://x")
        run_cli("remove", "blog", "ref-001")
        r = run_cli("list", "blog")
        assert json.loads(r.stdout)["refs"] == []

    def test_add_to_missing_project_returns_error(self, run_cli):
        r = run_cli("add", "ghost", "https://x", expect_rc=1)
        assert "not found" in r.stderr

    def test_path_cli(self, run_cli):
        self._create_project(run_cli, "blog")
        run_cli("add", "blog", "https://x")
        r = run_cli("path", "blog", "ref-001")
        expected = str(
            run_cli.skill_root / "projects" / "blog" / "references" / "ref-001.md"
        )
        assert r.stdout.strip() == expected
