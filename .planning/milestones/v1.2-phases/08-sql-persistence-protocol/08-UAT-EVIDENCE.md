---
phase: 08-sql-persistence-protocol
plan: 03
task: 5
type: uat-evidence
status: passed
captured: 2026-04-21T21:30:04-07:00
---

# Phase 8 UAT Evidence — Real Synthesis Burst → `execution_log` Row

Closes Plan 08-03 success criterion 8. Proves the Phase 8 write path is live
end-to-end: `forge_bridge.bridge.execute()` → `_on_execution_callback` →
`ExecutionLog.record()` → `_persist_execution` → `INSERT ... ON CONFLICT DO
NOTHING` → live row in projekt-forge's `execution_log` table.

## Environment

| Component          | Value |
|--------------------|-------|
| Flame version      | 2026.2.1 |
| Flame project      | `013_13_13_2026_2_1_portofino` |
| forge-bridge       | v1.3.0 (site-packages at `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages`) |
| projekt-forge      | editable @ `/Users/cnoellert/Documents/GitHub/projekt-forge` (pin `@v1.3.0`) |
| Conda env          | `forge` |
| Alembic head       | `005 (head)` |
| DB target          | `forge_bridge` Postgres @ `127.0.0.1:7533` (via `FORGE_DB_URL` env) |

## Pre-UAT state

```
$ alembic current
005 (head)

$ pip show forge-bridge
Name: forge-bridge
Version: 1.3.0
Location: /Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages

$ SELECT count(*) FROM execution_log
0
```

## LRN-05 gap discovered + closed inline

Initial MCP path (`flame_ping`, `flame_list_desktop`) produced **zero** rows. Root
cause: `forge_bridge.bridge.set_execution_callback()` is a public hook defined
in Phase 6 but never installed by any production caller — `_on_execution_callback`
defaulted to `None`, so `bridge.execute()` skipped the observation path
unconditionally (bridge.py:162-166). Unit tests had always called
`log.record()` directly, masking the missing link.

Fix (projekt-forge commit `cf221fe`): `projekt_forge.learning.wiring` now
installs a signature adapter `_forward_bridge_exec_to_log(code, response)` that
forwards successful `bridge.execute()` responses into `ExecutionLog.record(code,
intent=None)`. Failed responses are dropped to avoid polluting the learning
pipeline with unreachable synth candidates. `_reset_for_testing()` also clears
the bridge callback to prevent cross-test state leak. 4 new tests in
`tests/test_learning_wiring.py`. Full projekt-forge suite: **436 passed, 3
xfailed** (baseline 432 + 4 new, zero regressions).

## UAT verification

End-to-end driver script (Python, run in the `forge` conda env):

```python
# 1. Baseline
baseline = SELECT count(*) FROM execution_log  # → 0

# 2. Initialize pipeline
init_learning_pipeline(args=None)
# _on_execution_callback is now _forward_bridge_exec_to_log (not None)

# 3. Real bridge.execute() — HTTP POST to Flame at 127.0.0.1:9999
uat_code = "uat_marker = 'phase-8-UAT-45d26b80'; print(uat_marker)"
resp = await bridge.execute(uat_code)  # resp.ok=True, stdout='phase-8-UAT-45d26b80'

# 4. Post-query
post = SELECT count(*) FROM execution_log  # → 1, delta +1
```

### Verbatim run output

```
[1/4] baseline execution_log count: 0
[2/4] pipeline initialized — bridge callback: True
[3/4] bridge.execute ok=True stdout='phase-8-UAT-45d26b80'
[4/4] post-UAT count: 1   delta: 1
      row: {
        'code_hash': '174d89e4b9fa5fd686611578aa84cf3a8bf19561a7e2ad89a9f81105a809f658',
        'timestamp': datetime.datetime(2026, 4, 21, 21, 30, 4, 897814, tzinfo=-07:00),
        'intent': None,
        'code_len': 54
      }
```

`raw_code` is intentionally NOT displayed (T-08-03-06 mitigation — prevents
accidental secret disclosure during human verification); `length(raw_code)` = 54
characters confirms the full UAT code was stored.

## Criteria

