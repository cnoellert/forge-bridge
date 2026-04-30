---
phase: 19-code-quality-polish
plan: 03
subsystem: testing

tags: [pytest, sqlalchemy, asyncpg, postgres, atomicity, audit-trail, staged-operations, transactions]

# Dependency graph
requires:
  - phase: 13
    provides: "StagedOpRepo / EventRepo / DBEntity / DBEvent — the live store-layer surface the rewritten test exercises end-to-end"
  - phase: 18
    provides: "HARNESS-01..03 — session_factory + seeded_project fixtures + non-gated _phase13_postgres_available()"
  - phase: 19-02
    provides: "Past-tense WR-01 closure + Optional[str] regression test (non-overlapping hunk; 19-03 changes lines 323-398, 19-02 appended at line 675+)"
provides:
  - "Single-session approve+flush+rollback observation in `test_transition_atomicity` — pins the actual SQLAlchemy/Postgres atomicity contract instead of the prior trivially-passing `assert True  # placeholder` + contradictory `assert row is None` shape"
  - "T-19-03 mitigation landed: a future change that lets approve persist past a rollback, OR drops the originally-committed staged.proposed row alongside the rollback, will fail this test"
  - "WR-02 closure complete (Phase 13 deferred WR-02 → 19-03 closure path executed)"
affects: [v1.4.x close, POLISH-04, audit-trail invariants]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-session atomicity observation: propose+commit (baseline persists), approve+flush (in-flight visible), rollback (in-flight reverts), re-observe — exercises the real SQLAlchemy/Postgres semantics rather than relying on cross-session assertions that contradict committed-state durability."
    - "Documented-only RED→GREEN evidence: TDD gate captured in SUMMARY.md (verbatim pytest output for the rollback-removed RED experiment + the restored GREEN run); no deliberate-failure RED commit lands in v1.4.1 history (CONTEXT D-09)."

key-files:
  created: []
  modified:
    - "tests/test_staged_operations.py — body of `test_transition_atomicity` rewritten (lines 329-398 → 13-line single-session block); function signature + docstring at lines 323-328 preserved verbatim."

key-decisions:
  - "Atomicity contract is observable WITHIN a single session, not across session-factory calls. The original test mistakenly committed a baseline in one session, then asserted `row is None` post-rollback in a different session — a vacuously-broken assertion (the baseline commit had already durably persisted)."
  - "RED→GREEN evidence is captured in SUMMARY only (CONTEXT D-09). Reason: a deliberate-failure RED commit would clutter v1.4.1 history. The single GREEN commit is the only artifact that lands."
  - "Plan literal `forgepass` is a placeholder; actual local dev Postgres password is `forge`. Verification used the working credentials (Rule 1 deviation, documented; not a code change)."

patterns-established:
  - "Atomicity test for transactional store-layer code: ONE session, baseline-commit, in-flight mutate+flush, observe pre-rollback (visible), rollback, observe post-rollback (in-flight reverts; baseline survives). Use this template for any future rollback-semantics test in `forge_bridge/store/`."

requirements-completed: [POLISH-03]

# Metrics
duration: ~25min
completed: 2026-04-30
---

# Phase 19 Plan 03: POLISH-03 Single-Session Atomicity Observation Summary

**Rewrote `test_transition_atomicity` (74 → 26 lines) to a single-session approve+flush+rollback observation; replaces an `assert True  # placeholder` + a vacuously-broken `assert row is None` with a real audit-trail tamper guard against live Postgres at `localhost:7533`.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-30T04:18:00Z (approx)
- **Completed:** 2026-04-30T04:43:00Z (approx)
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `test_transition_atomicity` body replaced with a single 13-line atomicity observation per CONTEXT D-08.
- `assert True  # placeholder` (line 360) and `assert row is None` (line 388, contradicted SQLAlchemy/Postgres rollback semantics) both removed.
- Raw `select(DBEntity).where(...)` and `select(DBEvent).where(...)` blocks (lines 385-398) both removed — the test now exercises the public repo APIs (`StagedOpRepo.get` / `EventRepo.get_recent`) instead of bypassing them.
- Test passes against live dev Postgres at `localhost:7533` with `FORGE_DB_URL` set; full file (`tests/test_staged_operations.py`) reports `44 passed, 4 skipped, 0 failed`.
- T-19-03 (audit-trail tamper / dropped events) mitigation landed: removing the `await session.rollback()` line causes `assert len(events_after) == 1` to fail with `assert 2 == 1` — the test really exercises the atomicity contract.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `test_transition_atomicity` body to single-session observation** — `5f7ad7f` (fix)

_Note: This plan ran without a separate RED commit per CONTEXT D-09 (documented-only RED→GREEN evidence). The single `fix` commit is the GREEN artifact._

