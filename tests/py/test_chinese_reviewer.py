"""Tests for Chinese writing quality reviewer integration.

Validates orchestrate.py, quality_score.py, and pipeline_state.py
handle the chinese reviewer correctly (only active when language=zh).
"""

import json
import os

import pytest


# ============================================================
# Helpers
# ============================================================


DRAFT_ZH = """\
# Chinese Test Article

This is a test draft in Chinese context.

## Section 1

Some technical content here.

```python
def test():
    pass
```

## Conclusion

Done.
"""

DRAFT_EN = """\
# English Test Article

Test draft for English context.

## Conclusion

Done.
"""

STANDARD_REVIEWERS = [
    "technical", "editor", "adversarial", "audience", "seo", "external", "factcheck"
]


def setup_project(tmp_path, run_script, script_dir, name, topic, language):
    """Create and initialize a project with the given language."""
    proj = str(tmp_path / name)
    os.makedirs(os.path.join(proj, ".essay-state"), exist_ok=True)
    run_script("pipeline_state", "init", proj, topic)
    run_script("pipeline_state", "set-field", proj, "language", json.dumps(language))
    run_script("pipeline_state", "set-stage", proj, "draft")
    return proj


def write_draft(proj, content):
    """Write a draft file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", "draft-v1.md")
    with open(path, "w") as f:
        f.write(content)


def write_review(proj, reviewer, rating="PASS", summary="Good"):
    """Write a mock review JSON into .essay-state/."""
    path = os.path.join(proj, ".essay-state", f"review-{reviewer}.json")
    data = {"reviewer": reviewer, "rating": rating, "summary": summary, "issues": []}
    with open(path, "w") as f:
        json.dump(data, f)


def write_all_standard_reviews(proj):
    """Write mock reviews for all 7 standard reviewers."""
    for r in STANDARD_REVIEWERS:
        write_review(proj, r)


# ============================================================
# Test 1-4: Chinese review prompts when language=zh
# ============================================================


class TestChineseReviewPromptZh:
    """Tests 1-4: orchestrate builds chinese review prompts when language=zh."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.proj = setup_project(tmp_path, run_script, script_dir, "proj-zh", "Chinese Test Topic", "zh")
        write_draft(self.proj, DRAFT_ZH)
        run_script("pipeline_state", "set-stage", self.proj, "review")
        self.run = run_script
        self.sd = script_dir
        r = run_script("orchestrate", self.proj, self.sd, "build-review-prompts", "chinese")
        self.prompt_output = r.stdout

    def test_chinese_reviewer_prompt_nonempty(self):
        """T1: chinese reviewer prompt is non-empty for zh."""
        assert len(self.prompt_output) > 0

    def test_prompt_includes_reviewer_template(self):
        """T2: chinese prompt includes reviewer-chinese template."""
        assert "Chinese Writing Quality Reviewer" in self.prompt_output

    def test_prompt_includes_draft_content(self):
        """T3: chinese prompt includes draft content."""
        assert "Chinese Test Article" in self.prompt_output

    def test_prompt_includes_language_directive(self):
        """T4: chinese prompt has language directive."""
        assert "Language Directive" in self.prompt_output


# ============================================================
# Test 5: Chinese reviewer rejected when language=en
# ============================================================


class TestChineseReviewerRejectedForEn:
    """Test 5: chinese reviewer is rejected when language=en."""

    def test_chinese_reviewer_rejected_for_en(self, run_script, tmp_path, fake_home, script_dir):
        proj = setup_project(tmp_path, run_script, script_dir, "proj-en", "English Test Topic", "en")
        write_draft(proj, DRAFT_EN)
        run_script("pipeline_state", "set-stage", proj, "review")
        r = run_script("orchestrate", proj, script_dir, "build-review-prompts", "chinese")
        assert r.returncode != 0


# ============================================================
# Test 6: Standard reviewers still work when language=zh
# ============================================================


class TestStandardReviewersWorkForZh:
    """Test 6: standard reviewers still work when language=zh."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.proj = setup_project(tmp_path, run_script, script_dir, "proj-zh-std", "Chinese Test Topic", "zh")
        write_draft(self.proj, DRAFT_ZH)
        run_script("pipeline_state", "set-stage", self.proj, "review")
        self.run = run_script
        self.sd = script_dir

    @pytest.mark.parametrize("reviewer", STANDARD_REVIEWERS)
    def test_standard_reviewer_works_for_zh(self, reviewer):
        r = self.run("orchestrate", self.proj, self.sd, "build-review-prompts", reviewer)
        assert len(r.stdout) > 0


# ============================================================
# Tests 7-12: quality_score.py with chinese reviewer
# ============================================================


class TestQualityScoreChineseReviewer:
    """Tests 7-12: quality-score includes/excludes chinese reviewer based on language."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        # zh project with all 8 reviews (7 standard + chinese)
        self.proj_zh = setup_project(tmp_path, run_script, script_dir, "qs-zh", "Chinese Test Topic", "zh")
        write_draft(self.proj_zh, DRAFT_ZH)
        run_script("pipeline_state", "set-stage", self.proj_zh, "review")
        write_all_standard_reviews(self.proj_zh)
        write_review(self.proj_zh, "chinese", rating="NATIVE", summary="Reads naturally")

        # en project with 7 standard reviews
        self.proj_en = setup_project(tmp_path, run_script, script_dir, "qs-en", "English Test Topic", "en")
        write_draft(self.proj_en, DRAFT_EN)
        run_script("pipeline_state", "set-stage", self.proj_en, "review")
        write_all_standard_reviews(self.proj_en)

        self.run = run_script

    def test_verbose_output_includes_chinese_reviewer(self):
        """T7: quality-score verbose output includes chinese reviewer for zh."""
        r = self.run("quality_score", self.proj_zh, "verbose")
        assert "chinese" in r.stdout

    def test_reviews_expected_8_for_zh(self):
        """T8: reviews_expected=8 for zh."""
        r = self.run("quality_score", self.proj_zh)
        data = json.loads(r.stdout)
        assert data["reviews_expected"] == 8

    def test_reviews_expected_7_for_en(self):
        """T9: reviews_expected=7 for en."""
        r = self.run("quality_score", self.proj_en)
        data = json.loads(r.stdout)
        assert data["reviews_expected"] == 7

    def test_native_rating_in_verbose(self):
        """T10: NATIVE rating appears in verbose output."""
        r = self.run("quality_score", self.proj_zh, "verbose")
        assert "NATIVE" in r.stdout

    def test_translation_smell_rating_in_verbose(self):
        """T11: TRANSLATION_SMELL rating appears in verbose output."""
        write_review(self.proj_zh, "chinese", rating="TRANSLATION_SMELL",
                     summary="Reads like a translation")
        r = self.run("quality_score", self.proj_zh, "verbose")
        assert "TRANSLATION_SMELL" in r.stdout

    def test_acceptable_rating_in_verbose(self):
        """T12: ACCEPTABLE rating appears in verbose output."""
        write_review(self.proj_zh, "chinese", rating="ACCEPTABLE",
                     summary="Minor issues")
        r = self.run("quality_score", self.proj_zh, "verbose")
        assert "ACCEPTABLE" in r.stdout


