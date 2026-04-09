"""Tests for config.py — configuration management."""

import json
import os

import pytest


class TestConfigInit:
    def test_init_creates_config(self, run_script, fake_home):
        r = run_script("config", "init")
        assert "initialized" in r.stdout

    def test_config_file_created(self, run_script, fake_home):
        run_script("config", "init")
        assert os.path.isfile(os.path.join(fake_home, ".tech-essay-writer", "config.json"))

    def test_default_values(self, run_script, fake_home):
        run_script("config", "init")
        with open(os.path.join(fake_home, ".tech-essay-writer", "config.json")) as f:
            config = f.read()
        assert "internal" in config
        assert "external" in config
        assert "technical" in config
        assert '"en"' in config
        assert "true" in config
        assert "3" in config
        assert "software engineers" in config
        assert "updated_at" in config

    def test_init_idempotent(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "init")
        assert "already exists" in r.stdout


class TestConfigRead:
    def test_read_shows_content(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "read")
        assert "internal" in r.stdout
        assert "technical" in r.stdout
        assert "software engineers" in r.stdout
        assert "en" in r.stdout

    def test_read_shows_author_profile(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "read")
        assert "True" in r.stdout

    def test_read_shows_max_rounds(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "read")
        assert "3" in r.stdout

    def test_read_empty_config(self, run_script, tmp_path, monkeypatch):
        empty_home = str(tmp_path / "emptyhome")
        os.makedirs(empty_home)
        monkeypatch.setenv("HOME", empty_home)
        r = run_script("config", "read")
        assert "No config yet" in r.stdout


class TestConfigGet:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        self.run("config", "init")

    def test_get_platforms(self):
        r = self.run("config", "get", "default_platforms")
        assert "internal" in r.stdout
        assert "external" in r.stdout

    def test_get_writing_style(self):
        r = self.run("config", "get", "writing_style")
        assert r.stdout.strip() == "technical"

    def test_get_language(self):
        r = self.run("config", "get", "language")
        assert r.stdout.strip() == "en"

    def test_get_use_author_profile(self):
        r = self.run("config", "get", "use_author_profile")
        assert r.stdout.strip() == "true"

    def test_get_max_refinement_rounds(self):
        r = self.run("config", "get", "max_refinement_rounds")
        assert r.stdout.strip() == "3"

    def test_get_audiences(self):
        r = self.run("config", "get", "target_audiences")
        assert "software engineers" in r.stdout

    def test_get_nonexistent_key(self):
        r = self.run("config", "get", "nonexistent")
        assert r.stdout.strip() == ""

    def test_get_on_empty_config(self, tmp_path, monkeypatch):
        empty_home = str(tmp_path / "emptyhome2")
        os.makedirs(empty_home)
        monkeypatch.setenv("HOME", empty_home)
        r = self.run("config", "get", "language")
        assert r.stdout.strip() == ""


class TestConfigSet:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        self.home = str(tmp_path / "sethome")
        os.makedirs(self.home)
        monkeypatch.setenv("HOME", self.home)
        self.run = run_script
        self.run("config", "init")

    def test_set_writing_style(self):
        r = self.run("config", "set", "writing_style", "conversational")
        assert "Set writing_style" in r.stdout
        r = self.run("config", "get", "writing_style")
        assert r.stdout.strip() == "conversational"

    def test_set_language(self):
        r = self.run("config", "set", "language", "zh")
        assert "Set language" in r.stdout
        r = self.run("config", "get", "language")
        assert r.stdout.strip() == "zh"

    def test_set_use_author_profile_false(self):
        r = self.run("config", "set", "use_author_profile", "false")
        assert "Set use_author_profile" in r.stdout
        r = self.run("config", "get", "use_author_profile")
        assert r.stdout.strip() == "false"

    def test_set_use_author_profile_true(self):
        self.run("config", "set", "use_author_profile", "false")
        self.run("config", "set", "use_author_profile", "true")
        r = self.run("config", "get", "use_author_profile")
        assert r.stdout.strip() == "true"

    def test_set_max_refinement_rounds(self):
        r = self.run("config", "set", "max_refinement_rounds", "5")
        assert "Set max_refinement_rounds" in r.stdout
        r = self.run("config", "get", "max_refinement_rounds")
        assert r.stdout.strip() == "5"

    def test_set_platforms_json(self):
        r = self.run("config", "set", "default_platforms", '["internal","medium","wechat"]')
        assert "Set default_platforms" in r.stdout
        r = self.run("config", "get", "default_platforms")
        assert "medium" in r.stdout
        assert "wechat" in r.stdout

    def test_set_audiences_json(self):
        r = self.run("config", "set", "target_audiences", '["backend engineers","CTOs"]')
        assert "Set target_audiences" in r.stdout
        r = self.run("config", "get", "target_audiences")
        assert "CTOs" in r.stdout


