#!/usr/bin/env bash
# Taste memory — persist writing style preferences across sessions
# Inspired by gstack's design taste memory system
set -euo pipefail

TASTE_DIR="$HOME/.tech-essay-writer"

usage() {
  cat <<'EOF'
Usage: taste-memory.sh <command> [args...]

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
  suggest <project_dir>         Output personalized writing suggestions from accumulated taste data
EOF
}

ensure_dir() {
  mkdir -p "$TASTE_DIR"
}

taste_file() {
  echo "$TASTE_DIR/taste-memory.json"
}

read_taste() {
  local tf
  tf="$(taste_file)"
  if [ -f "$tf" ]; then
    cat "$tf"
  else
    echo '{}'
  fi
}

write_taste() {
  local json_str="$1"
  local tf
  tf="$(taste_file)"
  local tmp="${tf}.tmp.$$"
  ensure_dir
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$tf"
}

cmd_read() {
  local taste
  taste=$(read_taste)
  if [ "$taste" = "{}" ]; then
    echo "No taste memory yet. Will be populated after first article."
  else
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print('=== Writing Style Preferences ===')
if 'preferred_variant' in d:
    print(f\"Preferred style: {d['preferred_variant']}\")
if 'tone_preferences' in d:
    print(f\"Tone: {', '.join(d['tone_preferences'])}\")
if 'structural_preferences' in d:
    for k, v in d['structural_preferences'].items():
        print(f\"  {k}: {v}\")
if 'topics_written' in d:
    print(f\"Topics covered: {len(d['topics_written'])}\")
    for t in d['topics_written'][-5:]:
        print(f\"  - {t['topic']} ({t['date']})\")
if 'feedback_patterns' in d:
    print('Feedback patterns:')
    for p in d['feedback_patterns'][-5:]:
        print(f\"  - {p}\")
if 'learned_patterns' in d and d['learned_patterns']:
    print(f\"Learned patterns: {len(d['learned_patterns'])}\")
    for lp in d['learned_patterns'][-5:]:
        proj = lp.get('project', '?')
        print(f\"  [{lp.get('timestamp','?')[:10]}] project: {proj}\")
        for ins in lp.get('insights', []):
            print(f\"    - {ins}\")
if 'explicit_preferences' in d and d['explicit_preferences']:
    print('Explicit preferences:')
    cats = {}
    for fb in d['explicit_preferences']:
        cats.setdefault(fb['category'], []).append(fb['feedback'])
    for cat, items in cats.items():
        print(f\"  [{cat}]\")
        for item in items[-3:]:
            print(f\"    - {item}\")
" "$taste"
  fi
}

cmd_update() {
  local project_dir="$1" taste_file_path="${2:-}"
  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Read pipeline state if it exists
  local state='{}'
  if [ -f "$project_dir/.essay-state/pipeline-state.json" ]; then
    state=$(cat "$project_dir/.essay-state/pipeline-state.json")
  fi

  taste=$(python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
state = json.loads(sys.argv[2])
now = sys.argv[3]

# Initialize structure if needed
taste.setdefault('preferred_variant', None)
taste.setdefault('tone_preferences', [])
taste.setdefault('structural_preferences', {})
taste.setdefault('topics_written', [])
taste.setdefault('feedback_patterns', [])
taste.setdefault('articles_count', 0)
taste.setdefault('updated_at', now)

# Update from pipeline state
topic = state.get('topic', 'unknown')
variant = state.get('outline_variant')

# Track topics
taste['topics_written'].append({
    'topic': topic,
    'date': now,
    'variant': variant,
    'refinement_rounds': state.get('refinement_round', 0)
})

# Update variant preference (most recent wins, but track frequency)
if variant:
    taste['preferred_variant'] = variant

taste['articles_count'] += 1
taste['updated_at'] = now

# Keep last 50 topics max
taste['topics_written'] = taste['topics_written'][-50:]

print(json.dumps(taste))
" "$taste" "$state" "$now")

  write_taste "$taste"
  echo "Taste memory updated."
}

cmd_record_choice() {
  local key="$1" value="$2"
  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  taste=$(python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3]
now = sys.argv[4]

if key == 'tone':
    taste.setdefault('tone_preferences', [])
    if val not in taste['tone_preferences']:
        taste['tone_preferences'].append(val)
elif key == 'feedback':
    taste.setdefault('feedback_patterns', [])
    taste['feedback_patterns'].append(val)
    taste['feedback_patterns'] = taste['feedback_patterns'][-20:]
else:
    taste.setdefault('structural_preferences', {})
    taste['structural_preferences'][key] = val

taste['updated_at'] = now
print(json.dumps(taste))
" "$taste" "$key" "$value" "$now")

  write_taste "$taste"
}

cmd_get_preference() {
  local key="$1"
  local taste
  taste=$(read_taste)
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
key = sys.argv[2]
if key == 'tone':
    print(json.dumps(taste.get('tone_preferences', [])))
elif key == 'feedback':
    print(json.dumps(taste.get('feedback_patterns', [])))
elif key == 'variant':
    print(taste.get('preferred_variant', ''))
else:
    prefs = taste.get('structural_preferences', {})
    print(prefs.get(key, ''))
" "$taste" "$key"
}

cmd_history() {
  local taste
  taste=$(read_taste)
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
topics = taste.get('topics_written', [])
if not topics:
    print('No articles written yet.')
else:
    print(f'Articles written: {len(topics)}')
    for t in topics:
        print(f\"  [{t.get('date','?')[:10]}] {t.get('topic','?')} (variant: {t.get('variant','?')})\")
" "$taste"
}

cmd_diff_learn() {
  local project_dir="$1" original="$2" edited="$3"

  if [ ! -f "$original" ]; then
    echo "Error: original file not found: $original" >&2
    exit 1
  fi
  if [ ! -f "$edited" ]; then
    echo "Error: edited file not found: $edited" >&2
    exit 1
  fi

  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  taste=$(python3 -c "
import json, sys, difflib, os

taste = json.loads(sys.argv[1])
orig_path = sys.argv[2]
edited_path = sys.argv[3]
now = sys.argv[4]
project_dir = sys.argv[5]

with open(orig_path) as f:
    orig_lines = f.readlines()
with open(edited_path) as f:
    edited_lines = f.readlines()

orig_text = ''.join(orig_lines)
edited_text = ''.join(edited_lines)

sm = difflib.SequenceMatcher(None, orig_lines, edited_lines)
deleted = []
added = []
replacements = []

for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'delete':
        deleted.extend(l.strip() for l in orig_lines[i1:i2] if l.strip())
    elif tag == 'insert':
        added.extend(l.strip() for l in edited_lines[j1:j2] if l.strip())
    elif tag == 'replace':
        old = [l.strip() for l in orig_lines[i1:i2] if l.strip()]
        new = [l.strip() for l in edited_lines[j1:j2] if l.strip()]
        replacements.append({'old': old, 'new': new})

insights = []

# --- Tone changes ---
# Check formality shift via marker words
import re
orig_words = re.findall(r'\b\w+\b', orig_text.lower())
edited_words = re.findall(r'\b\w+\b', edited_text.lower())
formal_markers = {'furthermore', 'consequently', 'nevertheless', 'therefore', 'moreover', 'additionally', 'regarding', 'subsequently'}
casual_markers = {'basically', 'actually', 'pretty', 'really', 'just', 'gonna', 'stuff', 'things', 'cool', 'awesome'}
orig_formal = sum(1 for w in orig_words if w in formal_markers)
edited_formal = sum(1 for w in edited_words if w in formal_markers)
orig_casual = sum(1 for w in orig_words if w in casual_markers)
edited_casual = sum(1 for w in edited_words if w in casual_markers)

tone_shift = 'neutral'
if edited_formal > orig_formal + 1 and edited_casual <= orig_casual:
    tone_shift = 'more_formal'
    insights.append('Tone: shifts toward more formal language')
elif edited_casual > orig_casual + 1 and edited_formal <= orig_formal:
    tone_shift = 'more_casual'
    insights.append('Tone: shifts toward more casual language')

# --- Word replacements (line-level substitutions) ---
word_replacements = []
for r in replacements:
    old_text_r = ' '.join(r['old'])
    new_text_r = ' '.join(r['new'])
    if len(old_text_r) > len(new_text_r) * 1.3:
        insights.append('Prefers concise over verbose')
    elif len(new_text_r) > len(old_text_r) * 1.3:
        insights.append('Prefers detailed elaboration')
    # Extract word-level swaps
    ow = old_text_r.split()
    ew = new_text_r.split()
    wsm = difflib.SequenceMatcher(None, ow, ew)
    for wtag, wi1, wi2, wj1, wj2 in wsm.get_opcodes():
        if wtag == 'replace' and (wi2 - wi1) <= 3 and (wj2 - wj1) <= 3:
            old_phrase = ' '.join(ow[wi1:wi2])
            new_phrase = ' '.join(ew[wj1:wj2])
            if old_phrase != new_phrase:
                word_replacements.append({'from': old_phrase, 'to': new_phrase})

# --- Structure modifications ---
orig_headings = [l.strip() for l in orig_lines if l.strip().startswith('#')]
edited_headings = [l.strip() for l in edited_lines if l.strip().startswith('#')]
structure_changes = []
if orig_headings != edited_headings:
    common = set(orig_headings) & set(edited_headings)
    added_sections = [h for h in edited_headings if h not in orig_headings]
    removed_sections = [h for h in orig_headings if h not in edited_headings]
    orig_order = [h for h in orig_headings if h in common]
    edited_order = [h for h in edited_headings if h in common]
    reordered = orig_order != edited_order

    if added_sections:
        structure_changes.append({'type': 'sections_added', 'sections': added_sections[:10]})
        insights.append(f'Structure: added {len(added_sections)} section(s)')
    if removed_sections:
        structure_changes.append({'type': 'sections_removed', 'sections': removed_sections[:10]})
        insights.append(f'Structure: removed {len(removed_sections)} section(s)')
    if reordered:
        structure_changes.append({'type': 'sections_reordered', 'original_order': orig_order[:10], 'edited_order': edited_order[:10]})
        insights.append('Structure: reordered sections')
elif len(edited_headings) > len(orig_headings):
    insights.append('Prefers more section headings')
elif len(edited_headings) < len(orig_headings):
    insights.append('Prefers fewer section headings')

# --- Paragraph changes ---
orig_paras = [p for p in orig_text.split('\n\n') if p.strip()]
edited_paras = [p for p in edited_text.split('\n\n') if p.strip()]
if len(edited_paras) > len(orig_paras) * 1.2:
    insights.append('Prefers shorter paragraphs')
elif len(orig_paras) > len(edited_paras) * 1.2:
    insights.append('Prefers longer paragraphs')

# --- Length changes ---
orig_len = len(orig_text)
edited_len = len(edited_text)
length_ratio = edited_len / max(orig_len, 1)
length_change = 'expanded' if length_ratio > 1.15 else ('condensed' if length_ratio < 0.85 else 'similar')

# --- Code density ---
import re as re2
orig_code_blocks = len(re2.findall(r'\x60\x60\x60', orig_text))
edited_code_blocks = len(re2.findall(r'\x60\x60\x60', edited_text))
code_change = 'unchanged'
if edited_code_blocks > orig_code_blocks + 1:
    code_change = 'more_code'
    insights.append('Code density: added more code blocks')
elif edited_code_blocks < orig_code_blocks - 1:
    code_change = 'less_code'
    insights.append('Code density: removed code blocks')

if deleted:
    insights.append(f'Removed {len(deleted)} lines (content to avoid)')
if added:
    insights.append(f'Added {len(added)} lines (content to include)')

# Deduplicate insights
seen = set()
unique_insights = []
for ins in insights:
    if ins not in seen:
        seen.add(ins)
        unique_insights.append(ins)

# Compute diff stats
diff_lines = list(difflib.unified_diff(orig_lines, edited_lines, lineterm=''))
additions = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
deletions = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))

entry = {
    'timestamp': now,
    'project': project_dir,
    'tone_shift': tone_shift,
    'length_change': length_change,
    'length_ratio': round(length_ratio, 2),
    'paragraph_delta': len(edited_paras) - len(orig_paras),
    'code_density_change': code_change,
    'word_replacements': word_replacements[:20],
    'structure_changes': structure_changes,
    'insights': unique_insights,
    'diff_stats': {
        'additions': additions,
        'deletions': deletions,
        'replacements': len(replacements)
    }
}

taste.setdefault('learned_patterns', [])
taste['learned_patterns'].append(entry)
taste['learned_patterns'] = taste['learned_patterns'][-50:]
taste['updated_at'] = now

print(json.dumps(taste))
" "$taste" "$original" "$edited" "$now" "$project_dir")

  write_taste "$taste"

  # Print summary
  python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
entry = taste.get('learned_patterns', [])[-1]
stats = entry['diff_stats']
print(f\"Learned from diff: +{stats['additions']} -{stats['deletions']} ~{stats['replacements']}\")
print(f\"Tone: {entry['tone_shift']}, Length: {entry['length_change']} ({entry['length_ratio']}x), Code: {entry['code_density_change']}\")
insights = entry.get('insights', [])
if insights:
    print(f'Insights ({len(insights)}):')
    for ins in insights:
        print(f'  - {ins}')
else:
    print('No significant patterns detected.')
print('Pattern stored in taste memory.')
" "$taste"
}

VALID_FEEDBACK_CATEGORIES="tone structure vocabulary length code_density format"

cmd_feedback() {
  local project_dir="$1" category="$2" text="$3"

  # Validate category
  local valid=false
  for cat in $VALID_FEEDBACK_CATEGORIES; do
    if [ "$cat" = "$category" ]; then
      valid=true
      break
    fi
  done
  if [ "$valid" = "false" ]; then
    echo "Error: invalid category '$category'. Must be one of: $VALID_FEEDBACK_CATEGORIES" >&2
    exit 1
  fi

  local taste
  taste=$(read_taste)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  taste=$(python3 -c "
import json, sys
taste = json.loads(sys.argv[1])
category = sys.argv[2]
text = sys.argv[3]
now = sys.argv[4]
project_dir = sys.argv[5]

taste.setdefault('explicit_preferences', [])

entry = {
    'timestamp': now,
    'project': project_dir,
    'category': category,
    'feedback': text
}

taste['explicit_preferences'].append(entry)
# Keep last 100 explicit preferences
taste['explicit_preferences'] = taste['explicit_preferences'][-100:]
taste['updated_at'] = now

print(json.dumps(taste))
" "$taste" "$category" "$text" "$now" "$project_dir")

  write_taste "$taste"
  echo "Feedback recorded: [$category] $text"
}

cmd_suggest() {
  local project_dir="$1"
  local taste
  taste=$(read_taste)

  python3 -c "
import json, sys, collections

taste = json.loads(sys.argv[1])
project_dir = sys.argv[2]

learned = taste.get('learned_patterns', [])
explicit = taste.get('explicit_preferences', [])
tone_prefs = taste.get('tone_preferences', [])
structural_prefs = taste.get('structural_preferences', {})
feedback_patterns = taste.get('feedback_patterns', [])

if not learned and not explicit and not tone_prefs and not structural_prefs and not feedback_patterns:
    print('No taste data accumulated yet. Write some articles, use diff-learn, or provide feedback first.')
    sys.exit(0)

suggestions = []

print('=== Personalized Writing Suggestions ===')
print()

# --- Tone suggestions ---
tone_shifts = [p['tone_shift'] for p in learned if p.get('tone_shift') and p['tone_shift'] != 'neutral']
tone_counter = collections.Counter(tone_shifts)
if tone_counter:
    dominant_tone = tone_counter.most_common(1)[0]
    print(f'Tone: Your edits consistently shift toward {dominant_tone[0].replace(\"_\", \" \")} ({dominant_tone[1]} times).')
    if dominant_tone[0] == 'more_casual':
        suggestions.append('Use conversational language, contractions, and direct address.')
    elif dominant_tone[0] == 'more_formal':
        suggestions.append('Use precise terminology and structured argumentation.')

# Explicit tone preferences
tone_feedback = [e['feedback'] for e in explicit if e['category'] == 'tone']
if tone_feedback:
    print(f'Tone preferences ({len(tone_feedback)} entries):')
    for tf in tone_feedback[-3:]:
        print(f'  - {tf}')

if tone_prefs:
    print(f'Recorded tones: {\", \".join(tone_prefs)}')

# --- Length suggestions ---
length_changes = [p['length_change'] for p in learned if p.get('length_change')]
length_counter = collections.Counter(length_changes)
if length_counter:
    dominant_length = length_counter.most_common(1)[0]
    if dominant_length[0] == 'condensed':
        suggestions.append('Write more concisely. Your edits tend to cut content.')
        print(f'Length: You tend to condense drafts ({dominant_length[1]} times).')
    elif dominant_length[0] == 'expanded':
        suggestions.append('Include more detail and examples. You tend to expand drafts.')
        print(f'Length: You tend to expand drafts ({dominant_length[1]} times).')

# Explicit length preferences
length_feedback = [e['feedback'] for e in explicit if e['category'] == 'length']
if length_feedback:
    print(f'Length preferences:')
    for lf in length_feedback[-3:]:
        print(f'  - {lf}')

# --- Structure suggestions ---
structure_types = []
for p in learned:
    for sc in p.get('structure_changes', []):
        structure_types.append(sc['type'])
struct_counter = collections.Counter(structure_types)
if struct_counter:
    print(f'Structure patterns:')
    for stype, count in struct_counter.most_common(5):
        readable = stype.replace('_', ' ')
        print(f'  - {readable}: {count} times')

struct_feedback = [e['feedback'] for e in explicit if e['category'] == 'structure']
if struct_feedback:
    print(f'Structure preferences:')
    for sf in struct_feedback[-3:]:
        print(f'  - {sf}')

if structural_prefs:
    print('Structural settings:')
    for k, v in structural_prefs.items():
        print(f'  {k}: {v}')

# --- Vocabulary suggestions ---
# Aggregate word replacements across all learned patterns
replacement_pairs = collections.Counter()
for p in learned:
    for r in p.get('word_replacements', []):
        replacement_pairs[(r['from'], r['to'])] += 1
if replacement_pairs:
    print(f'Common replacements:')
    for (old, new), count in replacement_pairs.most_common(5):
        print(f'  \"{old}\" -> \"{new}\" ({count}x)')

vocab_feedback = [e['feedback'] for e in explicit if e['category'] == 'vocabulary']
if vocab_feedback:
    print(f'Vocabulary preferences:')
    for vf in vocab_feedback[-3:]:
        print(f'  - {vf}')

# --- Code density suggestions ---
code_changes = [p['code_density_change'] for p in learned if p.get('code_density_change') and p['code_density_change'] != 'unchanged']
code_counter = collections.Counter(code_changes)
if code_counter:
    dominant_code = code_counter.most_common(1)[0]
    if dominant_code[0] == 'more_code':
        suggestions.append('Include more code examples.')
        print(f'Code density: You tend to add more code examples ({dominant_code[1]} times).')
    elif dominant_code[0] == 'less_code':
        suggestions.append('Reduce code examples; focus on explanation.')
        print(f'Code density: You tend to remove code examples ({dominant_code[1]} times).')

code_feedback = [e['feedback'] for e in explicit if e['category'] == 'code_density']
if code_feedback:
    print(f'Code density preferences:')
    for cf in code_feedback[-3:]:
        print(f'  - {cf}')

# --- Format suggestions ---
format_feedback = [e['feedback'] for e in explicit if e['category'] == 'format']
if format_feedback:
    print(f'Format preferences:')
    for ff in format_feedback[-3:]:
        print(f'  - {ff}')

# --- Learned insights summary ---
all_insights = []
for p in learned:
    all_insights.extend(p.get('insights', []))
if all_insights:
    insight_counter = collections.Counter(all_insights)
    print(f'Recurring insights:')
    for ins, count in insight_counter.most_common(5):
        print(f'  - {ins} ({count}x)')

# --- Aggregated action items ---
if suggestions:
    print()
    print('=== Action Items for Next Draft ===')
    for i, s in enumerate(suggestions, 1):
        print(f'  {i}. {s}')

# --- Legacy feedback patterns ---
if feedback_patterns:
    print()
    print('Legacy feedback:')
    for fp in feedback_patterns[-3:]:
        print(f'  - {fp}')
" "$taste" "$project_dir"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  read) cmd_read ;;
  update) cmd_update "$@" ;;
  record-choice) cmd_record_choice "$@" ;;
  get-preference) cmd_get_preference "$@" ;;
  history) cmd_history ;;
  diff-learn) cmd_diff_learn "$@" ;;
  feedback) cmd_feedback "$@" ;;
  suggest) cmd_suggest "$@" ;;
  *) usage; exit 1 ;;
esac
