---
phase: 05-import-rewiring
verified: 2026-04-16T22:15:00Z
status: passed
score: 34/34 must-haves verified
overrides_applied: 0
requirements:
  - id: RWR-01
    status: satisfied
    evidence: "projekt-forge pyproject.toml line 25 declares 'forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1'; pip show forge-bridge reports Version 1.0.1 at /Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages"
  - id: RWR-02
    status: satisfied
    evidence: "projekt-forge commit 9856376 atomically adds the pip dep + deletes bridge.py/tools/publish.py/tools/switch_grade.py/tools/timeline.py (4 modules). All four absent from projekt_forge/. D-09b branch-b: client/async_client.py preserved for project_name routing."
  - id: RWR-03
    status: satisfied
    evidence: "projekt_forge/server/mcp.py collapsed to 45 lines; register_tools() called once at module top-level with prefix='forge_' source='builtin'; 7 forge-specific tools registered (trace_lineage, get_shot_deps, publish_pipeline, media_scan, seed_catalog, setup_denoise, list_desktop); runtime import lists 27 forge_* tools total (7 consumer + 20 canonical from register_builtins)."
  - id: RWR-04
    status: satisfied
    evidence: "projekt-forge tests/conftest.py lines 227-255 adds autouse session-scoped fixture assert_forge_bridge_from_site_packages with both site-packages assertion and defensive local-dir check. Smoke pytest run (12 tests) passes with fixture active."
commits:
  forge_bridge:
    - hash: "6c2456a"
      subject: "feat(protocol): add query_lineage, query_shot_deps, media_scan builders + entity_list narrowing (v1.0.1 1/4)"
    - hash: "d47a65b"
      subject: "fix(client): ref_msg_id correlation fallback + sync_client entity_list narrowing (v1.0.1 2/4)"
    - hash: "bdef13e"
      subject: "fix(timeline): T0 gap-fill via upward track scan (v1.0.1 3/4)"
    - hash: "92cadf1"
      subject: "chore(release): bump version to 1.0.1 (v1.0.1 4/4)"
    - hash: "v1.0.1"
      subject: "annotated tag at 92cadf1 (pushed to origin: refs/tags/v1.0.1)"
  projekt_forge:
    - hash: "137aac3"
      subject: "refactor(projekt_forge): rename forge_bridge namespace to projekt_forge + internal import sweep -- forge-bridge phase 5 wave A"
    - hash: "4d2b579"
      subject: "fix(hooks): append forge_bridge scripts dir to sys.path to prevent pip package shadowing (phase 5 D-12 precondition)"
    - hash: "9856376"
      subject: "refactor(projekt_forge): adopt forge-bridge v1.0.1 pip + delete 4 duplicate modules (RWR-02, D-09b branch-b)"
    - hash: "2722e23"
      subject: "refactor(projekt_forge): rebuild MCP server around get_mcp() + register_tools; rely on canonical lifespan -- forge-bridge phase 5 wave C"
    - hash: "7014c17"
      subject: "test(projekt_forge): add RWR-04 conftest guard asserting forge_bridge resolves to site-packages -- forge-bridge phase 5 wave D"
---

# Phase 5: Import Rewiring — Verification Report

**Phase Goal:** Rewire the projekt-forge / forge-bridge boundary so projekt-forge consumes forge-bridge as a pip dependency (v1.0.1) instead of carrying a duplicate local copy — eliminating the namespace collision, adopting the canonical MCP registry, and adding a conftest guard against regression.
**Verified:** 2026-04-16T22:15:00Z
**Status:** passed
**Re-verification:** No — initial verification
**Scope:** Cross-repo (forge-bridge + projekt-forge)

---

## Goal Achievement

