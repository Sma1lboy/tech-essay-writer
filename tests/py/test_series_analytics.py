"""Tests for series_manager.py, analytics_feedback.py, and orchestrator/pipeline integration."""

import json
import os

import pytest


# ============================================================
# Helpers
# ============================================================


def read_json(path):
    """Read and parse a JSON file."""
    with open(path) as f:
        return json.load(f)


def series_file(fake_home):
    """Return the path to series.json."""
    return os.path.join(fake_home, ".tech-essay-writer", "series.json")


def analytics_file(fake_home):
    """Return the path to analytics.json."""
    return os.path.join(fake_home, ".tech-essay-writer", "analytics.json")


def taste_file(fake_home):
    """Return the path to taste-memory.json."""
    return os.path.join(fake_home, ".tech-essay-writer", "taste-memory.json")


def setup_project(tmp_path, name):
    """Create a temp project dir with .essay-state/ and return its path."""
    proj = tmp_path / name
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".essay-state").mkdir(exist_ok=True)
    return str(proj)


def write_json_file(path, data):
    """Write JSON to a file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def write_state_json(proj, filename, data):
    """Write a JSON file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        json.dump(data, f)


def write_state_file(proj, filename, content):
    """Write a text file into .essay-state/."""
    path = os.path.join(proj, ".essay-state", filename)
    with open(path, "w") as f:
        f.write(content)


# ============================================================
# series_manager.py tests
# ============================================================


