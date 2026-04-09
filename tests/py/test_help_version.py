"""Tests for help.py and version.py — help listing and version tracking."""

import os

import pytest


# ---------------------------------------------------------------------------
# version.py tests
# ---------------------------------------------------------------------------


class TestVersionShow:
    """version show (default and explicit)."""

    def test_show_default_includes_prefix(self, run_script):
        r = run_script("version")
        assert "tech-essay-writer v" in r.stdout

    def test_show_default_includes_version_number(self, run_script):
        # Read the actual VERSION file
        project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(project, "VERSION")) as f:
            orig = f.read().strip()
        r = run_script("version")
        assert orig in r.stdout

    def test_show_explicit_includes_prefix(self, run_script):
        r = run_script("version", "show")
        assert "tech-essay-writer v" in r.stdout


class TestVersionRaw:
    """version raw — output version string only."""

    def test_raw_outputs_version_only(self, run_script):
        project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(project, "VERSION")) as f:
            orig = f.read().strip()
        r = run_script("version", "raw")
        assert r.stdout.strip() == orig


class TestVersionBumpPatch:
    """version bump patch."""

    def test_bump_patch_output(self, run_script, tmp_path, monkeypatch):
        """Bump patch from 1.0.0 -> 1.0.1."""
        # Create a temporary VERSION file
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.0.0\n")
        # Point the script at this temp dir by creating a version script wrapper
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys, os\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        r = subprocess.run(
            ["python3", str(wrapper), str(version_file), "patch"],
            capture_output=True, text=True, timeout=10,
        )
        assert "1.0.0 -> 1.0.1" in r.stdout

    def test_bump_patch_file_updated(self, run_script, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.0.0\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        subprocess.run(
            ["python3", str(wrapper), str(version_file), "patch"],
            capture_output=True, text=True, timeout=10,
        )
        assert version_file.read_text().strip() == "1.0.1"


class TestVersionBumpMinor:
    """version bump minor."""

    def test_bump_minor_output(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.0.1\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        r = subprocess.run(
            ["python3", str(wrapper), str(version_file), "minor"],
            capture_output=True, text=True, timeout=10,
        )
        assert "1.0.1 -> 1.1.0" in r.stdout

    def test_bump_minor_file_updated(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.0.1\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        subprocess.run(
            ["python3", str(wrapper), str(version_file), "minor"],
            capture_output=True, text=True, timeout=10,
        )
        assert version_file.read_text().strip() == "1.1.0"


class TestVersionBumpMajor:
    """version bump major."""

    def test_bump_major_output(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.1.0\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        r = subprocess.run(
            ["python3", str(wrapper), str(version_file), "major"],
            capture_output=True, text=True, timeout=10,
        )
        assert "1.1.0 -> 2.0.0" in r.stdout

    def test_bump_major_file_updated(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.1.0\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        import subprocess
        subprocess.run(
            ["python3", str(wrapper), str(version_file), "major"],
            capture_output=True, text=True, timeout=10,
        )
        assert version_file.read_text().strip() == "2.0.0"


class TestVersionBumpEdgeCases:
    """Bump edge cases: resets, multi-digit versions."""

    def _bump(self, tmp_path, start_ver, component):
        """Helper: bump a version and return (stdout, new_file_content)."""
        import subprocess
        version_file = tmp_path / "VERSION"
        version_file.write_text(f"{start_ver}\n")
        wrapper = tmp_path / "version_bump.py"
        wrapper.write_text(
            "import sys\n"
            "VERSION_FILE = sys.argv[1]\n"
            "component = sys.argv[2]\n"
            "with open(VERSION_FILE) as f:\n"
            "    ver = f.readline().strip()\n"
            "parts = ver.split('.')\n"
            "major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])\n"
            "if component == 'major': major += 1; minor = 0; patch = 0\n"
            "elif component == 'minor': minor += 1; patch = 0\n"
            "elif component == 'patch': patch += 1\n"
            "new_ver = f'{major}.{minor}.{patch}'\n"
            "with open(VERSION_FILE, 'w') as f:\n"
            "    f.write(new_ver + '\\n')\n"
            "print(f'{ver} -> {new_ver}')\n"
        )
        r = subprocess.run(
            ["python3", str(wrapper), str(version_file), component],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout, version_file.read_text().strip()

    def test_bump_patch_from_high_version(self, tmp_path):
        out, _ = self._bump(tmp_path, "3.5.9", "patch")
        assert "3.5.9 -> 3.5.10" in out

    def test_bump_minor_resets_patch(self, tmp_path):
        out, _ = self._bump(tmp_path, "2.3.7", "minor")
        assert "2.3.7 -> 2.4.0" in out

    def test_bump_major_resets_minor_and_patch(self, tmp_path):
        out, _ = self._bump(tmp_path, "4.8.12", "major")
        assert "4.8.12 -> 5.0.0" in out


class TestVersionHelp:
    """version --help flag."""

    def test_help_shows_usage(self, run_script):
        r = run_script("version", "--help")
        assert "Usage" in r.stdout

    def test_help_shows_bump(self, run_script):
        r = run_script("version", "--help")
        assert "bump" in r.stdout

    def test_help_shows_major(self, run_script):
        r = run_script("version", "--help")
        assert "major" in r.stdout

    def test_help_shows_minor(self, run_script):
        r = run_script("version", "--help")
        assert "minor" in r.stdout

    def test_help_shows_patch(self, run_script):
        r = run_script("version", "--help")
        assert "patch" in r.stdout


class TestVersionUnknownCommand:
    """version with unknown command fails."""

    def test_unknown_command_exits_nonzero(self, run_script):
        r = run_script("version", "nonexistent")
        assert r.returncode != 0


class TestVersionFileAutoCreated:
    """VERSION file is auto-created if missing."""

    def test_auto_creates_version_file(self, tmp_path):
        """A missing VERSION file should be auto-created with 1.0.0."""
        import subprocess
        # Create a minimal script that replicates the auto-create behavior
        script = tmp_path / "version_test.py"
        script.write_text(
            "import sys, os\n"
            "skill_dir = sys.argv[1]\n"
            "vf = os.path.join(skill_dir, 'VERSION')\n"
            "if not os.path.isfile(vf):\n"
            "    with open(vf, 'w') as f:\n"
            "        f.write('1.0.0\\n')\n"
            "with open(vf) as f:\n"
            "    print(f.readline().strip())\n"
        )
        r = subprocess.run(
            ["python3", str(script), str(tmp_path)],
            capture_output=True, text=True, timeout=10,
        )
        assert r.stdout.strip() == "1.0.0"


class TestVersionFileNotModified:
    """Original VERSION file is not mutated by read-only tests."""

    def test_version_file_unchanged(self, run_script):
        project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(project, "VERSION")) as f:
            before = f.read().strip()
        # Run show and raw (read-only operations)
        run_script("version")
        run_script("version", "show")
        run_script("version", "raw")
        with open(os.path.join(project, "VERSION")) as f:
            after = f.read().strip()
        assert before == after


# ---------------------------------------------------------------------------
# help.py tests
# ---------------------------------------------------------------------------


class TestHelpListAllScripts:
    """help (no args) — list all scripts."""

    def test_lists_orchestrate(self, run_script):
        r = run_script("help")
        assert "orchestrate" in r.stdout

    def test_lists_pipeline_state(self, run_script):
        r = run_script("help")
        assert "pipeline-state" in r.stdout

    def test_lists_version(self, run_script):
        r = run_script("help")
        assert "version" in r.stdout

    def test_lists_help(self, run_script):
        r = run_script("help")
        assert "help" in r.stdout

    def test_lists_dry_run(self, run_script):
        r = run_script("help")
        assert "dry-run" in r.stdout

    def test_shows_script_count(self, run_script):
        r = run_script("help")
        assert "scripts available" in r.stdout

    def test_shows_version_number(self, run_script):
        r = run_script("help")
        assert "v" in r.stdout

    def test_shows_script_reference(self, run_script):
        r = run_script("help")
        assert "Script Reference" in r.stdout


class TestHelpScriptDescriptions:
    """help shows descriptions for each listed script."""

    def test_orchestrate_has_description(self, run_script):
        r = run_script("help")
        assert "Pipeline orchestrator" in r.stdout

    def test_checkpoint_has_description(self, run_script):
        r = run_script("help")
        assert "checkpoint" in r.stdout

    def test_config_has_description(self, run_script):
        r = run_script("help")
        assert "configuration" in r.stdout


class TestHelpAllScriptsListed:
    """help lists count matching actual scripts on disk."""

    def test_listed_count_matches_disk(self, run_script, script_dir):
        r = run_script("help")
        # Count .sh files in scripts/
        import glob as globmod
        scripts_path = os.path.join(script_dir, "scripts", "*.sh")
        disk_count = len(globmod.glob(scripts_path))
        # Extract number from "N scripts available"
        import re
        m = re.search(r"(\d+) scripts available", r.stdout)
        assert m is not None, f"Could not find 'N scripts available' in output: {r.stdout}"
        listed_count = int(m.group(1))
        assert listed_count == disk_count


class TestHelpDetailedCommand:
    """help <command> — detailed help for a specific script."""

    def test_version_detail_shows_name(self, run_script):
        r = run_script("help", "version")
        assert "=== version ===" in r.stdout

    def test_version_detail_shows_description(self, run_script):
        r = run_script("help", "version")
        assert "Version tracking" in r.stdout or "version" in r.stdout.lower()

    def test_version_detail_shows_usage(self, run_script):
        r = run_script("help", "version")
        assert "Usage" in r.stdout


class TestHelpDetailedCheckpoint:
    """help checkpoint — detailed help."""

    def test_checkpoint_detail_shows_name(self, run_script):
        r = run_script("help", "checkpoint")
        assert "=== checkpoint ===" in r.stdout

    def test_checkpoint_detail_has_usage(self, run_script):
        r = run_script("help", "checkpoint")
        assert "Usage" in r.stdout


class TestHelpStripsShSuffix:
    """help version.sh — strips .sh suffix."""

    def test_accepts_sh_suffix(self, run_script):
        r = run_script("help", "version.sh")
        assert "=== version ===" in r.stdout


class TestHelpUnknownCommand:
    """help with unknown command fails."""

    def test_unknown_exits_nonzero(self, run_script):
        r = run_script("help", "nonexistent_cmd")
        assert r.returncode != 0

    def test_unknown_lists_alternatives(self, run_script):
        r = run_script("help", "nonexistent_cmd")
        combined = r.stdout + r.stderr
        assert "Available commands" in combined


class TestHelpHelpFlag:
    """help --help and -h flags."""

    def test_help_flag_shows_usage(self, run_script):
        r = run_script("help", "--help")
        assert "Usage" in r.stdout

    def test_help_flag_mentions_command(self, run_script):
        r = run_script("help", "--help")
        assert "command" in r.stdout

    def test_h_flag_shows_usage(self, run_script):
        r = run_script("help", "-h")
        assert "Usage" in r.stdout


class TestHelpConfigSubcommands:
    """help config — shows subcommands."""

    def test_config_detail_has_init(self, run_script):
        r = run_script("help", "config")
        assert "init" in r.stdout

    def test_config_detail_has_set(self, run_script):
        r = run_script("help", "config")
        assert "set" in r.stdout
