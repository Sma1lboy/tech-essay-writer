#!/usr/bin/env python3
"""Main orchestration engine for the tech-essay-writer pipeline.
Called by the conductor (SKILL.md) to manage pipeline progression.
Usage: orchestrate.py <project_dir> <skill_dir> <command> [args...]
"""

import glob
import json
import os
import subprocess
import sys

from utils import read_json_file

# ─── Global state set by main() ─────────────────────────────────────────────
project_dir = ""
skill_dir = ""
state_dir = ""

# ─── Caching layer ──────────────────────────────────────────────────────────
_cache = {}


def cached_taste_memory():
    if "taste_memory" not in _cache:
        path = os.path.expanduser("~/.tech-essay-writer/taste-memory.json")
        _cache["taste_memory"] = read_if_exists(path)
    return _cache["taste_memory"]


def cached_language():
    if "language" not in _cache:
        lang = "en"
        ps_path = os.path.join(state_dir, "pipeline-state.json")
        if os.path.isfile(ps_path):
            data = read_json_file(ps_path)
            lang = data.get("language", "en") or "en"
        _cache["language"] = lang
    return _cache["language"]


def cached_series_id():
    if "series_id" not in _cache:
        sid = ""
        ps_path = os.path.join(state_dir, "pipeline-state.json")
        if os.path.isfile(ps_path):
            data = read_json_file(ps_path)
            sid = data.get("series_id", "") or ""
        _cache["series_id"] = sid
    return _cache["series_id"]


def cached_series_context():
    if "series_context" not in _cache:
        ctx = ""
        sid = cached_series_id()
        if sid:
            try:
                result = subprocess.run(
                    ["bash", os.path.join(skill_dir, "scripts/series-manager.sh"), "context", sid],
                    capture_output=True, text=True, check=False,
                )
                ctx = result.stdout.strip()
            except Exception:
                ctx = ""
        _cache["series_context"] = ctx
    return _cache["series_context"]


def cached_research():
    if "research" not in _cache:
        _cache["research"] = read_if_exists(os.path.join(state_dir, "research-synthesis.json"))
    return _cache["research"]


def cached_materials():
    if "materials" not in _cache:
        _cache["materials"] = read_if_exists(os.path.join(state_dir, "materials.json"))
    return _cache["materials"]


def cached_pipeline_topic():
    if "pipeline_topic" not in _cache:
        topic = ""
        ps_path = os.path.join(state_dir, "pipeline-state.json")
        if os.path.isfile(ps_path):
            data = read_json_file(ps_path)
            topic = data.get("topic", "") or ""
        _cache["pipeline_topic"] = topic
    return _cache["pipeline_topic"]


# ─── Core helpers ────────────────────────────────────────────────────────────

def read_prompt(template):
    """Read file at skill_dir/prompts/{template}. Error if not found."""
    path = os.path.join(skill_dir, "prompts", template)
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()
    print(f"ERROR: Template not found: {template}", file=sys.stderr)
    sys.exit(1)


def read_if_exists(path):
    """Read file content if exists, else return empty string."""
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()
    return ""


def latest_draft():
    """Find highest draft-v{N}.md in state_dir. Return path or empty string."""
    for i in range(10, 0, -1):
        p = os.path.join(state_dir, f"draft-v{i}.md")
        if os.path.isfile(p):
            return p
    return ""


def latest_draft_version():
    """Return latest draft version number as string, or '0'."""
    for i in range(10, 0, -1):
        p = os.path.join(state_dir, f"draft-v{i}.md")
        if os.path.isfile(p):
            return str(i)
    return "0"


def build_language_directive():
    """Return language directive text based on cached language."""
    lang = cached_language()
    if lang == "zh":
        return (
            "\n## Language Directive\n\n"
            "Write all output (article text, analysis, suggestions) in Chinese (\u4e2d\u6587). "
            "Technical terms, code, and JSON keys should remain in English. "
            "Article prose, section titles, hooks, transitions, and all reader-facing text must be in Chinese."
        )
    return (
        "\n## Language Directive\n\n"
        "Write all output (article text, analysis, suggestions) in English."
    )


def get_series_context_section():
    """Return series context markdown section if available."""
    ctx = cached_series_context()
    if ctx:
        return (
            "\n## Series Context\n\n"
            "This article is part of a series. Consider the series arc and previous articles when writing.\n\n"
            f"```json\n{ctx}\n```"
        )
    return ""


def get_series_nav_section():
    """Return series navigation section if available."""
    ctx = cached_series_context()
    if ctx:
        return (
            "\n## Series Navigation\n\n"
            "Include series navigation links (previous/next article) where the format supports it.\n\n"
            f"```json\n{ctx}\n```"
        )
    return ""


def _find_draft_or_final():
    """Find latest draft or final article path. Return path or empty string."""
    dp = latest_draft()
    if dp:
        return dp
    for f in [os.path.join(state_dir, "final-external.md"),
              os.path.join(state_dir, "final-internal.md")]:
        if os.path.isfile(f):
            return f
    return ""


# ─── Command implementations ────────────────────────────────────────────────

