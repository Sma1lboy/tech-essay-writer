"""Tests for article templates and code_validate.py."""

import json
import os

import pytest


# All template names (without .md extension)
ALL_TEMPLATES = [
    "tutorial", "deep-dive", "narrative", "opinion", "case-study",
    "comparison", "listicle", "incident-postmortem", "release-announcement", "adr",
]

# Required sections every template must have
REQUIRED_SECTIONS = [
    "## Structure", "## Tone", "## Code Density", "## Target Length", "## Reader Promise",
]


# ── Template existence tests (bash tests 1-10) ──────────────────────────────


class TestTemplateExistence:
    @pytest.mark.parametrize("tmpl", ALL_TEMPLATES)
    def test_template_exists(self, script_dir, tmpl):
        path = os.path.join(script_dir, "templates", f"{tmpl}.md")
        assert os.path.isfile(path), f"template {tmpl}.md not found at {path}"


# ── Template content tests (bash tests 11-60) ───────────────────────────────


class TestTemplateContent:
    @pytest.mark.parametrize("tmpl", ALL_TEMPLATES)
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_template_has_required_section(self, script_dir, tmpl, section):
        path = os.path.join(script_dir, "templates", f"{tmpl}.md")
        content = open(path).read()
        assert section in content, f"{tmpl} missing '{section}'"


# ── New template content validation (bash tests 93-100) ─────────────────────


class TestTemplateContentValidation:
    """Detailed content validation for specific templates."""

    # Test 93: comparison.md structure items
    def test_comparison_has_hook(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "comparison.md")).read()
        assert "Hook" in content

    def test_comparison_has_criteria(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "comparison.md")).read()
        assert "Criteria" in content

    def test_comparison_has_verdict(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "comparison.md")).read()
        assert "Verdict" in content

    def test_comparison_has_comparison_table(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "comparison.md")).read()
        assert "comparison table" in content

    # Test 94: listicle.md structure items
    def test_listicle_has_hook(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "listicle.md")).read()
        assert "Hook" in content

    def test_listicle_has_items(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "listicle.md")).read()
        assert "Items" in content

    def test_listicle_has_honorable_mentions(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "listicle.md")).read()
        assert "Honorable mentions" in content

    # Test 95: incident-postmortem.md structure items
    def test_postmortem_has_tldr(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "incident-postmortem.md")).read()
        assert "TL;DR" in content

    def test_postmortem_has_timeline(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "incident-postmortem.md")).read()
        assert "Timeline" in content

    def test_postmortem_has_root_cause(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "incident-postmortem.md")).read()
        assert "Root cause" in content

    def test_postmortem_has_action_items(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "incident-postmortem.md")).read()
        assert "Action items" in content

    # Test 96: release-announcement.md structure items
    def test_release_has_headline_feature(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "release-announcement.md")).read()
        assert "Headline feature" in content

    def test_release_has_migration_guide(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "release-announcement.md")).read()
        assert "Migration guide" in content

    def test_release_has_breaking_changes(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "release-announcement.md")).read()
        assert "Breaking changes" in content

    # Test 97: adr.md structure items
    def test_adr_has_context(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "adr.md")).read()
        assert "Context" in content

    def test_adr_has_decision(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "adr.md")).read()
        assert "Decision" in content

    def test_adr_has_status(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "adr.md")).read()
        assert "Status" in content

    def test_adr_has_consequences(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "adr.md")).read()
        assert "Consequences" in content

    def test_adr_has_alternatives_considered(self, script_dir):
        content = open(os.path.join(script_dir, "templates", "adr.md")).read()
        assert "Alternatives considered" in content

    # Test 98: Code density ranges have percentages
    @pytest.mark.parametrize("tmpl", ALL_TEMPLATES)
    def test_code_density_has_percentage(self, script_dir, tmpl):
        content = open(os.path.join(script_dir, "templates", f"{tmpl}.md")).read()
        assert "%" in content, f"{tmpl} has no percentage in Code Density"

    # Test 99: Target lengths have word counts
    @pytest.mark.parametrize("tmpl", ALL_TEMPLATES)
    def test_target_length_has_word_count(self, script_dir, tmpl):
        content = open(os.path.join(script_dir, "templates", f"{tmpl}.md")).read()
        assert "words" in content, f"{tmpl} has no word count in Target Length"

    # Test 100: Reader Promise uses quotes
    @pytest.mark.parametrize("tmpl", ALL_TEMPLATES)
    def test_reader_promise_has_quoted_text(self, script_dir, tmpl):
        content = open(os.path.join(script_dir, "templates", f"{tmpl}.md")).read()
        assert '"After reading this' in content, f'{tmpl} Reader Promise missing quoted text'


