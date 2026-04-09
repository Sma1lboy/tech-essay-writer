#!/usr/bin/env python3
"""Influence score predictor — estimates article reach/impact potential from state data.
Usage: influence_score.py <project_dir> [verbose]
"""

import json
import os
import sys

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: influence_score.py <project_dir> [verbose]

Estimates article influence/reach potential from pipeline state data.
Scores across 5 dimensions: topic novelty, expertise match, SEO potential,
social shareability, and audience reach.

Reads: research-synthesis.json, pipeline-state.json, review-seo.json,
       social-package.json, review-audience.json, ~/.tech-essay-writer/expertise-graph.json
Writes: influence-score.json

Output: JSON result to stdout (or verbose text with 'verbose' flag)""")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    verbose = len(sys.argv) > 2 and sys.argv[2] == "verbose"

    if not project_dir:
        print("ERROR: project_dir required", file=sys.stderr)
        print("Usage: influence_score.py <project_dir> [verbose]", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, ".essay-state")

    # Read expertise graph directly from persistent data
    expertise_path = os.path.expanduser("~/.tech-essay-writer/expertise-graph.json")
    expertise = read_json_file(expertise_path, {"topics": {}})

    scores = {}

    # --- 1. Topic Novelty (from research-synthesis.json) ---
    novelty_score = 5.0
    research_file = os.path.join(state_dir, "research-synthesis.json")
    research = read_json_file(research_file)
    if research:
        novelty = 5.0

        # Check competitive landscape
        landscape = research.get("competitive_landscape", research.get("landscape", {}))
        existing = landscape.get("existing_articles", landscape.get("competitors", []))
        if isinstance(existing, list):
            if len(existing) == 0:
                novelty += 3.0  # Blue ocean
            elif len(existing) <= 3:
                novelty += 1.5  # Low competition
            elif len(existing) >= 10:
                novelty -= 1.0  # Saturated

        # Check for identified gap
        gap = research.get("gap", research.get("content_gap", ""))
        if gap and len(str(gap)) > 20:
            novelty += 1.5

        # Check unique angle
        angle = research.get("unique_angle", research.get("angle", ""))
        if angle and len(str(angle)) > 10:
            novelty += 1.0

        novelty_score = max(1, min(10, round(novelty, 1)))

    scores["topic_novelty"] = novelty_score

    # --- 2. Author Expertise Match (from expertise graph) ---
    expertise_score = 5.0
    topics_graph = expertise.get("topics", {})

    # Get current article topic from pipeline state
    pipeline_file = os.path.join(state_dir, "pipeline-state.json")
    pipeline = read_json_file(pipeline_file)
    article_topic = pipeline.get("topic", "").lower()

    if article_topic and topics_graph:
        # Direct match
        best_match_score = 0
        for topic_name, topic_data in topics_graph.items():
            if topic_name.lower() in article_topic or article_topic in topic_name.lower():
                authority = topic_data.get("authority_score", 0)
                best_match_score = max(best_match_score, authority)

        # Tag-based match
        tag_index = expertise.get("tag_index", {})
        for word in article_topic.split():
            if word in tag_index:
                for t in tag_index[word]:
                    if t in topics_graph:
                        score = topics_graph[t].get("authority_score", 0) * 0.5
                        best_match_score = max(best_match_score, score)

        expertise_score = max(1, min(10, round(best_match_score, 1))) if best_match_score > 0 else 3.0
    elif not topics_graph:
        expertise_score = 3.0  # No history = unknown authority

    scores["expertise_match"] = expertise_score

    # --- 3. SEO Potential (from review-seo.json) ---
    seo_score = 5.0
    seo_file = os.path.join(state_dir, "review-seo.json")
    seo = read_json_file(seo_file)
    if seo:
        rating = seo.get("rating", "NEEDS_WORK")
        rating_map = {"OPTIMIZED": 9, "NEEDS_WORK": 5, "INVISIBLE": 2}
        base = rating_map.get(rating, 5)

        # Bonus for specific SEO signals
        keywords = seo.get("keywords", seo.get("target_keywords", []))
        if isinstance(keywords, list) and len(keywords) >= 3:
            base += 0.5

        title_score = seo.get("title_score", seo.get("title_optimization", 0))
        if isinstance(title_score, (int, float)) and title_score >= 7:
            base += 0.5

        # Penalty for issues
        issues = seo.get("issues", [])
        critical = sum(1 for i in issues if i.get("severity") in ("critical", "devastating"))
        base -= critical * 1.5

        seo_score = max(1, min(10, round(base, 1)))

    scores["seo_potential"] = seo_score

    # --- 4. Social Shareability (from social-package.json) ---
    social_score = 5.0
    social_file = os.path.join(state_dir, "social-package.json")
    social = read_json_file(social_file)
    if social:
        base = 5.0
        # Check platform coverage
        platforms = 0
        for key in ["twitter_thread", "linkedin_post", "hn_title", "reddit_post",
                     "mastodon_post", "bluesky_post"]:
            if social.get(key):
                platforms += 1
        base += min(2.0, platforms * 0.5)

        # Hook quality — longer hooks suggest more thought
        hooks = social.get("hooks", social.get("twitter_thread", ""))
        if isinstance(hooks, str) and len(hooks) > 100:
            base += 1.0
        elif isinstance(hooks, list) and len(hooks) >= 3:
            base += 1.0

        # HN title (high shareability signal)
        hn = social.get("hn_title", "")
        if hn and len(str(hn)) > 10:
            base += 0.5

        # Hashtags
        hashtags = social.get("hashtags", [])
        if isinstance(hashtags, list) and len(hashtags) >= 3:
            base += 0.5

        social_score = max(1, min(10, round(base, 1)))

    scores["social_shareability"] = social_score

    # --- 5. Audience Size Estimate (from review-audience.json) ---
    audience_score = 5.0
    audience_file = os.path.join(state_dir, "review-audience.json")
    audience = read_json_file(audience_file)
    if audience:
        # Dual reader ratings
        ra = audience.get("reader_a", {}).get("rating", "MEH")
        rb = audience.get("reader_b", {}).get("rating", "MEH")
        rating_map = {"WOULD_SHARE": 9, "MEH": 5, "SKIP": 2}
        score_a = rating_map.get(ra, 5)
        score_b = rating_map.get(rb, 5)
        base = (score_a + score_b) / 2

        # Breadth signals
        target = audience.get("target_audience", audience.get("audience", ""))
        if isinstance(target, str) and ("beginner" in target.lower() or "all" in target.lower()):
            base += 1.0  # Broader audience
        elif isinstance(target, dict):
            size = target.get("size", target.get("breadth", ""))
            if str(size).lower() in ("large", "broad", "wide"):
                base += 1.0

        # Engagement signals
        engagement = audience.get("engagement_prediction", audience.get("engagement", ""))
        if str(engagement).lower() in ("high", "viral"):
            base += 1.0

        audience_score = max(1, min(10, round(base, 1)))

    scores["audience_reach"] = audience_score

    # --- Composite ---
    weights = {
        "topic_novelty": 0.25,
        "expertise_match": 0.15,
        "seo_potential": 0.20,
        "social_shareability": 0.20,
        "audience_reach": 0.20
    }

    available_weight = sum(weights[k] for k in scores)
    composite = sum(scores[k] * weights[k] / available_weight for k in scores) if available_weight > 0 else 0
    composite = round(composite, 1)

    # Influence tier
    if composite >= 8:
        tier = "HIGH_INFLUENCE"
        emoji = "\U0001f680"
    elif composite >= 6:
        tier = "MODERATE_INFLUENCE"
        emoji = "\U0001f4c8"
    elif composite >= 4:
        tier = "LOW_INFLUENCE"
        emoji = "\U0001f4ca"
    else:
        tier = "MINIMAL_INFLUENCE"
        emoji = "\U0001f4c9"

    result = {
        "influence_score": composite,
        "tier": tier,
        "dimensions": scores,
        "weights": weights,
        "dimensions_available": len(scores)
    }

    if verbose:
        print(f"\n{'='*40}")
        print(f"Influence Score: {composite}/10 {emoji}")
        print(f"Tier: {tier}")
        print(f"Dimensions: {len(scores)}/5")
        for dim, s in sorted(scores.items(), key=lambda x: -x[1]):
            bar = "\u2588" * int(s) + "\u2591" * (10 - int(s))
            w = weights.get(dim, 0)
            print(f"  {dim:22s} {bar} {s:4.1f} (w={w})")
    else:
        print(json.dumps(result))

    # Atomic write to state
    target_file = os.path.join(state_dir, "influence-score.json")
    atomic_json_write(target_file, result)


if __name__ == "__main__":
    main()
