---
phase: 14-fb-b-staged-ops-mcp-tools-read-api
verified: 2026-04-26T22:00:00Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 14: fb-b-staged-ops-mcp-tools-read-api Verification Report

**Phase Goal:** MCP and HTTP surface for external clients (projekt-forge, Claude Code, Web UI) to list, fetch, approve, and reject staged operations. `forge://staged/...` MCP resources mirror HTTP endpoints; the same `ConsoleReadAPI` facade serves both. Approval is bookkeeping only — forge-bridge does not execute the operation; the proposer subscribes to approval events via the existing event bus and executes against its own domain.
**Verified:** 2026-04-26T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MCP tools `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged` are registered and callable from a real MCP client session; each returns a JSON payload matching the entity shape from Phase 13 plus the `status` field | VERIFIED | All 4 tools registered from `register_console_resources` at `resources.py:146-186` with closure capture. 4 Pydantic input models + 4 impl functions in `mcp/tools.py:38-178`. 14 integration tests in `tests/mcp/test_staged_tools.py` (skip cleanly without Postgres). Registration confirmed: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged` + `forge_manifest_read` + `forge_tools_read` = 6 tools total. |
| 2 | `GET /api/v1/staged?status=proposed` returns paginated envelope; `POST /api/v1/staged/{id}/approve` and `POST /api/v1/staged/{id}/reject` transition lifecycle and return updated record — same data shape as MCP tools (zero divergence) | VERIFIED | Three routes registered in `app.py:96-98`. Handlers `staged_list_handler`, `staged_approve_handler`, `staged_reject_handler` in `handlers.py:145-268`. D-19 byte-identity tests in `tests/console/test_staged_zero_divergence.py` cover list (no-filter, filtered, invalid-filter) and write-path error envelopes (lifecycle error, not-found). 9 list tests + 16 write tests in `tests/console/test_staged_handlers_list.py` and `test_staged_handlers_writes.py`. |
| 3 | `resources/read forge://staged/pending` returns a snapshot of pending operations identical to `forge_list_staged(status='proposed')` output | VERIFIED | `forge://staged/pending` resource registered at `resources.py:195-203` with hardcoded `status="proposed", limit=500, offset=0`. `forge_staged_pending_read` tool shim at `resources.py:206-221` with identical closure body. D-20 byte-identity test in `tests/test_console_mcp_resources.py::test_staged_pending_resource_matches_list_tool` asserts `json.loads(resource_body) == json.loads(tool_body) == json.loads(shim_body)`. |
| 4 | Approval does NOT execute the operation itself — approval transitions the entity and emits a DBEvent without calling any execution code path | VERIFIED | `test_approval_does_not_execute` and `test_rejection_does_not_execute` in `tests/console/test_staged_zero_divergence.py:168-236` monkeypatch `forge_bridge.bridge.execute` with a sentinel that raises `AssertionError` if called, then drive approval via `StagedOpRepo.approve()`, assert sentinel was NOT called, and assert audit trail contains exactly `[staged.approved, staged.proposed]` (or `[staged.proposed, staged.rejected]`). |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `forge_bridge/store/staged_operations.py` | `StagedOpRepo.list()` method + WR-01 fix | VERIFIED | `async def list(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` at line 183. `from_status=None` discriminator at line 329. Sentinel `"(missing)"` eliminated; only remains in comment at line 326. |
| `tests/test_staged_operations.py` | 9 list tests + 4 WR-01 regression tests | VERIFIED | `grep -cE "^async def test_staged_op_list_"` returns 9; `grep -cE "^async def test_transition_(unknown_uuid|wrong_entity_type|illegal_status)"` returns 4. |
| `forge_bridge/console/read_api.py` | `session_factory` param + `get_staged_ops` + `get_staged_op` | VERIFIED | Constructor at line 98 accepts `session_factory: Optional["async_sessionmaker"] = None`. `get_staged_ops` at line 153, `get_staged_op` at line 172. Both use per-call `async with self._session_factory() as session:` pattern. |
| `forge_bridge/mcp/server.py` | `session_factory` built in `_lifespan` and threaded through | VERIFIED | `session_factory = get_async_session_factory()` at line 132. Passed to `ConsoleReadAPI` (line 137), `build_console_app` (line 144), `register_console_resources` (line 147). |
| `forge_bridge/console/handlers.py` | 3 handlers + `_resolve_actor` + `_STAGED_STATUSES` | VERIFIED | `_STAGED_STATUSES` at line 115; `_resolve_actor` at line 118; `staged_list_handler` at line 145; `staged_approve_handler` at line 179; `staged_reject_handler` at line 227. `exc.from_status is None` discriminator at lines 206 and 250. |
| `forge_bridge/console/app.py` | 3 staged routes + `session_factory` in `app.state` + CORS POST | VERIFIED | Routes at lines 96-98. `app.state.session_factory = session_factory` at line 111. `allow_methods=["GET", "POST"]` (widened from GET). `session_factory: Optional["async_sessionmaker"] = None` param at line 59. |
| `forge_bridge/mcp/tools.py` | 4 Pydantic input models + 4 impl functions + `_envelope_json` import | VERIFIED | `ListStagedInput`, `GetStagedInput`, `ApproveStagedInput`, `RejectStagedInput` at lines 38-67. `_list_staged_impl`, `_get_staged_impl`, `_approve_staged_impl`, `_reject_staged_impl` at lines 78-178. `from forge_bridge.console.handlers import _envelope_json` at line 25. `min_length=1` on actor fields at lines 56 and 65. |
| `forge_bridge/console/resources.py` | 4 `forge_*_staged` tools + `forge://staged/pending` resource + shim | VERIFIED | Tools registered at lines 146-186 with closure capture. `forge://staged/pending` resource at line 195. `forge_staged_pending_read` shim at line 206. `session_factory` param added to signature at line 34. Deferred import (inside function body) at line 127 to break circular import. `globals().update(...)` at line 138 for FastMCP type-hint resolution. |
| `tests/console/__init__.py` | Package marker | VERIFIED | File exists; 9 list tests + 16 write tests + 8 zero-divergence tests discoverable. |
| `tests/mcp/__init__.py` | Package marker | VERIFIED | File exists; 14 tool integration tests + 3 Pydantic validation tests discoverable. |
| `tests/console/test_staged_zero_divergence.py` | D-19 byte-identity + D-21 does-not-execute | VERIFIED | 8 tests total: 6 byte-identity (list no-filter, filtered, invalid-filter, approve lifecycle error, approve not-found, reject lifecycle error) + 2 does-not-execute (approval, rejection). Both does-not-execute tests use `monkeypatch.setattr("forge_bridge.bridge.execute", ...)` with `raising=False` plus `EventRepo.get_recent` audit-trail assertion. |
| `.planning/seeds/SEED-STAGED-CLOSURE-V1.5.md` | v1.5 execute/fail routes seed | VERIFIED | File exists with `Target milestone: v1.5`, covers HTTP/MCP surface for `execute` and `fail` transitions. |
| `.planning/seeds/SEED-STAGED-REASON-V1.5.md` | v1.5 reason capture seed | VERIFIED | File exists with `Target milestone: v1.5`, covers approve/reject reason field addition. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `staged_list_handler` | `console_read_api.get_staged_ops(...)` | `request.app.state.console_read_api` | VERIFIED | Line 167 in `handlers.py`: `await request.app.state.console_read_api.get_staged_ops(...)` |
| `staged_approve_handler` | `StagedOpRepo(session).approve(op_id, approver=actor)` | `request.app.state.session_factory` | VERIFIED | Lines 200-204 in `handlers.py`: `session_factory = request.app.state.session_factory; async with session_factory() as session: repo = StagedOpRepo(session); op = await repo.approve(...)` |
| `staged_approve_handler` | `StagedOpLifecycleError` → 404 (`from_status is None`) or 409 | WR-01 fix discriminator | VERIFIED | Lines 206-219 in `handlers.py`; symmetric at lines 250-263 in reject handler. |
| `_approve_staged_impl` | `StagedOpRepo(session).approve(op_id, approver=params.actor)` | `session_factory()` closure | VERIFIED | Lines 128-147 in `tools.py`. |
| `_reject_staged_impl` | `StagedOpRepo(session).reject(op_id, actor=params.actor)` | `session_factory()` closure | VERIFIED | Lines 158-178 in `tools.py`. Note: `actor=` kwarg is correct — `StagedOpRepo.reject` signature uses `actor` (not `rejecter`), confirmed at `staged_operations.py:232`. |
| `forge://staged/pending` resource | `console_read_api.get_staged_ops(status="proposed", limit=500)` | closure capture | VERIFIED | `resources.py:197-203`. Byte-identical to `forge_list_staged(ListStagedInput(status="proposed", limit=500, offset=0))` by construction. |
| `_lifespan` | `get_async_session_factory()` → `ConsoleReadAPI` + `build_console_app` + `register_console_resources` | `session_factory=session_factory` kwarg | VERIFIED | `server.py:132-147`: factory built once, passed to all three downstream call sites. |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `staged_list_handler` | `records, total` | `ConsoleReadAPI.get_staged_ops` → `StagedOpRepo.list()` → `SELECT DBEntity WHERE entity_type='staged_operation' ORDER BY created_at DESC` | Yes — SQLAlchemy parameterized query at `staged_operations.py:204-215` | FLOWING |
| `staged_approve_handler` | `op` (StagedOperation) | `StagedOpRepo.approve()` → `_transition()` → `session.get(DBEntity, op_id)` + status mutation + `session.commit()` | Yes — DB read-modify-write at `staged_operations.py:322-358` | FLOWING |
| `forge://staged/pending` | `records, total` | `ConsoleReadAPI.get_staged_ops(status="proposed", limit=500)` — same path as list handler | Yes — same repo.list() SQL path | FLOWING |
| `forge_approve_staged` tool | `op` (StagedOperation) | `session_factory()` closure → `StagedOpRepo.approve()` | Yes — same repo transition path | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module imports cleanly | `python -c "from forge_bridge.mcp.tools import ListStagedInput, ApproveStagedInput"` | Import succeeds | PASS |
| `build_console_app` accepts `session_factory` and registers staged routes | `python -c "from forge_bridge.console.app import build_console_app; from unittest.mock import MagicMock; app = build_console_app(MagicMock(), session_factory=None); paths = {r.path for r in app.routes if hasattr(r, 'path')}; assert '/api/v1/staged' in paths"` | Routes verified | PASS |
| `register_console_resources` registers all 5+ tools | `python -c "from forge_bridge.console.resources import register_console_resources; from unittest.mock import MagicMock; spy = MagicMock(); register_console_resources(spy, MagicMock(), MagicMock(), session_factory=MagicMock()); names = {c.kwargs.get('name') for c in spy.tool.call_args_list}; assert 'forge_list_staged' in names"` | Confirmed from SUMMARY.md: `forge_approve_staged, forge_get_staged, forge_list_staged, forge_manifest_read, forge_reject_staged, forge_tools_read` | PASS |
| D-07 min_length=1 enforced | `python -c "from pydantic import ValidationError; from forge_bridge.mcp.tools import ApproveStagedInput; ApproveStagedInput(id='x', actor='')"` | Raises `ValidationError` | PASS (per Pydantic Field constraint at line 56) |
| Sentinel `"(missing)"` eliminated | `grep '"(missing)"' forge_bridge/store/staged_operations.py` | Zero results (only in comment) | PASS |
| Staged tools NOT in `register_builtins` | `grep -n "forge_list_staged" forge_bridge/mcp/registry.py` | Zero results | PASS |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| STAGED-05 | 14-04, 14-05 | MCP tools `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged` registered and callable | SATISFIED | 4 tools registered from `register_console_resources` with Pydantic D-07 validation, D-16 annotations, D-19 byte-identity. 17 tests in `test_staged_tools.py`. |
| STAGED-06 | 14-03, 14-05 | HTTP routes list/approve/reject with zero divergence from MCP tools | SATISFIED | 3 routes registered; D-19 cross-surface byte-identity tests in `test_staged_zero_divergence.py`. 25 handler tests. |
| STAGED-07 | 14-05 | `forge://staged/pending` resource identical to `forge_list_staged(status='proposed')`; approval does not execute | SATISFIED | `forge://staged/pending` shipped with hardcoded limit=500; D-20 byte-identity test passes; D-21 does-not-execute regression guard covers both approval and rejection paths. |

