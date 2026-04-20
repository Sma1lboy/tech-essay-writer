#!/usr/bin/env python3
"""Per-project Reference Library for tech-essay-writer.

Stores references (URLs, files, notes) that a project accumulates over time.
Each reference gets a human-readable knowledge card (markdown) and a JSON
sidecar with structured metadata. An index.json tracks all refs for the project.

Phase 1 (this file): CRUD only. Knowledge cards are placeholders.
Phase 3 (later): per-type deep parsers (paper, docs, repo) produce rich cards.

See docs/PROJECTS.md for layout.

Commands:
  add <project> <source> [--title T] [--kind K] [--tag t1,t2]
                                  Add a reference. Kind auto-detected if absent.
  list <project>                  List all references in a project
  show <project> <ref-id>         Show a single reference (metadata + card)
  tag <project> <ref-id> <tag>    Append a tag
  untag <project> <ref-id> <tag>  Remove a tag
  remove <project> <ref-id>       Delete a reference (card, sidecar, index entry)
  path <project> <ref-id> [md|json] Print the on-disk path for a ref

Kinds: url, file, note, paper, docs, repo. Auto-detection picks url/file/note.
Explicit kinds (paper/docs/repo) unlock per-type parsing in Phase 3.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import project_manager as pm
from utils import atomic_json_write, read_json_file, timestamp_now


VALID_KINDS = {"url", "file", "note", "paper", "docs", "repo"}
INDEX_VERSION = 1


def _references_dir(project_slug: str) -> Path:
    return pm.project_dir(project_slug) / "references"


def _index_path(project_slug: str) -> Path:
    return _references_dir(project_slug) / "index.json"


def _card_path(project_slug: str, ref_id: str) -> Path:
    return _references_dir(project_slug) / f"{ref_id}.md"


def _meta_path(project_slug: str, ref_id: str) -> Path:
    return _references_dir(project_slug) / f"{ref_id}.json"


def _ensure_project(project_slug: str) -> None:
    pm.validate_slug(project_slug)
    if not pm.project_exists(project_slug):
        raise FileNotFoundError(f"project {project_slug!r} not found")
    _references_dir(project_slug).mkdir(parents=True, exist_ok=True)


def _read_index(project_slug: str) -> dict:
    idx = read_json_file(
        str(_index_path(project_slug)), default={"version": INDEX_VERSION, "refs": []}
    )
    if not isinstance(idx, dict) or "refs" not in idx:
        idx = {"version": INDEX_VERSION, "refs": []}
    return idx


def _write_index(project_slug: str, idx: dict) -> None:
    atomic_json_write(str(_index_path(project_slug)), idx)


def _next_ref_id(project_slug: str) -> str:
    """Monotonic ref id scoped to a project: ref-001, ref-002, ...

    Scan existing refs (index + on-disk) for the highest number so gaps from
    deletions don't get reused.
    """
    idx = _read_index(project_slug)
    max_n = 0
    for entry in idx.get("refs", []):
        rid = entry.get("id", "")
        if rid.startswith("ref-"):
            try:
                max_n = max(max_n, int(rid[4:]))
            except ValueError:
                continue
    # Also consider orphaned cards/metas (index out of sync).
    refs_dir = _references_dir(project_slug)
    if refs_dir.is_dir():
        for f in refs_dir.iterdir():
            name = f.name
            if name.startswith("ref-") and (name.endswith(".md") or name.endswith(".json")):
                try:
                    max_n = max(max_n, int(name[4:-3] if name.endswith(".md") else name[4:-5]))
                except ValueError:
                    continue
    return f"ref-{max_n + 1:03d}"


def _detect_kind(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return "url"
    # Treat things that look like filesystem paths and actually exist as files.
    if os.path.isfile(source):
        return "file"
    return "note"


def _placeholder_card(ref_id: str, title: str, kind: str, source: str, tags: list[str]) -> str:
    """Phase 1 placeholder card. Phase 3 replaces with per-kind parser output."""
    tag_line = ", ".join(tags) if tags else "_none_"
    return (
        f"# {title}\n\n"
        f"- **ID:** `{ref_id}`\n"
        f"- **Kind:** `{kind}`\n"
        f"- **Source:** {source}\n"
        f"- **Tags:** {tag_line}\n\n"
        "## Key points\n\n"
        "_Not yet parsed. Phase 3 will dispatch a per-kind parser agent to "
        "populate this section (abstract/findings for papers, API surface for "
        "docs, entry points for repos, thesis/evidence for blog posts)._\n\n"
        "## Notes\n\n"
        "_User notes or excerpted quotes go here._\n"
    )


def add_reference(
    project_slug: str,
    source: str,
    title: str = "",
    kind: str = "",
    tags: list[str] | None = None,
) -> dict:
    _ensure_project(project_slug)
    if not source:
        raise ValueError("source is required")
    if not kind:
        kind = _detect_kind(source)
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind {kind!r}; must be one of {sorted(VALID_KINDS)}")
    tags = sorted(set(tags or []))
    if not title:
        title = source  # will be refined by Phase 3 parsers

    ref_id = _next_ref_id(project_slug)
    now = timestamp_now()
    meta = {
        "id": ref_id,
        "title": title,
        "kind": kind,
        "source": source,
        "tags": tags,
        "added_at": now,
        "parsed_at": "",
        "parser_version": 0,
    }

    card_text = _placeholder_card(ref_id, title, kind, source, tags)
    _card_path(project_slug, ref_id).write_text(card_text)
    atomic_json_write(str(_meta_path(project_slug, ref_id)), meta)

    idx = _read_index(project_slug)
    idx["refs"].append(
        {
            "id": ref_id,
            "title": title,
            "kind": kind,
            "source": source,
            "tags": tags,
            "added_at": now,
        }
    )
    _write_index(project_slug, idx)
    return meta


def list_references(project_slug: str) -> list[dict]:
    _ensure_project(project_slug)
    idx = _read_index(project_slug)
    return idx.get("refs", [])


def show_reference(project_slug: str, ref_id: str) -> dict:
    _ensure_project(project_slug)
    meta_file = _meta_path(project_slug, ref_id)
    if not meta_file.is_file():
        raise FileNotFoundError(f"reference {ref_id!r} not found in {project_slug!r}")
    meta = read_json_file(str(meta_file))
    card_file = _card_path(project_slug, ref_id)
    card = card_file.read_text() if card_file.is_file() else ""
    return {"meta": meta, "card": card}


def _update_index_entry(project_slug: str, ref_id: str, **updates) -> dict:
    idx = _read_index(project_slug)
    found = None
    for entry in idx["refs"]:
        if entry.get("id") == ref_id:
            entry.update(updates)
            found = entry
            break
    if found is None:
        raise FileNotFoundError(f"reference {ref_id!r} not in index")
    _write_index(project_slug, idx)
    return found


def _update_meta_sidecar(project_slug: str, ref_id: str, **updates) -> dict:
    meta_file = _meta_path(project_slug, ref_id)
    if not meta_file.is_file():
        raise FileNotFoundError(f"reference {ref_id!r} sidecar missing")
    meta = read_json_file(str(meta_file))
    meta.update(updates)
    atomic_json_write(str(meta_file), meta)
    return meta


def tag_reference(project_slug: str, ref_id: str, tag: str) -> list[str]:
    _ensure_project(project_slug)
    if not tag:
        raise ValueError("tag must be non-empty")
    meta = _update_meta_sidecar(project_slug, ref_id)  # noqa: F841 (load to validate)
    # Reload and append uniquely.
    meta = read_json_file(str(_meta_path(project_slug, ref_id)))
    tags = sorted(set(meta.get("tags", []) + [tag]))
    _update_meta_sidecar(project_slug, ref_id, tags=tags)
    _update_index_entry(project_slug, ref_id, tags=tags)
    return tags


def untag_reference(project_slug: str, ref_id: str, tag: str) -> list[str]:
    _ensure_project(project_slug)
    meta = read_json_file(str(_meta_path(project_slug, ref_id)))
    tags = sorted(t for t in meta.get("tags", []) if t != tag)
    _update_meta_sidecar(project_slug, ref_id, tags=tags)
    _update_index_entry(project_slug, ref_id, tags=tags)
    return tags


def remove_reference(project_slug: str, ref_id: str) -> None:
    _ensure_project(project_slug)
    card = _card_path(project_slug, ref_id)
    meta = _meta_path(project_slug, ref_id)
    if not meta.is_file():
        raise FileNotFoundError(f"reference {ref_id!r} not found")
    if card.is_file():
        card.unlink()
    meta.unlink()
    idx = _read_index(project_slug)
    idx["refs"] = [e for e in idx["refs"] if e.get("id") != ref_id]
    _write_index(project_slug, idx)


def ref_path(project_slug: str, ref_id: str, kind: str = "md") -> Path:
    _ensure_project(project_slug)
    if kind == "md":
        return _card_path(project_slug, ref_id)
    if kind == "json":
        return _meta_path(project_slug, ref_id)
    raise ValueError("path kind must be 'md' or 'json'")


# ─── CLI ──────────────────────────────────────────────────────────────────


def _parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _cmd_add(args: argparse.Namespace) -> int:
    try:
        meta = add_reference(
            args.project,
            args.source,
            title=args.title or "",
            kind=args.kind or "",
            tags=_parse_tags(args.tag or ""),
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(meta, indent=2))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        refs = list_references(args.project)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"project": args.project, "refs": refs}, indent=2))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        data = show_reference(args.project, args.ref_id)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2))
    return 0


def _cmd_tag(args: argparse.Namespace) -> int:
    try:
        tags = tag_reference(args.project, args.ref_id, args.tag)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(tags))
    return 0


def _cmd_untag(args: argparse.Namespace) -> int:
    try:
        tags = untag_reference(args.project, args.ref_id, args.tag)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(tags))
    return 0


def _cmd_remove(args: argparse.Namespace) -> int:
    try:
        remove_reference(args.project, args.ref_id)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_path(args: argparse.Namespace) -> int:
    try:
        p = ref_path(args.project, args.ref_id, args.kind)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(str(p))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reference_library.py",
        description="Per-project Reference Library for tech-essay-writer.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="Add a reference")
    a.add_argument("project")
    a.add_argument("source", help="URL, file path, or note text")
    a.add_argument("--title", default="")
    a.add_argument("--kind", default="", choices=[""] + sorted(VALID_KINDS))
    a.add_argument("--tag", default="", help="Comma-separated tags")
    a.set_defaults(func=_cmd_add)

    l = sub.add_parser("list", help="List references in a project")
    l.add_argument("project")
    l.set_defaults(func=_cmd_list)

    s = sub.add_parser("show", help="Show a reference (meta + card)")
    s.add_argument("project")
    s.add_argument("ref_id")
    s.set_defaults(func=_cmd_show)

    t = sub.add_parser("tag", help="Add a tag to a reference")
    t.add_argument("project")
    t.add_argument("ref_id")
    t.add_argument("tag")
    t.set_defaults(func=_cmd_tag)

    u = sub.add_parser("untag", help="Remove a tag from a reference")
    u.add_argument("project")
    u.add_argument("ref_id")
    u.add_argument("tag")
    u.set_defaults(func=_cmd_untag)

    r = sub.add_parser("remove", help="Delete a reference")
    r.add_argument("project")
    r.add_argument("ref_id")
    r.set_defaults(func=_cmd_remove)

    pa = sub.add_parser("path", help="Print on-disk path for a reference")
    pa.add_argument("project")
    pa.add_argument("ref_id")
    pa.add_argument("kind", nargs="?", default="md", choices=["md", "json"])
    pa.set_defaults(func=_cmd_path)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
