#!/usr/bin/env python3
"""Readability analysis for markdown files.
Calculates Flesch-Kincaid grade level, sentence/word metrics, complexity, passive voice.
Usage: readability_score.py <markdown_file> [verbose]
"""

import json
import os
import re
import sys


def usage():
    print("""Usage: readability_score.py <markdown_file> [verbose]

Analyzes a markdown file for readability:
  - Flesch-Kincaid readability grade level
  - Average sentence length and word length (syllables)
  - Paragraph, sentence, word counts
  - Overly complex sentences (>30 words)
  - Passive voice detection

Output: JSON report to stdout
  verbose: includes per-sentence breakdown""")


# -- Strip markdown formatting to get prose text --

def strip_markdown(text):
    """Remove markdown syntax, code blocks, frontmatter, headings markers, links, images."""
    # Remove YAML frontmatter
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    # Remove fenced code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove images
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    # Convert links to just their text
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # Remove heading markers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove blockquotes marker
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    return text.strip()


# -- Syllable counting --

def count_syllables(word):
    """Estimate syllable count for an English word."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 2:
        return 1

    # Common suffixes that don't add syllables
    word_adj = word
    if word_adj.endswith('es') or word_adj.endswith('ed'):
        if not word_adj.endswith('ted') and not word_adj.endswith('ded') and \
           not word_adj.endswith('les') and not word_adj.endswith('ces') and \
           not word_adj.endswith('ges') and not word_adj.endswith('ses') and \
           not word_adj.endswith('zes'):
            word_adj = word_adj[:-2]
    if word_adj.endswith('e') and not word_adj.endswith('le'):
        word_adj = word_adj[:-1]

    # Count vowel groups
    vowels = 'aeiouy'
    count = 0
    prev_vowel = False
    for ch in word_adj:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    return max(1, count)


# -- Sentence splitting --

def split_sentences(text):
    """Split text into sentences. Handles common abbreviations."""
    # Protect common abbreviations
    protected = text
    abbrevs = ['Mr.', 'Mrs.', 'Dr.', 'Prof.', 'Sr.', 'Jr.', 'vs.', 'etc.',
               'e.g.', 'i.e.', 'Fig.', 'fig.', 'No.', 'no.', 'Vol.', 'vol.']
    for abbr in abbrevs:
        protected = protected.replace(abbr, abbr.replace('.', '\x00'))

    # Split on sentence-ending punctuation followed by space or end
    raw_sentences = re.split(r'(?<=[.!?])\s+', protected)

    sentences = []
    for s in raw_sentences:
        s = s.replace('\x00', '.').strip()
        # Only keep sentences with actual words
        words = re.findall(r'[a-zA-Z]+', s)
        if len(words) >= 2:
            sentences.append(s)
    return sentences


# -- Passive voice detection --

PASSIVE_PATTERN = re.compile(
    r'\b(?:is|are|was|were|been|being|be|am|get|gets|got|gotten)\s+'
    r'(?:\w+\s+)*?'  # optional adverbs
    r'(?:\w+ed|built|chosen|done|drawn|driven|eaten|fallen|felt|found|given|gone|'
    r'grown|had|heard|held|hidden|hit|hurt|kept|known|laid|led|left|lent|let|'
    r'lost|made|meant|met|paid|put|read|rid|run|said|seen|sent|set|shown|shut|'
    r'sold|spent|spoken|stood|stuck|taken|taught|thought|told|understood|won|'
    r'worn|written)\b',
    re.IGNORECASE
)


def detect_passive(sentence):
    """Return True if sentence likely contains passive voice."""
    return bool(PASSIVE_PATTERN.search(sentence))


# -- Paragraph counting --

def count_paragraphs(text):
    """Count non-empty paragraphs."""
    paragraphs = re.split(r'\n\s*\n', text)
    return len([p for p in paragraphs if p.strip()])


# -- Grade level interpretation --

def interpret_grade(grade):
    if grade <= 6:
        return "elementary"
    elif grade <= 8:
        return "middle_school"
    elif grade <= 10:
        return "high_school"
    elif grade <= 12:
        return "college_prep"
    elif grade <= 14:
        return "college"
    elif grade <= 16:
        return "graduate"
    else:
        return "professional"


def analyze(markdown_file, verbose=False):
    """Run readability analysis on a markdown file. Returns JSON result dict."""
    with open(markdown_file, 'r') as f:
        raw_content = f.read()

    prose = strip_markdown(raw_content)

    sentences = split_sentences(prose)
    all_words = []
    for s in sentences:
        words = re.findall(r"[a-zA-Z']+", s)
        all_words.extend(words)

    total_words = len(all_words)
    total_sentences = len(sentences)
    total_paragraphs = count_paragraphs(prose)
    total_syllables = sum(count_syllables(w) for w in all_words)

    # Flesch-Kincaid Grade Level
    if total_sentences > 0 and total_words > 0:
        avg_sentence_length = total_words / total_sentences
        avg_syllables_per_word = total_syllables / total_words
        fk_grade = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
        fk_grade = round(max(0, fk_grade), 2)

        # Flesch Reading Ease
        fre = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        fre = round(max(0, min(100, fre)), 2)
    else:
        avg_sentence_length = 0
        avg_syllables_per_word = 0
        fk_grade = 0
        fre = 0

    avg_sentence_length = round(avg_sentence_length, 2)
    avg_syllables_per_word = round(avg_syllables_per_word, 2)

    # Complex sentences (>30 words)
    complex_sentences = []
    for i, s in enumerate(sentences):
        words = re.findall(r"[a-zA-Z']+", s)
        if len(words) > 30:
            complex_sentences.append({
                "index": i,
                "word_count": len(words),
                "text": s[:120] + ("..." if len(s) > 120 else "")
            })

    # Passive voice detection
    passive_sentences = []
    for i, s in enumerate(sentences):
        if detect_passive(s):
            passive_sentences.append({
                "index": i,
                "text": s[:120] + ("..." if len(s) > 120 else "")
            })

    passive_percentage = round(
        (len(passive_sentences) / total_sentences * 100) if total_sentences > 0 else 0, 2
    )

    # Build result
    result = {
        "file": os.path.basename(markdown_file),
        "metrics": {
            "flesch_kincaid_grade": fk_grade,
            "flesch_reading_ease": fre,
            "grade_interpretation": interpret_grade(fk_grade),
            "avg_sentence_length": avg_sentence_length,
            "avg_syllables_per_word": avg_syllables_per_word,
            "total_words": total_words,
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
            "total_syllables": total_syllables
        },
        "complexity": {
            "complex_sentence_count": len(complex_sentences),
            "complex_sentences": complex_sentences
        },
        "passive_voice": {
            "passive_count": len(passive_sentences),
            "passive_percentage": passive_percentage,
            "passive_sentences": passive_sentences
        }
    }

    # Verbose: add per-sentence breakdown
    if verbose:
        sentence_details = []
        for i, s in enumerate(sentences):
            words = re.findall(r"[a-zA-Z']+", s)
            syllables = sum(count_syllables(w) for w in words)
            sentence_details.append({
                "index": i,
                "word_count": len(words),
                "syllable_count": syllables,
                "is_complex": len(words) > 30,
                "is_passive": detect_passive(s),
                "text": s[:200] + ("..." if len(s) > 200 else "")
            })
        result["sentence_details"] = sentence_details

    return result


def main():
    markdown_file = sys.argv[1] if len(sys.argv) > 1 else ""
    verbose_arg = sys.argv[2] if len(sys.argv) > 2 else ""

    if not markdown_file:
        usage()
        print('{"error":"no file specified"}', file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(markdown_file):
        print(json.dumps({"error": "file not found", "file": markdown_file}))
        sys.exit(1)

    verbose = verbose_arg == "verbose"
    result = analyze(markdown_file, verbose)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