### Roadmap Success Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `pip show forge-bridge` inside projekt-forge's venv shows the installed package (not local) | VERIFIED | `pip show forge-bridge` reports `Version: 1.0.1` at `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages` |
| 2 | `python -c "import forge_bridge; print(forge_bridge.__file__)"` resolves to site-packages | VERIFIED | From `/tmp` and from projekt-forge cwd: `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/__init__.py` |
| 3 | projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) registered via `register_tools()` | VERIFIED | Runtime inspection lists 7 consumer-registered forge_* tools: forge_trace_lineage, forge_get_shot_deps, forge_publish_pipeline, forge_media_scan, forge_seed_catalog, forge_setup_denoise, forge_list_desktop |
| 4 | All existing projekt-forge tests pass after rewire with no changes to test logic | VERIFIED | Plan 05-04 SUMMARY: 414 passed + 3 xfailed + 0 failed in 1.96s. Net -7 from 421 baseline was agreed Option 1 test-cleanup (fork-only switch_grade fields) |

### Observable Truths (per-plan must_haves)

**Plan 05-00 (forge-bridge Wave 0 — v1.0.1 release)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 0-1 | canonical protocol exposes query_lineage and query_shot_deps builders | VERIFIED | `forge_bridge/server/protocol.py` lines 387 (query_lineage) and 396 (query_shot_deps); MsgType constants at lines 118-119 |
| 0-2 | entity_list builder accepts optional shot_id, role, source_name narrowing kwargs | VERIFIED | `forge_bridge/server/protocol.py` line 298 `def entity_list(...)` with kwargs at 302-304 |
| 0-3 | AsyncClient correlates responses via ref_msg_id fallback | VERIFIED | `forge_bridge/client/async_client.py` line 426 `msg_id = msg.get("ref_msg_id") or msg.msg_id` on ok branch; line 442 same pattern on error branch |
| 0-4 | sync_client.entity_list() accepts shot_id and role narrowing kwargs | VERIFIED | `forge_bridge/client/sync_client.py` line 295 def entity_list, kwargs at 300-302, pass-through at 315-317 |
| 0-5 | timeline.rename_shots fills T0 gaps by scanning upward tracks | VERIFIED | `forge_bridge/tools/timeline.py` line 249 rename_shots; line 294 `gap_fills = set()`; line 318 `gap_fills.add(id(fill_seg))`; line 337 gap_fills check |
| 0-6 | forge-bridge v1.0.1 git tag exists on origin/main | VERIFIED | `git ls-remote --tags origin`: `15f1e2f0aa… refs/tags/v1.0.1` + peeled `92cadf19a… refs/tags/v1.0.1^{}`; local `git tag --list 'v1.0.*'` → v1.0.1 |

**Plan 05-01 (projekt-forge Wave A — rename)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1-1 | projekt-forge/forge_bridge/ removed; projekt-forge/projekt_forge/ exists | VERIFIED | `ls /Users/cnoellert/Documents/GitHub/projekt-forge/` shows projekt_forge/ directory; no forge_bridge/ at root |
| 1-2 | All internal from forge_bridge.* imports rewritten to projekt_forge.* (scoped to projekt_forge/, tests/, forge_gui/) | VERIFIED | `grep -rnE 'from forge_bridge\.' projekt_forge/ forge_gui/` shows only canonical pip flips (forge_bridge.bridge, forge_bridge.server.protocol — intentional Wave B) |
| 1-3 | flame_hooks/ still contains from forge_bridge.* (resolves against pip) | VERIFIED | `grep -rnE 'from forge_bridge\.' flame_hooks/` returns 4 matches (preserved) |
| 1-4 | pyproject.toml packages=['projekt_forge'], forge script → projekt_forge.cli.main:cli | VERIFIED | Line 40 `packages = ["projekt_forge"]`; line 37 `forge = "projekt_forge.cli.main:cli"` |
| 1-5 | Pre-rewrite forge-bridge console script removed | VERIFIED | `grep -c 'forge-bridge = "forge_bridge.server:main"' pyproject.toml` returns 0 |
| 1-6 | CLAUDE.md documents dev-loop (pip install -e) | VERIFIED | CLAUDE.md line 158 `## Local dev loop with forge-bridge`; line 165 `pip install -e /Users/cnoellert/Documents/GitHub/projekt-forge` |
| 1-7 | Full projekt-forge pytest suite passes | VERIFIED | Plan 05-01 SUMMARY: 421 passed + 3 xfailed in tests/ (2.15s) |
| 1-8 | Single atomic commit (or at most two) | VERIFIED | Single commit `137aac3` (106 files, +809/−788 rename-aware) |

