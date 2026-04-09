"""Tests for readability_score.py and word_frequency.py."""

import json

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────

SIMPLE_MD = """\
# Simple Article

This is a simple test. It has short sentences. The words are easy to read. Dogs like to play. Cats like to sleep. Birds like to fly.

This is another paragraph. It is also simple. We write short sentences here.
"""

COMPLEX_MD = """\
# Advanced Distributed Systems Architecture

The implementation of sophisticated distributed consensus algorithms necessitates a comprehensive understanding of the fundamental theoretical underpinnings that characterize Byzantine fault-tolerant systems, particularly when considering the implications of asynchronous network partitions on the availability guarantees prescribed by the CAP theorem and its subsequent refinements.

Furthermore, the reconciliation of eventually consistent replicated data structures with the stringent linearizability requirements demanded by financial transaction processing systems presents a multifaceted engineering challenge that requires careful consideration of the tradeoffs between consistency, availability, and partition tolerance.

The architectural decisions surrounding the selection of appropriate consensus protocols must account for the probabilistic guarantees offered by randomized algorithms versus the deterministic guarantees provided by classical Paxos-derived protocols.
"""

PASSIVE_MD = """\
# Project Update

The code was written by the team. The tests were run by the CI pipeline. The bugs were found by the QA engineers. The feature was deployed by the DevOps team. The documentation was updated by the technical writer.

The architecture was redesigned to improve performance. The database was migrated to a new cluster. The API was refactored for better usability.
"""

AI_SLOP_MD = """\
# The Evolving Landscape

Let us delve into the comprehensive landscape of modern technology. We must leverage robust frameworks to streamline our development processes. It is essential to utilize cutting-edge tools that facilitate rapid innovation.

The ever-evolving tapestry of our digital ecosystem requires us to harness transformative paradigms. By leveraging comprehensive strategies, we can streamline operations and facilitate groundbreaking synergy across the organization.

We must delve deeper into these robust solutions. The landscape continues to shift as we leverage new comprehensive approaches to streamline and facilitate holistic transformation.
"""

WITH_CODE_MD = """\
# Code Tutorial

Here is how to create a function. This is a simple example.

```python
def hello_world():
    print("Hello, world!")
    return True
```

The function above prints a greeting. It returns a boolean value. This is straightforward code.

```javascript
const add = (a, b) => a + b;
console.log(add(1, 2));
```

These examples show basic syntax. They are easy to understand.
"""

ONLY_CODE_MD = """\
```python
x = 1
y = 2
```
"""

OVERUSED_MD = """\
# Performance Analysis

Performance is critical for applications. Good performance means happy users. We measure performance with benchmarks. Performance testing reveals bottlenecks. Without performance optimization, applications suffer. Performance metrics guide our decisions. The performance team tracks performance daily. Performance improvements boost performance scores. Every performance review examines performance data. Performance goals drive performance culture.
"""

MINIMAL_MD = """\
Hello world.
"""

FRONTMATTER_MD = """\
---
title: Test Article
author: Test
date: 2024-01-01
---

# Article Title

This is a simple article with frontmatter. The content should be analyzed without the metadata block.

A second paragraph adds more content. It has clear and direct sentences.
"""

VERBOSE_TEST_MD = """\
# Test

The cat sat on the mat. The dog ran in the park. Birds fly in the sky.
"""

JARGON_MD = """\
# Architecture Decision

The containerization of our microservices enables greater scalability and interoperability across the organization. Our bespoke orchestration layer provides idempotent operations through non-blocking asynchronous processing.

The standardization and normalization of our API surface ensures orthogonal composability. This opinionated framework offers out-of-the-box turnkey solutions with zero boilerplate configuration.
"""


@pytest.fixture
def simple_md(tmp_path):
    p = tmp_path / "simple.md"
    p.write_text(SIMPLE_MD)
    return str(p)


@pytest.fixture
def complex_md(tmp_path):
    p = tmp_path / "complex.md"
    p.write_text(COMPLEX_MD)
    return str(p)


@pytest.fixture
def passive_md(tmp_path):
    p = tmp_path / "passive.md"
    p.write_text(PASSIVE_MD)
    return str(p)


@pytest.fixture
def ai_slop_md(tmp_path):
    p = tmp_path / "ai-slop.md"
    p.write_text(AI_SLOP_MD)
    return str(p)


@pytest.fixture
def with_code_md(tmp_path):
    p = tmp_path / "with-code.md"
    p.write_text(WITH_CODE_MD)
    return str(p)


