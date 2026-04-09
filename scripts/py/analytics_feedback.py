#!/usr/bin/env python3
"""Analytics feedback loop — track article performance and feed insights into taste memory.
Usage: analytics_feedback.py <command> [args...]
"""

import json
import os
import sys
import time

from utils import atomic_json_write, read_json_file

ANALYTICS_DIR = os.path.expanduser("~/.tech-essay-writer")
ANALYTICS_FILE = os.path.join(ANALYTICS_DIR, "analytics.json")
TASTE_FILE = os.path.join(ANALYTICS_DIR, "taste-memory.json")
XREF_FILE = os.path.join(ANALYTICS_DIR, "published-articles.json")

VALID_METRICS = ["views", "shares", "comments", "likes", "bookmarks", "read_time_avg", "bounce_rate"]


def usage():
    print("""Usage: analytics-feedback.sh <command> [args...]

Commands:
  record <article_id> <metric> <value>         Record a performance metric
  record-batch <article_id> <json_metrics>     Record multiple metrics from JSON
  query <article_id>                           Show all metrics for an article
  top [metric] [n]                             Top N articles by metric (default: views, 5)
  trends                                       Show performance trends
  feed-taste <project_dir>                     Analyze and update taste memory with insights
  summary                                      Human-readable analytics summary
  compare <article_id_1> <article_id_2>        Compare metrics between two articles""")


def ensure_analytics():
    os.makedirs(ANALYTICS_DIR, exist_ok=True)
    if not os.path.isfile(ANALYTICS_FILE):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_json_write(ANALYTICS_FILE, {"articles": {}, "updated_at": now})


def validate_metric(metric):
    if metric not in VALID_METRICS:
        print(f"ERROR: Invalid metric '{metric}'. Valid: {' '.join(VALID_METRICS)}", file=sys.stderr)
        return False
    return True


def cmd_record(args):
    if len(args) < 3 or not args[0] or not args[1] or not args[2]:
        print("ERROR: record requires <article_id> <metric> <value>", file=sys.stderr)
        return 1

    article_id = args[0]
    metric = args[1]
    if not validate_metric(metric):
        return 1

    raw = float(args[2])
    value = int(raw) if raw == int(raw) else raw

    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if article_id not in d["articles"]:
        d["articles"][article_id] = {
            "metrics": {},
            "first_recorded": now,
            "last_updated": now
        }

    d["articles"][article_id]["metrics"][metric] = value
    d["articles"][article_id]["last_updated"] = now
    d["updated_at"] = now

    atomic_json_write(ANALYTICS_FILE, d)
    print(f"Recorded {metric}={value} for {article_id}")
    return 0


def cmd_record_batch(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: record-batch requires <article_id> <json_metrics>", file=sys.stderr)
        return 1

    article_id = args[0]
    metrics_str = args[1]

    try:
        metrics = json.loads(metrics_str)
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON for metrics", file=sys.stderr)
        return 1

    # Validate all metric names
    valid = set(VALID_METRICS)
    for k in metrics:
        if k not in valid:
            print(f'ERROR: Invalid metric "{k}". Valid: {" ".join(sorted(valid))}', file=sys.stderr)
            return 1

    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if article_id not in d["articles"]:
        d["articles"][article_id] = {
            "metrics": {},
            "first_recorded": now,
            "last_updated": now
        }

    for k, v in metrics.items():
        fv = float(v)
        d["articles"][article_id]["metrics"][k] = int(fv) if fv == int(fv) else fv

    d["articles"][article_id]["last_updated"] = now
    d["updated_at"] = now

    atomic_json_write(ANALYTICS_FILE, d)
    print(f"Recorded {len(metrics)} metrics for {article_id}")
    return 0


def cmd_query(args):
    if not args or not args[0]:
        print("ERROR: query requires <article_id>", file=sys.stderr)
        return 1

    article_id = args[0]
    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})

    entry = d.get("articles", {}).get(article_id)
    if not entry:
        print(f"No metrics found for {article_id}", file=sys.stderr)
        return 1

    print(json.dumps(entry, indent=2))
    return 0


