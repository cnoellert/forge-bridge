# A.5.3.2 Gate 2 — Framing (seed corpus drive surface)

**Status:** Gate 2 opens at `9168df7` (origin/main, Gate 1 closed).
This framing establishes the architectural posture for the seed
corpus drive surface and locks the binding decisions reached
during the Gate 1 → Gate 2 convergence pass. It precedes spec
drafting for PR 7, PR 8, and PR 9.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants (six interlocking pairs).
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs,
  the visual-asymmetry pattern (§5.1), helper signature (§5.2),
  three architecturally-prohibited patterns (§5.3).
- `A.5.3.2-PR3-SPEC.md` — persistence layer (builder, writer,
  reader); the helper signature `emit_divergence_capture(...)`.
- `A.5.3.2-PR4-FRAMING.md` (`2281baf`) + `A.5.3.2-PR4-SPEC.md`
  (`b84a8c8`) + `A.5.3.2-PR4-CLOSE.md` (`fab26cb`) — chat-handler
  integration; carriers #1–#7.
- `A.5.3.2-PR5-FRAMING.md` (`2ae187a`) + `A.5.3.2-PR5-SPEC.md`
  (`42336c3`) + `A.5.3.2-PR5-CLOSE.md` (`b8f522e`) — chain-step
  integration; carriers #8–#11.
