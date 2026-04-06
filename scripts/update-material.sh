#!/usr/bin/env bash
# Update a specific material source with fetched content and key points
# Usage: update-material.sh <project_dir> <source_id> <content> [key_points_json]
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
SOURCE_ID="${2:?source_id required}"
CONTENT="${3:?content required}"
KEY_POINTS="${4:-[]}"
STATE_DIR="$PROJECT_DIR/.essay-state"
MATERIALS_FILE="$STATE_DIR/materials.json"

if [ ! -f "$MATERIALS_FILE" ]; then
  echo "No materials.json found." >&2
  exit 1
fi

python3 -c "
import json, sys, os

materials_file = sys.argv[1]
source_id = sys.argv[2]
content = sys.argv[3]
key_points_raw = sys.argv[4]

try:
    key_points = json.loads(key_points_raw)
except (json.JSONDecodeError, ValueError):
    key_points = [key_points_raw] if key_points_raw else []

with open(materials_file) as f:
    d = json.load(f)

found = False
for s in d['sources']:
    if s.get('id') == source_id:
        s['content'] = content[:5000]  # Truncate to prevent bloat
        s['key_points'] = key_points
        s['fetched'] = True
        found = True
        break

if not found:
    print(f'Source {source_id} not found', file=sys.stderr)
    sys.exit(1)

tmp = materials_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, materials_file)

print(f'Updated source {source_id} with {len(content)} chars, {len(key_points)} key points')
" "$MATERIALS_FILE" "$SOURCE_ID" "$CONTENT" "$KEY_POINTS"