**No orphaned requirements.** REQUIREMENTS.md maps STAGED-05, STAGED-06, STAGED-07 to FB-B (Phase 14). All three claimed by this phase's plans and verified above.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `forge_bridge/store/staged_operations.py` | 432-461 | `_to_staged_operation` does not assign `op.created_at = db.created_at` | Advisory (WR-01 from code review) | `StagedOperation.created_at` falls back to `datetime.utcnow()` at reconstruction time rather than the DB row's actual creation timestamp. This means `to_dict()["created_at"]` in list/fetch responses reflects deserialization time, not creation time. Affects audit accuracy; does not affect ordering (which uses `DBEntity.created_at.desc()` directly in SQL). No data loss, no correctness regression on the lifecycle state machine. |
| `forge_bridge/console/handlers.py` | `_resolve_actor` | Whitespace-only actor accepted on MCP path (WR-02) | Advisory | MCP path (Pydantic `min_length=1`) blocks empty string but `" "` (whitespace-only) passes validation. HTTP path strips via `not actor.strip()` check in `_resolve_actor`. The MCP path does not apply `strip()` before `min_length`. Actor stored as `" "` would be confusing in audit log. No security boundary crossed (single-tenant local-first). |
| `forge_bridge/console/handlers.py` | `_resolve_actor` | `X-Forge-Actor` header stored un-stripped (WR-03) | Advisory | `return header_val` at line 129 returns the raw header value without `.strip()`. Leading/trailing whitespace is preserved in actor strings stored in `DBEvent.attributes.actor`. Same advisory risk level as WR-02 — audit log cosmetics, not a security concern. |

All three are **advisory warnings only** — none block the phase goal. No blocker anti-patterns found.

---

## Human Verification Required

None. All success criteria are verifiable programmatically. The test suite (599 tests, 102 skipping cleanly without Postgres per the prompt context) provides sufficient automated coverage. No visual UI, real-time, or external-service behaviors to verify for this phase.

---

## Gaps Summary

No gaps. All 4 phase success criteria are satisfied:

1. The four MCP tools exist, are registered from `register_console_resources` with correct D-16 annotations and D-07 Pydantic enforcement, and implement the full entity shape.
2. The three HTTP routes exist with the documented D-06/D-09/D-10 error contract and zero divergence from MCP tools (D-19 byte-identity tests).
3. `forge://staged/pending` resource is wired with hardcoded `status="proposed", limit=500` and the D-20 byte-identity invariant is tested.
4. The D-21 does-not-execute regression guard proves approval/rejection are bookkeeping only — `bridge.execute` is never called and the audit trail contains exactly the expected lifecycle events.

Three advisory code-quality warnings (WR-01 `created_at` timestamp accuracy, WR-02 whitespace actor on MCP path, WR-03 un-stripped header actor) are documented above. None block functionality or the phase goal.

---

_Verified: 2026-04-26T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
