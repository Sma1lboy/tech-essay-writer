"""Shared fixtures for tech-essay-writer pytest suite."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Project root: two levels up from tests/py/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def script_dir():
    """Path to the project root (used by orchestrate which needs SCRIPT_DIR)."""
    return str(PROJECT_ROOT)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory and yield its path."""
    project = tmp_path / "test-project"
    project.mkdir()
    return str(project)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Set HOME to a temp directory, restore after test."""
    home = tmp_path / "fakehome"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return str(home)


@pytest.fixture
def run_script(tmp_path):
    """Helper to invoke a Python script in scripts/py/ via subprocess.

    Usage:
        result = run_script("pipeline_state", "init", "/tmp/proj", "My Topic")

    Calls: python3 scripts/py/pipeline_state.py init /tmp/proj "My Topic"
    Returns: subprocess.CompletedProcess with stdout/stderr as strings.

    Each invocation runs with TEW_SKILL_ROOT + TEW_USER_DATA_DIR pointed at
    a per-test sandbox. This keeps pipeline_state.init's project auto-resolve
    (which would otherwise create ~/.tech-essay-writer/active-project.txt and
    a real default project under the source tree) from leaking across tests.
    """
    sandbox_skill = tmp_path / "tew-skill"
    sandbox_user = tmp_path / "tew-user"
    sandbox_skill.mkdir(parents=True, exist_ok=True)
    sandbox_user.mkdir(parents=True, exist_ok=True)

    def _run(script_name, *args, **kwargs):
        cmd = [
            "python3",
            str(PROJECT_ROOT / "scripts" / "py" / f"{script_name}.py"),
            *[str(a) for a in args],
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "scripts" / "py")
        env["TEW_SKILL_ROOT"] = str(sandbox_skill)
        env["TEW_USER_DATA_DIR"] = str(sandbox_user)
        # Allow callers to override env vars
        if "env_override" in kwargs:
            env.update(kwargs.pop("env_override"))
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout", 30),
        )
    return _run
