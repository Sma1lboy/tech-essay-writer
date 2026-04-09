#!/usr/bin/env python3
"""Configuration management — persist user preferences across sessions.
Usage: config.py <command> [args...]
"""

import json
import os
import sys

from utils import atomic_json_write, read_json_file, timestamp_now

CONFIG_DIR = os.path.expanduser("~/.tech-essay-writer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

VALID_PLATFORMS = ["internal", "external", "medium", "devto", "hashnode", "wechat", "juejin"]
VALID_STYLES = ["technical", "conversational", "narrative", "formal", "casual", "academic"]
VALID_LANGUAGES = ["en", "zh"]


def usage():
    print("""Usage: config.py <command> [args...]

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

Available platforms: internal external medium devto hashnode wechat juejin""")


def read_config():
    return read_json_file(CONFIG_FILE)


def write_config(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    atomic_json_write(CONFIG_FILE, data)


def default_config():
    now = timestamp_now()
    return {
        "default_platforms": ["internal", "external"],
        "writing_style": "technical",
        "target_audiences": ["software engineers"],
        "language": "en",
        "use_author_profile": True,
        "max_refinement_rounds": 3,
        "updated_at": now
    }


def cmd_init():
    if os.path.isfile(CONFIG_FILE):
        print(f"Config already exists at {CONFIG_FILE}")
        return 0
    config = default_config()
    write_config(config)
    print(f"Config initialized at {CONFIG_FILE}")
    return 0


def cmd_read():
    config = read_config()
    if not config:
        print("No config yet. Run 'config.sh init' to create one.")
        return 0

    platforms = config.get("default_platforms", [])
    audiences = config.get("target_audiences", [])
    print("=== Tech Essay Writer Config ===")
    print(f"Default platforms: {', '.join(platforms)}")
    print(f"Writing style: {config.get('writing_style', 'technical')}")
    print(f"Target audiences: {', '.join(audiences)}")
    print(f"Language: {config.get('language', 'en')}")
    print(f"Use author profile: {config.get('use_author_profile', True)}")
    print(f"Max refinement rounds: {config.get('max_refinement_rounds', 3)}")
    print(f"Updated: {config.get('updated_at', 'never')}")
    return 0


def cmd_get(args):
    if not args:
        print("ERROR: get requires <key>", file=sys.stderr)
        return 1

    key = args[0]
    config = read_config()
    if not config:
        print("")
        return 0

    val = config.get(key)
    if val is None:
        print("")
    elif isinstance(val, (list, dict)):
        print(json.dumps(val))
    elif isinstance(val, bool):
        print("true" if val else "false")
    else:
        print(val)
    return 0


def cmd_set(args):
    if len(args) < 2:
        print("ERROR: set requires <key> <value>", file=sys.stderr)
        return 1

    key = args[0]
    value = args[1]
    config = read_config()
    if not config:
        config = default_config()

    now = timestamp_now()
    error = None

    if key == "default_platforms":
        try:
            platforms = json.loads(value)
            if not isinstance(platforms, list):
                error = "default_platforms must be a JSON array"
            else:
                invalid = [p for p in platforms if p not in VALID_PLATFORMS]
                if invalid:
                    error = f"Invalid platform(s): {', '.join(invalid)}. Valid: {', '.join(VALID_PLATFORMS)}"
                else:
                    config[key] = platforms
        except json.JSONDecodeError:
            error = "default_platforms must be a valid JSON array"
    elif key == "writing_style":
        if value not in VALID_STYLES:
            error = f"Invalid style '{value}'. Valid: {', '.join(VALID_STYLES)}"
        else:
            config[key] = value
    elif key == "target_audiences":
        try:
            audiences = json.loads(value)
            if not isinstance(audiences, list):
                error = "target_audiences must be a JSON array"
            else:
                config[key] = audiences
        except json.JSONDecodeError:
            error = "target_audiences must be a valid JSON array"
    elif key == "language":
        if value not in VALID_LANGUAGES:
            error = f"Invalid language '{value}'. Valid: {', '.join(VALID_LANGUAGES)}"
        else:
            config[key] = value
    elif key == "use_author_profile":
        if value.lower() in ("true", "1", "yes"):
            config[key] = True
        elif value.lower() in ("false", "0", "no"):
            config[key] = False
        else:
            error = f"Invalid value '{value}'. Use true or false"
    elif key == "max_refinement_rounds":
        try:
            rounds = int(value)
            if rounds < 1 or rounds > 10:
                error = "max_refinement_rounds must be between 1 and 10"
            else:
                config[key] = rounds
        except ValueError:
            error = "max_refinement_rounds must be an integer"
    else:
        error = f"Unknown config key '{key}'"

    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    else:
        config["updated_at"] = now
        write_config(config)
        print(f"Set {key}")
        return 0


def cmd_add_platform(args):
    if not args:
        print("ERROR: add-platform requires <platform>", file=sys.stderr)
        return 1

    platform = args[0]
    if platform not in VALID_PLATFORMS:
        print(f"ERROR: Invalid platform '{platform}'. Valid: {' '.join(VALID_PLATFORMS)}", file=sys.stderr)
        return 1

    config = read_config()
    if not config:
        config = default_config()

    platforms = config.get("default_platforms", [])
    if platform in platforms:
        print(f"Platform '{platform}' already in defaults.")
        return 0

    platforms.append(platform)
    config["default_platforms"] = platforms
    config["updated_at"] = timestamp_now()
    write_config(config)
    print(f"Added platform: {platform}")
    return 0


def cmd_remove_platform(args):
    if not args:
        print("ERROR: remove-platform requires <platform>", file=sys.stderr)
        return 1

    platform = args[0]
    config = read_config()
    if not config:
        print("No config exists. Run 'config.sh init' first.", file=sys.stderr)
        return 1

    platforms = config.get("default_platforms", [])
    if platform not in platforms:
        print(f"Platform '{platform}' not in defaults.", file=sys.stderr)
        return 1

    platforms.remove(platform)
    config["default_platforms"] = platforms
    config["updated_at"] = timestamp_now()
    write_config(config)
    print(f"Removed platform: {platform}")
    return 0


def cmd_add_audience(args):
    if not args:
        print("ERROR: add-audience requires <audience>", file=sys.stderr)
        return 1

    audience = args[0]
    config = read_config()
    if not config:
        config = default_config()

    audiences = config.get("target_audiences", [])
    if audience in audiences:
        print(f"Audience '{audience}' already in list.")
        return 0

    audiences.append(audience)
    config["target_audiences"] = audiences
    config["updated_at"] = timestamp_now()
    write_config(config)
    print(f"Added audience: {audience}")
    return 0


def cmd_remove_audience(args):
    if not args:
        print("ERROR: remove-audience requires <audience>", file=sys.stderr)
        return 1

    audience = args[0]
    config = read_config()
    if not config:
        print("No config exists. Run 'config.sh init' first.", file=sys.stderr)
        return 1

    audiences = config.get("target_audiences", [])
    if audience not in audiences:
        print(f"Audience '{audience}' not in list.", file=sys.stderr)
        return 1

    audiences.remove(audience)
    config["target_audiences"] = audiences
    config["updated_at"] = timestamp_now()
    write_config(config)
    print(f"Removed audience: {audience}")
    return 0


def cmd_reset():
    config = default_config()
    write_config(config)
    print("Config reset to defaults.")
    return 0


def cmd_export():
    config = read_config()
    if not config:
        config = default_config()
        write_config(config)
    print(json.dumps(config, indent=2))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "init": lambda: cmd_init(),
        "read": lambda: cmd_read(),
        "get": lambda: cmd_get(rest),
        "set": lambda: cmd_set(rest),
        "add-platform": lambda: cmd_add_platform(rest),
        "remove-platform": lambda: cmd_remove_platform(rest),
        "add-audience": lambda: cmd_add_audience(rest),
        "remove-audience": lambda: cmd_remove_audience(rest),
        "reset": lambda: cmd_reset(),
        "export": lambda: cmd_export(),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