# ============================================================
# Tests 13-15: pipeline_state review_panel_complete
# ============================================================


class TestPanelCompleteZh:
    """Tests 13-14: panel requires 8 reviews for zh."""

    @pytest.fixture(autouse=True)
    def setup(self, run_script, tmp_path, fake_home, script_dir):
        self.proj = setup_project(tmp_path, run_script, script_dir, "panel-zh", "Panel Test", "zh")
        run_script("pipeline_state", "set-stage", self.proj, "review")
        self.run = run_script

    def test_panel_not_complete_with_7_of_8_reviews(self):
        """T13: panel NOT complete with 7/8 reviews for zh."""
        for r in STANDARD_REVIEWERS:
            write_review(self.proj, r, rating="PASS", summary="OK")
            self.run("pipeline_state", "add-review", self.proj,
                     os.path.join(self.proj, ".essay-state", f"review-{r}.json"))
        r = self.run("pipeline_state", "read", self.proj)
        state = json.loads(r.stdout)
        assert state["review_panel_complete"] is False

    def test_panel_complete_with_8_of_8_reviews(self):
        """T14: panel complete with 8/8 reviews for zh."""
        for r in STANDARD_REVIEWERS:
            write_review(self.proj, r, rating="PASS", summary="OK")
            self.run("pipeline_state", "add-review", self.proj,
                     os.path.join(self.proj, ".essay-state", f"review-{r}.json"))
        write_review(self.proj, "chinese", rating="NATIVE", summary="Great")
        self.run("pipeline_state", "add-review", self.proj,
                 os.path.join(self.proj, ".essay-state", "review-chinese.json"))
        r = self.run("pipeline_state", "read", self.proj)
        state = json.loads(r.stdout)
        assert state["review_panel_complete"] is True


class TestPanelCompleteEn:
    """Test 15: panel complete with 7 reviews for en."""

    def test_panel_complete_with_7_of_7_reviews(self, run_script, tmp_path, fake_home, script_dir):
        """T15: panel complete with 7/7 reviews for en."""
        proj = setup_project(tmp_path, run_script, script_dir, "panel-en", "EN Panel Test", "en")
        run_script("pipeline_state", "set-stage", proj, "review")
        for r in STANDARD_REVIEWERS:
            write_review(proj, r, rating="PASS", summary="OK")
            run_script("pipeline_state", "add-review", proj,
                       os.path.join(proj, ".essay-state", f"review-{r}.json"))
        r = run_script("pipeline_state", "read", proj)
        state = json.loads(r.stdout)
        assert state["review_panel_complete"] is True


# ============================================================
# Test 16: quality-score excludes chinese for en
# ============================================================


class TestQualityScoreExcludesChineseForEn:
    """Test 16: quality-score does NOT include chinese weight for language=en."""

    def test_chinese_score_excluded_for_en(self, run_script, tmp_path, fake_home, script_dir):
        proj = setup_project(tmp_path, run_script, script_dir, "qs-en-excl", "English Test Topic", "en")
        write_draft(proj, DRAFT_EN)
        run_script("pipeline_state", "set-stage", proj, "review")
        write_all_standard_reviews(proj)
        # Even if a review-chinese.json exists for en project, it should not be scored
        write_review(proj, "chinese", rating="NATIVE", summary="Reads naturally")
        r = run_script("quality_score", proj)
        data = json.loads(r.stdout)
        assert "chinese" not in data.get("dimension_scores", {})


# ============================================================
# Test 17: Chinese reviewer prompt output file path
# ============================================================


class TestChineseReviewerOutputPath:
    """Test 17: chinese prompt instructs writing to review-chinese.json."""

    def test_prompt_references_output_file(self, run_script, tmp_path, fake_home, script_dir):
        proj = setup_project(tmp_path, run_script, script_dir, "prompt-path", "Chinese Test Topic", "zh")
        write_draft(proj, DRAFT_ZH)
        run_script("pipeline_state", "set-stage", proj, "review")
        r = run_script("orchestrate", proj, script_dir, "build-review-prompts", "chinese")
        assert "review-chinese.json" in r.stdout
