#!/usr/bin/env bash
# Export and archive system for tech-essay-writer
# Usage: export.sh <project_dir> <format> [output_dir]
#        export.sh list-archive [--json]
set -euo pipefail

ARCHIVE_BASE="$HOME/.tech-essay-writer/articles"
STATE_DIR=".essay-state"

usage() {
  cat <<'EOF'
Usage: export.sh <project_dir> <format> [output_dir]
       export.sh list-archive [--json]

Formats:
  bundle      Export everything (.essay-state/ + final articles) as a tar.gz
  markdown    Export all final-*.md files to output_dir
  html        Convert final-*.md to basic HTML with proper formatting
  json        Export pipeline state + all artifacts as single JSON
  archive     Add to ~/.tech-essay-writer/articles/ archive with metadata

Special commands:
  list-archive [--json]  List all archived articles

Examples:
  bash scripts/export.sh ./my-project bundle ./exports
  bash scripts/export.sh ./my-project markdown ./output
  bash scripts/export.sh ./my-project html ./html-output
  bash scripts/export.sh ./my-project json
  bash scripts/export.sh ./my-project archive
  bash scripts/export.sh list-archive
  bash scripts/export.sh list-archive --json
EOF
}

# ─── Validation helpers ─────────────────────────────────────────────────────

validate_project() {
  local project="$1"
  if [ ! -d "$project" ]; then
    echo "ERROR: Project directory not found: $project" >&2
    return 1
  fi
  if [ ! -d "$project/$STATE_DIR" ]; then
    echo "ERROR: No $STATE_DIR directory found in $project" >&2
    echo "Has the pipeline been initialized?" >&2
    return 1
  fi
}

# Check that at least one final-*.md exists
has_final_articles() {
  local project="$1"
  local count=0
  for f in "$project/$STATE_DIR"/final-*.md; do
    [ -f "$f" ] && count=$((count + 1))
  done
  echo "$count"
}

# Read topic from pipeline state
get_topic() {
  local project="$1"
  local state_file="$project/$STATE_DIR/pipeline-state.json"
  if [ -f "$state_file" ]; then
    python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('topic','untitled'))" "$state_file" 2>/dev/null || echo "untitled"
  else
    echo "untitled"
  fi
}

# Generate a slug from a topic string
make_slug() {
  local topic="$1"
  python3 -c "
import re, sys
topic = sys.argv[1]
slug = topic.lower().strip()
slug = re.sub(r'[^a-z0-9\s-]', '', slug)
slug = re.sub(r'[\s]+', '-', slug)
slug = re.sub(r'-+', '-', slug)
slug = slug.strip('-')
if not slug:
    slug = 'untitled'
# Limit length
if len(slug) > 60:
    slug = slug[:60].rstrip('-')
print(slug)
" "$topic"
}

# Get quality score if available
get_quality_score() {
  local project="$1"
  local state_file="$project/$STATE_DIR/pipeline-state.json"
  if [ -f "$state_file" ]; then
    python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
score = d.get('quality_score', '')
if score == '':
    score = d.get('composite_score', '')
print(score if score else 'N/A')
" "$state_file" 2>/dev/null || echo "N/A"
  else
    echo "N/A"
  fi
}

