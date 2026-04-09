#!/usr/bin/env python3
"""Quick project status and capability overview.
Usage: summary.py [project_dir]
"""

import glob
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/py/../../
CONFIG_DIR = os.path.expanduser("~/.tech-essay-writer")

# Section header prefixes (emoji codepoints)
_DOC = "\U0001F4C4"       # page facing up
_WRENCH = "\U0001F527"    # wrench
_PERSON = "\U0001F464"    # bust in silhouette
_PALETTE = "\U0001F3A8"   # artist palette
_CHART = "\U0001F4CA"     # bar chart
_BOOKS = "\U0001F4DA"     # books
_GEAR = "\u2699\uFE0F"    # gear

# Box-drawing
_TL = "\u2554"   # top-left double corner
_TR = "\u2557"   # top-right double corner
_BL = "\u255A"   # bottom-left double corner
_BR = "\u255D"   # bottom-right double corner
_H = "\u2550"    # horizontal double line
_V = "\u2551"    # vertical double line
_ARROW = "\u2192"
_BULLET = "\u2022"
_DASH = "\u2014"


def usage():
    print("""Usage: summary.py [project_dir]

Display a project status and capability overview.
If project_dir is omitted, the current working directory is used.""")


def read_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None


def count_templates():
    pattern = os.path.join(SKILL_DIR, "templates", "*.md")
    return len(glob.glob(pattern))


def print_pipeline(project_dir):
    state_file = os.path.join(project_dir, ".essay-state", "pipeline-state.json")
    if not os.path.isfile(state_file):
        print(f"{_DOC} No active pipeline. Start one with /tech-essay-writer.")
        return

    d = read_json(state_file)
    if d is None:
        print(f"{_DOC} Active Pipeline:")
        print("   (could not read pipeline state)")
        return

    print(f"{_DOC} Active Pipeline:")
    print(f"   Topic:    {d.get('topic', '(none)')}")
    print(f"   Stage:    {d.get('stage', 'unknown')}")
    print(f"   Language: {d.get('language', 'en')}")
    print(f"   Draft v:  {d.get('draft_version', 0)}")
    print(f"   Reviews:  {len(d.get('reviews', {}))}/8")
    print(f"   Complete: {d.get('completed', False)}")

    # Quality score
    quality_file = os.path.join(project_dir, ".essay-state", "quality-score.json")
    qd = read_json(quality_file)
    if qd:
        print(f"   Quality: {qd.get('composite_score', '?')}/10 ({qd.get('readiness', '?')})")

    # Checkpoints
    cp_index = os.path.join(project_dir, ".essay-state", "checkpoints", "index.json")
    cpd = read_json(cp_index)
    if cpd is not None and isinstance(cpd, list):
        print(f"   Checkpoints: {len(cpd)} saved")


def print_capabilities():
    print(f"{_WRENCH} Capabilities:")
    print(f"   Pipeline:    7-stage (intake {_ARROW} research {_ARROW} outline {_ARROW} draft {_ARROW} review {_ARROW} refine {_ARROW} polish)")
    print("   Reviewers:   8 agents (technical, editor, adversarial, audience, seo, external, factcheck, chinese)")
    print("   Platforms:   7 (internal, external, medium, dev.to, hashnode, wechat, juejin)")
    print(f"   Templates:   {count_templates()} article types")
    print("   Languages:   English + Chinese (with platform-specific formatting)")


def print_author_profile():
    print(f"{_PERSON} Author Profile:")
    path = os.path.join(CONFIG_DIR, "author-profile.json")
    d = read_json(path)
    if d is None:
        print("   Not configured. Run: bash scripts/author-profile.sh init")
        return

    name = d.get("name", "(not set)")
    bio = d.get("bio", "(not set)")
    expertise = ", ".join(d.get("expertise", [])) or "(not set)"
    print(f"   Name:      {name}")
    if len(bio) > 60:
        print(f"   Bio:       {bio[:60]}...")
    else:
        print(f"   Bio:       {bio}")
    print(f"   Expertise: {expertise}")


def print_taste_memory():
    print(f"{_PALETTE} Taste Memory:")
    path = os.path.join(CONFIG_DIR, "taste-memory.json")
    d = read_json(path)
    if d is None:
        print("   No taste data yet. It builds as you write articles.")
        return

    articles = d.get("articles_written", 0)
    patterns = len(d.get("learned_patterns", []))
    prefs = len(d.get("explicit_preferences", []))
    print(f"   Articles tracked: {articles}")
    print(f"   Learned patterns: {patterns}")
    print(f"   Explicit prefs:   {prefs}")


def print_expertise_graph():
    print(f"{_CHART} Expertise Graph:")
    path = os.path.join(CONFIG_DIR, "expertise-graph.json")
    d = read_json(path)
    if d is None:
        print("   No expertise data yet.")
        return

    topics = d.get("topics", {})
    if not topics:
        print("   No topics tracked yet.")
        return

    sorted_t = sorted(topics.items(), key=lambda x: x[1].get("authority_score", 0), reverse=True)
    for name, data in sorted_t[:5]:
        score = data.get("authority_score", 0)
        count = data.get("article_count", 0)
        print(f"   {name}: {score:.1f} authority ({count} articles)")


def print_published_articles():
    print(f"{_BOOKS} Published Articles:")
    path = os.path.join(CONFIG_DIR, "published-articles.json")
    d = read_json(path)
    if d is None:
        print("   None yet. Publish your first article!")
        return

    articles = d.get("articles", [])
    print(f"   Total: {len(articles)}")
    for a in articles[-3:]:
        title = a.get("title", "?")[:50]
        print(f"   {_BULLET} {title}")


def print_configuration():
    print(f"{_GEAR}  Configuration:")
    path = os.path.join(CONFIG_DIR, "config.json")
    d = read_json(path)
    if d is None:
        print("   Using defaults. Run: bash scripts/config.sh init")
        return

    lang = d.get("language", "en")
    platforms = ", ".join(d.get("default_platforms", [])) or "(none)"
    print(f"   Language:  {lang}")
    print(f"   Platforms: {platforms}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        usage()
        sys.exit(0)

    project_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    print(f"{_TL}{_H * 50}{_TR}")
    print(f"{_V}      Tech Essay Writer {_DASH} Project Summary         {_V}")
    print(f"{_BL}{_H * 50}{_BR}")
    print()

    print_pipeline(project_dir)
    print()

    print_capabilities()
    print()

    print_author_profile()
    print()

    print_taste_memory()
    print()

    print_expertise_graph()
    print()

    print_published_articles()
    print()

    print_configuration()
    print()

    print("Run 'bash scripts/dry-run.sh <dir>' to test the pipeline.")


if __name__ == "__main__":
    main()
