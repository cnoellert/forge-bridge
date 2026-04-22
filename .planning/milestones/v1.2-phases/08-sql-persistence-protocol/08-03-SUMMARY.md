---
phase: 08-sql-persistence-protocol
plan: 03
type: execute
wave: 3
completed: 2026-04-21T21:40:00-07:00
tasks_completed: 5
tasks_total: 5
status: passed
requirements_covered:
  - STORE-01
  - STORE-02
  - STORE-03
  - STORE-04
  - STORE-05
  - STORE-06
---

# Plan 08-03 Summary — Release + UAT (forge-bridge v1.3.0)

Ships forge-bridge v1.3.0 with the StoragePersistence Protocol, pins projekt-forge
to the new tag, applies Alembic revision 005 to live Postgres, closes the Phase 6
`bridge.execute()` → `ExecutionLog.record()` gap (LRN-05), and proves end-to-end
that a real `bridge.execute()` call produces a row in `execution_log`.

Closes Phase 8 (EXT-03) and, per the milestone plan, is the last technical phase
before the user invokes `/gsd-complete-milestone` on v1.2 Observability &
Provenance (Phases 7 + 7.1 + 8).

## Release artifacts

| Artifact | Identity |
|---|---|
| forge-bridge release commit | `36a0eaa` on `main` (pushed to origin) |
| Annotated tag | `v1.3.0` (pushed to origin) |
| GitHub Release | `v1.3.0` — 2 assets (`forge_bridge-1.3.0-py3-none-any.whl`, `forge_bridge-1.3.0.tar.gz`) |
| Release URL | https://github.com/cnoellert/forge-bridge/releases/tag/v1.3.0 |

Commit message (precedent-aligned with 07.1-02 `abd047c`, 7-04 `0987525`, 5-00
`92cadf1`): `chore(release): bump version 1.2.1 → 1.3.0 — StoragePersistence
Protocol (STORE-01..06)`.

## projekt-forge cross-repo commits (local `main`, NOT yet pushed)

| Commit | Purpose |
|---|---|
| `586b722` | `chore(deps): bump forge-bridge pin @v1.2.1 → @v1.3.0 (STORE-05)` |
| `7ddddbb` | `fix(db): correct alembic.ini script_location forge_bridge → projekt_forge` (Rule-3, stale path from pre-Phase-5 rename) |
| `cf221fe` | `feat(learning): wire bridge.execute → ExecutionLog.record (LRN-05)` (Rule-3 gap closure — see UAT evidence) |

Plus from Plan 08-02: `6a098be` (Alembic revision 005), `42b767b` (sync adapter),
`c76e321` (adapter unit tests), `60682bc` (wiring test updates).

**User pushes projekt-forge after reviewing this summary and the UAT evidence.**

## Conda env verification

```
$ conda run -n forge pip show forge-bridge
Name: forge-bridge
Version: 1.3.0
Location: /Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages
```

Confirmed site-packages install (Phase 07.1 Option A shadow remediation applied
correctly — no editable shadow on top of the pinned tag).

## Alembic state (live `forge_bridge` Postgres)

```
$ conda run -n forge alembic current
005 (head)
```

Upgrade path ran `001 → 002 → 003 → 004 → 005` in a single invocation (this DB
was at `001` prior; earlier milestones must have never run `alembic upgrade head`
against it). No tracebacks. `execution_log` table present with the locked 4-col
schema (no `promoted` per D-08), 2 indexes, 1 unique constraint on `(code_hash,
timestamp)`.

## Regression gate

projekt-forge full suite after all commits including LRN-05:

```
436 passed, 3 xfailed, 1 warning in 2.21s
```

Baseline at Phase 07.1 was 422. Phase 8 added: +10 tests from 08-02 (adapter unit
tests + wiring updates) and +4 tests from 08-03 / LRN-05 = +14 net new, zero
regressions.

forge-bridge full suite: `289 passed` (unchanged from 08-01 baseline).

## Task 5 UAT evidence — real bridge.execute → execution_log row

Summary (full verbatim output in `08-UAT-EVIDENCE.md`):