def cmd_status():
    ps_path = os.path.join(state_dir, "pipeline-state.json")
    if not os.path.isfile(ps_path):
        print("NOT_INITIALIZED")
        return 0
    d = read_json_file(ps_path)
    stage = d.get("stage", "unknown")
    topic = d.get("topic", "unknown")
    draft_v = d.get("draft_version", 0)
    ref_round = d.get("refinement_round", 0)
    reviews = len(d.get("reviews", {}))
    completed = d.get("completed", False)
    print(f"Stage: {stage}")
    print(f"Topic: {topic}")
    print(f"Draft version: {draft_v}")
    print(f"Refinement round: {ref_round}/3")
    print(f"Reviews: {reviews}/7")
    print(f"Completed: {completed}")
    return 0


def cmd_next_stage():
    ps_path = os.path.join(state_dir, "pipeline-state.json")
    if not os.path.isfile(ps_path):
        print("intake")
        return 0
    d = read_json_file(ps_path)
    stage = d.get("stage", "intake")

    if stage == "complete":
        print("complete")
    elif stage == "intake":
        mat_path = os.path.join(state_dir, "materials.json")
        if os.path.isfile(mat_path):
            m = read_json_file(mat_path)
            if m.get("source_count", 0) > 0:
                print("research")
            else:
                print("intake")
        else:
            print("intake")
    elif stage == "research":
        if os.path.isfile(os.path.join(state_dir, "research-synthesis.json")):
            print("outline")
        else:
            print("research")
    elif stage == "outline":
        has_outline = any(
            os.path.isfile(os.path.join(state_dir, f"outline-{v}.json"))
            for v in ["A", "B", "C"]
        )
        has_critique = os.path.isfile(os.path.join(state_dir, "outline-critique.json"))
        if has_outline and d.get("outline_variant"):
            print("draft")
        elif has_outline and has_critique:
            print("outline_choice")
        elif has_outline:
            print("outline_critique")
        else:
            print("outline")
    elif stage == "draft":
        if os.path.isfile(os.path.join(state_dir, "draft-v1.md")):
            print("review")
        else:
            print("draft")
    elif stage == "review":
        if d.get("review_panel_complete"):
            print("refinement")
        else:
            print("review")
    elif stage == "refinement":
        ref = d.get("refinement_round", 0)
        if ref >= d.get("max_refinement_rounds", 3):
            print("polish")
        else:
            print("refinement")
    elif stage == "polish":
        has_int = os.path.isfile(os.path.join(state_dir, "final-internal.md"))
        has_ext = os.path.isfile(os.path.join(state_dir, "final-external.md"))
        if has_int and has_ext:
            print("complete")
        else:
            print("polish")
    else:
        print(stage)
    return 0


def cmd_build_intake_summary():
    materials = read_if_exists(os.path.join(state_dir, "materials.json"))
    if not materials:
        print("No materials collected yet.")
        return 0
    d = json.loads(materials)
    print("## Materials Summary")
    print(f"Sources: {d.get('source_count', 0)}")
    for s in d.get("sources", []):
        t = s.get("type", "?")
        if t == "url":
            print(f"- URL: {s.get('title', s.get('url', '?'))}")
        elif t == "note":
            print(f"- Note: {s.get('content', '')[:80]}...")
        elif t == "file":
            print(f"- File: {s.get('path', '?')}")
        elif t == "code":
            print(f"- Code: {s.get('language', '?')} snippet")
    if d.get("themes"):
        print(f"\nThemes: {', '.join(d['themes'])}")
    if d.get("potential_angles"):
        print(f"Angles: {', '.join(d['potential_angles'])}")
    return 0


def cmd_build_research_prompt():
    materials = cached_materials() or "{}"
    taste = cached_taste_memory() or "{}"

    prompt = read_prompt("researcher.md")
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Materials Data

```json
{materials}
```

## Taste Memory (style preferences from prior articles)

```json
{taste}
```
{lang_dir}

## Instructions

1. Analyze all provided materials thoroughly
2. Use WebSearch to check the competitive landscape for this topic
3. Write your complete analysis to `.essay-state/research-synthesis.json`
4. Be specific — no generic observations. Ground everything in the actual materials.""")
    return 0


def cmd_build_outline_prompts(args):
    if not args:
        print("ERROR: variant A|B|C required", file=sys.stderr)
        return 1
    variant = args[0]

    research = cached_research() or "{}"
    materials = cached_materials() or "{}"
    taste = cached_taste_memory() or "{}"

    template_map = {"A": "tutorial.md", "B": "deep-dive.md", "C": "narrative.md"}
    template_name = template_map.get(variant, "")
    template_content = ""
    if template_name:
        tpath = os.path.join(skill_dir, "templates", template_name)
        if os.path.isfile(tpath):
            with open(tpath) as f:
                template_content = f.read()

    prompt = read_prompt("outliner.md")
    series_ctx = get_series_context_section()
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Your Assigned Variant: {variant}

Generate outline variant {variant} as described in the variant styles above.

## Article Type Template Reference

{template_content or "(no template available)"}

## Research Synthesis

```json
{research}
```

## Raw Materials (for reference)

```json
{materials}
```

## Taste Memory

```json
{taste}
```
{series_ctx}
{lang_dir}

## Instructions

1. Read the research synthesis carefully — your outline must serve the thesis
2. Generate outline variant {variant} following the style guide above
3. Write your outline to `.essay-state/outline-{variant}.json`
4. Make the hook SPECIFIC and SURPRISING — not generic
5. Every section needs a clear purpose and transition""")
    return 0


def cmd_build_outline_critique_prompt():
    outline_a = read_if_exists(os.path.join(state_dir, "outline-A.json")) or "{}"
    outline_b = read_if_exists(os.path.join(state_dir, "outline-B.json")) or "{}"
    outline_c = read_if_exists(os.path.join(state_dir, "outline-C.json")) or "{}"
    research = cached_research() or "{}"
    taste = cached_taste_memory() or "{}"

    prompt = read_prompt("outline-critic.md")
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Outline A

