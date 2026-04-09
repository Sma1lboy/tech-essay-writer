"""Tests for influence_score.py and seo_metadata.py."""

import json
import os

import pytest


# ============================================================
# Helpers
# ============================================================


def setup_project(tmp_path, name):
    """Create a temp project dir with .essay-state/ and return its path."""
    proj = tmp_path / name
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".essay-state").mkdir(exist_ok=True)
    return str(proj)


def write_json(proj, filename, data):
    """Write a JSON file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        json.dump(data, f)


def write_file(proj, filename, content):
    """Write a text file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        f.write(content)


def read_result_json(proj, filename):
    """Read a JSON file from .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path) as f:
        return json.load(f)


# ============================================================
# influence_score.py tests
# ============================================================


class TestInfluenceScoreEmptyState:
    """Test 1-2: Runs with empty state dir, produces valid JSON."""

    def test_runs_with_empty_state(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-empty")
        r = run_script("influence_score", proj)
        assert "influence_score" in r.stdout

    def test_creates_json_file(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-empty2")
        run_script("influence_score", proj)
        assert os.path.isfile(os.path.join(proj, ".essay-state", "influence-score.json"))

    def test_output_has_tier(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-empty3")
        r = run_script("influence_score", proj)
        assert "tier" in r.stdout

    def test_output_has_dimensions(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-empty4")
        r = run_script("influence_score", proj)
        assert "dimensions" in r.stdout


class TestInfluenceScoreDefaults:
    """Test 3: Default scores are mid-range (1-10)."""

    def test_default_score_gte_1(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-default")
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["influence_score"] >= 1

    def test_default_score_lte_10(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-default2")
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["influence_score"] <= 10


class TestInfluenceScoreNovelty:
    """Tests 4-5: Novelty scoring based on competitive landscape."""

    def test_blue_ocean_high_novelty(self, run_script, tmp_path, fake_home):
        """Test 4: Blue ocean topic (no competitors) + gap + unique angle => high novelty."""
        proj = setup_project(tmp_path, "inf-novelty")
        write_json(proj, "pipeline-state.json", {
            "topic": "Quantum ML Pipelines",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "competitive_landscape": {"existing_articles": []},
            "gap": "No articles cover quantum ML pipeline orchestration",
            "unique_angle": "First practical guide to quantum-classical hybrid pipelines",
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["topic_novelty"] >= 8

    def test_saturated_topic_low_novelty(self, run_script, tmp_path, fake_home):
        """Test 5: Saturated topic (15 competitors) => low novelty."""
        proj = setup_project(tmp_path, "inf-saturated")
        write_json(proj, "pipeline-state.json", {
            "topic": "React Hooks",
            "stage": "review",
            "language": "en",
        })
        articles = [{"title": f"Article {i}"} for i in range(15)]
        write_json(proj, "research-synthesis.json", {
            "competitive_landscape": {"existing_articles": articles},
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["topic_novelty"] <= 5


class TestInfluenceScoreSEO:
    """Tests 6-7: SEO review integration."""

    def test_optimized_seo_high_score(self, run_script, tmp_path, fake_home):
        """Test 6: OPTIMIZED rating with good keywords => high SEO score."""
        proj = setup_project(tmp_path, "inf-seo")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test SEO",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "review-seo.json", {
            "rating": "OPTIMIZED",
            "keywords": ["test", "seo", "optimization", "search"],
            "title_score": 8,
            "issues": [],
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["seo_potential"] >= 8

    def test_invisible_seo_low_score(self, run_script, tmp_path, fake_home):
        """Test 7: INVISIBLE rating with critical issues => low SEO score."""
        proj = setup_project(tmp_path, "inf-seo-bad")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test SEO",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "review-seo.json", {
            "rating": "INVISIBLE",
            "issues": [{"severity": "critical"}, {"severity": "critical"}],
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["seo_potential"] <= 3


class TestInfluenceScoreSocial:
    """Test 8: Social package integration."""

    def test_full_social_package_high_score(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-social")
        write_json(proj, "pipeline-state.json", {
            "topic": "Social Test",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "social-package.json", {
            "twitter_thread": "Thread about...",
            "linkedin_post": "Post...",
            "hn_title": "Show HN: Test",
            "reddit_post": "Check this out",
            "hashtags": ["#test", "#dev", "#coding"],
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["social_shareability"] >= 7


class TestInfluenceScoreAudience:
    """Tests 9-10: Audience review integration."""

    def test_would_share_broad_audience_high(self, run_script, tmp_path, fake_home):
        """Test 9: Both readers WOULD_SHARE + broad audience + high engagement => high score."""
        proj = setup_project(tmp_path, "inf-audience")
        write_json(proj, "pipeline-state.json", {
            "topic": "Audience Test",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "review-audience.json", {
            "reader_a": {"rating": "WOULD_SHARE"},
            "reader_b": {"rating": "WOULD_SHARE"},
            "target_audience": "all developers",
            "engagement_prediction": "high",
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["audience_reach"] >= 9

    def test_skip_meh_audience_low(self, run_script, tmp_path, fake_home):
        """Test 10: SKIP/MEH ratings => low audience score."""
        proj = setup_project(tmp_path, "inf-audience-bad")
        write_json(proj, "pipeline-state.json", {
            "topic": "Niche Test",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "review-audience.json", {
            "reader_a": {"rating": "SKIP"},
            "reader_b": {"rating": "MEH"},
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["audience_reach"] <= 5


class TestInfluenceScoreVerbose:
    """Test 11: Verbose output."""

    def test_verbose_shows_score(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-verbose")
        write_json(proj, "pipeline-state.json", {
            "topic": "Verbose Test",
            "stage": "review",
            "language": "en",
        })
        r = run_script("influence_score", proj, "verbose")
        assert "Influence Score:" in r.stdout

    def test_verbose_shows_tier(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-verbose2")
        write_json(proj, "pipeline-state.json", {
            "topic": "Verbose Test",
            "stage": "review",
            "language": "en",
        })
        r = run_script("influence_score", proj, "verbose")
        assert "Tier:" in r.stdout


class TestInfluenceScoreTier:
    """Test 12: Tier classification for high-scoring articles."""

    def test_high_scoring_has_influence_tier(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-tier-high")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "review",
            "language": "en",
        })
        write_json(proj, "research-synthesis.json", {
            "competitive_landscape": {"existing_articles": []},
            "gap": "Major gap in coverage",
            "unique_angle": "Revolutionary approach",
        })
        write_json(proj, "review-seo.json", {
            "rating": "OPTIMIZED",
            "keywords": ["a", "b", "c", "d"],
            "title_score": 9,
            "issues": [],
        })
        write_json(proj, "social-package.json", {
            "twitter_thread": "Great thread...",
            "linkedin_post": "Post",
            "hn_title": "Show HN: Amazing",
            "reddit_post": "Check out",
            "hashtags": ["#a", "#b", "#c"],
        })
        write_json(proj, "review-audience.json", {
            "reader_a": {"rating": "WOULD_SHARE"},
            "reader_b": {"rating": "WOULD_SHARE"},
            "target_audience": "all developers",
            "engagement_prediction": "high",
        })
        r = run_script("influence_score", proj)
        output = r.stdout
        assert "HIGH_INFLUENCE" in output or "MODERATE_INFLUENCE" in output


class TestInfluenceScoreWeightsAndDimensions:
    """Tests 13-14: Weights sum to 1.0 and all 5 dimensions present."""

    def test_weights_sum_to_one(self, run_script, tmp_path, fake_home):
        """Test 13: Weights sum to 1.0."""
        proj = setup_project(tmp_path, "inf-weights")
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        total = sum(data["weights"].values())
        assert abs(total - 1.0) < 0.001

    def test_five_dimensions_present(self, run_script, tmp_path, fake_home):
        """Test 14: All 5 dimensions present."""
        proj = setup_project(tmp_path, "inf-dims")
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert len(data["dimensions"]) == 5


class TestInfluenceScoreCorruptData:
    """Test 15: Corrupt review file handled gracefully."""

    def test_handles_corrupt_review_file(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-corrupt")
        write_json(proj, "pipeline-state.json", {
            "topic": "Corrupt Test",
            "stage": "review",
            "language": "en",
        })
        write_file(proj, "review-seo.json", "NOT JSON")
        r = run_script("influence_score", proj)
        assert "influence_score" in r.stdout


class TestInfluenceScoreAtomicWrite:
    """Test 34: No temp files left behind after atomic write."""

    def test_no_tmp_files_after_write(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-atomic")
        run_script("influence_score", proj)
        state_dir = os.path.join(proj, ".essay-state")
        tmp_files = [f for f in os.listdir(state_dir) if ".tmp." in f]
        assert len(tmp_files) == 0


class TestInfluenceScoreNoExpertise:
    """Test 39: Expertise defaults when no expertise graph exists."""

    def test_expertise_defaults_for_unknown_topic(self, run_script, tmp_path, fake_home):
        proj = setup_project(tmp_path, "inf-no-expertise")
        write_json(proj, "pipeline-state.json", {
            "topic": "Unknown Area",
            "stage": "review",
            "language": "en",
        })
        run_script("influence_score", proj)
        data = read_result_json(proj, "influence-score.json")
        assert data["dimensions"]["expertise_match"] == 3.0


# ============================================================
# seo_metadata.py tests
# ============================================================


class TestSEOMetadataEmptyState:
    """Test 16: Runs with empty state dir."""

    def test_runs_with_empty_state(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-empty")
        r = run_script("seo_metadata", proj)
        assert "opengraph_tags" in r.stdout

    def test_creates_json_file(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-empty2")
        run_script("seo_metadata", proj)
        assert os.path.isfile(os.path.join(proj, ".essay-state", "seo-metadata.json"))


class TestSEOMetadataTitle:
    """Tests 17-18: Title extraction and description from article."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path):
        self.proj = setup_project(tmp_path, "seo-title")
        write_file(self.proj, "final-external.md", (
            "# Building Scalable Microservices with Go\n"
            "\n"
            "Microservices architecture has evolved significantly in recent years.\n"
            "This article explores best practices for building scalable Go services.\n"
            "\n"
            "## Introduction\n"
            "\n"
            "Go is an excellent choice for microservices because of its concurrency model.\n"
        ))
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Go Microservices",
            "stage": "complete",
            "language": "en",
        })
        self.result = run_script("seo_metadata", self.proj)
        self.data = read_result_json(self.proj, "seo-metadata.json")

    def test_title_extracted_from_heading(self):
        """Test 17: Title extracted from first H1."""
        assert self.data["title"] == "Building Scalable Microservices with Go"

    def test_description_from_paragraph(self):
        """Test 18: Description from first paragraph."""
        assert "Microservices architecture" in self.result.stdout


