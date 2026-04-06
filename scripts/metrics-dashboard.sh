#!/usr/bin/env bash
# Comprehensive metrics dashboard for tech-essay-writer
# Displays pipeline health, quality trends, review panel stats,
# author growth, platform performance, and writing stats
# Usage: metrics-dashboard.sh [project_dir]
set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
STATE_DIR="$PROJECT_DIR/.essay-state"
GLOBAL_DIR="$HOME/.tech-essay-writer"

python3 - "$PROJECT_DIR" "$STATE_DIR" "$GLOBAL_DIR" << 'PYEOF'
import json, sys, os, glob, re, datetime, math, collections

project_dir = sys.argv[1]
state_dir = sys.argv[2]
global_dir = sys.argv[3]

WIDTH = 80

# ── Utility helpers ──────────────────────────────────────────────────────────

def load_json(path):
    """Load JSON file, return empty dict on failure."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def hr(ch="─"):
    """Horizontal rule."""
    return ch * WIDTH

def center(text, width=WIDTH):
    """Center text."""
    return text.center(width)

def bar_chart(value, max_val=10, width=30, filled="█", empty="░"):
    """ASCII bar chart."""
    if max_val <= 0:
        return empty * width
    ratio = min(value / max_val, 1.0)
    filled_len = int(ratio * width)
    return filled * filled_len + empty * (width - filled_len)

def spark_line(values, width=20):
    """ASCII sparkline from a list of numbers."""
    if not values:
        return ""
    sparks = "▁▂▃▄▅▆▇█"
    mn = min(values)
    mx = max(values)
    rng = mx - mn if mx != mn else 1
    # Resample if needed
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
    return "".join(sparks[min(len(sparks) - 1, int((v - mn) / rng * (len(sparks) - 1)))] for v in sampled)

def table_row(cols, widths):
    """Format a table row with fixed column widths."""
    parts = []
    for text, w in zip(cols, widths):
        s = str(text)[:w]
        parts.append(s.ljust(w))
    return "  ".join(parts)

def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def parse_iso_date(s):
    """Parse ISO date string to datetime, return None on failure."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None

# ── Load all data sources ────────────────────────────────────────────────────

pipeline_state = load_json(os.path.join(state_dir, "pipeline-state.json"))
quality_score = load_json(os.path.join(state_dir, "quality-score.json"))
review_summary = load_json(os.path.join(state_dir, "review-panel-summary.json"))
taste_memory = load_json(os.path.join(global_dir, "taste-memory.json"))
expertise_graph = load_json(os.path.join(global_dir, "expertise-graph.json"))
author_profile = load_json(os.path.join(global_dir, "author-profile.json"))
analytics_data = load_json(os.path.join(global_dir, "analytics.json"))
published_articles = load_json(os.path.join(global_dir, "published-articles.json"))

# Load all review files from state dir
reviews = {}
if os.path.isdir(state_dir):
    for rf in glob.glob(os.path.join(state_dir, "review-*.json")):
        basename = os.path.splitext(os.path.basename(rf))[0]
        if "panel-summary" in basename or "quality-score" in basename:
            continue
        reviews[basename] = load_json(rf)

# Load checkpoint data for stage timing
checkpoints = []
ckpt_dir = os.path.join(state_dir, "checkpoints")
if os.path.isdir(ckpt_dir):
    for name in sorted(os.listdir(ckpt_dir)):
        full = os.path.join(ckpt_dir, name)
        if os.path.isdir(full) and not name.startswith('.'):
            ps = load_json(os.path.join(full, "pipeline-state.json"))
            checkpoints.append({"name": name, "state": ps})

# ── Header ───────────────────────────────────────────────────────────────────

