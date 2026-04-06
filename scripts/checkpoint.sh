#!/usr/bin/env bash
# State checkpoint and recovery system for the essay writing pipeline
# Snapshots .essay-state/ for save/restore across pipeline stages
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR=".essay-state"
CHECKPOINT_DIR="checkpoints"
INDEX_FILE="index.json"

usage() {
  cat <<'EOF'
Usage: checkpoint.sh <command> <project_dir> [args...]

Commands:
  save <project_dir> [label]       Snapshot current .essay-state/
  list <project_dir>               List all checkpoints
  restore <project_dir> <id>       Restore a checkpoint
  delete <project_dir> <id>        Delete a checkpoint
  auto-save <project_dir>          Auto-save with stage name as label
EOF
}

ensure_checkpoint_dir() {
  local project="$1"
  mkdir -p "$project/$STATE_DIR/$CHECKPOINT_DIR"
}

index_file() {
  echo "$1/$STATE_DIR/$CHECKPOINT_DIR/$INDEX_FILE"
}

read_index() {
  local idx
  idx="$(index_file "$1")"
  if [ -f "$idx" ]; then
    cat "$idx"
  else
    echo '[]'
  fi
}

write_index() {
  local project="$1" json_str="$2"
  local idx
  idx="$(index_file "$project")"
  local tmp="${idx}.tmp.$$"
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$idx"
}

generate_id() {
  python3 -c "
import time, random, string
ts = int(time.time())
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
print(f'ckpt-{ts}-{suffix}')
"
}

get_current_stage() {
  local project="$1"
  local state_file="$project/$STATE_DIR/pipeline-state.json"
  if [ -f "$state_file" ]; then
    python3 -c "import json; print(json.load(open('$state_file')).get('stage','unknown'))"
  else
    echo "unknown"
  fi
}

count_state_files() {
  local project="$1"
  local count=0
  for f in "$project/$STATE_DIR"/*.json "$project/$STATE_DIR"/*.md; do
    if [ -f "$f" ]; then
      count=$((count + 1))
    fi
  done
  echo "$count"
}

cmd_save() {
  local project="$1"
  local label="${2:-}"

  # Verify .essay-state exists and has files
  if [ ! -d "$project/$STATE_DIR" ]; then
    echo "ERROR: No .essay-state/ directory found in $project" >&2
    return 1
  fi

  # Collect files to archive (*.json and *.md, excluding checkpoints dir)
  local files_to_archive=()
  for f in "$project/$STATE_DIR"/*.json "$project/$STATE_DIR"/*.md; do
    if [ -f "$f" ]; then
      local basename
      basename=$(basename "$f")
      files_to_archive+=("$basename")
    fi
  done

  if [ ${#files_to_archive[@]} -eq 0 ]; then
    echo "ERROR: No .json or .md files found in .essay-state/" >&2
    return 1
  fi

  ensure_checkpoint_dir "$project"

  local ckpt_id
  ckpt_id=$(generate_id)
  local stage
  stage=$(get_current_stage "$project")
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local archive="$project/$STATE_DIR/$CHECKPOINT_DIR/${ckpt_id}.tar.gz"
  local files_count=${#files_to_archive[@]}

  # If no label provided, use the checkpoint id
  if [ -z "$label" ]; then
    label="$ckpt_id"
  fi

  # Create tar.gz from .essay-state/ dir, excluding checkpoints/
  tar -czf "$archive" -C "$project/$STATE_DIR" "${files_to_archive[@]}"

  # Update index
  local index
  index=$(read_index "$project")
  index=$(python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
entries.append({
    'id': sys.argv[2],
    'label': sys.argv[3],
    'stage': sys.argv[4],
    'timestamp': sys.argv[5],
    'files_count': int(sys.argv[6])
})
print(json.dumps(entries))
" "$index" "$ckpt_id" "$label" "$stage" "$now" "$files_count")
  write_index "$project" "$index"

  echo "Checkpoint saved: $ckpt_id (label: $label, stage: $stage, files: $files_count)"
}

cmd_list() {
  local project="$1"
  local index
  index=$(read_index "$project")
  python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
if not entries:
    print('No checkpoints found.')
    sys.exit(0)
print(f'{len(entries)} checkpoint(s):')
for e in entries:
    print(f\"  {e['id']}  [{e['stage']}]  {e['label']}  ({e['timestamp']})  {e['files_count']} files\")
" "$index"
}

cmd_restore() {
  local project="$1" ckpt_id="$2"

  ensure_checkpoint_dir "$project"

  local archive="$project/$STATE_DIR/$CHECKPOINT_DIR/${ckpt_id}.tar.gz"
  if [ ! -f "$archive" ]; then
    echo "ERROR: Checkpoint '$ckpt_id' not found" >&2
    return 1
  fi

  # Verify the checkpoint id exists in the index
  local index
  index=$(read_index "$project")
  local found
  found=$(python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
ckpt_id = sys.argv[2]
found = any(e['id'] == ckpt_id for e in entries)
print('yes' if found else 'no')
" "$index" "$ckpt_id")

  if [ "$found" != "yes" ]; then
    echo "ERROR: Checkpoint '$ckpt_id' not found in index" >&2
    return 1
  fi

  # Extract tar.gz back into .essay-state/, overwriting current files
  tar -xzf "$archive" -C "$project/$STATE_DIR"

  local label
  label=$(python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
ckpt_id = sys.argv[2]
for e in entries:
    if e['id'] == ckpt_id:
        print(e['label'])
        break
" "$index" "$ckpt_id")

  echo "Restored checkpoint: $ckpt_id (label: $label)"
}

cmd_delete() {
  local project="$1" ckpt_id="$2"

  ensure_checkpoint_dir "$project"

  local archive="$project/$STATE_DIR/$CHECKPOINT_DIR/${ckpt_id}.tar.gz"
  local index
  index=$(read_index "$project")

  # Verify checkpoint exists in index
  local found
  found=$(python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
ckpt_id = sys.argv[2]
found = any(e['id'] == ckpt_id for e in entries)
print('yes' if found else 'no')
" "$index" "$ckpt_id")

  if [ "$found" != "yes" ]; then
    echo "ERROR: Checkpoint '$ckpt_id' not found" >&2
    return 1
  fi

  # Remove archive file
  if [ -f "$archive" ]; then
    rm "$archive"
  fi

  # Remove from index
  index=$(python3 -c "
import json, sys
entries = json.loads(sys.argv[1])
ckpt_id = sys.argv[2]
entries = [e for e in entries if e['id'] != ckpt_id]
print(json.dumps(entries))
" "$index" "$ckpt_id")
  write_index "$project" "$index"

  echo "Deleted checkpoint: $ckpt_id"
}

cmd_auto_save() {
  local project="$1"
  local stage
  stage=$(get_current_stage "$project")
  local label="pre-${stage}"
  cmd_save "$project" "$label"
}

# Main dispatch
CMD="${1:-}"
shift || true
PROJECT="${1:-}"
shift || true

if [ -z "$CMD" ] || [ -z "$PROJECT" ]; then
  usage
  exit 1
fi

case "$CMD" in
  save) cmd_save "$PROJECT" "${1:-}" ;;
  list) cmd_list "$PROJECT" ;;
  restore) cmd_restore "$PROJECT" "${1:-}" ;;
  delete) cmd_delete "$PROJECT" "${1:-}" ;;
  auto-save) cmd_auto_save "$PROJECT" ;;
  *) usage; exit 1 ;;
esac
