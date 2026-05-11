# A.5.3.2 PR 10 — Spec (comparator helper + structural protection)

**Status:** Spec-stage artifact for PR 10 of Gate 3. PR 10 framing
locked at `8ad7fe9` (1171 lines); this spec derives the
implementation contract by finalizing the six symbol-level
decisions named in the framing's "Things that might trip up #1"
plus one additional decision (the comparator behavioral test
file name) and one incarnation-time decision (conditional 3rd
authorship-preservation test).

PR 10 is the first of two (or conditionally three) PRs sequenced
within Gate 3 per Gate 3 framing §10. The PR 10 close artifact
(`A.5.3.2-PR10-CLOSE.md`) lands at the PR 10 final commit per
framing §9 condition 16; the Gate 3 close artifact ships at
PR 11 close per Gate 3 framing §11.

This spec's job: derive file-level precision from the framing's
locked decisions. Each new file's exact shape (path, imports,
docstring carrier order, function/constant signatures, body
structure). Each test's exact name + assertion contract. Each
implementation step's atomic boundary + verification checklist.
The spec's outputs are mergeability anchors — counts, file
paths, function names, test names — that PR 10 close §6 will
verify against.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Seventeen sentences** travel verbatim into PR 10's surface.
Sixteen are active carriers — fifteen inherited from PR 4 +
PR 5 + PR 6 + PR 8 + Gate 2 (the same set Gate 3 framing locks
at §3.1) + carrier #17 (introduced at Gate 3 framing §5.1). One
is the Gate 2 binding framing clarification on call-site-owned
arbitration inputs. PR 10 introduces **zero new numbered
carriers** beyond Gate 3 framing's #17 (per PR 10 framing §3.1).

**Two additional governing sentences travel at reduced sites:**

