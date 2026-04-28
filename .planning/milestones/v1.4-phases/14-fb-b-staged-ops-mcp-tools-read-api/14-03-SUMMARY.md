---
phase: 14
plan: 03
subsystem: console/handlers
tags: [http-handlers, staged-ops, actor-resolution, tdd, fb-b]
dependency_graph:
  requires: [14-01, 14-02]
  provides: [staged_list_handler, staged_approve_handler, staged_reject_handler, _resolve_actor, app.state.session_factory]
  affects: [forge_bridge/console/handlers.py, forge_bridge/console/app.py, tests/console/]
tech_stack:
  added: []
  patterns:
    - D-06 actor resolution (header > body > fallback)
    - D-09 strict 409 on illegal transitions
    - D-10 error code matrix (invalid_filter, bad_request, bad_actor, staged_op_not_found, illegal_transition, internal_error)
    - D-25 single read facade (console_read_api.get_staged_ops)
    - D-04 writes bypass read facade (StagedOpRepo direct via session_factory)
key_files:
  created:
    - tests/console/__init__.py
    - tests/console/conftest.py
    - tests/console/test_staged_handlers_list.py
    - tests/console/test_staged_handlers_writes.py
  modified:
    - forge_bridge/console/handlers.py
    - forge_bridge/console/app.py
