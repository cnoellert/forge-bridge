---
phase: 14-fb-b-staged-ops-mcp-tools-read-api
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - forge_bridge/console/app.py
  - forge_bridge/console/handlers.py
  - forge_bridge/console/read_api.py
  - forge_bridge/console/resources.py
  - forge_bridge/mcp/server.py
  - forge_bridge/mcp/tools.py
  - forge_bridge/store/staged_operations.py
  - tests/console/__init__.py
  - tests/console/conftest.py
  - tests/console/test_staged_handlers_list.py
  - tests/console/test_staged_handlers_writes.py
  - tests/console/test_staged_zero_divergence.py
  - tests/mcp/__init__.py
  - tests/mcp/test_staged_tools.py
  - tests/test_console_mcp_resources.py
  - tests/test_console_read_api.py
  - tests/test_staged_operations.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 14 (FB-B): Code Review Report

**Reviewed:** 2026-04-26
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 14 (FB-B) ships the read-side query methods (`ConsoleReadAPI.get_staged_ops` / `get_staged_op`), three new HTTP routes (`GET /api/v1/staged`, `POST .../approve|reject`), four `forge_*_staged` MCP tools, and the `forge://staged/pending` resource. The state machine and atomicity model from Phase 13 (FB-A) are well-designed and the D-06 actor-priority logic is correctly structured.

Three warnings were found, one of which is a data correctness bug that will cause every deserialized `StagedOperation` to report `created_at` as the time of deserialization rather than the actual DB insertion timestamp. This corrupts a key sort field and all API response timestamps for staged operations.

No security vulnerabilities were found. SQL injection is correctly blocked by SQLAlchemy parameterized queries throughout. Actor input is validated at both the HTTP and MCP boundaries. No hardcoded credentials or path traversal patterns exist.

---

## Warnings

### WR-01: `_to_staged_operation` drops `db.created_at` — all responses return wrong timestamp

**File:** `forge_bridge/store/staged_operations.py:447`

**Issue:** `_to_staged_operation` reconstructs a `StagedOperation` via `BridgeEntity.__init__(op, id=db.id, metadata={})` without passing `created_at=db.created_at`. `BridgeEntity.__init__` defaults `created_at` to `datetime.utcnow()` when `None` is passed (see `core/entities.py:67`). Every record returned by `StagedOpRepo.get`, `StagedOpRepo.list`, `ConsoleReadAPI.get_staged_ops`, and `ConsoleReadAPI.get_staged_op` will report `created_at` as the deserialization timestamp rather than the DB insertion timestamp. This affects:

- Every `GET /api/v1/staged` response (`to_dict()` includes `created_at` via `super().to_dict()`)
- Every `POST .../approve|reject` response (the returned `op` comes from `_transition` which calls `_to_staged_operation`)
- All four MCP tool responses
- The `forge://staged/pending` resource
- The ordering test `test_staged_list_orders_by_created_at_desc`: it compares the JSON `created_at` values, but since all records in a single handler invocation are deserialized within milliseconds of each other, the `created_at` comparisons are essentially comparing noise — the test can pass even if DB ordering is wrong.

**Fix:**
```python
# forge_bridge/store/staged_operations.py, _to_staged_operation, line 447
# Change:
BridgeEntity.__init__(op, id=db.id, metadata={})
# To:
BridgeEntity.__init__(op, id=db.id, created_at=db.created_at, metadata={})
```

---

### WR-02: Actor whitespace validation gap — HTTP path strips, MCP path does not

**File:** `forge_bridge/mcp/tools.py:54-66`

**Issue:** The HTTP handler `_resolve_actor` (handlers.py:127-138) rejects actors that are whitespace-only (`not actor.strip()`). The MCP `ApproveStagedInput` and `RejectStagedInput` models use `min_length=1`, which Pydantic applies on raw length before stripping — a `"   "` (spaces-only) actor string passes Pydantic validation and reaches `repo.approve(op_id, approver="   ")`. The audit trail then records a whitespace-only identity, which is semantically indistinguishable from an anonymous actor. The HTTP path correctly rejects this with `400 bad_actor`; the MCP path silently accepts it.