```json
{outline_a}
```

## Outline B

```json
{outline_b}
```

## Outline C

```json
{outline_c}
```

## Research Synthesis

```json
{research}
```

## Taste Memory

```json
{taste}
```
{lang_dir}

## Instructions

1. Read all 3 outlines and the research synthesis carefully
2. Analyze each outline for structural strengths and weaknesses
3. Compare the outlines across all dimensions
4. Write your critique to `.essay-state/outline-critique.json`
5. Be specific — reference exact section names, not vague observations""")
    return 0


def cmd_build_outline_mix(args):
    if not args:
        print("ERROR: sections_spec or 'list' required", file=sys.stderr)
        return 1
    spec_or_cmd = args[0]
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/outline-mixer.sh"), project_dir, spec_or_cmd],
        check=False,
    )
    return 0


def cmd_build_writer_prompt(args):
    chosen_outline = args[0] if args else ""
    outline_content = ""

    if chosen_outline:
        opath = os.path.join(state_dir, f"outline-{chosen_outline}.json")
        if os.path.isfile(opath):
            with open(opath) as f:
                outline_content = f.read()

    if not outline_content:
        for v in ["A", "B", "C"]:
            opath = os.path.join(state_dir, f"outline-{v}.json")
            if os.path.isfile(opath):
                with open(opath) as f:
                    outline_content = f.read()
                break

    research = cached_research() or "{}"
    materials = cached_materials() or "{}"
    taste = cached_taste_memory() or "{}"

    prompt = read_prompt("writer.md")
    series_ctx = get_series_context_section()
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Chosen Outline

```json
{outline_content or "{}"}
```

## Research Synthesis

```json
{research}
```

## Raw Materials (for code examples and details)

```json
{materials}
```

## Taste Memory (match this style)

```json
{taste}
```
{series_ctx}
{lang_dir}

## Instructions

1. Write the COMPLETE article following the outline exactly
2. Use real, runnable code examples from the materials
3. Match the tone and voice specified in the outline
4. Hit the target word count (+-10%)
5. Output to `.essay-state/draft-v1.md`""")
    return 0


def cmd_build_review_prompts(args):
    if not args:
        print("ERROR: reviewer name required", file=sys.stderr)
        return 1
    reviewer = args[0]

    template_map = {
        "technical": "reviewer-technical.md",
        "editor": "reviewer-editor.md",
        "adversarial": "reviewer-adversarial.md",
        "audience": "reviewer-audience.md",
        "seo": "reviewer-seo.md",
        "external": "reviewer-external.md",
        "factcheck": "reviewer-factcheck.md",
        "chinese": "reviewer-chinese.md",
    }

    # Chinese reviewer only when language=zh
    if reviewer == "chinese":
        lang = cached_language()
        if lang != "zh":
            print(f"ERROR: Chinese reviewer is only available when language=zh (current: {lang})", file=sys.stderr)
            return 1

    template = template_map.get(reviewer)
    if not template:
        print(f"ERROR: Unknown reviewer: {reviewer}", file=sys.stderr)
        return 1

    draft_path = latest_draft()
    draft_content = ""
    if draft_path:
        with open(draft_path) as f:
            draft_content = f.read()

    research = cached_research() or "{}"
    lang_dir = build_language_directive()

    prompt = read_prompt(template)

    print(f"""{prompt}

## Article Draft to Review

{draft_content or "(no draft available)"}

## Research Context (for reference only — review the ARTICLE, not this)

```json
{research}
```
{lang_dir}

## Instructions

1. Review the article thoroughly according to your role above
2. Be specific — reference exact sections, paragraphs, code blocks
3. Write your review to `.essay-state/review-{reviewer}.json`
4. If you can't find real issues, say so — don't manufacture criticism""")
    return 0


def cmd_build_refiner_prompt(args):
    round_num = args[0] if args else "1"

    draft_path = latest_draft()
    draft_content = ""
    if draft_path:
        with open(draft_path) as f:
            draft_content = f.read()

    panel_summary = read_if_exists(os.path.join(state_dir, "review-panel-summary.json")) or "{}"

    outline = ""
    for v in ["A", "B", "C"]:
        opath = os.path.join(state_dir, f"outline-{v}.json")
        if os.path.isfile(opath):
            with open(opath) as f:
                outline = f.read()
            break

    draft_version = latest_draft_version()
    next_version = int(draft_version) + 1

    prompt = read_prompt("refiner.md")
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Current Draft (v{draft_version})

{draft_content or "(no draft available)"}

## Review Panel Summary

```json
{panel_summary}
```

## Original Outline (to prevent scope drift)

```json
{outline or "{}"}
```

## Refinement Round: {round_num} / 3
{lang_dir}

## Instructions

1. Read ALL review feedback in the panel summary
2. Address issues in priority order (critical -> major -> minor)
3. Write refined draft to `.essay-state/draft-v{next_version}.md`
4. Write change log to `.essay-state/refinement-{round_num}-changes.json`
5. Do NOT rewrite sections that weren't flagged""")
    return 0


def cmd_list_platforms():
    print("internal")
    print("external")
    print("medium")
    print("devto")
    print("hashnode")
    print("wechat")
    print("juejin")
    return 0


