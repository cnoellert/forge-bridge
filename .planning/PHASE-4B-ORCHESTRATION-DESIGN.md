---
name: PHASE-4B-ORCHESTRATION-DESIGN
description: Repo-local design for Phase 4B — forge-bridge orchestration graph + memory; instantiates Phase 4 umbrella §§4, 5, 7, 8, 9 in forge-bridge
status: active
authored: 2026-05-28
depends_on: Phase 4 umbrella at forge-vision/.planning/PHASE-4-PIPELINE-ORCHESTRATION-DESIGN.md
---

# Phase 4B — forge-bridge orchestration design (repo-local)

This document instantiates Phase 4's umbrella in forge-bridge. The umbrella owns cross-repo contracts and pipeline shape; this doc owns implementation contracts at design-doc grain — schema additions, service shapes, refusal vocabularies, protocol signatures, sequencing. Sections are load-bearing in their stated order: §§1-2 frame and govern; §§3-4 establish substrate; §§5-9 specify subsystem contracts; §§10-13 align with umbrella memory model, name non-goals, sequence implementation, and carry forward discipline.

---

## §1. Purpose and scope

This doc owns:

- The schema additions forge-bridge takes on for Phase 4B (entity types, dedicated tables, relationship type families)
- The planner contract at implementation-design grain
- The graph engine's per-run lifecycle and transition semantics
- The replay execution engine's contract surface
- The provenance manifest assembly logic
- The sibling registration protocol from the bridge side
- How umbrella §9's five memory categories instantiate in this repo

This doc does NOT own:

- Anything resolved in the umbrella (cross-repo contracts, pipeline shape, ownership boundaries — those remain canonical in `forge-vision/.planning/PHASE-4-PIPELINE-ORCHESTRATION-DESIGN.md`)
- Specific Alembic migration content (those land at implementation time; this doc names the schema; the migration files realize it)
- Per-driver polling implementation (forge-generators owns; this doc consumes that surface)
- 4C's matte operators and Flame-consumable package layout (forge-vision's surface)
- 4A's already-shipped `GenerationArtifact` contract (forge-generators canonical at `forge-generators/.planning/PHASE-4A-FORGE-GENERATORS-V0.1-DESIGN.md`)

When implementation pressure surfaces decisions this doc didn't anticipate, this doc gets revised — implementation does not silently diverge from design.

---

## §2. System identity and governing doctrine

### System identity

Phase 4B is not "workflow orchestration." It is, more honestly:

**Semantic execution memory + constraint-driven planning + epistemic replay.**

Three commitments that braid together:

- **Semantic execution memory**: forge-bridge persists the substrate's full causal record across shots — intent, plans, execution provenance, audit verdicts, promotion decisions, lineage edges, methodology snapshots. The memory is queryable across time and across shots, not just within a single run.
- **Constraint-driven planning**: the planner is the semantic kernel of the substrate. It reads intent, capabilities, rules, and lineage; produces an `ExecutionPlan` or refuses with a typed verdict. Routing is not chained-operator dispatch; it is composing execution under semantic constraints.
- **Epistemic replay**: replay reconstructs what was known, intended, allowed, and attempted — not what was executed. A replay is a new run with new lineage that invokes the planner again under the source run's resolved policy bundle. Replay does not resurrect serialized execution.

The orchestration graph — analyze → generate → validate → audit → promote → publish — is **what the substrate looks like in motion**. It is not the system's identity; it is the system's surface during a run.

### Governing doctrine

**The substrate prefers explicit constrained state over degraded execution. Every refusal, partial, infeasibility, and degradation produces a typed, queryable artifact — never silent fallthrough.**

This doctrine appears repeatedly across the design:

- Planner infeasibility → `feasibility_verdict: infeasible` with explanation, not best-effort plan
- Replay refusal → typed `pinning_unreachable` codes, not silent divergence
- Partial fidelity → `partial+remediation` verdict with named dimensions, not pass-by-default
- Audit compromise → three-way reconciliation, not auto-resolution
- Bridge degraded startup → `bridge_degraded` event + planner refusal, not silent capability loss
- Sibling registration failure → typed event in `events`, not skipped silently

The doctrine has a corollary: **the substrate never invents — it surfaces.** Cost is never invented; it is summed from reported per-backend submissions. Verdicts are never inferred; they are declared by named operators with named evidence. Promotions are never automatic; they are explicit editorial events. The substrate's job is to keep semantic content honest; inventing semantic content silently is the failure mode the doctrine exists to prevent.

### The semantic vs operational ontological cut

Phase 4B's storage doctrine (§3) draws an ontological line between two kinds of objects:

- **Semantic artifacts**: provenance-bearing, content-addressable, lineage-participating. `LockedIntent`, `ExecutionPlan`, `AuditReport`, `RuleSnapshot`, `CapabilityDeclarationSnapshot`, `PartialFidelityModelSnapshot`, `GenerationArtifact`, `ValidationReport`, `ProvenanceManifest`, `SpecConvergenceTrace`, `PipelineRun`, `InputsCatalog`. These extend the existing `entities` discriminator with `orch_` prefix and ride the relationships table for lineage.
- **Operational substrate**: state-machine entities, append-only ledgers, execution bookkeeping. `OrchestrationLifecycleState`, `OrchestrationPromotionLedger`, `OrchestrationCompromiseLedger`. These get dedicated tables.

The cut is **semantic identity vs operational mechanics**, not "complex shape vs simple shape" and not "frequently-queried vs rarely-queried." Semantic artifacts can be operationally rich (a `ProvenanceManifest` is large); operational substrate can be structurally simple (a promotion ledger entry is small). The criterion is whether the object participates in lineage as a first-class node — if yes, it's semantic; if it is execution coordination, it's operational.

This distinction is load-bearing for replay, audit, debugging, and provenance visualization. Without it, everything degenerates into "another entity row" and the substrate loses its semantic discipline.

---

## §3. Storage doctrine

### Postgres-native

Phase 4B's state lives in the `forge_bridge` Postgres database. Stack matches forge-bridge's existing conventions:

- SQLAlchemy 2.x ORM
- asyncpg async runtime
- psycopg2-binary for Alembic and CLI
- Alembic hand-authored Python migrations, zero-padded sequential
- Async-first; caller owns transactions; repos take `AsyncSession` via constructor injection; repos never `commit()` themselves
- JSONB-heavy with promoted-column hot paths; GIN indexes where containment queries are expected
- snake_case_plural tables; `DB<Name>` ORM classes

### Hybrid discriminator-first

Semantic artifacts extend the existing `entities` table via new `entity_type` discriminator values. The migration template is `0003_staged_operation.py` (extends `ck_entities_type` CHECK). Rich shape lives in `attributes:JSONB`; hot query keys promote to columns. Defensive naming: all Phase 4B entity types carry the `orch_` prefix to signal the orchestration layer.

