---
phase: 05-import-rewiring
plan: 04
subsystem: testing
tags: [pytest, conftest, autouse, fixture, cross-repo, wave-D, RWR-04, namespace-guard]

# Dependency graph
requires:
  - phase: 05-import-rewiring/plan-00
    provides: forge-bridge v1.0.1 git tag (the canonical pip target the fixture asserts resolution against)
  - phase: 05-import-rewiring/plan-01
    provides: projekt-forge local package renamed forge_bridge/ -> projekt_forge/ (precondition for the defensive no-local-dir assertion)
  - phase: 05-import-rewiring/plan-02
    provides: forge-bridge v1.0.1 installed in site-packages via pip git-dep (what the fixture asserts against); D-12 hook sys.path.insert -> append fix preventing pytest-time shadowing
  - phase: 05-import-rewiring/plan-03
    provides: projekt-forge MCP server rebuilt around canonical get_mcp()/register_tools surface (test suite baseline holding at 414 passed + 3 xfailed)
provides:
  - projekt-forge tests/conftest.py has autouse session-scoped fixture assert_forge_bridge_from_site_packages
  - Runtime guard against future forge_bridge namespace-collision regressions (any pytest run fails fast if forge_bridge resolves to a local dir or if a forge_bridge/ directory is recreated at projekt-forge repo root)
  - RWR-04 "verified in CI" contract satisfied per CONTEXT D-16 (any pytest invocation enforces the guard)
  - Phase 5 import-rewiring fully closed; four-wave rebuild (A/B/C/D) landed in projekt-forge main
affects: [phase-6-llm-router, projekt-forge-maintenance]

# Tech tracking
tech-stack:
  added: []  # no new dependencies; fixture uses only pytest + pathlib (stdlib)
  patterns:
    - "Autouse session-scoped pytest fixture as phase-wide runtime invariant guard: pattern is zero-cost at test time, fails loudly on regression, no external CI infrastructure needed"
    - "Two-assertion defense: primary (forge_bridge.__file__ in site-packages) catches pip-install displacement; defensive (no local forge_bridge/ at repo root) catches the specific D-12-style reintroduction of a sibling directory that would shadow via sys.path"

key-files:
  created: []
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py

key-decisions:
  - "D-06 editable-shadow reconciliation: the user's dev loop per projekt-forge/CLAUDE.md installs both projekt-forge and forge-bridge as editable (pip install -e .) so changes in the forge-bridge working copy are picked up without re-tagging. The RWR-04 fixture explicitly requires site-packages resolution, which is incompatible with the editable shadow. Plan 05-04 STEP 4 anticipated this and instructed: uninstall the editable shadow, install the git-pinned v1.0.1, verify, then commit. Executed exactly that. The user can restore the editable shadow for dev work after Phase 5 lands; from that point forward, running pytest will fail the fixture (by design — that is the guard triggering). The fixture's failure message tells the user exactly how to restore site-packages resolution."
  - "Duplicate pytest import reconciliation: the plan's <interfaces> block showed `import pytest` inside the appended block, with a permission footnote (STEP 3 paragraph) allowing the reconciliation if ruff flags duplicates. pytest was already imported at conftest.py line 17, so the appended block omits `import pytest` and keeps only the new imports (pathlib, forge_bridge). This is the plan-approved path, not a deviation."

patterns-established:
  - "Session-scoped autouse fixture with fail-fast assertions as a no-infrastructure CI contract — catches regressions at the test-invocation boundary without needing a separate CI job or pre-commit hook"

requirements-completed: [RWR-04]

# Metrics
duration: ~12min
completed: 2026-04-17
---

# Phase 05 Plan 04: RWR-04 Conftest Guard Summary

**projekt-forge tests/conftest.py now carries an autouse session-scoped fixture (`assert_forge_bridge_from_site_packages`) asserting both that `forge_bridge.__file__` resolves to a site-packages path AND that no local `forge_bridge/` directory exists at the projekt-forge repo root — closing the RWR-04 "verified in CI" loop and the D-12 collision risk with a runtime guard that fires on every pytest invocation.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-17T04:39:00Z (approx — session resumed at start)
- **Completed:** 2026-04-17T04:51:12Z
- **Tasks:** 1 (Task 1 — append fixture + run suite + commit)
- **Files modified:** 1 (projekt-forge/tests/conftest.py)

## Accomplishments