def cmd_build_format_prompts(args):
    if not args:
        print("ERROR: format internal|external|medium|devto|hashnode|wechat|juejin required", file=sys.stderr)
        return 1
    fmt = args[0]

    template_map = {
        "internal": "formatter-internal.md",
        "external": "formatter-external.md",
        "medium": "formatter-medium.md",
        "devto": "formatter-devto.md",
        "hashnode": "formatter-hashnode.md",
        "wechat": "formatter-wechat.md",
        "juejin": "formatter-juejin.md",
    }
    template = template_map.get(fmt)
    if not template:
        print(f"ERROR: Unknown format: {fmt}", file=sys.stderr)
        return 1

    draft_path = latest_draft()
    draft_content = ""
    if draft_path:
        with open(draft_path) as f:
            draft_content = f.read()

    seo_review = read_if_exists(os.path.join(state_dir, "review-seo.json")) or "{}"
    audience_review = read_if_exists(os.path.join(state_dir, "review-audience.json")) or "{}"
    taste = cached_taste_memory() or "{}"

    # Author profile data via subprocess
    author_profile = ""
    author_bio = ""
    try:
        r = subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/author-profile.sh"), "read"],
            capture_output=True, text=True, check=False,
        )
        author_profile = r.stdout.strip()
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/author-profile.sh"), "get-bio"],
            capture_output=True, text=True, check=False,
        )
        author_bio = r.stdout.strip()
    except Exception:
        pass

    # Cross-references for the topic
    xrefs = ""
    topic = cached_pipeline_topic()
    pub_path = os.path.expanduser("~/.tech-essay-writer/published-articles.json")
    if topic and os.path.isfile(pub_path):
        try:
            r = subprocess.run(
                ["bash", os.path.join(skill_dir, "scripts/cross-reference.sh"), "suggest", topic],
                capture_output=True, text=True, check=False,
            )
            xrefs = r.stdout.strip()
        except Exception:
            pass

    prompt = read_prompt(template)
    series_nav = get_series_nav_section()
    lang_dir = build_language_directive()

    extra_instruction = ""
    if fmt == "external":
        extra_instruction = 'Also write social media package to `.essay-state/social-package.json`'

    print(f"""{prompt}

## Refined Draft

{draft_content or "(no draft available)"}

## SEO Review Data

```json
{seo_review}
```

## Audience Review Data

```json
{audience_review}
```

## Taste Memory

```json
{taste}
```

## Author Profile

{author_profile or "(no author profile configured)"}

Author bio line: {author_bio or "(not set)"}

## Previously Published Articles (for cross-referencing)

{xrefs or "(no published articles to cross-reference)"}
{series_nav}
{lang_dir}

## Instructions

Write the {fmt} version to `.essay-state/final-{fmt}.md`
Where relevant, cross-reference the author's previously published articles listed above.
Include author bio/expertise where the format supports it.
{extra_instruction}""")
    return 0


def cmd_build_social_prompt():
    draft_path = latest_draft()
    draft_content = ""
    if draft_path:
        with open(draft_path) as f:
            draft_content = f.read()

    # Author profile
    author_profile_json = ""
    try:
        r = subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/author-profile.sh"), "read"],
            capture_output=True, text=True, check=False,
        )
        author_profile_json = r.stdout.strip() or "(no author profile)"
    except Exception:
        author_profile_json = "(no author profile)"

    # Expertise graph
    expertise_graph_json = ""
    try:
        r = subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/expertise-graph.sh"), "read"],
            capture_output=True, text=True, check=False,
        )
        expertise_graph_json = r.stdout.strip() or "{}"
    except Exception:
        expertise_graph_json = "{}"

    seo_review = read_if_exists(os.path.join(state_dir, "review-seo.json")) or "{}"

    prompt = read_prompt("social-package.md")
    lang_dir = build_language_directive()

    print(f"""{prompt}

## Refined Draft

{draft_content or "(no draft available)"}

## Author Profile Data

{author_profile_json}

## Expertise Graph Data

```json
{expertise_graph_json}
```

## SEO Review Data

```json
{seo_review}
```
{lang_dir}

## Instructions

1. Read the article draft and understand its key points, unique angle, and target audience
2. Generate the complete social media package following the format specification above
3. Use the author profile to write authentic CTAs with correct handles
4. Use the expertise graph to position the author's authority on this topic
5. Write the package to `.essay-state/social-package.json`""")
    return 0


def cmd_build_calibration_summary():
    calibration = read_if_exists(os.path.join(state_dir, "review-calibration.json"))
    if not calibration:
        print("No calibration data available. Run calibrate-reviews.sh first.")
        return 0

    cal = json.loads(calibration)

    print("## Review Panel Calibration Report")
    print()

    avg = cal.get("panel_average", 0)
    agreement = cal.get("agreement_score", 0)
    print(f"**Panel Average Score:** {avg}/10")
    print(f"**Inter-Reviewer Agreement:** {agreement}/10")
    print()

    # Normalized scores
    print("### Normalized Scores")
    for name, data in cal.get("normalized_scores", {}).items():
        orig = data.get("original_rating", "?")
        score = data.get("numeric_score", "?")
        print(f"- {name}: {orig} -> {score}/10")
    print()

    # Outliers
    outliers = cal.get("outliers", [])
    if outliers:
        print("### Outlier Reviewers")
        for o in outliers:
            print(f'- **{o["reviewer"]}** ({o["direction"]}): scored {o["score"]}/10 vs panel avg {o["panel_average"]}/10')
        print()

    # Blind spots
    spots = cal.get("blind_spots", [])
    if spots:
        print("### Blind Spots (Uncovered Topics)")
        for s in spots:
            print(f'- **{s["topic"]}**: {s["description"]}')
            expected = ", ".join(s["expected_reviewers"])
            print(f"  Expected from: {expected}")
        print()

    # Disagreements
    disag = cal.get("disagreements", [])
    if disag:
        print("### Disagreements")
        for d in disag:
            print(f'- Rating spread: {d["spread"]} points ({d["highest"]["reviewers"]} high vs {d["lowest"]["reviewers"]} low)')
        print()

    # Notes
    notes = cal.get("calibration_notes", [])
    if notes:
        print("### Calibration Notes")
        for n in notes:
            print(f"- {n}")
    return 0


