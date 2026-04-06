#!/usr/bin/env bash
# Author profile — persist author identity and expertise across sessions
# Usage: author-profile.sh <command> [args...]
set -euo pipefail

PROFILE_DIR="$HOME/.tech-essay-writer"
PROFILE_FILE="$PROFILE_DIR/author-profile.json"

usage() {
  cat <<'EOF'
Usage: author-profile.sh <command> [args...]

Commands:
  init                            Create default profile if not exists
  read                            Display current profile
  set <field> <value>             Set a profile field (name, bio, role, company)
  set-social <platform> <handle>  Set a social handle (twitter, linkedin, github, xiaohongshu, weibo, zhihu)
  add-expertise <topic> <level>   Add an expertise area (beginner|intermediate|expert|authority)
  remove-expertise <topic>        Remove an expertise area
  set-voice <description>         Set writing voice description
  get-bio                         Output formatted bio for article footers
  get-social-handles              Output social media handles as JSON
EOF
}

ensure_dir() {
  mkdir -p "$PROFILE_DIR"
}

read_profile() {
  if [ -f "$PROFILE_FILE" ]; then
    cat "$PROFILE_FILE"
  else
    echo '{}'
  fi
}

write_profile() {
  local json_str="$1"
  local tmp="${PROFILE_FILE}.tmp.$$"
  ensure_dir
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$PROFILE_FILE"
}

default_profile() {
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  python3 -c "
import json, sys
now = sys.argv[1]
profile = {
    'name': '',
    'bio': '',
    'role': '',
    'company': '',
    'social': {
        'twitter': '',
        'linkedin': '',
        'github': '',
        'xiaohongshu': '',
        'weibo': '',
        'zhihu': ''
    },
    'expertise_areas': [],
    'writing_voice': '',
    'updated_at': now
}
print(json.dumps(profile))
" "$now"
}

cmd_init() {
  if [ -f "$PROFILE_FILE" ]; then
    echo "Author profile already exists."
    return
  fi
  local profile
  profile=$(default_profile)
  write_profile "$profile"
  echo "Author profile initialized at $PROFILE_FILE"
}

