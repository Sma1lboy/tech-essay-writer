#!/usr/bin/env bash
# Fetch URL content and update materials.json with extracted key points
# Usage: fetch-urls.sh <project_dir>
# Designed to be called by the conductor after intake stage
set -euo pipefail

PROJECT_DIR="${1:?project_dir required}"
STATE_DIR="$PROJECT_DIR/.essay-state"
MATERIALS_FILE="$STATE_DIR/materials.json"

if [ ! -f "$MATERIALS_FILE" ]; then
  echo "No materials.json found."
  exit 1
fi

# Find unfetched URLs
python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

unfetched = [s for s in d['sources'] if s.get('type') == 'url' and not s.get('fetched')]
if not unfetched:
    print('All URLs already fetched.')
    sys.exit(0)

for s in unfetched:
    print(f\"FETCH:{s['id']}:{s.get('url', '')}\")
" "$MATERIALS_FILE"
