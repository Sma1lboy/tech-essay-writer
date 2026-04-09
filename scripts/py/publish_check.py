#!/usr/bin/env python3
"""Pre-publish checklist — validates the article is ready for publication.
Usage: publish_check.py <project_dir>
"""

import json
import os
import re
import sys

from utils import read_json_file

PASS = 0
FAIL = 0
WARN = 0


def check(desc, condition):
    """Record a required check. Failure increments FAIL counter."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \u2713 {desc}")
    else:
        FAIL += 1
        print(f"  \u2717 {desc}")


def warn_check(desc, condition):
    """Record an advisory check. Failure increments WARN counter."""
    global PASS, WARN
    if condition:
        PASS += 1
        print(f"  \u2713 {desc}")
    else:
        WARN += 1
        print(f"  \u26a0 {desc}")


def file_has_heading(path):
    """Check if the first 5 lines of a file contain a # heading."""
    try:
        with open(path) as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                if line.startswith("#"):
                    return True
    except (IOError, OSError):
        pass
    return False


def file_grep_ci(pattern, path):
    """Case-insensitive search for pattern in file."""
    try:
        with open(path) as f:
            content = f.read()
        return bool(re.search(pattern, content, re.IGNORECASE))
    except (IOError, OSError):
        return False


def file_grep(pattern, path):
    """Case-sensitive search for pattern in file."""
    try:
        with open(path) as f:
            content = f.read()
        return bool(re.search(pattern, content))
    except (IOError, OSError):
        return False


def word_count(path):
    """Count words in a file."""
    try:
        with open(path) as f:
            content = f.read()
        return len(content.split())
    except (IOError, OSError):
        return 0


def usage():
    print("""Usage: publish_check.py <project_dir>

Pre-publish checklist that validates the article is ready for publication.
Checks pipeline state, content artifacts, quality gate, and review coverage.

Exits 0 if all required checks pass, 1 otherwise.""")


def cmd_check(project_dir):
    global PASS, FAIL, WARN
    state_dir = os.path.join(project_dir, ".essay-state")

    print("=== Pre-Publish Checklist ===")
    print()

    # Pipeline Completion
    print("Pipeline Completion:")
    pipeline_file = os.path.join(state_dir, "pipeline-state.json")
    check("Pipeline state exists", os.path.isfile(pipeline_file))
    if os.path.isfile(pipeline_file):
        state = read_json_file(pipeline_file)
        check("Pipeline marked complete", bool(state.get("completed")))
    else:
        check("Pipeline marked complete", False)

    # Content Artifacts
    print()
    print("Content Artifacts:")
    internal_file = os.path.join(state_dir, "final-internal.md")
    external_file = os.path.join(state_dir, "final-external.md")
    social_file = os.path.join(state_dir, "social-package.json")
    check("Internal version exists", os.path.isfile(internal_file))
    check("External version exists", os.path.isfile(external_file))
    check("Social package exists", os.path.isfile(social_file))

    # Internal version checks
    print()
    print("Internal version:")
    if os.path.isfile(internal_file):
        wc = word_count(internal_file)
        check(f"Internal version > 500 words ({wc} words)", wc > 500)
        check("Has title (# heading)", file_has_heading(internal_file))
        warn_check("Has TL;DR section", file_grep_ci(r"tl;dr|tldr|summary", internal_file))

    # External version checks
    print()
    print("External version:")
    if os.path.isfile(external_file):
        wc = word_count(external_file)
        check(f"External version > 500 words ({wc} words)", wc > 500)
        check("Has title (# heading)", file_has_heading(external_file))
        warn_check("Has About the Author", file_grep_ci(r"about the author|about me|bio", external_file))
        warn_check("Has code examples", file_grep(r"```", external_file))

    # Social package checks
    print()
    print("Social package:")
    if os.path.isfile(social_file):
        social = read_json_file(social_file)
        warn_check("Has Twitter thread", bool(social.get("twitter_thread")))
        warn_check("Has LinkedIn post", bool(social.get("linkedin_post")))
        warn_check("Has HN title", bool(social.get("hn_title")))

    # Quality Gate
    print()
    print("Quality Gate:")
    quality_file = os.path.join(state_dir, "quality-score.json")
    if os.path.isfile(quality_file):
        quality = read_json_file(quality_file)
        score = quality.get("composite_score", 0)
        readiness = quality.get("readiness", "UNKNOWN")
        check(
            f"Quality score \u2265 6.0 (score: {score}, readiness: {readiness})",
            float(score) >= 6.0,
        )
    else:
        warn_check("Quality score computed", False)

    # Review Coverage
    print()
    print("Review Coverage:")
    for reviewer in ["technical", "editor", "adversarial", "audience", "seo"]:
        review_file = os.path.join(state_dir, f"review-{reviewer}.json")
        check(f"Review: {reviewer}", os.path.isfile(review_file))

    # Summary
    print()
    print("================================")
    print(f"Pass: {PASS} | Fail: {FAIL} | Warn: {WARN}")
    if FAIL == 0:
        print("READY TO PUBLISH \u2705")
    else:
        print(f"NOT READY \u2014 {FAIL} checks failed \u274c")
    print("================================")

    return 0 if FAIL == 0 else 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        usage()
        sys.exit(1 if len(sys.argv) < 2 else 0)

    project_dir = sys.argv[1]
    result = cmd_check(project_dir)
    sys.exit(result)


if __name__ == "__main__":
    main()