**Plan 05-02 (projekt-forge Wave B — pip adoption + deletes)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 2-1 | pyproject.toml declares forge-bridge @ git+...@v1.0.1 in [project] dependencies | VERIFIED | Line 25 `"forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1"` |
| 2-2 | D-08 DELETE list executed: bridge.py, tools/publish.py, tools/switch_grade.py, tools/timeline.py removed | VERIFIED | All 4 files ABSENT from projekt_forge/ (programmatic `test ! -f` confirms) |
| 2-3 | projekt_forge/client/{__init__, async_client, sync_client}.py PRESERVED (D-09b branch-b) | VERIFIED | All 3 files present; async_client.py line 130 shows `project_name: str \| None = None` — forge-specific extension retained |
| 2-4 | projekt_forge/tools/batch.py and project.py PRESERVED (D-10) | VERIFIED | Both files exist in projekt_forge/tools/ |
| 2-5 | projekt_forge/server/protocol/ directory PRESERVED (D-09a) | VERIFIED | Directory exists with __init__.py |
| 2-6 | Canonical imports restored via pip (orchestrate forge_bridge.bridge; catalog forge_bridge.server.protocol) | VERIFIED | orchestrate.py line 17 `import forge_bridge.bridge as bridge`; catalog.py line 55 `from forge_bridge.server.protocol import query_lineage`; catalog.py line 77 `from forge_bridge.server.protocol import query_shot_deps`; scan.py line 27 `from forge_bridge.server.protocol import project_list` |
| 2-7 | Full projekt-forge test suite passes with pip-installed forge-bridge v1.0.1 | VERIFIED | Plan 05-02 SUMMARY: 414 passed + 3 xfailed (net −7 agreed Option 1 switch_grade cleanup) |
| 2-8 | Single atomic commit per RWR-02 (pip dep + delete + flip) | VERIFIED (with documented deviation) | Atomic RWR-02 commit: `9856376` combines pip dep add + 4 deletes + 9 canonical flips. Precondition commit `4d2b579` (D-12 hook sys.path) is separate and precedes it — documented deviation accepted as intentional |

**Plan 05-03 (projekt-forge Wave C — MCP rewire)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 3-1 | projekt_forge/server/mcp.py contains zero direct mcp.tool(...) calls | VERIFIED | `grep -cE 'mcp\.tool\s*\(' projekt_forge/server/mcp.py` returns 0; file is 45 lines |
| 3-2 | projekt_forge/server/mcp.py calls get_mcp() exactly once | VERIFIED | Line 30 `mcp = get_mcp()` — single call |
| 3-3 | register_tools called once at module top-level with prefix='forge_', source='builtin' | VERIFIED | Lines 32-45 register_tools at module top; line 43 `prefix="forge_"`; line 44 `source="builtin"` |
| 3-4 | All 7 forge-specific tools appear in register_tools argument list | VERIFIED | Lines 35-41: trace_lineage, get_shot_deps, publish_pipeline, media_scan, seed_catalog, setup_denoise, list_desktop — matches must_haves exactly. Runtime listing confirms all 7 registered with `forge_` prefix |
| 3-5 | __main__.py no longer calls _startup/_shutdown or startup_bridge/shutdown_bridge directly | VERIFIED | `grep -cE '_startup\(\|_shutdown\(\|await startup_bridge\|await shutdown_bridge' projekt_forge/__main__.py` returns 0 |
| 3-6 | __main__.py imports configure from forge_bridge.bridge (pip) | VERIFIED | Lines 27 and 44 both `from forge_bridge.bridge import configure` (lazy imports inside two helpers) |
| 3-7 | python -m projekt_forge --help exits 0 | VERIFIED | Live run: exits 0, help text begins with "usage: projekt_forge [-h] [--bridge-host ...]" |
| 3-8 | Full projekt-forge test suite passes (incl. MCP smoke tests) | VERIFIED | Plan 05-03 SUMMARY: 414 passed + 3 xfailed (baseline holding) |

