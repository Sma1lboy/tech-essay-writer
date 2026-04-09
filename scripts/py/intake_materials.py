#!/usr/bin/env python3
"""Intake materials parser — structures raw user inputs into materials.json.
Usage: intake_materials.py <command> <project_dir> [args...]
"""

import json
import os
import sys

from utils import atomic_json_write, gen_id, read_json_file, timestamp_now

STATE_DIR = ".essay-state"


def usage():
    print("""Usage: intake-materials.sh <project_dir> <command> [args...]

Commands:
  init <project_dir>                      Initialize materials store
  add-url <project_dir> <url> [title]     Add a URL source
  add-note <project_dir> <note>           Add a text note
  add-file <project_dir> <file_path>      Add a local file
  add-code <project_dir> <code> [lang]    Add a code snippet
  add-theme <project_dir> <theme>         Add a cross-cutting theme
  add-angle <project_dir> <angle>         Add a potential narrative angle
  list <project_dir>                      List all materials
  export <project_dir>                    Export full materials.json
  clear <project_dir>                     Clear all materials (with confirmation)""")


def materials_file(project):
    return os.path.join(project, STATE_DIR, "materials.json")


def empty_materials():
    return {
        "sources": [],
        "themes": [],
        "potential_angles": [],
        "technical_depth": "unknown",
        "source_count": 0
    }


def ensure_materials(project):
    mf = materials_file(project)
    os.makedirs(os.path.join(project, STATE_DIR), exist_ok=True)
    if not os.path.isfile(mf):
        with open(mf, 'w') as f:
            json.dump(empty_materials(), f, indent=2)


def read_materials(project):
    mf = materials_file(project)
    if not os.path.isfile(mf):
        print(f"ERROR: Materials file not found: {mf}", file=sys.stderr)
        return {}
    try:
        with open(mf) as f:
            content = f.read()
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        print(f"WARNING: Corrupt materials file: {mf} — treating as empty", file=sys.stderr)
        return empty_materials()


def write_materials(project, data):
    mf = materials_file(project)
    atomic_json_write(mf, data)


def cmd_init(project):
    ensure_materials(project)
    print("Materials store initialized.")
    return 0


def cmd_add_url(project, args):
    if not project or not args:
        print("ERROR: add-url requires <project_dir> <url> [title]", file=sys.stderr)
        return 1

    url = args[0]
    title = args[1] if len(args) > 1 else ""
    ensure_materials(project)
    mat = read_materials(project)
    sid = gen_id()

    source = {
        "id": sid,
        "type": "url",
        "url": url,
        "title": title if title else None,
        "content": None,
        "key_points": [],
        "fetched": False
    }
    mat["sources"].append(source)
    mat["source_count"] = len(mat["sources"])
    write_materials(project, mat)
    print(f"Added URL source: {url} ({sid})")
    return 0


def cmd_add_note(project, args):
    if not project or not args:
        print("ERROR: add-note requires <project_dir> <note>", file=sys.stderr)
        return 1

    note = args[0]
    ensure_materials(project)
    mat = read_materials(project)
    sid = gen_id()

    source = {
        "id": sid,
        "type": "note",
        "content": note,
        "key_points": [],
        "fetched": True
    }
    mat["sources"].append(source)
    mat["source_count"] = len(mat["sources"])
    write_materials(project, mat)
    print(f"Added note ({sid})")
    return 0


def cmd_add_file(project, args):
    if not project or not args:
        print("ERROR: add-file requires <project_dir> <file_path>", file=sys.stderr)
        return 1

    file_path = args[0]
    ensure_materials(project)

    if not os.path.isfile(file_path):
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        return 1

    mat = read_materials(project)
    sid = gen_id()

    with open(file_path) as f:
        content = f.read()

    ext = os.path.splitext(file_path)[1].lstrip(".")

    source = {
        "id": sid,
        "type": "file",
        "path": file_path,
        "extension": ext,
        "content": content,
        "key_points": [],
        "fetched": True
    }
    mat["sources"].append(source)
    mat["source_count"] = len(mat["sources"])
    write_materials(project, mat)
    print(f"Added file: {file_path} ({sid})")
    return 0


def cmd_add_code(project, args):
    if not project or not args:
        print("ERROR: add-code requires <project_dir> <code> [lang]", file=sys.stderr)
        return 1

    code = args[0]
    lang = args[1] if len(args) > 1 else ""
    ensure_materials(project)
    mat = read_materials(project)
    sid = gen_id()

    source = {
        "id": sid,
        "type": "code",
        "language": lang if lang else "unknown",
        "content": code,
        "key_points": [],
        "fetched": True
    }
    mat["sources"].append(source)
    mat["source_count"] = len(mat["sources"])
    write_materials(project, mat)
    print(f"Added code snippet ({sid})")
    return 0


def cmd_add_theme(project, args):
    if not project or not args:
        print("ERROR: add-theme requires <project_dir> <theme>", file=sys.stderr)
        return 1

    theme = args[0]
    ensure_materials(project)
    mat = read_materials(project)

    if theme not in mat["themes"]:
        mat["themes"].append(theme)

    write_materials(project, mat)
    print(f"Added theme: {theme}")
    return 0


def cmd_add_angle(project, args):
    if not project or not args:
        print("ERROR: add-angle requires <project_dir> <angle>", file=sys.stderr)
        return 1

    angle = args[0]
    ensure_materials(project)
    mat = read_materials(project)

    if angle not in mat["potential_angles"]:
        mat["potential_angles"].append(angle)

    write_materials(project, mat)
    print(f"Added angle: {angle}")
    return 0


def cmd_list(project):
    ensure_materials(project)
    mat = read_materials(project)

    print(f"Materials: {mat['source_count']} sources")
    for s in mat["sources"]:
        t = s["type"]
        if t == "url":
            fetched = "(fetched)" if s.get("fetched") else "(pending)"
            print(f"  [{s['id']}] URL: {s.get('url', '')} {fetched}")
        elif t == "note":
            preview = s.get("content", "")[:60]
            print(f"  [{s['id']}] Note: {preview}...")
        elif t == "file":
            print(f"  [{s['id']}] File: {s.get('path', '')}")
        elif t == "code":
            print(f"  [{s['id']}] Code: {s.get('language', 'unknown')} snippet")

    themes_str = ", ".join(mat.get("themes", [])) or "none"
    angles_str = ", ".join(mat.get("potential_angles", [])) or "none"
    print(f"Themes: {themes_str}")
    print(f"Angles: {angles_str}")
    return 0


def cmd_export(project):
    ensure_materials(project)
    mat = read_materials(project)
    print(json.dumps(mat))
    return 0


def cmd_clear(project):
    mf = materials_file(project)
    if os.path.isfile(mf):
        with open(mf, 'w') as f:
            json.dump(empty_materials(), f, indent=2)
        print("Materials cleared.")
    else:
        print("No materials file to clear.", file=sys.stderr)
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    project = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    rest = sys.argv[3:]

    dispatch = {
        "init": lambda: cmd_init(project),
        "add-url": lambda: cmd_add_url(project, rest),
        "add-note": lambda: cmd_add_note(project, rest),
        "add-file": lambda: cmd_add_file(project, rest),
        "add-code": lambda: cmd_add_code(project, rest),
        "add-theme": lambda: cmd_add_theme(project, rest),
        "add-angle": lambda: cmd_add_angle(project, rest),
        "list": lambda: cmd_list(project),
        "export": lambda: cmd_export(project),
        "clear": lambda: cmd_clear(project),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
