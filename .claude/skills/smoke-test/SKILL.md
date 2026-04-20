---
name: smoke-test
description: Quick end-to-end pipeline smoke test for tech-essay-writer. Compiles scripts, exercises the dry-run pipeline, and verifies Project + Reference Library CRUD in a disposable sandbox. ~30 seconds.
user-invocable: true
---

# Smoke Test — tech-essay-writer

Fast end-to-end verification. Creates a throwaway sandbox, exercises every
major surface (scripts, dry-run pipeline, Project workspace, Reference
Library), reports pass/fail per step, cleans up. Targets ~30-60 seconds.

Run this before pushing any refactor, after pulling someone else's work, or
whenever `pytest tests/py/` passes but you want a quick "everything still
hangs together" check that exercises real subprocess calls and real file I/O.

## What it verifies

1. **Compile**: every script under `scripts/py/` parses
2. **Sandbox init**: temp dir + git repo initialized cleanly
3. **Dry-run pipeline**: `dry_run.py` completes all 7 stages without failures
4. **Project CRUD**: create → list → set-active → resolve → article-dir
5. **Reference Library CRUD**: add → list → tag → show → remove
6. **Isolation**: `TEW_SKILL_ROOT` + `TEW_USER_DATA_DIR` overrides actually redirect I/O (not leaking into the real source tree or `~/.tech-essay-writer/`)
7. **Cleanup**: sandbox removed, no stray processes

## Run

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd ../../.. && pwd)"
SANDBOX=$(mktemp -d -t tew-smoke)
FAKE_SKILL_ROOT="$SANDBOX/skill"
FAKE_USER_DATA="$SANDBOX/user-data"
mkdir -p "$FAKE_SKILL_ROOT" "$FAKE_USER_DATA"
export TEW_SKILL_ROOT="$FAKE_SKILL_ROOT"
export TEW_USER_DATA_DIR="$FAKE_USER_DATA"
export PYTHONPATH="$SKILL_DIR/scripts/py"
PROJECT_DIR="$SANDBOX/project"
mkdir -p "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Smoke Test — tech-essay-writer pipeline"
echo " Sandbox:      $SANDBOX"
echo " Source repo:  $SKILL_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Execute

Run every step sequentially. Report each as `STEPn=PASS` or `STEPn=FAIL`
with a brief reason. Do NOT abort on failure — collect all results so one
bug doesn't hide the others.

### Step 1: Compile check

```bash
echo ""
echo "Step 1: Compile check"
if python3 -m compileall "$SKILL_DIR/scripts/py" -q 2>&1; then
  echo "STEP1=PASS"
else
  echo "STEP1=FAIL (compilation error)"
fi
```

### Step 2: Sandbox git repo

```bash
echo ""
echo "Step 2: Sandbox init"
cd "$PROJECT_DIR"
git init -q
echo "# Smoke sandbox" > README.md
git add . && git commit -q -m "init"
if [ -d "$PROJECT_DIR/.git" ]; then
  echo "STEP2=PASS"
else
  echo "STEP2=FAIL (git init did not create .git)"
fi
```

### Step 3: Dry-run pipeline (7 stages, mocked)

`dry_run.py` already exists to simulate the entire pipeline with fake data.
Run it against the sandbox and require a zero exit code.

```bash
echo ""
echo "Step 3: Dry-run pipeline"
python3 "$SKILL_DIR/scripts/py/dry_run.py" "$PROJECT_DIR" "$SKILL_DIR" > "$SANDBOX/dry-run.log" 2>&1
DR_EXIT=$?
DR_SUMMARY=$(tail -5 "$SANDBOX/dry-run.log")
if [ $DR_EXIT -eq 0 ]; then
  echo "STEP3=PASS"
else
  echo "STEP3=FAIL (dry_run.py exit=$DR_EXIT)"
  echo "---dry-run tail---"
  echo "$DR_SUMMARY"
  echo "---"
fi
```

### Step 4: Project CRUD (resolves into fake skill root)

Run this block via `bash -c` so word-splitting and `&&` chaining behave
identically across zsh and bash.

