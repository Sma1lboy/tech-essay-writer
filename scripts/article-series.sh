#!/usr/bin/env bash
# Article series management — multi-article series with reading order and narrative arc
# Usage: article-series.sh <command> [args...]
set -euo pipefail

SERIES_DIR="$HOME/.tech-essay-writer"
SERIES_FILE="$SERIES_DIR/article-series.json"

usage() {
  cat <<'EOF'
Usage: article-series.sh <command> [args...]

Commands:
  create-series <title> <description> [arc_type]  Create a new series (arc_type: progressive|comparative|exploratory)
  add-to-series <series_id> <article_id> [role] [synopsis]  Add article to series
  list-series                                    List all series
  get-series <series_id>                         Get series details as JSON
  get-reading-order <series_id>                  Get ordered article list for a series
  update-arc <series_id> <arc_json>              Update narrative arc metadata (JSON string)
  remove-from-series <series_id> <article_id>    Remove article from a series
  series-suggest <topic> [tags...]               Suggest which series a new article belongs to
EOF
}

ensure_series() {
  mkdir -p "$SERIES_DIR"
  if [ ! -f "$SERIES_FILE" ]; then
    echo '{"series":[]}' > "$SERIES_FILE"
  fi
}

cmd_create_series() {
  local title="$1" description="$2" arc_type="${3:-progressive}"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
title = sys.argv[2]
description = sys.argv[3]
arc_type = sys.argv[4]

if arc_type not in ('progressive', 'comparative', 'exploratory'):
    print(f'ERROR: Invalid arc type: {arc_type}. Use progressive|comparative|exploratory', file=sys.stderr)
    sys.exit(1)

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
series_id = f'series-{int(time.time())}'

d['series'].append({
    'id': series_id,
    'title': title,
    'description': description,
    'narrative_arc': {
        'type': arc_type,
        'theme': '',
        'progression': ''
    },
    'articles': [],
    'status': 'in-progress',
    'created_at': now,
    'updated_at': now,
    'tags': []
})

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Created series: {title} ({series_id})')
" "$SERIES_FILE" "$title" "$description" "$arc_type"
}

cmd_add_to_series() {
  local series_id="$1" article_id="$2" role="${3:-}" synopsis="${4:-}"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
article_id = sys.argv[3]
role = sys.argv[4] if sys.argv[4] else 'continuation'
synopsis = sys.argv[5] if sys.argv[5] else ''

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found = False

for s in d['series']:
    if s['id'] == series_id:
        found = True
        # Check for duplicate
        existing_ids = [a['article_id'] for a in s['articles']]
        if article_id in existing_ids:
            print(f'Article {article_id} already in series {series_id}')
            sys.exit(0)
        # Assign next order number
        max_order = max((a['order'] for a in s['articles']), default=0)
        s['articles'].append({
            'article_id': article_id,
            'order': max_order + 1,
            'role': role,
            'synopsis': synopsis
        })
        s['updated_at'] = now
        break

if not found:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Added {article_id} to {series_id} (order: {max_order + 1})')
" "$SERIES_FILE" "$series_id" "$article_id" "$role" "$synopsis"
}

cmd_list_series() {
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

if not d['series']:
    print('No series defined.')
else:
    print(f'Article series: {len(d[\"series\"])}')
    for s in d['series']:
        count = len(s.get('articles', []))
        arc = s.get('narrative_arc', {}).get('type', '?')
        print(f'  [{s[\"id\"]}] {s[\"title\"]} ({count} articles, {arc}, {s.get(\"status\", \"?\")})')
        if s.get('description'):
            print(f'    {s[\"description\"][:80]}')
" "$SERIES_FILE"
}

cmd_get_series() {
  local series_id="$1"
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

for s in d['series']:
    if s['id'] == sys.argv[2]:
        print(json.dumps(s, indent=2))
        sys.exit(0)

print(f'Series {sys.argv[2]} not found.', file=sys.stderr)
sys.exit(1)
" "$SERIES_FILE" "$series_id"
}

