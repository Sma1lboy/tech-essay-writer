#!/usr/bin/env python3
"""Cross-reference system — tracks published articles for internal linking.
Usage: cross_reference.py <command> [args...]
"""

import json
import os
import sys
import time

from utils import atomic_json_write, read_json_file

XREF_DIR = os.path.expanduser("~/.tech-essay-writer")
XREF_FILE = os.path.join(XREF_DIR, "published-articles.json")


def usage():
    print("""Usage: cross-reference.sh <command> [args...]

Commands:
  add <title> <url> [tags...]     Register a published article
  search <query>                  Search published articles by keyword
  list                            List all published articles
  suggest <topic>                 Suggest related articles to link to
  remove <id>                     Remove an article entry""")


def ensure_xref():
    os.makedirs(XREF_DIR, exist_ok=True)
    if not os.path.isfile(XREF_FILE):
        atomic_json_write(XREF_FILE, {"articles": []})


def read_xref():
    return read_json_file(XREF_FILE, {"articles": []})


def cmd_add(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: add requires <title> <url> [tags...]", file=sys.stderr)
        return 1

    title = args[0]
    url = args[1]
    tags = args[2:] if len(args) > 2 else []
    ensure_xref()

    d = read_xref()
    article_id = f"art-{int(time.time())}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    d["articles"].append({
        "id": article_id,
        "title": title,
        "url": url,
        "tags": tags,
        "added_at": now,
        "referenced_count": 0
    })

    atomic_json_write(XREF_FILE, d)
    print(f"Added: {title} ({article_id})")
    return 0


def cmd_search(args):
    if not args or not args[0]:
        print("ERROR: search requires <query>", file=sys.stderr)
        return 1

    query = args[0].lower()
    ensure_xref()
    d = read_xref()

    results = []
    for a in d["articles"]:
        score = 0
        if query in a["title"].lower():
            score += 2
        for tag in a.get("tags", []):
            if query in tag.lower():
                score += 1
        if score > 0:
            results.append((score, a))

    results.sort(key=lambda x: -x[0])
    if not results:
        print("No matching articles found.")
    else:
        for score, a in results[:5]:
            print(f"  [{a['id']}] {a['title']}")
            print(f"    URL: {a['url']}")
            print(f"    Tags: {', '.join(a.get('tags', []))}")
    return 0


def cmd_list():
    ensure_xref()
    d = read_xref()

    if not d["articles"]:
        print("No published articles registered.")
    else:
        print(f"Published articles: {len(d['articles'])}")
        for a in d["articles"]:
            print(f"  [{a['id']}] {a['title']} ({a['url']})")
            if a.get("tags"):
                print(f"    Tags: {', '.join(a['tags'])}")
    return 0


def cmd_suggest(args):
    if not args or not args[0]:
        print("ERROR: suggest requires <topic>", file=sys.stderr)
        return 1

    topic = args[0].lower()
    topic_words = set(topic.split())
    ensure_xref()
    d = read_xref()

    suggestions = []
    for a in d["articles"]:
        title_words = set(a["title"].lower().split())
        tag_words = set(t.lower() for t in a.get("tags", []))
        overlap = len(topic_words & (title_words | tag_words))
        if overlap > 0:
            suggestions.append((overlap, a))

    suggestions.sort(key=lambda x: -x[0])
    if not suggestions:
        print("No related articles to cross-reference.")
    else:
        print("Suggested cross-references:")
        for score, a in suggestions[:3]:
            print(f"  - [{a['title']}]({a['url']})")
    return 0


def cmd_remove(args):
    if not args or not args[0]:
        print("ERROR: remove requires <article_id>", file=sys.stderr)
        return 1

    article_id = args[0]
    ensure_xref()
    d = read_xref()

    before = len(d["articles"])
    d["articles"] = [a for a in d["articles"] if a.get("id") != article_id]
    after = len(d["articles"])

    if before == after:
        print(f"Article {article_id} not found.")
        return 1

    atomic_json_write(XREF_FILE, d)
    print(f"Removed article {article_id}")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "add": lambda: cmd_add(rest),
        "search": lambda: cmd_search(rest),
        "list": lambda: cmd_list(),
        "suggest": lambda: cmd_suggest(rest),
        "remove": lambda: cmd_remove(rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
