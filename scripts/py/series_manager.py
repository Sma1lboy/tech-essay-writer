#!/usr/bin/env python3
"""Series manager — manages multi-article series with narrative arc and reading order.
Usage: series_manager.py <command> [args...]
"""

import json
import os
import sys
import time

from utils import atomic_json_write, read_json_file

SERIES_DIR = os.path.expanduser("~/.tech-essay-writer")
SERIES_FILE = os.path.join(SERIES_DIR, "series.json")


def usage():
    print("""Usage: series-manager.sh <command> [args...]

Commands:
  create <name> <description>                     Create a new series
  add <series_id> <article_id> <title> [position] Add article to series
  list                                            List all series
  show <series_id>                                Show series details
  context <series_id>                             Output JSON context for prompt injection
  set-arc <series_id> <arc_description>           Set narrative arc description
  set-summary <series_id> <article_id> <summary>  Set article summary within series
  next-position <series_id>                       Output next available position
  search <query>                                  Search series by keyword
  reorder <series_id> <article_id> <new_position> Move article to new position""")


def ensure_series():
    os.makedirs(SERIES_DIR, exist_ok=True)
    if not os.path.isfile(SERIES_FILE):
        atomic_json_write(SERIES_FILE, {"series": []})


def read_series():
    return read_json_file(SERIES_FILE, {"series": []})


