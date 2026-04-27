---
status: complete
phase: 16-fb-d-chat-endpoint
plan: 07
plan_name: "FB-D SEED planting + post-rename test cleanup"
subsystem: planning
tags: [seeds, fb-d, deferred-work, test-cleanup, scope-extension, ui]
updated: 2026-04-27T19:13:10Z

# Dependency graph
requires:
  - phase: 16-fb-d-chat-endpoint
    plan: 04
    provides: "D-decisions D-01/D-03/D-04/D-05/D-06/D-14a — verbatim source for SEED content"
  - phase: 16-fb-d-chat-endpoint
    plan: 05
    provides: "stub.html deletion + ui_chat_stub_handler rename — the orphan-creating event this plan cleans up"
  - phase: 16-fb-d-chat-endpoint
    plan: 06
    provides: "integration-test pattern (Wave 3) confirming live panel works end-to-end before final cleanup"
provides:
  - "5 SEED files documenting FB-D's deferred ideas (D-01/D-04/D-05/D-06/D-03+D-14a) and their v1.5+ migration shapes"
  - "Post-rename guard test (test_ui_chat_handler_renders_panel_template) protecting against stub re-introduction"
  - "Wheel-package template parametrize list updated to reflect chat/panel.html (the live template) instead of the deleted chat/stub.html"
affects:
  - "v1.5 milestone planning — when SEED-AUTH-V1.5 lands, two paired SEEDs (CLOUD-CALLER, PERSIST-HISTORY) become unblocked"
  - "Phase 16 close gate — only outstanding work item is CHAT-04 D-12 D-36 fresh-operator artist UAT (operator activity, not coded test)"

# Tech tracking
tech-stack:
  added: []   # docs-only + test cleanup; zero new dependencies
  patterns:
    - "SEED-planting pattern (established in Phase 15 plan 15-10): topic-specific markdown files in .planning/seeds/ with trigger / v1.4-baseline / v1.5+-migration-shape / cross-refs / open-questions sections — re-applied here for FB-D's 5 deferred decisions."
    - "Post-rename guard with negative assertions: when an in-place rename retires an old surface (stub -> panel), add a guard test that asserts BOTH the new surface is present AND the old surface's identifying strings are absent. Makes regression-via-restore impossible without explicit test breakage."

key-files:
  created:
    - ".planning/seeds/SEED-CHAT-STREAMING-V1.4.x.md"
    - ".planning/seeds/SEED-CHAT-TOOL-ALLOWLIST-V1.5.md"
    - ".planning/seeds/SEED-CHAT-CLOUD-CALLER-V1.5.md"
    - ".planning/seeds/SEED-CHAT-PERSIST-HISTORY-V1.5+.md"
    - ".planning/seeds/SEED-CHAT-PARTIAL-OUTPUT-V1.5.md"
  modified:
    - "tests/console/test_chat_handler.py"
    - "tests/test_ui_wheel_package.py"
  deleted:
    - "tests/test_ui_chat_stub.py"

key-decisions:
  - "Followed the plan's verbatim SEED content spec exactly — no editorial drift from the planner's intent. Each SEED is 59-83 lines (within the planner's 40-150 line budget)."
  - "Added the optional post-rename guard test (test_ui_chat_handler_renders_panel_template) the plan recommended — it provides a permanent contract that /ui/chat renders the live panel and cannot silently regress to the stub. Replaces the 5 retired stub-regression tests with a single forward-looking guard."
  - "Accepted the orchestrator-mandated scope extension (Task 3, test_ui_wheel_package.py swap) as a cohesive third atomic commit. Both orphan cleanups (test_ui_chat_stub.py retirement + test_ui_wheel_package.py template swap) belong to the same theme: stub.html is gone, panel.html replaces it."

patterns-established:
  - "Same-theme orchestrator scope extension: when planning surfaces an unanticipated second orphan from the same root cause (stub.html deletion in Wave 3 producing TWO failing tests, only one of which the plan author saw), execute it as a separate atomic commit in the same plan rather than spawning a follow-up plan. Document explicitly in SUMMARY under a Scope Extensions section."
  - "Negative-assertion guard pattern (re-stated): assert presence of the new surface AND absence of the deleted surface's identifying strings in the same test. Three-line additions to existing fixture-backed tests are cheaper than a separate file and reuse mock setup."

