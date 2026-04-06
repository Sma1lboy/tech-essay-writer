#!/usr/bin/env bash
# Cross-reference system — tracks published articles for internal linking
# Usage: cross-reference.sh <command> [args...]
set -euo pipefail

XREF_DIR="$HOME/.tech-essay-writer"
XREF_FILE="$XREF_DIR/published-articles.json"

usage() {
  cat <<'EOF'
Usage: cross-reference.sh <command> [args...]

Commands:
  add <title> <url> [tags...]     Register a published article
  search <query>                  Search published articles by keyword
  list                            List all published articles
  suggest <topic>                 Suggest related articles to link to
  remove <id>                     Remove an article entry
EOF
}

ensure_xref() {
  mkdir -p "$XREF_DIR"
  if [ ! -f "$XREF_FILE" ]; then
    echo '{"articles":[]}' > "$XREF_FILE"
  fi
}

cmd_add() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add requires <title> <url> [tags...]" >&2
    return 1
  fi
  local title="$1" url="$2"
  shift 2
  local tags="$*"
  ensure_xref
  python3 -c "
import json, sys, os, time

xref_file = sys.argv[1]
title = sys.argv[2]
url = sys.argv[3]
tags = sys.argv[4].split() if sys.argv[4] else []

with open(xref_file) as f:
    d = json.load(f)

article_id = f'art-{int(time.time())}'
d['articles'].append({
    'id': article_id,
    'title': title,
    'url': url,
    'tags': tags,
    'added_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'referenced_count': 0
})

tmp = xref_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, xref_file)

print(f'Added: {title} ({article_id})')
" "$XREF_FILE" "$title" "$url" "$tags"
}

cmd_search() {
  if [ -z "${1:-}" ]; then
    echo "ERROR: search requires <query>" >&2
    return 1
  fi
  local query="$1"
  ensure_xref
  python3 -c "
import json, sys

query = sys.argv[1].lower()
with open(sys.argv[2]) as f:
    d = json.load(f)

results = []
for a in d['articles']:
    score = 0
    if query in a['title'].lower():
        score += 2
    for tag in a.get('tags', []):
        if query in tag.lower():
            score += 1
    if score > 0:
        results.append((score, a))

results.sort(key=lambda x: -x[0])
if not results:
    print('No matching articles found.')
else:
    for score, a in results[:5]:
        print(f\"  [{a['id']}] {a['title']}\")
        print(f\"    URL: {a['url']}\")
        print(f\"    Tags: {', '.join(a.get('tags', []))}\")
" "$query" "$XREF_FILE"
}

cmd_list() {
  ensure_xref
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

if not d['articles']:
    print('No published articles registered.')
else:
    print(f\"Published articles: {len(d['articles'])}\")
    for a in d['articles']:
        print(f\"  [{a['id']}] {a['title']} ({a['url']})\")
        if a.get('tags'):
            print(f\"    Tags: {', '.join(a['tags'])}\")
" "$XREF_FILE"
}

cmd_suggest() {
  if [ -z "${1:-}" ]; then
    echo "ERROR: suggest requires <topic>" >&2
    return 1
  fi
  local topic="$1"
  ensure_xref
  python3 -c "
import json, sys

topic = sys.argv[1].lower()
topic_words = set(topic.split())

with open(sys.argv[2]) as f:
    d = json.load(f)

suggestions = []
for a in d['articles']:
    title_words = set(a['title'].lower().split())
    tag_words = set(t.lower() for t in a.get('tags', []))
    overlap = len(topic_words & (title_words | tag_words))
    if overlap > 0:
        suggestions.append((overlap, a))

suggestions.sort(key=lambda x: -x[0])
if not suggestions:
    print('No related articles to cross-reference.')
else:
    print('Suggested cross-references:')
    for score, a in suggestions[:3]:
        print(f\"  - [{a['title']}]({a['url']})\")
" "$topic" "$XREF_FILE"
}

cmd_remove() {
  if [ -z "${1:-}" ]; then
    echo "ERROR: remove requires <article_id>" >&2
    return 1
  fi
  local article_id="$1"
  ensure_xref
  python3 -c "
import json, sys, os

xref_file = sys.argv[1]
article_id = sys.argv[2]

with open(xref_file) as f:
    d = json.load(f)

before = len(d['articles'])
d['articles'] = [a for a in d['articles'] if a.get('id') != article_id]
after = len(d['articles'])

if before == after:
    print(f'Article {article_id} not found.')
    sys.exit(1)

tmp = xref_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, xref_file)

print(f'Removed article {article_id}')
" "$XREF_FILE" "$article_id"
}

CMD="${1:-}"
shift || true

case "$CMD" in
  add) cmd_add "$@" ;;
  search) cmd_search "$@" ;;
  list) cmd_list ;;
  suggest) cmd_suggest "$@" ;;
  remove) cmd_remove "$@" ;;
  *) usage; exit 1 ;;
esac
