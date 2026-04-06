#!/usr/bin/env bash
# Analytics feedback loop — record performance metrics, analyze patterns, feed into taste memory
# Usage: analytics-feedback.sh <command> [args...]
set -euo pipefail

ANALYTICS_DIR="$HOME/.tech-essay-writer"
ANALYTICS_FILE="$ANALYTICS_DIR/analytics-data.json"
TASTE_FILE="$ANALYTICS_DIR/taste-memory.json"

usage() {
  cat <<'EOF'
Usage: analytics-feedback.sh <command> [args...]

Commands:
  record-metrics <article_id> <metrics_json>  Record performance metrics for an article
  get-metrics <article_id>                    Get metrics for a specific article
  trends                                      Show aggregate performance trends
  top-performers [metric] [count]             Best articles by metric (views|shares|comments|completion_rate, default: views, top 5)
  feed-taste                                  Analyze top performers and update taste memory
  reset                                       Clear all analytics data
EOF
}

ensure_analytics() {
  mkdir -p "$ANALYTICS_DIR"
  if [ ! -f "$ANALYTICS_FILE" ]; then
    printf '{"metrics":{},"updated_at":""}' > "$ANALYTICS_FILE"
  fi
}

cmd_record_metrics() {
  local article_id="$1" metrics_json="$2"
  ensure_analytics
  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
article_id = sys.argv[2]
metrics_json_str = sys.argv[3]

try:
    metrics = json.loads(metrics_json_str)
except json.JSONDecodeError:
    print('ERROR: Invalid JSON for metrics', file=sys.stderr)
    sys.exit(1)

with open(analytics_file) as f:
    d = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

# Build metrics entry — merge with existing if present
existing = d['metrics'].get(article_id, {})
entry = {
    'article_id': article_id,
    'title': metrics.get('title', existing.get('title', '')),
    'published_at': metrics.get('published_at', existing.get('published_at', '')),
    'recorded_at': now,
    'views': metrics.get('views', existing.get('views', 0)),
    'shares': metrics.get('shares', existing.get('shares', 0)),
    'comments': metrics.get('comments', existing.get('comments', 0)),
    'avg_read_time_seconds': metrics.get('avg_read_time_seconds', existing.get('avg_read_time_seconds', 0)),
    'completion_rate': metrics.get('completion_rate', existing.get('completion_rate', 0)),
    'platforms': metrics.get('platforms', existing.get('platforms', {})),
    'tags': metrics.get('tags', existing.get('tags', [])),
    'variant_used': metrics.get('variant_used', existing.get('variant_used', '')),
    'quality_score': metrics.get('quality_score', existing.get('quality_score', 0)),
    'refinement_rounds': metrics.get('refinement_rounds', existing.get('refinement_rounds', 0))
}

d['metrics'][article_id] = entry
d['updated_at'] = now

tmp = analytics_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, analytics_file)

print(f'Recorded metrics for {article_id}')
" "$ANALYTICS_FILE" "$article_id" "$metrics_json"
}

cmd_get_metrics() {
  local article_id="$1"
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

article_id = sys.argv[2]
entry = d['metrics'].get(article_id)

if not entry:
    print(f'No metrics found for {article_id}', file=sys.stderr)
    sys.exit(1)

print(json.dumps(entry, indent=2))
" "$ANALYTICS_FILE" "$article_id"
}

