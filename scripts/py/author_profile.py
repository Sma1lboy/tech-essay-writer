#!/usr/bin/env python3
"""Author profile — persist author identity and expertise across sessions.
Usage: author_profile.py <command> [args...]
"""

import json
import os
import sys

from utils import atomic_json_write, read_json_file, timestamp_now

PROFILE_DIR = os.path.expanduser("~/.tech-essay-writer")
PROFILE_FILE = os.path.join(PROFILE_DIR, "author-profile.json")

VALID_FIELDS = ["name", "bio", "role", "company"]
VALID_SOCIAL_PLATFORMS = ["twitter", "linkedin", "github", "xiaohongshu", "weibo", "zhihu"]
VALID_EXPERTISE_LEVELS = ["beginner", "intermediate", "expert", "authority"]


def usage():
    print("""Usage: author-profile.sh <command> [args...]

Commands:
  init                            Create default profile if not exists
  read                            Display current profile
  set <field> <value>             Set a profile field (name, bio, role, company)
  set-social <platform> <handle>  Set a social handle (twitter, linkedin, github, xiaohongshu, weibo, zhihu)
  add-expertise <topic> <level>   Add an expertise area (beginner|intermediate|expert|authority)
  remove-expertise <topic>        Remove an expertise area
  set-voice <description>         Set writing voice description
  get-bio                         Output formatted bio for article footers
  get-social-handles              Output social media handles as JSON""")


def read_profile():
    return read_json_file(PROFILE_FILE)


def write_profile(data):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    atomic_json_write(PROFILE_FILE, data)


def default_profile():
    now = timestamp_now()
    return {
        "name": "",
        "bio": "",
        "role": "",
        "company": "",
        "social": {
            "twitter": "",
            "linkedin": "",
            "github": "",
            "xiaohongshu": "",
            "weibo": "",
            "zhihu": ""
        },
        "expertise_areas": [],
        "writing_voice": "",
        "updated_at": now
    }


def cmd_init():
    if os.path.isfile(PROFILE_FILE):
        print("Author profile already exists.")
        return 0
    profile = default_profile()
    write_profile(profile)
    print(f"Author profile initialized at {PROFILE_FILE}")
    return 0


def cmd_read():
    profile = read_profile()
    if not profile:
        print("No author profile yet. Run 'author-profile.sh init' to create one.")
        return 0

    print("=== Author Profile ===")
    if profile.get("name"):
        print(f"Name: {profile['name']}")
    if profile.get("role"):
        print(f"Role: {profile['role']}")
    if profile.get("company"):
        print(f"Company: {profile['company']}")
    if profile.get("bio"):
        print(f"Bio: {profile['bio']}")
    if profile.get("writing_voice"):
        print(f"Voice: {profile['writing_voice']}")
    social = profile.get("social", {})
    active_social = {k: v for k, v in social.items() if v}
    if active_social:
        print("Social:")
        for platform, handle in active_social.items():
            print(f"  {platform}: {handle}")
    expertise = profile.get("expertise_areas", [])
    if expertise:
        print("Expertise:")
        for e in expertise:
            print(f"  {e['topic']} ({e['level']})")
    return 0


