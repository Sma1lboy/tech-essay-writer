"""Tests for install.py — skill install/uninstall into ~/.claude/skills/."""

import os
import shutil
import subprocess

import pytest

# Real project root (two levels up from tests/py/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _setup_fake_project(base_dir):
    """Create a fake project directory with install.py and skeleton components."""
    project = os.path.join(base_dir, "fake-project")
    scripts_py = os.path.join(project, "scripts", "py")
    prompts = os.path.join(project, "prompts")
    templates = os.path.join(project, "templates")
    os.makedirs(scripts_py)
    os.makedirs(prompts)
    os.makedirs(templates)

    # Create minimal component files
    with open(os.path.join(project, "SKILL.md"), "w") as f:
        f.write("# Skill\n")
    with open(os.path.join(prompts, "researcher.md"), "w") as f:
        f.write("# Prompt\n")
    with open(os.path.join(templates, "tutorial.md"), "w") as f:
        f.write("# Template\n")

    # Copy the real install.py into the fake project
    real_install = os.path.join(PROJECT_ROOT, "scripts", "py", "install.py")
    shutil.copy2(real_install, os.path.join(scripts_py, "install.py"))

    return project


def _run_install(project_dir, *args, home_dir=None, env_override=None):
    """Run install.py from a given project directory with optional HOME override."""
    cmd = ["python3", os.path.join(project_dir, "scripts", "py", "install.py"), *args]
    env = os.environ.copy()
    if home_dir:
        env["HOME"] = home_dir
    if env_override:
        env.update(env_override)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)


class TestFreshInstall:
    """install.py — fresh install"""

    def test_install_prints_success(self, run_script, fake_home):
        r = run_script("install")
        assert "Installed" in r.stdout

    def test_skill_directory_created(self, run_script, fake_home):
        run_script("install")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        assert os.path.isdir(skill_dir)

    def test_skill_md_is_symlink(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert os.path.islink(link)

    def test_scripts_py_is_symlink(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "scripts", "py")
        assert os.path.islink(link)

    def test_prompts_is_symlink(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "prompts")
        assert os.path.islink(link)

    def test_templates_is_symlink(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "templates")
        assert os.path.islink(link)

    def test_skill_md_points_to_project(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert os.readlink(link) == os.path.join(PROJECT_ROOT, "SKILL.md")

    def test_scripts_py_points_to_project(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "scripts", "py")
        assert os.readlink(link) == os.path.join(PROJECT_ROOT, "scripts", "py")

    def test_prompts_points_to_project(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "prompts")
        assert os.readlink(link) == os.path.join(PROJECT_ROOT, "prompts")

    def test_templates_points_to_project(self, run_script, fake_home):
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "templates")
        assert os.readlink(link) == os.path.join(PROJECT_ROOT, "templates")

    def test_skill_md_readable_through_symlink(self, run_script, fake_home):
        run_script("install")
        path = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert os.path.isfile(path)


class TestReplacesWholeDirectorySymlink:
    """install.py — replaces whole-directory symlink from old install method"""

    def test_precondition_whole_dir_symlink_exists(self, tmp_path):
        """Verify our test setup creates a whole-directory symlink."""
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)
        assert os.path.islink(skill_dir)

    def test_mentions_removing_existing_symlink(self, tmp_path):
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)

        r = _run_install(fake_project, home_dir=fake_home)
        assert "Removing existing symlink" in r.stdout

    def test_skill_dir_is_real_directory_after_replace(self, tmp_path):
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)

        _run_install(fake_project, home_dir=fake_home)
        assert os.path.isdir(skill_dir)
        assert not os.path.islink(skill_dir), "skill dir should be real directory, not symlink"

    def test_skill_md_symlink_created_after_replacing(self, tmp_path):
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)

        _run_install(fake_project, home_dir=fake_home)
        assert os.path.islink(os.path.join(skill_dir, "SKILL.md"))


class TestIdempotentReinstall:
    """install.py — idempotent reinstall"""

    def test_reinstall_prints_success(self, run_script, fake_home):
        run_script("install")
        r = run_script("install")
        assert "Installed" in r.stdout

    def test_skill_md_still_symlink_after_reinstall(self, run_script, fake_home):
        run_script("install")
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert os.path.islink(link)

    def test_skill_md_target_correct_after_reinstall(self, run_script, fake_home):
        run_script("install")
        run_script("install")
        link = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert os.readlink(link) == os.path.join(PROJECT_ROOT, "SKILL.md")