cmd_trends() {
  ensure_analytics
  python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

metrics = d.get('metrics', {})
if not metrics:
    print('No analytics data recorded yet.')
    sys.exit(0)

entries = list(metrics.values())
n = len(entries)

total_views = sum(e.get('views', 0) for e in entries)
total_shares = sum(e.get('shares', 0) for e in entries)
total_comments = sum(e.get('comments', 0) for e in entries)
avg_completion = sum(e.get('completion_rate', 0) for e in entries) / n if n else 0
avg_read_time = sum(e.get('avg_read_time_seconds', 0) for e in entries) / n if n else 0
avg_quality = sum(e.get('quality_score', 0) for e in entries) / n if n else 0

# Variant distribution
variant_counts = {}
for e in entries:
    v = e.get('variant_used', 'unknown')
    if v:
        variant_counts[v] = variant_counts.get(v, 0) + 1

# Tag frequency
tag_counts = {}
for e in entries:
    for t in e.get('tags', []):
        tag_counts[t] = tag_counts.get(t, 0) + 1

# Platform breakdown
platform_views = {}
for e in entries:
    for pname, pdata in e.get('platforms', {}).items():
        platform_views[pname] = platform_views.get(pname, 0) + pdata.get('views', 0)

# Output
result = {
    'total_articles': n,
    'total_views': total_views,
    'total_shares': total_shares,
    'total_comments': total_comments,
    'avg_views_per_article': round(total_views / n, 1) if n else 0,
    'avg_shares_per_article': round(total_shares / n, 1) if n else 0,
    'avg_completion_rate': round(avg_completion, 3),
    'avg_read_time_seconds': round(avg_read_time, 1),
    'avg_quality_score': round(avg_quality, 2),
    'variant_distribution': variant_counts,
    'top_tags': dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:10]),
    'platform_views': platform_views
}

print(json.dumps(result, indent=2))
" "$ANALYTICS_FILE"
}

cmd_top_performers() {
  local metric="${1:-views}" count="${2:-5}"
  ensure_analytics
  python3 -c "
import json, sys

metric = sys.argv[2]
count = int(sys.argv[3])

valid_metrics = ['views', 'shares', 'comments', 'completion_rate', 'quality_score', 'avg_read_time_seconds']
if metric not in valid_metrics:
    print(f'ERROR: Invalid metric. Use: {\"|\".join(valid_metrics)}', file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1]) as f:
    d = json.load(f)

entries = list(d.get('metrics', {}).values())
if not entries:
    print('No analytics data recorded yet.')
    sys.exit(0)

# Sort by metric descending
entries.sort(key=lambda e: e.get(metric, 0), reverse=True)
top = entries[:count]

print(f'Top {len(top)} by {metric}:')
for i, e in enumerate(top, 1):
    val = e.get(metric, 0)
    title = e.get('title', e.get('article_id', '?'))
    print(f'  {i}. [{e[\"article_id\"]}] {title} — {metric}: {val}')

# Also output JSON
print()
print(json.dumps([{
    'article_id': e['article_id'],
    'title': e.get('title', ''),
    metric: e.get(metric, 0),
    'variant_used': e.get('variant_used', ''),
    'tags': e.get('tags', []),
    'quality_score': e.get('quality_score', 0),
    'refinement_rounds': e.get('refinement_rounds', 0)
} for e in top], indent=2))
" "$ANALYTICS_FILE" "$metric" "$count"
}