def cmd_build_influence_score(args):
    verbose = args[0] if args else ""
    cmd = ["bash", os.path.join(skill_dir, "scripts/influence-score.sh"), project_dir, skill_dir]
    if verbose:
        cmd.append(verbose)
    subprocess.run(cmd, check=False)
    return 0


def cmd_build_seo_metadata(args):
    verbose = args[0] if args else ""
    cmd = ["bash", os.path.join(skill_dir, "scripts/seo-metadata.sh"), project_dir]
    if verbose:
        cmd.append(verbose)
    subprocess.run(cmd, check=False)
    return 0


def cmd_build_topic_research(args):
    topic = args[0] if args else ""
    if not topic:
        topic = cached_pipeline_topic()
    if not topic:
        print('{"error":"topic required -- pass as argument or set in pipeline-state.json"}', file=sys.stderr)
        return 1
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/topic-research.sh"), project_dir, topic],
        check=False,
    )
    return 0


def cmd_build_title_variations(args):
    count = args[0] if args else "10"
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/title-generator.sh"), project_dir, count],
        check=False,
    )
    return 0


def cmd_build_hook_variations(args):
    style = args[0] if args else "all"
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/hook-workshop.sh"), project_dir, style],
        check=False,
    )
    return 0


def cmd_build_code_validation():
    draft_path = _find_draft_or_final()
    if not draft_path:
        print('{"error":"no draft or final article found to validate"}')
        return 1
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/code-validate.sh"), draft_path],
        check=False,
    )
    return 0


def cmd_build_diagram_suggestions(args):
    verbose = args[0] if args else ""
    draft_path = _find_draft_or_final()
    if not draft_path:
        print('{"error":"no draft or final article found for diagram suggestions"}')
        return 1
    cmd = ["bash", os.path.join(skill_dir, "scripts/diagram-suggest.sh"), draft_path]
    if verbose:
        cmd.append(verbose)
    subprocess.run(cmd, check=False)
    return 0


def cmd_build_readability_report(args):
    verbose = args[0] if args else ""
    draft_path = _find_draft_or_final()
    if not draft_path:
        print('{"error":"no draft or final article found for readability analysis"}')
        return 1
    cmd = ["bash", os.path.join(skill_dir, "scripts/readability-score.sh"), draft_path]
    if verbose:
        cmd.append(verbose)
    subprocess.run(cmd, check=False)
    return 0


def cmd_build_word_analysis(args):
    top_n = args[0] if args else "25"
    draft_path = _find_draft_or_final()
    if not draft_path:
        print('{"error":"no draft or final article found for word analysis"}')
        return 1
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/word-frequency.sh"), draft_path, top_n],
        check=False,
    )
    return 0


def cmd_build_series_context():
    series_id = cached_series_id()
    if series_id:
        context = cached_series_context()
        if context:
            print("## Series Context")
            print()
            print("This article is part of a series. Here is the series context:")
            print()
            print("```json")
            print(context)
            print("```")
            print()
            print("**Writing guidance**: Build on previous articles in the series. Reference prior entries where relevant for continuity.")
        else:
            print(f"(series {series_id} not found)")
    else:
        print("(no series associated with this article)")
    return 0


def cmd_build_analytics_insights():
    taste = cached_taste_memory()
    if not taste:
        print("(no performance insights available)")
        return 0

    taste_data = json.loads(taste)
    insights = taste_data.get("performance_insights")
    if not insights:
        print("(no performance insights available)")
        return 0

    print("## Performance Insights")
    print()
    print("Based on analytics from published articles:")
    print()
    tags = insights.get("best_performing_tags", [])
    if tags:
        print(f"Best performing tags: {', '.join(tags[:5])}")
    fmt = insights.get("best_performing_format", "")
    if fmt and fmt != "unknown":
        print(f"Best performing format: {fmt}")
    avg_v = insights.get("avg_views", 0)
    if avg_v:
        print(f"Average views: {avg_v}")
    for i in insights.get("insights", []):
        print(f"- {i}")
    return 0


def cmd_build_analytics_summary():
    result = subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/analytics-feedback.sh"), "trends"],
        capture_output=True, text=True, check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    else:
        print("(no analytics data available)")
    return 0


def cmd_build_config_summary():
    config_file = os.path.expanduser("~/.tech-essay-writer/config.json")
    if not os.path.isfile(config_file):
        print("(no user config -- using defaults)")
        return 0
    config = read_json_file(config_file)
    platforms = config.get("default_platforms", [])
    audiences = config.get("target_audiences", [])
    print("## User Configuration")
    print()
    print(f"Default platforms: {', '.join(platforms)}")
    print(f"Writing style: {config.get('writing_style', 'technical')}")
    print(f"Target audiences: {', '.join(audiences)}")
    print(f"Language: {config.get('language', 'en')}")
    print(f"Use author profile: {config.get('use_author_profile', True)}")
    print(f"Max refinement rounds: {config.get('max_refinement_rounds', 3)}")
    return 0