| Success criterion | Status |
|---|---|
| SC1 — `pyproject.toml` version 1.3.0 + test_package_version asserts 1.3.0 + pytest green | PASS |
| SC2 — annotated tag v1.3.0 pushed to origin | PASS |
| SC3 — GitHub Release v1.3.0 exists with 2 assets (wheel + sdist) | PASS |
| SC4 — projekt-forge pin at `@v1.3.0` | PASS |
| SC5 — `forge` conda env forge-bridge in site-packages, not editable shadow; `from forge_bridge import StoragePersistence` works | PASS |
| SC6 — `alembic current` = `005 (head)`; `execution_log` has 4-col + UNIQUE + 2-index schema (no `promoted` per D-08) | PASS |
| SC7 — projekt-forge `pytest tests/` exits 0 with no regressions from 422 baseline | PASS (436 passed, 3 xfailed; baseline 432 + 4 new LRN-05 tests) |
| **SC8 — real bridge.execute() produces a row in execution_log; no DB-write WARNING lines** | **PASS (delta +1, code_hash 174d89e4…, zero WARNING lines in driver log)** |
| SC9 — requirements STORE-01..06 all covered by shipped artifact | PASS (STORE-01..04 via forge-bridge v1.3.0 Protocol+barrel+docstring; STORE-05 via projekt-forge adapter+migration+LRN-05 wiring; STORE-06 via no-retry invariant — UAT had no outage, no retries logged) |

## Deviation log (Rule-3 auto-fixes applied during 08-03 execution)

| Deviation | Commit | Rationale |
|-----------|--------|-----------|
| Unified task-1 (version bump) with task-2 (release) commit | `36a0eaa` (forge-bridge) | Plan specified two commits; executor combined into the single `chore(release)` commit that precedent 07.1-02 and 7-04 both used. Rule-3 — precedent-aligned. |
| `alembic.ini` `script_location` fix (`forge_bridge/db/migrations` → `projekt_forge/db/migrations`) | `7ddddbb` (projekt-forge) | Stale path from pre-Phase-5 rename blocked `alembic upgrade`. Rule-3 — unambiguous fix required to proceed. |
| Plan Step C used `forge_admin` in its inline Python; actual live DB is `forge_bridge` | — (narrative fix only, no code change) | `get_db_config()` resolves to `forge_admin` but `FORGE_DB_URL` (the env-set runtime URL) points at `forge_bridge` Postgres. Plan's hardcoded `forge_admin` was an artifact of the discuss-phase assumption; actual topology was verified at runtime during Task 4. |
| **LRN-05 gap closure — `bridge.execute()` → `ExecutionLog.record()` hook wiring** | `cf221fe` (projekt-forge) | SC8 unreachable without this. Phase 6 defined `set_execution_callback()` as a public API but never installed it; no production code called it. Discovered during UAT when real `bridge.execute()` calls produced zero rows. Fix is in-scope for Phase 8 because SC8 ("real synthesis → row") was the blocking gap. **User pre-approved the fix as a real architectural fix, not a hotfix.** |

## Post-UAT DB state

```sql
SELECT code_hash, timestamp, intent, length(raw_code) AS code_len
FROM execution_log
ORDER BY timestamp DESC LIMIT 3;

code_hash                                                         timestamp                       intent  code_len
────────────────────────────────────────────────────────────────  ─────────────────────────────   ──────  ────────
174d89e4b9fa5fd686611578aa84cf3a8bf19561a7e2ad89a9f81105a809f658  2026-04-21 21:30:04.897814-07   NULL    54
```

Zero `execution_log DB write failed` WARNING lines observed in the driver
session — the D-06 no-retry / log-once-and-swallow path did not trigger.

## Next-step handoff

- forge-bridge: all phase-8 commits are on `main` and pushed to origin; tag `v1.3.0` is pushed; GitHub Release v1.3.0 is live.
- projekt-forge: 4 commits stacked locally on `main` (`60682bc`, `586b722`, `7ddddbb`, `cf221fe`) — **NOT yet pushed**. User reviews + pushes after reading this evidence and the 08-03-SUMMARY.
- Milestone close ceremony (`/gsd-complete-milestone` for v1.2 Observability & Provenance) is the user's next manual step after Phase 8 closes.
