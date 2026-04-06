#!/usr/bin/env bash
# Quality score calculator — produces a composite 0-10 score from review data
# Usage: quality-score.sh <project_dir> [verbose]
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
VERBOSE="${2:-}"
STATE_DIR="$PROJECT_DIR/.essay-state"

python3 - "$STATE_DIR" "$VERBOSE" << 'PYEOF'
import json, sys, os, glob

state_dir = sys.argv[1]
verbose = sys.argv[2] == "verbose" if len(sys.argv) > 2 else False

scores = {}
weights = {
    "technical": 0.20,
    "editor": 0.20,
    "adversarial": 0.15,
    "audience": 0.10,
    "seo": 0.10,
    "external": 0.10,
    "factcheck": 0.15
}

# Rating to score mappings
rating_scores = {
    # Technical
    "PASS": 9, "NEEDS_FIXES": 5, "REJECT": 2,
    # Editor
    "PUBLISH_READY": 9, "NEEDS_EDITING": 5, "REWRITE": 2,
    # Adversarial
    "SOLID": 9, "VULNERABLE": 5, "WEAK": 2,
    # Audience
    "WOULD_SHARE": 9, "MEH": 5, "SKIP": 2,
    # SEO
    "OPTIMIZED": 9, "NEEDS_WORK": 5, "INVISIBLE": 2,
    # External
    "CLEAR": 9, "NEEDS_CONTEXT": 5, "INACCESSIBLE": 2,
    # Factcheck
    "VERIFIED": 9, "NEEDS_VERIFICATION": 5, "UNRELIABLE": 2
}

# Read each review
for reviewer in weights:
    review_file = os.path.join(state_dir, f"review-{reviewer}.json")
    if not os.path.exists(review_file):
        if verbose:
            print(f"  {reviewer}: MISSING (skipped)")
        continue

    try:
        with open(review_file) as f:
            review = json.load(f)
    except json.JSONDecodeError:
        if verbose:
            print(f"  {reviewer}: CORRUPT (skipped)")
        continue

    rating = review.get("rating", "unknown")

    # Handle audience reviewer (dual rating)
    if reviewer == "audience":
        ra = review.get("reader_a", {}).get("rating", "MEH")
        rb = review.get("reader_b", {}).get("rating", "MEH")
        score_a = rating_scores.get(ra, 5)
        score_b = rating_scores.get(rb, 5)
        score = (score_a + score_b) / 2
    else:
        score = rating_scores.get(rating, 5)

    # Adjust based on issue count
    issues = review.get("issues", [])
    critical = sum(1 for i in issues if i.get("severity") in ("critical", "devastating"))
    major = sum(1 for i in issues if i.get("severity") in ("major", "significant"))
    minor = sum(1 for i in issues if i.get("severity") == "minor")

    # Penalty: critical=-2, major=-0.5, minor=-0.1
    penalty = critical * 2 + major * 0.5 + minor * 0.1
    adjusted = max(1, score - penalty)

    # Editor-specific: use sub-scores if available
    if reviewer == "editor":
        sub_scores = []
        for key in ["hook_score", "clarity_score", "flow_score", "voice_score",
                     "engagement_score", "economy_score"]:
            if key in review:
                sub_scores.append(review[key])
        if sub_scores:
            adjusted = sum(sub_scores) / len(sub_scores)

    scores[reviewer] = round(adjusted, 1)

    if verbose:
        print(f"  {reviewer}: {rating} → {score} → adjusted {adjusted:.1f} "
              f"(critical={critical}, major={major}, minor={minor})")

# Calculate weighted composite
if not scores:
    print("NO_REVIEWS")
    sys.exit(0)

# Re-weight based on available reviews
available_weight = sum(weights[r] for r in scores)
composite = sum(scores[r] * weights[r] / available_weight for r in scores)
composite = round(composite, 1)

# Determine publish readiness
if composite >= 8:
    readiness = "READY"
    emoji = "✅"
elif composite >= 6:
    readiness = "CLOSE"
    emoji = "🟡"
elif composite >= 4:
    readiness = "NEEDS_WORK"
    emoji = "🟠"
else:
    readiness = "NOT_READY"
    emoji = "🔴"

# Output
result = {
    "composite_score": composite,
    "readiness": readiness,
    "dimension_scores": scores,
    "reviews_available": len(scores),
    "reviews_expected": 7
}

if verbose:
    print(f"\n{'='*40}")
    print(f"Quality Score: {composite}/10 {emoji}")
    print(f"Readiness: {readiness}")
    print(f"Reviews: {len(scores)}/7")
    for r, s in sorted(scores.items(), key=lambda x: -x[1]):
        bar = "█" * int(s) + "░" * (10 - int(s))
        print(f"  {r:15s} {bar} {s}")
else:
    print(json.dumps(result))

# Also write to state
result_file = os.path.join(state_dir, "quality-score.json")
with open(result_file, "w") as f:
    json.dump(result, f, indent=2)
PYEOF