## Files Created/Modified

- `tests/test_staged_operations.py` — body of `test_transition_atomicity` rewritten; function signature + docstring at lines 323-328 preserved verbatim.

## Verbatim Diff Applied

```diff
diff --git a/tests/test_staged_operations.py b/tests/test_staged_operations.py
index 5110346..73de8a4 100644
--- a/tests/test_staged_operations.py
+++ b/tests/test_staged_operations.py
@@ -329,73 +329,25 @@ async def test_transition_atomicity(session_factory):
     async with session_factory() as session:
         repo = StagedOpRepo(session)
         op = await repo.propose(
-            operation="flame.publish_sequence",
-            proposer="setup",
-            parameters={"shot_id": "abc"},
+            operation="op-atom", proposer="p", parameters={},
         )
-        await session.commit()
-        op_id = op.id
-
-    # In a new session: approve, then explicitly rollback (simulates an error
-    # raised by a downstream caller — e.g., FB-B's HTTP handler aborting after
-    # the repo call).
-    async with session_factory() as session:
-        repo = StagedOpRepo(session)
-        await repo.approve(op_id, approver="web-ui:artist")
-        # Verify mid-flight state inside the open transaction
-        await session.flush()  # don't commit — push to DB so rollback has work
-        await session.rollback()
-
-    # Verify post-rollback state in a fresh session: status is still 'proposed'
-    # AND only the original 'staged.proposed' event exists. No staged.approved.
-    async with session_factory() as session:
-        repo = StagedOpRepo(session)
-        fetched = await repo.get(op_id)
-        # NOTE: because each session_factory() call provisions a fresh DB, the
-        # rollback test must be self-contained within a single session. Above we
-        # asserted the rollback happened inside the open session; this final
-        # assertion uses the SAME session_factory but a different DB instance —
-        # which makes the test trivially pass. To make the atomicity claim
-        # observable, we verify it WITHIN the rollback session:
-        assert True  # placeholder; the meaningful check is below
+        await session.commit()  # baseline: 1 entity + 1 staged.proposed event committed
 
-    # Reconstruct the test in a single session for atomicity observation:
-    async with session_factory() as session:
-        repo = StagedOpRepo(session)
-        op2 = await repo.propose(operation="op-atom", proposer="p", parameters={})
-        await session.commit()
-
-        events_before = await EventRepo(session).get_recent(entity_id=op2.id, limit=10)
-        assert len(events_before) == 1  # staged.proposed
-        assert events_before[0].event_type == "staged.proposed"
-
-        # Now approve and rollback within the same session
-        await repo.approve(op2.id, approver="artist")
+        # Approve in same session, flush (push to DB), observe pre-rollback state
+        await repo.approve(op.id, approver="artist")
         await session.flush()
-
-        events_mid_flight = await EventRepo(session).get_recent(entity_id=op2.id, limit=10)
-        assert len(events_mid_flight) == 2  # both rows visible pre-commit
+        events_mid = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
+        assert len(events_mid) == 2, "both events visible pre-rollback"
 
         await session.rollback()
 
-        # In the same session post-rollback, both writes are gone
-        db_entity = await session.get(DBEntity, op2.id)
-        # (depending on session expiration, db_entity may be None after rollback;
-        # re-fetch via fresh query to be safe)
-        row = (await session.execute(
-            select(DBEntity).where(DBEntity.id == op2.id)
-        )).scalar_one_or_none()
-        assert row is None, (
-            "post-rollback: even the original proposed entity is rolled back "
-            "because its commit was tied to the rolled-back session"
-        )
-        event_rows = (await session.execute(
-            select(DBEvent).where(DBEvent.entity_id == op2.id)
-        )).scalars().all()
-        assert len(event_rows) == 0, (
-            "ATOMICITY VIOLATED: events persist after session rollback — "
-            "audit-trail tamper risk surfaced"
-        )
+        # Post-rollback: only the originally-committed state remains
+        events_after = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
+        assert len(events_after) == 1
+        assert events_after[0].event_type == "staged.proposed"
+        fetched = await repo.get(op.id)
+        assert fetched is not None
+        assert fetched.status == "proposed"
```

GREEN atomic commit: **`5f7ad7f`** on `worktree-agent-aae10213e545a7449` (worktree branch off `gsd/v1.4-staged-ops-platform` HEAD `a0b71ce`).

## RED → GREEN Evidence (DOCUMENTED ONLY — NOT COMMITTED)

Per CONTEXT D-09, RED→GREEN evidence is captured here in SUMMARY only; no deliberate-failure RED commit lands in v1.4.1 history.

**Both runs used the env var:**
```
FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:7533/forge_bridge
```

