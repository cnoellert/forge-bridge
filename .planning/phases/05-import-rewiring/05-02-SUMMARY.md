---
phase: 05-import-rewiring
plan: 02
subsystem: api
tags: [pip, delete, pip-install, cross-repo, atomic, wave-B, RWR-02]

# Dependency graph
requires:
  - phase: 05-import-rewiring/plan-00
    provides: forge-bridge v1.0.1 tag (canonical protocol builders, ref_msg_id fix, timeline gap-fill) — git+...@v1.0.1 resolves to site-packages
  - phase: 05-import-rewiring/plan-01
    provides: projekt-forge local package renamed forge_bridge/ -> projekt_forge/; 179 imports rewritten; test suite green at 421 passing / 3 xfailed
provides:
  - projekt-forge pyproject.toml dependencies list contains 'forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1'
  - 4 duplicated modules deleted from projekt-forge tree (bridge.py, tools/publish.py, tools/switch_grade.py, tools/timeline.py)
  - Canonical pip imports restored in projekt_forge/__main__.py, server/mcp.py, tools/{orchestrate,batch,project,reconform,utility,catalog,scan}.py
  - Forge-specific extensions PRESERVED: client/{__init__,async_client,sync_client}.py (D-09b branch-b), server/protocol/ (D-09a), tools/{batch,project}.py (D-10)
  - Hook sys.path collision fixed in flame_hooks/forge_tools/**/scripts/*.py + 3 test helpers (D-12 precondition to Wave B)
affects: [05-03, 05-04, projekt-forge-phase-5-wave-C]

# Tech tracking
tech-stack:
  added:
    - "forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1 (projekt-forge runtime dep)"
  patterns:
    - "Hook precondition + RWR-02 atomic commit split: separate 'fix(hooks)' commit for the sys.path collision precondition, then the single atomic RWR-02 'refactor(projekt_forge)' commit for pip-dep + deletes + import flips in one unit"
    - "Projekt-forge-specific test cleanup rule: keep tests that map to pip surface; delete tests asserting on fork-only internals (alternative_path/alternative_start_frame/alternative_duration/entity_id fields, server-side openclip writer, UUID _switch.clip naming, forge_openclip_writer wiring)"
    - "Pytest invocation scoping: run `pytest tests/` (explicit path) to avoid default-collection pollution from flame_hooks/forge_tools/forge_bridge/scripts/forge_llm_test.py (matches *_test.py + sys.exit on Ollama offline)"

key-files:
  created: []
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/mcp.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/orchestrate.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/batch.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/project.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/reconform.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/utility.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/catalog.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/scan.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_switch_grade_mcp.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/forge_tools/** (13 hook files, sys.path.insert -> append)
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_forge_stream.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_catalog_client_shared.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_ingest_dialog_catalog.py
    - /Users/cnoellert/Documents/GitHub/forge-bridge/.planning/phases/05-import-rewiring/05-RESEARCH.md (D-12 entry appended)
  deleted:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/bridge.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/publish.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/switch_grade.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/timeline.py

key-decisions:
  - "D-09b resolved to branch-b (preserve local clients) — projekt-forge's db_server relies on the forge-specific extended HELLO 'project_name' for per-project DB routing; canonical pip AsyncClient sends canonical HELLO with no project_name, so swapping the client would silently break DB routing at runtime. All three client files kept: client/__init__.py, client/async_client.py, client/sync_client.py."
  - "Two-commit execution instead of single: a precondition 'fix(hooks)' commit for the sys.path.insert->append collision at 17 sites, then the atomic 'refactor(projekt_forge)' RWR-02 commit. The plan wrote 'single atomic commit'; the deviation is that the precondition commit is mechanically separate (it fixes an issue discovered during Wave B execution that was not described in the plan). The RWR-02 commit itself is still atomic per RWR-02 language."
  - "tests/test_switch_grade_mcp.py pared from 22 tests to 15 — deleted 7 projekt-forge-specific test cases that asserted on fork-only SwitchGradeInput fields (alternative_path/alternative_start_frame/alternative_duration/entity_id), the server-side openclip writer (_write_openclip_server_side / forge_openclip_writer), and UUID _switch.clip naming. Rewrote 4 tests in TestSwitchGradeInput + TestSwitchGradeInputDefaults + TestSwitchGradeBridgeCode to use the pip-canonical media_path field. Preserved coverage for: QueryAlternativesInput validation, SwitchGradeInput validation, async-callable invariants, bridge code emits smart_replace_media + create_reel. This is the Option 1 path the user approved."

requirements-completed: [RWR-01, RWR-02]

# Metrics
duration: ~40min (including test-cleanup analysis and verification loops)
completed: 2026-04-16
---

# Phase 05 Plan 02: Adopt forge-bridge v1.0.1 pip + Atomic RWR-02 Delete Summary

**projekt-forge now consumes forge-bridge v1.0.1 via pip (git+tag pin), 4 duplicated modules deleted in the same atomic commit as the dep add + canonical-import flips, with the D-09b local client layer preserved for forge-specific DB routing — pytest tests/ green at 414 passed + 3 xfailed (baseline 421 - 7 projekt-forge-specific switch_grade tests removed per user approval of Option 1).**

## Commits Landed

### projekt-forge repo

1. **`4d2b579` — fix(hooks): append forge_bridge scripts dir to sys.path to prevent pip package shadowing (phase 5 D-12)**
   - Precondition commit unblocking Wave B's test suite.
   - 16 files changed, 17 insertions(+), 17 deletions(-).
   - Changed `sys.path.insert(0, scripts_dir)` → `sys.path.append(scripts_dir)` at 17 edit sites across 13 Flame hook files + 3 test helpers.
   - See D-12 note below for technical detail.

2. **`9856376` — refactor(projekt_forge): adopt forge-bridge v1.0.1 pip + delete 4 duplicate modules (RWR-02, D-09b branch-b)**
   - The atomic RWR-02 commit.
   - 15 files changed, 50 insertions(+), 3039 deletions(-).
   - Adds forge-bridge pip dep, flips 9 import sites to canonical pip, rewrites test_switch_grade_mcp.py against pip surface, deletes 4 duplicated modules.

## D-08 DELETE List (final state — all removed from projekt_forge/)

| File | Status |
|------|--------|
| `projekt_forge/bridge.py` | DELETED (canonical in pip) |
| `projekt_forge/tools/publish.py` | DELETED (canonical in pip; Phase 4 PKG-03 scrubbed portofino) |
| `projekt_forge/tools/switch_grade.py` | DELETED (canonical evolved in v1.0; fork copy stale) |
| `projekt_forge/tools/timeline.py` | DELETED (canonical v1.0.1 has gap-fill + strip fix) |

Verification: `test ! -f` on each — all four pass.

## D-08 PRESERVE List (final state — all retained)

| File / Dir | Reason |
|-----------|--------|
| `projekt_forge/client/__init__.py` | D-09b branch-b — re-exports forge-specific AsyncClient/SyncClient |
| `projekt_forge/client/async_client.py` | D-09b branch-b — extended HELLO with `project_name` for per-project DB routing |
| `projekt_forge/client/sync_client.py` | D-09b branch-b — matching sync variant |
| `projekt_forge/server/protocol/` | D-09a — extended wire types (QUERY_LINEAGE, QUERY_SHOT_DEPS, etc.) |
| `projekt_forge/tools/batch.py` | D-10 — forge-specific `setup_denoise` |
| `projekt_forge/tools/project.py` | D-10 — enhanced `list_desktop` with scope/filter |
| `projekt_forge/tools/catalog.py` | D-10 — forge-specific lineage queries (imports canonical builders from pip) |
| `projekt_forge/tools/orchestrate.py` | D-10 — forge-specific publish pipeline |
| `projekt_forge/tools/scan.py` | D-10 — forge-specific scanner MCP wrapper |
| `projekt_forge/server/{handlers,db_server,registry}.py` | D-09a — forge-specific server composition |
| `projekt_forge/scanner/, conform/, db/, config/, cli/, seed/` | All forge-specific |
| `flame_hooks/forge_tools/**` | All forge-specific (sys.path bootstrapping fixed in D-12) |

Verification: `test -f` / `test -d` on each — all pass.

## D-09b Audit Result (branch-b disposition confirmed)

Per prior-agent state carried into this resume session: `AsyncClient(project_name=...)` usage was found in projekt-forge db_server paths, which justifies preserving projekt_forge/client/async_client.py rather than deleting. The full client layer was kept per branch-b; no re-wrapping work was needed in this plan.

## Import Flip Count (canonical pip restorations)

9 source files flipped from local `projekt_forge.*` imports to canonical `forge_bridge.*` pip imports:

1. `projekt_forge/__main__.py` — `from forge_bridge.bridge import configure`
2. `projekt_forge/server/mcp.py` — canonical server lifecycle imports
3. `projekt_forge/tools/orchestrate.py` — `import forge_bridge.bridge as bridge`
4. `projekt_forge/tools/batch.py` — canonical tool-layer imports
5. `projekt_forge/tools/project.py` — canonical tool-layer imports
6. `projekt_forge/tools/reconform.py` — canonical tool-layer imports
7. `projekt_forge/tools/utility.py` — canonical tool-layer imports
8. `projekt_forge/tools/catalog.py` — `from forge_bridge.server.protocol import query_lineage, query_shot_deps` (v1.0.1 canonical lazy imports)
9. `projekt_forge/tools/scan.py` — `from forge_bridge.server.protocol import ...` canonical builders

Plus `tests/test_switch_grade_mcp.py` — imports flipped and projekt-forge-specific tests removed (see deviation below).

## Pytest Before/After

| Metric | Wave A Baseline | Wave B Final |
|--------|----------------|--------------|
| Passed | 421 | 414 |
| xfailed | 3 | 3 |
| Failed | 0 | 0 |
| Errors | 0 | 0 |
| Duration | ~2.5s | ~2.5s |

Net delta: −7 tests, accounted for entirely by test_switch_grade_mcp.py cleanup (see below).

### test_switch_grade_mcp.py Cleanup (per user Option 1)

File went from 22 tests → 15 tests (−7 net).

**Deleted (7 tests — projekt-forge-specific fork internals):**
- `TestSwitchGradeInput.test_requires_alternative_path` — field absent from pip SwitchGradeInput
- `TestSwitchGradeInput.test_requires_alternative_start_frame` — field absent from pip
- `TestSwitchGradeInput.test_requires_alternative_duration` — field absent from pip
- `TestSwitchGradeInput.test_requires_entity_id` — field absent from pip
- `TestSwitchGradeUUIDPath.test_entity_id_used_in_openclip_path` — pip switch_grade has no entity_id
- `TestSwitchGradeUUIDPath.test_module_source_contains_switch_clip_suffix` — pip has no `_switch.clip` suffix
- `TestSwitchGradeOpenclipWriterWiring.*` (2 tests) — pip has no `forge_openclip_writer` / `ClipVersion` / `_write_clip_xml` wiring

**Rewritten (4 tests to use pip `media_path` field):**
- `TestSwitchGradeInput.test_requires_segment_name` (kept validation but switched fixture kwargs)
- `TestSwitchGradeInput.test_requires_sequence_name` (same)
- `TestSwitchGradeInput.test_valid_all_required` — now asserts `media_path` equality
- Added `TestSwitchGradeInput.test_requires_media_path` (replaces 4 deleted alternative_* / entity_id required-field tests)
- `TestSwitchGradeInputDefaults.test_reel_group_default` + `test_reel_default` — fixture switched to media_path
- `TestSwitchGradeBridgeCode._run_switch_grade` — removed `_write_openclip_server_side` patch, fixture switched to media_path

**Preserved (no rewrite needed — pip surface matches):**
- `TestQueryAlternativesInput.*` (3 tests)
- `TestQueryAlternativesAsync.test_is_async_callable`
- `TestSwitchGradeAsync.test_is_async_callable`
- `TestSwitchGradeBridgeCode.test_bridge_code_contains_smart_replace_media`
- `TestSwitchGradeBridgeCode.test_bridge_code_contains_create_reel`
- `TestSwitchGradeScratchReel.test_module_source_contains_create_reel`

## PKG-03 Grep Result

Command: `grep -rn "portofino\|assist-01\|ACM_" /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/`

Result (post-commit, after bytecode cache clean):

```
projekt_forge/seed/profiles/tier1.py:4: Paths follow the actual Flame pipeline storage layout on portofino.
projekt_forge/seed/profiles/tier1.py:14: SEED_HOSTNAME = "portofino"
```

**These are NOT PKG-03 regressions.** They live in `projekt_forge/seed/profiles/tier1.py` — a forge-specific seed profile that intentionally references the Flame pipeline's storage hostname. The Phase 4 PKG-03 scrub covered canonical forge-bridge content only; this seed data is a projekt-forge-specific development fixture and is on the D-08 PRESERVE list (part of `projekt_forge/seed/`).

The `bridge.py`, `tools/publish.py`, `tools/switch_grade.py`, `tools/timeline.py` (all deleted) are verified clean — deletion removed any canonical content that might have carried leaks.

## D-12 Call-Out (new research entry)

Added to `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/phases/05-import-rewiring/05-RESEARCH.md` (after D-10, before v1.0.1 BLOCKER VERDICT).

**Summary:** Flame hook scripts in `flame_hooks/forge_tools/**/scripts/*.py` bootstrap with `sys.path.insert(0, <scripts_dir>)`, where the scripts directory contains a sibling file `forge_bridge.py` (the in-Flame HTTP server). Inserting at position 0 makes that flat-module `forge_bridge.py` shadow the installed pip package `forge_bridge/` during pytest collection — any subsequent `from forge_bridge.tools.X import Y` resolves against the flat hook module, which has no `.tools` submodule, and collection errors.

Fix sites (17 total):
- 13 hook files: `flame_hooks/forge_tools/{forge_publish_shots, forge_publish_traffik, forge_batch_render (batch_render.py@31, batch_render_dialog.py@37, render_registration.py@34), forge_denoise@38, forge_ingest (ingest.py@45, ingest_dialog.py@18), forge_layout@62, forge_stream (2 sites@66+332), forge_switch_grade@34, forge_bridge/forge_llm_test@27, forge_rename@1319-subprocess-fstring}/scripts/*.py`
- 3 test helpers: `tests/{test_forge_stream.py@31, test_catalog_client_shared.py@38, test_ingest_dialog_catalog.py@71}`

Resolution: flip `sys.path.insert(0, scripts_dir)` to `sys.path.append(scripts_dir)`. Flame's own runtime still picks up the local hook module (Flame's path already prefixes the scripts dir ahead of site-packages); pytest now resolves against the pip package. Committed as `4d2b579` (fix commit) before the atomic RWR-02 commit.

Long-term safety net: Plan 05-04's `conftest.py` autouse fixture (`assert_forge_bridge_site_packages`) will fail-fast on any future regression with a clear message.

## Deviations from Plan

### Rule 3 — Blocking issue auto-fixed: hook sys.path collision (D-12)

**Found during:** Plan 05-02 initial pytest attempts after Wave A's rename.
**Issue:** pytest collection errored on `ModuleNotFoundError` / `AttributeError` because hook scripts with `sys.path.insert(0, ...)` shadowed the pip package.
**Fix:** 17-site `insert`→`append` flip (see D-12 above).
**Commit:** `4d2b579` in projekt-forge — separate from the RWR-02 atomic commit, as a precondition.

### Option 1 — projekt-forge-specific test classes deleted from test_switch_grade_mcp.py

**Approved by user.** −7 tests in the file that assert on fork-only SwitchGradeInput fields (`alternative_path`, `alternative_start_frame`, `alternative_duration`, `entity_id`) and fork-only internals (`_write_openclip_server_side`, `forge_openclip_writer`, `ClipVersion`/`_write_clip_xml`, `_switch.clip` naming). 4 tests rewritten to use pip's `media_path` field. Coverage of pip surface maintained and expanded (`test_requires_media_path` added). See "test_switch_grade_mcp.py Cleanup" above for the full list.

## Pre-Existing Issues (NOT fixed in this plan)

**Pytest default-collection pollution in projekt-forge from `flame_hooks/forge_tools/forge_bridge/scripts/forge_llm_test.py`.** That file matches the default pytest discovery pattern `*_test.py` AND runs `sys.exit(1)` at import time when Ollama is offline, which poisons any bare `pytest` invocation. Workaround applied in this plan: run `pytest tests/` with an explicit path argument. Long-term fix options (out of scope for 05-02): (a) rename the hook file so it no longer matches `*_test.py`, or (b) add `testpaths = ["tests"]` / `norecursedirs = ["flame_hooks"]` to projekt-forge's pytest config in pyproject.toml or pytest.ini. Deferred to a future projekt-forge housekeeping pass.

## Must-Haves Checklist

- [x] projekt-forge pyproject.toml declares `forge-bridge @ git+...@v1.0.1` in `[project] dependencies` (confirmed — `pip show forge-bridge` resolves to site-packages)
- [x] D-08 DELETE list executed: bridge.py, tools/publish.py, tools/switch_grade.py, tools/timeline.py all removed
- [x] projekt_forge/client/{__init__,async_client,sync_client}.py PRESERVED (D-09b branch-b)
- [x] projekt_forge/tools/{batch,project}.py PRESERVED (D-10 MOVE)
- [x] projekt_forge/server/protocol/ PRESERVED (D-09a proper-extension)
- [x] Canonical imports restored via pip: orchestrate.py → forge_bridge.bridge; catalog.py → forge_bridge.server.protocol lineage builders
- [x] Full projekt-forge test suite passes with pip-installed forge-bridge v1.0.1 (`pytest tests/` — 414 passed, 3 xfailed)
- [x] Atomic commit for RWR-02 (pip dep add + deletes + canonical import flips in 9856376)
- [x] D-12 precondition fix committed separately (4d2b579) with clear causal framing
- [x] PKG-03 regression check: canonical tree clean; only tier1.py seed profile references portofino (forge-specific dev data, not a leak)
- [x] D-12 entry appended to 05-RESEARCH.md

## Self-Check: PASSED

- **Files:** FOUND `.planning/phases/05-import-rewiring/05-02-SUMMARY.md`, FOUND `05-RESEARCH.md` (with new D-12 section), FOUND `STATE.md`
- **Commits in projekt-forge:** FOUND `4d2b579` (fix hooks), FOUND `9856376` (RWR-02 atomic)
- **Deletions in projekt_forge/:** 4/4 confirmed
- **Preservations in projekt_forge/:** 12/12 confirmed
- **pytest tests/:** 414 passed + 3 xfailed + 0 failed + 0 errors
- **Pip package resolution:** `forge_bridge.__file__` → site-packages path (verified via resume-inherited state)
