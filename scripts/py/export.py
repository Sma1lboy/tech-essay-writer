#!/usr/bin/env python3
"""Export and archive system for tech-essay-writer.
Usage: export.py <project_dir> <format> [output_dir]
       export.py list-archive [--json]
"""

import base64
import glob
import json
import os
import re
import shutil
import sys
import tarfile

from utils import atomic_json_write, read_json_file, timestamp_now

ARCHIVE_BASE = os.path.expanduser("~/.tech-essay-writer/articles")
STATE_DIR = ".essay-state"


def usage():
    print("""Usage: export.py <project_dir> <format> [output_dir]
       export.py list-archive [--json]

Formats:
  bundle      Export everything (.essay-state/ + final articles) as a tar.gz
  markdown    Export all final-*.md files to output_dir
  html        Convert final-*.md to basic HTML with proper formatting
  json        Export pipeline state + all artifacts as single JSON
  archive     Add to ~/.tech-essay-writer/articles/ archive with metadata

Special commands:
  list-archive [--json]  List all archived articles

Examples:
  python3 scripts/py/export.py ./my-project bundle ./exports
  python3 scripts/py/export.py ./my-project markdown ./output
  python3 scripts/py/export.py ./my-project html ./html-output
  python3 scripts/py/export.py ./my-project json
  python3 scripts/py/export.py ./my-project archive
  python3 scripts/py/export.py list-archive
  python3 scripts/py/export.py list-archive --json""")


# ── Validation helpers ──────────────────────────────────────────────────────


def validate_project(project):
    """Check project dir exists and has .essay-state/. Print ERROR to stderr and return 1 if not."""
    if not os.path.isdir(project):
        print(f"ERROR: Project directory not found: {project}", file=sys.stderr)
        return 1
    state_path = os.path.join(project, STATE_DIR)
    if not os.path.isdir(state_path):
        print(f"ERROR: No {STATE_DIR} directory found in {project}", file=sys.stderr)
        print("Has the pipeline been initialized?", file=sys.stderr)
        return 1
    return 0


def has_final_articles(project):
    """Count final-*.md files in .essay-state/. Return count."""
    pattern = os.path.join(project, STATE_DIR, "final-*.md")
    return len(glob.glob(pattern))


def get_topic(project):
    """Read pipeline-state.json, return topic or 'untitled'."""
    state_file = os.path.join(project, STATE_DIR, "pipeline-state.json")
    data = read_json_file(state_file)
    return data.get("topic", "untitled") if data else "untitled"


def make_slug(topic):
    """Convert to lowercase slug suitable for filenames."""
    slug = topic.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if not slug:
        slug = "untitled"
    if len(slug) > 60:
        slug = slug[:60].rstrip('-')
    return slug


def get_quality_score(project):
    """Read pipeline-state.json, return quality_score or composite_score field, or 'N/A'."""
    state_file = os.path.join(project, STATE_DIR, "pipeline-state.json")
    data = read_json_file(state_file)
    if not data:
        return "N/A"
    score = data.get("quality_score", "")
    if score == "":
        score = data.get("composite_score", "")
    return score if score else "N/A"


def get_platforms(project):
    """Read pipeline-state.json, return comma-joined platforms list."""
    state_file = os.path.join(project, STATE_DIR, "pipeline-state.json")
    data = read_json_file(state_file)
    if not data:
        return ""
    platforms = data.get("platforms", [])
    if isinstance(platforms, list):
        return ",".join(platforms)
    return str(platforms)


def _utc_timestamp():
    """Return YYYYMMDD-HHMMSS in UTC."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _utc_date():
    """Return YYYY-MM-DD in UTC."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Commands ────────────────────────────────────────────────────────────────


def cmd_bundle(project, output_dir=None):
    if output_dir is None or output_dir == "":
        output_dir = project
    err = validate_project(project)
    if err:
        return err

    topic = get_topic(project)
    slug = make_slug(topic)
    timestamp = _utc_timestamp()
    archive_name = f"essay-bundle-{slug}-{timestamp}.tar.gz"

    os.makedirs(output_dir, exist_ok=True)

    archive_path = os.path.join(output_dir, archive_name)
    state_path = STATE_DIR

    # Create tar.gz of .essay-state/ directory from within the project dir
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(os.path.join(project, state_path), arcname=state_path)

    size = os.path.getsize(archive_path)
    print(f"Bundle created: {archive_path}")
    print(f"Size: {size} bytes")
    return 0


