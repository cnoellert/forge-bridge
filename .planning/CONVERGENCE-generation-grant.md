# Convergence — GenerationGrant authority mechanism (#146)

**Date:** 2026-07-01
**Subject:** How to build the `GenerationGrant` spend-gate that unblocks generators'
dark `forge_generate_*` tools (flips `_GENERATION_GRANT_AVAILABLE = True`).
**Method:** 5-view convergence (maintainer / operator-consumer / skeptic /
authority-security / future-evolution), grounded against `main`, redlined.
**Operator lean going in:** full ratify surface, build once, don't revisit.

---

## Grounding facts that shaped the answers

- **Storage is JSONB `attributes` on one shared `entities` table.** `orch_pipeline_run`,
  `assent_record`, and a future `generation_grant` are all rows discriminated by
  `entity_type`, every field in the `attributes` dict, exposed via `_attr()` view
  accessors (`orch_entity_views.py:99-117`). → adding `grant_id` to a run, or
  `budget`/`count` to a grant, is a **JSONB key-add + accessor, zero column
  migration**. A new entity type is **one CHECK-enum add** (`0009_assent_record`
  pattern), not a new table. *Stop optimizing for migrations.*
- **Two repo lineages, NOT interchangeable:** `PipelineRunRepo` = pure
  content-addressed **immutable** (update/delete raise). `AssentRecordRepo` =
  content-addressed **terms** + **mutable state machine** (`_transition` updates
  `status`+`attributes` in place, EventRepo-audited).
- **Both dispatch doors converge at one chokepoint:** `dispatch_plan` (planner /
  live `manual_qc` path) AND `dispatch_generation` (direct tool) both call
  `dispatch_envelope`, whose single `driver.submit()` is `dispatcher.py:280`. The
  planner door reaches it **without** passing `generation_entry`.
- **No live spend in bridge to gate:** the concrete driver lives in
  forge-generators; the stock registry is empty; the direct path has zero
  non-test callers; the consumer is dark pending this grant.
- **`AssentRecordRepo._transition` is non-atomic** (read-check-write, no CAS) —
  must NOT be the pattern for the spend consume.

---

## Converged positions

