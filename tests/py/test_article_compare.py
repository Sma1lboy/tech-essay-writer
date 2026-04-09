"""Tests for article_compare.py -- side-by-side draft comparison."""

import json
import os

import pytest


# ── Fixtures: markdown files ─────────────────────────────────────────

ARTICLE_V1 = """\
# My Tech Article

## Introduction

This is a simple article about technology. It covers important topics that many engineers care about. The goal is to help readers understand how things work.

## Architecture

The system uses a client-server architecture. The server handles all the business logic. The client sends requests over HTTP. We chose this approach for simplicity.

## Performance

Performance is good under normal load. We measured response times averaging 50ms. The system handles about 1000 requests per second. Memory usage stays below 512MB.

## Conclusion

In conclusion, this architecture works well for our use case. We recommend it for small to medium teams. Future work includes adding caching.
"""

ARTICLE_V2 = """\
# My Tech Article

## Introduction

This is a comprehensive article about modern system architecture. It covers critical topics that engineers at all levels need to understand. The goal is to provide actionable guidance for building reliable systems.

## Architecture

The system uses a client-server architecture with an event-driven messaging layer. The server handles business logic through a command pattern. The client communicates via gRPC for low-latency operations. We chose this approach after evaluating three alternatives.

### Event Bus

The event bus decouples producers from consumers. It uses Apache Kafka for durability and ordering guarantees.

```python
class EventBus:
    def publish(self, event):
        self.kafka.send(event.topic, event.serialize())
```

## Performance

Performance is excellent under both normal and peak load conditions. We measured response times averaging 12ms at P50 and 45ms at P99. The system handles about 5000 requests per second with horizontal scaling. Memory usage stays below 256MB per instance.

### Benchmarks

We ran benchmarks using wrk with 100 concurrent connections. Results showed linear scaling up to 8 instances.

## Security

All communication uses mutual TLS. Authentication is handled via JWT tokens with short expiry. We follow the principle of least privilege for all service accounts.

## Conclusion

In conclusion, this architecture works well for our use case and has proven itself in production for six months. We recommend it for teams of any size with proper observability in place. Future work includes adding a caching layer with Redis and implementing circuit breakers.
"""

DIFFERENT_ARTICLE = """\
# Database Selection Guide

## Why Databases Matter

Choosing the right database is one of the most impactful architectural decisions. The wrong choice creates years of technical debt.

## SQL vs NoSQL

SQL databases offer ACID guarantees. NoSQL databases offer horizontal scalability. The choice depends on your consistency requirements.

## Recommendation

Use PostgreSQL unless you have specific requirements that demand otherwise.
"""

EMPTY_ARTICLE = "\n"

MINIMAL_ARTICLE = """\
# Title

One sentence article.
"""

CODE_HEAVY_ARTICLE = """\
# Code Examples

## Setup

Install dependencies first.

```bash
npm install express
npm install cors
```

## Server Code

Here is the server:

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/health', (req, res) => {
  res.json({ healthy: true });
});

app.listen(3000);
```

## Client Code

Here is the client:

```javascript
const response = await fetch('http://localhost:3000');
const data = await response.json();
console.log(data);
```

## Summary

That is all.
"""

WITH_LINKS_ARTICLE = """\
# Article with Links

Read the [official docs](https://example.com/docs) for more info.
Also see [this guide](https://example.com/guide) and [the FAQ](https://example.com/faq).
"""


@pytest.fixture
def md_files(tmp_path):
    """Write all fixture markdown files and return a dict of paths."""
    files = {}
    content_map = {
        "article-v1.md": ARTICLE_V1,
        "article-v2.md": ARTICLE_V2,
        "article-v1-copy.md": ARTICLE_V1,
        "different.md": DIFFERENT_ARTICLE,
        "empty.md": EMPTY_ARTICLE,
        "minimal.md": MINIMAL_ARTICLE,
        "code-heavy.md": CODE_HEAVY_ARTICLE,
        "with-links.md": WITH_LINKS_ARTICLE,
    }
    for name, content in content_map.items():
        p = tmp_path / name
        p.write_text(content)
        files[name] = str(p)
    return files