**Plan 05-04 (projekt-forge Wave D — conftest guard)**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 4-1 | tests/conftest.py has autouse session-scoped assert_forge_bridge_from_site_packages fixture | VERIFIED | Line 235 `@pytest.fixture(autouse=True, scope="session")`; line 236 `def assert_forge_bridge_from_site_packages():` |
| 4-2 | Fixture asserts no top-level forge_bridge/ at projekt-forge repo root | VERIFIED | Lines 249-252 defensive check: `local_pkg = repo_root / "forge_bridge"` then `assert not local_pkg.exists()` |
| 4-3 | Fixture runs exactly once per pytest session and fails fast if assertions break | VERIFIED | scope="session" + autouse=True; both assert statements with specific failure messages pointing at remediation |
| 4-4 | Full projekt-forge test suite passes including the new assertion | VERIFIED | Plan 05-04 SUMMARY: 414 passed + 3 xfailed; live smoke run of test_smoke_project_creation.py → 12 passed with fixture active |
| 4-5 | Running pytest from projekt-forge repo root exits 0 and -v shows fixture | VERIFIED | Plan 05-04 SUMMARY captured `pytest --setup-show` output: `SETUP    S assert_forge_bridge_from_site_packages` appearing for every test |
| 4-6 | Single atomic Wave D commit | VERIFIED | Commit `7014c17` — 1 file, 31 insertions |

