#!/usr/bin/env bash
# Compare two article drafts side-by-side
# Usage: article-compare.sh <file1> <file2> [--json] [--no-color]
# Outputs word count diff, structure diff, reading level diff,
# highlights significantly changed sections, and summarizes improvements/regressions.
set -euo pipefail

FILE1="${1:-}"
FILE2="${2:-}"
JSON_OUTPUT=false
NO_COLOR=false

# Parse optional flags
shift 2 2>/dev/null || true
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON_OUTPUT=true; shift ;;
    --no-color) NO_COLOR=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$FILE1" ] || [ -z "$FILE2" ]; then
  echo "Usage: article-compare.sh <file1> <file2> [--json] [--no-color]" >&2
  echo "" >&2
  echo "Compares two article drafts and reports:" >&2
  echo "  - Word count differences" >&2
  echo "  - Structure (heading) differences" >&2
  echo "  - Reading level differences" >&2
  echo "  - Sections with significant changes" >&2
  echo "  - Summary of improvements and regressions" >&2
  exit 1
fi

if [ ! -f "$FILE1" ]; then
  echo "ERROR: File not found: $FILE1" >&2
  exit 1
fi

if [ ! -f "$FILE2" ]; then
  echo "ERROR: File not found: $FILE2" >&2
  exit 1
fi

python3 - "$FILE1" "$FILE2" "$JSON_OUTPUT" "$NO_COLOR" << 'PYEOF'
import sys
import re
import math
import json
import os
from difflib import SequenceMatcher

file1_path = sys.argv[1]
file2_path = sys.argv[2]
json_output = sys.argv[3].lower() == "true"
no_color = sys.argv[4].lower() == "true"

# --- Color helpers ---
def color(text, code):
    if no_color or json_output:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(text):  return color(text, "32")
def red(text):    return color(text, "31")
def yellow(text): return color(text, "33")
def bold(text):   return color(text, "1")
def dim(text):    return color(text, "2")
def cyan(text):   return color(text, "36")

# --- File reading ---
def read_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

text1 = read_file(file1_path)
text2 = read_file(file2_path)

# --- Word count analysis ---
def count_words(text):
    return len(text.split())

def count_sentences(text):
    # Split on sentence-ending punctuation followed by space or end of string
    sentences = re.split(r'[.!?]+(?:\s|$)', text)
    return max(1, len([s for s in sentences if s.strip()]))

def count_syllables(word):
    word = word.lower().strip(".,!?;:'\"()-")
    if not word:
        return 0
    # Simple syllable counting heuristic
    count = 0
    vowels = "aeiouy"
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # Handle silent e
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)

def count_complex_words(text):
    """Words with 3+ syllables (not counting common suffixes)."""
    words = text.split()
    return sum(1 for w in words if count_syllables(w) >= 3)

# --- Reading level metrics ---
def flesch_kincaid_grade(text):
    words = count_words(text)
    sentences = count_sentences(text)
    syllables = sum(count_syllables(w) for w in text.split())
    if words == 0 or sentences == 0:
        return 0.0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

def flesch_reading_ease(text):
    words = count_words(text)
    sentences = count_sentences(text)
    syllables = sum(count_syllables(w) for w in text.split())
    if words == 0 or sentences == 0:
        return 0.0
    return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

def gunning_fog(text):
    words = count_words(text)
    sentences = count_sentences(text)
    complex_words = count_complex_words(text)
    if words == 0 or sentences == 0:
        return 0.0
    return 0.4 * ((words / sentences) + 100.0 * (complex_words / words))

def reading_ease_label(score):
    if score >= 80:   return "Easy"
    elif score >= 60: return "Standard"
    elif score >= 40: return "Difficult"
    elif score >= 20: return "Very Difficult"
    else:             return "Extremely Difficult"

def avg_sentence_length(text):
    words = count_words(text)
    sentences = count_sentences(text)
    if sentences == 0:
        return 0.0
    return words / sentences

# --- Structure (heading) extraction ---
def extract_headings(text):
    """Extract markdown headings with their level and text."""
    headings = []
    for line in text.split("\n"):
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append({"level": level, "title": title})
    return headings