cmd_get_reading_order() {
  local series_id="$1"
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

for s in d['series']:
    if s['id'] == sys.argv[2]:
        articles = sorted(s.get('articles', []), key=lambda a: a.get('order', 0))
        print(f'Reading order for: {s[\"title\"]}')
        if not articles:
            print('  (no articles yet)')
        for a in articles:
            print(f'  {a[\"order\"]}. [{a[\"article_id\"]}] ({a.get(\"role\", \"?\")})')
            if a.get('synopsis'):
                print(f'     {a[\"synopsis\"][:80]}')
        # Output JSON to stdout for machine consumption
        print()
        print(json.dumps({'series_id': s['id'], 'title': s['title'], 'articles': articles}, indent=2))
        sys.exit(0)

print(f'Series {sys.argv[2]} not found.', file=sys.stderr)
sys.exit(1)
" "$SERIES_FILE" "$series_id"
}

cmd_update_arc() {
  local series_id="$1" arc_json="$2"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
arc_json = sys.argv[3]

try:
    arc = json.loads(arc_json)
except json.JSONDecodeError:
    print('ERROR: Invalid JSON for arc metadata', file=sys.stderr)
    sys.exit(1)

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found = False

for s in d['series']:
    if s['id'] == series_id:
        found = True
        existing_arc = s.get('narrative_arc', {})
        # Merge: only update keys present in arc_json
        for k, v in arc.items():
            existing_arc[k] = v
        s['narrative_arc'] = existing_arc
        s['updated_at'] = now
        # Also update tags if provided
        if 'tags' in arc:
            s['tags'] = arc['tags']
        break

if not found:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Updated arc for {series_id}')
" "$SERIES_FILE" "$series_id" "$arc_json"
}

cmd_remove_from_series() {
  local series_id="$1" article_id="$2"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
article_id = sys.argv[3]

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found_series = False
removed = False

for s in d['series']:
    if s['id'] == series_id:
        found_series = True
        before = len(s['articles'])
        s['articles'] = [a for a in s['articles'] if a['article_id'] != article_id]
        after = len(s['articles'])
        if before > after:
            removed = True
            # Renumber remaining articles
            for i, a in enumerate(sorted(s['articles'], key=lambda x: x['order']), 1):
                a['order'] = i
            s['updated_at'] = now
        break

if not found_series:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

if not removed:
    print(f'Article {article_id} not found in series {series_id}.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Removed {article_id} from {series_id}')
" "$SERIES_FILE" "$series_id" "$article_id"
}

cmd_series_suggest() {
  local topic="$1"
  shift
  local tags="$*"
  ensure_series
  python3 -c "
import json, sys

topic = sys.argv[1].lower()
tags = sys.argv[2].lower().split() if sys.argv[2] else []
topic_words = set(topic.split()) | set(tags)

with open(sys.argv[3]) as f:
    d = json.load(f)

if not d['series']:
    print('No series available for suggestion.')
    sys.exit(0)

scored = []
for s in d['series']:
    score = 0
    # Match against series title
    title_words = set(s['title'].lower().split())
    score += len(topic_words & title_words) * 2

    # Match against description
    desc_words = set(s.get('description', '').lower().split())
    score += len(topic_words & desc_words)

    # Match against series tags
    series_tags = set(t.lower() for t in s.get('tags', []))
    score += len(topic_words & series_tags) * 3

    # Match against narrative arc theme
    theme_words = set(s.get('narrative_arc', {}).get('theme', '').lower().split())
    score += len(topic_words & theme_words) * 2

    # Match against existing article synopses
    for a in s.get('articles', []):
        syn_words = set(a.get('synopsis', '').lower().split())
        score += len(topic_words & syn_words)

    # Bonus for in-progress series (they need more articles)
    if s.get('status') == 'in-progress':
        score += 1

    if score > 0:
        scored.append((score, s))

scored.sort(key=lambda x: -x[0])

if not scored:
    print('No matching series found. Consider creating a new series.')
else:
    print('Suggested series:')
    for score, s in scored[:3]:
        count = len(s.get('articles', []))
        print(f'  [{s[\"id\"]}] {s[\"title\"]} (score: {score}, {count} articles, {s.get(\"status\", \"?\")})')
        if s.get('description'):
            print(f'    {s[\"description\"][:80]}')
" "$topic" "$tags" "$SERIES_FILE"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  create-series) cmd_create_series "$@" ;;
  add-to-series) cmd_add_to_series "$@" ;;
  list-series) cmd_list_series ;;
  get-series) cmd_get_series "$@" ;;
  get-reading-order) cmd_get_reading_order "$@" ;;
  update-arc) cmd_update_arc "$@" ;;
  remove-from-series) cmd_remove_from_series "$@" ;;
  series-suggest) cmd_series_suggest "$@" ;;
  *) usage; exit 1 ;;
esac
