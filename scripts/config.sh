#!/usr/bin/env bash
# Configuration management — persist user preferences across sessions
# Usage: config.sh <command> [args...]
set -euo pipefail

CONFIG_DIR="$HOME/.tech-essay-writer"
CONFIG_FILE="$CONFIG_DIR/config.json"

VALID_PLATFORMS="internal external medium devto hashnode wechat juejin"
VALID_STYLES="technical conversational narrative formal casual academic"
VALID_LANGUAGES="en zh"

usage() {
  cat <<'EOF'
Usage: config.sh <command> [args...]

Commands:
  init                        Create default config if not exists
  read                        Display current config (human-readable)
  get <key>                   Get a specific value
  set <key> <value>           Set a value (with validation)
  add-platform <platform>     Add a platform to defaults
  remove-platform <platform>  Remove a platform from defaults
  add-audience <audience>     Add a target audience
  remove-audience <audience>  Remove a target audience
  reset                       Reset to defaults
  export                      Output full JSON (for piping)

Keys for get/set:
  default_platforms       List of platforms (JSON array for set)
  writing_style           Writing style (technical|conversational|narrative|formal|casual|academic)
  target_audiences        List of audiences (JSON array for set)
  language                Language preference (en|zh)
  use_author_profile      Use author profile (true|false)
  max_refinement_rounds   Max refinement rounds (1-10)

Available platforms: internal external medium devto hashnode wechat juejin
EOF
}

ensure_dir() {
  mkdir -p "$CONFIG_DIR"
}

read_config() {
  if [ -f "$CONFIG_FILE" ]; then
    cat "$CONFIG_FILE"
  else
    echo '{}'
  fi
}

write_config() {
  local json_str="$1"
  local tmp="${CONFIG_FILE}.tmp.$$"
  ensure_dir
  python3 -c "
import json, sys, os
d = json.loads(sys.argv[1])
tmp = sys.argv[2]
target = sys.argv[3]
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.rename(tmp, target)
" "$json_str" "$tmp" "$CONFIG_FILE"
}

default_config() {
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  python3 -c "
import json, sys
now = sys.argv[1]
config = {
    'default_platforms': ['internal', 'external'],
    'writing_style': 'technical',
    'target_audiences': ['software engineers'],
    'language': 'en',
    'use_author_profile': True,
    'max_refinement_rounds': 3,
    'updated_at': now
}
print(json.dumps(config))
" "$now"
}

cmd_init() {
  if [ -f "$CONFIG_FILE" ]; then
    echo "Config already exists at $CONFIG_FILE"
    return
  fi
  local config
  config=$(default_config)
  write_config "$config"
  echo "Config initialized at $CONFIG_FILE"
}

