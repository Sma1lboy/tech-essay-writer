#!/usr/bin/env bash
# Rich progress visualization for the tech-essay-writer pipeline
# Shows stage indicators, completion %, quality dashboard, artifacts
# Usage: progress-display.sh <project_dir> [--format text|json] [--verbose]
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
shift

FORMAT="text"
VERBOSE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --format) FORMAT="${2:?format value required}"; shift 2 ;;
    --verbose) VERBOSE="true"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [ "$FORMAT" != "text" ] && [ "$FORMAT" != "json" ]; then
  echo "ERROR: format must be 'text' or 'json'" >&2
  exit 1
fi

STATE_DIR="$PROJECT_DIR/.essay-state"
STATE_FILE="$STATE_DIR/pipeline-state.json"
QUALITY_FILE="$STATE_DIR/quality-score.json"

if [ ! -f "$STATE_FILE" ]; then
  if [ "$FORMAT" = "json" ]; then
    python3 -c "import json; print(json.dumps({'error':'not_initialized','message':'Pipeline not initialized'}))"
  else
    echo "Pipeline not initialized. Run intake first."
  fi
  exit 0
fi

python3 - "$STATE_FILE" "$QUALITY_FILE" "$STATE_DIR" "$FORMAT" "$VERBOSE" << 'PYEOF'
import json, sys, os, glob

state_file = sys.argv[1]
quality_file = sys.argv[2]
state_dir = sys.argv[3]
fmt = sys.argv[4]
verbose = sys.argv[5] == "true"

# Stage definitions with weights for completion calculation
STAGES = [
    ("intake",      "INTAKE",      0.05),
    ("research",    "RESEARCH",    0.10),
    ("outline",     "OUTLINE",     0.10),
    ("draft",       "DRAFT",       0.20),
    ("review",      "REVIEW",      0.20),
    ("refinement",  "REFINE",      0.20),
    ("polish",      "POLISH",      0.10),
    ("complete",    "COMPLETE",    0.05),
]
STAGE_KEYS = [s[0] for s in STAGES]

REVIEWERS = ["technical", "editor", "adversarial", "audience", "seo", "external", "factcheck"]

# Load pipeline state
try:
    with open(state_file) as f:
        state = json.load(f)
except (json.JSONDecodeError, IOError) as e:
    if fmt == "json":
        print(json.dumps({"error": "corrupt_state", "message": str(e)}))
    else:
        print(f"ERROR: Cannot read pipeline state: {e}", file=sys.stderr)
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
    current_idx = len(STAGE_KEYS) - 1  # complete stage
else:
    current_idx = STAGE_KEYS.index(current_stage) if current_stage in STAGE_KEYS else 0

# Calculate completion percentage with weighted stages
if completed or current_stage == "complete":
    completion = 100.0
else:
    # Sum weights of fully completed stages
    completion = sum(STAGES[i][2] for i in range(current_idx)) * 100
    # Add partial progress within current stage
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
quality = None
if os.path.exists(quality_file):
    try:
        with open(quality_file) as f:
            quality = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

# Read individual review files for detailed scores
review_details = {}
for reviewer in REVIEWERS:
    review_file = os.path.join(state_dir, f"review-{reviewer}.json")
    if os.path.exists(review_file):
        try:
            with open(review_file) as f:
                r = json.load(f)
            issues = r.get("issues", r.get("attacks", []))
            review_details[reviewer] = {
                "rating": r.get("rating", "UNKNOWN"),
                "issues_count": len(issues),
            }
        except (json.JSONDecodeError, IOError):
            pass

# Collect artifacts
artifacts = []
artifact_patterns = [
    ("draft",               "draft-v*.md"),
    ("research-synthesis",  "research-synthesis.json"),
    ("outline",             "outline-*.json"),
    ("review-panel-summary","review-panel-summary.json"),
    ("review-calibration",  "review-calibration.json"),
    ("final-internal",      "final-internal.md"),
    ("final-external",      "final-external.md"),
    ("final-medium",        "final-medium.md"),
    ("final-devto",         "final-devto.md"),
    ("final-hashnode",      "final-hashnode.md"),
    ("final-wechat",        "final-wechat.md"),
    ("final-juejin",        "final-juejin.md"),
    ("social-package",      "social-package.json"),
    ("seo-metadata",        "seo-metadata.json"),
    ("influence-score",     "influence-score.json"),
    ("diagram-suggestions", "diagram-suggestions.json"),
    ("quality-score",       "quality-score.json"),
]
for name, pattern in artifact_patterns:
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

# Pipeline map — labels row + indicators row
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
PYEOF
