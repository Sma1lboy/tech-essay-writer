#!/usr/bin/env bash
# Aggregate all review results into a single panel summary
# Usage: aggregate-reviews.sh <project_dir>
set -euo pipefail

PROJECT_DIR="$1"
STATE_DIR="$PROJECT_DIR/.essay-state"
OUTPUT="$STATE_DIR/review-panel-summary.json"

python3 - "$STATE_DIR" << 'PYEOF'
import json, os, sys, glob

state_dir = sys.argv[1]
reviews = {}
review_files = glob.glob(os.path.join(state_dir, "review-*.json"))

for rf in review_files:
    if "panel-summary" in rf:
        continue
    name = os.path.splitext(os.path.basename(rf))[0]
    try:
        with open(rf) as f:
            reviews[name] = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        reviews[name] = {"error": str(e)}

# Aggregate
summary = {
    "reviews_count": len(reviews),
    "reviews": {},
    "critical_issues": [],
    "all_issues": [],
    "ratings": {},
    "consensus": None,
    "action_required": False
}

for name, review in reviews.items():
    rating = review.get("rating", "unknown")
    summary["ratings"][name] = rating
    summary["reviews"][name] = {
        "rating": rating,
        "summary": review.get("summary", ""),
        "issues_count": len(review.get("issues", []))
    }

    # Collect issues with source attribution
    for issue in review.get("issues", []):
        issue["source_reviewer"] = name
        if issue.get("severity") == "critical":
            summary["critical_issues"].append(issue)
        summary["all_issues"].append(issue)

    # Also collect code_issues, factual_errors, attacks, etc.
    for code_issue in review.get("code_issues", []):
        code_issue["source_reviewer"] = name
        code_issue["severity"] = "major"
        summary["all_issues"].append(code_issue)

    for attack in review.get("attacks", []):
        attack["source_reviewer"] = name
        if attack.get("severity") == "devastating":
            summary["critical_issues"].append(attack)
        summary["all_issues"].append(attack)

# Determine consensus
reject_signals = ["REJECT", "REWRITE", "WEAK"]
pass_signals = ["PASS", "PUBLISH_READY", "SOLID", "OPTIMIZED", "WOULD_SHARE"]

rejects = sum(1 for r in summary["ratings"].values()
               if any(s in str(r) for s in reject_signals))
passes = sum(1 for r in summary["ratings"].values()
              if any(s in str(r) for s in pass_signals))

if rejects >= 2:
    summary["consensus"] = "NEEDS_MAJOR_REVISION"
    summary["action_required"] = True
elif len(summary["critical_issues"]) > 0:
    summary["consensus"] = "NEEDS_FIXES"
    summary["action_required"] = True
elif passes >= 3:
    summary["consensus"] = "READY_TO_PUBLISH"
    summary["action_required"] = False
else:
    summary["consensus"] = "NEEDS_MINOR_REVISION"
    summary["action_required"] = True

# Sort issues by severity
severity_order = {"critical": 0, "devastating": 0, "major": 1, "significant": 1, "minor": 2}
summary["all_issues"].sort(key=lambda x: severity_order.get(x.get("severity", "minor"), 2))

# Prioritized action items (top 10)
summary["prioritized_actions"] = []
for issue in summary["all_issues"][:10]:
    summary["prioritized_actions"].append({
        "from": issue.get("source_reviewer", "unknown"),
        "severity": issue.get("severity", "unknown"),
        "issue": issue.get("issue", issue.get("attack", issue.get("target", "unknown"))),
        "suggestion": issue.get("suggestion", issue.get("defense", ""))
    })

output_path = os.path.join(state_dir, "review-panel-summary.json")
with open(output_path, "w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps({
    "consensus": summary["consensus"],
    "critical_issues": len(summary["critical_issues"]),
    "total_issues": len(summary["all_issues"]),
    "ratings": summary["ratings"]
}, indent=2))
PYEOF
