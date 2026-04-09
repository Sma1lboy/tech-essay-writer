#!/usr/bin/env python3
"""Version tracking for tech-essay-writer.
Usage: version.py [show|bump <major|minor|patch>|raw]
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/py/../../
VERSION_FILE = os.path.join(SKILL_DIR, "VERSION")


def usage():
    print("""Usage: version.py [command]

Commands:
  show                  Display current version (default)
  bump <major|minor|patch>  Bump the version number
  raw                   Output version string only (no label)

Examples:
  python3 scripts/py/version.py              # Show version
  python3 scripts/py/version.py show         # Show version
  python3 scripts/py/version.py bump patch   # 1.0.0 -> 1.0.1
  python3 scripts/py/version.py bump minor   # 1.0.0 -> 1.1.0
  python3 scripts/py/version.py bump major   # 1.0.0 -> 2.0.0""")


def ensure_version_file():
    if not os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE, "w") as f:
            f.write("1.0.0\n")


def read_version():
    ensure_version_file()
    with open(VERSION_FILE) as f:
        return f.readline().strip()


def parse_version(ver):
    if not re.match(r"^\d+\.\d+\.\d+$", ver):
        print(f"ERROR: Invalid version format '{ver}' (expected N.N.N)", file=sys.stderr)
        return None
    parts = ver.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def cmd_show():
    ver = read_version()
    print(f"tech-essay-writer v{ver}")
    return 0


def cmd_raw():
    print(read_version())
    return 0


def cmd_bump(args):
    if not args:
        print("ERROR: specify major, minor, or patch", file=sys.stderr)
        usage()
        return 1

    component = args[0]
    if component not in ("major", "minor", "patch"):
        print(f"ERROR: unknown component '{component}' (use major, minor, or patch)", file=sys.stderr)
        return 1

    old_ver = read_version()
    parsed = parse_version(old_ver)
    if parsed is None:
        return 1

    major, minor, patch = parsed

    if component == "major":
        major += 1
        minor = 0
        patch = 0
    elif component == "minor":
        minor += 1
        patch = 0
    elif component == "patch":
        patch += 1

    new_ver = f"{major}.{minor}.{patch}"

    # Atomic write
    tmp_file = f"{VERSION_FILE}.tmp.{os.getpid()}"
    with open(tmp_file, "w") as f:
        f.write(f"{new_ver}\n")
    os.rename(tmp_file, VERSION_FILE)

    print(f"{old_ver} -> {new_ver}")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    rest = sys.argv[2:]

    dispatch = {
        "show": lambda: cmd_show(),
        "raw": lambda: cmd_raw(),
        "bump": lambda: cmd_bump(rest),
        "--help": lambda: (usage(), 0)[1],
        "-h": lambda: (usage(), 0)[1],
        "help": lambda: (usage(), 0)[1],
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        print(f"ERROR: unknown command '{cmd}'", file=sys.stderr)
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
