# A.5.3.2 Gate 2 — Close (cross-PR architectural synthesis)

**Status:** Durable archival state at gate scope. Gate 2 closes
across PR 7 + PR 8 + PR 9. The three-PR arc that opened at
`A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`, 2026-05-08) closes at
this commit. PR 9 close (`A.5.3.2-PR9-CLOSE.md`) ships at the
same commit per Gate 2 framing §11.6 + PR 8 close §7 step 11.

This artifact is **gate-level synthesis** — what took 3 PRs to
build, what it means architecturally, what Gate 3 / Gate 4
should NOT re-litigate. No section duplicates PR-level
archaeology (PR 7 close `b035c87`, PR 8 close `b102010`, PR 9
close `A.5.3.2-PR9-CLOSE.md` carry the per-PR detail).

**Cross-artifact responsibility split (per close convergence):**

- **Gate 2 close (this artifact)** owns:
  - Gate-level synthesis (§1)
  - Gate 3 inheritance contract at gate scope (§2)
  - Complete 4-variant amendment taxonomy with PR-of-origin (§5)
  - Promotion-candidate inventory (§5)
  - Cleanup-pressure-resistance class final inventory at gate scope (§5)
  - The four §7.3 ontological questions handoff (§2)
- **PR-level closes** (PR 7 / PR 8 / PR 9) own per-PR
  archaeology, step-by-step commits, surface contracts.

Future phase architects read **this Gate 2 close** for cross-PR
synthesis. PR-level closes are the per-PR archaeology
references this artifact's §5 + §8 link to.

---

## 1. What Gate 2 established as a whole

The three PRs of Gate 2 (PR 7 + PR 8 + PR 9) establish a
**fourfold architectural deliverable** that no individual PR
captures in isolation. Each PR ships a load-bearing surface;
the gate-level synthesis is the composition of those surfaces
+ the methodology contributions that emerged across the arc.

### 1.1 Three-authority-surface partition made operational

Gate 2 framing §3.4 introduced the three-authority-surface
partition as Gate 2's architectural delta beyond Gate 1:

| Surface | Gate 2 PR | Operational artifact |
|---|---|---|
| **Observation (call-site)** | PR 7 | `emit_divergence_capture` + contextvar resolution path inside `_capture.py` |
| **Dispatch provenance (operational)** | PR 7 | `seed_dispatch_scope` + `_DispatchContext` |
| **Authored expectation (declaration)** | PR 8 | `emit_seed_expectation` + `drive_seed_fixture` + schema validator expectation branch |

