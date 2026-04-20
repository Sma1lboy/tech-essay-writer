#!/usr/bin/env python3
"""Pipeline state management for tech-essay-writer.
Tracks article progress through stages with atomic writes.
"""

import json
import os
import subprocess
import sys

from utils import atomic_json_write, read_json_file, timestamp_now

STATE_DIR = ".essay-state"
VALID_STAGES = ["intake", "research", "outline", "draft", "review", "refinement", "polish", "complete"]


def usage():
    print("""Usage: pipeline-state.py <command> <project_dir> [args...]

Commands:
  init <project_dir> <topic> [--series <id>] [--project <slug>]
                                       Initialize new article pipeline. The
                                       --project flag binds the article to a
                                       workspace Project (see project_manager.py);
                                       if omitted, resolve_project() picks
                                       active-project or auto-creates 'default'.
  set-stage <project_dir> <stage>      Update current stage
  get-stage <project_dir>              Get current stage
  read <project_dir>                   Read full pipeline state
  set-field <project_dir> <key> <val>  Set arbitrary field
  get-field <project_dir> <key>        Get field value
  add-review <project_dir> <file>      Register a review result
  refinement-round <project_dir>       Increment refinement round
  complete <project_dir>               Mark pipeline complete""")


def state_file(project):
    return os.path.join(project, STATE_DIR, "pipeline-state.json")


def read_state(project):
    sf = state_file(project)
    if not os.path.isfile(sf):
        return {}
    try:
        with open(sf) as f:
            content = f.read()
        json.loads(content)  # validate
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        print(f"WARNING: Corrupt state file: {sf} — treating as empty", file=sys.stderr)
        return {}


def write_state(project, data):
    sf = state_file(project)
    atomic_json_write(sf, data)


def _resolve_project_slug(requested: str) -> str:
    """Resolve a workspace Project slug, falling back to active/default.

    Returns "" when the projects feature isn't reachable (import failure,
    filesystem quirk) — the pipeline predates projects and must still work,
    so we degrade silently to "no project association".
    """
    try:
        import project_manager as pm
        return pm.resolve_project(requested)
    except Exception:
        return ""


def cmd_init(project, args):
    if not project:
        print("ERROR: project_dir is required for init", file=sys.stderr)
        return 1

    # Parse args: topic, --series <id>, --project <slug>
    topic = ""
    series_id = ""
    project_slug = ""
    i = 0
    while i < len(args):
        if args[i] == "--series":
            series_id = args[i + 1] if i + 1 < len(args) else ""
            i += 2
        elif args[i] == "--project":
            project_slug = args[i + 1] if i + 1 < len(args) else ""
            i += 2
        else:
            if not topic:
                topic = args[i]
            i += 1

    # Resolve workspace project: explicit --project > active-project > default.
    # Failures are non-fatal — existing articles without a project association
    # continue to work (project field stays empty string).
    project_slug = _resolve_project_slug(project_slug)

    os.makedirs(os.path.join(project, STATE_DIR), exist_ok=True)
    now = timestamp_now()

    # Read defaults from config if available
    config_file = os.path.expanduser("~/.tech-essay-writer/config.json")
    config_language = "en"
    config_max_rounds = 3
    config = read_json_file(config_file)
    if config:
        config_language = config.get("language", "en")
        config_max_rounds = config.get("max_refinement_rounds", 3)

    state = {
        "topic": topic,
        "stage": "intake",
        "created_at": now,
        "updated_at": now,
        "language": config_language,
        "project": project_slug,
        "materials_count": 0,
        "outline_variant": None,
        "draft_version": 0,
        "refinement_round": 0,
        "max_refinement_rounds": int(config_max_rounds),
        "reviews": {},
        "review_panel_complete": False,
        "completed": False,
        "artifacts": []
    }
    if series_id:
        state["series_id"] = series_id

    write_state(project, state)
    msg = f"Pipeline initialized for: {topic}"
    if project_slug:
        msg += f" (project: {project_slug})"
    print(msg)
    return 0


