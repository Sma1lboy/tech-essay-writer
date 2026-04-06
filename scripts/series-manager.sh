#!/usr/bin/env bash
# Series manager — manages multi-article series with narrative arc and reading order
# Usage: series-manager.sh <command> [args...]
set -euo pipefail

SERIES_DIR="$HOME/.tech-essay-writer"
SERIES_FILE="$SERIES_DIR/series.json"

usage() {
  cat <<'EOF'
Usage: series-manager.sh <command> [args...]

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
  reorder <series_id> <article_id> <new_position> Move article to new position
EOF
}

ensure_series() {
  mkdir -p "$SERIES_DIR"
  if [ ! -f "$SERIES_FILE" ]; then
    echo '{"series":[]}' > "$SERIES_FILE"
  fi
}

cmd_create() {
  local name="$1" description="$2"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
name = sys.argv[2]
description = sys.argv[3]

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
# Use existing IDs to ensure uniqueness
existing_ids = {s['id'] for s in d['series']}
base_id = int(time.time())
series_id = f'ser-{base_id}'
while series_id in existing_ids:
    base_id += 1
    series_id = f'ser-{base_id}'

d['series'].append({
    'id': series_id,
    'name': name,
    'description': description,
    'narrative_arc': '',
    'created_at': now,
    'updated_at': now,
    'articles': []
})

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Created series: {name} ({series_id})')
" "$SERIES_FILE" "$name" "$description"
}

cmd_add() {
  local series_id="$1" article_id="$2" title="$3" position="${4:-}"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
article_id = sys.argv[3]
title = sys.argv[4]
position = sys.argv[5] if sys.argv[5] else ''

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found = False

for s in d['series']:
    if s['id'] == series_id:
        found = True
        articles = s['articles']

        if position:
            pos = int(position)
        else:
            # Auto-position at end
            pos = max((a['position'] for a in articles), default=0) + 1

        articles.append({
            'article_id': article_id,
            'title': title,
            'position': pos,
            'summary': '',
            'added_at': now
        })

        # Sort by position
        s['articles'] = sorted(articles, key=lambda a: a['position'])
        s['updated_at'] = now
        break

if not found:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Added: {title} to {series_id} at position {pos}')
" "$SERIES_FILE" "$series_id" "$article_id" "$title" "$position"
}

cmd_list() {
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

if not d['series']:
    print('No series defined.')
else:
    print(f'Series: {len(d[\"series\"])}')
    for s in d['series']:
        count = len(s.get('articles', []))
        print(f'  [{s[\"id\"]}] {s[\"name\"]} ({count} articles)')
        if s.get('description'):
            print(f'    {s[\"description\"][:80]}')
" "$SERIES_FILE"
}

cmd_show() {
  local series_id="$1"
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

for s in d['series']:
    if s['id'] == sys.argv[2]:
        print(f'Series: {s[\"name\"]}')
        print(f'ID: {s[\"id\"]}')
        print(f'Description: {s.get(\"description\", \"\")}')
        print(f'Narrative arc: {s.get(\"narrative_arc\", \"\")}')
        print(f'Created: {s[\"created_at\"]}')
        print(f'Updated: {s[\"updated_at\"]}')
        articles = sorted(s.get('articles', []), key=lambda a: a['position'])
        print(f'Articles ({len(articles)}):')
        for a in articles:
            summary_str = f' — {a[\"summary\"]}' if a.get('summary') else ''
            print(f'  {a[\"position\"]}. [{a[\"article_id\"]}] {a[\"title\"]}{summary_str}')
        sys.exit(0)

print(f'Series {sys.argv[2]} not found.', file=sys.stderr)
sys.exit(1)
" "$SERIES_FILE" "$series_id"
}

cmd_context() {
  local series_id="$1"
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

for s in d['series']:
    if s['id'] == sys.argv[2]:
        articles = sorted(s.get('articles', []), key=lambda a: a['position'])
        context = {
            'series_name': s['name'],
            'series_description': s.get('description', ''),
            'narrative_arc': s.get('narrative_arc', ''),
            'total_articles': len(articles),
            'articles': [
                {
                    'article_id': a['article_id'],
                    'title': a['title'],
                    'position': a['position'],
                    'summary': a.get('summary', '')
                }
                for a in articles
            ]
        }
        print(json.dumps(context, indent=2))
        sys.exit(0)

print(json.dumps({'error': f'Series {sys.argv[2]} not found'}))
sys.exit(1)
" "$SERIES_FILE" "$series_id"
}

