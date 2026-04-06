#!/usr/bin/env bash
# Hook workshop — generates and scores opening hook variations for articles
# Usage: hook-workshop.sh <project_dir> [style]
# Styles: story, data, question, contrast, bold (default: all)
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
STYLE="${2:-all}"
STATE_DIR="$PROJECT_DIR/.essay-state"

python3 - "$STATE_DIR" "$STYLE" << 'PYEOF'
import json, sys, os, re, hashlib

state_dir = sys.argv[1]
requested_style = sys.argv[2]

# --- Read inputs ---

research = {}
research_file = os.path.join(state_dir, "research-synthesis.json")
if os.path.exists(research_file):
    try:
        with open(research_file) as f:
            research = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

materials = {}
materials_file = os.path.join(state_dir, "materials.json")
if os.path.exists(materials_file):
    try:
        with open(materials_file) as f:
            materials = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

pipeline = {}
pipeline_file = os.path.join(state_dir, "pipeline-state.json")
if os.path.exists(pipeline_file):
    try:
        with open(pipeline_file) as f:
            pipeline = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

# --- Extract context from research ---

topic = pipeline.get("topic", research.get("topic", ""))
angle = research.get("unique_angle", research.get("angle", ""))
gap = research.get("gap", research.get("content_gap", ""))
audience = pipeline.get("target_audience", research.get("target_audience", ""))

key_findings = research.get("key_findings", research.get("findings", []))
if isinstance(key_findings, str):
    key_findings = [key_findings]

pain_points = research.get("pain_points", research.get("challenges", []))
if isinstance(pain_points, str):
    pain_points = [pain_points]

# Statistics/data points from research
statistics = research.get("statistics", research.get("data_points", research.get("stats", [])))
if isinstance(statistics, str):
    statistics = [statistics]
elif not isinstance(statistics, list):
    statistics = []

# Conventional wisdom
conventional = research.get("conventional_wisdom", research.get("common_beliefs", ""))
if isinstance(conventional, list) and conventional:
    conventional = conventional[0]
elif not isinstance(conventional, str):
    conventional = ""

# Approach
approach = research.get("approach", research.get("method", ""))
if isinstance(approach, list) and approach:
    approach = approach[0]
elif not isinstance(approach, str):
    approach = ""

# Result
result_text = research.get("result", research.get("outcome", ""))
if isinstance(result_text, list) and result_text:
    result_text = result_text[0]
elif not isinstance(result_text, str):
    result_text = ""

# Author
author = pipeline.get("author", research.get("author", ""))

# Competitor landscape
landscape = research.get("competitive_landscape", research.get("landscape", {}))
competitors = landscape.get("existing_articles", landscape.get("competitors", []))
competitor_count = len(competitors) if isinstance(competitors, list) else 0

# Deterministic seed
seed_str = topic + angle + gap
seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

# --- Hook generators ---

def gen_story_hook():
    """Personal anecdote opening."""
    t = topic if topic else "software engineering"
    pain = ""
    if pain_points and isinstance(pain_points, list) and pain_points:
        p = pain_points[0]
        if isinstance(p, dict):
            pain = p.get("name", p.get("problem", str(p)))
        else:
            pain = str(p)

    result_part = result_text if result_text else f"understanding {t} deeply"
    approach_part = approach if approach else "a different approach"

    if pain:
        hook = (
            f"Last year, I spent three weeks debugging what turned out to be a fundamental "
            f"misunderstanding of {t}. The problem was {pain}. That experience changed how I "
            f"think about {t} entirely, and led me to {approach_part} — which is what I want "
            f"to share with you today."
        )
    else:
        hook = (
            f"I still remember the moment it clicked. After months of struggling with {t}, "
            f"I stumbled onto {approach_part} almost by accident. What followed was {result_part}. "
            f"This is the story of what I learned, and why it might change your approach too."
        )
    return hook

def gen_data_hook():
    """Surprising statistic opening."""
    t = topic if topic else "this approach"

    # Try to use actual statistics from research
    if statistics and isinstance(statistics, list) and statistics:
        stat = statistics[0]
        if isinstance(stat, dict):
            stat_text = stat.get("value", stat.get("stat", str(stat)))
        else:
            stat_text = str(stat)
        hook = (
            f"Here's a number that should make you uncomfortable: {stat_text}. "
            f"Most teams working with {t} don't realize this, but the data tells a clear story. "
            f"And once you see it, you can't unsee it."
        )
    elif competitor_count > 0:
        hook = (
            f"There are over {competitor_count} articles about {t} — and most of them give "
            f"the same advice. But when you look at the actual data, the conventional approach "
            f"fails in predictable ways. Here's what the numbers really say."
        )
    else:
        hook = (
            f"According to recent industry data, teams that get {t} right see dramatically "
            f"different outcomes from those that don't. The gap isn't small — it's a chasm. "
            f"And the surprising part? The fix isn't what most people think."
        )
    return hook

