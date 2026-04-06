#!/usr/bin/env bash
# Taste memory — persist writing style preferences across sessions
# Inspired by gstack's design taste memory system
set -euo pipefail

TASTE_DIR="$HOME/.tech-essay-writer"

usage() {
  cat <<'EOF'
Usage: taste-memory.sh <command> [args...]

Commands:
  read                          Read current taste memory
  update <project_dir> <file>   Update taste from completed article
  record-choice <key> <value>   Record a specific preference
  get-preference <key>          Get a specific preference
  history                       Show article history
EOF
}

ensure_dir() {
  mkdir -p "$TASTE_DIR"
}

taste_file() {
  echo "$TASTE_DIR/taste-memory.json"
}

read_taste() {
  local tf
  tf="$(taste_file)"
  if [ -f "$tf" ]; then
    cat "$tf"
  else
    echo '{}'
  fi
}

write_taste() {
  local json_str="$1"
  local tf
  tf="$(taste_file)"
  local tmp="${tf}.tmp.$$"
  ensure_dir
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$tf"
}

cmd_read() {
  local taste
  taste=$(read_taste)
  if [ "$taste" = "{}" ]; then
    echo "No taste memory yet. Will be populated after first article."
  else
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print('=== Writing Style Preferences ===')
if 'preferred_variant' in d:
    print(f\"Preferred style: {d['preferred_variant']}\")
if 'tone_preferences' in d:
    print(f\"Tone: {', '.join(d['tone_preferences'])}\")
if 'structural_preferences' in d:
    for k, v in d['structural_preferences'].items():
        print(f\"  {k}: {v}\")
if 'topics_written' in d:
    print(f\"Topics covered: {len(d['topics_written'])}\")
    for t in d['topics_written'][-5:]:
        print(f\"  - {t['topic']} ({t['date']})\")
if 'feedback_patterns' in d:
    print('Feedback patterns:')
    for p in d['feedback_patterns'][-5:]:
        print(f\"  - {p}\")
" "$taste"
  fi
}

cmd_update() {
  local project_dir="$1" taste_file_path="${2:-}"
  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Read pipeline state if it exists
  local state='{}'
  if [ -f "$project_dir/.essay-state/pipeline-state.json" ]; then
    state=$(cat "$project_dir/.essay-state/pipeline-state.json")
  fi

  taste=$(python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
state = json.loads(sys.argv[2])
now = sys.argv[3]

# Initialize structure if needed
taste.setdefault('preferred_variant', None)
taste.setdefault('tone_preferences', [])
taste.setdefault('structural_preferences', {})
taste.setdefault('topics_written', [])
taste.setdefault('feedback_patterns', [])
taste.setdefault('articles_count', 0)
taste.setdefault('updated_at', now)

# Update from pipeline state
topic = state.get('topic', 'unknown')
variant = state.get('outline_variant')

# Track topics
taste['topics_written'].append({
    'topic': topic,
    'date': now,
    'variant': variant,
    'refinement_rounds': state.get('refinement_round', 0)
})

# Update variant preference (most recent wins, but track frequency)
if variant:
    taste['preferred_variant'] = variant

taste['articles_count'] += 1
taste['updated_at'] = now

# Keep last 50 topics max
taste['topics_written'] = taste['topics_written'][-50:]

print(json.dumps(taste))
" "$taste" "$state" "$now")

  write_taste "$taste"
  echo "Taste memory updated."
}

cmd_record_choice() {
  local key="$1" value="$2"
  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  taste=$(python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3]
now = sys.argv[4]

if key == 'tone':
    taste.setdefault('tone_preferences', [])
    if val not in taste['tone_preferences']:
        taste['tone_preferences'].append(val)
elif key == 'feedback':
    taste.setdefault('feedback_patterns', [])
    taste['feedback_patterns'].append(val)
    taste['feedback_patterns'] = taste['feedback_patterns'][-20:]
else:
    taste.setdefault('structural_preferences', {})
    taste['structural_preferences'][key] = val

taste['updated_at'] = now
print(json.dumps(taste))
" "$taste" "$key" "$value" "$now")

  write_taste "$taste"
}

cmd_get_preference() {
  local key="$1"
  local taste
  taste=$(read_taste)
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
key = sys.argv[2]
if key == 'tone':
    print(json.dumps(taste.get('tone_preferences', [])))
elif key == 'feedback':
    print(json.dumps(taste.get('feedback_patterns', [])))
elif key == 'variant':
    print(taste.get('preferred_variant', ''))
else:
    prefs = taste.get('structural_preferences', {})
    print(prefs.get(key, ''))
" "$taste" "$key"
}

cmd_history() {
  local taste
  taste=$(read_taste)
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
topics = taste.get('topics_written', [])
if not topics:
    print('No articles written yet.')
else:
    print(f'Articles written: {len(topics)}')
    for t in topics:
        print(f\"  [{t.get('date','?')[:10]}] {t.get('topic','?')} (variant: {t.get('variant','?')})\")
" "$taste"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  read) cmd_read ;;
  update) cmd_update "$@" ;;
  record-choice) cmd_record_choice "$@" ;;
  get-preference) cmd_get_preference "$@" ;;
  history) cmd_history ;;
  *) usage; exit 1 ;;
esac
