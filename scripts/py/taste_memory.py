#!/usr/bin/env python3
"""Taste memory — persist writing style preferences across sessions.
Inspired by gstack's design taste memory system.
Usage: taste_memory.py <command> [args...]
"""

import collections
import difflib
import json
import os
import re
import sys

from utils import atomic_json_write, read_json_file, timestamp_now

TASTE_DIR = os.path.expanduser("~/.tech-essay-writer")
TASTE_FILE = os.path.join(TASTE_DIR, "taste-memory.json")

VALID_FEEDBACK_CATEGORIES = ["tone", "structure", "vocabulary", "length", "code_density", "format"]


def usage():
    print("""Usage: taste-memory.sh <command> [args...]

Commands:
  read                          Read current taste memory
  update <project_dir> <file>   Update taste from completed article
  record-choice <key> <value>   Record a specific preference
  get-preference <key>          Get a specific preference
  history                       Show article history
  diff-learn <project_dir> <original_file> <edited_file>
                                Learn style patterns by comparing draft with user-edited version
  feedback <project_dir> <category> <text>
                                Record explicit feedback (tone|structure|vocabulary|length|code_density|format)
  suggest <project_dir>         Output personalized writing suggestions from accumulated taste data""")


def read_taste():
    return read_json_file(TASTE_FILE)


def write_taste(data):
    os.makedirs(TASTE_DIR, exist_ok=True)
    atomic_json_write(TASTE_FILE, data)


def cmd_read():
    taste = read_taste()
    if not taste:
        print("No taste memory yet. Will be populated after first article.")
        return 0

    print("=== Writing Style Preferences ===")
    if "preferred_variant" in taste:
        print(f"Preferred style: {taste['preferred_variant']}")
    if "tone_preferences" in taste:
        print(f"Tone: {', '.join(taste['tone_preferences'])}")
    if "structural_preferences" in taste:
        for k, v in taste["structural_preferences"].items():
            print(f"  {k}: {v}")
    if "topics_written" in taste:
        print(f"Topics covered: {len(taste['topics_written'])}")
        for t in taste["topics_written"][-5:]:
            print(f"  - {t['topic']} ({t['date']})")
    if "feedback_patterns" in taste:
        print("Feedback patterns:")
        for p in taste["feedback_patterns"][-5:]:
            print(f"  - {p}")
    if taste.get("learned_patterns"):
        print(f"Learned patterns: {len(taste['learned_patterns'])}")
        for lp in taste["learned_patterns"][-5:]:
            proj = lp.get("project", "?")
            print(f"  [{lp.get('timestamp', '?')[:10]}] project: {proj}")
            for ins in lp.get("insights", []):
                print(f"    - {ins}")
    if taste.get("explicit_preferences"):
        print("Explicit preferences:")
        cats = {}
        for fb in taste["explicit_preferences"]:
            cats.setdefault(fb["category"], []).append(fb["feedback"])
        for cat, items in cats.items():
            print(f"  [{cat}]")
            for item in items[-3:]:
                print(f"    - {item}")
    return 0


def cmd_update(args):
    if not args or not args[0]:
        print("ERROR: update requires <project_dir>", file=sys.stderr)
        return 1

    project_dir = args[0]
    taste = read_taste()
    now = timestamp_now()

    # Read pipeline state if it exists
    state_file = os.path.join(project_dir, ".essay-state", "pipeline-state.json")
    state = read_json_file(state_file)

    # Initialize structure if needed
    taste.setdefault("preferred_variant", None)
    taste.setdefault("tone_preferences", [])
    taste.setdefault("structural_preferences", {})
    taste.setdefault("topics_written", [])
    taste.setdefault("feedback_patterns", [])
    taste.setdefault("articles_count", 0)
    taste.setdefault("updated_at", now)

    # Update from pipeline state
    topic = state.get("topic", "unknown")
    variant = state.get("outline_variant")

    # Track topics
    taste["topics_written"].append({
        "topic": topic,
        "date": now,
        "variant": variant,
        "refinement_rounds": state.get("refinement_round", 0)
    })

    # Update variant preference (most recent wins, but track frequency)
    if variant:
        taste["preferred_variant"] = variant

    taste["articles_count"] += 1
    taste["updated_at"] = now

    # Keep last 50 topics max
    taste["topics_written"] = taste["topics_written"][-50:]

    write_taste(taste)
    print("Taste memory updated.")
    return 0