PR 7 + PR 8 introduce the three surfaces; **PR 9 consumes the
composition end-to-end** through the real `chat_handler`
arbitration pipeline. The partition is operational at gate
close — each surface has a distinct authority class; each is
mechanically protected against cross-surface authority leakage
(via Layer 2 walkers + member #7/#8/#9 protections); each
composes cleanly under real seeded execution.

**The composition is the deliverable, not the parts.** Any one
of the three surfaces could exist in isolation without the
other two; the architectural commitment Gate 2 makes is that
**all three exist together AND compose**. Gate 3's comparator
work depends on this composition holding.

### 1.2 Seed corpus operational end-to-end

PR 9 ships the **first operational seed corpus** consuming the
three-authority partition:

- Three hand-grounded fixture modules (`fix_single_survivor`,
  `fix_multi_match`, `fix_no_keyword_match`) under
  `tests/corpus/fixtures/`.
- Five integration tests driving the corpus through the REAL
  `chat_handler` arbitration pipeline (PR14 + PR21 + emission).
- Two property tests proving Gate 4 comparator dependencies
  (record_kind partition + fixture_id joinability).
- A controlled reachable-tool set
  (`_PR9_REACHABLE_TOOLS` at module scope) preserving real
  arbitration semantics while removing host-environment
  reachability variance.

**The corpus is data + one orchestration call only** (member
#9 protection; PR 9 framing §6.1). No fixture-management
framework. No registry/factory/generator/parametrization. Each
fixture is named explicitly + consumed explicitly by its
matching integration test.

Gate 4's comparator authoring inherits an **operational seed
corpus** — the comparator does not need to ship its own
fixtures; the PR 9 corpus is the starting reference set.

### 1.3 Four-variant amendment taxonomy canonicalized

Across PR 7 + PR 8 + PR 9, the amendment-at-incarnation cluster
canonicalized **four distinct variants**:

| Variant | Surfaces at | PR of canonical instance | Pattern |
|---|---|---|---|
| **Drafting-time** | Spec authoring | PR 7 + PR 8 spec §4.5 | Discoveries surfaced during spec drafting; registered as NO-code spec amendment commits |
| **Implementation-time** | Step N implementation | PR 8 §1.3 cluster #5-#7 | Discoveries surfaced during a step's implementation; registered as amendment within step commit body |
| **Verification-time** | Step 5 verification | PR 8 Step 4.5 (`9785d69`) | Drift surfaced during verbatim-travel verification; registered as surgical N.5 commit before Step 5 lands |
| **Grounding-time** | Step 2 / Step 3 implementation grounding | PR 9 §4.7 amendment 2026-05-11 (`2c7a2ca`) | Empirical inspection of live code surface reveals framing/spec extrapolation; registered as separate NO-code amendment commit |

Gate 2 close §5 details each variant with full archaeology.
The four-variant taxonomy is **methodology-grade** — future
reliability phases should expect amendments at all four
boundaries and have the cadence available for use.

**Critical structural observation:** Each variant has a
**distinct trigger-time** and a **distinct atomic boundary
discipline**:

- Drafting-time: surfaces at spec authoring; registered as
  spec §4.5 sub-section + NO-code commit.
- Implementation-time: surfaces at step implementation;
  folded into step commit body.
- Verification-time: surfaces at Step 5 verification;
  registered as surgical Step N.5 commit before Step 5 lands.
- Grounding-time: surfaces at Step 2/3 empirical consumption;
  registered as separate NO-code commit per amendment-
  convergence direction.

The discipline — atomic boundary preservation — is **invariant
across variants**. The variants differ in WHEN they surface,
not in HOW they are registered.

### 1.4 Cleanup-pressure-resistance class at 9 members

The architectural class introduced at PR 7 framing §6 reaches
**9 members at Gate 2 close**:

| # | Member | PR of origin |
|---|---|---|
| 1 | Helper duplication | PR 7 |
| 2 | Visual asymmetry / Properties A–D | PR 6 (Gate 1) |
| 3 | Intentionally inert structural parameters | PR 7 |
| 4 | Always-present `fixture_id` field on observation records | PR 7 |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 |
| 7 | Companion records as truth-partitioning | PR 8 |
| 8 | `emit_seed_expectation` as semantics-not-topology | PR 8 |
| 9 | Fixture-surface-data-discipline | PR 9 |

PR 7 contributed 6 members; PR 8 contributed 2; PR 9
contributed 1. The class is **demonstrably populatable across
three reliability phases**. Each member's protection is
documented inline at every operational placement site
(framing language + module docstrings + mechanical
enforcement tests).

**Promotion to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`**
remains gated on a **fourth phase populating the class under
genuinely independent conditions**. The three-phase
corroboration is strong but the fourth phase is the discipline
gate per PR 7 framing §6 original criterion.

§5 carries the full per-member protection summaries and the
promotion-candidate framing.

### 1.5 The 15 inherited carriers traveled verbatim across all Gate 2 surfaces

Gate 2 inherited 14 carriers from Gate 1 + introduced carrier
#14 at gate framing time + introduced carrier #15 at PR 8
framing time. The 15-carrier set + binding framing
clarification travel **verbatim** into every Gate 2 production
module + test docstring + commit message:

- **PR 7 production surfaces:** `_capture.py` (lines 6–135) +
  `_schema.py` + `_sources.py` carry the inherited 14 + carrier
  #14 at the module docstrings.
- **PR 8 production surfaces:** `_seed.py` (lines 19–200)
  carries 15 + binding clarification + 2 PR-8-LOCAL binding
  statements (member #7 + member #8) + PR-INTERNAL three-way
  authority partition prose.
- **PR 9 test surfaces:** Three fixture modules carry 15
  inherited + binding clarification per relevance-by-file
  ordering (carrier #15 at top). Two new test modules carry
  carriers by reference (slim per-test-file pattern; PR 8 spec
  §0 travel sites #4).
- **All Gate 2 commit bodies:** Carriers reproduced verbatim
  in "preserved invariants" sections.

The verbatim travel discipline is **load-bearing for cross-PR
auditability**. A reviewer can land at any Gate 2 surface and
encounter the full inherited governance context without
reading any spec or framing artifact.

PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5 legacy-synthesis)
remain scope-local to `_capture.py` + `reader.py`. PR-8-LOCAL
binding statements (member #7 + member #8) remain scope-local
to `_seed.py` + `emit_seed_expectation`. PR-9-LOCAL is the
fixture-surface-data-discipline contract (operational via
`_FIXTURE_PERMITTED_IMPORTS` + walker). The non-regeneration
rule (PR-N-LOCAL statements do NOT travel to subsequent PRs)
preserves scope-local protections without cross-contamination.

### 1.6 Three-walker Layer 2 partition operational

At Gate 2 close, **three Layer 2 AST walkers** operate against
the codebase. Each protects a distinct ontology:

- **PR 4 walker** — production import topology (one-directional
  flow: corpus not imported by narrowing subsystem).
- **PR 8 walker** — orchestration participation discipline
  (`_seed.py`'s 5-symbol bounded toolbox; semantics-not-
  cardinal).
- **PR 9 walker** — declarative fixture-data discipline
  (fixture modules' single-symbol-gate;
  `_FIXTURE_PERMITTED_IMPORTS` value-locked at 1).

**Shared AST mechanics do not imply shared ontology.** Future
"walker unification" cleanup proposals are rejected at the
spec layer (PR 9 spec §4.6 + §7 + this artifact §5).

The three-walker partition is **architecturally load-bearing**
— each ontology evolves independently; no walker generalizes
without collapsing protections.

### 1.7 PR-INTERNAL three-way authority partition (PR 8 spec §4.1.5.1)

PR 8 introduced a sub-partition within Gate 2's authored-
expectation surface: a PR-INTERNAL three-way authority
partition splitting the authored-expectation surface into:

- **Authored expectation semantics** → `emit_seed_expectation`
  (truth claim authority)
- **Orchestration semantics** → `drive_seed_fixture`
  (invocation contract authority)
- **Persistence topology** → `_persist_expectation_record`
  (PR 7 seam — write authority)

The PR-INTERNAL partition + the Gate 2 §3.4 gate-level
partition compose to a **two-level authority partitioning
discipline** at Gate 2 close. Future cleanup PRs proposing to
collapse either level are rejected at the spec layer (PR 8
spec §7 phase-end conditions table + PR 9 spec §2 + §7).

---

## 2. Gate 3 / Gate 4 inheritance contract

### 2.1 What the comparator needs (Gate 4 dependency)

Gate 4 ships the comparator artifact (per Gate 2 framing §11.3:
*"Gate 2 ships no comparator artifact, stub or otherwise."*).
The comparator depends on **two foundational properties** that
Gate 2 ships **operationally verified**:

1. **Record-kind partition correctness.** The corpus must be
   partitionable by `record_kind` into observation records
   + expectation records as separate authority claims. Member
   #7 (companion records as truth-partitioning) protects this
   property at PR 8; PR 9 Step 4 (test 4) verifies it
   mechanically against persisted records.

2. **Fixture-id joinability.** Each observation record + its
   companion expectation record must share an identical
   `fixture_id` field. The shared field is the comparator's
   join key. PR 9 Step 4 (test 5) verifies the join shape
   mechanically against persisted records by building a
   `dict[fixture_id, dict[record_kind, record]]` structure.

**Gate 4 framing inherits these two properties unblocked.**
The comparator's foundational data structure (`fixture_id`-keyed
join over `record_kind`-partitioned corpus records) is
demonstrated end-to-end at Gate 2 close.

**Gate 4 framing must NOT** revisit the partition or
joinability properties; both are operationally verified at
PR 9 close. Any future PR proposing to merge `record_kind`
discriminators OR to decouple `fixture_id` population at
expectation vs. observation persistence sites is rejected at
the spec layer per member #7 protection.

### 2.2 What the carrier set hands forward

The 15-carrier set + binding framing clarification is the
durable governance set Gate 3 / Gate 4 inherit:

- **Carriers #1-#13** — Gate 1 (PR 4 + PR 5 + PR 6) governance.
  Inherited unchanged into Gate 2.
- **Carrier #14** — Gate 2 framing §6.1: declared epistemic
  class vs. persisted provenance distinction. Property C
  governs declaration; KNOWN_SOURCE_VALUES governs persisted
  provenance after contextual annotation. Introduced at Gate 2
  framing.
- **Carrier #15** — PR 8 framing §0: chat-handler-only seeding
  scope. PR 8 seeds chat-handler observation surface only;
  chain-step seeding deferred; cross-surface expectation
  semantics require a dedicated framing pass. Introduced at
  PR 8 framing.
- **Binding framing clarification** — Gate 2 framing §6.2:
  arbitration-state fields are call-site-owned explicit
  inputs; dispatch provenance is contextual metadata derived
  at emission time.

**The carrier set's 15-count is permanent at Gate 2 close.**
Gate 3 framing may introduce a **carrier #16** if it surfaces
a load-bearing protection that requires verbatim travel into
production source. The PR 9 governing sentence ("PR 9 proves
topology, not infrastructure.") is a **carrier #16 candidate**;
its travel pattern across PR 9 surfaces (8+ surfaces; spec +
framing + fixtures + test modules + commit bodies) provides
corroboration evidence. Gate 3 framing may revisit the
promotion question with that evidence.

**Gate 3 framing MUST** carry the 15 inherited carriers +
binding framing clarification verbatim into any new Gate 3
production module + test module + commit body. The verbatim
travel discipline is non-optional for Gate 2-substrate
consumers.

### 2.3 What remains undecided

Gate 2 close ships with **four ontological questions** Gate 3
framing must answer if it touches cross-surface fixture
identity. These questions were surfaced at PR 8 framing §7.3
and carried through PR 9 close unchanged:

1. **Does one expectation target one observation surface or
   multiple?** PR 9's three fixtures each target chat-handler
   (one surface); the question of multi-surface expectation
   records remains open.

2. **Does `fixture_id` identify a logical prompt or a specific
   arbitration surface?** PR 9's `fixture_id` values are
   PR-9-anchored strings without surface-encoding. Whether
   "fix-pr9-single-survivor" identifies "the prompt as
   exercised through any surface" OR "the prompt as exercised
   through chat-handler specifically" is not decided.

3. **Is cross-surface divergence meaningful or noise?** If a
   fixture's `expected_narrow` matches chat-handler's actual
   narrowing decision but chain-step's narrowing decision
   differs, is that a Gate 4-reportable divergence or normal
   surface asymmetry? Not decided.

4. **Does Gate 4 compare within surfaces or across them?** The
   comparator's partition strategy — fixture-keyed joins
   vs. fixture-plus-surface-keyed joins — depends on questions
   1-3. Not decided.

Carrier #15's third clause is **governance, not explanation**:

> *"Cross-surface expectation semantics require a dedicated
> framing pass before implementation proceeds."*

Any future PR proposing chain-step seeding OR cross-surface
fixture identity OR cross-surface comparator semantics
**without a dedicated framing pass first** is rejected at the
spec layer.

**Gate 3 framing has two paths:**

- **Path A:** Address the four ontological questions via a
  dedicated cross-surface fixture-identity framing pass.
  Resolution unblocks chain-step seeding + cross-surface
  comparator semantics.
- **Path B:** Defer the four questions to Gate 4 or beyond.
  Gate 3 ships the comparator scoped to within-surface
  comparison only (chat-handler-only per carrier #15's
  current scope). Cross-surface semantics remain open.

PR 9 close + Gate 2 close do NOT prescribe a path. Gate 3
framing decides.

### 2.4 What Gate 3 / Gate 4 must NOT re-litigate

Gate 2 close ships the following decisions as **non-revisitable
at gate scope**:

1. **The three-authority-surface partition.** Gate 2 framing
   §3.4 + PR 8 spec §4.1.5.1 are operational. Future cleanup
   PRs proposing to collapse the partition are rejected at
   the spec layer.
2. **`forge_bridge.__all__` at 19 symbols.** PR 7 + PR 8 + PR 9
   surfaces are corpus-internal; no Gate 2 deliverable enters
   `__all__`. Future promotion requires framing-level review
   at first concrete external consumer (deferred per PR 8
   framing §5.6 Q5 + PR 9 framing §5.6 Q6).
3. **`KNOWN_SOURCE_VALUES` 2-element + `_KNOWN_RECORD_KINDS`
   2-element.** PR 7 spec §7 close conditions reject any
   third-value addition without framing-level review.
4. **The expectation record schema (3 required keys).** PR 9
   spec §5.5 Q5 rejects extension without framing-level
   review. Gate 4 comparator may surface concrete need; that
   surfaces at Gate 4 framing.
5. **The three-walker Layer 2 partition.** Future "walker
   unification" cleanup proposals rejected at the spec layer
   (PR 9 spec §4.6 + §7).
6. **Carrier #10's chain-step-specific zero-match language.**
   PR 9 §4.7 amendment 2026-05-11 canonicalized the
   chat-handler-surface narrowing-outcome topology (single
   survivor / multi-match / no-keyword-match fallback). Any
   future extrapolation of chain-step semantics onto
   chat-handler is rejected at the spec layer.
7. **Cleanup-pressure-resistance class members #1-#9.** Each
   member's protection is operationally enforced; future
   cleanup PRs proposing to erode any member's protection are
   rejected at the spec layer (per each member's per-PR close
   §1 protection summary + Gate 2 close §5 inventory).
8. **The amendment-at-incarnation cluster methodology.** Four
   variants canonicalized; future amendments use the
   canonicalized variants (drafting-time / implementation-time
   / verification-time / grounding-time).
9. **The Step N.5 surgical cadence.** Three-times corroborated
   (PR 8 Step 4.5 + PR 9 Step 2.5 + PR 9 Step 5.5); available
   to future reliability phases without re-framing.
10. **Zero production source file modifications at PR 9 as
    architectural validation signal.** Validates PR 7 + PR 8
    decomposition strategy; the validation is permanent
    archaeology.

---

## 3. Gate 2 close criteria — verification per framing §11

Gate 2 framing §11 lists six closure criteria. All six are
operationally verified at this artifact's commit:

1. **The two Gate-2 authority surfaces** (observation +
   authored expectation) operate end-to-end under real seeded
   execution. **✓ verified at PR 9 Step 3** (3 e2e integration
   tests; arbitration grounding center).
2. **First fixtures run end-to-end** demonstrating observation
   + expectation persistence + reader validation. **✓ verified
   at PR 9 Step 3 + Step 4** (3 fixtures + 5 integration tests
   + reader-based assertion suite).
3. **Gate 4 unblocked for comparator articulation:**
   `KNOWN_SOURCE_VALUES` + `record_kind` schema in place (PR 7);
   comparator dependencies named + verified mechanically. **✓
   verified at PR 9 Step 4** (partition/joinability proof
   center; tests 4 + 5).
4. **Layer 1 + Layer 2 extensions mechanically verified.**
   Layer 3 unchanged + still green against modified `_capture.py`.
   **✓ verified at PR 9 Step 5** (Layer 3 lint regression
   17/17 unchanged; PR 4 walker unchanged; PR 8 walker
   unchanged; PR 9 walker operational).
5. **The 14+ carriers travel verbatim** into all Gate 2
   production modules + test docstrings + commit messages. **✓
   verified at PR 9 Step 5 item 9** (15 carriers + binding
   framing clarification travel verbatim across all Gate 2
   surfaces).
6. **A `A.5.3.2-GATE-2-CLOSE.md` artifact** ships at the PR 9
   close commit. **✓ at this commit** (this artifact + PR 9
   close artifact ship at the same commit).

All six criteria reached. Gate 2 is structurally closed.

---

## 4. Architectural delta from Gate 1 → Gate 2

Gate 1 closed at PR 6 (commit `9168df7`). Gate 2 advances the
architecture along **four orthogonal axes**:

### 4.1 Substrate evolution

Gate 1's substrate was the **observation-only persistence
layer**: `_capture.py` ships `emit_divergence_capture` +
record schema (single record kind, single source-of-truth).
Gate 2 evolved the substrate to a **dual-record-kind
persistence layer**:

- `record_kind` discriminator field added to schema (PR 7).
- `KNOWN_SOURCE_VALUES` introduced for source provenance
  governance (PR 7).
- `seed_dispatch_scope` + `_DispatchContext` introduced for
  contextvar-scoped dispatch provenance (PR 7).
- `_persist_expectation_record` seam introduced for
  expectation-record persistence (PR 7).

The substrate evolution preserves backward compatibility — PR 6
records remain readable; PR 7 + PR 8 records add new kinds
without breaking existing readers.

### 4.2 Authority surface introduction

Gate 1 had one authority surface (the observation call-site +
emit-helper pair). Gate 2 introduces **two new authority
surfaces** (the dispatch-provenance scope + the authored-
expectation helper) and a **PR-INTERNAL sub-partition** within
the authored-expectation surface (PR 8 spec §4.1.5.1).

The total authority-surface count at Gate 2 close: **3 gate-
level + 3 PR-internal = 6 distinct authority classes**, each
mechanically protected.

### 4.3 Cleanup-pressure-resistance class growth

Gate 1 contributed 1 member to the cleanup-pressure-resistance
class (member #2: visual asymmetry / Properties A-D at PR 6).
Gate 2 grows the class to **9 members** (PR 7 = 6; PR 8 = 2;
PR 9 = 1).

The class is now demonstrably populatable across two gates
(Gate 1 + Gate 2). Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is candidate;
final promotion gate is a fourth-reliability-phase
corroboration.

### 4.4 Methodology contribution — amendment cluster + Step N.5

Gate 1 introduced amendment-at-incarnation as a single variant
(drafting-time, at PR 6 spec). Gate 2 **canonicalized the
4-variant taxonomy**:

- Drafting-time (PR 6 + PR 7 + PR 8 spec §4.5).
- Implementation-time (PR 8 §1.3 cluster #5-#7).
- Verification-time (PR 8 Step 4.5).
- Grounding-time (PR 9 §4.7 amendment 2026-05-11).

Plus the **Step N.5 surgical cadence**: introduced at PR 8
Step 4.5; corroborated at PR 9 Step 2.5 + PR 9 Step 5.5
(three instances total).

Gate 2's methodology contribution is the **cluster
canonicalization** — Gate 3 framing inherits a four-variant
amendment vocabulary + a three-times-corroborated surgical
cadence, ready to use without re-derivation.

---

## 5. Methodology observations across PR 7 + PR 8 + PR 9

### 5.1 The four-variant amendment taxonomy — complete inventory

**Variant 1: Drafting-time amendments**

- **Trigger:** Spec authoring surfaces a discovery against the
  framing or against actual code surfaces being committed to
  in the spec.
- **Registration:** Spec §4.5 sub-section + NO-code amendment
  commit.
- **Atomic boundary:** The spec amendment IS the commit;
  separate from implementation work.

**PR instances:**

- PR 6 spec §4.5 — first drafting-time amendment in the
  reliability-phase arc (Gate 1).
- PR 7 spec §4.5 — 2 amendments at drafting (per PR 7 close
  §5 if it exists; otherwise per PR 7 spec §4.5 directly).
- PR 8 spec §4.5 — 4 amendments at drafting:
  - §4.5.1: schema validator extension scope.
  - §4.5.2: `_SEED_PERMITTED_IMPORTS` admission semantics.
  - §4.5.3: corpus → console import direction exception.
  - §4.5.4: Path E sync→async bridge architecture.

**Variant 2: Implementation-time amendments**

- **Trigger:** Step N implementation surfaces a discovery the
  spec did not anticipate; the discovery alters the step's
  implementation shape mid-flight.
- **Registration:** Folded into step commit body as
  "implementation-time amendment" section.
- **Atomic boundary:** The step commit IS the implementation
  + the amendment; not separated.

**PR instances:**

- PR 8 §1.3 cluster #5-#7 (3 amendments) — the methodology-
  hygiene cluster at PR 8 close §1.3.

**Variant 3: Verification-time amendments**

- **Trigger:** Step 5 verbatim-travel verification surfaces
  scaffold prose drift OR carrier travel drift adjacent to
  the load-bearing block.
- **Registration:** Surgical Step N.5 commit before Step 5
  verification lands.
- **Atomic boundary:** Step N.5 + Step 5 = two separate
  commits; Step N.5 preserves Step 5's "no new code"
  discipline.

**PR instances:**

- PR 8 Step 4.5 (`9785d69`) — scaffold prose cleanup; 14
  deletions / 2 insertions across 2 files.

**Variant 4: Grounding-time amendments — NEW at PR 9**

- **Trigger:** Step 2 / Step 3 implementation begins consuming
  a previously-only-described substrate empirically. Empirical
  inspection reveals framing/spec extrapolation does not
  hold.
- **Registration:** Separate NO-code amendment commit per
  amendment-convergence direction.
- **Atomic boundary:** Amendment commit is distinct from the
  implementation step that surfaces it; the amendment's
  archaeology travels as its own commit.

**PR instances:**

- PR 9 §4.7 amendment 2026-05-11 (`2c7a2ca`) — `fix_zero_match.py`
  → `fix_no_keyword_match.py` rename + corrected chat-handler
  narrowing-outcome topology + spec §4.5 monkeypatch strategy
  subsection + spec §4.7 amendment archaeology.

**Total amendment count across PR 7 + PR 8 + PR 9: 10 amendments.**

(PR 7 = 2 drafting; PR 8 = 4 drafting + 3 implementation +
1 verification = 8; PR 9 = 1 grounding. **2 + 8 + 1 = 11
amendments**; the framing's "8 amendments at incarnation"
count was a conservative estimate — actual count after PR 9
inclusion is 11.)

### 5.2 The Step N.5 surgical cadence

**Pattern:** Mid-flight guidance surfaces an additive
improvement to a recently-shipped deliverable. Register the
improvement as a surgical N.5 commit BEFORE the next major
deliverable lands.

**Properties:**

- May be empty (Step 5.5) or small (Step 2.5: 18 lines).
- Preserves the step boundary's "distinct atomic boundary"
  discipline.
- Triggered by user guidance, NOT by autonomous discovery.

**Corroborations (3 instances across PR 8 + PR 9):**

1. **PR 8 Step 4.5** (`9785d69`) — verification-time variant.
   Scaffold prose cleanup surfaced at Step 5 verification;
   14 deletions / 2 insertions.
2. **PR 9 Step 2.5** (`94022de`) — mid-flight guidance variant.
   Authored/observed divergence framing addition; 18-line
   additive insertion.
3. **PR 9 Step 5.5** (`d598bf6`) — post-verification guidance
   variant. Item 11 standalone verification + cumulative-
   architectural-concentration wording refinement; empty
   commit.

**Promotion candidacy:** Three-times corroborated. Strong
methodology promotion candidate. Final promotion gate is a
**fourth-phase corroboration under genuinely independent
conditions** (matching the cleanup-pressure-resistance class
promotion gate).

### 5.3 The cleanup-pressure-resistance class — complete inventory at gate scope

| # | Member | PR of origin | Protection summary |
|---|---|---|---|
| 1 | Helper duplication (`emit_divergence_capture` + `_persist_expectation_record`) | PR 7 | Sibling helpers; no shared internal writer; protected by framing §6 + spec §7 close conditions. Protects against "let's DRY them" cleanup pressure that would erode the persistence-topology authority partition. |
| 2 | Visual asymmetry / Properties A–D at every call site | PR 6 (Gate 1) | The structural-backstop pattern: arbitration vs. observation visual asymmetry verified by Layer 3 lint. Protects against "let's collapse the pair into one function" cleanup pressure. |
| 3 | Intentionally inert structural parameters (`source="runtime"`) | PR 7 | Call sites pass `source="runtime"` literal as structural truth-of-call-site; contextvar dispatch later overrides at emission boundary. §4.2 binding pair documents protection. Protects against "this parameter is useless" cleanup pressure. |
| 4 | Always-present `fixture_id` field on observation records | PR 7 | Builder dict carries `"fixture_id": None` when no scope is active. Protects against "let's omit the field when null" cleanup pressure that would erode reader's null-handling discipline. |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 | Reader's `fixture_id` synthesis is NESTED inside the `record_kind not in record` branch. §5.5 binding pair documents protection. Protects against "let's flatten the conditional" cleanup pressure. |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 | No shared `_log_persistence_warning` helper extracted; each I-6 wrapper site duplicates the logging block inline. Protects against "let's DRY the logging" cleanup pressure that would erode the per-site exception-handling specificity. |
| 7 | Companion records as truth-partitioning | PR 8 | Observation + expectation records persist as separate records; member #7 protection in `_seed.py` module docstring + spec §0 + framing §6.1. Schema validator's expectation-branch rejection of `source` field is mechanical persistence-boundary guard. Protects against "let's merge them into one richer record" cleanup pressure that would destroy falsifiability. |
| 8 | `emit_seed_expectation` as semantics-not-topology | PR 8 | Helper builds record dict + delegates persistence to `_persist_expectation_record`; does NOT inline file I/O. `_SEED_PERMITTED_IMPORTS` value-locked at 5 symbols (2 authority surfaces + 3 universal-key utilities). Protects against "let's inline persistence for symmetry with `emit_divergence_capture`" cleanup pressure. |
| 9 | Fixture-surface-data-discipline | PR 9 | Fixtures are data + one orchestration call only. `_FIXTURE_PERMITTED_IMPORTS` value-locked at 1 symbol + walker enforces against fixture directory glob. Three protected properties: grep archaeology + carrier travel discipline + single-symbol-gate Layer 2 discipline. Protects against "let's add a `make_fixture(...)` helper" / "let's parametrize the fixture set" cleanup pressure. |

**Promotion-candidate inventory** for
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`:

- **Strong candidates** (three-phase corroboration):
  - Cleanup-pressure-resistance class as a discipline (Gate 1
    + Gate 2's three PRs = three reliability phases
    contributed members).
  - Step N.5 surgical cadence (PR 8 + PR 9 × 2 = 3 instances).
- **Strong candidates** (two-phase corroboration):
  - Relevance-by-file ordering principle (PR 7 close §1.5
    introduced; PR 8 close §1.5 generalized to NEW modules;
    PR 9 extends to fixture modules).
  - PR-INTERNAL three-way authority partition pattern (PR 8
    introduced; PR 9 inherited unchanged).
- **Candidate** (single-phase introduction):
  - Grounding-time amendment variant (PR 9 §4.7 introduced).
    Requires future reliability-phase corroboration before
    promotion.
  - Three-walker Layer 2 parallel-not-extension partition
    (PR 9 §4.6 + §4.7 introduced; PR 4 + PR 8 + PR 9 walker
    discipline). Pattern itself is two-phase (PR 8 had a
    walker; PR 9 introduces a parallel walker) but the
    parallel-not-extension articulation is PR 9-specific.

**Promotion gate (the discipline rule):**
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` promotion is
gated on **a fourth reliability phase populating the class /
methodology under genuinely independent conditions** (per
PR 7 framing §6 original criterion). The third-phase
corroboration is strong but the fourth phase is the discipline
gate.

### 5.4 Three-walker Layer 2 parallel-not-extension partition

PR 4 + PR 8 + PR 9 each ship a Layer 2 AST walker. Each
protects a distinct ontology. **Shared AST mechanics do not
imply shared ontology.**

- **PR 4 walker** — production import topology; target =
  production source files; rule = one-directional flow.
- **PR 8 walker** — orchestration participation discipline;
  target = `_seed.py`; rule = 5-symbol bounded toolbox
  (semantics-not-cardinal).
- **PR 9 walker** — declarative fixture-data discipline;
  target = `tests/corpus/fixtures/*.py` glob; rule =
  single-symbol-gate (1-symbol value-lock).

Future "walker unification" cleanup proposals are **rejected
at the spec layer** per PR 9 spec §4.6 + §7. A unified walker
abstraction is appealing locally (deduplication of AST
traversal code) but architecturally erodes three distinct
protections. Each walker stays local to its ontology.

The closing sentence — *"Shared AST mechanics do not imply
shared ontology."* — lands as carrier-equivalent prose in the
PR 9 discipline test module docstring + PR 9 spec §4.6 +
this Gate 2 close §5.4.

### 5.5 The relevance-by-file ordering principle generalized

PR 7 close §1.5 introduced the relevance-by-file ordering
principle: at each new file's docstring carrier block, the
**most-relevant inherited carrier lands at TOP** of the block,
followed by the rest in numbered order.

**Three-phase generalization:**

- **PR 7** — `_capture.py` carries 14 inherited carriers
  + PR-7-LOCAL pairs.
- **PR 8** — `_seed.py` carries 15 carriers + 2 PR-8-LOCAL
  binding statements; carrier #15 lands at TOP (most-relevant
  for the seed-driver scope).
- **PR 9** — three fixture modules each carry 15 carriers per
  the principle (carrier #15 at TOP for each fixture; chat-
  handler-only scope is the most-relevant inherited governance
  for fixture surfaces).

`fix_no_keyword_match.py` exhibits a subtle variation: the
§4.7 amendment archaeology paragraph lands FIRST (per most-
current-PR-anchored governance precedence) + carrier #15
follows. This is the principle correctly applied — current
PR-anchored governance precedes inherited carrier blocks per
PR 7 close §1.5 + PR 8 close §1.5 + the §4.7 amendment's
"renaming archaeology" requirement.

### 5.6 Cumulative-architectural-concentration framing

PR 9 Step 5.5 (`d598bf6`) canonicalized the framing for
multi-step proof surfaces:

- **Step 3 + Step 4** form a single architectural concentration
  (the Gate 4 comparator-unblock proof surface), spanning
  two complementary proof centers (arbitration grounding +
  partition/joinability proof).
- **Avoid** "the architectural center" (singular) or
  "architectural-center #1 / #2" (hierarchical) framings.
- **Prefer** "[Step X + Step Y] form the [proof surface name]"
  framings.

The methodology contribution: future reliability phases
consuming multi-step proofs should adopt the cumulative-
concentration framing. Single-step architectural centers
remain valid (per PR 7's Step N pattern); multi-step centers
need the cumulative framing.

---

## 6. Cross-references

- **`A.5.3.2-PR9-CLOSE.md`** (this commit) — ships at the
  same commit as this artifact. PR 9 close owns PR-level
  archaeology + 10-commit chain detail + grounding-time
  amendment as PR 9 contribution. This Gate 2 close owns
  gate-arc synthesis.
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — durable PR 8
  archival state; §1.3 amendment cluster (3 implementation-
  time amendments); §5.2 verification-time amendment
  methodology (Step 4.5 pattern).
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — durable PR 7
  archival state; substrate evolution archaeology;
  cleanup-pressure-resistance class members #1-#6.
- **`A.5.3.2-PR6-CLOSE.md`** (`9168df7`) — Gate 1 close
  template; §6 carries Gate 1 closure synthesis. This Gate 2
  close mirrors PR 6 close's gate-closure shape but ships as
  a separate file per Gate 2 framing §11.6.
- **`A.5.3.2-GATE-2-FRAMING.md`** (`ceac9b5`) — Gate 2
  framing; §3.4 three-authority-surface partition; §4
  architectural delta; §5 binding decisions; §6 carrier
  delta; §11 close criteria.
- **`A.5.3.2-PR9-FRAMING.md`** (`5628817`) — §0 governing
  sentence; §6.1 member #9.
- **`A.5.3.2-PR9-SPEC.md`** (`f8ccf0f` + amendment
  `2c7a2ca`) — §0 16 verbatim sentences; §4.7 grounding-time
  amendment archaeology.
- **`A.5.3.2-PR8-FRAMING.md`** (`23f2a20`) — §0 carrier #15;
  §6 members #7 + #8; §7 non-acquisition commitments + §7.3
  four ontological questions.
- **`A.5.3.2-PR8-SPEC.md`** (`85c5bc1`) — §0 18 verbatim
  sentences; §4.1.5.1 PR-INTERNAL three-way authority
  partition; §4.5 four drafting-time amendments; §7
  phase-end conditions rejection table.
- **`A.5.3.2-PR7-FRAMING.md`** (`1c1e061`) — §6 cleanup-
  pressure-resistance class introduction; §7 non-acquisition
  commitments.
- **`A.5.3.2-PR7-SPEC.md`** (`84392d2`) — `seed_dispatch_scope`,
  `_persist_expectation_record`, `KNOWN_SOURCE_VALUES`,
  `_KNOWN_RECORD_KINDS`; §7 phase-end rejection table.
- **`forge_bridge/corpus/_seed.py`** — PR 8 production
  surface; carries 15 carriers + binding clarification +
  2 PR-8-LOCAL binding statements at module docstring.
- **`forge_bridge/corpus/_capture.py`** — PR 7 production
  surface (modified at PR 7 from PR 6 baseline); carries 14
  inherited carriers + binding clarification at module
  docstring.
- **`forge_bridge/console/_tool_filter.py:258-407`** — PR14
  + PR21 narrowing pipeline; the §4.7 grounding-time
  amendment's empirical anchor.
- **`tests/corpus/test_pr4_participation_creep.py`** — PR 4
  walker (production import topology).
- **`tests/corpus/test_pr8_seed_surface.py`** — PR 8 walker
  (orchestration participation discipline).
- **`tests/corpus/test_pr9_fixture_discipline.py`** — PR 9
  walker (declarative fixture-data discipline).
- **`tests/corpus/fixtures/*.py`** — PR 9 fixture corpus
  (three modules + `__init__.py`).
- **`tests/corpus/test_pr9_fixture_integration.py`** — PR 9
  integration test infrastructure + 5 named integration
  tests.
- **Local memory** updates expected at next session:
  - `project_state_2026_05_11_pr9_closed_gate_2_closed.md`
    — new cursor superseding pr8-closed cursor.
  - `project_three_architectural_layers.md` — Gate 2
    completes the second layer (arbitration); the layer is
    now operational across substrate + boundary + consumption.

---

End of Gate 2 close. The three-PR arc that opened at Gate 2
framing (`ceac9b5`, 2026-05-08) closes here. PR 7 substrate +
PR 8 boundary + PR 9 consumption compose the **operational
three-authority-surface partition** that is Gate 2's load-
bearing deliverable.

The four-variant amendment-at-incarnation cluster is
canonicalized. The Step N.5 surgical cadence is three-times
corroborated. The cleanup-pressure-resistance class is at 9
members across two gates. The three-walker Layer 2 partition
operates parallel-not-extension. Carrier #15 governs the
chat-handler-only scope; the four §7.3 ontological questions
remain open for Gate 3 framing.

**Gate 4 inherits an unblocked path.** The comparator's two
foundational dependencies (record_kind partition + fixture_id
joinability) are operationally verified at PR 9 Step 4.
Gate 4's comparator authoring begins from a stable foundation
— the partition + the join + the controlled-set + the
authored/observed divergence proof case (`fix_no_keyword_match`)
all ship at this commit.

**Gate 3 framing has two paths** (per §2.3): address the four
ontological questions via cross-surface fixture-identity
framing pass (Path A) OR defer to Gate 4+ and ship comparator
scoped to chat-handler only (Path B). Gate 2 close does NOT
prescribe; Gate 3 framing decides.

The 15 inherited carriers + binding framing clarification +
PR 8 carrier #15 travel verbatim into all Gate 2 surfaces.
PR 9's governing sentence — *"PR 9 proves topology, not
infrastructure."* — remains a **carrier #16 candidate** with
8+ surface travel-pattern corroboration. Gate 3 framing may
revisit promotion.

Gate 2 closes structurally. The substrate Gate 4 needs is
operational. The methodology Gate 3 inherits is canonicalized.
The discipline that produced it — atomic boundary preservation
+ amendment-at-incarnation hygiene + cleanup-pressure-resistance
class growth + relevance-by-file ordering + cumulative-
architectural-concentration framing — is the durable
methodological contribution of Gate 2.