Operational substrate gets dedicated tables. These are state-machine or append-only ledgers whose query shape demands typed columns over JSONB introspection.

### Two-track content-addressable storage

**Semantic immutables** (intents, plans, snapshots, audit reports, manifests): stored as `entities` rows with a `content_hash` column (sha256 over canonical JSON serialization of the row body) computed at insert. Repository layer refuses `update()` on these rows; the only write path is `insert_if_absent(body)` which computes the hash and inserts only if absent.

**Media artifacts** (generated stills, video, mattes): stored as `entities` rows with a `content_hash` column AND a `locations` entry (existing forge-bridge pattern) pointing at the filesystem path. The DB carries identity + metadata + path; the filesystem carries bytes. This matches the umbrella's Flame-consumable structure (§1) — media lives on disk where Flame can consume it.

### Repository-layer immutability

For content-addressed semantic-artifact entities, the immutability discipline lives in the repository layer, not in DB triggers:

- A shared `ContentAddressedRepo[T]` base class implements `insert_if_absent(body) -> T` and refuses `update(...)`
- `content_hash` is computed by the repo from canonical JSON serialization of the body (not trusted from caller)
- DB-level enforcement (triggers, rules, partial unique constraints) is deferred — the repo discipline is the contract; the DB is the durable layer beneath it

If implementation pressure later demands DB-level immutability enforcement, that's an additive change; the repo discipline carries the semantics today.

### Bridge owns tables directly

No `StoragePersistence`-protocol indirection for Phase 4B's orchestration tables. The `StoragePersistence` pattern in forge-pipeline made sense because learning observations are host-emitted; orchestration memory is bridge-intrinsic. Bridge defines models, owns migrations, owns repositories, owns the transactional semantics. The seam to siblings (forge-generators, forge-vision) is the operator + sibling-registration protocol (§9), not a storage protocol.

### Defensive naming

To prevent collision with existing forge-bridge entities and future forge-pipeline tables:

- All Phase 4B `entity_type` discriminator values carry `orch_` prefix
- All Phase 4B dedicated tables use `orchestration_` prefix
- Snake_case_plural for table names; `DBOrch<Name>` ORM classes
- Relationship type names for run lineage use the `_run` suffix (`replays_run`, `remediates_run`, `amends_run`) to distinguish from artifact lineage

---

## §4. Schema additions

### Entity types (extend `entities` discriminator)

The migration extends the `ENTITY_TYPES` frozenset and the `ck_entities_type` CHECK constraint:

| `entity_type` value | Purpose | Notable JSONB shape | Hot promoted columns |
|---|---|---|---|
| `orch_pipeline_run` | Per-run lifecycle anchor; nodes for run-to-run lineage | `{run_kind: original|replay|remediation, intent_id, source_run_id?, effective_pinning_policy?}` | `content_hash`, `run_kind` |
| `orch_inputs_catalog` | Canonical UUID + role-assignment manifest | `{inputs: [...], role_assignments: {...}}` | `content_hash` |
| `orch_spec_convergence_trace` | Working-spec iterations + Q&A history | `{iterations: [v1..vN], lock_event?}` | `content_hash`, `locked` (bool) |
| `orch_locked_intent` | Locked executable intent (with measurement_spec per criterion) | `{source_read, change_manifest, success_criteria: [{criterion_id, statement, measurement_spec: {...}, tolerances}], allowed_compromises, hard_constraints, escalation_threshold, deliverable_spec}` | `content_hash` |
| `orch_rule_snapshot` | Methodology rules in force at snapshot time | `{rules: [{rule_id, statement, rationale, validating_phase_ref, enforcement_phases, authoritative_phase, version, amends?}], source_ref}` | `content_hash` |
| `orch_capability_snapshot` | Per-backend capability declarations frozen at plan time | `{snapshots: [{backend_identity_triple, declaration_hash, capabilities_opaque}]}` | `content_hash` |
| `orch_partial_fidelity_snapshot` | Per-backend per-dimension expected partial fidelity | `{models: [{backend_identity_triple, dimensions: [{axis, scalar, rationale}]}]}` | `content_hash` |
| `orch_execution_plan` | Planner output | full shape per §5 | `content_hash`, `intent_id`, `feasibility_verdict` |
| `orch_generation_artifact` | Generation operator output (forge-generators-produced; bridge stores) | `{platform_locators, content_provenance, execution_provenance, partial_fidelity_report?, polling_history}` | `content_hash`, `lifecycle_state`, `run_id` |
| `orch_validation_report` | Validation operator output (forge-vision-produced; bridge stores) | `{verdict, evidence, evidence_refs}` | `content_hash` |
| `orch_audit_report` | Composed assessment of candidate against locked intent | full shape per umbrella §8 | `content_hash`, `candidate_artifact_id`, `overall_verdict` |
| `orch_provenance_manifest` | Publish-time portable extract | full shape per §8 | `content_hash`, `canonical_artifact_id` |

Each carries `content_hash` (sha256 over canonical JSON of the body) as a promoted column with a unique constraint. Repository layer refuses `update()` on all of these.

Promoted hot columns are added beyond `content_hash` only where query pressure is structurally clear from the design (lifecycle state on generation artifacts, feasibility verdict on plans, overall verdict on audits, run_kind on pipeline runs). Other queries go through JSONB containment via the existing GIN index pattern.

### Dedicated operational tables

#### `orchestration_lifecycle_state` (one row per run)

```
orchestration_lifecycle_state
  run_id              UUID PK (FK → entities.id where entity_type = 'orch_pipeline_run')
  shot_id             UUID    (FK → entities.id where entity_type = 'shot')
  current_stage       text    (CHECK ∈ {ingest, spec_convergence, routing, execution, audit, promotion, publish})
  stage_entered_at    timestamptz
  intent_id           UUID?   (FK → entities.id once locked)
  plan_id             UUID?   (FK → entities.id once planned)
  current_canonical   UUID?   (FK → entities.id once promoted)
  status              text    (CHECK ∈ {active, paused, completed, failed, cancelled})
  block               JSONB?  (shape per §6; null when not blocked; status='paused' requires block != null)
  last_event_id       UUID    (FK → events.id; resumability anchor)
  created_at          timestamptz
  updated_at          timestamptz

  Indexes:
    ix_orchestration_lifecycle_state_shot_id_active  partial WHERE status = 'active'
    ix_orchestration_lifecycle_state_current_stage
    ix_orchestration_lifecycle_state_status

  Constraint:
    ck_orchestration_lifecycle_state_paused_has_block:
      (status = 'paused') = (block IS NOT NULL)
```

#### `orchestration_promotion_ledger`