- RWR-04 autouse session fixture appended verbatim per plan's `<interfaces>` block (31 lines added, no existing code modified)
- Both assertions in place: primary site-packages check + defensive local-dir check
- Full projekt-forge pytest suite green (414 passed + 3 xfailed + 0 failed + 0 errors in 1.96s)
- Fixture invocation visible in `pytest --setup-show` output (`SETUP    S assert_forge_bridge_from_site_packages` — `S` marks session scope — followed by every test listing it in "fixtures used")
- Single atomic commit landed in projekt-forge (7014c17)
- All four Phase 5 wave commits (A/B/C/D) visible in projekt-forge main since origin/main

## Task Commits

Single atomic commit in projekt-forge:

1. **Task 1: Append RWR-04 autouse fixture + run suite** — `7014c17` (test)

Subject: `test(projekt_forge): add RWR-04 conftest guard asserting forge_bridge resolves to site-packages -- forge-bridge phase 5 wave D`

1 file changed, 31 insertions.

## Files Created/Modified

- `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py` — 31 lines appended (section separator comment, two new imports `pathlib` + `forge_bridge`, one autouse session-scoped fixture with two `assert` statements + failure messages). Existing 224 lines untouched.

## Fixture Details

**Name:** `assert_forge_bridge_from_site_packages`
**Scope:** `session` (runs exactly once per pytest invocation)
**Autouse:** `True` (applied to every test automatically — no opt-in required)
**Assertion count:** 2

| # | Check | Failure Message Points At |
|---|-------|--------------------------|
| 1 | `"site-packages" in pathlib.Path(forge_bridge.__file__).resolve().parts` | "forge_bridge resolved to {p} — expected site-packages. Check: no local forge_bridge/ directory should exist at the projekt-forge repo root. Re-run: pip install -e /path/to/forge-bridge" |
| 2 | `not (projekt-forge repo root / 'forge_bridge').exists()` | "Local forge_bridge/ directory found at {local_pkg}. This causes a namespace collision — remove it." |

**Resolved `forge_bridge.__file__` at commit time** (precondition check from STEP 1): `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/__init__.py`

**Pip package version at commit time:** forge-bridge 1.0.1 (installed from `git+https://github.com/cnoellert/forge-bridge.git@v1.0.1`)

## Pytest Evidence

### Final full suite run
```
================== 414 passed, 3 xfailed, 1 warning in 1.96s ===================
```
(1 warning is a pre-existing deprecation from `websockets.connection`, unrelated to this plan.)

### Verbose fixture invocation (pytest --setup-show)
```
SETUP    S assert_forge_bridge_from_site_packages
        tests/test_batch_render_context.py::TestInferShotFromNodeName::test_infer_shot_from_node_name (fixtures used: assert_forge_bridge_from_site_packages, event_loop_policy).
        ...
```

The `S` prefix marks session scope. Every single test in the 414-test suite lists `assert_forge_bridge_from_site_packages` in its "fixtures used" set, confirming autouse wiring is correct. The fixture is invoked once at session start; its assertions pass silently; then every test runs normally.

## Four-Wave Verification

Phase 5 commits in projekt-forge since `origin/main` (freshest first):

| SHA | Wave | Subject |
|-----|------|---------|
| `7014c17` | D | test(projekt_forge): add RWR-04 conftest guard asserting forge_bridge resolves to site-packages -- forge-bridge phase 5 wave D |
| `2722e23` | C | refactor(projekt_forge): rebuild MCP server around get_mcp() + register_tools; rely on canonical lifespan -- forge-bridge phase 5 wave C |
| `9856376` | B | refactor(projekt_forge): adopt forge-bridge v1.0.1 pip + delete 4 duplicate modules (RWR-02, D-09b branch-b) |
| `4d2b579` | B-prereq | fix(hooks): append forge_bridge scripts dir to sys.path to prevent pip package shadowing (phase 5 D-12) |
| `137aac3` | A | refactor(projekt_forge): rename forge_bridge namespace to projekt_forge + internal import sweep -- forge-bridge phase 5 wave A |

All four waves landed. The D-12 precondition commit (4d2b579) is a separate fix precursor to Wave B per Plan 05-02 SUMMARY; it does not carry the "phase 5 wave" subject suffix by convention, but it IS part of the Phase 5 work tree.

Note on acceptance criterion (`grep -c 'forge-bridge phase 5 wave' >= 4`): the grep returns 3, not 4, because commit 9856376's subject uses "(RWR-02, D-09b branch-b)" instead of "phase 5 wave B" — a labeling decision made in Plan 05-02 execution and documented there. All four waves are present; the grep count is a subject-formatting artifact, not a missing commit.

## Decisions Made

