# projects/

Each subdirectory here is a Project — a workspace grouping related articles,
shared references, and shared research.

This directory is **gitignored** except for this README. Your projects live
locally; the skill repo stays clean.

## Quick start

```bash
# Create a project
python3 scripts/py/project_manager.py create my-blog "Personal tech blog"

# Make it active
python3 scripts/py/project_manager.py set-active my-blog

# Add a reference
python3 scripts/py/reference_library.py add my-blog https://arxiv.org/abs/1706.03762 --title "Attention Is All You Need"

# See everything
python3 scripts/py/project_manager.py show my-blog
python3 scripts/py/reference_library.py list my-blog
```

## Structure

```
<project-slug>/
├── project.json          # metadata (name, description, voice, created_at)
├── references/           # Reference Library
│   ├── index.json
│   ├── <ref-id>.md       # knowledge card (human-readable)
│   └── <ref-id>.json     # metadata sidecar
├── research/             # cross-article research notes
└── articles/             # per-article state (wired in Phase 2)
```

## Skipping projects entirely

If you don't pass `--project` and never run `set-active`, a `default` project
is auto-created on first use. Everything still works; the project concept is
just invisible. Reference Library and shared research are opt-in features —
leave them empty and the pipeline behaves exactly like the pre-project flow.
