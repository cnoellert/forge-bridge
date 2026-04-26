---
name: SEED-STAGED-REASON-V1.5
description: Approve/reject reason capture deferred from FB-B
type: forward-looking-idea
planted_during: Phase 14 (FB-B) close — 2026-04-26
trigger_when: A consumer asks why an op was rejected, or multi-user review accountability surfaces
---

# SEED-STAGED-REASON-V1.5 — Approve/Reject Reason Capture

**Planted:** 2026-04-26 (Phase 14 / FB-B close)
**Deferred from:** Phase 14 (FB-B) — CONTEXT Deferred Ideas
**Target milestone:** v1.5

## Summary

Phase 14 (FB-B) ships approve/reject HTTP and MCP surfaces with actor identity capture
(D-06/D-07) but NOT reason capture. An artist who rejects a staged operation has no
way to leave a "why" — the audit trail records who, what, and when, but not the
reasoning. For v1.4 single-tenant local-first this is acceptable; for v1.5 multi-user
or projekt-forge integration with mixed-team review, free-text reason fields become
load-bearing.

## v1.5 Scope

Add optional `reason: str` field to the approve/reject contracts on BOTH surfaces:
- HTTP: `POST /api/v1/staged/{id}/approve` body accepts `{"actor": "...", "reason": "..."}`.
  Reason ends up in `DBEvent.attributes.approve_reason` (or `reject_reason`).
- MCP: `ApproveStagedInput` and `RejectStagedInput` Pydantic models gain optional
  `reason: Optional[str] = None` field.
- StagedOpRepo: `approve(op_id, *, approver, attribute_updates=None, reason: str | None = None)`
  — the existing `attribute_updates` kwarg can absorb this (`{"approve_reason": reason}`),
  so v1.5 may not need a repo signature change at all — just a v1.5 audit of how the
  attribute is populated end-to-end.

UI consideration: the Web UI chat panel (FB-D consumer) and projekt-forge Flame hooks
benefit from a free-text `reason` form field; the field is purely advisory (no
validation beyond max length, e.g., 1000 chars).

## Triggers

- A consumer asks: "I need to know why my op was rejected."
- Multi-user reviews require accountability beyond actor identity.
- v1.5 SEED-AUTH lands and caller-identity bucketing surfaces the need for richer audit.

## Notes

Patterns to follow:
- The `DBEvent.attributes` JSONB field already supports arbitrary KV; FB-A D-09 stores
  the approver/rejecter in `attributes`. Adding `approve_reason` / `reject_reason`
  follows the same pattern.
- The HTTP body parser already exists (`_resolve_actor` does `await request.json()`);
  extending it to extract `reason` is a 3-line change.
- The Pydantic field addition is one line per input model.
- Test: extend the existing zero-divergence tests with `reason="..."` payloads and
  confirm both surfaces store identical `DBEvent.attributes`.