def cmd_set(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: set requires <field> <value>", file=sys.stderr)
        return 1

    field = args[0]
    value = args[1]

    if field not in VALID_FIELDS:
        print(f"ERROR: Invalid field '{field}'. Valid fields: {' '.join(VALID_FIELDS)}", file=sys.stderr)
        return 1

    profile = read_profile()
    if not profile:
        profile = default_profile()

    now = timestamp_now()
    profile[field] = value
    profile["updated_at"] = now
    write_profile(profile)
    print(f"Set {field} = {value}")
    return 0


def cmd_set_social(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: set-social requires <platform> <handle>", file=sys.stderr)
        return 1

    platform = args[0]
    handle = args[1]

    if platform not in VALID_SOCIAL_PLATFORMS:
        print(f"ERROR: Invalid platform '{platform}'. Valid platforms: {' '.join(VALID_SOCIAL_PLATFORMS)}", file=sys.stderr)
        return 1

    profile = read_profile()
    if not profile:
        profile = default_profile()

    now = timestamp_now()
    profile.setdefault("social", {})
    profile["social"][platform] = handle
    profile["updated_at"] = now
    write_profile(profile)
    print(f"Set social.{platform} = {handle}")
    return 0


def cmd_add_expertise(args):
    if len(args) < 2 or not args[0] or not args[1]:
        print("ERROR: add-expertise requires <topic> <level>", file=sys.stderr)
        return 1

    topic = args[0]
    level = args[1]

    if level not in VALID_EXPERTISE_LEVELS:
        print(f"ERROR: Invalid level '{level}'. Valid levels: {' '.join(VALID_EXPERTISE_LEVELS)}", file=sys.stderr)
        return 1

    profile = read_profile()
    if not profile:
        profile = default_profile()

    now = timestamp_now()
    profile.setdefault("expertise_areas", [])

    # Update existing or add new
    found = False
    for e in profile["expertise_areas"]:
        if e["topic"] == topic:
            e["level"] = level
            found = True
            break
    if not found:
        profile["expertise_areas"].append({
            "topic": topic,
            "level": level,
            "added_at": now
        })

    profile["updated_at"] = now
    write_profile(profile)
    print(f"Added expertise: {topic} ({level})")
    return 0


def cmd_remove_expertise(args):
    if not args or not args[0]:
        print("ERROR: remove-expertise requires <topic>", file=sys.stderr)
        return 1

    topic = args[0]
    profile = read_profile()
    if not profile:
        print("No profile exists.")
        return 1

    before = len(profile.get("expertise_areas", []))
    profile["expertise_areas"] = [e for e in profile.get("expertise_areas", []) if e["topic"] != topic]
    after = len(profile["expertise_areas"])

    if before == after:
        print(f"Expertise topic '{topic}' not found.")
        return 1

    now = timestamp_now()
    profile["updated_at"] = now
    write_profile(profile)
    print(f"Removed expertise: {topic}")
    return 0


def cmd_set_voice(args):
    if not args or not args[0]:
        print("ERROR: set-voice requires <description>", file=sys.stderr)
        return 1

    description = args[0]
    profile = read_profile()
    if not profile:
        profile = default_profile()

    now = timestamp_now()
    profile["writing_voice"] = description
    profile["updated_at"] = now
    write_profile(profile)
    print("Set writing voice.")
    return 0


def cmd_get_bio():
    profile = read_profile()
    if not profile:
        print("")
        return 0

    parts = []
    name = profile.get("name", "")
    if name:
        parts.append(name)
    role = profile.get("role", "")
    company = profile.get("company", "")
    if role and company:
        parts.append(f"{role} at {company}")
    elif role:
        parts.append(role)
    elif company:
        parts.append(company)
    bio = profile.get("bio", "")
    if bio:
        parts.append(bio)
    expertise = profile.get("expertise_areas", [])
    if expertise:
        topics = [e["topic"] for e in expertise if e.get("level") in ("expert", "authority")]
        if topics:
            parts.append(f"Expert in {', '.join(topics)}")
    print(" | ".join(parts) if parts else "")
    return 0


def cmd_get_social_handles():
    profile = read_profile()
    if not profile:
        print("{}")
        return 0

    social = profile.get("social", {})
    active = {k: v for k, v in social.items() if v}
    print(json.dumps(active, indent=2))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    rest = sys.argv[2:]

    dispatch = {
        "init": lambda: cmd_init(),
        "read": lambda: cmd_read(),
        "set": lambda: cmd_set(rest),
        "set-social": lambda: cmd_set_social(rest),
        "add-expertise": lambda: cmd_add_expertise(rest),
        "remove-expertise": lambda: cmd_remove_expertise(rest),
        "set-voice": lambda: cmd_set_voice(rest),
        "get-bio": lambda: cmd_get_bio(),
        "get-social-handles": lambda: cmd_get_social_handles(),
    }

    if cmd in dispatch:
        result = dispatch[cmd]()
        sys.exit(result or 0)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