(Note: plan literal cited `forgepass` as the password; actual local dev password is `forge`. Using `forgepass` raises `asyncpg.exceptions.InvalidPasswordError`. See "Deviations from Plan" — Rule 1.)

### RED experiment — `await session.rollback()` line removed (in working tree only, NOT committed)

Replaced the rollback line with a `# RED experiment: rollback line temporarily removed (NOT committed)` comment, then ran:

```
$ FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:7533/forge_bridge \
    pytest tests/test_staged_operations.py::test_transition_atomicity -v -p no:pytest-blender

            # Approve in same session, flush (push to DB), observe pre-rollback state
            await repo.approve(op.id, approver="artist")
            await session.flush()
            events_mid = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
            assert len(events_mid) == 2, "both events visible pre-rollback"

            # RED experiment: rollback line temporarily removed (NOT committed)

            # Post-rollback: only the originally-committed state remains
            events_after = await EventRepo(session).get_recent(entity_id=op.id, limit=10)
>           assert len(events_after) == 1
E           assert 2 == 1
E            +  where 2 = len([<DBEvent staged.approved at 2026-04-30 04:25:39.452684+00:00>, <DBEvent staged.proposed at 2026-04-30 04:25:39.448230+00:00>])

tests/test_staged_operations.py:346: AssertionError
=========================== short test summary info ============================
FAILED tests/test_staged_operations.py::test_transition_atomicity - assert 2 ...
========================= 1 failed, 1 warning in 0.26s =========================
```

Both events (`staged.approved` + `staged.proposed`) persisted because rollback never ran — the test correctly fails. Atomicity invariant proven by negative example.

### GREEN run — `await session.rollback()` line restored

```
$ FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:7533/forge_bridge \
    pytest tests/test_staged_operations.py::test_transition_atomicity -v -p no:pytest-blender

rootdir: /Users/cnoellert/Documents/GitHub/forge-bridge/.claude/worktrees/agent-aae10213e545a7449
configfile: pyproject.toml
plugins: anyio-4.12.1, playwright-0.7.2, cov-7.1.0, timeout-2.4.0, asyncio-1.3.0, base-url-2.1.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

tests/test_staged_operations.py::test_transition_atomicity PASSED        [100%]

========================= 1 passed, 1 warning in 0.22s =========================
```

The restoration was the working-tree revert; this is the state captured in commit **`5f7ad7f`**.

**Explicit confirmation:** No RED commit was landed (CONTEXT D-09 compliance). `git log --oneline -3` shows only the GREEN fix commit + prior 19-02 history.

## Grep-Guard Outputs

All four grep guards return zero matches (exit=1):

```
$ grep -nE 'assert True  # placeholder' tests/test_staged_operations.py
exit=1   # no matches — placeholder gone

$ grep -nE 'assert row is None' tests/test_staged_operations.py
exit=1   # no matches — contradiction-assertion gone

$ grep -nE 'select\(DBEntity\)\.where\(DBEntity\.id == op2\.id\)' tests/test_staged_operations.py
exit=1   # no matches — raw select(DBEntity) block gone

$ grep -nE 'select\(DBEvent\)\.where\(DBEvent\.entity_id == op2\.id\)' tests/test_staged_operations.py
exit=1   # no matches — raw select(DBEvent) block gone
```

New observations are present (exit=0, exactly one match each):

```
$ grep -nE '^\s*events_after = await EventRepo\(session\)\.get_recent\(entity_id=op\.id' tests/test_staged_operations.py
345:        events_after = await EventRepo(session).get_recent(entity_id=op.id, limit=10)

$ grep -nE '^\s*assert fetched\.status == "proposed"' tests/test_staged_operations.py
350:        assert fetched.status == "proposed"
```

## Full-File Regression Verification

```
$ FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:7533/forge_bridge \
    pytest tests/test_staged_operations.py -v -p no:pytest-blender
...
=================== 44 passed, 4 skipped, 1 warning in 5.98s ===================
```

The 4 skipped cases are the by-design `should_raise=False` cross-product transitions in `test_transition_legality[None-...]` (matches Phase 13 baseline). No new failures introduced.

## Decisions Made

