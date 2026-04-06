#!/usr/bin/env bash
# Pipeline state management for tech-essay-writer
# Tracks article progress through stages with atomic writes
set -euo pipefail

STATE_DIR=".essay-state"

usage() {
  cat <<'EOF'
Usage: pipeline-state.sh <command> <project_dir> [args...]

Commands:
  init <project_dir> <topic>           Initialize new article pipeline
  set-stage <project_dir> <stage>      Update current stage
  get-stage <project_dir>              Get current stage
  read <project_dir>                   Read full pipeline state
  set-field <project_dir> <key> <val>  Set arbitrary field
  get-field <project_dir> <key>        Get field value
  add-review <project_dir> <file>      Register a review result
  refinement-round <project_dir>       Increment refinement round
  complete <project_dir>               Mark pipeline complete
EOF
}

ensure_state_dir() {
  local project="$1"
  mkdir -p "$project/$STATE_DIR"
}

state_file() {
  echo "$1/$STATE_DIR/pipeline-state.json"
}

read_state() {
  local sf
  sf="$(state_file "$1")"
  if [ -f "$sf" ]; then
    cat "$sf"
  else
    echo '{}'
  fi
}

write_state() {
  local project="$1" json_str="$2"
  local sf
  sf="$(state_file "$project")"
  local tmp="${sf}.tmp.$$"
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$sf"
}

cmd_init() {
  local project="$1" topic="${2:-}"
  ensure_state_dir "$project"
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local state
  state=$(python3 -c "
import json, sys
d = {
    'topic': sys.argv[1],
    'stage': 'intake',
    'created_at': sys.argv[2],
    'updated_at': sys.argv[2],
    'language': 'en',
    'materials_count': 0,
    'outline_variant': None,
    'draft_version': 0,
    'refinement_round': 0,
    'max_refinement_rounds': 3,
    'reviews': {},
    'review_panel_complete': False,
    'completed': False,
    'artifacts': []
}
print(json.dumps(d))
" "$topic" "$now")
  write_state "$project" "$state"
  echo "Pipeline initialized for: $topic"
}

cmd_set_stage() {
  local project="$1" stage="$2"
  local valid_stages="intake research outline draft review refinement polish complete"
  if ! echo "$valid_stages" | grep -qw "$stage"; then
    echo "ERROR: Invalid stage '$stage'. Valid: $valid_stages" >&2
    return 1
  fi
  local state
  state=$(read_state "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  state=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d['stage'] = sys.argv[2]
d['updated_at'] = sys.argv[3]
print(json.dumps(d))
" "$state" "$stage" "$now")
  write_state "$project" "$state"
  echo "Stage → $stage"
}

cmd_get_stage() {
  local project="$1"
  local state
  state=$(read_state "$project")
  python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('stage','unknown'))" "$state"
}

cmd_read() {
  local project="$1"
  read_state "$project"
}

cmd_set_field() {
  local project="$1" key="$2" val="$3"
  local state
  state=$(read_state "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  state=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3]
# Try to parse as JSON value, fallback to string
try:
    val = json.loads(val)
except (json.JSONDecodeError, ValueError):
    pass
d[key] = val
d['updated_at'] = sys.argv[4]
print(json.dumps(d))
" "$state" "$key" "$val" "$now")
  write_state "$project" "$state"
}

cmd_get_field() {
  local project="$1" key="$2"
  local state
  state=$(read_state "$project")
  python3 -c "import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2]); print(json.dumps(v) if v is not None else '')" "$state" "$key"
}

cmd_add_review() {
  local project="$1" review_file="$2"
  local state
  state=$(read_state "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  state=$(python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
review_file = sys.argv[2]
name = os.path.splitext(os.path.basename(review_file))[0]
if os.path.exists(review_file):
    with open(review_file) as f:
        review = json.load(f)
    d['reviews'][name] = {
        'file': review_file,
        'rating': review.get('rating', 'unknown'),
        'issues_count': len(review.get('issues', []))
    }
else:
    d['reviews'][name] = {'file': review_file, 'rating': 'missing', 'issues_count': 0}
d['updated_at'] = sys.argv[3]
# Check if all 5 reviews are in
if len(d['reviews']) >= 5:
    d['review_panel_complete'] = True
print(json.dumps(d))
" "$state" "$review_file" "$now")
  write_state "$project" "$state"
}

cmd_refinement_round() {
  local project="$1"
  local state
  state=$(read_state "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  state=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d['refinement_round'] = d.get('refinement_round', 0) + 1
d['updated_at'] = sys.argv[2]
print(json.dumps(d))
" "$state" "$now")
  write_state "$project" "$state"
  python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(f\"Refinement round {d['refinement_round']}/{d['max_refinement_rounds']}\")" "$state"
}

cmd_complete() {
  local project="$1"
  local state
  state=$(read_state "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  state=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d['stage'] = 'complete'
d['completed'] = True
d['completed_at'] = sys.argv[2]
d['updated_at'] = sys.argv[2]
print(json.dumps(d))
" "$state" "$now")
  write_state "$project" "$state"
  echo "Pipeline complete!"
}

# Main dispatch
CMD="${1:-}"
shift || true
PROJECT="${1:-$(pwd)}"
shift || true

case "$CMD" in
  init) cmd_init "$PROJECT" "$@" ;;
  set-stage) cmd_set_stage "$PROJECT" "$@" ;;
  get-stage) cmd_get_stage "$PROJECT" ;;
  read) cmd_read "$PROJECT" ;;
  set-field) cmd_set_field "$PROJECT" "$@" ;;
  get-field) cmd_get_field "$PROJECT" "$@" ;;
  add-review) cmd_add_review "$PROJECT" "$@" ;;
  refinement-round) cmd_refinement_round "$PROJECT" ;;
  complete) cmd_complete "$PROJECT" ;;
  *) usage; exit 1 ;;
esac
