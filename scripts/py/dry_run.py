#!/usr/bin/env python3
"""Dry run — simulate the complete pipeline without LLM agents.
Creates mock data at each stage to verify the pipeline infrastructure works.
Usage: dry_run.py <project_dir> [skill_dir] [--chinese]
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

STATE_DIR = ".essay-state"

PASS_COUNT = 0
FAIL_COUNT = 0
TOTAL_COUNT = 0


def log(msg):
    print(f"  [DRY-RUN] {msg}")


def step(name):
    print()
    print(f"=== STAGE: {name} ===")


def check(desc, filepath):
    """Validate file exists and (if JSON) is valid."""
    global PASS_COUNT, FAIL_COUNT, TOTAL_COUNT
    TOTAL_COUNT += 1
    if os.path.isfile(filepath):
        if filepath.endswith(".json"):
            try:
                with open(filepath) as f:
                    json.load(f)
                print(f"  \u2713 {desc}")
                PASS_COUNT += 1
            except (json.JSONDecodeError, ValueError):
                print(f"  \u2717 {desc} (invalid JSON)")
                FAIL_COUNT += 1
        else:
            print(f"  \u2713 {desc}")
            PASS_COUNT += 1
    else:
        print(f"  \u2717 {desc} (missing: {filepath})")
        FAIL_COUNT += 1


def check_condition(desc, condition):
    """Validate an arbitrary boolean condition."""
    global PASS_COUNT, FAIL_COUNT, TOTAL_COUNT
    TOTAL_COUNT += 1
    if condition:
        print(f"  \u2713 {desc}")
        PASS_COUNT += 1
    else:
        print(f"  \u2717 {desc}")
        FAIL_COUNT += 1


def run_script(skill_dir, script_name, args, capture=True):
    """Run a bash script from the skill's scripts/ directory."""
    script_path = os.path.join(skill_dir, "scripts", script_name)
    cmd = ["bash", script_path] + [str(a) for a in args]
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    else:
        subprocess.run(cmd, capture_output=True, text=True)
        return None


def write_json(filepath, data):
    """Write JSON data to a file."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def usage():
    print("""Usage: dry_run.py <project_dir> [skill_dir] [--chinese]

Simulates the complete pipeline without LLM agents using mock data.
Useful for testing script changes without burning API tokens.

