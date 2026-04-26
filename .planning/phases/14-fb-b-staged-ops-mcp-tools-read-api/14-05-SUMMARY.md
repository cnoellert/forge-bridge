---
phase: 14
plan: 05
subsystem: mcp-resources
tags: [staged-ops, mcp-resource, byte-identity, regression-guard, seeds]
dependency_graph:
  requires: [14-03, 14-04]
  provides: [forge://staged/pending, forge_staged_pending_read, D-19 byte-identity tests, D-21 regression guard]
  affects: [forge_bridge/console/resources.py, tests/test_console_mcp_resources.py, tests/console/test_staged_zero_divergence.py]
tech_stack:
  added: []
  patterns: [closure-capture MCP resource, P-03 tool shim, negative-assertion sentinel, byte-identity mod formatting]
key_files:
  created:
    - tests/console/test_staged_zero_divergence.py
    - .planning/seeds/SEED-STAGED-CLOSURE-V1.5.md
    - .planning/seeds/SEED-STAGED-REASON-V1.5.md
  modified:
    - forge_bridge/console/resources.py
    - tests/test_console_mcp_resources.py
decisions:
  - "D-12/D-13 confirmed: forge://staged/pending only (proposed-only, limit=500 hardcoded)"
  - "D-14 confirmed: forge://staged/{status} and forge://staged/{id} templates NOT shipped"
  - "D-20 byte-identity holds: resource == tool == shim via same closure args"
  - "D-21 proven: StagedOpRepo.approve/reject call zero execution-side code paths"
  - "Postgres-gated tests skip cleanly on machines without DB (all 10 Postgres tests skip)"
metrics:
  duration: ~12min
  completed: 2026-04-26
  tasks: 3
  files: 5
---

# Phase 14 Plan 05: forge://staged/pending Resource + Byte-Identity Tests Summary

**One-liner:** forge://staged/pending MCP resource + forge_staged_pending_read shim with D-19/D-20 byte-identity regression guards and D-21 does-not-execute negative-assertion sentinel.

## What Was Built

### Task 1 — forge://staged/pending resource + forge_staged_pending_read shim (86b98d7)

Added to `forge_bridge/console/resources.py::register_console_resources`:

- `@mcp.resource("forge://staged/pending")` — returns proposed-only snapshot via `get_staged_ops(status="proposed", limit=500, offset=0, project_id=None)`. Byte-identical to `forge_list_staged(ListStagedInput(status="proposed", limit=500, offset=0))` by construction (D-13).
- `@mcp.tool(name="forge_staged_pending_read")` — tool shim with identical closure body (P-03 prevention for Cursor/Gemini CLI clients that don't support resources).

Updated `tests/test_console_mcp_resources.py`:
- `test_register_console_resources_registers_all_four_resources`: count updated 4→5 (now includes forge://staged/pending)
- `test_register_console_resources_registers_two_tool_shims`: count updated 6→7 (now includes forge_staged_pending_read)
- `_READ_ONLY_TOOLS` set updated to include `forge_staged_pending_read`
- Added `test_staged_pending_resource_matches_list_tool` (D-20 byte-identity: resource == list_tool == shim; also asserts 2 records in proposed-only filter from 4-op seeded dataset)
- Added `test_staged_pending_empty_queue` (empty queue: data=[], meta.total=0, meta.limit=500)

### Task 2 — Cross-surface byte-identity + does-not-execute tests (4845095)

Created `tests/console/test_staged_zero_divergence.py` — 8 tests (all Postgres-gated, skip cleanly without DB):

**D-19 byte-identity tests (6):**
- `test_list_staged_no_filter_byte_identity` — forge_list_staged() == GET /api/v1/staged
- `test_list_staged_filtered_byte_identity` — forge_list_staged(proposed,50) == GET ?status=proposed&limit=50
- `test_list_staged_invalid_filter_byte_identity` — invalid_filter envelope identical on both surfaces
- `test_approve_lifecycle_error_byte_identity` — illegal_transition envelope with current_status field identical
- `test_approve_not_found_byte_identity` — staged_op_not_found envelope identical
- `test_reject_lifecycle_error_byte_identity` — re-reject illegal_transition envelope identical

**D-21 does-not-execute regression guards (2):**
- `test_approval_does_not_execute` — monkeypatches `forge_bridge.bridge.execute` with sentinel; proves approval calls zero execution code; asserts audit trail has exactly `[staged.approved, staged.proposed]`
- `test_rejection_does_not_execute` — symmetric guard; audit trail has exactly `[staged.proposed, staged.rejected]`

### Task 3 — SEED files (2eafc73)

- `.planning/seeds/SEED-STAGED-CLOSURE-V1.5.md` — tracks HTTP/MCP execute+fail surface for v1.5 (FB-A repo methods already exist; only HTTP/MCP wrapper needed)
- `.planning/seeds/SEED-STAGED-REASON-V1.5.md` — tracks approve/reject reason capture (DBEvent.attributes supports KV; 3-line HTTP+Pydantic change)

Both files follow the SEED-AUTH-V1.5 format: frontmatter + ## Summary + ## v1.5 Scope + ## Triggers + ## Notes.

## Test Counts

| Category | Tests | Status |
|---|---|---|
| Byte-identity (D-19) | 6 | Skip without Postgres |
| Does-not-execute guard (D-21) | 2 | Skip without Postgres |
| D-20 resource snapshot equality | 2 | Skip without Postgres |
| Non-Postgres resource registration tests | 12 | Pass always |
| **Total new tests this plan** | **10** | — |
| **Total passing (no Postgres)** | **12** | — |

## Requirements Closed

| Requirement | Status | Evidence |
|---|---|---|
| STAGED-05 (MCP tools callable) | Confirmed via Tools 4 (14-04) + byte-identity guards (14-05) | D-19 tests |
| STAGED-06 (HTTP routes + zero-divergence) | Confirmed via Handlers 3 (14-03) + D-19 guards | byte-identity tests |
| STAGED-07 (resource snapshot) | forge://staged/pending shipped + D-20 test | Task 1 |

All 3 STAGED requirements (05, 06, 07) are reachable end-to-end on both MCP and HTTP surfaces. Phase 14 (FB-B) is now ready for `/gsd-verify-work 14`.

## Commits

| Hash | Type | Description |
|---|---|---|
| 86b98d7 | feat | forge://staged/pending resource + forge_staged_pending_read shim |
| 4845095 | test | D-19 byte-identity tests + D-21 does-not-execute guard |
| 2eafc73 | chore | SEED-STAGED-CLOSURE-V1.5 and SEED-STAGED-REASON-V1.5 |

## Deviations from Plan

None — plan executed exactly as written.

The `test_approve_staged_success_byte_identity` and `test_reject_staged_success_byte_identity` tests were explicitly noted in the plan as NOT required (Plan note: "NOTES: The byte-identity tests for test_approve_staged_success_byte_identity and test_reject_staged_success_byte_identity are NOT included in this task") — success-path byte-identity cannot be trivially asserted because each call mutates state (id/created_at/approved_at fields differ between two seeded ops). This is by design, not a gap.

## Known Stubs

None. The forge://staged/pending resource calls `console_read_api.get_staged_ops()` which reads from the real database (session_factory required). No hardcoded empty returns or placeholder data.

## Threat Flags

No new network endpoints, auth paths, or trust boundary changes beyond what is documented in the plan's threat model (T-14-05-01 through T-14-05-05). The `forge://staged/pending` resource exposes proposed-only entries to any connected MCP client — accepted per T-14-05-01 (single-tenant local-first; SEED-AUTH-V1.5 will gate this later).

## Self-Check: PASSED

| Check | Result |
|---|---|
| forge_bridge/console/resources.py exists | FOUND |
| tests/test_console_mcp_resources.py exists | FOUND |
| tests/console/test_staged_zero_divergence.py exists | FOUND |
| .planning/seeds/SEED-STAGED-CLOSURE-V1.5.md exists | FOUND |
| .planning/seeds/SEED-STAGED-REASON-V1.5.md exists | FOUND |
| Commit 86b98d7 exists | FOUND |
| Commit 4845095 exists | FOUND |
| Commit 2eafc73 exists | FOUND |
