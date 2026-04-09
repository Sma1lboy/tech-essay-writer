#!/usr/bin/env python3
"""Title generator — produces scored title variations from research and materials.
Usage: title_generator.py <project_dir> [count]
"""

import hashlib
import json
import os
import re
import sys

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: title_generator.py <project_dir> [count]

Generates title variations for articles and scores them on
clarity, curiosity gap, specificity, and shareability.

count: number of titles to generate (default: 10)

Reads: research-synthesis.json, materials.json, pipeline-state.json
Writes: title-variations.json

Output: JSON result to stdout""")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    count = 10
    if len(sys.argv) > 2:
        try:
            count = int(sys.argv[2])
        except ValueError:
            count = 10

    if not project_dir:
        print("ERROR: project_dir required", file=sys.stderr)
        print("Usage: title_generator.py <project_dir> [count]", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, ".essay-state")

    # --- Read inputs ---

    research_file = os.path.join(state_dir, "research-synthesis.json")
    materials_file = os.path.join(state_dir, "materials.json")
    pipeline_file = os.path.join(state_dir, "pipeline-state.json")

    research = read_json_file(research_file)
    materials = read_json_file(materials_file)
    pipeline = read_json_file(pipeline_file)

    # --- Extract key elements from research and materials ---

    topic = pipeline.get("topic", research.get("topic", ""))
    angle = research.get("unique_angle", research.get("angle", ""))
    gap = research.get("gap", research.get("content_gap", ""))
    audience = pipeline.get("target_audience", research.get("target_audience", ""))

    # Extract key findings, pain points, results
    key_findings = research.get("key_findings", research.get("findings", []))
    if isinstance(key_findings, str):
        key_findings = [key_findings]

    pain_points = research.get("pain_points", research.get("challenges", []))
    if isinstance(pain_points, str):
        pain_points = [pain_points]

    # Extract from materials
    material_titles = []
    material_sources = []
    if isinstance(materials, dict):
        items = materials.get("items", materials.get("sources", materials.get("materials", [])))
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    t = item.get("title", item.get("name", ""))
                    if t:
                        material_titles.append(t)
                    s = item.get("source", item.get("url", ""))
                    if s:
                        material_sources.append(s)
    elif isinstance(materials, list):
        for item in materials:
            if isinstance(item, dict):
                t = item.get("title", item.get("name", ""))
                if t:
                    material_titles.append(t)

    # Competitor count
    landscape = research.get("competitive_landscape", research.get("landscape", {}))
    competitors = landscape.get("existing_articles", landscape.get("competitors", []))
    competitor_count = len(competitors) if isinstance(competitors, list) else 0

    # Conventional wisdom / common beliefs
    conventional = research.get("conventional_wisdom", research.get("common_beliefs", ""))
    if isinstance(conventional, list) and conventional:
        conventional = conventional[0]
    elif not isinstance(conventional, str):
        conventional = ""

    # Build approach / method
    approach = research.get("approach", research.get("method", research.get("methodology", "")))
    if isinstance(approach, list) and approach:
        approach = approach[0]
    elif not isinstance(approach, str):
        approach = ""

    # Result / outcome
    result_text = research.get("result", research.get("outcome", research.get("conclusion", "")))
    if isinstance(result_text, list) and result_text:
        result_text = result_text[0]
    elif not isinstance(result_text, str):
        result_text = ""

    # Company / author
    company = research.get("company", research.get("organization", ""))
    author = pipeline.get("author", research.get("author", ""))

    # Famous reference
    famous_ref = research.get("analogy", research.get("metaphor", research.get("reference", "")))
    if isinstance(famous_ref, list) and famous_ref:
        famous_ref = famous_ref[0]
    elif not isinstance(famous_ref, str):
        famous_ref = ""

    # Duration / time period
    duration = research.get("duration", research.get("time_period", ""))
    if isinstance(duration, list) and duration:
        duration = duration[0]
    elif not isinstance(duration, str):
        duration = ""

    # Bad practice / good practice
    bad_practice = ""
    good_practice = ""
    if pain_points and isinstance(pain_points, list) and len(pain_points) > 0:
        bp = pain_points[0]
        if isinstance(bp, dict):
            bad_practice = bp.get("name", bp.get("practice", str(bp)))
        else:
            bad_practice = str(bp)
    if key_findings and isinstance(key_findings, list) and len(key_findings) > 0:
        gp = key_findings[0]
        if isinstance(gp, dict):
            good_practice = gp.get("name", gp.get("finding", str(gp)))
        else:
            good_practice = str(gp)

    # Adjectives for variety
    adjectives_definitive = ["Complete", "Definitive", "Ultimate", "Practical", "Essential", "Comprehensive", "No-Nonsense"]
    adjectives_counter = ["Overrated", "Misunderstood", "Broken", "Dead", "Harder Than You Think", "Simpler Than You Think", "Not What You Think"]

    # --- Deterministic seed for stable output ---
    seed_str = topic + angle + gap
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

    def pick(lst, offset=0):
        """Pick an item deterministically from a list."""
        if not lst:
            return ""
        return lst[(seed + offset) % len(lst)]

    # --- Title formula generators ---

    def formula_how_achieved():
        """How [company/I] [achieved result] with [approach]"""
        who = company if company else ("I" if author else "We")
        result_part = result_text if result_text else f"improved {topic}" if topic else "achieved great results"
        approach_part = approach if approach else topic if topic else "this approach"
        return f"How {who} {result_part} with {approach_part}"

    def formula_number_list():
        """[Number]: [List of things about topic]"""
        nums = [5, 7, 8, 10, 12]
        n = pick(nums, 1)
        t = topic if topic else "Software Engineering"
        qualifiers = ["Lessons", "Patterns", "Principles", "Strategies", "Techniques", "Insights", "Rules", "Mistakes"]
        q = pick(qualifiers, 2)
        return f"{n} {q} for {t} That Actually Work"

    def formula_why_wrong():
        """Why [conventional wisdom] is Wrong About [topic]"""
        cw = conventional if conventional else "everyone" if topic else "common advice"
        t = topic if topic else "this approach"
        return f"Why {cw} is Wrong About {t}"

    def formula_counterintuitive():
        """[Topic] is [counterintuitive adjective]: Here's Why"""
        t = topic if topic else "This"
        adj = pick(adjectives_counter, 3)
        return f"{t} is {adj}: Here's Why"

    def formula_guide():
        """The [adjective] Guide to [topic]"""
        adj = pick(adjectives_definitive, 4)
        t = topic if topic else "Getting Started"
        return f"The {adj} Guide to {t}"

    def formula_stop_do():
        """Stop [bad practice]. Do [good practice] Instead."""
        bp = bad_practice if bad_practice else f"overcomplicating {topic}" if topic else "doing it wrong"
        gp = good_practice if good_practice else f"simplifying {topic}" if topic else "doing it right"
        # Truncate for readability
        bp = bp[:60].rstrip(".,! ")
        gp = gp[:60].rstrip(".,! ")
        return f"Stop {bp}. Do {gp} Instead."

    def formula_problem_solution():
        """[Problem]? [Solution]."""
        problem = ""
        if pain_points and isinstance(pain_points, list) and len(pain_points) > 0:
            p = pain_points[0]
            if isinstance(p, dict):
                problem = p.get("name", p.get("problem", str(p)))
            else:
                problem = str(p)
        if not problem:
            problem = f"Struggling with {topic}" if topic else "Stuck on this problem"
        solution = ""
        if approach:
            solution = approach
        elif angle:
            solution = angle
        elif topic:
            solution = f"A practical {topic} approach"
        else:
            solution = "Here's your answer"
        problem = problem[:80].rstrip(".,!? ")
        solution = solution[:80].rstrip(".,!? ")
        return f"{problem}? {solution}."

    def formula_learned():
        """I [action] for [time]. Here's What I Learned."""
        action = ""
        if approach:
            action = f"used {approach}"
        elif topic:
            action = f"worked with {topic}"
        else:
            action = "did this"
        time = duration if duration else "2 years"
        return f"I {action} for {time}. Here's What I Learned."

    def formula_without():
        """[Topic] Without [pain point]"""
        t = topic if topic else "Building Software"
        pain = ""
        if pain_points and isinstance(pain_points, list) and len(pain_points) > 0:
            p = pain_points[-1] if len(pain_points) > 1 else pain_points[0]
            if isinstance(p, dict):
                pain = p.get("name", p.get("problem", str(p)))
            else:
                pain = str(p)
        if not pain:
            pain = "the Complexity"
        pain = pain[:50].rstrip(".,!? ")
        return f"{t} Without {pain}"

    def formula_taught_me():
        """What [famous thing] Taught Me About [topic]"""
        ref = famous_ref if famous_ref else "Building Side Projects"
        t = topic if topic else "Software Engineering"
        return f"What {ref} Taught Me About {t}"

    # All formula functions in order
    formulas = [
        ("how_achieved", formula_how_achieved),
        ("number_list", formula_number_list),
        ("why_wrong", formula_why_wrong),
        ("counterintuitive", formula_counterintuitive),
        ("guide", formula_guide),
        ("stop_do", formula_stop_do),
        ("problem_solution", formula_problem_solution),
        ("learned", formula_learned),
        ("without", formula_without),
        ("taught_me", formula_taught_me),
    ]

    # --- Generate titles ---

    titles = []
    formulas_used = set()

    # First pass: one title per formula (up to count)
    for i, (name, fn) in enumerate(formulas):
        if len(titles) >= count:
            break
        title_text = fn()
        formulas_used.add(name)
        titles.append({
            "title": title_text,
            "formula": name,
        })

    # Second pass: if more are needed, cycle through formulas with variations
    cycle = 0
    while len(titles) < count:
        cycle += 1
        idx = cycle % len(formulas)
        name, fn = formulas[idx]
        title_text = fn()
        # Add slight variation to avoid exact duplicates
        suffixes = [" in {year}".format(year=2024 + cycle % 3),
                    " (And Why It Matters)",
                    " — A Deep Dive",
                    " for {audience}".format(audience=audience if audience else "Engineers"),
                    " That No One Talks About"]
        suffix = suffixes[cycle % len(suffixes)]
        title_text = title_text.rstrip(".") + suffix
        titles.append({
            "title": title_text,
            "formula": name + "_variant",
        })

    # --- Score each title ---

    def score_clarity(title):
        """How clear is the title about what the reader will get?"""
        score = 5.0
        # Shorter titles are clearer (sweet spot: 40-70 chars)
        length = len(title)
        if 40 <= length <= 70:
            score += 2.0
        elif 30 <= length < 40 or 70 < length <= 90:
            score += 1.0
        elif length > 120:
            score -= 2.0
        elif length > 90:
            score -= 1.0
        # Contains specific terms
        specifics = ["how", "why", "what", "guide", "tutorial", "lesson",
                     "pattern", "principle", "strategy", "technique"]
        lower = title.lower()
        for s in specifics:
            if s in lower:
                score += 0.5
                break
        # Penalize vague titles
        vague = ["stuff", "things", "misc", "some thoughts", "random"]
        for v in vague:
            if v in lower:
                score -= 1.5
                break
        # Topic mentioned in title
        if topic and topic.lower() in lower:
            score += 1.0
        return max(1, min(10, round(score, 1)))

    def score_curiosity_gap(title):
        """Does the title create a desire to know more?"""
        score = 5.0
        lower = title.lower()
        # Curiosity triggers
        triggers = ["why", "how", "what", "secret", "surprising", "unexpected",
                    "wrong", "mistake", "myth", "truth", "actually", "here's",
                    "no one", "nobody", "hidden", "overlooked"]
        for t in triggers:
            if t in lower:
                score += 1.0
                break
        # Question marks drive curiosity
        if "?" in title:
            score += 1.5
        # Contrast words
        contrasts = ["but", "however", "instead", "without", "not", "stop",
                     "dead", "broken", "overrated"]
        for c in contrasts:
            if c in lower:
                score += 1.0
                break
        # Numbers suggest structured content
        if re.search(r'\b\d+\b', title):
            score += 0.5
        # Colons/dashes suggest depth
        if ":" in title or " — " in title or " - " in title:
            score += 0.5
        # Very generic titles have low curiosity
        if len(title) < 20:
            score -= 1.5
        return max(1, min(10, round(score, 1)))

    def score_specificity(title):
        """How specific and concrete is the title?"""
        score = 5.0
        lower = title.lower()
        # Named technologies, companies, specific terms
        if topic and topic.lower() in lower:
            score += 2.0
        # Numbers add specificity
        if re.search(r'\b\d+\b', title):
            score += 1.5
        # Concrete nouns
        concrete = ["api", "database", "deploy", "test", "scale", "performance",
                    "security", "architecture", "pipeline", "kubernetes", "docker",
                    "react", "python", "go", "rust", "typescript", "sql"]
        for c in concrete:
            if c in lower:
                score += 1.0
                break
        # Time references add specificity
        if re.search(r'\b(year|month|week|day|hour|minute|202\d)\b', lower):
            score += 0.5
        # Very short titles are often too vague
        words = title.split()
        if len(words) < 4:
            score -= 1.5
        elif len(words) > 15:
            score -= 1.0  # Too wordy reduces specificity
        # Audience mentioned
        if audience and audience.lower() in lower:
            score += 0.5
        return max(1, min(10, round(score, 1)))

    def score_shareability(title):
        """How likely is someone to share this title?"""
        score = 5.0
        lower = title.lower()
        length = len(title)
        # Ideal Twitter-friendly length (< 100 chars)
        if length <= 80:
            score += 1.0
        elif length <= 100:
            score += 0.5
        elif length > 140:
            score -= 1.5
        # Emotional triggers
        emotional = ["wrong", "mistake", "secret", "truth", "dead",
                     "overrated", "actually", "surprising", "love", "hate",
                     "stop", "never", "always", "best", "worst"]
        for e in emotional:
            if e in lower:
                score += 1.0
                break
        # Contrarian titles get shared more
        contrarian = ["wrong", "dead", "overrated", "broken", "stop",
                      "not what you think", "myth", "lie"]
        for c in contrarian:
            if c in lower:
                score += 1.0
                break
        # Personal angle ("I", "my", "we")
        if re.search(r'\b(I|my|we|our)\b', title):
            score += 0.5
        # Numbers (listicles are highly shareable)
        if re.search(r'^\d+\b', title):
            score += 1.5
        elif re.search(r'\b\d+\b', title):
            score += 0.5
        # Colon suggests depth/value
        if ":" in title:
            score += 0.5
        return max(1, min(10, round(score, 1)))

    # Score all titles
    for entry in titles:
        t = entry["title"]
        clarity = score_clarity(t)
        curiosity = score_curiosity_gap(t)
        specificity = score_specificity(t)
        shareability = score_shareability(t)
        composite = round((clarity + curiosity + specificity + shareability) / 4.0, 1)
        entry["scores"] = {
            "clarity": clarity,
            "curiosity_gap": curiosity,
            "specificity": specificity,
            "shareability": shareability,
            "composite": composite,
        }

    # Sort by composite score descending
    titles.sort(key=lambda x: -x["scores"]["composite"])

    # Add rank
    for i, entry in enumerate(titles):
        entry["rank"] = i + 1

    # --- Build output ---

    result = {
        "titles": titles,
        "count": len(titles),
        "topic": topic,
        "inputs_used": {
            "research_synthesis": os.path.exists(research_file),
            "materials": os.path.exists(materials_file),
            "pipeline_state": os.path.exists(pipeline_file),
        },
        "formulas_available": len(formulas),
    }

    print(json.dumps(result, indent=2))

    # Atomic write to state
    target_file = os.path.join(state_dir, "title-variations.json")
    atomic_json_write(target_file, result)


if __name__ == "__main__":
    main()
