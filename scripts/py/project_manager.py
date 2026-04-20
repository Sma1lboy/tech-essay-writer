#!/usr/bin/env python3
"""Project workspace manager for tech-essay-writer.

A Project groups related articles + shared references + shared research.
Data lives at SKILL_ROOT/projects/<slug>/ (gitignored). The active-project
pointer lives at ~/.tech-essay-writer/active-project.txt.

See docs/PROJECTS.md for the design rationale.

Commands:
  init                             Ensure the projects/ root exists
  create <slug> [description]      Create a new project
  list                             List all projects with basic metadata
  show <slug>                      Dump a project's full metadata
  get-active                       Print the active-project slug (empty if none)
  set-active <slug>                Make a project active
  clear-active                     Clear the active-project pointer
  ensure-default                   Create 'default' project if missing; set
                                   active if no active project is set
  article-dir <slug> <article>     Print the resolved article state dir
                                   (SKILL_ROOT/projects/<slug>/articles/<article>/)
  resolve [--project <slug>]       Resolve which project to use given precedence:
                                   --project flag > active-project > default

Exits non-zero on malformed slugs, missing projects, or IO errors.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from utils import atomic_json_write, read_json_file, timestamp_now


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

DEFAULT_SLUG = "default"


def skill_root() -> Path:
    """Skill repo root (resolves symlinks so installed-symlink paths work).

    scripts/py/project_manager.py -> skill_root = parents[2]

    Env override: TEW_SKILL_ROOT relocates the root. Used by tests; also lets
    users stash projects/ elsewhere without touching the source tree.
    """
    override = os.environ.get("TEW_SKILL_ROOT", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def _user_data_dir() -> Path:
    override = os.environ.get("TEW_USER_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return Path(os.path.expanduser("~/.tech-essay-writer"))


def _active_project_file() -> Path:
    return _user_data_dir() / "active-project.txt"


def projects_root() -> Path:
    return skill_root() / "projects"


def project_dir(slug: str) -> Path:
    return projects_root() / slug


def project_meta_file(slug: str) -> Path:
    return project_dir(slug) / "project.json"


def validate_slug(slug: str) -> None:
    """Raise ValueError if slug is unsafe or malformed.

    Slugs must be lowercase, start alnum, contain only [a-z0-9-], max 64 chars.
    This also blocks path-traversal attempts (../, leading dots, slashes).
    """
    if not isinstance(slug, str) or not slug:
        raise ValueError("slug must be a non-empty string")
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"invalid slug {slug!r}: must be lowercase alnum + hyphen, "
            "start with alnum, max 64 chars"
        )


def ensure_projects_root() -> Path:
    root = projects_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def project_exists(slug: str) -> bool:
    return project_meta_file(slug).is_file()


def create_project(slug: str, description: str = "") -> dict:
    """Create a new project. Raises FileExistsError if slug already exists."""
    validate_slug(slug)
    ensure_projects_root()
    if project_exists(slug):
        raise FileExistsError(f"project {slug!r} already exists")

    pdir = project_dir(slug)
    (pdir / "references").mkdir(parents=True, exist_ok=True)
    (pdir / "research").mkdir(parents=True, exist_ok=True)
    (pdir / "articles").mkdir(parents=True, exist_ok=True)

    now = timestamp_now()
    meta = {
        "slug": slug,
        "name": slug,
        "description": description,
        "voice": "",
        "created_at": now,
        "updated_at": now,
    }
    atomic_json_write(str(project_meta_file(slug)), meta)

    # Seed an empty references index so Phase 2 can assume it exists.
    ref_index = pdir / "references" / "index.json"
    if not ref_index.exists():
        atomic_json_write(str(ref_index), {"version": 1, "refs": []})

    return meta


def list_projects() -> list[dict]:
    """Return all project metadata, sorted by slug."""
    root = projects_root()
    if not root.is_dir():
        return []
    out = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        meta_file = entry / "project.json"
        if not meta_file.is_file():
            continue
        meta = read_json_file(str(meta_file))
        if isinstance(meta, dict) and meta.get("slug"):
            out.append(meta)
    return out


def read_project(slug: str) -> dict:
    validate_slug(slug)
    if not project_exists(slug):
        raise FileNotFoundError(f"project {slug!r} not found")
    return read_json_file(str(project_meta_file(slug)))


def get_active() -> str:
    apf = _active_project_file()
    if not apf.is_file():
        return ""
    try:
        slug = apf.read_text().strip()
    except OSError:
        return ""
    if not slug:
        return ""
    # If the pointer references a deleted project, treat as unset.
    try:
        validate_slug(slug)
    except ValueError:
        return ""
    if not project_exists(slug):
        return ""
    return slug


def set_active(slug: str) -> None:
    validate_slug(slug)
    if not project_exists(slug):
        raise FileNotFoundError(f"project {slug!r} not found")
    udd = _user_data_dir()
    udd.mkdir(parents=True, exist_ok=True)
    apf = _active_project_file()
    tmp = apf.with_suffix(f".tmp.{os.getpid()}")
    tmp.write_text(slug + "\n")
    os.rename(tmp, apf)


def clear_active() -> None:
    apf = _active_project_file()
    if apf.exists():
        apf.unlink()


def ensure_default() -> str:
    """Guarantee the 'default' project exists; set it active if nothing is active.

    Returns the slug of the now-active project. Safe to call repeatedly.
    """
    if not project_exists(DEFAULT_SLUG):
        create_project(DEFAULT_SLUG, description="Auto-created default project")
    if not get_active():
        set_active(DEFAULT_SLUG)
    return get_active() or DEFAULT_SLUG


def resolve_project(requested: str = "") -> str:
    """Resolve which project to use.

    Precedence: explicit `requested` > active-project > default (auto-created).
    Returns the resolved slug. Raises FileNotFoundError if `requested` is
    supplied but doesn't exist — callers must decide whether to auto-create.
    """
    if requested:
        validate_slug(requested)
        if not project_exists(requested):
            raise FileNotFoundError(f"project {requested!r} not found")
        return requested
    active = get_active()
    if active:
        return active
    return ensure_default()


def article_dir(slug: str, article_slug: str) -> Path:
    """Resolved article state directory. Does NOT create it — callers do."""
    validate_slug(slug)
    validate_slug(article_slug)
    return project_dir(slug) / "articles" / article_slug


# ─── CLI ──────────────────────────────────────────────────────────────────


def _cmd_init(_args: argparse.Namespace) -> int:
    root = ensure_projects_root()
    print(str(root))
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    try:
        meta = create_project(args.slug, args.description or "")
    except (ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(meta, indent=2))
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    projects = list_projects()
    active = get_active()
    print(json.dumps({"active": active, "projects": projects}, indent=2))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        meta = read_project(args.slug)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(meta, indent=2))
    return 0


def _cmd_get_active(_args: argparse.Namespace) -> int:
    print(get_active())
    return 0


def _cmd_set_active(args: argparse.Namespace) -> int:
    try:
        set_active(args.slug)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(args.slug)
    return 0


def _cmd_clear_active(_args: argparse.Namespace) -> int:
    clear_active()
    return 0


def _cmd_ensure_default(_args: argparse.Namespace) -> int:
    slug = ensure_default()
    print(slug)
    return 0


def _cmd_article_dir(args: argparse.Namespace) -> int:
    try:
        path = article_dir(args.slug, args.article)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(str(path))
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    try:
        slug = resolve_project(args.project or "")
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(slug)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="project_manager.py",
        description="Project workspace manager for tech-essay-writer.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Ensure projects/ root exists").set_defaults(
        func=_cmd_init
    )

    c = sub.add_parser("create", help="Create a new project")
    c.add_argument("slug")
    c.add_argument("description", nargs="?", default="")
    c.set_defaults(func=_cmd_create)

    sub.add_parser("list", help="List all projects").set_defaults(func=_cmd_list)

    s = sub.add_parser("show", help="Show project metadata")
    s.add_argument("slug")
    s.set_defaults(func=_cmd_show)

    sub.add_parser("get-active", help="Print active-project slug").set_defaults(
        func=_cmd_get_active
    )

    sa = sub.add_parser("set-active", help="Set active project")
    sa.add_argument("slug")
    sa.set_defaults(func=_cmd_set_active)

    sub.add_parser("clear-active", help="Clear active-project pointer").set_defaults(
        func=_cmd_clear_active
    )

    sub.add_parser(
        "ensure-default", help="Auto-create 'default' if missing + set active"
    ).set_defaults(func=_cmd_ensure_default)

    ad = sub.add_parser("article-dir", help="Resolve article state dir path")
    ad.add_argument("slug")
    ad.add_argument("article")
    ad.set_defaults(func=_cmd_article_dir)

    r = sub.add_parser("resolve", help="Resolve which project to use (precedence)")
    r.add_argument("--project", default="")
    r.set_defaults(func=_cmd_resolve)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
