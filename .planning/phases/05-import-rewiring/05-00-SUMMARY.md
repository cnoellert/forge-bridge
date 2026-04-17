---
phase: 05-import-rewiring
plan: 00
subsystem: api
tags: [protocol, websocket, release, pip, v1.0.1]

# Dependency graph
requires:
  - phase: 04-api-surface-hardening
    provides: Stable forge-bridge API surface to patch on top of
provides:
  - query_lineage, query_shot_deps, media_scan protocol builders
  - entity_list narrowing kwargs (shot_id, role, source_name)
  - ref_msg_id correlation fallback in async_client._handle_message
  - sync_client.entity_list narrowing kwargs passthrough
  - timeline.rename_shots T0 gap-fill via upward track scan
  - forge-bridge v1.0.1 pip-installable release tag on origin
affects: [05-01, 05-02, 05-03, 05-04, projekt-forge-phase-5-wave-B]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyword-only narrowing kwargs on protocol builders (backward-compatible extension)"
    - "ref_msg_id-first correlation fallback in WebSocket client (msg.get('ref_msg_id') or msg.msg_id)"
    - "gap_fills set + upward track scan for timeline rename resilience against T0 gaps"

key-files:
  created:
    - tests/test_protocol_builders.py
    - tests/test_async_client_correlation.py
    - tests/test_timeline_gap_fill.py
  modified:
    - forge_bridge/server/protocol.py
    - forge_bridge/client/async_client.py
    - forge_bridge/client/sync_client.py
    - forge_bridge/tools/timeline.py
    - pyproject.toml

key-decisions:
  - "Ported projekt-forge's v1.0.1 fixes upstream rather than keeping them as a local fork so Phase 5 Wave B can delete projekt-forge's duplicate client/, server/protocol/, tools/timeline.py files"
  - "project_name kwarg NOT added to AsyncClient.__init__ — stays in projekt-forge's fork per RESEARCH §D-09b disposition"
  - "Narrowing kwargs on entity_list are keyword-only (* separator) to preserve backward compat with 2-arg positional call sites"
  - "Annotated tag v1.0.1 (git tag -a) so GitHub recognizes it as a release and pip resolution works via @v1.0.1"

patterns-established:
  - "v1.0.x patch workflow: TDD each fix → atomic commit per patch → bundle with version bump → annotated tag → push tag + main"
  - "Protocol builders: flat-file with class-attr MsgType and Message(dict) subclass (NOT the enum+dataclass pattern from projekt-forge's directory layout)"

requirements-completed: [RWR-01]

# Metrics
duration: ~45min (across 3 executor runs; tests run once @ 207 passed)
completed: 2026-04-16
---

# Phase 05 Plan 00: forge-bridge v1.0.1 Release Summary

**Shipped forge-bridge v1.0.1 patch release porting four projekt-forge fixes upstream (query_lineage/query_shot_deps/media_scan builders, entity_list narrowing, ref_msg_id correlation fallback, timeline T0 gap-fill) — unblocks Phase 5 Wave B deletion of duplicate projekt-forge modules.**

## Performance

- **Duration:** ~45 min (spanned 3 executor runs due to GitHub archive state requiring user intervention)
- **Completed:** 2026-04-16
- **Tasks:** 4 (3 auto TDD tasks + 1 human-verify checkpoint for tag push)
- **Files modified:** 5 source + 3 new test files
- **Tests:** 207 passed (full pytest suite)

## Accomplishments

- **Canonical protocol extended:** `query_lineage`, `query_shot_deps`, `media_scan` builders + three new MsgType constants. `entity_list` now accepts keyword-only `shot_id`/`role`/`source_name` narrowing kwargs while preserving 2-arg backward compatibility.
- **WebSocket correlation bug fixed:** `AsyncClient._handle_message` now correlates responses via `msg.get("ref_msg_id") or msg.msg_id` fallback on both `ok` and `error` branches — servers that echo request IDs via a distinct `ref_msg_id` field are no longer dropped.
- **sync_client parity:** `SyncClient.entity_list` accepts the same narrowing kwargs and passes them through to `protocol.entity_list`.
- **Timeline gap-fill:** `timeline.rename_shots` builds a `gap_fills` set and scans upward tracks (T1, T2, …) when T0 is empty at a record range, preventing silent shot-skipping on gapped T0 edits.
- **v1.0.1 tag pushed to origin** at `92cadf1` — `pip install 'forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1'` now resolves.

## Task Commits

All on `main`, pushed to `origin/main`:

1. **Task 1: Add query_lineage/query_shot_deps/media_scan + entity_list narrowing** — `6c2456a` (feat)
2. **Task 2: Fix ref_msg_id correlation in async_client + sync_client narrowing** — `d47a65b` (fix)
3. **Task 3a: T0 gap-fill in timeline.rename_shots** — `bdef13e` (fix)
4. **Task 3b: Bump version to 1.0.1** — `92cadf1` (chore)
5. **Task 4: Create + push v1.0.1 annotated tag** — tag object `15f1e2f` → commit `92cadf1`

