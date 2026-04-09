#!/usr/bin/env python3
"""Expertise graph — track topic authority based on published articles.
Usage: expertise_graph.py <command> [args...]
"""

import json
import os
import sys
from datetime import datetime, timezone

from utils import atomic_json_write, read_json_file, timestamp_now

GRAPH_DIR = os.path.expanduser("~/.tech-essay-writer")
GRAPH_FILE = os.path.join(GRAPH_DIR, "expertise-graph.json")


def usage():
    print("""Usage: expertise-graph.sh <command> [args...]

Commands:
  update <topic> [tags...]    Record an article published on this topic
  query <topic>               Get authority level for a topic
  top [n]                     List top N expertise areas by article count
  suggest                     Suggest topics to write about next
  read                        Dump the full graph""")


def read_graph():
    data = read_json_file(GRAPH_FILE)
    if not data:
        return {"topics": {}, "tag_index": {}, "updated_at": ""}
    return data


def write_graph(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    atomic_json_write(GRAPH_FILE, data)


def calc_recency_bonus(last_article_date_str):
    """Calculate recency bonus from last_article date string (YYYY-MM-DD)."""
    try:
        last_date = datetime.strptime(last_article_date_str, "%Y-%m-%d")
        days_ago = (datetime.utcnow() - last_date).days
        if days_ago <= 90:
            return 1.0
        elif days_ago <= 180:
            return 0.5
        else:
            return 0
    except Exception:
        return 0


def calc_authority_score(article_count, last_article_date_str):
    """Calculate authority score: min(10, count*2 + recency_bonus)."""
    recency_bonus = calc_recency_bonus(last_article_date_str)
    return round(min(10, article_count * 2 + recency_bonus), 1)


def cmd_update(args):
    if not args or not args[0]:
        print("ERROR: update requires <topic>", file=sys.stderr)
        return 1

    topic = args[0]
    tags = args[1:] if len(args) > 1 else []
    graph = read_graph()
    now = timestamp_now()

    topics = graph.setdefault("topics", {})
    tag_index = graph.setdefault("tag_index", {})

    if topic in topics:
        topics[topic]["article_count"] += 1
        topics[topic]["last_article"] = now[:10]
        existing_tags = set(topics[topic].get("tags", []))
        existing_tags.update(tags)
        topics[topic]["tags"] = sorted(existing_tags)
    else:
        topics[topic] = {
            "article_count": 1,
            "tags": sorted(tags),
            "first_article": now[:10],
            "last_article": now[:10],
            "authority_score": 0
        }

    # Recalculate authority score
    entry = topics[topic]
    entry["authority_score"] = calc_authority_score(entry["article_count"], entry["last_article"])

    # Update tag index
    for tag in tags:
        tag_index.setdefault(tag, [])
        if topic not in tag_index[tag]:
            tag_index[tag].append(topic)

    graph["updated_at"] = now
    write_graph(graph)
    print(f"Updated topic: {topic}")
    return 0


def cmd_query(args):
    if not args or not args[0]:
        print("ERROR: query requires <topic>", file=sys.stderr)
        return 1

    topic = args[0]
    graph = read_graph()
    topics = graph.get("topics", {})

    if topic not in topics:
        print(f"No data for topic: {topic}")
        return 0

    entry = topics[topic]
    count = entry["article_count"]
    score = calc_authority_score(count, entry.get("last_article", ""))

    print(f"Topic: {topic}")
    print(f"Articles: {count}")
    print(f"Authority score: {score}/10")
    print(f"Tags: {', '.join(entry.get('tags', []))}")
    print(f"First article: {entry.get('first_article', '?')}")
    print(f"Last article: {entry.get('last_article', '?')}")
    return 0


def cmd_top(args):
    n = int(args[0]) if args else 5
    graph = read_graph()
    topics = graph.get("topics", {})

    if not topics:
        print("No topics tracked yet.")
        return 0

    scored = []
    for name, entry in topics.items():
        count = entry["article_count"]
        score = calc_authority_score(count, entry.get("last_article", ""))
        scored.append((score, count, name, entry))

    scored.sort(key=lambda x: (-x[0], -x[1]))
    print(f"Top {min(n, len(scored))} expertise areas:")
    for score, count, name, entry in scored[:n]:
        tags_str = ", ".join(entry.get("tags", [])[:3])
        print(f"  {name}: {score}/10 ({count} articles) [{tags_str}]")
    return 0


def cmd_suggest():
    graph = read_graph()

    # Also read author profile expertise if available
    author_expertise = []
    profile_file = os.path.join(GRAPH_DIR, "author-profile.json")
    if os.path.isfile(profile_file):
        try:
            profile = read_json_file(profile_file)
            author_expertise = profile.get("expertise_areas", [])
        except Exception:
            pass

    topics = graph.get("topics", {})
    tag_index = graph.get("tag_index", {})
    suggestions = []

    # 1. Expertise gaps: topics in author profile but not in graph
    for e in author_expertise:
        t = e["topic"]
        if t not in topics:
            suggestions.append(("GAP", t, f"Listed as {e['level']} but no articles written yet"))
        elif topics[t]["article_count"] < 2:
            suggestions.append(("THIN", t, f"Only {topics[t]['article_count']} article(s) — build authority"))

    # 2. Stale topics: haven't written about recently
    for name, entry in topics.items():
        last = entry.get("last_article", "")
        try:
            last_date = datetime.strptime(last, "%Y-%m-%d")
            days_ago = (datetime.utcnow() - last_date).days
            if days_ago > 180 and entry["article_count"] >= 2:
                suggestions.append(("STALE", name, f"Last article {days_ago} days ago — refresh authority"))
        except Exception:
            pass

    # 3. Adjacent topics: tags that appear in multiple topics suggest bridges
    tag_bridges = {}
    for tag, topic_list in tag_index.items():
        if len(topic_list) >= 2:
            tag_bridges[tag] = topic_list

    if tag_bridges:
        for tag, bridged in tag_bridges.items():
            combined = f"{bridged[0]}+{bridged[1]}"
            if combined not in topics:
                suggestions.append(("ADJACENT", f"{bridged[0]} x {bridged[1]}", f"Bridge via shared tag '{tag}'"))

    if not suggestions:
        print("No specific suggestions. Consider exploring new topic areas.")
    else:
        print("Suggested next topics:")
        for kind, topic, reason in suggestions[:5]:
            print(f"  [{kind}] {topic} — {reason}")
    return 0


def cmd_read():
    graph = read_graph()
    print(json.dumps(graph, indent=2))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "update": lambda: cmd_update(rest),
        "query": lambda: cmd_query(rest),
        "top": lambda: cmd_top(rest),
        "suggest": lambda: cmd_suggest(),
        "read": lambda: cmd_read(),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