def cmd_top(args):
    metric = args[0] if args else "views"
    n = int(args[1]) if len(args) > 1 else 5

    if not validate_metric(metric):
        return 1

    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})

    scored = []
    for aid, entry in d.get("articles", {}).items():
        val = entry.get("metrics", {}).get(metric, 0)
        scored.append((val, aid))

    scored.sort(key=lambda x: -x[0])

    if not scored:
        print("No analytics data yet.")
    else:
        print(f"Top {min(n, len(scored))} articles by {metric}:")
        for val, aid in scored[:n]:
            print(f"  {aid}: {val}")
    return 0


def cmd_trends():
    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})

    articles = d.get("articles", {})
    if not articles:
        print("No analytics data recorded yet.")
        return 0

    n = len(articles)
    all_metrics = {}
    for aid, entry in articles.items():
        for k, v in entry.get("metrics", {}).items():
            all_metrics.setdefault(k, []).append(v)

    result = {"total_articles": n, "metrics_summary": {}}
    for metric, values in all_metrics.items():
        avg = sum(values) / len(values) if values else 0
        result["metrics_summary"][metric] = {
            "average": round(avg, 2),
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }

    # Simple trend: compare first half vs second half by last_updated
    entries = [(aid, e) for aid, e in articles.items()]
    entries.sort(key=lambda x: x[1].get("last_updated", ""))

    if n >= 4:
        mid = n // 2
        first_half = entries[:mid]
        second_half = entries[mid:]
        trends = {}
        for metric in all_metrics:
            first_avg = sum(e.get("metrics", {}).get(metric, 0) for _, e in first_half) / len(first_half)
            second_avg = sum(e.get("metrics", {}).get(metric, 0) for _, e in second_half) / len(second_half)
            if first_avg > 0:
                change = ((second_avg - first_avg) / first_avg) * 100
                direction = "improving" if change > 5 else ("declining" if change < -5 else "stable")
                trends[metric] = {"direction": direction, "change_pct": round(change, 1)}
            else:
                trends[metric] = {"direction": "new", "change_pct": 0}
        result["trends"] = trends

    print(json.dumps(result, indent=2))
    return 0


def cmd_feed_taste(args):
    if not args or not args[0]:
        print("ERROR: feed-taste requires <project_dir>", file=sys.stderr)
        return 1

    ensure_analytics()

    # Ensure taste file exists
    if not os.path.isfile(TASTE_FILE):
        atomic_json_write(TASTE_FILE, {})

    analytics = read_json_file(ANALYTICS_FILE, {"articles": {}})
    taste = read_json_file(TASTE_FILE)

    # Load published articles for metadata correlation
    xref = read_json_file(XREF_FILE, {"articles": []})

    articles = analytics.get("articles", {})
    if not articles:
        print("No analytics data to analyze.")
        return 0

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Build article metadata map from cross-references
    meta_map = {}
    for a in xref.get("articles", []):
        meta_map[a["id"]] = a

    # Calculate averages
    total_views = 0
    total_shares = 0
    count = 0
    tag_performance = {}
    top_article = None
    top_views = 0

    for aid, entry in articles.items():
        metrics = entry.get("metrics", {})
        views = metrics.get("views", 0)
        shares = metrics.get("shares", 0)
        total_views += views
        total_shares += shares
        count += 1

        if views > top_views:
            top_views = views
            meta = meta_map.get(aid, {})
            top_article = {
                "id": aid,
                "title": meta.get("title", aid),
                "views": views
            }

        # Correlate with tags if available
        meta = meta_map.get(aid, {})
        for tag in meta.get("tags", []):
            tag_performance.setdefault(tag, {"total_views": 0, "total_shares": 0, "count": 0})
            tag_performance[tag]["total_views"] += views
            tag_performance[tag]["total_shares"] += shares
            tag_performance[tag]["count"] += 1

    # Find best performing tags
    best_tags = sorted(
        tag_performance.items(),
        key=lambda x: x[1]["total_views"] / max(x[1]["count"], 1),
        reverse=True
    )[:5]

    # Generate insights
    insights = []
    avg_views = total_views / max(count, 1)
    avg_shares = total_shares / max(count, 1)

    if best_tags:
        top_tag = best_tags[0]
        tag_avg = top_tag[1]["total_views"] / max(top_tag[1]["count"], 1)
        if tag_avg > avg_views * 1.2:
            pct = int((tag_avg / max(avg_views, 1) - 1) * 100)
            insights.append(f'Articles tagged "{top_tag[0]}" average {pct}% more views')

    # Determine best performing format from taste memory topics
    topics = taste.get("topics_written", [])
    variant_perf = {}
    for t in topics:
        variant = t.get("variant")
        topic_name = t.get("topic", "")
        if variant:
            variant_perf.setdefault(variant, {"count": 0, "total_views": 0})
            for aid, entry in articles.items():
                meta = meta_map.get(aid, {})
                if topic_name.lower() in meta.get("title", "").lower():
                    variant_perf[variant]["total_views"] += entry.get("metrics", {}).get("views", 0)
                    variant_perf[variant]["count"] += 1

    best_format = None
    best_format_avg = 0
    for v, perf in variant_perf.items():
        if perf["count"] > 0:
            v_avg = perf["total_views"] / perf["count"]
            if v_avg > best_format_avg:
                best_format_avg = v_avg
                best_format = v

    if best_format and best_format_avg > avg_views:
        insights.append(f"{best_format}-style articles perform above average")

    performance_insights = {
        "best_performing_tags": [t[0] for t in best_tags],
        "best_performing_format": best_format or "unknown",
        "avg_views": round(avg_views, 1),
        "avg_shares": round(avg_shares, 1),
        "top_article": top_article,
        "insights": insights,
        "updated_at": now
    }

    taste["performance_insights"] = performance_insights
    atomic_json_write(TASTE_FILE, taste)

    print("Performance insights updated in taste memory.")
    print(f"  Articles analyzed: {count}")
    print(f"  Avg views: {avg_views:.0f}")
    print(f"  Avg shares: {avg_shares:.0f}")
    if insights:
        print("  Insights:")
        for i in insights:
            print(f"    - {i}")
    return 0


