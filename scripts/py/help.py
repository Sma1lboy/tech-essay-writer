#!/usr/bin/env python3
"""Usage reference for all tech-essay-writer scripts.
Usage: help.py [command]
Without args: list all scripts with one-line descriptions.
With command: show detailed help for that script.
"""

import glob
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/py/../../
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

DESCRIPTIONS = {
    "aggregate-reviews": "Aggregate 7 review JSON files into panel summary with consensus",
    "analytics-feedback": "Analytics feedback loop: record, track, query, trends, feed-taste",
    "article-compare": "Side-by-side draft comparison: word count, structure, reading level",
    "author-profile": "Author identity management: name, bio, social handles, expertise",
    "calibrate-reviews": "Post-aggregate calibration: normalize scores, detect outliers",
    "checkpoint": "State checkpoint and recovery: snapshot, list, rollback, clean",
    "code-validate": "Code example validator: syntax checking, imports, fragment detection",
    "config": "User configuration management: language, style, platforms, audiences",
    "cross-reference": "Published article registry for internal linking",
    "detect-input": "Classify user input into URLs, code blocks, file paths, notes",
    "diagram-suggest": "Diagram/image suggestion engine with Mermaid syntax output",
    "dry-run": "Full pipeline simulation with mock data (no LLM agents)",
    "expertise-graph": "Topic authority tracking with recency-weighted scoring",
    "export": "Export and archive: bundle, markdown, html, json, archive formats",
    "fetch-urls": "URL content fetcher for materials intake",
    "help": "Show this help listing, or detailed help for a specific command",
    "hook-workshop": "Opening hook generator and scorer (5 styles)",
    "influence-score": "Influence potential predictor: novelty, SEO, social, audience",
    "install": "Skill installer/uninstaller (symlink to ~/.claude/skills/)",
    "intake-materials": "Material intake: add-url, add-note, add-file, add-code, add-theme",
    "metrics-dashboard": "Comprehensive metrics dashboard: health, quality, growth",
    "orchestrate": "Pipeline orchestrator: 27 commands for prompt building, stage control",
    "outline-mixer": "Outline variant mixer: combine elements from multiple outlines",
    "pipeline-state": "Pipeline state CRUD with atomic writes",
    "progress-display": "Rich pipeline progress visualization with quality dashboard",
    "publish-check": "Pre-publish readiness checklist across multiple dimensions",
    "publishing-guide": "Per-platform publishing workflow guides with SEO tips",
    "quality-score": "Composite 0-10 quality score from weighted review dimensions",
    "readability-score": "Readability analysis: Flesch-Kincaid, passive voice, complexity",
    "seo-metadata": "SEO metadata generator: OpenGraph, meta tags, JSON-LD",
    "series-manager": "Article series manager: create, add, list, show, reorder",
    "summary": "Quick project status and capability overview",
    "taste-memory": "Persistent writing style preferences and learned patterns",
    "title-generator": "Title variation generator with scoring",
    "topic-research": "Research question generator, competitive landscape, unique angles",
    "update-material": "Update a specific material source with fetched content",
    "version": "Show or bump the project version (major/minor/patch)",
    "word-frequency": "Word frequency analysis: top-N, overused words, jargon, AI patterns",
}


def usage():
    print("""Usage: help.py [command]

Without arguments: list all available scripts
With a command name: show detailed help for that script""")


def get_version():
    """Get the current version string via version.sh raw."""
    version_sh = os.path.join(SCRIPTS_DIR, "version.sh")
    if not os.path.isfile(version_sh):
        return "?"
    try:
        result = subprocess.run(
            ["bash", version_sh, "raw"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "?"
    except (subprocess.SubprocessError, OSError):
        return "?"


def get_script_names():
    """Return sorted list of script basenames (without .sh)."""
    pattern = os.path.join(SCRIPTS_DIR, "*.sh")
    files = glob.glob(pattern)
    names = [os.path.splitext(os.path.basename(f))[0] for f in files]
    return sorted(names)


def get_description(name):
    """Get description for a script name, with fallback to file comment."""
    desc = DESCRIPTIONS.get(name, "")
    if desc:
        return desc
    # Fallback: extract from file's second line comment
    script_path = os.path.join(SCRIPTS_DIR, f"{name}.sh")
    if os.path.isfile(script_path):
        try:
            with open(script_path) as f:
                lines = f.readlines()
            if len(lines) >= 2 and lines[1].startswith("#"):
                return lines[1].lstrip("# ").rstrip()
        except OSError:
            pass
    return ""


def list_all():
    """List all scripts with one-line descriptions."""
    ver = get_version()
    names = get_script_names()

    print(f"tech-essay-writer v{ver} -- Script Reference")
    print("=============================================")
    print()
    print("Usage: bash scripts/help.sh [command]")
    print()

    # Find max name length for alignment
    max_len = max((len(n) for n in names), default=0)

    count = 0
    for name in names:
        desc = get_description(name)
        print(f"  {name:<{max_len}}  {desc}")
        count += 1

    print()
    print(f"{count} scripts available.")
    print()
    print("For detailed help: bash scripts/help.sh <command>")


def show_help(cmd):
    """Show detailed help for a specific script."""
    # Strip .sh if user appended it
    if cmd.endswith(".sh"):
        cmd = cmd[:-3]

    script_path = os.path.join(SCRIPTS_DIR, f"{cmd}.sh")

    if not os.path.isfile(script_path):
        print(f"ERROR: Unknown command '{cmd}'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Available commands:", file=sys.stderr)
        for name in get_script_names():
            print(f"  {name}", file=sys.stderr)
        sys.exit(1)

    print(f"=== {cmd} ===")
    print()

    # Extract the usage comment block from top of the file
    try:
        with open(script_path) as f:
            for line in f:
                line = line.rstrip("\n")
                # Skip shebang
                if line.startswith("#!/"):
                    continue
                # Stop at first non-comment, non-empty line
                if not line.startswith("#") and line != "":
                    break
                # Stop at set -euo pipefail
                if line.startswith("set "):
                    break
                # Print comment lines (strip leading "# " or "#")
                if line.startswith("#"):
                    stripped = line[2:] if line.startswith("# ") else line[1:]
                    if stripped == "#":
                        stripped = ""
                    print(stripped)
    except OSError:
        pass

    print()

    # If script has a usage() function, try to get --help output
    try:
        with open(script_path) as f:
            content = f.read()
    except OSError:
        content = ""

    if "usage()" in content:
        print("--- Detailed Usage ---")
        print()
        usage_output = ""
        for flag in ["--help", "-h"]:
            try:
                result = subprocess.run(
                    ["bash", script_path, flag],
                    capture_output=True, text=True, timeout=5
                )
                combined = (result.stdout + result.stderr).strip()
                if combined:
                    usage_output = combined
                    break
            except (subprocess.SubprocessError, OSError):
                continue

        if not usage_output:
            try:
                result = subprocess.run(
                    ["bash", script_path],
                    capture_output=True, text=True, timeout=5
                )
                combined = (result.stdout + result.stderr).strip()
                if combined:
                    usage_output = combined
            except (subprocess.SubprocessError, OSError):
                pass

        if usage_output:
            print(usage_output)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if not cmd:
        list_all()
    elif cmd in ("--help", "-h"):
        usage()
    else:
        show_help(cmd)


if __name__ == "__main__":
    main()