cmd_feed_taste() {
  ensure_analytics
  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
taste_file = sys.argv[2]

with open(analytics_file) as f:
    analytics = json.load(f)

entries = list(analytics.get('metrics', {}).values())
if not entries:
    print('No analytics data to analyze.')
    sys.exit(0)

# Load taste memory
taste = {}
if os.path.exists(taste_file):
    with open(taste_file) as f:
        taste = json.load(f)

now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

# --- Find top 25% by composite score (views + shares*10) ---
for e in entries:
    e['_composite'] = e.get('views', 0) + e.get('shares', 0) * 10

entries_sorted = sorted(entries, key=lambda e: e['_composite'], reverse=True)
cutoff_idx = max(1, len(entries_sorted) // 4)
top_performers = entries_sorted[:cutoff_idx]
top_ids = set(e['article_id'] for e in top_performers)

# --- Extract patterns from top performers ---

# Variant preference
variant_counts = {}
for e in top_performers:
    v = e.get('variant_used', '')
    if v:
        variant_counts[v] = variant_counts.get(v, 0) + 1
best_variant = max(variant_counts, key=variant_counts.get) if variant_counts else None

# Top tags
tag_scores = {}
for e in top_performers:
    for t in e.get('tags', []):
        tag_scores[t] = tag_scores.get(t, 0) + e['_composite']
top_tags = sorted(tag_scores, key=tag_scores.get, reverse=True)[:10]

# Quality score stats
quality_scores = [e.get('quality_score', 0) for e in top_performers if e.get('quality_score', 0) > 0]
avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

# Refinement round stats
refinements = [e.get('refinement_rounds', 0) for e in top_performers if e.get('refinement_rounds', 0) > 0]
avg_refinements = sum(refinements) / len(refinements) if refinements else 0

# Read time signals (article length proxy)
read_times = [e.get('avg_read_time_seconds', 0) for e in top_performers if e.get('avg_read_time_seconds', 0) > 0]
avg_read_time = sum(read_times) / len(read_times) if read_times else 0

# Completion rate stats
completions = [e.get('completion_rate', 0) for e in top_performers if e.get('completion_rate', 0) > 0]
avg_completion = sum(completions) / len(completions) if completions else 0

# --- Update taste memory (idempotent) ---

# Initialize analytics-derived section
taste.setdefault('analytics_derived', {})
ad = taste['analytics_derived']

ad['last_analyzed_at'] = now
ad['articles_analyzed'] = len(entries)
ad['top_performer_count'] = len(top_performers)
ad['top_performer_ids'] = list(top_ids)

if best_variant:
    ad['best_performing_variant'] = best_variant
    # Also set as preferred variant if it has enough data
    if variant_counts.get(best_variant, 0) >= 2:
        taste['preferred_variant'] = best_variant

ad['successful_tags'] = top_tags
ad['avg_top_quality_score'] = round(avg_quality, 2)
ad['avg_top_refinement_rounds'] = round(avg_refinements, 1)
ad['optimal_read_time_seconds'] = round(avg_read_time, 1)
ad['avg_top_completion_rate'] = round(avg_completion, 3)

# Feed structural preferences
taste.setdefault('structural_preferences', {})
if avg_read_time > 0:
    minutes = round(avg_read_time / 60, 1)
    taste['structural_preferences']['optimal_read_time_minutes'] = minutes
if avg_completion > 0:
    taste['structural_preferences']['target_completion_rate'] = round(avg_completion, 2)

# Record as feedback pattern (idempotent — replace analytics line)
taste.setdefault('feedback_patterns', [])
analytics_pattern = f'Analytics: top performers use variant={best_variant or \"?\"}, tags={top_tags[:3]}, avg_quality={round(avg_quality,1)}'
taste['feedback_patterns'] = [p for p in taste['feedback_patterns'] if not p.startswith('Analytics:')]
taste['feedback_patterns'].append(analytics_pattern)
taste['feedback_patterns'] = taste['feedback_patterns'][-20:]

taste['updated_at'] = now

# Write atomically
tmp = taste_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(taste, f, indent=2)
os.rename(tmp, taste_file)

# Output summary
print(f'Analyzed {len(entries)} articles, {len(top_performers)} top performers')
print(f'Best variant: {best_variant or \"(none)\"}')
print(f'Successful tags: {\", \".join(top_tags[:5]) if top_tags else \"(none)\"}')
print(f'Avg quality (top): {round(avg_quality, 1)}')
print(f'Avg read time (top): {round(avg_read_time/60, 1) if avg_read_time else 0} min')
print(f'Taste memory updated.')
" "$ANALYTICS_FILE" "$TASTE_FILE"
}

cmd_reset() {
  ensure_analytics
  python3 -c "
import json, sys, os, time

analytics_file = sys.argv[1]
now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
d = {'metrics': {}, 'updated_at': now}
tmp = analytics_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, analytics_file)
print('Analytics data reset.')
" "$ANALYTICS_FILE"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  record-metrics) cmd_record_metrics "$@" ;;
  get-metrics) cmd_get_metrics "$@" ;;
  trends) cmd_trends ;;
  top-performers) cmd_top_performers "$@" ;;
  feed-taste) cmd_feed_taste ;;
  reset) cmd_reset ;;
  *) usage; exit 1 ;;
esac