# Get platforms from pipeline state
get_platforms() {
  local project="$1"
  local state_file="$project/$STATE_DIR/pipeline-state.json"
  if [ -f "$state_file" ]; then
    python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
platforms = d.get('platforms', [])
if isinstance(platforms, list):
    print(','.join(platforms))
else:
    print(str(platforms))
" "$state_file" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# ─── Bundle format ──────────────────────────────────────────────────────────

cmd_bundle() {
  local project="$1"
  local output_dir="${2:-$project}"
  validate_project "$project"

  local topic
  topic=$(get_topic "$project")
  local slug
  slug=$(make_slug "$topic")
  local timestamp
  timestamp=$(date -u +"%Y%m%d-%H%M%S")
  local archive_name="essay-bundle-${slug}-${timestamp}.tar.gz"

  mkdir -p "$output_dir"

  # Create tar.gz from the .essay-state directory and any final-*.md at project root
  local tar_source="$STATE_DIR"
  (cd "$project" && tar -czf "$output_dir/$archive_name" "$tar_source")

  echo "Bundle created: $output_dir/$archive_name"
  local size
  size=$(wc -c < "$output_dir/$archive_name" | tr -d ' ')
  echo "Size: ${size} bytes"
}

# ─── Markdown format ────────────────────────────────────────────────────────

cmd_markdown() {
  local project="$1"
  local output_dir="${2:-$project/export-markdown}"
  validate_project "$project"

  local count
  count=$(has_final_articles "$project")
  if [ "$count" -eq 0 ]; then
    echo "ERROR: No final articles found in $project/$STATE_DIR/" >&2
    echo "Pipeline must reach the polish stage to produce final-*.md files." >&2
    return 1
  fi

  mkdir -p "$output_dir"

  local exported=0
  for f in "$project/$STATE_DIR"/final-*.md; do
    [ -f "$f" ] || continue
    local basename
    basename=$(basename "$f")
    cp "$f" "$output_dir/$basename"
    exported=$((exported + 1))
  done

  echo "Exported $exported markdown file(s) to $output_dir"
}

# ─── HTML format ─────────────────────────────────────────────────────────────

cmd_html() {
  local project="$1"
  local output_dir="${2:-$project/export-html}"
  validate_project "$project"

  local count
  count=$(has_final_articles "$project")
  if [ "$count" -eq 0 ]; then
    echo "ERROR: No final articles found in $project/$STATE_DIR/" >&2
    echo "Pipeline must reach the polish stage to produce final-*.md files." >&2
    return 1
  fi

  mkdir -p "$output_dir"

  local topic
  topic=$(get_topic "$project")
  local exported=0

  for f in "$project/$STATE_DIR"/final-*.md; do
    [ -f "$f" ] || continue
    local basename
    basename=$(basename "$f")
    local html_name="${basename%.md}.html"

    python3 - "$f" "$output_dir/$html_name" "$topic" << 'PYEOF'
import sys, re, html as html_mod

md_path = sys.argv[1]
html_path = sys.argv[2]
title = sys.argv[3]

with open(md_path, 'r') as f:
    content = f.read()

# Basic markdown to HTML conversion
lines = content.split('\n')
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

with open(html_path, 'w') as f:
    f.write(html_doc)
PYEOF

    exported=$((exported + 1))
  done

  echo "Exported $exported HTML file(s) to $output_dir"
}

# ─── JSON format ─────────────────────────────────────────────────────────────

cmd_json() {
  local project="$1"
  local output_dir="${2:-$project}"
  validate_project "$project"

  local topic
  topic=$(get_topic "$project")
  local slug
  slug=$(make_slug "$topic")
  local timestamp
  timestamp=$(date -u +"%Y%m%d-%H%M%S")
  local json_name="essay-export-${slug}-${timestamp}.json"

  mkdir -p "$output_dir"

  python3 - "$project/$STATE_DIR" "$output_dir/$json_name" << 'PYEOF'
import json, sys, os, base64

state_dir = sys.argv[1]
output_path = sys.argv[2]

export_data = {
    "format_version": "1.0",
    "exported_at": None,
    "pipeline_state": None,
    "artifacts": {},
    "final_articles": {}
}

# Timestamp
from datetime import datetime, timezone
export_data["exported_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Pipeline state
ps_path = os.path.join(state_dir, "pipeline-state.json")
if os.path.exists(ps_path):
    with open(ps_path) as f:
        export_data["pipeline_state"] = json.load(f)

# Collect all artifacts
for fname in sorted(os.listdir(state_dir)):
    fpath = os.path.join(state_dir, fname)
    if not os.path.isfile(fpath):
        continue
    if fname == "pipeline-state.json":
        continue

    try:
        with open(fpath, 'r') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Binary file: base64-encode it
        with open(fpath, 'rb') as f:
            content = base64.b64encode(f.read()).decode('ascii')
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

with open(output_path, 'w') as f:
    json.dump(export_data, f, indent=2, ensure_ascii=False)
PYEOF

  echo "JSON export: $output_dir/$json_name"
  local size
  size=$(wc -c < "$output_dir/$json_name" | tr -d ' ')
  echo "Size: ${size} bytes"
}

# ─── Archive format ──────────────────────────────────────────────────────────

cmd_archive() {
  local project="$1"
  validate_project "$project"

  local count
  count=$(has_final_articles "$project")
  if [ "$count" -eq 0 ]; then
    echo "ERROR: No final articles to archive in $project/$STATE_DIR/" >&2
    echo "Pipeline must reach the polish stage to produce final-*.md files." >&2
    return 1
  fi

  local topic
  topic=$(get_topic "$project")
  local slug
  slug=$(make_slug "$topic")
  local date_str
  date_str=$(date -u +"%Y-%m-%d")
  local archive_dir="$ARCHIVE_BASE/${date_str}-${slug}"

  # If directory already exists, add a numeric suffix
  if [ -d "$archive_dir" ]; then
    local i=2
    while [ -d "${archive_dir}-${i}" ]; do
      i=$((i + 1))
    done
    archive_dir="${archive_dir}-${i}"
  fi

  mkdir -p "$archive_dir"

  # Copy final articles
  local archived=0
  for f in "$project/$STATE_DIR"/final-*.md; do
    [ -f "$f" ] || continue
    cp "$f" "$archive_dir/"
    archived=$((archived + 1))
  done

  # Build metadata
  local quality_score
  quality_score=$(get_quality_score "$project")
  local platforms
  platforms=$(get_platforms "$project")

  python3 - "$archive_dir" "$topic" "$quality_score" "$platforms" "$project" << 'PYEOF'
import json, sys, os
from datetime import datetime, timezone

archive_dir = sys.argv[1]
topic = sys.argv[2]
quality_score = sys.argv[3]
platforms = sys.argv[4]
project_dir = sys.argv[5]

# Try to parse quality score as number
try:
    quality_score = float(quality_score)
except (ValueError, TypeError):
    quality_score = None

# Parse platforms
platform_list = [p.strip() for p in platforms.split(',') if p.strip()] if platforms else []

# Get stage and other info from pipeline state
stage = "unknown"
publish_dates = {}
language = "en"
series_id = ""
ps_path = os.path.join(project_dir, ".essay-state", "pipeline-state.json")
if os.path.exists(ps_path):
    with open(ps_path) as f:
        ps = json.load(f)
    stage = ps.get("stage", "unknown")
    publish_dates = ps.get("publish_dates", {})
    language = ps.get("language", "en")
    series_id = ps.get("series_id", "")

# List archived files
files = sorted(f for f in os.listdir(archive_dir) if os.path.isfile(os.path.join(archive_dir, f)))

metadata = {
    "topic": topic,
    "quality_score": quality_score,
    "platforms": platform_list,
    "publish_dates": publish_dates,
    "language": language,
    "series_id": series_id,
    "pipeline_stage": stage,
    "archived_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "source_project": os.path.abspath(project_dir),
    "files": files
}

meta_path = os.path.join(archive_dir, "metadata.json")
with open(meta_path, 'w') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
PYEOF

  echo "Archived $archived article(s) to $archive_dir"
  echo "Metadata saved: $archive_dir/metadata.json"
}

# ─── List archive ────────────────────────────────────────────────────────────

cmd_list_archive() {
  local json_mode=false
  if [ "${1:-}" = "--json" ]; then
    json_mode=true
  fi

  if [ ! -d "$ARCHIVE_BASE" ]; then
    if [ "$json_mode" = true ]; then
      echo "[]"
    else
      echo "No archived articles found."
      echo "Archive directory: $ARCHIVE_BASE"
    fi
    return
  fi

  python3 - "$ARCHIVE_BASE" "$json_mode" << 'PYEOF'
import json, sys, os

archive_base = sys.argv[1]
json_mode = sys.argv[2].lower() == "true"

entries = []
for name in sorted(os.listdir(archive_base)):
    full = os.path.join(archive_base, name)
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
        # Directory exists but no metadata — infer from dirname
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
            score_str = f"{score:.1f}/10" if isinstance(score, (int, float)) and score is not None else "N/A"
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
PYEOF
}

# ─── Main dispatch ───────────────────────────────────────────────────────────

# Handle list-archive as first argument (no project dir needed)
if [ "${1:-}" = "list-archive" ]; then
  shift
  cmd_list_archive "$@"
  exit 0
fi

# Normal commands require project_dir and format
PROJECT_DIR="${1:-}"
FORMAT="${2:-}"
OUTPUT_DIR="${3:-}"

if [ -z "$PROJECT_DIR" ] || [ -z "$FORMAT" ]; then
  usage
  exit 1
fi

case "$FORMAT" in
  bundle) cmd_bundle "$PROJECT_DIR" "$OUTPUT_DIR" ;;
  markdown) cmd_markdown "$PROJECT_DIR" "$OUTPUT_DIR" ;;
  html) cmd_html "$PROJECT_DIR" "$OUTPUT_DIR" ;;
  json) cmd_json "$PROJECT_DIR" "$OUTPUT_DIR" ;;
  archive) cmd_archive "$PROJECT_DIR" ;;
  *) echo "ERROR: Unknown format '$FORMAT'. Valid: bundle markdown html json archive" >&2; usage; exit 1 ;;
esac