- Baseline count: **0**
- `bridge.execute("uat_marker = 'phase-8-UAT-45d26b80'; print(uat_marker)")` →
  `ok=True`, stdout `'phase-8-UAT-45d26b80'`
- Post-UAT count: **1** (delta +1)
- Row: `code_hash=174d89e4…`, `timestamp=2026-04-21T21:30:04Z`, `intent=None`,
  `code_len=54`
- **Zero** `execution_log DB write failed` WARNING log lines (D-06 clean path)

The UAT was driven via a direct Python process (not through Claude Code's MCP
surface) because Claude Code's MCP client was attached to a projekt-forge
instance spawned before the LRN-05 fix. The direct path exercises the same
production code chain — `bridge.execute()` hits the live Flame HTTP bridge on
`127.0.0.1:9999`, which then fires through `_on_execution_callback` →
`ExecutionLog.record()` → `_persist_execution()` → live `execution_log` row.
Equivalent to an MCP-driven synthesis for verification purposes.

## LRN-05 gap closure (Rule-3 deviation)

Discovered during initial UAT that MCP-driven `flame_*` calls produced zero
rows. Root cause: `forge_bridge.bridge.set_execution_callback()` was a Phase 6
public API that **no production code ever installed**. The hook was defined but
left `None`. Every `bridge.execute()` skipped the observation path unconditionally.

Closed in `cf221fe`: `projekt_forge.learning.wiring.init_learning_pipeline()`
now installs `_forward_bridge_exec_to_log(code, response)` — a 10-line adapter
that forwards `response.ok=True` executions into `ExecutionLog.record(code,
intent=None)`. Test coverage: 4 new tests asserting install / forward-on-success
/ drop-on-failure / reset-for-testing hygiene.

User pre-approved this as an in-scope Rule-3 fix (required to make SC8
reachable) — "a real fix, not a hot fix." Not expanded into Phase 8.1 because
the gap is small and surfaced during UAT, not during planning.

## Success criteria (from 08-03-PLAN.md)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | pyproject.toml 1.3.0 + test_package_version + pytest green | PASS |
| 2 | Annotated tag v1.3.0 pushed to origin | PASS |
| 3 | GitHub Release v1.3.0 with 2 assets + STORE-01..06 in notes | PASS |
| 4 | projekt-forge pin `@v1.3.0` | PASS |
| 5 | forge env forge-bridge 1.3.0 in site-packages; StoragePersistence importable | PASS |
| 6 | alembic `005 (head)`; execution_log schema matches docstring; no `promoted` | PASS |
| 7 | projekt-forge pytest tests/ green, no regressions | PASS (436 passed, 3 xfailed) |
| 8 | Real execution produces execution_log row; no DB-write WARNING lines | **PASS (delta +1, row captured)** |
| 9 | STORE-01..06 covered | PASS (see UAT evidence) |
| 10 | `/gsd-complete-milestone` NOT invoked (user's manual step) | PASS (deferred to user) |

## Milestone close handoff

All technical work for **v1.2 Observability & Provenance** is complete:

- Phase 7 — Tool Provenance in MCP Annotations (commit lineage `1429227` and earlier)
- Phase 07.1 — startup_bridge hotfix + deployment UAT (`d7ac8ce`)
- Phase 8 — SQL Persistence Protocol (this plan, ending at `36a0eaa` on forge-bridge + `cf221fe` on projekt-forge)

User's next manual step (one-line command):

```
/gsd-complete-milestone
```

This archives the completed milestone's phase directories into `.planning/archive/v1.2/`
and rolls STATE.md + ROADMAP.md forward to the next milestone.

## Cross-references

- Phase 8 plans and wave summaries: [08-01-SUMMARY.md](08-01-SUMMARY.md), [08-02-SUMMARY.md](08-02-SUMMARY.md)
- UAT verbatim output: [08-UAT-EVIDENCE.md](08-UAT-EVIDENCE.md)
- Locked decisions: [08-CONTEXT.md](08-CONTEXT.md) (D-01..D-14)
- Release precedents: phase 07.1-02 (`abd047c`), phase 7-04 (`0987525`)