- **Single-session observation is the correct shape for atomicity tests.** The original test split the work across three session-factory calls and then asserted `row is None` in a fourth — a contradiction with SQLAlchemy/Postgres rollback semantics (committed state survives a rolled-back later session). The new shape exercises the actual contract.
- **RED→GREEN evidence is documented-only.** A deliberate-failure RED commit would clutter v1.4.1 history. CONTEXT D-09 made this explicit; this plan honors it.
- **The placeholder line is at line 360, not line 363 as CONTEXT cited.** RESEARCH Pitfall 2 corrected the off-by-3 cite; the final rewrite mapped to the actual file content.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's literal Postgres password (`forgepass`) is wrong**
- **Found during:** Task 1 verification (pytest connection attempt).
- **Issue:** Plan referenced `FORGE_DB_URL=postgresql://forge:forgepass@localhost:7533/forge_bridge` in `<verify>` and `<acceptance_criteria>`. Using `forgepass` raises `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "forge"`. The actual local dev Postgres password is `forge` (matches `127.0.0.1:7533/forge_bridge` references in `MILESTONES.md` and `v1.4-MILESTONE-AUDIT.md`).
- **Fix:** Used `FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:7533/forge_bridge` for all verification runs. Documents-only artifact; no code change.
- **Files modified:** None (verification env-var only).
- **Verification:** Both RED and GREEN runs above use `forge:forge`; both connect to live Postgres at `:7533`; both runs reflect real test outcomes (RED fails with `assert 2 == 1`, GREEN passes).
- **Committed in:** N/A (env-var setting, not source change).

**2. [Rule 3 - Blocking] `pytest-blender` plugin failed to collect tests**
- **Found during:** Task 1 verification (initial pytest invocation).
- **Issue:** The conda env has `pytest-blender` installed; without a Blender executable on PATH, the plugin emits `Exit: 'blender' executable not found.` and aborts pytest before collecting any tests. This is unrelated to forge-bridge and out-of-scope for this plan.
- **Fix:** Added `-p no:pytest-blender` to all pytest invocations in this plan's verification. Did NOT modify the conda env (out-of-scope per executor SCOPE BOUNDARY rule).
- **Files modified:** None.
- **Verification:** All five pytest runs in this plan (1 baseline-current, 1 GREEN single-test, 1 RED single-test, 1 GREEN single-test post-restore, 1 GREEN full-file) use `-p no:pytest-blender` and collect successfully.
- **Committed in:** N/A (pytest invocation flag, not source change).
- **Deferred-items follow-up:** Either install Blender on the dev machine OR uninstall `pytest-blender` from the conda env if it isn't needed for forge-bridge work. Not a v1.4.x blocker.

---

**Total deviations:** 2 auto-fixed (1 bug — plan literal incorrect; 1 blocking — out-of-scope plugin)
**Impact on plan:** Both deviations are environmental (DB password literal, conda env plugin). Plan logic and source rewrite landed exactly as specified by CONTEXT D-08. No scope creep; no runtime code modified beyond the targeted body rewrite.

## Issues Encountered

- The plan-literal Postgres password (`forgepass`) does not match the local dev DB role. Resolved by using the correct password (`forge`) for verification runs. Not a code change; documented under Deviations.
- The conda env's `pytest-blender` plugin requires a Blender executable that isn't installed; this aborts pytest at the plugin-load stage with `Exit: 'blender' executable not found.` — unrelated to forge-bridge. Resolved by passing `-p no:pytest-blender`.

## Self-Check

- [x] Modified file exists and contains rewrite: `tests/test_staged_operations.py` lines 323-350 — verified via `Read` tool post-edit; function signature + docstring at 323-328 preserved; new body at 329-350 (single `async with session_factory() as session:` block).
- [x] Commit hash exists: `git log --oneline -3` shows `5f7ad7f fix(19-03): close POLISH-03 — single-session atomicity observation (WR-02 closure)`.
- [x] Grep guards all return exit=1 (zero matches): `assert True  # placeholder`, `assert row is None`, `select(DBEntity).where(DBEntity.id == op2.id)`, `select(DBEvent).where(DBEvent.entity_id == op2.id)`.
- [x] New observations present: `events_after = await EventRepo(session).get_recent(entity_id=op.id` (line 345), `assert fetched.status == "proposed"` (line 350).
- [x] GREEN test passes against live dev Postgres at `:7533` (`1 passed`).
- [x] Full file run: 44 passed, 4 skipped (by-design), 0 failed.
- [x] No accidental file deletions: `git diff --diff-filter=D --name-only HEAD~1 HEAD` returned empty.

## Self-Check: PASSED

## Next Phase Readiness

- POLISH-03 closes WR-02 cleanly. Phase 19 has POLISH-04 still in flight (qwen2.5-coder `<|im_start|>` tail-token strip in chat handler) per the v1.4.x roadmap.
- Worktree branch `worktree-agent-aae10213e545a7449` is at `5f7ad7f` (one commit on top of `a0b71ce`); ready for orchestrator merge into the wave's integration branch.
- After this plan + POLISH-04 land, v1.4.1 tag becomes ready (per ROADMAP.md).

---
*Phase: 19-code-quality-polish*
*Plan: 03 (POLISH-03)*
*Completed: 2026-04-30*
