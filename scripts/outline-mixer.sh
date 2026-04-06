#!/usr/bin/env bash
# Outline Mixer — cherry-pick sections from different outline variants
# Usage: bash scripts/outline-mixer.sh <project_dir> <sections_spec>
#   mix:   bash scripts/outline-mixer.sh ./proj "A:1,2 B:3,4 C:5"
#   list:  bash scripts/outline-mixer.sh ./proj list
#
# sections_spec format: "VARIANT:SECTION[,SECTION...] ..."
#   Takes sections 1,2 from outline A, sections 3,4 from outline B, section 5 from outline C
#   Section numbers are 1-based (matching display in "list" output)
#
# Output: .essay-state/outline-mixed.json
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: outline-mixer.sh <project_dir> <sections_spec|list>

Commands:
  mix     outline-mixer.sh <project_dir> "A:1,2 B:3,4 C:5"
          Cherry-pick sections from different outline variants and assemble
          a mixed outline. Writes to .essay-state/outline-mixed.json

  list    outline-mixer.sh <project_dir> list
          Show all sections from all available outline variants side-by-side

sections_spec format:
  VARIANT:SECTIONS [VARIANT:SECTIONS ...]
  VARIANT = A, B, or C
  SECTIONS = comma-separated 1-based section numbers

Examples:
  outline-mixer.sh ./proj "A:1,2 B:3,4 C:5"
  outline-mixer.sh ./proj "B:1,2,3 A:4,5"
  outline-mixer.sh ./proj list
EOF
}

# ── Argument validation ────────────────────────────────────────────────────────