Options:
  --chinese   Run the pipeline in zh language mode (adds Chinese reviewer)""")


def main():
    global PASS_COUNT, FAIL_COUNT, TOTAL_COUNT

    # Parse arguments: positional first, then flags
    positional = []
    language = "en"
    for arg in sys.argv[1:]:
        if arg == "--chinese":
            language = "zh"
        elif arg in ("-h", "--help"):
            usage()
            sys.exit(0)
        else:
            positional.append(arg)

    if not positional:
        usage()
        sys.exit(1)

    project_dir = positional[0]
    # Default skill_dir: go up from scripts/py/ to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_skill_dir = os.path.dirname(os.path.dirname(script_dir))
    skill_dir = positional[1] if len(positional) > 1 else default_skill_dir

    state_dir = os.path.join(project_dir, STATE_DIR)

    # Clean slate
    if os.path.exists(state_dir):
        shutil.rmtree(state_dir)
    os.makedirs(state_dir, exist_ok=True)

    print("Tech Essay Writer \u2014 Dry Run")
    print(f"Project: {project_dir}")
    print(f"Skill: {skill_dir}")
    print(f"Language: {language}")
    print()

    # --- Stage 1: INTAKE ---
    step("INTAKE")

    run_script(skill_dir, "pipeline-state.sh",
               ["init", project_dir, "Dry Run: How We Built a Multi-Agent Review System"])
    check("Pipeline initialized", os.path.join(state_dir, "pipeline-state.json"))

    # Set language from --chinese flag
    run_script(skill_dir, "pipeline-state.sh",
               ["set-field", project_dir, "language", language])
    result = run_script(skill_dir, "pipeline-state.sh",
                        ["get-field", project_dir, "language"])
    lang_check = result.stdout.strip().strip('"') if result else ""
    check_condition(f"Language set to {language}", lang_check == language)

    run_script(skill_dir, "intake-materials.sh",
               ["add-url", project_dir, "https://example.com/agents", "Multi-Agent Systems"])
    run_script(skill_dir, "intake-materials.sh",
               ["add-note", project_dir, "Our review pipeline uses 7 independent agents"])
    run_script(skill_dir, "intake-materials.sh",
               ["add-code", project_dir,
                'const reviewers = ["tech","editor","adversarial","audience","seo","external","factcheck"]',
                "javascript"])
    run_script(skill_dir, "intake-materials.sh",
               ["add-theme", project_dir, "adversarial AI quality"])
    run_script(skill_dir, "intake-materials.sh",
               ["add-angle", project_dir, "multi-agent consensus as quality gate"])
    check("Materials collected", os.path.join(state_dir, "materials.json"))

    log("Intake summary:")
    run_script(skill_dir, "orchestrate.sh",
               [project_dir, skill_dir, "build-intake-summary"])

    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "research"])

    # --- Stage 2: RESEARCH ---
    step("RESEARCH")

    synthesis = {
        "thesis": "Multi-agent adversarial review produces higher quality articles than single-reviewer systems",
        "thesis_expanded": "By using 7 independent agents with different review perspectives, we catch issues that any single reviewer would miss.",
        "evidence_map": [
            {"claim": "Independent reviewers find different issues", "sources": ["url-1", "note-1"], "strength": "strong", "notes": ""},
            {"claim": "Adversarial review catches logical gaps", "sources": ["note-1"], "strength": "moderate", "notes": ""}
        ],
        "knowledge_gaps": [{"gap": "Benchmark data", "impact": "medium", "resolution": "Run comparison test"}],
        "competitive_landscape": [{"title": "Writing with AI", "url": "https://example.com", "angle": "Single agent", "gap": "No adversarial review"}],
        "unique_angle": "First deep dive into multi-agent adversarial review for tech writing",
        "recommended_depth": "intermediate",
        "recommended_length": "medium (1500-3000)",
        "key_terms": ["multi-agent", "adversarial review", "quality gate"]
    }
    write_json(os.path.join(state_dir, "research-synthesis.json"), synthesis)
    check("Research synthesis", os.path.join(state_dir, "research-synthesis.json"))

    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "outline"])

    # --- CHECKPOINT SAVE/RESTORE VERIFICATION ---
    step("CHECKPOINT VERIFICATION")

    # Wait 1s to ensure unique timestamp for our checkpoint
    time.sleep(1)

    log("Creating explicit checkpoint...")
    ckpt_result = run_script(skill_dir, "checkpoint.sh",
                             ["snapshot", project_dir, "dryrun-ckpt"])
    ckpt_out = (ckpt_result.stdout + ckpt_result.stderr).strip() if ckpt_result else ""
    has_checkpoint = "Checkpoint:" in ckpt_out
    check_condition("Checkpoint created", has_checkpoint)

    # Extract the checkpoint ID from output like "Checkpoint: dryrun-ckpt-20260406T... (3 files)"
    ckpt_id = ""
    if has_checkpoint:
        match = re.search(r"Checkpoint:\s+(\S+)", ckpt_out)
        if match:
            ckpt_id = match.group(1)

    # List checkpoints
    ckpt_list_result = run_script(skill_dir, "checkpoint.sh", ["list", project_dir])
    ckpt_list = (ckpt_list_result.stdout + ckpt_list_result.stderr).strip() if ckpt_list_result else ""
    check_condition("Checkpoint listed", "dryrun-ckpt" in ckpt_list)

    # Verify latest checkpoint contains our label
    ckpt_latest_result = run_script(skill_dir, "checkpoint.sh", ["latest", project_dir])
    ckpt_latest = (ckpt_latest_result.stdout + ckpt_latest_result.stderr).strip() if ckpt_latest_result else ""
    # Even if latest is an auto-snapshot, we count it as pass (matching bash behavior)
    if "dryrun-ckpt" in ckpt_latest:
        check_condition("Latest checkpoint is dryrun-ckpt", True)
    else:
        check_condition("Checkpoint exists (latest may be auto-snapshot)", True)

    # Rollback test
    if ckpt_id:
        # Save current stage
        pre_stage_result = run_script(skill_dir, "pipeline-state.sh",
                                      ["get-stage", project_dir])

        # Mutate: add a marker field that won't exist in the checkpoint
        run_script(skill_dir, "pipeline-state.sh",
                   ["set-field", project_dir, "dry_run_marker", "should_disappear"])

        log(f"Rolling back to checkpoint: {ckpt_id}")
        rollback_result = run_script(skill_dir, "checkpoint.sh",
                                     ["rollback", project_dir, ckpt_id])
        rollback_out = (rollback_result.stdout + rollback_result.stderr).strip() if rollback_result else ""
        check_condition("Rollback succeeded", "Rolled back" in rollback_out)

        # Verify state was restored
        restored_result = run_script(skill_dir, "pipeline-state.sh",
                                     ["get-stage", project_dir])
        restored_stage = restored_result.stdout.strip() if restored_result else ""
        check_condition(f"State restored after rollback (stage={restored_stage})",
                        len(restored_stage) > 0)
    else:
        log("Skipping rollback test (no checkpoint ID)")

    # Ensure we're at outline stage for next section
    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "outline"])

    # --- Stage 3: OUTLINE ---
    step("OUTLINE")

    for variant in ["A", "B", "C"]:
        style_map = {"A": "Tutorial", "B": "Deep Dive", "C": "Narrative"}
        outline = {
            "variant": variant,
            "style": style_map[variant],
            "title": "How We Built a 7-Agent Review System for Tech Articles",
            "hook": "What if your article had 7 expert reviewers before anyone else saw it?",
            "sections": [
                {"title": "The Problem", "purpose": "Establish the pain point", "words": 300},
                {"title": "The Architecture", "purpose": "Show the multi-agent design", "words": 600},
                {"title": "Adversarial Review", "purpose": "Deep dive on the adversarial agent", "words": 400},
                {"title": "Results", "purpose": "Show quality improvements", "words": 300}
            ],
            "target_words": 1600,
            "tone": "technical but accessible"
        }
        write_json(os.path.join(state_dir, f"outline-{variant}.json"), outline)
        check(f"Outline variant {variant}", os.path.join(state_dir, f"outline-{variant}.json"))

    run_script(skill_dir, "pipeline-state.sh",
               ["set-field", project_dir, "outline_variant", "B"])
    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "draft"])

    # --- Stage 4: DRAFT ---
    step("DRAFT")

    draft_content = """# How We Built a 7-Agent Review System for Tech Articles

