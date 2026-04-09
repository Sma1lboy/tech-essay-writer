#!/usr/bin/env python3
"""Fetch URL content — find unfetched URLs in materials.json.
Usage: fetch_urls.py <project_dir>
"""

import json
import os
import sys

from utils import read_json_file


def usage():
    print("""Usage: fetch_urls.py <project_dir>

Scans materials.json for URL sources that have not been fetched yet.
Prints one line per unfetched URL in the format: FETCH:<id>:<url>
Exits 1 if materials.json does not exist.""")


def cmd_fetch(project_dir):
    state_dir = os.path.join(project_dir, ".essay-state")
    materials_file = os.path.join(state_dir, "materials.json")

    if not os.path.isfile(materials_file):
        print("No materials.json found.")
        return 1

    data = read_json_file(materials_file)
    sources = data.get("sources", [])

    unfetched = [s for s in sources if s.get("type") == "url" and not s.get("fetched")]
    if not unfetched:
        print("All URLs already fetched.")
        return 0

    for s in unfetched:
        print(f"FETCH:{s['id']}:{s.get('url', '')}")
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        usage()
        sys.exit(1 if len(sys.argv) < 2 else 0)

    project_dir = sys.argv[1]
    result = cmd_fetch(project_dir)
    sys.exit(result)


if __name__ == "__main__":
    main()