- The **Gate-3-LOCAL governing sentence** ("Gate 3 proves
  topology, not infrastructure.") is the **candidate carrier
  #16 corroboration substrate** — framing-artifact-scoped per
  Gate 3 framing §0 + §6.1 promotion deferral. Travels into
  `_compare.py` module docstring + PR 10 test module
  docstrings + PR 10 commit message bodies, always with
  explicit *candidate carrier #16 corroboration substrate*
  marking. Promotion to carrier #16 is evaluated at Gate 3
  close (PR 11), not at PR 10 close. PR 10 must NOT write
  *"17 active carriers"* or *"carriers #1–#17"* — correct
  phrasing is *"16 active carriers + candidate #16"* (per
  PR 10 framing §3.1).

- The **Gate 2 binding framing clarification on cross-surface
  unbinding** (Gate 3 framing §6.2):
  > **The comparator's authority is bounded to within-surface
  > divergence between authored expectation and observed
  > arbitration outcome for a single operational arbitration
  > surface. Cross-surface comparator semantics are
  > intentionally unbound pending dedicated framing review.**
  This clarification governs scope; it travels into `_compare.py`
  module docstring + PR 10 commit message bodies.

**Three PR-LOCAL binding statements travel scope-locally:**

- The **proactive scope guardrail** (PR 10 framing §3.5,
  inherited from Gate 3 framing §2.3) — names what the
  comparator compares operationally.
- The **§4.2 binding behavioral commitment** ("compare as
  persisted") — names the comparator's normalization-rejection
  posture at the function body.
- The **PR-10-LOCAL binding statement** (PR 10 framing §5.6)
  — names the read-only mutability invariant at the function
  surface.

All three travel verbatim into `_compare.py` function docstring
+ PR 10 test module docstrings + PR 10 commit message bodies.
Per the PR-N-LOCAL non-regeneration rule (Gate 2 framing §3.1):
these scope-local statements do NOT regenerate beyond PR 10's
own surfaces. PR 11 / PR 12 / Gate 4 work does not inherit them
unless re-stated at framing level.

The seventeen sentences plus the three PR-LOCAL statements
travel into:

1. `forge_bridge/corpus/_compare.py` module-level docstring per
   the relevance-by-file ordering (carrier #17 + Gate-3-LOCAL
   form + proactive scope guardrail + PR-10-LOCAL + cross-
   surface unbinding clarification at TOP; inherited carriers
   #1–#15 after; call-site-owned-inputs binding framing
   clarification after).
2. `forge_bridge/corpus/_compare.py::compare_records` function
   docstring (carrier #17 + proactive scope guardrail + §4.2
   binding behavioral commitment + PR-10-LOCAL binding
   statement; inherited carriers cited by reference to the
   module docstring).
3. `tests/corpus/test_pr10_comparator_discipline.py` top-level
   docstring (carrier #17 + Gate-3-LOCAL form + the *"Shared
   AST mechanics do not imply shared ontology"* protection echo
   + carriers #1–#15 cited by reference to `_seed.py` canonical
   source).
4. `tests/corpus/test_pr10_comparator.py` top-level docstring
   (carrier #17 + Gate-3-LOCAL form + proactive scope guardrail
   + paraphrased PR-10-LOCAL statement: *"tests assert the
   comparator does not mutate its inputs and produces no side
   effects"*).
5. PR 10 commit message bodies under "preserved invariants" /
   "Gate-3-LOCAL corroboration" sections.

### Active carrier #17 — recomposition discipline (introduced at Gate 3 framing §5.1)

> **Recomposition preserves authorship. The comparator joins
> observation + expectation records by `fixture_id` at read
> time; the join produces a derived view that names each
> authority surface's contribution explicitly. Cleanup pressure
> to collapse the three-authority-surface partition through
> interpretive synthesis is rejected at the spec layer.**

Carrier #17 is the architectural commitment PR 10 enacts.
Every PR 10 deliverable — the function signature, the
divergence report shape, the 4th walker's protection — is the
operational form of this carrier.

### Inherited carriers #1–#14 + binding framing clarification (verbatim)

Production-truth source: `forge_bridge/corpus/_capture.py:6–135`
+ `forge_bridge/corpus/_seed.py:19–135`. Reproduced here in the
same order they land in the source-of-truth artifacts.

**#1–#2 — risk-category shift (PR 4):**

> **PR 4 is the controlled introduction of observational
> side-effects into live arbitration surfaces.**

> **The risk category has shifted from persistence-substrate risk
> to participation-creep risk.**

**#3–#6 — integration-discipline quartet (PR 4):**

> **The call site is the source of the three explicit inputs.**
>
> **The integration layer passes truth.**
>
> **The integration layer never reconstructs truth.**
>
> **The builder does not discover runtime state.**

**#7 — finalized-state contract (PR 4):**

> **Capture emission occurs only after arbitration state is
> finalized for the current execution path. Capture records
> completed arbitration observations, not provisional
> intermediate state.**

**#8 — risk-inheritance + surface-geometry distinction (PR 5):**

> **PR 5 is the second call site under the integration discipline
> PR 4 established. The risk profile is inherited; the surface
> geometry is not.**

**#9 — caller's view of deployment identity (PR 5):**

> **The chain-step's deployment identity is the caller's view, not
> the global daemon registry view.**

**#10 — ambiguity-as-arbitration-outcome (PR 5):**

> **Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths. `pr20_condition_met`
> is always False and `collapse_occurred` is False on all
> rejection paths. These semantics differ from the chat-handler
> case and must not be silently overloaded.**

**#11 — measured-not-inferred coverage (PR 5):**

> **No-dependency coverage at the chain-step surface must be
> measured, not inferred. The existing probe drives only the
> chat-handler single-step path; PR 5 owns the responsibility to
> extend coverage to the chain-step path empirically.**

**#12 — structural-backstop framing (PR 6):**

> **PR 6 is the structural backstop for the visual-asymmetry
> pattern. The lint validates shape, not content; structure, not
> interpretation. Carrier content is the room's job; field
> validation is the helper signature's job; the lint validates the
> visual asymmetry between arbitration and observation.**

**#13 — observation-not-participation framing (PR 6):**

> **The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.**

**#14 — declared epistemic class vs. persisted provenance (Gate 2):**

> **Property C governs the epistemic class declared at the
> observation boundary. KNOWN_SOURCE_VALUES governs persisted
> provenance classes after contextual annotation has been
> resolved.**

**Binding framing clarification — call-site-owned arbitration
inputs (Gate 2):**

> **Arbitration-state fields remain call-site-owned explicit
> inputs. Dispatch provenance is contextual metadata derived at
> emission time and does not participate in arbitration
> semantics.**

### Inherited carrier #15 (PR 8)

**#15 — chat-handler-only seeding scope:**

> **PR 8 seeds the chat-handler observation surface only. Chain-
> step seeding is explicitly deferred because `handlers.py` and
> `_step.py` produce semantically distinct observation records.
> Cross-surface expectation semantics require a dedicated framing
> pass before implementation proceeds.**

Carrier #15 governs PR 10's scope: the comparator operates
within the chat-handler observation surface only. Carrier #15's
"semantically distinct observation records" warning is the
operational ancestor of carrier #17's "three-authority-surface
partition" governance. PR 10 inherits unchanged.

### Candidate carrier #16 + Gate-3-LOCAL governing sentence

**Gate-3-LOCAL governing sentence (candidate carrier #16
corroboration substrate):**

> **Gate 3 proves topology, not infrastructure.**

Promotion to numbered carrier #16 is evaluated at Gate 3 close
(PR 11). PR 10 contributes ≥3 of the ≥4 surfaces required for
the promotion evaluation per Gate 3 framing §6.1 criterion 1.
PR 11 contributes the remaining ≥1.

The sentence is short by design. It is the rejection key for the
function-vs-subsystem cleanup-pressure trap. PR 10 is the
canonical instance of that trap — successful resistance during
implementation is the load-bearing corroboration Gate 3 close
evaluates.

**Travel discipline at PR 10:** the Gate-3-LOCAL form appears
**after** carrier #17 (active, primary) with explicit *candidate
carrier #16 corroboration substrate* marking. The asymmetric
ordering matches the asymmetric carrier states (active vs.
candidate) per PR 10 framing §0.

### Binding framing clarification — cross-surface unbinding (Gate 3)

> **The comparator's authority is bounded to within-surface
> divergence between authored expectation and observed
> arbitration outcome for a single operational arbitration
> surface. Cross-surface comparator semantics are intentionally
> unbound pending dedicated framing review.**

This clarification governs scope at the explicitly-unbound-vs-
implicitly-rejected distinction (per
`feedback_explicitly_unbound_vs_implicitly_rejected`). The
language is deferral, not rejection: cross-surface comparator
semantics may eventually surface; PR 10 does not foreclose them
by spec language; PR 10 does not implement them. Path B locked
at Gate 3 framing §5.1.

### Proactive scope guardrail (Gate 3 framing §2.3 + PR 10 framing §3.5)

> **The comparator compares authored expectation records against
> observed arbitration records within a single operational
> arbitration surface.**

(NOT "logical prompts," NOT "semantic tasks," NOT "cross-surface
executions" — per Gate 3 framing §2.3.)

Field names in the divergence report MUST NOT smuggle broader
scope vocabulary (e.g., `task_outcome`, `prompt_resolution`,
`semantic_match`). Such field names are rejected at PR 10
implementation review per PR 10 framing §3.5.

### §4.2 binding behavioral commitment — "compare as persisted" (PR 10 framing §4.2)

> **The comparator compares authored and observed records as
> persisted. It does not normalize, reorder, canonicalize,
> repair, or semantically coerce either surface before
> comparison.**

This sentence is the function-body-level binding commitment
closing cleanup-pressure form #5 (premature surface
normalization; Gate 3 framing §4.2). Form #5's enumeration
*describes* the pressure; this commitment is what rejects the
pressure at the function body.

**Operational rejections this commitment makes explicit (verbatim
from PR 10 framing §4.2):**

- The comparator does NOT sort `narrower.decision` or
  `expected_narrow` before comparing — order is meaningful
  observation/expectation; reordering masks divergence.
- The comparator does NOT lowercase tool names, strip
  whitespace, or apply any string canonicalization — those are
  surface-authorship details preserved.
- The comparator does NOT "repair" missing fields, fill
  defaults, or infer absent values — missing data is a
  validation failure (§4.2 validation discipline), not a
  silent normalization.
- The comparator does NOT compare semantically (e.g., "these
  two records mean the same thing even though they differ") —
  comparison is byte-for-byte structural on the persisted
  record contents.

### PR-10-LOCAL binding statement — read-only mutability invariant (PR 10 framing §5.6)

> **The comparator function is structurally incapable of
> mutating its inputs or producing side effects. The signature
> returns a new structured value; the inputs are read but never
> modified; no I/O is invoked; no module-level state is held
> across calls. Tests assert input records remain byte-identical
> after the function returns.**

This is the operational discipline statement protecting
carrier #17 + PR 10 framing §5.3 at the function level.
Structurally parallel to PR 7-LOCAL pairs (scope-local to
`_capture.py` + `reader.py`) and PR 8-LOCAL binding statements
(scope-local to `_seed.py` + `emit_seed_expectation`).

PR-10-LOCAL does NOT regenerate beyond PR 10 scope. PR 11 / PR 12
/ Gate 4 / future-gate work does not inherit PR-10-LOCAL; new
PR-N-LOCAL statements may be authored as their own PR-scope
discipline statements per the canonicalized pattern.

---

## 1. Real job + success condition

**Real job:** *"Land the comparator helper for Gate 3. Ship
`forge_bridge/corpus/_compare.py` as a single pair-input
pure-functional read surface that consumes one observation
record + one expectation record, validates their joinability
through authority-class pre-checks, and produces a structured
`DivergenceReport` dict preserving each authority surface's
authored contribution explicitly. Land the 4th Layer 2 walker
(`tests/corpus/test_pr10_comparator_discipline.py`) protecting
read-only-interpretive authority. Land the comparator
behavioral test module
(`tests/corpus/test_pr10_comparator.py`) — three unit tests
(one per PR 9 fixture) plus two authorship-preservation tests
(mutation-invariant + sort-rejection). Verify the nine
regression contracts hold (PR 3 discipline, PR 4 walker, PR 6
Layer 3 lint, PR 7 modules, PR 8 walker, PR 9 walker, PR 9
integration tests, public API, full corpus test count landing
at 214 forge env / 208 forge-bridge env)."*

**Note (per §4.4 amendment 2026-05-11):** PR 10 ships **zero**
modifications to any test discipline file. The framing §8.1 +
spec §4.4 originally called for a one-line
`test_pr3_discipline.py::_ALLOWLIST` extension; grounding
against the actual test (lines 92–96) revealed the corpus
subtree is auto-excluded before the allowlist check —
`_compare.py` is blanket-permitted by location, no entry
required. See §4.4 for the corrected understanding + amendment
archaeology.

**Success condition:** All seven new tests pass; all eight
regression contracts hold; the 16 active carriers + candidate
#16 Gate-3-LOCAL form + Gate 2 binding framing clarification +
Gate 3 cross-surface-unbinding clarification + proactive scope
guardrail + §4.2 binding behavioral commitment + PR-10-LOCAL
binding statement all travel verbatim into the relevant
docstrings + commit message bodies; the Gate-3-LOCAL form
contributes verbatim travel through ≥3 PR 10 surfaces (per
framing §9 condition 7); zero production source modifications
land outside `forge_bridge/corpus/_compare.py`; `forge_bridge.
__all__` stays at 19 symbols; the three-authority-surface
partition + the PR-INTERNAL three-way authority partition (PR 8
§4.1.5.1) + the 9-member cleanup-pressure-resistance class all
preserve unchanged; the three-walker Layer 2 partition expands
to a four-walker partition with the parallel-not-extension
boundary preserved.

PR 10's success is **operational corroboration** of carrier #17:
the comparator's output shape names the per-surface partition
structurally; the 4th walker enforces the import-set closure
mechanically; the function-body-level §4.2 binding commitment
rejects premature surface normalization; the PR-10-LOCAL
mutability invariant is asserted mechanically by at least one
test. Carrier #17 holds operationally if and only if all five
of these protections land.

The architectural success signal — **0 production source file
modifications outside the new `_compare.py`** — continues from
PR 9. Per Gate 3 framing §11 criterion 11 + PR 10 framing §2.3,
this is a goal not just a happy outcome. If PR 10 implementation
surfaces a need to modify `_capture.py`, `_seed.py`,
`_schema.py`, `_sources.py`, `reader.py`, or any other corpus
or production module, treat as red flag and surface for
framing-level review (see PR 10 framing §9 condition 11 +
"Things that might trip up #7").

---

## 2. Scope

**In scope:**

- **New production source module** —
  `forge_bridge/corpus/_compare.py`. Contains:
  - Module docstring with carrier #17 + Gate-3-LOCAL form +
    proactive scope guardrail + PR-10-LOCAL binding statement +
    cross-surface unbinding clarification at TOP (relevance-by-
    file ordering per framing §4.1), inherited carriers #1–#15
    + Gate 2 call-site-owned-inputs clarification after.
  - Module-level `DivergenceReport: TypeAlias = dict[str, Any]`.
  - Module-level `class ComparatorInputError(ValueError)` —
    exception type raised on caller authority-class misuse.
  - Module-level `compare_records(observation_record: dict,
    expectation_record: dict) -> DivergenceReport` function.
  - Zero other public symbols. Zero classes beyond
    `ComparatorInputError`. Zero module-level mutable state.
- **New test module** —
  `tests/corpus/test_pr10_comparator_discipline.py`. Houses:
  - `_COMPARE_PERMITTED_IMPORTS: frozenset[str]` — value-locked
    to **zero symbols** (`frozenset()`) per §4.1.4 + §5.5.
  - `_compare_corpus_references(source: str) -> list[str]` AST
    walker scoped to `forge_bridge/corpus/_compare.py` per
    §4.2.3.
  - 2 Layer 2 discipline tests per §5.1:
    - `test_compare_permitted_imports_value_locked` (frozenset
      value-lock regression).
    - `test_compare_module_references_subset_of_permitted_imports`
      (walker subset-enforcement against `_compare.py`).
- **New test module** —
  `tests/corpus/test_pr10_comparator.py`. Houses 5 behavioral
  tests per §4.3 + §5.1:
  - 3 unit tests (one per PR 9 fixture).
  - 2 authorship-preservation tests (mutation + sort).
- **Verified test discipline files** (no modifications):
  - `tests/corpus/test_pr3_discipline.py` — **no code changes**
    per §4.4 amendment 2026-05-11. The Layer 1 discipline test
    auto-excludes the corpus subtree (lines 92–96) before the
    `_ALLOWLIST` check; `_compare.py` is blanket-permitted by
    its location inside `forge_bridge/corpus/`. The framing
    §8.1 + spec-original §4.4 calling for a "mechanical
    allowlist extension" was a grounding-time misreading of
    `_ALLOWLIST` semantics. The discipline test passes against
    the post-PR-10 codebase without any modification.
  - `tests/corpus/test_pr4_participation_creep.py` — **no code
    changes.** PR 4 walker protects production-import-topology
    ontology (one-directional flow from narrowing-subsystem
    into corpus). PR 10 ships zero new narrowing-subsystem
    files; the PR 4 walker's input set is unchanged. The
    parallel-not-extension boundary is preserved at the spec
    layer per framing §3.3 + §8.2.
  - `tests/corpus/test_pr8_seed_surface.py` — **no code
    changes.** PR 8 walker protects orchestration-participation
    discipline scoped to `_seed.py`. PR 10 does not modify
    `_seed.py`. The walker's input set is unchanged.
  - `tests/corpus/test_pr9_fixture_discipline.py` — **no code
    changes.** PR 9 walker protects declarative fixture-data
    discipline scoped to `tests/corpus/fixtures/*.py`. PR 10
    does not modify fixture modules. The walker's input set is
    unchanged.
  - `tests/corpus/test_pr6_visual_asymmetry.py` — **no code
    changes.** Layer 3 lint's discovery walk finds calls to
    `emit_divergence_capture` only. PR 10 introduces zero new
    `emit_divergence_capture` call sites (the comparator is a
    consumer, not an emission surface); the lint's input set
    is unchanged.
  - `tests/corpus/test_pr9_fixture_integration.py` — **no code
    changes.** PR 9's 5 integration tests ship unchanged.
  - All `test_pr7_*.py` modules — **no code changes.** PR 7
    surfaces ship unchanged.

**Inheritance from PR 7 + PR 8 + PR 9 (binding):**

> **PR 10 introduces no new dispatch-provenance substrate, no
> new observation-record schema, no new authored-expectation
> helper, no new orchestration surface, no new Layer 3 lint
> surface, no new fixture modules, no new integration tests
> against arbitration. PR 7's `seed_dispatch_scope` +
> `_persist_expectation_record` + `KNOWN_SOURCE_VALUES` +
> `_KNOWN_RECORD_KINDS` ship unchanged. PR 8's
> `emit_seed_expectation` + `drive_seed_fixture` +
> `_SEED_PERMITTED_IMPORTS` + schema-validator expectation-
> branch ship unchanged. PR 9's three-fixture corpus +
> `_FIXTURE_PERMITTED_IMPORTS` + integration tests ship
> unchanged. PR 6's Layer 3 lint enforcement remains unchanged
> and is inherited transitively.**

This sentence resolves the question of why PR 10 ships exactly
one new production source file plus three test-surface
additions. PR 10's job is the comparator helper — a single
read-only-interpretive read surface that consumes substrate
that already ships in PR 7 + PR 8 + PR 9. The new mechanical
enforcement is PR-10-LOCAL Layer 2 read-only-interpretive
authority discipline (two regression-asserted walker tests
scoped to `_compare.py` only); the new comparator surface is
one function (`compare_records`); the new data shapes are one
`TypeAlias` (`DivergenceReport`) + one exception class
(`ComparatorInputError`).

**Out of scope** (per framing §7 non-acquisition commitments,
reproduced as spec-level rejections):

1. **Persisting divergence reports.** No third `record_kind`,
   no sidecar artifact, no comparator-authored persistence per
   framing §5.3 + §7 item 1. The comparator returns a pure
   value; persistence is the caller's concern, deferred to
   future scope.
2. **Mutating observation or expectation records.** Per
   PR-10-LOCAL binding statement + framing §5.6 + §7 item 2.
   The comparator is structurally incapable of mutation; tests
   assert mechanically.
3. **Triggering upstream emission.** `_compare.py` imports zero
   emission helpers; the 4th walker enforces the closure per
   framing §4.4 + §7 item 3. A future PR proposing to inline
   an `emit_*` call inside the comparator is rejected at the
   walker mechanically.
4. **Batching records or orchestrating iteration.** Pair-input
   is locked per framing §5.2 + §7 item 4. Caller handles the
   join (3-line dict-comprehension boilerplate per framing
   §2.1). A future PR proposing `compare_corpus(records: list)
   -> dict[fixture_id, DivergenceReport]` is rejected at the
   spec layer.
5. **Authoring cross-surface comparator semantics.** Path B
   locked at Gate 3 framing §5.1 + §5.2 per framing §7 item 5.
   The comparator's scope is intentionally bounded to a single
   operational arbitration surface (chat-handler at PR 10).
   Cross-surface semantics are intentionally unbound pending
   dedicated framing review (not rejected — see the cross-
   surface unbinding clarification in §0).
6. **Modifying the PR 9 three-fixture corpus.** Per framing §7
   item 6. PR 10 unit tests build records in-memory from
   fixture data (`FIXTURE["fixture_id"]`, `FIXTURE["prompt"]`,
   `FIXTURE["expected_narrow"]`); the fixture modules
   themselves are untouched.
7. **Modifying the three-authority-surface partition.** Per
   framing §7 item 7. The observation / dispatch-provenance /
   authored-expectation surfaces preserve unchanged. PR 10
   consumes all three through their persisted records, speaks
   on behalf of none.
8. **Modifying the PR-INTERNAL three-way authority partition.**
   Per framing §7 item 8 + framing §3.9. PR 8's sub-partition
   (authored expectation semantics / orchestration semantics /
   persistence topology) preserves unchanged.
9. **Touching the Layer 3 lint** (`test_pr6_visual_asymmetry.
   py`). Per framing §7 item 9. The comparator is not an
   emission surface.
10. **Modifying `divergence_capture_enabled()` or its env-gate.**
    Per framing §7 item 10. Carrier #5 protection preserves.
11. **Extending `KNOWN_SOURCE_VALUES`.** Per framing §7 item 11.
12. **Extending `_KNOWN_RECORD_KINDS`.** Per framing §7 item 12.
    Two-element set locked per PR 7 spec §7 close conditions.
13. **Modifying the expectation record schema.** Per framing §7
    item 13. Three required keys (`fixture_id`, `prompt`,
    `expected_narrow`) locked.
14. **Modifying `forge_bridge.__all__`.** Per framing §5.7 + §7
    item 14. Stays at 19 symbols. The comparator surface
    (`compare_records`, `DivergenceReport`, `ComparatorInputError`)
    is corpus-internal at PR 10. Promotion to `__all__` is a
    framing-level decision deferred to PR 11 / Gate 4 if a
    concrete external consumer surfaces.
15. **Authoring new cleanup-pressure-resistance class members
    speculatively.** Per framing §6 + §7 item 15. PR 10
    framing names three forms likely to surface (helper
    merger, persistence creep, walker abstraction); new class
    members register at PR 10 close based on actual pressure
    encountered, not predicted pressure.
16. **Promoting candidate carrier #16 to active.** Per framing
    §7 item 16. Promotion gates on Gate 3 close evaluation
    (PR 11) per Gate 3 framing §6.1. PR 10 contributes
    Gate-3-LOCAL form travel as corroboration substrate; the
    spec language must NOT write *"17 active carriers"* or
    *"carriers #1–#17"*.
17. **Shipping a join helper or batch-orchestration function.**
    Per framing §5.2 + §7 item 17. Pair-input is locked. PR 12
    may revisit if join boilerplate proliferates across 4+
    call sites — observation-driven, not speculation-driven.
18. **Generalizing the 4th walker into a parametrized base
    class.** Per framing §3.3 + Gate 2 close §1.6 + §2.4 item
    5 + framing §7 item 18. Walker unification rejected.
    *"Shared AST mechanics do not imply shared ontology."*
19. **Using cross-surface vocabulary in field names or
    docstrings.** Per framing §3.5 + §7 item 19. Field names
    like `task_outcome`, `prompt_resolution`, `semantic_match`
    rejected at PR 10 implementation review.
20. **Implementing a `DivergenceReport` shape that loses
    authorship.** Per framing §7 item 20 + carrier #17.
    Reducing to `{matched: bool}` without preserving observed-
    vs-expected partition rejected at spec layer.

---

## 3. The seven risks → named tests

PR 10's risk topology differs from PR 7's, PR 8's, and PR 9's.
PR 7 was substrate plumbing (risks: substrate eroding under
cleanup pressure). PR 8 was boundary work (risks: new authority
surface blurring against existing surfaces). PR 9 was integration
work (risks: the integration not actually exercising what it
claims to exercise). **PR 10 is interpretive read-surface
work** — the risks are *the comparator silently coercing one or
both surfaces before comparison*, *the comparator acquiring
emission/persistence authority under cleanup pressure*, *the
output shape losing the authorship partition*, and *the function
mutating its inputs through aliased references in the return
value*.

Seven risks. Five map to named tests in
`test_pr10_comparator.py` (3 unit + 2 authorship); two map to
named tests in `test_pr10_comparator_discipline.py` (the 4th
walker tests).

| # | Risk | Mitigation |
|---|---|---|
| 1 | Comparator fails to detect divergence when observation and expectation actually agree (single-survivor case) | Test 1 (`test_compare_records_single_survivor_no_divergence`) builds the single-survivor fixture's expected/observed pair in-memory; asserts the returned report has `divergence.narrow_diverged == False` + the correct per-surface contributions. |
| 2 | Comparator fails to detect divergence when observation and expectation actually agree (multi-match case — list-ordering preservation under carrier #10) | Test 2 (`test_compare_records_multi_match_no_divergence`) builds the multi-match fixture's pair; asserts list-equality on the 2-element `narrower.decision` / `expected_narrow` is order-preserving (carrier #10's "filtered list verbatim" requirement); divergence is False. |
| 3 | Comparator fails to surface the authored/observed divergence on the no-keyword-match fixture (Gate 4 unblock proof's behavioral payoff) | Test 3 (`test_compare_records_no_keyword_match_divergence`) builds the no-keyword-match pair (`expected_narrow=[]` vs. `observed_narrow=` full 4-tool fallback); asserts `divergence.narrow_diverged == True` + the report's `expectation.expected_narrow == []` + `observation.observed_narrow` carries all four tools verbatim. The load-bearing PR 9-authored divergence proof case. |
| 4 | Comparator silently mutates one or both input records through aliased list references in the return value (PR-10-LOCAL violation) | Test 4 (`test_compare_records_does_not_mutate_inputs`) builds a pair; takes `copy.deepcopy(...)` of both records before invocation; asserts `record == deepcopy_pre_invocation` after. Asserts the comparator structurally cannot mutate. |
| 5 | Comparator silently sorts `narrower.decision` or `expected_narrow` before comparison, masking authentic ordering divergence (§4.2 binding behavioral commitment violation) | Test 5 (`test_compare_records_does_not_sort_inputs`) builds a pair where `observation_record["narrower"]["decision"]` and `expectation_record["expected_narrow"]` contain identical multi-element lists in DIFFERENT orderings (e.g., `["a", "b"]` vs. `["b", "a"]`); asserts the returned report has `divergence.narrow_diverged == True`. The mechanical assertion that closes cleanup-pressure form #5 at the function body. |
| 6 | `_compare.py` silently acquires forbidden imports, eroding read-only-interpretive authority discipline | Tests A + B in `test_pr10_comparator_discipline.py` mechanically enforce: A (`test_compare_permitted_imports_value_locked`) — frozenset value-lock regression at zero symbols; B (`test_compare_module_references_subset_of_permitted_imports`) — walker enforcement against `_compare.py`. |
| 7 | `_compare.py` acquires read-only-interpretive authority but the 4th walker silently expands target set to multiple files (parallel-not-extension boundary violation) | Test B (above) is target-scoped to `_compare.py` only; framing §3.3 + spec §4.2.4 enforce parallel-not-extension at the walker target-set level. Verification checklist item at Step 5 (§6) confirms the walker's `_COMPARE_TARGET` constant points exclusively to `_compare.py`. |

Risk #7 is structural (no named test required — the walker's
target-set is value-locked in the same way the frozenset is).
Verification at Step 5 confirms target-set integrity against
the post-PR-10 codebase.

Verification checklist items mitigating non-test risks:

| Item | Risk | Mitigation |
|---|---|---|
| Carrier travel verification | Carriers #1–#15 + #17 + Gate-3-LOCAL form + binding clarifications + proactive scope guardrail + §4.2 binding behavioral commitment + PR-10-LOCAL binding statement don't actually land verbatim | Step 5 verifier reads each module's docstring; cross-references each verbatim block against §0. Surfaces drift before close commit. The Gate-3-LOCAL form travel through ≥3 PR 10 surfaces is the Gate 3 close evaluation prerequisite (framing §9 condition 7). |
| Regression contract | PR 4 / PR 6 / PR 7 / PR 8 / PR 9 test surfaces regress silently due to PR 10 additions | Step 5 verifier runs full `pytest tests/corpus/` and confirms 214 collected forge env (207 PR 9 baseline + 7 PR 10 new). Per-module assertions: PR 4 walker passes unchanged; PR 6 Layer 3 lint passes unchanged; PR 8 walker passes unchanged; PR 9 walker passes unchanged; PR 9 integration tests pass unchanged. |
| Architectural success signal | A future PR or PR 10 implementation modifies a production source file outside `_compare.py` | Step 5 verifier runs `git diff --stat <pre-PR-10-base>..HEAD -- forge_bridge/` and confirms only one file modification: addition of `forge_bridge/corpus/_compare.py`. Any other production source diff is a red flag per framing §9 condition 11. |
| `__all__` drift | A future PR speculatively promotes `compare_records` / `DivergenceReport` / `ComparatorInputError` to `forge_bridge.__all__` during PR 10 implementation | PR 8's existing `test_pr8_helpers_remain_corpus_internal` test continues to enforce against `emit_seed_expectation` + `drive_seed_fixture`; Step 5 verifier confirms it passes. PR 10 does NOT add an additional `__all__` drift guard test for the comparator symbols (the existing one covers the pattern; promotion of any new corpus symbol routes through framing review). |

---

## 4. Module surface

### 4.1 `forge_bridge/corpus/_compare.py` (new — the comparator helper)

**Path:** `forge_bridge/corpus/_compare.py`

**Purpose:** The pair-input pure-functional comparator. Consumes
one observation record + one expectation record, validates their
joinability through authority-class pre-checks, and produces a
structured `DivergenceReport` dict preserving each authority
surface's authored contribution explicitly. Read-only-
interpretive authority surface per framing §4.1.

#### 4.1.1 Module-level docstring structure (relevance-by-file ordering)

The docstring is structured top-down with carrier #17 + Gate-3-
LOCAL form + proactive scope guardrail + PR-10-LOCAL binding
statement + cross-surface unbinding clarification landing at the
**top** of the carrier block (per framing §4.1 — these are the
most-relevant governance for `_compare.py` specifically; the
inherited carriers #1–#15 land after). The §4.2 binding
behavioral commitment travels at the FUNCTION docstring not the
module docstring (it governs the function body specifically).

**Docstring outline (top-down):**

1. One-line module purpose.
2. **Carrier #17 verbatim** (top of carrier block — the
   architectural commitment this module enacts).
3. **Gate-3-LOCAL governing sentence verbatim** with explicit
   *candidate carrier #16 corroboration substrate* marking.
4. **Proactive scope guardrail verbatim** (framing §3.5).
5. **PR-10-LOCAL binding statement verbatim** (framing §5.6).
6. **Cross-surface unbinding clarification verbatim** (Gate 3
   framing §6.2).
7. **Inherited carriers #1–#15** verbatim from the canonical
   source (`_capture.py:6–135` + `_seed.py:19–135`). Cite
   canonical source explicitly.
8. **Gate 2 binding framing clarification** (call-site-owned
   arbitration inputs) verbatim.
9. The PR-N-LOCAL non-regeneration note (PR-7-LOCAL +
   PR-8-LOCAL + PR-9-LOCAL + PR-10-LOCAL pair pattern).
10. Implementation contract reference: "See
    `A.5.3.2-PR10-SPEC.md` §4.1 for the contract this module
    implements."

#### 4.1.2 Module-level imports

```python
from __future__ import annotations

from typing import Any, TypeAlias
```

**Why exactly these imports — no others:**

- `from __future__ import annotations` — matches every other
  corpus module's style (`_capture.py`, `_seed.py`, `_schema.py`,
  `reader.py`). Postponed evaluation of annotations.
- `Any` — for `DivergenceReport: TypeAlias = dict[str, Any]`.
- `TypeAlias` — for the same.

**No speculative imports.** Specifically: `import copy` is NOT
imported at PR 10. The §4.1.6 reference implementation uses
`list(...)` for fresh list allocation; `copy.deepcopy(...)` is
used only by the test module (§4.3.1) for the mutation-invariant
assertion in test 4 — that import lives in
`tests/corpus/test_pr10_comparator.py`, not in production.

A "reserved" `import copy  # noqa: F401` in the production
module would be a speculative import — designing for a
hypothetical future need rather than the current
implementation. Speculative imports conflict with the §4.2
binding behavioral commitment ("compare as persisted") + the
PR-10-LOCAL binding statement (the function does what its
signature claims; no held-back capability). If a future
authorship-preservation implementation needs `copy.deepcopy`,
that's an incarnation-time decision routed through the §4.1.7
amendment trigger language (the same routing that gates
schema-constant admission). No reserved imports.

**Zero imports from `forge_bridge.corpus`.** This is the
load-bearing property the 4th walker enforces. The comparator
validates `record_kind` against the string literals
`"observation"` and `"expectation"` directly; it does NOT import
`_KNOWN_RECORD_KINDS` from `_schema.py`. Rationale at §4.1.4.

#### 4.1.3 Module-level public symbols

Three symbols:

1. `DivergenceReport: TypeAlias = dict[str, Any]` — vocabulary
   anchor for callers.
2. `class ComparatorInputError(ValueError)` — exception type.
3. `def compare_records(...) -> DivergenceReport` — the
   comparator function.

No private symbols beyond what Python's import semantics treat
as private (`_*` names). No module-level mutable state. No
classes beyond `ComparatorInputError`. No module-level
constants beyond `DivergenceReport`.

#### 4.1.4 `DivergenceReport` TypeAlias

```python
DivergenceReport: TypeAlias = dict[str, Any]
"""Per-surface nested dict shape preserving authorship.

Structural shape (verbatim — exact field names are part of the
contract):

    {
        "fixture_id": str,
        "expectation": {
            "expected_narrow": list[str],
        },
        "observation": {
            "observed_narrow": list[str],
        },
        "divergence": {
            "narrow_diverged": bool,
        },
    }

The three sub-dict keys (``expectation``, ``observation``,
``divergence``) structurally enforce the three-authority-surface
partition per carrier #17. The ``divergence`` key's value is the
comparator's interpretive claim; the ``expectation`` and
``observation`` keys' values are the surface contributions the
claim is derived from.

A single dict access (``report["divergence"]``) gives the
comparator's whole verdict; another single access
(``report["expectation"]`` or ``report["observation"]``) gives
the surface contribution that informed it.

Per framing §4.3, the TypeAlias is the chosen shape posture
(option (a) — per-surface nested dict). Options (b) flat-prefix-
naming and (c) frozen dataclass were rejected at framing per
§4.3 reasoning (b is fragile to spec amendments; c adds typing
ceremony without adding carrier #17 protection).

The TypeAlias resolves to plain ``dict[str, Any]`` — no typing
enforcement beyond the IDE-discoverability of the alias name.
Future contributors proposing to tighten the alias into a
``TypedDict`` or ``Protocol`` are rejected at the spec layer
per framing §4.3 (c)-rejection + carrier #17 (the typing
ceremony doesn't add protection; the field-naming discipline +
the function-body construction discipline + the unit tests are
what enforce the shape).
"""
```

**Field-name lock (verbatim):**

| Field path | Type | Source |
|---|---|---|
| `fixture_id` | `str` | Both records share this value (validated equal at function entry); the report's top-level `fixture_id` value is the shared identifier verbatim |
| `expectation.expected_narrow` | `list[str]` | Fresh-allocated copy of `expectation_record["expected_narrow"]` (preserves contents + order; new list identity) |
| `observation.observed_narrow` | `list[str]` | Fresh-allocated copy of `observation_record["narrower"]["decision"]` (preserves contents + order; new list identity) |
| `divergence.narrow_diverged` | `bool` | `True` iff `observed_narrow != expected_narrow` (list-equality, NOT set-equality; carrier #10's "filtered list verbatim" requirement makes ordering meaningful) |

**Field-naming discipline (load-bearing):**

- The `expectation.*` and `observation.*` sub-dicts use the
  prefix discipline `expected_*` / `observed_*` for the surface
  contribution field. Symmetric naming makes the per-surface
  partition structurally visible at the field-name level *as
  well as* the dict-structure level (double redundancy of
  carrier #17 protection).
- The `divergence.*` sub-dict uses the suffix discipline
  `*_diverged` for the comparator's interpretive claims. The
  prefix asymmetry between surface contributions (`expected_` /
  `observed_`) and comparator claims (`*_diverged`) makes the
  authority-class distinction structurally visible.
- **No cross-surface vocabulary.** Field names like
  `task_outcome`, `prompt_resolution`, `semantic_match`,
  `chain_step_result` are rejected per framing §3.5 + proactive
  scope guardrail.

#### 4.1.5 `ComparatorInputError(ValueError)` exception

```python
class ComparatorInputError(ValueError):
    """Raised when caller misuses the comparator's authority-class
    contract.

    The comparator validates four authority-class boundaries at entry:

    1. ``observation_record`` must be a ``dict``.
    2. ``expectation_record`` must be a ``dict``.
    3. ``observation_record["record_kind"] == "observation"``.
    4. ``expectation_record["record_kind"] == "expectation"``.
    5. ``observation_record["fixture_id"] == expectation_record["fixture_id"]``
       (both non-None).
    6. ``observation_record["narrower"]["decision"]`` exists +
       is a list.
    7. ``expectation_record["expected_narrow"]`` exists + is a
       list.

    Any of these failing raises ``ComparatorInputError``. The
    exception subclasses ``ValueError`` so callers catching
    ``ValueError`` for general input-validation reasons get this
    one too; subclassing lets discriminating callers catch the
    comparator-specific case explicitly.

    Distinct from ``forge_bridge.corpus._schema.SchemaValidationError``:
    the schema validator enforces *whether a record is a structurally
    valid record* (universal keys + record_kind-conditional fields);
    ``ComparatorInputError`` enforces *whether the caller passed
    records of the correct authority class to the comparator
    function*. The records may be schema-valid yet still misused
    at the comparator (right schema, wrong authority class for
    the parameter — e.g., two observation records passed where
    the comparator expects an observation + expectation pair).

    Future contributors must not collapse ``ComparatorInputError``
    into ``SchemaValidationError`` or vice versa — the two enforce
    different boundaries and the comparator's boundary is
    authority-class, not schema. Distinct exception types
    preserve the discriminability at the catch-site.
    """
```

**Why a new exception type (and not `ValueError` directly):**

- Callers catching `ValueError` for unrelated reasons (e.g., bad
  command-line arg parsing, malformed user input) would
  accidentally swallow comparator misuse signals.
- Callers catching `SchemaValidationError` already know the
  failure is at the schema layer; the comparator's failure is
  one layer further (the caller's authority-class wiring).
- Subclassing `ValueError` honors the framing §4.2 "Raises:
  ValueError" promise without losing discriminability.
- Pattern matches PR 7's `SchemaVersionMismatch(ValueError)` —
  a distinct subclass for a distinct failure mode that callers
  may want to catch separately.

#### 4.1.6 `compare_records` function

**Signature (locked):**

```python
def compare_records(
    observation_record: dict,
    expectation_record: dict,
) -> DivergenceReport:
```

- **Positional-only? Keyword-only? Plain positional?** — Plain
  positional. The framing example uses positional. The two
  parameter names are descriptive enough that callers reading
  `compare_records(obs, exp)` understand which goes where; the
  reverse order (`compare_records(exp, obs)`) is caught at entry
  by the `record_kind` validation. Asymmetric parameter names
  (`observation_record`, `expectation_record`) plus asymmetric
  in-function validation makes positional-arg misuse loud (raises
  `ComparatorInputError`), not silent.
- **No default values.** Per framing §5.2 — "NOT optional-arg
  with default fallback." Both inputs are required.

**Docstring outline (top-down):**

```python
def compare_records(
    observation_record: dict,
    expectation_record: dict,
) -> DivergenceReport:
    """Compare a single observation record against its companion
    expectation record. Return a structured divergence report
    naming each authority surface's contribution explicitly.

    [Carrier #17 verbatim — relevance at top per framing §4.1.]

    [Proactive scope guardrail verbatim — framing §3.5.]

    [§4.2 binding behavioral commitment verbatim — "compare as
    persisted."]

    [PR-10-LOCAL binding statement verbatim — framing §5.6.]

    Args:
        observation_record: a dict with ``record_kind == "observation"``
            — the runtime observation authored by
            ``emit_divergence_capture`` under
            ``seed_dispatch_scope``. Must contain
            ``record_kind="observation"``,  a non-None
            ``fixture_id``, and a ``narrower`` sub-dict carrying
            ``decision`` (list[str]).
        expectation_record: a dict with ``record_kind == "expectation"``
            — the authored expectation declared by
            ``emit_seed_expectation``. Must contain
            ``record_kind="expectation"``, a non-None
            ``fixture_id`` equal to ``observation_record["fixture_id"]``,
            and ``expected_narrow`` (list[str]).

    Returns:
        A ``DivergenceReport`` (typed alias for ``dict[str, Any]``)
        with the four-key structural shape (``fixture_id``,
        ``expectation``, ``observation``, ``divergence``) preserving
        authorship. The lists inside ``expectation.expected_narrow``
        and ``observation.observed_narrow`` are FRESH allocations
        — mutation of the report does not propagate back into the
        input records.

    Raises:
        ComparatorInputError: on any of the seven authority-class
            boundary violations enumerated in
            ``ComparatorInputError``'s docstring (records not dicts,
            wrong ``record_kind``, ``fixture_id`` mismatch or None,
            missing required fields, wrong field types).
    """
```

**Implementation (reference body):**

```python
def compare_records(
    observation_record: dict,
    expectation_record: dict,
) -> DivergenceReport:
    # ── Authority pre-check 1: type ──────────────────────────────
    if not isinstance(observation_record, dict):
        raise ComparatorInputError(
            f"observation_record must be a dict, got "
            f"{type(observation_record).__name__}"
        )
    if not isinstance(expectation_record, dict):
        raise ComparatorInputError(
            f"expectation_record must be a dict, got "
            f"{type(expectation_record).__name__}"
        )

    # ── Authority pre-check 2: record_kind ───────────────────────
    obs_kind = observation_record.get("record_kind")
    if obs_kind != "observation":
        raise ComparatorInputError(
            f"observation_record must have "
            f"record_kind='observation'; got record_kind={obs_kind!r}"
        )
    exp_kind = expectation_record.get("record_kind")
    if exp_kind != "expectation":
        raise ComparatorInputError(
            f"expectation_record must have "
            f"record_kind='expectation'; got record_kind={exp_kind!r}"
        )

    # ── Authority pre-check 3: fixture_id joinability ────────────
    obs_fid = observation_record.get("fixture_id")
    exp_fid = expectation_record.get("fixture_id")
    if obs_fid is None or exp_fid is None:
        raise ComparatorInputError(
            f"fixture_id must be non-None on both records; got "
            f"observation_record fixture_id={obs_fid!r}, "
            f"expectation_record fixture_id={exp_fid!r}"
        )
    if obs_fid != exp_fid:
        raise ComparatorInputError(
            f"fixture_id mismatch: observation_record carries "
            f"{obs_fid!r}, expectation_record carries {exp_fid!r}"
        )

    # ── Authority pre-check 4: required-field shapes ─────────────
    narrower = observation_record.get("narrower")
    if not isinstance(narrower, dict):
        raise ComparatorInputError(
            "observation_record missing required field "
            "'narrower' (dict)"
        )
    obs_decision = narrower.get("decision")
    if not isinstance(obs_decision, list):
        raise ComparatorInputError(
            "observation_record missing required field "
            "'narrower.decision' (list[str])"
        )
    exp_narrow = expectation_record.get("expected_narrow")
    if not isinstance(exp_narrow, list):
        raise ComparatorInputError(
            "expectation_record missing required field "
            "'expected_narrow' (list[str])"
        )

    # ── Compare-as-persisted divergence computation ──────────────
    # Direct list-equality. NO sort, NO canonicalization, NO
    # semantic coercion. Per §4.2 binding behavioral commitment.
    # Carrier #10's "filtered list verbatim" makes ordering
    # meaningful — list-equality preserves it.
    narrow_diverged = obs_decision != exp_narrow

    # ── Report construction — fresh-allocated lists ──────────────
    # Fresh list allocation per PR-10-LOCAL binding statement:
    # mutation of the report does not propagate into the input
    # records. ``list(...)`` is one-level copy (sufficient — the
    # list elements are strings, immutable).
    return {
        "fixture_id": obs_fid,
        "expectation": {
            "expected_narrow": list(exp_narrow),
        },
        "observation": {
            "observed_narrow": list(obs_decision),
        },
        "divergence": {
            "narrow_diverged": narrow_diverged,
        },
    }
```

**Implementation discipline locked at spec layer:**

- **Direct `!=` comparison** on `obs_decision` and `exp_narrow`.
  No `set(obs_decision) != set(exp_narrow)`. No `sorted(...)
  != sorted(...)`. No `[s.lower() for s in ...] != [...]`.
  Per §4.2 binding behavioral commitment's four operational
  rejections.
- **Fresh list allocation** for the report's contained lists.
  `list(exp_narrow)` and `list(obs_decision)` create new list
  identities; the input records' list values remain referenced
  by their original containers exclusively. Per PR-10-LOCAL.
- **No deep-copy of records.** The comparator does not call
  `copy.deepcopy(...)`. Inputs are read but never modified;
  only the contained lists that flow into the report are
  copied. Per PR-10-LOCAL "the inputs are read but never
  modified."
- **`isinstance(..., dict)` checks for the record-level
  containers** and `isinstance(..., list)` for the field-level
  values. `.get(key)` returns `None` for missing keys; the
  missing-field branch raises `ComparatorInputError`.
- **No `assert` statements.** Validation uses explicit `raise`.
  `assert` is stripped under `-O` Python; the validation must
  be load-bearing at all optimization levels.

#### 4.1.7 Why zero `forge_bridge.corpus.*` imports

The reference implementation uses **string literals** for
`record_kind` comparison (`"observation"`, `"expectation"`) and
**dict-path traversal** for field access (`record["narrower"]
["decision"]`). Neither requires importing from
`forge_bridge.corpus`. Specifically:

- `_KNOWN_RECORD_KINDS` from `_schema.py` is NOT imported.
  String literals are sufficient — the comparator's authority-
  class check is structurally tied to the two specific values
  `"observation"` and `"expectation"` (not the set membership).
  A future schema change introducing a third `record_kind`
  would NOT make the comparator silently accept it; the
  comparator's literal-comparison check would still raise on
  the new value (per the framing §3.5 proactive scope guardrail
  + the cross-surface unbinding clarification — a third
  `record_kind` is a new authority surface requiring framing-
  level review of the comparator's scope).
- `_REQUIRED_OBSERVATION_KEYS` / `_REQUIRED_EXPECTATION_KEYS`
  from `_schema.py` are NOT imported. The comparator does NOT
  enumerate all required keys — it checks only the specific
  fields it consumes (`narrower.decision`, `expected_narrow`).
  Full-schema validation is the schema validator's job (called
  by emitters at persistence time, not by the comparator at
  read time).
- `reader.py` is NOT imported. The comparator takes records as
  function arguments, not as reader-yielded iterators. The
  caller (PR 11 / Gate 4 / future-gate work) reads the records;
  the comparator computes divergence on a single pair.

**Amendment trigger language (load-bearing):**

If incarnation-time implementation surfaces a need to import a
`forge_bridge.corpus.*` constant for validation (e.g., the
implementer prefers `_KNOWN_RECORD_KINDS` over string literals
for record_kind comparison, or chooses to enumerate
`_REQUIRED_EXPECTATION_KEYS` for the missing-field check),
**`_COMPARE_PERMITTED_IMPORTS` MUST be updated to admit the
specific symbol(s)** and the framing amendment discipline
applies per `A.5.3.2-PR9-SPEC.md` §4.7 amendment-at-incarnation
taxonomy.

The amendment is **NOT a cleanup-PR-layer change**. Admitting a
schema-constant import to `_COMPARE_PERMITTED_IMPORTS` is a
framing-level decision because it admits a participation channel
between the comparator and the schema authority. The framing
review evaluates:

1. Whether the imported symbol's value is genuinely a
   universal-truth-class lock (e.g., `_KNOWN_RECORD_KINDS` is —
   the two-element set is locked at framing per PR 7 spec §7
   close conditions; the comparator importing it inherits the
   lock).
2. Whether the import introduces an unintended coupling
   direction (e.g., a future schema change would force a
   comparator change, vs. the current literal-comparison
   approach where the comparator stays stable under schema
   evolution).
3. Whether the import erodes the read-only-interpretive
   authority discipline (e.g., importing a `validate_*` helper
   from `_schema.py` would smuggle schema-validation authority
   into the comparator — rejected).

The amendment trigger language prevents silent permission creep
from an implementation shortcut that imports a schema constant
"just for validation." Any such import surfaces the framing
review explicitly.

**Default disposition: zero imports.** The reference
implementation above uses string literals + dict-path traversal;
the framing-time + spec-time analysis is that this is sufficient.
The amendment trigger exists as a safety valve, not an
expectation.

### 4.2 `tests/corpus/test_pr10_comparator_discipline.py` (new — 4th Layer 2 walker)

**Path:** `tests/corpus/test_pr10_comparator_discipline.py`

**Purpose:** The 4th Layer 2 walker module. Houses
`_COMPARE_PERMITTED_IMPORTS` (value-locked frozenset, **zero
symbols** at PR 10) + `_compare_corpus_references()` AST walker
+ 2 discipline tests (value-lock + walker subset-enforcement).

**Explicitly NOT** an extension of `test_pr4_participation_creep.
py`, `test_pr8_seed_surface.py`, or `test_pr9_fixture_discipline.
py` — distinct ontology. Shared AST mechanics do not imply
shared ontology.

#### 4.2.1 Four-walker partition (spec-level, parallel-not-extension)

At PR 10 close, **four** Layer 2 AST walkers operate against
the codebase. Each protects a distinct ontology. The protections
are partitioned, not unified:

| Walker | Target | Ontology | Rejection rule |
|---|---|---|---|
| PR 4 | narrowing-subsystem source files | production import topology | one-directional flow (narrowing-subsystem → corpus is rejected) |
| PR 8 | `_seed.py` | orchestration participation discipline | 5-symbol bounded toolbox (semantics-not-cardinal); persistence-topology authority rejected |
| PR 9 | fixture directory glob | declarative fixture-data discipline | single-symbol-gate (`drive_seed_fixture` only) |
| **PR 10 (new)** | `_compare.py` | **read-only-interpretive authority** | **zero-symbol-gate at PR 10**; emission/persistence/orchestration imports rejected |

The four walkers share AST mechanics (each uses `ast.walk` +
import-node traversal); they DO NOT share ontology.
Generalization would require unifying their target-set
semantics + their admission ontologies + their rejection-
message shapes + their future evolution pressure — which
collapses four protections into one rejection surface.

**Future "walker unification" cleanup proposals are rejected
at the spec layer** per framing §3.3 + §8.2 + Gate 2 close §1.6
+ §2.4 item 5 + this section. A unified walker abstraction is
appealing locally (deduplication of AST traversal code) but
architecturally erodes four distinct protections. Each walker
stays local to its ontology.

**Shared AST mechanics do not imply shared ontology.**

#### 4.2.2 Top-level structure

```python
"""PR-10-local Layer 2 read-only-interpretive authority discipline.

[Carrier #17 verbatim — relevance at top per framing §4.1.]

[Gate-3-LOCAL governing sentence with *candidate carrier #16
corroboration substrate* marking.]

[The four-walker partition rationale paragraph — see §4.2.1.]

[Closing sentence: "Shared AST mechanics do not imply shared
ontology."]

[Inherited carriers #1–#15 + Gate 2 binding framing clarification
— cited by reference to the canonical source (_seed.py:19–135),
not regenerated verbatim. The PR 10 walker module is one layer
removed from the production authority surfaces; carrier travel
discipline here is reduced relative to fixture modules per
framing §4.1's "abbreviated where the carriers themselves are
not load-bearing for _compare.py specifically."]

PR 10 governing sentence (framing-artifact-scoped per
A.5.3.2-PR10-FRAMING.md §0 + Gate 3 framing §6.1):

  Gate 3 proves topology, not infrastructure.

This module operationalizes the governing sentence at the
Layer 2 read-only-interpretive authority surface: the frozenset
value-locks at ZERO symbols (admitting any symbol erodes the
zero-symbol-gate; framing amendment discipline applies per
A.5.3.2-PR10-SPEC.md §4.1.7), and the walker target-set is
exclusively `_compare.py` (admitting any other target would
erode the parallel-not-extension protection).
"""
from __future__ import annotations

import ast
import pathlib

import forge_bridge


# Layer 2 read-only-interpretive authority constant —
# value-locked at ZERO symbols. Admission to this frozenset
# requires framing-level review per
# A.5.3.2-PR10-SPEC.md §4.1.7 amendment trigger language.
_COMPARE_PERMITTED_IMPORTS: frozenset[str] = frozenset()


# Target file for the walker. Lives at module scope so the
# value-lock test + the subset-enforcement test share the same
# target reference.
_COMPARE_TARGET = pathlib.Path(
    forge_bridge.__file__
).parent / "corpus" / "_compare.py"


def _compare_corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

    Mirrors the AST mechanics of
    ``tests/corpus/test_pr8_seed_surface.py::_corpus_references``
    and
    ``tests/corpus/test_pr9_fixture_discipline.py::_fixture_corpus_references``
    — scoped to a different target (``_compare.py``) and a
    different protected ontology (read-only-interpretive
    authority vs. orchestration-participation vs. fixture-data-
    discipline). Shared AST mechanics do not imply shared
    ontology.

    Walks the AST for ``ImportFrom`` and ``Import`` nodes;
    records dotted symbol forms for any
    ``from forge_bridge.corpus.<submodule> import <symbol>``
    and any direct ``import forge_bridge.corpus.<submodule>``.
    Both syntactic forms are captured for completeness; at PR 10
    close ``_compare.py`` carries zero ``forge_bridge.corpus.*``
    imports of either form, so both branches exercise vacuously.

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected (AST
    walks only ``Import`` / ``ImportFrom`` nodes), matching the
    "import-target, not text-occurrence" semantic the discipline
    requires.
    """
    refs: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "forge_bridge.corpus":
                for alias in node.names:
                    refs.append(f"forge_bridge.corpus.{alias.name}")
            elif module.startswith("forge_bridge.corpus."):
                for alias in node.names:
                    refs.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name == "forge_bridge.corpus"
                    or alias.name.startswith("forge_bridge.corpus.")
                ):
                    refs.append(alias.name)
    return refs


def test_compare_permitted_imports_value_locked() -> None:
    """Frozenset value-lock regression.

    The frozenset MUST equal exactly the empty frozenset:

        frozenset()

    Cardinality is exactly 0 at PR 10. Any future PR adding a
    symbol must amend the spec + framing first per
    A.5.3.2-PR10-SPEC.md §4.1.7 amendment trigger language —
    the zero-symbol-gate IS the read-only-interpretive authority
    discipline at PR 10. The test asserts both cardinality AND
    exact set membership.
    """
    expected: frozenset[str] = frozenset()
    assert _COMPARE_PERMITTED_IMPORTS == expected, (
        "_COMPARE_PERMITTED_IMPORTS has drifted from the "
        "A.5.3.2-PR10-FRAMING.md §5.5 + A.5.3.2-PR10-SPEC.md "
        "§4.1.7 zero-symbol-gate lock. Expected exactly zero "
        "symbols.\n"
        f"Actual ({len(_COMPARE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {s}\n" for s in sorted(_COMPARE_PERMITTED_IMPORTS))
        + "Any admission of a symbol requires framing-level "
        "review per A.5.3.2-PR10-SPEC.md §4.1.7 amendment "
        "trigger language. The amendment evaluates whether the "
        "imported symbol erodes read-only-interpretive authority "
        "discipline (e.g., emission helpers, persistence "
        "helpers, orchestration surfaces — all rejected) vs. "
        "preserves it (e.g., a universal-truth-class lock like "
        "_KNOWN_RECORD_KINDS — conditionally admitted if the "
        "implementation chooses set-membership validation over "
        "string-literal validation)."
    )


def test_compare_module_references_subset_of_permitted_imports() -> None:
    """Walker subset-enforcement.

    ``forge_bridge/corpus/_compare.py`` is walked; every fully-
    qualified ``forge_bridge.corpus.<X>`` reference is collected;
    the collected set must be a SUBSET of
    ``_COMPARE_PERMITTED_IMPORTS`` (which is empty at PR 10).

    At PR 10 close: ``_compare.py`` carries zero
    ``forge_bridge.corpus.*`` imports (validation uses string
    literals + dict-path traversal per §4.1.4 reference
    implementation). The subset-enforcement holds vacuously
    (empty set is a subset of the empty set), which is the
    correct shape at PR 10.

    A future PR adding ``from forge_bridge.corpus._schema import
    _KNOWN_RECORD_KINDS`` to ``_compare.py`` (e.g., to replace
    string-literal validation with set-membership validation)
    fails the walker. The implementer must amend
    ``_COMPARE_PERMITTED_IMPORTS`` to admit the symbol AND
    route through framing review per A.5.3.2-PR10-SPEC.md
    §4.1.7.

    A future PR adding ``from forge_bridge.corpus._capture
    import emit_divergence_capture`` (the canonical
    helper-merger cleanup-pressure form per A.5.3.2-PR10-FRAMING.md
    §3.6 form #1) fails the walker structurally — the comparator
    is read-only-interpretive authority; emission helpers are
    rejected regardless of framing review.
    """
    assert _COMPARE_TARGET.exists(), (
        f"_compare.py expected at {_COMPARE_TARGET}. The PR-10-"
        f"local read-only-interpretive authority discipline test "
        f"cannot enforce its boundary if the file it walks is "
        f"gone. Either restore the file or amend this test's "
        f"path."
    )
    source = _COMPARE_TARGET.read_text(encoding="utf-8")

    offenders: list[str] = []
    for ref in _compare_corpus_references(source):
        if ref not in _COMPARE_PERMITTED_IMPORTS:
            offenders.append(ref)

    assert not offenders, (
        "PR-10-local read-only-interpretive authority discipline "
        "violated: _compare.py imports a corpus surface OUTSIDE "
        "the permitted set.\n"
        "\n"
        "comparator is interpretive read-only authority; "
        "emission/persistence imports are rejected at the spec "
        "layer. The 4th walker preserves the three-walker "
        "partition's parallel-not-extension boundary — "
        "read-only-interpretive ontology is distinct from "
        "production-import-topology, orchestration-participation, "
        "and fixture-data-discipline ontologies. Shared AST "
        "mechanics do not imply shared ontology.\n"
        "\n"
        f"Permitted ({len(_COMPARE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {p}\n" for p in sorted(_COMPARE_PERMITTED_IMPORTS))
        + "\n"
        "Offenders:\n"
        + "".join(f"  {ref}\n" for ref in offenders)
        + "\n"
        "If the import is genuinely required for validation "
        "(e.g., set-membership over _KNOWN_RECORD_KINDS), the "
        "admission decision is framing-level — route through "
        "framing review per A.5.3.2-PR10-SPEC.md §4.1.7 "
        "amendment trigger language. The amendment evaluates "
        "whether the imported symbol preserves read-only-"
        "interpretive authority or erodes it."
    )
```

#### 4.2.3 Test signature commitments (locked)

- **Test A** (`test_compare_permitted_imports_value_locked`) —
  names the frozenset value-lock regression mechanically; the
  assertion error message names §4.1.7 amendment trigger
  language explicitly + names the read-only-interpretive
  authority discipline rationale.
- **Test B** (`test_compare_module_references_subset_of_permitted_imports`)
  — walks `_compare.py` only (target is `_COMPARE_TARGET`, NOT
  a directory glob — the walker target-set is parallel-not-
  extension to PR 9's directory-glob target); enforces subset
  semantics; the assertion error message names the rejection
  message from framing §4.4 verbatim ("comparator is
  interpretive read-only authority...") + the offender
  references + the §4.1.7 amendment routing.
- The walker handles **both `ImportFrom` and `Import` node
  kinds** (mirrors PR 9 walker's defensive completeness — even
  though `import forge_bridge.corpus._capture as fb_cap` is
  rejected by the discipline, the walker captures it for
  mechanical completeness).
- The target-set is exclusively `_compare.py` (NOT a glob;
  NOT a directory walk). This is the parallel-not-extension
  boundary per §4.2.1.

#### 4.2.4 What this module does NOT contain

- A walker that targets `_seed.py` (PR 8's walker handles that;
  PR 10's walker target is `_compare.py` only).
- A walker that targets `_capture.py` or any other corpus
  source (PR 4's walker handles the production-source target;
  PR 8's walker handles `_seed.py`; PR 9's walker handles
  fixture modules).
- A walker that targets fixture modules under
  `tests/corpus/fixtures/` (PR 9's walker handles that).
- Helper functions beyond `_compare_corpus_references()`.
- Tests beyond the two discipline tests (the five comparator
  tests live in §4.3).
- An autouse fixture (no setup needed; the discipline tests
  are static AST walks).
- Imports from `forge_bridge.corpus` (the module imports only
  `forge_bridge` at top-level — to locate `_compare.py` via
  `forge_bridge.__file__` — and stdlib `ast` + `pathlib`).

### 4.3 `tests/corpus/test_pr10_comparator.py` (new — comparator behavioral tests)

**Path:** `tests/corpus/test_pr10_comparator.py`

**Purpose:** The comparator behavioral test module. Houses 5
named tests at PR 10 close: 3 unit tests (one per PR 9 fixture)
+ 2 authorship-preservation tests (mutation + sort). Per framing
§5.5 test count target (5–7 new tests at PR 10) + spec §3 risks
#1–#5.

**Conditional 6th test:** if PR 10 implementation introduces any
pre-comparison string processing (lowercasing, whitespace strip,
Unicode normalization, etc.), a 3rd authorship-preservation
test (`test_compare_records_does_not_canonicalize_inputs`) is
required and the test count amends from 5 to 6 at incarnation
per §4.3.3 conditional test language. The framing's 5–7 range
accommodates the conditional addition without exceeding the
upper bound (5 baseline + 1 conditional = 6 ≤ 7).

**Default disposition: 5 tests** (2 walker + 3 unit + 2
authorship = 7 PR 10 tests total). The reference implementation
at §4.1.6 uses direct `!=` comparison on the lists; no string
processing happens; the canonicalization vector is structurally
unreachable; the 3rd authorship test is unnecessary.

#### 4.3.1 Top-level structure

```python
"""PR 10 comparator behavioral tests — unit tests (one per
PR 9 fixture) + authorship-preservation tests (mutation + sort
rejection).

[Carrier #17 verbatim — relevance at top per framing §4.1.]

[Gate-3-LOCAL governing sentence with *candidate carrier #16
corroboration substrate* marking.]

[Proactive scope guardrail verbatim — framing §3.5.]

[Paraphrased PR-10-LOCAL binding statement: "tests assert the
comparator does not mutate its inputs and produces no side
effects."]

[Inherited carriers #1–#15 + Gate 2 binding framing clarification
— cited by reference to the canonical source (_seed.py:19–135)
+ to _compare.py module docstring. Not regenerated verbatim;
the comparator test module is one layer removed from authority
emission per framing §4.1 abbreviation discipline.]

Test inventory at PR 10 close:

  - test_compare_records_single_survivor_no_divergence (risk #1)
  - test_compare_records_multi_match_no_divergence (risk #2)
  - test_compare_records_no_keyword_match_divergence (risk #3)
  - test_compare_records_does_not_mutate_inputs (risk #4 /
    PR-10-LOCAL invariant)
  - test_compare_records_does_not_sort_inputs (risk #5 / §4.2
    binding behavioral commitment — sort-rejection vector)

Conditional 6th test (incarnation-time decision per
A.5.3.2-PR10-SPEC.md §4.3.3):

  - test_compare_records_does_not_canonicalize_inputs — REQUIRED
    if and only if PR 10 implementation introduces pre-comparison
    string processing. The §4.1.6 reference implementation uses
    direct list equality; the canonicalization vector is
    structurally unreachable; the test is omitted by default.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from forge_bridge.corpus._compare import (
    ComparatorInputError,
    DivergenceReport,
    compare_records,
)
from forge_bridge.corpus._schema import SCHEMA_VERSION

# PR 9 fixture data — re-used by reference, not modified.
from tests.corpus.fixtures.fix_single_survivor import FIXTURE as FIX_SINGLE
from tests.corpus.fixtures.fix_multi_match import FIXTURE as FIX_MULTI
from tests.corpus.fixtures.fix_no_keyword_match import FIXTURE as FIX_NO_KW
```

**Import discipline:**

- `from forge_bridge.corpus._compare import ...` — the
  comparator surface under test. Direct symbol imports
  (`compare_records`, `DivergenceReport`, `ComparatorInputError`).
- `from forge_bridge.corpus._schema import SCHEMA_VERSION` —
  needed to hand-craft minimum-shape observation/expectation
  records (matches PR 8 schema-test pattern at
  `test_pr8_seed_surface.py:288–320` `_minimum_valid_expectation_record`).
- `from tests.corpus.fixtures.fix_* import FIXTURE` — PR 9
  fixture data re-used as the source of fixture_id / prompt /
  expected_narrow values. The FIXTURE dicts themselves are
  data sources; the tests build full records (observation +
  expectation) in-memory by combining FIXTURE data with
  hand-crafted universal-key fields.
- `import copy` — for `copy.deepcopy(...)` in test 4
  (mutation-invariant assertion).
- `import pytest` — for test-function discovery + optional
  parametrize (unused at PR 10; reserved if conditional 6th
  test adds parametrize over canonicalization vectors).

**No imports from `forge_bridge.corpus._capture`,
`forge_bridge.corpus._seed`, `forge_bridge.corpus.reader`** —
the comparator tests do NOT drive emission helpers or
orchestration surfaces. The tests build records in-memory
directly (PR 8 schema-test pattern), not by invoking emission
infrastructure.

#### 4.3.2 Test signatures + body shape

**Helper (local to module):**

```python
def _build_observation_record(
    *,
    fixture_id: str,
    prompt: str,
    narrower_decision: list[str],
    pr20_condition_met: bool = False,
    collapse_occurred: bool = False,
    ambiguity_state: str = "multi_survivor",
) -> dict[str, Any]:
    """Build a minimum-shape valid observation record.

    Mirrors the pattern from
    ``tests/corpus/test_pr8_seed_surface.py::_minimum_valid_expectation_record``.
    Returns a dict carrying the 4 universal keys + the 6
    observation-required keys (source, prompt, candidate_set,
    topology, identity, narrower) + ``fixture_id`` (always
    present on observation records per PR 7 §4.3 Q3 structural-
    uniformity decision).

    The defaults align with the multi-match arbitration outcome
    by default; callers override per test.

    This helper is local because the comparator tests need
    full-shape observation records, not the schema-test
    minimum-shape (which only validates the schema validator's
    branch logic). Reusing PR 7/8 test helpers would couple
    PR 10 tests to PR 7/8 test internals; building locally
    preserves test-module independence.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "test-capture-id-obs",
        "captured_at": "2026-05-11T12:00:00.000Z",
        "record_kind": "observation",
        "source": "seed",
        "fixture_id": fixture_id,
        "prompt": prompt,
        "candidate_set": {
            "post_reachability": ["forge_ping", "forge_list_projects"],
            "post_pr14_filter": narrower_decision,
        },
        "topology": {
            "probed_at": "2026-05-11T12:00:00.000Z",
            "backends": {
                "flame_bridge": {"reachable": True},
                "ollama_local": {"reachable": True},
                "anthropic": {"reachable": True},
            },
        },
        "identity": {
            "narrower_version_hash": "test-narrower-hash",
            "registered_tools_snapshot_hash": "test-tools-hash",
            "daemon_git_sha": "test-git-sha",
        },
        "narrower": {
            "decision": narrower_decision,
            "pr20_condition_met": pr20_condition_met,
            "collapse_occurred": collapse_occurred,
            "ambiguity_state": ambiguity_state,
            "latency_ms": 12.5,
        },
    }


def _build_expectation_record(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> dict[str, Any]:
    """Build a minimum-shape valid expectation record.

    Mirrors PR 8's helper at
    ``test_pr8_seed_surface.py::_minimum_valid_expectation_record``.
    Carries the 4 universal keys + the 3 PR 8-required
    expectation keys (fixture_id, prompt, expected_narrow). No
    ``source`` field (per the schema validator's expectation-
    branch no-source check at ``_schema.py:243–247``).
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "test-capture-id-exp",
        "captured_at": "2026-05-11T12:00:00.000Z",
        "record_kind": "expectation",
        "fixture_id": fixture_id,
        "prompt": prompt,
        "expected_narrow": expected_narrow,
    }
```

**Test 1 — `test_compare_records_single_survivor_no_divergence` (risk #1):**

```python
def test_compare_records_single_survivor_no_divergence() -> None:
    """Single-survivor fixture: expected = observed = ['forge_ping'];
    comparator reports no divergence + correct per-surface
    contributions.

    Sources fixture_id + prompt + expected_narrow from
    ``tests.corpus.fixtures.fix_single_survivor.FIXTURE``. Builds
    a matching observation record (narrower.decision =
    ['forge_ping'], pr20_condition_met=True, collapse_occurred=True
    per the fixture's PR 9 spec §4.2 arbitration trace
    archaeology).
    """
    obs = _build_observation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        narrower_decision=["forge_ping"],
        pr20_condition_met=True,
        collapse_occurred=True,
        ambiguity_state="single_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        expected_narrow=list(FIX_SINGLE["expected_narrow"]),
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-single-survivor",
        "expectation": {"expected_narrow": ["forge_ping"]},
        "observation": {"observed_narrow": ["forge_ping"]},
        "divergence": {"narrow_diverged": False},
    }
```

**Test 2 — `test_compare_records_multi_match_no_divergence` (risk #2):**

```python
def test_compare_records_multi_match_no_divergence() -> None:
    """Multi-match fixture: expected = observed = ['forge_list_projects',
    'flame_list_libraries'] verbatim (list-equality, order
    preserved per carrier #10); comparator reports no divergence.

    The two-element list ordering is meaningful per carrier #10:
    "narrower_decision carries the filtered list verbatim at
    narrowing finalization." Test asserts the comparator does
    NOT sort or reorder before comparison.
    """
    obs = _build_observation_record(
        fixture_id=FIX_MULTI["fixture_id"],
        prompt=FIX_MULTI["prompt"],
        narrower_decision=["forge_list_projects", "flame_list_libraries"],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_MULTI["fixture_id"],
        prompt=FIX_MULTI["prompt"],
        expected_narrow=list(FIX_MULTI["expected_narrow"]),
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-multi-match",
        "expectation": {
            "expected_narrow": ["forge_list_projects", "flame_list_libraries"],
        },
        "observation": {
            "observed_narrow": ["forge_list_projects", "flame_list_libraries"],
        },
        "divergence": {"narrow_diverged": False},
    }
```

**Test 3 — `test_compare_records_no_keyword_match_divergence` (risk #3):**

```python
def test_compare_records_no_keyword_match_divergence() -> None:
    """No-keyword-match fixture: expected = [], observed = full
    4-tool controlled set; comparator reports
    narrow_diverged=True + correct per-surface contributions.

    THE load-bearing PR 9-authored divergence proof case (per
    PR 9 spec §4.4 + the authored/observed divergence framing
    in fix_no_keyword_match.py). The fixture-author's
    aspirational claim (``expected_narrow=[]``) disagrees with
    the chat-handler's actual PR14 fallback behavior (full
    capability preserved); the comparator surfaces the
    divergence as a structured report claim.
    """
    obs = _build_observation_record(
        fixture_id=FIX_NO_KW["fixture_id"],
        prompt=FIX_NO_KW["prompt"],
        narrower_decision=[
            "forge_ping",
            "forge_list_projects",
            "flame_list_libraries",
            "flame_render_status",
        ],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_NO_KW["fixture_id"],
        prompt=FIX_NO_KW["prompt"],
        expected_narrow=list(FIX_NO_KW["expected_narrow"]),  # []
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-no-keyword-match",
        "expectation": {"expected_narrow": []},
        "observation": {
            "observed_narrow": [
                "forge_ping",
                "forge_list_projects",
                "flame_list_libraries",
                "flame_render_status",
            ],
        },
        "divergence": {"narrow_diverged": True},
    }
```

**Test 4 — `test_compare_records_does_not_mutate_inputs` (risk #4 / PR-10-LOCAL invariant):**

```python
def test_compare_records_does_not_mutate_inputs() -> None:
    """PR-10-LOCAL binding statement (A.5.3.2-PR10-SPEC.md §0):
    'The signature returns a new structured value; the inputs
    are read but never modified ... Tests assert input records
    remain byte-identical after the function returns.'

    Builds a single-survivor pair; takes ``copy.deepcopy(...)``
    of both records BEFORE invoking ``compare_records``;
    asserts both records equal their pre-invocation deepcopies
    AFTER the function returns.

    Also asserts that mutating the RETURNED report's nested
    lists does NOT propagate back into the input records (the
    report's lists are fresh allocations per §4.1.6
    implementation discipline).
    """
    obs = _build_observation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        narrower_decision=["forge_ping"],
        pr20_condition_met=True,
        collapse_occurred=True,
        ambiguity_state="single_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        expected_narrow=["forge_ping"],
    )

    obs_pre = copy.deepcopy(obs)
    exp_pre = copy.deepcopy(exp)

    report = compare_records(obs, exp)

    # Invariant: inputs byte-identical after the function returns.
    assert obs == obs_pre, (
        "observation_record mutated by compare_records — "
        "PR-10-LOCAL binding statement violated"
    )
    assert exp == exp_pre, (
        "expectation_record mutated by compare_records — "
        "PR-10-LOCAL binding statement violated"
    )

    # Defense in depth: mutating the report's contained lists
    # does NOT propagate back into input records.
    report["observation"]["observed_narrow"].append("smuggled_tool")
    report["expectation"]["expected_narrow"].clear()

    assert obs == obs_pre, (
        "observation_record mutated by report-list mutation — "
        "report's lists must be fresh allocations per "
        "A.5.3.2-PR10-SPEC.md §4.1.6 implementation discipline"
    )
    assert exp == exp_pre, (
        "expectation_record mutated by report-list mutation — "
        "report's lists must be fresh allocations per "
        "A.5.3.2-PR10-SPEC.md §4.1.6 implementation discipline"
    )
```

**Test 5 — `test_compare_records_does_not_sort_inputs` (risk #5 / §4.2 binding behavioral commitment — sort-rejection vector):**

```python
def test_compare_records_does_not_sort_inputs() -> None:
    """§4.2 binding behavioral commitment: 'The comparator does
    NOT sort narrower.decision or expected_narrow before
    comparing — order is meaningful observation/expectation;
    reordering masks divergence.'

    Builds a pair where ``observation_record["narrower"]["decision"]``
    and ``expectation_record["expected_narrow"]`` contain
    identical multi-element lists in DIFFERENT orderings.
    Asserts the comparator reports ``narrow_diverged=True``
    (NOT False — silent sorting would mask the ordering
    divergence).

    Carrier #10 ("narrower_decision carries the filtered list
    verbatim") makes ordering meaningful — list-equality
    preserves it; set-equality or sorted-equality would
    structurally mask divergence at the chat-handler observation
    surface where PR14 input order is preserved through PR21.
    """
    obs = _build_observation_record(
        fixture_id="fix-pr10-sort-test",
        prompt="test sort rejection",
        narrower_decision=["tool_a", "tool_b"],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id="fix-pr10-sort-test",
        prompt="test sort rejection",
        expected_narrow=["tool_b", "tool_a"],  # SAME contents, DIFFERENT order
    )

    report = compare_records(obs, exp)

    assert report["divergence"]["narrow_diverged"] is True, (
        "compare_records silently sorted/reordered one or both "
        "lists before comparison — §4.2 binding behavioral "
        "commitment violated. Input ordering must be preserved "
        "verbatim per carrier #10's 'filtered list verbatim' "
        "requirement at the chat-handler observation surface."
    )

    # Defense in depth: assert the per-surface contributions
    # preserve the ORIGINAL input orderings, not a sorted view.
    assert report["observation"]["observed_narrow"] == ["tool_a", "tool_b"], (
        "observation.observed_narrow does not preserve input "
        "ordering — comparator silently sorted/reordered the "
        "observation list. §4.2 binding behavioral commitment "
        "violated."
    )
    assert report["expectation"]["expected_narrow"] == ["tool_b", "tool_a"], (
        "expectation.expected_narrow does not preserve input "
        "ordering — comparator silently sorted/reordered the "
        "expectation list. §4.2 binding behavioral commitment "
        "violated."
    )
```

#### 4.3.3 Conditional 6th test — `test_compare_records_does_not_canonicalize_inputs`

**Status:** **Incarnation-time decision per PR 10 implementation.**

The §4.2 binding behavioral commitment enumerates four
operational rejections: sort, lowercase/whitespace strip,
"repair," and semantic coercion. Tests 4 + 5 cover the
mutation vector + sort-rejection vector (the two structurally
visible-from-outside vectors). The remaining two vectors —
canonicalization (string-level processing) and "repair" — are
addressed differently:

- **"Repair"** is addressed by the authority pre-checks: missing
  fields raise `ComparatorInputError`, they don't get
  silently defaulted. Tests 1–3 exercise the success path with
  full records; the failure path is covered structurally by
  the function body's `raise` statements (no test required at
  PR 10 — the validation is a sanity check against caller
  misuse, not a semantic claim, per framing §4.2 validation
  discipline note).
- **Canonicalization** is the string-level vector
  (lowercase, whitespace strip, Unicode NFC/NFD normalization,
  etc.).

**Trigger condition for the conditional 6th test:**

> If PR 10 implementation introduces **any** pre-comparison
> string processing — including but not limited to:
>
> - `s.lower()` on tool names
> - `s.strip()` on tool names
> - `unicodedata.normalize(...)` on tool names
> - any list-comprehension that transforms strings before
>   comparison (e.g., `[s.lower() for s in obs_decision]`)
> - any `casefold()`, `replace()`, or regex substitution
>   applied to list elements
>
> a 3rd authorship-preservation test
> (`test_compare_records_does_not_canonicalize_inputs`) is
> REQUIRED and the test count amends from 5 to 6 at the same
> implementation commit.

**Reference test body (if the trigger fires):**

```python
def test_compare_records_does_not_canonicalize_inputs() -> None:
    """§4.2 binding behavioral commitment: 'The comparator does
    NOT lowercase tool names, strip whitespace, or apply any
    string canonicalization — those are surface-authorship
    details preserved.'

    Builds a pair where ``observed_narrow`` and
    ``expected_narrow`` contain strings that differ ONLY in
    canonicalization-adjacent ways (case, whitespace, Unicode
    composition). Asserts narrow_diverged=True (NOT False —
    silent canonicalization would mask divergence).
    """
    obs = _build_observation_record(
        fixture_id="fix-pr10-canon-test",
        prompt="test canonicalization rejection",
        narrower_decision=["FORGE_PING"],  # UPPERCASE
        pr20_condition_met=True,
        collapse_occurred=True,
        ambiguity_state="single_survivor",
    )
    exp = _build_expectation_record(
        fixture_id="fix-pr10-canon-test",
        prompt="test canonicalization rejection",
        expected_narrow=["forge_ping"],  # lowercase
    )

    report = compare_records(obs, exp)

    assert report["divergence"]["narrow_diverged"] is True, (
        "compare_records silently canonicalized one or both "
        "lists before comparison — §4.2 binding behavioral "
        "commitment violated."
    )
```

**Default disposition at PR 10:** the §4.1.6 reference
implementation uses **direct list equality** (`obs_decision !=
exp_narrow`) without any string processing. The
canonicalization vector is structurally unreachable; the
conditional 6th test is **NOT required** and **NOT shipped**.

**If the implementer deviates** from the §4.1.6 reference
implementation in a way that introduces string processing, the
conditional 6th test ships in the same commit as the
implementation change, AND the deviation is registered as a
grounding-time amendment per
`A.5.3.2-PR9-SPEC.md` §4.7 amendment-at-incarnation taxonomy.
The amendment records:

- The specific string-processing operation introduced.
- The rationale (why direct list-equality was insufficient).
- The new test body.
- The framing-level approval routing (the deviation requires
  framing review because it weakens the §4.2 binding behavioral
  commitment's structural unreachability claim).

**Test count budget:** 5 tests (default) → 6 tests
(conditional). The framing's 5–7 range accommodates either.
PR 10 close §6 reports the actual count + the conditional
trigger disposition.

### 4.4 `tests/corpus/test_pr3_discipline.py` (no modifications — amendment 2026-05-11)

**Path:** `tests/corpus/test_pr3_discipline.py`

**Modification:** **none.** Zero lines changed. The framing
§8.1 + spec-original §4.4 called for a one-line `_ALLOWLIST`
extension; grounding against the actual test reveals the
extension is unnecessary AND would be misleading.

#### 4.4.1 The corrected understanding

`tests/corpus/test_pr3_discipline.py::test_zero_production_imports_outside_corpus`
walks the production package tree (`forge_bridge/`) and asserts
no source file imports `forge_bridge.corpus` in any form,
EXCEPT for files matching `_ALLOWLIST`. The implementation
auto-excludes the corpus subtree before the allowlist check:

```python
# from tests/corpus/test_pr3_discipline.py:90–96
for py in package_root.rglob("*.py"):
    # Skip the corpus package itself — it imports itself freely.
    try:
        py.relative_to(corpus_subtree)
        continue
    except ValueError:
        pass
    ...
    if rel in _ALLOWLIST:
        continue
```

The asymmetry is: **the corpus subtree is blanket-permitted**;
files **outside** the corpus subtree that need to import from
`forge_bridge.corpus` are admitted **by name** via
`_ALLOWLIST`. The current allowlist entries
(`console/handlers.py`, `console/_step.py`) are both outside
the corpus subtree — they ARE the integration call sites the
allowlist exists to govern.

`forge_bridge/corpus/_compare.py` is **inside** the corpus
subtree. It is blanket-permitted by location. Adding it to
`_ALLOWLIST` would be:

1. **Mechanically inert** — the discipline check never reaches
   the allowlist for corpus-subtree files (`continue` fires
   first at the subtree-exclusion check).
2. **Semantically misleading** — future contributors reading
   `_ALLOWLIST` would assume `_compare.py` is an integration
   call site like `handlers.py` / `_step.py`. The allowlist's
   discriminating purpose (naming external integration sites)
   would be diluted.
3. **Counter to the read-before-spec discipline** — per
   `feedback_ground_specs_in_actual_files`, the framing
   inferred allowlist semantics rather than reading the test
   implementation.

#### 4.4.2 Spec amendment 2026-05-11 — `_ALLOWLIST` extension unnecessary

**Surfaced at:** pre-Step-1 grounding of
`tests/corpus/test_pr3_discipline.py` against the framing §8.1
"mechanical extension" assumption inherited into spec-original
§4.4.

**Trigger:** empirical reading of `test_pr3_discipline.py`
lines 92–96 revealed the corpus-subtree auto-exclusion. The
framing's phrasing — *"only files inside `forge_bridge/corpus/`
and the explicit allowlist may import from `forge_bridge.corpus`"*
— is structurally correct, but the conclusion drawn
(*"the comparator module is inside the corpus package, so
locality holds; the allowlist extension is mechanical"*)
contradicts itself: if locality holds, no allowlist entry is
needed (the location alone is sufficient permission).

**Earlier than PR 9's §4.7 amendment** (PR 9 caught the
fixture-name error at Step 2 implementation; PR 10 catches the
allowlist-semantics error pre-Step-1). The earlier catch is
the discipline working at the right cadence — per
`feedback_ground_specs_in_actual_files`, the read-before-draft
rule extends to "read-before-implement" when spec drafting
might have inferred rather than grounded.

**Corrected understanding:**

| Spec-original (incorrect) | Amendment (corrected) |
|---|---|
| One-line `_ALLOWLIST` entry added | Zero modifications to `test_pr3_discipline.py` |
| `test_pr3_discipline.py` in "Modified test discipline file" §2 in-scope | `test_pr3_discipline.py` in "Verified test discipline files (no modifications)" §2 in-scope |
| Step 1 atomic commit = `_compare.py` skeleton + allowlist entry | Step 1 atomic commit = `_compare.py` skeleton only |
| Step 5 verification item 6 rationale: "the one-line allowlist extension is consumed" | Step 5 verification item 6 rationale: "passes unchanged via corpus-subtree auto-exclusion at lines 92–96" |
| §1 real-job names "eight regression contracts" | §1 real-job names "nine regression contracts" (PR 3 discipline added to explicit list) |

**Sections affected by the amendment:**

- §1 real-job — sentence about extending `_ALLOWLIST`
  removed; regression-contract count bumped 8 → 9 with PR 3
  discipline named explicitly; amendment note added.
- §2 in-scope — `test_pr3_discipline.py` moved from
  "Modified test discipline file" entry to "Verified test
  discipline files (no modifications)" list with auto-
  exclusion rationale.
- §4.4 — this section, rewritten in place.
- §5.2 regression contract — "PR 3 discipline" line rewritten
  to state "no modifications" with auto-exclusion rationale.
- §6 Step 1 — `_ALLOWLIST` modification instruction removed;
  atomic commit simplified to single-file (`_compare.py`
  skeleton); verification item 1 rationale updated.
- §6 Step 5 verification item 6 — rationale updated.
- §8 cross-references — `_ALLOWLIST` entry updated to state
  "not modified at PR 10."
- Resume protocol — Step 1 instruction simplified.

**Spec-amendment cadence:** registered as standalone NO-code
commit before Step 1 lands. Matches the PR 9 §4.7 cadence
(separate NO-code amendment commit) per
`feedback_ground_specs_in_actual_files` discipline.

**What this amendment does NOT change:**

- The architectural success signal (0 production source
  modifications outside `_compare.py`) is unaffected — PR 10
  was always going to ship exactly one production source file
  (`_compare.py`); the test-file modification was always test-
  surface anyway.
- The four-walker partition (PR 4 + PR 8 + PR 9 + PR 10) is
  unaffected — each walker's target-set + ontology is
  preserved.
- The seven symbol-level decisions (§4.1.4 + §4.1.5 + §4.1.6 +
  §4.2.2 + §4.3) are unaffected.
- The 7-named-test count (5 comparator + 2 discipline) is
  unaffected.
- The cumulative test-count anchors (214 forge / 208 forge-
  bridge at default disposition) are unaffected.

**What the amendment archaeology preserves (load-bearing):**

The `_ALLOWLIST` is **for files outside the corpus subtree
that need to import FROM the corpus** — the integration call
sites. Both current entries (`console/handlers.py`,
`console/_step.py`) are outside the corpus subtree. A future
PR adding a third integration call site (e.g., a future
`tools/some_helper.py` that emits Layer 1 records under
allowed conditions) extends `_ALLOWLIST` by one named entry
per the PR 4 framing §2 contract. Corpus-internal modules
(`_capture.py`, `_seed.py`, `_compare.py`, etc.) NEVER appear
in `_ALLOWLIST` — they are blanket-permitted by location.

---

## 5. Test plan

### 5.1 Test inventory (7 named tests)

| # | Module | Test name | Risk | Notes |
|---|---|---|---|---|
| 1 | `test_pr10_comparator.py` | `test_compare_records_single_survivor_no_divergence` | §3 risk #1 | Single-survivor unit; FIX_SINGLE pair; asserts full report shape. |
| 2 | `test_pr10_comparator.py` | `test_compare_records_multi_match_no_divergence` | §3 risk #2 | Multi-match unit; FIX_MULTI pair; 2-element list ordering preserved per carrier #10. |
| 3 | `test_pr10_comparator.py` | `test_compare_records_no_keyword_match_divergence` | §3 risk #3 | No-keyword-match unit; FIX_NO_KW pair; THE divergence proof case (expected=[] vs. observed=full 4-tool fallback). |
| 4 | `test_pr10_comparator.py` | `test_compare_records_does_not_mutate_inputs` | §3 risk #4 | Authorship preservation — PR-10-LOCAL invariant; deepcopy assertion + fresh-list-allocation defense in depth. |
| 5 | `test_pr10_comparator.py` | `test_compare_records_does_not_sort_inputs` | §3 risk #5 | Authorship preservation — §4.2 binding behavioral commitment sort-rejection vector; identical contents, different orderings → narrow_diverged=True. |
| A | `test_pr10_comparator_discipline.py` | `test_compare_permitted_imports_value_locked` | §3 risk #6 | Frozenset value-lock regression at zero symbols. Read-only-interpretive authority discipline enforcement. |
| B | `test_pr10_comparator_discipline.py` | `test_compare_module_references_subset_of_permitted_imports` | §3 risk #6 | Walker subset-enforcement against `_compare.py`. Read-only-interpretive authority discipline enforcement. |

**Total: 7 named tests.** No `parametrize` over fixtures (per
§4.3.1 pattern — fixtures are imported as data, used in three
distinct test bodies; programmatic fixture parametrization
adds infrastructure topology per framing §3.6 form #6
speculative-fixture-semantics-widening risk).

**Named == collected** for PR 10's contribution at default
disposition. If the conditional 6th test fires per §4.3.3, the
count amends to 8 (5 comparator + 3 conditional → 5 walker +
comparator + 1 = wait, recount: 5 comparator behavioral + 1
conditional = 6, plus 2 discipline = 8 total).

### 5.2 Regression contract

PR 10 must NOT regress:

- **PR 3 discipline** — `test_pr3_discipline.py`. **Zero
  modifications** per §4.4 amendment 2026-05-11. The Layer 1
  discipline test auto-excludes the corpus subtree (lines
  92–96) before the `_ALLOWLIST` check; `_compare.py` is
  blanket-permitted by location. The test passes against the
  post-PR-10 codebase without any modification to the
  allowlist or the discipline logic.
- **PR 4 walker** — `test_pr4_participation_creep.py`. Passes
  unchanged. The parallel-not-extension Layer 2 boundary
  preserves: PR 4 walker target-set is narrowing-subsystem
  production files (NOT `_compare.py`); PR 10's parallel walker
  does not modify PR 4's input set or admission ontology.
- **PR 4 + PR 5 integration tests** —
  `test_pr4_chat_handler_integration.py`,
  `test_pr4_no_dependency.py`,
  `test_pr5_chain_step_integration.py`. Pass unchanged. PR 10
  introduces zero new emission call sites; chat-handler and
  chain-step integration behaviors are unchanged.
- **PR 6 Layer 3 lint** —
  `test_pr6_visual_asymmetry.py`. All 17 tests pass unchanged.
  PR 10 introduces zero new `emit_divergence_capture` call
  sites; the lint's discovery walk input set is unchanged.
- **PR 7 modules** — all `test_pr7_*.py` modules pass
  unchanged.
- **PR 8 walker** — `test_pr8_seed_surface.py` passes unchanged
  (all 14 named tests / 25 collected). PR 10 does not modify
  `_seed.py`; PR 8 walker input set unchanged.
- **PR 9 walker** — `test_pr9_fixture_discipline.py` passes
  unchanged (2 tests). PR 10 does not modify fixture modules
  under `tests/corpus/fixtures/`; PR 9 walker input set
  unchanged.
- **PR 9 integration tests** —
  `test_pr9_fixture_integration.py` passes unchanged (5
  tests). PR 10 does not modify fixtures or driver
  orchestration.
- **Public API** — `forge_bridge.__all__` stays at 19 symbols.
  PR 8's `test_pr8_helpers_remain_corpus_internal` continues
  to enforce the existing corpus-internal helpers; Step 5
  verifies the comparator surface (`compare_records`,
  `DivergenceReport`, `ComparatorInputError`) is similarly
  corpus-internal (no `__all__` membership).

### 5.3 Test count delta

**Baseline at PR 9 close** (per PR 9 close §1 + PR 9 spec §5.3):

- Forge env: **207 collected** (175 pre-PR-8 + 25 PR 8 +
  7 PR 9).
- Forge-bridge env: **201 collected** (194 pre-PR-8 + 25 PR 8 +
  7 PR 9 − 25 PR 8 = wait, recount). Actually per PR 9 spec
  §5.3 directly: forge-bridge env baseline at PR 9 close = 201
  (194 baseline + 7 PR 9 = 201; same 6-test gap continues per
  `project_v1_4_x_harness_debt.md`).

**PR 10 contribution:** 7 named tests at default disposition
(5 comparator + 2 discipline); 8 if conditional 6th fires.

**Target at PR 10 close (default disposition):**

- Forge env: **214 collected** (207 baseline + 7 new = 214).
- Forge-bridge env: **208 collected** (201 baseline + 7 new =
  208; same 6-test gap continues).

**Target at PR 10 close (conditional 6th fires):**

- Forge env: **215 collected**.
- Forge-bridge env: **209 collected**.

**Per `feedback_counts_are_archaeology_grade`**, count
inconsistencies are rejected at PR 10 close review. PR 10 close
§6 reports both **named** and **collected** counts (identical at
PR 10 due to no parametrize) plus the full-corpus 214 / 208 (or
215 / 209) anchor verification.

**Do not conflate the two env counts.** Forge-bridge env gap is
load-bearing per `project_v1_4_x_harness_debt.md`; PR 10 close
§6 documents both env counts explicitly.

### 5.4 What PR 10 deliberately does NOT test

Per framing §7 + spec §2 out-of-scope:

- **End-to-end fixture drive.** PR 10 tests do not invoke
  `drive_seed_fixture` or any arbitration helper. The records
  consumed by tests 1–3 are built in-memory from FIXTURE data;
  the arbitration trace recorded in each fixture's docstring
  is the source of truth for the observation record's
  `narrower.decision` values. PR 9 integration tests already
  exercise end-to-end fixture drive (5 named tests); PR 10
  decouples from that exercise to keep unit-test isolation +
  env-independence.
- **Reader integration.** PR 10 tests do not invoke
  `read_capture_file()` or any reader surface. The reader is
  exercised by PR 3 + PR 7 + PR 9 tests. The comparator is
  decoupled from the reader by design (caller's job to read +
  partition + join).
- **Cross-fixture record join.** PR 10 tests do not exercise
  driving multiple fixtures and joining their records by
  `fixture_id` across surfaces. Each test invokes
  `compare_records` on exactly one pair. Multi-pair join is
  caller's concern (PR 11 integration tests demonstrate the
  3-line dict-comprehension boilerplate per framing §2.1).
- **Performance / scaling.** PR 10 tests do not measure
  comparator latency, memory allocation patterns, or scaling
  characteristics.
- **Schema validity round-trip.** PR 10 tests build minimum-
  shape records in-memory; they do NOT validate the built
  records against `validate_capture_record(record)` from
  `_schema.py`. The schema validator is exercised by PR 7 +
  PR 8 schema-test modules; PR 10 inherits that coverage by
  reference. (The minimum-shape helpers in §4.3.2 produce
  schema-valid records; the validator passes against them; the
  PR 10 tests don't re-prove that.)
- **`ComparatorInputError` raise paths beyond the
  authorship-preservation tests' coverage.** PR 10 tests 4 +
  5 build only valid pairs (they assert behavior on success
  paths). The seven `ComparatorInputError` raise paths
  enumerated in §4.1.6 are NOT each separately tested at
  PR 10. The framing §4.2 validation discipline note classes
  these as "sanity check against caller misuse — NOT a
  semantic claim"; they are structurally covered by the body's
  `raise` statements, and the cost of seven separate raise-
  path tests outweighs the marginal protection at PR 10's test-
  count budget. If a future PR proposes adding the raise-path
  tests, the addition is framing-level review territory (it
  expands the test-count target beyond the 5–7 framing budget).
- **TypeAlias resolution semantics.** PR 10 tests do not
  assert `DivergenceReport is dict[str, Any]` or similar
  typing-introspection assertions. The TypeAlias is a
  vocabulary anchor (per §4.1.4); its typing resolution is
  static-analysis-only and not runtime-observable.

---

## 6. Implementation sequence

The framing §5.7 cadence-matches-work-depth rule applies. PR 10
is **interpretive-read-surface work** (per §3 risk classification)
— closer to PR 7's plumbing depth than PR 8's boundary depth or
PR 9's integration depth. Full three-round review applies to
Step 3 (the architectural-center: comparator function body +
unit tests); Steps 1, 2, 4 are mechanical (skeleton, discipline
scaffolding, authorship tests) and may proceed with reduced
review depth at the implementer's discretion.

Five steps. Each step changes one authority or ontology boundary
cleanly.

### Step 1 — `_compare.py` skeleton (single-file)

Create `forge_bridge/corpus/_compare.py` with:

- Module-level docstring (all carriers + binding statements +
  proactive scope guardrail + PR-10-LOCAL + cross-surface
  unbinding clarification per §4.1.1 ordering).
- Module imports (`__future__ annotations`, `Any`, `TypeAlias`
  per §4.1.2).
- `DivergenceReport: TypeAlias = dict[str, Any]` with full
  docstring per §4.1.4.
- `class ComparatorInputError(ValueError)` with full docstring
  per §4.1.5.
- `def compare_records(observation_record: dict,
  expectation_record: dict) -> DivergenceReport:` with full
  docstring per §4.1.6 + body raising `NotImplementedError`:

  ```python
  def compare_records(
      observation_record: dict,
      expectation_record: dict,
  ) -> DivergenceReport:
      """[Full docstring per §4.1.6.]"""
      raise NotImplementedError(
          "compare_records body lands at Step 3 per "
          "A.5.3.2-PR10-SPEC.md §6"
      )
  ```

Per §4.4 amendment 2026-05-11, **no modification** to
`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` is required —
`_compare.py` is blanket-permitted by its location inside the
corpus subtree (auto-excluded at lines 92–96 of the discipline
test before the allowlist check). Step 1 atomic commit is
single-file.

**Atomic commit:** new production module skeleton —
`forge_bridge/corpus/_compare.py` only. No test-file
modifications.

**Reduced review depth** acceptable — the step is mechanical;
docstrings + signatures are the load-bearing content, and they
are derived directly from §4.1.

**Verification:**

- `pytest tests/corpus/test_pr3_discipline.py` — passes
  unchanged (corpus-subtree auto-exclusion handles `_compare.py`
  without an allowlist entry per §4.4 amendment).
- `python -c "from forge_bridge.corpus._compare import
  compare_records, DivergenceReport, ComparatorInputError;
  print('imports clean')"` — imports succeed.
- `python -c "from forge_bridge.corpus._compare import
  compare_records; compare_records({}, {})"` — raises
  `NotImplementedError` (skeleton body honored).
- Full `pytest tests/corpus/` — 207 collected forge env / 201
  collected forge-bridge env (PR 9 baseline; no new tests yet).

### Step 2 — `test_pr10_comparator_discipline.py` (4th walker)

Create `tests/corpus/test_pr10_comparator_discipline.py` with
the full structure per §4.2.2. Zero modifications to other test
files at this step.

The walker passes against the Step 1 `_compare.py` skeleton —
the skeleton imports only `__future__`, `typing` (`Any`,
`TypeAlias`), which carry zero `forge_bridge.corpus.*`
references. The walker's subset-enforcement holds vacuously
(empty `_compare.py` corpus-imports ⊆ empty
`_COMPARE_PERMITTED_IMPORTS`).

**Atomic commit:** discipline test module — 2 tests pass.

**Reduced review depth** acceptable — the step mirrors PR 9
walker pattern (`test_pr9_fixture_discipline.py`) with the
single-target-file scope distinction.

**Verification:**

- `pytest tests/corpus/test_pr10_comparator_discipline.py` — 2
  tests pass.
- `pytest tests/corpus/test_pr3_discipline.py` — passes
  unchanged.
- `pytest tests/corpus/test_pr4_participation_creep.py` —
  passes unchanged (PR 10 walker does not affect PR 4 walker).
- `pytest tests/corpus/test_pr8_seed_surface.py` — passes
  unchanged (PR 10 walker does not affect PR 8 walker).
- `pytest tests/corpus/test_pr9_fixture_discipline.py` —
  passes unchanged.
- Full `pytest tests/corpus/` — 209 collected forge env (207
  + 2 walker) / 203 collected forge-bridge env.

### Step 3 — `compare_records` body + 3 unit tests **(architectural-center)**

Replace the `NotImplementedError` body in `_compare.py` with the
reference implementation per §4.1.6. The implementation is
mechanical from the spec — copy the body verbatim (or transpose
to the implementer's style, preserving the discipline locks at
§4.1.6 implementation-discipline bullets).

Create `tests/corpus/test_pr10_comparator.py` with:

- Module docstring per §4.3.1.
- Imports per §4.3.1 (`copy`, `Any`, `pytest`,
  `compare_records` / `DivergenceReport` / `ComparatorInputError`
  from `forge_bridge.corpus._compare`, `SCHEMA_VERSION` from
  `_schema`, fixture imports from `tests.corpus.fixtures.*`).
- The two builder helpers `_build_observation_record` +
  `_build_expectation_record` per §4.3.2.
- The 3 unit tests (test 1 single-survivor, test 2 multi-match,
  test 3 no-keyword-match) per §4.3.2.

**Architectural-center.** This step lands:

1. The comparator function body — the operational form of
   carrier #17.
2. The §4.2 binding behavioral commitment's direct-list-
   equality discipline at the function body.
3. The 4th walker's subset-enforcement now actively exercises
   the post-Step-3 `_compare.py` (still zero corpus imports
   per §4.1.7 default disposition).
4. The PR 9 fixture corpus + the PR 7 substrate's structural
   companionship (compare consumes records shaped by both).
5. Tests 1–3 surface the PR 9-authored divergence proof case
   as a structured `DivergenceReport` claim (test 3).

**Full three-round review.**

**Atomic commit:** `_compare.py` body + new
`test_pr10_comparator.py` with 3 unit tests. Bundling is
appropriate (the tests need the implemented body; the body
without tests is unprovable).

**Verification:**

- `pytest tests/corpus/test_pr10_comparator.py` — 3 tests pass.
- `pytest tests/corpus/test_pr10_comparator_discipline.py` —
  2 tests pass unchanged (walker still passes against
  zero-corpus-imports `_compare.py`).
- `python -c "from forge_bridge.corpus._compare import
  compare_records; r = compare_records({'record_kind':
  'observation', 'fixture_id': 'x', 'narrower': {'decision':
  ['a']}}, {'record_kind': 'expectation', 'fixture_id': 'x',
  'expected_narrow': ['a']}); print(r)"` — produces the
  expected report dict.
- Full `pytest tests/corpus/` — 212 collected forge env (209
  + 3 unit) / 206 collected forge-bridge env.

### Step 4 — 2 authorship-preservation tests

Add tests 4 + 5 to `tests/corpus/test_pr10_comparator.py` per
§4.3.2.

This step is the operational corroboration of:

- The PR-10-LOCAL binding statement (test 4).
- The §4.2 binding behavioral commitment's sort-rejection
  vector (test 5).

If the implementer's Step 3 body deviated from §4.1.6 reference
implementation in a way that introduced pre-comparison string
processing (per §4.3.3 trigger condition), the conditional 6th
test
(`test_compare_records_does_not_canonicalize_inputs`) ships at
this step ALSO, AND the spec amendment per §4.3.3 trigger-
condition routing is registered at the commit message body.

**Default disposition: 2 tests added (4 + 5); test count at
this step lands at 5 comparator + 2 discipline = 7 total PR 10
tests.**

**Conditional disposition (canonicalization trigger fired): 3
tests added (4 + 5 + 6); test count lands at 6 comparator +
2 discipline = 8 total PR 10 tests + spec amendment
registered.**

**Reduced review depth** acceptable — the tests are derived
mechanically from §4.3.2 + §4.3.3 reference bodies.

**Atomic commit:** authorship-preservation tests added. Bundle
is appropriate (same module; same fixture imports; same builder
helpers).

**Verification:**

- `pytest tests/corpus/test_pr10_comparator.py` — 5 tests pass
  (or 6 if conditional fires).
- `pytest tests/corpus/test_pr10_comparator_discipline.py` —
  2 tests pass unchanged.
- Full PR 10 suite: `pytest tests/corpus/test_pr10_*.py` — 7
  tests pass (default) / 8 (conditional).
- PR 7 + PR 8 + PR 9 regression: `pytest tests/corpus/test_pr7_*.py
  tests/corpus/test_pr8_seed_surface.py tests/corpus/test_pr9_*.py`
  — all pass unchanged.

### Step 5 — Final verification

No new code lands at Step 5. This step verifies the post-PR-10
codebase against all regression contracts + close conditions.
The atomic commit registers the verification + carries the PR 10
commit message body (carriers + binding statements + governing
sentence + any spec amendments named explicitly).

**Verification checklist:**

1. **PR 10 suite:** `pytest tests/corpus/test_pr10_*.py` — 7/7
   pass (5 comparator + 2 discipline) at default disposition;
   8/8 (6 comparator + 2 discipline) at conditional disposition.
2. **PR 7 + PR 8 + PR 9 suites:** `pytest
   tests/corpus/test_pr7_*.py tests/corpus/test_pr8_seed_surface.py
   tests/corpus/test_pr9_*.py` — all pass unchanged.
3. **Layer 3 lint regression:** `pytest
   tests/corpus/test_pr6_visual_asymmetry.py` — 17/17 pass
   unchanged. Confirms PR 10 introduced zero new
   `emit_divergence_capture` call sites.
4. **PR 4 walker regression:** `pytest
   tests/corpus/test_pr4_participation_creep.py` — passes
   unchanged. Confirms PR 10's parallel walker did not affect
   PR 4's walker (different ontologies; both operational).
5. **PR 4 + PR 5 integration tests:** chat-handler + chain-step
   integration tests — pass unchanged.
6. **PR 3 discipline:** `pytest tests/corpus/test_pr3_discipline.py`
   — passes unchanged. Per §4.4 amendment 2026-05-11, no
   allowlist modification was needed — the corpus-subtree
   auto-exclusion (lines 92–96 of the discipline test) handles
   `_compare.py` blanket-style.
7. **Full corpus suite:** `pytest tests/corpus/` —
   **214 collected forge env** (207 baseline + 7 PR 10 new) /
   **208 collected forge-bridge env** (201 baseline + 7 PR 10
   new; same 6-test gap continues per
   `project_v1_4_x_harness_debt.md`). Or 215 / 209 if
   conditional 6th fires. Document both env counts in Step 5
   commit body; do not conflate.
8. **Console tests:** `pytest tests/console/test_chat_handler.py`
   — 50/50 unchanged.
9. **Public API regression:** `python -c "import forge_bridge;
   assert len(forge_bridge.__all__) == 19; assert
   'compare_records' not in forge_bridge.__all__; assert
   'DivergenceReport' not in forge_bridge.__all__; assert
   'ComparatorInputError' not in forge_bridge.__all__"` —
   clean. PR 8's `test_pr8_helpers_remain_corpus_internal`
   continues to enforce.
10. **Verbatim travel verification:** Step 5 verifier reads
    `_compare.py` module docstring + function docstring +
    `test_pr10_comparator_discipline.py` docstring +
    `test_pr10_comparator.py` docstring; cross-references each
    verbatim block against §0; surfaces any drift before the
    close commit. Carrier #17 lands at top of each module's
    carrier block per relevance-by-file ordering. The Gate-3-
    LOCAL form's *candidate carrier #16 corroboration substrate*
    marking is present at every site.
11. **Gate-3-LOCAL travel count verification:** Step 5 verifier
    confirms the Gate-3-LOCAL governing sentence travels
    through **≥3 PR 10 surfaces** (per framing §9 condition 7).
    Default expected count: 4 surfaces (`_compare.py` module
    docstring + both test module docstrings + ≥1 PR 10 commit
    message body — Step 5 commit qualifies if the sentence is
    included). Verifier confirms travel count ≥ 3.
12. **Architectural success signal verification:** `git diff
    --stat <pre-PR-10-base>..HEAD -- forge_bridge/` — exactly
    one production source file modification: addition of
    `forge_bridge/corpus/_compare.py`. Zero modifications to
    any other production source.
13. **Three-walker → four-walker partition verification:**
    Step 5 verifier confirms four Layer 2 walkers operate at
    PR 10 close (PR 4 + PR 8 + PR 9 + PR 10), each with a
    distinct target-set and ontology; the parallel-not-
    extension boundary is preserved.

**Step 5 commit message body** carries (in order):

- Section: "preserved invariants" — 16 active carriers +
  candidate #16 Gate-3-LOCAL form + Gate 2 binding framing
  clarification + Gate 3 cross-surface unbinding clarification +
  proactive scope guardrail + §4.2 binding behavioral
  commitment + PR-10-LOCAL binding statement verbatim.
- Section: "Gate-3-LOCAL corroboration" — explicit count of
  the surfaces through which the Gate-3-LOCAL governing
  sentence traveled at PR 10 (≥3 required per framing §9
  condition 7) + the explicit *candidate carrier #16
  corroboration substrate* marking.
- Section: "architectural success signal" — confirmation of 0
  production source modifications outside `_compare.py`.
- Section: "test count anchor" — 207 baseline + 7 new = 214
  forge env collected (or 215 if conditional 6th fires); 201
  baseline + 7 new = 208 forge-bridge env collected (or 209 if
  conditional fires); 6-test gap inherited per
  `project_v1_4_x_harness_debt.md`.
- Section: "cleanup-pressure resistance archaeology" — record
  of which cleanup pressure forms surfaced (if any) during
  PR 10 implementation + how each was rejected + which existing
  class member protected against them (per framing §6.2
  discipline; new members register at PR 10 close only if a
  genuinely distinct form surfaced).
- Section: "spec amendments at incarnation" — discoveries
  named explicitly with section references (if any surfaced
  during Steps 1–4). Specifically: if the conditional 6th
  test fired, the §4.3.3 trigger-condition routing + the
  spec amendment is registered here.
- Section: "regression contracts" — verification checklist
  results.

### Closing prose — Step 5 vs. close artifact

`A.5.3.2-PR10-CLOSE.md` lands as a distinct subsequent commit
after Step 5 verification completes (per framing §9 condition
16). The Gate 3 close artifact (`A.5.3.2-GATE-3-CLOSE.md`) does
NOT land at PR 10 close — it ships at PR 11 final commit per
Gate 3 framing §11.

The cadence preserves the PR 4–9 separation: implementation
sequence ≠ close archaeology. Step 5 concludes implementation +
verification authority; the close artifact performs retrospective
architectural synthesis (durable archival state, methodology
observations, cleanup-pressure class additions if any,
verbatim-travel archaeology).

PR 9 cadence verified: Step 5 verification at `5f057fc`
followed by close artifact at `a6e42f0` — two separate commits
(though Gate 2 close artifact landed at the same commit as
PR 9 close per Gate 2 framing §11.6). PR 10 mirrors with one
distinction: Step 5 verification commit followed by
`A.5.3.2-PR10-CLOSE.md` at a single subsequent commit (Gate 3
close ships at PR 11, not at PR 10).

### Natural pause points

- **Between Step 1 and Step 2** — verifies the production
  module skeleton is operational before the discipline walker
  lands. If the skeleton fails to import (e.g., docstring
  syntax error, TypeAlias resolution failure), surface before
  Step 2 fires its subset-enforcement against the broken file.
  Per §4.4 amendment 2026-05-11, no allowlist modification is
  part of Step 1; corpus-subtree auto-exclusion handles the
  discipline check.
- **Between Step 2 and Step 3** — verifies the 4th walker is
  operational + the carrier travel landed verbatim in the
  walker module before the architectural-center body lands.
  If carrier travel drift surfaces at this pause, register a
  Step 2.5 surgical cleanup commit (analogous to PR 8 Step 4.5
  pattern from PR 8 close §5.2 and PR 9 Step 5.5 pattern from
  PR 9 close `d598bf6`).
- **Between Step 3 and Step 4** — verifies the architectural-
  center is operational (3 unit tests passing; comparator body
  matches §4.1.6 reference implementation; walker still passes
  against zero-corpus-imports `_compare.py`). Confirms the
  §4.3.3 default disposition holds (no canonicalization
  trigger fired). If the implementer deviated in a way that
  triggered the canonicalization conditional, register the
  spec amendment + the conditional 6th test at this pause.
- **Immediately after Step 4** — full PR 10 suite green (7
  tests at default, 8 at conditional). Before Step 5
  verification, this is the moment to sanity-check the
  verbatim travel placements + the Gate-3-LOCAL travel count
  + the architectural success signal (0 production source
  modifications outside `_compare.py`) + the test count
  arithmetic against the collected total.

### What about an inter-step polish step?

PR 4, PR 5, PR 6 reserved a "polish step (no-op for this PR)"
slot. PR 7 + PR 8 + PR 9 surfaced no analogous polish during
spec drafting and did not reserve one. PR 10 surfaces no polish
during this drafting and does not reserve one. The five steps
above are the implementation sequence in full.

PR 8 + PR 9 introduced the Step N.5 surgical cadence variant —
PR 10 should expect verbatim-travel verification at Step 5 to
potentially surface implementation-time amendments analogous
to PR 8 Step 4.5 + PR 9 Step 5.5. The natural Step 4.5 slot
exists implicitly: if Step 5 verification surfaces scaffold
prose drift or carrier travel drift, register a surgical
pre-Step-5 cleanup commit before Step 5 verification lands.
Per Gate 3 framing §3.8, PR 10 may contribute a fourth Step
N.5 corroboration instance if mid-flight guidance surfaces.

---

## 7. Phase-end conditions for PR 10

| Trigger | Response |
|---|---|
| All 7 new tests pass (or 8 if conditional fires) + Layer 3 lint passes unchanged + PR 4 + PR 5 + PR 7 + PR 8 + PR 9 test surfaces pass unchanged + the 17 verbatim sentences in §0 (15 inherited carriers + carrier #17 + Gate 2 binding clarification) travel verbatim + the Gate-3-LOCAL governing sentence travels through ≥3 PR 10 surfaces with explicit *candidate carrier #16 corroboration substrate* marking + the proactive scope guardrail + §4.2 binding behavioral commitment + PR-10-LOCAL binding statement + cross-surface unbinding clarification travel verbatim into the relevant docstrings + commit message body + 0 production source modifications outside `forge_bridge/corpus/_compare.py` + `forge_bridge.__all__` stays at 19 symbols + the three-authority-surface partition + PR-INTERNAL three-way authority partition + 9-member cleanup-pressure-resistance class all preserve unchanged + the four-walker partition is operational with parallel-not-extension boundary preserved | PR 10 closes; `A.5.3.2-PR10-CLOSE.md` drafts as a distinct subsequent commit; Gate 3 framing → spec → implementation cadence advances to PR 11 (Gate 4 comparator's integration consumer + Gate 3 close artifact). |
| `test_pr6_visual_asymmetry.py` regresses against the post-PR-10 codebase | Hard CI failure; Layer 3 lint has been touched accidentally or PR 10 has begun introducing `emit_divergence_capture` call sites (the comparator is read-only-interpretive authority; emission helpers are rejected per framing §3.3 + this spec §4.2.1). Reject at CI; review surfaces the read-only-interpretive ontology rationale + the parallel-not-extension Layer 2 boundary. |
| `test_pr4_participation_creep.py` regresses on a future PR | Hard CI failure; either the PR 4 walker has been touched accidentally OR the parallel-not-extension Layer 2 ontology has been violated (e.g., PR 4 walker target-set expanded to include `_compare.py`, conflating two ontologies). Reject at CI; review surfaces the four-walker partition (§4.2.1) + "shared AST mechanics do not imply shared ontology" verbatim. |
| `test_pr8_seed_surface.py` regresses on a future PR | Hard CI failure; either PR 8 walker has been touched OR `_seed.py` acquired a forbidden corpus import. Neither is a PR 10 surface; the regression points to substrate drift. Reject at CI; review traces back to PR 8 walker integrity. |
| `test_pr9_fixture_discipline.py` regresses on a future PR | Hard CI failure; either PR 9 walker has been touched OR a fixture module acquired a forbidden corpus import. Neither is a PR 10 surface; the regression points to fixture-data discipline drift. Reject at CI; review traces back to PR 9 walker integrity. |
| `test_compare_permitted_imports_value_locked` regresses on a future PR | Hard CI failure; the zero-symbol-gate has been violated. The frozenset has acquired a symbol without framing-level review. Reject at CI; review surfaces §4.1.7 amendment trigger language + the read-only-interpretive authority discipline rationale + the framing routing for symbol admission. |
| `test_compare_module_references_subset_of_permitted_imports` regresses on a future PR | Hard CI failure; PR-10-LOCAL read-only-interpretive authority discipline has been violated. `_compare.py` has acquired a forbidden corpus import. Reject at CI; review surfaces framing §4.4 rejection message verbatim + the offender references + the §4.1.7 amendment routing. |
| `test_compare_records_single_survivor_no_divergence` regresses on a future PR | Hard CI failure; either the comparator body has been touched in a way that breaks the canonical single-survivor success case OR the fixture data has drifted OR the `_build_observation_record` / `_build_expectation_record` helpers have drifted. Reject at CI; review traces back to whichever surface broke. |
| `test_compare_records_multi_match_no_divergence` regresses on a future PR | Hard CI failure; either the comparator's list-equality semantics have been weakened (e.g., silently sorted, set-converted) OR carrier #10's "filtered list verbatim" requirement has been violated structurally. Reject at CI; review surfaces carrier #10 verbatim + §4.2 binding behavioral commitment + test 5's sort-rejection coverage. |
| `test_compare_records_no_keyword_match_divergence` regresses on a future PR | Hard CI failure; either the comparator silently coerced one of the surfaces (e.g., empty-list → full-list "repair," or full-list → empty-list "normalization") OR the divergence verdict logic was inverted. Reject at CI; review surfaces §4.2 binding behavioral commitment's "no repair" rejection + the load-bearing PR 9-authored divergence proof case from PR 9 spec §4.4. |
| `test_compare_records_does_not_mutate_inputs` regresses on a future PR | Hard CI failure; PR-10-LOCAL binding statement violated. The comparator silently mutated one or both input records, OR the report's contained lists alias back into input record list values (fresh-list-allocation discipline at §4.1.6 violated). Reject at CI; review surfaces PR-10-LOCAL verbatim + the §4.1.6 implementation discipline + the fresh-list-allocation rationale. |
| `test_compare_records_does_not_sort_inputs` regresses on a future PR | Hard CI failure; §4.2 binding behavioral commitment's sort-rejection vector violated. The comparator silently sorted, reordered, or set-converted one or both lists before comparison. Reject at CI; review surfaces §4.2 binding behavioral commitment's four operational rejections + carrier #10's "filtered list verbatim" + the sort-rejection vector specifically. |
| A future PR proposes inlining `emit_divergence_capture`, `_persist_expectation_record`, or any emission/persistence helper into the comparator | Rejected at the spec layer per framing §3.6 form #1 (helper merger) + §3.6 form #3 (persistence creep) + §5.3 + §7 items 1 + 2 + 3 + carrier #17 + member #7 + member #8. The comparator is read-only-interpretive authority; emission and persistence are distinct authority surfaces. The 4th walker enforces mechanically. |
| A future PR proposes batch-input variant (`compare_corpus(records: list) -> dict`) inside PR 10's scope or as a "natural extension" | Rejected at the spec layer per framing §2.1 + §5.2 + §7 item 4 + §7 item 17 + the function-vs-subsystem cleanup-pressure trap candidate carrier #16 exists to govern. Pair-input is locked. PR 12 may revisit if join boilerplate proliferates across 4+ call sites — observation-driven, not speculation-driven. |
| A future PR proposes a `DivergenceReport` dataclass / TypedDict / Protocol | Rejected at the spec layer per framing §4.3 (c)-rejection + §4.1.4 TypeAlias rationale + carrier #17. Typing ceremony does not add carrier #17 protection; the field-naming discipline + function-body construction discipline + unit tests are what enforce the shape. |
| A future PR proposes adding a flat-prefix variant (`DivergenceReport` shape (b) per framing §4.3) | Rejected at the spec layer per framing §4.3 default-lean (a) + §4.1.4 reasoning. The (b) shape is fragile to spec amendments adding non-prefixed fields without violating any structural test; (a) protects carrier #17 at the dict-structure level, not just at field-name level. |
| A future PR proposes promoting `compare_records` / `DivergenceReport` / `ComparatorInputError` to `forge_bridge.__all__` inside a cleanup PR | Rejected at the spec layer per framing §5.7 + §7 item 14 + PR 8 spec §2 out-of-scope #4. Comparator surface is corpus-internal at PR 10. Promotion to `__all__` is a framing-level decision deferred to PR 11 / Gate 4 if a concrete external consumer surfaces. |
| A future PR proposes modifying any production source file inside PR 10's scope outside `forge_bridge/corpus/_compare.py` | Rejected at the spec layer per framing §2.3 + §9 condition 11 + the architectural success signal continuity from PR 9. PR 10 is purely the addition of one production source file. Any modification to `_capture.py`, `_seed.py`, `_schema.py`, `_sources.py`, `reader.py`, or any other corpus or production module is a red flag requiring framing-level review. |
| A future PR proposes admitting a symbol to `_COMPARE_PERMITTED_IMPORTS` inside a cleanup PR | Rejected at the spec layer per §4.1.7 amendment trigger language + the read-only-interpretive authority discipline rationale. Admitting any symbol requires framing-level review evaluating whether the symbol preserves or erodes the discipline. |
| A future PR proposes unifying the PR 4 + PR 8 + PR 9 + PR 10 walkers into a generalized AST walker | Rejected at the spec layer per framing §3.3 + §8.2 + this spec §4.2.1 + Gate 2 close §1.6 + §2.4 item 5 + the four-walker parallel-not-extension rationale + "Shared AST mechanics do not imply shared ontology." The four walkers protect four distinct ontologies; unification collapses four protections into one rejection surface. |
| A future PR proposes pre-comparison string processing (lowercasing, whitespace strip, Unicode normalization, etc.) without registering the conditional 6th test + spec amendment | Rejected at the spec layer per §4.3.3 conditional test trigger + §4.2 binding behavioral commitment. The string-processing introduction must ship the conditional 6th test in the same commit AND register the §4.3.3 trigger-condition routing as a spec amendment at PR 10 close. Silent introduction without the test + amendment is rejected. |
| A future PR proposes promoting candidate carrier #16 to active inside PR 10's scope | Rejected at the spec layer per framing §3.1 + §7 item 16 + the Gate-3-LOCAL governing sentence's *candidate carrier #16 corroboration substrate* marking discipline. Promotion gates on Gate 3 close evaluation (PR 11). PR 10 contributes Gate-3-LOCAL form travel as corroboration substrate, but does NOT promote. Spec language must use "16 active carriers + candidate #16" not "17 active carriers." |
| A future PR proposes cross-surface comparator semantics (chat-handler observation joined with chain-step observation, etc.) inside PR 10's scope | Rejected at the spec layer per Gate 3 framing §5.1 + §5.2 + this spec §0 cross-surface unbinding clarification + framing §7 item 5. Path B is locked: cross-surface comparator semantics are intentionally unbound (not implicitly rejected) pending dedicated framing review. PR 10 does not draft, prefigure, or scaffold that review. |

---

## 8. Cross-references

- `A.5.3.2-PR10-FRAMING.md` (`8ad7fe9`) — **immediate
  predecessor; the PR-level inheritance contract this spec
  operates against.** §0 crystallizing pair (carrier #17 + Gate-
  3-LOCAL form); §2 objective + scope; §3 architectural
  inheritance; §4 architectural delta (§4.1 module + §4.2 function
  + §4.3 DivergenceReport posture + §4.4 4th walker + §4.5
  PR-10-LOCAL); §5 six binding decisions; §6 cleanup-pressure
  resistance; §7 20 non-acquisition commitments; §8 Layer 1/2/3
  implications; §9 phase-end conditions.
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — gate-level
  inheritance contract; three inherited truths; Path B locked
  (§5.1 + §5.2); candidate carrier #16 + Gate-3-LOCAL form
  (§5.4 + §6.1); carrier #17 (§5.5); binding framing
  clarification on cross-surface unbinding (§6.2); seven
  canonical cleanup-pressure forms (§4.2); proactive scope
  guardrail (§2.3); §6.1 evaluation criteria for candidate #16
  promotion.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis;
  §1 cross-PR composition; §2.1 Gate 4 comparator's two
  foundational dependencies (record_kind partition +
  fixture_id joinability) operationally verified at PR 9
  Step 4 — PR 10 inherits as unblock; §2.4 non-revisitable
  decisions including item 5 (walker unification rejection).
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus
  PR 10 consumes; §1.1 fixture corpus + grounding traces;
  §1.3 grounding-time amendment archaeology (PR 10 may
  surface a similar variant per framing §3.7); §2.4 the
  authored/observed divergence proof case (`fix_no_keyword_match`)
  — PR 10 unit test 3 surfaces this divergence as a structured
  report claim.
- `A.5.3.2-PR9-SPEC.md` — section structure + Layer 2 walker
  pattern this spec mirrors; §4.6 walker module surface; §4.7
  amendment-at-incarnation taxonomy (PR 10 inherits at §4.1.7
  + §4.3.3 + Step 4 trigger language); §5.1 test inventory
  shape; §5.2 regression contract pattern; §5.3 test count
  delta pattern; §6 implementation sequence + Step N.5
  surgical cadence pattern.
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface; `emit_seed_expectation` + `drive_seed_fixture` +
  schema validator; member #7 (companion records as truth-
  partitioning) + member #8 (`emit_seed_expectation` as
  semantics-not-topology) protect against PR 10 cleanup
  pressure forms 1 + 4.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces; carrier #14;
  `_KNOWN_RECORD_KINDS` 2-element lock; members #1–#6
  inherited unchanged into PR 10.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper; PR 10 reads its **output records**
  (persisted observation records — built in-memory in PR 10
  tests per §4.3.2 builder helpers), not its helper.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` —
  expectation helper; PR 10 reads its **output records**
  (persisted expectation records — built in-memory in PR 10
  tests per §4.3.2 builder helpers), not its helper.
- `forge_bridge/corpus/_seed.py::drive_seed_fixture` —
  fixture orchestrator; PR 10 does NOT invoke. PR 11
  integration tests invoke (via the PR 9 fixture corpus)
  and pass resulting records to PR 10's comparator.
- `forge_bridge/corpus/_schema.py` — schema validator + PR 7's
  `_KNOWN_RECORD_KINDS` + PR 8's `_REQUIRED_EXPECTATION_KEYS`.
  PR 10 does NOT import from `_schema.py` per §4.1.4 default
  disposition; the comparator validates via string literals.
- `forge_bridge/corpus/reader.py` — JSONL reader; PR 10
  comparator does NOT import. The reader is the caller's
  surface (PR 11 / Gate 4); the comparator takes pre-read
  records as function arguments.
- `forge_bridge/corpus/_compare.py` (planned, PR 10) — the
  comparator module.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` —
  Layer 1; **not modified at PR 10** per §4.4 amendment
  2026-05-11. The corpus-subtree auto-exclusion (lines 92–96)
  handles `_compare.py` without an allowlist entry.
  `_ALLOWLIST` is for integration call sites outside the
  corpus subtree (currently `console/handlers.py` +
  `console/_step.py`); corpus-internal modules never appear in
  it.
- `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
  — Layer 2 (PR 4 walker); preserves unchanged.
- `tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS`
  — Layer 2 (PR 8 walker); preserves unchanged.
- `tests/corpus/test_pr9_fixture_discipline.py::_FIXTURE_PERMITTED_IMPORTS`
  — Layer 2 (PR 9 walker); preserves unchanged.
- `tests/corpus/test_pr10_comparator_discipline.py::_COMPARE_PERMITTED_IMPORTS`
  (planned, PR 10) — Layer 2 (4th walker, Option A); scoped
  to `_compare.py`; value-locked at zero symbols.
- `tests/corpus/test_pr10_comparator.py` (planned, PR 10) —
  comparator behavioral tests; 5 named at default, 6 at
  conditional disposition.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3;
  ships unchanged into PR 10.
- `tests/corpus/fixtures/fix_single_survivor.py` — PR 9
  fixture; PR 10 test 1 consumes data (FIX_SINGLE).
- `tests/corpus/fixtures/fix_multi_match.py` — PR 9 fixture;
  PR 10 test 2 consumes data (FIX_MULTI).
- `tests/corpus/fixtures/fix_no_keyword_match.py` — PR 9
  fixture; PR 10 test 3 consumes data (FIX_NO_KW) — the
  authored/observed divergence proof case lands here as a
  structured `DivergenceReport` claim.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; PR 10 contributes:
  - Gate-3-LOCAL governing sentence travel corroboration for
    candidate carrier #16 (≥3 of ≥4 surfaces required for
    Gate 3 close promotion evaluation per Gate 3 framing
    §6.1).
  - Potentially a fourth Step N.5 surgical cadence
    corroboration instance if mid-flight guidance surfaces.
  - Potentially candidate cleanup-pressure-resistance class
    member 10+ at PR 10 close if a new pressure form
    surfaces under genuinely independent recomposition
    conditions.

---

## Resume protocol — what the next session does with this spec

1. **Read §0 + §4.1 + §4.2 + §4.3 + §5.1 + §6 Step 1.** §0
   is the verbatim block authority — copy carriers + binding
   statements from here into the implementation surfaces.
   §4.1 + §4.2 + §4.3 are the file-level shape contracts —
   each implementation step derives directly from one or two
   of these sections. §5.1 is the test inventory. §6 Step 1
   is the immediate next action.

2. **Confirm state.** HEAD at `8ad7fe9` (PR 10 framing landed);
   parity with origin/main; clean working tree (only AGENTS.md
   untracked, ignore). Test count baseline: 207 forge env /
   201 forge-bridge env.

3. **Begin Step 1.** Create `forge_bridge/corpus/_compare.py`
   skeleton per §4.1. **No test-file modifications** per §4.4
   amendment 2026-05-11 (corpus-subtree auto-exclusion handles
   `_compare.py` without an `_ALLOWLIST` entry). Atomic commit
   is single-file. Verification per §6 Step 1.

4. **Advance through Steps 2–5 per §6.** The natural pause
   points (§6 closing prose) are checkpoint surfaces for
   verbatim-travel verification + carrier-travel drift
   detection + amendment-at-incarnation surfacing.

5. **Watch for the canonicalization trigger.** §4.3.3
   trigger-condition language fires if the implementer
   deviates from §4.1.6 reference implementation in a way
   that introduces pre-comparison string processing. If the
   trigger fires, ship the conditional 6th test +
   register the spec amendment per §4.3.3 routing.

6. **PR 10 close artifact** (`A.5.3.2-PR10-CLOSE.md`) drafts
   as a distinct subsequent commit after Step 5 verification.
   Gate 3 close artifact does NOT ship at PR 10 close — it
   ships at PR 11 final commit per Gate 3 framing §11. PR 10
   close §6 reports archaeology-grade test counts +
   architectural success signal verification + cleanup-
   pressure-resistance class additions (if any) + Gate-3-LOCAL
   travel count corroboration.
