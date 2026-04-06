#!/usr/bin/env bash
# Calibrate review panel: normalize scores, detect outliers and blind spots
# Runs AFTER aggregate-reviews.sh
# Usage: calibrate-reviews.sh <project_dir>
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "ERROR: project_dir required" >&2
  echo "Usage: calibrate-reviews.sh <project_dir>" >&2
  exit 1
fi
PROJECT_DIR="$1"
STATE_DIR="$PROJECT_DIR/.essay-state"
OUTPUT="$STATE_DIR/review-calibration.json"

if [ ! -d "$STATE_DIR" ]; then
  echo "ERROR: State directory not found: $STATE_DIR" >&2
  exit 1
fi

python3 - "$STATE_DIR" << 'PYEOF'
import json, os, sys, glob, tempfile

state_dir = sys.argv[1]

# Load all review files
reviews = {}
review_files = glob.glob(os.path.join(state_dir, "review-*.json"))
for rf in review_files:
    if "panel-summary" in rf or "calibration" in rf:
        continue
    name = os.path.splitext(os.path.basename(rf))[0].replace("review-", "")
    try:
        with open(rf) as f:
            reviews[name] = json.load(f)
    except (json.JSONDecodeError, IOError):
        continue

if not reviews:
    print(json.dumps({"error": "No review files found"}))
    sys.exit(0)

# --- 1. Normalize ratings to 1-10 numeric scale ---

rating_map = {
    # Positive (7-10)
    "PASS": 8, "PUBLISH_READY": 9, "SOLID": 9, "OPTIMIZED": 9,
    "WOULD_SHARE": 8, "VERIFIED": 8,
    # Neutral (4-6)
    "NEEDS_FIXES": 5, "NEEDS_EDITING": 5, "NEEDS_WORK": 5,
    "NEEDS_CONTEXT": 5, "NEEDS_VERIFICATION": 5,
    "MEH": 4, "VULNERABLE": 4,
    # Negative (1-3)
    "REJECT": 2, "REWRITE": 2, "WEAK": 3,
}

normalized_scores = {}
for name, review in reviews.items():
    rating = review.get("rating", "")
    # Handle nested rating (e.g. audience has reader_a/reader_b)
    if isinstance(rating, dict):
        rating = "MEH"  # default for complex ratings
    score = rating_map.get(str(rating).upper(), 5)
    normalized_scores[name] = {
        "original_rating": rating,
        "numeric_score": score
    }

# --- 2. Detect outliers ---

scores = [v["numeric_score"] for v in normalized_scores.values()]
if len(scores) >= 3:
    avg = sum(scores) / len(scores)
    # Standard deviation
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
else:
    avg = sum(scores) / max(len(scores), 1)
    std_dev = 0

outliers = []
for name, data in normalized_scores.items():
    score = data["numeric_score"]
    deviation = score - avg
    if std_dev > 0 and abs(deviation) > 1.5 * std_dev:
        direction = "lenient" if deviation > 0 else "harsh"
        outliers.append({
            "reviewer": name,
            "score": score,
            "panel_average": round(avg, 1),
            "deviation": round(deviation, 1),
            "direction": direction,
            "note": f"{name} is significantly more {direction} than the panel average ({round(avg, 1)})"
        })

# --- 3. Detect blind spots ---

# Topics that SHOULD be examined in a tech article review
expected_coverage = {
    "code_correctness": {
        "description": "Code examples checked for correctness and runnability",
        "expected_reviewers": ["technical", "factcheck"],
        "check_fields": ["code_issues", "code_verification"]
    },
    "accessibility": {
        "description": "Content accessible to target audience, jargon explained",
        "expected_reviewers": ["external", "audience"],
        "check_fields": ["jargon_issues", "assumed_knowledge", "first_confusion_point"]
    },
    "factual_accuracy": {
        "description": "Claims and statistics verified",
        "expected_reviewers": ["factcheck", "technical"],
        "check_fields": ["factual_errors", "claims_checked", "unverified_claims"]
    },
    "argument_logic": {
        "description": "Logical coherence of the argument",
        "expected_reviewers": ["adversarial", "editor"],
        "check_fields": ["logic_gaps", "premise_valid", "premise_attack"]
    },
    "seo_discoverability": {
        "description": "Title, meta, and search optimization",
        "expected_reviewers": ["seo"],
        "check_fields": ["title_analysis", "social_package"]
    }
}

blind_spots = []
for topic, spec in expected_coverage.items():
    covered = False
    for reviewer_name in spec["expected_reviewers"]:
        if reviewer_name in reviews:
            review = reviews[reviewer_name]
            # Check if the reviewer actually addressed this topic
            for field in spec["check_fields"]:
                val = review.get(field)
                if val is not None and val != [] and val != {} and val != "":
                    covered = True
                    break
        if covered:
            break
    if not covered:
        blind_spots.append({
            "topic": topic,
            "description": spec["description"],
            "expected_reviewers": spec["expected_reviewers"],
            "status": "not_covered",
            "recommendation": f"No reviewer addressed {spec['description'].lower()}. Consider re-reviewing."
        })

# --- 4. Inter-reviewer agreement ---

if len(scores) >= 2:
    # Simple agreement: what fraction of reviewers are within 2 points of the median
    sorted_scores = sorted(scores)
    median = sorted_scores[len(sorted_scores) // 2]
    agreement_count = sum(1 for s in scores if abs(s - median) <= 2)
    agreement_score = round(agreement_count / len(scores) * 10, 1)

    # Identify areas of disagreement
    disagreements = []
    if max(scores) - min(scores) >= 4:
        high = [n for n, d in normalized_scores.items() if d["numeric_score"] == max(scores)]
        low = [n for n, d in normalized_scores.items() if d["numeric_score"] == min(scores)]
        disagreements.append({
            "type": "rating_spread",
            "spread": max(scores) - min(scores),
            "highest": {"reviewers": high, "score": max(scores)},
            "lowest": {"reviewers": low, "score": min(scores)},
            "note": "Large spread suggests reviewers are evaluating different aspects or have different standards"
        })
else:
    agreement_score = 10.0
    disagreements = []

# --- Build calibration output ---

calibration = {
    "reviewers_calibrated": len(normalized_scores),
    "normalized_scores": normalized_scores,
    "panel_average": round(avg, 1),
    "panel_std_dev": round(std_dev, 1),
    "outliers": outliers,
    "blind_spots": blind_spots,
    "agreement_score": agreement_score,
    "disagreements": disagreements,
    "calibration_notes": []
}

# Add calibration notes
if outliers:
    calibration["calibration_notes"].append(
        f"{len(outliers)} outlier(s) detected — consider weighting their feedback accordingly"
    )
if blind_spots:
    calibration["calibration_notes"].append(
        f"{len(blind_spots)} blind spot(s) found — topics not covered by any reviewer"
    )
if agreement_score < 5:
    calibration["calibration_notes"].append(
        "Low inter-reviewer agreement — reviewers may be evaluating different quality dimensions"
    )

# Atomic write
output_path = os.path.join(state_dir, "review-calibration.json")
tmp_path = output_path + ".tmp." + str(os.getpid())
with open(tmp_path, "w") as f:
    json.dump(calibration, f, indent=2)
os.rename(tmp_path, output_path)

# Print summary for conductor
print(json.dumps({
    "panel_average": calibration["panel_average"],
    "agreement_score": calibration["agreement_score"],
    "outliers": len(outliers),
    "blind_spots": len(blind_spots)
}, indent=2))
PYEOF
