# A.5.3.2 PR 8 — Spec (seed driver + authored-expectation helper)

**Status:** drafted 2026-05-10 (post-PR-8-framing session). Derived
from `A.5.3.2-PR8-FRAMING.md` (commit `23f2a20`). The framing is
the binding pre-spec contract; this spec is the implementation
contract derived from it. Boundary-shaped work per Gate 2 framing
§5.7 — full three-round review applies across the entire PR.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants (I-1 through I-6).
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1, Properties A–D); helper signature
  (§5.2); architecturally prohibited patterns (§5.3).
- `A.5.3.2-PR3-SPEC.md` — persistence layer; atomic-append
  discipline (§6.5); orthogonal-truth-surfaces framing (§5).
- `A.5.3.2-PR4-CLOSE.md` (`fab26cb`) — risk-category shift;
  integration-discipline quartet; "what PR N+1 inherits"
  archaeology shape.
- `A.5.3.2-PR5-CLOSE.md` (`b8f522e`) — surface geometry asymmetry;
  chain-step integration durable archival state.
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Layer 3 lint; Gate 1
  closure; truth-vs-mechanism distinction (informs `_seed.py`
  governance docstring shape).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level architecture;
  §3.4 three-authority-surface partitioning (PR 8 closes the third
  surface); §4.1 Model A locked; §4.4 companion records (truth-
  partitioning, not duplication); §5.3 Q1.6 companion records +
  dedicated expectation helper locked; §5.5 module siting
  (`_seed.py`); §5.7 PR partitioning (PR 8 = boundary work, full
  three-round); §6.1 carrier #14; §6.2 binding framing
  clarification; §7 six non-acquisition commitments; §8.1 Layer 1
  extension; §8.2 Layer 2 extension; §8.3 Layer 3 unchanged.
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — §6 cleanup-pressure-
  resistance class (introduced at PR 7; PR 8 contributes members
  #7 + #8); §7 seven non-acquisition commitments (preserved into
  PR 8 plus PR 8 adds one — chain-step seeding).
- `A.5.3.2-PR7-SPEC.md` (`84392d2`) — §4.2.4 `seed_dispatch_scope`;
  §4.2.6 `_persist_expectation_record` (the two symbols `_seed.py`
  may import); §7 phase-end conditions (rejection table preserved
  into PR 8 — PR 8 may not propose any of those mutations even
  incidentally).
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — durable archival state PR 8
  inherits; §2 "what PR 8 inherits from PR 7" (the seam contract);
  §3 "what PR 8 changes" (this spec operationalizes that section);
  §1.2 cleanup-pressure-resistance class inventory (6 members at
  PR 7 close; PR 8 grows to 8); §5 methodology observations
  (close-authors-inheritance / framing-consumes-inheritance
  cadence — this spec consumes the inheritance directly rather
  than re-deriving it from session history).
- **`A.5.3.2-PR8-FRAMING.md`** (`23f2a20`) — binding pre-spec
  contract. §0 carrier #15 (chat-handler-only seeding scope); §5
  six binding decisions (Q1 invocation path, Q1' surface scope,
  Q2 minimum-viable expectation shape, Q3 helper signature, Q4
  driver shape, Q5 `__all__` deferral); §6 two new cleanup-
  pressure-resistance class members (#7 companion-records-as-
  truth-partitioning; #8 `emit_seed_expectation`-as-semantics-
  not-topology); §7.3 ontological quartet (four explicit non-
  decisions); §8 Layer 1/2/3 extension specifications; §9 twelve
  phase-end rejection rows. Mandatory predecessor read.
- `project_pr8_base_expectation_args.md` (local memory) — flagged
  expectation: `base_expectation_args` test helper lands at PR 8,
  not at incarnation-time discovery. Consumed at framing §4.4;
  this spec §4.4 articulates the helper's exact form.

**Successor (NOT this spec):** PR 9 spec — fixtures + integration
tests. PR 8 ships the seed-driver seam PR 9 consumes; PR 8 does
not draft fixture format, fixture-loading surface, or integration
test scaffolding.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Eighteen sentences travel verbatim into PR 8's surface. Fifteen
are numbered carriers — fourteen inherited from PR 7 (the same
set Gate 2 framing locks at §3.1 and PR 7 ships in production at
`forge_bridge/corpus/_capture.py:6–135`) and one new at PR 8
framing time (carrier #15, framing §0). One is the binding
framing clarification on call-site-owned arbitration inputs
(Gate 2 framing §6.2). The remaining two are PR 8-local binding
statements derived from this convergence pass: the member #7
protection (companion records as truth-partitioning) and the
member #8 protection (`emit_seed_expectation` as semantics-not-
topology). The PR 8-local statements are not numbered carriers —
their scope is internal to the new module's documentation — but
their language is binding.

The sentences travel into:

1. `forge_bridge/corpus/_seed.py` module docstring. **Carrier #15
   lands at the top of the carrier block** (most-current PR-
   anchored governance text first per the relevance-by-file
   ordering PR 7 close §1.5 establishes); then carriers #1–#14
   in their inherited numbered order; then the binding framing
   clarification; then both PR 8-local statements.
2. `emit_seed_expectation`'s docstring (member #8 protection
   statement inline as the semantics-not-topology guard at the
   helper's authority surface).
3. `drive_seed_fixture`'s docstring (carrier #15 inline as the
   chat-handler-only scope guard at the orchestration surface).
4. Top-level docstring of `tests/corpus/test_pr8_seed_surface.py`
   (carriers #1–#15; per-test-file carrier blocks stay slim
   because tests are not production surfaces — the module name
   and the test names carry the contract; the docstring carries
   the inherited governance).
5. The PR 8 commit message body under "preserved invariants" /
   "new carrier introduced" / "cleanup-pressure-resistance class
   additions" — all eighteen sentences in their full form.

A reader who encounters `_seed.py` without reading the full spec
should encounter carrier #15 first (the chat-handler-only scope
governance), then the inherited carriers + binding framing
clarification, then the two PR 8-local protections. The ordering
makes the new authority surface's governance immediately legible
without obscuring the inherited contract.

PR 7's two PR-7-LOCAL binding pairs (§4.2 inert-parameter, §5.5
legacy-synthesis) do NOT travel into PR 8 surfaces — they remain
scope-local to `_capture.py` and `reader.py` respectively. PR 7
close §2.1 names this explicitly: PR-N-LOCAL pairs do not
regenerate.

### Inherited carriers (verbatim)

The fourteen inherited carriers + the binding framing
clarification are reproduced here in the same order they land in
the source-of-truth artifacts (PR 7 spec §0 for #1–#14; Gate 2
framing §6.1 for #14 specifically; Gate 2 framing §6.2 for the
clarification). Production-truth source: `forge_bridge/corpus/
_capture.py:6–135`.

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
> completed arbitration observations, not provisional intermediate
> state.**

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

**#14 — declared epistemic class vs. persisted provenance
(Gate 2):**

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

### PR 8 new carrier (verbatim)

**#15 — chat-handler-only seeding scope (PR 8):**

> **PR 8 seeds the chat-handler observation surface only. Chain-
> step seeding is explicitly deferred because `handlers.py` and
> `_step.py` produce semantically distinct observation records.
> Cross-surface expectation semantics require a dedicated framing
> pass before implementation proceeds.**

The third clause is governance, not explanation: any future PR
proposing chain-step seeding must produce a framing artifact
defining cross-surface expectation semantics BEFORE implementation
proceeds. Implementation-first work on chain-step seeding is
rejected at the spec layer.

The carrier travels at TWO operational placement sites in PR 8's
delta (in addition to its `_seed.py` module docstring presence):

- **`drive_seed_fixture`'s docstring** — inline as the chat-
  handler-only scope guard. The orchestration surface IS the
  surface a future contributor would reach for to "just add
  chain-step driving"; the carrier's verbatim presence at the
  function's docstring puts the protection at the proposal site.
- **`tests/corpus/test_pr8_seed_surface.py`'s top-level docstring**
  — the test module's contract is grounded in the carrier's
  verbatim presence; the test asserting the driver does not
  invoke chain-step (§3 risk #3) is the mechanical enforcement.

### PR 8-local binding statements

Two statements anchor the cleanup-pressure-resistance class
members PR 8 contributes to the architectural class introduced at
PR 7 framing §6. Each statement IS the load-bearing protection;
the framing's three-part rationale structure (local simplification
pressure → hidden truth collapse → protected architectural
property) is preserved at every operational placement site.

**Member #7 protection — companion records as truth-partitioning
(verbatim, scope-local to `_seed.py` + `emit_seed_expectation`):**

> **A unified "richer" record appears mechanically simpler because
> it collapses authored expectation and observed arbitration into
> one persistence surface. The simplification is false: it
> destroys falsifiability by allowing expectation and observation
> to co-author the same artifact.**