def cmd_create(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: create requires <name> <description>", file=sys.stderr)
        return 1

    name = args[0]
    description = args[1]
    ensure_series()
    d = read_series()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    existing_ids = {s["id"] for s in d["series"]}
    base_id = int(time.time())
    series_id = f"ser-{base_id}"
    while series_id in existing_ids:
        base_id += 1
        series_id = f"ser-{base_id}"

    d["series"].append({
        "id": series_id,
        "name": name,
        "description": description,
        "narrative_arc": "",
        "created_at": now,
        "updated_at": now,
        "articles": []
    })

    atomic_json_write(SERIES_FILE, d)
    print(f"Created series: {name} ({series_id})")
    return 0


def cmd_add(args):
    if len(args) < 3 or not args[0] or not args[1] or not args[2]:
        print("ERROR: add requires <series_id> <article_id> <title> [position]", file=sys.stderr)
        return 1

    series_id = args[0]
    article_id = args[1]
    title = args[2]
    position = args[3] if len(args) > 3 and args[3] else ""
    ensure_series()
    d = read_series()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    found = False

    for s in d["series"]:
        if s["id"] == series_id:
            found = True
            articles = s["articles"]

            if position:
                pos = int(position)
            else:
                pos = max((a["position"] for a in articles), default=0) + 1

            articles.append({
                "article_id": article_id,
                "title": title,
                "position": pos,
                "summary": "",
                "added_at": now
            })

            s["articles"] = sorted(articles, key=lambda a: a["position"])
            s["updated_at"] = now
            break

    if not found:
        print(f"Series {series_id} not found.", file=sys.stderr)
        return 1

    atomic_json_write(SERIES_FILE, d)
    print(f"Added: {title} to {series_id} at position {pos}")
    return 0


def cmd_list():
    ensure_series()
    d = read_series()

    if not d["series"]:
        print("No series defined.")
    else:
        print(f"Series: {len(d['series'])}")
        for s in d["series"]:
            count = len(s.get("articles", []))
            print(f"  [{s['id']}] {s['name']} ({count} articles)")
            if s.get("description"):
                print(f"    {s['description'][:80]}")
    return 0


def cmd_show(args):
    if not args or not args[0]:
        print("ERROR: show requires <series_id>", file=sys.stderr)
        return 1

    series_id = args[0]
    ensure_series()
    d = read_series()

    for s in d["series"]:
        if s["id"] == series_id:
            print(f"Series: {s['name']}")
            print(f"ID: {s['id']}")
            print(f"Description: {s.get('description', '')}")
            print(f"Narrative arc: {s.get('narrative_arc', '')}")
            print(f"Created: {s['created_at']}")
            print(f"Updated: {s['updated_at']}")
            articles = sorted(s.get("articles", []), key=lambda a: a["position"])
            print(f"Articles ({len(articles)}):")
            for a in articles:
                summary_str = f" — {a['summary']}" if a.get("summary") else ""
                print(f"  {a['position']}. [{a['article_id']}] {a['title']}{summary_str}")
            return 0

    print(f"Series {series_id} not found.", file=sys.stderr)
    return 1


def cmd_context(args):
    if not args or not args[0]:
        print("ERROR: context requires <series_id>", file=sys.stderr)
        return 1

    series_id = args[0]
    ensure_series()
    d = read_series()

    for s in d["series"]:
        if s["id"] == series_id:
            articles = sorted(s.get("articles", []), key=lambda a: a["position"])
            context = {
                "series_name": s["name"],
                "series_description": s.get("description", ""),
                "narrative_arc": s.get("narrative_arc", ""),
                "total_articles": len(articles),
                "articles": [
                    {
                        "article_id": a["article_id"],
                        "title": a["title"],
                        "position": a["position"],
                        "summary": a.get("summary", "")
                    }
                    for a in articles
                ]
            }
            print(json.dumps(context, indent=2))
            return 0

    print(json.dumps({"error": f"Series {series_id} not found"}))
    return 1


def cmd_set_arc(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: set-arc requires <series_id> <arc_description>", file=sys.stderr)
        return 1

    series_id = args[0]
    arc_description = args[1]
    ensure_series()
    d = read_series()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    found = False

    for s in d["series"]:
        if s["id"] == series_id:
            found = True
            s["narrative_arc"] = arc_description
            s["updated_at"] = now
            break

    if not found:
        print(f"Series {series_id} not found.", file=sys.stderr)
        return 1

    atomic_json_write(SERIES_FILE, d)
    print(f"Set arc for {series_id}")
    return 0


def cmd_set_summary(args):
    if len(args) < 3 or not args[0] or not args[1] or not args[2]:
        print("ERROR: set-summary requires <series_id> <article_id> <summary>", file=sys.stderr)
        return 1

    series_id = args[0]
    article_id = args[1]
    summary = args[2]
    ensure_series()
    d = read_series()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    found_series = False
    found_article = False

    for s in d["series"]:
        if s["id"] == series_id:
            found_series = True
            for a in s["articles"]:
                if a["article_id"] == article_id:
                    found_article = True
                    a["summary"] = summary
                    break
            s["updated_at"] = now
            break

    if not found_series:
        print(f"Series {series_id} not found.", file=sys.stderr)
        return 1
    if not found_article:
        print(f"Article {article_id} not found in series {series_id}.", file=sys.stderr)
        return 1

    atomic_json_write(SERIES_FILE, d)
    print(f"Set summary for {article_id} in {series_id}")
    return 0


def cmd_next_position(args):
    if not args or not args[0]:
        print("ERROR: next-position requires <series_id>", file=sys.stderr)
        return 1

    series_id = args[0]
    ensure_series()
    d = read_series()

    for s in d["series"]:
        if s["id"] == series_id:
            articles = s.get("articles", [])
            pos = max((a["position"] for a in articles), default=0) + 1
            print(pos)
            return 0

    print(f"Series {series_id} not found.", file=sys.stderr)
    return 1


def cmd_search(args):
    if not args or not args[0]:
        print("ERROR: search requires <query>", file=sys.stderr)
        return 1

    query = args[0].lower()
    ensure_series()
    d = read_series()

    results = []
    for s in d["series"]:
        score = 0
        if query in s["name"].lower():
            score += 2
        if query in s.get("description", "").lower():
            score += 1
        if query in s.get("narrative_arc", "").lower():
            score += 1
        if score > 0:
            results.append((score, s))

    results.sort(key=lambda x: -x[0])
    if not results:
        print("No matching series found.")
    else:
        for score, s in results:
            count = len(s.get("articles", []))
            print(f"  [{s['id']}] {s['name']} ({count} articles)")
            if s.get("description"):
                print(f"    {s['description'][:80]}")
    return 0


def cmd_reorder(args):
    if len(args) < 3 or not args[0] or not args[1] or not args[2]:
        print("ERROR: reorder requires <series_id> <article_id> <new_position>", file=sys.stderr)
        return 1

    series_id = args[0]
    article_id = args[1]
    new_pos = int(args[2])
    ensure_series()
    d = read_series()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    found_series = False
    found_article = False

    for s in d["series"]:
        if s["id"] == series_id:
            found_series = True
            target = None
            others = []
            for a in s["articles"]:
                if a["article_id"] == article_id:
                    found_article = True
                    target = a
                else:
                    others.append(a)

            if not found_article:
                print(f"Article {article_id} not found in series {series_id}.", file=sys.stderr)
                return 1

            target["position"] = new_pos

            # Rebuild: insert target at new_pos, renumber others
            others = sorted(others, key=lambda a: a["position"])
            result = []
            inserted = False
            pos = 1
            for a in others:
                if pos == new_pos and not inserted:
                    result.append(target)
                    target["position"] = pos
                    pos += 1
                    inserted = True
                a["position"] = pos
                result.append(a)
                pos += 1

            if not inserted:
                target["position"] = pos
                result.append(target)

            s["articles"] = result
            s["updated_at"] = now
            break

    if not found_series:
        print(f"Series {series_id} not found.", file=sys.stderr)
        return 1

    atomic_json_write(SERIES_FILE, d)
    print(f"Reordered {article_id} to position {new_pos} in {series_id}")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "create": lambda: cmd_create(rest),
        "add": lambda: cmd_add(rest),
        "list": lambda: cmd_list(),
        "show": lambda: cmd_show(rest),
        "context": lambda: cmd_context(rest),
        "set-arc": lambda: cmd_set_arc(rest),
        "set-summary": lambda: cmd_set_summary(rest),
        "next-position": lambda: cmd_next_position(rest),
        "search": lambda: cmd_search(rest),
        "reorder": lambda: cmd_reorder(rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
