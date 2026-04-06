#!/usr/bin/env bash
# State checkpoint and recovery system for the essay writing pipeline
# Snapshots .essay-state/ before each stage transition for rollback/retry
set -euo pipefail

STATE_DIR=".essay-state"
CHECKPOINT_DIR="checkpoints"

usage() {
  cat <<'EOF'
Usage: checkpoint.sh <command> <project_dir> [args...]

Commands:
  snapshot <project_dir> [label]          Snapshot .essay-state/ (label defaults to current stage)
  list <project_dir>                      List all checkpoints
  rollback <project_dir> <checkpoint_id>  Restore state from a checkpoint
  latest <project_dir>                    Show most recent checkpoint
  clean <project_dir> [--keep N]          Remove old checkpoints, keeping N most recent (default 5)
EOF
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

cmd_snapshot() {
  local project="$1"
  local label="${2:-}"

  if [ ! -d "$project/$STATE_DIR" ]; then
    echo "ERROR: No $STATE_DIR directory found in $project" >&2
    return 1
  fi

  # Default label to current stage
  if [ -z "$label" ]; then
    label=$(get_current_stage "$project")
  fi

  local timestamp
  timestamp=$(date -u +"%Y%m%dT%H%M%S")
  local checkpoint_id="${label}-${timestamp}"
  local ckpt_base="$project/$STATE_DIR/$CHECKPOINT_DIR"
  local ckpt_dir="$ckpt_base/$checkpoint_id"
  local tmp_dir="$ckpt_base/.tmp-${checkpoint_id}.$$"

  mkdir -p "$ckpt_base"

  # Copy state files to temp dir (atomic: copy then rename)
  mkdir -p "$tmp_dir"
  local file_count=0
  for f in "$project/$STATE_DIR"/*; do
    if [ -f "$f" ]; then
      cp "$f" "$tmp_dir/"
      file_count=$((file_count + 1))
    fi
  done

  if [ "$file_count" -eq 0 ]; then
    rm -rf "$tmp_dir"
    echo "ERROR: No files found in $STATE_DIR to snapshot" >&2
    return 1
  fi

  # Atomic rename
  mv "$tmp_dir" "$ckpt_dir"

  echo "Checkpoint: $checkpoint_id ($file_count files)"
}

cmd_list() {
  local project="$1"
  local ckpt_base="$project/$STATE_DIR/$CHECKPOINT_DIR"

  if [ ! -d "$ckpt_base" ]; then
    echo "No checkpoints found."
    return
  fi

  python3 -c "
import os, sys, json

ckpt_base = sys.argv[1]
entries = []
for name in os.listdir(ckpt_base):
    full = os.path.join(ckpt_base, name)
    if not os.path.isdir(full) or name.startswith('.'):
        continue
    # Extract label and timestamp from dirname: <label>-<YYYYMMDDTHHmmss>
    parts = name.rsplit('-', 1)
    label = parts[0] if len(parts) == 2 else name
    ts = parts[1] if len(parts) == 2 else ''
    # Read stage from checkpoint's pipeline-state.json
    stage = 'unknown'
    ps = os.path.join(full, 'pipeline-state.json')
    if os.path.exists(ps):
        try:
            with open(ps) as f:
                stage = json.load(f).get('stage', 'unknown')
        except:
            pass
    files = len([f for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))])
    entries.append((name, stage, label, ts, files))

# Sort by timestamp
entries.sort(key=lambda x: x[3])

if not entries:
    print('No checkpoints found.')
else:
    print(f'{len(entries)} checkpoint(s):')
    for name, stage, label, ts, files in entries:
        print(f'  {name}  [{stage}]  label:{label}  ({ts})  {files} files')
" "$ckpt_base"
}

cmd_rollback() {
  local project="$1"
  local checkpoint_id="${2:-}"

  if [ -z "$checkpoint_id" ]; then
    echo "ERROR: checkpoint_id required" >&2
    return 1
  fi

  local ckpt_dir="$project/$STATE_DIR/$CHECKPOINT_DIR/$checkpoint_id"

  if [ ! -d "$ckpt_dir" ]; then
    echo "ERROR: Checkpoint '$checkpoint_id' not found" >&2
    return 1
  fi

  # Remove current state files (preserve directories like checkpoints/)
  for f in "$project/$STATE_DIR"/*; do
    if [ -f "$f" ]; then
      rm "$f"
    fi
  done

  # Copy checkpoint files back to .essay-state/
  local restored=0
  for f in "$ckpt_dir"/*; do
    if [ -f "$f" ]; then
      cp "$f" "$project/$STATE_DIR/"
      restored=$((restored + 1))
    fi
  done

  echo "Rolled back to: $checkpoint_id ($restored files restored)"
}

cmd_latest() {
  local project="$1"
  local ckpt_base="$project/$STATE_DIR/$CHECKPOINT_DIR"

  if [ ! -d "$ckpt_base" ]; then
    echo "No checkpoints found."
    return 1
  fi

  python3 -c "
import os, sys, json

ckpt_base = sys.argv[1]
entries = []
for name in os.listdir(ckpt_base):
    full = os.path.join(ckpt_base, name)
    if not os.path.isdir(full) or name.startswith('.'):
        continue
    parts = name.rsplit('-', 1)
    ts = parts[1] if len(parts) == 2 else ''
    entries.append((name, ts))

entries.sort(key=lambda x: x[1])

if not entries:
    print('No checkpoints found.')
    sys.exit(1)

latest = entries[-1][0]
full = os.path.join(ckpt_base, latest)
parts = latest.rsplit('-', 1)
label = parts[0] if len(parts) == 2 else latest
ts = parts[1] if len(parts) == 2 else ''

stage = 'unknown'
ps = os.path.join(full, 'pipeline-state.json')
if os.path.exists(ps):
    try:
        with open(ps) as f:
            stage = json.load(f).get('stage', 'unknown')
    except:
        pass
files = len([f for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))])
print(f'{latest}  [{stage}]  label:{label}  ({ts})  {files} files')
" "$ckpt_base"
}

cmd_clean() {
  local project="$1"
  shift
  local keep=5

  while [ $# -gt 0 ]; do
    case "$1" in
      --keep) keep="${2:-5}"; shift 2 ;;
      *) shift ;;
    esac
  done

  local ckpt_base="$project/$STATE_DIR/$CHECKPOINT_DIR"

  if [ ! -d "$ckpt_base" ]; then
    echo "No checkpoints to clean."
    return
  fi

  python3 -c "
import os, sys, shutil

ckpt_base = sys.argv[1]
keep = int(sys.argv[2])

entries = []
for name in os.listdir(ckpt_base):
    full = os.path.join(ckpt_base, name)
    if not os.path.isdir(full) or name.startswith('.'):
        continue
    parts = name.rsplit('-', 1)
    ts = parts[1] if len(parts) == 2 else ''
    entries.append((name, ts))

entries.sort(key=lambda x: x[1])
total = len(entries)

if total <= keep:
    print(f'Only {total} checkpoint(s), keeping all (threshold: {keep}).')
    sys.exit(0)

to_remove = entries[:total - keep]
for name, _ in to_remove:
    shutil.rmtree(os.path.join(ckpt_base, name))

print(f'Cleaned {len(to_remove)} checkpoint(s), kept {keep}.')
" "$ckpt_base" "$keep"
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
  snapshot) cmd_snapshot "$PROJECT" "${1:-}" ;;
  list) cmd_list "$PROJECT" ;;
  rollback) cmd_rollback "$PROJECT" "${1:-}" ;;
  latest) cmd_latest "$PROJECT" ;;
  clean) cmd_clean "$PROJECT" "$@" ;;
  *) usage; exit 1 ;;
esac