class TestConfigSetValidation:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "valhome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.run("config", "init")

    def test_reject_invalid_style(self):
        r = self.run("config", "set", "writing_style", "invalid-style")
        assert r.returncode != 0

    def test_reject_invalid_language(self):
        r = self.run("config", "set", "language", "fr")
        assert r.returncode != 0

    def test_reject_invalid_platform(self):
        r = self.run("config", "set", "default_platforms", '["internal","fakePlatform"]')
        assert r.returncode != 0

    def test_reject_rounds_too_high(self):
        r = self.run("config", "set", "max_refinement_rounds", "99")
        assert r.returncode != 0

    def test_reject_rounds_zero(self):
        r = self.run("config", "set", "max_refinement_rounds", "0")
        assert r.returncode != 0

    def test_reject_rounds_not_number(self):
        r = self.run("config", "set", "max_refinement_rounds", "abc")
        assert r.returncode != 0

    def test_reject_invalid_boolean(self):
        r = self.run("config", "set", "use_author_profile", "maybe")
        assert r.returncode != 0

    def test_reject_unknown_key(self):
        r = self.run("config", "set", "unknown_key", "value")
        assert r.returncode != 0

    def test_reject_non_json_platforms(self):
        r = self.run("config", "set", "default_platforms", "not-json")
        assert r.returncode != 0


class TestConfigAddRemovePlatform:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "plathome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.run("config", "init")

    def test_add_platform(self):
        r = self.run("config", "add-platform", "medium")
        assert "Added platform: medium" in r.stdout
        r = self.run("config", "get", "default_platforms")
        assert "medium" in r.stdout

    def test_add_duplicate_platform(self):
        self.run("config", "add-platform", "medium")
        r = self.run("config", "add-platform", "medium")
        assert "already" in r.stdout

    def test_add_invalid_platform(self):
        r = self.run("config", "add-platform", "fakePlatform")
        assert r.returncode != 0

    def test_remove_platform(self):
        self.run("config", "add-platform", "medium")
        r = self.run("config", "remove-platform", "medium")
        assert "Removed platform: medium" in r.stdout
        r = self.run("config", "get", "default_platforms")
        assert "medium" not in r.stdout

    def test_remove_nonexistent_platform(self):
        r = self.run("config", "remove-platform", "hashnode")
        assert r.returncode != 0


class TestConfigAddRemoveAudience:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "audhome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.run("config", "init")

    def test_add_audience(self):
        r = self.run("config", "add-audience", "DevOps engineers")
        assert "Added audience: DevOps engineers" in r.stdout
        r = self.run("config", "get", "target_audiences")
        assert "DevOps" in r.stdout

    def test_add_duplicate_audience(self):
        self.run("config", "add-audience", "DevOps engineers")
        r = self.run("config", "add-audience", "DevOps engineers")
        assert "already" in r.stdout

    def test_remove_audience(self):
        self.run("config", "add-audience", "DevOps engineers")
        r = self.run("config", "remove-audience", "DevOps engineers")
        assert "Removed audience: DevOps engineers" in r.stdout
        r = self.run("config", "get", "target_audiences")
        assert "DevOps" not in r.stdout

    def test_remove_nonexistent_audience(self):
        r = self.run("config", "remove-audience", "nonexistent")
        assert r.returncode != 0


class TestConfigReset:
    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "resethome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        self.run = run_script
        self.run("config", "init")

    def test_reset_message(self):
        self.run("config", "set", "language", "zh")
        r = self.run("config", "reset")
        assert "reset to defaults" in r.stdout

    def test_reset_restores_language(self):
        self.run("config", "set", "language", "zh")
        self.run("config", "reset")
        r = self.run("config", "get", "language")
        assert r.stdout.strip() == "en"

    def test_reset_restores_style(self):
        self.run("config", "set", "writing_style", "narrative")
        self.run("config", "reset")
        r = self.run("config", "get", "writing_style")
        assert r.stdout.strip() == "technical"