cmd_read() {
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    echo "No config yet. Run 'config.sh init' to create one."
  else
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print('=== Tech Essay Writer Config ===')
platforms = d.get('default_platforms', [])
print(f\"Default platforms: {', '.join(platforms)}\")
print(f\"Writing style: {d.get('writing_style', 'technical')}\")
audiences = d.get('target_audiences', [])
print(f\"Target audiences: {', '.join(audiences)}\")
print(f\"Language: {d.get('language', 'en')}\")
print(f\"Use author profile: {d.get('use_author_profile', True)}\")
print(f\"Max refinement rounds: {d.get('max_refinement_rounds', 3)}\")
print(f\"Updated: {d.get('updated_at', 'never')}\")
" "$config"
  fi
}

cmd_get() {
  local key="$1"
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    echo ""
    return
  fi
  python3 -c "
import json, sys
d = json.loads(sys.argv[1])
key = sys.argv[2]
val = d.get(key)
if val is None:
    print('')
elif isinstance(val, (list, dict)):
    print(json.dumps(val))
elif isinstance(val, bool):
    print('true' if val else 'false')
else:
    print(val)
" "$config" "$key"
}

cmd_set() {
  local key="$1" value="$2"
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    config=$(default_config)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  config=$(python3 -c "
import json, sys

config = json.loads(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3]
now = sys.argv[4]
valid_platforms = sys.argv[5].split()
valid_styles = sys.argv[6].split()
valid_languages = sys.argv[7].split()

error = None

if key == 'default_platforms':
    try:
        platforms = json.loads(val)
        if not isinstance(platforms, list):
            error = 'default_platforms must be a JSON array'
        else:
            invalid = [p for p in platforms if p not in valid_platforms]
            if invalid:
                error = f\"Invalid platform(s): {', '.join(invalid)}. Valid: {', '.join(valid_platforms)}\"
            else:
                config[key] = platforms
    except json.JSONDecodeError:
        error = 'default_platforms must be a valid JSON array'
elif key == 'writing_style':
    if val not in valid_styles:
        error = f\"Invalid style '{val}'. Valid: {', '.join(valid_styles)}\"
    else:
        config[key] = val
elif key == 'target_audiences':
    try:
        audiences = json.loads(val)
        if not isinstance(audiences, list):
            error = 'target_audiences must be a JSON array'
        else:
            config[key] = audiences
    except json.JSONDecodeError:
        error = 'target_audiences must be a valid JSON array'
elif key == 'language':
    if val not in valid_languages:
        error = f\"Invalid language '{val}'. Valid: {', '.join(valid_languages)}\"
    else:
        config[key] = val
elif key == 'use_author_profile':
    if val.lower() in ('true', '1', 'yes'):
        config[key] = True
    elif val.lower() in ('false', '0', 'no'):
        config[key] = False
    else:
        error = f\"Invalid value '{val}'. Use true or false\"
elif key == 'max_refinement_rounds':
    try:
        rounds = int(val)
        if rounds < 1 or rounds > 10:
            error = 'max_refinement_rounds must be between 1 and 10'
        else:
            config[key] = rounds
    except ValueError:
        error = 'max_refinement_rounds must be an integer'
else:
    error = f\"Unknown config key '{key}'\"

if error:
    print(json.dumps({'error': error}))
else:
    config['updated_at'] = now
    print(json.dumps(config))
" "$config" "$key" "$value" "$now" "$VALID_PLATFORMS" "$VALID_STYLES" "$VALID_LANGUAGES")

  # Check for error
  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if 'error' not in d else 1)" "$config" 2>/dev/null; then
    write_config "$config"
    echo "Set $key"
  else
    local err
    err=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['error'])" "$config")
    echo "ERROR: $err" >&2
    return 1
  fi
}

cmd_add_platform() {
  local platform="$1"
  if ! echo "$VALID_PLATFORMS" | grep -qw "$platform"; then
    echo "ERROR: Invalid platform '$platform'. Valid: $VALID_PLATFORMS" >&2
    return 1
  fi

  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    config=$(default_config)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  config=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
platform = sys.argv[2]
now = sys.argv[3]
platforms = d.get('default_platforms', [])
if platform in platforms:
    print(json.dumps({'error': 'already_exists'}))
else:
    platforms.append(platform)
    d['default_platforms'] = platforms
    d['updated_at'] = now
    print(json.dumps(d))
" "$config" "$platform" "$now")

  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if 'error' not in d else 1)" "$config" 2>/dev/null; then
    write_config "$config"
    echo "Added platform: $platform"
  else
    echo "Platform '$platform' already in defaults."
  fi
}

cmd_remove_platform() {
  local platform="$1"
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    echo "No config exists. Run 'config.sh init' first." >&2
    return 1
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  config=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
platform = sys.argv[2]
now = sys.argv[3]
platforms = d.get('default_platforms', [])
if platform not in platforms:
    print(json.dumps({'error': 'not_found'}))
else:
    platforms.remove(platform)
    d['default_platforms'] = platforms
    d['updated_at'] = now
    print(json.dumps(d))
" "$config" "$platform" "$now")

  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if 'error' not in d else 1)" "$config" 2>/dev/null; then
    write_config "$config"
    echo "Removed platform: $platform"
  else
    echo "Platform '$platform' not in defaults." >&2
    return 1
  fi
}

cmd_add_audience() {
  local audience="$1"
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    config=$(default_config)
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  config=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
audience = sys.argv[2]
now = sys.argv[3]
audiences = d.get('target_audiences', [])
if audience in audiences:
    print(json.dumps({'error': 'already_exists'}))
else:
    audiences.append(audience)
    d['target_audiences'] = audiences
    d['updated_at'] = now
    print(json.dumps(d))
" "$config" "$audience" "$now")

  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if 'error' not in d else 1)" "$config" 2>/dev/null; then
    write_config "$config"
    echo "Added audience: $audience"
  else
    echo "Audience '$audience' already in list."
  fi
}

cmd_remove_audience() {
  local audience="$1"
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    echo "No config exists. Run 'config.sh init' first." >&2
    return 1
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  config=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
audience = sys.argv[2]
now = sys.argv[3]
audiences = d.get('target_audiences', [])
if audience not in audiences:
    print(json.dumps({'error': 'not_found'}))
else:
    audiences.remove(audience)
    d['target_audiences'] = audiences
    d['updated_at'] = now
    print(json.dumps(d))
" "$config" "$audience" "$now")

  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if 'error' not in d else 1)" "$config" 2>/dev/null; then
    write_config "$config"
    echo "Removed audience: $audience"
  else
    echo "Audience '$audience' not in list." >&2
    return 1
  fi
}

cmd_reset() {
  local config
  config=$(default_config)
  write_config "$config"
  echo "Config reset to defaults."
}

cmd_export() {
  local config
  config=$(read_config)
  if [ "$config" = "{}" ]; then
    config=$(default_config)
    write_config "$config"
  fi
  python3 -c "import json,sys; print(json.dumps(json.loads(sys.argv[1]), indent=2))" "$config"
}

# Main dispatch
CMD="${1:-}"
shift || true

case "$CMD" in
  init) cmd_init ;;
  read) cmd_read ;;
  get) cmd_get "$@" ;;
  set) cmd_set "$@" ;;
  add-platform) cmd_add_platform "$@" ;;
  remove-platform) cmd_remove_platform "$@" ;;
  add-audience) cmd_add_audience "$@" ;;
  remove-audience) cmd_remove_audience "$@" ;;
  reset) cmd_reset ;;
  export) cmd_export ;;
  *) usage; exit 1 ;;
esac