@pytest.fixture
def only_code_md(tmp_path):
    p = tmp_path / "only-code.md"
    p.write_text(ONLY_CODE_MD)
    return str(p)


@pytest.fixture
def overused_md(tmp_path):
    p = tmp_path / "overused.md"
    p.write_text(OVERUSED_MD)
    return str(p)


@pytest.fixture
def minimal_md(tmp_path):
    p = tmp_path / "minimal.md"
    p.write_text(MINIMAL_MD)
    return str(p)


@pytest.fixture
def frontmatter_md(tmp_path):
    p = tmp_path / "frontmatter.md"
    p.write_text(FRONTMATTER_MD)
    return str(p)


@pytest.fixture
def verbose_test_md(tmp_path):
    p = tmp_path / "verbose-test.md"
    p.write_text(VERBOSE_TEST_MD)
    return str(p)


@pytest.fixture
def jargon_md(tmp_path):
    p = tmp_path / "jargon.md"
    p.write_text(JARGON_MD)
    return str(p)


# ── readability_score tests ──────────────────────────────────────────────


class TestReadabilityScoreErrors:
    """T1-T2: error handling for readability_score."""

    def test_no_file_argument_shows_error(self, run_script):
        """T1: no file argument shows usage/error."""
        r = run_script("readability_score")
        assert "error" in (r.stdout + r.stderr).lower()

    def test_missing_file_returns_error(self, run_script, tmp_path):
        """T2: missing file returns error JSON."""
        r = run_script("readability_score", str(tmp_path / "nonexistent.md"))
        assert "file not found" in (r.stdout + r.stderr).lower()


