#!/usr/bin/env bash
# Intake materials parser — structures raw user inputs into materials.json
# Usage: intake-materials.sh <project_dir> <command> [args...]
set -euo pipefail

STATE_DIR=".essay-state"

usage() {
  cat <<'EOF'
Usage: intake-materials.sh <project_dir> <command> [args...]

Commands:
  init <project_dir>                      Initialize materials store
  add-url <project_dir> <url> [title]     Add a URL source
  add-note <project_dir> <note>           Add a text note
  add-file <project_dir> <file_path>      Add a local file
  add-code <project_dir> <code> [lang]    Add a code snippet
  add-theme <project_dir> <theme>         Add a cross-cutting theme
  add-angle <project_dir> <angle>         Add a potential narrative angle
  list <project_dir>                      List all materials
  export <project_dir>                    Export full materials.json
  clear <project_dir>                     Clear all materials (with confirmation)
EOF
}

materials_file() {
  echo "$1/$STATE_DIR/materials.json"
}

ensure_materials() {
  local project="$1"
  local mf
  mf="$(materials_file "$project")"
  mkdir -p "$project/$STATE_DIR"
  if [ ! -f "$mf" ]; then
    python3 -c "
import json, sys
d = {
    'sources': [],
    'themes': [],
    'potential_angles': [],
    'technical_depth': 'unknown',
    'source_count': 0
}
with open(sys.argv[1], 'w') as f:
    json.dump(d, f, indent=2)
" "$mf"
  fi
}

read_materials() {
  local mf
  mf="$(materials_file "$1")"
  if [ ! -f "$mf" ]; then
    echo "ERROR: Materials file not found: $mf" >&2
    echo '{}'
    return 1
  fi
  local content
  content=$(cat "$mf")
  # Validate JSON; fall back if corrupt
  if python3 -c "import json,sys; json.loads(sys.argv[1])" "$content" 2>/dev/null; then
    echo "$content"
  else
    echo "WARNING: Corrupt materials file: $mf — treating as empty" >&2
    echo '{"sources":[],"themes":[],"potential_angles":[],"technical_depth":"unknown","source_count":0}'
  fi
}

write_materials() {
  local project="$1" json_str="$2"
  local mf
  mf="$(materials_file "$project")"
  local tmp="${mf}.tmp.$$"
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$mf"
}

gen_id() {
  python3 -c "import time,random; print(f'src-{int(time.time())}-{random.randint(100,999)}')"
}

cmd_init() {
  local project="$1"
  ensure_materials "$project"
  echo "Materials store initialized."
}

cmd_add_url() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-url requires <project_dir> <url> [title]" >&2
    return 1
  fi
  local project="$1" url="$2" title="${3:-}"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  local id
  id=$(gen_id)
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
source = {
    'id': sys.argv[2],
    'type': 'url',
    'url': sys.argv[3],
    'title': sys.argv[4] if sys.argv[4] else None,
    'content': None,
    'key_points': [],
    'fetched': False
}
d['sources'].append(source)
d['source_count'] = len(d['sources'])
print(json.dumps(d))
" "$mat" "$id" "$url" "$title")
  write_materials "$project" "$mat"
  echo "Added URL source: $url ($id)"
}

cmd_add_note() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-note requires <project_dir> <note>" >&2
    return 1
  fi
  local project="$1" note="$2"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  local id
  id=$(gen_id)
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
source = {
    'id': sys.argv[2],
    'type': 'note',
    'content': sys.argv[3],
    'key_points': [],
    'fetched': True
}
d['sources'].append(source)
d['source_count'] = len(d['sources'])
print(json.dumps(d))
" "$mat" "$id" "$note")
  write_materials "$project" "$mat"
  echo "Added note ($id)"
}

cmd_add_file() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-file requires <project_dir> <file_path>" >&2
    return 1
  fi
  local project="$1" file_path="$2"
  ensure_materials "$project"
  if [ ! -f "$file_path" ]; then
    echo "ERROR: File not found: $file_path" >&2
    return 1
  fi
  local mat
  mat=$(read_materials "$project")
  local id
  id=$(gen_id)
  local content
  content=$(cat "$file_path")
  local ext="${file_path##*.}"
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
source = {
    'id': sys.argv[2],
    'type': 'file',
    'path': sys.argv[3],
    'extension': sys.argv[4],
    'content': sys.argv[5],
    'key_points': [],
    'fetched': True
}
d['sources'].append(source)
d['source_count'] = len(d['sources'])
print(json.dumps(d))
" "$mat" "$id" "$file_path" "$ext" "$content")
  write_materials "$project" "$mat"
  echo "Added file: $file_path ($id)"
}