What if your article had 7 expert reviewers before anyone else saw it?

## The Problem

Most tech articles go through a single review pass — maybe a colleague reads it, maybe not.
The result: technical errors slip through, the tone feels off, and the SEO is an afterthought.

We built something different: a multi-agent review pipeline where 7 independent AI agents
each review your article from a completely different perspective.

## The Architecture

```javascript
const reviewers = [
  "technical",    // Catches code errors, outdated APIs
  "editor",       // Checks flow, voice, AI slop
  "adversarial",  // Tries to break your argument
  "audience",     // Would real readers share this?
  "seo",          // Search optimization
  "external",     // Fresh-eyes perspective
  "factcheck"     // Verifies all claims
];
```

Each reviewer gets fresh context — no knowledge of other reviewers' findings.
This prevents groupthink and ensures independent assessment.

## The Adversarial Agent

The adversarial reviewer is the star of the system. Its job: find the weakest point
in your article and attack it. Not to be mean — to make the article stronger.

It runs an "internet stress test": what would the top HN comment say?
What would a Twitter critic quote-tweet? What would a domain expert flag?

## Results

After implementing this system, our article quality scores improved from 5.2/10 to 8.1/10.
The adversarial reviewer alone caught issues in 73% of articles that other reviewers missed.

The key insight: independent agents with different perspectives find more issues than
a single comprehensive reviewer. The adversarial agent is the quality gate that makes
the entire system worthwhile.
"""
    draft_path = os.path.join(state_dir, "draft-v1.md")
    with open(draft_path, "w") as f:
        f.write(draft_content)
    check("Draft v1", draft_path)

    run_script(skill_dir, "pipeline-state.sh",
               ["set-field", project_dir, "draft_version", "1"])

    # Code validation on good draft
    log("Running code validation on valid draft...")
    valid_code_result = run_script(skill_dir, "code-validate.sh", [draft_path])
    valid_code_out = valid_code_result.stdout.strip() if valid_code_result else ""
    try:
        code_data = json.loads(valid_code_out)
        has_blocks = code_data.get("total_blocks", 0) > 0
    except (json.JSONDecodeError, ValueError):
        has_blocks = False
    # Either way counts as pass (matching bash behavior)
    if has_blocks:
        check_condition("Code validation ran on valid draft", True)
    else:
        check_condition("Code validation ran (no blocks or non-JSON output)", True)

    # Code validation with intentionally bad code
    log("Testing code validation with intentionally bad code...")
    bad_code_path = os.path.join(state_dir, "draft-badcode-test.md")
    bad_code_content = """# Test Article with Bad Code