class TestReadabilityScoreJSON:
    """T3: valid JSON output."""

    def test_simple_text_produces_valid_json(self, run_script, simple_md):
        """T3: simple text produces valid JSON."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert isinstance(data, dict)


class TestReadabilityScoreGradeLevels:
    """T4-T5: grade level thresholds."""

    def test_simple_text_low_grade(self, run_script, simple_md):
        """T4: simple text grade < 8."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["flesch_kincaid_grade"] < 8

    def test_complex_text_high_grade(self, run_script, complex_md):
        """T5: complex text grade > 12."""
        r = run_script("readability_score", complex_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["flesch_kincaid_grade"] > 12


class TestReadabilityScoreCounts:
    """T6-T8: word, sentence, paragraph counts."""

    def test_word_count_positive(self, run_script, simple_md):
        """T6: word count > 0."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["total_words"] > 0

    def test_sentence_count_positive(self, run_script, simple_md):
        """T7: sentence count > 0."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["total_sentences"] > 0

    def test_paragraph_count(self, run_script, simple_md):
        """T8: paragraph count >= 2."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["total_paragraphs"] >= 2


class TestReadabilityScoreComplexity:
    """T9-T10: complex sentence detection."""

    def test_complex_sentences_detected(self, run_script, complex_md):
        """T9: complex sentences > 0 in complex text."""
        r = run_script("readability_score", complex_md)
        data = json.loads(r.stdout)
        assert data["complexity"]["complex_sentence_count"] > 0

    def test_no_complex_sentences_in_simple(self, run_script, simple_md):
        """T10: no complex sentences in simple text."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["complexity"]["complex_sentence_count"] == 0


class TestReadabilityScorePassiveVoice:
    """T11-T12: passive voice detection."""

    def test_passive_voice_detected(self, run_script, passive_md):
        """T11: passive voice count > 0."""
        r = run_script("readability_score", passive_md)
        data = json.loads(r.stdout)
        assert data["passive_voice"]["passive_count"] > 0

    def test_passive_percentage_substantial(self, run_script, passive_md):
        """T12: passive % > 30 for passive-heavy text."""
        r = run_script("readability_score", passive_md)
        data = json.loads(r.stdout)
        assert data["passive_voice"]["passive_percentage"] > 30


class TestReadabilityScoreCodeStripping:
    """T13: code blocks stripped from analysis."""

    def test_code_blocks_stripped(self, run_script, with_code_md):
        """T13: code blocks stripped (no 'def hello' in output)."""
        r = run_script("readability_score", with_code_md)
        assert "def hello" not in r.stdout


class TestReadabilityScoreFleschEase:
    """T14-T15: Flesch reading ease."""

    def test_flesch_reading_ease_present(self, run_script, simple_md):
        """T14: has flesch_reading_ease."""
        r = run_script("readability_score", simple_md)
        assert "flesch_reading_ease" in r.stdout

    def test_simple_text_high_reading_ease(self, run_script, simple_md):
        """T15: simple reading ease > 60."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["flesch_reading_ease"] > 60


class TestReadabilityScoreInterpretation:
    """T16: grade interpretation."""

    def test_grade_interpretation_present(self, run_script, simple_md):
        """T16: grade_interpretation present."""
        r = run_script("readability_score", simple_md)
        assert "grade_interpretation" in r.stdout


class TestReadabilityScoreVerbose:
    """T17-T19: verbose mode."""

    def test_verbose_includes_sentence_details(self, run_script, verbose_test_md):
        """T17: verbose has sentence_details."""
        r = run_script("readability_score", verbose_test_md, "verbose")
        assert "sentence_details" in r.stdout

    def test_verbose_has_word_count_per_sentence(self, run_script, verbose_test_md):
        """T18: verbose has word_count per sentence."""
        r = run_script("readability_score", verbose_test_md, "verbose")
        assert "word_count" in r.stdout

    def test_non_verbose_omits_sentence_details(self, run_script, verbose_test_md):
        """T19: non-verbose omits sentence_details."""
        r = run_script("readability_score", verbose_test_md)
        assert "sentence_details" not in r.stdout


class TestReadabilityScoreMetadata:
    """T20-T23: miscellaneous output fields."""

    def test_file_name_in_output(self, run_script, simple_md):
        """T20: file name in output."""
        r = run_script("readability_score", simple_md)
        assert "simple.md" in r.stdout

    def test_avg_syllables_reasonable(self, run_script, simple_md):
        """T21: avg syllables per word between 0.9 and 3.0."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        avg = data["metrics"]["avg_syllables_per_word"]
        assert avg > 0.9
        assert avg < 3.0

    def test_frontmatter_stripped(self, run_script, frontmatter_md):
        """T22: frontmatter stripped (no 'date: 2024')."""
        r = run_script("readability_score", frontmatter_md)
        assert "date: 2024" not in r.stdout

    def test_total_syllables_positive(self, run_script, simple_md):
        """T23: total_syllables > 0."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        assert data["metrics"]["total_syllables"] > 0


# ── word_frequency tests ────────────────────────────────────────────────


class TestWordFrequencyErrors:
    """T24-T25: error handling for word_frequency."""

    def test_no_file_argument_shows_error(self, run_script):
        """T24: no file argument shows usage/error."""
        r = run_script("word_frequency")
        assert "error" in (r.stdout + r.stderr).lower()

    def test_missing_file_returns_error(self, run_script, tmp_path):
        """T25: missing file returns error JSON."""
        r = run_script("word_frequency", str(tmp_path / "nonexistent.md"))
        assert "file not found" in (r.stdout + r.stderr).lower()


class TestWordFrequencyJSON:
    """T26: valid JSON output."""

    def test_simple_text_produces_valid_json(self, run_script, simple_md):
        """T26: simple text produces valid JSON."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert isinstance(data, dict)


class TestWordFrequencyTopWords:
    """T27-T28: top words and total counts."""

    def test_top_words_populated(self, run_script, simple_md):
        """T27: has top words."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert len(data["top_words"]) > 0

    def test_total_words_counted(self, run_script, simple_md):
        """T28: total_words > 0."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert data["total_words"] > 0


class TestWordFrequencyAIPatterns:
    """T29-T31: AI pattern detection."""

    def test_ai_patterns_detected_in_slop(self, run_script, ai_slop_md):
        """T29: AI flags > 0 in AI-slop text."""
        r = run_script("word_frequency", ai_slop_md)
        data = json.loads(r.stdout)
        assert len(data["ai_patterns"]["flagged_words"]) > 0

    def test_ai_risk_high_for_slop(self, run_script, ai_slop_md):
        """T30: AI risk = high for slop text."""
        r = run_script("word_frequency", ai_slop_md)
        data = json.loads(r.stdout)
        assert data["ai_patterns"]["risk_level"] == "high"

    def test_no_ai_patterns_in_simple(self, run_script, simple_md):
        """T31: no AI patterns in simple text."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert data["ai_patterns"]["risk_level"] == "none"


class TestWordFrequencyOverused:
    """T32-T33: overused word detection."""

    def test_overused_words_detected(self, run_script, overused_md):
        """T32: overused words found."""
        r = run_script("word_frequency", overused_md)
        data = json.loads(r.stdout)
        assert len(data["overused_words"]) > 0

    def test_top_overused_word_is_performance(self, run_script, overused_md):
        """T33: top overused word is 'performance'."""
        r = run_script("word_frequency", overused_md)
        data = json.loads(r.stdout)
        assert data["overused_words"][0]["word"] == "performance"


class TestWordFrequencyCodeExclusion:
    """T34: code blocks excluded from frequency analysis."""

    def test_code_tokens_not_in_top_words(self, run_script, with_code_md):
        """T34: code 'console' not in top words."""
        r = run_script("word_frequency", with_code_md)
        data = json.loads(r.stdout)
        all_words = " ".join(w["word"] for w in data["top_words"])
        assert "console" not in all_words


class TestWordFrequencyTopN:
    """T35: custom top_n parameter."""

    def test_custom_top_n_respected(self, run_script, simple_md):
        """T35: top_n=3 returns <= 3 words."""
        r = run_script("word_frequency", simple_md, "3")
        data = json.loads(r.stdout)
        assert len(data["top_words"]) <= 3


class TestWordFrequencyJargon:
    """T36-T37: jargon detection."""

    def test_jargon_detected(self, run_script, jargon_md):
        """T36: jargon count > 0."""
        r = run_script("word_frequency", jargon_md)
        data = json.loads(r.stdout)
        assert data["jargon"]["count"] > 0

    def test_jargon_density_percentage_present(self, run_script, jargon_md):
        """T37: jargon density_percentage present."""
        r = run_script("word_frequency", jargon_md)
        assert "density_percentage" in r.stdout


class TestWordFrequencyMetrics:
    """T38-T41: type-token ratio, file name, content words, unique words."""

    def test_type_token_ratio_reasonable(self, run_script, simple_md):
        """T38: TTR > 0 and <= 1."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert data["type_token_ratio"] > 0
        assert data["type_token_ratio"] < 1.01

    def test_file_name_in_output(self, run_script, simple_md):
        """T39: file name in output."""
        r = run_script("word_frequency", simple_md)
        assert "simple.md" in r.stdout

    def test_content_words_less_than_total(self, run_script, simple_md):
        """T40: content_words < total_words (stop words filtered)."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert data["content_words"] < data["total_words"]

    def test_unique_words_positive(self, run_script, simple_md):
        """T41: unique_words > 0."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert data["unique_words"] > 0


class TestWordFrequencyDelve:
    """T42: delve flagged as high severity."""

    def test_delve_high_severity(self, run_script, ai_slop_md):
        """T42: delve is high severity."""
        r = run_script("word_frequency", ai_slop_md)
        data = json.loads(r.stdout)
        delve_severity = None
        for f in data["ai_patterns"]["flagged_words"]:
            if f["word"] == "delve":
                delve_severity = f["severity"]
                break
        assert delve_severity == "high"


class TestWordFrequencyFrontmatter:
    """T43: frontmatter stripped from word frequency."""

    def test_frontmatter_key_not_in_top_words(self, run_script, frontmatter_md):
        """T43: frontmatter key 'author' not in top words."""
        r = run_script("word_frequency", frontmatter_md)
        data = json.loads(r.stdout)
        all_words = " ".join(w["word"] for w in data["top_words"])
        assert "author" not in all_words


class TestWordFrequencyPercentage:
    """T44: each top word has percentage field."""

    def test_all_top_words_have_percentage(self, run_script, simple_md):
        """T44: all top words have percentage."""
        r = run_script("word_frequency", simple_md)
        data = json.loads(r.stdout)
        assert all("percentage" in w for w in data["top_words"])


# ── Integration / edge case tests ───────────────────────────────────────


class TestReadabilityEdgeCases:
    """T45, T47: edge cases for readability_score."""

    def test_minimal_text_does_not_crash(self, run_script, minimal_md):
        """T45: minimal text has metrics."""
        r = run_script("readability_score", minimal_md)
        assert "metrics" in (r.stdout + r.stderr)

    def test_avg_sentence_length_reasonable(self, run_script, simple_md):
        """T47: avg_sentence_length between 2 and 30."""
        r = run_script("readability_score", simple_md)
        data = json.loads(r.stdout)
        avg = data["metrics"]["avg_sentence_length"]
        assert avg > 2
        assert avg < 30


class TestWordFrequencyEdgeCases:
    """T46, T48: edge cases for word_frequency."""

    def test_minimal_text_does_not_crash(self, run_script, minimal_md):
        """T46: minimal text has total_words."""
        r = run_script("word_frequency", minimal_md)
        assert "total_words" in (r.stdout + r.stderr)

    def test_overused_word_percentage_gt_2(self, run_script, overused_md):
        """T48: overused word percentage > 2."""
        r = run_script("word_frequency", overused_md)
        data = json.loads(r.stdout)
        assert data["overused_words"][0]["percentage"] > 2.0