class TestUninstall:
    """install.py --uninstall"""

    def test_uninstall_prints_success(self, run_script, fake_home):
        run_script("install")
        r = run_script("install", "--uninstall")
        assert "Uninstalled" in r.stdout

    def test_skill_md_removed(self, run_script, fake_home):
        run_script("install")
        run_script("install", "--uninstall")
        path = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "SKILL.md")
        assert not os.path.exists(path) and not os.path.islink(path)

    def test_scripts_removed(self, run_script, fake_home):
        run_script("install")
        run_script("install", "--uninstall")
        path = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "scripts")
        assert not os.path.exists(path) and not os.path.islink(path)

    def test_prompts_removed(self, run_script, fake_home):
        run_script("install")
        run_script("install", "--uninstall")
        path = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "prompts")
        assert not os.path.exists(path) and not os.path.islink(path)

    def test_templates_removed(self, run_script, fake_home):
        run_script("install")
        run_script("install", "--uninstall")
        path = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer", "templates")
        assert not os.path.exists(path) and not os.path.islink(path)

    def test_skill_directory_removed(self, run_script, fake_home):
        run_script("install")
        run_script("install", "--uninstall")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        assert not os.path.exists(skill_dir) and not os.path.islink(skill_dir)


class TestUninstallWholeDirectorySymlink:
    """install.py --uninstall — removes whole-directory symlink"""

    def test_uninstall_removes_whole_dir_symlink(self, tmp_path):
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)

        r = _run_install(fake_project, "--uninstall", home_dir=fake_home)
        assert "Removed symlink" in r.stdout

    def test_whole_dir_symlink_gone_after_uninstall(self, tmp_path):
        fake_home = str(tmp_path / "home")
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        os.makedirs(os.path.dirname(skill_dir))
        fake_project = _setup_fake_project(str(tmp_path))
        os.symlink(fake_project, skill_dir)

        _run_install(fake_project, "--uninstall", home_dir=fake_home)
        assert not os.path.exists(skill_dir) and not os.path.islink(skill_dir)


class TestUninstallNoop:
    """install.py --uninstall — noop when nothing installed"""

    def test_uninstall_noop_message(self, run_script, fake_home):
        r = run_script("install", "--uninstall")
        assert "Nothing to uninstall" in r.stdout


class TestUnknownOption:
    """install.py — unknown option"""

    def test_rejects_unknown_option(self, run_script, fake_home):
        r = run_script("install", "--bogus")
        assert r.returncode != 0


class TestHelp:
    """install.py --help"""

    def test_help_shows_usage(self, run_script, fake_home):
        r = run_script("install", "--help")
        assert "Usage" in r.stdout

    def test_help_mentions_uninstall(self, run_script, fake_home):
        r = run_script("install", "--help")
        assert "uninstall" in r.stdout.lower()


class TestMissingComponent:
    """install.py — missing component gracefully skipped"""

    def test_warns_about_missing_component(self, tmp_path):
        fake_home = str(tmp_path / "home")
        os.makedirs(os.path.join(fake_home, ".claude", "skills"))
        fake_project = _setup_fake_project(str(tmp_path))
        # Remove the templates directory to trigger warning
        shutil.rmtree(os.path.join(fake_project, "templates"))

        r = _run_install(fake_project, home_dir=fake_home)
        assert "Warning" in r.stdout

    def test_warns_about_templates(self, tmp_path):
        fake_home = str(tmp_path / "home")
        os.makedirs(os.path.join(fake_home, ".claude", "skills"))
        fake_project = _setup_fake_project(str(tmp_path))
        shutil.rmtree(os.path.join(fake_project, "templates"))

        r = _run_install(fake_project, home_dir=fake_home)
        assert "templates" in r.stdout

    def test_skill_md_still_installed(self, tmp_path):
        fake_home = str(tmp_path / "home")
        os.makedirs(os.path.join(fake_home, ".claude", "skills"))
        fake_project = _setup_fake_project(str(tmp_path))
        shutil.rmtree(os.path.join(fake_project, "templates"))

        _run_install(fake_project, home_dir=fake_home)
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        assert os.path.islink(os.path.join(skill_dir, "SKILL.md"))

    def test_templates_not_installed(self, tmp_path):
        fake_home = str(tmp_path / "home")
        os.makedirs(os.path.join(fake_home, ".claude", "skills"))
        fake_project = _setup_fake_project(str(tmp_path))
        shutil.rmtree(os.path.join(fake_project, "templates"))

        _run_install(fake_project, home_dir=fake_home)
        skill_dir = os.path.join(fake_home, ".claude", "skills", "tech-essay-writer")
        assert not os.path.exists(os.path.join(skill_dir, "templates"))
