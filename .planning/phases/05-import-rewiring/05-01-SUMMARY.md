---
phase: 05-import-rewiring
plan: 01
subsystem: api
tags: [rename, namespace, projekt-forge, cross-repo, wave-A]

# Dependency graph
requires:
  - phase: 05-import-rewiring/plan-00
    provides: forge-bridge v1.0.1 release with protocol + client + timeline patches upstream (unblocks Wave B, but not used in this wave)
provides:
  - projekt-forge's embedded forge_bridge/ package renamed to projekt_forge/ (history-preserving git mv)
  - 179 internal forge_bridge.* imports rewritten to projekt_forge.* across projekt_forge/, tests/, forge_gui/
  - 8 bare 'from forge_bridge import bridge' statements rewritten to 'from projekt_forge import bridge'
  - All unittest.mock.patch() string-literal targets rewritten to new module path
  - pyproject.toml: packages=['projekt_forge'], forge=projekt_forge.cli.main:cli, forge-bridge console_scripts removed
  - CLAUDE.md dev-loop section documenting pip install -e shadowing pattern
  - flame_hooks/ preserved (imports stay as forge_bridge.* — resolve against pip package in Wave B)
  - forge-bridge consumer's Python namespace collision eliminated before Wave B adds the pip dep
affects: [05-02, 05-03, 05-04, projekt-forge-phase-5-wave-B]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scoped sed bulk import rewrite (macOS-correct `sed -i ''`) targeting projekt_forge/, tests/, forge_gui/ only"
    - "Quoted-string patch-target rewriting: unittest.mock.patch(\"pkg.mod.sym\") targets treated as first-class rename candidates"
    - "Behavior-preserving pre-rename: flame_hooks/ subprocess-script imports intentionally untouched (resolve against pip package, not local tree)"

key-files:
  created: []
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/ (entire tree, renamed from forge_bridge/)
    - /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml
    - /Users/cnoellert/Documents/GitHub/projekt-forge/CLAUDE.md
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_handler_routing.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_smoke_project_creation.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui/core/flame_creator.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui/ui/project_hub.py

key-decisions:
  - "Committed as a single atomic commit (137aac3) in projekt-forge: even though the diff exceeds the 500-line heuristic (106 files / 809+ / 788-), the rewrite is mechanical and programmatic — reviewers gain more from seeing rename + import sweep together via git's --find-renames than from an artificial split"
  - "Expanded the sed rewrite scope beyond what the plan specified: added passes for bare `from forge_bridge import X` (8 sites), `import forge_bridge.X as Y` (2 sites), quoted string-literal patch targets (30+ sites in test files), and filesystem-path string literals in static-analysis tests (2 sites). All are local-package self-references; the Wave A rename applies to all of them per D-01 behavior-preserving semantics."
  - "Cosmetic mentions (docstrings saying 'forge_bridge.db.models', log channel name 'forge_bridge', FastMCP(\"forge_bridge\") literal, `python -m forge_bridge` usage text) were intentionally left unchanged in this wave — they do not affect import resolution or test behavior, and Wave C rewrites server/mcp.py and __main__.py where many of these live."

patterns-established:
  - "Wave-A rename workflow: git mv → scoped sed over .py files → cleanup __pycache__ → pyproject.toml edits → CLAUDE.md append → pip reinstall smoke check → pytest green → atomic commit with D-18 convention"
  - "Test scoping: pytest runs must be targeted at `tests/` (and nested `projekt_forge/{scanner,conform}/tests/`) to avoid pytest collecting flame_hooks script files that do sys.exit() at import time"

requirements-completed: [RWR-01]

# Metrics
duration: ~25min
completed: 2026-04-16
---

# Phase 05 Plan 01: projekt-forge rename forge_bridge -> projekt_forge (Wave A)

**Renamed projekt-forge's embedded `forge_bridge/` package to `projekt_forge/` via history-preserving `git mv` and rewrote all 179 internal `from forge_bridge.*` imports (plus bare-import and patch-target variants) to `from projekt_forge.*`, scoped to projekt_forge/, tests/, forge_gui/ — behavior-preserving, test suite still green.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-04-16
- **Tasks:** 1 (single-task plan)
- **Files changed:** 106 (with --find-renames=90%)
- **Diff:** +809 / -788 lines (rename-aware)
- **Test run:** 421 passed + 3 xfailed in tests/ (2.15s); 518 passed + 3 xfailed across all test directories

## Accomplishments

