#!/usr/bin/env bash
# Analytics feedback loop — track article performance and feed insights into taste memory
# Usage: analytics-feedback.sh <command> [args...]
set -euo pipefail

ANALYTICS_DIR="$HOME/.tech-essay-writer"
ANALYTICS_FILE="$ANALYTICS_DIR/analytics.json"
TASTE_FILE="$ANALYTICS_DIR/taste-memory.json"
XREF_FILE="$ANALYTICS_DIR/published-articles.json"

VALID_METRICS="views shares comments likes bookmarks read_time_avg bounce_rate"

usage() {
  cat <<'EOF'
Usage: analytics-feedback.sh <command> [args...]

Commands:
  record <article_id> <metric> <value>         Record a performance metric
  record-batch <article_id> <json_metrics>     Record multiple metrics from JSON
  query <article_id>                           Show all metrics for an article
  top [metric] [n]                             Top N articles by metric (default: views, 5)
  trends                                       Show performance trends
  feed-taste <project_dir>                     Analyze and update taste memory with insights
  summary                                      Human-readable analytics summary
  compare <article_id_1> <article_id_2>        Compare metrics between two articles
EOF
}

ensure_analytics() {
  mkdir -p "$ANALYTICS_DIR"
  if [ ! -f "$ANALYTICS_FILE" ]; then
    python3 -c "
import json, sys, time
d = {
    'articles': {},
    'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
}
with open(sys.argv[1], 'w') as f:
    json.dump(d, f, indent=2)
" "$ANALYTICS_FILE"
  fi
}

validate_metric() {
  local metric="$1"
  if ! echo "$VALID_METRICS" | grep -qw "$metric"; then
    echo "ERROR: Invalid metric '$metric'. Valid: $VALID_METRICS" >&2
    return 1
  fi
}

cmd_record() {
  if [ $# -lt 3 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
    echo "ERROR: record requires <article_id> <metric> <value>" >&2
    return 1
  fi
  local article_id="$1" metric="$2" value="$3"
  validate_metric "$metric"
  ensure_analytics
  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
article_id = sys.argv[2]
metric = sys.argv[3]
raw = float(sys.argv[4])
value = int(raw) if raw == int(raw) else raw

with open(analytics_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

if article_id not in d['articles']:
    d['articles'][article_id] = {
        'metrics': {},
        'first_recorded': now,
        'last_updated': now
    }

d['articles'][article_id]['metrics'][metric] = value
d['articles'][article_id]['last_updated'] = now
d['updated_at'] = now

tmp = analytics_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, analytics_file)

print(f'Recorded {metric}={value} for {article_id}')
" "$ANALYTICS_FILE" "$article_id" "$metric" "$value"
}

cmd_record_batch() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: record-batch requires <article_id> <json_metrics>" >&2
    return 1
  fi
  local article_id="$1" json_metrics="$2"
  ensure_analytics
  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
article_id = sys.argv[2]
metrics_str = sys.argv[3]

valid = set('views shares comments likes bookmarks read_time_avg bounce_rate'.split())

try:
    metrics = json.loads(metrics_str)
except json.JSONDecodeError:
    print('ERROR: Invalid JSON for metrics', file=sys.stderr)
    sys.exit(1)

# Validate all metric names
for k in metrics:
    if k not in valid:
        print(f'ERROR: Invalid metric \"{k}\". Valid: {\" \".join(sorted(valid))}', file=sys.stderr)
        sys.exit(1)

with open(analytics_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

if article_id not in d['articles']:
    d['articles'][article_id] = {
        'metrics': {},
        'first_recorded': now,
        'last_updated': now
    }

for k, v in metrics.items():
    fv = float(v)
    d['articles'][article_id]['metrics'][k] = int(fv) if fv == int(fv) else fv

d['articles'][article_id]['last_updated'] = now
d['updated_at'] = now

tmp = analytics_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, analytics_file)

print(f'Recorded {len(metrics)} metrics for {article_id}')
" "$ANALYTICS_FILE" "$article_id" "$json_metrics"
}

cmd_query() {
  if [ -z "${1:-}" ]; then
    echo "ERROR: query requires <article_id>" >&2
    return 1
  fi
  local article_id="$1"
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

article_id = sys.argv[2]
entry = d.get('articles', {}).get(article_id)

if not entry:
    print(f'No metrics found for {article_id}', file=sys.stderr)
    sys.exit(1)

print(json.dumps(entry, indent=2))
" "$ANALYTICS_FILE" "$article_id"
}

