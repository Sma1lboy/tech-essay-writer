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

## Phase 2 (shipped — commits `226a010`, `f16dd15`)

- `pipeline_state.py init --project <slug>` binds the article to a workspace Project; falls back to `resolve_project()` (active → default) when the flag is omitted
- `reference_library.format_for_prompt(slug)` renders the library as a compact markdown block
- `orchestrate.py` injects that block into the research, outline, and writer prompts
- SKILL.md Stage 1 explicitly calls `pipeline_state init` (previously state was lazy-created via `set-field`, silently bypassing the project binding)

Remaining Phase-2-shaped work (not yet done, queue for later):
- `resolve_state_dir(project_dir, project=None, article=None)` utility + migrate the 977 `.essay-state/` references
- Migration tool for existing `.essay-state/` → `projects/<slug>/articles/<slug>/`

## Phase 3 — Relevance-driven summarizer (NOT per-kind parsers)

**Design correction.** The earlier plan ("dispatch paper/docs/repo parsers by `kind`") is wrong. `kind` is the *source format*, but what writer / researcher / factcheck agents actually want from a reference is its **relevance to the current article** — the same question regardless of whether the source is a paper, docs, blog post, or repo.

Splitting by source type creates:
- **Arbitrary rules**: a paper introducing a library is also docs; a repo with a great README is mostly docs; forcing one `kind` per ref is a false dichotomy.
- **Bureaucratic schemas**: N schemas to maintain, N test branches, N places for edge cases, without buying anything the consuming agent actually uses.
- **Wrong axis**: consumers want "what claim does this source make that matters for my topic / thesis?" — that is not source-type-dependent.

### Revised approach

One unified **summarizer** agent (tentative name `summarize-reference.md`, not "parser"). Input: the reference's fetched/read content + the project topic + the current article's thesis when available. Output: a single structured schema, identical across all references.

Tentative schema for the JSON sidecar under `references/<ref-id>.json`:

```jsonc
{
  "claims": ["what this source argues / provides"],
  "evidence": [
    {"quote": "...", "where": "section 3.1 / line 42 / README intro"}
  ],
  "relevance": "why this matters for the current article (supporting, counter-example, benchmark, prior art, inspiration, ...)",
  "caveats": ["limitations", "publication date staleness", "disputed claims"]
}
```

The knowledge-card `<ref-id>.md` becomes a human-readable rendering of the same data.

### What `kind` becomes

Stays as display-only metadata — nothing dispatches on it. Users see `Kind: paper` in the prompt block for context, but the summarizer runs the same prompt whether `kind` is `paper`, `url`, `note`, or anything else. Auto-detection of `url` vs `file` vs `note` is still convenient for display; it no longer implies a different code path.

### Citation tracking (unchanged goal, updated phrasing)

- Writer output embeds citation anchors (e.g. `[ref-003]`) tying claims to library entries
- fact-check reviewer cross-checks the anchors against the `claims` + `evidence` in the ref sidecar

### Why delay implementation

Phase 2 is reachable and useful right now: a user can curate refs, start writing, and the agent sees them — the refs just show up as `{title, source, tags}` rather than structured extractions. Phase 3 upgrades the *quality* of what the agent sees, not whether anything works. Before coding the summarizer, we want at least one real project's-worth of curated refs to pressure-test the schema against — otherwise we're designing in the abstract.