print(hr("═"))
print(center("TECH ESSAY WRITER — METRICS DASHBOARD"))
print(hr("═"))
print(f"  Project: {project_dir}")
print(f"  Date:    {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print(hr("─"))

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Pipeline Health
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(center("[ 1. PIPELINE HEALTH ]"))
print(hr("─"))

STAGE_ORDER = ["intake", "research", "outline", "draft", "review", "refinement", "polish", "complete"]

if pipeline_state:
    current_stage = pipeline_state.get("stage", "unknown")
    topic = pipeline_state.get("topic", "unknown")
    created = pipeline_state.get("created_at", "")
    updated = pipeline_state.get("updated_at", "")
    completed = pipeline_state.get("completed", False)
    refinement_round = pipeline_state.get("refinement_round", 0)
    max_rounds = pipeline_state.get("max_refinement_rounds", 3)

    # Pipeline visual
    stage_line = "  "
    for s in STAGE_ORDER:
        if s == current_stage:
            stage_line += f"[{s.upper()[:4]}]"
        elif STAGE_ORDER.index(s) < STAGE_ORDER.index(current_stage) if current_stage in STAGE_ORDER else False:
            stage_line += f" {s[:4].upper()} "
        else:
            stage_line += f" .... "
        if s != STAGE_ORDER[-1]:
            stage_line += ">"

    print(f"  Topic: {topic}")
    print(f"  Stage: {current_stage.upper()}" + (" (COMPLETE)" if completed else ""))
    print()
    print(stage_line)
    print()

    # Time in pipeline
    created_dt = parse_iso_date(created)
    updated_dt = parse_iso_date(updated)
    if created_dt and updated_dt:
        total_elapsed = (updated_dt - created_dt).total_seconds()
        print(f"  Total elapsed:       {format_duration(total_elapsed)}")

    if refinement_round > 0:
        print(f"  Refinement rounds:   {refinement_round}/{max_rounds}")

    # Stage timing from checkpoints
    if checkpoints:
        stage_times = {}
        prev_time = created_dt
        for ckpt in checkpoints:
            ckpt_state = ckpt["state"]
            ckpt_stage = ckpt_state.get("stage", "")
            ckpt_updated = parse_iso_date(ckpt_state.get("updated_at", ""))
            if ckpt_stage and ckpt_updated and prev_time:
                delta = (ckpt_updated - prev_time).total_seconds()
                if delta > 0:
                    stage_times[ckpt_stage] = stage_times.get(ckpt_stage, 0) + delta
                prev_time = ckpt_updated

        if stage_times:
            print()
            print("  Stage Timing:")
            bottleneck_stage = ""
            bottleneck_time = 0
            for s in STAGE_ORDER:
                if s in stage_times:
                    t = stage_times[s]
                    pct = (t / max(sum(stage_times.values()), 1)) * 100
                    bar = bar_chart(pct, 100, 20)
                    print(f"    {s:<12s} {bar} {format_duration(t):>6s} ({pct:.0f}%)")
                    if t > bottleneck_time:
                        bottleneck_time = t
                        bottleneck_stage = s

            if bottleneck_stage:
                print(f"\n  Bottleneck: {bottleneck_stage.upper()} ({format_duration(bottleneck_time)})")
else:
    print("  Pipeline not initialized for this project.")
    print("  Run: pipeline-state.sh init <project_dir> <topic>")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Quality Trends
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(hr("─"))
print(center("[ 2. QUALITY TRENDS ]"))
print(hr("─"))

topics_written = taste_memory.get("topics_written", [])

if len(topics_written) >= 2:
    # Track refinement rounds over time as a quality proxy
    rounds = [t.get("refinement_rounds", 0) for t in topics_written]
    dates = [t.get("date", "")[:10] for t in topics_written]

    print(f"  Articles in taste memory: {len(topics_written)}")
    print()

    # Refinement rounds trend (fewer rounds = improving)
    print("  Refinement Rounds Over Time (fewer = better):")
    print(f"    {spark_line(rounds, 40)}")
    if len(rounds) >= 2:
        first_half_avg = sum(rounds[:len(rounds)//2]) / max(len(rounds)//2, 1)
        second_half_avg = sum(rounds[len(rounds)//2:]) / max(len(rounds) - len(rounds)//2, 1)
        if first_half_avg > 0:
            change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            direction = "IMPROVING" if change_pct < -10 else ("DECLINING" if change_pct > 10 else "STABLE")
            print(f"    Early avg: {first_half_avg:.1f}  Recent avg: {second_half_avg:.1f}  Trend: {direction}")
        else:
            print(f"    Early avg: {first_half_avg:.1f}  Recent avg: {second_half_avg:.1f}")

    # Variant distribution
    variants = [t.get("variant") for t in topics_written if t.get("variant")]
    if variants:
        print()
        print("  Style Variant Distribution:")
        variant_counts = collections.Counter(variants)
        for v, count in variant_counts.most_common(5):
            pct = (count / len(variants)) * 100
            bar = bar_chart(count, max(variant_counts.values()), 20)
            print(f"    {str(v):<18s} {bar} {count:>3d} ({pct:.0f}%)")

    # Recent articles table
    print()
    print("  Recent Articles:")
    widths = [12, 35, 8, 8]
    print("  " + table_row(["Date", "Topic", "Variant", "Rounds"], widths))
    print("  " + table_row(["─"*12, "─"*35, "─"*8, "─"*8], widths))
    for t in topics_written[-5:]:
        print("  " + table_row([
            t.get("date", "?")[:10],
            t.get("topic", "?"),
            str(t.get("variant", "-"))[:8],
            str(t.get("refinement_rounds", "-"))
        ], widths))
elif len(topics_written) == 1:
    print(f"  Only 1 article in taste memory. Write more to see trends.")
    t = topics_written[0]
    print(f"    Topic: {t.get('topic', '?')} ({t.get('date', '?')[:10]})")
else:
    print("  No taste memory data. Complete articles to build quality trends.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Review Panel Stats
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(hr("─"))
print(center("[ 3. REVIEW PANEL STATS ]"))
print(hr("─"))

if reviews:
    # Rating to score mapping for averaging
    rating_scores = {
        "PASS": 9, "NEEDS_FIXES": 5, "REJECT": 2,
        "PUBLISH_READY": 9, "NEEDS_EDITING": 5, "REWRITE": 2,
        "SOLID": 9, "VULNERABLE": 5, "WEAK": 2,
        "WOULD_SHARE": 9, "MEH": 5, "SKIP": 2,
        "OPTIMIZED": 9, "NEEDS_WORK": 5, "INVISIBLE": 2,
        "CLEAR": 9, "NEEDS_CONTEXT": 5, "INACCESSIBLE": 2,
        "VERIFIED": 9, "NEEDS_VERIFICATION": 5, "UNRELIABLE": 2,
        "NATIVE": 9, "ACCEPTABLE": 6, "TRANSLATION_SMELL": 2,
    }

    # Per-reviewer stats
    print(f"  Reviews loaded: {len(reviews)}")
    print()

    widths_r = [18, 16, 6, 8, 30]
    print("  " + table_row(["Reviewer", "Rating", "Score", "Issues", "Bar"], widths_r))
    print("  " + table_row(["─"*18, "─"*16, "─"*6, "─"*8, "─"*30], widths_r))

    reviewer_scores = {}
    all_issues = []
    issue_categories = collections.Counter()

    for name, review in sorted(reviews.items()):
        rating = review.get("rating", "?")

        # Handle audience reviewer dual rating
        if "audience" in name:
            ra = review.get("reader_a", {}).get("rating", "MEH")
            rb = review.get("reader_b", {}).get("rating", "MEH")
            score = (rating_scores.get(ra, 5) + rating_scores.get(rb, 5)) / 2
            rating = f"{ra}/{rb}"
        else:
            score = rating_scores.get(rating, 5)

        issues = review.get("issues", [])
        issue_count = len(issues)

        # Collect issues for category analysis
        for issue in issues:
            all_issues.append(issue)
            severity = issue.get("severity", "minor")
            issue_categories[severity] += 1

        # Also collect code_issues and attacks
        for ci in review.get("code_issues", []):
            all_issues.append(ci)
            issue_categories["code"] += 1
        for atk in review.get("attacks", []):
            all_issues.append(atk)
            issue_categories[atk.get("severity", "major")] += 1

        reviewer_name = name.replace("review-", "")
        reviewer_scores[reviewer_name] = score
        bar = bar_chart(score, 10, 30)
        print("  " + table_row([reviewer_name, rating, f"{score:.1f}", str(issue_count), bar], widths_r))

    # Average score
    if reviewer_scores:
        avg = sum(reviewer_scores.values()) / len(reviewer_scores)
        print()
        print(f"  Average score: {avg:.1f}/10")

    # Reviewer agreement
    if len(reviewer_scores) >= 2:
        scores_list = list(reviewer_scores.values())
        mean = sum(scores_list) / len(scores_list)
        variance = sum((s - mean) ** 2 for s in scores_list) / len(scores_list)
        std_dev = math.sqrt(variance)
        agreement = "HIGH" if std_dev < 1.5 else ("MODERATE" if std_dev < 3.0 else "LOW")
        print(f"  Reviewer agreement: {agreement} (std dev: {std_dev:.1f})")

    # Most common issue severities
    if issue_categories:
        print()
        print("  Issue Breakdown:")
        for severity, count in issue_categories.most_common():
            bar = bar_chart(count, max(issue_categories.values()), 15)
            print(f"    {severity:<12s} {bar} {count}")

    # Top issues by frequency
    issue_texts = collections.Counter()
    for issue in all_issues:
        text = issue.get("issue", issue.get("attack", issue.get("target", "")))
        if text:
            # Truncate for grouping
            key = str(text)[:60]
            issue_texts[key] += 1

    if issue_texts and len(issue_texts) > 1:
        print()
        print("  Most Common Issues:")
        for text, count in issue_texts.most_common(5):
            print(f"    [{count}x] {text}")

    # Quality score summary if available
    if quality_score:
        composite = quality_score.get("composite_score", 0)
        readiness = quality_score.get("readiness", "?")
        print()
        print(f"  Composite Quality: {composite}/10 ({readiness})")
        print(f"  {bar_chart(composite, 10, 40)}")
else:
    print("  No review data found for this project.")
    print("  Reviews appear after the review stage completes.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Author Growth
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(hr("─"))
print(center("[ 4. AUTHOR GROWTH ]"))
print(hr("─"))

topics_graph = expertise_graph.get("topics", {})

if topics_graph:
    # Expertise graph visualization (ASCII)
    print("  Expertise Map:")
    print()

    # Sort by authority score descending
    sorted_topics = sorted(
        topics_graph.items(),
        key=lambda x: x[1].get("authority_score", 0),
        reverse=True
    )

    max_authority = max(t[1].get("authority_score", 1) for t in sorted_topics) if sorted_topics else 1

    for topic_name, data in sorted_topics[:12]:
        authority = data.get("authority_score", 0)
        articles = data.get("article_count", 0)
        bar = bar_chart(authority, max(max_authority, 10), 25)
        tags = ", ".join(data.get("tags", [])[:3])
        label = f"{topic_name[:20]:<20s}"
        print(f"    {label} {bar} {authority:>4.1f} ({articles} art) [{tags}]")

    print()

    # Articles per topic summary
    total_articles = sum(d.get("article_count", 0) for d in topics_graph.values())
    total_topics = len(topics_graph)
    print(f"  Total topics:   {total_topics}")
    print(f"  Total articles: {total_articles}")
    if total_topics > 0:
        print(f"  Avg per topic:  {total_articles / total_topics:.1f}")

    # Authority score distribution
    scores = [d.get("authority_score", 0) for d in topics_graph.values()]
    if scores:
        high = sum(1 for s in scores if s >= 7)
        medium = sum(1 for s in scores if 4 <= s < 7)
        low = sum(1 for s in scores if s < 4)
        print()
        print("  Authority Distribution:")
        print(f"    High (7+):   {'*' * high} {high}")
        print(f"    Medium (4-6):{'*' * medium} {medium}")
        print(f"    Low (<4):    {'*' * low} {low}")

    # Tag cloud (most used tags)
    tag_index = expertise_graph.get("tag_index", {})
    if tag_index:
        tag_counts = {tag: len(topics) for tag, topics in tag_index.items()}
        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
        if sorted_tags:
            print()
            print("  Top Tags: " + "  ".join(f"{t}({c})" for t, c in sorted_tags))
else:
    # Fallback to author profile expertise
    expertise_areas = author_profile.get("expertise_areas", [])
    if expertise_areas:
        print("  Expertise (from profile):")
        for e in expertise_areas:
            level = e.get("level", "?")
            level_score = {"beginner": 2, "intermediate": 5, "expert": 8, "authority": 10}.get(level, 3)
            bar = bar_chart(level_score, 10, 20)
            print(f"    {e['topic']:<25s} {bar} {level}")
    else:
        print("  No expertise data available.")
        print("  Run: expertise-graph.sh update <topic> [tags...]")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Platform Performance
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(hr("─"))
print(center("[ 5. PLATFORM PERFORMANCE ]"))
print(hr("─"))

analytics_articles = analytics_data.get("articles", {})

if analytics_articles:
    # Aggregate metrics
    total_views = 0
    total_shares = 0
    total_comments = 0
    total_likes = 0
    total_bookmarks = 0
    article_count = len(analytics_articles)

    # Per-article performance for ranking
    article_performance = []

    for aid, entry in analytics_articles.items():
        metrics = entry.get("metrics", {})
        views = metrics.get("views", 0)
        shares = metrics.get("shares", 0)
        comments = metrics.get("comments", 0)
        likes = metrics.get("likes", 0)
        bookmarks = metrics.get("bookmarks", 0)

        total_views += views
        total_shares += shares
        total_comments += comments
        total_likes += likes
        total_bookmarks += bookmarks

        article_performance.append({
            "id": aid,
            "views": views,
            "shares": shares,
            "engagement": shares + comments + likes + bookmarks,
        })

    print(f"  Articles tracked: {article_count}")
    print()
    print("  Aggregate Metrics:")
    metric_data = [
        ("Views", total_views),
        ("Shares", total_shares),
        ("Comments", total_comments),
        ("Likes", total_likes),
        ("Bookmarks", total_bookmarks),
    ]
    max_metric = max(v for _, v in metric_data) if metric_data else 1
    for name, val in metric_data:
        if val > 0 or name == "Views":
            bar = bar_chart(val, max(max_metric, 1), 25)
            avg = val / max(article_count, 1)
            print(f"    {name:<12s} {bar} {val:>8.0f} (avg {avg:.1f})")

    # Top performing articles
    article_performance.sort(key=lambda x: -x["views"])
    if article_performance:
        print()
        print("  Top Articles by Views:")
        for a in article_performance[:5]:
            bar = bar_chart(a["views"], max(article_performance[0]["views"], 1), 15)
            print(f"    {a['id'][:30]:<30s} {bar} {a['views']}")

    # Engagement ratio
    if total_views > 0:
        engagement_rate = ((total_shares + total_comments + total_likes) / total_views) * 100
        print()
        print(f"  Engagement rate: {engagement_rate:.1f}%")

    # Trends (compare first half vs second half)
    entries_sorted = sorted(analytics_articles.items(), key=lambda x: x[1].get("last_updated", ""))
    if len(entries_sorted) >= 4:
        mid = len(entries_sorted) // 2
        first_half = entries_sorted[:mid]
        second_half = entries_sorted[mid:]

        fh_views = sum(e.get("metrics", {}).get("views", 0) for _, e in first_half) / max(len(first_half), 1)
        sh_views = sum(e.get("metrics", {}).get("views", 0) for _, e in second_half) / max(len(second_half), 1)

        if fh_views > 0:
            change = ((sh_views - fh_views) / fh_views) * 100
            direction = "UP" if change > 5 else ("DOWN" if change < -5 else "FLAT")
            arrow = "^" if direction == "UP" else ("v" if direction == "DOWN" else "="
            )
            print(f"  Views trend: {direction} ({arrow} {abs(change):.0f}%)")
else:
    print("  No analytics data recorded.")
    print("  Run: analytics-feedback.sh record <article_id> <metric> <value>")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Writing Stats
# ═══════════════════════════════════════════════════════════════════════════════

print()
print(hr("─"))
print(center("[ 6. WRITING STATS ]"))
print(hr("─"))

# Scan for markdown files in the project
md_files = []
if os.path.isdir(project_dir):
    for pattern in ["*.md", "drafts/*.md", "output/*.md", "articles/*.md"]:
        md_files.extend(glob.glob(os.path.join(project_dir, pattern)))
    # Remove CLAUDE.md, OWNER.md, README.md etc
    md_files = [f for f in md_files if os.path.basename(f).lower() not in
                ("claude.md", "owner.md", "readme.md", "changelog.md", "skill.md")]

# Scan for readability scores in state dir
readability_files = glob.glob(os.path.join(state_dir, "readability-*.json")) if os.path.isdir(state_dir) else []

def analyze_markdown(filepath):
    """Basic text analysis on a markdown file."""
    try:
        with open(filepath) as f:
            content = f.read()
    except IOError:
        return None

    # Strip markdown formatting
    text = content
    # Remove YAML frontmatter
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    # Remove fenced code blocks (but count them first)
    code_blocks = re.findall(r'```[\s\S]*?```', text)
    code_lines = sum(cb.count('\n') for cb in code_blocks)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove HTML, images, links
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # Remove heading markers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    words = re.findall(r'[a-zA-Z]+', text)
    total_lines = content.count('\n') + 1

    return {
        "file": os.path.basename(filepath),
        "word_count": len(words),
        "code_blocks": len(code_blocks),
        "code_lines": code_lines,
        "total_lines": total_lines,
        "code_density": round(code_lines / max(total_lines, 1) * 100, 1),
    }

# Collect stats from readability score files
readability_stats = []
for rf in readability_files:
    data = load_json(rf)
    if data and "metrics" in data:
        readability_stats.append(data["metrics"])

# Also analyze any markdown files directly
article_stats = []
for mf in md_files:
    stats = analyze_markdown(mf)
    if stats and stats["word_count"] > 50:  # Skip trivial files
        article_stats.append(stats)

has_data = bool(article_stats) or bool(readability_stats)

if has_data:
    if article_stats:
        word_counts = [s["word_count"] for s in article_stats]
        code_densities = [s["code_density"] for s in article_stats]

        print(f"  Articles analyzed: {len(article_stats)}")
        print()

        # Word count stats
        avg_words = sum(word_counts) / len(word_counts)
        min_words = min(word_counts)
        max_words = max(word_counts)
        print(f"  Word Count:")
        print(f"    Average: {avg_words:.0f}    Min: {min_words}    Max: {max_words}")
        if len(word_counts) > 1:
            print(f"    Distribution: {spark_line(sorted(word_counts), 30)}")

        # Code density
        avg_code = sum(code_densities) / len(code_densities)
        print()
        print(f"  Code Density:")
        print(f"    Average: {avg_code:.1f}%")
        for s in article_stats[:8]:
            bar = bar_chart(s["code_density"], 50, 20)
            print(f"    {s['file'][:25]:<25s} {bar} {s['code_density']:>5.1f}%")

    if readability_stats:
        print()
        print("  Readability Scores:")

        fk_grades = [s.get("flesch_kincaid_grade", 0) for s in readability_stats]
        fre_scores = [s.get("flesch_reading_ease", 0) for s in readability_stats]
        avg_sentence_lens = [s.get("avg_sentence_length", 0) for s in readability_stats]

        if fk_grades:
            avg_fk = sum(fk_grades) / len(fk_grades)
            print(f"    Flesch-Kincaid grade: {avg_fk:.1f} (avg)")
            if len(fk_grades) > 1:
                print(f"    Grade range: {min(fk_grades):.1f} - {max(fk_grades):.1f}")
                print(f"    Trend: {spark_line(fk_grades, 20)}")

        if fre_scores:
            avg_fre = sum(fre_scores) / len(fre_scores)
            print(f"    Reading ease: {avg_fre:.1f} (avg)")

        if avg_sentence_lens:
            avg_sl = sum(avg_sentence_lens) / len(avg_sentence_lens)
            print(f"    Avg sentence length: {avg_sl:.1f} words")

    # Taste memory writing stats
    learned = taste_memory.get("learned_patterns", [])
    if learned:
        tone_shifts = [p["tone_shift"] for p in learned if p.get("tone_shift") and p["tone_shift"] != "neutral"]
        length_changes = [p["length_change"] for p in learned if p.get("length_change")]
        code_changes = [p["code_density_change"] for p in learned if p.get("code_density_change") and p["code_density_change"] != "unchanged"]

        if tone_shifts or length_changes or code_changes:
            print()
            print("  Editing Patterns (from taste memory):")
            if tone_shifts:
                tc = collections.Counter(tone_shifts)
                print(f"    Tone shifts: {', '.join(f'{k}({v})' for k, v in tc.most_common(3))}")
            if length_changes:
                lc = collections.Counter(length_changes)
                print(f"    Length edits: {', '.join(f'{k}({v})' for k, v in lc.most_common(3))}")
            if code_changes:
                cc = collections.Counter(code_changes)
                print(f"    Code edits:  {', '.join(f'{k}({v})' for k, v in cc.most_common(3))}")
else:
    print("  No article files or readability data found.")
    print("  Stats appear after writing drafts or running readability-score.sh.")

# ── Footer ───────────────────────────────────────────────────────────────────

print()
print(hr("═"))
print(center("Dashboard generated " + datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")))
print(hr("═"))
PYEOF