cmd_top() {
  local metric="${1:-views}" n="${2:-5}"
  validate_metric "$metric"
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

metric = sys.argv[2]
n = int(sys.argv[3])

scored = []
for aid, entry in d['articles'].items():
    val = entry['metrics'].get(metric, 0)
    scored.append((val, aid))

scored.sort(key=lambda x: -x[0])

if not scored:
    print('No analytics data yet.')
else:
    print(f'Top {min(n, len(scored))} articles by {metric}:')
    for val, aid in scored[:n]:
        print(f'  {aid}: {val}')
" "$ANALYTICS_FILE" "$metric" "$n"
}

cmd_trends() {
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

articles = d.get('articles', {})
if not articles:
    print('No analytics data recorded yet.')
    sys.exit(0)

n = len(articles)
all_metrics = {}
for aid, entry in articles.items():
    for k, v in entry.get('metrics', {}).items():
        all_metrics.setdefault(k, []).append(v)

result = {'total_articles': n, 'metrics_summary': {}}
for metric, values in all_metrics.items():
    avg = sum(values) / len(values) if values else 0
    result['metrics_summary'][metric] = {
        'average': round(avg, 2),
        'min': min(values),
        'max': max(values),
        'count': len(values)
    }

# Simple trend: compare first half vs second half by last_updated
entries = [(aid, e) for aid, e in articles.items()]
entries.sort(key=lambda x: x[1].get('last_updated', ''))

if n >= 4:
    mid = n // 2
    first_half = entries[:mid]
    second_half = entries[mid:]
    trends = {}
    for metric in all_metrics:
        first_avg = sum(e.get('metrics', {}).get(metric, 0) for _, e in first_half) / len(first_half)
        second_avg = sum(e.get('metrics', {}).get(metric, 0) for _, e in second_half) / len(second_half)
        if first_avg > 0:
            change = ((second_avg - first_avg) / first_avg) * 100
            direction = 'improving' if change > 5 else ('declining' if change < -5 else 'stable')
            trends[metric] = {'direction': direction, 'change_pct': round(change, 1)}
        else:
            trends[metric] = {'direction': 'new', 'change_pct': 0}
    result['trends'] = trends

print(json.dumps(result, indent=2))
" "$ANALYTICS_FILE"
}

cmd_feed_taste() {
  if [ -z "${1:-}" ]; then
    echo "ERROR: feed-taste requires <project_dir>" >&2
    return 1
  fi
  local project_dir="$1"
  ensure_analytics

  # Ensure taste file exists
  if [ ! -f "$TASTE_FILE" ]; then
    echo '{}' > "$TASTE_FILE"
  fi

  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
taste_file = sys.argv[2]
xref_file = sys.argv[3]

with open(analytics_file) as f:
    analytics = json.load(f)

with open(taste_file) as f:
    taste = json.load(f)

# Load published articles for metadata correlation
xref = {'articles': []}
if os.path.exists(xref_file):
    with open(xref_file) as f:
        xref = json.load(f)

articles = analytics.get('articles', {})
if not articles:
    print('No analytics data to analyze.')
    sys.exit(0)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

# Build article metadata map from cross-references
meta_map = {}
for a in xref.get('articles', []):
    meta_map[a['id']] = a

# Calculate averages
total_views = 0
total_shares = 0
count = 0
tag_performance = {}
top_article = None
top_views = 0

for aid, entry in articles.items():
    metrics = entry.get('metrics', {})
    views = metrics.get('views', 0)
    shares = metrics.get('shares', 0)
    total_views += views
    total_shares += shares
    count += 1

    if views > top_views:
        top_views = views
        meta = meta_map.get(aid, {})
        top_article = {
            'id': aid,
            'title': meta.get('title', aid),
            'views': views
        }

    # Correlate with tags if available
    meta = meta_map.get(aid, {})
    for tag in meta.get('tags', []):
        tag_performance.setdefault(tag, {'total_views': 0, 'total_shares': 0, 'count': 0})
        tag_performance[tag]['total_views'] += views
        tag_performance[tag]['total_shares'] += shares
        tag_performance[tag]['count'] += 1

# Find best performing tags
best_tags = sorted(
    tag_performance.items(),
    key=lambda x: x[1]['total_views'] / max(x[1]['count'], 1),
    reverse=True
)[:5]

# Generate insights
insights = []
avg_views = total_views / max(count, 1)
avg_shares = total_shares / max(count, 1)

if best_tags:
    top_tag = best_tags[0]
    tag_avg = top_tag[1]['total_views'] / max(top_tag[1]['count'], 1)
    if tag_avg > avg_views * 1.2:
        pct = int((tag_avg / max(avg_views, 1) - 1) * 100)
        insights.append(f'Articles tagged \"{top_tag[0]}\" average {pct}% more views')

# Determine best performing format from taste memory topics
topics = taste.get('topics_written', [])
variant_perf = {}
for t in topics:
    variant = t.get('variant')
    topic_name = t.get('topic', '')
    if variant:
        variant_perf.setdefault(variant, {'count': 0, 'total_views': 0})
        for aid, entry in articles.items():
            meta = meta_map.get(aid, {})
            if topic_name.lower() in meta.get('title', '').lower():
                variant_perf[variant]['total_views'] += entry.get('metrics', {}).get('views', 0)
                variant_perf[variant]['count'] += 1

best_format = None
best_format_avg = 0
for v, perf in variant_perf.items():
    if perf['count'] > 0:
        v_avg = perf['total_views'] / perf['count']
        if v_avg > best_format_avg:
            best_format_avg = v_avg
            best_format = v

if best_format and best_format_avg > avg_views:
    insights.append(f'{best_format}-style articles perform above average')

performance_insights = {
    'best_performing_tags': [t[0] for t in best_tags],
    'best_performing_format': best_format or 'unknown',
    'avg_views': round(avg_views, 1),
    'avg_shares': round(avg_shares, 1),
    'top_article': top_article,
    'insights': insights,
    'updated_at': now
}

taste['performance_insights'] = performance_insights

tmp = taste_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(taste, f, indent=2)
os.rename(tmp, taste_file)

print('Performance insights updated in taste memory.')
print(f'  Articles analyzed: {count}')
print(f'  Avg views: {avg_views:.0f}')
print(f'  Avg shares: {avg_shares:.0f}')
if insights:
    print('  Insights:')
    for i in insights:
        print(f'    - {i}')
" "$ANALYTICS_FILE" "$TASTE_FILE" "$XREF_FILE"
}