```bash
echo ""
echo "Step 4: Project CRUD"
bash -c '
  set -e
  PM=$1
  python3 "$PM" init >/dev/null
  python3 "$PM" create smoke-proj "smoke project" >/dev/null
  python3 "$PM" set-active smoke-proj >/dev/null
  ACTIVE=$(python3 "$PM" get-active)
  RESOLVED=$(python3 "$PM" resolve)
  ADIR=$(python3 "$PM" article-dir smoke-proj first-post)
  [ "$ACTIVE" = "smoke-proj" ] || { echo "STEP4=FAIL (active=$ACTIVE)"; exit 1; }
  [ "$RESOLVED" = "smoke-proj" ] || { echo "STEP4=FAIL (resolved=$RESOLVED)"; exit 1; }
  [ "$ADIR" = "$2/projects/smoke-proj/articles/first-post" ] || { echo "STEP4=FAIL (article_dir=$ADIR)"; exit 1; }
  echo "STEP4=PASS"
' _ "$SKILL_DIR/scripts/py/project_manager.py" "$FAKE_SKILL_ROOT"
```

### Step 5: Reference Library CRUD

```bash
echo ""
echo "Step 5: Reference Library CRUD"
bash -c '
  set -e
  RL=$1
  python3 "$RL" add smoke-proj "https://arxiv.org/abs/1706.03762" --title "Attention" --tag "llm,paper" >/dev/null
  python3 "$RL" add smoke-proj "https://example.com/post" --title "Blog" >/dev/null
  COUNT=$(python3 "$RL" list smoke-proj | python3 -c "import json,sys; print(len(json.load(sys.stdin)[\"refs\"]))")
  python3 "$RL" tag smoke-proj ref-002 "reference" >/dev/null
  HAS_TITLE=$(python3 "$RL" show smoke-proj ref-001 | python3 -c "import json,sys; print(\"Attention\" in json.load(sys.stdin)[\"meta\"][\"title\"])")
  python3 "$RL" remove smoke-proj ref-001 >/dev/null
  LEFT=$(python3 "$RL" list smoke-proj | python3 -c "import json,sys; print(len(json.load(sys.stdin)[\"refs\"]))")
  [ "$COUNT" = "2" ] || { echo "STEP5=FAIL (initial count=$COUNT)"; exit 1; }
  [ "$HAS_TITLE" = "True" ] || { echo "STEP5=FAIL (has_title=$HAS_TITLE)"; exit 1; }
  [ "$LEFT" = "1" ] || { echo "STEP5=FAIL (after_remove=$LEFT)"; exit 1; }
  echo "STEP5=PASS"
' _ "$SKILL_DIR/scripts/py/reference_library.py"
```

### Step 6: Isolation check — env overrides landed

Verify the env overrides actually redirected writes into the sandbox,
not into the source repo or `~/.tech-essay-writer/`.

```bash
echo ""
echo "Step 6: Isolation check"
PROJ_FILE="$FAKE_SKILL_ROOT/projects/smoke-proj/project.json"
ACTIVE_FILE="$FAKE_USER_DATA/active-project.txt"
# Source-repo projects/ should NOT contain 'smoke-proj' (only README.md + maybe committed projects).
SRC_LEAK=$(ls "$SKILL_DIR/projects/" 2>/dev/null | grep -x smoke-proj | head -1)
if [ -f "$PROJ_FILE" ] && [ -f "$ACTIVE_FILE" ] && [ -z "$SRC_LEAK" ]; then
  echo "STEP6=PASS"
else
  echo "STEP6=FAIL (proj_file=$([ -f $PROJ_FILE ] && echo ok || echo missing) active=$([ -f $ACTIVE_FILE ] && echo ok || echo missing) leak=$SRC_LEAK)"
fi
```

### Step 7: Cleanup

```bash
echo ""
echo "Step 7: Cleanup"
cd /
rm -rf "$SANDBOX" 2>/dev/null
unset TEW_SKILL_ROOT TEW_USER_DATA_DIR PYTHONPATH
if [ ! -d "$SANDBOX" ]; then
  echo "STEP7=PASS"
else
  echo "STEP7=FAIL (sandbox not removed)"
fi
```

## Report

After all 7 steps finish, print a summary table counting PASS/FAIL. If every
step passed, print `ALL PASS ✅`. If any failed, list the failing step numbers
and their captured reasons.

```bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SMOKE TEST RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

Tally the STEPn variables you captured and print the table. Keep it terse —
one line per step, then the overall verdict.

## Abort conditions

- If Step 3 (dry-run) fails, the pipeline itself is broken — report the
  `dry-run.log` tail and tell the user to run `pytest tests/py/test_e2e_dryrun.py -v`
  for detailed diagnostics.
- If Step 6 (isolation) fails, **STOP and surface loudly**: state likely
  leaked into the real source tree. Point at `$SKILL_DIR/projects/` and
  `~/.tech-essay-writer/active-project.txt` and ask the user to inspect
  before running any destructive cleanup.