# ── code_validate tests ─────────────────────────────────────────────────────


class TestCodeValidateValidJS:
    """Test 61: Valid JS code block passes."""

    def test_valid_js_report_has_file(self, run_script, tmp_path):
        md = tmp_path / "valid-js.md"
        md.write_text(
            "# Test Article\n\n"
            "```javascript\n"
            "function add(a, b) {\n"
            "  return a + b;\n"
            "}\n"
            "console.log(add(1, 2));\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        assert "valid-js.md" in r.stdout

    def test_valid_js_validated_count(self, run_script, tmp_path):
        md = tmp_path / "valid-js.md"
        md.write_text(
            "# Test Article\n\n"
            "```javascript\n"
            "function add(a, b) {\n"
            "  return a + b;\n"
            "}\n"
            "console.log(add(1, 2));\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["validated"] == 1

    def test_valid_js_passes(self, run_script, tmp_path):
        md = tmp_path / "valid-js.md"
        md.write_text(
            "# Test Article\n\n"
            "```javascript\n"
            "function add(a, b) {\n"
            "  return a + b;\n"
            "}\n"
            "console.log(add(1, 2));\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["pass"] == 1


class TestCodeValidateInvalidJS:
    """Test 62: Invalid JS syntax fails."""

    def test_invalid_js_fails(self, run_script, tmp_path):
        md = tmp_path / "invalid-js.md"
        md.write_text(
            "# Bad JS\n\n"
            "```javascript\n"
            "function broken( {\n"
            "  return 1;\n"
            "}\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["fail"] == 1

    def test_invalid_js_has_syntax_error(self, run_script, tmp_path):
        md = tmp_path / "invalid-js.md"
        md.write_text(
            "# Bad JS\n\n"
            "```javascript\n"
            "function broken( {\n"
            "  return 1;\n"
            "}\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        out = r.stdout
        assert ("syntax_valid\": false" in out or
                "syntax error" in out or
                '"syntax_valid": false' in out)


class TestCodeValidateValidPython:
    """Test 63: Valid Python code block passes."""

    def test_valid_python_passes(self, run_script, tmp_path):
        md = tmp_path / "valid-py.md"
        md.write_text(
            "# Python Test\n\n"
            "```python\n"
            'def hello():\n'
            '    return "world"\n'
            "\n"
            "print(hello())\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["pass"] == 1


class TestCodeValidateInvalidPython:
    """Test 64: Invalid Python syntax fails."""

    def test_invalid_python_fails(self, run_script, tmp_path):
        md = tmp_path / "invalid-py.md"
        md.write_text(
            "# Bad Python\n\n"
            "```python\n"
            "def broken(\n"
            "    return 1\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["fail"] == 1


class TestCodeValidateFragments:
    """Tests 65-66: Fragment detection (ellipsis and TODO)."""

    def test_ellipsis_fragment_detected(self, run_script, tmp_path):
        """Test 65: Code block with ellipsis -> fragment detected."""
        md = tmp_path / "fragment.md"
        md.write_text(
            "# Fragment Example\n\n"
            "```javascript\n"
            "function handler(req, res) {\n"
            "  // handle request\n"
            "  ...\n"
            "}\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        out = r.stdout
        assert ("fragments_detected\": true" in out or
                "contains ellipsis" in out or
                '"fragments_detected": true' in out)

    def test_todo_fragment_detected(self, run_script, tmp_path):
        """Test 66: Code block with TODO -> fragment."""
        md = tmp_path / "todo-fragment.md"
        md.write_text(
            "# TODO Fragment\n\n"
            "```python\n"
            "def process():\n"
            "    # TODO: implement this\n"
            "    pass\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        assert "TODO" in r.stdout


class TestCodeValidateNoLanguage:
    """Test 67: Code block with no language tag -> skipped."""

    def test_no_lang_skipped(self, run_script, tmp_path):
        md = tmp_path / "no-lang.md"
        md.write_text(
            "# No Language\n\n"
            "```\n"
            "some random text here\n"
            "not real code\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["skipped"] == 1

    def test_no_lang_summary_skip(self, run_script, tmp_path):
        md = tmp_path / "no-lang.md"
        md.write_text(
            "# No Language\n\n"
            "```\n"
            "some random text here\n"
            "not real code\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["skip"] == 1


class TestCodeValidateNonexistent:
    """Test 68: Non-existent file -> error."""

    def test_nonexistent_file_error(self, run_script, tmp_path):
        r = run_script("code_validate", str(tmp_path / "nonexistent.md"))
        out = r.stdout + r.stderr
        assert "error" in out.lower() or "file not found" in out.lower()


class TestCodeValidateMultipleBlocks:
    """Test 69: Multiple blocks -> correct total count."""

    MULTI_MD = (
        "# Multi Block\n\n"
        "```javascript\n"
        "const a = 1;\n"
        "```\n\n"
        "Some text.\n\n"
        "```python\n"
        "x = 2\n"
        "```\n\n"
        "More text.\n\n"
        "```bash\n"
        "echo hello\n"
        "```\n\n"
        "```\n"
        "plain text\n"
        "```\n"
    )

    def test_multiple_blocks_total_count(self, run_script, tmp_path):
        md = tmp_path / "multi.md"
        md.write_text(self.MULTI_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["total_blocks"] == 4

    def test_multiple_blocks_validated_count(self, run_script, tmp_path):
        md = tmp_path / "multi.md"
        md.write_text(self.MULTI_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["validated"] == 3

    def test_multiple_blocks_skipped_count(self, run_script, tmp_path):
        md = tmp_path / "multi.md"
        md.write_text(self.MULTI_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["skipped"] == 1


class TestCodeValidateBash:
    """Tests 70-71: Valid and invalid bash."""

    def test_valid_bash_passes(self, run_script, tmp_path):
        """Test 70: Valid bash code block."""
        md = tmp_path / "valid-bash.md"
        md.write_text(
            "# Bash Test\n\n"
            "```bash\n"
            "#!/bin/bash\n"
            "for i in 1 2 3; do\n"
            '  echo "$i"\n'
            "done\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["pass"] == 1

    def test_invalid_bash_fails(self, run_script, tmp_path):
        """Test 71: Invalid bash syntax."""
        md = tmp_path / "invalid-bash.md"
        md.write_text(
            "# Bad Bash\n\n"
            "```bash\n"
            "if then\n"
            "  echo broken\n"
            "fi\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["fail"] == 1


class TestCodeValidateImports:
    """Tests 72-74: Import parsing."""

    def test_js_imports_parsed(self, run_script, tmp_path):
        """Test 72: JS with imports."""
        md = tmp_path / "imports-js.md"
        md.write_text(
            "# Imports\n\n"
            "```javascript\n"
            "import React from 'react';\n"
            "import { useState } from 'react';\n"
            "const fs = require('fs');\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        imports_count = len(report["blocks"][0]["imports"])
        assert imports_count >= 2

    def test_relative_import_unverifiable(self, run_script, tmp_path):
        """Test 73: JS with relative import -> unverifiable."""
        md = tmp_path / "relative-import.md"
        md.write_text(
            "# Relative Import\n\n"
            "```javascript\n"
            "import { helper } from './utils';\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        assert "unverifiable" in r.stdout

    def test_python_imports_parsed(self, run_script, tmp_path):
        """Test 74: Python imports."""
        md = tmp_path / "imports-py.md"
        md.write_text(
            "# Python Imports\n\n"
            "```python\n"
            "import json\n"
            "from os.path import join\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        py_imports = len(report["blocks"][0]["imports"])
        assert py_imports >= 2


class TestCodeValidateEmpty:
    """Test 75: Empty markdown -> no blocks."""

    def test_empty_markdown_zero_blocks(self, run_script, tmp_path):
        md = tmp_path / "empty.md"
        md.write_text("# Empty Article\n\nNo code blocks here.\n")
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["total_blocks"] == 0


class TestCodeValidateJSON:
    """Test 76: Output is valid JSON."""

    def test_output_is_valid_json(self, run_script, tmp_path):
        md = tmp_path / "json-check.md"
        md.write_text(
            "# JSON Check\n\n"
            "```javascript\n"
            "const x = 1;\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        # Should not raise
        json.loads(r.stdout)


class TestCodeValidateLanguageAliases:
    """Tests 77-80: Language alias recognition."""

    def test_sh_recognized_as_bash(self, run_script, tmp_path):
        """Test 77: 'sh' language tag recognized as bash."""
        md = tmp_path / "sh-tag.md"
        md.write_text(
            "# Shell\n\n"
            "```sh\n"
            'echo "hello"\n'
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["blocks"][0]["language"] == "bash"

    def test_js_alias_recognized(self, run_script, tmp_path):
        """Test 78: 'js' alias recognized."""
        md = tmp_path / "js-tag.md"
        md.write_text(
            "# JS Alias\n\n"
            "```js\n"
            "const x = 1;\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["blocks"][0]["language"] == "javascript"

    def test_py_alias_recognized(self, run_script, tmp_path):
        """Test 79: 'py' alias recognized."""
        md = tmp_path / "py-tag.md"
        md.write_text(
            "# PY Alias\n\n"
            "```py\n"
            "x = 1\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["blocks"][0]["language"] == "python"

    def test_ts_alias_recognized(self, run_script, tmp_path):
        """Test 80: 'ts' alias recognized."""
        md = tmp_path / "ts-tag.md"
        md.write_text(
            "# TS Alias\n\n"
            "```ts\n"
            "const x: number = 1;\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["blocks"][0]["language"] == "typescript"


class TestCodeValidatePseudoCode:
    """Test 81: Pseudo-code marker detected."""

    def test_pseudo_code_marker(self, run_script, tmp_path):
        md = tmp_path / "pseudo.md"
        md.write_text(
            "# Pseudo\n\n"
            "```javascript\n"
            "function doStuff() {\n"
            "  // your code here\n"
            "}\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        out = r.stdout
        assert ("pseudo-code marker" in out or
                "your code here" in out or
                '"fragments_detected": true' in out)


class TestCodeValidateMisspelling:
    """Test 82: Misspelled import flagged."""

    def test_misspelled_import(self, run_script, tmp_path):
        md = tmp_path / "misspell.md"
        md.write_text(
            "# Misspell\n\n"
            "```javascript\n"
            "import express from 'expresss';\n"
            "```\n"
        )
        r = run_script("code_validate", str(md))
        assert "possible_misspelling" in r.stdout


class TestCodeValidateMixed:
    """Tests 83-84: Mixed file with pass/fail/skip."""

    MIXED_MD = (
        "# Mixed\n\n"
        "```javascript\n"
        "const ok = true;\n"
        "```\n\n"
        "```python\n"
        "def good():\n"
        "    return True\n"
        "```\n\n"
        "```javascript\n"
        "function bad( {\n"
        "  return;\n"
        "}\n"
        "```\n\n"
        "```\n"
        "not code\n"
        "```\n"
    )

    def test_mixed_total_blocks(self, run_script, tmp_path):
        """Test 83a: Mixed total blocks."""
        md = tmp_path / "mixed.md"
        md.write_text(self.MIXED_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["total_blocks"] == 4

    def test_mixed_pass_count(self, run_script, tmp_path):
        """Test 83b: Mixed pass count."""
        md = tmp_path / "mixed.md"
        md.write_text(self.MIXED_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["pass"] == 2

    def test_mixed_fail_count(self, run_script, tmp_path):
        """Test 83c: Mixed fail count."""
        md = tmp_path / "mixed.md"
        md.write_text(self.MIXED_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["fail"] == 1

    def test_mixed_skip_count(self, run_script, tmp_path):
        """Test 83d: Mixed skip count."""
        md = tmp_path / "mixed.md"
        md.write_text(self.MIXED_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["summary"]["skip"] == 1

    def test_line_in_file_is_positive(self, run_script, tmp_path):
        """Test 84: line_in_file is correct (positive)."""
        md = tmp_path / "mixed.md"
        md.write_text(self.MIXED_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        issues = report["issues"]
        assert len(issues) > 0
        assert issues[0]["line_in_file"] > 0


class TestCodeValidateAllValid:
    """Tests 85-86: All-valid file."""

    ALL_VALID_MD = (
        "# All Valid\n\n"
        "```javascript\n"
        "const x = 1;\n"
        "```\n\n"
        "```python\n"
        "y = 2\n"
        "```\n\n"
        "```bash\n"
        'echo "hi"\n'
        "```\n"
    )

    def test_all_valid_zero_issues(self, run_script, tmp_path):
        """Test 85: No issues for all-valid file."""
        md = tmp_path / "all-valid.md"
        md.write_text(self.ALL_VALID_MD)
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert len(report["issues"]) == 0

    def test_file_path_in_report(self, run_script, tmp_path):
        """Test 86: File path appears in report."""
        md = tmp_path / "all-valid.md"
        md.write_text(self.ALL_VALID_MD)
        r = run_script("code_validate", str(md))
        assert "all-valid.md" in r.stdout


class TestCodeValidateUnknownLanguage:
    """Test 87: Unrecognized language tags skipped."""

    def test_unknown_languages_skipped(self, run_script, tmp_path):
        md = tmp_path / "unknown-lang.md"
        md.write_text(
            "# Unknown\n\n"
            "```ruby\n"
            'puts "hello"\n'
            "```\n\n"
            "```haskell\n"
            'main = putStrLn "hello"\n'
            "```\n"
        )
        r = run_script("code_validate", str(md))
        report = json.loads(r.stdout)
        assert report["skipped"] == 2


class TestCodeValidateNoArgs:
    """Test 88: No arguments -> error/usage."""

    def test_no_args_shows_usage(self, run_script):
        r = run_script("code_validate")
        out = r.stdout + r.stderr
        assert ("Usage" in out or "error" in out or "no file specified" in out)


# ── orchestrate.sh integration tests (89-92) ────────────────────────────────


class TestOrchestrateCodeValidation:
    """Tests for build-code-validation through orchestrate.py."""

    @pytest.fixture
    def pipeline_project(self, tmp_path, monkeypatch):
        """Create a project dir with .essay-state/."""
        home = str(tmp_path / "fakehome")
        os.makedirs(home)
        monkeypatch.setenv("HOME", home)
        project = str(tmp_path / "proj-cv")
        os.makedirs(os.path.join(project, ".essay-state"), exist_ok=True)
        return project

    def test_usage_shows_build_code_validation(self, run_script, tmp_path, script_dir):
        """Test 89: build-code-validation command in usage."""
        r = run_script("orchestrate", str(tmp_path), script_dir, "invalid")
        out = r.stdout + r.stderr
        assert "build-code-validation" in out

    def test_build_code_validation_with_draft(self, run_script, pipeline_project, script_dir):
        """Test 90: build-code-validation with a draft."""
        draft = os.path.join(pipeline_project, ".essay-state", "draft-v1.md")
        with open(draft, "w") as f:
            f.write(
                "# Test Draft\n\n"
                "```javascript\n"
                "const x = 1;\n"
                "```\n"
            )
        r = run_script("orchestrate", pipeline_project, script_dir, "build-code-validation")
        out = r.stdout + r.stderr
        assert "total_blocks" in out or "validated" in out

    def test_build_code_validation_no_draft_error(self, run_script, pipeline_project, script_dir):
        """Test 91: build-code-validation with no draft -> error."""
        r = run_script("orchestrate", pipeline_project, script_dir, "build-code-validation")
        out = r.stdout + r.stderr
        assert "error" in out.lower() or "not found" in out.lower()

    def test_build_code_validation_uses_final_external_fallback(self, run_script, pipeline_project, script_dir):
        """Test 92: build-code-validation uses final-external when no draft."""
        final = os.path.join(pipeline_project, ".essay-state", "final-external.md")
        with open(final, "w") as f:
            f.write(
                "# Final\n\n"
                "```python\n"
                "x = 1\n"
                "```\n"
            )
        r = run_script("orchestrate", pipeline_project, script_dir, "build-code-validation")
        out = r.stdout + r.stderr
        assert "total_blocks" in out or "validated" in out