def gen_question_hook():
    """Provocative question opening."""
    t = topic if topic else "your current approach"

    if conventional:
        hook = (
            f"What if everything you've been told about {t} is wrong? "
            f"The common wisdom says {conventional}. But what if that advice is not just "
            f"outdated — what if it's actively harmful? Before you dismiss this as contrarian "
            f"clickbait, consider this: the evidence has been hiding in plain sight."
        )
    elif pain_points and isinstance(pain_points, list) and pain_points:
        p = pain_points[0]
        if isinstance(p, dict):
            pain = p.get("name", p.get("problem", str(p)))
        else:
            pain = str(p)
        hook = (
            f"Why do so many teams still struggle with {pain}? It's not because the problem "
            f"is unsolvable — it's because we've been asking the wrong question entirely. "
            f"The real question isn't how to fix {pain}. It's why we created the conditions "
            f"for it in the first place."
        )
    else:
        hook = (
            f"When was the last time you questioned your assumptions about {t}? "
            f"Not the surface-level stuff — the deep, foundational beliefs that shape "
            f"every decision you make. Most engineers never do. And that's exactly the problem."
        )
    return hook

def gen_contrast_hook():
    """Before/after or problem/solution opening."""
    t = topic if topic else "software delivery"

    pain = ""
    if pain_points and isinstance(pain_points, list) and pain_points:
        p = pain_points[0]
        if isinstance(p, dict):
            pain = p.get("name", p.get("problem", str(p)))
        else:
            pain = str(p)

    result_part = result_text if result_text else f"a dramatically better outcome"

    if pain and approach:
        hook = (
            f"Before: {pain}. Deadlines slipping, team morale dropping, "
            f"and the same problems resurfacing sprint after sprint.\n\n"
            f"After: {result_part}. The difference? {approach}.\n\n"
            f"This isn't a fairy tale. It's a documented journey from one state to the "
            f"other, with every painful lesson along the way."
        )
    elif gap:
        hook = (
            f"There are two kinds of teams working with {t} today. The first kind follows "
            f"the standard playbook and gets standard results. The second kind discovered "
            f"something the first kind missed: {gap}.\n\n"
            f"The gap between these two groups is growing. Here's how to end up on the right side."
        )
    else:
        hook = (
            f"The old way: spend weeks on {t}, hope for the best, firefight when things break.\n\n"
            f"The new way: a systematic approach that catches problems before they happen and "
            f"scales without drama.\n\n"
            f"If you're still doing it the old way, this article is your upgrade path."
        )
    return hook

def gen_bold_hook():
    """Controversial statement opening."""
    t = topic if topic else "this technology"

    if conventional:
        hook = (
            f"I'm going to say something unpopular: {conventional} is wrong. "
            f"Not slightly wrong, not outdated-but-mostly-fine wrong — fundamentally, "
            f"dangerously wrong. And the industry's blind adherence to this idea is costing "
            f"teams millions of dollars and thousands of hours every year."
        )
    elif angle:
        hook = (
            f"Most of what's been written about {t} is, to put it bluntly, wrong. "
            f"Not because the authors are incompetent — but because they're all starting "
            f"from the same flawed premise. {angle}. "
            f"That single shift in perspective changes everything."
        )
    else:
        hook = (
            f"{t} is broken. Not in the 'needs a few tweaks' sense — in the "
            f"'the foundation is cracked' sense. And yet, we keep building on top of it, "
            f"adding complexity to hide the cracks instead of fixing them. "
            f"It's time to talk about what nobody wants to admit."
        )
    return hook

# Map of all hook styles
hook_generators = {
    "story": ("Personal anecdote", gen_story_hook),
    "data": ("Surprising statistic", gen_data_hook),
    "question": ("Provocative question", gen_question_hook),
    "contrast": ("Before/after contrast", gen_contrast_hook),
    "bold": ("Controversial statement", gen_bold_hook),
}

# --- Determine which hooks to generate ---

if requested_style == "all":
    styles_to_gen = list(hook_generators.keys())
else:
    if requested_style not in hook_generators:
        print(json.dumps({
            "error": f"Unknown style '{requested_style}'. Valid styles: {', '.join(hook_generators.keys())}",
        }))
        sys.exit(1)
    styles_to_gen = [requested_style]

# --- Generate and score hooks ---

def score_engagement(hook, style):
    """How likely is this hook to keep the reader reading?"""
    score = 5.0
    lower = hook.lower()
    # Strong opening sentence
    first_sentence = hook.split(".")[0] if "." in hook else hook[:80]
    if len(first_sentence) < 80:
        score += 1.0  # Punchy first sentence
    # Questions drive engagement
    if "?" in hook:
        score += 1.0
    # Emotional words
    emotional = ["struggle", "wrong", "painful", "broken", "surprising",
                 "dramatic", "dangerous", "uncomfortable", "changed",
                 "remember", "imagine", "unpopular"]
    for e in emotional:
        if e in lower:
            score += 0.5
            if score >= 9.5:
                break
    # Personal pronouns create connection
    if re.search(r'\b(I|you|we|your|my)\b', hook):
        score += 0.5
    # Concrete details
    if re.search(r'\b\d+\b', hook):
        score += 0.5
    # Story hooks are inherently engaging
    if style == "story":
        score += 0.5
    # Bold hooks grab attention
    if style == "bold":
        score += 0.5
    # Too long reduces engagement
    if len(hook) > 600:
        score -= 1.0
    elif len(hook) > 400:
        score -= 0.5
    return max(1, min(10, round(score, 1)))

