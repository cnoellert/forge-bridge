---
phase: 14
plan: "02"
subsystem: console-read-api
tags: [read-api, session-factory, staged-ops, mcp-server, tdd]
dependency_graph:
  requires:
    - "14-01 (StagedOpRepo.list method — parallel wave 1, merged before tests run)"
    - "forge_bridge/store/session.py::get_async_session_factory (existing)"
    - "forge_bridge/store/staged_operations.py::StagedOpRepo (existing)"
  provides:
    - "ConsoleReadAPI.session_factory constructor parameter (default None)"
    - "ConsoleReadAPI.get_staged_ops(status, limit, offset, project_id)"
    - "ConsoleReadAPI.get_staged_op(op_id)"
    - "_lifespan session_factory singleton build + injection into ConsoleReadAPI, build_console_app, register_console_resources"
  affects:
    - "14-03 (build_console_app receives session_factory kwarg at call site)"
    - "14-04 (register_console_resources receives session_factory kwarg at call site)"
    - "14-05 (forge://staged/pending resource reads via ConsoleReadAPI.get_staged_ops)"
tech_stack:
  added: []
  patterns:
    - "Per-call async session pattern (async with self._session_factory() as session)"
    - "TDD RED/GREEN cycle for constructor parameter + async methods"
    - "TYPE_CHECKING block for async_sessionmaker and StagedOperation type hints"
key_files:
  created: []
  modified:
    - forge_bridge/console/read_api.py
    - forge_bridge/mcp/server.py
    - tests/test_console_read_api.py
decisions:
  - "session_factory kwargs at build_console_app and register_console_resources are LIVE (not commented out) per plan guidance: wave graph guarantees 14-03/14-04 start after 14-02 commits, so kwargs are inert until those plans add the parameter on the receiving side"
  - "get_async_session_factory() import placed at module top level in server.py (not inline in _lifespan body) to match existing module-level import style"
  - "10 new tests added (4 sync + 6 async); 6 Postgres-dependent tests skip cleanly without Postgres per local-first philosophy"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-26T19:41:04Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 14 Plan 02: ConsoleReadAPI session_factory + get_staged_ops + _lifespan injection Summary

ConsoleReadAPI extended with session_factory constructor parameter (default None, backward-compat) and two new async read methods (get_staged_ops, get_staged_op) that open a session per call via StagedOpRepo; _lifespan updated to build the canonical session_factory singleton once and thread it through to all three downstream call sites.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED  | Failing tests for session_factory + get_staged_ops | 2906a22 | tests/test_console_read_api.py |
| GREEN Task 1 | ConsoleReadAPI session_factory + methods | baebfde | forge_bridge/console/read_api.py |
| Task 2 | _lifespan session_factory injection | 4646e94 | forge_bridge/mcp/server.py |

## What Was Built

### `forge_bridge/console/read_api.py`

- Added `import uuid` and TYPE_CHECKING imports for `async_sessionmaker` and `StagedOperation`
- Extended `ConsoleReadAPI.__init__` with `session_factory: Optional["async_sessionmaker"] = None` as last kwarg; stored as `self._session_factory`
- Added `get_staged_ops(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` — opens session per call, delegates to `StagedOpRepo.list()`
- Added `get_staged_op(op_id: uuid.UUID) -> StagedOperation | None` — opens session per call, delegates to `StagedOpRepo.get()`
- Both methods use `async with self._session_factory() as session:` (per-call session, D-03)

### `forge_bridge/mcp/server.py`

- Added top-level import: `from forge_bridge.store.session import get_async_session_factory`
- In `_lifespan` Step 4: added `session_factory = get_async_session_factory()` before `ConsoleReadAPI(...)` construction
- Added `session_factory=session_factory` kwarg to `ConsoleReadAPI(...)` constructor call
- Added `session_factory=session_factory` kwarg to `build_console_app(...)` call (live, per wave-graph guarantee)
- Added `session_factory=session_factory` kwarg to `register_console_resources(...)` call (live, per wave-graph guarantee)

### `tests/test_console_read_api.py`

- Added `import uuid` and `import pytest_asyncio`
- Added `api_with_session_factory` fixture (composes `session_factory` fixture from conftest.py)
- Added 10 new test functions (4 sync, 6 async/Postgres-dependent):
  - `test_console_read_api_session_factory_defaults_to_none` — backward-compat guard
  - `test_console_read_api_session_factory_stored` — constructor stores kwarg
  - `test_get_staged_ops_is_async` / `test_get_staged_op_is_async` — async method guards
  - `test_get_staged_ops_returns_tuple` — (records, total) shape (SKIP without Postgres)
  - `test_get_staged_ops_filter_by_status` — status filter (SKIP without Postgres)
  - `test_get_staged_ops_pagination_passes_through` — limit/offset pagination (SKIP without Postgres)
  - `test_get_staged_op_returns_record` — single op lookup by id (SKIP without Postgres)
  - `test_get_staged_op_returns_none_for_unknown` — missing UUID returns None (SKIP without Postgres)
  - `test_get_staged_ops_opens_fresh_session_per_call` — per-call session isolation (SKIP without Postgres)

## Test Results

- `pytest tests/test_console_read_api.py`: 13 passed, 6 skipped (Postgres unavailable)
- `pytest tests/test_mcp_server_graceful_degradation.py tests/test_console_instance_identity.py`: 6 passed
- `pytest tests/ -k "read_api or console_routes or console_health"`: 39 passed, 6 skipped

## Output Spec Answers (per plan `<output>` block)

| Question | Answer |
|----------|--------|
| kwargs at `build_console_app` and `register_console_resources` LIVE or commented? | **LIVE** — wave graph guarantees 14-02 commits before 14-03/14-04 start |
| Number of new tests added to `test_console_read_api.py` | **10** (4 sync + 6 async) |
| `_lifespan` import succeeds, no graceful-degradation regression? | **Yes** — all 6 graceful-degradation + instance-identity tests pass |
| Does `_to_staged_operation` helper exist in Plan 14-01's output? | **Yes** — confirmed at `staged_operations.py:393`; `get_staged_op` delegates to `repo.get()` which uses it |

## Deviations from Plan

None — plan executed exactly as written. The decision to activate kwargs LIVE (vs commented-out) was explicitly directed by the plan's final "Decision:" paragraph in Task 2 `<action>`.

## Known Stubs

None — all methods are fully wired. Integration tests that require `StagedOpRepo.list()` (from Plan 14-01) skip cleanly without Postgres; they are not stubs, they are integration tests awaiting the parallel wave 1 merge.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The `get_async_session_factory()` call is environment-driven from `FORGE_DB_URL`; this is an existing trust boundary documented in the plan's threat model (T-14-02-01). The existing `_lifespan` outer try/except logs only `type(exc).__name__` (never `str(exc)`) per Phase 8 LRN — verified by reading `_lifespan`.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| forge_bridge/console/read_api.py exists | FOUND |
| forge_bridge/mcp/server.py exists | FOUND |
| tests/test_console_read_api.py exists | FOUND |
| Commit 2906a22 (RED tests) exists | FOUND |
| Commit baebfde (GREEN implementation) exists | FOUND |
| Commit 4646e94 (Task 2 _lifespan) exists | FOUND |