- **Directory rename:** `projekt-forge/forge_bridge/` → `projekt-forge/projekt_forge/` via `git mv` (git history preserved; `git log --follow` traces cleanly through the rename).
- **Dotted import sweep:** 179 `from forge_bridge.X import Y` rewritten to `from projekt_forge.X import Y` (scoped via `find ... -exec sed -i '' ...`).
- **Bare import sweep:** 8 `from forge_bridge import bridge` rewritten (plan's sed pattern `from forge_bridge\.` didn't catch these).
- **`import ... as` sweep:** 2 `import forge_bridge.cli.auth as auth_mod` + 1 `import forge_bridge as _fb` (fallback version lookup).
- **String-literal patch-target sweep:** 30+ `"forge_bridge.XYZ"` targets inside `unittest.mock.patch(...)` calls rewritten — these resolve the symbol at patch time, so they must match the new location for tests to pass.
- **Static-analysis path sweep:** 2 filesystem-path string literals in tests (`Path("forge_bridge/server/handlers.py")`, `repo_root / "forge_bridge"`) rewritten to point at `projekt_forge/`.
- **pyproject.toml:** `packages = ["projekt_forge"]`; `forge = "projekt_forge.cli.main:cli"`; `forge-bridge = "forge_bridge.server:main"` entry removed (pip package ships its own console_scripts after Wave B).
- **CLAUDE.md:** Appended `## Local dev loop with forge-bridge` section with `pip install -e /path/to/forge-bridge` shadowing instructions and the un-shadow recipe.
- **`flame_hooks/` preserved:** 3 executable imports in subprocess script strings + 1 docstring reference — all still say `from forge_bridge.*` so they resolve against the forge-bridge pip package after Wave B (per D-03 / RESEARCH flame_hooks audit).

## projekt-forge Commit

Single atomic commit in `/Users/cnoellert/Documents/GitHub/projekt-forge` on `main`:

1. **Wave A rename + import sweep** — `137aac3` (refactor)
   - Subject: `refactor(projekt_forge): rename forge_bridge namespace to projekt_forge + internal import sweep -- forge-bridge phase 5 wave A`
   - Matches D-18 convention.
   - Working tree clean post-commit (`git status --porcelain` returns empty).
   - NOT pushed (per execution instructions: projekt-forge's push policy is the user's call).

## Files Created/Modified (by category)

**Directory rename (99 files moved + updated):**
- `projekt_forge/**/*.py` — entire renamed tree (was `forge_bridge/**/*.py`)

**projekt-forge root config (2 files):**
- `pyproject.toml` — packages list, scripts block, forge-bridge entry removed
- `CLAUDE.md` — appended `Local dev loop with forge-bridge` section

**Out-of-tree projekt_forge imports (4 files):**
- `tests/test_handler_routing.py` — filesystem-path string rewritten
- `tests/test_smoke_project_creation.py` — filesystem-path string + docstring rewritten
- `forge_gui/core/flame_creator.py` — imports rewritten
- `forge_gui/ui/project_hub.py` — imports rewritten

**Intentionally untouched:**
- `flame_hooks/**/*.py` — 3 executable imports (subprocess context) + 1 docstring preserved

## Decisions Made

- **Single commit, not split.** Plan's STEP 10 allows both; though the rename-aware diff is 1597 lines (>500 threshold), the work is mechanical/programmatic and reviewers gain more from seeing rename + sed result together with `git diff --find-renames`. Two-commit split would require reverting file contents to stage pure renames first, which adds friction without review value.
- **Expanded sed scope.** The plan's sed was `from forge_bridge\.` only. Found 8 bare `from forge_bridge import bridge` statements, 30+ quoted patch targets, and 2 filesystem-path string literals that all needed the same rewrite. These are Rule 2 / Rule 3 deviations (missing functionality + blocking), documented below.
- **Cosmetic docstring/comment mentions left alone.** Things like `logger = logging.getLogger("forge_bridge")`, `FastMCP("forge_bridge")`, and `python -m forge_bridge` in help text do not affect import resolution or tests. Wave C's `server/mcp.py` and `__main__.py` rewrites will sweep those up alongside the architectural rewire.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bare `from forge_bridge import bridge` imports not covered by plan's sed**
- **Found during:** Task 1, STEP 9 pytest run
- **Issue:** The plan's `sed 's/from forge_bridge\./from projekt_forge\./g'` pattern requires a dot after `forge_bridge`. 8 files in `projekt_forge/tools/` used the bare-module form `from forge_bridge import bridge` (top-level import of the `bridge` module, not a submodule symbol). After Wave A rename, these still said `from forge_bridge import bridge`, and since no `forge_bridge/` local package existed any more, Python's import machinery found a stray `forge_bridge.py` Flame-hook file on sys.path that auto-starts a server and doesn't export `bridge` — producing `ImportError: cannot import name 'bridge' from 'forge_bridge'`.
- **Fix:** Added a second sed pass: `sed -i '' 's/^from forge_bridge import /from projekt_forge import /g'` over the same scope.
- **Files modified:** `projekt_forge/tools/{batch,orchestrate,project,publish,reconform,switch_grade,timeline,utility}.py` (8 files)
- **Verification:** `grep -rn "from forge_bridge" projekt_forge/ tests/ forge_gui/` returns 0; pytest progresses past the ImportError.
- **Committed in:** `137aac3` (part of the single atomic commit)