def cmd_check_convergence(args):
    round_num = args[0] if args else "1"
    adv_review = read_if_exists(os.path.join(state_dir, "review-adversarial.json"))

    if not adv_review:
        print("NO_REVIEW")
        return 0

    review = json.loads(adv_review)
    rnd = int(round_num)
    rating = review.get("rating", "UNKNOWN")

    if rating == "SOLID":
        print("CONVERGED")
    elif rnd >= 3:
        print("MAX_ROUNDS")
    else:
        attacks = review.get("attacks", [])
        serious = [a for a in attacks if a.get("severity") in ("devastating", "significant")]
        if len(serious) == 0:
            print("CONVERGED")
        else:
            print("CONTINUE")
    return 0


def cmd_show_progress(args):
    cmd = ["bash", os.path.join(skill_dir, "scripts/progress-display.sh"), project_dir] + list(args)
    subprocess.run(cmd, check=False)
    return 0


def cmd_publishing_guide(args):
    if not args:
        print("ERROR: platform required", file=sys.stderr)
        return 1
    platform = args[0]
    rest = list(args[1:])
    cmd = ["bash", os.path.join(skill_dir, "scripts/publishing-guide.sh"), platform, project_dir] + rest
    subprocess.run(cmd, check=False)
    return 0


def cmd_list_checkpoints():
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/checkpoint.sh"), "list", project_dir],
        check=False,
    )
    return 0


def cmd_rollback(args):
    if not args:
        print("ERROR: checkpoint id required", file=sys.stderr)
        return 1
    ckpt_id = args[0]
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/checkpoint.sh"), "rollback", project_dir, ckpt_id],
        check=False,
    )
    return 0


def cmd_retry_stage(args):
    if not args:
        print("ERROR: stage required", file=sys.stderr)
        return 1
    stage = args[0]
    valid_stages = ["intake", "research", "outline", "draft", "review", "refinement", "polish"]
    if stage not in valid_stages:
        print(f"ERROR: Cannot retry stage '{stage}'. Valid: {' '.join(valid_stages)}", file=sys.stderr)
        return 1

    # Map target stage to preceding stage for checkpoint lookup
    preceding_map = {
        "research": "intake",
        "outline": "research",
        "draft": "outline",
        "review": "draft",
        "refinement": "review",
        "polish": "refinement",
    }
    preceding = preceding_map.get(stage, "")

    # Try to rollback to the preceding stage's checkpoint
    if preceding:
        ckpt_base = os.path.join(state_dir, "checkpoints")
        found_ckpt = ""
        if os.path.isdir(ckpt_base):
            matches = []
            for name in os.listdir(ckpt_base):
                full = os.path.join(ckpt_base, name)
                if not os.path.isdir(full) or name.startswith("."):
                    continue
                parts = name.rsplit("-", 1)
                label = parts[0] if len(parts) == 2 else name
                ts = parts[1] if len(parts) == 2 else ""
                if label == preceding:
                    matches.append((name, ts))
            matches.sort(key=lambda x: x[1])
            if matches:
                found_ckpt = matches[-1][0]

        if found_ckpt:
            print(f"Rolling back to checkpoint: {found_ckpt}")
            subprocess.run(
                ["bash", os.path.join(skill_dir, "scripts/checkpoint.sh"), "rollback", project_dir, found_ckpt],
                check=False,
            )
        else:
            print(f"No checkpoint found for '{preceding}'. Resetting stage only.")

    # Set stage directly (use set-field to avoid triggering another auto-snapshot)
    subprocess.run(
        ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "stage", stage],
        capture_output=True, check=False,
    )

    # Clear artifacts for the target stage
    if stage == "intake":
        p = os.path.join(state_dir, "materials.json")
        if os.path.isfile(p):
            os.unlink(p)

    elif stage == "research":
        p = os.path.join(state_dir, "research-synthesis.json")
        if os.path.isfile(p):
            os.unlink(p)

    elif stage == "outline":
        for v in ["A", "B", "C"]:
            p = os.path.join(state_dir, f"outline-{v}.json")
            if os.path.isfile(p):
                os.unlink(p)
        p = os.path.join(state_dir, "outline-critique.json")
        if os.path.isfile(p):
            os.unlink(p)
        subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "outline_variant", "null"],
            capture_output=True, check=False,
        )

    elif stage == "draft":
        for p in glob.glob(os.path.join(state_dir, "draft-v*.md")):
            os.unlink(p)
        subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "draft_version", "0"],
            capture_output=True, check=False,
        )

    elif stage == "review":
        for p in glob.glob(os.path.join(state_dir, "review-*.json")):
            os.unlink(p)
        subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "reviews", "{}"],
            capture_output=True, check=False,
        )
        subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "review_panel_complete", "false"],
            capture_output=True, check=False,
        )

    elif stage == "refinement":
        for p in glob.glob(os.path.join(state_dir, "refinement-*-changes.json")):
            os.unlink(p)
        # Remove subsequent draft versions (keep v1)
        for i in range(10, 1, -1):
            p = os.path.join(state_dir, f"draft-v{i}.md")
            if os.path.isfile(p):
                os.unlink(p)
        subprocess.run(
            ["bash", os.path.join(skill_dir, "scripts/pipeline-state.sh"), "set-field", project_dir, "refinement_round", "0"],
            capture_output=True, check=False,
        )

    elif stage == "polish":
        for p in glob.glob(os.path.join(state_dir, "final-*.md")):
            os.unlink(p)
        for fname in ["social-package.json", "influence-score.json", "seo-metadata.json", "diagram-suggestions.json"]:
            p = os.path.join(state_dir, fname)
            if os.path.isfile(p):
                os.unlink(p)

    print(f"Retry: stage reset to '{stage}', ready for re-execution.")
    return 0