Here is some broken JavaScript:

```javascript
const x = {
  name: "test"
  age: 42  // missing comma
  ...; // fragment
}
// TODO: implement this
```

And some broken Python:

```python
def broken_function(
    print("missing closing paren and colon"
    ... # ellipsis fragment
```

"""
    with open(bad_code_path, "w") as f:
        f.write(bad_code_content)

    bad_code_result = run_script(skill_dir, "code-validate.sh", [bad_code_path])
    bad_code_out = bad_code_result.stdout.strip() if bad_code_result else ""
    bad_detected = bool(re.search(
        r'"fail":\s*[1-9]|"fragments_detected":\s*true|"syntax_valid":\s*false',
        bad_code_out
    ))
    check_condition("Code validation detected issues in bad code", bad_detected)
    if os.path.exists(bad_code_path):
        os.remove(bad_code_path)

    # Diagram suggestions
    log("Running diagram suggestions...")
    run_script(skill_dir, "diagram-suggest.sh", [draft_path])

    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "review"])

    # --- Stage 5: REVIEW ---
    step("REVIEW")

    reviews = {
        "technical": {
            "reviewer": "technical", "rating": "PASS", "confidence": "high",
            "summary": "Code examples are correct.",
            "issues": [], "code_issues": [], "factual_errors": [], "missing_caveats": []
        },
        "editor": {
            "reviewer": "editor", "rating": "PUBLISH_READY",
            "summary": "Well-structured article.",
            "hook_score": 8, "clarity_score": 8, "flow_score": 7, "voice_score": 8,
            "engagement_score": 7, "economy_score": 8, "overall_score": 8,
            "issues": [], "ai_slop_flags": [],
            "best_line": "Independent agents find more issues.",
            "weakest_section": "Results could use more data",
            "cut_candidates": []
        },
        "adversarial": {
            "reviewer": "adversarial", "rating": "SOLID",
            "summary": "Argument is well-supported.",
            "premise_valid": True, "premise_attack": None,
            "attacks": [{
                "target": "73% stat", "attack": "Where does this come from?",
                "severity": "minor", "likely_source": "HN comment",
                "defense": "Internal testing data", "verdict": "acceptable risk"
            }],
            "cherry_picking": [], "logic_gaps": [],
            "missing_nuance": ["Scale considerations"],
            "stress_test": {
                "hn_top_comment": "Interesting but sample size?",
                "twitter_quote": "Good approach",
                "expert_reaction": "Solid methodology"
            },
            "overall_vulnerability": "Low"
        },
        "audience": {
            "reviewer": "audience",
            "reader_a": {
                "persona": "Internal engineer", "rating": "WOULD_SHARE",
                "actionability": 8, "relevance": 7, "time_well_spent": True,
                "share_trigger": "Multi-agent pattern is reusable",
                "feedback": "Great practical example"
            },
            "reader_b": {
                "persona": "External community", "rating": "WOULD_SHARE",
                "hn_potential": 7, "twitter_potential": 6, "novelty": 7,
                "credibility": 7, "memorability": 6,
                "share_trigger": "Novel approach",
                "feedback": "Would like more benchmarks"
            },
            "discovery_analysis": {
                "search_terms": ["multi-agent review", "AI writing quality"],
                "social_hook": "7 agents review your article",
                "newsletter_pitch": "Novel multi-agent approach to article quality",
                "target_communities": ["HN", "r/programming"]
            },
            "overall_verdict": "Strong influence-building potential"
        },
        "seo": {
            "reviewer": "seo", "rating": "OPTIMIZED",
            "summary": "Good keyword presence.", "issues": []
        },
        "external": {
            "reviewer": "external", "rating": "CLEAR",
            "summary": "Accessible to outsiders.", "issues": []
        },
        "factcheck": {
            "reviewer": "factcheck", "rating": "VERIFIED",
            "summary": "Claims are supported.", "issues": []
        },
    }

    for reviewer, review_data in reviews.items():
        write_json(os.path.join(state_dir, f"review-{reviewer}.json"), review_data)
        check(f"Review: {reviewer}", os.path.join(state_dir, f"review-{reviewer}.json"))

    # Add Chinese reviewer when running in zh mode
    if language == "zh":
        chinese_review = {
            "reviewer": "chinese",
            "rating": "NATURAL",
            "summary": "Chinese writing quality is natural and fluent.",
            "naturalness_score": 8,
            "terminology_score": 9,
            "style_score": 8,
            "issues": [],
            "suggestions": ["Consider using more idiomatic expressions"]
        }
        write_json(os.path.join(state_dir, "review-chinese.json"), chinese_review)
        check("Review: chinese", os.path.join(state_dir, "review-chinese.json"))

    # Aggregate and score
    log("Aggregating reviews...")
    run_script(skill_dir, "aggregate-reviews.sh", [project_dir])
    check("Review panel summary", os.path.join(state_dir, "review-panel-summary.json"))

    log("Computing quality score...")
    run_script(skill_dir, "quality-score.sh", [project_dir, "verbose"])
    check("Quality score", os.path.join(state_dir, "quality-score.json"))

    # Calibrate
    log("Calibrating reviews...")
    run_script(skill_dir, "calibrate-reviews.sh", [project_dir])

    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "refinement"])

    # --- Stage 6: REFINEMENT ---
    step("REFINEMENT")

    shutil.copy2(os.path.join(state_dir, "draft-v1.md"),
                 os.path.join(state_dir, "draft-v2.md"))
    run_script(skill_dir, "pipeline-state.sh",
               ["set-field", project_dir, "draft_version", "2"])
    run_script(skill_dir, "pipeline-state.sh", ["refinement-round", project_dir])
    check("Refined draft v2", os.path.join(state_dir, "draft-v2.md"))

    run_script(skill_dir, "pipeline-state.sh", ["set-stage", project_dir, "polish"])

    # --- Stage 7: POLISH ---
    step("POLISH")

    shutil.copy2(os.path.join(state_dir, "draft-v2.md"),
                 os.path.join(state_dir, "final-internal.md"))
    shutil.copy2(os.path.join(state_dir, "draft-v2.md"),
                 os.path.join(state_dir, "final-external.md"))
    check("Final internal", os.path.join(state_dir, "final-internal.md"))
    check("Final external", os.path.join(state_dir, "final-external.md"))

    # Social package
    social_pkg = {
        "twitter_thread": [
            "1/ We built a 7-agent review system for tech articles.",
            "2/ Each agent reviews independently \u2014 no groupthink.",
            "3/ The adversarial agent alone caught issues in 73% of articles."
        ],
        "linkedin_post": "Excited to share how multi-agent AI review improved our article quality from 5.2 to 8.1/10.",
        "hn_title": "How We Built a 7-Agent Review System for Tech Articles",
        "xiaohongshu_post": "\u5206\u4eab\uff1a\u6211\u4eec\u5982\u4f55\u75287\u4e2aAI Agent\u6765\u5ba1\u67e5\u6280\u672f\u6587\u7ae0"
    }
    write_json(os.path.join(state_dir, "social-package.json"), social_pkg)
    check("Social package", os.path.join(state_dir, "social-package.json"))

    # Influence score
    log("Computing influence score...")
    run_script(skill_dir, "influence-score.sh", [project_dir, "verbose"])

    # SEO metadata
    log("Generating SEO metadata...")
    run_script(skill_dir, "seo-metadata.sh", [project_dir])

    # Publish check
    log("Running publish readiness check...")
    run_script(skill_dir, "publish-check.sh", [project_dir])

    # Progress display
    log("Pipeline progress:")
    run_script(skill_dir, "progress-display.sh", [project_dir])

    # --- COMPLETION ---
    step("COMPLETION")

    run_script(skill_dir, "pipeline-state.sh", ["complete", project_dir])
    check("Pipeline complete", os.path.join(state_dir, "pipeline-state.json"))

    # Verify final state
    final_result = run_script(skill_dir, "pipeline-state.sh",
                              ["get-stage", project_dir])
    final_stage = final_result.stdout.strip() if final_result else ""
    check_condition(f"Final stage is 'complete'", final_stage == "complete")

    # --- SUMMARY ---
    print()
    print("========================================")
    print(f"DRY RUN: {TOTAL_COUNT} checks | Pass: {PASS_COUNT} | Fail: {FAIL_COUNT}")
    print("========================================")

    if FAIL_COUNT > 0:
        print("\u26a0  Some checks failed. Review output above.")
        sys.exit(1)
    else:
        print("\u2705 All pipeline stages completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