**Fix:**
```python
# forge_bridge/mcp/tools.py — ApproveStagedInput and RejectStagedInput
from pydantic import BaseModel, Field, field_validator

class ApproveStagedInput(BaseModel):
    id: str = Field(..., description="Staged operation UUID")
    actor: str = Field(
        ...,
        min_length=1,
        description="Caller identity (free string, non-empty per D-07)",
    )

    @field_validator("actor")
    @classmethod
    def actor_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("actor must not be whitespace-only")
        return v
```

Apply the same validator to `RejectStagedInput`.

---

### WR-03: `_resolve_actor` returns un-stripped header value — leading/trailing whitespace stored in audit trail

**File:** `forge_bridge/console/handlers.py:127-129`

**Issue:** `_resolve_actor` correctly rejects a whitespace-only `X-Forge-Actor` header (line 127: `if not header_val.strip(): raise ValueError`), but then returns the original `header_val` rather than `header_val.strip()` (line 129). A header value like `"  alice  "` passes the not-empty check and is returned as-is. The padded string is then stored as the `approver` field in the DB attributes JSONB and in the DBEvent `client_name` and `payload.actor` fields. This creates inconsistent audit records when the same actor submits via different clients that trim or don't trim whitespace.

**Fix:**
```python
# forge_bridge/console/handlers.py, _resolve_actor, line 129
# Change:
return header_val
# To:
return header_val.strip()
```

---

## Info

### IN-01: `globals().update(...)` in `register_console_resources` is a sharp edge for multi-registration

**File:** `forge_bridge/console/resources.py:138-143`

**Issue:** `register_console_resources` mutates module-level globals with `globals().update({...})` to inject Pydantic input model names for FastMCP's `get_type_hints()` resolution. The comment explains this is a FastMCP requirement when `from __future__ import annotations` keeps annotations as strings. The approach works, but `globals()` returns the module's `__dict__` and mutations persist across calls. If `register_console_resources` is called more than once (e.g., in tests using `_ResourceSpy` — which it is, multiple times), the globals are overwritten with the same values on each call, which is benign today. The risk is that a future refactor introduces a different `ListStagedInput` for a different use-case, and the global clobbers the previous registration silently.

**Suggestion:** Document this limitation with a `# NOTE: idempotent only because the model classes are module-level singletons` comment, or use `fn.__globals__["ListStagedInput"] = ListStagedInput` directly on each registered function instead of the module-level globals dict.

---

### IN-02: Unused `import time` in test file

**File:** `tests/console/test_staged_handlers_list.py:12`

**Issue:** `import time` is imported but never referenced in the file. `asyncio.sleep` is used for the ordering test delay instead.

**Fix:** Remove line 12: `import time`.

---

### IN-03: Redundant `@pytest.mark.asyncio` decorators in `tests/mcp/test_staged_tools.py`

**File:** `tests/mcp/test_staged_tools.py:76,100,109,118,129,138,148,157,169,186,198,209,220,237`

**Issue:** `pyproject.toml` sets `asyncio_mode = "auto"`, which makes `@pytest.mark.asyncio` unnecessary on every `async def test_*` function. All integration test functions in this file carry the decorator, while the sibling test files (`test_staged_handlers_list.py`, `test_staged_handlers_writes.py`, `test_staged_zero_divergence.py`) correctly omit it. The decorators are harmless but create inconsistent style across the test suite.

**Fix:** Remove the 14 `@pytest.mark.asyncio` decorators from `tests/mcp/test_staged_tools.py`. The tests will still run identically under `asyncio_mode = "auto"`.

---

_Reviewed: 2026-04-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