class TestConfigExport:
    def test_export_is_json(self, run_script, fake_home):
        run_script("config", "init")
        r = run_script("config", "export")
        assert "default_platforms" in r.stdout
        assert "writing_style" in r.stdout
        assert "language" in r.stdout

    def test_export_auto_inits(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "exporthome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("config", "export")
        assert "default_platforms" in r.stdout
        assert os.path.isfile(os.path.join(home, ".tech-essay-writer", "config.json"))


class TestConfigUsage:
    def test_usage_shows_commands(self, run_script, fake_home):
        r = run_script("config")
        output = r.stdout + r.stderr
        assert "init" in output
        assert "read" in output
        assert "get" in output
        assert "set" in output


class TestConfigSetWithoutInit:
    def test_set_without_init(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "noinithome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        r = run_script("config", "set", "language", "zh")
        assert "Set language" in r.stdout
        r = run_script("config", "get", "language")
        assert r.stdout.strip() == "zh"
        r = run_script("config", "get", "writing_style")
        assert r.stdout.strip() == "technical"


class TestConfigPipelineIntegration:
    def test_pipeline_uses_config_language_zh(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "integhome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        run_script("config", "set", "language", "zh")
        project = str(tmp_path / "config-proj")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "Config Test Topic")
        r = run_script("pipeline_state", "get-field", project, "language")
        assert "zh" in r.stdout

    def test_pipeline_uses_config_language_en(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "integhome2")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        project = str(tmp_path / "config-proj2")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "Config Test EN")
        r = run_script("pipeline_state", "get-field", project, "language")
        assert "en" in r.stdout

    def test_pipeline_falls_back_to_en(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "noconfighome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        project = str(tmp_path / "config-proj3")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "No Config Topic")
        r = run_script("pipeline_state", "get-field", project, "language")
        assert "en" in r.stdout

    def test_pipeline_uses_config_max_rounds(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "integhome3")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        run_script("config", "set", "max_refinement_rounds", "5")
        project = str(tmp_path / "config-proj4")
        os.makedirs(project)
        run_script("pipeline_state", "init", project, "Rounds Test")
        r = run_script("pipeline_state", "get-field", project, "max_refinement_rounds")
        assert "5" in r.stdout


class TestConfigOrchestrateIntegration:
    def test_build_config_summary(self, run_script, tmp_path, monkeypatch, script_dir):
        home = str(tmp_path / "orchhome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        run_script("config", "set", "writing_style", "narrative")
        run_script("config", "add-platform", "medium")
        project = str(tmp_path / "orch-proj")
        state_dir = os.path.join(project, ".essay-state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "pipeline-state.json"), "w") as f:
            json.dump({"stage": "intake", "topic": "test", "language": "en"}, f)
        r = run_script("orchestrate", project, script_dir, "build-config-summary")
        assert "internal" in r.stdout
        assert "medium" in r.stdout
        assert "narrative" in r.stdout
        assert "software engineers" in r.stdout
        assert "en" in r.stdout


class TestConfigAtomicWrite:
    def test_no_tmp_files(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "atomichome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        config_dir = os.path.join(home, ".tech-essay-writer")
        tmp_files = [f for f in os.listdir(config_dir) if ".tmp." in f]
        assert len(tmp_files) == 0


class TestConfigAllValidStyles:
    def test_all_styles_accepted(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "stylehome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        for style in ["technical", "conversational", "narrative", "formal", "casual", "academic"]:
            run_script("config", "set", "writing_style", style)
            r = run_script("config", "get", "writing_style")
            assert r.stdout.strip() == style


class TestConfigAllValidPlatforms:
    def test_all_platforms(self, run_script, tmp_path, monkeypatch):
        home = str(tmp_path / "allplathome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        run_script("config", "init")
        run_script("config", "set", "default_platforms",
                   '["internal","external","medium","devto","hashnode","wechat","juejin"]')
        r = run_script("config", "get", "default_platforms")
        assert "juejin" in r.stdout
        assert "hashnode" in r.stdout
        assert "wechat" in r.stdout
