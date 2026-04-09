#!/usr/bin/env python3
"""Code example validation for markdown drafts.
Parses fenced code blocks and validates syntax, imports, and runnability.
Usage: code_validate.py <markdown_file> [--json]
"""

import json
import os
import re
import subprocess
import sys
import tempfile


def usage():
    print("""Usage: code_validate.py <markdown_file> [--json]

Validates fenced code blocks in a markdown file:
  - Syntax checking (node, python3, go, rustc, bash, javac)
  - Import/require statement verification
  - Fragment detection (ellipsis, TODO, pseudo-code)

Output: JSON validation report to stdout""")


# Language normalization
LANG_MAP = {
    'javascript': 'javascript', 'js': 'javascript',
    'typescript': 'typescript', 'ts': 'typescript',
    'python': 'python', 'py': 'python',
    'go': 'go', 'rust': 'rust',
    'bash': 'bash', 'sh': 'bash',
    'java': 'java',
}

EXT_MAP = {
    'javascript': '.js', 'typescript': '.ts',
    'python': '.py', 'go': '.go', 'rust': '.rs',
    'bash': '.sh', 'java': '.java',
}

TOOL_CHECK = {
    'javascript': ['node', '--version'],
    'typescript': ['node', '--version'],
    'python': ['python3', '--version'],
    'go': ['go', 'version'],
    'rust': ['rustc', '--version'],
    'bash': ['bash', '--version'],
    'java': ['javac', '-version'],
}


def parse_code_blocks(markdown_file):
    """Parse fenced code blocks from a markdown file."""
    with open(markdown_file, 'r') as f:
        lines = f.read().split('\n')

    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^```(\w*)', line)
        if m:
            lang = m.group(1)
            start_line = i + 1  # 1-indexed
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^```\s*$', lines[i]):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                'language': lang,
                'content': '\n'.join(code_lines),
                'line_in_file': start_line
            })
        i += 1

    return blocks


def has_tool(lang):
    """Check if the syntax-checking tool for a language is installed."""
    try:
        subprocess.run(TOOL_CHECK[lang], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, KeyError):
        return False