def cmd_set_stage(project, args):
    if not project or not args:
        print("ERROR: set-stage requires <project_dir> <stage>", file=sys.stderr)
        return 1

    stage = args[0]
    if stage not in VALID_STAGES:
        print(f"ERROR: Invalid stage '{stage}'. Valid: {' '.join(VALID_STAGES)}", file=sys.stderr)
        return 1

    state = read_state(project)

    # Auto-snapshot current stage before transition (non-fatal)
    current_stage = state.get("stage", "")
    if current_stage:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        checkpoint_sh = os.path.join(script_dir, "checkpoint.sh")
        try:
            subprocess.run(
                ["bash", checkpoint_sh, "snapshot", project, current_stage],
                capture_output=True, timeout=30
            )
        except Exception:
            pass

    now = timestamp_now()
    state["stage"] = stage
    state["updated_at"] = now
    write_state(project, state)
    print(f"Stage → {stage}")
    return 0


def cmd_get_stage(project):
    if not project:
        print("ERROR: get-stage requires <project_dir>", file=sys.stderr)
        return 1
    state = read_state(project)
    print(state.get("stage", "unknown"))
    return 0


def cmd_read(project):
    state = read_state(project)
    print(json.dumps(state))
    return 0


def cmd_set_field(project, args):
    if not project or len(args) < 2:
        print("ERROR: set-field requires <project_dir> <key> <value>", file=sys.stderr)
        return 1

    key = args[0]
    val = args[1]

    state = read_state(project)
    now = timestamp_now()

    # Try to parse as JSON value, fallback to string
    try:
        val = json.loads(val)
    except (json.JSONDecodeError, ValueError):
        pass

    state[key] = val
    state["updated_at"] = now
    write_state(project, state)
    return 0


def cmd_get_field(project, args):
    if not project or not args:
        print("ERROR: get-field requires <project_dir> <key>", file=sys.stderr)
        return 1

    key = args[0]
    state = read_state(project)
    v = state.get(key)
    if v is not None:
        print(json.dumps(v))
    else:
        print("")
    return 0


def cmd_add_review(project, args):
    if not project or not args:
        print("ERROR: add-review requires <project_dir> <review_file>", file=sys.stderr)
        return 1

    review_file = args[0]
    state = read_state(project)
    now = timestamp_now()

    name = os.path.splitext(os.path.basename(review_file))[0]
    if os.path.exists(review_file):
        review = read_json_file(review_file)
        state["reviews"][name] = {
            "file": review_file,
            "rating": review.get("rating", "unknown"),
            "issues_count": len(review.get("issues", []))
        }
    else:
        state["reviews"][name] = {"file": review_file, "rating": "missing", "issues_count": 0}

    state["updated_at"] = now

    # Check if all reviews are in (8 for zh, 7 otherwise)
    expected_reviews = 8 if state.get("language", "en") == "zh" else 7
    if len(state["reviews"]) >= expected_reviews:
        state["review_panel_complete"] = True

    write_state(project, state)
    return 0


def cmd_refinement_round(project):
    if not project:
        print("ERROR: refinement-round requires <project_dir>", file=sys.stderr)
        return 1

    state = read_state(project)
    now = timestamp_now()
    state["refinement_round"] = state.get("refinement_round", 0) + 1
    state["updated_at"] = now
    write_state(project, state)
    print(f"Refinement round {state['refinement_round']}/{state['max_refinement_rounds']}")
    return 0


def cmd_complete(project):
    if not project:
        print("ERROR: complete requires <project_dir>", file=sys.stderr)
        return 1

    state = read_state(project)
    now = timestamp_now()
    state["stage"] = "complete"
    state["completed"] = True
    state["completed_at"] = now
    state["updated_at"] = now
    write_state(project, state)
    print("Pipeline complete!")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    project = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    rest = sys.argv[3:]

    dispatch = {
        "init": lambda: cmd_init(project, rest),
        "set-stage": lambda: cmd_set_stage(project, rest),
        "get-stage": lambda: cmd_get_stage(project),
        "read": lambda: cmd_read(project),
        "set-field": lambda: cmd_set_field(project, rest),
        "get-field": lambda: cmd_get_field(project, rest),
        "add-review": lambda: cmd_add_review(project, rest),
        "refinement-round": lambda: cmd_refinement_round(project),
        "complete": lambda: cmd_complete(project),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