# --- Section extraction ---
def extract_sections(text):
    """Split text into sections by headings. Returns list of {heading, content, level}."""
    lines = text.split("\n")
    sections = []
    current_heading = "(Introduction)"
    current_level = 0
    current_lines = []

    for line in lines:
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            # Save previous section
            if current_lines or current_heading:
                content = "\n".join(current_lines).strip()
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": content
                })
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    content = "\n".join(current_lines).strip()
    if content or current_heading != "(Introduction)":
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "content": content
        })

    return sections

# --- Section comparison ---
def compare_sections(sections1, sections2):
    """Compare sections between two drafts. Returns list of change descriptors."""
    changes = []
    headings1 = {s["heading"]: s for s in sections1}
    headings2 = {s["heading"]: s for s in sections2}

    all_headings = []
    seen = set()
    for s in sections1 + sections2:
        if s["heading"] not in seen:
            all_headings.append(s["heading"])
            seen.add(s["heading"])

    for heading in all_headings:
        s1 = headings1.get(heading)
        s2 = headings2.get(heading)

        if s1 and not s2:
            changes.append({
                "heading": heading,
                "type": "removed",
                "detail": f"Section removed ({count_words(s1['content'])} words)"
            })
        elif s2 and not s1:
            changes.append({
                "heading": heading,
                "type": "added",
                "detail": f"Section added ({count_words(s2['content'])} words)"
            })
        elif s1 and s2:
            similarity = SequenceMatcher(None, s1["content"], s2["content"]).ratio()
            w1 = count_words(s1["content"])
            w2 = count_words(s2["content"])
            word_delta = w2 - w1

            if similarity < 0.5:
                change_type = "major_rewrite"
            elif similarity < 0.8:
                change_type = "significant_edit"
            elif similarity < 0.95:
                change_type = "minor_edit"
            else:
                change_type = "unchanged"

            changes.append({
                "heading": heading,
                "type": change_type,
                "similarity": round(similarity * 100, 1),
                "words_before": w1,
                "words_after": w2,
                "word_delta": word_delta,
                "detail": f"{round(similarity * 100, 1)}% similar, {word_delta:+d} words"
            })

    return changes

# --- Code block analysis ---
def count_code_blocks(text):
    return len(re.findall(r'```', text)) // 2

def code_density(text):
    """Percentage of text that is inside code blocks."""
    in_code = False
    code_lines = 0
    total_lines = 0
    for line in text.split("\n"):
        total_lines += 1
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
    if total_lines == 0:
        return 0.0
    return round(100.0 * code_lines / total_lines, 1)

# --- Paragraph analysis ---
def count_paragraphs(text):
    paragraphs = re.split(r'\n\s*\n', text)
    return len([p for p in paragraphs if p.strip()])

def avg_paragraph_length(text):
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p for p in paragraphs if p.strip()]
    if not paragraphs:
        return 0.0
    return sum(count_words(p) for p in paragraphs) / len(paragraphs)

# --- Link analysis ---
def count_links(text):
    return len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text))

# --- Compute all metrics ---
def compute_metrics(text):
    return {
        "word_count": count_words(text),
        "sentence_count": count_sentences(text),
        "paragraph_count": count_paragraphs(text),
        "heading_count": len(extract_headings(text)),
        "code_block_count": count_code_blocks(text),
        "code_density": code_density(text),
        "link_count": count_links(text),
        "avg_sentence_length": round(avg_sentence_length(text), 1),
        "avg_paragraph_length": round(avg_paragraph_length(text), 1),
        "flesch_kincaid_grade": round(flesch_kincaid_grade(text), 1),
        "flesch_reading_ease": round(flesch_reading_ease(text), 1),
        "gunning_fog": round(gunning_fog(text), 1),
        "reading_ease_label": reading_ease_label(flesch_reading_ease(text)),
    }

metrics1 = compute_metrics(text1)
metrics2 = compute_metrics(text2)

headings1 = extract_headings(text1)
headings2 = extract_headings(text2)

sections1 = extract_sections(text1)
sections2 = extract_sections(text2)

section_changes = compare_sections(sections1, sections2)

