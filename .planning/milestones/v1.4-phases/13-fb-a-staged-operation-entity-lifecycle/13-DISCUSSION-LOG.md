# Phase 13 (FB-A): Staged Operation Entity & Lifecycle — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 13-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 13-fb-a-staged-operation-entity-lifecycle (alias FB-A)
**Areas discussed:** Storage shape, Event vocabulary, Lifecycle enforcement, Actor identity, Failure result payload

---

## Pre-Session: Tooling Impedance Resolution

Before discuss-phase could proceed, `gsd-tools find-phase "FB-A"` returned `found: false`. Root cause: `normalizePhaseName()` strips letter prefixes only when followed by a digit (`FB-13` would parse, `FB-A` does not — letter suffix expects `\d+[A-Z]?` shape). The locked roadmap decision preserved the `FB-A..FB-D` letter scheme as a cross-repo contract with projekt-forge v1.5.

**Resolution presented:**
| Option | Description | Selected |
|--------|-------------|----------|
| Dual-name | Numeric ID 12-15 for tooling, FB-A..FB-D as alias | initially proposed |
| Use letter IDs and bypass tooling | Manual workflow, lose checkpoint/state automation | |
| Reverse the locked decision | Renumber to 12-15, drop letter scheme | |

**User's choice:** Dual-name (Option 1)

**Numbering correction (caught before commit):** Proposed mapping `12-15` collided with superseded Phase 12 "LLM Chat" already in v1.3 history. Corrected to `13-16` (skipping 12). Final: Phase 13 (FB-A), Phase 14 (FB-B), Phase 15 (FB-C), Phase 16 (FB-D).

**Notes:** Amendment committed as `43ab0fd` (`docs(v1.4): apply dual-naming amendment`) before discuss-session proper began. ROADMAP.md and STATE.md updated; new decision row added to STATE.md decisions log recording the amendment rationale.

---

## Storage Shape

| Option | Description | Selected |
|--------|-------------|----------|
| (a) JSONB sub-keys in `attributes` | proposer/operation/parameters/result live as keys inside existing `DBEntity.attributes` JSONB — consistent with version/media/shot/asset conventions. Single GIN index covers it. | ✓ |
| (b) Promoted JSONB columns | Add `parameters` and `result` as first-class JSONB columns on `DBEntity`. NULL for every other entity type, breaks polymorphic invariant. | |
| (c) Separate `staged_operations` table | Clean isolation, breaks polymorphic pattern that FB-B and existing entity query infrastructure rely on. | |

**User's choice:** (a) JSONB sub-keys
**Notes:** Reco accepted as-is. STAGED-04's "diff via SQL alone" is satisfied by `SELECT attributes->'parameters', attributes->'result' FROM entities WHERE entity_type='staged_operation' AND id=?`.

---

## Event Vocabulary

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Reuse `entity.status_changed` | Generic existing type; subscribers filter on JSONB payload (no indexed query path). | |
| (b) Specific per-transition types | New types `staged.proposed`, `staged.approved`, `staged.rejected`, `staged.executed`, `staged.failed`. Indexed via existing `ix_events_type_time`. Matches granular existing vocabulary. | ✓ |

**User's choice:** (b) Specific per-transition events
**Notes:** Reco accepted. FB-B's projekt-forge consumer subscribes specifically to `staged.approved` — clean subscription contract, indexed query path.

---

## Lifecycle Enforcement Layer

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Repo/application layer | StagedOpRepo (or methods) holds transition map; raises StagedOpLifecycleError. DB stays generic. | ✓ |
| (b) DB-level constraint | CHECK constraint or trigger gating allowed transitions. Belt-and-braces. | |
| (c) Both layers | App raises early; DB constraint catches drift. | |

**User's choice:** (a) Repo/application layer
**Notes:** Reco accepted. Matches established pattern (no DB-level rules on JSONB shape, no enum on `status`, application-level relationships). Adding a CHECK constraint just for one entity_type creates an exception to the polymorphic invariant. All writers (FB-B MCP tools, HTTP routes, future projekt-forge integration) go through the repo — no bypass risk.

---

## Actor Identity Representation

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Free string | `"projekt-forge:flame-a"` style — mirrors existing `DBEvent.client_name` pattern. | ✓ |
| (b) Structured object | `{actor_type, actor_id, session_id?}` JSONB. Forward-compatible with auth but premature. | |
| (c) Reuse `DBSession.id` | Tight binding to existing session tracking. Auth migration in v1.5 changes session semantics. | |

**User's choice:** (a) Free string
**Notes:** Reco accepted. SEED-AUTH-V1.5 owns the eventual migration to structured caller-identity. v1.4 is the staged-ops MVP, not the identity model.

---

## Failure Result Payload Shape

On `approved → failed`, the `result` JSONB gets populated.

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Minimal | `{"error": "<message>", "traceback": "<stack>"}` | |
| (b) Typed | `{"error": "<message>", "error_type": "<exception class>", "details": {...}}` | ✓ |
| (c) Mirror parameters | `{"status": "failed", "error": ..., "partial_result": ...}` — captures partial work. | |

**User's choice:** (b) Typed
**Notes:** Reco accepted. `error_type` lets projekt-forge consumers branch on error class without string-matching. `details` is open for caller-supplied context. (c)'s partial-result is speculative for v1.4.

---

## Claude's Discretion

The user accepted all five recos as-presented and approved Claude's discretion on:
- Exact filename for the new Alembic migration version (existing convention is `NNNN_description.py`).
- Module organization for new repo and entity-class code (extend existing files vs add new modules).
- Test-file granularity (single `test_staged_operations.py` vs split per criterion).
- Whether `EVENT_TYPES` enforcement is a DB CHECK constraint (verification needed) or Python-side frozenset only.

## Deferred Ideas

Captured in 13-CONTEXT.md `<deferred>` section:
- Caller-identity bucketing for actors (SEED-AUTH-V1.5)
- Operation-specific parameter validation (v1.5)
- Cancel/cancel-on-timeout transitions
- Relationship edges on staged_operation
- Bulk approval / batch operations

No scope creep introduced during the session — discussion stayed within FB-A's boundary.
