#!/usr/bin/env python3
"""Calibrate review panel: normalize scores, detect outliers and blind spots.
Runs AFTER aggregate-reviews.sh.
Usage: calibrate_reviews.py <project_dir>
"""

import glob
import json
import os
import sys

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: calibrate_reviews.py <project_dir>

Post-aggregation calibration:
  - Normalizes scores to 1-10 numeric scale
  - Detects outliers (>1.5 std dev from panel average)
  - Finds blind spots (topics no reviewer covered)
  - Measures inter-reviewer agreement

Writes review-calibration.json to .essay-state/""")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""

    if not project_dir:
        print("ERROR: project_dir required", file=sys.stderr)
        print("Usage: calibrate_reviews.py <project_dir>", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, ".essay-state")

    if not os.path.isdir(state_dir):
        print(f"ERROR: State directory not found: {state_dir}", file=sys.stderr)
        sys.exit(1)

    # Load all review files
    reviews = {}
    review_files = glob.glob(os.path.join(state_dir, "review-*.json"))
    for rf in review_files:
        if "panel-summary" in rf or "calibration" in rf:
            continue
        name = os.path.splitext(os.path.basename(rf))[0].replace("review-", "")
        data = read_json_file(rf)
        if data:
            reviews[name] = data

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
        sorted_scores = sorted(scores)
        median = sorted_scores[len(sorted_scores) // 2]
        agreement_count = sum(1 for s in scores if abs(s - median) <= 2)
        agreement_score = round(agreement_count / len(scores) * 10, 1)

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
            f"{len(outliers)} outlier(s) detected \u2014 consider weighting their feedback accordingly"
        )
    if blind_spots:
        calibration["calibration_notes"].append(
            f"{len(blind_spots)} blind spot(s) found \u2014 topics not covered by any reviewer"
        )
    if agreement_score < 5:
        calibration["calibration_notes"].append(
            "Low inter-reviewer agreement \u2014 reviewers may be evaluating different quality dimensions"
        )

    # Atomic write
    output_path = os.path.join(state_dir, "review-calibration.json")
    atomic_json_write(output_path, calibration)

    # Print summary for conductor
    print(json.dumps({
        "panel_average": calibration["panel_average"],
        "agreement_score": calibration["agreement_score"],
        "outliers": len(outliers),
        "blind_spots": len(blind_spots)
    }, indent=2))


if __name__ == "__main__":
    main()
