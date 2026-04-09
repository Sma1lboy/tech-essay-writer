#!/usr/bin/env python3
"""Rich progress visualization for the tech-essay-writer pipeline.
Shows stage indicators, completion %, quality dashboard, artifacts.
Usage: progress_display.py <project_dir> [--format text|json] [--verbose]
"""

import glob
import json
import os
import sys

from utils import read_json_file

STATE_DIR = ".essay-state"

# Stage definitions with weights for completion calculation
STAGES = [
    ("intake",     "INTAKE",     0.05),
    ("research",   "RESEARCH",   0.10),
    ("outline",    "OUTLINE",    0.10),
    ("draft",      "DRAFT",      0.20),
    ("review",     "REVIEW",     0.20),
    ("refinement", "REFINE",     0.20),
    ("polish",     "POLISH",     0.10),
    ("complete",   "COMPLETE",   0.05),
]
STAGE_KEYS = [s[0] for s in STAGES]

REVIEWERS = ["technical", "editor", "adversarial", "audience", "seo", "external", "factcheck"]

ARTIFACT_PATTERNS = [
    ("draft",                "draft-v*.md"),
    ("research-synthesis",   "research-synthesis.json"),
    ("outline",              "outline-*.json"),
    ("review-panel-summary", "review-panel-summary.json"),
    ("review-calibration",   "review-calibration.json"),
    ("final-internal",       "final-internal.md"),
    ("final-external",       "final-external.md"),
    ("final-medium",         "final-medium.md"),
    ("final-devto",          "final-devto.md"),
    ("final-hashnode",       "final-hashnode.md"),
    ("final-wechat",         "final-wechat.md"),
    ("final-juejin",         "final-juejin.md"),
    ("social-package",       "social-package.json"),
    ("seo-metadata",         "seo-metadata.json"),
    ("influence-score",      "influence-score.json"),
    ("diagram-suggestions",  "diagram-suggestions.json"),
    ("quality-score",        "quality-score.json"),
]