# --- Improvements / Regressions ---
def assess_changes(m1, m2, changes):
    improvements = []
    regressions = []
    neutral = []

    # Word count
    wdiff = m2["word_count"] - m1["word_count"]
    if abs(wdiff) > 50:
        item = f"Word count: {m1['word_count']} -> {m2['word_count']} ({wdiff:+d})"
        if abs(wdiff) / max(m1["word_count"], 1) < 0.3:
            neutral.append(item)
        elif wdiff > 0:
            improvements.append(item + " (more thorough)")
        else:
            # Could be improvement (tighter) or regression (lost content)
            significant_removals = [c for c in changes if c["type"] == "removed"]
            if significant_removals:
                regressions.append(item + " (sections removed)")
            else:
                improvements.append(item + " (tighter writing)")

    # Reading level
    fk_diff = m2["flesch_kincaid_grade"] - m1["flesch_kincaid_grade"]
    if abs(fk_diff) >= 0.5:
        item = f"Reading level: grade {m1['flesch_kincaid_grade']} -> {m2['flesch_kincaid_grade']} ({fk_diff:+.1f})"
        if fk_diff < -0.5:
            improvements.append(item + " (more accessible)")
        elif fk_diff > 1.0:
            regressions.append(item + " (harder to read)")
        else:
            neutral.append(item)

    # Reading ease
    re_diff = m2["flesch_reading_ease"] - m1["flesch_reading_ease"]
    if abs(re_diff) >= 3:
        item = f"Reading ease: {m1['flesch_reading_ease']} -> {m2['flesch_reading_ease']} ({re_diff:+.1f})"
        if re_diff > 3:
            improvements.append(item + " (easier to read)")
        elif re_diff < -3:
            regressions.append(item + " (harder to read)")

    # Sentence length
    sl_diff = m2["avg_sentence_length"] - m1["avg_sentence_length"]
    if abs(sl_diff) >= 2:
        item = f"Avg sentence length: {m1['avg_sentence_length']} -> {m2['avg_sentence_length']} ({sl_diff:+.1f} words)"
        if sl_diff < -2 and m1["avg_sentence_length"] > 20:
            improvements.append(item + " (shorter sentences)")
        elif sl_diff > 3:
            regressions.append(item + " (longer sentences)")
        else:
            neutral.append(item)

    # Structure
    hdiff = m2["heading_count"] - m1["heading_count"]
    if hdiff != 0:
        item = f"Headings: {m1['heading_count']} -> {m2['heading_count']} ({hdiff:+d})"
        if hdiff > 0:
            improvements.append(item + " (better structure)")
        elif m2["heading_count"] < 2:
            regressions.append(item + " (lost structure)")
        else:
            neutral.append(item)

    # Code density
    cd_diff = m2["code_density"] - m1["code_density"]
    if abs(cd_diff) >= 5:
        item = f"Code density: {m1['code_density']}% -> {m2['code_density']}% ({cd_diff:+.1f}%)"
        neutral.append(item)

    # Section rewrites
    major_rewrites = [c for c in changes if c["type"] == "major_rewrite"]
    if major_rewrites:
        for c in major_rewrites:
            improvements.append(f"Major rewrite: \"{c['heading']}\" ({c['similarity']}% similarity)")

    # Added sections
    added = [c for c in changes if c["type"] == "added"]
    if added:
        for c in added:
            improvements.append(f"New section: \"{c['heading']}\"")

    # Removed sections
    removed = [c for c in changes if c["type"] == "removed"]
    if removed:
        for c in removed:
            regressions.append(f"Removed section: \"{c['heading']}\"")

    return improvements, regressions, neutral

improvements, regressions, neutral = assess_changes(metrics1, metrics2, section_changes)

# --- Overall similarity ---
overall_similarity = round(SequenceMatcher(None, text1, text2).ratio() * 100, 1)

# --- JSON output ---
if json_output:
    result = {
        "file1": os.path.basename(file1_path),
        "file2": os.path.basename(file2_path),
        "overall_similarity": overall_similarity,
        "metrics": {
            "file1": metrics1,
            "file2": metrics2,
        },
        "headings": {
            "file1": [h["title"] for h in headings1],
            "file2": [h["title"] for h in headings2],
        },
        "section_changes": section_changes,
        "improvements": improvements,
        "regressions": regressions,
        "neutral_changes": neutral,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0)

# --- Human-readable output ---

name1 = os.path.basename(file1_path)
name2 = os.path.basename(file2_path)

print(bold(f"Article Comparison: {name1} vs {name2}"))
print("=" * 60)