cmd_add_code() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-code requires <project_dir> <code> [lang]" >&2
    return 1
  fi
  local project="$1" code="$2" lang="${3:-}"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  local id
  id=$(gen_id)
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
source = {
    'id': sys.argv[2],
    'type': 'code',
    'language': sys.argv[3] if sys.argv[3] else 'unknown',
    'content': sys.argv[4],
    'key_points': [],
    'fetched': True
}
d['sources'].append(source)
d['source_count'] = len(d['sources'])
print(json.dumps(d))
" "$mat" "$id" "$lang" "$code")
  write_materials "$project" "$mat"
  echo "Added code snippet ($id)"
}

cmd_add_theme() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-theme requires <project_dir> <theme>" >&2
    return 1
  fi
  local project="$1" theme="$2"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
theme = sys.argv[2]
if theme not in d['themes']:
    d['themes'].append(theme)
print(json.dumps(d))
" "$mat" "$theme")
  write_materials "$project" "$mat"
  echo "Added theme: $theme"
}

cmd_add_angle() {
  if [ $# -lt 2 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "ERROR: add-angle requires <project_dir> <angle>" >&2
    return 1
  fi
  local project="$1" angle="$2"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  mat=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
angle = sys.argv[2]
if angle not in d['potential_angles']:
    d['potential_angles'].append(angle)
print(json.dumps(d))
" "$mat" "$angle")
  write_materials "$project" "$mat"
  echo "Added angle: $angle"
}

cmd_list() {
  local project="$1"
  ensure_materials "$project"
  local mat
  mat=$(read_materials "$project")
  python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print(f\"Materials: {d['source_count']} sources\")
for s in d['sources']:
    t = s['type']
    if t == 'url':
        print(f\"  [{s['id']}] URL: {s.get('url','')} {'(fetched)' if s.get('fetched') else '(pending)'}\")
    elif t == 'note':
        preview = s.get('content','')[:60]
        print(f\"  [{s['id']}] Note: {preview}...\")
    elif t == 'file':
        print(f\"  [{s['id']}] File: {s.get('path','')}\")
    elif t == 'code':
        print(f\"  [{s['id']}] Code: {s.get('language','unknown')} snippet\")
print(f\"Themes: {', '.join(d.get('themes', [])) or 'none'}\")
print(f\"Angles: {', '.join(d.get('potential_angles', [])) or 'none'}\")
" "$mat"
}

cmd_export() {
  local project="$1"
  ensure_materials "$project"
  read_materials "$project"
}

cmd_clear() {
  local project="$1"
  local mf
  mf="$(materials_file "$project")"
  if [ -f "$mf" ]; then
    python3 -c "
import json, sys
d = {
    'sources': [],
    'themes': [],
    'potential_angles': [],
    'technical_depth': 'unknown',
    'source_count': 0
}
with open(sys.argv[1], 'w') as f:
    json.dump(d, f, indent=2)
" "$mf"
    echo "Materials cleared."
  else
    echo "No materials file to clear." >&2
  fi
}

# Main dispatch
CMD="${1:-}"
shift || true
PROJECT="${1:-$(pwd)}"
shift || true

case "$CMD" in
  init) cmd_init "$PROJECT" ;;
  add-url) cmd_add_url "$PROJECT" "$@" ;;
  add-note) cmd_add_note "$PROJECT" "$@" ;;
  add-file) cmd_add_file "$PROJECT" "$@" ;;
  add-code) cmd_add_code "$PROJECT" "$@" ;;
  add-theme) cmd_add_theme "$PROJECT" "$@" ;;
  add-angle) cmd_add_angle "$PROJECT" "$@" ;;
  list) cmd_list "$PROJECT" ;;
  export) cmd_export "$PROJECT" ;;
  clear) cmd_clear "$PROJECT" ;;
  *) usage; exit 1 ;;
esac
