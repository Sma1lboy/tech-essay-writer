#!/usr/bin/env python3
"""Install/uninstall tech-essay-writer skill into ~/.claude/skills/.
Usage: install.py [--uninstall]
"""

import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/py/../../
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", "tech-essay-writer")

FLAT_COMPONENTS = ["SKILL.md", "prompts", "templates"]
NESTED_COMPONENTS = [("scripts/py", "scripts/py")]  # (source_rel, dest_rel)


def usage():
    print("""Usage: install.py [--uninstall]

Install:   install.py
Uninstall: install.py --uninstall""")


def _link_component(target, link):
    """Create a symlink from link -> target, removing stale entries."""
    if not os.path.exists(target):
        print(f"Warning: {target} does not exist, skipping")
        return

    # Remove stale symlink or existing file/directory at the link path
    if os.path.islink(link):
        os.unlink(link)
    elif os.path.exists(link):
        print(f"Warning: {link} exists and is not a symlink, replacing")
        if os.path.isdir(link):
            shutil.rmtree(link)
        else:
            os.unlink(link)

    os.symlink(target, link)
    print(f"Linked: {link} -> {target}")


def do_install():
    # Remove existing whole-directory symlink if present
    if os.path.islink(SKILL_DIR):
        print(f"Removing existing symlink: {SKILL_DIR}")
        os.unlink(SKILL_DIR)

    # Ensure parent directory exists and create skill directory
    os.makedirs(os.path.dirname(SKILL_DIR), exist_ok=True)
    os.makedirs(SKILL_DIR, exist_ok=True)

    # Symlink flat components
    for component in FLAT_COMPONENTS:
        target = os.path.join(PROJECT_DIR, component)
        link = os.path.join(SKILL_DIR, component)
        _link_component(target, link)

    # Symlink nested components (create parent dirs as needed)
    for source_rel, dest_rel in NESTED_COMPONENTS:
        target = os.path.join(PROJECT_DIR, source_rel)
        link = os.path.join(SKILL_DIR, dest_rel)
        os.makedirs(os.path.join(SKILL_DIR, os.path.dirname(dest_rel)), exist_ok=True)
        _link_component(target, link)

    print(f"Installed tech-essay-writer skill to {SKILL_DIR}")
    return 0


def do_uninstall():
    if not os.path.isdir(SKILL_DIR) and not os.path.islink(SKILL_DIR):
        print(f"Nothing to uninstall: {SKILL_DIR} does not exist")
        return 0

    # If it's a whole-directory symlink, just remove it
    if os.path.islink(SKILL_DIR):
        os.unlink(SKILL_DIR)
        print(f"Removed symlink: {SKILL_DIR}")
        return 0

    # Remove flat component symlinks
    for component in FLAT_COMPONENTS:
        link = os.path.join(SKILL_DIR, component)
        if os.path.islink(link):
            os.unlink(link)
            print(f"Removed: {link}")

    # Remove nested component symlinks and empty parent dirs
    for _source_rel, dest_rel in NESTED_COMPONENTS:
        link = os.path.join(SKILL_DIR, dest_rel)
        if os.path.islink(link):
            os.unlink(link)
            print(f"Removed: {link}")
        parent = os.path.join(SKILL_DIR, os.path.dirname(dest_rel))
        if os.path.isdir(parent):
            try:
                os.rmdir(parent)
                print(f"Removed directory: {parent}")
            except OSError:
                pass

    # Remove the directory if empty
    if os.path.isdir(SKILL_DIR):
        try:
            os.rmdir(SKILL_DIR)
            print(f"Removed directory: {SKILL_DIR}")
        except OSError:
            print(f"Warning: {SKILL_DIR} not empty, not removed")

    print("Uninstalled tech-essay-writer skill")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    dispatch = {
        "--uninstall": lambda: do_uninstall(),
        "--help": lambda: (usage(), 0)[1],
        "-h": lambda: (usage(), 0)[1],
        "": lambda: do_install(),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        print(f"Unknown option: {cmd}", file=sys.stderr)
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
