#!/usr/bin/env python3
"""Word frequency analysis for markdown files.
Detects overused words, jargon density, and AI-generated text patterns.
Usage: word_frequency.py <markdown_file> [top_n]
"""

import json
import os
import re
import sys
from collections import Counter


def usage():
    print("""Usage: word_frequency.py <markdown_file> [top_n]

Analyzes word frequencies in a markdown file:
  - Top N word frequencies (default 25), excluding stop words
  - Overused words (>2% frequency)
  - Jargon density measurement
  - AI-generated text pattern detection

Output: JSON report to stdout""")


# -- Strip markdown formatting --

def strip_markdown(text):
    """Remove markdown syntax, code blocks, frontmatter, etc."""
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    return text.strip()


# -- Stop words --

STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'need',
    'dare', 'ought', 'used', 'not', 'no', 'nor', 'so', 'yet', 'both',
    'each', 'few', 'more', 'most', 'other', 'some', 'such', 'than',
    'too', 'very', 'just', 'about', 'above', 'after', 'again', 'all',
    'also', 'am', 'any', 'because', 'before', 'between', 'during',
    'even', 'get', 'got', 'here', 'how', 'i', 'if', 'into', 'it',
    'its', 'like', 'make', 'many', 'me', 'much', 'my', 'new', 'now',
    'only', 'our', 'out', 'over', 'own', 'same', 'she', 'he', 'her',
    'him', 'his', 'that', 'their', 'them', 'then', 'there', 'these',
    'they', 'this', 'those', 'through', 'under', 'up', 'us', 'we',
    'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why',
    'you', 'your', 'one', 'two', 'three', 'first', 'way', 'well',
    's', 't', 'd', 're', 've', 'll', 'don', 'doesn', 'didn', 'won',
    'isn', 'aren', 'wasn', 'weren', 'hasn', 'haven', 'hadn', 'wouldn',
    'couldn', 'shouldn', 'mustn', 'let', 'de', 'use', 'using',
    'still', 'already', 'down', 'off', 'once', 'until', 'without',
    'however', 'although', 'though', 'since', 'whether', 'either',
    'neither', 'rather', 'quite', 'enough', 'less', 'least', 'never',
    'always', 'often', 'sometimes', 'usually', 'actually', 'really',
    'simply', 'basically', 'especially', 'particularly', 'specifically',
    'generally', 'typically', 'essentially',
}

# -- AI slop words --

AI_PATTERN_WORDS = [
    'delve', 'landscape', 'leverage', 'utilize', 'facilitate',
    'streamline', 'robust', 'comprehensive',
]

# Extended AI patterns (common AI writing tells)
AI_EXTENDED_PATTERNS = [
    'tapestry', 'multifaceted', 'ever-evolving', 'game-changer',
    'paradigm', 'synergy', 'holistic', 'cutting-edge', 'pivotal',
    'groundbreaking', 'transformative', 'revolutionize', 'empower',
    'spearhead', 'harness', 'navigate', 'realm', 'aforementioned',
    'fostering', 'enhancing', 'bolstering',
]

# -- Jargon / technical terms --

JARGON_PATTERNS = [
    r'\b\w+ization\b', r'\b\w+ifiable\b', r'\b\w+istically\b',
    r'\bsynerg\w+\b', r'\bparadigm\b', r'\bholistic\b',
    r'\bscalability\b', r'\binteroperab\w+\b', r'\bagnostic\b',
    r'\bidempoten\w+\b', r'\borthogonal\b', r'\bnon-trivial\b',
    r'\bbespoke\b', r'\bopinionated\b', r'\bfirst-class\b',
    r'\bout-of-the-box\b', r'\bturnkey\b', r'\bboilerplate\b',
    r'\bblocking\b', r'\bnon-blocking\b', r'\basynchronous\b',
]


def extract_words(text):
    """Extract lowercase words from text."""
    return [w.lower() for w in re.findall(r"[a-zA-Z']+", text) if len(w) > 1]