requirements-completed: []   # SEED planting + cleanup is meta-work; the v1.4 requirement set (CHAT-01..05) was fully resolved by plans 16-04..16-06

# Metrics
duration: ~10m
completed: 2026-04-27
tasks: 3   # 2 plan-prescribed + 1 orchestrator-mandated scope extension
files_created: 5
files_modified: 2
files_deleted: 1
---

# Phase 16 Plan 07: FB-D SEED Planting + Post-Rename Test Cleanup Summary

**Planted 5 forward-looking SEEDs capturing FB-D's deferred decisions (D-01/D-03/D-04/D-05/D-06/D-14a) with their v1.5+ migration shapes, retired one orphan stub-regression test file, swapped the deleted stub.html for the live panel.html in the wheel-package template parametrize list (orchestrator-mandated scope extension), and added a single post-rename guard test that makes a future restore of the stub impossible without explicit test breakage. Phase 16 is now structurally complete; the only outstanding item is the CHAT-04 D-12 D-36 fresh-operator artist UAT (operator activity, not a coded test).**

## What Shipped

| Artifact | Type | Key contract |
| -------- | ---- | ------------ |
| `.planning/seeds/SEED-CHAT-STREAMING-V1.4.x.md` | created | D-01 forward path — SSE / WebSocket streaming for chat responses; activates after CHAT-04 artist UAT if "spinner runs too long" feedback surfaces. 59 lines. |
| `.planning/seeds/SEED-CHAT-TOOL-ALLOWLIST-V1.5.md` | created | D-04 forward path — caller-specified `tool_allowlist: list[str] \| None` request field for browse-only / mutation-restricted sessions. 65 lines. |
| `.planning/seeds/SEED-CHAT-CLOUD-CALLER-V1.5.md` | created | D-05 forward path — opt-in `sensitive=False` cloud (Anthropic) chat path; cross-references SEED-AUTH-V1.5 as hard prerequisite (caller identity → cost attribution). 68 lines. |
| `.planning/seeds/SEED-CHAT-PERSIST-HISTORY-V1.5+.md` | created | D-06 forward path — server-side per-user `chat_session` entity with full CRUD MCP/HTTP surface; cross-references SEED-AUTH-V1.5 + SEED-MESSAGE-PRUNING-V1.5. 60 lines. |
| `.planning/seeds/SEED-CHAT-PARTIAL-OUTPUT-V1.5.md` | created | D-03 / D-14a forward path — `return_history: bool = False` kwarg on FB-C's `complete_with_tools()` for partial-state surfacing on cap-fire. 83 lines. |
| `tests/test_ui_chat_stub.py` | deleted | Entire file was stub-regression: 5 tests, 3 of which asserted on deleted stub copy ("launches in Phase 12", chip-links, chat-stub-card class). Plan 16-05 SUMMARY explicitly deferred retirement to this plan. |
| `tests/console/test_chat_handler.py` | modified | Appended `test_ui_chat_handler_renders_panel_template` (the optional post-rename guard the plan recommended). Negative-assertion pattern: asserts `x-data="chatPanel()"` is present AND `"launches in Phase 12"` / `"chat-stub-card"` are absent. |
| `tests/test_ui_wheel_package.py` | modified | Parametrize entry `chat/stub.html` → `chat/panel.html` (orchestrator-mandated Task 3). Swap reflects the post-Wave-3 reality. |

## Performance

- **Duration:** ~10 minutes (3 atomic commits)
- **Tasks:** 3/3 complete (2 plan-prescribed + 1 orchestrator scope extension)
- **Test impact:** baseline 4 failed / 729 passed → final 0 failed / 729 passed, 106 skipped (full repo)

## Task Commits

| # | Type | Hash | Message |
| - | ---- | ---- | ------- |
| 1 | docs | `51760c6` | docs(16-07): plant 5 FB-D SEEDs for v1.4.x / v1.5+ migration paths |
| 2 | test | `57a3243` | test(16-07): retire orphan ui_chat_stub_handler tests, add post-rename guard |
| 3 | test | `ad0577d` | test(16-07): replace stub.html with panel.html in wheel-package template list (orphan cleanup) |

Plan metadata commit (this SUMMARY): forthcoming as a separate atomic commit.

## Scope Extensions

**Orchestrator-mandated Task 3 — `test_ui_wheel_package.py` template swap.**