```
orchestration_promotion_ledger
  promotion_id          UUID PK
  shot_id               UUID  (FK → entities.id)
  promoted_artifact_id  UUID  (FK → entities.id; the orch_generation_artifact entity)
  superseded_id         UUID? (FK → entities.id; previous canonical)
  audit_report_id       UUID? (FK → entities.id; AuditReport that scored the promoted artifact)
  promoted_at           timestamptz
  promoted_by           text  (operator_id or 'policy-driven')
  rationale             text

  Indexes:
    ix_orchestration_promotion_ledger_shot_id_promoted_at desc
    ix_orchestration_promotion_ledger_promoted_artifact_id

Per-shot current canonical resolved by:
  SELECT promoted_artifact_id FROM orchestration_promotion_ledger
   WHERE shot_id = ? ORDER BY promoted_at DESC LIMIT 1
```

The dedicated table is preferred over the `events` table here because `canonical(shot_id, at?: timestamp)` is a hot query and supersession traversal is structured (parent_chain via `superseded_id`).

#### `orchestration_compromise_ledger`

```
orchestration_compromise_ledger
  entry_id          UUID PK
  intent_id         UUID    (FK → entities.id; the LockedIntent the consumption is against)
  run_id            UUID    (FK → entities.id; the run that produced this entry)
  plan_id           UUID?   (FK → entities.id; the plan that recorded this if planning-side)
  artifact_id       UUID?   (FK → entities.id; the artifact that recorded this if audit-side)
  criterion_id      text    (LockedIntent.success_criteria[i].criterion_id)
  dimension         text    (the measured axis)
  side              text    (CHECK ∈ {planned_predicted, audit_actual})
  magnitude         JSONB   (shape conforms to LockedIntent.success_criteria[i].measurement_spec; scalar or structured)
  recorded_at       timestamptz

  Indexes:
    ix_orchestration_compromise_ledger_intent_criterion (intent_id, criterion_id, dimension)
    ix_orchestration_compromise_ledger_run_id
```

Append-only; repository refuses `update()` and `delete()`. Aggregation by `(intent_id, criterion_id, dimension)` to compute cumulative consumption across original + remediation runs. Gates `LockedIntent.escalation_threshold` at plan time (§5 pass 6).

### Relationship type families

Phase 4B adds new relationship types to the existing `registry_relationship_types` table. The migration seeds them with well-known UUIDs.

**Artifact lineage:**

| `name` | Direction | Purpose |
|---|---|---|
| `content_source` | source → derived | Content lineage (what produced what) |
| `anchored_to` | derived → source-truth | Anchor lineage (rule 4 — what each step was anchored against) |
| `remediated_from` | new attempt → prior attempt | Artifact-level remediation lineage |
| `superseded_by` | older canonical → newer canonical | Promotion supersession |

**Run lineage (separate family — runs are not artifacts in the content sense):**

| `name` | Direction | Purpose |
|---|---|---|
| `replays_run` | replay run → source run | Top-level replay relationship |
| `remediates_run` | remediation run → source run | Remediation entry to source run |
| `amends_run` | replan-amended-intent run → source run | Specifically the amended-intent variant |

**Reference role (carries the ontological reference roles from umbrella §3 into the schema):**

| `name` | Direction | Purpose |
|---|---|---|
| `reference_structural` | plan/artifact → reference identity | Structural reference role |
| `reference_editorial` | plan/artifact → reference identity | Editorial reference (never image input) |
| `reference_identity` | plan/artifact → reference identity | Identity-lock reference |
| `reference_motion` | plan/artifact → reference identity | Motion-source reference |
| `reference_depth` | plan/artifact → reference identity | Depth reference |
| `reference_compositional_anchor` | plan/artifact → reference identity | Compositional anchor (rule 9) |
| `reference_source_truth_anchor` | plan/artifact → reference identity | Source-truth anchor (rule 4) |

Pre-existing forge-bridge relationship types (`member_of`, `consumes`, `produces`, etc.) remain unchanged and untouched by this migration.

### Migration sequence

Phase 4B's schema arrives as a sequence of hand-authored Alembic revisions continuing forge-bridge's existing sequence (current head: `0003_staged_operation.py`):

1. **0004_phase4b_relationship_types** — seeds new relationship type rows in `registry_relationship_types` with well-known UUIDs; does not modify table shape
2. **0005_phase4b_entity_types** — extends `ck_entities_type` CHECK constraint with all `orch_*` discriminators; adds `content_hash text NULL` column on `entities` with a unique partial index `WHERE entity_type LIKE 'orch_%'`. Existing non-orch rows leave `content_hash` null; new orch_* rows MUST have it set.
3. **0006_phase4b_orchestration_lifecycle_state** — creates `orchestration_lifecycle_state` table
4. **0007_phase4b_orchestration_promotion_ledger** — creates `orchestration_promotion_ledger` table
5. **0008_phase4b_orchestration_compromise_ledger** — creates `orchestration_compromise_ledger` table

Each migration has explicit `upgrade()` and `downgrade()` per forge-bridge convention.

---

## §5. Planner contract

### Inputs

The planner reads:

- `LockedIntent` — with each `success_criterion` carrying a `measurement_spec` (the operator's declaration of how the criterion is measured for pass / partial+remediation / fail). The `allowed_compromises` sub-surface is read as the budget side of the three-way reconciliation.
- `InputsCatalog` — canonical UUIDs + role assignments
- `RuleSnapshot` — current methodology snapshot; planner uses only rules whose `enforcement_phases` includes `planning-time`
- `CapabilityDeclarationSnapshot` — per-backend capability declarations as of plan-construction time; bridge snapshots from forge-generators' declarations at plan invocation
- `PartialFidelityModelSnapshot` — operator-authored per-backend per-dimension expected compromise; methodology state, not capability state
- `PlatformUUIDRegistry` — forge-generators-owned mapping of content_sha256 ↔ platform UUIDs per backend; planner reads to determine whether external upload is needed
- `TrainedIdentityRegistry` — forge-generators-owned registry of trained identities; planner checks `validity_window` and `reuse_constraints` against current shot context
- `LineageGraph` — current orchestration lineage; planner reads at plan time to enforce anchor-lineage discipline (rule 4) and compute chain depth (rule 5)

### Six-pass decision model

The planner operates as an ordered sequence of passes. Each pass is a different kind of operation:

| Pass | Operation | Refusal output (if fails) |
|---|---|---|
| **1. Validate completeness** | Verify all required inputs are present and snapshots are resolvable | `inputs_missing` / `snapshot_unresolvable` / `locked_intent_unresolvable` |
| **2. Filter candidates by hard capability** | For each operator in the natural sequence, retain backends with feasible input pathway (with or without transform insertion); eliminate backends that cannot meet hard constraints (first-frame guarantee, identity-lock support, reference topology); validate trained-identity validity and reuse | `no_feasible_backend` / `trained_identity_validity_expired` / `identity_reuse_forbidden` / `external_upload_unavailable` |
| **3. Insert required transforms** | For surviving candidates, insert pre/post transforms required by content-policy bypass (cross-capability calls to forge-vision perceptual operators per umbrella §4); record `transforms_inserted` with rule_ref justification | `transform_unavailable` |
| **4. Validate plan-shape rules** | Check the constructed operator sequence against plan-shape rules: anchor-lineage discipline (rule 4 — every step anchors to source UUID per `reference_source_truth_anchor`); chain-depth hard cap (rule 5 at the limit); aspect-ratio integrity for video (rule 10) | `anchor_lineage_violation` / `chain_depth_exceeded` / `aspect_integrity_violation` |
| **5. Rank candidates & compute predicted compromises** | For each remaining candidate, score against acceptance bar; compute predicted compromise per criterion using `PartialFidelityModelSnapshot`; rank by (meets-acceptance-bar, then cost within tier, then chain-depth as tiebreaker) | (no refusal — produces an ordered candidate list) |
| **6. Emit feasibility verdict** | If top-ranked candidate's predicted compromises stay within `allowed_compromises` and cumulative against `escalation_threshold`: emit `feasible` or `constrained-but-feasible` plan. Otherwise: `infeasible` with explanation. Pass 6 reads the `orchestration_compromise_ledger` for cross-run cumulative budget. | `compromise_budget_exceeded` / `cumulative_threshold_exceeded` |

**Pass 2 / pass 3 coupling.** Pass 2 filters on "backend has *some* feasible input pathway, with or without transform insertion." This prevents pass 2 from silently eliminating candidates that pass 3 would have made feasible (e.g., Magnific motion-control-pro under rule-14 depth preprocessing).

**Pass 5's prediction model.** `PartialFidelityModelSnapshot` is operator-authored at file edit; the substrate does not auto-adjust from observed deltas (umbrella §9 deferral). Predicted compromises are estimates and are explicitly marked as such on the plan; actuals land in `orchestration_compromise_ledger.side = audit_actual` at audit time. The three-way reconciliation (`allowed_compromises` → predicted → actual) is what audit (§8 of umbrella) performs.

### `ExecutionPlan` shape

```
ExecutionPlan {
  plan_id:                       UUID
  content_hash:                  sha256
  intent_id:                     UUID
  planner_version:               str
  capability_snapshot_id:        UUID
  rule_snapshot_id:              UUID
  partial_fidelity_snapshot_id:  UUID
  authored_at:                   timestamptz

  operator_sequence: [
    {
      operator_id:            str
      backend_assignment:     BackendIdentityTriple
      inputs:                 [{role, identity_coordinate}]
      expected_artifact_kind: str
      transforms_pre:         [transform_id]
      transforms_post:        [transform_id]
      fidelity_target:        str
      candidacy:              "candidate" | "diagnostic"
                              # v0.1: derived from terminal state per §6 (complete|partial → candidate;
                              # failed|cancelled → diagnostic). Reserved on the plan shape for the
                              # documented eject (plan-declared diagnostic operators).
    }
  ]

  backend_assignments:           { operator_id → BackendIdentityTriple }
  transforms_inserted:           [{ transform_id, reason, rule_ref, providing_operator }]
  external_uploads_required:     [{ asset_identity_coordinate, target_backend, time_estimate, cost_estimate }]

  cost_estimate: {
    tier:        str
    currency:    str
    breakdown:   {...}
  }

  predicted_compromise_consumption: [
    { criterion_id, dimension, magnitude_estimate, source_backend, rationale }
  ]

  provenance_obligations: [
    { operator_id, must_measure: [dimension], must_report: [field] }
  ]

  feasibility_verdict:     "feasible" | "constrained-but-feasible" | "infeasible"
  feasibility_explanation: text
  refusal_code?:           RefusalCode   # populated when verdict = infeasible
}
```

### Typed refusal vocabulary

Closed enum at the planner boundary. Each refusal carries an explanation and an optional remediation hint:

| Code | When |
|---|---|
| `inputs_missing` | Pass 1 — required input absent |
| `snapshot_unresolvable` | Pass 1 — rule / capability / partial-fidelity snapshot id cannot be resolved |
| `locked_intent_unresolvable` | Pass 1 — intent reference invalid or measurement_spec absent |
| `no_feasible_backend` | Pass 2 — no backend can produce the required operator output |
| `external_upload_unavailable` | Pass 2 / pass 3 — backend requires pre-uploaded HTTPS URL but no upload pathway exists |
| `trained_identity_validity_expired` | Pass 2 — referenced trained identity's `validity_window` has expired |
| `identity_reuse_forbidden` | Pass 2 — referenced trained identity's `reuse_constraints` forbid current shot context |
| `transform_unavailable` | Pass 3 — required preprocessing transform cannot be inserted (forge-vision operator absent or refused) |
| `anchor_lineage_violation` | Pass 4 — operator sequence would necessarily violate rule 4 |
| `chain_depth_exceeded` | Pass 4 — chain depth exceeds rule 5 hard cap |
| `aspect_integrity_violation` | Pass 4 — video deliverable would require pillarbox bake (rule 10) |
| `compromise_budget_exceeded` | Pass 6 — predicted compromises exceed `allowed_compromises` |
| `cumulative_threshold_exceeded` | Pass 6 — cumulative consumption (across original + remediations) exceeds `escalation_threshold` |
| `backend_revision_unreachable` | Replay-mode pass — honor-pinning policy and source backend revision is gone |
| `rule_snapshot_unresolvable` | Replay-mode pass — honor-pinning policy and source rule snapshot cannot be resolved |
| `capability_snapshot_unresolvable` | Replay-mode pass — same for capability snapshot |
| `partial_fidelity_snapshot_unresolvable` | Replay-mode pass — same for partial-fidelity snapshot |
| `spec_convergence_trace_missing` | Replay or `replan_amended_intent` — required convergence trace absent |
| `source_run_incomplete` | Replay-mode pass — source run never reached promotion/publish |

### Remediation triage trichotomy

When audit fails and the operator initiates remediation, the planner is invoked via one of three named entry points:

| Entry point | Effect | Planner invoked? |
|---|---|---|
| `new_attempt_same_plan` | Re-execute the existing plan against same/no seed; new `GenerationArtifact` emitted | No (graph engine re-runs execution stage with source plan) |
| `replan_same_intent` | Planner re-runs against same `LockedIntent`; snapshots may shift (or honor-pinned per `ReconstructionRequest`) | Yes |
| `replan_amended_intent` | New `LockedIntent` lock event with `derived_from` reference to original; planner re-runs against amended intent | Yes (after lock) |

`new_attempt_same_plan` produces a new artifact edged via `remediated_from` (artifact-level lineage). `replan_*` produces a new run edged via `remediates_run` or `amends_run` (run-level lineage per §4).

### Rules taxonomy

Each rule in a `RuleSnapshot` carries:

```
{
  rule_id:               str  (e.g., "rule-14")
  title:                 str
  statement:             str
  rationale:             str
  validating_phase_ref:  str
  version:               int  (within this snapshot)
  amends:                rule_id?
  enforcement_phases:    [phase]    # subset of {planning-time, execution-time, audit-time}
  authoritative_phase:   phase      # the phase whose enforcement is canonical
}
```

`enforcement_phases` allows a rule to fire at multiple stages; `authoritative_phase` resolves which fire is canonical. Example: rule 4 (anchor lineage) has `enforcement_phases: [planning-time, audit-time]` and `authoritative_phase: planning-time` — primarily planning enforces; audit catches violations or external drift as a typed finding.

If audit fails a rule whose `authoritative_phase` is `planning-time`, the audit report records a **planning/execution discrepancy finding** — a substrate signal that something violated discipline between plan and execution. This is itself a queryable artifact; the substrate does not silently absorb the discrepancy.

### Cross-capability transform insertion

When pass 3 requires a transform that lives in forge-vision (e.g., Depth Anything V2 for rule-14 content-policy bypass), the planner records a cross-capability call:

- `transforms_inserted` carries `{ transform_id, reason, rule_ref, providing_operator: "forge_vision.estimate_depth_v2" }`
- The graph engine, when executing this operator_sequence step, invokes the forge-vision operator via the existing bridge transport
- The output artifact composes back into the next generation operator as a reference with the role declared in `transforms_inserted`

Per umbrella §4: perception remains perceptual, generation remains generative, orchestration composes them.

---

## §6. Graph engine contract

### Per-run lifecycle row

One row per pipeline run lives in `orchestration_lifecycle_state` (§4 shape). Each transition is a write that updates the row AND appends an event to `events` in the **same transaction** — enforced at the graph engine service layer, not the repository layer.

### Closed transition vocabulary

Stage transitions fall into a closed set of two kinds:

- `auto_on_condition` — engine advances when a named upstream condition becomes true
- `await_decision_event` — engine pauses until a typed decision event arrives

Stage transition map:

| Transition | Kind | Trigger |
|---|---|---|
| Ingest → Spec convergence | `auto_on_condition` | `InputsCatalog` complete |
| Spec convergence → Routing | `await_decision_event` | `lock_intent` decision event |
| Routing → Execution | `auto_on_condition` | `ExecutionPlan.feasibility_verdict ∈ {feasible, constrained-but-feasible}`; refuse on infeasible (no advance, pause for operator decision) |
| Execution → Audit | `auto_on_condition` | All planned operators terminal (complete / partial / failed / cancelled) AND at least one candidate (complete / partial) exists |
| Execution → paused (zero candidates) | `auto_on_condition` | All planned operators terminal AND zero candidates |
| Audit → Promotion | `await_decision_event` | `promote_candidate` decision event |
| Promotion → Publish | `auto_on_condition` | `PromotionLedgerEntry` recorded |
| Any → cancelled | `await_decision_event` | `cancel_run` decision event |

Decision events are typed:

- `lock_intent` — operator signoff on `LockedIntent`
- `approve_remediation` — operator selection of remediation entry point
- `promote_candidate` — operator selection of canonical from audit candidates
- `cancel_run` — operator-initiated run cancellation

Decision events live in the existing `events` table (purely event-shaped; `event_type` enforced Python-side per existing forge-bridge convention — no DB CHECK).

### Block shape

```
block: {
  kind:           "awaiting_decision" | "engine_failure" | "external_dependency"
  decision_type?: "lock_intent" | "approve_remediation" | "promote_candidate" | "cancel_run"
  reason:         str
  set_at:         timestamptz
} | null
```

State transitions enforce consistency at the engine service layer:

- `status = 'paused'` ⟺ `block IS NOT NULL`
- `status ∈ {'active', 'completed', 'failed', 'cancelled'}` ⟹ `block IS NULL`

Block setting and lifecycle state transition happen in the same write (atomic via single-transaction discipline).

### Stage over artifact sets

The pipeline is sequential at the stage level and graph-shaped within stages:

- Execution can produce N parallel `GenerationArtifact`s (the four-takes-in-parallel pattern)
- Audit operates over the candidate set, producing N `AuditReport`s (one per candidate)
- Promotion picks one canonical from the set

The lifecycle state's `current_canonical` field is null until promotion; before promotion, "the audit candidates of this run" is a query against the entities table (filter by `run_id` and `entity_type = orch_generation_artifact` and `lifecycle_state ∈ {complete, partial}`).

### Async/sync composition — worker contract

Generation operators are async (submit → poll → terminal); perception/validation/audit operators are sync. The graph engine schedules work and tracks transitions; a separate worker advances generation artifacts to terminal states.

**Engine responsibilities:**

- Subscribe to `generation_artifact_terminal` events
- Apply `auto_on_condition` transition rule for the affected run
- Update lifecycle state + append event in one transaction

**Worker responsibilities:**

- Query Postgres for non-terminal generation artifacts (`lifecycle_state ∈ {submitted, polling}`)
- For each: defer to the appropriate forge-generators driver (forge-generators owns the polling protocol, status normalization, backoff per backend)
- Update the artifact's `lifecycle_state` + append polling event in one transaction
- On terminal state transition: emit `generation_artifact_terminal` event for the engine to consume

**Boundary:** the worker knows about artifacts, not runs. The engine knows about runs, not polling cadence. The interface between them is the events table.

**v0.1 deployment:** worker runs as an async task within the bridge server process. The interface is defined such that promoting it to a separate process (`python -m forge_bridge.orchestration.worker`) is non-breaking. **Eject condition:** concurrent or long-running operational pressure (multiple bridges, polling load, restart latency requirements) — at that point, separate process becomes the deployment.

### Execution failure handling

When execution stage's operators reach terminal states:

| Set of terminal states | Engine behavior |
|---|---|
| All `complete` | Auto-advance to audit |
| Mixed `complete + partial + failed` | Auto-advance to audit; failed artifacts come along as diagnostics (`candidacy = diagnostic`, derived from terminal state) |
| All `failed` or all `cancelled` (zero candidates) | Pause; emit block with `kind = awaiting_decision`, `decision_type = approve_remediation` |

Zero-candidates pause is the design's explicit human-in-the-loop seam for "the plan needs to be reconsidered." The operator then dispatches one of the three remediation entry points (§5 trichotomy) via the planner.

The substrate **does not auto-remediate**. Doing so would collapse operator judgment into engine logic — exactly the doctrine §2 argues against.

### Single-transaction discipline (engine service layer)

For each transition, the engine service:

1. Opens an `AsyncSession`
2. Reads current lifecycle state (with row lock if concurrent run access is ever introduced; v0.1 is single-writer per run so the lock is unnecessary)
3. Updates lifecycle state row + appends event row
4. Commits — both writes succeed or both fail

The discipline lives in `forge_bridge.orchestration.engine.GraphEngine.transition(...)`, which is the only code path that writes to `orchestration_lifecycle_state`. Repos for lifecycle state are read-only externally; the engine is the sole writer.

### Resumability

If the bridge process crashes mid-run:

- Lifecycle state row reflects the last committed transition (every transition is atomic with its event)
- `last_event_id` anchors the most recent transition event
- Worker, on restart, queries non-terminal generation artifacts and resumes polling
- Graph engine, on restart, queries `active` lifecycle rows and rebuilds in-memory dispatch state

There is no in-memory orchestration state that does not have a Postgres durable counterpart. Restart is recovery, not replay.

---

## §7. Replay execution engine

### `ReconstructionRequest`

Replay and remediation share one request model. Global mode reduces default complexity; per-dimension overrides preserve fine control.

```
ReconstructionRequest {
  request_id:        UUID
  kind:              "replay" | "remediation"
  source_run_id:     UUID

  # remediation-only
  remediation_entry?: "new_attempt_same_plan" | "replan_same_intent" | "replan_amended_intent"

  # global mode, with optional per-dimension overrides
  pinning_mode:      "honor_original" | "refresh_current"

  overrides?: {
    backend?:           "honor_pinning" | "refresh_current"
    rules?:             "honor_snapshot" | "refresh_current"
    capability?:        "honor_snapshot" | "refresh_current"
    partial_fidelity?:  "honor_snapshot" | "refresh_current"
    identity?:          "honor_pinning" | "refresh_current"
  }

  comparison_target: "compare_against_original" | "independent"

  authored_at:       timestamptz
  authored_by:       str
}
```

The resolved effective policy (after applying overrides to the global mode) is stored on the new run's `entity.attributes.effective_pinning_policy`. This makes replay-of-replay coherent — the new run's policy is queryable without recomputing the resolution.

### Engine behavior

For each pinning dimension:

- `honor_*`: resolve the snapshot reference from the source run's provenance. If unresolvable, emit typed refusal (`backend_revision_unreachable`, `rule_snapshot_unresolvable`, `capability_snapshot_unresolvable`, `partial_fidelity_snapshot_unresolvable`, `trained_identity_validity_expired`, `spec_convergence_trace_missing`, `locked_intent_unresolvable`, `identity_reuse_forbidden`, `source_run_incomplete`).
- `refresh_*`: bind to current state; record the divergence in the new run's effective policy attributes.

### Replay invokes the planner

**This is the central architectural commitment of §7.** Replay does NOT serialize-and-resurrect execution. Replay reconstructs the semantic context (resolved snapshot bundle), then invokes the planner against that bundle. The planner produces a fresh `ExecutionPlan` under the resolved policy. The new run executes that fresh plan.

Consequences:

- Planning stays centralized as the semantic kernel
- Refusal semantics are consistent across original runs and replays (same six-pass model, same typed refusal vocabulary)
- Methodology evolution remains coherent — a replay against today's rules vs. honor-pinned rules produces explicitly different plans
- Capability drift is explicit — refresh-mode capabilities mean a different plan; the divergence is queryable

The replay engine is a **thin orchestrator over the planner + graph engine, not its own planning surface.** This is a major architectural boundary.

### Remediation entry-point semantics

Within remediation, the entry point determines where the new run enters the graph engine:

| Entry point | Graph entry stage | Planner invoked? | New `LockedIntent`? |
|---|---|---|---|
| `new_attempt_same_plan` | Execution (with the source run's plan) | No | No |
| `replan_same_intent` | Routing (planner re-runs against same intent under resolved policy) | Yes | No |
| `replan_amended_intent` | Spec convergence (operator amends `LockedIntent`; new lock event required) | Yes (after lock) | Yes |

`new_attempt_same_plan` is the exception to "replay invokes planner" — it intentionally bypasses planning to test pure execution nondeterminism. It still counts as a remediation run with proper lineage edges.

### Replay lineage

The new run gets a new `run_id` and is edged via the run-lineage relationship family:

- `replays_run` for `kind = replay`
- `remediates_run` for `kind = remediation` with `remediation_entry ∈ {new_attempt_same_plan, replan_same_intent}`
- `amends_run` for `remediation_entry = replan_amended_intent`

The new run's plan, audit reports, generation artifacts get their own entities and content provenance; they do not overwrite the source run's records.

### v0.1 scope: top-level replay only

Phase 4B replay enters the graph at the appropriate stage per `kind` and `remediation_entry`. It does NOT support "re-execute from stage N with current upstream artifacts." Mid-run replay (e.g., re-execute only the audit stage) is a different surface and deferred.

The eject condition: a real production case where mid-run replay is operationally needed and the design effort is justified.

---

## §8. `ProvenanceManifest` assembly

### Closure-of-canonical

The manifest is the publish-time portable extract of the **canonical's lineage closure**, not the entire run record. The full run record stays in the `forge_bridge` DB and is queryable / replayable from there. The manifest is what travels with the published package.

### Subgraph closure rule

Starting from the promoted canonical `GenerationArtifact`:

1. **Walk lineage backward** via `content_source` and `anchored_to` edges until reaching source-truth anchor terminals
2. **Include** the canonical's run-scoped semantic artifacts: `LockedIntent`, `SpecConvergenceTrace`, `ExecutionPlan`, the `AuditReport` that scored the canonical, the `PromotionLedgerEntry` that named the canonical
3. **Include** every snapshot referenced by the closure's plans, audits, and execution provenances: `RuleSnapshot`, `CapabilityDeclarationSnapshot`, `PartialFidelityModelSnapshot`
4. **Include** all artifacts in the closure with both their `ContentProvenance` and `ExecutionProvenance`
5. **Exclude** refusal records, failed-candidate artifacts, and partial-fidelity records that are NOT in the canonical's lineage closure AND NOT referenced by the promotion rationale

The exclusion rule is what keeps the manifest from becoming "the entire orchestration database for this shot." Failed candidates from this run that the operator chose not to promote are queryable in the DB but do not travel with the published package.

### Manifest shape

```
ProvenanceManifest {
  manifest_id:                 UUID
  content_hash:                sha256
  shot_id:                     UUID
  run_id:                      UUID
  intent_id:                   UUID
  spec_convergence_trace_id:   UUID
  execution_plan_id:           UUID
  audit_report_id:             UUID
  promotion_ledger_entry_id:   UUID   # the editorial decision that named the canonical
  canonical_artifact_id:       UUID
  canonical_content_hash:      sha256

  full_lineage: {
    artifacts: [
      {
        artifact_id:           UUID
        content_hash:          sha256
        entity_type:           str
        content_provenance:    {...}
        execution_provenance?: {...}   # only on GenerationArtifacts
      }
    ]
    edges: [
      { from_artifact_id, to_artifact_id, relationship_type: "content_source" | "anchored_to" }
    ]
    superseded_within_run: [ artifact_id ]
  }

  snapshots_bundled_by_content: {
    rule_snapshot:              { snapshot_id, content_hash, body }
    capability_snapshot:        { snapshot_id, content_hash, body }
    partial_fidelity_snapshot:  { snapshot_id, content_hash, body }
  }

  refusal_and_partial_records: [
    # Only those in the canonical's lineage or referenced by promotion rationale
    { record_id, kind: "refusal" | "partial", verdict, dimensions, ... }
  ]

  cost_summary: {
    total_by_currency:   { USD: decimal, credits: int }
    by_stage:            { stage_id → cost }
    by_backend:          { backend_identity_triple → cost }
  }

  assembled_at:                timestamptz
  assembled_by:                "forge_bridge.orchestration.manifest_assembler"
}
```

### Snapshots bundled by content

Each referenced snapshot is included **in the manifest body**, not just by reference. A package opened later (months, years) does not require DB access to reconstruct methodology context. The snapshot's `content_hash` is recorded; the snapshot body is embedded.

The DB-side snapshot row remains the canonical source; the manifest carries a content-equal copy. If the DB-side row is ever lost (substrate migration, archive purge), the manifest is the durable surface — content-hashes guarantee equivalence.

### Cost aggregation

Pure summation walk over `ExecutionProvenance.cost` entries for each `GenerationArtifact` in the closure. Per umbrella §7 discipline: bridge sums what forge-generators reports; bridge never invents cost. Aggregation runs at assembly time and the result is recorded on the manifest.

### Replay-produced manifests

A replay run can produce its own canonical, which has its own manifest with its own `manifest_id` and `content_hash`. Multiple manifests for the same `shot_id` coexist — neither supersedes the other at the manifest layer. The `PromotionLedger` tracks which canonical is currently named for the shot, but historical manifests remain valid published extracts.

### Boundary with 4C

Phase 4B assembles the manifest as a JSON document (with embedded snapshot bodies). Phase 4C's `DeliverablePackage` packaging layer (forge-vision repo) wraps the manifest in the Flame-consumable folder structure (EXR/DPX sequence layout, color-space conversion, metadata sidecars).

The manifest is JSON; the package is the folder shape around it. 4B owns the former; 4C owns the latter.

---

## §9. Sibling registration protocol

### Discovery: entry points + config override

Bridge discovers siblings via Python entry points declared in each sibling's `pyproject.toml`:

```
[project.entry-points."forge_bridge.siblings"]
forge_generators = "forge_generators.bridge:register_bridge_adapters"
forge_vision     = "forge_vision.bridge:register_bridge_adapters"
```

On startup, bridge enumerates entries under the `forge_bridge.siblings` group, imports each entry point, and obtains the `register_bridge_adapters` callable for that sibling.

**Config override** for dev/local: a config file (or env vars) can:

- Disable specific siblings by name
- Enable additional local siblings (path to a Python module exposing `register_bridge_adapters`)
- Override the entry-point set entirely (for test isolation)

Resolution order:

1. Entry points → declared sibling set
2. Config override → enables / disables / adds local siblings (overrides entry points)
3. `required_capability_kinds` config → defines which kinds MUST register

### Function signature

```
def register_bridge_adapters(
    ctx: BridgeRegistrationContext,
    register_tool: RegisterToolCallable,
) -> None:
    """
    Sibling's entry point. Bridge calls this once at startup for each discovered sibling.
    The sibling calls register_tool(...) once per tool it exposes.
    The sibling does NOT import forge_bridge.* — ctx and register_tool are the only seams.
    """
```

The sibling does not import forge-bridge directly. The function signature is the only contract; the sibling depends only on the type definitions for `BridgeRegistrationContext` and `ToolRegistration` (which can be declared in a tiny shared types package or duplicated as protocols).

### `BridgeRegistrationContext` shape

```
@dataclass
class BridgeRegistrationContext:
    bridge_version:      str
    capability_kinds:    frozenset[str]    # kinds bridge expects (e.g., {"perceptual", "validation", "generation", "matte"})
    dry_run:             bool              # true in isolation tests; sibling should not perform side effects
    config:              Mapping[str, Any] # opaque per-sibling config from bridge config file
```

`config` is the channel for passing sibling-specific configuration without bridge needing to know the schema. A sibling reads its own config keys.

### `ToolRegistration` shape

```
@dataclass
class ToolRegistration:
    tool_id:        str                  # globally unique, e.g., "forge_generators.magnific.motion_control_pro"
    family:         str                  # "perceptual" | "validation" | "editorial" | "generation" | "matte"
    payload_family: str                  # "perception_validation_v1" | "generation_v1"  (umbrella §8 sibling families)
    schema:         dict                 # JSONSchema for invocation arguments
    handler:        Callable             # async or sync; bridge wraps appropriately
    capabilities:   Any                  # family-typed; bridge stores opaquely; planner reads

RegisterToolCallable = Callable[[ToolRegistration], None]
```

**`capabilities` is family-typed.** The bridge does NOT enforce a single capability schema across families. The sibling provides whatever shape the family conventions require:

- `family = "generation"` → forge-generators' `CapabilityDeclaration` (already shipped at 4A)
- `family = "perceptual"` → forge-vision-defined perceptual capability shape
- `family = "validation"` → forge-vision-defined validation capability shape

Bridge stores `capabilities` opaquely (as JSONB on the `ToolRegistration` record). The planner reads it during plan construction and applies family-appropriate scoring. New families add new shapes without bridge schema changes.

### Error semantics

| Scenario | Bridge behavior |
|---|---|
| Sibling entry point not found (declared but module missing) | Skip-with-event: emit `sibling_registration_failed` event with reason `"entry_point_missing"` |
| `register_bridge_adapters` raises during execution | Skip-with-event: emit `sibling_registration_failed` event with reason `"adapter_registration_raised"` and exception detail |
| Sibling registers zero tools | Skip-with-event: emit `sibling_registered_empty` event |
| Sibling registers but no tool's `family` is in a `required_capability_kinds` set after all siblings processed | **Hard-degraded mode**: emit `bridge_degraded` event with reason `"required_capability_missing"` and the missing kinds; bridge starts; planner refuses any plan requiring the missing kind with refusal code `no_feasible_backend` |

**Hard-degraded mode** means the bridge process is healthy and observable, but the planner cannot construct feasible plans for runs that need the missing capability kind. Operator sees the missing-kind event; downstream code queries `bridge_degraded` state by reading the event log. Nothing is silent.

`required_capability_kinds` defaults to empty (dev mode) — all siblings are optional. Production deployment sets this explicitly.

### What 4B does not own (registration scope)

Per the umbrella §4 amendment: the negative side (siblings don't import forge-bridge) is asserted by isolation tests on each sibling repo. The positive side — bridge actually performing discovery and registration — is what this section instantiates. Sibling-side test responsibility for the `register_bridge_adapters` protocol is the sibling repo's concern; this doc defines what bridge calls and what bridge expects.

---

## §10. Memory model alignment (umbrella §9 ↔ forge-bridge)

| Umbrella §9 category | Phase 4B instantiation |
|---|---|
| **Per-shot lifecycle state** | `orchestration_lifecycle_state` table (dedicated, operational) — one row per active run; mutable; archived implicitly via supersession when run completes |
| **Replay state** | Composed across multiple entities: `orch_locked_intent`, `orch_spec_convergence_trace`, `orch_execution_plan`, `orch_audit_report`, all `orch_generation_artifact` rows, snapshots — all content-addressable and immutable per repo discipline |
| **Methodology state** | `orch_rule_snapshot`, `orch_partial_fidelity_snapshot`, `orch_capability_snapshot` — semantic-artifact entities, content-addressable, immutable; new snapshots create new entities (never modify existing) |
| **Editorial state** | `orchestration_promotion_ledger` table (dedicated, operational) — append-only with canonical-pointer resolution by `ORDER BY promoted_at DESC LIMIT 1` |
| **Archival provenance** | `orch_provenance_manifest` semantic-artifact entity + embedded snapshot bodies; package layer (4C) wraps for Flame consumption |

The boundary discipline holds: every persistent thing in Phase 4B belongs to exactly one category. The hybrid storage doctrine (semantic → discriminator, operational → dedicated tables) maps cleanly onto the category boundary — semantic categories use the entity-discriminator family, operational categories use dedicated tables.

---

## §11. What 4B does NOT build (explicit non-goals)

- **Rule authoring UI or workflow.** Rules are authored by file edit; bridge snapshots them. No auto-amendment from observed failures.
- **Promotion UI.** Promotion is operator-driven via the substrate API (the `promote_candidate` decision event); no web/desktop UI in Phase 4.
- **Cross-shot methodology analytics.** The data is queryable; analysis surfaces are later-phase consumers.
- **Multi-operator promotion approval workflow.** Single-operator signoff suffices.
- **DB-level immutability enforcement.** Repository-layer discipline only in v0.1; triggers/rules/partial-uniques deferred.
- **Mid-run replay.** Top-level replay only. Stage-N replay deferred.
- **Auto-remediation.** The substrate pauses on zero candidates and dispatches to the operator; it does not auto-select a remediation entry point.
- **Auto-amendment of `PartialFidelityModelSnapshot` from observed deltas.** Operator amends by file edit.
- **Spec convergence Q&A automation.** The substrate stores and locks the conversation; it does not conduct it.
- **Plan-declared candidacy (vs derived from terminal state).** v0.1 derives candidacy from `lifecycle_state`. Plan-declared candidacy is the documented eject for diagnostic/control operators in future plans.
- **`polling_history` as a dedicated table.** v0.1 stores polling history as JSONB array on `orch_generation_artifact`. Promotion to a dedicated `orchestration_polling_events` table is the documented eject under cross-artifact polling query pressure.

Each deferral is deliberate. Phase 4B's commitment is the substrate that supports these capabilities later, not the capabilities themselves.

---

## §12. Implementation sequencing

Implementation against this doc proceeds in approximately this order. Each step lands as one or a few commits with passing tests before the next step starts.

| Step | Scope | Test coverage |
|---|---|---|
| 1 | Migrations 0004 + 0005 (relationship types + entity types + `content_hash` column) | Migration up/down roundtrip; existing tests still pass |
| 2 | Migrations 0006 + 0007 + 0008 (operational tables) | Migration up/down roundtrip; basic CRUD on each dedicated table |
| 3 | `ContentAddressedRepo[T]` base class + `DBOrchLockedIntent` model + `LockedIntentRepo` (canonical content-hash-and-insert pattern) | `insert_if_absent`, `get_by_content_hash`, refusal of `update()` |
| 4 | All other `orch_*` entity models + their content-addressed repos | Per-type repo tests |
| 5 | `OrchestrationLifecycleStateRepo`, `OrchestrationPromotionLedgerRepo`, `OrchestrationCompromiseLedgerRepo` | Dedicated-table repo tests; ledger aggregation queries |
| 6 | `GraphEngine.transition(...)` service layer with single-transaction discipline | Lifecycle row + event append atomicity; status / block consistency; transition vocabulary tests |
| 7 | Worker contract: `forge_bridge.orchestration.worker.GenerationPoller` (async task in bridge process) | Mock-driver tests; terminal-event emission; resumability test |
| 8 | Sibling registration: entry-point discovery + `BridgeRegistrationContext` + error-semantics paths | Discovery tests with mock siblings; required-capability-kinds tests; hard-degraded mode test |
| 9 | Planner: `forge_bridge.orchestration.planner.Planner` with six-pass model | Unit tests per pass; refusal-vocabulary tests; predicted-compromise tests against a stubbed `PartialFidelityModel`; remediation triage routing |
| 10 | Replay engine: `ReconstructionRequest` resolution + planner invocation + new-run setup | Pinning resolution tests; refusal vocabulary tests; remediation-entry-point routing tests; effective_pinning_policy persistence |
| 11 | Provenance manifest assembler: subgraph closure + snapshot bundling + cost aggregation | Closure rule tests (inclusion + exclusion); embedded-snapshot tests; cost summation tests |
| 12 | End-to-end smoke test: stub-backed seven-stage run from spec convergence to publish, producing a manifest | One mocked-shot smoke; one mocked-replay smoke; one mocked-remediation smoke |

Steps 1-5 establish the data layer; steps 6-7 establish the runtime; step 8 establishes sibling composition; steps 9-11 establish the orchestration semantics; step 12 proves the system end-to-end against stubbed siblings.

Real-sibling integration (forge-generators driver hooks, forge-vision perceptual operator calls for cross-capability transforms) is the cross-repo integration work that follows Phase 4B's repo-local completion.

---

## §13. Discipline carried forward

- **Design lands in this doc first; implementation against it second.** Implementation that diverges from this design requires an updated version of this doc.
- **Contracts crossing repo boundaries trace back to the umbrella, not this doc.** If implementation surfaces a cross-repo pressure not anticipated by the umbrella, the umbrella gets revised — not this doc.
- **Substrate prefers explicit constrained state over degraded execution.** Every refusal, partial, infeasibility, and degradation produces a typed, queryable artifact.
- **The substrate never invents — it surfaces.** Costs are summed, not estimated. Verdicts are declared, not inferred. Promotions are explicit, not automatic.
- **Semantic vs operational is load-bearing.** When in doubt about where an object lives, ask whether it participates in lineage. If yes, semantic (entity discriminator); if it is execution coordination, operational (dedicated table).
- **Repository transactions are caller-owned.** Repos take `AsyncSession` via constructor; never `commit()` themselves. Engine service layer owns transaction boundaries.
- **Subset assertions for evolving consumer contracts.** Tests assert what's required; exact equality only when the full set is intentionally part of the contract.