cmd_read() {
  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    echo "No author profile yet. Run 'author-profile.sh init' to create one."
  else
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print('=== Author Profile ===')
if d.get('name'):
    print(f\"Name: {d['name']}\")
if d.get('role'):
    print(f\"Role: {d['role']}\")
if d.get('company'):
    print(f\"Company: {d['company']}\")
if d.get('bio'):
    print(f\"Bio: {d['bio']}\")
if d.get('writing_voice'):
    print(f\"Voice: {d['writing_voice']}\")
social = d.get('social', {})
active_social = {k: v for k, v in social.items() if v}
if active_social:
    print('Social:')
    for platform, handle in active_social.items():
        print(f'  {platform}: {handle}')
expertise = d.get('expertise_areas', [])
if expertise:
    print('Expertise:')
    for e in expertise:
        print(f\"  {e['topic']} ({e['level']})\")
" "$profile"
  fi
}

cmd_set() {
  local field="$1" value="$2"
  local valid_fields="name bio role company"
  if ! echo "$valid_fields" | grep -qw "$field"; then
    echo "ERROR: Invalid field '$field'. Valid fields: $valid_fields" >&2
    return 1
  fi

  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    profile=$(default_profile)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  profile=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d[sys.argv[2]] = sys.argv[3]
d['updated_at'] = sys.argv[4]
print(json.dumps(d))
" "$profile" "$field" "$value" "$now")

  write_profile "$profile"
  echo "Set $field = $value"
}

cmd_set_social() {
  local platform="$1" handle="$2"
  local valid_platforms="twitter linkedin github xiaohongshu weibo zhihu"
  if ! echo "$valid_platforms" | grep -qw "$platform"; then
    echo "ERROR: Invalid platform '$platform'. Valid platforms: $valid_platforms" >&2
    return 1
  fi

  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    profile=$(default_profile)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  profile=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d.setdefault('social', {})
d['social'][sys.argv[2]] = sys.argv[3]
d['updated_at'] = sys.argv[4]
print(json.dumps(d))
" "$profile" "$platform" "$handle" "$now")

  write_profile "$profile"
  echo "Set social.$platform = $handle"
}

cmd_add_expertise() {
  local topic="$1" level="$2"
  local valid_levels="beginner intermediate expert authority"
  if ! echo "$valid_levels" | grep -qw "$level"; then
    echo "ERROR: Invalid level '$level'. Valid levels: $valid_levels" >&2
    return 1
  fi

  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    profile=$(default_profile)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  profile=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
topic = sys.argv[2]
level = sys.argv[3]
now = sys.argv[4]

d.setdefault('expertise_areas', [])
# Update existing or add new
found = False
for e in d['expertise_areas']:
    if e['topic'] == topic:
        e['level'] = level
        found = True
        break
if not found:
    d['expertise_areas'].append({
        'topic': topic,
        'level': level,
        'added_at': now
    })

d['updated_at'] = now
print(json.dumps(d))
" "$profile" "$topic" "$level" "$now")

  write_profile "$profile"
  echo "Added expertise: $topic ($level)"
}

cmd_remove_expertise() {
  local topic="$1"
  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    echo "No profile exists."
    return 1
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  profile=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
topic = sys.argv[2]
now = sys.argv[3]

before = len(d.get('expertise_areas', []))
d['expertise_areas'] = [e for e in d.get('expertise_areas', []) if e['topic'] != topic]
after = len(d['expertise_areas'])

if before == after:
    print(json.dumps({'error': 'not_found'}))
else:
    d['updated_at'] = now
    print(json.dumps(d))
" "$profile" "$topic" "$now")

  if echo "$profile" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if 'error' not in d else 1)" 2>/dev/null; then
    write_profile "$profile"
    echo "Removed expertise: $topic"
  else
    echo "Expertise topic '$topic' not found."
    return 1
  fi
}

cmd_set_voice() {
  local description="$1"
  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    profile=$(default_profile)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  profile=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d['writing_voice'] = sys.argv[2]
d['updated_at'] = sys.argv[3]
print(json.dumps(d))
" "$profile" "$description" "$now")

  write_profile "$profile"
  echo "Set writing voice."
}

cmd_get_bio() {
  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    echo ""
    return
  fi
  python3 -c "
import json, sys
d = json.loads(sys.argv[1])
parts = []
name = d.get('name', '')
if name:
    parts.append(name)
role = d.get('role', '')
company = d.get('company', '')
if role and company:
    parts.append(f'{role} at {company}')
elif role:
    parts.append(role)
elif company:
    parts.append(company)
bio = d.get('bio', '')
if bio:
    parts.append(bio)
expertise = d.get('expertise_areas', [])
if expertise:
    topics = [e['topic'] for e in expertise if e.get('level') in ('expert', 'authority')]
    if topics:
        parts.append(f\"Expert in {', '.join(topics)}\")
print(' | '.join(parts) if parts else '')
" "$profile"
}

cmd_get_social_handles() {
  local profile
  profile=$(read_profile)
  if [ "$profile" = "{}" ]; then
    echo '{}'
    return
  fi
  python3 -c "
import json, sys
d = json.loads(sys.argv[1])
social = d.get('social', {})
active = {k: v for k, v in social.items() if v}
print(json.dumps(active, indent=2))
" "$profile"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  init) cmd_init ;;
  read) cmd_read ;;
  set) cmd_set "$@" ;;
  set-social) cmd_set_social "$@" ;;
  add-expertise) cmd_add_expertise "$@" ;;
  remove-expertise) cmd_remove_expertise "$@" ;;
  set-voice) cmd_set_voice "$@" ;;
  get-bio) cmd_get_bio ;;
  get-social-handles) cmd_get_social_handles ;;
  *) usage; exit 1 ;;
esac