def analyze(markdown_file, top_n=25):
    """Run word frequency analysis on a markdown file. Returns JSON result dict."""
    with open(markdown_file, 'r') as f:
        raw_content = f.read()

    prose = strip_markdown(raw_content)

    all_words = extract_words(prose)
    total_words = len(all_words)

    # Filter out stop words for frequency analysis
    content_words = [w for w in all_words if w.lower() not in STOP_WORDS]
    total_content_words = len(content_words)

    # Word frequency counts
    freq = Counter(content_words)
    top_words = freq.most_common(top_n)

    # -- Overused words (>2% of content words) --
    overused = []
    if total_content_words > 0:
        for word, count in freq.items():
            pct = count / total_content_words * 100
            if pct > 2.0:
                overused.append({
                    "word": word,
                    "count": count,
                    "percentage": round(pct, 2)
                })
        overused.sort(key=lambda x: x["percentage"], reverse=True)

    # -- AI pattern detection --
    ai_flags = []
    all_words_lower = [w.lower() for w in all_words]
    word_freq_all = Counter(all_words_lower)

    for ai_word in AI_PATTERN_WORDS:
        count = word_freq_all.get(ai_word, 0)
        for variant in [ai_word + 's', ai_word + 'd', ai_word + 'ing']:
            count += word_freq_all.get(variant, 0)
        if count > 0:
            ai_flags.append({
                "word": ai_word,
                "count": count,
                "severity": "high"
            })

    for ai_word in AI_EXTENDED_PATTERNS:
        count = word_freq_all.get(ai_word, 0)
        for variant in [ai_word + 's', ai_word + 'd', ai_word + 'ing']:
            count += word_freq_all.get(variant, 0)
        if count > 0:
            ai_flags.append({
                "word": ai_word,
                "count": count,
                "severity": "medium"
            })

    ai_word_total = sum(f["count"] for f in ai_flags)
    ai_score = round(
        (ai_word_total / total_words * 100) if total_words > 0 else 0, 2
    )

    # Risk level based on AI pattern density
    if ai_score > 2.0 or len([f for f in ai_flags if f["severity"] == "high"]) >= 3:
        ai_risk = "high"
    elif ai_score > 0.5 or len(ai_flags) >= 3:
        ai_risk = "medium"
    elif len(ai_flags) > 0:
        ai_risk = "low"
    else:
        ai_risk = "none"

    # -- Jargon density --
    jargon_matches = []
    prose_lower = prose.lower()
    for pattern in JARGON_PATTERNS:
        matches = re.findall(pattern, prose_lower)
        jargon_matches.extend(matches)

    jargon_unique = list(set(jargon_matches))
    jargon_count = len(jargon_matches)
    jargon_density = round(
        (jargon_count / total_words * 100) if total_words > 0 else 0, 2
    )

    if jargon_density > 5.0:
        jargon_level = "very_high"
    elif jargon_density > 3.0:
        jargon_level = "high"
    elif jargon_density > 1.0:
        jargon_level = "moderate"
    else:
        jargon_level = "low"

    # -- Vocabulary richness (type-token ratio) --
    unique_words = len(set(content_words))
    ttr = round(unique_words / total_content_words, 4) if total_content_words > 0 else 0

    # -- Build result --
    result = {
        "file": os.path.basename(markdown_file),
        "total_words": total_words,
        "content_words": total_content_words,
        "unique_words": unique_words,
        "type_token_ratio": ttr,
        "top_words": [
            {"word": w, "count": c, "percentage": round(c / total_content_words * 100, 2) if total_content_words > 0 else 0}
            for w, c in top_words
        ],
        "overused_words": overused,
        "jargon": {
            "density_percentage": jargon_density,
            "level": jargon_level,
            "count": jargon_count,
            "unique_terms": sorted(jargon_unique)
        },
        "ai_patterns": {
            "risk_level": ai_risk,
            "ai_word_percentage": ai_score,
            "flagged_words": ai_flags,
            "total_ai_word_count": ai_word_total
        }
    }

    return result


def main():
    markdown_file = sys.argv[1] if len(sys.argv) > 1 else ""
    top_n_arg = sys.argv[2] if len(sys.argv) > 2 else "25"

    if not markdown_file:
        usage()
        print('{"error":"no file specified"}', file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(markdown_file):
        print(json.dumps({"error": "file not found", "file": markdown_file}))
        sys.exit(1)

    try:
        top_n = int(top_n_arg)
    except ValueError:
        top_n = 25

    result = analyze(markdown_file, top_n)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