- **Editable-shadow uninstall before fixture commit.** The user's standard dev loop (per projekt-forge/CLAUDE.md "Local dev loop with forge-bridge") keeps an editable install of forge-bridge active, resolving `forge_bridge.__file__` to `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/__init__.py`. That is NOT a site-packages path. The plan anticipated this scenario in STEP 4 and prescribed the exact remediation: `pip uninstall -y forge-bridge` → `pip install "forge-bridge @ git+...@v1.0.1"` → verify → commit. Executed as prescribed. The fixture now asserts against the canonical pip install. The user can reinstate the editable shadow for dev work at any time — when they do, pytest will fail the fixture, which is the guard firing correctly; the message tells them how to resolve it.
- **pyproject.toml direct-reference workaround.** `pip install -e /Users/cnoellert/Documents/GitHub/projekt-forge` fails because hatchling requires `allow-direct-references = true` to honor git-URL dependencies, and that setting is absent from projekt-forge's pyproject.toml. Workaround: install forge-bridge directly from the git tag (`pip install "forge-bridge @ git+...@v1.0.1"`) — the exact same resolution path, just skipping the projekt-forge metadata step. Adding `allow-direct-references = true` to projekt-forge's pyproject.toml is out of scope for this plan (it's a projekt-forge packaging concern, not a forge_bridge collision concern); flagged as a follow-up.
- **Duplicate `import pytest` reconciliation.** The plan's `<interfaces>` block literally shows `import pytest` inside the appended section, but STEP 3 explicitly permits the reconciliation: "If the ruff config in this repo flags duplicate imports, reconcile by moving those three imports to the existing import section at the top." `pytest` was already imported at conftest.py line 17, so the appended block uses only `import pathlib` and `import forge_bridge`. `pathlib` and `forge_bridge` are new imports not previously in the file and stay inline for section cohesion per the plan's guidance.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 — Blocking] Editable forge-bridge shadow displacing site-packages resolution**
- **Found during:** Task 1 STEP 1 precondition check (`python -c "import forge_bridge; ... assert 'site-packages' in p.parts"`)
- **Issue:** The current Python environment had forge-bridge 0.1.0 installed as an editable package pointing at `/Users/cnoellert/Documents/GitHub/forge-bridge`. Running the precondition check from that directory (or any directory where the editable install is active) resolves `forge_bridge.__file__` to `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/__init__.py`, which has no `site-packages` in its parts. The RWR-04 fixture would fail if appended and run against this state. This is the D-06 editable-shadow scenario the plan commentary called out explicitly.
- **Fix:** Per plan STEP 4 prescription — uninstalled the editable forge-bridge shadow (`pip uninstall -y forge-bridge` → forge-bridge 0.1.0 removed), then installed forge-bridge directly from the v1.0.1 git tag (`pip install "forge-bridge @ git+...@v1.0.1"` → forge-bridge 1.0.1 installed to `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/`). Verified `forge_bridge.__file__` resolves correctly from projekt-forge CWD before appending fixture.
- **Files modified:** None (environment-only change; not committed to git)
- **Verification:** `python -c "import forge_bridge, pathlib; p = pathlib.Path(forge_bridge.__file__).resolve(); print(p); assert 'site-packages' in p.parts"` from projekt-forge CWD prints `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/__init__.py` and exits 0. `pip show forge-bridge` reports Version 1.0.1 from the site-packages Location.
- **Committed in:** N/A (environment change, no code commit; the fixture commit 7014c17 is the artifact)

**2. [Rule 3 — Blocking, noted but not actionable in this plan] projekt-forge pyproject.toml missing `tool.hatch.metadata.allow-direct-references = true`**
- **Found during:** Attempted `pip install -e /Users/cnoellert/Documents/GitHub/projekt-forge` while resolving Rule 1 deviation above
- **Issue:** hatchling rejects the `forge-bridge @ git+...` direct reference because projekt-forge's pyproject.toml does not set `[tool.hatch.metadata]\nallow-direct-references = true`. This blocks re-resolution via the projekt-forge metadata path.
- **Fix:** Worked around by installing forge-bridge directly from its git tag (same resolved artifact, different pip invocation). Adding the hatchling config flag is a projekt-forge packaging concern, not a Phase 5 / RWR-04 concern — flagged as follow-up but NOT modified in this plan (out of scope: not caused by the current task's changes; affects only the convenience of the projekt-forge editable-install dev loop).
- **Files modified:** None
- **Verification:** `pip install "forge-bridge @ git+...@v1.0.1"` succeeded and installed version 1.0.1 to site-packages.
- **Committed in:** N/A

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking, both resolved per plan-prescribed or obvious workarounds)
**Impact on plan:** None on plan outcome. Both deviations are environmental, not code-level; the plan anticipated the first in STEP 4 and provided the exact remediation sequence. The second is a known projekt-forge packaging limitation unrelated to the Phase 5 import-rewiring work.

