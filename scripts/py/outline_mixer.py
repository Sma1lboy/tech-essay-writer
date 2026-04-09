#!/usr/bin/env python3
"""Outline Mixer — cherry-pick sections from different outline variants.
Usage: outline_mixer.py <project_dir> <sections_spec|list>

Commands:
  mix     outline_mixer.py <project_dir> "A:1,2 B:3,4 C:5"
  list    outline_mixer.py <project_dir> list

sections_spec format:
  VARIANT:SECTIONS [VARIANT:SECTIONS ...]
  VARIANT = A, B, or C
  SECTIONS = comma-separated 1-based section numbers
"""

import json
import os
import re
import sys

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: outline_mixer.py <project_dir> <sections_spec|list>

Commands:
  mix     outline_mixer.py <project_dir> "A:1,2 B:3,4 C:5"
          Cherry-pick sections from different outline variants and assemble
          a mixed outline. Writes to .essay-state/outline-mixed.json

  list    outline_mixer.py <project_dir> list
          Show all sections from all available outline variants side-by-side

sections_spec format:
  VARIANT:SECTIONS [VARIANT:SECTIONS ...]
  VARIANT = A, B, or C
  SECTIONS = comma-separated 1-based section numbers

Examples:
  outline_mixer.py ./proj "A:1,2 B:3,4 C:5"
  outline_mixer.py ./proj "B:1,2,3 A:4,5"
  outline_mixer.py ./proj list""")


def cmd_list(state_dir):
    """Show all sections from all available outline variants."""
    found = 0
    for v in ["A", "B", "C"]:
        path = os.path.join(state_dir, f"outline-{v}.json")
        data = read_json_file(path)
        if not data:
            continue
        found += 1

        variant_name = data.get("variant_name", v)
        title = data.get("title", "(no title)")
        tone = data.get("tone", "(no tone)")
        target_words = data.get("target_word_count", "?")
        sections = data.get("sections", [])

        print(f"=== Outline {v} — {variant_name} ===")
        print(f"  Title: {title}")
        print(f"  Tone:  {tone}")
        print(f"  Target words: {target_words}")
        print(f"  Sections ({len(sections)}):")
        for i, sec in enumerate(sections, 1):
            title_s = sec.get("title", "(untitled)")
            purpose = sec.get("purpose", "")
            words = sec.get("estimated_words", "?")
            kp = sec.get("key_points", [])
            kp_str = ", ".join(kp) if kp else ""
            print(f"    {i}. {title_s}")
            print(f"       Purpose: {purpose} | ~{words} words")
            if kp_str:
                print(f"       Key points: {kp_str}")
        print()

    if found == 0:
        print("ERROR: No outline variants found in " + state_dir, file=sys.stderr)
        print("Run the outline generation stage first.", file=sys.stderr)
        sys.exit(1)

    print(f"Total variants available: {found}")
    print('Usage: outline_mixer.py <project_dir> "A:1,2 B:3,4 C:5"')


def cmd_mix(state_dir, spec):
    """Parse spec and assemble a mixed outline."""
    if not os.path.isdir(state_dir):
        print(f"ERROR: State directory not found: {state_dir}", file=sys.stderr)
        print("Make sure you've run the pipeline to generate outlines first.", file=sys.stderr)
        sys.exit(1)

    # Check at least one outline exists
    avail = sum(1 for v in ["A", "B", "C"] if os.path.isfile(os.path.join(state_dir, f"outline-{v}.json")))
    if avail == 0:
        print("ERROR: No outline variants found in " + state_dir, file=sys.stderr)
        print("Run the outline generation stage first.", file=sys.stderr)
        sys.exit(1)

    # Parse spec: 'A:1,2 B:3,4 C:5'
    tokens = spec.strip().split()
    if not tokens:
        print("ERROR: Empty sections spec", file=sys.stderr)
        sys.exit(1)

    # Load all outlines
    outlines = {}
    for v in ["A", "B", "C"]:
        path = os.path.join(state_dir, f"outline-{v}.json")
        data = read_json_file(path)
        if data:
            outlines[v] = data

    # Parse each token
    parsed = []
    seen_sections = set()
    errors = []

    for token in tokens:
        match = re.match(r'^([A-Ca-c]):(.+)$', token)
        if not match:
            errors.append(f'Invalid spec token: "{token}". Expected format like A:1,2')
            continue

        variant = match.group(1).upper()
        section_nums_str = match.group(2)

        if variant not in outlines:
            errors.append(f"Outline variant {variant} not found (outline-{variant}.json missing)")
            continue

        sections = outlines[variant].get("sections", [])
        total_sections = len(sections)

        for num_str in section_nums_str.split(","):
            num_str = num_str.strip()
            if not num_str:
                continue
            try:
                num = int(num_str)
            except ValueError:
                errors.append(f'Invalid section number "{num_str}" in {token}')
                continue

            if num < 1 or num > total_sections:
                errors.append(f"Section {num} out of range for outline {variant} (has {total_sections} sections)")
                continue

            key = (variant, num)
            if key in seen_sections:
                errors.append(f"Duplicate section reference: {variant}:{num}")
                continue
            seen_sections.add(key)

            parsed.append({
                "variant": variant,
                "section_index": num - 1,
                "section_num": num,
                "section": sections[num - 1]
            })

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not parsed:
        print("ERROR: No valid sections found in spec", file=sys.stderr)
        sys.exit(1)

    # Assemble the mixed outline
    mixed_sections = []
    source_map = []
    total_words = 0

    for entry in parsed:
        sec = entry["section"]
        mixed_sections.append(sec)
        source_map.append({
            "variant": entry["variant"],
            "original_section": entry["section_num"],
            "title": sec.get("title", "(untitled)")
        })
        total_words += sec.get("estimated_words", 0)

    mixed = {
        "variant": "mixed",
        "variant_name": "Mixed (cherry-picked)",
        "title": "(mixed — update title after review)",
        "hook": "(mixed — update hook after review)",
        "sections": mixed_sections,
        "target_word_count": total_words,
        "tone": "(mixed — update tone after review)",
        "source_map": source_map,
        "mix_spec": spec
    }

    # Write output
    out_path = os.path.join(state_dir, "outline-mixed.json")
    atomic_json_write(out_path, mixed)

    # Print summary
    print("Mixed outline assembled successfully!")
    print(f"Output: {out_path}")
    print(f"Sections: {len(mixed_sections)}")
    print(f"Estimated words: {total_words}")
    print()
    print("Section mapping:")
    for i, sm in enumerate(source_map, 1):
        print(f'  {i}. [{sm["variant"]}:{sm["original_section"]}] {sm["title"]}')
    print()
    print("NOTE: Update title, hook, and tone in the mixed outline before proceeding.")


def main():
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    project_dir = sys.argv[1]
    spec_or_cmd = sys.argv[2]

    state_dir = os.path.join(project_dir, ".essay-state")

    if spec_or_cmd in ("list",):
        cmd_list(state_dir)
    elif spec_or_cmd in ("-h", "--help", "help"):
        usage()
    elif not spec_or_cmd:
        print("ERROR: sections_spec or command required", file=sys.stderr)
        usage()
        sys.exit(1)
    else:
        cmd_mix(state_dir, spec_or_cmd)


if __name__ == "__main__":
    main()