# Word count
print(f"\n{bold('WORD COUNT')}")
wdiff = metrics2["word_count"] - metrics1["word_count"]
pct = round(100 * wdiff / max(metrics1["word_count"], 1), 1)
indicator = green(f"+{wdiff}") if wdiff > 0 else red(str(wdiff)) if wdiff < 0 else dim("0")
print(f"  {name1}: {metrics1['word_count']} words")
print(f"  {name2}: {metrics2['word_count']} words")
print(f"  Delta:  {indicator} words ({pct:+.1f}%)")

# Structural metrics
print(f"\n{bold('STRUCTURE')}")
print(f"  {'Metric':<25s} {'File 1':>8s} {'File 2':>8s} {'Delta':>8s}")
print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
for label, key in [
    ("Headings", "heading_count"),
    ("Paragraphs", "paragraph_count"),
    ("Sentences", "sentence_count"),
    ("Code blocks", "code_block_count"),
    ("Links", "link_count"),
]:
    v1 = metrics1[key]
    v2 = metrics2[key]
    delta = v2 - v1
    ds = f"{delta:+d}" if delta != 0 else "-"
    print(f"  {label:<25s} {v1:>8} {v2:>8} {ds:>8}")

# Reading level
print(f"\n{bold('READING LEVEL')}")
print(f"  {'Metric':<25s} {'File 1':>8s} {'File 2':>8s} {'Delta':>8s}")
print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
for label, key in [
    ("Flesch-Kincaid Grade", "flesch_kincaid_grade"),
    ("Flesch Reading Ease", "flesch_reading_ease"),
    ("Gunning Fog Index", "gunning_fog"),
    ("Avg Sentence Length", "avg_sentence_length"),
    ("Avg Paragraph Length", "avg_paragraph_length"),
    ("Code Density %", "code_density"),
]:
    v1 = metrics1[key]
    v2 = metrics2[key]
    delta = round(v2 - v1, 1)
    ds = f"{delta:+.1f}" if delta != 0 else "-"
    print(f"  {label:<25s} {v1:>8} {v2:>8} {ds:>8}")

print(f"  Reading ease: {metrics1['reading_ease_label']} -> {metrics2['reading_ease_label']}")

# Heading structure diff
print(f"\n{bold('HEADING STRUCTURE')}")
h1_titles = [h["title"] for h in headings1]
h2_titles = [h["title"] for h in headings2]
if h1_titles == h2_titles:
    print(f"  {dim('(identical)')}")
else:
    added_h = [h for h in h2_titles if h not in h1_titles]
    removed_h = [h for h in h1_titles if h not in h2_titles]
    kept_h = [h for h in h1_titles if h in h2_titles]
    if kept_h:
        for h in kept_h:
            print(f"  {dim('  ')} {h}")
    if added_h:
        for h in added_h:
            print(f"  {green('+ ' + h)}")
    if removed_h:
        for h in removed_h:
            print(f"  {red('- ' + h)}")

# Section changes
significant = [c for c in section_changes if c["type"] in ("major_rewrite", "significant_edit", "added", "removed")]
if significant:
    print(f"\n{bold('SIGNIFICANT SECTION CHANGES')}")
    for c in significant:
        if c["type"] == "added":
            print(f"  {green('[ADDED]')}    {c['heading']} - {c['detail']}")
        elif c["type"] == "removed":
            print(f"  {red('[REMOVED]')}  {c['heading']} - {c['detail']}")
        elif c["type"] == "major_rewrite":
            print(f"  {yellow('[REWRITE]')} {c['heading']} - {c['detail']}")
        elif c["type"] == "significant_edit":
            print(f"  {cyan('[EDITED]')}   {c['heading']} - {c['detail']}")

# Summary
print(f"\n{bold('SUMMARY')}")
print(f"  Overall similarity: {overall_similarity}%")

if improvements:
    print(f"\n  {green('Improvements:')}")
    for item in improvements:
        print(f"    {green('+')} {item}")

if regressions:
    print(f"\n  {red('Regressions:')}")
    for item in regressions:
        print(f"    {red('-')} {item}")

if neutral:
    print(f"\n  {dim('Neutral changes:')}")
    for item in neutral:
        print(f"    {dim('~')} {item}")

if not improvements and not regressions and not neutral:
    if overall_similarity > 95:
        print(f"  {dim('Files are nearly identical — no significant changes detected.')}")
    else:
        print(f"  {dim('Changes detected but no clear improvements or regressions.')}")

print()
PYEOF
