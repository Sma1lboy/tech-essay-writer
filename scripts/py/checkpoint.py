#!/usr/bin/env python3
"""State checkpoint and recovery system for the essay writing pipeline.
Snapshots .essay-state/ before each stage transition for rollback/retry.
Usage: checkpoint.py <command> <project_dir> [args...]
"""

import os
import shutil
import sys
from datetime import datetime, timezone

from utils import read_json_file

STATE_DIR = ".essay-state"
CHECKPOINT_DIR = "checkpoints"


def usage():
    print("""Usage: checkpoint.py <command> <project_dir> [args...]

Commands:
  snapshot <project_dir> [label]          Snapshot .essay-state/ (label defaults to current stage)
  list <project_dir>                      List all checkpoints
  rollback <project_dir> <checkpoint_id>  Restore state from a checkpoint
  latest <project_dir>                    Show most recent checkpoint
  clean <project_dir> [--keep N]          Remove old checkpoints, keeping N most recent (default 5)""")


def get_current_stage(project):
    """Read the current stage from pipeline-state.json."""
    state_file = os.path.join(project, STATE_DIR, "pipeline-state.json")
    state = read_json_file(state_file)
    return state.get("stage", "unknown") if state else "unknown"


def list_checkpoint_entries(ckpt_base):
    """Collect checkpoint entries as (name, stage, label, timestamp, file_count) tuples."""
    entries = []
    if not os.path.isdir(ckpt_base):
        return entries
    for name in os.listdir(ckpt_base):
        full = os.path.join(ckpt_base, name)
        if not os.path.isdir(full) or name.startswith("."):
            continue
        parts = name.rsplit("-", 1)
        label = parts[0] if len(parts) == 2 else name
        ts = parts[1] if len(parts) == 2 else ""
        # Read stage from checkpoint's pipeline-state.json
        ps = os.path.join(full, "pipeline-state.json")
        ps_data = read_json_file(ps)
        stage = ps_data.get("stage", "unknown") if ps_data else "unknown"
        files = len([f for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))])
        entries.append((name, stage, label, ts, files))
    entries.sort(key=lambda x: x[3])
    return entries


def cmd_snapshot(project, label=""):
    state_dir = os.path.join(project, STATE_DIR)
    if not os.path.isdir(state_dir):
        print(f"ERROR: No {STATE_DIR} directory found in {project}", file=sys.stderr)
        return 1

    # Default label to current stage
    if not label:
        label = get_current_stage(project)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    checkpoint_id = f"{label}-{timestamp}"
    ckpt_base = os.path.join(state_dir, CHECKPOINT_DIR)
    ckpt_dir = os.path.join(ckpt_base, checkpoint_id)
    tmp_dir = os.path.join(ckpt_base, f".tmp-{checkpoint_id}.{os.getpid()}")

    os.makedirs(ckpt_base, exist_ok=True)

    # Copy state files to temp dir (atomic: copy then rename)
    os.makedirs(tmp_dir, exist_ok=True)
    file_count = 0
    for name in os.listdir(state_dir):
        src = os.path.join(state_dir, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(tmp_dir, name))
            file_count += 1

    if file_count == 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"ERROR: No files found in {STATE_DIR} to snapshot", file=sys.stderr)
        return 1

    # Atomic rename
    os.rename(tmp_dir, ckpt_dir)

    print(f"Checkpoint: {checkpoint_id} ({file_count} files)")
    return 0


def cmd_list(project):
    ckpt_base = os.path.join(project, STATE_DIR, CHECKPOINT_DIR)
    entries = list_checkpoint_entries(ckpt_base)

    if not entries:
        print("No checkpoints found.")
        return 0

    print(f"{len(entries)} checkpoint(s):")
    for name, stage, label, ts, files in entries:
        print(f"  {name}  [{stage}]  label:{label}  ({ts})  {files} files")
    return 0


def cmd_rollback(project, checkpoint_id=""):
    if not checkpoint_id:
        print("ERROR: checkpoint_id required", file=sys.stderr)
        return 1

    ckpt_dir = os.path.join(project, STATE_DIR, CHECKPOINT_DIR, checkpoint_id)
    if not os.path.isdir(ckpt_dir):
        print(f"ERROR: Checkpoint '{checkpoint_id}' not found", file=sys.stderr)
        return 1

    state_dir = os.path.join(project, STATE_DIR)

    # Remove current state files (preserve directories like checkpoints/)
    for name in os.listdir(state_dir):
        path = os.path.join(state_dir, name)
        if os.path.isfile(path):
            os.remove(path)

    # Copy checkpoint files back to .essay-state/
    restored = 0
    for name in os.listdir(ckpt_dir):
        src = os.path.join(ckpt_dir, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(state_dir, name))
            restored += 1

    print(f"Rolled back to: {checkpoint_id} ({restored} files restored)")
    return 0


def cmd_latest(project):
    ckpt_base = os.path.join(project, STATE_DIR, CHECKPOINT_DIR)
    entries = list_checkpoint_entries(ckpt_base)

    if not entries:
        print("No checkpoints found.")
        return 1

    latest = entries[-1]
    name, stage, label, ts, files = latest
    print(f"{name}  [{stage}]  label:{label}  ({ts})  {files} files")
    return 0


def cmd_clean(project, args):
    keep = 5
    i = 0
    while i < len(args):
        if args[i] == "--keep":
            try:
                keep = int(args[i + 1]) if i + 1 < len(args) else 5
            except ValueError:
                keep = 5
            i += 2
        else:
            i += 1

    ckpt_base = os.path.join(project, STATE_DIR, CHECKPOINT_DIR)
    if not os.path.isdir(ckpt_base):
        print("No checkpoints to clean.")
        return 0

    entries = list_checkpoint_entries(ckpt_base)
    total = len(entries)

    if total <= keep:
        print(f"Only {total} checkpoint(s), keeping all (threshold: {keep}).")
        return 0

    to_remove = entries[:total - keep]
    for name, _stage, _label, _ts, _files in to_remove:
        shutil.rmtree(os.path.join(ckpt_base, name))

    print(f"Cleaned {len(to_remove)} checkpoint(s), kept {keep}.")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    project = sys.argv[2] if len(sys.argv) > 2 else ""
    rest = sys.argv[3:]

    if not cmd or not project:
        usage()
        sys.exit(1)

    dispatch = {
        "snapshot": lambda: cmd_snapshot(project, rest[0] if rest else ""),
        "list": lambda: cmd_list(project),
        "rollback": lambda: cmd_rollback(project, rest[0] if rest else ""),
        "latest": lambda: cmd_latest(project),
        "clean": lambda: cmd_clean(project, rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