cmd_set_arc() {
  local series_id="$1" arc_description="$2"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
arc_desc = sys.argv[3]

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found = False

for s in d['series']:
    if s['id'] == series_id:
        found = True
        s['narrative_arc'] = arc_desc
        s['updated_at'] = now
        break

if not found:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Set arc for {series_id}')
" "$SERIES_FILE" "$series_id" "$arc_description"
}

cmd_set_summary() {
  local series_id="$1" article_id="$2" summary="$3"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
article_id = sys.argv[3]
summary = sys.argv[4]

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found_series = False
found_article = False

for s in d['series']:
    if s['id'] == series_id:
        found_series = True
        for a in s['articles']:
            if a['article_id'] == article_id:
                found_article = True
                a['summary'] = summary
                break
        s['updated_at'] = now
        break

if not found_series:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)
if not found_article:
    print(f'Article {article_id} not found in series {series_id}.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Set summary for {article_id} in {series_id}')
" "$SERIES_FILE" "$series_id" "$article_id" "$summary"
}

cmd_next_position() {
  local series_id="$1"
  ensure_series
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

for s in d['series']:
    if s['id'] == sys.argv[2]:
        articles = s.get('articles', [])
        pos = max((a['position'] for a in articles), default=0) + 1
        print(pos)
        sys.exit(0)

print(f'Series {sys.argv[2]} not found.', file=sys.stderr)
sys.exit(1)
" "$SERIES_FILE" "$series_id"
}

cmd_search() {
  local query="$1"
  ensure_series
  python3 -c "
import json, sys

query = sys.argv[1].lower()
with open(sys.argv[2]) as f:
    d = json.load(f)

results = []
for s in d['series']:
    score = 0
    if query in s['name'].lower():
        score += 2
    if query in s.get('description', '').lower():
        score += 1
    if query in s.get('narrative_arc', '').lower():
        score += 1
    if score > 0:
        results.append((score, s))

results.sort(key=lambda x: -x[0])
if not results:
    print('No matching series found.')
else:
    for score, s in results:
        count = len(s.get('articles', []))
        print(f'  [{s[\"id\"]}] {s[\"name\"]} ({count} articles)')
        if s.get('description'):
            print(f'    {s[\"description\"][:80]}')
" "$query" "$SERIES_FILE"
}

cmd_reorder() {
  local series_id="$1" article_id="$2" new_position="$3"
  ensure_series
  python3 -c "
import json, sys, os, time

series_file = sys.argv[1]
series_id = sys.argv[2]
article_id = sys.argv[3]
new_pos = int(sys.argv[4])

with open(series_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
found_series = False
found_article = False

for s in d['series']:
    if s['id'] == series_id:
        found_series = True
        # Find the article and remove it
        target = None
        others = []
        for a in s['articles']:
            if a['article_id'] == article_id:
                found_article = True
                target = a
            else:
                others.append(a)

        if not found_article:
            print(f'Article {article_id} not found in series {series_id}.', file=sys.stderr)
            sys.exit(1)

        # Set the new position
        target['position'] = new_pos

        # Rebuild: insert target at new_pos, renumber others
        others = sorted(others, key=lambda a: a['position'])
        result = []
        inserted = False
        pos = 1
        for a in others:
            if pos == new_pos and not inserted:
                result.append(target)
                target['position'] = pos
                pos += 1
                inserted = True
            a['position'] = pos
            result.append(a)
            pos += 1

        if not inserted:
            target['position'] = pos
            result.append(target)

        s['articles'] = result
        s['updated_at'] = now
        break

if not found_series:
    print(f'Series {series_id} not found.', file=sys.stderr)
    sys.exit(1)

tmp = series_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, series_file)

print(f'Reordered {article_id} to position {new_pos} in {series_id}')
" "$SERIES_FILE" "$series_id" "$article_id" "$new_position"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  create) cmd_create "$@" ;;
  add) cmd_add "$@" ;;
  list) cmd_list ;;
  show) cmd_show "$@" ;;
  context) cmd_context "$@" ;;
  set-arc) cmd_set_arc "$@" ;;
  set-summary) cmd_set_summary "$@" ;;
  next-position) cmd_next_position "$@" ;;
  search) cmd_search "$@" ;;
  reorder) cmd_reorder "$@" ;;
  *) usage; exit 1 ;;
esac