- `A.5.3.2-PR6-FRAMING.md` (`2142ab6`) + `A.5.3.2-PR6-SPEC.md`
  (`630e646`) + `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Layer 3
  visual-asymmetry executable lint; carriers #12–#13.
- **Gate 1 → Gate 2 convergence pass (this session):** Q1, Q1.5,
  Q1.6, Q1.7 locked through writer's-room iteration. The pass
  produced carrier #14 + the binding framing clarification on
  arbitration-state input ownership (§6).

---

## 2. Gate 2 objective

Gate 2 ships the **seed corpus drive surface** — fixture-based
deterministic execution that drives the live arbitration pipeline
through the existing chat-handler and chain-step call sites,
captures observational records via the unchanged emission helper
(with dispatch-provenance resolution at the persistence layer),
and persists authored expectation records via a distinct
epistemic surface.

The architectural commitment is truth partitioning, not record
duplication:

| Authority surface | Helper | Truth claim | Record kind |
|---|---|---|---|
| Observational | `emit_divergence_capture(...)` | "I observed finalized arbitration." | runtime observation (`source ∈ {"runtime", "seed"}` after contextvar resolution) |
| Authored expectation | `emit_seed_expectation(...)` | "the fixture declared this should happen." | seed expectation (single epistemic class; no `source` field) |
| Interpretive | Gate 4 comparator | "this is how the two diverged." | comparison artifact (Gate 4 deliverable) |

Three truth classes. Three authority surfaces. Three record
kinds. Each helper's authority claim remains singular; no helper
speaks on behalf of more than one truth.

In property-preservation language: Gate 2 preserves every
invariant Gate 1 crystallized. It does so by recognizing that the
seed surface is a *driver*, not an *emitter* — the seed knows
what its inputs are; runtime call sites continue to observe
finalized arbitration; the comparator interprets the difference
later. Each layer keeps its existing meaning.

---

## 3. Architectural inheritance from Gate 1

### 3.1 14 carrier sentences (verbatim)

Eleven carriers inherited from PR 4 + PR 5 + two added by PR 6
travel into Gate 2 unchanged. Gate 2 adds carrier #14 (§6.1).
Total: 14 carriers under Gate 2 governance.

Carriers travel verbatim into:
- module docstrings of any Gate 2 production module.
- top-level docstrings of any Gate 2 test module.
- commit message bodies under "preserved invariants."

The repetition is the property crystallizing. (SEED §2.3.)

### 3.2 Three-layer structural-test discipline

| Layer | Test | Drift class caught |
|---|---|---|
| 1 | `test_pr3_discipline.py::_ALLOWLIST` | Topology drift — *which files may import `forge_bridge.corpus`?* |
| 2 | `test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS` | Symbol / import drift — *within those files, which corpus symbols may be imported?* |
| 3 | `test_pr6_visual_asymmetry.py` | Semantic-shape drift — *at those import sites, how must the imported emission path be invoked?* |

Gate 2 extends Layers 1 and 2 mechanically. Gate 2 does NOT
extend or modify Layer 3. (See §7 for the non-acquisition
commitments and §8 for the extension deltas.)

### 3.3 Four architectural invariants

The four invariants that crystallized through PR 2 and have
governed Gate 1 throughout:

- **descriptive-not-evaluative** — records describe what was
  observed; they do not score, judge, or rank.
- **observational-not-semantic** — records capture observations
  at a boundary; they do not encode meaning derived from
  interpretation.
- **no-lazy-side-effects** — observation occurs at named
  boundaries through explicit call paths; no side effects derived
  from inspectable side state.
- **loud-asymmetry** — the visual asymmetry between arbitration
  and observation is load-bearing; refactors that preserve
  semantics while collapsing visual structure are rejected.

Gate 2 must preserve all four. The expectation surface
(`emit_seed_expectation`) is itself authored declaration — that
is its truth class — and the framing must articulate how its
authority claim composes with the four invariants without
violating them. (See §4.4.)

### 3.4 Gate separation — call-site shape vs. persisted-record ontology

Gate 1 / PR 6 owns **call-site declared shape** (epistemic class
at the observation boundary). Gate 2 / Gate 4 own
**persisted-record ontology** (resolved provenance class after
contextual annotation, ontology of record kinds, comparator
semantics).

This separation is load-bearing:

- The Layer 3 lint stays *structural*. It validates declared
  shape at the call site; it does not validate persisted record
  semantics.
- The persistence layer stays *semantic*. It validates record
  schema and provenance class governance; it does not enforce
  call-site shape.
- The contextvar dispatch path inside `emit_divergence_capture`
  is the *only* surface where call-site declaration becomes
  resolved record provenance. Neither lint nor schema sees the
  rewrite as a structural concern.

This separation is the load-bearing claim carrier #14 protects
against drift in either direction (§6.1).

---

## 4. Architectural delta — what Gate 2 introduces

### 4.1 Model A — seed fixtures drive live arbitration

The seed surface drives the *real* chat-handler / chain-step
arbitration pipeline. Real narrowing occurs. Runtime call sites
remain authoritative observers of finalized arbitration state.
Seed code contributes declared expectation metadata via a
distinct surface but does not author observation records.

**Why Model A and not synthetic-record authoring (Model B):**

Synthetic-record authoring would mean seed code constructs
observation records directly. That collapses two truth classes
into one helper:

- "I observed arbitration" (the runtime claim)
- "I authored a deterministic expectation artifact" (the seed
  claim)

The collapse smears observational authority with authored
semantic declaration — exactly the asymmetry Gate 1 spent six
PRs protecting. Fields like `collapse_occurred`,
`candidate_set_post_reachability`, `narrower_latency_ms` would no
longer represent real observations under Model B; they'd be
fabricated to satisfy the schema.

Model A keeps observation grounded in real arbitration behavior
and keeps Gate 4's comparator cleanly partitioned: declared
expectation versus observed runtime result, joined later on
fixture identity.

### 4.2 Three authority surfaces, three record kinds, three helpers

The three surfaces are introduced in §2 (objective table). The
practical consequence: each helper has a singular signature with
a singular truth claim. Helpers do not grow optional kwargs that
shift their authority claim depending on which kwargs are
populated. The expectation helper stands apart from the
observation helper because it makes a different truth claim, not
because its arguments differ.

### 4.3 contextvars-scoped dispatch provenance

The mechanism for resolving `source ∈ {"runtime", "seed"}` at the
persistence layer is a `contextvars.ContextVar` whose scope is
managed by a context-scope helper colocated with
`emit_divergence_capture`. The seed driver enters the scope
before dispatching fixtures through the arbitration pipeline; the
helper consults the contextvar at emission time and resolves the
`source` field on the persisted record.

**Why contextvars and not env vars or explicit threading:**

- Env vars are process-global; they fail when in-process fixtures
  share a runtime (e.g., a test harness running multiple
  fixtures sequentially without subprocess isolation).
- Explicit parameter threading would require modifying chat
  handler / chain step signatures, propagating a seed-context
  marker through every layer. That's invasive and conflicts with
  §3.1's principle that arbitration-state fields remain
  call-site-owned explicit inputs (§6.2).
- `contextvars` provides explicit scope boundaries (`with` /
  `set`/`reset`) and survives `asyncio` task transitions
  natively. The scope is named, greppable, and bounded.

The contextvar resolution path inside `emit_divergence_capture`
is the *only* surface where the rewrite happens. Call-site
declaration remains literal `source="runtime"`; the helper
internally consults the contextvar; the persisted record carries
the resolved value. This preserves Property C (the lint sees the
declared literal, never the resolved value) and the four
invariants (no-lazy-side-effects holds because the contextvar
scope is explicit and named).

### 4.4 Companion records — truth partitioning, not duplication

Authored expectation records are emitted via
`emit_seed_expectation(...)` and persist alongside runtime
observation records. The two record kinds are distinguished by a
`record_kind` discriminator at the persistence layer. Gate 4's
comparator joins on `fixture_id`.

The split is **not duplication**. The same fixture run produces:

- one observation record (runtime, with `source="seed"` after
  contextvar resolution and `fixture_id` populated as augmenting
  provenance)
- one expectation record (seed, with `fixture_id` and authored
  expectation metadata — `expected_narrow`, prompt label, etc.)

Each record carries information the other cannot:
- observation knows what *actually* happened (real narrowing,
  real latency, real candidate set).
- expectation knows what the fixture *declared* should happen
  (the deterministic input the seed authored).

The four invariants govern observation as before. Expectation
records are authored — they do not claim observational truth and
do not need to. Expectation records are authored *before*
execution and therefore cannot derive authority from runtime
observation; the temporal asymmetry is itself part of the truth-
partitioning. The observational-not-semantic invariant applies
to the observation surface; the expectation surface is
explicitly an authored-declaration surface, and its truth claim
is consistent with that.

---

## 5. Binding decisions

### 5.1 Q1 — Model A locked

Seed code is a driver, not an emitter. Runtime call sites at
`forge_bridge/console/handlers.py:1185` and
`forge_bridge/console/_step.py:233` remain the singular
observation authority. `emit_divergence_capture(source="seed")`
is epistemically honest because the helper still means what it
meant under Gate 1: "I observed finalized arbitration." The
pipeline really runs; the narrow really happens.

**What this rejects:** synthetic record authoring (Model B),
γ-path builder/writer bypass, any architecture that asks the
runtime helper to speak on behalf of authored declaration.

### 5.2 Q1.5 — contextvars-scoped dispatch context locked

Source resolution from `"runtime"` (declared) to `"seed"`
(resolved) occurs via a `contextvars.ContextVar` scope managed by
the seed driver. Property A's `divergence_capture_enabled()`
guard remains the single env-gated boundary. The seed driver
forces the gate on for its own runs (or sets the equivalent
contextvar) at the dispatch boundary.

**What this rejects:** process-global env-var-only resolution,
explicit parameter threading through chat handler / chain step
signatures, lazy state inspection from arbitrary side state.

### 5.3 Q1.6 — companion records + dedicated expectation helper locked

Expectation records are authored declarations, not observed
arbitration events. They MUST NOT travel through
`emit_divergence_capture(...)`. A distinct helper —
`emit_seed_expectation(...)` — owns the authored-expectation
authority surface. The observation helper's authority claim
remains singular and unchanged.

This is **not** γ-path builder/writer bypass. The expectation
helper has its own signature, its own authority claim, and its
own structural shape — it is not a low-level builder/writer
exposed to the seed driver. It is a peer authority surface to
the observation helper, distinguished by truth class.

**`emit_seed_expectation` owns authored expectation semantics,
not persistence topology.** The helper expresses the authored-
declaration truth claim; persistence is delegated to a narrow
persistence-surface (§8.2) that the seed driver also imports.
Future contributors must not read the helper as the expectation
persistence layer — that authority belongs to the dedicated
persistence helper, not to the expectation surface.

**What this rejects:** inline augmentation of the observation
helper with seed-knowable kwargs (helper-singularity smearing),
direct builder/writer access from seed code (γ-path), conflation
of observation and expectation under any single signature, and
conflation of authored expectation semantics with persistence
topology under the expectation helper.

### 5.4 Q1.7 — Property C unchanged; KNOWN_SOURCE_VALUES at persistence layer

The Layer 3 lint validates **declared shape at the call site**.
It never observes the contextvar-resolved effective source value.
Property C remains unchanged: it asserts literal
`source="runtime"` at every discovered call site.

`KNOWN_SOURCE_VALUES` lives at the **persistence/record-schema
layer**, not in the lint module. It governs persisted provenance
classes after contextual annotation has been resolved. Its
consumers are: the contextvar resolution path inside
`emit_divergence_capture` (validates the override target),
reader validation (validates persisted records at read time),
and Gate 4's comparator (partitions by source). Gate 2 ships the
constant; Gate 4 inherits the dependency.

**What this rejects:** modifying `test_pr6_visual_asymmetry.py`
to broaden Property C, embedding `KNOWN_SOURCE_VALUES` in the
lint module, conflating call-site shape governance with
record-ontology governance.

### 5.5 Module siting — `forge_bridge/corpus/_seed.py`

Seed driver and `emit_seed_expectation` live in a single module
sibling to `_capture.py`. Not a subpackage (`corpus/seed/`); not
a peer package (`forge_bridge/seed/`).

Rationale: Layer 1's locality property depends on the corpus
package boundary. A peer package would force `_ALLOWLIST` to span
beyond corpus and weaken the local-shape claim. A subpackage
signals more breadth than v1's surface area justifies — one
driver + one helper. Promote to subpackage if seed surfaces
multiply later.

### 5.6 KNOWN_SOURCE_VALUES siting — `forge_bridge/corpus/_sources.py`

Dedicated module with a single export and a protected-property
docstring at the constant's definition site. The truth — "new
source classes require explicit framing-level review plus
maintenance-surface update" — is documented adjacent to the
mechanism (the `frozenset` contents) but distinct from it.

Rationale: this constant has the same maintenance-surface
character as `NARROWING_FUNCTION_NAMES` (PR 6 §1.3). Operators
and reviewers need a named locus to grep against. Embedding in
`_capture.py` next to contextvar resolution buries the
governance role next to implementation noise. A dedicated module
makes the truth-vs-mechanism distinction architecturally
visible.

### 5.7 PR partitioning — three PRs (cadence-matches-work-depth)

| PR | Scope | Review depth |
|---|---|---|
| **PR 7** — schema + contextvar resolution | `_sources.py` + `KNOWN_SOURCE_VALUES`, `record_kind` discriminator, reader validation extension, contextvar resolution path inside `emit_divergence_capture` | Plumbing — light-touch |
| **PR 8** — seed driver + expectation helper | `_seed.py` with the driver + `emit_seed_expectation`; Layer 1 + Layer 2 extensions with tightly scoped permitted-symbols entries | Boundary — full three-round (new authority surface) |
| **PR 9** — first fixtures + end-to-end integration | First seed fixtures; integration tests demonstrating two authority surfaces composing under real seeded execution | Integration — full review pass |

Rationale: cadence-matches-work-depth (Gate 1 lesson; PR 6 close
§2.5). PR 7 is plumbing — schema additions and resolution
plumbing. PR 8 is boundary work — establishing the new authority
surface. PR 9 is integration — demonstrating composition. Each
is its own atomic landing; bundling smears the review shape.

---

## 6. Carrier delta

### 6.1 Carrier #14 — declared epistemic class vs. persisted provenance

> **Property C governs the epistemic class declared at the
> observation boundary. KNOWN_SOURCE_VALUES governs persisted
> provenance classes after contextual annotation has been
> resolved.**

Carrier #14 prevents two specific drift modes that the Gate 1 →
Gate 2 convergence pass surfaced:

1. **Upward collapse:** record-ontology governance creeping into
   the structural lint (the original Q1.7 lean, corrected
   in-flight).
2. **Downward collapse:** contextual provenance leaking into
   arbitration truth, weakening carrier #3's
   explicit-input doctrine via provenance rewriting.

The carrier's structural form — two clauses connected by the
declared-vs-resolved axis — is itself the protection. Either
clause without the other admits one of the two drifts.

### 6.2 Binding framing clarification — call-site-owned arbitration inputs

> **Arbitration-state fields remain call-site-owned explicit
> inputs. Dispatch provenance is contextual metadata derived at
> emission time and does not participate in arbitration
> semantics.**

This clarification travels alongside carrier #14 as binding
governance. It distinguishes:

- **arbitration-state fields** (candidate set, narrowed set,
  collapse occurrence, latency, etc.) — owned by the call site,
  passed as explicit positional/keyword arguments per the
  helper signature, validated by the helper, surfaced by the
  Layer 3 lint as Property C+D structural shape.
- **dispatch provenance** (source, fixture_id when applicable) —
  derived at emission time from the contextvar scope, not
  passed by the call site, never participates in arbitration
  semantics.

The clarification is binding (it governs PR 7's contextvar
resolution path implementation) but is not numbered as a carrier
because it is structurally a *qualification* of carrier #3
(explicit input doctrine) rather than an independent property.

---

## 7. Non-acquisition commitments

Gate 2 explicitly does **not**:

1. **Touch the Layer 3 lint.** `test_pr6_visual_asymmetry.py`
   ships into Gate 2 with zero modifications. Property C remains
   `source="runtime"` literal. Gate 2's record-ontology work
   cannot regress Property C because Property C operates at a
   layer Gate 2 doesn't touch.

2. **Bypass live arbitration.** γ-path (seed code constructing
   records via low-level builder/writer) is rejected. All
   observation records are produced by the live arbitration
   pipeline through the existing call sites.

3. **Author expectation through the observation helper.** Inline
   augmentation of `emit_divergence_capture` with seed-knowable
   kwargs (`fixture_id`, `expected`, etc.) is rejected. The
   observation helper's authority surface remains singular.

4. **Extend Layer 3 lint coverage to expectation emission.**
   `emit_seed_expectation(...)` is structurally distinct from
   the arbitration-boundary shape and does not inherit Properties
   A–D. Expectation emission may have its own future structural
   tests, but Gate 2 ships none — the surface is small enough
   that human review carries it. (Promote to a Layer-3-equivalent
   if expectation emission proliferates in later milestones.)

5. **Modify `divergence_capture_enabled()` or its env-gate.** The
   single boundary remains the Gate 1 boundary. The seed driver
   manages the env / context scope at dispatch; it does not
   redefine the gate.

6. **Collapse contextual provenance downward into arbitration
   semantics.** Source resolution is metadata at the persistence
   layer, never an arbitration input. (Carrier #14 + §6.2.)

---

## 8. Layer 1 / Layer 2 / Layer 3 extension delta

### 8.1 Layer 1 — `_ALLOWLIST` mechanical extension

`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extends with:

- `forge_bridge/corpus/_seed.py` — the seed driver and
  expectation helper module.
- `forge_bridge/corpus/_sources.py` — the KNOWN_SOURCE_VALUES
  governance module.

(Both are inside `forge_bridge/corpus/`, so the locality property
holds. The allowlist semantics are unchanged: only files inside
the corpus package + the explicit allowlist may import from
`forge_bridge.corpus`.)

### 8.2 Layer 2 — `_PERMITTED_CORPUS_IMPORTS` narrowly scoped extension

`tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
extends with one entry:

```python
"forge_bridge.corpus._seed": frozenset({
    "<dispatch-scope-helper>",         # finalized in PR 7 spec
    "<narrow-persistence-surface>",    # finalized in PR 7 spec
}),
```

`_seed.py` may import only the dispatch-scope helper and the
narrow persistence-surface required to persist authored
expectation records. Direct builder/writer orchestration remains
prohibited outside dedicated persistence helpers.

`_seed.py` is **not** permitted to import:
- `emit_divergence_capture` (the observation helper — wrong
  authority surface).
- low-level builder/writer surfaces (`_record_writer`, builder
  primitives, JSONL writers, etc.) — persistence topology is
  owned by dedicated persistence helpers, not by the seed
  driver.
- any read / analysis surfaces.

This preserves the participation-creep posture: the seed driver
participates in dispatch-context management and authored
declaration only, never in observational authoring or in
persistence-topology orchestration.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged. The lint's
discovery walk (`_find_emit_call_sites`) finds calls to
`emit_divergence_capture` only. `emit_seed_expectation` calls are
not discovered by the existing lint and inherit no Property A–D
validation. This is by design: expectation emission is a distinct
truth class with a distinct structural shape.

If `emit_seed_expectation` call sites proliferate beyond the
small surface area Gate 2 anticipates, a future milestone may
introduce an analogous Layer-3-equivalent for the expectation
surface. Gate 2 does not.

---

## 9. Schema / persistence delta

### 9.1 KNOWN_SOURCE_VALUES — governance contract

```python
# forge_bridge/corpus/_sources.py

