#!/usr/bin/env python3
"""Update a specific material source with fetched content and key points.
Usage: update_material.py <project_dir> <source_id> <content> [key_points_json]
"""

import json
import os
import sys

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: update_material.py <project_dir> <source_id> <content> [key_points_json]

Updates a material source in materials.json with fetched content and key points.
Content is truncated to 5000 characters to prevent bloat.

Arguments:
  project_dir      Project directory containing .essay-state/
  source_id        ID of the source to update
  content          Fetched content text
  key_points_json  Optional JSON array of key points (default: [])""")


def cmd_update(project_dir, source_id, content, key_points_raw):
    state_dir = os.path.join(project_dir, ".essay-state")
    materials_file = os.path.join(state_dir, "materials.json")

    if not os.path.isfile(materials_file):
        print("No materials.json found.", file=sys.stderr)
        return 1

    # Parse key points
    try:
        key_points = json.loads(key_points_raw)
    except (json.JSONDecodeError, ValueError):
        key_points = [key_points_raw] if key_points_raw else []

    data = read_json_file(materials_file)
    sources = data.get("sources", [])

    found = False
    for s in sources:
        if s.get("id") == source_id:
            s["content"] = content[:5000]  # Truncate to prevent bloat
            s["key_points"] = key_points
            s["fetched"] = True
            found = True
            break

    if not found:
        print(f"Source {source_id} not found", file=sys.stderr)
        return 1

    atomic_json_write(materials_file, data)
    print(f"Updated source {source_id} with {len(content)} chars, {len(key_points)} key points")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        usage()
        sys.exit(0)
    if len(sys.argv) < 4:
        usage()
        sys.exit(1)

    project_dir = sys.argv[1]
    source_id = sys.argv[2]
    content = sys.argv[3]
    key_points_raw = sys.argv[4] if len(sys.argv) > 4 else "[]"

    result = cmd_update(project_dir, source_id, content, key_points_raw)
    sys.exit(result)


if __name__ == "__main__":
    main()