The framing's §6.1 names this protection in full. The verbatim
statement above is the load-bearing middle clause (the "hidden
truth collapse" portion of the three-part structure). Operational
placement: `_seed.py` module docstring carries Gate 2 framing
§4.4 paragraphs (the truth-partitioning architectural framing)
plus this verbatim statement (the cleanup-pressure protection).
The schema validator's expectation-branch rejection of records
carrying a `source` field is the mechanical enforcement at the
persistence boundary; this statement names the rejection as a
falsifiability protection, not merely a structural rule.

**Member #8 protection — `emit_seed_expectation` as semantics-not-
topology (verbatim, scope-local to `_seed.py` +
`emit_seed_expectation`):**

> **Inlining persistence into `emit_seed_expectation` appears
> symmetrical with `emit_divergence_capture` but silently
> transfers persistence-topology authority into a semantics-scoped
> helper. The separation is protected because authored expectation
> and persistence topology are intentionally distinct authority
> surfaces.**

The framing's §6.2 names this protection in full. The verbatim
statement above is the load-bearing middle clause. Operational
placement: `emit_seed_expectation`'s docstring carries this
statement inline as the helper's authority guard;
`_seed.py`'s module docstring restates the authority-surface
distinction; the PR-8-local participation discipline test
(`test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS` + AST
walker) enforces mechanically — `_seed.py` is permitted to
import two authority surfaces (`seed_dispatch_scope` +
`_persist_expectation_record`) plus three universal-key utilities
(`_now_iso_ms`, `_new_uuid`, `SCHEMA_VERSION`); the participation
contract is semantic, not cardinal — the bright line rejects
persistence-topology authority (`_build_capture_record`,
`_resolve_corpus_dir`, `_make_header`, `_serialize_line`, direct
file I/O), not cardinal symbol counts. A future PR attempting to
inline persistence would either need a new admission to
`_SEED_PERMITTED_IMPORTS` (visible at review) or violate the
existing AST walker enforcement (mechanically caught).

The two PR 8-local statements protect against the symmetric
failure modes that surface when a new authority partitioning
lands: collapsing the partition either DOWNWARD (member #7 —
merging the two record kinds) or LATERALLY (member #8 — blurring
the helper/seam boundary). Both protections are operational at
PR 8 close; both class members are documented inline at every
protection site.

---

## 1. Real job + success condition

**Real job:** *"Land the seed-driver authority surface for Gate 2.
Ship `forge_bridge/corpus/_seed.py` containing two helpers: a
single `emit_seed_expectation(...)` helper that authors a declared
expectation record (semantics-not-topology per Gate 2 framing
§5.3 + member #8), and a single `drive_seed_fixture(...)` function
that orchestrates one fixture invocation — building the
expectation, persisting it via the helper, opening
`seed_dispatch_scope`, invoking `chat_handler` directly in-
process, exiting the scope. Add a PR-8-local mechanical
enforcement test in `tests/corpus/test_pr8_seed_surface.py` with
a `_SEED_PERMITTED_IMPORTS` constant + AST walker scoped to
`_seed.py`; the constant admits two authority surfaces
(`seed_dispatch_scope`, `_persist_expectation_record`) plus three
universal-key utilities (`_now_iso_ms`, `_new_uuid`,
`SCHEMA_VERSION`). The participation contract is semantic, not
cardinal — the bright line rejects persistence-topology authority
(`_build_capture_record`, `_resolve_corpus_dir`, `_make_header`,
`_serialize_line`, direct file I/O), not cardinal symbol counts.
`test_pr4_participation_creep.py` is unchanged — its protected
property (narrowing-subsystem → corpus discipline) is orthogonal
to PR 8's `_seed.py` import boundary. Extend the schema
validator's `record_kind == "expectation"` branch with the three
PR 8-required fields (`fixture_id`, `prompt`, `expected_narrow`)
plus per-field type validation. Add `base_expectation_args` to
`tests/corpus/_pr3_helpers.py` per the `base_writer_args` /
`base_builder_args` precedent. Ship the new test module
`tests/corpus/test_pr8_seed_surface.py` exercising the helper +
driver + PR-8-local participation discipline + schema validator
extension + carrier #15 enforcement + `__all__` drift guard.
Layer 1 admission is structural (no `_ALLOWLIST` text changes —
`_seed.py` lives inside `corpus/`, which the discipline test
pre-filters per PR 7 spec §4.5 amendment). Layer 3 lint is
unchanged. PR 8 seeds the chat-handler observation surface only —
carrier #15 governs. `_seed.py` is a corpus-adjacent
orchestration surface whose purpose is to drive the live
arbitration surface in-process; it is the exception surface, not
a generalized corpus → console direction."*

PR 8's three operational responsibilities:

- **Author the authored-expectation surface.** A new public-
  from-corpus helper `emit_seed_expectation(...)` that captures
  the truth claim *"this is what the fixture-author declares the
  arbitration outcome should be."* Distinct signature from
  `emit_divergence_capture` per framing §5.4. Delegates
  persistence to the PR 7 seam (`_persist_expectation_record`).
  The helper's docstring carries the member #8 verbatim
  protection statement.
- **Wire the orchestration surface.** A new public-from-corpus
  function `drive_seed_fixture(...)` that orchestrates one
  fixture invocation. The driver invokes `chat_handler` directly
  in-process (Q1 lock); does NOT invoke chain-step (carrier #15
  governs); does NOT build the expectation record dict directly
  (delegates to `emit_seed_expectation` per member #8 protection).
  The driver's docstring carries the carrier #15 verbatim guard.
- **Extend the structural-test discipline mechanically.** A new
  PR-8-local participation discipline test
  (`test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS` + AST
  walker) admits `_seed.py → {seed_dispatch_scope,
  _persist_expectation_record, _now_iso_ms, _new_uuid,
  SCHEMA_VERSION}` — two authority surfaces plus three universal-
  key utilities. The participation contract is semantic, not
  cardinal; the bright line is persistence-topology rejection,
  not symbol-count enforcement.
  `tests/corpus/test_pr4_participation_creep.py` is unchanged —
  its protected property (narrowing-subsystem → corpus
  one-directional flow) is orthogonal to PR 8's `_seed.py` import
  boundary, and conflating them would weaken both. Layer 1
  admission is structural (no text changes). Layer 3 unchanged
  (no new `emit_divergence_capture` call sites in PR 8's delta).
  Schema validator extends additively with the expectation-
  branch required-keys check.

Plus one PR-8-internal-but-Gate-4-bound deliverable: extending
the schema validator's `record_kind == "expectation"` branch with
required-keys-for-expectation. PR 7 close left this as a deferred
extension (per `_schema.py:225–228` inline comment); PR 8
operationalizes it because PR 8 is the first PR to construct
expectation records. The extension is purely additive —
observation-record validation is unchanged; PR 7's
`test_pr7_record_kind_schema.py` and reader tests remain green.

**Success condition:** *"PR 8 ships `_seed.py` (new), the schema
validator extension in `forge_bridge/corpus/_schema.py`, the
`base_expectation_args` helper in `tests/corpus/_pr3_helpers.py`,
and the new test module `tests/corpus/test_pr8_seed_surface.py`
exercising the helper + driver + PR-8-local participation
discipline (`_SEED_PERMITTED_IMPORTS` + AST walker) + schema
validator extension + carrier #15 enforcement + `__all__` drift
guard. `test_pr4_participation_creep.py` ships unchanged.
The Layer 3 lint (`tests/corpus/test_pr6_visual_asymmetry.py`)
ships unchanged and passes against the post-PR-8 codebase. PR 4
+ PR 5 + PR 7 integration tests pass unchanged under all four
capture states. PR 8 seeds `chat_handler` only; no
`_step.py:233` driver path lands; the test suite asserts
mechanically. The fifteen carriers + binding framing
clarification + two PR 8-local binding statements travel verbatim
into `_seed.py` module
docstring + `emit_seed_expectation` docstring + `drive_seed_
fixture` docstring + the new test module docstring + the PR 8
commit message body. `forge_bridge.__all__` membership is
unchanged at v1.4.1 baseline (19 symbols); neither PR 8 helper
enters `__all__`. Full three-round review applies across the
entire PR per Gate 2 framing §5.7."*

**Operator-visible behavior change:** none in production paths.
The new module `_seed.py` is consumed by no production call site
in PR 8's delta. The schema validator's expectation-branch
required-keys check fires only on records carrying
`record_kind="expectation"` — and the only callers that produce
such records (post-PR 8) are PR 8's own helpers + PR 9's future
fixtures. Live arbitration emissions from `chat_handler` and
`chain_step` are observation records (`record_kind="observation"`)
and remain unaffected.

---

## 2. Scope

**In scope:**

- **New production module** —
  `forge_bridge/corpus/_seed.py`. Houses the seed-driver authority
  surface per §4.1 + §4.2:
  - `emit_seed_expectation(...)` — public-from-corpus
    authored-declaration helper; signature locked at framing
    §5.4 (Q3); delegates persistence to
    `_persist_expectation_record`.
  - `drive_seed_fixture(...)` — public-from-corpus orchestration
    function; signature locked at framing §5.5 (Q4); invokes
    `chat_handler` directly in-process.
  - Module docstring carrying carrier #15 (top), carriers #1–#14
    + binding framing clarification (inherited block), and both
    PR 8-local binding statements (member #7 + #8 protections).
- **Modified production module** —
  `forge_bridge/corpus/_schema.py`:
  - `_REQUIRED_EXPECTATION_KEYS: Final[frozenset[str]] =
    frozenset({"fixture_id", "prompt", "expected_narrow"})`
    constant added.
  - `validate_capture_record`'s `record_kind == "expectation"`
    branch extended with the required-keys check + per-field
    type validation per §4.3. The existing no-source check
    (lines 220–224) is preserved unchanged. The extension is
    additive — observation-record validation is unchanged.
- **Modified test infrastructure** —
  `tests/corpus/_pr3_helpers.py`:
  - `base_expectation_args(**overrides) -> dict[str, Any]` added
    per §4.4. Sibling of `base_writer_args` and
    `base_builder_args`. Returns ONLY the three PR 8-required
    kwargs (`fixture_id`, `prompt`, `expected_narrow`) — does
    NOT layer on `base_writer_args` because expectation records
    have a structurally distinct shape (no `source`, no
    arbitration-state fields, no nested `narrower` block).
- **Verified test discipline files** (no modifications):
  - `tests/corpus/test_pr3_discipline.py` — **no code changes.**
    Per PR 7 spec §4.5 amendment, `_ALLOWLIST` is the
    **permission-to-import-corpus** boundary, not the
    **admission-into-corpus** boundary. `_seed.py` is admitted
    into corpus by virtue of living in the `corpus/` subtree
    (which the discipline test pre-filters before consulting
    `_ALLOWLIST`). Step 1 (§6) verifies the discipline test
    passes with `_seed.py` present — confirming the corpus-
    subtree filter still behaves correctly after the new file
    lands.
  - `tests/corpus/test_pr4_participation_creep.py` — **no code
    changes.** Per the spec amendment captured at §4.5, the
    PR 4 test enforces narrowing-subsystem → corpus
    one-directional flow (a different protected property than
    PR 8's `_seed.py` import boundary). The framing's §8.2
    language ("extend `_PERMITTED_CORPUS_IMPORTS`") was
    conceptually right but file-wrong — the existing
    enforcement topology must be grounded in the actual test
    surface, not inferred from naming symmetry. PR 8's
    mechanical enforcement lives in
    `tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS`
    + an AST walker scoped to `_seed.py`. The PR 4 test stays
    untouched; its protected property is preserved.
- **New test module** —
  `tests/corpus/test_pr8_seed_surface.py`:
  - 14 tests covering: schema validator extension (4 tests),
    `emit_seed_expectation` helper (3 tests),
    `drive_seed_fixture` driver (4 tests), PR-8-local
    participation discipline (2 tests — `_SEED_PERMITTED_IMPORTS`
    constant regression + AST walker enforcement),
    `__all__` drift guard (1 test). Final inventory at §5.1.
  - Houses `_SEED_PERMITTED_IMPORTS: frozenset[str]` constant
    + `_corpus_references` AST walker (mirrors the PR 4 test's
    `_corpus_references` shape but scoped to a single source
    file and a different protected property — see §4.6).

**Inheritance from PR 7 (binding):**

> **PR 8 introduces no new dispatch-provenance substrate, no new
> observation-record schema, and no new Layer 3 lint surface.
> PR 7's `seed_dispatch_scope` + `_persist_expectation_record` +
> `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS` ship unchanged.
> PR 6's Layer 3 lint enforcement remains unchanged and is
> inherited transitively.**

This sentence resolves the question of why PR 8 has no §5
("Property + rejection validators") — the substrate it would
govern already ships in PR 7. PR 8's mechanical enforcement is
PR-8-local participation discipline (two regression-asserted
tests scoped to `_seed.py` only) plus the additive schema-
validator extension; both are derivative of PR 7's substrate,
not new substrate themselves.

**Out of scope** (per framing §7 + carrier #15 + Q5 deferral):

1. **Seeding the chain-step observation surface.**
   `forge_bridge/console/_step.py:233` is not driven by any
   PR 8 surface. Carrier #15 governs. The driver's test suite
   asserts mechanically (§3 risk #3). Cross-surface expectation
   semantics require a dedicated framing pass; PR 8 does not
   draft, prefigure, or scaffold that pass.
2. **Concrete seed fixtures.** PR 8 ships ZERO concrete
   fixtures. The driver function is callable; PR 9 will call it
   with fixtures. PR 8's tests construct minimal-shape kwargs
   inline (via `base_expectation_args`) — not as a fixture
   format, fixture-loading surface, or `list[SeedFixture]`
   scaffolding.
3. **Integration tests.** End-to-end tests demonstrating
   observation + expectation composition under real seeded
   execution are PR 9's domain. PR 8's tests are unit-shaped:
   helper signature validation, driver invocation path
   verification, Layer 2 admission verification, schema
   validator extension verification.
4. **`forge_bridge.__all__` promotion.** Neither
   `emit_seed_expectation` nor `drive_seed_fixture` enters
   `forge_bridge.__all__` at PR 8. Q5 lock per framing §5.6.
   The `__all__` drift guard test (§3 risk #6) enforces
   mechanically; the regression target is the v1.4.1 baseline
   count (19 symbols).
5. **Modifying `_capture.py`, `_schema.py` source-class
   validation, `_sources.py`, or `reader.py`.** PR 7's
   deliverables are locked. PR 8 only extends `_schema.py`'s
   expectation-branch validator — and that extension is
   additive (adds required-keys + type validation), not a
   modification of existing observation-record validation or
   `KNOWN_SOURCE_VALUES`-aware source validation.
6. **Touching the Layer 3 lint.**
   `tests/corpus/test_pr6_visual_asymmetry.py` ships unchanged.
   Layer 3's discovery walk finds calls to
   `emit_divergence_capture` only. PR 8 introduces zero new
   `emit_divergence_capture` call sites; `emit_seed_expectation`
   and `drive_seed_fixture` are not in the lint's discovery
   scope (per Gate 2 framing §8.3 binding decision).
7. **Surface-explicit driver naming.** A future PR proposing
   to rename `drive_seed_fixture` to `drive_chat_handler_fixture`
   (or any surface-explicit name) without a framing artifact is
   rejected at the spec layer per framing §5.5 (Q4) + carrier
   #15. The generic name preserves option-space about how the
   future chain-step-seeding framing pass resolves the
   ontological questions (framing §7.3); renaming forecloses
   that pass's authority.
8. **Companion-records collapse into a unified record.** A
   future PR proposing to merge observation and expectation
   into a single richer record is rejected at the spec layer
   per cleanup-pressure-resistance class member #7 + Gate 2
   framing §4.4. The truth-partitioning is the comparator's
   foundation; merging the records erodes Gate 4's
   architecture.
9. **Inlining persistence into `emit_seed_expectation`.** A
   future PR proposing to inline `_persist_expectation_record`'s
   body into `emit_seed_expectation` ("for symmetry with
   `emit_divergence_capture`") is rejected at the spec layer
   per cleanup-pressure-resistance class member #8 + Gate 2
   framing §5.3. The helpers' asymmetry is structural;
   collapsing it erodes the three-authority-surface
   partitioning.
10. **HTTP transport for the driver.** A future PR proposing
    to drive seed fixtures via HTTP instead of in-process is
    rejected at the spec layer per framing §5.1 (Q1) +
    carriers #3–#6. The arbitration pipeline is the thing
    being measured; transport is incidental.
11. **Adding a fourth required field to expectation records.**
    A future PR proposing to add a fourth required field
    (`label`, `expected_ambiguity_state`, `expectation_author`,
    etc.) inside a cleanup PR is rejected at the spec layer
    per framing §5.3 (Q2) minimum-viable lock. Expectation-
    record shape changes require framing-level review; Gate 4
    will surface concrete needs at comparator-write time.
12. **Acquiring persistence-topology authority in
    `_SEED_PERMITTED_IMPORTS`.** A future PR proposing to admit
    a persistence-topology symbol to `_SEED_PERMITTED_IMPORTS`
    (e.g., `_build_capture_record`, `_resolve_corpus_dir`,
    `_make_header`, `_serialize_line`, or any direct file-I/O
    surface) is rejected at the spec layer per cleanup-pressure-
    resistance class member #8 + framing §8.2 + the spec amendment
    captured at §4.5/§4.6. The participation contract is
    semantic, not cardinal — admitting a universal-key utility
    sibling (e.g., a future deterministic-ID generator at PR 9)
    is a different question and routes through framing review;
    admitting a persistence-topology symbol is rejected outright.
13. **Other corpus modules importing from `forge_bridge.console`.**
    PR 8's `_seed.py` is the orchestration-surface exception —
    its purpose is to drive the live arbitration surface in-
    process, and carrier #15 governs the scope of that exception.
    No other corpus module (`_capture.py`, `_schema.py`,
    `_sources.py`, `_identity.py`, `_topology.py`, `reader.py`,
    or future corpus modules) may acquire a `forge_bridge.console`
    import without framing-level review. PR 8 does not generalize
    the inversion; `_seed.py` is the exception surface, not a
    generalized corpus → console direction. Mechanical
    enforcement of this commitment is deferred to a future
    framing question (planted as a governance seed for v1.6+);
    PR 8's discipline is spec-language + cleanup-PR review.

---

## 3. The six risks → named tests

PR 8's risk topology differs from PR 7's. PR 7 was plumbing
work — the risks were *the substrate leaking semantics across
boundaries* and *the substrate eroding under cleanup pressure*.
PR 8 is boundary work — the risks are *the new authority surface
getting blurred against existing surfaces* (observation,
dispatch provenance) or *against the cleanup-pressure class*.
Every risk maps to a structural property the tests preserve
mechanically.

Each of the six named risks maps to a named test that fires
when the risk materializes:

| # | Risk | Failure mode | Named test |
|---|---|---|---|
| 1 | **Helper-singularity smearing (member #8 surface).** A future PR widens `emit_seed_expectation`'s signature with arbitration-state fields, optional kwargs, a return value, or a `source` parameter — eroding the semantics-not-topology guard. The helper begins behaving like a thin observation-helper variant. | Test asserts `inspect.signature(emit_seed_expectation)` has exactly 3 keyword-only parameters (`fixture_id`, `prompt`, `expected_narrow`), each without a default value, and the return annotation is `None`. The signature shape IS the truth claim; widening it would silently broaden the authority surface. | `test_pr8_seed_surface.py::test_emit_seed_expectation_signature_is_authority_pure` |
| 2 | **Companion-records collapse pressure (member #7 surface).** A future PR proposes (or accidentally introduces) a unified record carrying both expectation and observation fields. The schema validator must reject the unified shape mechanically — the merged record would destroy falsifiability by allowing expectation and observation to co-author the same artifact. | Test constructs an expectation record carrying a `source` field (the canonical observation-record marker); asserts `validate_capture_record` raises `SchemaValidationError`. Sibling test constructs an expectation record missing one of the three PR 8-required keys; asserts `validate_capture_record` raises `SchemaValidationError` naming the missing key. | `test_pr8_seed_surface.py::test_expectation_record_rejects_observation_fields` + `::test_expectation_record_requires_three_keys` |
| 3 | **Carrier #15 breach.** The driver invokes `chat_handler` with a multi-step prompt that internally fires `_step.py:233`, eroding the chat-handler-only scope. A future PR may introduce a fixture shape that drives chain-step indirectly without the driver's signature changing. | The test invokes `drive_seed_fixture(...)` directly with canonical single-step fixture shapes (via `base_expectation_args()`) while patching the `_step.py` chain-step entry point with a sentinel. The sentinel asserts that chain-step arbitration was not invoked during those seeded driver executions. The scope is local orchestration-boundary enforcement (the tests assert what the driver does), not global suite surveillance. | `test_pr8_seed_surface.py::test_driver_does_not_invoke_chain_step` |
| 4 | **Authority-surface inversion in the driver.** `drive_seed_fixture` builds the expectation record dict directly — bypassing `emit_seed_expectation` — collapsing the helper/driver authority partitioning. The orchestration surface acquires authored-semantics authority. The test protects against orchestration-layer collapse into authored-semantics authority. | Test patches `emit_seed_expectation` with a sentinel; invokes `drive_seed_fixture(**base_expectation_args())`; asserts the sentinel was called exactly once with the exact 3-kwarg shape (no positional args, no extra kwargs, no missing kwargs). The driver delegating to the helper is structurally load-bearing, not stylistic. | `test_pr8_seed_surface.py::test_driver_emits_expectation_through_helper` |
| 5 | **PR-8-local participation discipline drift.** A future PR adds a persistence-topology symbol to `_SEED_PERMITTED_IMPORTS` (e.g., `_build_capture_record` "for symmetry," `_resolve_corpus_dir` "to inline persistence", `_make_header`, `_serialize_line`), or `_seed.py` acquires an actual import outside the allowlist. The bright line is semantic, not cardinal — the protection is rejection of persistence-topology authority, not enforcement of an exact symbol count. Both drift modes (allowlist value drift + actual import drift) are independently catchable; both tests are needed. | **Test 5a (allowlist value regression):** asserts `_SEED_PERMITTED_IMPORTS` is exactly `frozenset({"forge_bridge.corpus._capture.seed_dispatch_scope", "forge_bridge.corpus._capture._persist_expectation_record", "forge_bridge.corpus._capture._now_iso_ms", "forge_bridge.corpus._capture._new_uuid", "forge_bridge.corpus._schema.SCHEMA_VERSION"})` — fires on growth, shrinkage, or substitution. **Test 5b (AST walker enforcement):** parses `forge_bridge/corpus/_seed.py`; extracts every `forge_bridge.corpus.<X>` reference; asserts every reference is in `_SEED_PERMITTED_IMPORTS`. Fires on `_seed.py` actually importing a forbidden symbol (e.g., `_build_capture_record`). | `test_pr8_seed_surface.py::test_seed_module_permitted_imports_locked` (5a) + `::test_seed_module_imports_match_permitted_set` (5b) |
| 6 | **Public-API drift inside a cleanup PR.** A future PR promotes `emit_seed_expectation` or `drive_seed_fixture` to `forge_bridge.__all__` "because consumers might want it," bypassing the §5.6 deferral that requires a concrete external consumer to surface first. Each `__all__` entry is authority-surface expansion (per PR 7 spec §7 close conditions); silent promotion is exactly the kind of cleanup-PR-shape this risk exists to reject. | Test imports `forge_bridge`; asserts `"emit_seed_expectation" not in forge_bridge.__all__` and `"drive_seed_fixture" not in forge_bridge.__all__`; additionally asserts `len(forge_bridge.__all__) == 19` (the v1.4.1 baseline count). Counter-asserts protect against both targeted promotion and silent baseline drift. | `test_pr8_seed_surface.py::test_pr8_helpers_remain_corpus_internal` |

The six risks map to PR 8's load-bearing architectural
protections: helper authority partitioning (#1, #4), companion-
records truth partitioning (#2), carrier #15 governance (#3),
PR-8-local participation discipline (#5), public-API deferral
(#6). No test in this list validates content; every test
validates structural property preservation.

Risks #1, #4, and #5 are **structurally co-named with cleanup-
pressure-resistance class member #8**. The class member's
verbatim protection statement (§0 PR 8-local binding statement
#2) lives at three operational placement sites: the helper
docstring (member #8 inline guard), the `_seed.py` module
docstring, and the PR 8 commit message body. The named tests
enforce the protection mechanically across orthogonal boundaries
— helper signature shape (#1, one test), driver delegation (#4,
one test), and PR-8-local participation discipline (#5, two
tests: allowlist value regression + AST walker enforcement). The
two #5 tests are not redundant; they protect orthogonal drift
modes (constant value drift vs. actual import drift), and either
mode in isolation is invisible to the other test.

Risk #2 is **structurally co-named with cleanup-pressure-
resistance class member #7**. The class member's verbatim
protection statement (§0 PR 8-local binding statement #1) lives
at the `_seed.py` module docstring and the PR 8 commit message
body; the schema validator's no-source check enforces
mechanically.

Risk #3 is **structurally co-named with carrier #15**. The
carrier's verbatim text lives at three operational placement
sites (`_seed.py` module docstring, `drive_seed_fixture`'s
docstring inline, the test module's top-level docstring). The
test enforces the protection by patching the chain-step entry
point with a sentinel and asserting no invocation during seeded
driver executions.

Risk #6 enforces the §5.6 (Q5) `__all__` deferral mechanically;
its protection lives in the spec only (no docstring placement
needed — the test IS the protection).

---

## 4. Module surface

### 4.1 `forge_bridge/corpus/_seed.py` (new)

The seed-driver authority surface. Houses two public-from-corpus
helpers (`emit_seed_expectation` + `drive_seed_fixture`) plus one
private async helper (`_invoke_chat_handler_in_process` — see
§4.5 amendment for Path E rationale). Module docstring carries
all eighteen verbatim entries (15 carriers + binding framing
clarification + 2 PR 8-local statements) per §0.

#### 4.1.1 Module docstring (carrier block)

```python
"""forge_bridge.corpus._seed — seed driver + authored-expectation
helper.

This module is the seed-driver authority surface for Gate 2. It
houses two public-from-corpus helpers — ``emit_seed_expectation``
and ``drive_seed_fixture`` — that author declared expectations and
orchestrate single-fixture invocations through the chat-handler
arbitration pipeline. The module is consumed by PR 9 fixtures and
by future Gate 4 comparator regression tests; PR 8 ships zero
production call sites.

This module is a corpus-adjacent orchestration surface whose
purpose is to drive the live arbitration surface in-process. It
is the exception surface — not a generalized corpus → console
direction. No other corpus module may acquire a
``forge_bridge.console`` import without framing-level review (see
``A.5.3.2-PR8-SPEC.md`` §2 out-of-scope #13).

PR 8 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR8-SPEC.md`` §0):

PR 8 carrier #15 — chat-handler-only seeding scope (LANDS AT TOP
PER FRAMING §3.2 RELEVANCE-BY-FILE ORDERING):

  PR 8 seeds the chat-handler observation surface only. Chain-step
  seeding is explicitly deferred because handlers.py and _step.py
  produce semantically distinct observation records. Cross-surface
  expectation semantics require a dedicated framing pass before
  implementation proceeds.

Inherited carriers #1–#2 — risk-category shift (PR 4):
[verbatim text reproduced from ``forge_bridge/corpus/_capture.py``
lines 40–46.]

Inherited carriers #3–#6 — integration-discipline quartet (PR 4):
[verbatim, lines 48–56.]

Inherited carrier #7 — finalized-state contract (PR 4):
[verbatim, lines 58–63.]

Inherited carrier #8 — risk-inheritance + surface-geometry
distinction (PR 5):
[verbatim, lines 65–70.]

Inherited carrier #9 — caller's view of deployment identity
(PR 5):
[verbatim, lines 72–75.]

Inherited carrier #10 — ambiguity-as-arbitration-outcome (PR 5):
[verbatim, lines 77–85.]

Inherited carrier #11 — measured-not-inferred coverage (PR 5):
[verbatim, lines 87–92.]

Inherited carrier #12 — structural-backstop framing (PR 6):
[verbatim, lines 94–100.]

Inherited carrier #13 — observation-not-participation framing
(PR 6):
[verbatim, lines 102–108.]

Inherited carrier #14 — declared epistemic class vs. persisted
provenance (Gate 2):
[verbatim, lines 110–116.]

Binding framing clarification — call-site-owned arbitration inputs
(Gate 2):
[verbatim, lines 118–124.]

PR 8-local binding — companion records as truth-partitioning
(member #7 protection, scope-local to this module +
emit_seed_expectation):

  A unified "richer" record appears mechanically simpler because
  it collapses authored expectation and observed arbitration into
  one persistence surface. The simplification is false: it
  destroys falsifiability by allowing expectation and observation
  to co-author the same artifact.

  Operationally: observation records and expectation records are
  persisted as separate records in the same date-partitioned JSONL
  file, distinguished by record_kind, joined later by Gate 4's
  comparator on fixture_id. The schema validator rejects records
  carrying record_kind="expectation" and a source field at the
  persistence boundary; this module's helpers preserve the
  partition by construction (emit_seed_expectation persists
  record_kind="expectation" with no source field;
  emit_divergence_capture persists record_kind="observation" with
  source ∈ KNOWN_SOURCE_VALUES).

PR 8-local binding — emit_seed_expectation as semantics-not-
topology (member #8 protection, scope-local to this module +
emit_seed_expectation):

  Inlining persistence into emit_seed_expectation appears
  symmetrical with emit_divergence_capture but silently transfers
  persistence-topology authority into a semantics-scoped helper.
  The separation is protected because authored expectation and
  persistence topology are intentionally distinct authority
  surfaces.

  Operationally: emit_seed_expectation builds the expectation
  record dict and delegates persistence to
  _persist_expectation_record (the PR 7 seam). It does NOT call
  _resolve_corpus_dir, _make_header, _serialize_line, or any direct
  file I/O surface. The PR-8-local participation discipline test
  (tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS
  + AST walker) enforces mechanically. The participation contract
  is semantic, not cardinal — the bright line is rejection of
  persistence-topology authority, not enforcement of an exact
  symbol count.

This module implements the seed-driver portion of Gate 2 framing's
three-authority-surface partitioning (§3.4):

  - Observation surface (PR 7): emit_divergence_capture +
    contextvar resolution path. Unchanged by PR 8.
  - Dispatch provenance surface (PR 7): seed_dispatch_scope +
    _DispatchContext. Unchanged by PR 8 (this module CONSUMES the
    scope; it does not modify it).
  - Authored expectation surface (PR 8 — THIS MODULE):
    emit_seed_expectation + drive_seed_fixture +
    _invoke_chat_handler_in_process.

See ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 for the canonical record
shape, ``A.5.3.2-GATE-2-FRAMING.md`` §3.4–§5.7 for the gate-level
architecture, and ``A.5.3.2-PR8-FRAMING.md`` for the PR-level
binding decisions this module operationalizes.
"""
```

The module docstring is **~250 lines** at Step 1 landing. The
inherited 14 carriers + binding framing clarification follow the
existing PR 7 production text in `_capture.py:6–135` verbatim;
the spec body abbreviates with `[verbatim, lines N–M]` references
to avoid double-archiving the same governance text. PR 8's own
contributions (carrier #15 + 2 PR-8-local statements) are inlined
in full because they have no other production-truth source until
this module ships.

A reader who encounters `_seed.py` without reading the full spec
encounters carrier #15 first (most-current PR-anchored governance
text per relevance-by-file ordering), then the inherited block,
then the binding framing clarification, then the two PR-8-local
protections. The ordering makes the new authority surface's
governance immediately legible without obscuring the inherited
contract.

#### 4.1.2 Imports

```python
from __future__ import annotations

import asyncio
import json
import logging
import uuid as _uuid_module

from starlette.requests import Request

from forge_bridge.corpus._capture import (
    _new_uuid,
    _now_iso_ms,
    _persist_expectation_record,
    seed_dispatch_scope,
)
from forge_bridge.corpus._schema import SCHEMA_VERSION

logger = logging.getLogger(__name__)
```

Five `forge_bridge.corpus.*` symbol imports, mapped to
`_SEED_PERMITTED_IMPORTS` (§4.4.1):

- **Authority surfaces (2):** `seed_dispatch_scope` (consumed by
  the driver to activate seed provenance during chat_handler
  invocation), `_persist_expectation_record` (consumed by
  `emit_seed_expectation` to persist the authored expectation).
- **Universal-key utilities (3):** `_new_uuid` + `_now_iso_ms`
  (consumed by `emit_seed_expectation` to populate the
  `capture_id` and `captured_at` universal keys), `SCHEMA_VERSION`
  (consumed for the `schema_version` universal key).

The participation contract is **semantic, not cardinal.** The
bright line rejects persistence-topology authority
(`_build_capture_record`, `_resolve_corpus_dir`, `_make_header`,
`_serialize_line`, direct file I/O), not the cardinal symbol
count. Universal-key utilities and the governance constant are
infrastructural, not authority-bearing.

Stdlib + starlette imports are outside the participation contract
(`_SEED_PERMITTED_IMPORTS` scopes only `forge_bridge.corpus.*`
references). The `starlette.requests.Request` import is necessary
for Path E's chat_handler invocation (§4.1.4); starlette is
already an installed dependency (FastMCP transitively pulls it).

The `from forge_bridge.console.handlers import chat_handler`
import is **function-scoped** inside
`_invoke_chat_handler_in_process` (§4.1.4), not module-scoped.
This is structural: the import only fires when the driver is
actually invoked, which preserves the carrier-#15-governs scope
of the corpus → console exception. Module-scoped import would
fire on `_seed.py` import (e.g., during test collection),
broadening the exception's effective scope.

#### 4.1.3 `emit_seed_expectation(...)` public helper

```python
def emit_seed_expectation(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Persist an authored expectation record for a seed fixture.

    PR 8 SEMANTICS-NOT-TOPOLOGY GUARD (verbatim, load-bearing —
    see ``A.5.3.2-PR8-SPEC.md`` §0 PR 8-local binding statement
    #2):

      Inlining persistence into emit_seed_expectation appears
      symmetrical with emit_divergence_capture but silently
      transfers persistence-topology authority into a semantics-
      scoped helper. The separation is protected because authored
      expectation and persistence topology are intentionally
      distinct authority surfaces.

    Future contributors must not inline ``_persist_expectation_record``'s
    body into this helper, must not call ``_resolve_corpus_dir``
    or any direct file I/O surface from this helper, and must not
    add a ``source`` parameter or any arbitration-state parameter
    to this helper's signature. The cleanup-pressure-resistance
    class member #8 (``A.5.3.2-PR8-FRAMING.md`` §6.2) names the
    architectural protection; the PR-8-local participation
    discipline test
    (``tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS``)
    enforces mechanically.

    Args:
        fixture_id: REQUIRED keyword-only. The seed fixture
            identifier the expectation describes. Persisted as
            the ``fixture_id`` field on the expectation record.
        prompt: REQUIRED keyword-only. The single-step prompt
            text the fixture exercises. Persisted as the
            ``prompt`` field.
        expected_narrow: REQUIRED keyword-only. The list of tool
            names the fixture-author declares the narrowing
            decision should produce. Possibly empty (the empty
            list is a valid expectation — it expresses
            "expected zero-survivor narrowing for this prompt").
            Persisted as the ``expected_narrow`` field.

    Returns:
        ``None``. Failure-invisibility per I-6: any exception from
        record construction, schema validation (inside
        ``_persist_expectation_record``), or persistence is caught
        and logged at WARNING; nothing propagates. Defense in
        depth — ``_persist_expectation_record`` already wraps its
        body in I-6 internally; this helper's outer wrap is the
        belt-and-suspenders posture matching the corpus
        convention.
    """
    try:
        record = {
            "schema_version": SCHEMA_VERSION,
            "capture_id": _new_uuid(),
            "captured_at": _now_iso_ms(),
            "record_kind": "expectation",
            "fixture_id": fixture_id,
            "prompt": prompt,
            "expected_narrow": expected_narrow,
        }
        _persist_expectation_record(record)
    except Exception as exc:  # noqa: BLE001 — I-6 failure invisibility
        try:
            logger.warning(
                "emit_seed_expectation failed: fixture_id=%r, "
                "error=%s: %s",
                fixture_id,
                type(exc).__name__,
                exc,
            )
        except Exception:  # noqa: BLE001 — even logging must not propagate
            pass
    return None
```

The helper:
1. Builds the expectation record dict (4 universal keys +
   `record_kind="expectation"` + the 3 PR 8-required fields).
2. Calls `_persist_expectation_record(record)` — the PR 7 seam.
3. Returns `None` per I-6 fire-and-forget convention.

The helper does NOT:
- Take a `source` parameter (expectation records have no
  `source` field; the schema validator rejects expectation
  records carrying one).
- Take arbitration-state parameters (`narrower_decision`,
  `pr20_condition_met`, etc. — those are observation-record
  fields).
- Return the persisted record dict (signature returns `None`
  per Q3 lock).
- Call `_resolve_corpus_dir`, `_make_header`, `_serialize_line`,
  or any direct file I/O surface — persistence topology is
  delegated to the PR 7 seam.

#### 4.1.4 `_invoke_chat_handler_in_process(prompt)` private async helper

Path E resolution (§4.5 amendment): chat_handler is async and
takes a Starlette Request; the sync driver bridges via
`asyncio.run` + a hand-built minimal Request. This private async
helper encapsulates the bridge.

`_invoke_chat_handler_in_process` is a **real architectural seam**,
not an obscured implementation detail. It carries four concrete
seam roles:

1. **Sync → async bridge.** The sync driver (Q4 lock) reaches the
   async handler via `asyncio.run` invoking this helper. The
   bridge is named, isolated, and testable in isolation.
2. **Request-envelope reconstruction seam.** The minimal Starlette
   Request is constructed here (ASGI scope dict + injected body).
   The reconstruction is wrapping truth in the chat-handler
   protocol envelope, not synthesizing arbitration truth (carrier
   #6 preserved).
3. **Corpus → console exception seam.** The function-scoped
   `from forge_bridge.console.handlers import chat_handler` lives
   here. The exception's effective scope is the helper's
   invocation, not `_seed.py`'s import time.
4. **Carrier #15 enforcement seam.** The chat-handler-only scope
   is the helper's single concern; tests patch this helper or
   its target to assert chain-step is never invoked during seeded
   driver executions.

The leading underscore + module-private convention reflect
internal-API status (not in `__all__`, not in
`_SEED_PERMITTED_IMPORTS`), but the helper is structurally
visible — governance + tests protect it, not obscurity. A
nested-closure-inside-driver alternative was rejected: closure-
form obscures the four seam roles, prevents direct unit testing
of the bridge mechanics, and would force test 11
(`test_driver_invokes_chat_handler_in_process`) to patch
`chat_handler` indirectly through the closure's call site.

```python
async def _invoke_chat_handler_in_process(prompt: str) -> None:
    """Invoke chat_handler with a minimal in-process Request.

    Carrier #15 governs (verbatim, see module docstring): PR 8
    seeds the chat-handler observation surface only. Cross-surface
    expectation semantics require a dedicated framing pass before
    implementation proceeds.

    The corpus → console import (``from forge_bridge.console.handlers
    import chat_handler``) is function-scoped here, not module-
    scoped on ``_seed.py``. This is structural: the import only
    fires when the driver is invoked, preserving carrier #15's
    chat-handler-only scope. Module-scoped import would broaden
    the exception's effective scope to include test collection
    and any reflective import (e.g., ``importlib`` walks).

    Carrier #6 preserved (integration layer passes truth, not
    transport): the prompt + minimal protocol envelope (a single-
    user-message body) IS the chat-handler arbitration surface.
    The Request object is the protocol envelope, not arbitration
    truth; building it is wrapping the truth, not reconstructing
    it. The handler's internal arbitration logic — narrowing,
    tool dispatch, observation emission at handlers.py:1185 — is
    what the seed driver exercises.

    Args:
        prompt: The single-step prompt text. Wrapped in the
            canonical D-02 messages body shape:
            ``{"messages": [{"role": "user", "content": prompt}]}``.

    Returns:
        ``None``. The JSONResponse from chat_handler is
        intentionally ignored — the observation emission fires
        inside chat_handler's body BEFORE the response is built
        (per the existing call site at handlers.py:1185). The
        seed driver's interest is in the emission, not the
        response.
    """
    # Function-scoped import preserves carrier #15's chat-handler-
    # only scope. Do NOT promote to module scope.
    from forge_bridge.console.handlers import chat_handler

    body = {"messages": [{"role": "user", "content": prompt}]}
    body_bytes = json.dumps(body).encode("utf-8")

    # Synthetic per-invocation client identity: prevents rate-limit
    # collision across consecutive driver invocations. Each fixture
    # invocation looks like a fresh client to chat_handler's
    # CHAT-01 / D-13 rate-limit pre-gate. The synthetic identity
    # is opaque to the arbitration logic (it lives only in the
    # rate-limit cache); test isolation is maintained by the
    # ``clean_rate_limit_state`` fixture in
    # ``tests/corpus/conftest.py`` (§4.5).
    synthetic_client = (f"seed-{_uuid_module.uuid4().hex[:8]}", 0)

    # Minimal ASGI HTTP scope. The fields chat_handler reads are:
    # request.client.host, request.json() (which awaits receive()),
    # and starlette's internal routing metadata (path, method,
    # headers — all required by Request's constructor).
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/chat",
        "raw_path": b"/api/v1/chat",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": synthetic_client,
        "server": ("seed-driver", 0),
        "scheme": "http",
        "http_version": "1.1",
    }

    # Body injection via _body bypasses the receive() coroutine.
    # Starlette's Request.json() consults _body first if set, then
    # falls back to receive(). Setting _body directly is the
    # documented pattern for in-process invocation without an ASGI
    # server. (Alternative: pass an async receive callable via
    # Request(scope, receive=...) — slightly more boilerplate,
    # equivalent semantics.)
    request = Request(scope)
    request._body = body_bytes  # type: ignore[attr-defined]

    response = await chat_handler(request)
    # JSONResponse intentionally ignored. The seed driver does not
    # consume chat_handler's output — only the observation
    # emission side-effect (which fires inside chat_handler before
    # the response is built).
    _ = response
```

The helper is private (leading underscore). The corpus →
console import is function-scoped (not module-scoped) per the
carrier-#15 scoping rationale documented inline. The
`asyncio.run`-driven invocation lives one frame above this
helper, in `drive_seed_fixture`'s body (§4.1.5).

#### 4.1.5 `drive_seed_fixture(...)` public driver

```python
def drive_seed_fixture(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Drive one seed fixture through the chat-handler arbitration
    pipeline.

    Builds and persists the authored expectation, opens
    ``seed_dispatch_scope``, invokes ``chat_handler`` in-process
    (via ``_invoke_chat_handler_in_process``), exits the scope.

    PR 8 CARRIER #15 — chat-handler-only seeding scope (verbatim,
    load-bearing — see ``A.5.3.2-PR8-SPEC.md`` §0):

      PR 8 seeds the chat-handler observation surface only.
      Chain-step seeding is explicitly deferred because
      handlers.py and _step.py produce semantically distinct
      observation records. Cross-surface expectation semantics
      require a dedicated framing pass before implementation
      proceeds.

    A future contributor proposing to drive ``_step.py:233`` from
    this function must produce a framing artifact defining cross-
    surface expectation semantics BEFORE proposing implementation.
    Implementation-first chain-step seeding is rejected at the
    spec layer per
    ``A.5.3.2-PR8-SPEC.md`` §2 out-of-scope #1 + §7
    (phase-end-conditions rejection table).

    PR 8 ORCHESTRATION-NOT-AUTHORING GUARD (verbatim, load-
    bearing — see
    ``A.5.3.2-PR8-FRAMING.md`` §6.2 + ``A.5.3.2-PR8-SPEC.md``
    §6 Step 4):

      drive_seed_fixture is an orchestration surface, not an
      expectation-authoring surface.

    The driver delegates expectation construction to
    ``emit_seed_expectation``; it does NOT build the expectation
    record dict directly. Inlining the construction would
    collapse the helper/driver authority partitioning. The
    delegation is structurally load-bearing, not stylistic.

    Args:
        fixture_id: REQUIRED keyword-only. The seed fixture
            identifier. Forwarded to ``emit_seed_expectation`` and
            to ``seed_dispatch_scope``.
        prompt: REQUIRED keyword-only. The single-step prompt
            text. Forwarded to ``emit_seed_expectation`` and to
            ``_invoke_chat_handler_in_process``.
        expected_narrow: REQUIRED keyword-only. The list of tool
            names the fixture-author declares the narrowing
            decision should produce. Forwarded to
            ``emit_seed_expectation``.

    Returns:
        ``None``. The driver does not surface the chat_handler
        response or any observation outcome — the seed driver's
        interest is in the emission side-effect (the observation
        record that fires inside chat_handler), not the response.
    """
    emit_seed_expectation(
        fixture_id=fixture_id,
        prompt=prompt,
        expected_narrow=expected_narrow,
    )
    with seed_dispatch_scope(fixture_id=fixture_id):
        asyncio.run(_invoke_chat_handler_in_process(prompt))
```

The driver:
1. **Delegates expectation construction** to
   `emit_seed_expectation` (member #8 protection +
   orchestration-not-authoring guard).
2. **Opens `seed_dispatch_scope`** (PR 7 §4.2.4 substrate
   consumed). Inside the scope, observation emissions persist
   `source="seed"` + the supplied `fixture_id`.
3. **Invokes chat_handler in-process** via the async helper
   (Path E resolution). The chat_handler's internal
   `emit_divergence_capture` call fires while the scope is
   active — the persisted observation record carries
   `source="seed"`.
4. **Exits the scope** automatically via the context manager's
   `finally` block. Subsequent emissions revert to runtime
   default.

The order matters: expectation persistence happens BEFORE the
scope is entered (the expectation record carries no `source`
field; persistence is independent of scope state). The
chat_handler invocation happens INSIDE the scope (so observation
emissions inside chat_handler see the active scope). The
ordering is documented inline at the call site as the structural
contract.

#### 4.1.5.1 The three-way authority partition (PR-8-internal)

Gate 2 framing §3.4 named the three GATE-level authority surfaces
(observation, dispatch provenance, authored expectation). PR 8
introduces a sub-partition INSIDE the third surface (authored
expectation), splitting it into three PR-8-internal authority
surfaces:

| Surface | Function | Authority |
|---|---|---|
| Authored expectation semantics | `emit_seed_expectation` | The truth claim: *"this is what the fixture-author declares the arbitration outcome should be."* |
| Orchestration semantics | `drive_seed_fixture` | The invocation contract: *"this is how a single fixture is exercised through the chat-handler pipeline."* |
| Persistence topology | `_persist_expectation_record` | The persistence discipline: *"this is how a record is written to disk under atomic-append + I-6."* |

The three surfaces are **intentionally distinct authority
classes**. Each surface answers a different architectural
question; collapsing any two of them blurs which authority class
holds which contract. Future cleanup PRs proposing to collapse
these surfaces are rejected at the spec layer:

- **Collapsing semantics into orchestration** (driver builds the
  expectation record dict directly, bypassing
  `emit_seed_expectation`) — rejected per orchestration-not-
  authoring guard + risk #4 test. The orchestration surface
  acquires authored-semantics authority; the partition collapses.
- **Collapsing persistence into semantics** (inlining
  `_persist_expectation_record`'s body into
  `emit_seed_expectation`) — rejected per cleanup-pressure
  class member #8 + Gate 2 framing §5.3 + §2 out-of-scope #9.
  The semantics surface acquires persistence-topology authority;
  the partition collapses.
- **Collapsing orchestration into persistence** (driver writes
  records directly, bypassing both the helper AND the seam) —
  rejected per all of the above + carrier #6 (integration layer
  passes truth, never reconstructs it). The orchestration surface
  acquires persistence-topology authority; both partitions
  collapse.

The three-way partition is documented inline at three operational
placement sites: `_seed.py` module docstring (the authority
table is reproduced verbatim), `drive_seed_fixture`'s docstring
(the orchestration-not-authoring guard names the partition),
and the PR 8 commit message body (the partition is named under
"preserved invariants — authority partitioning"). The PR-8-local
participation discipline test enforces the persistence-topology
half mechanically; the driver-delegation test (risk #4) enforces
the orchestration-not-authoring half mechanically.

### 4.2 `forge_bridge/corpus/_schema.py` (modified — additive)

Single additive change to the schema validator's
`record_kind == "expectation"` branch. PR 7 left this branch
with the no-source check only (per `_schema.py:225–228` inline
comment); PR 8 extends it with required-keys-for-expectation +
per-field type validation.

#### 4.2.1 New constant

```python
# Expectation-specific required keys. PR 8 introduces these per
# ``A.5.3.2-PR8-SPEC.md`` §4.2 — the first PR to construct
# expectation records. The set is locked at framing-time minimum-
# viable per ``A.5.3.2-PR8-FRAMING.md`` §5.3 (Q2).
_REQUIRED_EXPECTATION_KEYS: Final[frozenset[str]] = frozenset({
    "fixture_id",
    "prompt",
    "expected_narrow",
})
```

Adjacent to the existing `_REQUIRED_OBSERVATION_KEYS` and
`_KNOWN_RECORD_KINDS` constants in `_schema.py:80–103`. The
`Final` typing-marker matches the existing constant pattern.

#### 4.2.2 Expectation-branch extension

Replace the existing `elif record_kind == "expectation":` branch
(currently `_schema.py:219–228`) with:

```python
elif record_kind == "expectation":
    if "source" in record:
        raise SchemaValidationError(
            "expectation record must not carry a 'source' field; "
            f"found source={record['source']!r}"
        )
    missing_exp = _REQUIRED_EXPECTATION_KEYS - record.keys()
    if missing_exp:
        raise SchemaValidationError(
            f"expectation record missing required keys: "
            f"{sorted(missing_exp)}"
        )
    if not isinstance(record["fixture_id"], str) or not record["fixture_id"]:
        raise SchemaValidationError(
            "expectation fixture_id must be a non-empty string"
        )
    if not isinstance(record["prompt"], str) or not record["prompt"]:
        raise SchemaValidationError(
            "expectation prompt must be a non-empty string"
        )
    if not isinstance(record["expected_narrow"], list):
        raise SchemaValidationError(
            "expectation expected_narrow must be a list"
        )
    if not all(
        isinstance(tool, str) for tool in record["expected_narrow"]
    ):
        raise SchemaValidationError(
            "expectation expected_narrow entries must be strings"
        )
```

Six checks in order: no-source (preserved from PR 7),
required-keys, fixture_id non-empty string, prompt non-empty
string, expected_narrow is list, expected_narrow entries are
strings. The first failure raises; the function does not
aggregate errors (matches existing PR 7 validator convention).

The extension is **purely additive**. Observation-record
validation (`record_kind == "observation"` branch at
`_schema.py:197–217`) is unchanged. The `_REQUIRED_TOP_KEYS`
universal-required-keys check at `_schema.py:166–170` is
unchanged. PR 7's `test_pr7_record_kind_schema.py` (4 tests) and
reader tests (`test_pr7_reader_validation.py`,
`test_pr7_legacy_record_synthesis.py`) remain green.

`expected_narrow` accepts the empty list — that's a valid
expectation expressing "the fixture-author declares zero-
survivor narrowing for this prompt." The validator rejects
non-list types and lists containing non-strings, but does not
reject the empty list.

### 4.3 `tests/corpus/_pr3_helpers.py` (modified — additive)

Add `base_expectation_args()` per the `base_writer_args` /
`base_builder_args` precedent. The helper does NOT layer on
`base_writer_args` — expectation records have a structurally
distinct shape (no `source`, no `narrower` block, no `topology`,
no arbitration-state fields).

```python
def base_expectation_args(**overrides: Any) -> dict[str, Any]:
    """Default-valid kwargs for ``emit_seed_expectation`` (the
    seed driver's authored-expectation surface).

    Tests passing these kwargs to the helper get a canonical
    expectation emission. Tests override individual keys to
    exercise specific behaviors (e.g.,
    ``base_expectation_args(prompt="multi-step ...")`` for
    parametrized prompt-shape tests).

    The defaults form a coherent expectation that passes schema
    validation. The default set is deliberately small (one tool,
    one fixture) so test assertions don't need to thread fixture-
    scale data through every check.

    Sibling of ``base_writer_args()`` (observation/writer surface)
    and ``base_builder_args()`` (observation/builder surface). The
    three-helper split mirrors the three-authority-surface
    partitioning the corpus package establishes — observation
    records have a different default-valid kwargs shape than
    expectation records (no ``source``, no arbitration-state
    fields).

    The defaults return ONLY the three PR 8-required kwargs the
    helper accepts. Universal keys (``schema_version``,
    ``capture_id``, ``captured_at``, ``record_kind``) are built
    internally by ``emit_seed_expectation`` — they're not caller-
    provided and therefore not in this helper's output. Schema
    validation tests that need raw record dicts hand-craft the
    minimum-shape records directly (same pattern as PR 7's
    expectation-persistence tests).
    """
    defaults: dict[str, Any] = {
        "fixture_id": "fix-pr8-default",
        "prompt": "list staged shots",
        "expected_narrow": ["forge_list_staged"],
    }
    defaults.update(overrides)
    return defaults
```

The default `prompt` value is single-step shape — exercising
chat_handler with this prompt MUST NOT fire chain-step
arbitration (carrier #15 enforcement). The default
`expected_narrow` is a single tool name matching the canonical
single-survivor narrowing case PR 4 + PR 5 use throughout.

### 4.4 `tests/corpus/test_pr8_seed_surface.py` (new — overview)

The new test module houses the 14-test inventory (full inventory
in §5.1). Top-level docstring carries carriers #1–#15. The
module also houses two structural constants for the PR-8-local
participation discipline (per Discovery #1 resolution):
`_SEED_PERMITTED_IMPORTS` + `_corpus_references` AST walker.

#### 4.4.1 `_SEED_PERMITTED_IMPORTS` constant

```python
# PR-8-local participation discipline — _seed.py is the corpus-
# adjacent orchestration surface for Gate 2. It is permitted to
# import a small, named set of corpus symbols. The set is
# documented as the participation contract: two authority
# surfaces (the seam consumed by emit_seed_expectation, the
# scope consumed by drive_seed_fixture) plus three universal-
# key utilities (uuid, timestamp, schema version constant).
#
# The participation contract is SEMANTIC, not cardinal. The
# bright line rejects persistence-topology authority
# (_build_capture_record, _resolve_corpus_dir, _make_header,
# _serialize_line, direct file I/O), not the cardinal symbol
# count. Universal-key utilities and the schema version constant
# are infrastructural, not authority-bearing.
#
# Future PRs adding a sibling universal-key utility (e.g., a
# deterministic-ID generator at PR 9) route through framing
# review to confirm the addition belongs in the universal-keys
# class and not in the persistence-topology class. The
# admission decision is framing-level; the test value here is
# the artifact of that decision.
#
# See ``A.5.3.2-PR8-SPEC.md`` §4.4.1 + §4.5 amendment for the
# rationale and the cleanup-pressure-resistance class member #8
# protection this constant operationalizes.
_SEED_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    # Authority surfaces (2):
    "forge_bridge.corpus._capture.seed_dispatch_scope",
    "forge_bridge.corpus._capture._persist_expectation_record",
    # Universal-key utilities (3):
    "forge_bridge.corpus._capture._now_iso_ms",
    "forge_bridge.corpus._capture._new_uuid",
    "forge_bridge.corpus._schema.SCHEMA_VERSION",
})
```

The constant lives at module scope in
`test_pr8_seed_surface.py` (not in `_seed.py` itself, and not
in `test_pr4_participation_creep.py`). Locality of protection:
the test file owns the discipline; future readers find it
co-located with the tests that enforce it.

#### 4.4.2 `_corpus_references` AST walker

```python
def _corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified ``forge_bridge.corpus.<X>``
    reference imported by ``source``.

    Mirrors the shape of
    ``tests/corpus/test_pr4_participation_creep.py::_corpus_references``
    but scoped to a single source file (``_seed.py``) and a
    different protected property (PR-8-local participation
    discipline rather than narrowing-subsystem → corpus
    one-directional flow).

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected (AST
    walks only Import / ImportFrom nodes), matching the
    "import-target, not text-occurrence" semantic the framing
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
                # `from forge_bridge.corpus.X import Y` — record
                # the dotted import target (module.symbol).
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
```

The walker's `ImportFrom` handling for `forge_bridge.corpus.X`
references resolves submodule.symbol form (e.g.,
`forge_bridge.corpus._capture.seed_dispatch_scope`) — matching
the `_SEED_PERMITTED_IMPORTS` element shape. This differs from
the PR 4 walker's behavior (which records the submodule itself,
e.g., `forge_bridge.corpus._capture`); the difference is
intentional — the PR 4 test enforces submodule-level admission;
PR 8's test enforces symbol-level admission.

### 4.5 Spec amendment 2026-05-10 — four discoveries at incarnation

This subsection captures four spec amendments that surfaced
during PR 8 spec drafting (2026-05-10). Each amendment resolves
a gap the framing did not trace through. The amendments are
LOCKED at this spec; PR 8 implementation derives from the
amended spec, not the framing alone.

#### 4.5.1 Discovery #1 — PR-8-local participation discipline test placement

**Framing position:** `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
extends with a dict-shaped entry keyed by importing module
(`"forge_bridge.corpus._seed": frozenset({...})`).

**Discovered gap:** the existing PR 4 test enforces a different
protected property (narrowing-subsystem → corpus one-directional
flow) using a flat `frozenset[str]` of permitted import targets.
The framing's dict-shaped entry doesn't fit the existing data
structure; broadening the test's enforcement scope to include
corpus-internal participation would conflate two orthogonal
properties.

**Spec resolution:** new PR-8-local mechanical enforcement test
in `tests/corpus/test_pr8_seed_surface.py` with its own
`_SEED_PERMITTED_IMPORTS` constant + AST walker. The PR 4 test
stays unchanged. The shared constant pattern preserves locality
of protection (the test file owns the discipline) and
grepability (future readers find the discipline co-located with
its tests).

**Methodology principle (candidate for close-artifact §5):**
**existing enforcement topology must be grounded in the actual
test surface, not inferred from naming symmetry.** Sibling of
the PR 7 spec §4.5 `_ALLOWLIST` lesson (admission-vs-import
distinction); both lessons emerged when implementation surfaced
gaps the framing's named-test-references didn't trace through
to actual file shape.

#### 4.5.2 Discovery #2 — universal-key import dependency gap

**Framing position:** `_seed.py` may import only two symbols
from corpus: `seed_dispatch_scope` + `_persist_expectation_record`.

**Discovered gap:** the framing's §4.2 helper body and §4.3
record shape reference `SCHEMA_VERSION`, `_new_uuid()`,
`_now_iso_ms()` without specifying their import sources. The
two-symbol allowlist doesn't cover them. The helper cannot
build a valid expectation record without these dependencies.

**Spec resolution:** expand `_SEED_PERMITTED_IMPORTS` to five
symbols across two source modules — `seed_dispatch_scope`,
`_persist_expectation_record`, `_now_iso_ms`, `_new_uuid` from
`_capture.py`; `SCHEMA_VERSION` from `_schema.py`. The
participation contract is **semantic, not cardinal** — the
bright line rejects persistence-topology authority
(`_build_capture_record`, `_resolve_corpus_dir`, `_make_header`,
`_serialize_line`, direct file I/O), not the cardinal symbol
count. Universal-key utilities and the schema version constant
are infrastructural, not authority-bearing; importing them does
not transfer persistence-topology authority into a semantics-
scoped helper.

**Methodology principle (candidate for close-artifact §5):**
**the participation contract is semantic, not cardinal.** The
framing's "two-symbol" language reified an artifact of
incomplete dependency tracing into the protection itself.
Future spec drafting verifies dependency closure of the
proposed allowlist before locking the cardinality.

#### 4.5.3 Discovery #3 — corpus → console import direction

**Framing position:** `drive_seed_fixture` invokes `chat_handler`
directly in-process; framing implicitly authorizes the corpus →
console direction (Gate 2 framing §4.1 Model A + framing §5.1
Q1 lock).

**Discovered gap:** `_seed.py` is the first corpus module that
imports from `forge_bridge.console`. Current corpus modules
(`_capture.py`, `_schema.py`, `_sources.py`, `_identity.py`,
`_topology.py`, `reader.py`) all observe one-directional flow:
console → corpus. PR 8 introduces corpus → console. The framing
did not address what mechanically prevents `_capture.py` (or
any other corpus module) from acquiring a console import next.

**Spec resolution:** document the dependency in §4.1.4 with
rationale (`_seed.py` is the corpus-adjacent orchestration
surface — the **exception surface, not a generalized corpus →
console direction**); add §2 out-of-scope #13 prohibiting any
other corpus module from importing from `forge_bridge.console`
without framing-level review; defer mechanical enforcement to a
future framing question. Function-scoped import inside
`_invoke_chat_handler_in_process` (not module-scoped on
`_seed.py`) preserves carrier #15's chat-handler-only effective
scope.

**Methodology principle (candidate for close-artifact §5):**
**exception surfaces vs. generalized disciplines — a single
named exception is governance-only at introduction; mechanical
enforcement layers are deferred to a future framing question.**
Inventing a "Layer 4" corpus-to-console discipline test inside
PR 8 spec is scope creep disguised as discipline. The exception
is captured; the generalized rule is planted as a v1.6+
governance seed.

#### 4.5.4 Discovery #4 — chat_handler async/Request shape (Path E)

**Framing position:** `drive_seed_fixture` (sync, per Q4 lock)
invokes `chat_handler` directly in-process (per Q1 lock).

**Discovered gap:** `chat_handler` is async, takes a Starlette
Request, runs rate-limit + body validation + JSONResponse
construction. Sync invocation of async handler from sync driver
+ Request construction + rate-limit isolation + response
ignoring all need implementation-shape resolution.

**Spec resolution (Path E):**
- Driver stays sync per Q4 lock.
- Driver body's chat_handler invocation goes through a private
  async helper `_invoke_chat_handler_in_process(prompt: str)`.
- The helper builds a minimal Starlette Request from a hand-
  built ASGI scope dict + injected `_body` bytes.
- The driver wraps the helper in `asyncio.run(...)` inside the
  `seed_dispatch_scope` block.
- A synthetic per-invocation client identity (`seed-<uuid>`) is
  provided in the ASGI scope's `client` field — prevents
  rate-limit collision across consecutive driver invocations
  during testing.
- The corpus → console import is function-scoped inside the
  helper (not module-scoped on `_seed.py`) — preserves
  carrier #15's chat-handler-only effective scope (see §4.5.3).
- The JSONResponse return is intentionally ignored — the
  observation emission fires inside chat_handler before the
  response is built.
- Test isolation via a `clean_rate_limit_state` fixture in
  `tests/corpus/conftest.py` (see §4.6 — new test fixture).

**Carrier #6 preserved:** the integration layer passes truth
(prompt + minimal protocol envelope wrapping it). The Request
object is the protocol envelope, not arbitration truth;
building it wraps the truth, it does not reconstruct it. The
chat-handler arbitration surface IS the request-protocol
surface; exercising it requires the protocol envelope.

**Alternatives rejected:**
- **Refactor chat_handler to extract inner function** —
  substantial console-side change; expands PR 8 scope
  significantly; would require its own framing pass.
- **Drive `LLMRouter.complete_with_tools` directly** —
  bypasses the chat-handler surface; wrong observation
  surface; carrier #15 forbids.
- **Make driver async** — Q4 framing amendment; consumer
  ergonomics worse; tests need pytest-asyncio.
- **`MockRequest` dataclass** — fragile to Starlette upgrades.

### 4.6 `tests/corpus/conftest.py` (modified or new — Path E test fixture)

A new pytest fixture (`clean_rate_limit_state`) supports test
isolation for Path E's chat_handler invocations.

**Contract (spec-level, binding):**

- The fixture clears chat_handler's rate-limit state on entry
  AND on exit, ensuring each driver-invoking test exercises a
  clean rate-limit surface.
- The fixture is opt-in: tests that do not invoke the driver
  do not request it.
- Tests using this fixture: every PR 8 driver-invoking test
  (`test_driver_does_not_invoke_chain_step`,
  `test_driver_emits_expectation_through_helper`,
  `test_driver_opens_scope_around_chat_handler`,
  `test_driver_invokes_chat_handler_in_process`).

**Architectural rationale.** PR 8 tests that invoke
`drive_seed_fixture` exercise `chat_handler`'s D-13 rate-limit
pre-gate. Without isolation, consecutive tests in the same
pytest process accumulate rate-limit state across the synthetic
per-invocation client identities (the cache key is
`client_ip`; each test uses a different synthetic id, but the
cache itself persists across tests). The isolation contract is
architectural: every PR 8 driver-invoking test enters and exits
with a clean rate-limit cache.

**Implementation grounding deferred to Step 4.** The spec
captures the architectural contract (what isolation must
achieve); the concrete rate-limit state surface — the
handler-owned cache implementing D-13, its accessor pattern,
and the reset semantics — is implementation archaeology. Step 4
confirms the concrete rate-limit state surface and installs the
isolation fixture against the actual handler-owned cache. The
spec-level contract binds Step 4's implementation choice; the
implementation choice does NOT bind the spec retroactively.

The fixture lives in `tests/corpus/conftest.py` (existing
file; the fixture extends it). The fixture's console-side
reference is from `forge_bridge.console.handlers` — same
console-side import the seed driver uses, but in test scope
(which is not governed by `_SEED_PERMITTED_IMPORTS`). The
fixture is opt-in.

---

## 5. Test plan

### 5.1 Test inventory (14 tests)

All tests live in `tests/corpus/test_pr8_seed_surface.py`.
Module-level docstring carries carriers #1–#15.

#### Schema validator extension (4 tests)

1. `test_expectation_record_rejects_observation_fields` — risk #2
   (member #7). Constructs an expectation record carrying a
   `source` field; asserts `validate_capture_record` raises
   `SchemaValidationError`. Preserved behavior from PR 7's
   no-source check (lines 220–224); the test ensures PR 8's
   additive extension does not erode it.
2. `test_expectation_record_requires_three_keys` — risk #2
   sibling. Parametrized over `["fixture_id", "prompt",
   "expected_narrow"]`; for each, constructs an expectation
   record missing that key; asserts `validate_capture_record`
   raises `SchemaValidationError` naming the missing key.
3. `test_expectation_record_field_types_validated` — behavioral
   fill. Parametrized over per-field invalid types: empty
   `fixture_id`, non-string `fixture_id`, empty `prompt`, non-
   string `prompt`, non-list `expected_narrow`, list-of-non-
   strings `expected_narrow`. Asserts each raises
   `SchemaValidationError` with the appropriate field-named
   message.
4. `test_expectation_record_round_trip_valid` — behavioral fill.
   Constructs a fully-valid expectation record (4 universal
   keys + record_kind + 3 PR 8-required fields); asserts
   `validate_capture_record` returns `None` (does not raise).
   Empty `expected_narrow` list is included as a valid
   sub-case.

#### `emit_seed_expectation` helper (3 tests)

5. `test_emit_seed_expectation_signature_is_authority_pure` —
   risk #1 (member #8). Asserts
   `inspect.signature(emit_seed_expectation)` has exactly 3
   keyword-only parameters (`fixture_id`, `prompt`,
   `expected_narrow`), each without a default value, and the
   return annotation is `None`.
6. `test_emit_seed_expectation_persists_via_seam` — behavioral
   fill. Patches `_persist_expectation_record` with a sentinel;
   invokes `emit_seed_expectation(**base_expectation_args())`;
   asserts the sentinel was called exactly once with a dict
   carrying `record_kind="expectation"`, the 3 PR 8-required
   fields, and the 4 universal keys (`schema_version` +
   `capture_id` + `captured_at` + `record_kind`). The dict
   shape assertion is structural, not value-exact (uuid +
   timestamp are non-deterministic).
7. `test_emit_seed_expectation_failure_invisibility` —
   behavioral fill. Patches `_persist_expectation_record` to
   raise `RuntimeError`; invokes `emit_seed_expectation(...)`;
   asserts the helper returns `None` and the exception is
   logged at WARNING level (caplog assertion). I-6 enforcement.

#### `drive_seed_fixture` driver (4 tests)

All four use the `clean_rate_limit_state` fixture (§4.6).

8. `test_driver_does_not_invoke_chain_step` — risk #3 (carrier
   #15). Patches `forge_bridge.console._step.chain_step` (or
   the canonical chain-step entry point at `_step.py:233`)
   with a sentinel; invokes
   `drive_seed_fixture(**base_expectation_args())`; asserts
   the sentinel was not called. The scope is local
   orchestration-boundary enforcement (the test asserts what
   the driver does), not global suite surveillance.
9. `test_driver_emits_expectation_through_helper` — risk #4.
   Patches `emit_seed_expectation` (in `_seed.py`'s namespace)
   with a sentinel; invokes
   `drive_seed_fixture(**base_expectation_args())`; asserts
   the sentinel was called exactly once with the exact
   3-kwarg shape (no positional args, no extra kwargs, no
   missing kwargs).
10. `test_driver_opens_scope_around_chat_handler` — behavioral
    fill. Patches `_invoke_chat_handler_in_process` with an
    async sentinel that captures `_dispatch_context.get()` at
    invocation time; invokes
    `drive_seed_fixture(**base_expectation_args())`; asserts
    the captured context is non-None, has
    `source="seed"`, and `fixture_id` matches the kwarg.
    Sibling assertion: post-driver,
    `_dispatch_context.get() is None` (scope correctly
    exited).
11. `test_driver_invokes_chat_handler_in_process` — Q1 lock
    confirmation. Patches `forge_bridge.console.handlers.chat_handler`
    (the source namespace, not the consumer namespace inside
    `_invoke_chat_handler_in_process`) with an async sentinel;
    invokes `drive_seed_fixture(**base_expectation_args())`;
    asserts the sentinel was called exactly once with a
    Starlette Request argument carrying a JSON body whose
    `messages[0].content` matches the prompt kwarg. **Patching
    the source namespace** is structurally load-bearing: the
    architectural contract is that the driver reaches the
    console handler surface; tests should not couple to import
    timing or helper-local bindings. Patching the helper-local
    namespace would silently succeed if the helper acquired a
    second `chat_handler` reference (e.g., via a different
    import path), masking the boundary violation.

#### PR-8-local participation discipline (2 tests)

12. `test_seed_module_permitted_imports_locked` — risk #5a.
    Asserts `_SEED_PERMITTED_IMPORTS` is exactly the 5-element
    frozenset specified at §4.4.1. Fires on growth (a 6th
    symbol added), shrinkage (a symbol removed), or
    substitution (a symbol replaced). Belt-and-suspenders
    alongside the AST walker test.
13. `test_seed_module_imports_match_permitted_set` — risk #5b.
    Reads `forge_bridge/corpus/_seed.py` source via
    `Path(forge_bridge.__file__).parent / "corpus" / "_seed.py"`;
    extracts every `forge_bridge.corpus.<X>` reference via
    `_corpus_references(...)`; asserts every reference is in
    `_SEED_PERMITTED_IMPORTS`. Fires on `_seed.py` actually
    importing a forbidden symbol.

#### `__all__` drift guard (1 test)

14. `test_pr8_helpers_remain_corpus_internal` — risk #6.
    Imports `forge_bridge`; asserts
    `"emit_seed_expectation" not in forge_bridge.__all__` and
    `"drive_seed_fixture" not in forge_bridge.__all__`;
    additionally asserts `len(forge_bridge.__all__) == 19`
    (the v1.4.1 baseline count). Counter-asserts protect
    against both targeted promotion and silent baseline
    drift.

### 5.2 Regression contract

After PR 8 lands, the following test surfaces ship green:

- **PR 8 corpus tests:** all 14 new tests pass.
- **PR 7 corpus tests:** all 27 PR 7 tests pass unchanged.
  Specifically: `test_pr7_record_kind_schema.py` (4 tests) —
  PR 8's additive extension does not affect record_kind enum
  validation; `test_pr7_expectation_persistence.py` (5
  tests) — PR 8's helper does not modify
  `_persist_expectation_record`'s contract;
  `test_pr7_reader_validation.py` +
  `test_pr7_legacy_record_synthesis.py` — reader behavior
  unchanged.
- **PR 6 corpus tests:** all 17 Layer 3 lint tests pass
  unchanged. The lint's discovery walk finds calls to
  `emit_divergence_capture` only; PR 8 introduces zero new
  call sites.
- **PR 5 corpus tests:** chain-step integration tests under
  all four capture states pass unchanged. PR 8 does not
  modify `_step.py:233`.
- **PR 4 corpus tests:** chat-handler integration tests under
  all four capture states pass unchanged.
  `test_pr4_participation_creep.py` (1 test) passes unchanged
  — PR 8 does not modify `_PERMITTED_CORPUS_IMPORTS`.
- **PR 3 corpus tests:** all PR 3 baseline tests pass
  unchanged. `test_pr3_discipline.py` (Layer 1 admission
  test) passes with `_seed.py` present.
- **Console tests:** `tests/console/test_chat_handler.py`
  (50/50) unchanged. PR 8 does not modify `chat_handler`'s
  body.
- **Pre-existing failures** (4): `stdio_cleanliness` (×2),
  `typer_entrypoint` (×2). Same set PR 7 close documented;
  unrelated to PR 8.

### 5.3 Test count delta

| Test category | PR 7 close | PR 8 close | Delta |
|---|---|---|---|
| Corpus tests (forge env) | 175 | 189 | +14 |
| Corpus tests (forge-bridge env) | 169 | 183 | +14 |
| Console tests | 50 | 50 | unchanged |
| Pre-existing failures | 4 | 4 | unchanged |

PR 8 adds exactly 14 tests; all live in
`tests/corpus/test_pr8_seed_surface.py`. The forge-bridge env
total (183) reflects the same 14-test addition over the PR 7
close baseline (169) — pre-existing env-specific differences
(6 tests gated on the forge env's broader fixture set) are
preserved.

### 5.4 What PR 8 deliberately does NOT test

PR 8's test inventory is unit-shaped + structural-property
preservation. The following surfaces are deliberately out of
test scope:

- **Concrete fixture content.** PR 8 ships no concrete seed
  fixtures; the helper + driver are exercised with inline
  `base_expectation_args()` data. Fixture loading, fixture
  format, fixture iteration are PR 9 concerns.
- **End-to-end observation + expectation composition.** The
  Gate 4 comparator joins observation + expectation records
  on `fixture_id`. PR 8 does not exercise the join. PR 9
  ships the integration tests that exercise it.
- **Real chat_handler arbitration outcome.** PR 8 patches
  `chat_handler` (or `_invoke_chat_handler_in_process`) with
  sentinels in the driver tests — the actual narrowing
  behavior under a single-step prompt is exercised by PR 4
  + PR 5 integration tests, which run unchanged. Threading
  PR 8's tests through real arbitration would conflate the
  driver's invocation contract (PR 8's protected property)
  with the arbitration's behavior (PR 4 + PR 5's protected
  property).
- **Multi-fixture parallel invocation.** Carrier #15 +
  Q4 single-fixture-shape lock means the driver is exercised
  with one fixture at a time. Multi-fixture parallelism (if
  ever needed) is a future framing question; PR 8 ships no
  scaffolding.
- **Cross-surface expectation semantics.** Carrier #15's
  ontological quartet (framing §7.3) is explicitly deferred
  — PR 8 tests do not assert any cross-surface property
  because the cross-surface ontology is not yet decided.
- **Rate-limit behavior under load.** The
  `clean_rate_limit_state` fixture isolates each test's
  rate-limit surface; PR 8 does not exercise rate-limit
  enforcement (D-13 contract is exercised by
  `test_chat_handler.py` + the rate-limit test suite, both
  unchanged).

---

## 6. Implementation sequence

The framing §5.7 cadence-matches-work-depth rule applies, with
boundary-work elevation across the entire PR (full three-round
review on every step per Gate 2 framing §5.7 — PR 8 is
boundary-shaped, not plumbing-shaped). Step 3 + Step 4 are
co-equal architectural centers (helper + driver); Step 5 is
verification, not implementation.

Five steps. Each step changes one authority or ontology
boundary cleanly.

### Step 1 — Skeleton + PR-8-local participation discipline test scaffolding

Create `forge_bridge/corpus/_seed.py` per §4.1.1 + §4.1.2:
- Full module docstring (carrier block — carrier #15 at top,
  inherited #1–#14, binding framing clarification, two
  PR-8-local statements).
- Imports per §4.1.2 (5 corpus symbols + stdlib + starlette).
- **No function bodies yet** — `emit_seed_expectation`,
  `_invoke_chat_handler_in_process`, `drive_seed_fixture` all
  defined as stubs raising `NotImplementedError`. The stub
  shape + signatures land for the participation discipline
  test to verify.

Create `tests/corpus/test_pr8_seed_surface.py` skeleton per
§4.4:
- Module-level docstring (carriers #1–#15).
- `_SEED_PERMITTED_IMPORTS` constant per §4.4.1.
- `_corpus_references` AST walker per §4.4.2.
- Two participation discipline tests (test 12 + test 13).

Verify Layer 1 admission via existing structural-location
check (no `_ALLOWLIST` text changes). Run
`pytest tests/corpus/test_pr3_discipline.py` — confirm zero
offenders with `_seed.py` present.

**Atomic commit:** `_seed.py` skeleton + Layer 1 verification +
participation discipline test (passes against the skeleton —
imports match the allowlist exactly).

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr3_discipline.py` — passes.
- `pytest tests/corpus/test_pr8_seed_surface.py -k 'permitted_imports or imports_match_permitted'` — both tests pass.
- `python -c "from forge_bridge.corpus._seed import emit_seed_expectation, drive_seed_fixture"` — imports clean.

### Step 2 — Schema validator extension + tests

Extend `forge_bridge/corpus/_schema.py` per §4.2:
- Add `_REQUIRED_EXPECTATION_KEYS` constant per §4.2.1.
- Replace `record_kind == "expectation"` branch per §4.2.2
  (adds required-keys check + per-field type validation;
  preserves no-source check unchanged).

Add four schema-extension tests to
`tests/corpus/test_pr8_seed_surface.py` (tests 1–4 per §5.1):
- `test_expectation_record_rejects_observation_fields`
- `test_expectation_record_requires_three_keys`
- `test_expectation_record_field_types_validated`
- `test_expectation_record_round_trip_valid`

**Atomic commit:** schema extension + 4 tests. Validator must
be live before `emit_seed_expectation` exercises it (Step 3).

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr8_seed_surface.py -k 'expectation_record'` — 4 tests pass.
- `pytest tests/corpus/test_pr7_record_kind_schema.py` — PR 7's 4 tests pass unchanged (regression: PR 8's additive extension does not affect record_kind enum validation).

### Step 3 — `emit_seed_expectation` helper + `base_expectation_args` + tests **(architectural-center #1)**

Implement `emit_seed_expectation` in `_seed.py` per §4.1.3
(replace `NotImplementedError` stub with the helper body).

Add `base_expectation_args(...)` to
`tests/corpus/_pr3_helpers.py` per §4.3.

Add three helper tests to `test_pr8_seed_surface.py` (tests
5–7 per §5.1):
- `test_emit_seed_expectation_signature_is_authority_pure`
- `test_emit_seed_expectation_persists_via_seam`
- `test_emit_seed_expectation_failure_invisibility`

**Architectural-center #1.** This step lands cleanup-pressure-
resistance class member #8's protection (the semantics-not-
topology guard) operationally. The helper docstring carries
the verbatim member #8 statement; the signature shape is the
load-bearing protection; test 5 enforces it mechanically.

**Atomic commit:** helper body + test infrastructure + 3
tests. Bundling avoids orphaned-commit pressure (the test
infrastructure has no consumer until the helper lands).

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr8_seed_surface.py -k 'emit_seed_expectation'` — 3 tests pass.
- `pytest tests/corpus/test_pr7_expectation_persistence.py` — PR 7's 5 tests pass unchanged (regression: PR 8's helper consumes the seam without modifying it).
- Participation discipline test 13 (AST walker) passes —
  `_seed.py` imports match `_SEED_PERMITTED_IMPORTS` exactly
  (5 symbols).

### Step 4 — `drive_seed_fixture` driver + `_invoke_chat_handler_in_process` + `clean_rate_limit_state` fixture + tests **(architectural-center #2)**

Implement `_invoke_chat_handler_in_process` in `_seed.py` per
§4.1.4 (replace stub with the async helper body).

Implement `drive_seed_fixture` in `_seed.py` per §4.1.5
(replace stub with the driver body).

Add `clean_rate_limit_state` fixture to
`tests/corpus/conftest.py` per §4.6.

Add four driver tests to `test_pr8_seed_surface.py` (tests
8–11 per §5.1; all use the `clean_rate_limit_state` fixture):
- `test_driver_does_not_invoke_chain_step` (carrier #15
  enforcement)
- `test_driver_emits_expectation_through_helper`
  (orchestration-not-authoring guard)
- `test_driver_opens_scope_around_chat_handler`
- `test_driver_invokes_chat_handler_in_process`

**Architectural-center #2.** This step lands cleanup-pressure-
resistance class member #7's protection (companion records as
truth-partitioning) and carrier #15's chat-handler-only scope
operationally. The driver docstring carries the verbatim
carrier #15 statement and the orchestration-not-authoring
guard; the function body's structural ordering (expectation
persistence → scope open → in-process invocation → scope exit)
is the load-bearing protection; tests 8 + 9 enforce
mechanically.

**`drive_seed_fixture(...)` is an orchestration surface, not an
expectation-authoring surface.** The driver delegates
expectation construction to `emit_seed_expectation`; inlining
construction would collapse the helper/driver authority
partitioning. The delegation is structurally load-bearing, not
stylistic. (This sentence travels into the driver's docstring
verbatim; test 9 enforces it mechanically.)

**Atomic commit:** driver body + async helper + rate-limit
fixture + 4 tests. The four tests need both the driver and
the rate-limit fixture; bundling them is the atomic boundary.

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr8_seed_surface.py -k 'driver'` — 4 tests pass.
- `pytest tests/corpus/test_pr8_seed_surface.py` — full module passes (14/14 tests).
- Participation discipline test 13 (AST walker) passes — `_seed.py` imports still match `_SEED_PERMITTED_IMPORTS` exactly (5 symbols; the corpus → console import is function-scoped inside `_invoke_chat_handler_in_process` and outside the AST walker's `forge_bridge.corpus.*` filter).

### Step 5 — Final verification

No new code lands at Step 5. This step verifies the post-PR-8
codebase against all regression contracts and close conditions.
The atomic commit registers the verification + carries the
PR 8 commit message body (carriers + binding framing
clarification + 2 PR-8-local statements + 4 spec amendments
named explicitly).

**Verification checklist:**

1. **PR 8 corpus tests:** `pytest tests/corpus/test_pr8_seed_surface.py` — 14/14 pass.
2. **PR 7 corpus tests:** `pytest tests/corpus/test_pr7_*.py` — all PR 7 tests pass unchanged.
3. **Layer 3 lint regression:** `pytest tests/corpus/test_pr6_visual_asymmetry.py` — 17/17 pass unchanged. Confirms PR 8 introduced zero new `emit_divergence_capture` call sites.
4. **PR 4 + PR 5 integration tests:** chat-handler + chain-step integration tests under all four capture states — pass unchanged.
5. **Full corpus suite:** `pytest tests/corpus/` — 189 pass (175 PR 7 baseline + 14 new) in forge env; 183 pass (169 PR 7 baseline + 14 new) in forge-bridge env. Same 4 pre-existing failures (`stdio_cleanliness` ×2, `typer_entrypoint` ×2).
6. **Console tests:** `pytest tests/console/test_chat_handler.py` — 50/50 unchanged.
7. **Public API regression:** `python -c "import forge_bridge; assert len(forge_bridge.__all__) == 19; assert 'emit_seed_expectation' not in forge_bridge.__all__; assert 'drive_seed_fixture' not in forge_bridge.__all__"` — clean.
8. **Verbatim travel verification:** Step 5 verifier reads `_seed.py`'s module docstring, `emit_seed_expectation`'s docstring, `drive_seed_fixture`'s docstring, and `test_pr8_seed_surface.py`'s top-level docstring; cross-references each verbatim block against §0; surfaces any drift before the close commit.

**Step 5 commit message body** carries (in order):
- Section: "preserved invariants" — 14 inherited carriers +
  binding framing clarification.
- Section: "new carrier introduced" — carrier #15 verbatim.
- Section: "cleanup-pressure-resistance class additions" —
  member #7 + #8 protection statements verbatim.
- Section: "spec amendments at incarnation" — Discoveries
  #1–#4 named explicitly with §4.5 sub-section references.
- Section: "regression contracts" — verification checklist
  results.

### Closing prose — Step 5 vs. close artifact

`A.5.3.2-PR8-CLOSE.md` lands as a distinct subsequent commit
after Step 5 verification completes. The close artifact is not
part of the implementation sequence itself.

The cadence preserves the PR 4–7 separation:
**implementation sequence ≠ close archaeology.** Step 5
concludes implementation + verification authority; the close
artifact performs retrospective architectural synthesis
(durable archival state PR 9 inherits, methodology
observations, cleanup-pressure class final-inventory archive,
verbatim-travel archaeology). Folding them together would
collapse two distinct authority classes.

PR 7 cadence verified: Step 8 implementation at `7838f9a`
followed by close artifact at `b035c87` — two separate
commits. PR 8 mirrors: Step 5 verification commit followed by
`A.5.3.2-PR8-CLOSE.md` commit.

### Natural pause points

- **Between Step 1 and Step 2** — verifies the PR-8-local
  participation discipline test surface is operational before
  any helper bodies land. If the AST walker fires unexpectedly
  on the skeleton, the framing-time `_SEED_PERMITTED_IMPORTS`
  spec is wrong and needs amendment before bodies proceed.
- **Between Step 2 and Step 3** — verifies the schema
  validator extension ships green (4 tests + PR 7 regression)
  before `emit_seed_expectation` exercises it. Without this
  pause, a Step 3 test failure could be a helper bug OR a
  schema-validator bug.
- **Between Step 3 and Step 4** — verifies the
  authored-expectation surface is operational (helper + 3
  tests + PR 7 expectation-persistence regression) before the
  driver wraps it. The driver's invocation contract depends
  on the helper's authority-pure shape; locking the helper
  before driver ships scopes any Step 4 failure to driver
  logic.
- **Immediately after Step 4** — full PR 8 suite green (14
  tests). Before Step 5 verification, this is the moment to
  sanity-check the verbatim travel placements in
  `_seed.py`'s docstrings.

### What about an inter-step polish step?

PR 4, PR 5, and PR 6 reserved a "polish step (no-op for this
PR)" slot. PR 7 surfaced no analogous polish during spec
drafting and did not reserve one. PR 8 surfaces no polish
during this drafting and does not reserve one. The five steps
above are the implementation sequence in full.

---

## 7. Phase-end conditions for PR 8

| Trigger | Response |
|---|---|
| All 14 new tests pass + Layer 3 lint passes unchanged + PR 4 + PR 5 + PR 7 integration tests pass under all four capture states + the 18 sentences in §0 travel verbatim into the relevant docstrings + commit message body + no implementation step shortcuts or weakens any member of the constructs-resistant-to-cleanup-pressure class (framing §6) + the three-way authority partition (§4.1.5.1) is preserved across all PR 8 surfaces | PR 8 closes; `A.5.3.2-PR8-CLOSE.md` drafts as a distinct subsequent commit; PR 9 framing/spec drafting begins. |
| `test_pr6_visual_asymmetry.py` regresses against the post-PR-8 codebase | Hard CI failure; Layer 3 lint has been touched accidentally or `_seed.py` has begun introducing `emit_divergence_capture` call sites. Reject at CI; review surfaces the structural violation. |
| `test_driver_does_not_invoke_chain_step` regresses on a future PR | Hard CI failure; carrier #15 has been violated. The chat-handler-only seeding scope has been breached — either `drive_seed_fixture` now invokes `_step.py:233` directly, or a fixture introduced multi-step prompt content that fires chain-step internally. Reject at CI; review surfaces carrier #15 verbatim + the cross-surface-semantics framing-pass requirement. |
| `test_emit_seed_expectation_signature_is_authority_pure` regresses on a future PR | Hard CI failure; cleanup-pressure class member #8 has been violated (signature-shape surface). The helper has acquired a fourth parameter, a default value, a return type, or its kwargs have lost the keyword-only marker. Reject at CI; review surfaces the semantics-not-topology guard verbatim + the framing's Q3 lock. |
| `test_driver_emits_expectation_through_helper` regresses on a future PR | Hard CI failure; the orchestration-not-authoring guard (§6 Step 4 + §4.1.5.1) has been violated. The driver has acquired authored-semantics authority (building the expectation record dict directly, or invoking `_persist_expectation_record` without going through `emit_seed_expectation`). Reject at CI; review surfaces the verbatim guard + the three-way authority partition table. |
| `test_seed_module_permitted_imports_locked` OR `test_seed_module_imports_match_permitted_set` regresses on a future PR | Hard CI failure; PR-8-local participation discipline has been violated. Either `_SEED_PERMITTED_IMPORTS` has been amended without spec review (test 5a fires) or `_seed.py` has acquired a forbidden import (test 5b fires). Reject at CI; review surfaces §4.5.1 + §4.5.2 amendments + the participation-contract-is-semantic-not-cardinal framing. |
| `test_pr8_helpers_remain_corpus_internal` regresses on a future PR | Hard CI failure; the Q5 `__all__` deferral has been violated. A PR has promoted `emit_seed_expectation` or `drive_seed_fixture` to `forge_bridge.__all__` without a concrete external consumer surfacing first. Reject at CI; review surfaces framing §5.6 + §2 out-of-scope #4. Variant: `len(forge_bridge.__all__)` no longer equals 19 — silent baseline drift, also caught by this test. |
| `test_expectation_record_rejects_observation_fields` regresses on a future PR | Hard CI failure; cleanup-pressure class member #7 has been violated. The schema validator no longer rejects expectation records carrying a `source` field — meaning the truth-partitioning the comparator depends on has been eroded. Reject at CI; review surfaces the falsifiability framing + Gate 2 framing §4.4 verbatim. |
| A future PR proposes seeding the chain-step observation surface | Rejected at the spec layer per carrier #15 + §2 out-of-scope #1. Cross-surface expectation semantics require a dedicated framing pass BEFORE implementation proceeds. Implementation-first chain-step seeding is rejected at every review boundary. |
| A future PR proposes shipping concrete seed fixtures | Rejected at the spec layer per §2 out-of-scope #2. PR 9's domain. PR 8 ships the seed-driver seam only. |
| A future PR proposes shipping end-to-end integration tests demonstrating observation + expectation composition | Rejected at the spec layer per §2 out-of-scope #3. PR 9's domain. |
| A future PR proposes promoting `emit_seed_expectation` or `drive_seed_fixture` to `forge_bridge.__all__` inside a cleanup PR | Rejected at the spec layer per §2 out-of-scope #4 + framing §5.6 (Q5). The public-API decision is deferred to first concrete external consumer; revisit at framing time, not inside an unrelated cleanup PR. |
| A future PR proposes merging observation and expectation records into a single richer record per fixture (companion-records collapse) | Rejected at the spec layer per cleanup-pressure class member #7 + Gate 2 framing §4.4 + §2 out-of-scope #8. The truth-partitioning is the comparator's foundation; merging the records erodes Gate 4's architecture. |
| A future PR proposes to inline `_persist_expectation_record`'s body into `emit_seed_expectation` ("for symmetry with `emit_divergence_capture`") | Rejected at the spec layer per cleanup-pressure class member #8 + Gate 2 framing §5.3 + §2 out-of-scope #9. The helpers' asymmetry is structural; collapsing it transfers persistence-topology authority into a semantics-scoped helper. The three-way authority partition (§4.1.5.1) names the three classes; collapsing semantics + persistence violates the partition. |
| A future PR proposes that `drive_seed_fixture` write records directly to disk (collapsing orchestration → persistence-topology) | Rejected at the spec layer per the three-way authority partition (§4.1.5.1) + carriers #3–#6 (integration layer passes truth, never reconstructs it) + §2 out-of-scope #9 (no inlining of persistence). The driver's orchestration authority is structurally distinct from the seam's persistence-topology authority; bypassing both `emit_seed_expectation` and `_persist_expectation_record` collapses two partitions at once. |
| A future PR proposes that `drive_seed_fixture` build the expectation record dict directly (collapsing orchestration → authored-semantics) | Rejected at the spec layer per the orchestration-not-authoring guard (§6 Step 4 + §4.1.5.1) + cleanup-pressure class member #8. The driver's orchestration authority is structurally distinct from the helper's authored-semantics authority; the driver delegating to the helper is structurally load-bearing, not stylistic. |
| A future PR proposes to drive seed fixtures via HTTP instead of in-process | Rejected at the spec layer per framing §5.1 (Q1) + carriers #3–#6 + §2 out-of-scope #10. The arbitration pipeline is the thing being measured; transport is incidental. The Request-envelope reconstruction inside `_invoke_chat_handler_in_process` is wrapping truth in the protocol envelope, not threading transport. |
| A future PR proposes to add a fourth required field to expectation records inside a cleanup PR | Rejected at the spec layer per framing §5.3 (Q2) minimum-viable lock + §2 out-of-scope #11. Expectation-record shape changes require framing-level review; Gate 4 will surface concrete needs at comparator-write time. A spec amendment cadence event (NO-code commit registering the amendment) is required BEFORE any code lands. |
| A future PR proposes to admit a persistence-topology symbol to `_SEED_PERMITTED_IMPORTS` (e.g., `_build_capture_record`, `_resolve_corpus_dir`, `_make_header`, `_serialize_line`, any direct file-I/O surface) | Rejected at the spec layer per cleanup-pressure class member #8 + §2 out-of-scope #12 + §4.5.1/§4.5.2 amendments. The participation contract is semantic, not cardinal — the bright line is rejection of persistence-topology authority. |
| A future PR proposes to admit a universal-key sibling utility to `_SEED_PERMITTED_IMPORTS` (e.g., a deterministic-ID generator at PR 9) | Routed to framing review at the proposing PR's framing pass — NOT rejected outright. The admission decision is framing-level: does the candidate symbol belong in the universal-keys class (infrastructural, not authority-bearing) or in the persistence-topology class (authority-bearing, rejected)? Framing review confirms the classification before the spec lands. |
| A future PR proposes that another corpus module (`_capture.py`, `_schema.py`, `_sources.py`, `_identity.py`, `_topology.py`, `reader.py`, or any future corpus module other than `_seed.py`) import from `forge_bridge.console` | Rejected at the spec layer per §2 out-of-scope #13. PR 8's `_seed.py` is the orchestration-surface exception; no other corpus module may acquire a `forge_bridge.console` import without framing-level review. The mechanical enforcement layer is planted as a v1.6+ governance seed; PR 8's discipline is spec-language + cleanup-PR review. |
| A future PR proposes to rename `drive_seed_fixture` to a surface-explicit name (e.g., `drive_chat_handler_fixture`) without a framing artifact | Rejected at the spec layer per framing §5.5 (Q4) + carrier #15 + §2 out-of-scope #7. The generic name preserves option-space about how the future chain-step-seeding framing pass resolves the ontological questions (framing §7.3); renaming forecloses that pass's authority. |
| A future PR proposes to make `drive_seed_fixture` async (changing Q4 lock) | Rejected at the spec layer per framing §5.5 (Q4). The sync signature is consumer-ergonomic and matches the corpus convention (every public-from-corpus helper is sync). Async-driver proposals route through a framing amendment, not a spec-amendment cycle. |
| A future PR proposes to remove the function-scoped corpus → console import in `_invoke_chat_handler_in_process` (e.g., promote `chat_handler` to module-scope import in `_seed.py`) | Rejected at the spec layer per §4.1.4 + §4.5.3 amendment. The function-scoped placement is structurally load-bearing — preserves carrier #15's chat-handler-only effective scope by limiting the import's effective scope to driver invocation. Module-scoped import broadens the exception to test collection and reflective import paths. |
| A future PR proposes to ship the `clean_rate_limit_state` fixture WITHOUT verifying the concrete rate-limit state surface against the actual handler-owned cache | Rejected at the spec layer per §4.6. The architectural contract (entry+exit isolation) is binding; the implementation MUST be grounded against the actual handler-owned cache during Step 4 verification. Spec-level guess is not acceptable as the final implementation. |

---

## 8. Cross-references

- `A.5.3.2-PR8-FRAMING.md` (`23f2a20`) — binding pre-spec
  contract. §0 carrier #15 (this spec §0); §5 six binding
  decisions (this spec §1 + §2 + §4); §6 cleanup-pressure-
  resistance class member #7 + #8 (this spec §0 PR 8-local
  binding statements + §4.1 module docstring + §7 phase-end
  conditions); §7.3 ontological quartet (this spec §2 out-of-
  scope #1 + §5.4 what-not-tested); §8 Layer 1/2/3 extension
  specifications (this spec §4.5.1 amendment supersedes §8.2's
  test-placement language); §9 twelve phase-end rejection rows
  (this spec §7 expands to 22 rows with the four spec
  amendments + three-way partition rejections).
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — §6 cleanup-pressure-
  resistance class (introduced at PR 7; PR 8 contributes
  members #7 + #8 per this spec §0 + §4.1.5.1).
- `A.5.3.2-PR7-SPEC.md` (`84392d2`) — §4.2.4
  `seed_dispatch_scope` + §4.2.6 `_persist_expectation_record`
  (the two authority-surface symbols `_seed.py` may import per
  this spec §4.1.2 + §4.4.1); §4.5 amendment
  (admission-vs-import distinction — sibling lesson to this
  spec §4.5.1's enforcement-topology-grounding lesson); §7
  phase-end conditions (rejection table preserved into PR 8
  per this spec §2 out-of-scope + §7).
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — durable archival state
  PR 8 inherits; §1.2 cleanup-pressure-resistance class
  inventory (6 members at PR 7 close; PR 8 grows to 8 per this
  spec §4.1.5.1); §5 methodology observations (this spec §4.5
  amendments are candidates for promotion to
  `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level
  architecture; §3.4 three-authority-surface partitioning
  (PR 8 closes the third surface; PR 8 also introduces a
  PR-8-internal three-way sub-partition per this spec
  §4.1.5.1); §4.1 Model A; §4.4 companion records (this spec
  §0 PR 8-local binding statement #1 names the protection);
  §5.3 Q1.6 companion records + dedicated expectation helper
  locked (this spec §0 PR 8-local binding statement #2 names
  the protection); §5.5 module siting; §5.7 PR 8 = boundary
  work (this spec §6 full three-round review across all five
  steps); §6.1 carrier #14; §6.2 binding framing
  clarification; §7 six non-acquisition commitments (inherited
  per this spec §2 out-of-scope); §8.1/§8.2/§8.3 Layer
  extension specifications (this spec §4.5.1 amendment
  supersedes §8.2's test-placement language).
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — §1.3 truth-vs-mechanism
  distinction (informs `_seed.py`'s governance docstring
  shape per this spec §4.1.1); §1.5 relevance-by-file ordering
  (carrier #15 lands at top of carrier block per this spec
  §0 + §4.1.1).
- `A.5.3.2-PR4-CLOSE.md` (`fab26cb`) — risk-category shift;
  integration-discipline quartet (inherited carriers #3–#6;
  preserved in this spec §0 + §4.5.4 Path E rationale —
  carrier #6 explicitly cited).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §3 — record shape; PR 8
  extends with expectation-record-specific keys per this spec
  §4.2 + §4.2.1.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §2.2 + §8.4 — structural
  invariants I-1 through I-6 + privacy posture; preserved
  unchanged by PR 8 (I-6 failure invisibility applied to
  `emit_seed_expectation` + `_invoke_chat_handler_in_process`
  + `drive_seed_fixture` per the corpus convention).
- `forge_bridge/console/handlers.py::chat_handler` —
  **invoked by `_invoke_chat_handler_in_process` (§4.1.4) via
  function-scoped corpus → console import**. PR 8 makes no
  modifications to this function. Test 11 patches
  `forge_bridge.console.handlers.chat_handler` (source
  namespace) per this spec §5.1 test 11.
- `forge_bridge/console/_step.py::chain_step` — **NOT invoked
  by PR 8**. Carrier #15 governs; test 8 enforces mechanically
  via sentinel patch.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  unchanged by PR 8 (Layer 3 lint enforcement). The call site
  at `handlers.py:1185` fires during chat_handler invocation
  inside `_invoke_chat_handler_in_process`; the resolution
  path consults `_dispatch_context` which is active (set by
  `seed_dispatch_scope`), so the persisted observation record
  carries `source="seed"` + the supplied `fixture_id`.
- `forge_bridge/corpus/_capture.py::seed_dispatch_scope` —
  **consumed by `drive_seed_fixture` (§4.1.5)**; one of the
  two authority-surface symbols admitted in
  `_SEED_PERMITTED_IMPORTS` (§4.4.1).
- `forge_bridge/corpus/_capture.py::_persist_expectation_record` —
  **consumed by `emit_seed_expectation` (§4.1.3)**; the other
  authority-surface symbol admitted in
  `_SEED_PERMITTED_IMPORTS` (§4.4.1). PR 8 does not modify the
  seam.
- `forge_bridge/corpus/_capture.py::_now_iso_ms` +
  `_new_uuid` — **consumed by `emit_seed_expectation`
  (§4.1.3)**; two of the three universal-key utilities
  admitted in `_SEED_PERMITTED_IMPORTS` (§4.4.1).
- `forge_bridge/corpus/_schema.py::SCHEMA_VERSION` —
  **consumed by `emit_seed_expectation` (§4.1.3)**; the third
  universal-key utility admitted in `_SEED_PERMITTED_IMPORTS`
  (§4.4.1).
- `forge_bridge/corpus/_schema.py::validate_capture_record` —
  PR 8 extends the `record_kind == "expectation"` branch
  additively per §4.2.2. Observation-record validation
  unchanged.
- `forge_bridge/corpus/_schema.py::_REQUIRED_EXPECTATION_KEYS` —
  new constant added per §4.2.1.
- `forge_bridge/corpus/_seed.py` (planned, PR 8) — seed driver
  module per §4.1.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer 1;
  unchanged at PR 8 (structural-location admission per PR 7
  spec §4.5 amendment). Step 1 verifies `_seed.py` is admitted
  by the existing corpus-subtree filter.
- `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS` —
  **unchanged at PR 8** per §4.5.1 amendment. PR 8's
  participation discipline lives in
  `test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS`, not in
  this PR 4 surface.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3; **
  unchanged by PR 8**, regression-asserted in this spec §6
  Step 5 (post-PR 8 codebase check) and §7 close conditions.
- `tests/corpus/_pr3_helpers.py::base_writer_args` +
  `base_builder_args` — PR 7 + PR 4 test infrastructure;
  unchanged by PR 8. New sibling helper `base_expectation_args`
  lands per §4.3.
- `tests/corpus/_pr3_helpers.py::base_expectation_args` —
  new helper added per §4.3.
- `tests/corpus/conftest.py::clean_rate_limit_state` — new
  fixture added per §4.6. Implementation grounding deferred to
  Step 4 verification.
- `tests/corpus/test_pr8_seed_surface.py` (planned, PR 8) —
  new test module per §4.4 + §5.1. Houses the 14-test
  inventory + `_SEED_PERMITTED_IMPORTS` constant +
  `_corpus_references` AST walker.
- `project_pr8_base_expectation_args.md` (local memory) —
  flagged expectation; consumed at framing §4.4 + this spec
  §4.3.
- `project_state_2026_05_10_pr8_framing.md` (local memory) —
  active cursor at spec drafting; supersedes
  `project_state_2026_05_10_pr7_closed.md`.
- `feedback_ground_specs_in_actual_files.md` (local memory) —
  applied throughout: §4.1 grounded against `_capture.py`
  read at drafting time; §4.2 grounded against `_schema.py`'s
  actual expectation-branch state; §4.3 grounded against
  `_pr3_helpers.py`'s `base_writer_args` / `base_builder_args`
  shape; §4.4 grounded against
  `test_pr4_participation_creep.py`'s actual data structure
  (Discovery #1 surfaced when the assumption was checked
  against the file).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — methodology
  seed. PR 8's four spec amendments at incarnation (§4.5.1–
  §4.5.4) are candidates for promotion alongside PR 7's
  six methodology observations.

---

## Resume protocol — what the next session does with this spec

Resumption from this spec opens at **Step 1** of §6 (`_seed.py`
skeleton + PR-8-local participation discipline test
scaffolding). The five steps proceed in order; all five receive
full three-round review per the boundary-work cadence (Gate 2
framing §5.7). Step 3 + Step 4 are architectural centers;
Step 5 is verification (no new code), and `A.5.3.2-PR8-CLOSE.md`
lands as a distinct subsequent commit per §6 closing prose.

If a future session opens mid-implementation, the resume
protocol is:

1. `git status` to identify the in-progress step.
2. Cross-reference §6 to determine which step is incomplete.
3. Re-read the relevant subsection of §4 for the surface
   contract — including the §4.5 amendments at incarnation.
4. Verify all preceding steps' tests still pass before
   continuing.
5. Verify the verbatim travel placements in `_seed.py`'s
   docstrings cross-reference cleanly against §0 (the 18
   sentences are load-bearing — paraphrasing destroys the
   protection).
6. If Step 4 is incomplete, re-confirm the architectural
   center status and apply full three-round review on the
   remaining step body. Step 4 is where the orchestration-
   not-authoring guard + carrier #15 enforcement seam land;
   both are load-bearing.

---

End of spec. PR 8 implementation opens against this spec per
the boundary-work cadence (Gate 2 framing §5.7) — full three-
round review across the entire five-step staircase. The four
spec amendments (§4.5.1–§4.5.4) are LOCKED at this drafting;
implementation derives from the amended spec, not the framing
alone. The 18 verbatim entries (§0) travel into `_seed.py`'s
module docstring + `emit_seed_expectation`'s docstring +
`drive_seed_fixture`'s docstring + the new test module
docstring + the PR 8 commit message body. Carrier #15 governs;
the three-way authority partition (§4.1.5.1) is preserved
across all PR 8 surfaces; cleanup-pressure-resistance class
final inventory at PR 8 close: 8 members.