class TestSeriesCreate:
    """Tests 1-3: Create a series, verify file and JSON structure."""

    def test_create_returns_success(self, run_script, fake_home):
        r = run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        assert "Created series" in r.stdout

    def test_series_file_created(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        assert os.path.isfile(series_file(fake_home))

    def test_series_name_stored(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        assert data["series"][0]["name"] == "Building a Compiler"

    def test_series_description_stored(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        assert data["series"][0]["description"] == "A 5-part series on compilers"

    def test_series_articles_empty(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        assert data["series"][0]["articles"] == []

    def test_series_id_has_prefix(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        assert data["series"][0]["id"].startswith("ser-")


class TestSeriesAddArticles:
    """Tests 4-5: Add articles and verify ordering."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        self.run("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]

    def test_add_returns_success(self):
        r = self.run("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        assert "Added" in r.stdout

    def test_article_positions_sequential(self):
        self.run("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        self.run("series_manager", "add", self.series_id, "art-101", "Part 2: Parsing")
        self.run("series_manager", "add", self.series_id, "art-102", "Part 3: AST")
        data = read_json(series_file(self.home))
        arts = data["series"][0]["articles"]
        pos_map = {a["article_id"]: a["position"] for a in arts}
        assert pos_map["art-100"] == 1
        assert pos_map["art-101"] == 2
        assert pos_map["art-102"] == 3


class TestSeriesList:
    """Test 6: List series."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        run_script("series_manager", "add", sid, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", sid, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", sid, "art-102", "Part 3: AST")

    def test_list_shows_name(self):
        r = self.run("series_manager", "list")
        assert "Building a Compiler" in r.stdout

    def test_list_shows_article_count(self):
        r = self.run("series_manager", "list")
        assert "3 articles" in r.stdout


class TestSeriesShow:
    """Test 7: Show series details."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", self.series_id, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", self.series_id, "art-102", "Part 3: AST")

    def test_show_displays_name(self):
        r = self.run("series_manager", "show", self.series_id)
        assert "Building a Compiler" in r.stdout

    def test_show_displays_article(self):
        r = self.run("series_manager", "show", self.series_id)
        assert "Part 1: Lexing" in r.stdout

    def test_show_displays_article_count(self):
        r = self.run("series_manager", "show", self.series_id)
        assert "Articles (3)" in r.stdout


class TestSeriesContext:
    """Test 8: Context output for prompt injection."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")

    def test_context_has_series_name(self):
        r = self.run("series_manager", "context", self.series_id)
        assert "series_name" in r.stdout

    def test_context_has_articles_array(self):
        r = self.run("series_manager", "context", self.series_id)
        assert "articles" in r.stdout

    def test_context_is_valid_json(self):
        r = self.run("series_manager", "context", self.series_id)
        # Should not raise
        json.loads(r.stdout)


class TestSeriesSetArc:
    """Test 9: Set narrative arc."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]

    def test_set_arc_returns_success(self):
        r = self.run("series_manager", "set-arc", self.series_id, "From lexer to codegen, building complexity")
        assert "Set arc" in r.stdout

    def test_arc_description_stored(self):
        self.run("series_manager", "set-arc", self.series_id, "From lexer to codegen, building complexity")
        data = read_json(series_file(self.home))
        assert data["series"][0]["narrative_arc"] == "From lexer to codegen, building complexity"


class TestSeriesSetSummary:
    """Test 10: Set article summary within series."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")

    def test_set_summary_returns_success(self):
        r = self.run("series_manager", "set-summary", self.series_id, "art-100",
                      "We built a tokenizer that handles Unicode")
        assert "Set summary" in r.stdout

    def test_summary_stored(self):
        self.run("series_manager", "set-summary", self.series_id, "art-100",
                  "We built a tokenizer that handles Unicode")
        data = read_json(series_file(self.home))
        arts = data["series"][0]["articles"]
        summary = next(a["summary"] for a in arts if a["article_id"] == "art-100")
        assert summary == "We built a tokenizer that handles Unicode"


class TestSeriesNextPosition:
    """Test 11: Next position returns correct number."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", self.series_id, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", self.series_id, "art-102", "Part 3: AST")

    def test_next_position_is_4(self):
        r = self.run("series_manager", "next-position", self.series_id)
        assert r.stdout.strip() == "4"


class TestSeriesSearch:
    """Tests 12-13, 18: Search by name, description, and no results."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")

    def test_search_by_name(self):
        r = self.run("series_manager", "search", "compiler")
        assert "Building a Compiler" in r.stdout

    def test_search_by_description(self):
        r = self.run("series_manager", "search", "5-part")
        assert "Building a Compiler" in r.stdout

    def test_search_no_results(self):
        r = self.run("series_manager", "search", "nonexistent-xyz-topic")
        assert "No matching" in r.stdout


class TestSeriesReorder:
    """Test 14: Reorder article within series."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", self.series_id, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", self.series_id, "art-102", "Part 3: AST")

    def test_reorder_moves_to_position_1(self):
        self.run("series_manager", "reorder", self.series_id, "art-102", "1")
        data = read_json(series_file(self.home))
        arts = data["series"][0]["articles"]
        pos = next(a["position"] for a in arts if a["article_id"] == "art-102")
        assert pos == 1


class TestSeriesAddExplicitPosition:
    """Test 15: Add article with explicit position."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        self.series_id = data["series"][0]["id"]
        run_script("series_manager", "add", self.series_id, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", self.series_id, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", self.series_id, "art-102", "Part 3: AST")

    def test_explicit_position_respected(self):
        self.run("series_manager", "add", self.series_id, "art-103", "Interlude: Theory", "2")
        data = read_json(series_file(self.home))
        arts = data["series"][0]["articles"]
        pos = next(a["position"] for a in arts if a["article_id"] == "art-103")
        assert pos == 2


class TestSeriesDuplicateNames:
    """Test 16: Duplicate series names allowed."""

    def test_duplicate_name_allowed(self, run_script, fake_home):
        r1 = run_script("series_manager", "create", "Building a Compiler", "First description")
        assert "Created series" in r1.stdout
        r2 = run_script("series_manager", "create", "Building a Compiler", "Different description")
        assert "Created series" in r2.stdout

    def test_two_series_exist(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "First description")
        run_script("series_manager", "create", "Building a Compiler", "Different description")
        data = read_json(series_file(fake_home))
        assert len(data["series"]) == 2


class TestSeriesEmptyHandling:
    """Test 17: Empty series handling."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        self.home = fake_home
        run_script("series_manager", "create", "Building a Compiler", "First")
        run_script("series_manager", "create", "Empty Series", "Nothing here")
        data = read_json(series_file(fake_home))
        self.series_id2 = data["series"][1]["id"]

    def test_show_empty_series(self):
        r = self.run("series_manager", "show", self.series_id2)
        assert "Articles (0)" in r.stdout

    def test_next_position_for_empty_is_1(self):
        r = self.run("series_manager", "next-position", self.series_id2)
        assert r.stdout.strip() == "1"


class TestSeriesContextIncludesArc:
    """Test 19: Context includes narrative_arc."""

    def test_context_includes_narrative_arc(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        run_script("series_manager", "set-arc", sid, "From lexer to codegen, building complexity")
        r = run_script("series_manager", "context", sid)
        assert "narrative_arc" in r.stdout


class TestSeriesSetSummaryNonexistent:
    """Test 20: set-summary for nonexistent article fails."""

    def test_set_summary_nonexistent_article_fails(self, run_script, fake_home):
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        r = run_script("series_manager", "set-summary", sid, "art-999", "some summary")
        assert r.returncode != 0


# ============================================================
# analytics_feedback.py tests
# ============================================================


class TestAnalyticsRecord:
    """Tests 21-22: Record a single metric and verify structure."""

    def test_record_returns_success(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record", "art-200", "views", "1500")
        assert "Recorded" in r.stdout

    def test_analytics_file_created(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        assert os.path.isfile(analytics_file(fake_home))

    def test_metric_value_stored(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        data = read_json(analytics_file(fake_home))
        assert data["articles"]["art-200"]["metrics"]["views"] == 1500


class TestAnalyticsRecordBatch:
    """Test 23: Record-batch multiple metrics."""

    def test_record_batch_returns_success(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record-batch", "art-201",
                        '{"views":800,"shares":30,"comments":5}')
        assert "Recorded 3 metrics" in r.stdout

    def test_batch_views_stored(self, run_script, fake_home):
        run_script("analytics_feedback", "record-batch", "art-201",
                    '{"views":800,"shares":30,"comments":5}')
        data = read_json(analytics_file(fake_home))
        assert data["articles"]["art-201"]["metrics"]["views"] == 800

    def test_batch_shares_stored(self, run_script, fake_home):
        run_script("analytics_feedback", "record-batch", "art-201",
                    '{"views":800,"shares":30,"comments":5}')
        data = read_json(analytics_file(fake_home))
        assert data["articles"]["art-201"]["metrics"]["shares"] == 30


class TestAnalyticsQuery:
    """Test 24: Query article metrics."""

    def test_query_shows_views_value(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        r = run_script("analytics_feedback", "query", "art-200")
        assert "1500" in r.stdout

    def test_query_shows_metric_name(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        r = run_script("analytics_feedback", "query", "art-200")
        assert "views" in r.stdout


class TestAnalyticsTop:
    """Tests 25-26: Top articles by metric."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        run_script("analytics_feedback", "record", "art-200", "shares", "45")
        run_script("analytics_feedback", "record-batch", "art-201",
                    '{"views":800,"shares":30,"comments":5}')

    def test_top_by_views_shows_art_200(self):
        r = self.run("analytics_feedback", "top", "views", "5")
        assert "art-200" in r.stdout

    def test_top_by_shares_shows_art_200(self):
        r = self.run("analytics_feedback", "top", "shares", "5")
        assert "art-200" in r.stdout


class TestAnalyticsRecordUpdate:
    """Test 27: Record updates existing metric (overwrites)."""

    def test_metric_updated_to_new_value(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-200", "views", "1500")
        run_script("analytics_feedback", "record", "art-200", "views", "2000")
        data = read_json(analytics_file(fake_home))
        assert data["articles"]["art-200"]["metrics"]["views"] == 2000


class TestAnalyticsTrends:
    """Test 28: Trends with data."""

    def test_trends_output_exists(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-202", "views", "500")
        run_script("analytics_feedback", "record", "art-203", "views", "3000")
        r = run_script("analytics_feedback", "trends")
        assert "trends" in r.stdout.lower() or r.returncode == 0


class TestAnalyticsFeedTaste:
    """Tests 29-31: Feed-taste writes performance_insights to taste memory."""

    def test_feed_taste_returns_success(self, run_script, fake_home, tmp_path):
        # Set up analytics data
        run_script("analytics_feedback", "record", "art-400", "views", "1000")
        run_script("analytics_feedback", "record", "art-400", "shares", "50")
        # Set up taste memory
        write_json_file(taste_file(fake_home), {})
        r = run_script("analytics_feedback", "feed-taste", str(tmp_path))
        assert "Performance insights updated" in r.stdout

    def test_taste_has_performance_insights(self, run_script, fake_home, tmp_path):
        run_script("analytics_feedback", "record", "art-400", "views", "1000")
        run_script("analytics_feedback", "record", "art-400", "shares", "50")
        write_json_file(taste_file(fake_home), {})
        run_script("analytics_feedback", "feed-taste", str(tmp_path))
        data = read_json(taste_file(fake_home))
        assert "performance_insights" in data

    def test_best_performing_tags_is_list(self, run_script, fake_home, tmp_path):
        run_script("analytics_feedback", "record", "art-400", "views", "1000")
        run_script("analytics_feedback", "record", "art-400", "shares", "50")
        write_json_file(taste_file(fake_home), {})
        run_script("analytics_feedback", "feed-taste", str(tmp_path))
        data = read_json(taste_file(fake_home))
        assert isinstance(data["performance_insights"]["best_performing_tags"], list)

    def test_avg_views_is_numeric(self, run_script, fake_home, tmp_path):
        run_script("analytics_feedback", "record", "art-400", "views", "1000")
        run_script("analytics_feedback", "record", "art-400", "shares", "50")
        write_json_file(taste_file(fake_home), {})
        run_script("analytics_feedback", "feed-taste", str(tmp_path))
        data = read_json(taste_file(fake_home))
        assert isinstance(data["performance_insights"]["avg_views"], (int, float))

    def test_feed_taste_no_data_handled(self, run_script, fake_home, tmp_path):
        # No analytics data at all
        af = analytics_file(fake_home)
        if os.path.isfile(af):
            os.remove(af)
        write_json_file(taste_file(fake_home), {})
        r = run_script("analytics_feedback", "feed-taste", str(tmp_path))
        assert "No analytics data" in r.stdout


class TestAnalyticsSummary:
    """Test 32: Summary output formatting."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("analytics_feedback", "record", "art-300", "views", "1000")
        run_script("analytics_feedback", "record", "art-300", "shares", "50")
        run_script("analytics_feedback", "record", "art-301", "views", "500")
        run_script("analytics_feedback", "record", "art-301", "shares", "20")

    def test_summary_shows_article_count(self):
        r = self.run("analytics_feedback", "summary")
        assert "2 articles" in r.stdout

    def test_summary_shows_views_metric(self):
        r = self.run("analytics_feedback", "summary")
        assert "views" in r.stdout


class TestAnalyticsCompare:
    """Tests 33-34: Compare two articles."""

    @pytest.fixture(autouse=True)
    def _setup(self, run_script, fake_home):
        self.run = run_script
        run_script("analytics_feedback", "record", "art-300", "views", "1000")
        run_script("analytics_feedback", "record", "art-300", "shares", "50")
        run_script("analytics_feedback", "record", "art-301", "views", "500")
        run_script("analytics_feedback", "record", "art-301", "shares", "20")

    def test_compare_shows_both_ids(self):
        r = self.run("analytics_feedback", "compare", "art-300", "art-301")
        assert "art-300" in r.stdout

    def test_compare_shows_metric_names(self):
        r = self.run("analytics_feedback", "compare", "art-300", "art-301")
        assert "views" in r.stdout

    def test_compare_missing_article_handled(self):
        r = self.run("analytics_feedback", "compare", "art-300", "art-999")
        assert "No data" in r.stdout


class TestAnalyticsInvalidMetric:
    """Test 35: Record invalid metric name rejected."""

    def test_invalid_metric_rejected(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record", "art-300", "invalid_metric", "100")
        assert r.returncode != 0


class TestAnalyticsValidMetrics:
    """Test 36: All 7 valid metrics accepted."""

    @pytest.mark.parametrize("metric", [
        "views", "shares", "comments", "likes", "bookmarks", "read_time_avg", "bounce_rate",
    ])
    def test_valid_metric_accepted(self, run_script, fake_home, metric):
        r = run_script("analytics_feedback", "record", "art-valid", metric, "1")
        assert r.returncode == 0


class TestAnalyticsTopCustomN:
    """Test 37: Top with custom N."""

    def test_top_with_n_2(self, run_script, fake_home):
        run_script("analytics_feedback", "record", "art-t1", "views", "100")
        run_script("analytics_feedback", "record", "art-t2", "views", "200")
        run_script("analytics_feedback", "record", "art-t3", "views", "300")
        r = run_script("analytics_feedback", "top", "views", "2")
        assert "Top 2" in r.stdout


class TestAnalyticsFileInit:
    """Test 38: Analytics file auto-creation on summary."""

    def test_summary_works_on_fresh_init(self, run_script, fake_home):
        # Ensure no analytics file
        af = analytics_file(fake_home)
        if os.path.isfile(af):
            os.remove(af)
        r = run_script("analytics_feedback", "summary")
        assert "No analytics data" in r.stdout

    def test_analytics_file_auto_created(self, run_script, fake_home):
        af = analytics_file(fake_home)
        if os.path.isfile(af):
            os.remove(af)
        run_script("analytics_feedback", "summary")
        assert os.path.isfile(af)


class TestAnalyticsBatchValidation:
    """Tests 39-40: Record-batch validation."""

    def test_record_batch_rejects_invalid_metric(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record-batch", "art-300", '{"bad_metric":100}')
        assert r.returncode != 0

    def test_record_batch_rejects_invalid_json(self, run_script, fake_home):
        r = run_script("analytics_feedback", "record-batch", "art-300", "not json")
        assert r.returncode != 0


# ============================================================
# Integration tests (pipeline-state + orchestrate + series/analytics)
# ============================================================


class TestPipelineInitWithSeries:
    """Tests 41-42: Pipeline init with/without --series flag."""

    def test_init_with_series_stores_id(self, run_script, fake_home, tmp_path):
        # Create a series first
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]

        proj = setup_project(tmp_path, "int-project")
        r = run_script("pipeline_state", "init", proj, "Compiler Part 1", "--series", sid)
        assert "initialized" in r.stdout
        state = read_json(os.path.join(proj, ".essay-state", "pipeline-state.json"))
        assert state["series_id"] == sid

    def test_init_without_series_has_no_series_id(self, run_script, fake_home, tmp_path):
        proj = setup_project(tmp_path, "int-project2")
        run_script("pipeline_state", "init", proj, "Standalone Article")
        state = read_json(os.path.join(proj, ".essay-state", "pipeline-state.json"))
        assert "series_id" not in state


class TestOrchestrateSeriesContext:
    """Tests 43-44: Orchestrator build-series-context."""

    def test_build_series_context_with_series(self, run_script, fake_home, tmp_path, script_dir):
        # Create series with articles
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        run_script("series_manager", "add", sid, "art-100", "Part 1: Lexing")
        run_script("series_manager", "add", sid, "art-101", "Part 2: Parsing")
        run_script("series_manager", "add", sid, "art-102", "Part 3: AST")

        proj = setup_project(tmp_path, "int-proj")
        run_script("pipeline_state", "init", proj, "Compiler Part 1", "--series", sid)
        r = run_script("orchestrate", proj, script_dir, "build-series-context")
        assert "Series Context" in r.stdout or "series" in r.stdout.lower()
        assert "Building a Compiler" in r.stdout

    def test_build_series_context_without_series(self, run_script, fake_home, tmp_path, script_dir):
        proj = setup_project(tmp_path, "int-proj2")
        run_script("pipeline_state", "init", proj, "Standalone Article")
        r = run_script("orchestrate", proj, script_dir, "build-series-context")
        assert "no series" in r.stdout.lower()


class TestOrchestrateAnalyticsInsights:
    """Test 45: Orchestrator build-analytics-insights."""

    def test_build_analytics_insights(self, run_script, fake_home, tmp_path, script_dir):
        # Set up analytics data and feed taste
        write_json_file(taste_file(fake_home), {})
        run_script("analytics_feedback", "record", "art-400", "views", "1000")
        run_script("analytics_feedback", "record", "art-400", "shares", "50")
        run_script("analytics_feedback", "feed-taste", str(tmp_path))

        proj = setup_project(tmp_path, "int-proj")
        run_script("pipeline_state", "init", proj, "Test Article")
        r = run_script("orchestrate", proj, script_dir, "build-analytics-insights")
        assert "Performance Insights" in r.stdout


class TestOrchestrateWriterPromptWithSeries:
    """Test 46: Series context appears in writer prompt when series_id set."""

    def test_writer_prompt_includes_series_context(self, run_script, fake_home, tmp_path, script_dir):
        # Create series
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        run_script("series_manager", "add", sid, "art-100", "Part 1: Lexing")

        proj = setup_project(tmp_path, "int-proj")
        run_script("pipeline_state", "init", proj, "Compiler Part 1", "--series", sid)
        # Create minimal outline
        write_state_json(proj, "outline-A.json", {"sections": []})
        run_script("pipeline_state", "set-field", proj, "outline_variant", "A")
        r = run_script("orchestrate", proj, script_dir, "build-writer-prompt", "A")
        assert "Series Context" in r.stdout


class TestOrchestrateFormatPromptWithSeries:
    """Test 47: Series nav appears in format prompts when series_id set."""

    def test_format_prompt_includes_series_navigation(self, run_script, fake_home, tmp_path, script_dir):
        # Create series
        run_script("series_manager", "create", "Building a Compiler", "A 5-part series on compilers")
        data = read_json(series_file(fake_home))
        sid = data["series"][0]["id"]
        run_script("series_manager", "add", sid, "art-100", "Part 1: Lexing")

        proj = setup_project(tmp_path, "int-proj")
        run_script("pipeline_state", "init", proj, "Compiler Part 1", "--series", sid)
        # Create minimal draft
        write_state_file(proj, "draft-v1.md", "# Test Draft")
        r = run_script("orchestrate", proj, script_dir, "build-format-prompts", "internal")
        assert "Series Navigation" in r.stdout