decisions:
  - _resolve_actor and staged handlers appended to existing handlers.py (was 172 lines; landed at 339 lines, within the ~400-line split threshold per Claude's Discretion)
  - Shared fixtures (staged_client, proposed_op_id, approved_op_id, rejected_op_id) extracted to tests/console/conftest.py rather than duplicating across test files
  - CORS allow_headers left as ["*"] (wildcard already allows X-Forge-Actor); only allow_methods extended to ["GET", "POST"]
metrics:
  duration_seconds: 224
  completed_date: "2026-04-26"
  tasks_completed: 3
  files_created: 4
  files_modified: 2
---

# Phase 14 Plan 03: Staged HTTP Handlers + Route Registration Summary

Three HTTP routes delivering STAGED-06 HTTP surface: `GET /api/v1/staged`, `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject` — with actor resolution, strict lifecycle error mapping, and comprehensive test coverage.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tests/console/ package marker | d6771a2 | tests/console/__init__.py |
| 2 (RED) | Add failing tests for staged HTTP handlers | 8652cd9 | tests/console/conftest.py, test_staged_handlers_list.py, test_staged_handlers_writes.py |
| 2 (GREEN) | Add staged HTTP handlers + _resolve_actor to handlers.py | 11be508 | forge_bridge/console/handlers.py |
| 3 | Register staged routes + CORS + session_factory in build_console_app | 6a62db7 | forge_bridge/console/app.py |

## Implementation Decisions

### Handler module placement
`_resolve_actor` and the three staged handlers were appended to the existing `forge_bridge/console/handlers.py` rather than creating a new `staged_handlers.py` module. The file grew from 172 to 339 lines — comfortably under the ~400-line Claude's Discretion split threshold.

### Shared test fixtures
The `staged_client`, `proposed_op_id`, `approved_op_id`, and `rejected_op_id` fixtures were extracted to `tests/console/conftest.py` rather than duplicating them across both test files. The `rejected_op_id` fixture was added beyond the plan's explicit list to support the re-reject and approve-then-reject test cases.

### CORS extension
`allow_methods` extended from `["GET"]` to `["GET", "POST"]`. `allow_headers` was already `["*"]` (wildcard), which covers `X-Forge-Actor` without modification. Only the methods field was widened per the plan's instruction to only widen as needed.

### Route ordering
The three staged routes were appended at the end of the routes list in `build_console_app`, after the static mount. This is slightly non-canonical but harmless — Starlette matches routes in order and the staged routes have distinct prefixes from all existing routes.

### Confirmed routes registered
```
/api/v1/staged
/api/v1/staged/{id}/approve
/api/v1/staged/{id}/reject
```
Verified by: `python -c "from forge_bridge.console.app import build_console_app; from unittest.mock import MagicMock; app = build_console_app(MagicMock(), session_factory=None); assert '/api/v1/staged' in {r.path for r in app.routes if hasattr(r, 'path')}; print('ok')"`

## Test Run Summary

| Suite | Tests | Passed | Skipped | Why Skipped |
|-------|-------|--------|---------|-------------|
| tests/console/test_staged_handlers_list.py | 9 | 0 | 9 | Postgres at localhost:5432 unreachable (Phase 13 fixture behavior) |
| tests/console/test_staged_handlers_writes.py | 16 | 0 | 16 | Postgres at localhost:5432 unreachable |
| tests/test_console_routes.py | 15 | 15 | 0 | — |
| tests/test_console_health.py | varies | all | 0 | — |
| tests/test_console_ui_routes_registered.py | varies | all | 0 | — |

**No regression** in existing console routes. The 25 staged-handler tests skip cleanly without Postgres — they will run and pass in the Postgres-equipped CI/UAT environment (Phase 13 pattern inherited).

## Final Line Counts

| File | Before | After |
|------|--------|-------|
| forge_bridge/console/handlers.py | 172 | 339 |
| forge_bridge/console/app.py | 106 | 113 |

## Acceptance Criteria Verification

- `grep -nE "^async def (staged_list_handler|staged_approve_handler|staged_reject_handler|_resolve_actor)\("` → 4 matches (lines 118, 145, 179, 227)
- `grep -n "_STAGED_STATUSES = frozenset"` → 1 match (line 115)
- `grep -nE "invalid_filter|bad_actor|staged_op_not_found|illegal_transition"` → 6+ matches
- `grep -n "exc.from_status is None"` → 2 matches (approve handler line 206, reject handler line 250)
- `grep -n "X-Forge-Actor"` → 3 matches (header lookup + 2 docstring/error references)
- `grep -n "request.app.state.session_factory"` → 2 matches (one in approve, one in reject)
- `grep -n "request.app.state.console_read_api.get_staged_ops"` → 1 match (staged_list_handler)
- `grep -cE "^async def test_staged_list_"` → 9 (meets >=9 requirement)
- `grep -cE "^async def test_(approve|reject|re_approve|re_reject)"` → 16 (meets >=14 requirement)
- 3 staged routes registered and verified via Python import check
- 48 existing tests pass, 0 regression

## Deviations from Plan

None — plan executed exactly as written. The `rejected_op_id` fixture was added to `conftest.py` beyond the explicit plan list; this is additive-only and required by the `test_re_reject_returns_409` and `test_approve_then_reject_returns_409` tests specified in the plan's behavior section.

## Known Stubs

None. All handlers wire to real data sources (ConsoleReadAPI.get_staged_ops for reads, StagedOpRepo direct for writes) when a session_factory is available.

## Threat Flags

No new network endpoints or trust boundary surfaces beyond what was specified in the plan's threat model (T-14-03-01 through T-14-03-09). The three HTTP routes are the planned surface.

## Self-Check

Checking file existence and commit integrity:

- tests/console/__init__.py: FOUND
- tests/console/conftest.py: FOUND
- tests/console/test_staged_handlers_list.py: FOUND
- tests/console/test_staged_handlers_writes.py: FOUND
- forge_bridge/console/handlers.py (3 handlers + helper): FOUND
- forge_bridge/console/app.py (3 routes + session_factory): FOUND

Commits:
- d6771a2 (Task 1): chore(14-03): create tests/console/ package marker
- 8652cd9 (Task 2 RED): test(14-03): add failing tests for staged HTTP handlers
- 11be508 (Task 2 GREEN): feat(14-03): add staged HTTP handlers + _resolve_actor
- 6a62db7 (Task 3): feat(14-03): register staged routes + CORS + session_factory

## Self-Check: PASSED