# PROTECTED PROPERTY (truth):
# Persisted provenance classes are governed. Adding a new source
# class requires explicit framing-level review plus synchronous
# update of: this constant, reader validation, the contextvar
# resolution path inside emit_divergence_capture, and the Gate 4
# comparator's partition logic. Mergeability is contingent on all
# four updating in lockstep.
#
# MECHANISM:
KNOWN_SOURCE_VALUES: frozenset[str] = frozenset({"runtime", "seed"})
```

The mergeability contract for source-enum additions is a four-way
synchronous update. Reviewers reading any source-enum-touching
PR must verify all four loci update together.

### 9.2 record_kind discriminator

The persistence layer gains a `record_kind` field distinguishing
observation records from expectation records:

```python
record_kind: Literal["observation", "expectation"]
```

`record_kind` is governed **structurally** rather than
operationally: new values imply a new authority surface, not
merely a new provenance class. Adding a third `record_kind`
requires the corresponding helper, signature, and truth claim —
all framing-level decisions that pass through the same review
discipline that produced the observation and expectation
surfaces. Provenance classes can multiply within an existing
authority surface (`KNOWN_SOURCE_VALUES` admits new values via
its mergeability contract); record kinds cannot.

### 9.3 Reader validation extension

PR 3's reader gains validation logic:

- `record_kind` must be a known value.
- For `record_kind == "observation"`, `source` must be a member
  of `KNOWN_SOURCE_VALUES`.
- For `record_kind == "expectation"`, no `source` field is
  expected (expectation records are single-class).

Records failing validation are rejected at read time. (Whether
they're quarantined, logged, or hard-failed is a Gate 4
comparator-policy question deferred to that gate.)

### 9.4 Gate 4 comparator dependency

Gate 4's comparator inherits a hard dependency on
`KNOWN_SOURCE_VALUES` for partition logic and on `record_kind`
for record-kind filtering. The mergeability contract above
ensures the comparator never sees an unknown source value or
record kind.

---

## 10. PR sequencing within Gate 2

Three PRs, sequenced linearly. Each closes with a CLOSE artifact
following the Gate 1 cadence. Each opens with a FRAMING + SPEC
pair following the Gate 1 cadence.

### PR 7 — schema + contextvar resolution

**Deliverables:**
- `forge_bridge/corpus/_sources.py` — `KNOWN_SOURCE_VALUES`
  constant + governance docstring.
- `forge_bridge/corpus/_capture.py` — contextvar definition,
  scope-helper, resolution logic inside
  `emit_divergence_capture`.
- Persistence-layer `record_kind` discriminator + reader
  validation extension.
- Layer 1 allowlist update (mechanical).

**Tests:**
- Reader validation against `KNOWN_SOURCE_VALUES`.
- Contextvar resolution path: declared `source="runtime"` +
  scope active → persisted `source="seed"`; declared
  `source="runtime"` + scope inactive → persisted
  `source="runtime"`.
- `record_kind` discriminator round-trip.

**Property C remains unchanged.** Verified by running
`test_pr6_visual_asymmetry.py` unchanged against the modified
`_capture.py`; Property C's literal check passes because call
sites are unchanged.

**Cadence:** plumbing-shaped; light-touch review.

### PR 8 — seed driver + expectation helper

**Deliverables:**
- `forge_bridge/corpus/_seed.py` — seed driver +
  `emit_seed_expectation(...)` helper.
- Layer 1 + Layer 2 extensions per §8.1 + §8.2.
- Public-API addition (decision deferred to PR 8 spec):
  whether `emit_seed_expectation` and the dispatch-scope helper
  belong in `forge_bridge.__all__` or remain corpus-internal.

**Tests:**
- Expectation helper signature + persistence validation.
- Layer 1 extension test passes (new files in allowlist).
- Layer 2 extension test passes (seed driver imports only
  permitted symbols).
- Layer 3 lint passes (no new emit_divergence_capture call sites
  added).

**Cadence:** boundary work; full three-round review (this is
where the new authority surface lands; PR 4 + PR 5 cadence
applies).

### PR 9 — first fixtures + end-to-end integration

**Deliverables:**
- A small, deliberate set of seed fixtures (count + scope
  finalized in PR 9 spec; design intent: minimum that exercises
  observation + expectation distinguishability and provenance
  partitioning end-to-end).
- Integration tests driving fixtures through real arbitration
  with capture enabled.

**Tests:**
- End-to-end: fixture → driver → live arbitration → observation
  record (`source="seed"`) + expectation record persisted →
  reader validates both.
- Two authority surfaces composing without smearing.
  Interpretive authority is Gate 4's deliverable; Gate 2 does
  not exercise it. **Gate 2 ships no comparator artifact, stub
  or otherwise.**

**Cadence:** integration; full review pass.

---

## 11. Phase-end conditions / Gate 2 close criteria

Gate 2 closes when:

1. The two Gate-2 authority surfaces (observation + authored
   expectation) are operational under real seeded execution.
   Interpretive authority remains Gate 4's deliverable; Gate 2
   does not exercise it.
2. First fixtures run end-to-end demonstrating observation +
   expectation persistence + reader validation.
3. Gate 4 is unblocked for comparator articulation: the
   `KNOWN_SOURCE_VALUES` + `record_kind` schema is in place
   and the comparator dependency is named. Gate 2 ships no
   comparator artifact, stub or otherwise.
4. Layer 1 + Layer 2 extensions are mechanically verified.
   Layer 3 unchanged + still green against the modified
   `_capture.py`.
5. The 14 carriers travel verbatim into all Gate 2 production
   modules + test docstrings + commit messages.
6. A `A.5.3.2-GATE-2-CLOSE.md` artifact ships at the PR 9 close
   commit, following the PR 6 close artifact's structure
   (predecessors, what Gate 2 established, what Gate 3/4
   inherits, methodology observations, cross-references).

---

## 12. Cross-references

- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Gate 1 close; durable
  archival state Gate 2 inherits; §3.1 names the structural
  difference between runtime and seed call sites; §7 reseed
  protocol governs Gate 2's opening cadence.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (binding for Properties A–D acceptance criteria; preserved
  unchanged into Gate 2).
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature for
  `emit_divergence_capture(...)` (preserved unchanged into
  Gate 2; contextvar resolution path is a new internal
  consumer).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-
  prohibited patterns (binding for Rejections 1, 2, 3; PR 5
  added Rejection 4; preserved unchanged into Gate 2).
- `forge_bridge/console/handlers.py:1185` — chat-handler
  observation call site (PR 4 integration); Gate 2 dispatches
  fixtures through this site without modification.
- `forge_bridge/console/_step.py:233` — chain-step observation
  call site (PR 5 integration); Gate 2 dispatches fixtures
  through this site without modification.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper; Gate 2 PR 7 adds contextvar resolution
  internally; signature unchanged from external view.
- `forge_bridge/corpus/_capture.py` (planned) — dispatch-scope
  helper (exact name finalized in PR 7 spec); colocated with the
  observation helper to keep the contextvar surface local.
- `forge_bridge/corpus/_seed.py` (planned, PR 8) — seed driver +
  `emit_seed_expectation`.
- `forge_bridge/corpus/_sources.py` (planned, PR 7) —
  `KNOWN_SOURCE_VALUES` + governance docstring.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer 1;
  extends in PR 7 + PR 8.
- `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
  — Layer 2; extends in PR 8.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3; ships
  unchanged into Gate 2; verified green after PR 7 lands.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; §2.2 (interlock vs. coexist) +
  §2.3 (substrate maturity → property-preservation discipline)
  governed Gate 2's framing convergence pass.

---

Gate 2 framing locks here. PR 7 framing drafts at the next
session boundary; PR 7 spec derives from that framing; PR 7
implementation derives from that spec per the Gate 1 cadence.