The plan as written modified two test surfaces: 5 SEED files + `tests/test_ui_chat_stub.py`. After Wave 3 deleted `forge_bridge/console/templates/chat/stub.html`, a SECOND orphan failure surfaced that the plan author didn't anticipate:

```
tests/test_ui_wheel_package.py::test_wheel_contains_all_phase_10_templates[forge_bridge/console/templates/chat/stub.html]
AssertionError: template forge_bridge/console/templates/chat/stub.html MISSING from wheel.
```

The orchestrator added a third task to this plan's execution: swap `chat/stub.html` for `chat/panel.html` in the parametrized templates list at `tests/test_ui_wheel_package.py:107`. Implemented as a separate atomic commit (`ad0577d`) so the per-task atomicity discipline is preserved. Both orphan cleanups belong to the same theme: stub.html is gone, panel.html is the new live template.

No further scope creep — strictly the one swap.

## Decisions Made

1. **Followed the plan's verbatim SEED content exactly.** The plan author authored the full SEED file contents inline; I reproduced them byte-for-byte rather than re-writing. This is the correct posture for SEED planting — the planner's framing is the authoritative voice, the executor is the typist. Each SEED came in within the 40-150 line budget (59-83 lines actual).
2. **Added the optional post-rename guard test the plan recommended.** Rather than skip the optional sub-step, I added `test_ui_chat_handler_renders_panel_template` to `tests/console/test_chat_handler.py`. Reuses the existing `chat_client` fixture (zero fixture duplication), provides a permanent regression contract, replaces 5 retired tests with 1 forward-looking guard.
3. **Three atomic commits, not two.** The orchestrator's Task 3 was a real cleanup of the same theme but a separate file with separate semantics — a wheel-package contract test rather than a stub-regression test. Bundling it into commit 2 would have produced a less-readable history; a third atomic commit is the right grain.

## Deviations from Plan

### Auto-fixed Issues

**None.** The plan executed exactly as written for Tasks 1 and 2.

### Orchestrator-Driven Scope Extension

**Task 3 (test_ui_wheel_package.py template swap)** — Not a deviation in the auto-fix sense; the orchestrator extended the plan's scope before execution started. Documented above under "Scope Extensions." Implemented as the third atomic commit (`ad0577d`).

## Issues Encountered

None. Baseline pytest run before changes confirmed exactly the 4 failures the plan + orchestrator scope extension targeted (`test_ui_chat_stub_body_copy`, `test_ui_chat_stub_chip_links`, `test_ui_chat_stub_uses_chat_stub_card_class`, `test_wheel_contains_all_phase_10_templates[chat/stub.html]`). All 4 resolved by the three commits above.

## Acceptance Criteria — Status

### Task 1 (5 SEED files)
- All 5 files exist in `.planning/seeds/` ✓
- `grep -c '^# SEED:' .planning/seeds/SEED-CHAT-*.md` returns `5` ✓
- `grep -l "SEED-AUTH-V1.5" .planning/seeds/SEED-CHAT-CLOUD-CALLER-V1.5.md` returns the file path ✓
- `grep -l "SEED-AUTH-V1.5" .planning/seeds/SEED-CHAT-PERSIST-HISTORY-V1.5+.md` returns the file path ✓
- All 5 files contain their required content keywords (SSE, tool_allowlist, sensitive=False, auth, return_history) ✓
- Line counts within the 40-150 range: 59 / 65 / 68 / 60 / 83 ✓

### Task 2 (orphan sweep + retire dead tests)
- `grep -rln "ui_chat_stub_handler" tests/ forge_bridge/` clean (after exclusions) ✓
- `grep -rln "chat/stub.html" tests/ forge_bridge/` clean (after exclusions) ✓
- `grep -rln "launches in Phase 12" tests/ forge_bridge/` clean — only the negative assertion in the new guard test references the string ✓
- `grep -c 'href="/ui/chat"' forge_bridge/console/templates/shell.html` returns `1` ✓
- `pytest tests/` exits 0 ✓

### Task 3 (orchestrator scope extension)
- `tests/test_ui_wheel_package.py` parametrize list: `chat/stub.html` removed, `chat/panel.html` added ✓
- `pytest tests/test_ui_wheel_package.py` returns 22 passed ✓