def usage():
    print("""Usage: progress_display.py <project_dir> [--format text|json] [--verbose]

Displays pipeline progress with stage map, completion %, quality dashboard, and artifacts.

Options:
  --format text|json   Output format (default: text)
  --verbose            Show extra details (pending reviewers, dimension scores, artifact list)""")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    project_dir = sys.argv[1]
    fmt = "text"
    verbose = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--format":
            if i + 1 < len(sys.argv):
                fmt = sys.argv[i + 1]
                i += 2
            else:
                print("ERROR: --format requires a value", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[i] == "--verbose":
            verbose = True
            i += 1
        else:
            print(f"Unknown option: {sys.argv[i]}", file=sys.stderr)
            sys.exit(1)

    if fmt not in ("text", "json"):
        print("ERROR: format must be 'text' or 'json'", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, STATE_DIR)
    state_file = os.path.join(state_dir, "pipeline-state.json")
    quality_file = os.path.join(state_dir, "quality-score.json")

    if not os.path.isfile(state_file):
        if fmt == "json":
            print(json.dumps({"error": "not_initialized", "message": "Pipeline not initialized"}))
        else:
            print("Pipeline not initialized. Run intake first.")
        sys.exit(0)

    # Load pipeline state
    state = read_json_file(state_file)
    if not state:
        if fmt == "json":
            print(json.dumps({"error": "corrupt_state", "message": "Cannot read pipeline state"}))
        else:
            print("ERROR: Cannot read pipeline state", file=sys.stderr)
        sys.exit(1)

    current_stage = state.get("stage", "intake")
    topic = state.get("topic", "Unknown")
    completed = state.get("completed", False)
    draft_version = state.get("draft_version", 0)
    refinement_round = state.get("refinement_round", 0)
    max_rounds = state.get("max_refinement_rounds", 3)
    materials_count = state.get("materials_count", 0)
    language = state.get("language", "en")
    reviews_state = state.get("reviews", {})
    series_id = state.get("series_id", None)

    # Determine current stage index
    if completed or current_stage == "complete":
        current_idx = len(STAGE_KEYS) - 1
    else:
        current_idx = STAGE_KEYS.index(current_stage) if current_stage in STAGE_KEYS else 0

    # Calculate completion percentage with weighted stages
    if completed or current_stage == "complete":
        completion = 100.0
    else:
        completion = sum(STAGES[i][2] for i in range(current_idx)) * 100
        if current_stage == "review":
            review_count = len(reviews_state)
            completion += STAGES[current_idx][2] * (review_count / 7.0) * 100
        elif current_stage == "refinement" and max_rounds > 0:
            completion += STAGES[current_idx][2] * (refinement_round / max_rounds) * 100
    completion = round(min(completion, 100.0), 1)

    # Build stage status map
    stage_map = []
    for i, (key, label, weight) in enumerate(STAGES):
        if completed or current_stage == "complete":
            status = "completed"
            symbol = "\u2713"
        elif i < current_idx:
            status = "completed"
            symbol = "\u2713"
        elif i == current_idx:
            status = "current"
            symbol = "\u25cf"
        else:
            status = "pending"
            symbol = "\u25cb"
        stage_map.append({
            "stage": key,
            "label": label,
            "status": status,
            "symbol": symbol,
            "weight": weight,
        })

    # Load quality score
    quality = read_json_file(quality_file) or None

    # Read individual review files for detailed scores
    review_details = {}
    for reviewer in REVIEWERS:
        review_file = os.path.join(state_dir, f"review-{reviewer}.json")
        r = read_json_file(review_file)
        if r:
            issues = r.get("issues", r.get("attacks", []))
            review_details[reviewer] = {
                "rating": r.get("rating", "UNKNOWN"),
                "issues_count": len(issues),
            }

    # Collect artifacts
    artifacts = []
    for name, pattern in ARTIFACT_PATTERNS:
        matches = glob.glob(os.path.join(state_dir, pattern))
        if matches:
            artifacts.append(name)

    # === JSON output ===
    if fmt == "json":
        result = {
            "topic": topic,
            "stage": current_stage,
            "completed": completed,
            "completion_pct": completion,
            "language": language,
            "draft_version": draft_version,
            "refinement_round": refinement_round,
            "max_refinement_rounds": max_rounds,
            "materials_count": materials_count,
            "series_id": series_id,
            "stages": stage_map,
            "reviews": review_details,
            "quality": quality,
            "artifacts": artifacts,
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # === Text output ===
    print()
    print(f"  Essay Pipeline: {topic}")
    print(f"  {'=' * 58}")
    print()

    # Pipeline map -- labels row + indicators row
    label_row = ""
    indicator_row = ""
    for i, s in enumerate(stage_map):
        label = s["label"]
        sym = s["symbol"]
        pad = len(label)
        ind_padded = sym.center(pad)
        if i < len(stage_map) - 1:
            label_row += label + " \u2192 "
            indicator_row += ind_padded + "   "
        else:
            label_row += label
            indicator_row += ind_padded

    print(f"  {label_row}")
    print(f"  {indicator_row}")
    print()

    # Completion bar
    bar_width = 40
    filled = int(bar_width * completion / 100)
    empty = bar_width - filled
    bar = "\u2588" * filled + "\u2591" * empty
    print(f"  Progress: [{bar}] {completion}%")
    print()

    # Details
    print(f"  Stage:            {current_stage}")
    print(f"  Draft version:    {draft_version}")
    print(f"  Refinement round: {refinement_round}/{max_rounds}")
    print(f"  Materials:        {materials_count}")
    print(f"  Language:          {language}")
    if series_id:
        print(f"  Series:            {series_id}")
    if completed:
        completed_at = state.get("completed_at", state.get("updated_at", "unknown"))
        print(f"  Completed at:     {completed_at}")
    print()

    # Review scores dashboard
    if review_details or verbose:
        print("  Review Dashboard:")
        for reviewer in REVIEWERS:
            if reviewer in review_details:
                rd = review_details[reviewer]
                rating = rd["rating"]
                issues = rd["issues_count"]
                print(f"    {reviewer:15s} {rating:20s} ({issues} issues)")
            elif verbose:
                print(f"    {reviewer:15s} {'PENDING':20s}")
        print(f"    Reviews: {len(review_details)}/7")
        print()

    # Quality metrics
    if quality and quality.get("composite_score") is not None:
        score = quality["composite_score"]
        readiness = quality.get("readiness", "UNKNOWN")
        reviews_avail = quality.get("reviews_available", 0)
        reviews_expected = quality.get("reviews_expected", 7)

        score_filled = int(score)
        score_empty = 10 - score_filled
        score_bar = "\u2588" * score_filled + "\u2591" * score_empty

        if readiness == "READY":
            emoji = "\u2705"
        elif readiness == "CLOSE":
            emoji = "\U0001F7E1"
        elif readiness == "NEEDS_WORK":
            emoji = "\U0001F7E0"
        else:
            emoji = "\U0001F534"

        print(f"  Quality: [{score_bar}] {score}/10 {emoji} {readiness}")
        print(f"  Reviews: {reviews_avail}/{reviews_expected}")

        # Per-dimension scores in verbose mode
        dim_scores = quality.get("dimension_scores", {})
        if verbose and dim_scores:
            print()
            print("  Dimension Scores:")
            for dim, s in sorted(dim_scores.items(), key=lambda x: -x[1]):
                dim_bar = "\u2588" * int(s) + "\u2591" * (10 - int(s))
                print(f"    {dim:15s} [{dim_bar}] {s}")
        print()
    else:
        print("  Quality: No score available yet")
        print()

    # Artifacts
    if artifacts:
        print(f"  Artifacts: {len(artifacts)}")
        if verbose:
            for a in artifacts:
                print(f"    \u2022 {a}")
        print()

    print(f"  {'=' * 58}")


if __name__ == "__main__":
    main()