**2. [Rule 3 - Blocking] Quoted patch-target strings (`"forge_bridge.*"`) in `unittest.mock.patch(...)` calls**
- **Found during:** Task 1, STEP 9 pytest run (after fix #1)
- **Issue:** `unittest.mock.patch("forge_bridge.config.forge_config.get_db_config")` resolves the symbol at patch time via `importlib`/`pkgutil.resolve_name`. After the directory rename, no `forge_bridge.config.forge_config` symbol exists any more (or worse — resolves against a stray Flame-hook `forge_bridge.py` that doesn't have `.config`). 30+ such patch targets in 9 test files (tests/ and projekt_forge/scanner/tests/) raised `AttributeError: module 'forge_bridge' has no attribute 'config'`.
- **Fix:** Added sed pass: `sed -i '' 's/"forge_bridge\./"projekt_forge./g; s/'"'"'forge_bridge\./'"'"'projekt_forge./g'` (both single- and double-quoted forms).
- **Files modified:** `tests/test_catalog_db_creation.py`, `tests/test_project_invite.py`, `tests/test_switch_grade_mcp.py`, `tests/test_forge_cli.py`, `projekt_forge/scanner/tests/test_scanner.py`, `projekt_forge/scanner/tests/test_endpoints.py`, and 3 others.
- **Verification:** `grep -rn "\"forge_bridge\." projekt_forge/ tests/ forge_gui/` returns 0 (excluding docstrings).
- **Committed in:** `137aac3`

**3. [Rule 3 - Blocking] Filesystem-path string literals in static-analysis tests**
- **Found during:** Task 1, STEP 9 pytest run (after fixes #1 and #2)
- **Issue:** Two tests used string paths to read source files directly: `Path("forge_bridge/server/handlers.py")` in `tests/test_handler_routing.py` and `repo_root / "forge_bridge"` in `tests/test_smoke_project_creation.py::test_smoke_no_hardcoded_db`. After the directory rename, these paths do not exist → `FileNotFoundError` / empty iteration.
- **Fix:** Hand-edited both files to point at `projekt_forge/...`. Preserved the OTHER `forge_bridge` mentions in `test_smoke_project_creation.py` (fixtures that create fake flame-hook directories named `forge_bridge` — those are referring to the `flame_hooks/forge_tools/forge_bridge/` Flame-hook package, not the projekt-forge source tree, and must keep that name).
- **Files modified:** `tests/test_handler_routing.py` (1 line), `tests/test_smoke_project_creation.py` (2 lines + docstring)
- **Verification:** Full pytest suite passes (421 in `tests/`, 518 across all dirs).
- **Committed in:** `137aac3`

**4. [Rule 3 - Blocking] `import forge_bridge.X as Y` statements + bare `import forge_bridge as _fb`**
- **Found during:** Task 1, STEP 9 pytest run
- **Issue:** Plan STEP 4 caught `^import forge_bridge$` but not `import forge_bridge.cli.auth as auth_mod` (2 sites in `tests/test_smoke_project_creation.py`) or `import forge_bridge as _fb` (1 site in `projekt_forge/cli/installer.py` version-lookup fallback).
- **Fix:** Added sed pass: `sed -i '' 's/import forge_bridge\./import projekt_forge./g; s/import forge_bridge as /import projekt_forge as /g'` over the same scope.
- **Files modified:** `tests/test_smoke_project_creation.py` (2 sites), `projekt_forge/cli/installer.py` (1 site)
- **Verification:** Grep confirms 0 remaining `import forge_bridge` forms in scope.
- **Committed in:** `137aac3`

---

**Total deviations:** 4 auto-fixed (all Rule 3 — blocking: import/patch-target forms the plan's sed pattern didn't cover).
**Impact on plan:** No scope creep — all four are variants of the same "rewrite local-package references" transformation the plan intended, just beyond what the literal `from forge_bridge\.` sed pattern matched. Final outcome matches the plan's must_haves exactly.

## Issues Encountered

- **`pip install -e .` fails under hatchling without `tool.hatch.metadata.allow-direct-references = true`:** The existing `[project.optional-dependencies] cv` block uses a `git+https://` direct reference, which newer hatchling rejects by default. This is a **pre-existing issue** unrelated to the rename (the block was written before hatchling tightened its validation). Worked around by NOT reinstalling — the existing editable install already points at the repo root, so the directory rename is picked up automatically. Tests ran against the live source tree. Flagging for a future pyproject.toml patch in projekt-forge (out of scope for Wave A per plan — not in `must_haves`).
- **pytest default collection pulls in `flame_hooks/forge_tools/forge_bridge/scripts/forge_llm_test.py`** which `sys.exit(1)`s at import, breaking collection. Resolved by scoping pytest to `tests/` explicitly — which is the research-recommended command (`pytest tests/ -x -q --no-header`, RESEARCH.md §Validation Architecture). No pytest config change needed; documented in the "Test scoping" pattern above.

## must_haves Checklist

- [x] `projekt-forge/forge_bridge/` directory no longer exists; `projekt-forge/projekt_forge/` exists with identical content (via `git mv`, history preserved)
- [x] All 179 internal `from forge_bridge.*` imports (scoped to projekt_forge/, tests/, forge_gui/) rewritten to `from projekt_forge.*` — plus additional bare-import, `import ... as`, and quoted patch-target variants
- [x] `flame_hooks/` tree untouched — still contains 4 `from forge_bridge.*` references (3 executable + 1 docstring)
- [x] `pyproject.toml` packages list = `["projekt_forge"]`; forge script = `"projekt_forge.cli.main:cli"`
- [x] Pre-rewrite `forge-bridge = "forge_bridge.server:main"` console_scripts entry removed
- [x] CLAUDE.md has `Local dev loop with forge-bridge` section with `pip install -e` instructions
- [x] Full projekt-forge pytest suite passes (421 in `tests/` + 97 in nested `projekt_forge/{scanner,conform}/tests/` = 518 passed, 3 xfailed)
- [x] Single atomic commit in projekt-forge (`137aac3`)

## Self-Check

- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__init__.py` exists
- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/` does NOT exist
- [x] `grep -c 'packages = \["projekt_forge"\]' pyproject.toml` returns 1
- [x] `grep -c 'forge = "projekt_forge.cli.main:cli"' pyproject.toml` returns 1
- [x] `grep -c 'forge-bridge = "forge_bridge.server:main"' pyproject.toml` returns 0
- [x] `grep -c 'forge-bridge @ git+' pyproject.toml` returns 0 (NOT added — that is Wave B)
- [x] `grep -c 'pip install -e' CLAUDE.md` returns >= 1 (9 occurrences in dev-loop section)
- [x] `grep -rn 'from forge_bridge\.' projekt_forge/ tests/ forge_gui/` returns 0 matches
- [x] `grep -rn 'from forge_bridge\.' flame_hooks/` returns 4 matches (3 exec + 1 docstring preserved)
- [x] projekt-forge commit `137aac3` exists on `main` with D-18-compliant subject
- [x] `git -C /Users/cnoellert/Documents/GitHub/projekt-forge status --porcelain` returns empty
- [x] pytest `tests/` green: 421 passed, 3 xfailed

## Self-Check: PASSED

## Next Phase Readiness

- **Ready for Plan 05-02 (Wave B):** projekt-forge now has a clean `projekt_forge/` namespace with no `forge_bridge` local package in the way. Wave B can add the `forge-bridge @ git+...@v1.0.1` dependency and start deleting duplicates (`bridge.py`, canonical tools) with clean `ModuleNotFoundError` signals if any import flip is missed — no more silent ambiguity between local and pip.
- **No blockers for downstream plans.**
- **Forward-note for Wave C:** The cosmetic forge_bridge mentions left in `projekt_forge/server/mcp.py` (`FastMCP("forge_bridge")`, argparse `prog`, usage text) and `projekt_forge/__main__.py` (logger name, usage text) will be rewritten as part of Wave C's architectural rewrite. They do not affect Wave B.

---
*Phase: 05-import-rewiring*
*Plan: 01*
*Completed: 2026-04-16*