### Q1 — Entity + repo shape
**Distinct `generation_grant` entity; copy the `AssentRecordRepo` *lineage*
(immutable-terms + mutable state-machine), NOT `PipelineRunRepo`.**
This is the single seam expensive to reverse (future-evolution won it):
`PipelineRunRepo` is the tempting nearest neighbor but raises on update — a grant
that transitions state (and later carries #142's decrement) can't live on it.
- Terms body immutable + hashed; `status` mutable on the same row; EventRepo audit.
- States: `proposed → ratified → consumed` (+ `revoked`/`failed`).
- **No `chain_steps`, no `applied_at`/`apply_result`** — nothing to replay/apply;
  the *runs* spend, not the grant.
- **`nonce: uuid` in the terms body** so every mint is unique — prevents
  content-identity collapsing a re-quote onto a revoked/consumed grant
  (maintainer's resurrection catch). `grant_id = content_hash[:12]` stays an
  opaque 12-hex handle (keeps CLI/endpoint regex identical), per-mint-unique.
- **Cost stamped immutably** in the same hashed terms body.

### Q2 — Consumption + 1:many (the crux)
**Single-use grant, atomically CAS-consumed at the chokepoint; 1:many
schema-ready but NOT wired.**
Kills the naive `live == ratified` boolean (authority: on a 1:many grant that is
an unlimited-spend license — ratify once, submit forever). The operator's shape
reconciles all three lenses:
- Grant authorizes **one** submit, consumed via a **single atomic
  `UPDATE … WHERE status='ratified' RETURNING`** state-flip at `driver.submit()`.
- That IS authority's finite-atomic-consume (count-of-1 via terminal state); it
  hands **#141 idempotency for free** (consumed grant refuses the replay); it needs
  **zero** accumulator/counter/budget — the decrementing ledger is genuinely #142.
- The consume must **not** copy `_transition`'s non-atomic read-then-write (it
  double-spends under session-per-request) — conditional SQL update only.
- **Overrule:** future-evolution wanted to wire the reserved `manual_qc:217`
  remediation-inherit now — **rejected this slice**: a single-use grant, inherited,
  is already-consumed and would refuse the remediation run. Inherit belongs with
  #142's shared-budget model. Leave `:134`/`:217` reserved as-is.

### Q3 — Where the check lives  *(structural seam)*
**Chokepoint-mandatory + direct-door advisory, one shared helper.**
Both doors funnel through `dispatch_envelope`'s `driver.submit()`
(`dispatcher.py:280`); the planner/`manual_qc` path reaches it without passing
`generation_entry`, so guarding the direct door alone leaves the live door
ungated. The mandatory CAS-consume-then-submit lives at the chokepoint;
`generation_entry.py:107` gets an early *advisory* refuse calling the **same**
`_resolve_and_consume_grant` helper (never a second copy).

### Q4 — How the grant is resolved  *(structural seam)*
**`grant_id` as a new sibling kwarg on `dispatch_generation`/`dispatch_envelope`;
`run.grant_id` is the durable home when a run exists; NEVER in the
`InvocationEnvelope` or the `provenance` dict.**
The envelope feeds `content_provenance` (byte-stability — maintainer), so grant
stays out of it; a separate `grant_id: str | None` kwarg touches neither envelope
identity nor the composition executor. `provenance` is plan-lineage only. The core
loads the grant from the **store** by that id and checks/consumes persisted
`status` — a caller-supplied id is a lookup key, never trusted as authority.
Fail-closed falls out: no resolvable ratified grant → refuse. Absorbs the
skeptic's `run_id: uuid | None` bypass into the same gate.
Refusal: `DispatchResult(status="refused", refusal_code="grant_not_ratified")`;
distinct code `grant_consumed` for the replay case is optional but clearer.

### Q5 — Ratify surface + cost
**Full programmatic surface (repo + `POST /api/v1/ratify-generation` +
`fbridge ratify-generation` + one MCP ratify tool), all thin adapters over one
repo mint method; Console projection deferred to CA-line.**
- Endpoint response = canonical extensible **`grant.to_dict()`** (the assent
  discipline). Then #140 cost-preview is a `cost_estimate` key-add, #142 budget
  adds keys, Console (CA.1 pattern) templates the same JSON — zero endpoint
  re-touch. A bespoke flat response is what fossilizes.
- N surfaces / **1 repo mint method**; forbid direct grant-row writes
  (mirror `assent.py:40`).
- **Cost is peer-declared:** driver/capability `estimated_cost` stamped immutably
  on the proposed grant, re-rendered at ratify. Bridge never authors the dollar
  number (federation: source facts at peer boundaries).
- **Mint point:** the estimate/quote call mints the *proposed* grant (a free quote
  — reversible, no spend; "free" = no *spend*, not no *writes*).
  `forge_generate_*` has one mode: requires a ratified grant.
- MCP ratify tool is the flip-critical one (generators' proof runs through MCP);
  HTTP+CLI are same-slice fast-follow honoring build-once. Skeptic's "speculative
  surface for a dark consumer" is **noted, consciously overruled** by the
  build-once lean + the genuine value of a deliberate dollar-legible affordance
  for paid spend.

---

## Intentionally unbound (re-open trigger)
- **Remediation-inherit (`manual_qc:217`)** — pending #142's shared-budget model
  (what inheriting a partially-spent grant means). Re-open: iterative/remediation
  generation needs one assent to cover many attempts.
- **Budget/count ceiling + decrement ledger** — this is #142. Re-open: a
  batch/iterative caller needs quantity-scoped authorization.
- **Console dollar-affordance for grant ratify** — CA-line UI work. Re-open: paid
  render moves from MCP-proof to production operator use.
- **Real operator identity on ratify** — pending auth (SEED-AUTH-V1.5). Today
  structural-trust (only the operator surface calls ratify) — **stated in code +
  doc, not proven cryptographically.**

## Rejected (reason)
- **Reuse AssentRecord as the grant** — conflates two authority classes; pollutes
  its terminal 1:1 host-mutation machine with spend semantics.
- **Copy `PipelineRunRepo` (immutable) for the grant** — the one expensive-to-
  reverse mistake; a state-machine grant can't live on raise-on-update.
- **`live == ratified` boolean gate** — unlimited-spend license on a 1:many grant.
- **Wiring 1:many inherit / building the CAS accumulator this slice** — premature
  (→ #142); single-use terminal consume delivers safety without it.
- **Grant in the envelope / `provenance` dict** — breaks byte-stability / conflates
  spend-authority with plan-lineage.

## Proof honesty
Bridge has no live spend to gate (driver in forge-generators, consumer dark), so
bridge-side "done" is **fixture-verified**: a fake-driver test asserting
missing/unratified→refuse, ratified→submit-once→consumed, replay→refuse,
no-anchor→refuse. The **live** submit→poll→terminal proof is generators' job
post-flip. #146 done-criteria states exactly this.