def cmd_summary():
    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})

    articles = d.get("articles", {})
    if not articles:
        print("No analytics data yet.")
        return 0

    print(f"Analytics Summary ({len(articles)} articles)")
    print(f"Last updated: {d.get('updated_at', '?')}")
    print()

    # Aggregate stats
    all_metrics = {}
    for aid, entry in articles.items():
        for k, v in entry.get("metrics", {}).items():
            all_metrics.setdefault(k, []).append(v)

    for metric, values in sorted(all_metrics.items()):
        avg = sum(values) / len(values)
        total = sum(values)
        print(f"{metric}:")
        print(f"  Total: {total:.1f}  Avg: {avg:.1f}  Min: {min(values):.1f}  Max: {max(values):.1f}")
    return 0


def cmd_compare(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: compare requires <article_id_1> <article_id_2>", file=sys.stderr)
        return 1

    id1 = args[0]
    id2 = args[1]
    ensure_analytics()
    d = read_json_file(ANALYTICS_FILE, {"articles": {}})

    a1 = d.get("articles", {}).get(id1)
    a2 = d.get("articles", {}).get(id2)

    if not a1:
        print(f"No data for article: {id1}")
        return 0
    if not a2:
        print(f"No data for article: {id2}")
        return 0

    m1 = a1.get("metrics", {})
    m2 = a2.get("metrics", {})
    all_keys = sorted(set(list(m1.keys()) + list(m2.keys())))

    print(f"Comparison: {id1} vs {id2}")
    print(f"{'Metric':<16} {id1:<12} {id2:<12} Diff")
    print("-" * 52)
    for k in all_keys:
        v1 = m1.get(k, 0)
        v2 = m2.get(k, 0)
        diff = v2 - v1
        sign = "+" if diff > 0 else ""
        print(f"{k:<16} {v1:<12.1f} {v2:<12.1f} {sign}{diff:.1f}")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "record": lambda: cmd_record(rest),
        "record-batch": lambda: cmd_record_batch(rest),
        "query": lambda: cmd_query(rest),
        "top": lambda: cmd_top(rest),
        "trends": lambda: cmd_trends(),
        "feed-taste": lambda: cmd_feed_taste(rest),
        "summary": lambda: cmd_summary(),
        "compare": lambda: cmd_compare(rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
