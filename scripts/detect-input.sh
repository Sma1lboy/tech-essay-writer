#!/usr/bin/env bash
# Detect input type from user-provided text
# Returns structured JSON describing what the user provided
# Usage: detect-input.sh <text>
set -euo pipefail

TEXT="${1:?text required}"

python3 -c "
import re, json, sys

text = sys.argv[1]
results = []

# Detect URLs
urls = re.findall(r'https?://[^\s<>\"]+', text)
for url in urls:
    url_type = 'article'
    if 'github.com' in url:
        if '/blob/' in url or '/tree/' in url:
            url_type = 'code_file'
        elif '/pull/' in url or '/issues/' in url:
            url_type = 'discussion'
        else:
            url_type = 'repository'
    elif 'arxiv.org' in url:
        url_type = 'paper'
    elif 'youtube.com' in url or 'youtu.be' in url:
        url_type = 'video'
    elif any(d in url for d in ['docs.', 'documentation', '/api/', '/reference/']):
        url_type = 'documentation'
    results.append({'type': 'url', 'subtype': url_type, 'value': url})

# Detect file paths
paths = re.findall(r'(?:^|\s)([/~][^\s]+\.\w+)', text)
for path in paths:
    results.append({'type': 'file', 'value': path.strip()})

# Detect code blocks
code_blocks = re.findall(r'\x60\x60\x60(\w*)\n(.*?)\x60\x60\x60', text, re.DOTALL)
for lang, code in code_blocks:
    results.append({'type': 'code', 'language': lang or 'unknown', 'value': code.strip()})

# Remaining text is notes
remaining = text
for url in urls:
    remaining = remaining.replace(url, '')
for path in paths:
    remaining = remaining.replace(path, '')
remaining = re.sub(r'\x60\x60\x60\w*\n.*?\x60\x60\x60', '', remaining, flags=re.DOTALL)
remaining = remaining.strip()
if remaining and len(remaining) > 10:
    results.append({'type': 'note', 'value': remaining})

# Detect themes
themes = []
for pattern in [r'(?:about|regarding|on the topic of|covering)\s+([^,.]+)',
                r'(?:theme|topic|subject):\s*([^,.]+)']:
    themes.extend(m.strip() for m in re.findall(pattern, text, re.IGNORECASE))

output = {
    'items': results,
    'item_count': len(results),
    'has_urls': any(r['type'] == 'url' for r in results),
    'has_code': any(r['type'] == 'code' for r in results),
    'has_files': any(r['type'] == 'file' for r in results),
    'detected_themes': themes
}
print(json.dumps(output, indent=2))
" "$TEXT"
