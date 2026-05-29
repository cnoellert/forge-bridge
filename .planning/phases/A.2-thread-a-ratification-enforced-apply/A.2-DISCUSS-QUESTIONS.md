---
milestone: v1.7
thread: A
phase: A.2
phase_name: Ratification + enforced apply — assent as substrate state
status: phase-discuss
opened: 2026-05-28
drafted: 2026-05-28
revised:
  - 2026-05-28 (v3 — second cross-voice micro-cycle absorbed. N1 (DT framing-grade, Creative concurring): C7 absorption in v2 landed adjacent to the concern (lifetime evolution within the record) rather than on it (apparent contradiction between framing's per-turn-statelessness invariant and A.2's persistence-across-turns requirement). v3 adds explicit runtime-object-vs-substrate-snapshot reconciliation in R-A2.1+R-A2.2: graph-intent as runtime object is per-turn; graph-intent as substrate snapshot is persistent; A.2 persists the snapshot, not the runtime object; assent_record stores the snapshot. Without this paragraph, Stage 1b would re-raise the contradiction reading framing + discuss side-by-side. N2 (DT archaeology-grade): FC count drift swept — body has 8 top-level FCs (FC-A2.1..FC-A2.8) with FC-A2.2a subordinate; prose previously saying "seven forward-looking caveats" updated. Per Creative close-frame: catch profile has shifted entirely from architecture discovery to archaeology consistency; DT sign-off territory reached. Next meaningful scrutiny expected in A.2-PLAN.md rather than another discuss-cycle expansion.)
  - 2026-05-28 (v2 — first cross-voice cycle absorbed. Framing-grade catches: C1 demoted the audit-event-contamination paragraph relative to the constitutive-semantic argument under R-A2.0 (DT — strongest argument deserves load-bearing weight); C3 distinguished extend-primitive-law cascade-independence from the kwarg-TYPE dependence on R-A2.0 (DT — law is general, type signature is not); C8 replaced certainty-language with preference-language throughout R-A2.0 prose (Creative — discuss-stage discipline; ruling must remain visibly open per framing's category separation). Polish-grade catches: C2 renamed "Stage 1b carve-outs" → "Discuss carve-outs — plan locks (Stage 1b verifies)" (DT — authority misplacement in heading); C4 replaced cycle-count prediction with catch-size diagnostic (DT — predicting cycles doesn't help downstream); C5 added CAR-docstring-scope broadening caveat (DT — generic implementation vs orch_*-scoped docstring is a future archaeology trap); C6 added 12-char prefix directional lean on graph-intent-id wire shape (DT — discuss has enough info to express preference); C7 added persistence two-lifetimes clarification distinguishing graph-intent body from ratification metadata (DT); C9 named the distinction between graph-intent identity and ratification-event identity, ruling on the former only (Creative); C10 added FC-A2.5 deliberate-dual-surface note per Q5's operator-surface ruling (Creative). Cross-voice cadence converged in one cycle: 3 framing-grade + 7 polish = 10 catches absorbed; per Creative close-frame, room energy now reserved for plan stage unless a new architectural objection appears.)
type: phase-discuss
derives_from:
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-FRAMING.md
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-FRAMING.md
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-CLOSE.md
grounding: A.2-FRAMING.md v3.1 (ratified at 072948f) + this-session reads of forge_bridge/store/staged_operations.py + forge_bridge/store/content_addressed_repo.py + forge_bridge/store/migrations/versions/0003_staged_operation.py + forge_bridge/core/staged.py + forge_bridge/mcp/tools.py (staged-ops impl section)
artifact_role: load-bearing — A.2-PLAN.md drafts from these converged rulings
review_state: writing-room-v3-dt-sign-off-territory-pending-operator-ratification
---

# A.2 — Phase discuss: nine framing-grade questions, room-converged v3

> **What this artifact is.** The discuss-stage convergence artifact
> for A.2's nine framing-grade questions (Q-A2.0..Q-A2.8). v2
> absorbed the first cross-voice cycle (3 framing-grade + 7
> polish-grade); v3 absorbed a second micro-cycle (N1
> runtime-vs-snapshot reconciliation + N2 FC count drift sweep).
> Q-A2.0 walks all three candidate shapes per Creative C3 cascade
> discipline; downstream rulings name their dependence on Q-A2.0's
> resolution explicitly so the room can trace consequences. Operator
> ratification pending; per Creative close-frame at v3, the room
> reached DT sign-off territory and remaining scrutiny is expected in
> A.2-PLAN.md rather than further discuss-cycle expansion.
>
> **What this artifact is not.** Not A.2-PLAN.md. The plan derives
> from this once ratified; the rulings below are framing-grade
> rulings, not implementation specs.

## Architectural inheritance (from A.2-FRAMING.md v3.1)

A.2 framing v3.1 (ratified `072948f`) locked six architectural laws
and one common-case assumption that bind every ruling below:

| Law (binding) | Source |
|---|---|
| Substrate self-views are first-class operator surfaces (derived, not reconstructed) | Inherited Thread A |
| The LLM never owns assent | Q5 constitutional |
| Enforcement via substrate composition — assent check AT the commit primitive inside `run_chain_steps` | Inherited Thread A (FC-5) |
| Ratification attaches to graph-intent identity | A.2 framing v3.1 (promoted from working position per Creative C5) |
| Primitive-responsibility extension (narrowly scoped) | A.2 framing v3 (Creative C1) |
| Coexistence architecture preserved — three chat regimes; no 4th | Inherited A.1 |

| Common-case assumption (design center, not constraint) | Source |
|---|---|
| Sync apply — operator assent within same session, seconds-to-minutes | A.2 framing v3 (Creative C2) |

These are not relitigated below. Rulings flow from them.

## Grounding refresh — verified 2026-05-28 against main @ 072948f

This-session reads grounding Q-A2.0 + Q-A2.1 + Q-A2.6:

| Site | Status / load-bearing finding |
|---|---|
| `forge_bridge/store/staged_operations.py:1-115` — module docstring + state machine | ✓ State machine `proposed → approved → executed/rejected/failed` (5 states, 5 transitions in `_ALLOWED_TRANSITIONS`); composes EventRepo on shared session for atomicity |
| `forge_bridge/core/staged.py:5-7` — module docstring constitutive invariant | ✓ **Load-bearing verbatim:** *"forge-bridge is the bookkeeper that persists the proposed operation, its approval state, and the realized result; it does NOT execute the operation."* |
| `forge_bridge/core/staged.py:30-36` — `StagedOperation` class docstring | ✓ Reinforces: *"The proposer subscribes to `staged.approved` events via the existing event bus and executes against its own domain."* |
| `forge_bridge/store/migrations/versions/0003_staged_operation.py` | ✓ `staged_operation` is a `ck_entities_type` CHECK-constraint discriminator value on the shared `entities` table; JSONB `attributes` column carries the typed payload (8 keys per D-02 in `_serialize`) |
| `forge_bridge/store/content_addressed_repo.py:32-127` — `ContentAddressedRepo` base class | ✓ **Shipped at HEAD as generic base.** Uses canonical-JSON sha256, `insert_if_absent`, `__entity_type__` ClassVar discriminator. Generic; orch_* phase-4b consumers depend on it but the base ship is independent |
| `forge_bridge/mcp/tools.py:88-266` — staged-ops MCP tool impls | ✓ Four approval-surface tools (`forge_list_staged` / `forge_get_staged` / `forge_approve_staged` / `forge_reject_staged`). Propose-side tools (`forge_stage_*`) live in consumer per CLAUDE.md "Approval surface, not propose-side" |
| `forge_bridge/mcp/tools.py:212-235` — `_approve_staged_impl` write path | ✓ Calls `StagedOpRepo.approve(op_id, approver=params.actor)` — only sanctioned write path; the MCP `actor` field is the human-approver identity |

**Three load-bearing findings shape the rulings below:**

1. **`staged_operation` is schema-flexible** (DBEntity + JSONB attributes).
   Q-A2.0(b) is schema-feasible — any graph-intent shape fits.
2. **The shipped substrate carries a load-bearing constitutive
   invariant**: bridge is bookkeeper, NOT executor. The proposer
   subscribes to events and executes against its own domain. Bridge
   ships only the approval-surface tools; propose-side lives in
   consumers (projekt-forge in production).
3. **`ContentAddressedRepo` ships at HEAD as a generic base class.**
   A.2 can extend it for an `assent_record` entity_type WITHOUT
   depending on phase-4b's orch_* consumers — the base is mainline,
   not in-flight.

Finding (2) is the load-bearing one for Q-A2.0. The next nine rulings
flow from how the room reads it.

## The nine rulings (writing-room v3, DT sign-off territory)

### R-A2.0 — `staged_operation` positioning: PARALLEL SUBSTRATE (writing-room lean, room-converged v2)

**Ruling (writing-room v3):** Shape (a) — parallel substrate. A.2 ships
its own `assent_record` substrate; `staged_operation` remains for the
MCP-side propose-approve workflow. Two substrates coexist with what the
writing room currently reads as distinct constitutive identities — a
reading the room could revise if a future cycle surfaces evidence that
the distinction is workflow rather than substrate.

**Walk of the three candidate shapes** (per Creative C3 cascade
discipline; honoring "trace downstream collapse explicitly under each"):

**Shape (a) — Parallel substrate.** A.2 ships `assent_record`
(content-hash-keyed, table-backed per Q-A2.1+Q-A2.2 joint).
`staged_operation` stays exactly as shipped. The two state machines
coexist on the same `DBEntity` table via distinct `entity_type`
discriminators. The four shipped `forge_*_staged` MCP tools continue
to operate on `staged_operation`; the new `fbridge ratify` CLI
operates on `assent_record`. **Cascade under (a):** Q-A2.1..Q-A2.8
leans below apply as framed.

**Shape (b) — Built on top.** A.2's preview is a `staged_operation`
row with `state=proposed` carrying graph-intent in the `parameters`
JSONB; `fbridge ratify` transitions to `state=approved`; apply
transitions to `state=executed` or `state=failed`. Reuses shipped
substrate. **Cascade under (b)** — per framing Q-A2.0 cascade
analysis, collapses Q-A2.1 (identity = `staged_operation.id`), Q-A2.2
(storage = existing table), Q-A2.3 (partial), Q-A2.4 (partial — taxa
mirror state machine), Q-A2.6 (partial — CLI↔`forge_approve_staged`
relationship requires explicit positioning), Q-A2.8 (partial — rides
shipped identity-field decisions).

**Shape (c) — Supersession.** `assent_record` becomes the canonical
approval lane; `staged_operation` deprecates for the chat-originated
path. **Cascade under (c):** Q-A2.1..Q-A2.2 designed de novo; legacy
`staged_operation` deprecates; MCP-tool consumers (projekt-forge)
affected; potentially milestone-scale rather than phase-scale A.2.

**Rationale for (a):**

The writing-room lean rests on **what the room currently reads as a
constitutive-semantic divergence between the two substrates**, not on
a state-machine shape difference. The state machines look surprisingly
similar (`proposed/approved/executed`-shaped on both sides); the
underlying constitutive identities appear different.

**The real question hiding under R-A2.0** (per Creative cycle-1
meta-frame): is the bookkeeper/executor distinction *constitutive*
identity or *behavioral* identity? If constitutive, the substrate
itself encodes the bookkeeper invariant and (a) is the structurally
right call. If behavioral, the invariant is a workflow convention
overlaid on a more general "human-in-the-loop authorization" substrate,
and (b) becomes plausible because `staged_operation` could legitimately
host both workflow shapes under its ontology.

The current writing-room read: the distinction is constitutive,
documented prominently across `staged.py:5-7` AND CLAUDE.md
("Approval surface, not propose-side"). The room acknowledges,
however, that the invariant lives in **docstrings + project prose,
not in code-enforced substrate semantics** — `StagedOpRepo`, the
state machine, and the audit-event emission do not reference or
enforce the bookkeeper-not-executor invariant. That cuts both ways:

- **Constitutive reading:** documented prominently across multiple
  load-bearing surfaces (substrate docstring + CLAUDE.md) ⇒ it
  functions as architectural invariant via convention even without
  code enforcement; changing it is a substrate-identity change.
- **Behavioral reading:** docs-only distinction ⇒ workflow convention
  with no substrate enforcement; could legitimately be relaxed if the
  ontology is read as more general than the documented usage.

The room currently reads constitutive. The room could rule behavioral
without rejecting the substrate evidence — only by reading it as
docs-level convention rather than substrate-level identity.

**Reference reads, holding the constitutive interpretation:**

`staged_operation` (shipped — verbatim from `staged.py:5-7`):

> forge-bridge is the bookkeeper that persists the proposed
> operation, its approval state, and the realized result; it does
> NOT execute the operation.

Under the constitutive reading, this names a load-bearing invariant:
**bridge as bookkeeper, never as executor**. Consumer (projekt-forge
in production) proposes via consumer-owned `forge_stage_*` MCP tools;
human approves via bridge's approval-surface tools; consumer
subscribes to `staged.approved` events and executes against its own
domain. Bridge persists; consumer executes. The propose-side and
execute-side both live OUTSIDE bridge.

A.2's `assent_record` (proposed by R-A2.0):

- **Propose-side is bridge** (chat handler regime-3 emits preview from
  bridge-compiled graph-intent)
- **Execute-side is bridge** (`run_chain_steps` runs INSIDE bridge once
  assent is recorded, per FC-5 inherited from A.1)
- **Approve-side is operator** (via `fbridge ratify` CLI)

Under the constitutive reading, A.2's substrate inverts the bookkeeper
invariant on the propose AND execute sides. The only side that
overlaps is approve.

**Shape (b) "Built on top" appears to require one of two moves the
writing room currently views as problematic:**

- **Move 1:** redefine `staged_operation`'s bookkeeper invariant. The
  invariant is documented prominently in `staged.py` AND in CLAUDE.md
  ("Approval surface, not propose-side"); shipped consumers
  (projekt-forge) depend on this semantic. Under the constitutive
  reading, redefining is a breaking change to the substrate's
  published contract. (Under the behavioral reading, this is less
  costly — the docstring narrows; consumers continue working.)
- **Move 2:** introduce a hidden discriminator branch ("this
  staged_operation row's proposer is bridge, executor is bridge; that
  one's proposer is consumer, executor is consumer"). Adds a hidden
  mode-bit on top of the clean entity_type discriminator pattern,
  conditioning subscriber semantics on undocumented row provenance.

(A secondary concern under shape (b) is audit-event semantic
contamination: `StagedOpRepo._append_event` emits `staged.*` events
on a shared session, and consumers subscribed to those events for
projekt-forge workflows would also receive chat-side ratification
events. This is real but follows downstream from Moves 1 and 2 above
rather than standing as an independent argument.)

**Shape (c) "Supersession" is milestone-scale.** Deprecating
`staged_operation` reaches the propose-side MCP tool surface
projekt-forge depends on. Not phase-scale, independent of how the
constitutive/behavioral question is read.

**Shape (a) "Parallel substrate" most directly preserves the
divergence as currently understood:**

Two substrates, two constitutive identities (under the current room
reading):
- `staged_operation` — bookkeeper substrate. Bridge persists what
  consumers proposed for humans to approve, and the result the
  consumer reports back. **Bridge is bookkeeper.**
- `assent_record` — authority-attached substrate. Bridge persists
  operator decisions on bridge-compiled graph-intents that bridge
  will execute. **Bridge is executor.**

Conceptual fragmentation cost is real and acknowledged (FC-A2.1
below). The alternative costs — redefining the shipped invariant,
inventing a hidden discriminator branch, or accepting milestone-scale
A.2 — are what the room currently reads as structurally worse under
the constitutive interpretation. If the room rules behavioral
instead, this calculus shifts and (b) becomes the structurally right
call.

**Honest acknowledgement to the room:** the substrate-coherence
pull toward shape (b) is what
`[[feedback-substrate-coherence-revealed-retrospect]]` warns about.
The framing categorized this question as UNRESOLVED for a reason —
the room may rule otherwise. If the room rules (b), R-A2.1..R-A2.8
cascade per the framing's cascade analysis; the rulings below name
the shifts explicitly so the cascade is mechanically traceable.

**Discuss-grade distinction within (a) per Creative C4:** "parallel
substrate" specifically — A.2 ships a new authority substrate that
runs PARALLEL to staged_operation, NOT as a long-term step toward
collapsing them. If the room later wants substrate consolidation,
that's a future-phase question with its own framing. Naming the
parallel-vs-supersession distinction now keeps the future maneuver
explicit.

---

### R-A2.1 + R-A2.2 — Joint: CONTENT-HASH identity + `ContentAddressedRepo`-pattern table

**Ruling (writing-room v3, joint per Creative coupling rule):**

- **R-A2.1 (identity):** Content-hash. sha256 over canonical JSON
  serialization of the chain-step `list[str]`. Same canonical-JSON
  shape `ContentAddressedRepo._canonical_hash` already ships:
  `sort_keys=True, separators=(',', ':'), ensure_ascii=False`.
- **R-A2.2 (storage):** New substrate table backed by the
  `ContentAddressedRepo` pattern — `entity_type='assent_record'`,
  content-hash column populated, `attributes` JSONB carries graph-intent
  body + decision metadata. New Alembic migration extends
  `ck_entities_type` CHECK to include `'assent_record'` (analog to
  migration 0003 for `staged_operation`).

**Rationale.** Creative's coupling rule binds Q-A2.1 + Q-A2.2 as joint:
content-hash + content-addressed storage is a coherent pair;
content-hash + JSONL is the least coherent combination.

`ContentAddressedRepo` ships at HEAD as a generic base class. A.2
extending it for `assent_record` is additive infrastructure reuse — no
phase-4b coupling, because the BASE class is mainline (independent of
the orch_* consumers in flight). The CAR base already enforces:
- `content_hash` computed by repo (never trusted from caller)
- `insert_if_absent(body)` idempotent-by-content
- Immutability discipline (`update`/`delete` raise `ImmutableArtifactError`)

These are exactly the disciplines A.2's assent_record substrate
wants. Reusing the base avoids reinventing canonical-JSON +
idempotent-insert + immutability machinery.

**Why content-hash over UUID:** content-hash gives the substrate the
identity-IS-content stability the framing's "ratification attaches to
graph-intent identity" law wants. UUID makes the identifier
independent of content — which means two identical compile-intents
get different IDs, breaking the natural dedup of "operator already
ratified this exact graph-intent in a prior turn." Content-hash is
also what FC-A2.3 + FC-A2.4 forward-looking reasoning (drift
detection, re-compile equality check) naturally rides on.

**Identity scope — what R-A2.1 rules on:** the framing's law is that
**graph-intent identity is content-addressed.** R-A2.1 rules ONLY on
graph-intent identity. **Ratification-event identity remains an open
question** — A.2 does not foreclose whether future ratification
history (repeated ratifications of the same graph by the same
operator, independent ratifications by different operators, revoke
+ re-ratify cycles) is content-addressed or event-addressed. The
discuss-stage ruling preserves maneuverability per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`. Future
plans (or post-A.2 phases) decide ratification-event identity on
their own merits.

**Reconciling per-turn statelessness with persistent storage** (per
DT N1, Creative concurring). The A.2 framing's anti-scope
("Multi-turn graph-intent persistence — A.2 preserves the per-turn
statelessness of graph-intent") appears in tension with A.2's need
to persist graph-intent across the propose-turn → apply-turn gap.
The reconciliation makes the apparent contradiction disappear:

- **Graph-intent as runtime object is per-turn.** `compile_intent()`
  produces a `list[str]` chain-step text within a turn; the runtime
  object does not survive the turn boundary; subsequent turns
  re-invoke `compile_intent()` from natural language without
  inheriting prior-turn runtime state. The framing's
  per-turn-statelessness invariant constrains THIS layer.
- **Graph-intent as substrate snapshot is persistent.** R-A2.7
  store-and-replay persists a SNAPSHOT of the runtime object as the
  `assent_record` body. The snapshot is content-addressed,
  immutable, and survives across turns by virtue of substrate
  storage — not by virtue of any runtime accumulation.
- **A.2 persists the snapshot, not the runtime object.** Persisting
  at the substrate layer does not violate per-turn-statelessness at
  the runtime layer. These are distinct architectural layers under
  R-A2.0(a) parallel-substrate positioning.
- **`assent_record` stores the snapshot.** This is what makes
  store-and-replay possible without contradicting per-turn-stateless
  graph-intent: the apply path reads a substrate snapshot keyed by
  content-hash, not a runtime object that survived from a prior
  turn.

The framing's "Multi-turn graph-intent persistence" anti-scope
addresses runtime-layer accumulation (e.g., chat state inheriting
prior-turn graph-intents as context); A.2's substrate-layer
persistence does not violate this — it stores immutable snapshots
of decided artifacts, not running state. Named explicitly here so
the plan inherits the reconciliation; without it, a Stage 1b
reviewer reading framing + discuss side-by-side would reasonably
re-raise the apparent contradiction.

**Two lifetimes within the record** (per DT C7): the assent_record
carries two distinct things with distinct lifetimes:
- **Graph-intent body** (chain_steps `list[str]`) — immutable,
  content-addressed, persists as long as the substrate holds the
  record. Eternal under the immutability discipline CAR enforces.
- **Ratification metadata** (decided_by, decided_at, applied_at,
  audit-event references) — mutable in the sense that it accumulates
  state transitions over the record's lifetime (proposed → decided
  → applied). Append-only at the event-bus level.

Both lifetimes coexist within a single record under R-A2.0(a).
Whether they should share an entity_type or split into
graph-intent-as-`assent_record-body` + ratification-history-as-events
is a plan-stage question that follows downstream from R-A2.1+R-A2.2.
What R-A2.1+R-A2.2 lock at discuss stage is graph-intent identity
shape; the ratification-history shape is plan stage's call.

**Coherent pair selection per Creative's rule:** content-hash +
new-CAR-table is the coherent pair; the alternative coherent pair
(UUID + JSONL log) trades dedup-stability for operator-grep-able
archaeology. Under sync-apply common-case assumption, dedup-stability
is the load-bearing property; archaeology can be served via the
existing event-bus pattern (FC-A2.7 below).

**Pattern, not implementation dependency:** A.2 extends
`ContentAddressedRepo` (the shipped base class). A.2 does NOT depend
on phase-4b's orch_* repos. If phase-4b's CAR usage evolves
post-A.2, A.2's `assent_record` repo is insulated — both ride the
base, neither depends on the other.

**Cascade under R-A2.0(b):** if the room reverses R-A2.0 to (b)
"Built on top," R-A2.1+R-A2.2 collapse to "use `staged_operation.id`
+ existing table." The content-hash discipline would either be lost
or grafted onto `staged_operation` as a new column — both worse than
(a)'s clean extension.

---

### R-A2.3 — Expiration: NO EXPIRATION, DRIFT-INVALIDATES

**Ruling (writing-room v3, confirming framing lean (a)):** No TTL on
assent records. Drift detection (re-compile producing a different
content-hash than the assented preview) invalidates assent at apply
time.

**Rationale.** Under the Thesis sync-apply common-case assumption,
TTL is not load-bearing for the design center (operator assents and
applies within the same session). Drift-invalidation is the
substrate-grounded check: if a re-compile produces a different
graph-intent content-hash, the operator's prior decision doesn't
apply because they decided on a different graph.

This ruling presupposes R-A2.7 store-and-replay. Under store-and-replay
the chain-step `list[str]` is persisted alongside the content-hash;
drift detection at apply time compares the persisted chain-step hash
against the operator-assented hash. If they match (they will, in the
store-and-replay flow), assent applies. (Re-compile path under R-A2.7(b)
would compute a fresh hash from a fresh compile and gate equality
there — also valid drift detection, with the failure-mode trade-off
the framing names.)

**Cascade under design-center shift:** if the room contests the
sync-apply common-case assumption (shifts to async-tolerance), R-A2.3
may need a TTL position regardless of drift semantics. Framing
flagged this as a re-evaluation trigger; ruling carries that flag
forward.

---

### R-A2.4 — Chat-side SSE taxa: NEW `apply_complete` terminal taxon

**Ruling (writing-room v3, confirming framing lean (b)):** Add a new
terminal SSE taxon `event: apply_complete` for the ratified-apply
success path, distinct from regime-2's `event: chain_complete`. A.2
ships 6 chat-side terminal taxa total (A.1's 5 + `apply_complete`).

**Rationale.** A.1's L9 invariant: distinct event taxa for distinct
architectural outcomes. *Ratified mutation applied* and *non-mutating
chain completed* are different authority transitions — the former
crossed an operator-assent gate, the latter did not. Per
`[[feedback-description-layer-multi-register-surface]]`: distinct
registers reach distinct behaviors. Folding both into
`chain_complete` collapses the architectural distinction at the wire
surface.

**Failure-side terminal taxon:** the apply path can fail at either
the assent check (`assent_invalid`) or downstream chain execution
(falls into existing `chain_aborted` semantics if a non-commit step
fails, or a new sub-taxon if the commit-node verification fails).
The exact wire-shape of failure-side taxa is a discuss carve-out
(below) for plan to lock.

**Cascade under R-A2.0(b):** if the room reverses R-A2.0 to (b), the
ruling shifts toward shape (d) from the framing — SSE taxa mirror the
`staged_operation` state machine
(`event: staged_proposed/approved/executed/failed`). Adding both (b)
and (d) under R-A2.0(b) would duplicate the state-machine vocabulary
at the chat surface, so the room would have to pick one.

---

### R-A2.5 — `CommitNode.verify()` signature: OPTIONAL `assent` kwarg

**Ruling (writing-room v3, confirming framing lean (a)):**
`CommitNode.verify(held, fresh, assent=None) -> CommitVerification`.
When `assent` is None, drift-only check (backward-compatible with the
4 test call sites). When provided, both drift and assent validity
fire. `CommitVerification` dataclass gets two new fields:
`assent_valid: bool` and `assent_record: AssentRecord | None`.

**Rationale.** The narrowly-scoped extend-the-primitive law applies
directly here: `commit.verify(...)` already owns the
authority-gate responsibility (it's the substrate primitive A.1 D2
shipped as the named home for `compile→commit` authority transition).
A.2 extends that primitive rather than reconstructing the assent
check at a higher consumer layer.

The 5-call-site grounding from the framing means migration cost is
trivial either way; the lean rides architectural-shape ground:

- Option (b) sibling-method (`verify` stays + new `verify_with_assent`)
  is a structurally-cleaner version of the anti-pattern — still
  two-call composition at the consumer (`if assent: verify_with_assent
  else: verify`), authority lives in consumer branching, not in
  the primitive.
- Option (c) always-required positional `assent` breaks backward
  compat without architectural gain — the drift-only check is a
  legitimate use case (the 4 test call sites exist for a reason).

Optional kwarg keeps authority inside the primitive while preserving
the drift-only invocation shape consumers already use.

**Law-independence vs kwarg-type-dependence on R-A2.0** (per DT C3):
two distinct independence claims that must be held apart.

- **The extend-the-primitive LAW is cascade-independent** from R-A2.0.
  The law constrains "don't reconstruct authority-gate logic in
  consumer code"; that constraint holds the same shape under (a),
  (b), or (c). The room rules on the law, not on the implementation.
- **The kwarg TYPE is NOT cascade-independent** from R-A2.0. Under
  R-A2.0(a) parallel substrate, the kwarg is `assent:
  AssentRecord | None`. Under R-A2.0(b) built-on-top, it's
  `assent: StagedOperation | None` (or a narrower projection
  thereof). Under R-A2.0(c) supersession, it's the canonical
  substrate type whatever the room rules. R-A2.5 rules on the
  signature SHAPE (optional kwarg with None default for backward
  compat); the specific Python type annotation cascades from R-A2.0
  and is locked at plan stage.

This distinction matters because conflating law and type would have
the discuss artifact appear to rule on a Python signature when it
should rule on an architectural pattern. The signature follows from
R-A2.0 + R-A2.5 together at plan stage.

---

### R-A2.6 — CLI surface: TOP-LEVEL `fbridge ratify <graph-intent-id>`

**Ruling (writing-room v3, confirming framing lean (a)):** Top-level
subcommand `fbridge ratify <graph-intent-id> [--actor LOCAL]`.
Matches the existing top-level pattern (`chat`, `exec`, `run`,
`flame-exec`). Single verb; no subgroup until pressure exists.

Under R-A2.0(a), the relationship to `forge_approve_staged` (MCP
tool) is: **parallel surfaces targeting different substrates.** Not
sugar, not the same operation under different transport — different
constitutive identities:

- `forge_approve_staged` operates on `staged_operation` rows
  (consumer-proposed, human-approved, consumer-executed).
- `fbridge ratify` operates on `assent_record` rows (bridge-compiled,
  operator-assented, bridge-executed).

The CLI and the MCP tool don't collide because they target distinct
entity_type discriminators. Operator using `fbridge ratify` on a
staged_operation UUID is a usage error caught by entity_type lookup
(structured error response, not silent dispatch). Operator using
`forge_approve_staged` on an assent_record UUID is symmetric.

**Exit codes (locked pattern from `fbridge flame-exec`):** 0 = ok,
1 = failure (assent failed to record, e.g., unknown graph-intent-id
or storage error), 2 = transport (daemon unreachable). Discuss
carve-out below for the exact error envelope (plan locks).

**Cascade under R-A2.0(b):** if the room reverses, the CLI↔MCP
relationship shifts to "parallel surfaces over the same operation."
Either CLI delegates to the same `StagedOpRepo.approve` code path as
`_approve_staged_impl`, or one is sugar for the other. R-A2.6 still
lands shape (a) top-level naming; only the delegation pattern shifts.

---

### R-A2.7 — Apply flow: STORE-AND-REPLAY

**Ruling (writing-room v3, confirming framing constitutional-grade
lean (a)):** Store-and-replay. The preview-emit step persists the
chain-step `list[str]` alongside the graph-intent-id content-hash in
the `assent_record` body. Apply flow looks up the persisted chain by
graph-intent-id (after assent-validity check) and feeds it directly
to `run_chain_steps`. No second compile_intent call between assent
and apply.

**Rationale.** The authority chain Thread A is building:

```
NL → compile → graph-intent → preview → ratify
                                          ↓
                              replay exact graph-intent
                                          ↓
                                        commit
```

Not:

```
NL → compile → graph-intent → preview → ratify
                                          ↓
                                      recompile
                                          ↓
                                        execute
```

The re-compile shape (R-A2.7(b)) quietly hands authority back to the
compiler between assent and apply. The framing's verbatim Creative
position: *"even if the natural-language request is identical, the
compile stage is inferential. The entire point of Thread A was to
move authority away from inference at the boundary."* Store-and-replay
binds operator authority CONSTITUTIONALLY to the specific graph-intent
they decided on; re-compile binds it content-hash-equality-conditionally
(modulo LLM sampling noise — a known failure mode per the framing's
trade-off matrix).

**Failure-mode trade-off matrix (from framing, ruling adopts):**

| Failure mode | Store-and-replay (a) | Re-compile + hash gate (b) |
|---|---|---|
| LLM sampling noise between assent + apply | impossible (no second LLM call) | UX-catastrophic — re-ratification storm on noise |
| Substrate drift (tool deleted/renamed) | caught at run-time via `CompileToolUnknown` taxa | caught at hash boundary before apply attempt |
| Sync apply latency (A.2 design center) | identical | identical |
| Async apply latency (outside A.2 design center) | safer (no LLM dependency) | substrate-drift detection more valuable |

**Cascade under design-center shift:** if the room contests the
sync-apply common-case assumption, R-A2.7's lean shifts toward (b).
The framing names this as a re-evaluation trigger; ruling carries
forward.

**Cascade under R-A2.0(b):** `assent_record.body` storage of
chain-step `list[str]` becomes `staged_operation.parameters` storage
of the same. R-A2.7 lean shape unchanged; only the storage substrate
shifts.

---

### R-A2.8 — Multi-operator: `decided_by` placeholder field

**Ruling (writing-room v3, confirming framing lean (a)):**
`assent_record.body` carries a `decided_by` string field. Pre-auth
default: `"local"`. SEED-AUTH-V1.5 will populate from authenticated
identity when auth lands. No identity validation in A.2; field is
structurally a placeholder.

**Rationale.** Per `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`:
the placeholder field is explicit deferral language; absence is
implicit rejection. One string column / one JSONB key is structurally
free and future-proofs the substrate naturally.

The CLI `--actor` flag (R-A2.6) populates `decided_by` directly. CLI
default to `"local"` matches the assent_record default; explicit
`--actor` lets operators distinguish workstations or roles informally
pre-auth.

**Cascade under R-A2.0(b):** `decided_by` rides existing
`staged_operation.parameters.proposer` field semantics (currently a
free-string identity per D-07). R-A2.8 lean unchanged; storage field
location shifts.

---

## Forward-looking caveats for the plan drafter

Not blocking the rulings. Ammo for Stage 1b and the spec.

**FC-A2.1. Substrate-coherence-revealed-retrospect candidate.**
R-A2.0(a) ships two substrates with surface-similar state machines
and surface-different constitutive identities. In a future world
where consumers (projekt-forge) evolve their staged-operation usage
toward bridge-executed semantics (or A.2's assent_record substrate
evolves toward consumer-executed semantics), the two substrates may
converge under a unified "authorized-operation" pattern. Not A.2's
job. `[[feedback-substrate-coherence-revealed-retrospect]]` shape —
flag in the plan as a "future-phase pressure point" claim, not an
A.2 design choice. The fragmentation is real but constitutive, not
accidental.

**FC-A2.2. `ContentAddressedRepo` extension pattern.** A.2 ships a
new `AssentRecordRepo(ContentAddressedRepo)` subclass at
`forge_bridge/store/assent_record_repo.py`. Sets `__entity_type__ =
"assent_record"` and a `__model__` that materializes from
`DBEntity.attributes`. Reuses the base class's `_canonical_hash` +
`insert_if_absent` + immutability discipline. Migration extends
`ck_entities_type` CHECK to include `'assent_record'` (analog to
`0003_staged_operation.py` migration). Plan must specify the
`AssentRecord` core dataclass shape (sibling to `StagedOperation`).

**FC-A2.2a. CAR docstring scope broadening** (per DT C5). The
`ContentAddressedRepo` base class is generic by implementation
(`Generic[T]`, ClassVar-discriminated entity type, canonical-JSON
hashing — none of it orch_*-specific). The docstring at
`content_addressed_repo.py:1` and `:32-45`, however, scopes the
class to "Phase 4B orch_* semantic artifacts" — the class purpose
is documented as orch_*-only even though the implementation is
substrate-general. A.2 broadens usage to include `assent_record`,
which is not an orch_* artifact and lives in a different
architectural register.

This is a forward archaeology trap: a future reviewer encountering
the docstring after A.2 ships would legitimately ask *"why is
assent_record using this when the docstring says orch_* only?"* The
docstring/implementation scope mismatch produces a future
writing-room cycle that would not need to happen if A.2 addresses
it proactively.

Plan must decide whether to (i) broaden the docstring to acknowledge
non-orch_* usage, (ii) preserve the docstring and add a one-line
note at the assent_record subclass site explaining the broader
inheritance, or (iii) leave the docstring unchanged and accept the
future archaeology cycle as priced-in cost. Writing-room lean (not
binding on plan): (i) — broaden the docstring, since the
implementation already supports broader usage and the cost is one
sentence.

**FC-A2.3. Graph-intent-id wire shape.** content-hash is sha256 hex
(64 chars). The wire shape on the SSE preview event + the CLI
positional argument needs a decision: full 64-char hash, prefix
(12 chars matching CAR's `name` field convention at line 94), or
typed wrapper (`graph_intent_id` as a distinct string type).

**Discuss-stage directional lean (per DT C6):** 12-character prefix.
Rationale: matches the convention `ContentAddressedRepo` already
uses for its `name` field (`f"{entity_type}:{content_hash[:12]}"` at
`content_addressed_repo.py:94`); coherent with shipped pattern;
addresses paste-friction per
`[[feedback-paste-friction-line-length]]` without the typing
overhead of a wrapper. Collision risk on 12 hex chars (48 bits) is
negligible for A.2's substrate density. Plan locks the final shape
including any collision-handling fallback to longer prefix; discuss
expresses preference.

Operator dogfood UAT will fail if the CLI arg is "ratify the long
hash" — the 12-char lean addresses this proactively.

**FC-A2.4. Deferred-raise pattern for apply-time assent check
(24.4 lineage).** A.2's assent check fires AT the commit-node step
inside `run_chain_steps` (FC-5 from A.1 carries forward). The pattern
established at Phase 24.4 D-07 — deferred raise of an internal
exception caught at the handler boundary, emit a distinct SSE taxon —
is the precedent. Plan should anchor the apply-failure taxa
(`assent_invalid`, drift-related variants) on this pattern.

**FC-A2.5. Chat-handler regime-3 branch threading.** A.1 D3 shipped
the four-regime `CompileBranchOutcome` enum and routed
`compiled_mutating_preview` to preview emission. A.2 threads the
graph-intent-id through the preview surface AND into the next-turn
apply path. Plan must specify:
- where in the regime-3 branch the graph-intent-id is allocated
  (probably in `_chat_compile.py` after compile_intent returns,
  before preview-event emission)
- how the apply-path lookup happens (chat handler check for
  graph-intent-id reference in next-turn prompt? operator-CLI
  out-of-band? both?)

The framing's end-to-end flow diagram covers the steady state; the
plan needs to specify the regime-3 branch modification under the
sync-apply common-case assumption — operator assents via CLI, then
next chat turn checks for pending assent records and applies.

**Cross-surface chat↔CLI transition is deliberate** (per Creative
C10). The dual-surface flow — preview emitted on the chat surface,
ratification recorded on the CLI surface, apply triggered on the
chat surface (or out-of-band) — is intentional per Q5's
operator-surface ruling: A.2 ships CLI as the operator surface;
Console comes later; a conversational affordance (if ever shipped)
is thin verbatim transport per the constitutional line. The
cross-surface transition is the architecturally-correct shape under
that ruling, not an oversight that a future phase should
"consolidate." Future consolidation, if desired, is a separate
architectural motion with its own framing — not a regret to be
addressed post-hoc.

**FC-A2.6. `fbridge ratify` exit-code envelope.** Locked exit-code
pattern (0=ok / 1=failure / 2=unreachable) per the existing CLI
contract. Discuss carve-out for the exact error envelope shape
(plan locks) —
unknown graph-intent-id, already-ratified (idempotent), already-applied
(terminal-state), assent-record write failure, daemon-unreachable.

**FC-A2.7. Audit-event story for `assent_record`.** The shipped
`StagedOpRepo` composes `EventRepo` on the shared session for atomic
audit-event emission. A.2's `AssentRecordRepo` likely wants symmetric
audit-event emission (`assent.proposed`? `assent.recorded`?
`assent.applied`? — name TBD by plan). Different event types than
`staged.*` to honor R-A2.0(a) parallel-substrate semantics; same
atomicity discipline (shared session, no separate commit) for the
same load-bearing reason (tamper-evident audit gaps closed by
atomicity).

**FC-A2.8. The K=2 termination semantics from 24.4 are preserved
unchanged.** A.2 modifies regime 3 (preview emission + apply flow);
the K=2 canonical-recurrence termination trigger lives in
`complete_with_tools` (Phase 24.4 D-07 site at router.py:639-662),
which is the legacy-agentic substrate primitive A.1 left in place
for non-chat callers. A.2 doesn't touch that surface. Coexistence
architecture preserved per inherited binding.

---

## Discuss carve-outs — plan locks (Stage 1b verifies)

Authority structure: **discuss identifies; plan locks; Stage 1b
verifies the plan locked them.** The items below are discuss-stage
identifications carried forward as plan-side ruling obligations.
Stage 1b's role is verification of plan completeness, not
re-decision of the items.

1. **R-A2.0 ↔ R-A2.6 boundary** — the entity_type lookup pattern
   that distinguishes `assent_record` UUIDs from `staged_operation`
   UUIDs when an operator passes the wrong one to `fbridge ratify`
   or `forge_approve_staged`. Locked behavior: structured error
   envelope naming the mismatch.
2. **R-A2.1 graph-intent-id wire shape** — full 64-char sha256 hex,
   12-char prefix, or typed wrapper. FC-A2.3 surfaces the UX
   trade-off; plan must pick.
3. **R-A2.2 AssentRecord core dataclass shape** — sibling to
   `StagedOperation` at `forge_bridge/core/`. Required keys:
   graph_intent_id (content-hash), chain_steps (`list[str]`),
   decided_by, decided_at, applied_at (None until apply). Optional:
   any audit metadata.
4. **R-A2.4 apply-failure taxa enumeration** — `assent_invalid` is
   the named one; drift-related variants TBD. Sweep-completeness
   per `[[feedback-grep-c-completion-invariant]]`.
5. **R-A2.5 CommitVerification field additions** — `assent_valid:
   bool`, `assent_record: AssentRecord | None`. Plan must specify
   how `verify(...)` constructs CommitVerification under both
   drift-only and drift+assent paths (no None-vs-False ambiguity on
   the assent fields).
6. **R-A2.6 ratify exit-code envelope** — error shapes for unknown
   graph-intent-id, already-ratified, already-applied, write failure,
   daemon unreachable.
7. **R-A2.7 storage payload for store-and-replay** — exact JSONB
   shape of `assent_record.body` carrying chain_steps. Coordinates
   with FC-A2.5 (regime-3 threading) on which subsystem populates
   the body and where.
8. **FC-A2.5 regime-3 branch modification** — the exact chat-handler
   diff for graph-intent-id allocation, preview-emission threading,
   and next-turn apply-path lookup. Likely the largest implementation
   surface in A.2.
9. **FC-A2.7 `AssentRecordRepo` audit-event names** — `assent.*`
   event-type strings; matches the `staged.*` analog without
   semantic blur per R-A2.0(a).
10. **Migration ordering and downgrade path** — Alembic migration
    extending `ck_entities_type` to include `'assent_record'`.
    Sibling to `0003_staged_operation.py`. Plan must specify
    revision number against current head.

---

## What A.2's plan derives from this

When operator ratifies the nine rulings (R-A2.0..R-A2.8) and the eight
forward-looking caveats (FC-A2.1..FC-A2.8, with FC-A2.2a subordinate
under FC-A2.2), A.2-PLAN.md opens against:

- New `forge_bridge/core/assent.py` — `AssentRecord` dataclass (sibling
  to `StagedOperation`)
- New `forge_bridge/store/assent_record_repo.py` —
  `AssentRecordRepo(ContentAddressedRepo)` subclass with audit-event
  emission analog
- New Alembic migration — extends `ck_entities_type` CHECK to include
  `'assent_record'` (analog to migration 0003)
- Extension of `forge_bridge/graph/commit.py` — `CommitNode.verify`
  signature gains optional `assent` kwarg; `CommitVerification`
  dataclass gains `assent_valid` + `assent_record` fields
- Extension of `forge_bridge/console/_engine.py:run_chain_steps` —
  passes assent record to `CommitNode.verify` at the commit-node step
- Modification of `forge_bridge/console/_chat_compile.py` regime-3
  branch — allocates graph-intent-id; threads into preview event;
  persists `AssentRecord` (state=proposed, no decision yet)
- Modification of chat-handler — next-turn apply path that looks up
  pending assent records by graph-intent-id reference
- New `fbridge ratify` CLI subcommand at `forge_bridge/cli/main.py` —
  top-level subcommand; writes assent via `AssentRecordRepo`
- New chat-side SSE terminal taxon `event: apply_complete`
- New `assent.*` audit-event types emitted by `AssentRecordRepo`

A.2's plan opens against these contracts. Stage 1b reviews against
them. Implementation hands off in D1..Dn ordered against the v3-ish
form of the plan (A.1 shipped D1..D8; A.2 surface count similar
order).

---

## Status

**Phase discuss v3 — DT sign-off territory, pending operator
ratification.** Drafted 2026-05-28 against:
- A.2-FRAMING.md v3.1 at `072948f`
- Thread A framing (THREAD-A-FRAMING.md)
- A.1 close cursor (A.1-CLOSE.md) + A.1-DISCUSS-QUESTIONS.md format
  precedent
- This-session grounding reads enumerated in §"Grounding refresh"

v1 → v2 absorbed one cross-voice cycle (DT + Creative; operator
converged the disposition). 3 framing-grade catches (C1 audit-event
demote, C3 law-vs-kwarg-type distinction, C8 preference-language for
R-A2.0) + 7 polish-grade catches (C2 heading authority, C4 cycle-count
removal, C5 CAR docstring scope, C6 12-char prefix lean, C7 two-lifetimes,
C9 graph-intent vs ratification-event identity, C10 deliberate
dual-surface). All 10 absorbed in v2.

v2 → v3 absorbed a second micro-cycle: N1 (DT framing-grade, Creative
concurring) — C7 v2 absorption landed adjacent to the concern;
runtime-object-vs-substrate-snapshot reconciliation added explicitly
in R-A2.1+R-A2.2. N2 (DT archaeology-grade) — FC count drift swept
(eight top-level FCs with FC-A2.2a subordinate). No ruling reversals;
no cascade disputes; no new architectural questions surfaced.

**Cycle-size diagnostic** (per DT C4 — replaces cycle-count
prediction): compare catch SIZE to framing. Structural catches at a
cycle boundary signal unresolved architecture; surgical catches
signal convergence. v1 → v2 catches were calibration + category
discipline + cascade honesty + future-pressure visibility — surgical,
not structural. v2 → v3 catches shifted further toward archaeology
consistency (N2 was pure count drift; N1 was framing/discuss-boundary
reconciliation). Per Creative close-frame at v3: the catch profile has
shifted almost entirely from architecture discovery to archaeology
consistency — usually the signal that the room has extracted most of
the architectural value available from the discuss artifact. Room
energy post-v3 is reserved for plan stage.

**Layering discipline observation** (Creative at v3): the document
now exhibits clean layer boundaries — framing owns laws + assumptions
+ question space; discuss owns rulings + rationale; FC sections own
future pressure + plan obligations; discuss carve-outs own plan-lock
requirements; Stage 1b owns verification. Late-stage writing-room
churn usually comes from layer leakage rather than wrong decisions;
v3's clean boundaries reduce that risk for downstream artifacts.

**Motion:** v3 holds for operator ratification. Once ratified,
A.2-PLAN.md drafts in code-handoff format against R-A2.0..R-A2.8 +
FC-A2.1..FC-A2.8 + the discuss carve-outs (plan locks; Stage 1b
verifies), then goes to Stage 1b review before implementation handoff.