# ── Usage and error handling ─────────────────────────────────────────


class TestUsageAndErrors:
    """Tests 1-3: argument validation and error messages."""

    def test_no_args_shows_usage(self, run_script):
        r = run_script("article_compare")
        combined = r.stdout + r.stderr
        assert "Usage" in combined

    def test_missing_file1_exits_with_error(self, run_script, md_files, tmp_path):
        r = run_script(
            "article_compare",
            str(tmp_path / "nonexistent.md"),
            md_files["article-v1.md"],
        )
        assert r.returncode == 1
        assert "not found" in (r.stdout + r.stderr).lower()

    def test_missing_file2_exits_with_error(self, run_script, md_files, tmp_path):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            str(tmp_path / "nonexistent.md"),
        )
        assert r.returncode == 1
        assert "not found" in (r.stdout + r.stderr).lower()


# ── Basic comparison (human-readable output) ─────────────────────────


class TestBasicComparison:
    """Tests 4-9: text-mode output sections and file names."""

    @pytest.fixture(autouse=True)
    def _compare(self, run_script, md_files):
        self.result = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--no-color",
        )

    def test_exits_successfully(self):
        assert self.result.returncode == 0

    def test_output_has_word_count(self):
        assert "WORD COUNT" in self.result.stdout

    def test_output_has_structure(self):
        assert "STRUCTURE" in self.result.stdout

    def test_output_has_reading_level(self):
        assert "READING LEVEL" in self.result.stdout

    def test_output_has_summary(self):
        assert "SUMMARY" in self.result.stdout

    def test_output_shows_file1_name(self):
        assert "article-v1.md" in self.result.stdout

    def test_output_shows_file2_name(self):
        assert "article-v2.md" in self.result.stdout


# ── JSON output ──────────────────────────────────────────────────────