def score_relevance(hook, style):
    """How relevant is the hook to the article's topic?"""
    score = 5.0
    lower = hook.lower()
    # Topic mentioned
    if topic and topic.lower() in lower:
        score += 2.0
    # Key findings referenced
    if key_findings:
        for f in key_findings[:3]:
            f_text = str(f).lower() if not isinstance(f, dict) else str(f.get("finding", f.get("name", ""))).lower()
            if f_text and any(word in lower for word in f_text.split()[:3] if len(word) > 4):
                score += 0.5
                break
    # Pain points referenced
    if pain_points:
        for p in pain_points[:3]:
            p_text = str(p).lower() if not isinstance(p, dict) else str(p.get("name", p.get("problem", ""))).lower()
            if p_text and any(word in lower for word in p_text.split()[:3] if len(word) > 4):
                score += 1.0
                break
    # Approach mentioned
    if approach and approach.lower()[:20] in lower:
        score += 1.0
    # Angle present
    if angle and any(word in lower for word in angle.lower().split()[:3] if len(word) > 4):
        score += 1.0
    # Generic hooks are less relevant
    generic_phrases = ["software engineering", "technology", "the industry"]
    for g in generic_phrases:
        if g in lower and not topic:
            score -= 0.5
    return max(1, min(10, round(score, 1)))

def score_authenticity(hook, style):
    """Does this hook feel genuine, not clickbaity?"""
    score = 6.0  # Start slightly above mid — our hooks are decent
    lower = hook.lower()
    # Overhyped phrases reduce authenticity
    clickbait = ["you won't believe", "mind-blowing", "game-changer",
                 "jaw-dropping", "insane", "crazy", "genius hack",
                 "this one trick", "doctors hate"]
    for c in clickbait:
        if c in lower:
            score -= 2.0
            break
    # Specific details increase authenticity
    if re.search(r'\b(week|month|year|sprint|team|project|codebase)\b', lower):
        score += 0.5
    if re.search(r'\b\d+\b', hook):
        score += 0.5
    # Hedging language shows honesty
    hedges = ["might", "perhaps", "in my experience", "for us", "your mileage"]
    for h in hedges:
        if h in lower:
            score += 0.5
            break
    # Story hooks feel more authentic
    if style == "story":
        score += 1.0
    # Data hooks with actual stats feel authentic
    if style == "data" and statistics:
        score += 1.0
    # Bold hooks risk feeling inauthentic
    if style == "bold":
        score -= 0.5
    # Question hooks are neutral
    # Contrast hooks with real details are good
    if style == "contrast" and (pain_points or result_text):
        score += 0.5
    # Too aggressive language
    aggressive = ["fundamentally", "dangerously", "catastrophically",
                  "millions of dollars", "blind adherence"]
    penalty = 0
    for a in aggressive:
        if a in lower:
            penalty += 0.3
    score -= min(1.5, penalty)
    return max(1, min(10, round(score, 1)))

hooks = []
for style_name in styles_to_gen:
    desc, gen_fn = hook_generators[style_name]
    hook_text = gen_fn()
    eng = score_engagement(hook_text, style_name)
    rel = score_relevance(hook_text, style_name)
    auth = score_authenticity(hook_text, style_name)
    composite = round((eng + rel + auth) / 3.0, 1)

    hooks.append({
        "style": style_name,
        "description": desc,
        "hook": hook_text,
        "scores": {
            "engagement": eng,
            "relevance": rel,
            "authenticity": auth,
            "composite": composite,
        },
        "word_count": len(hook_text.split()),
    })

# Sort by composite score descending
hooks.sort(key=lambda x: -x["scores"]["composite"])

# Add rank
for i, h in enumerate(hooks):
    h["rank"] = i + 1

# --- Build output ---

result = {
    "hooks": hooks,
    "count": len(hooks),
    "topic": topic,
    "requested_style": requested_style,
    "inputs_used": {
        "research_synthesis": os.path.exists(research_file),
        "materials": os.path.exists(materials_file),
        "pipeline_state": os.path.exists(pipeline_file),
    },
}

print(json.dumps(result, indent=2))

# Atomic write to state
tmp_file = os.path.join(state_dir, "hook-variations.json.tmp." + str(os.getpid()))
target_file = os.path.join(state_dir, "hook-variations.json")
with open(tmp_file, "w") as f:
    json.dump(result, f, indent=2)
os.rename(tmp_file, target_file)
PYEOF