class TestSEOMetadataOpenGraph:
    """Test 19: OpenGraph tags present."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path):
        self.proj = setup_project(tmp_path, "seo-og")
        write_file(self.proj, "final-external.md", (
            "# Building Scalable Microservices with Go\n"
            "\n"
            "Microservices architecture has evolved significantly.\n"
        ))
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Go Microservices",
            "stage": "complete",
            "language": "en",
        })
        self.result = run_script("seo_metadata", self.proj)

    def test_has_og_title(self):
        assert "og:title" in self.result.stdout

    def test_has_og_type(self):
        assert "og:type" in self.result.stdout

    def test_has_og_description(self):
        assert "og:description" in self.result.stdout


class TestSEOMetadataMetaTags:
    """Test 20: Meta tags present."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path):
        self.proj = setup_project(tmp_path, "seo-meta")
        write_file(self.proj, "final-external.md", (
            "# Test Article\n"
            "\n"
            "A paragraph about testing.\n"
        ))
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        self.result = run_script("seo_metadata", self.proj)

    def test_has_meta_description(self):
        assert '"description"' in self.result.stdout

    def test_has_meta_robots(self):
        assert "robots" in self.result.stdout


class TestSEOMetadataTwitterCard:
    """Test 21: Twitter card tags."""

    def test_twitter_card_present(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-twitter")
        write_file(proj, "final-external.md", (
            "# Twitter Test\n\nA paragraph.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        r = run_script("seo_metadata", proj)
        assert "twitter:card" in r.stdout

    def test_twitter_card_type(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-twitter2")
        write_file(proj, "final-external.md", (
            "# Twitter Test\n\nA paragraph.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["twitter_card"]["twitter:card"] == "summary_large_image"


class TestSEOMetadataStructuredData:
    """Test 22: JSON-LD structured data."""

    def test_jsonld_type_is_tech_article(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-jsonld")
        write_file(proj, "final-external.md", (
            "# JSON-LD Test\n\nA paragraph.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["structured_data"]["@type"] == "TechArticle"

    def test_jsonld_context_is_schema_org(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-jsonld2")
        write_file(proj, "final-external.md", (
            "# JSON-LD Test\n\nA paragraph.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["structured_data"]["@context"] == "https://schema.org"


class TestSEOMetadataKeywordDensity:
    """Test 23: Keyword density analysis has entries."""

    def test_keyword_density_has_entries(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-kd")
        write_file(proj, "final-external.md", (
            "# Building Scalable Microservices with Go\n"
            "\n"
            "Microservices architecture has evolved significantly in recent years.\n"
            "This article explores best practices for building scalable Go services.\n"
            "\n"
            "## Introduction\n"
            "\n"
            "Go is an excellent choice for microservices because of its concurrency model.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Go Microservices",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert len(data["keyword_density"]) > 0


class TestSEOMetadataWordCount:
    """Test 24: Word count calculated."""

    def test_word_count_positive(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-wc")
        write_file(proj, "final-external.md", (
            "# Building Scalable Microservices with Go\n"
            "\n"
            "Microservices architecture has evolved significantly in recent years.\n"
            "This article explores best practices for building scalable Go services.\n"
            "\n"
            "## Introduction\n"
            "\n"
            "Go is an excellent choice for microservices because of its concurrency model.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Go Microservices",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["total_words"] > 0


class TestSEOMetadataFallbackToDraft:
    """Test 25: Reads from draft when no final article exists."""

    def test_title_from_draft(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-draft")
        write_file(proj, "draft-v2.md", (
            "# Draft Article About Testing\n"
            "\n"
            "Testing is a fundamental practice in software engineering.\n"
            "This guide covers unit testing, integration testing, and end-to-end testing.\n"
            "\n"
            "## Unit Testing\n"
            "\n"
            "Unit tests verify individual functions work correctly.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Software Testing",
            "stage": "draft",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["title"] == "Draft Article About Testing"


class TestSEOMetadataKeywordsIntegration:
    """Test 26: SEO review keywords integrated."""

    def test_seo_keywords_in_meta(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-keywords")
        write_file(proj, "final-external.md", (
            "# Kubernetes Deployment Strategies\n"
            "\n"
            "Learn about blue-green deployments, canary releases, and rolling updates for Kubernetes.\n"
            "\n"
            "## Blue-Green Deployments\n"
            "\n"
            "Blue-green deployment is a technique for zero-downtime releases.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "Kubernetes",
            "stage": "complete",
            "language": "en",
        })
        write_json(proj, "review-seo.json", {
            "rating": "OPTIMIZED",
            "keywords": ["kubernetes", "deployment", "blue-green", "canary"],
        })
        r = run_script("seo_metadata", proj)
        assert "kubernetes" in r.stdout


class TestSEOMetadataChinese:
    """Test 27: Chinese language metadata."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path):
        self.proj = setup_project(tmp_path, "seo-chinese")
        write_file(self.proj, "final-external.md", (
            "# \u4f7f\u7528Go\u6784\u5efa\u5fae\u670d\u52a1\u67b6\u6784\n"
            "\n"
            "\u5fae\u670d\u52a1\u67b6\u6784\u5728\u8fd1\u5e74\u6765\u5f97\u5230\u4e86\u5feb\u901f\u53d1\u5c55\uff0c\u672c\u6587\u5c06\u63a2\u8ba8Go\u8bed\u8a00\u5728\u5fae\u670d\u52a1\u4e2d\u7684\u6700\u4f73\u5b9e\u8df5\u3002\n"
            "\n"
            "## \u7b80\u4ecb\n"
            "\n"
            "Go\u8bed\u8a00\u56e0\u5176\u51fa\u8272\u7684\u5e76\u53d1\u6a21\u578b\u800c\u6210\u4e3a\u5fae\u670d\u52a1\u7684\u7edd\u4f73\u9009\u62e9\u3002\n"
        ))
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Go\u5fae\u670d\u52a1",
            "stage": "complete",
            "language": "zh",
        })
        run_script("seo_metadata", self.proj)
        self.data = read_result_json(self.proj, "seo-metadata.json")

    def test_chinese_locale_in_og(self):
        assert self.data["opengraph_tags"]["og:locale"] == "zh_CN"

    def test_chinese_in_language_in_jsonld(self):
        assert self.data["structured_data"]["inLanguage"] == "zh-CN"


class TestSEOMetadataVerbose:
    """Test 28: Verbose output."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, tmp_path):
        self.proj = setup_project(tmp_path, "seo-verbose")
        write_file(self.proj, "final-external.md", (
            "# Verbose Test Article\n"
            "\n"
            "This is a test article for verbose output.\n"
        ))
        write_json(self.proj, "pipeline-state.json", {
            "topic": "Verbose",
            "stage": "complete",
            "language": "en",
        })
        self.result = run_script("seo_metadata", self.proj, "verbose")

    def test_verbose_shows_title(self):
        assert "SEO Metadata for:" in self.result.stdout

    def test_verbose_shows_word_count(self):
        assert "Word count:" in self.result.stdout


class TestSEOMetadataCanonicalURL:
    """Test 29: Canonical URL placeholder."""

    def test_canonical_url_is_template(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-canon")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
        })
        write_file(proj, "final-external.md", "# Test\n")
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["canonical_url"] == "{{CANONICAL_URL}}"


class TestSEOMetadataCodeBlockExclusion:
    """Test 30: Code blocks excluded from keyword density."""

    def test_code_block_content_excluded(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-codeblock")
        write_file(proj, "final-external.md", (
            "# Code Article\n"
            "\n"
            "This article discusses JavaScript patterns.\n"
            "\n"
            "```javascript\n"
            "function unusualFunctionNameXYZ() {\n"
            "  const unusualFunctionNameXYZ = true;\n"
            "  return unusualFunctionNameXYZ;\n"
            "}\n"
            "```\n"
            "\n"
            "JavaScript is great for web development.\n"
        ))
        write_json(proj, "pipeline-state.json", {
            "topic": "JavaScript",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        kd_keywords = [kd["keyword"] for kd in data["keyword_density"]]
        assert "unusualfunctionnamexyz" not in kd_keywords


class TestSEOMetadataFallbackDescription:
    """Test 31: Fallback description when no article exists."""

    def test_fallback_description_contains_topic(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-fallback")
        write_json(proj, "pipeline-state.json", {
            "topic": "Fallback Topic",
            "stage": "complete",
            "language": "en",
        })
        # No article file at all
        r = run_script("seo_metadata", proj)
        assert "Fallback Topic" in r.stdout


class TestSEOMetadataAuthor:
    """Test 32: Author from pipeline state."""

    def test_author_from_pipeline_state(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-author")
        write_file(proj, "final-external.md", "# Test\n")
        write_json(proj, "pipeline-state.json", {
            "topic": "Test",
            "stage": "complete",
            "language": "en",
            "author": "Jane Dev",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert data["meta_tags"]["author"] == "Jane Dev"


class TestSEOMetadataAtomicWrite:
    """Test 33: No partial/temp files left behind."""

    def test_no_tmp_files_after_write(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-atomic")
        write_file(proj, "final-external.md", "# Atomic Test\n")
        write_json(proj, "pipeline-state.json", {
            "topic": "Atomic",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        state_dir = os.path.join(proj, ".essay-state")
        tmp_files = [f for f in os.listdir(state_dir) if ".tmp." in f]
        assert len(tmp_files) == 0


class TestSEOMetadataHeadlineTruncation:
    """Test 35: Headline truncated to 110 chars in JSON-LD."""

    def test_headline_truncated_to_110(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-long-title")
        long_title = (
            "This Is An Extremely Long Title That Goes Way Beyond One Hundred "
            "And Ten Characters To Test The Truncation Logic In The Structured "
            "Data Schema Generation"
        )
        write_file(proj, "final-external.md", f"# {long_title}\n\nSome paragraph text here.\n")
        write_json(proj, "pipeline-state.json", {
            "topic": "Long Title",
            "stage": "complete",
            "language": "en",
        })
        run_script("seo_metadata", proj)
        data = read_result_json(proj, "seo-metadata.json")
        assert len(data["structured_data"]["headline"]) <= 110


class TestSEOMetadataCommaKeywords:
    """Test 40: Comma-separated keywords parsed correctly."""

    def test_comma_keywords_parsed(self, run_script, tmp_path):
        proj = setup_project(tmp_path, "seo-comma-kw")
        write_file(proj, "final-external.md", "# Comma Test\n")
        write_json(proj, "pipeline-state.json", {
            "topic": "Comma",
            "stage": "complete",
            "language": "en",
        })
        write_json(proj, "review-seo.json", {
            "rating": "OPTIMIZED",
            "keywords": "react, typescript, testing",
        })
        r = run_script("seo_metadata", proj)
        assert "react" in r.stdout


# ============================================================
# orchestrate.py integration tests
# ============================================================


class TestOrchestrateInfluenceScore:
    """Test 36: build-influence-score command dispatches."""

    def test_orchestrate_dispatches_influence(self, run_script, tmp_path, fake_home, script_dir):
        proj = setup_project(tmp_path, "orch-influence")
        r = run_script("orchestrate", proj, script_dir, "build-influence-score")
        # The orchestrator delegates to the script which outputs influence data
        combined = r.stdout + r.stderr
        assert "influence_score" in combined or r.returncode == 0


class TestOrchestrateSEOMetadata:
    """Test 37: build-seo-metadata command dispatches."""

    def test_orchestrate_dispatches_seo(self, run_script, tmp_path, fake_home, script_dir):
        proj = setup_project(tmp_path, "orch-seo")
        write_file(proj, "final-external.md", "# Orch Test\n")
        write_json(proj, "pipeline-state.json", {
            "topic": "Orchestrator SEO",
            "stage": "complete",
            "language": "en",
        })
        r = run_script("orchestrate", proj, script_dir, "build-seo-metadata")
        combined = r.stdout + r.stderr
        assert "opengraph_tags" in combined or r.returncode == 0


class TestOrchestrateUsage:
    """Test 38: Usage shows new commands."""

    def test_usage_shows_build_influence_score(self, run_script, tmp_path, script_dir):
        r = run_script("orchestrate", "x", "x", "invalid")
        combined = r.stdout + r.stderr
        assert "build-influence-score" in combined

    def test_usage_shows_build_seo_metadata(self, run_script, tmp_path, script_dir):
        r = run_script("orchestrate", "x", "x", "invalid")
        combined = r.stdout + r.stderr
        assert "build-seo-metadata" in combined
