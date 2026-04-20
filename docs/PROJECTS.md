# Projects & Reference Library

Design doc for the Project abstraction and per-project Reference Library.
Landed in Phase 1 (foundation only — no integration with the existing pipeline yet).

## Motivation

Writing a blog post rarely starts from scratch. Users collect references (papers,
docs, prior posts), research a topic across multiple articles, and develop a
consistent voice over a body of related work. The current pipeline treats every
article as an isolated `<cwd>/.essay-state/` run — references don't persist,
research is re-done per article, and there's no way to group related articles.

This adds two concepts:

1. **Project** — a workspace grouping multiple articles + shared references + shared research
2. **Reference Library** — per-project pool of parsed references (papers, docs, URLs) reusable across articles in that project

## Layout

```
<SKILL_ROOT>/
├── projects/                         # gitignored; user's workspaces live here
│   ├── README.md                     # (committed) explainer for new users
│   └── <project-slug>/
│       ├── project.json              # metadata: name, topic, voice, created_at
│       ├── references/               # Reference Library
│       │   ├── index.json            # tag/domain/relevance index over all refs
│       │   ├── <ref-id>.md           # human-readable knowledge card
│       │   └── <ref-id>.json         # structured metadata (url, kind, tags, parsed_at)
│       ├── research/                 # cross-article research notes (Phase 2+)
│       └── articles/                 # (Phase 2) individual article state dirs
│           └── <article-slug>/
│               └── ...               # migration of today's .essay-state/ contents
└── ~/.tech-essay-writer/
    ├── active-project.txt            # slug of currently active project
    └── ... (existing files: taste-memory, config, author-profile, etc.)
```

**Why `SKILL_ROOT/projects/` and not `~/.tech-essay-writer/projects/`?**
User-facing data lives next to the skill repo for portability and visibility.
Backups are one-dir. `ls projects/` shows current work. Installation via
symlink (see `install.py`) uses `Path.resolve()`, so `projects/` always lands
in the source repo regardless of install method.

**Why `~/.tech-essay-writer/active-project.txt` not in `projects/`?**
"Which project is active" is a per-user runtime preference, not project data.
Keeping it with the other user-level state (taste-memory, config) is consistent.

## Opt-in semantics

A project is *available*, never *required*. Every invocation:

- If `--project <slug>` passed → use that project
- Else if active-project set via `set-active` → use that
- Else → use `default` project (auto-created on first run by `ensure-default`)

Users who never touch `/project` commands still get `default` behind the scenes,
with one article per run. They never see the project concept unless they want to.

**References, shared research, cross-article voice are all opt-in within a project.**
An article in `default` with zero references behaves identically to today's
`.essay-state/` flow (Phase 2 wires this up).

## Phase 1 (this PR)

Foundation only — no pipeline integration yet:

- `projects/` dir + gitignore entry
- `scripts/py/project_manager.py` — CRUD (`init`, `create`, `list`, `show`, `get-active`, `set-active`, `article-dir`, `ensure-default`)
- `scripts/py/reference_library.py` — CRUD (`add`, `list`, `show`, `tag`, `remove`) with placeholder knowledge cards (no deep-parsing yet)
- Tests for both

No changes to existing 977 `.essay-state` references.
No SKILL.md pipeline changes.
Everything is additive and invokable standalone.

## Phase 2 (follow-up PR)

- `resolve_state_dir(project_dir, project=None, article=None)` utility in `utils.py`
- Migrate `pipeline_state.py` to use the resolver (legacy `.essay-state/` still supported)
- Writer/research agents read from Reference Library when available
- Migration tool for existing `.essay-state/` → `projects/migrated-<ts>/articles/<slug>/`

## Phase 3 (follow-up PR)

- Deep parsers (`parser-paper.md`, `parser-docs.md`, `parser-repo.md`) — dispatched as agents when user adds a reference, produce structured knowledge cards
- Citation tracking: draft → which claims came from which references
- fact-check reviewer cross-checks citations