def cmd_resume():
    ps_path = os.path.join(state_dir, "pipeline-state.json")
    if not os.path.isfile(ps_path):
        print("STATUS: not_initialized")
        print("ACTION: Run intake to start a new pipeline")
        return 0

    d = read_json_file(ps_path)
    stage = d.get("stage", "unknown")
    completed = d.get("completed", False)

    if completed:
        print("STATUS: complete")
        print("ACTION: Pipeline already complete. Start a new one or rollback to modify.")
        return 0

    print(f"STATUS: {stage}")

    if stage == "intake":
        mat_path = os.path.join(state_dir, "materials.json")
        if os.path.isfile(mat_path):
            m = read_json_file(mat_path)
            count = m.get("source_count", 0)
            print(f"PROGRESS: {count} material(s) collected")
            if count > 0:
                print("ACTION: Materials ready. Advance to research stage.")
            else:
                print("ACTION: Add materials before advancing.")
        else:
            print("PROGRESS: No materials yet")
            print("ACTION: Add materials (URLs, notes, files, code).")

    elif stage == "research":
        if os.path.isfile(os.path.join(state_dir, "research-synthesis.json")):
            print("PROGRESS: Research synthesis complete")
            print("ACTION: Advance to outline stage.")
        else:
            print("PROGRESS: Research not started")
            print("ACTION: Run research agent.")

    elif stage == "outline":
        outlines = [v for v in ["A", "B", "C"]
                     if os.path.isfile(os.path.join(state_dir, f"outline-{v}.json"))]
        has_critique = os.path.isfile(os.path.join(state_dir, "outline-critique.json"))
        chosen = d.get("outline_variant")
        print(f"PROGRESS: {len(outlines)}/3 outlines, critique={has_critique}, chosen={chosen}")
        if chosen:
            print("ACTION: Advance to draft stage.")
        elif has_critique:
            print("ACTION: Choose an outline variant (A/B/C).")
        elif len(outlines) == 3:
            print("ACTION: Run outline critique agent.")
        elif len(outlines) > 0:
            missing = [v for v in ["A", "B", "C"] if v not in outlines]
            print(f"ACTION: Generate missing outline(s): {missing}")
        else:
            print("ACTION: Generate 3 outline variants.")

    elif stage == "draft":
        drafts = [f for f in os.listdir(state_dir) if f.startswith("draft-v") and f.endswith(".md")]
        if drafts:
            latest = sorted(drafts)[-1]
            print(f"PROGRESS: Draft exists ({latest})")
            print("ACTION: Advance to review stage.")
        else:
            print("PROGRESS: No draft written yet")
            print("ACTION: Run writer agent.")

    elif stage == "review":
        reviews = d.get("reviews", {})
        has_summary = os.path.isfile(os.path.join(state_dir, "review-panel-summary.json"))
        expected = ["technical", "editor", "adversarial", "audience", "seo", "external", "factcheck"]
        done = [r for r in expected
                if r in reviews or os.path.isfile(os.path.join(state_dir, f"review-{r}.json"))]
        missing = [r for r in expected if r not in done]
        print(f"PROGRESS: {len(done)}/7 reviews complete")
        if missing:
            print(f"MISSING: {missing}")
            print(f"ACTION: Run missing reviewer(s): {missing}")
        elif not has_summary:
            print("ACTION: Aggregate reviews (run aggregate-reviews.sh).")
        else:
            print("ACTION: Advance to refinement stage.")

    elif stage == "refinement":
        ref_round = d.get("refinement_round", 0)
        max_rounds = d.get("max_refinement_rounds", 3)
        print(f"PROGRESS: Round {ref_round}/{max_rounds}")
        if ref_round >= max_rounds:
            print("ACTION: Max rounds reached. Advance to polish stage.")
        else:
            print(f"ACTION: Run refinement round {ref_round + 1}.")

    elif stage == "polish":
        has_internal = os.path.isfile(os.path.join(state_dir, "final-internal.md"))
        has_external = os.path.isfile(os.path.join(state_dir, "final-external.md"))
        print(f"PROGRESS: internal={has_internal}, external={has_external}")
        if has_internal and has_external:
            print("ACTION: Both formats ready. Complete the pipeline.")
        elif has_internal:
            print("ACTION: Generate external format.")
        elif has_external:
            print("ACTION: Generate internal format.")
        else:
            print("ACTION: Generate internal and external formats.")
    else:
        print("ACTION: Unknown state. Check pipeline-state.json manually.")
    return 0


def cmd_export(args):
    if not args:
        print("ERROR: export format required", file=sys.stderr)
        return 1
    fmt = args[0]
    output_dir = args[1] if len(args) > 1 else ""
    cmd = ["bash", os.path.join(skill_dir, "scripts/export.sh"), project_dir, fmt]
    if output_dir:
        cmd.append(output_dir)
    subprocess.run(cmd, check=False)
    return 0