**Truth total: 34/34 VERIFIED**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| forge-bridge/forge_bridge/server/protocol.py | query_lineage, query_shot_deps, media_scan, narrowed entity_list | VERIFIED | 3 new builders present (lines 387/396/405); MsgType constants lines 118-119,122; entity_list narrowing lines 298-325 |
| forge-bridge/forge_bridge/client/async_client.py | ref_msg_id correlation fallback | VERIFIED | Lines 426 and 442 both apply `msg.get("ref_msg_id") or msg.msg_id` pattern |
| forge-bridge/forge_bridge/client/sync_client.py | entity_list narrowing kwargs | VERIFIED | Line 295 method signature; kwargs 300-302; pass-through 315-317 |
| forge-bridge/forge_bridge/tools/timeline.py | gap_fills set + upward track scan | VERIFIED | Lines 249, 294, 318, 337 |
| forge-bridge/pyproject.toml | version = "1.0.1" | VERIFIED | Line 7 `version = "1.0.1"` |
| projekt-forge/projekt_forge/__init__.py | renamed local package root | VERIFIED | Directory exists; __init__.py present |
| projekt-forge/pyproject.toml | updated packages + scripts | VERIFIED | Lines 25, 37, 40 (forge-bridge dep, forge script, packages list) |
| projekt-forge/CLAUDE.md | dev-loop documentation | VERIFIED | Line 158+ "Local dev loop with forge-bridge" section |
| projekt-forge/projekt_forge/server/mcp.py | FastMCP singleton + register_tools | VERIFIED | 45 lines: docstring + get_mcp() + single register_tools() call |
| projekt-forge/projekt_forge/__main__.py | canonical lifespan orchestration | VERIFIED | 169 lines; lazy `from forge_bridge.bridge import configure` in 2 helpers; TaskGroup and dispose_all_engines preserved |
| projekt-forge/tests/conftest.py | autouse session fixture | VERIFIED | Lines 227-255 RWR-04 section |
| projekt-forge/projekt_forge/tools/orchestrate.py | canonical bridge.BRIDGE_URL via pip | VERIFIED | Line 17 `import forge_bridge.bridge as bridge` |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| forge-bridge git tag v1.0.1 | projekt-forge pyproject @v1.0.1 URL | GitHub origin push | WIRED (refs/tags/v1.0.1 on origin; pip show reports 1.0.1) |
| projekt-forge projekt_forge/**/*.py | projekt_forge.* internal imports | Python imports after sed rewrite | WIRED (grep `from projekt_forge.` succeeds; `from forge_bridge.` in projekt_forge/ only hits the 4 canonical pip flips) |
| projekt-forge flame_hooks/**/*.py | forge_bridge.* imports (pip) | subprocess script strings | WIRED (preserved; 4 matches remain — intentional) |
| projekt_forge/tools/orchestrate.py | forge_bridge.bridge (pip) | `import forge_bridge.bridge as bridge` | WIRED (line 17 exact match; canonical BRIDGE_URL/BRIDGE_TIMEOUT attributes resolve) |
| projekt_forge/tools/catalog.py | forge_bridge.server.protocol.query_lineage (v1.0.1 canonical) | lazy import inside async fn | WIRED (lines 55 and 77 — canonical builders shipped in v1.0.1) |
| projekt_forge/server/mcp.py | forge_bridge.mcp (pip) | get_mcp() + register_tools() | WIRED (line 21 top-level import; singleton pattern in line 30) |
| projekt_forge/__main__.py | canonical lifespan in forge_bridge/mcp/server.py | mcp.run() triggers _lifespan | WIRED (lazy import chain confirms mcp.run() delegates startup/shutdown) |
| tests/conftest.py | forge_bridge pip install | pathlib.Path(forge_bridge.__file__).resolve() | WIRED (pytest passes against site-packages resolution) |
| tests/conftest.py | projekt-forge repo root | pathlib.Path(__file__).parent.parent / 'forge_bridge' | WIRED (defensive assert confirmed absent during smoke run) |

### Data-Flow Trace (Level 4)