def cmd_record_choice(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: record-choice requires <key> <value>", file=sys.stderr)
        return 1

    key = args[0]
    value = args[1]
    taste = read_taste()
    now = timestamp_now()

    if key == "tone":
        taste.setdefault("tone_preferences", [])
        if value not in taste["tone_preferences"]:
            taste["tone_preferences"].append(value)
    elif key == "feedback":
        taste.setdefault("feedback_patterns", [])
        taste["feedback_patterns"].append(value)
        taste["feedback_patterns"] = taste["feedback_patterns"][-20:]
    else:
        taste.setdefault("structural_preferences", {})
        taste["structural_preferences"][key] = value

    taste["updated_at"] = now
    write_taste(taste)
    return 0


def cmd_get_preference(args):
    if not args or not args[0]:
        print("ERROR: get-preference requires <key>", file=sys.stderr)
        return 1

    key = args[0]
    taste = read_taste()

    if key == "tone":
        print(json.dumps(taste.get("tone_preferences", [])))
    elif key == "feedback":
        print(json.dumps(taste.get("feedback_patterns", [])))
    elif key == "variant":
        print(taste.get("preferred_variant", ""))
    else:
        prefs = taste.get("structural_preferences", {})
        print(prefs.get(key, ""))
    return 0


def cmd_history():
    taste = read_taste()
    topics = taste.get("topics_written", [])
    if not topics:
        print("No articles written yet.")
    else:
        print(f"Articles written: {len(topics)}")
        for t in topics:
            print(f"  [{t.get('date', '?')[:10]}] {t.get('topic', '?')} (variant: {t.get('variant', '?')})")
    return 0


def cmd_diff_learn(args):
    if len(args) < 3:
        print("ERROR: diff-learn requires <project_dir> <original_file> <edited_file>", file=sys.stderr)
        return 1

    project_dir = args[0]
    original = args[1]
    edited = args[2]

    if not os.path.isfile(original):
        print(f"Error: original file not found: {original}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(edited):
        print(f"Error: edited file not found: {edited}", file=sys.stderr)
        sys.exit(1)

    taste = read_taste()
    now = timestamp_now()

    with open(original) as f:
        orig_lines = f.readlines()
    with open(edited) as f:
        edited_lines = f.readlines()

    orig_text = "".join(orig_lines)
    edited_text = "".join(edited_lines)

    sm = difflib.SequenceMatcher(None, orig_lines, edited_lines)
    deleted = []
    added = []
    replacements = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "delete":
            deleted.extend(l.strip() for l in orig_lines[i1:i2] if l.strip())
        elif tag == "insert":
            added.extend(l.strip() for l in edited_lines[j1:j2] if l.strip())
        elif tag == "replace":
            old = [l.strip() for l in orig_lines[i1:i2] if l.strip()]
            new = [l.strip() for l in edited_lines[j1:j2] if l.strip()]
            replacements.append({"old": old, "new": new})

    insights = []

    # --- Tone changes ---
    orig_words = re.findall(r'\b\w+\b', orig_text.lower())
    edited_words = re.findall(r'\b\w+\b', edited_text.lower())
    formal_markers = {'furthermore', 'consequently', 'nevertheless', 'therefore', 'moreover', 'additionally', 'regarding', 'subsequently'}
    casual_markers = {'basically', 'actually', 'pretty', 'really', 'just', 'gonna', 'stuff', 'things', 'cool', 'awesome'}
    orig_formal = sum(1 for w in orig_words if w in formal_markers)
    edited_formal = sum(1 for w in edited_words if w in formal_markers)
    orig_casual = sum(1 for w in orig_words if w in casual_markers)
    edited_casual = sum(1 for w in edited_words if w in casual_markers)

    tone_shift = "neutral"
    if edited_formal > orig_formal + 1 and edited_casual <= orig_casual:
        tone_shift = "more_formal"
        insights.append("Tone: shifts toward more formal language")
    elif edited_casual > orig_casual + 1 and edited_formal <= orig_formal:
        tone_shift = "more_casual"
        insights.append("Tone: shifts toward more casual language")

    # --- Word replacements (line-level substitutions) ---
    word_replacements = []
    for r in replacements:
        old_text_r = " ".join(r["old"])
        new_text_r = " ".join(r["new"])
        if len(old_text_r) > len(new_text_r) * 1.3:
            insights.append("Prefers concise over verbose")
        elif len(new_text_r) > len(old_text_r) * 1.3:
            insights.append("Prefers detailed elaboration")
        # Extract word-level swaps
        ow = old_text_r.split()
        ew = new_text_r.split()
        wsm = difflib.SequenceMatcher(None, ow, ew)
        for wtag, wi1, wi2, wj1, wj2 in wsm.get_opcodes():
            if wtag == "replace" and (wi2 - wi1) <= 3 and (wj2 - wj1) <= 3:
                old_phrase = " ".join(ow[wi1:wi2])
                new_phrase = " ".join(ew[wj1:wj2])
                if old_phrase != new_phrase:
                    word_replacements.append({"from": old_phrase, "to": new_phrase})

    # --- Structure modifications ---
    orig_headings = [l.strip() for l in orig_lines if l.strip().startswith("#")]
    edited_headings = [l.strip() for l in edited_lines if l.strip().startswith("#")]
    structure_changes = []
    if orig_headings != edited_headings:
        common = set(orig_headings) & set(edited_headings)
        added_sections = [h for h in edited_headings if h not in orig_headings]
        removed_sections = [h for h in orig_headings if h not in edited_headings]
        orig_order = [h for h in orig_headings if h in common]
        edited_order = [h for h in edited_headings if h in common]
        reordered = orig_order != edited_order

        if added_sections:
            structure_changes.append({"type": "sections_added", "sections": added_sections[:10]})
            insights.append(f"Structure: added {len(added_sections)} section(s)")
        if removed_sections:
            structure_changes.append({"type": "sections_removed", "sections": removed_sections[:10]})
            insights.append(f"Structure: removed {len(removed_sections)} section(s)")
        if reordered:
            structure_changes.append({"type": "sections_reordered", "original_order": orig_order[:10], "edited_order": edited_order[:10]})
            insights.append("Structure: reordered sections")
    elif len(edited_headings) > len(orig_headings):
        insights.append("Prefers more section headings")
    elif len(edited_headings) < len(orig_headings):
        insights.append("Prefers fewer section headings")

    # --- Paragraph changes ---
    orig_paras = [p for p in orig_text.split("\n\n") if p.strip()]
    edited_paras = [p for p in edited_text.split("\n\n") if p.strip()]
    if len(edited_paras) > len(orig_paras) * 1.2:
        insights.append("Prefers shorter paragraphs")
    elif len(orig_paras) > len(edited_paras) * 1.2:
        insights.append("Prefers longer paragraphs")

    # --- Length changes ---
    orig_len = len(orig_text)
    edited_len = len(edited_text)
    length_ratio = edited_len / max(orig_len, 1)
    length_change = "expanded" if length_ratio > 1.15 else ("condensed" if length_ratio < 0.85 else "similar")

    # --- Code density ---
    orig_code_blocks = len(re.findall(r'```', orig_text))
    edited_code_blocks = len(re.findall(r'```', edited_text))
    code_change = "unchanged"
    if edited_code_blocks > orig_code_blocks + 1:
        code_change = "more_code"
        insights.append("Code density: added more code blocks")
    elif edited_code_blocks < orig_code_blocks - 1:
        code_change = "less_code"
        insights.append("Code density: removed code blocks")

    if deleted:
        insights.append(f"Removed {len(deleted)} lines (content to avoid)")
    if added:
        insights.append(f"Added {len(added)} lines (content to include)")

    # Deduplicate insights
    seen = set()
    unique_insights = []
    for ins in insights:
        if ins not in seen:
            seen.add(ins)
            unique_insights.append(ins)

    # Compute diff stats
    diff_lines = list(difflib.unified_diff(orig_lines, edited_lines, lineterm=""))
    additions = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    entry = {
        "timestamp": now,
        "project": project_dir,
        "tone_shift": tone_shift,
        "length_change": length_change,
        "length_ratio": round(length_ratio, 2),
        "paragraph_delta": len(edited_paras) - len(orig_paras),
        "code_density_change": code_change,
        "word_replacements": word_replacements[:20],
        "structure_changes": structure_changes,
        "insights": unique_insights,
        "diff_stats": {
            "additions": additions,
            "deletions": deletions,
            "replacements": len(replacements)
        }
    }

    taste.setdefault("learned_patterns", [])
    taste["learned_patterns"].append(entry)
    taste["learned_patterns"] = taste["learned_patterns"][-50:]
    taste["updated_at"] = now

    write_taste(taste)

    # Print summary
    stats = entry["diff_stats"]
    print(f"Learned from diff: +{stats['additions']} -{stats['deletions']} ~{stats['replacements']}")
    print(f"Tone: {entry['tone_shift']}, Length: {entry['length_change']} ({entry['length_ratio']}x), Code: {entry['code_density_change']}")
    if unique_insights:
        print(f"Insights ({len(unique_insights)}):")
        for ins in unique_insights:
            print(f"  - {ins}")
    else:
        print("No significant patterns detected.")
    print("Pattern stored in taste memory.")
    return 0


def cmd_feedback(args):
    if len(args) < 3 or not args[0] or not args[1] or not args[2]:
        print("ERROR: feedback requires <project_dir> <category> <text>", file=sys.stderr)
        return 1

    project_dir = args[0]
    category = args[1]
    text = args[2]

    if category not in VALID_FEEDBACK_CATEGORIES:
        print(f"Error: invalid category '{category}'. Must be one of: {' '.join(VALID_FEEDBACK_CATEGORIES)}", file=sys.stderr)
        sys.exit(1)

    taste = read_taste()
    now = timestamp_now()

    taste.setdefault("explicit_preferences", [])
    taste["explicit_preferences"].append({
        "timestamp": now,
        "project": project_dir,
        "category": category,
        "feedback": text
    })
    # Keep last 100 explicit preferences
    taste["explicit_preferences"] = taste["explicit_preferences"][-100:]
    taste["updated_at"] = now

    write_taste(taste)
    print(f"Feedback recorded: [{category}] {text}")
    return 0


def cmd_suggest(args):
    if not args or not args[0]:
        print("ERROR: suggest requires <project_dir>", file=sys.stderr)
        return 1

    project_dir = args[0]
    taste = read_taste()

    learned = taste.get("learned_patterns", [])
    explicit = taste.get("explicit_preferences", [])
    tone_prefs = taste.get("tone_preferences", [])
    structural_prefs = taste.get("structural_preferences", {})
    feedback_patterns = taste.get("feedback_patterns", [])

    if not learned and not explicit and not tone_prefs and not structural_prefs and not feedback_patterns:
        print("No taste data accumulated yet. Write some articles, use diff-learn, or provide feedback first.")
        return 0

    suggestions = []

    print("=== Personalized Writing Suggestions ===")
    print()

    # --- Tone suggestions ---
    tone_shifts = [p["tone_shift"] for p in learned if p.get("tone_shift") and p["tone_shift"] != "neutral"]
    tone_counter = collections.Counter(tone_shifts)
    if tone_counter:
        dominant_tone = tone_counter.most_common(1)[0]
        print(f'Tone: Your edits consistently shift toward {dominant_tone[0].replace("_", " ")} ({dominant_tone[1]} times).')
        if dominant_tone[0] == "more_casual":
            suggestions.append("Use conversational language, contractions, and direct address.")
        elif dominant_tone[0] == "more_formal":
            suggestions.append("Use precise terminology and structured argumentation.")

    # Explicit tone preferences
    tone_feedback = [e["feedback"] for e in explicit if e["category"] == "tone"]
    if tone_feedback:
        print(f"Tone preferences ({len(tone_feedback)} entries):")
        for tf in tone_feedback[-3:]:
            print(f"  - {tf}")

    if tone_prefs:
        print(f"Recorded tones: {', '.join(tone_prefs)}")

    # --- Length suggestions ---
    length_changes = [p["length_change"] for p in learned if p.get("length_change")]
    length_counter = collections.Counter(length_changes)
    if length_counter:
        dominant_length = length_counter.most_common(1)[0]
        if dominant_length[0] == "condensed":
            suggestions.append("Write more concisely. Your edits tend to cut content.")
            print(f"Length: You tend to condense drafts ({dominant_length[1]} times).")
        elif dominant_length[0] == "expanded":
            suggestions.append("Include more detail and examples. You tend to expand drafts.")
            print(f"Length: You tend to expand drafts ({dominant_length[1]} times).")

    # Explicit length preferences
    length_feedback = [e["feedback"] for e in explicit if e["category"] == "length"]
    if length_feedback:
        print("Length preferences:")
        for lf in length_feedback[-3:]:
            print(f"  - {lf}")

    # --- Structure suggestions ---
    structure_types = []
    for p in learned:
        for sc in p.get("structure_changes", []):
            structure_types.append(sc["type"])
    struct_counter = collections.Counter(structure_types)
    if struct_counter:
        print("Structure patterns:")
        for stype, count in struct_counter.most_common(5):
            readable = stype.replace("_", " ")
            print(f"  - {readable}: {count} times")

    struct_feedback = [e["feedback"] for e in explicit if e["category"] == "structure"]
    if struct_feedback:
        print("Structure preferences:")
        for sf in struct_feedback[-3:]:
            print(f"  - {sf}")

    if structural_prefs:
        print("Structural settings:")
        for k, v in structural_prefs.items():
            print(f"  {k}: {v}")

    # --- Vocabulary suggestions ---
    replacement_pairs = collections.Counter()
    for p in learned:
        for r in p.get("word_replacements", []):
            replacement_pairs[(r["from"], r["to"])] += 1
    if replacement_pairs:
        print("Common replacements:")
        for (old, new), count in replacement_pairs.most_common(5):
            print(f'  "{old}" -> "{new}" ({count}x)')

    vocab_feedback = [e["feedback"] for e in explicit if e["category"] == "vocabulary"]
    if vocab_feedback:
        print("Vocabulary preferences:")
        for vf in vocab_feedback[-3:]:
            print(f"  - {vf}")

    # --- Code density suggestions ---
    code_changes = [p["code_density_change"] for p in learned if p.get("code_density_change") and p["code_density_change"] != "unchanged"]
    code_counter = collections.Counter(code_changes)
    if code_counter:
        dominant_code = code_counter.most_common(1)[0]
        if dominant_code[0] == "more_code":
            suggestions.append("Include more code examples.")
            print(f"Code density: You tend to add more code examples ({dominant_code[1]} times).")
        elif dominant_code[0] == "less_code":
            suggestions.append("Reduce code examples; focus on explanation.")
            print(f"Code density: You tend to remove code examples ({dominant_code[1]} times).")

    code_feedback = [e["feedback"] for e in explicit if e["category"] == "code_density"]
    if code_feedback:
        print("Code density preferences:")
        for cf in code_feedback[-3:]:
            print(f"  - {cf}")

    # --- Format suggestions ---
    format_feedback = [e["feedback"] for e in explicit if e["category"] == "format"]
    if format_feedback:
        print("Format preferences:")
        for ff in format_feedback[-3:]:
            print(f"  - {ff}")

    # --- Learned insights summary ---
    all_insights = []
    for p in learned:
        all_insights.extend(p.get("insights", []))
    if all_insights:
        insight_counter = collections.Counter(all_insights)
        print("Recurring insights:")
        for ins, count in insight_counter.most_common(5):
            print(f"  - {ins} ({count}x)")

    # --- Aggregated action items ---
    if suggestions:
        print()
        print("=== Action Items for Next Draft ===")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")

    # --- Legacy feedback patterns ---
    if feedback_patterns:
        print()
        print("Legacy feedback:")
        for fp in feedback_patterns[-3:]:
            print(f"  - {fp}")

    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "read": lambda: cmd_read(),
        "update": lambda: cmd_update(rest),
        "record-choice": lambda: cmd_record_choice(rest),
        "get-preference": lambda: cmd_get_preference(rest),
        "history": lambda: cmd_history(),
        "diff-learn": lambda: cmd_diff_learn(rest),
        "feedback": lambda: cmd_feedback(rest),
        "suggest": lambda: cmd_suggest(rest),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