def cmd_list_archive(args):
    cmd = ["bash", os.path.join(skill_dir, "scripts/export.sh"), "list-archive"] + list(args)
    subprocess.run(cmd, check=False)
    return 0


# ─── Usage and main dispatch ────────────────────────────────────────────────

def usage():
    print("""Usage: orchestrate.py <project_dir> <skill_dir> <command> [args...]

Commands:
  status              Show current pipeline status
  next-stage          Determine and output the next stage to execute
  build-intake-summary  Build intake summary for user checkpoint
  build-research-prompt Build research agent prompt
  build-outline-prompts Build 3 parallel outline agent prompts
  build-outline-critique-prompt  Build outline adversarial critique prompt
  build-outline-mix <spec|list>  Mix sections from outline variants or list them
  build-writer-prompt   Build writer agent prompt
  build-review-prompts  Build 7 parallel review agent prompts
  build-refiner-prompt  Build refiner agent prompt (with round number)
  build-format-prompts  Build formatter prompts (internal|external|medium|devto|hashnode|wechat|juejin)
  build-social-prompt   Build social media package agent prompt
  build-calibration-summary  Build human-readable calibration summary
  build-influence-score Compute influence score from state data (no agent needed)
  build-seo-metadata    Generate SEO metadata from article + state data (no agent needed)
  build-code-validation Validate code examples in the latest draft
  build-diagram-suggestions Suggest diagrams/images for the latest draft
  build-readability-report  Compute readability metrics (FK grade, passive voice, complexity)
  build-word-analysis       Word frequency, overuse, jargon density, AI pattern detection
  build-series-context  Build series context for injection into writer/formatter prompts
  build-analytics-insights Output performance insights from analytics for prompt injection
  build-analytics-summary Show performance trends and analytics summary
  build-config-summary  Build config context summary for prompt injection
  build-topic-research   Generate research brief (questions, landscape, angles) for a topic
  build-title-variations Generate scored title variations from research data
  build-hook-variations  Generate scored opening hook variations
  list-platforms        List all available platform format names
  check-convergence     Check if refinement loop should continue
  show-progress         Show rich pipeline progress visualization
  publishing-guide      Show per-platform publishing workflow guide
  list-checkpoints      List all saved state checkpoints
  rollback <id>         Restore state from a checkpoint
  retry-stage <stage>   Reset and retry a failed stage
  resume                Detect partial state and advise next action
  export <format> [out] Export articles (bundle|markdown|html|json|archive)
  list-archive [--json] List archived articles""")


def main():
    global project_dir, skill_dir, state_dir

    if len(sys.argv) < 4:
        usage()
        sys.exit(1)

    project_dir = sys.argv[1]
    skill_dir = sys.argv[2]
    cmd = sys.argv[3]
    rest = sys.argv[4:]

    state_dir = os.path.join(project_dir, ".essay-state")

    dispatch = {
        "status": lambda: cmd_status(),
        "next-stage": lambda: cmd_next_stage(),
        "build-intake-summary": lambda: cmd_build_intake_summary(),
        "build-research-prompt": lambda: cmd_build_research_prompt(),
        "build-outline-prompts": lambda: cmd_build_outline_prompts(rest),
        "build-outline-critique-prompt": lambda: cmd_build_outline_critique_prompt(),
        "build-outline-mix": lambda: cmd_build_outline_mix(rest),
        "build-writer-prompt": lambda: cmd_build_writer_prompt(rest),
        "build-review-prompts": lambda: cmd_build_review_prompts(rest),
        "build-refiner-prompt": lambda: cmd_build_refiner_prompt(rest),
        "build-format-prompts": lambda: cmd_build_format_prompts(rest),
        "build-social-prompt": lambda: cmd_build_social_prompt(),
        "build-calibration-summary": lambda: cmd_build_calibration_summary(),
        "build-influence-score": lambda: cmd_build_influence_score(rest),
        "build-seo-metadata": lambda: cmd_build_seo_metadata(rest),
        "build-topic-research": lambda: cmd_build_topic_research(rest),
        "build-title-variations": lambda: cmd_build_title_variations(rest),
        "build-hook-variations": lambda: cmd_build_hook_variations(rest),
        "build-code-validation": lambda: cmd_build_code_validation(),
        "build-diagram-suggestions": lambda: cmd_build_diagram_suggestions(rest),
        "build-readability-report": lambda: cmd_build_readability_report(rest),
        "build-word-analysis": lambda: cmd_build_word_analysis(rest),
        "build-series-context": lambda: cmd_build_series_context(),
        "build-analytics-insights": lambda: cmd_build_analytics_insights(),
        "build-analytics-summary": lambda: cmd_build_analytics_summary(),
        "build-config-summary": lambda: cmd_build_config_summary(),
        "list-platforms": lambda: cmd_list_platforms(),
        "check-convergence": lambda: cmd_check_convergence(rest),
        "show-progress": lambda: cmd_show_progress(rest),
        "publishing-guide": lambda: cmd_publishing_guide(rest),
        "list-checkpoints": lambda: cmd_list_checkpoints(),
        "rollback": lambda: cmd_rollback(rest),
        "retry-stage": lambda: cmd_retry_stage(rest),
        "resume": lambda: cmd_resume(),
        "export": lambda: cmd_export(rest),
        "list-archive": lambda: cmd_list_archive(rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
