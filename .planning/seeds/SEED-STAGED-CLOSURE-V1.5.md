---
name: SEED-STAGED-CLOSURE-V1.5
description: HTTP/MCP surface for execute/fail lifecycle transitions deferred from FB-B
type: forward-looking-idea
planted_during: Phase 14 (FB-B) close — 2026-04-26
trigger_when: A consumer asks for HTTP/MCP lifecycle closure (execute/fail transitions)
---

# SEED-STAGED-CLOSURE-V1.5 — Lifecycle Closure HTTP/MCP Surface

**Planted:** 2026-04-26 (Phase 14 / FB-B close)
**Deferred from:** Phase 14 (FB-B) — CONTEXT D-14 / Deferred Ideas
**Target milestone:** v1.5

## Summary

The staged-operation lifecycle has 5 states: `proposed → approved → executed/failed`
plus `proposed → rejected`. v1.4 (FB-B) ships HTTP and MCP surfaces for `approve` and
`reject` only. The `execute` and `fail` transitions are FB-A repository methods
(`StagedOpRepo.execute`, `StagedOpRepo.fail`) but have no v1.4 HTTP/MCP surface.

For v1.4, the v1.5 consumer (projekt-forge Flame hooks) writes the `executed`/`failed`
transitions by calling `StagedOpRepo` directly via the Python API (it has `forge-bridge`
as a pip dep). Or the staged_operation row simply stays at `approved` forever — the
audit log captures who approved what, and projekt-forge's own DB tracks completion.

## v1.5 Scope

When v1.5 lands, ship:
- `POST /api/v1/staged/{id}/execute` — accepts optional `result` JSONB body; transitions
  approved → executed; emits `staged.executed` DBEvent. Same actor-resolution contract
  as approve/reject (D-06).
- `POST /api/v1/staged/{id}/fail` — same shape; transitions approved → failed; emits
  `staged.failed` DBEvent. Body may include error context (`{result: {error: ...}}`).
- `forge_execute_staged(id, actor, result?)` MCP tool — symmetric to `forge_approve_staged`.
- `forge_fail_staged(id, actor, result?)` MCP tool — symmetric to `forge_reject_staged`.

Reuse the FB-B patterns (Plan 14-03 handler shape, Plan 14-04 tool registration via
`register_console_resources`, byte-identity tests via `_ResourceSpy` + TestClient).

## Triggers

- A consumer asks for HTTP/MCP closure (likely projekt-forge v1.5 Flame hooks once they
  finish their executor).
- Auditing requires `executed`/`failed` to be written by a different actor than `approved`
  (currently only achievable via direct repo calls, which is fine for projekt-forge but
  awkward for Web UI / CLI consumers).

## Notes

The repo methods `StagedOpRepo.execute(op_id, executor=str, result: dict | None = None)`
and `StagedOpRepo.fail(op_id, executor=str, result: dict | None = None)` are already
shipped in FB-A (verify exact signatures). v1.5's HTTP/MCP layer is a thin wrapper —
the same template Plan 14-03/14-04 used.