def cmd_markdown(project, output_dir=None):
    if output_dir is None or output_dir == "":
        output_dir = os.path.join(project, "export-markdown")
    err = validate_project(project)
    if err:
        return err

    count = has_final_articles(project)
    if count == 0:
        print(f"ERROR: No final articles found in {project}/{STATE_DIR}/", file=sys.stderr)
        print("Pipeline must reach the polish stage to produce final-*.md files.", file=sys.stderr)
        return 1

    os.makedirs(output_dir, exist_ok=True)

    exported = 0
    pattern = os.path.join(project, STATE_DIR, "final-*.md")
    for f in sorted(glob.glob(pattern)):
        basename = os.path.basename(f)
        shutil.copy2(f, os.path.join(output_dir, basename))
        exported += 1

    print(f"Exported {exported} markdown file(s) to {output_dir}")
    return 0


def _md_to_html(md_content, title):
    """Convert markdown content to a full HTML document."""
    import html as html_mod

    lines = md_content.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    code_lang = ''

    for line in lines:
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                html_lines.append('</code></pre>')
                in_code_block = False
            else:
                code_lang = line[3:].strip()
                lang_attr = f' class="language-{html_mod.escape(code_lang)}"' if code_lang else ''
                html_lines.append(f'<pre><code{lang_attr}>')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(html_mod.escape(line))
            continue

        # Close list if we hit a non-list line
        if in_list and not line.startswith('- ') and not line.startswith('* ') and not re.match(r'^\d+\.\s', line):
            html_lines.append('</ul>')
            in_list = False

        # Headers
        if line.startswith('######'):
            html_lines.append(f'<h6>{html_mod.escape(line[6:].strip())}</h6>')
        elif line.startswith('#####'):
            html_lines.append(f'<h5>{html_mod.escape(line[5:].strip())}</h5>')
        elif line.startswith('####'):
            html_lines.append(f'<h4>{html_mod.escape(line[4:].strip())}</h4>')
        elif line.startswith('###'):
            html_lines.append(f'<h3>{html_mod.escape(line[3:].strip())}</h3>')
        elif line.startswith('##'):
            html_lines.append(f'<h2>{html_mod.escape(line[2:].strip())}</h2>')
        elif line.startswith('#'):
            html_lines.append(f'<h1>{html_mod.escape(line[1:].strip())}</h1>')
        # Horizontal rule
        elif re.match(r'^---+$', line.strip()):
            html_lines.append('<hr>')
        # Unordered list
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            item = line[2:].strip()
            html_lines.append(f'<li>{html_mod.escape(item)}</li>')
        # Ordered list
        elif re.match(r'^\d+\.\s', line):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            item = re.sub(r'^\d+\.\s', '', line).strip()
            html_lines.append(f'<li>{html_mod.escape(item)}</li>')
        # Blockquote
        elif line.startswith('>'):
            text = line.lstrip('>').strip()
            html_lines.append(f'<blockquote><p>{html_mod.escape(text)}</p></blockquote>')
        # Empty line
        elif line.strip() == '':
            html_lines.append('')
        # Paragraph
        else:
            escaped = html_mod.escape(line)
            # Inline formatting: bold, italic, code, links
            escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
            escaped = re.sub(r'\*(.+?)\*', r'<em>\1</em>', escaped)
            escaped = re.sub(r'`(.+?)`', r'<code>\1</code>', escaped)
            escaped = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', escaped)
            html_lines.append(f'<p>{escaped}</p>')

    # Close any open tags
    if in_list:
        html_lines.append('</ul>')
    if in_code_block:
        html_lines.append('</code></pre>')

    body = '\n'.join(html_lines)

    html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_mod.escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      max-width: 800px;
      margin: 2rem auto;
      padding: 0 1rem;
      line-height: 1.6;
      color: #333;
    }}
    h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; color: #111; }}
    h1 {{ font-size: 2rem; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }}
    pre {{ background: #f6f8fa; padding: 1em; border-radius: 6px; overflow-x: auto; }}
    code {{ background: #f0f0f0; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }}
    pre code {{ background: none; padding: 0; }}
    blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    hr {{ border: none; border-top: 1px solid #eee; margin: 2em 0; }}
    ul {{ padding-left: 2em; }}
    li {{ margin: 0.25em 0; }}
    strong {{ font-weight: 600; }}
    p {{ margin: 0.8em 0; }}
  </style>
</head>
<body>
{body}
</body>
</html>'''

    return html_doc


def cmd_html(project, output_dir=None):
    if output_dir is None or output_dir == "":
        output_dir = os.path.join(project, "export-html")
    err = validate_project(project)
    if err:
        return err

    count = has_final_articles(project)
    if count == 0:
        print(f"ERROR: No final articles found in {project}/{STATE_DIR}/", file=sys.stderr)
        print("Pipeline must reach the polish stage to produce final-*.md files.", file=sys.stderr)
        return 1

    os.makedirs(output_dir, exist_ok=True)

    topic = get_topic(project)
    exported = 0

    pattern = os.path.join(project, STATE_DIR, "final-*.md")
    for f in sorted(glob.glob(pattern)):
        basename = os.path.basename(f)
        html_name = basename.rsplit('.md', 1)[0] + '.html'

        with open(f, 'r') as fh:
            md_content = fh.read()

        html_content = _md_to_html(md_content, topic)

        html_path = os.path.join(output_dir, html_name)
        with open(html_path, 'w') as fh:
            fh.write(html_content)

        exported += 1

    print(f"Exported {exported} HTML file(s) to {output_dir}")
    return 0


def cmd_json(project, output_dir=None):
    if output_dir is None or output_dir == "":
        output_dir = project
    err = validate_project(project)
    if err:
        return err

    topic = get_topic(project)
    slug = make_slug(topic)
    timestamp = _utc_timestamp()
    json_name = f"essay-export-{slug}-{timestamp}.json"

    os.makedirs(output_dir, exist_ok=True)

    state_dir_path = os.path.join(project, STATE_DIR)

    export_data = {
        "format_version": "1.0",
        "exported_at": timestamp_now(),
        "pipeline_state": None,
        "artifacts": {},
        "final_articles": {}
    }

    # Pipeline state
    ps_path = os.path.join(state_dir_path, "pipeline-state.json")
    if os.path.exists(ps_path):
        export_data["pipeline_state"] = read_json_file(ps_path)

    # Collect all artifacts
    for fname in sorted(os.listdir(state_dir_path)):
        fpath = os.path.join(state_dir_path, fname)
        if not os.path.isfile(fpath):
            continue
        if fname == "pipeline-state.json":
            continue

        try:
            with open(fpath, 'r') as fh:
                content = fh.read()
        except UnicodeDecodeError:
            # Binary file: base64-encode it
            with open(fpath, 'rb') as fh:
                content = base64.b64encode(fh.read()).decode('ascii')
            export_data["artifacts"][fname] = {"encoding": "base64", "content": content}
            continue

        # Try to parse as JSON
        if fname.endswith('.json'):
            try:
                export_data["artifacts"][fname] = json.loads(content)
                continue
            except json.JSONDecodeError:
                pass

        # Final articles get a special section
        if fname.startswith('final-') and fname.endswith('.md'):
            platform = fname[6:-3]  # strip "final-" and ".md"
            export_data["final_articles"][platform] = content
        else:
            export_data["artifacts"][fname] = content

    json_path = os.path.join(output_dir, json_name)
    with open(json_path, 'w') as fh:
        json.dump(export_data, fh, indent=2, ensure_ascii=False)

    size = os.path.getsize(json_path)
    print(f"JSON export: {json_path}")
    print(f"Size: {size} bytes")
    return 0


def cmd_archive(project):
    err = validate_project(project)
    if err:
        return err

    count = has_final_articles(project)
    if count == 0:
        print(f"ERROR: No final articles to archive in {project}/{STATE_DIR}/", file=sys.stderr)
        print("Pipeline must reach the polish stage to produce final-*.md files.", file=sys.stderr)
        return 1

    topic = get_topic(project)
    slug = make_slug(topic)
    date_str = _utc_date()
    archive_dir = os.path.join(ARCHIVE_BASE, f"{date_str}-{slug}")

    # If directory already exists, add a numeric suffix
    if os.path.isdir(archive_dir):
        i = 2
        while os.path.isdir(f"{archive_dir}-{i}"):
            i += 1
        archive_dir = f"{archive_dir}-{i}"

    os.makedirs(archive_dir, exist_ok=True)

    # Copy final articles
    archived = 0
    pattern = os.path.join(project, STATE_DIR, "final-*.md")
    for f in sorted(glob.glob(pattern)):
        shutil.copy2(f, archive_dir)
        archived += 1

    # Build metadata
    quality_score = get_quality_score(project)
    platforms_str = get_platforms(project)

    # Try to parse quality score as number
    try:
        quality_score_val = float(quality_score)
    except (ValueError, TypeError):
        quality_score_val = None

    # Parse platforms
    platform_list = [p.strip() for p in platforms_str.split(',') if p.strip()] if platforms_str else []

    # Get stage and other info from pipeline state
    stage = "unknown"
    publish_dates = {}
    language = "en"
    series_id = ""
    ps_path = os.path.join(project, STATE_DIR, "pipeline-state.json")
    ps_data = read_json_file(ps_path)
    if ps_data:
        stage = ps_data.get("stage", "unknown")
        publish_dates = ps_data.get("publish_dates", {})
        language = ps_data.get("language", "en")
        series_id = ps_data.get("series_id", "")

    # List archived files
    files = sorted(f for f in os.listdir(archive_dir) if os.path.isfile(os.path.join(archive_dir, f)))

    metadata = {
        "topic": topic,
        "quality_score": quality_score_val,
        "platforms": platform_list,
        "publish_dates": publish_dates,
        "language": language,
        "series_id": series_id,
        "pipeline_stage": stage,
        "archived_at": timestamp_now(),
        "source_project": os.path.abspath(project),
        "files": files
    }

    meta_path = os.path.join(archive_dir, "metadata.json")
    atomic_json_write(meta_path, metadata)

    print(f"Archived {archived} article(s) to {archive_dir}")
    print(f"Metadata saved: {meta_path}")
    return 0


def cmd_list_archive(json_mode=False):
    if not os.path.isdir(ARCHIVE_BASE):
        if json_mode:
            print("[]")
        else:
            print("No archived articles found.")
            print(f"Archive directory: {ARCHIVE_BASE}")
        return 0

    entries = []
    for name in sorted(os.listdir(ARCHIVE_BASE)):
        full = os.path.join(ARCHIVE_BASE, name)
        if not os.path.isdir(full):
            continue

        meta_path = os.path.join(full, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, IOError):
                meta = {"topic": name, "error": "corrupt metadata"}
        else:
            # Directory exists but no metadata -- infer from dirname
            meta = {"topic": name, "quality_score": None, "platforms": [], "archived_at": "unknown"}

        meta["_dirname"] = name
        articles = [f for f in os.listdir(full) if f.startswith("final-") and f.endswith(".md")]
        meta["_article_count"] = len(articles)
        entries.append(meta)

    if json_mode:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
    else:
        if not entries:
            print("No archived articles found.")
        else:
            print(f"{len(entries)} archived article(s):\n")
            for e in entries:
                dirname = e.get("_dirname", "?")
                topic = e.get("topic", "untitled")
                score = e.get("quality_score")
                if isinstance(score, (int, float)) and score is not None:
                    score_str = f"{score:.1f}/10"
                else:
                    score_str = "N/A"
                platforms = e.get("platforms", [])
                plat_str = ", ".join(platforms) if platforms else "none"
                archived_at = e.get("archived_at", "unknown")
                count = e.get("_article_count", 0)
                pub_dates = e.get("publish_dates", {})
                pub_str = ""
                if pub_dates:
                    pub_parts = [f"{k}: {v}" for k, v in pub_dates.items()]
                    pub_str = f"  Published: {'; '.join(pub_parts)}\n"

                print(f"  {dirname}/")
                print(f"    Topic: {topic}")
                print(f"    Score: {score_str}  |  Platforms: {plat_str}  |  Articles: {count}")
                if pub_str:
                    print(pub_str, end='')
                print(f"    Archived: {archived_at}")
                print()

    return 0


# ── Main dispatch ───────────────────────────────────────────────────────────


def main():
    # Handle list-archive as first argument (no project dir needed)
    if len(sys.argv) > 1 and sys.argv[1] == "list-archive":
        json_mode = "--json" in sys.argv[2:]
        result = cmd_list_archive(json_mode)
        sys.exit(result or 0)

    # Normal commands require project_dir and format
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    project_dir = sys.argv[1]
    fmt = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    dispatch = {
        "bundle": lambda: cmd_bundle(project_dir, output_dir),
        "markdown": lambda: cmd_markdown(project_dir, output_dir),
        "html": lambda: cmd_html(project_dir, output_dir),
        "json": lambda: cmd_json(project_dir, output_dir),
        "archive": lambda: cmd_archive(project_dir),
    }

    if fmt in dispatch:
        result = dispatch[fmt]()
        sys.exit(result or 0)
    else:
        print(f"ERROR: Unknown format '{fmt}'. Valid: bundle markdown html json archive", file=sys.stderr)
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