class TestJSONOutput:
    """Tests 10-13: JSON validity, fields, and word counts."""

    @pytest.fixture(autouse=True)
    def _compare_json(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_json_output_is_valid(self):
        # If autouse fixture parsed it, it's valid JSON
        assert isinstance(self.data, dict)

    def test_json_has_file1(self):
        assert self.data["file1"] == "article-v1.md"

    def test_json_has_file2(self):
        assert self.data["file2"] == "article-v2.md"

    def test_file1_word_count_positive(self):
        assert self.data["metrics"]["file1"]["word_count"] > 0

    def test_file2_word_count_positive(self):
        assert self.data["metrics"]["file2"]["word_count"] > 0

    def test_v2_has_more_words_than_v1(self):
        v1 = self.data["metrics"]["file1"]["word_count"]
        v2 = self.data["metrics"]["file2"]["word_count"]
        assert v2 > v1


# ── Identical files ──────────────────────────────────────────────────


class TestIdenticalFiles:
    """Tests 14-15: identical files produce 100% similarity with no diffs."""

    @pytest.fixture(autouse=True)
    def _compare_identical(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v1-copy.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_identical_files_100_similarity(self):
        assert self.data["overall_similarity"] == 100.0

    def test_identical_files_no_improvements(self):
        assert len(self.data["improvements"]) == 0

    def test_identical_files_no_regressions(self):
        assert len(self.data["regressions"]) == 0


# ── Structure detection ──────────────────────────────────────────────


class TestStructureDetection:
    """Tests 16-18: added sections and heading counts."""

    @pytest.fixture(autouse=True)
    def _compare_structure(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_detects_added_security_section(self):
        added = [c for c in self.data["section_changes"] if c["type"] == "added"]
        headings = [c["heading"] for c in added]
        assert any("Security" in h for h in headings)

    def test_detects_added_subsections(self):
        added = [c for c in self.data["section_changes"] if c["type"] == "added"]
        headings = [c["heading"] for c in added]
        assert "Event Bus" in headings or "Benchmarks" in headings

    def test_v2_has_more_headings(self):
        h1 = len(self.data["headings"]["file1"])
        h2 = len(self.data["headings"]["file2"])
        assert h2 > h1


# ── Reading level ────────────────────────────────────────────────────


class TestReadingLevel:
    """Tests 19-20: Flesch-Kincaid metrics present and in range."""

    @pytest.fixture(autouse=True)
    def _compare_reading(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_file1_has_fk_grade(self):
        assert self.data["metrics"]["file1"]["flesch_kincaid_grade"] > 0

    def test_file2_has_fk_grade(self):
        assert self.data["metrics"]["file2"]["flesch_kincaid_grade"] > 0

    def test_file1_reading_ease_positive(self):
        assert self.data["metrics"]["file1"]["flesch_reading_ease"] > 0

    def test_file1_reading_ease_below_100(self):
        assert self.data["metrics"]["file1"]["flesch_reading_ease"] < 100


# ── Completely different files ───────────────────────────────────────


class TestDifferentFiles:
    """Tests 21-22: low similarity and section changes for different articles."""

    @pytest.fixture(autouse=True)
    def _compare_different(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["different.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_low_similarity(self):
        assert self.data["overall_similarity"] < 40

    def test_has_section_changes(self):
        assert len(self.data["section_changes"]) > 0


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests 23-26: empty, minimal, and code-heavy files."""

    def test_empty_vs_nonempty_produces_valid_json(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["empty.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_minimal_vs_full_produces_valid_json(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["minimal.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_code_heavy_file_has_high_code_density(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["code-heavy.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file2"]["code_density"] > 30

    def test_non_code_file_has_low_code_density(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["code-heavy.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file1"]["code_density"] < 5


# ── Improvements and regressions ─────────────────────────────────────


class TestImprovementsRegressions:
    """Tests 27-28: direction-dependent improvement/regression detection."""

    def test_v1_to_v2_has_improvements(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert len(data["improvements"]) > 0

    def test_v2_to_v1_has_regressions(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v2.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert len(data["regressions"]) > 0


# ── Section similarity ───────────────────────────────────────────────


class TestSectionSimilarity:
    """Tests 29-30: per-section similarity scores and edit types."""

    @pytest.fixture(autouse=True)
    def _compare_sections(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        self.data = json.loads(r.stdout)

    def test_shared_sections_have_similarity(self):
        shared = [c for c in self.data["section_changes"] if "similarity" in c]
        assert len(shared) > 0

    def test_introduction_section_was_edited(self):
        intro = [
            c for c in self.data["section_changes"] if c["heading"] == "Introduction"
        ]
        assert len(intro) > 0
        valid_types = ("significant_edit", "major_rewrite", "minor_edit")
        assert intro[0]["type"] in valid_types


# ── --no-color flag ──────────────────────────────────────────────────


class TestNoColorFlag:
    """Test 31: no ANSI escape codes in --no-color output."""

    def test_no_ansi_codes(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--no-color",
        )
        assert "\033" not in r.stdout


# ── Paragraph and sentence metrics ───────────────────────────────────


class TestParagraphSentenceMetrics:
    """Tests 32-34: sentence/paragraph counts and code block detection."""

    def test_v1_has_sentences(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file1"]["sentence_count"] > 3

    def test_v2_has_sentences(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file2"]["sentence_count"] > 3

    def test_v1_has_paragraphs(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file1"]["paragraph_count"] > 2

    def test_v2_has_paragraphs(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v2.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file2"]["paragraph_count"] > 2

    def test_code_heavy_has_code_blocks(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["code-heavy.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file1"]["code_block_count"] > 2


# ── Link detection ───────────────────────────────────────────────────


class TestLinkDetection:
    """Test 35: markdown link counting."""

    def test_with_links_has_3_links(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["with-links.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file1"]["link_count"] == 3

    def test_article_v1_has_0_links(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["with-links.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["metrics"]["file2"]["link_count"] == 0


# ── Self-comparison ──────────────────────────────────────────────────


class TestSelfComparison:
    """Test 36: a file compared to itself is 100% similar."""

    def test_self_comparison_100_similarity(self, run_script, md_files):
        r = run_script(
            "article_compare",
            md_files["article-v1.md"],
            md_files["article-v1.md"],
            "--json",
        )
        data = json.loads(r.stdout)
        assert data["overall_similarity"] == 100.0