if [ $# -lt 2 ]; then
  usage
  exit 1
fi

PROJECT_DIR="${1:?project_dir required}"
SPEC_OR_CMD="${2}"

STATE_DIR="$PROJECT_DIR/.essay-state"

# ── Helpers ────────────────────────────────────────────────────────────────────

read_outline() {
  local variant="$1"
  local path="$STATE_DIR/outline-${variant}.json"
  if [ -f "$path" ]; then
    cat "$path"
  else
    echo ""
  fi
}

# Count how many outline variants exist
count_available_outlines() {
  local count=0
  for v in A B C; do
    if [ -f "$STATE_DIR/outline-${v}.json" ]; then
      count=$((count + 1))
    fi
  done
  echo "$count"
}

# ── List command ───────────────────────────────────────────────────────────────

cmd_list() {
  local found=0
  for v in A B C; do
    local outline
    outline=$(read_outline "$v")
    if [ -z "$outline" ]; then
      continue
    fi
    found=$((found + 1))

    python3 -c "
import json, sys

data = json.loads(sys.argv[1])
variant = sys.argv[2]

variant_name = data.get('variant_name', variant)
title = data.get('title', '(no title)')
tone = data.get('tone', '(no tone)')
target_words = data.get('target_word_count', '?')
sections = data.get('sections', [])

print(f'=== Outline {variant} — {variant_name} ===')
print(f'  Title: {title}')
print(f'  Tone:  {tone}')
print(f'  Target words: {target_words}')
print(f'  Sections ({len(sections)}):')
for i, sec in enumerate(sections, 1):
    title_s = sec.get('title', '(untitled)')
    purpose = sec.get('purpose', '')
    words = sec.get('estimated_words', '?')
    kp = sec.get('key_points', [])
    kp_str = ', '.join(kp) if kp else ''
    print(f'    {i}. {title_s}')
    print(f'       Purpose: {purpose} | ~{words} words')
    if kp_str:
        print(f'       Key points: {kp_str}')
print()
" "$outline" "$v"
  done

  if [ "$found" -eq 0 ]; then
    echo "ERROR: No outline variants found in $STATE_DIR" >&2
    echo "Run the outline generation stage first." >&2
    return 1
  fi

  echo "Total variants available: $found"
  echo "Usage: outline-mixer.sh <project_dir> \"A:1,2 B:3,4 C:5\""
}

# ── Mix command ────────────────────────────────────────────────────────────────

cmd_mix() {
  local spec="$1"

  # Validate project dir has .essay-state
  if [ ! -d "$STATE_DIR" ]; then
    echo "ERROR: State directory not found: $STATE_DIR" >&2
    echo "Make sure you've run the pipeline to generate outlines first." >&2
    return 1
  fi

  # Check at least one outline exists
  local avail
  avail=$(count_available_outlines)
  if [ "$avail" -eq 0 ]; then
    echo "ERROR: No outline variants found in $STATE_DIR" >&2
    echo "Run the outline generation stage first." >&2
    return 1
  fi

  # Parse and validate the spec, assemble the mixed outline
  python3 -c "
import json, sys, os, re

spec = sys.argv[1]
state_dir = sys.argv[2]

# Parse spec: 'A:1,2 B:3,4 C:5'
tokens = spec.strip().split()
if not tokens:
    print('ERROR: Empty sections spec', file=sys.stderr)
    sys.exit(1)

# Load all outlines
outlines = {}
for v in ['A', 'B', 'C']:
    path = os.path.join(state_dir, f'outline-{v}.json')
    if os.path.exists(path):
        with open(path) as f:
            outlines[v] = json.load(f)

# Parse each token
parsed = []
seen_sections = set()  # track (variant, section_num) for duplicate detection
errors = []

for token in tokens:
    # Validate format: LETTER:NUMBERS
    match = re.match(r'^([A-Ca-c]):(.+)$', token)
    if not match:
        errors.append(f'Invalid spec token: \"{token}\". Expected format like A:1,2')
        continue

    variant = match.group(1).upper()
    section_nums_str = match.group(2)

    # Check variant exists
    if variant not in outlines:
        errors.append(f'Outline variant {variant} not found (outline-{variant}.json missing)')
        continue

    sections = outlines[variant].get('sections', [])
    total_sections = len(sections)

    # Parse section numbers
    for num_str in section_nums_str.split(','):
        num_str = num_str.strip()
        if not num_str:
            continue
        try:
            num = int(num_str)
        except ValueError:
            errors.append(f'Invalid section number \"{num_str}\" in {token}')
            continue

        if num < 1 or num > total_sections:
            errors.append(f'Section {num} out of range for outline {variant} (has {total_sections} sections)')
            continue

        key = (variant, num)
        if key in seen_sections:
            errors.append(f'Duplicate section reference: {variant}:{num}')
            continue
        seen_sections.add(key)

        # 1-based to 0-based
        parsed.append({
            'variant': variant,
            'section_index': num - 1,
            'section_num': num,
            'section': sections[num - 1]
        })

if errors:
    for e in errors:
        print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)

if not parsed:
    print('ERROR: No valid sections found in spec', file=sys.stderr)
    sys.exit(1)

# Assemble the mixed outline
mixed_sections = []
source_map = []
total_words = 0

for entry in parsed:
    sec = entry['section']
    mixed_sections.append(sec)
    source_map.append({
        'variant': entry['variant'],
        'original_section': entry['section_num'],
        'title': sec.get('title', '(untitled)')
    })
    total_words += sec.get('estimated_words', 0)

# Build the mixed outline JSON
mixed = {
    'variant': 'mixed',
    'variant_name': 'Mixed (cherry-picked)',
    'title': '(mixed — update title after review)',
    'hook': '(mixed — update hook after review)',
    'sections': mixed_sections,
    'target_word_count': total_words,
    'tone': '(mixed — update tone after review)',
    'source_map': source_map,
    'mix_spec': spec
}

# Write output
out_path = os.path.join(state_dir, 'outline-mixed.json')
with open(out_path, 'w') as f:
    json.dump(mixed, f, indent=2)

# Print summary
print('Mixed outline assembled successfully!')
print(f'Output: {out_path}')
print(f'Sections: {len(mixed_sections)}')
print(f'Estimated words: {total_words}')
print()
print('Section mapping:')
for i, sm in enumerate(source_map, 1):
    print(f'  {i}. [{sm[\"variant\"]}:{sm[\"original_section\"]}] {sm[\"title\"]}')
print()
print('NOTE: Update title, hook, and tone in the mixed outline before proceeding.')
" "$spec" "$STATE_DIR"
}

# ── Main dispatch ──────────────────────────────────────────────────────────────

case "$SPEC_OR_CMD" in
  list)
    cmd_list
    ;;
  -h|--help|help)
    usage
    ;;
  "")
    echo "ERROR: sections_spec or command required" >&2
    usage
    exit 1
    ;;
  *)
    cmd_mix "$SPEC_OR_CMD"
    ;;
esac
