#!/usr/bin/env bash
# Expertise graph — track topic authority based on published articles
# Usage: expertise-graph.sh <command> [args...]
set -euo pipefail

GRAPH_DIR="$HOME/.tech-essay-writer"
GRAPH_FILE="$GRAPH_DIR/expertise-graph.json"

usage() {
  cat <<'EOF'
Usage: expertise-graph.sh <command> [args...]

Commands:
  update <topic> [tags...]    Record an article published on this topic
  query <topic>               Get authority level for a topic
  top [n]                     List top N expertise areas by article count
  suggest                     Suggest topics to write about next
  read                        Dump the full graph
EOF
}

ensure_dir() {
  mkdir -p "$GRAPH_DIR"
}

read_graph() {
  if [ -f "$GRAPH_FILE" ]; then
    cat "$GRAPH_FILE"
  else
    echo '{"topics":{},"tag_index":{},"updated_at":""}'
  fi
}

write_graph() {
  local json_str="$1"
  local tmp="${GRAPH_FILE}.tmp.$$"
  ensure_dir
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$GRAPH_FILE"
}

cmd_update() {
  local topic="$1"
  shift
  local tags="$*"
  local graph
  graph=$(read_graph)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  graph=$(python3 -c "
import json, sys
graph = json.loads(sys.argv[1])
topic = sys.argv[2]
tags = sys.argv[3].split() if sys.argv[3] else []
now = sys.argv[4]

topics = graph.setdefault('topics', {})
tag_index = graph.setdefault('tag_index', {})

if topic in topics:
    topics[topic]['article_count'] += 1
    topics[topic]['last_article'] = now[:10]
    # Merge new tags
    existing_tags = set(topics[topic].get('tags', []))
    existing_tags.update(tags)
    topics[topic]['tags'] = sorted(existing_tags)
else:
    topics[topic] = {
        'article_count': 1,
        'tags': sorted(tags),
        'first_article': now[:10],
        'last_article': now[:10],
        'authority_score': 0
    }

# Recalculate authority score
import datetime
entry = topics[topic]
count = entry['article_count']
last = entry['last_article']
try:
    last_date = datetime.datetime.strptime(last, '%Y-%m-%d')
    days_ago = (datetime.datetime.utcnow() - last_date).days
    if days_ago <= 90:
        recency_bonus = 1.0
    elif days_ago <= 180:
        recency_bonus = 0.5
    else:
        recency_bonus = 0
except:
    recency_bonus = 0
entry['authority_score'] = round(min(10, count * 2 + recency_bonus), 1)

# Update tag index
for tag in tags:
    tag_index.setdefault(tag, [])
    if topic not in tag_index[tag]:
        tag_index[tag].append(topic)

graph['updated_at'] = now
print(json.dumps(graph))
" "$graph" "$topic" "$tags" "$now")

  write_graph "$graph"
  echo "Updated topic: $topic"
}

cmd_query() {
  local topic="$1"
  local graph
  graph=$(read_graph)
  python3 -c "
import json, sys, datetime
graph = json.loads(sys.argv[1])
topic = sys.argv[2]

topics = graph.get('topics', {})
if topic not in topics:
    print(f'No data for topic: {topic}')
    sys.exit(0)

entry = topics[topic]
# Recalculate authority score with current date
count = entry['article_count']
last = entry.get('last_article', '')
try:
    last_date = datetime.datetime.strptime(last, '%Y-%m-%d')
    days_ago = (datetime.datetime.utcnow() - last_date).days
    if days_ago <= 90:
        recency_bonus = 1.0
    elif days_ago <= 180:
        recency_bonus = 0.5
    else:
        recency_bonus = 0
except:
    recency_bonus = 0
score = round(min(10, count * 2 + recency_bonus), 1)

print(f\"Topic: {topic}\")
print(f\"Articles: {count}\")
print(f\"Authority score: {score}/10\")
print(f\"Tags: {', '.join(entry.get('tags', []))}\")
print(f\"First article: {entry.get('first_article', '?')}\")
print(f\"Last article: {entry.get('last_article', '?')}\")
" "$graph" "$topic"
}

cmd_top() {
  local n="${1:-5}"
  local graph
  graph=$(read_graph)
  python3 -c "
import json, sys, datetime
graph = json.loads(sys.argv[1])
n = int(sys.argv[2])

topics = graph.get('topics', {})
if not topics:
    print('No topics tracked yet.')
    sys.exit(0)

# Recalculate all authority scores with current date
scored = []
for name, entry in topics.items():
    count = entry['article_count']
    last = entry.get('last_article', '')
    try:
        last_date = datetime.datetime.strptime(last, '%Y-%m-%d')
        days_ago = (datetime.datetime.utcnow() - last_date).days
        if days_ago <= 90:
            recency_bonus = 1.0
        elif days_ago <= 180:
            recency_bonus = 0.5
        else:
            recency_bonus = 0
    except:
        recency_bonus = 0
    score = round(min(10, count * 2 + recency_bonus), 1)
    scored.append((score, count, name, entry))

scored.sort(key=lambda x: (-x[0], -x[1]))
print(f'Top {min(n, len(scored))} expertise areas:')
for score, count, name, entry in scored[:n]:
    tags_str = ', '.join(entry.get('tags', [])[:3])
    print(f'  {name}: {score}/10 ({count} articles) [{tags_str}]')
" "$graph" "$n"
}

cmd_suggest() {
  local graph
  graph=$(read_graph)

  # Also read author profile expertise if available
  local author_expertise="[]"
  if [ -f "$GRAPH_DIR/author-profile.json" ]; then
    author_expertise=$(python3 -c "
import json
with open('$GRAPH_DIR/author-profile.json') as f:
    d = json.load(f)
print(json.dumps(d.get('expertise_areas', [])))
" 2>/dev/null || echo "[]")
  fi

  python3 -c "
import json, sys, datetime
graph = json.loads(sys.argv[1])
author_expertise = json.loads(sys.argv[2])

topics = graph.get('topics', {})
tag_index = graph.get('tag_index', {})

suggestions = []

# 1. Expertise gaps: topics in author profile but not in graph
for e in author_expertise:
    t = e['topic']
    if t not in topics:
        suggestions.append(('GAP', t, f\"Listed as {e['level']} but no articles written yet\"))
    elif topics[t]['article_count'] < 2:
        suggestions.append(('THIN', t, f\"Only {topics[t]['article_count']} article(s) — build authority\"))

# 2. Stale topics: haven't written about recently
for name, entry in topics.items():
    last = entry.get('last_article', '')
    try:
        last_date = datetime.datetime.strptime(last, '%Y-%m-%d')
        days_ago = (datetime.datetime.utcnow() - last_date).days
        if days_ago > 180 and entry['article_count'] >= 2:
            suggestions.append(('STALE', name, f\"Last article {days_ago} days ago — refresh authority\"))
    except:
        pass

# 3. Adjacent topics: tags that appear in multiple topics suggest bridges
tag_bridges = {}
for tag, topic_list in tag_index.items():
    if len(topic_list) >= 2:
        tag_bridges[tag] = topic_list

if tag_bridges:
    for tag, bridged in tag_bridges.items():
        combined = f\"{bridged[0]}+{bridged[1]}\"
        if combined not in topics:
            suggestions.append(('ADJACENT', f'{bridged[0]} x {bridged[1]}', f\"Bridge via shared tag '{tag}'\"))

if not suggestions:
    print('No specific suggestions. Consider exploring new topic areas.')
else:
    print('Suggested next topics:')
    for kind, topic, reason in suggestions[:5]:
        print(f'  [{kind}] {topic} — {reason}')
" "$graph" "$author_expertise"
}

cmd_read() {
  local graph
  graph=$(read_graph)
  python3 -c "
import json, sys
print(json.dumps(json.loads(sys.argv[1]), indent=2))
" "$graph"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  update) cmd_update "$@" ;;
  query) cmd_query "$@" ;;
  top) cmd_top "$@" ;;
  suggest) cmd_suggest ;;
  read) cmd_read ;;
  *) usage; exit 1 ;;
esac