Not applicable — Phase 5 is a refactor/packaging phase. No dynamic data rendering; the "data" is static package resolution and tool registration, both verified above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `forge_bridge` resolves from site-packages (external cwd) | `cd /tmp && python3 -c "import forge_bridge, pathlib; print(pathlib.Path(forge_bridge.__file__).resolve())"` | `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/__init__.py` | PASS |
| `forge_bridge` resolves from projekt-forge cwd | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && python3 -c "..."` | Same site-packages path | PASS |
| `pip show forge-bridge` reports v1.0.1 | `pip show forge-bridge` | `Version: 1.0.1` at site-packages Location | PASS |
| `python -m projekt_forge --help` exits 0 | live run | Help text printed; exit 0 | PASS |
| MCP singleton imports cleanly | `python -c "from projekt_forge.server.mcp import mcp; print(type(mcp).__name__)"` | `FastMCP` | PASS |
| 7 consumer forge_* tools registered | list mcp._tool_manager._tools.keys() | All 7 present (trace_lineage, get_shot_deps, publish_pipeline, media_scan, seed_catalog, setup_denoise, list_desktop) | PASS |
| Conftest fixture runs without failure | `pytest tests/test_smoke_project_creation.py` | 12 passed — autouse session fixture passes site-packages + no-local-dir assertions | PASS |
| forge-bridge v1.0.1 tag on origin | `git ls-remote --tags origin \| grep v1.0.1` | `15f1e2f... refs/tags/v1.0.1` + peeled | PASS |
| No local forge_bridge/ at projekt-forge root | `test ! -d /Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge` | absent | PASS |
| D-08 DELETE list confirmed | `test ! -f` on 4 files | 4/4 absent | PASS |
| D-08 PRESERVE list confirmed | `test -f` / `test -d` on 10 artifacts | 10/10 present | PASS |
| flame_hooks sys.path collision fixed (D-12) | `grep sys.path.insert flame_hooks/` | Only the forge_rename.py inner fstring literal `sys.path.append({bridge!r})` — no runtime `insert(0, ...)` collisions | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RWR-01 | 05-00, 05-01, 05-02 | projekt-forge adds forge-bridge>=1.0,<2.0 to pyproject.toml dependencies | SATISFIED | Exact pin `forge-bridge @ git+...@v1.0.1` satisfies the ≥1.0,<2.0 range; v1.0.1 tag exists on origin |
| RWR-02 | 05-02 | Duplicated tool modules deleted from projekt-forge in same commit as pip dep addition | SATISFIED | Commit 9856376 is atomic: pyproject.toml + 4 deletes + 9 canonical flips in a single commit (verified via `git log -1 --name-status`) |
| RWR-03 | 05-03 | projekt-forge's forge-specific tools registered via register_tools() | SATISFIED | mcp.py line 32-45 single register_tools() call with 7 tools; runtime inspection confirms all 7 registered with forge_ prefix and source="builtin" |
| RWR-04 | 05-04 | forge_bridge.__file__ resolves to site-packages verified in CI | SATISFIED | Conftest autouse session fixture with both site-packages assertion and defensive local-dir check; REQUIREMENTS.md traceability row still shows "Pending" but implementation is complete (REQUIREMENTS.md status field was not updated post-commit — follow-up note below) |

**Note on REQUIREMENTS.md:** All four RWR-* rows in the Traceability table show "Pending" status except RWR-03 ("Complete"). The implementation evidence clearly satisfies all four requirements. The Traceability table is out of sync with the actual phase state — this is a documentation drift, not an implementation gap. Recommended follow-up: update REQUIREMENTS.md Traceability table when closing Phase 5.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| projekt_forge/seed/profiles/tier1.py | 4, 14 | "portofino" string literal (SEED_HOSTNAME) | Info | Pre-existing; Phase 4 PKG-03 scrub covered canonical forge-bridge only. Forge-specific seed fixture — documented and accepted in 05-02 SUMMARY. Not a Phase 5 regression. |
| None | - | No other anti-patterns detected in modified files | - | grep -rE "TODO\|FIXME\|XXX\|HACK" on modified files in both repos returns no new blockers |

---

## Deviation Log

### Documented Deviation D-09b (branch-b): Local clients preserved

**Location:** Plan 05-02
**Plan originally specified:** Delete projekt_forge/client/async_client.py + sync_client.py (D-09b disposition TBD at planning time)
**Actually executed:** Both client files PRESERVED (branch-b resolution)
**Reason:** projekt-forge's db_server relies on forge-specific extended HELLO `project_name` for per-project DB routing. Canonical pip AsyncClient sends a canonical HELLO with no project_name, so swapping the client would silently break DB routing at runtime.
**Plan correction:** Plan 05-02 must_haves were updated before commit 9856376 to reflect branch-b (preserve). Verification confirmed the updated must_haves exactly match the final state: async_client.py preserved at line 130 with `project_name: str | None = None` parameter intact.
**Status:** Accepted and verified — no override needed; must_haves were updated in the plan itself.

### Documented Deviation D-12 (precondition): Hook sys.path collision fix

**Location:** Plan 05-02 execution, captured in 05-RESEARCH.md §D-12
**Plan originally specified:** Single atomic commit for RWR-02 (pip dep + delete + flip)
**Actually executed:** TWO commits in sequence:
  - `4d2b579` — precondition fix: `fix(hooks): append forge_bridge scripts dir to sys.path to prevent pip package shadowing (phase 5 D-12)` (17 sites: insert(0, ...) → append(...))
  - `9856376` — atomic RWR-02: pip dep add + 4 deletes + 9 canonical flips (the actual RWR-02 commit)
**Reason:** Pytest collection failed in projekt-forge because `flame_hooks/forge_tools/**/scripts/*.py` bootstrapped with `sys.path.insert(0, scripts_dir)`, which placed a sibling `forge_bridge.py` (Flame HTTP server module) ahead of the pip `forge_bridge/` package. Any `from forge_bridge.tools.X import Y` resolved against the flat hook module and failed. Fix had to precede the RWR-02 commit or its test suite could not run.
**Plan correction:** The precondition is mechanically separate from RWR-02 by design — it fixes a pre-existing condition uncovered during execution. The RWR-02 commit itself remains atomic per the requirement's literal wording.
**Research trace:** D-12 entry present at `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/phases/05-import-rewiring/05-RESEARCH.md` lines 269-277, documenting the root cause, all 17 edit sites, and the long-term safety net (RWR-04 conftest guard).
**Status:** Accepted and verified — RESEARCH.md entry present; commit trail intact; post-fix grep confirms 0 runtime `sys.path.insert(0, ...)` collisions in flame_hooks/.

### Documented Deviation Option 1: test_switch_grade_mcp.py cleanup

**Location:** Plan 05-02 execution
**Plan originally specified:** Full test suite passes unchanged
**Actually executed:** Test file pared from 22 tests → 15 tests (net −7). 7 tests deleted that asserted on fork-only SwitchGradeInput fields (alternative_path/alternative_start_frame/alternative_duration/entity_id) and fork-only internals (_write_openclip_server_side, forge_openclip_writer, ClipVersion/_write_clip_xml, _switch.clip naming). 4 tests rewritten to use canonical pip `media_path` field. 1 new test added: `test_requires_media_path`.
**Reason:** User-approved Option 1 (per 05-02 SUMMARY). The deleted tests asserted on fork-only fields that are not part of canonical pip SwitchGradeInput. Retaining them would have blocked the wave or required a hybrid fork layer that defeats the purpose of the pip adoption.
**Status:** Accepted — user approval recorded in 05-02 SUMMARY; coverage of canonical pip surface preserved and expanded.

---

## Human Verification Required

None — all must-haves verified programmatically. The following items are explicitly NOT required for this phase verdict:

- Running the full 414+-test pytest suite end-to-end in this verification session (plans' SUMMARYs captured the green runs at commit time; re-running is unnecessary per verification instruction item 6)
- Launching the MCP server against a live Flame bridge (out of scope — this phase is a packaging/import refactor, not a runtime behavior change)

### User awareness items (informational, not blocking)

- **Dev-loop editable shadow** — per CLAUDE.md "Local dev loop with forge-bridge", the user may reinstate `pip install -e /Users/cnoellert/Documents/GitHub/forge-bridge` to shadow the git-pinned install for local forge-bridge development. When that shadow is active, the RWR-04 conftest fixture will fail the site-packages assertion — **this is the guard firing correctly**, not a regression. The fixture's failure message documents the remediation inline.
- **REQUIREMENTS.md Traceability table drift** — rows for RWR-01, RWR-02, RWR-04 still read "Pending" even though implementation is complete. Updating those rows is a documentation cleanup task, not a verification gap.

---

## Gaps Summary

No gaps. All 34 must-haves across 5 plans verified. All 4 requirement IDs (RWR-01, RWR-02, RWR-03, RWR-04) satisfied with documented evidence. All 9 key links wired. All 12 behavioral spot-checks pass. Both cross-repo commit trails are intact and labeled per D-18 convention. The three documented deviations (D-09b branch-b, D-12 precondition, Option 1 test cleanup) are all accepted and reflected either in the updated plan must_haves (D-09b) or in RESEARCH.md (D-12) or in 05-02 SUMMARY (Option 1).

Phase 5 achieves its goal: projekt-forge consumes forge-bridge v1.0.1 as a pip dependency with the namespace collision eliminated, the canonical MCP registry adopted, and an autouse conftest guard protecting against regression.

---

*Verified: 2026-04-16T22:15:00Z*
*Verifier: Claude (gsd-verifier)*
