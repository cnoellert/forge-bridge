# Phase 14 (FB-B): Staged Ops MCP Tools + Read API — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 14-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 14 (FB-B) — fb-b-staged-ops-mcp-tools-read-api
**Areas discussed:** all 8 gray areas, condensed into a single recommendation pass per user preference (`feedback_strong_recos_technical.md`)

---

## Discussion Mode

User preference invoked: lead with strong recommendations + rationale instead of presenting neutral menus. After Claude presented the 8 gray areas, user replied: *"I think in these instances your recos are what I'll go with anyway but I'd like to know what they are before committing."*

Claude presented all 8 recommendations in a single pass with rationale. User confirmed: *"All good!"*

All 8 areas resolved in one round. No back-and-forth, no scope creep raised, no override of any recommendation.

---

## Area 1: List Query Surface (STAGED-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Adopt Phase 9 pattern verbatim (single-status, limit/offset, project_id, created_at DESC) | Smallest surface; zero divergence from existing v1.3 dialect; reuses `_parse_pagination` / `_parse_filters` helpers | ✓ |
| Multi-status filter (`?status=proposed,approved`) | Defer — single-status covers both projekt-forge consumer needs (poll-pending, my-recent-executed) | |
| Cursor / keyset pagination (`?after=<id>`) | Defer to v1.5+; volume is expected dozens/day, not millions | |
| Generic `?filter=<jsonpath>` | Rejected — Phase 9 didn't ship one; staged-ops doesn't need one | |

**Locked:** D-01, D-02 in CONTEXT.md.

---

## Area 2: Read/Write Facade Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Extend `ConsoleReadAPI` with `session_factory` + read methods; writes go through `StagedOpRepo` direct from handlers | Preserves Phase 9 D-25 single-read-facade invariant; respects FB-A's "all writers through StagedOpRepo" rule (FB-A D-08); no new abstraction | ✓ |
| Add sibling `ConsoleWriteAPI` for symmetry | Rejected — ceremony with one consumer; adds an abstraction layer no caller asked for | |
| Rename `ConsoleReadAPI → ConsoleAPI` and add mutation methods | Rejected — name collides with the Phase 9 D-25 invariant; muddies the read-only contract that other surfaces depend on | |
| Skip facade entirely; handlers call `StagedOpRepo` directly for everything | Rejected — would break the byte-identity contract D-26 between MCP resource (which has no handler) and HTTP route | |

**Locked:** D-03, D-04, D-05 in CONTEXT.md.

---

## Area 3: Actor Identity Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP: header `X-Forge-Actor` → body `actor` field → default `"http:anonymous"`. MCP: required Pydantic field, no default, non-empty | Three-tier fallback for HTTP (operator-friendly); strict for MCP (clients always know their identity) | ✓ |
| Always require explicit actor in HTTP (no fallback default) | Rejected — would 400 every direct curl call; FB-A D-12 explicitly says any non-empty string accepted in v1.4 | |
| Cookie/session-based identity | Rejected — that's v1.5 SEED-AUTH territory | |
| MCP tool: implicit identity via FastMCP context | Considered but skipped — FastMCP context APIs aren't part of the v1.4 stack and would couple FB-B to FastMCP-specific plumbing | |

**Locked:** D-06, D-07, D-08 in CONTEXT.md.

---

## Area 4: Idempotency on Approve/Reject

| Option | Description | Selected |
|--------|-------------|----------|
| Strict 409 on illegal/duplicate transitions; include `current_status` in error envelope | Honest, debuggable, surfaces programmer errors in retry logic; matches FB-A's underlying state machine | ✓ |
| Idempotent 200 if target status matches current (return current record) | Rejected — silently swallows duplicate approval requests; FB-A's repo never records the duplicate attempt in DBEvent (it raises before commit), so 200 would hide programmer errors from the only place that could surface them | |
| Idempotent only when actor matches | Rejected — over-engineered; v1.4 actors are free strings, no notion of "same caller" yet | |
| 422 Unprocessable Entity instead of 409 | Rejected — 409 Conflict is the canonical HTTP code for state-machine illegal transitions; 422 is for input validation | |

**Locked:** D-09 in CONTEXT.md.

---

## Area 5: HTTP / MCP Error Code Mapping

User accepted the locked table verbatim. Alternatives considered:

