---
phase: 14-fb-b-staged-ops-mcp-tools-read-api
fixed_at: 2026-04-26T00:00:00Z
review_path: .planning/phases/14-fb-b-staged-ops-mcp-tools-read-api/14-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 14 (FB-B): Code Review Fix Report

**Fixed at:** 2026-04-26
**Source review:** .planning/phases/14-fb-b-staged-ops-mcp-tools-read-api/14-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `_to_staged_operation` drops `db.created_at` — all responses return wrong timestamp

**Files modified:** `forge_bridge/store/staged_operations.py`
**Commit:** a9682cf
**Applied fix:** Added `created_at=db.created_at` keyword argument to the `BridgeEntity.__init__` call inside `_to_staged_operation`. Previously the call was `BridgeEntity.__init__(op, id=db.id, metadata={})`, which caused `BridgeEntity.__init__` to default `created_at` to `datetime.utcnow()` on every deserialization. The fix passes the actual DB-stored timestamp so every reconstructed `StagedOperation` carries the real insertion time.

---

### WR-02: Actor whitespace validation gap — HTTP path strips, MCP path does not

**Files modified:** `forge_bridge/mcp/tools.py`
**Commit:** 43dba48
**Applied fix:** Added `field_validator` to the pydantic import line, then added an `actor_not_whitespace_only` `@field_validator("actor")` classmethod to both `ApproveStagedInput` and `RejectStagedInput`. The validator raises `ValueError("actor must not be whitespace-only")` when `v.strip()` is empty, matching the rejection behaviour of `_resolve_actor` in the HTTP path. Whitespace-only strings like `"   "` now fail Pydantic validation before reaching the repo.

---

### WR-03: `_resolve_actor` returns un-stripped header value — leading/trailing whitespace stored in audit trail

**Files modified:** `forge_bridge/console/handlers.py`
**Commit:** aa5671a
**Applied fix:** Changed `return header_val` to `return header_val.strip()` on the header-present branch of `_resolve_actor`. The whitespace-only guard immediately above (`if not header_val.strip(): raise ValueError`) already ensures only non-empty strings reach the return, so stripping here is safe and only removes leading/trailing padding that would otherwise pollute the `approver`, `client_name`, and `payload.actor` audit fields.

---

_Fixed: 2026-04-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