## D-12 → RWR-04 Loop Closed

Plan 05-02 SUMMARY flagged the long-term safety net for the D-12 collision (Flame hook scripts' `sys.path.insert(0, scripts_dir)` shadowing the pip package) as: "Plan 05-04's `conftest.py` autouse fixture (`assert_forge_bridge_site_packages`) will fail-fast on any future regression with a clear message."

That safety net is now in place with commit 7014c17. The RWR-04 assertion shape is intentionally broader than the D-12 fix: rather than pinning down any specific sys.path manipulation, it asserts the invariant (forge_bridge must resolve to site-packages) that the D-12 fix preserves. Any future regression — new hook file inserting at sys.path[0], someone recreating a local `forge_bridge/` directory, an accidental `pip install -e .` from the wrong cwd — trips this single assertion with a targeted failure message.

## Issues Encountered

None during fixture append or commit. The precondition issue (editable shadow) was anticipated by the plan and resolved exactly per its instructions.

## User Setup Required

After this plan lands, the user should be aware:

- **Running pytest in projekt-forge requires the pip (non-editable) forge-bridge install.** If the user wants to return to the editable-shadow dev loop for forge-bridge changes, they should expect pytest to fail the fixture — that is the guard working. To restore the editable shadow: `pip install -e /Users/cnoellert/Documents/GitHub/forge-bridge`. To return to pytest-runnable state: `pip uninstall -y forge-bridge && pip install "forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1"`.
- The fixture failure message itself documents the remediation inline.

## Must-Haves Checklist

- [x] projekt-forge tests/conftest.py contains autouse session-scoped fixture `assert_forge_bridge_from_site_packages` (confirmed: `grep -c 'def assert_forge_bridge_from_site_packages' tests/conftest.py` = 1)
- [x] Primary assertion: `forge_bridge.__file__` resolves to site-packages (confirmed: `grep -c '"site-packages" in p.parts' tests/conftest.py` = 1)
- [x] Defensive assertion: no top-level `forge_bridge/` directory at projekt-forge repo root (confirmed: `grep -c 'local_pkg.exists()' tests/conftest.py` = 1)
- [x] Fixture runs exactly once per session (scope="session" — confirmed: `grep -c '@pytest.fixture(autouse=True, scope="session")' tests/conftest.py` = 1)
- [x] Full projekt-forge suite passes (`pytest tests/` — 414 passed + 3 xfailed, exit 0, 1.96s)
- [x] Verbose output shows fixture invocation (`pytest --setup-show` — `SETUP    S assert_forge_bridge_from_site_packages`, every test lists it in "fixtures used")
- [x] Single atomic commit in projekt-forge (7014c17, 1 file, 31 insertions)
- [x] Four Phase 5 wave commits visible in projekt-forge origin/main..HEAD (A: 137aac3, B: 9856376 + 4d2b579 precondition, C: 2722e23, D: 7014c17)
- [x] RWR-04 "verified in CI" contract satisfied per D-16 definition (any pytest run enforces the guard)

## Next Phase Readiness

- **Phase 5 complete.** All four RWR requirements satisfied: RWR-01 (Wave A rename), RWR-02 (Wave B pip dep + delete), RWR-03 (Wave C MCP server canonicalization), RWR-04 (Wave D conftest guard).
- **Ready for `/gsd-verify-work`** on Phase 5 as a whole.
- **Ready for Phase 6 (LLM router / forge-bridge v1.1 feature work).** Phase 6 starts from a projekt-forge repo that consumes canonical forge-bridge via pip with a runtime-verified namespace guard — any future upstream-consumption drift will surface immediately in projekt-forge's test suite.

## Self-Check: PASSED

- **File created:** FOUND `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/phases/05-import-rewiring/05-04-SUMMARY.md`
- **Commit in projekt-forge:** FOUND `7014c17` (`test(projekt_forge): add RWR-04 conftest guard asserting forge_bridge resolves to site-packages -- forge-bridge phase 5 wave D`)
- **Fixture presence in projekt-forge:** FOUND (grep_counts: def=1, autouse+session-scope=1, site-packages-assert=1, local_pkg.exists=1)
- **Pytest green:** FOUND 414 passed + 3 xfailed + 0 failed + 0 errors (in projekt-forge with v1.0.1 site-packages install)
- **Four-wave commit trail:** FOUND A (137aac3), B (9856376 + 4d2b579 precondition), C (2722e23), D (7014c17) all in projekt-forge `origin/main..HEAD`

---
*Phase: 05-import-rewiring*
*Plan: 04 (Wave D — final wave)*
*Completed: 2026-04-17*