**Plan metadata commit:** (this SUMMARY.md + STATE.md + ROADMAP.md) — lands on main after the tag; v1.0.1 stays frozen on `92cadf1`.

## Files Created/Modified

- `forge_bridge/server/protocol.py` — 3 new MsgType class attrs + 3 new builder functions + narrowed entity_list signature
- `forge_bridge/client/async_client.py` — `ref_msg_id` fallback on `ok` and `error` branches in `_handle_message`
- `forge_bridge/client/sync_client.py` — `entity_list` accepts and passes through `shot_id`/`role`/`source_name`
- `forge_bridge/tools/timeline.py` — `gap_fills` set + upward track scan in `rename_shots`
- `pyproject.toml` — version bumped 1.0.0 → 1.0.1
- `tests/test_protocol_builders.py` — 6 behaviors covering all new builders + backward compat
- `tests/test_async_client_correlation.py` — 3 async tests (ref_msg_id on ok, id-echo backward compat, ref_msg_id on error) + 1 sync_client signature test
- `tests/test_timeline_gap_fill.py` — 3 behaviors for T0 gap handling

## Decisions Made

- **Ported upstream, not forked:** All four patches land in canonical forge-bridge so projekt-forge's local duplicates can be deleted in Waves B+. Keeps a single source of truth for protocol + client + timeline behavior.
- **`project_name` kwarg stays out of canonical:** projekt-forge's `AsyncClient.__init__` has a `project_name` kwarg that is forge-specific (multi-project routing). Per RESEARCH §D-09b disposition, that stays in the projekt-forge fork and is NOT pushed to canonical.
- **Keyword-only narrowing kwargs:** Used `*` separator in `entity_list` so existing 2-arg positional calls in `flame_hooks/forge_publish/` remain unchanged.
- **Annotated tag, not lightweight:** `git tag -a v1.0.1 -m "..."` creates a tag object (visible as `refs/tags/v1.0.1` pointing to `refs/tags/v1.0.1^{}` → commit). Required for GitHub release recognition and pip `@v1.0.1` resolution.

## Deviations from Plan

**1. [Rule 3 - Blocking] Three-run execution due to GitHub archive state**
- **Found during:** Task 4 (tag push checkpoint)
- **Issue:** First push attempt hit "This repository was archived so it is read-only" on the GitHub remote. Tag was created locally but could not be pushed.
- **Fix:** Returned structured checkpoint asking user to unarchive the repo. User unarchived; this run retried `git push origin main` + `git push origin v1.0.1` without re-running tests or re-applying patches.
- **Files modified:** None — purely network/remote-state issue.
- **Verification:** `git ls-remote --tags origin | grep refs/tags/v1.0.1` → 1 match (annotated tag object `15f1e2f` → commit `92cadf1`); `git rev-parse origin/main` == `92cadf1`.
- **Committed in:** N/A (no code change).

**Total deviations:** 1 blocking (external service state, resolved by user action).
**Impact on plan:** No code or test changes — plan executed exactly as specified once the remote became writable.

## Issues Encountered

- **GitHub remote archived:** Repo was in archived (read-only) state at tag-push time. Resolved by user unarchiving the repo between executor runs. Not a code issue.
- **Execution split across three runs:** Prior agent state preserved all work locally (commits `6c2456a`, `d47a65b`, `bdef13e`, `92cadf1` + tag `v1.0.1`), so continuation required only the two push commands and SUMMARY/state updates. No rework.

## Self-Check

- [x] `forge_bridge/server/protocol.py` defines `query_lineage` (1 match)
- [x] `forge_bridge/client/async_client.py` references `ref_msg_id` (4 matches)
- [x] `forge_bridge/client/sync_client.py` accepts `shot_id` (10 matches)
- [x] `forge_bridge/tools/timeline.py` has `gap_fills` (3 matches)
- [x] `pyproject.toml` version = "1.0.1"
- [x] `v1.0.1` tag exists on origin (`git ls-remote --tags origin` → `refs/tags/v1.0.1`)
- [x] `origin/main` == `92cadf1` (matches HEAD)
- [x] 207 tests passed in prior run (not re-run this continuation)
- [x] All 4 patch commits present in `git log 5ae88eb..92cadf1`

## Next Phase Readiness

- **Ready for Plan 05-01+:** projekt-forge Wave B can now delete its local `forge_bridge/client/`, `forge_bridge/server/protocol/`, and `forge_bridge/tools/timeline.py` shadows and `pip install forge-bridge@git+...@v1.0.1` to consume canonical.
- **No blockers for downstream plans.**

---
*Phase: 05-import-rewiring*
*Plan: 00*
*Completed: 2026-04-16*