### Plan-level
- All 5 SEED files planted with consistent format and cross-references ✓
- Orphan `ui_chat_stub_handler` / `chat/stub.html` / "launches in Phase 12" references swept from production paths ✓
- shell.html chat-nav link verified intact ✓
- Optional post-rename guard test added ✓
- Full repo test suite: **729 passed, 106 skipped, 0 failed** ✓

## Threat Surface Verification

The plan listed 3 threat IDs (T-16-07-01..03). Disposition status after implementation:

| Threat ID | Category | Disposition | Mitigation Verified |
| --------- | -------- | ----------- | ------------------- |
| T-16-07-01 (T) | Tampering — silent scope drop | mitigate | 5 SEED files planted with cross-reference graph (CLOUD-CALLER → AUTH, PERSIST-HISTORY → AUTH, PERSIST-HISTORY → MESSAGE-PRUNING). Future v1.5 milestone planners can walk the graph to discover all FB-D-deferred work items. |
| T-16-07-02 (I) | Information disclosure | accept | Deleted stub HTML contained only "launches in Phase 12" copy + chip-row — no sensitive data. Removal is purely cosmetic + correctness. |
| T-16-07-03 (R) | Repudiation — nav-link drift | mitigate | shell.html nav-link to /ui/chat verified at line 12 (`grep -c 'href="/ui/chat"' = 1`). The post-rename guard test additionally enforces /ui/chat returns HTTP 200 with the live panel — any future shell.html refactor that breaks the nav-link will fail this test. |

No new threat surfaces introduced.

## Phase 16 Close Posture

This plan completes Wave 5 (the final wave) of Phase 16. The phase is structurally complete:

- **CHAT-01** (rate limiting) — shipped in Wave 2
- **CHAT-02** (125s timeout) — shipped in Wave 2
- **CHAT-03** (sanitization boundary) — shipped in Wave 2 + verified by integration tests in Wave 3
- **CHAT-04** (Web UI chat panel) — shipped in Wave 3 (live panel.html); dogfood UAT confirmed; D-12 / D-36 fresh-operator artist UAT remains as the only outstanding gate
- **CHAT-05** (external-consumer parity with projekt-forge Flame hooks) — verified in Wave 4 integration tests

The CHAT-04 D-12 / D-36 fresh-operator artist UAT is an operator activity (run manually on assist-01 with a non-developer artist), NOT a coded test. Failure would trigger a Phase 16.1 remediation analogous to Phase 10.1.

## Consumers (Forward References)

- **v1.5 milestone open:** SEED-CHAT-CLOUD-CALLER-V1.5 and SEED-CHAT-PERSIST-HISTORY-V1.5+ both block on SEED-AUTH-V1.5 — when v1.5 auth phase opens, walk those two SEEDs into the auth phase's downstream-effects table.
- **v1.4.x patch consideration:** SEED-CHAT-STREAMING-V1.4.x activates only after CHAT-04 artist UAT — if the artist debrief surfaces "spinner runs too long" feedback, this SEED is the v1.4.x scope source.
- **FB-C extension (when triggered):** SEED-CHAT-PARTIAL-OUTPUT-V1.5 requires a two-step migration (FB-C `return_history` kwarg, then FB-D handler change). Both steps wait for a v1.5 consumer to ask for partial-state UX.

## Self-Check: PASSED

- `.planning/seeds/SEED-CHAT-STREAMING-V1.4.x.md` exists ✓
- `.planning/seeds/SEED-CHAT-TOOL-ALLOWLIST-V1.5.md` exists ✓
- `.planning/seeds/SEED-CHAT-CLOUD-CALLER-V1.5.md` exists ✓
- `.planning/seeds/SEED-CHAT-PERSIST-HISTORY-V1.5+.md` exists ✓
- `.planning/seeds/SEED-CHAT-PARTIAL-OUTPUT-V1.5.md` exists ✓
- `tests/test_ui_chat_stub.py` does NOT exist ✓
- `tests/console/test_chat_handler.py` contains `test_ui_chat_handler_renders_panel_template` ✓
- `tests/test_ui_wheel_package.py` parametrize list contains `chat/panel.html` and NOT `chat/stub.html` ✓
- Commits `51760c6`, `57a3243`, `ad0577d` all present in `git log --oneline` ✓
- `pytest tests/` → 729 passed, 106 skipped, 0 failed ✓
- shell.html nav-link to /ui/chat verified intact (count=1) ✓

---
*Phase: 16-fb-d-chat-endpoint*
*Plan: 07*
*Completed: 2026-04-27*