cmd_summary() {
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

articles = d.get('articles', {})
if not articles:
    print('No analytics data yet.')
    sys.exit(0)

print(f'Analytics Summary ({len(articles)} articles)')
print(f'Last updated: {d.get(\"updated_at\", \"?\")}')
print()

# Aggregate stats
all_metrics = {}
for aid, entry in articles.items():
    for k, v in entry.get('metrics', {}).items():
        all_metrics.setdefault(k, []).append(v)

for metric, values in sorted(all_metrics.items()):
    avg = sum(values) / len(values)
    total = sum(values)
    print(f'{metric}:')
    print(f'  Total: {total:.1f}  Avg: {avg:.1f}  Min: {min(values):.1f}  Max: {max(values):.1f}')
" "$ANALYTICS_FILE"
}

cmd_compare() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: compare requires <article_id_1> <article_id_2>" >&2
    return 1
  fi
  local id1="$1" id2="$2"
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

id1 = sys.argv[2]
id2 = sys.argv[3]

a1 = d['articles'].get(id1)
a2 = d['articles'].get(id2)

if not a1:
    print(f'No data for article: {id1}')
    sys.exit(0)
if not a2:
    print(f'No data for article: {id2}')
    sys.exit(0)

m1 = a1.get('metrics', {})
m2 = a2.get('metrics', {})
all_keys = sorted(set(list(m1.keys()) + list(m2.keys())))

print(f'Comparison: {id1} vs {id2}')
print(f'{\"Metric\":<16} {id1:<12} {id2:<12} Diff')
print('-' * 52)
for k in all_keys:
    v1 = m1.get(k, 0)
    v2 = m2.get(k, 0)
    diff = v2 - v1
    sign = '+' if diff > 0 else ''
    print(f'{k:<16} {v1:<12.1f} {v2:<12.1f} {sign}{diff:.1f}')
" "$ANALYTICS_FILE" "$id1" "$id2"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  record) cmd_record "$@" ;;
  record-batch) cmd_record_batch "$@" ;;
  query) cmd_query "$@" ;;
  top) cmd_top "$@" ;;
  trends) cmd_trends ;;
  feed-taste) cmd_feed_taste "$@" ;;
  summary) cmd_summary ;;
  compare) cmd_compare "$@" ;;
  *) usage; exit 1 ;;
esac