def syntax_check(lang, content, tmp_dir):
    """Run syntax check for given language. Returns (valid, error_msg)."""
    ext = EXT_MAP.get(lang, '.txt')
    tmp_path = os.path.join(tmp_dir, f'block{ext}')
    with open(tmp_path, 'w') as f:
        f.write(content)

    try:
        if lang in ('javascript', 'typescript'):
            r = subprocess.run(['node', '--check', tmp_path], capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
        elif lang == 'python':
            r = subprocess.run(['python3', '-c',
                             'import sys,py_compile; py_compile.compile(sys.argv[1], doraise=True)',
                             tmp_path],
                             capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
        elif lang == 'go':
            r = subprocess.run(['go', 'vet', tmp_path], capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
        elif lang == 'rust':
            r = subprocess.run(['rustc', '--edition', '2021', '--crate-type', 'lib', tmp_path, '-o', '/dev/null'],
                             capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
        elif lang == 'bash':
            r = subprocess.run(['bash', '-n', tmp_path], capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
        elif lang == 'java':
            r = subprocess.run(['javac', '-d', '/tmp', tmp_path], capture_output=True, text=True, timeout=10)
            return (r.returncode == 0, r.stderr.strip())
    except subprocess.TimeoutExpired:
        return (False, "timeout during syntax check")
    except FileNotFoundError:
        return (None, "tool_missing")
    return (None, "unknown language")


def detect_fragments(content):
    """Detect placeholder/fragment markers in code."""
    markers = []
    if re.search(r'\.{3}|\u2026', content):
        markers.append('contains ellipsis')
    if re.search(r'(?i)//\s*TODO|#\s*TODO|//\s*FIXME|#\s*FIXME', content):
        markers.append('contains TODO/FIXME')
    if re.search(r'(?i)your code here|PLACEHOLDER|// \.\.\.|pseudo', content):
        markers.append('contains pseudo-code marker')
    return markers


def parse_imports(lang, content):
    """Parse import statements from code block."""
    imports = []
    if lang in ('javascript', 'typescript'):
        for m in re.finditer(r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\))""", content):
            mod = m.group(1) or m.group(2)
            status = "ok"
            if mod.startswith('./') or mod.startswith('../'):
                status = "unverifiable"
            misspellings = {'expresss', 'axois', 'loadash', 'momment', 'reeact', 'angualr', 'reacr'}
            if mod in misspellings:
                status = "possible_misspelling"
            imports.append({"module": mod, "status": status})
    elif lang == 'python':
        for m in re.finditer(r'^(?:import\s+([a-zA-Z0-9_.]+)|from\s+([a-zA-Z0-9_.]+)\s+import)', content, re.MULTILINE):
            mod = m.group(1) or m.group(2)
            status = "ok"
            if mod.startswith('.'):
                status = "unverifiable"
            imports.append({"module": mod, "status": status})
    elif lang == 'go':
        for m in re.finditer(r'"([^"]+)"', content):
            imports.append({"module": m.group(1), "status": "ok"})
    elif lang == 'rust':
        for m in re.finditer(r'^use\s+([a-zA-Z0-9_:]+);', content, re.MULTILINE):
            imports.append({"module": m.group(1), "status": "ok"})
    elif lang == 'java':
        for m in re.finditer(r'^import\s+([a-zA-Z0-9_.]+);', content, re.MULTILINE):
            imports.append({"module": m.group(1), "status": "ok"})
    return imports


def validate(markdown_file):
    """Validate all code blocks in a markdown file. Returns report dict."""
    blocks = parse_code_blocks(markdown_file)

    tmp_dir = tempfile.mkdtemp()

    total = len(blocks)
    validated = 0
    skipped = 0
    all_blocks = []
    summary = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}

    for idx, block in enumerate(blocks):
        raw_lang = block['language']
        norm_lang = LANG_MAP.get(raw_lang, '')

        if not norm_lang:
            skipped += 1
            summary["skip"] += 1
            continue

        if not has_tool(norm_lang):
            skipped += 1
            entry = {
                "block_index": idx,
                "language": norm_lang,
                "line_in_file": block['line_in_file'],
                "syntax_valid": None,
                "syntax_error": "tool_missing",
                "imports": [],
                "runnable": None,
                "fragments_detected": False,
                "issues": [f"{norm_lang} tool not installed"]
            }
            all_blocks.append(entry)
            summary["skip"] += 1
            continue

        validated += 1
        content = block['content']

        # Syntax check
        valid, err = syntax_check(norm_lang, content, tmp_dir)

        # Fragment detection
        frag_markers = detect_fragments(content)
        has_fragments = len(frag_markers) > 0

        # Import parsing
        import_list = parse_imports(norm_lang, content)

        # Determine runnable
        runnable = (valid is True) and not has_fragments

        # Collect issues
        block_issues = []
        if valid is False:
            block_issues.append(f"syntax error: {err[:200]}")
        if has_fragments:
            block_issues.extend(frag_markers)
        for imp in import_list:
            if imp['status'] != 'ok':
                block_issues.append(f"import {imp['module']}: {imp['status']}")

        entry = {
            "block_index": idx,
            "language": norm_lang,
            "line_in_file": block['line_in_file'],
            "syntax_valid": valid if valid is not None else False,
            "syntax_error": err if valid is False else None,
            "imports": import_list,
            "runnable": runnable,
            "fragments_detected": has_fragments,
            "issues": block_issues
        }

        if valid is False:
            summary["fail"] += 1
        elif block_issues:
            summary["warn"] += 1
        else:
            summary["pass"] += 1

        all_blocks.append(entry)

    # Cleanup temp dir
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Issues list = only blocks with problems
    issues = [b for b in all_blocks if b.get('issues')]

    report = {
        "file": markdown_file,
        "total_blocks": total,
        "validated": validated,
        "skipped": skipped,
        "blocks": all_blocks,
        "issues": issues,
        "summary": summary
    }

    return report


def main():
    markdown_file = sys.argv[1] if len(sys.argv) > 1 else ""

    if not markdown_file:
        usage()
        print('{"error":"no file specified"}', file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(markdown_file):
        print(json.dumps({"error": "file not found", "file": markdown_file}))
        sys.exit(1)

    report = validate(markdown_file)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