| Cause | Selected | Alternatives considered |
|-------|----------|--------------------------|
| Lifecycle violation | 409 `illegal_transition` | 422 `state_error` (rejected — wrong HTTP semantic) |
| Op not found | 404 `staged_op_not_found` | Generic 404 `not_found` (rejected — code namespace conflicts with future entity-type 404s) |
| Bad UUID | 400 `bad_request` | 422 `validation_error` (rejected — handlers don't use 422 elsewhere; consistency over precision) |
| Bad status filter value | 400 `invalid_filter` | Phase 9 uses `bad_request` for everything (rejected — filter-specific code aids client error handling) |
| Empty actor | 400 `bad_actor` | Generic 400 (rejected — explicit code helps callers fix the request) |
| DB / unexpected | 500 `internal_error` | Same as Phase 9 — locked, no alternative considered |

**Locked:** D-10, D-11 in CONTEXT.md.

---

## Area 6: Resource Template Scope (STAGED-07)

| Option | Description | Selected |
|--------|-------------|----------|
| Ship `forge://staged/pending` only + `forge_staged_pending_read` shim (minimum required by STAGED-07) | Tight surface; every resource is a public commitment; matches roadmap success criterion #3 minimum | ✓ |
| Add `forge://staged/{status}` template | Rejected — MCP tool already filters by status; resource is duplicative |  |
| Add `forge://staged/{id}` template | Rejected — `forge_get_staged(id)` MCP tool covers single-op lookup; mirrors the `forge://tools/{name}` pattern but no consumer asked for it |  |

**Locked:** D-12, D-13, D-14 in CONTEXT.md.

---

## Area 7: Tool Naming & Input Shape

User accepted Pydantic input model names and tool names verbatim. Locked:

- Tools: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`, `forge_staged_pending_read`
- Inputs: `ListStagedInput`, `GetStagedInput`, `ApproveStagedInput`, `RejectStagedInput`
- `actor` field: required + non-empty in `ApproveStagedInput` / `RejectStagedInput`
- `status` filter on `ListStagedInput`: `Optional[str] = None` (= all statuses); `forge://staged/pending` resource hardcodes `"proposed"`
- Annotations: `readOnlyHint=True, idempotentHint=True` for reads; `readOnlyHint=False, idempotentHint=False, destructiveHint=False` for writes

**Locked:** D-15, D-16, D-17 in CONTEXT.md.

---

## Area 8: Approval / Reject Reason Capture

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to v1.5 (plant SEED-STAGED-REASON-V1.5) | FB-A's repo signatures don't accept `reason`; v1.5 may want richer `decision_metadata`; actor identity already records "who" | ✓ |
| Add optional `reason: str | None` field to `ApproveStagedInput` / `RejectStagedInput` and store in `attributes.approve_reason` | Rejected — extends FB-A's just-shipped repo retroactively; no consumer asking for it in v1.4 |  |
| Add reason via separate "annotation" event type | Rejected — overengineering for a feature no one is asking for |  |

**Locked:** Deferred section in CONTEXT.md; planner will plant `SEED-STAGED-REASON-V1.5.md`.

---

## Bonus Findings (Codebase Scout)

- **Gap surfaced:** `StagedOpRepo` has no `list()` / `list_by_status()` method. FB-B will add one (D-02). This was flagged to the user as part of the recommendation set; not pushed back on.
- **Lifecycle closure clarification:** Re-reading STAGED-05..07 confirmed only approve/reject are in v1.4 scope. `executed`/`failed` transitions stay as FB-A repo methods callable by projekt-forge directly (or left un-called in v1.4); HTTP/MCP surface for them is deferred to v1.5 (`SEED-STAGED-CLOSURE-V1.5.md`). Captured in `<specifics>` and `<deferred>`.

---

## Claude's Discretion

- Whether the staged-ops handlers live in a new module (`forge_bridge/console/staged_handlers.py`) or are appended to existing `handlers.py` (171 lines — appending may be fine).
- Exact file layout for `StagedOpRepo.list()` extension — same module per FB-A's single-source-of-truth pattern.
- Test file granularity (single `test_staged_handlers.py` vs split list/writes/zero-divergence files).
- Helper function placement for `_resolve_actor(request) -> str` (D-06).
- Whether MCP tool function bodies share a `_handle_staged_action()` internal helper to dedupe HTTP and MCP write paths.
- HTTP write route body parser style (request body JSON vs query-string-only for actor — D-06 covers both).

---

## Deferred Ideas (carried into 14-CONTEXT.md `<deferred>` section)

- `POST /api/v1/staged/{id}/execute` and `/fail` routes (`SEED-STAGED-CLOSURE-V1.5`)
- Approval/reject reason capture (`SEED-STAGED-REASON-V1.5`)
- Multi-status filter
- Resource templates beyond `pending`
- Bulk approve/reject
- Caller-identity bucketing (`SEED-AUTH-V1.5`)
- `staged` CLI subcommands
- Cursor / keyset pagination
