# A.5.3.2 PR 9 — Spec (fixture corpus + end-to-end integration)

**Status:** Spec-stage artifact for PR 9 of Gate 2. PR 9 framing
locked at `5628817` (1222 lines); this spec derives the
implementation contract. Integration-shaped work — full three-
round review applies across the entire PR (per Gate 2 framing
§5.7 + PR 8 close §3 "what PR 9 changes" + PR 9 framing §2).

PR 9 is the final PR of Gate 2. Two artifacts land at the PR 9
close commit: `A.5.3.2-PR9-CLOSE.md` (PR 9 archival) and
`A.5.3.2-GATE-2-CLOSE.md` (Gate 2 archival) per Gate 2 framing
§11.6 + PR 8 close §7 step 11.

This spec's job: derive file-level precision from the framing's
locked decisions. Each new file's exact shape (path, imports,
docstring carrier order, function/constant signatures, body
structure). Each test's exact name + assertion contract. Each
implementation step's atomic boundary + verification checklist.
The spec's outputs are mergeability anchors — counts, file
paths, function names, test names — that PR 9 close §6 will
verify against.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Sixteen sentences** travel verbatim into PR 9's surface.
Fifteen are numbered carriers — fourteen inherited from PR 4 +
PR 5 + PR 6 + Gate 2 (the same set Gate 2 framing locks at §3.1
and PR 7 + PR 8 ship in production) + carrier #15 (introduced
at PR 8 framing). One is the binding framing clarification on
call-site-owned arbitration inputs (Gate 2 framing §6.2). PR 9
introduces **zero new numbered carriers** (per framing §3.2 —
all 15 inherited).

The **PR 9 governing sentence** ("PR 9 proves topology, not
infrastructure.") is included in this section as a framing-
artifact-scoped statement, NOT as a carrier (per framing §0
deferral decision). Its travel sites are reduced — it lands in:

- PR 9 spec §0 (this section, below).
- PR 9 commit message bodies (close artifact + at least one
  implementation commit).
- Optionally PR 9 fixture module docstrings (Step 2 amendment
  candidate — register as spec amendment if Step 2
  implementation surfaces a need to carry it inline at the
  fixture surface).

Promotion to carrier #16 is deferred — if PR 9 implementation
surfaces a recurring need to carry it verbatim into source-of-
truth files (analogous to carriers #1–#15), the promotion lands
as a Step N amendment commit.

The sixteen sentences travel into:

1. Each fixture module's docstring under
   `tests/corpus/fixtures/`. Per the relevance-by-file ordering
   principle (PR 7 close §1.5 + PR 8 close §1.5), **carrier #15
   lands at the top** of the carrier block — each PR 9 fixture
   is structurally scoped to the chat-handler observation surface,
   making carrier #15 the most-relevant inherited governance for
   the file. Then carriers #1–#14 in their inherited numbered
   order; then the binding framing clarification.
2. `tests/corpus/test_pr9_fixture_integration.py` top-level
   docstring (carriers #1–#15 + binding framing clarification).
3. `tests/corpus/test_pr9_fixture_discipline.py` top-level
   docstring (carriers #1–#15 + binding framing clarification +
   the parallel-not-extension rationale paragraph + the closing
   sentence "Shared AST mechanics do not imply shared ontology.").
4. PR 9 commit message bodies under "preserved invariants" /
   "carriers inherited verbatim" sections. All sixteen sentences
   in their full form.

The **PR-7-LOCAL** binding pairs (§4.2 inert-parameter, §5.5
legacy-synthesis) do NOT travel into PR 9 surfaces. The
**PR-8-LOCAL** binding statements (member #7 truth-partitioning,
member #8 semantics-not-topology) do NOT regenerate at PR 9 —
they remain scope-local to `_seed.py` + `emit_seed_expectation`
per PR 8 spec §0's PR-N-LOCAL non-regeneration rule. PR 9's
fixture modules + integration test module + discipline test
module do NOT carry the PR-7-LOCAL or PR-8-LOCAL statements
verbatim.

### Inherited carriers (verbatim)

The fourteen inherited carriers + binding framing clarification
are reproduced here in the same order they land in the source-
of-truth artifacts. Production-truth source:
`forge_bridge/corpus/_capture.py:6–135` +
`forge_bridge/corpus/_seed.py:19–135`.

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

### PR 8-inherited carrier (verbatim)

**#15 — chat-handler-only seeding scope (PR 8):**

> **PR 8 seeds the chat-handler observation surface only. Chain-
> step seeding is explicitly deferred because `handlers.py` and
> `_step.py` produce semantically distinct observation records.
> Cross-surface expectation semantics require a dedicated framing
> pass before implementation proceeds.**

Carrier #15 is the most-relevant inherited governance for PR 9
fixture modules — each PR 9 fixture is structurally scoped to
the chat-handler observation surface (per `drive_seed_fixture`'s
scope per PR 8 spec §0). Carrier #15 lands at the **top** of
each fixture module's docstring carrier block per the relevance-
by-file ordering principle.

PR 9 introduces **zero new numbered carriers** (per framing §3.2).
The framing-level governing sentence ("PR 9 proves topology, not
infrastructure.") is included for completeness below; its travel
discipline is reduced relative to carriers per the framing's §0
deferral decision.

### PR 9 governing sentence (framing-artifact-scoped)

> **PR 9 proves topology, not infrastructure.**

The sentence is short by design. It is the rejection key for an
entire category of speculative scope (per framing §0). PR 9 spec
§0 is its one mandatory travel site at the spec layer; PR 9
commit message bodies are the secondary travel sites. Fixture
module docstrings are the optional tertiary travel sites —
spec-amendment-candidate.

The sentence is NOT a numbered carrier at PR 9 close. Promotion
to carrier #16 is gated on PR 9 implementation surfacing a need
to carry it verbatim into production-source files; if PR 9 ships
without that need surfacing, the sentence remains framing-scoped
and Gate 4 framing (or a future reliability phase) revisits the
promotion question with corroborating evidence.

---

## 1. Real job + success condition

**Real job:** *"Land the fixture-data surface for Gate 2 close.
Ship `tests/corpus/fixtures/` as a new test-resident directory
containing `__init__.py` (empty package init) + three fixture
modules: `fix_single_survivor.py`, `fix_multi_match.py`,
`fix_zero_match.py`. Each fixture module exposes exactly one
top-level constant `FIXTURE: dict` carrying exactly the three
PR-8-locked keys (`fixture_id`, `prompt`, `expected_narrow`).
Each fixture module's docstring carries the 15 inherited carriers
+ binding framing clarification per the relevance-by-file
ordering principle (carrier #15 at top). Ship
`tests/corpus/test_pr9_fixture_integration.py` exercising five
named tests — three end-to-end drives (one per fixture module)
+ two Gate 4 unblock proofs (`record_kind` partition correctness
+ `fixture_id` joinability). Ship
`tests/corpus/test_pr9_fixture_discipline.py` containing
`_FIXTURE_PERMITTED_IMPORTS: frozenset[str]` (value-locked to
exactly 1 symbol — `forge_bridge.corpus._seed.drive_seed_fixture`)
+ a new AST walker `_fixture_corpus_references()` scoped to
`tests/corpus/fixtures/*.py` + two Layer 2 discipline tests
(frozenset value-lock + walker subset-enforcement). The
discipline-test module is EXPLICITLY NOT an extension of
`tests/corpus/test_pr4_participation_creep.py` — different
ontology (PR 4 walker protects production import topology; PR 9
walker protects declarative fixture-data discipline). The
governing sentence — 'PR 9 proves topology, not infrastructure.'
— travels into PR 9 spec §0 + PR 9 commit message bodies (optional
travel: fixture module docstrings via Step 2 amendment if
implementation surfaces the need). PR 9 does NOT modify any
production source file; PR 9 does NOT modify any PR 4 / PR 6 /
PR 7 / PR 8 test module."*

PR 9's three operational responsibilities:

- **Author the fixture-data surface.** A new directory
  `tests/corpus/fixtures/` with `__init__.py` + three fixture
  modules. Each fixture module is data + a module docstring
  (carriers verbatim) + no functions, no classes, no constants
  beyond `FIXTURE`, no imports beyond `__future__` annotations
  and `typing` types if needed. Each `fixture_id` is a stable
  PR-9-anchored string (`fix-pr9-single-survivor`,
  `fix-pr9-multi-match`, `fix-pr9-zero-match`).
- **Author the integration test surface.** A new test module
  `tests/corpus/test_pr9_fixture_integration.py` with five
  named tests. Three tests drive one fixture each end-to-end
  (import the fixture module → invoke
  `drive_seed_fixture(**FIXTURE)` → assert persisted record
  shape). Two tests prove Gate 4 unblock properties:
  `record_kind`-partitionability + `fixture_id`-joinability.
  Each test is independent — no parametrization framework, no
  test-to-test ordering, no shared state beyond the
  PR-8-supplied `clean_rate_limit_state` fixture.
- **Author the Layer 2 fixture discipline.** A new test module
  `tests/corpus/test_pr9_fixture_discipline.py` containing a
  parallel-not-extension Layer 2 surface: a value-locked
  frozenset (1 symbol) + a new AST walker scoped to
  `tests/corpus/fixtures/*.py` + two discipline tests
  (frozenset value-lock + walker subset-enforcement). The
  parallel-not-extension shape preserves three distinct Layer 2
  ontologies (`_PERMITTED_CORPUS_IMPORTS` /
  `_SEED_PERMITTED_IMPORTS` / `_FIXTURE_PERMITTED_IMPORTS`)
  per framing §4.3 + §8.2.

**Success condition:** *"PR 9 ships seven named tests across two
new test modules, three new fixture modules under a new
`tests/corpus/fixtures/` directory with `__init__.py`. The
seven tests all pass; PR 4 + PR 5 + PR 6 + PR 7 + PR 8
integration tests pass unchanged. Layer 3 lint passes unchanged.
Full corpus suite reaches 207 collected tests in forge env (200
PR 8 close baseline + 7 PR 9 new; named == collected for PR 9
due to no parametrize per framing Q3). The 15 inherited carriers
+ binding framing clarification travel verbatim into three
fixture module docstrings + two new test module docstrings +
PR 9 commit message bodies, per the relevance-by-file ordering
principle (carrier #15 at top). The governing sentence appears in
PR 9 spec §0 + at least one PR 9 commit message body. Zero
modifications to production source files. Zero modifications to
PR 4, PR 6, PR 7, PR 8 test modules. `forge_bridge.__all__`
stays at 19 symbols. Cleanup-pressure-resistance class reaches 9
members at PR 9 close (member #9 = fixture-surface-data-
discipline). Two close artifacts ship at PR 9 close commit:
`A.5.3.2-PR9-CLOSE.md` (PR 9 archival) and
`A.5.3.2-GATE-2-CLOSE.md` (Gate 2 archival)."*

**Architectural success signal:**

**PR 9 lands with 0 production source file modifications.**

This is not merely a scope constraint — it is the architectural
validation signal for the PR 7 + PR 8 decomposition strategy.
Three claims about that strategy are validated by PR 9 closing
without touching production source:

- **Fixtures are consumers, not modifiers.** The fixture surface
  transacts with `drive_seed_fixture` as a pure consumer of the
  PR 8 orchestration boundary. No fixture content requires
  reaching into `_seed.py`, `_capture.py`, `_schema.py`, or any
  other production module. The PR 8 framing's §5 binding
  decisions (Q1 in-process, Q3 signature lock, Q4 single-
  function driver shape) hold under real consumer load.
- **Orchestration topology proved sufficient.** The
  `drive_seed_fixture` surface — single function, three kwargs,
  one orchestration call — is shape-sufficient to drive three
  distinct narrowing-outcome shapes (single-survivor / multi-
  match / zero-match) end-to-end. No additional orchestration
  parameter, no additional driver function, no scope-extension
  helper surfaces at PR 9 implementation. The PR 8 framing §5.5
  (Q4) single-function-driver lock is corroborated by PR 9
  consumption.
- **Gate 2 advances entirely from the outside-in.** PR 7
  established the substrate (`seed_dispatch_scope`,
  `_persist_expectation_record`, `KNOWN_SOURCE_VALUES`,
  `_KNOWN_RECORD_KINDS`); PR 8 established the boundary
  (`emit_seed_expectation`, `drive_seed_fixture`, schema
  validator expectation branch); PR 9 establishes the
  consumption surface (fixtures + integration tests + Layer 2
  fixture discipline) without reaching back into substrate or
  boundary. The decomposition is operationally proven —
  inside-out modification was not required at any point in the
  Gate 2 consumption chain.

A future PR 9 implementation surfacing a need to modify
production source is a structural signal that the PR 7 or PR 8
decomposition is incomplete; the surfaced need routes through
framing-level review BEFORE landing as a production-source diff.
Per §2 out-of-scope #8 + framing §7.1 commitment #8.

---

## 2. Scope

**In scope:**

- **New test-resident directory** —
  `tests/corpus/fixtures/`. Contains:
  - `__init__.py` — empty package init (zero lines beyond
    package marker; no docstring required since the directory
    is a test-resident namespace, not an authored API surface).
  - `fix_single_survivor.py` — single fixture module per §4.2.
  - `fix_multi_match.py` — single fixture module per §4.3.
  - `fix_zero_match.py` — single fixture module per §4.4.
- **New test module** —
  `tests/corpus/test_pr9_fixture_integration.py`. Houses 5
  named tests per §4.5 + §5.1:
  - 3 end-to-end drive tests (one per fixture; tests 1–3).
  - 2 partition/joinability property tests (tests 4–5).
- **New test module** —
  `tests/corpus/test_pr9_fixture_discipline.py`. Houses:
  - `_FIXTURE_PERMITTED_IMPORTS: frozenset[str]` (value-locked
    to 1 symbol — `forge_bridge.corpus._seed.drive_seed_fixture`).
  - `_fixture_corpus_references(source: str) -> list[str]`
    AST walker scoped to `tests/corpus/fixtures/*.py` per §4.6.
  - 2 Layer 2 discipline tests per §5.1 (tests A + B):
    - `test_fixture_permitted_imports_locked_at_one_symbol`
      (frozenset value-lock regression).
    - `test_fixture_modules_references_subset_of_permitted_imports`
      (walker subset-enforcement against the fixture directory).
- **Verified test discipline files** (no modifications):
  - `tests/corpus/test_pr3_discipline.py` — **no code changes.**
    Per PR 7 spec §4.5 amendment, `_ALLOWLIST` governs the
    production-source admission topology. PR 9 ships zero new
    production source files; the discipline test is unaffected.
    Step 1 (§6) verifies the discipline test passes with PR 9's
    new test-surface additions present.
  - `tests/corpus/test_pr4_participation_creep.py` — **no code
    changes.** The PR 4 test enforces narrowing-subsystem →
    corpus one-directional flow (production import topology).
    PR 9's `_FIXTURE_PERMITTED_IMPORTS` + walker enforce a
    distinct ontology (fixture-data discipline) and live in a
    new test module — explicitly NOT an extension of the PR 4
    walker per framing §4.3 + §8.2. The two walkers share AST
    mechanics; **shared AST mechanics do not imply shared
    ontology**.
  - `tests/corpus/test_pr8_seed_surface.py` — **no code
    changes.** PR 8's `_SEED_PERMITTED_IMPORTS` is scoped to
    `_seed.py`'s own imports (5 symbols); PR 9 does not modify
    `_seed.py`. PR 9's `_FIXTURE_PERMITTED_IMPORTS` is scoped to
    fixture modules' imports (1 symbol). The two frozensets are
    parallel, not nested. PR 8's walker continues to enforce
    against `_seed.py`; PR 9's walker enforces against the
    fixture directory glob.
  - `tests/corpus/test_pr6_visual_asymmetry.py` — **no code
    changes.** Layer 3 lint's discovery walk finds calls to
    `emit_divergence_capture` only. PR 9 introduces zero new
    `emit_divergence_capture` call sites; the lint's input set
    is unchanged.
  - All `test_pr7_*.py` modules — **no code changes.** PR 7
    surfaces ship unchanged at PR 9.

**Inheritance from PR 7 + PR 8 (binding):**

> **PR 9 introduces no new dispatch-provenance substrate, no new
> observation-record schema, no new authored-expectation helper,
> no new orchestration surface, no new Layer 3 lint surface. PR
> 7's `seed_dispatch_scope` + `_persist_expectation_record` +
> `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS` ship unchanged.
> PR 8's `emit_seed_expectation` + `drive_seed_fixture` +
> `_SEED_PERMITTED_IMPORTS` + schema-validator expectation-branch
> ship unchanged. PR 6's Layer 3 lint enforcement remains
> unchanged and is inherited transitively.**

This sentence resolves the question of why PR 9 ships zero
modifications to production source. PR 9's job is consumption +
orchestration proof; the substrate it consumes already ships in
PR 7 + PR 8. The new mechanical enforcement is PR-9-LOCAL Layer 2
fixture discipline (two regression-asserted tests scoped to
fixture modules only); the new test infrastructure is the 5-test
integration surface; the new data is the 3-fixture corpus.

**Out of scope** (per framing §7 + carrier #15 + Q-locks):

1. **Seeding the chain-step observation surface.**
   `forge_bridge/console/_step.py:233` is not driven by any
   PR 9 surface — directly or indirectly. Carrier #15 governs.
   Cross-surface expectation semantics require a dedicated
   framing pass; PR 9 does not draft, prefigure, or scaffold
   that pass. Mechanical enforcement: every PR 9 fixture's
   `prompt` field is single-step shape (does NOT fire chain-step
   arbitration when handed to `chat_handler`); test 1 (single-
   survivor e2e) asserts mechanically.
2. **Comparator stub or Gate 4 artifact.** PR 9 ships zero
   comparator code. Tests 4 + 5 (partition + join) prove Gate 4
   unblock properties WITHOUT shipping comparator helpers per
   Gate 2 framing §11.3 ("Gate 2 ships no comparator artifact,
   stub or otherwise"). A future PR proposing a
   `compare_fixture_records(...)` function or any comparator
   helper inside Gate 2's scope is rejected at the spec layer
   per framing §7.1 commitment #2.
3. **Fixture loader / CLI / daemon hook.** Per framing §5.2 (Q2)
   + governing sentence. The integration tests ARE the fixture
   consumer surface at PR 9. A future PR proposing a
   `load_fixture_corpus()` function, a `forge-bridge fixtures
   ...` CLI command, or a daemon-startup fixture-driver invocation
   is rejected at the spec layer per framing §7.1 commitment #3.
4. **Fixture registry / factory / generator / parametrization
   framework.** Per framing §5.1 (Q1) + §5.3 (Q3) + governing
   sentence. Each fixture is a Python module with one top-level
   `FIXTURE` dict; no programmatic fixture-management abstraction
   lands. A future PR proposing `@pytest.mark.parametrize` over
   the three fixtures, a `FIXTURES = [...]` collection, a
   `make_fixture(id, prompt, expected)` factory, or a fixture-
   discovery walker is rejected at the spec layer per framing
   §7.1 commitment #4 + member #9 protection.
5. **Non-Python fixture formats.** Per framing §5.1 (Q1). No
   JSON, YAML, TOML, CSV fixture files. A future PR proposing a
   non-Python fixture format is rejected at the spec layer per
   framing §7.1 commitment #5.
6. **Expectation record schema extension.** Per framing §5.5
   (Q5) + member #7 protection. The 3 PR-8-locked required keys
   (`fixture_id`, `prompt`, `expected_narrow`) remain the only
   required keys. No new required keys, no new optional keys.
   A future PR proposing a fourth field is rejected at the spec
   layer per framing §7.1 commitment #6.
7. **`forge_bridge.__all__` promotion.** Per framing §5.6 (Q6) +
   PR 8 spec §2 out-of-scope #4. Neither `emit_seed_expectation`
   nor `drive_seed_fixture` enters `forge_bridge.__all__` at
   PR 9. The PR 8 `__all__` drift guard test
   (`test_pr8_helpers_remain_corpus_internal`) continues to
   enforce mechanically.
8. **Modifying any production source file.** PR 9 ships zero
   changes to `_seed.py`, `_capture.py`, `_schema.py`,
   `_sources.py`, `_identity.py`, `_topology.py`, `reader.py`,
   `console/handlers.py`, `console/_step.py`, or any other
   production source. PR 9 is purely test-surface additions.
9. **Modifying PR 4, PR 6, PR 7, PR 8 test modules.**
   `test_pr4_participation_creep.py` is NOT extended. PR 6's
   Layer 3 lint module is NOT touched. PR 7's modules ship
   unchanged. PR 8's `test_pr8_seed_surface.py` is NOT extended.
   PR 9's new test modules live alongside, not within, the
   existing PR-N modules.
10. **Programmatic fixture generation.** No
    `[FIXTURE for n in range(N)]` patterns, no fixture-discovery
    walkers driving test parametrization, no fixture-data
    builders. Each fixture is hand-authored. A future PR proposing
    programmatic fixture emission is rejected at the spec layer
    per framing §7.1 commitment #10 + member #9 protection.
11. **Test ordering coupling.** Each PR 9 test is independent.
    No fixture-emitted state survives across tests beyond the
    date-partitioned JSONL persistence (which PR 9 tests read by
    `fixture_id` match, NOT by file ordering). The
    PR-8-supplied `clean_rate_limit_state` fixture grounds each
    test's rate-limit slate. A future PR proposing test-to-test
    ordering dependencies (e.g., test 5 reading records produced
    by test 1) is rejected at the spec layer per framing §7.1
    commitment #11.
12. **Acquiring additional Layer 2 admissions.** A future PR
    proposing to admit a second symbol to
    `_FIXTURE_PERMITTED_IMPORTS` (e.g., `emit_seed_expectation`,
    `seed_dispatch_scope`, or any direct corpus-internal symbol)
    is rejected at the spec layer per cleanup-pressure class
    member #9 + framing §5.4 (Q4) + framing §8.2. The single-
    symbol-gate IS the fixture-data discipline; admitting a
    second symbol erodes the protection.
13. **Cross-fixture imports.** No fixture module imports from
    another fixture module. No shared base classes, mixins,
    helper functions. Each fixture stands alone. A future PR
    proposing `from fix_single_survivor import FIXTURE_BASE`
    inside another fixture module is rejected mechanically by
    `_FIXTURE_PERMITTED_IMPORTS` + walker (cross-fixture imports
    are not `forge_bridge.corpus.*` imports, but they ARE
    structural imports — the walker enforces a stricter "no
    corpus imports beyond the orchestration call" semantic; the
    cross-fixture case is rejected via spec rather than walker
    mechanics).

---

## 3. The six risks → named tests

PR 9's risk topology differs from PR 7's and PR 8's. PR 7 was
plumbing work (risks: substrate semantics leaking across
boundaries; substrate eroding under cleanup pressure). PR 8 was
boundary work (risks: new authority surface blurring against
existing surfaces). PR 9 is **integration work** — the risks are
*the integration not actually exercising what it claims to
exercise*, *the fixture surface acquiring infrastructure under
cleanup pressure*, and *the Gate 4 unblock proofs becoming
coupled to the e2e drive*.

Six risks. Five map to named tests (3 e2e + 2 property);
two-discipline-tests cover risk #4; risks #5–#6 map to
verification checklist items at Step 5 (no named tests required —
Step 5 verifier checks them retrospectively against the
post-PR-9 codebase).

| # | Risk | Mitigation |
|---|---|---|
| 1 | Single-survivor narrowing produces expectation + observation that don't actually compose end-to-end | Test 1 (`test_fixture_runs_end_to_end_single_survivor`) drives the fixture and asserts BOTH records persist with the correct `record_kind` + matching `fixture_id` + correct field shapes. |
| 2 | Multi-match ambiguity-rejection narrowing produces records that overload the chat-handler semantics or fire chain-step | Test 2 (`test_fixture_runs_end_to_end_multi_match`) drives the multi-match fixture and asserts the persisted observation reflects ambiguity-rejection arbitration outcome per carrier #10 (`pr20_condition_met=False`, `collapse_occurred=False`, `narrower_decision` carries the filtered list verbatim). |
| 3 | Zero-match narrowing produces records that silently fall through or fire chain-step | Test 3 (`test_fixture_runs_end_to_end_zero_match`) drives the zero-match fixture and asserts the persisted observation reflects zero-match arbitration outcome per carrier #10 (`narrower_decision` carries the empty list). |
| 4 | Fixture modules silently acquire forbidden imports, eroding fixture-data discipline | Tests A + B in `test_pr9_fixture_discipline.py` mechanically enforce: A (`test_fixture_permitted_imports_locked_at_one_symbol`) — frozenset value-lock regression; B (`test_fixture_modules_references_subset_of_permitted_imports`) — walker enforcement against the fixture directory glob. |
| 5 | The two persisted records (expectation + observation) cannot be partitioned by `record_kind` (Gate 4 unblock dependency #1) | Test 4 (`test_observation_and_expectation_distinguishable_by_record_kind`) drives one fixture and asserts the two records have distinct `record_kind` values; the schema validator accepts both. Independent of tests 1–3 (drives its own fixture; not coupled to test ordering). |
| 6 | The two persisted records cannot be joined by `fixture_id` (Gate 4 unblock dependency #2) | Test 5 (`test_records_join_on_fixture_id`) drives one fixture and asserts the two records share the same `fixture_id`; a `fixture_id`-keyed join over corpus reader output reunites them. Independent of tests 1–4 (drives its own fixture). |

Risks #5–#6 are Gate 4 unblock proofs — they decouple the
comparator dependency from the e2e drive. A future PR could
break test 1 (an arbitrary e2e regression) without breaking
tests 4–5 (the partition + join properties), and vice versa.
The orthogonality is the load-bearing protection.

Verification checklist items mitigating non-test risks:

| Item | Risk | Mitigation |
|---|---|---|
| Carrier travel verification | Carriers don't actually land verbatim in fixture module docstrings | Step 5 verifier reads each fixture module's docstring, each new test module's docstring, and cross-references each verbatim block against §0. Surfaces drift before close commit. |
| Regression contract | PR 4/6/7/8 test surfaces regress silently due to PR 9 additions (e.g., directory-discovery side-effects) | Step 5 verifier runs full `pytest tests/corpus/` and confirms 207 collected (200 baseline + 7 new). Per-module assertions: PR 4 walker (`test_pr4_participation_creep.py`) passes unchanged; PR 6 Layer 3 lint passes unchanged; PR 7 module count unchanged; PR 8 module count unchanged. |
| `__all__` drift | A future PR speculatively promotes `drive_seed_fixture` to `forge_bridge.__all__` during PR 9 implementation | PR 8's existing `test_pr8_helpers_remain_corpus_internal` test continues to enforce; Step 5 verifier confirms it passes against post-PR-9 codebase. PR 9 does NOT add an additional `__all__` drift guard test (the existing one suffices). |

---

## 4. Module surface

### 4.1 `tests/corpus/fixtures/__init__.py` (new)

**Path:** `tests/corpus/fixtures/__init__.py`

**Purpose:** Empty package init. Makes `tests/corpus/fixtures/`
a Python package importable by `tests.corpus.fixtures.fix_*` in
the integration test module.

**Content:**

```python
"""Test-resident seed fixture package for PR 9.

Each fixture module exposes one top-level constant FIXTURE: dict
carrying the three PR-8-locked keys (fixture_id, prompt,
expected_narrow). Per A.5.3.2-PR9-FRAMING.md §4.1 + §5.1 (Q1) +
member #9 (fixture-surface-data-discipline): fixture modules are
data + one orchestration call only. The Layer 2 fixture
discipline (_FIXTURE_PERMITTED_IMPORTS + walker in
test_pr9_fixture_discipline.py) enforces mechanically.

This __init__.py carries no logic; the package marker exists
solely so `from tests.corpus.fixtures.fix_<name> import FIXTURE`
works from test_pr9_fixture_integration.py.
"""
```

The docstring is brief; the `__init__.py` carries no carriers
verbatim (carriers live in the fixture modules themselves, where
the data lives). The `__init__.py` is a structural marker, not
an authored surface.

### 4.2 `tests/corpus/fixtures/fix_single_survivor.py` (new)

**Path:** `tests/corpus/fixtures/fix_single_survivor.py`

**Purpose:** Single fixture exercising the canonical single-
survivor narrowing outcome. `chat_handler`'s arbitration on the
fixture's `prompt` produces a single tool name; the observation
record's `narrower_decision` carries `[<that tool name>]`; the
expectation record's `expected_narrow` carries the same single-
element list.

**Content shape:**

```python
"""Module docstring carries the 15 inherited carriers + binding
framing clarification per the relevance-by-file ordering
principle (carrier #15 at top — chat-handler-only seeding scope
is the most-relevant inherited governance for this surface).

PR 9 carrier block (verbatim — see A.5.3.2-PR9-SPEC.md §0):

PR 8 carrier #15 — chat-handler-only seeding scope (LANDS AT
TOP per relevance-by-file ordering):

  [verbatim text of carrier #15]

Inherited carriers #1–#2 — risk-category shift (PR 4):
  [verbatim]

Inherited carriers #3–#6 — integration-discipline quartet (PR 4):
  [verbatim — all four]

Inherited carrier #7 — finalized-state contract (PR 4):
  [verbatim]

Inherited carrier #8 — risk-inheritance + surface-geometry (PR 5):
  [verbatim]

Inherited carrier #9 — caller's view of deployment identity (PR 5):
  [verbatim]

Inherited carrier #10 — ambiguity-as-arbitration-outcome (PR 5):
  [verbatim — full text including narrower_decision specifics]

Inherited carrier #11 — measured-not-inferred coverage (PR 5):
  [verbatim]

Inherited carrier #12 — structural-backstop framing (PR 6):
  [verbatim]

Inherited carrier #13 — observation-not-participation framing (PR 6):
  [verbatim]

Inherited carrier #14 — declared epistemic class vs. persisted
provenance (Gate 2):
  [verbatim]

Binding framing clarification — call-site-owned arbitration
inputs (Gate 2):
  [verbatim]

Fixture purpose:

This fixture exercises the canonical single-survivor narrowing
outcome. The prompt is shape-locked at single-step (does NOT fire
chain-step arbitration); the expected_narrow declares a single
tool name; the chat_handler arbitration on this prompt is
expected to produce a narrowing decision matching that single
tool name. The integration test
(test_pr9_fixture_integration.py::test_fixture_runs_end_to_end_single_survivor)
drives this fixture and asserts the expectation + observation
records both persist correctly.

PR 9 governs by one framing-level sentence (per framing §0):
PR 9 proves topology, not infrastructure. The fixture is data
+ one orchestration call only — no helpers, no factories, no
parametrization framework. Per member #9 protection
(fixture-surface-data-discipline; framing §6.1).
"""
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr9-single-survivor",
    "prompt": "<exact prompt text — see Step 2 implementation note>",
    "expected_narrow": ["<expected tool name — see Step 2 implementation note>"],
}
```

**Step 2 implementation note:** The exact `prompt` text + the
exact `expected_narrow` tool name require reading the live
arbitration surface at Step 2 implementation time. The prompt
must satisfy two binding constraints:

1. **Single-step shape** — the prompt does NOT fire chain-step
   arbitration when handed to `chat_handler` (per carrier #15).
   Mechanical verification at Step 2: trace `chat_handler`'s
   execution against the chosen prompt and confirm `_step.py:233`
   is not reached.
2. **Single-survivor narrowing outcome** — the prompt yields
   exactly one tool name from the narrowing decision. The
   `expected_narrow` declares that tool name.

The fixture is hand-authored — the spec does NOT pre-name a
prompt or a tool. Per framing §7.1 commitment #10 (no
programmatic fixture generation) + member #9 protection (data,
not infrastructure), the spec author selects the prompt + tool
combination at Step 2 implementation time after surveying
`chat_handler`'s live behavior. Step 2 commit message names the
selection rationale + the live-arbitration check that confirmed
the single-step + single-survivor binding constraints.

### 4.3 `tests/corpus/fixtures/fix_multi_match.py` (new)

**Path:** `tests/corpus/fixtures/fix_multi_match.py`

**Purpose:** Single fixture exercising the multi-match ambiguity-
rejection narrowing outcome per carrier #10. `chat_handler`'s
arbitration on the fixture's `prompt` produces multiple tool
names; the observation record's `narrower_decision` carries the
multi-element list verbatim; `pr20_condition_met=False`;
`collapse_occurred=False`. The expectation record's
`expected_narrow` declares the multi-element list — the
fixture-author's claim about what arbitration ought to produce
for the multi-match prompt.

**Content shape:**

Module docstring identical to §4.2 in structure (carriers at top
per relevance-by-file ordering; fixture purpose paragraph
specific to multi-match) — the spec does not repeat the full
carrier verbatim block for each fixture module (carriers are
identical across all three; only the fixture-purpose paragraph
differs).

Fixture purpose paragraph (specific to this module):

> This fixture exercises the multi-match ambiguity-rejection
> narrowing outcome per carrier #10. The prompt is shape-locked
> at single-step; the expected_narrow declares a multi-element
> list (≥2 tool names); the chat_handler arbitration on this
> prompt is expected to produce a narrowing decision carrying
> the multi-element filtered list verbatim with
> pr20_condition_met=False + collapse_occurred=False per the
> ambiguity-rejection semantics carrier #10 establishes. The
> integration test
> (test_pr9_fixture_integration.py::test_fixture_runs_end_to_end_multi_match)
> drives this fixture and asserts both records persist correctly
> + the observation reflects the ambiguity-rejection outcome.

**Constant shape:**

```python
FIXTURE: dict = {
    "fixture_id": "fix-pr9-multi-match",
    "prompt": "<multi-match-inducing prompt text — see Step 2 implementation note>",
    "expected_narrow": ["<tool-1>", "<tool-2>", ...],  # ≥2 elements
}
```

**Step 2 implementation note:** Same selection-at-implementation-
time discipline as §4.2. Binding constraints for this fixture's
prompt:

1. **Single-step shape** — does NOT fire chain-step arbitration.
2. **Multi-match narrowing outcome** — yields ≥2 tool names from
   the narrowing decision. The `expected_narrow` declares the
   exact multi-element list arbitration produces.

The multi-match list ordering must match arbitration's output
ordering exactly (test 2 asserts list equality, not set
equality, per carrier #10's "narrower_decision carries the
filtered list verbatim" language).

### 4.4 `tests/corpus/fixtures/fix_zero_match.py` (new)

**Path:** `tests/corpus/fixtures/fix_zero_match.py`

**Purpose:** Single fixture exercising the zero-match ambiguity-
rejection narrowing outcome per carrier #10. `chat_handler`'s
arbitration on the fixture's `prompt` produces zero tool names;
the observation record's `narrower_decision` carries the empty
list verbatim; `pr20_condition_met=False`; `collapse_occurred=False`.
The expectation record's `expected_narrow` declares the empty
list — the fixture-author's claim that arbitration ought to
produce zero survivors for the zero-match prompt.

**Content shape:**

Module docstring identical to §4.2 structure; fixture purpose
paragraph specific to zero-match.

Fixture purpose paragraph (specific to this module):

> This fixture exercises the zero-match ambiguity-rejection
> narrowing outcome per carrier #10. The prompt is shape-locked
> at single-step; the expected_narrow declares the empty list;
> the chat_handler arbitration on this prompt is expected to
> produce a narrowing decision carrying the empty list verbatim
> with pr20_condition_met=False + collapse_occurred=False per
> the zero-match ambiguity-rejection semantics. The integration
> test
> (test_pr9_fixture_integration.py::test_fixture_runs_end_to_end_zero_match)
> drives this fixture and asserts both records persist correctly
> + the observation reflects the zero-match outcome.
>
> The empty-list expected_narrow is a valid expectation — it
> expresses "expected zero-survivor narrowing for this prompt"
> per emit_seed_expectation's contract
> (forge_bridge/corpus/_seed.py:259–264).

**Constant shape:**

```python
FIXTURE: dict = {
    "fixture_id": "fix-pr9-zero-match",
    "prompt": "<zero-match-inducing prompt text — see Step 2 implementation note>",
    "expected_narrow": [],  # empty list — explicitly valid per emit_seed_expectation contract
}
```

**Step 2 implementation note:** Same selection-at-implementation-
time discipline as §4.2 + §4.3. Binding constraints:

1. **Single-step shape** — does NOT fire chain-step arbitration.
2. **Zero-match narrowing outcome** — yields zero tool names
   from the narrowing decision. The `expected_narrow` is the
   empty list.

The empty-list case is explicitly valid per
`emit_seed_expectation`'s docstring (the empty list expresses
"expected zero-survivor narrowing for this prompt" — a valid
expectation, not a missing field).

### 4.5 `tests/corpus/test_pr9_fixture_integration.py` (new)

**Path:** `tests/corpus/test_pr9_fixture_integration.py`

**Purpose:** Five named integration tests proving end-to-end
composition of PR 7 + PR 8 surfaces under three narrowing-
outcome shapes + two Gate 4 unblock properties.

**Top-level structure:**

```python
"""[Module docstring — carriers #1–#15 + binding framing
clarification per relevance-by-file ordering; carrier #15 at top.
Plus the PR 9 governing sentence at the bottom of the carrier
block:

  PR 9 proves topology, not infrastructure.

This module operationalizes the governing sentence at the
integration-test surface: each test independently invokes
drive_seed_fixture against ONE fixture (no parametrization, no
shared state, no test-to-test ordering), and asserts the
end-to-end composition properties directly. The five tests are
hand-named and hand-asserted — no programmatic test generation.
Per framing §4.2 + §7.1 commitments #4 + #11.]
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from forge_bridge.corpus._seed import drive_seed_fixture
from forge_bridge.corpus.reader import read_records  # PR 7 reader surface

# Fixture imports — one per fixture module, named explicitly:
from tests.corpus.fixtures.fix_single_survivor import FIXTURE as FIXTURE_SINGLE_SURVIVOR
from tests.corpus.fixtures.fix_multi_match import FIXTURE as FIXTURE_MULTI_MATCH
from tests.corpus.fixtures.fix_zero_match import FIXTURE as FIXTURE_ZERO_MATCH


def test_fixture_runs_end_to_end_single_survivor(
    clean_rate_limit_state,  # PR 8 conftest fixture
    tmp_corpus_dir,  # existing conftest.py fixture surface (corpus dir isolation)
):
    """Single-survivor e2e: drive fixture → assert two records persist
    with correct shape + matching fixture_id + distinct record_kind."""
    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = read_records(tmp_corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for fix-pr9-single-survivor; got {len(matching)}"
    )
    record_kinds = {r["record_kind"] for r in matching}
    assert record_kinds == {"observation", "expectation"}, (
        f"Expected record_kinds={{observation, expectation}}; got {record_kinds}"
    )
    expectation = next(r for r in matching if r["record_kind"] == "expectation")
    observation = next(r for r in matching if r["record_kind"] == "observation")
    assert expectation["prompt"] == FIXTURE_SINGLE_SURVIVOR["prompt"]
    assert expectation["expected_narrow"] == FIXTURE_SINGLE_SURVIVOR["expected_narrow"]
    assert "source" not in expectation, "expectation must not carry source field"
    assert observation["source"] == "seed", "observation must carry source=seed under driver scope"
    assert observation.get("narrower_decision") == FIXTURE_SINGLE_SURVIVOR["expected_narrow"]


def test_fixture_runs_end_to_end_multi_match(
    clean_rate_limit_state,
    tmp_corpus_dir,
):
    """Multi-match e2e: drive fixture → assert ambiguity-rejection
    observation per carrier #10 (filtered list verbatim, no collapse)."""
    drive_seed_fixture(**FIXTURE_MULTI_MATCH)

    records = read_records(tmp_corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-multi-match"]
    assert len(matching) == 2
    observation = next(r for r in matching if r["record_kind"] == "observation")
    # Carrier #10 enforcement at multi-match: narrower_decision carries the
    # filtered list verbatim; no collapse; no pr20 condition met.
    assert observation["narrower_decision"] == FIXTURE_MULTI_MATCH["expected_narrow"]
    assert observation.get("pr20_condition_met") is False
    assert observation.get("collapse_occurred") is False
    assert len(observation["narrower_decision"]) >= 2, (
        "multi-match fixture must yield ≥2 tool names from narrowing"
    )


def test_fixture_runs_end_to_end_zero_match(
    clean_rate_limit_state,
    tmp_corpus_dir,
):
    """Zero-match e2e: drive fixture → assert zero-survivor observation
    per carrier #10 (empty list verbatim, no collapse)."""
    drive_seed_fixture(**FIXTURE_ZERO_MATCH)

    records = read_records(tmp_corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-zero-match"]
    assert len(matching) == 2
    observation = next(r for r in matching if r["record_kind"] == "observation")
    # Carrier #10 enforcement at zero-match: narrower_decision is the empty list;
    # no collapse; no pr20 condition met.
    assert observation["narrower_decision"] == []
    assert observation.get("pr20_condition_met") is False
    assert observation.get("collapse_occurred") is False
    # Expectation's expected_narrow is also empty list — fixture-author's claim
    # matches arbitration's actual outcome at zero-match. The match is
    # archaeology-grade per Gate 2 framing §4.4 + member #7 protection.
    expectation = next(r for r in matching if r["record_kind"] == "expectation")
    assert expectation["expected_narrow"] == []


def test_observation_and_expectation_distinguishable_by_record_kind(
    clean_rate_limit_state,
    tmp_corpus_dir,
):
    """Gate 4 unblock proof #1: record_kind partition correctness.

    Drives one fixture (single-survivor) and asserts the two persisted
    records have distinct record_kind values that the schema validator
    accepts. Independent of tests 1–3 — drives its own fixture,
    asserts a different property. Decouples the comparator's partition
    dependency from any e2e regression in tests 1–3.

    Independence is structural: a future PR could break test 1 (e2e
    regression) without breaking this test, and vice versa. The two
    failure modes are orthogonal; both must pass for Gate 4 to remain
    unblocked.
    """
    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = read_records(tmp_corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2

    # Partition by record_kind:
    expectations = [r for r in matching if r["record_kind"] == "expectation"]
    observations = [r for r in matching if r["record_kind"] == "observation"]
    assert len(expectations) == 1, "exactly one expectation record per fixture invocation"
    assert len(observations) == 1, "exactly one observation record per fixture invocation"

    # Schema validator accepts both record kinds:
    from forge_bridge.corpus._schema import validate_capture_record
    validate_capture_record(expectations[0])
    validate_capture_record(observations[0])


def test_records_join_on_fixture_id(
    clean_rate_limit_state,
    tmp_corpus_dir,
):
    """Gate 4 unblock proof #2: fixture_id joinability.

    Drives one fixture (single-survivor) and asserts the two persisted
    records share the same fixture_id; a fixture_id-keyed join over the
    corpus reader output reunites them as a pair. Independent of tests
    1–4 — drives its own fixture, asserts a different property.
    Decouples the comparator's join dependency from any partition
    regression in test 4.
    """
    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = read_records(tmp_corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2

    # The two records share the same fixture_id mechanically — the join key
    # is the fixture_id field, populated identically at expectation persistence
    # (emit_seed_expectation) + observation persistence (handlers.py:1185 under
    # seed_dispatch_scope).
    fixture_ids = {r["fixture_id"] for r in matching}
    assert fixture_ids == {"fix-pr9-single-survivor"}, (
        "both records must share the same fixture_id — Gate 4 comparator depends on this"
    )

    # Joinability proof: build a fixture_id-keyed dict over the corpus reader
    # output; verify the entry for our fixture_id contains both record kinds.
    by_fixture: dict[str, dict[str, dict]] = {}
    for r in records:
        fid = r.get("fixture_id")
        kind = r.get("record_kind")
        if fid is None or kind is None:
            continue
        by_fixture.setdefault(fid, {})[kind] = r
    paired = by_fixture.get("fix-pr9-single-survivor", {})
    assert set(paired.keys()) == {"observation", "expectation"}, (
        f"fixture_id-keyed join did not reunite the pair: {set(paired.keys())}"
    )
```

**Test signature commitments (locked):**

- All 5 tests use the `clean_rate_limit_state` fixture (PR 8
  conftest contribution) to ground the rate-limit slate per
  test invocation.
- All 5 tests use the `tmp_corpus_dir` fixture — existing
  `conftest.py` fixture surface — to isolate the corpus JSONL
  directory per test. Historical provenance of the fixture is
  not load-bearing for this spec.
- All 5 tests import fixture modules by explicit name; no
  `pytest.fixture(params=...)` patterns, no
  `@pytest.mark.parametrize`.
- Tests 4 + 5 use the single-survivor fixture (the simplest
  shape for partition + join assertions). Their independence
  from tests 1–3 is structural — each test invokes
  `drive_seed_fixture` itself; no test depends on records
  produced by another test.

**What this module does NOT contain:**

- Helper functions (no `def make_assertions(...)`, no
  `def assert_records_pair(...)`).
- Shared fixture/setup logic (no `pytest.fixture(autouse=True)`
  beyond the conftest-supplied fixtures).
- `@pytest.mark.parametrize` decorators.
- Test-to-test ordering markers (`@pytest.mark.dependency`,
  `@pytest.mark.order`).

### 4.6 `tests/corpus/test_pr9_fixture_discipline.py` (new)

**Path:** `tests/corpus/test_pr9_fixture_discipline.py`

**Purpose:** Parallel Layer 2 fixture discipline. Houses
`_FIXTURE_PERMITTED_IMPORTS` (value-locked frozenset, 1 symbol)
+ `_fixture_corpus_references()` AST walker + 2 discipline tests
(value-lock + walker subset-enforcement).

**Explicitly NOT** an extension of
`tests/corpus/test_pr4_participation_creep.py` — distinct
ontology. Shared AST mechanics do not imply shared ontology.

**Three-walker partition (spec-level, parallel-not-extension):**

At PR 9 close, three Layer 2 AST walkers operate against the
codebase. Each protects a distinct ontology. The protections
are partitioned, not unified:

- **PR 4 walker** (`tests/corpus/test_pr4_participation_creep.py`)
  — protects **production import topology**: the narrowing-
  subsystem may not acquire corpus dependencies. Target set:
  production source files. Rejection rule: one-directional
  flow.
- **PR 8 walker** (`tests/corpus/test_pr8_seed_surface.py`,
  `_corpus_references` + `_SEED_PERMITTED_IMPORTS`) — protects
  **orchestration participation discipline**: `_seed.py`'s own
  corpus-internal imports stay within the 5-symbol bounded
  toolbox (semantics-not-cardinal per PR 8 close §1.7). Target
  set: `_seed.py`. Rejection rule: persistence-topology
  authority cannot leak into the seed-driver-internal scope.
- **PR 9 walker** (`tests/corpus/test_pr9_fixture_discipline.py`,
  `_fixture_corpus_references` + `_FIXTURE_PERMITTED_IMPORTS`)
  — protects **declarative fixture-data discipline**: fixture
  modules under `tests/corpus/fixtures/` import nothing from
  the corpus beyond the single orchestration symbol
  (`drive_seed_fixture`). Target set: fixture directory glob.
  Rejection rule: single-symbol-gate.

The three walkers share AST mechanics (each uses `ast.walk` +
import-node traversal); they DO NOT share ontology.
Generalization would require unifying their target-set semantics
+ their admission ontologies + their rejection-message shapes +
their future evolution pressure — which collapses three
protections into one rejection surface.

**Future "walker unification" cleanup proposals are rejected at
the spec layer** per framing §4.3 + §8.2 + this section. A
unified walker abstraction is appealing locally (deduplication
of AST traversal code) but architecturally erodes three distinct
protections. Each walker stays local to its ontology.

**Shared AST mechanics do not imply shared ontology.**

**Top-level structure:**

```python
"""[Module docstring — carriers #1–#15 + binding framing
clarification per relevance-by-file ordering; carrier #15 at top.
Plus the parallel-not-extension rationale paragraph + the closing
sentence per framing §4.3.

The parallel-not-extension rationale:

  _FIXTURE_PERMITTED_IMPORTS is the parallel Layer 2 frozenset
  scoped to fixture modules under tests/corpus/fixtures/. It is
  NOT an extension of test_pr4_participation_creep.py's PR 4
  walker — the two walkers protect distinct ontologies.

  PR 4 walker (test_pr4_participation_creep.py) protects
  PRODUCTION import topology: the narrowing-subsystem may not
  acquire corpus dependencies (one-directional flow). The PR 4
  walker walks PRODUCTION source files and rejects forbidden
  production-to-corpus imports.

  PR 9 walker (this file) protects DECLARATIVE FIXTURE-DATA
  discipline: fixture modules under tests/corpus/fixtures/ are
  data + one orchestration call only. The PR 9 walker walks
  fixture modules (declared TEST source, not production) and
  rejects any corpus import other than drive_seed_fixture.

  The two walkers share AST mechanics (ImportFrom traversal,
  fully-qualified dotted reference extraction) but they are NOT
  the same walker generalized. Generalization would require
  unifying their target-set semantics + their admission
  ontologies, which collapses two protections into one rejection
  surface. Each walker stays local to its ontology.

  Shared AST mechanics do not imply shared ontology.

PR 9 governing sentence (framing-scoped):

  PR 9 proves topology, not infrastructure.

This module operationalizes the governing sentence at the
Layer 2 fixture-discipline surface: the frozenset value-locks at
one symbol (admitting any second symbol would erode member #9's
single-symbol-gate protection per framing §6.1), and the walker
target-set is the fixture directory glob (admitting any other
target would erode the parallel-not-extension protection).
]
"""
from __future__ import annotations

import ast
import pathlib

# Layer 2 fixture-discipline constant — value-locked at 1 symbol.
# Admission to this frozenset requires explicit framing-level review
# per cleanup-pressure-resistance class member #9 (framing §6.1).
_FIXTURE_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    "forge_bridge.corpus._seed.drive_seed_fixture",
})

# Target glob for the walker. Lives at module scope so test B can
# discover the file set + the value-lock test can document the scope.
_FIXTURE_DIRECTORY = pathlib.Path(__file__).parent / "fixtures"


def _fixture_corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified `forge_bridge.corpus.<X>` reference
    imported by `source`.

    Mirrors the AST mechanics of
    tests/corpus/test_pr8_seed_surface.py::_corpus_references — scoped
    to a different target-set (fixture modules vs. _seed.py) and a
    different protected ontology (fixture-data discipline vs.
    seed-driver-internal participation discipline). Shared AST
    mechanics do not imply shared ontology.

    Walks the AST for ImportFrom nodes and records dotted symbol
    forms for any `from forge_bridge.corpus.<submodule> import
    <symbol>` (the form `_FIXTURE_PERMITTED_IMPORTS` admits).
    Direct `import forge_bridge.corpus.<submodule>` is also
    captured but expected to not appear in fixture modules
    (fixtures import nothing at PR 9; the admission for
    drive_seed_fixture exists for future cases where a fixture
    module wants to inline its driver invocation per framing §4.1).

    Returns a list of dotted strings — one per imported name or
    submodule. Comments and docstrings are not inspected.
    """
    refs: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("forge_bridge.corpus"):
                for alias in node.names:
                    refs.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("forge_bridge.corpus"):
                    refs.append(alias.name)
    return refs


def test_fixture_permitted_imports_locked_at_one_symbol():
    """Frozenset value-lock regression.

    The frozenset MUST equal exactly:
      {"forge_bridge.corpus._seed.drive_seed_fixture"}

    Cardinality is exactly 1. Any future PR adding a second symbol
    must amend the spec + framing first (member #9 protection;
    framing §6.1 single-symbol-gate). The test asserts both
    cardinality AND exact set membership.
    """
    expected = frozenset({"forge_bridge.corpus._seed.drive_seed_fixture"})
    assert _FIXTURE_PERMITTED_IMPORTS == expected, (
        "_FIXTURE_PERMITTED_IMPORTS has drifted from the framing §5.4 (Q4) lock. "
        "Expected exactly one symbol: forge_bridge.corpus._seed.drive_seed_fixture. "
        f"Actual ({len(_FIXTURE_PERMITTED_IMPORTS)} elements):\n"
        + "".join(f"  {s}\n" for s in sorted(_FIXTURE_PERMITTED_IMPORTS))
        + "Any admission of a second symbol requires framing-level review per "
        + "cleanup-pressure-resistance class member #9 (framing §6.1)."
    )


def test_fixture_modules_references_subset_of_permitted_imports():
    """Walker subset-enforcement.

    Every Python file under tests/corpus/fixtures/ (excluding
    __init__.py) is walked; every fully-qualified
    forge_bridge.corpus.<X> reference is collected; the collected
    set must be a SUBSET of _FIXTURE_PERMITTED_IMPORTS.

    At PR 9 close: fixture modules import nothing from
    forge_bridge.corpus (the FIXTURE constants are pure data
    delegated to drive_seed_fixture via the integration test, not
    via the fixture module itself). The subset-enforcement holds
    vacuously (empty set is a subset of any set), which is the
    correct shape at PR 9.

    A future PR adding `from forge_bridge.corpus._seed import
    drive_seed_fixture` to a fixture module (e.g., to inline the
    driver invocation) passes the walker because
    drive_seed_fixture is admitted. A future PR adding any other
    corpus symbol import fails the walker.
    """
    fixture_files = sorted(
        f for f in _FIXTURE_DIRECTORY.glob("*.py") if f.name != "__init__.py"
    )
    assert len(fixture_files) >= 1, (
        f"Expected fixture modules under {_FIXTURE_DIRECTORY}; "
        f"found {len(fixture_files)}. PR 9 ships 3 fixture modules per "
        "framing §5.3 (Q3)."
    )

    offenders: list[tuple[str, list[str]]] = []
    for f in fixture_files:
        refs = _fixture_corpus_references(f.read_text())
        forbidden = [r for r in refs if r not in _FIXTURE_PERMITTED_IMPORTS]
        if forbidden:
            offenders.append((f.name, forbidden))

    assert not offenders, (
        "Fixture modules acquired forbidden corpus imports — violating "
        "member #9 (fixture-surface-data-discipline; framing §6.1) + Q4 "
        "single-symbol-gate Layer 2 discipline.\n"
        + "Offenders:\n"
        + "".join(
            f"  {fname}:\n" + "".join(f"    {r}\n" for r in fbidn)
            for fname, fbidn in offenders
        )
        + f"\nPermitted ({len(_FIXTURE_PERMITTED_IMPORTS)} symbol):\n"
        + "".join(f"  {s}\n" for s in sorted(_FIXTURE_PERMITTED_IMPORTS))
        + "\nAny import beyond the single permitted symbol requires "
        + "framing-level review (member #9 protection)."
    )
```

**Test signature commitments (locked):**

- Test A names the frozenset value-lock regression mechanically;
  the assertion error message names the spec/framing references
  + the single-symbol-gate protection rationale.
- Test B walks the fixture directory glob (excluding
  `__init__.py`) and enforces subset semantics; the assertion
  error message names offender files + forbidden references +
  the protection rationale.
- The walker handles both `ImportFrom` and `Import` node kinds
  (PR 8's walker handled only `ImportFrom`; PR 9's walker is
  slightly more conservative to handle the hypothetical case
  where a fixture module uses `import forge_bridge.corpus._seed
  as fb_seed` — currently rejected by spec language, but the
  walker captures it for completeness).

**What this module does NOT contain:**

- A walker that targets `_seed.py` (PR 8's walker handles that;
  PR 9's walker target is the fixture directory only).
- A walker that targets `_capture.py` or any other corpus
  source (PR 4's walker handles the production-source target).
- Helper functions beyond `_fixture_corpus_references()`.
- Tests beyond the two discipline tests (the five integration
  tests live in §4.5).
- An autouse fixture (no setup needed; the discipline tests are
  static AST walks).

---

## 5. Test plan

### 5.1 Test inventory (7 named tests)

| # | Module | Test name | Risk | Notes |
|---|---|---|---|---|
| 1 | `test_pr9_fixture_integration.py` | `test_fixture_runs_end_to_end_single_survivor` | §3 risk #1 | Single-survivor e2e drive + record persistence assertion. |
| 2 | `test_pr9_fixture_integration.py` | `test_fixture_runs_end_to_end_multi_match` | §3 risk #2 | Multi-match e2e + carrier #10 enforcement (`narrower_decision` verbatim filtered list, no collapse, no pr20). |
| 3 | `test_pr9_fixture_integration.py` | `test_fixture_runs_end_to_end_zero_match` | §3 risk #3 | Zero-match e2e + carrier #10 enforcement (empty list verbatim, no collapse, no pr20). |
| 4 | `test_pr9_fixture_integration.py` | `test_observation_and_expectation_distinguishable_by_record_kind` | §3 risk #5 | Gate 4 unblock proof #1 — record_kind partition correctness. Independent drive of single-survivor fixture; orthogonal to tests 1–3. |
| 5 | `test_pr9_fixture_integration.py` | `test_records_join_on_fixture_id` | §3 risk #6 | Gate 4 unblock proof #2 — fixture_id joinability. Independent drive of single-survivor fixture; orthogonal to tests 1–4. |
| A | `test_pr9_fixture_discipline.py` | `test_fixture_permitted_imports_locked_at_one_symbol` | §3 risk #4 | Frozenset value-lock regression. Member #9 protection enforcement. |
| B | `test_pr9_fixture_discipline.py` | `test_fixture_modules_references_subset_of_permitted_imports` | §3 risk #4 | Walker subset-enforcement against `tests/corpus/fixtures/*.py`. Member #9 protection enforcement. |

**Total: 7 named tests.** No parametrize over fixtures (per Q3
lock). Named == collected for PR 9's contribution.

### 5.2 Regression contract

PR 9 must NOT regress:

- **PR 4 integration tests** —
  `tests/corpus/test_pr4_chat_handler_integration.py`,
  `tests/corpus/test_pr4_no_dependency.py`,
  `tests/corpus/test_pr4_participation_creep.py`. Each passes
  unchanged at PR 9 close.
- **PR 5 integration tests** —
  `tests/corpus/test_pr5_chain_step_integration.py`. Passes
  unchanged.
- **PR 6 Layer 3 lint** —
  `tests/corpus/test_pr6_visual_asymmetry.py`. All 17 tests
  pass unchanged. PR 9 introduces zero new
  `emit_divergence_capture` call sites; lint input set
  unchanged.
- **PR 7 modules** — all `test_pr7_*.py` modules pass unchanged.
- **PR 8 module** — `test_pr8_seed_surface.py` passes unchanged
  (all 14 named tests / 25 collected).
- **PR 3 discipline** — `test_pr3_discipline.py` passes
  unchanged. PR 9 introduces zero new production source files;
  `_ALLOWLIST` is unaffected.
- **Public API** — `forge_bridge.__all__` stays at 19 symbols.
  PR 8's `test_pr8_helpers_remain_corpus_internal` enforces
  mechanically; PR 9 verifies at Step 5.

### 5.3 Test count delta

**Baseline at PR 8 close** (per PR 8 close §1.6):

- Forge env: 200 collected (175 pre-PR-8 + 25 PR 8 collected
  from 14 named × parametrize expansion).
- Forge-bridge env: 194 collected (200 minus 6-test gap
  inherited from PR 7 per `project_v1_4_x_harness_debt.md` —
  starlette TestClient + asyncpg loop conflict +
  Project-seeding fixture gap).

**PR 9 contribution:** 7 named tests, zero parametrize, so
named == collected.

**Target at PR 9 close:**

- Forge env: **207 collected** (200 baseline + 7 new = 207).
- Forge-bridge env: **201 collected** (194 baseline + 7 new =
  201; same 6-test gap continues).

The named-vs-collected distinction is archaeology-grade per
PR 8 close §1.6. PR 9 close §6 reports both **named (7)** and
**collected (7 — identical at PR 9 due to no parametrize)**
plus the full-corpus 207 / 201 anchor verification.

**Do not conflate the two env counts.** Forge-bridge env gap is
load-bearing per `project_v1_4_x_harness_debt.md`; PR 9 close §6
documents both env counts explicitly.

### 5.4 What PR 9 deliberately does NOT test

Per framing §7.3 + spec §2 out-of-scope:

- **Multi-fixture composition.** PR 9 tests do not exercise
  driving multiple fixtures in a single test (no
  `for FIXTURE in [F1, F2, F3]: drive(...)`). Each test invokes
  one fixture. Multi-fixture composition is out-of-scope per
  framing §7.1 commitment #11 (no test ordering coupling).
- **Chain-step fixture coverage.** Per carrier #15 + spec §2
  out-of-scope #1. No PR 9 test exercises `_step.py:233`.
- **Comparator semantics.** Tests 4 + 5 prove the comparator's
  partition + join dependencies WITHOUT writing the comparator.
  No PR 9 test asserts that observation and expectation
  "diverge" or "match" in any semantic sense — that's Gate 4's
  scope.
- **Cross-fixture record join.** PR 9 tests do not assert that
  `fixture_id`-keyed joins WORK ACROSS MULTIPLE FIXTURES (e.g.,
  drive 3 fixtures then build a 3-pair join dict). Each test
  drives one fixture and asserts the 1-pair join. Cross-fixture
  join is out-of-scope per spec §2 + governing sentence
  (multi-fixture orchestration is fixture-management
  infrastructure).
- **Performance / scaling.** PR 9 tests do not measure
  arbitration latency, persistence throughput, or fixture-set
  scaling characteristics.
- **Fixture validity beyond mechanical schema.** PR 9 tests do
  not assert that fixture prompts are "good" prompts or that
  `expected_narrow` lists are "correct" expectations — those
  are Gate 4 comparator concerns. PR 9 asserts that whatever
  fixtures the spec author writes drive arbitration end-to-end
  + produce persistable records.
- **`drive_seed_fixture` failure paths.** PR 8 tests the
  failure-invisibility contract; PR 9 inherits that coverage.
  PR 9 tests do not exercise scenarios where
  `drive_seed_fixture` raises (it doesn't — it's
  I-6-wrapped) or where persistence fails silently.

---

## 6. Implementation sequence

The framing §5.7 cadence-matches-work-depth rule applies, with
integration-work elevation across the entire PR (full three-
round review on every step per Gate 2 framing §5.7 — PR 9 is
integration-shaped, not plumbing-shaped). Step 3 + Step 4 are
co-equal architectural centers (e2e tests + property tests);
Step 5 is verification, not implementation.

Five steps. Each step changes one authority or ontology boundary
cleanly.

### Step 1 — Fixture directory + discipline scaffolding

Create `tests/corpus/fixtures/` directory with `__init__.py` per
§4.1.

Create `tests/corpus/test_pr9_fixture_discipline.py` per §4.6:
- Module docstring (carriers + parallel-not-extension rationale +
  closing sentence + governing sentence).
- `_FIXTURE_PERMITTED_IMPORTS` frozenset (1 symbol).
- `_FIXTURE_DIRECTORY` module-scope path.
- `_fixture_corpus_references` AST walker function.
- Test A (`test_fixture_permitted_imports_locked_at_one_symbol`).
- Test B (`test_fixture_modules_references_subset_of_permitted_imports`).

At this step, no fixture modules exist yet. The walker (test B)
asserts:
- The fixture directory exists.
- At least 1 fixture module is present (the test will FAIL at
  Step 1 if no fixture modules exist — this is the correct shape;
  the test is designed to require fixtures to exist).

**Step 1 verification deviation from PR 8:** Step 1's test B
will FAIL initially because no fixture modules have landed yet.
To allow Step 1 to commit clean, Step 1 lands ONE placeholder
fixture module (`fix_single_survivor.py` skeleton — module
docstring + `FIXTURE = {"fixture_id": "placeholder", "prompt":
"placeholder", "expected_narrow": []}`) so test B finds at least
one module to walk and the empty-set subset check passes
vacuously. Step 2 fills in the actual fixture content
(skeleton → real values).

**Atomic commit:** discipline test module + fixture directory +
`__init__.py` + placeholder `fix_single_survivor.py` skeleton.
2 discipline tests pass; placeholder fixture has empty corpus
imports → walker subset check passes vacuously.

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr9_fixture_discipline.py` — 2 tests
  pass.
- `pytest tests/corpus/test_pr3_discipline.py` — passes
  unchanged.
- `pytest tests/corpus/test_pr4_participation_creep.py` —
  passes unchanged (PR 9 walker does not affect PR 4 walker).
- `pytest tests/corpus/test_pr8_seed_surface.py` — passes
  unchanged (PR 9 walker does not affect PR 8 walker).
- `python -c "from tests.corpus.fixtures.fix_single_survivor import FIXTURE; assert FIXTURE['fixture_id'] == 'placeholder'"` — imports clean.

### Step 2 — Three fixture modules (content lands)

Replace `fix_single_survivor.py` placeholder content with real
fixture per §4.2. Implementation note (per §4.2 step note):
select a single-step prompt that yields a single-survivor
narrowing decision against live `chat_handler` arbitration.
Trace the chosen prompt through `chat_handler` at implementation
time to verify both binding constraints (single-step shape +
single-survivor outcome).

Create `fix_multi_match.py` per §4.3. Select a multi-step-shape-
rejecting prompt that yields multi-match narrowing.

Create `fix_zero_match.py` per §4.4. Select a single-step prompt
that yields zero-match narrowing (no tool name matches).

Each fixture module's full module docstring is written at this
step (the placeholder skeleton from Step 1 had only the
constant; Step 2 lands the full carrier block + fixture purpose
paragraph).

**Step 2 commit message body** documents the implementation-time
prompt selection for each fixture, including:
- The chosen prompt text.
- The trace verification confirming single-step shape (no
  `_step.py:233` invocation).
- The arbitration outcome observed (single-survivor / multi-match
  / zero-match) with the actual tool name(s) yielded.

This commit body documentation is archaeology-grade per
`feedback_counts_are_archaeology_grade.md` — future contributors
diagnosing fixture regressions can verify against the trace
recorded at this commit.

**Atomic commit:** three fixture modules (placeholder filled in
+ two new) + Step 2 commit-message implementation notes.

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr9_fixture_discipline.py` — 2 tests
  pass against the three real fixture modules.
- Manual carrier travel verification: `_seed.py`'s carrier
  block (lines 19-135) compared against each fixture module's
  carrier block. Carrier #15 lands at top in each; the 14
  inherited carriers + binding clarification land verbatim.
- `python -c "import tests.corpus.fixtures.fix_single_survivor as F; assert F.FIXTURE['fixture_id'] == 'fix-pr9-single-survivor'"` and similar for the other two — imports clean, identifiers correct.

### Step 3 — Three e2e integration tests **(architectural-center #1)**

Create `tests/corpus/test_pr9_fixture_integration.py` per §4.5.
Tests 1, 2, 3 (single-survivor / multi-match / zero-match e2e).

**Architectural-center #1.** This step lands the end-to-end
composition proof. Tests 1–3 demonstrate that PR 7's substrate
(seed_dispatch_scope, _persist_expectation_record,
KNOWN_SOURCE_VALUES, _KNOWN_RECORD_KINDS) + PR 8's surfaces
(emit_seed_expectation, drive_seed_fixture, schema validator
expectation branch) compose end-to-end against real arbitration
under three narrowing-outcome shapes.

Each test's body is per §4.5 (drive fixture → read records →
assert pair shape + per-fixture properties). The three tests are
hand-written in full — no shared helper function (per member #9
protection extension + framing §7.1 commitment #4).

**Atomic commit:** test module + 3 named tests. The three tests
need their respective fixtures + the corpus reader fixture +
the clean_rate_limit_state fixture; bundling them is the atomic
boundary.

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr9_fixture_integration.py -k 'end_to_end'` — 3 tests pass.
- `pytest tests/corpus/test_pr9_fixture_discipline.py` — 2 tests pass unchanged (PR 9 discipline tests do not depend on integration tests).
- `pytest tests/corpus/test_pr8_seed_surface.py` — passes unchanged (PR 8's tests don't break from PR 9's additions).

### Step 4 — Two property tests **(architectural-center #2)**

Add tests 4 + 5 to `tests/corpus/test_pr9_fixture_integration.py`
per §4.5.

**Architectural-center #2.** This step lands the Gate 4 unblock
proofs. Test 4 (record_kind partition) + test 5 (fixture_id
joinability) demonstrate the two mechanical properties Gate 4's
comparator depends on, WITHOUT writing the comparator (per Gate 2
framing §11.3 + spec §2 out-of-scope #2).

Tests 4 + 5 each independently invoke `drive_seed_fixture`
against the single-survivor fixture. The independence from tests
1–3 is structural — a future PR could break tests 1–3 (e2e
regressions across narrowing outcomes) without breaking tests
4–5 (the partition + join properties), and vice versa. The
orthogonality is the load-bearing protection.

**Atomic commit:** 2 property tests added to the integration
test module. Bundle is appropriate (same module; same fixture
imports; same conftest dependencies).

**Full three-round review.** Verification:
- `pytest tests/corpus/test_pr9_fixture_integration.py` — 5 tests pass total.
- `pytest tests/corpus/test_pr9_fixture_discipline.py` — 2 tests pass unchanged.
- Full PR 9 suite: `pytest tests/corpus/test_pr9_*.py` — 7 tests pass.
- PR 7 + PR 8 regression: `pytest tests/corpus/test_pr7_*.py tests/corpus/test_pr8_seed_surface.py` — all pass unchanged.

### Step 5 — Final verification

No new code lands at Step 5. This step verifies the post-PR-9
codebase against all regression contracts and close conditions.
The atomic commit registers the verification + carries the PR 9
commit message body (carriers + binding framing clarification +
governing sentence + any spec amendments named explicitly).

**Verification checklist:**

1. **PR 9 corpus tests:** `pytest tests/corpus/test_pr9_*.py` —
   7/7 pass (5 integration + 2 discipline).
2. **PR 7 + PR 8 corpus tests:** `pytest
   tests/corpus/test_pr7_*.py tests/corpus/test_pr8_seed_surface.py`
   — all pass unchanged.
3. **Layer 3 lint regression:** `pytest
   tests/corpus/test_pr6_visual_asymmetry.py` — 17/17 pass
   unchanged. Confirms PR 9 introduced zero new
   `emit_divergence_capture` call sites.
4. **PR 4 walker regression:** `pytest
   tests/corpus/test_pr4_participation_creep.py` — passes
   unchanged. Confirms PR 9's parallel walker did not
   accidentally break PR 4's walker (different ontologies; both
   operational).
5. **PR 4 + PR 5 integration tests:** chat-handler + chain-step
   integration tests under all four capture states — pass
   unchanged.
6. **Full corpus suite:** `pytest tests/corpus/` —
   **207 collected forge env** (200 baseline + 7 PR 9 new).
   **201 collected forge-bridge env** (194 baseline + 7 PR 9
   new; same 6-test gap continues per
   `project_v1_4_x_harness_debt.md`). Document both env counts
   in Step 5 commit body; do not conflate.
7. **Console tests:** `pytest tests/console/test_chat_handler.py`
   — 50/50 unchanged.
8. **Public API regression:** `python -c "import forge_bridge;
   assert len(forge_bridge.__all__) == 19; assert
   'emit_seed_expectation' not in forge_bridge.__all__; assert
   'drive_seed_fixture' not in forge_bridge.__all__"` — clean.
   PR 8's `test_pr8_helpers_remain_corpus_internal` continues to
   enforce mechanically.
9. **Verbatim travel verification:** Step 5 verifier reads each
   fixture module's docstring, both new test module docstrings;
   cross-references each verbatim block against §0; surfaces any
   drift before the close commit. Carrier #15 lands at top in
   each fixture module per the relevance-by-file ordering
   principle.
10. **Governing sentence verification:** Step 5 verifier
    confirms "PR 9 proves topology, not infrastructure." appears
    in PR 9 spec §0 (this artifact) + at least one PR 9 commit
    message body (Step 5 commit qualifies if the sentence is
    included).

**Step 5 commit message body** carries (in order):

- Section: "preserved invariants" — 14 inherited carriers +
  carrier #15 + binding framing clarification verbatim.
- Section: "PR 9 governing sentence" — the framing-scoped
  sentence verbatim, with the framing §0 deferral note (NOT
  promoted to carrier #16 at PR 9).
- Section: "cleanup-pressure-resistance class addition" —
  member #9 (fixture-surface-data-discipline) protection summary.
- Section: "spec amendments at incarnation" — Discoveries
  named explicitly with section references (if any surfaced
  during Steps 1–4).
- Section: "regression contracts" — verification checklist
  results.
- Section: "test count anchor" — 200 baseline + 7 new = 207
  forge env collected; 194 baseline + 7 new = 201 forge-bridge
  env collected (6-test gap inherited).

### Closing prose — Step 5 vs. close artifact

`A.5.3.2-PR9-CLOSE.md` lands as a distinct subsequent commit
after Step 5 verification completes. The Gate 2 close artifact
(`A.5.3.2-GATE-2-CLOSE.md`) lands at the SAME commit as the
PR 9 close artifact per Gate 2 framing §11.6 + PR 8 close §7
step 11.

The cadence preserves the PR 4–8 separation: implementation
sequence ≠ close archaeology. Step 5 concludes implementation +
verification authority; the close artifact(s) perform
retrospective architectural synthesis (durable archival state,
methodology observations, cleanup-pressure class final-inventory
archive, verbatim-travel archaeology; PLUS the Gate 2 close
artifact's separate retrospective on Gate 2 as a whole).

PR 8 cadence verified: Step 5 verification at `1fd9846`
followed by close artifact at `b102010` — two separate commits.
PR 9 mirrors with one extension: Step 5 verification commit
followed by `A.5.3.2-PR9-CLOSE.md` + `A.5.3.2-GATE-2-CLOSE.md`
landing at the same close commit (two artifacts; one commit).

### Natural pause points

- **Between Step 1 and Step 2** — verifies the fixture
  directory + discipline scaffolding is operational before
  fixture content lands. Test A's value-lock holds; test B's
  walker passes against the placeholder fixture. If test B fires
  unexpectedly, the framing-time `_FIXTURE_PERMITTED_IMPORTS`
  spec is wrong and needs amendment before content proceeds.
- **Between Step 2 and Step 3** — verifies the three fixture
  modules are operational + carrier travel landed verbatim
  before integration tests consume them. If carrier travel drift
  surfaces at this pause, register a Step 2.5 surgical cleanup
  commit (analogous to PR 8 Step 4.5 pattern from PR 8 close
  §5.2).
- **Between Step 3 and Step 4** — verifies the three e2e tests
  ship green before the two property tests land. Without this
  pause, a Step 4 test failure could be a property-test bug OR
  an e2e-test regression bleeding into property assertions.
- **Immediately after Step 4** — full PR 9 suite green (7
  tests). Before Step 5 verification, this is the moment to
  sanity-check the verbatim travel placements + the governing-
  sentence presence + the test count arithmetic against the
  collected total.

### What about an inter-step polish step?

PR 4, PR 5, PR 6 reserved a "polish step (no-op for this PR)"
slot. PR 7 + PR 8 surfaced no analogous polish during spec
drafting and did not reserve one. PR 9 surfaces no polish during
this drafting and does not reserve one. The five steps above are
the implementation sequence in full.

PR 8 introduced a new variant (verification-time amendment via
Step 4.5) — PR 9 should expect verbatim-travel verification at
Step 5 to potentially surface implementation-time amendments
analogous to PR 8's 5th–7th. The natural Step 4.5 slot exists
implicitly: if Step 5 verification surfaces scaffold prose drift
or carrier travel drift, register a surgical pre-Step-5 cleanup
commit before Step 5 verification lands.

---

## 7. Phase-end conditions for PR 9

| Trigger | Response |
|---|---|
| All 7 new tests pass + Layer 3 lint passes unchanged + PR 4 + PR 5 + PR 7 + PR 8 integration tests pass unchanged + the 16 sentences in §0 (15 carriers + binding framing clarification) travel verbatim into the relevant docstrings + commit message body + the PR 9 governing sentence appears in spec §0 + at least one PR 9 commit body + no implementation step shortcuts or weakens member #9 (fixture-surface-data-discipline) or any prior member of the cleanup-pressure-resistance class + the parallel-not-extension Layer 2 ontology (§4.3 + §8.2) is preserved | PR 9 closes; `A.5.3.2-PR9-CLOSE.md` + `A.5.3.2-GATE-2-CLOSE.md` draft as a distinct subsequent commit (single commit hosting both artifacts per Gate 2 framing §11.6); Gate 2 closes; Gate 3 / Gate 4 framing drafting begins. |
| `test_pr6_visual_asymmetry.py` regresses against the post-PR-9 codebase | Hard CI failure; Layer 3 lint has been touched accidentally or a PR 9 surface has begun introducing `emit_divergence_capture` call sites. Reject at CI; review surfaces the structural violation. |
| `test_pr4_participation_creep.py` regresses on a future PR | Hard CI failure; either the PR 4 walker has been touched accidentally OR the parallel-not-extension Layer 2 ontology has been violated (e.g., PR 4 walker target-set expanded to include fixture modules, conflating two ontologies). Reject at CI; review surfaces the framing §4.3 + §8.2 parallel-not-extension rationale + "shared AST mechanics do not imply shared ontology" verbatim. |
| `test_fixture_permitted_imports_locked_at_one_symbol` regresses on a future PR | Hard CI failure; cleanup-pressure class member #9 has been violated. The frozenset has acquired a second symbol without framing-level review. Reject at CI; review surfaces framing §5.4 (Q4) + member #9 protection (framing §6.1) verbatim + the single-symbol-gate rationale. |
| `test_fixture_modules_references_subset_of_permitted_imports` regresses on a future PR | Hard CI failure; PR-9-LOCAL fixture-data discipline has been violated. A fixture module has acquired a forbidden corpus import. Reject at CI; review surfaces framing §6.1 (member #9) + the offender file name + the forbidden references named in the walker's assertion error. |
| `test_fixture_runs_end_to_end_single_survivor` regresses on a future PR | Hard CI failure; PR 7 substrate or PR 8 surfaces have been touched in a way that breaks end-to-end composition under the canonical single-survivor narrowing outcome. Reject at CI; review traces back to whichever substrate or surface broke (PR 7 schema, PR 7 dispatch context, PR 8 helper, PR 8 driver, PR 8 scope). |
| `test_fixture_runs_end_to_end_multi_match` regresses on a future PR | Hard CI failure; either the multi-match arbitration outcome path has regressed OR carrier #10's ambiguity-rejection semantics have been silently overloaded against handlers.py. Reject at CI; review surfaces carrier #10 verbatim + the surface-asymmetry distinction (chat-handler vs. chain-step). |
| `test_fixture_runs_end_to_end_zero_match` regresses on a future PR | Hard CI failure; either the zero-match arbitration outcome path has regressed OR `emit_seed_expectation`'s empty-list-is-valid contract has been violated. Reject at CI; review surfaces carrier #10 + the empty-list validity language at `forge_bridge/corpus/_seed.py:259–264`. |
| `test_observation_and_expectation_distinguishable_by_record_kind` regresses on a future PR | Hard CI failure; Gate 4 unblock dependency #1 has been violated. Either the `record_kind` discriminator has been touched (PR 7 substrate regression) OR a future PR has begun collapsing observation + expectation into a single record kind (member #7 violation). Reject at CI; review surfaces member #7 protection verbatim + Gate 2 framing §4.4 falsifiability framing. |
| `test_records_join_on_fixture_id` regresses on a future PR | Hard CI failure; Gate 4 unblock dependency #2 has been violated. Either the `fixture_id` field is no longer being populated identically at expectation persistence + observation persistence (PR 7 or PR 8 substrate regression) OR a future PR has decoupled the two record kinds' join key. Reject at CI; review surfaces the join-key population sites (`emit_seed_expectation` at `_seed.py:296`, `handlers.py:1185` under `seed_dispatch_scope`). |
| A future PR proposes seeding the chain-step observation surface inside PR 9's scope | Rejected at the spec layer per carrier #15 + §2 out-of-scope #1. Cross-surface expectation semantics require a dedicated framing pass BEFORE implementation proceeds. PR 9 does not draft, prefigure, or scaffold that pass. |
| A future PR proposes shipping a Gate 4 comparator artifact (stub or otherwise) inside PR 9's scope | Rejected at the spec layer per Gate 2 framing §11.3 + §2 out-of-scope #2 + framing §7.1 commitment #2. Tests 4 + 5 prove the comparator dependencies WITHOUT shipping the comparator. The comparator is Gate 4's deliverable. |
| A future PR proposes a fixture loader / CLI / daemon hook inside PR 9's scope | Rejected at the spec layer per framing §5.2 (Q2) + governing sentence + §2 out-of-scope #3. The integration tests ARE the fixture consumer surface at PR 9. |
| A future PR proposes parametrize over fixtures, a fixture registry/factory/generator, or any fixture-management abstraction | Rejected at the spec layer per framing §5.1 (Q1) + §5.3 (Q3) + governing sentence + §2 out-of-scope #4 + member #9 protection. Each fixture is a Python module with one top-level `FIXTURE` dict; programmatic fixture management is rejected. |
| A future PR proposes non-Python fixture formats (JSON / YAML / TOML / CSV) | Rejected at the spec layer per framing §5.1 (Q1) + governing sentence + §2 out-of-scope #5. |
| A future PR proposes adding a fourth required field to expectation records inside a cleanup PR | Rejected at the spec layer per framing §5.5 (Q5) + member #7 protection + §2 out-of-scope #6. Schema extensions require framing-level review; Gate 4 surfaces concrete needs at comparator-write time. |
| A future PR proposes promoting `emit_seed_expectation` or `drive_seed_fixture` to `forge_bridge.__all__` inside a cleanup PR | Rejected at the spec layer per framing §5.6 (Q6) + PR 8 spec §2 out-of-scope #4 + §2 out-of-scope #7. PR 8's `test_pr8_helpers_remain_corpus_internal` continues to enforce mechanically. |
| A future PR proposes modifying any production source file inside PR 9's scope | Rejected at the spec layer per framing §2 + §2 out-of-scope #8. PR 9 is purely test-surface additions. |
| A future PR proposes admitting a second symbol to `_FIXTURE_PERMITTED_IMPORTS` inside a cleanup PR | Rejected at the spec layer per member #9 + framing §5.4 (Q4) + framing §6.1 single-symbol-gate + §2 out-of-scope #12. The single-symbol-gate IS the fixture-data discipline; admitting a second symbol erodes the protection. |
| A future PR proposes unifying the PR 4 + PR 8 + PR 9 walkers into a generalized AST walker | Rejected at the spec layer per framing §4.3 + §8.2 + the parallel-not-extension rationale + the closing sentence "Shared AST mechanics do not imply shared ontology." The three walkers protect three distinct ontologies; unification collapses three protections into one rejection surface. |
| A future PR proposes shipping a fourth fixture inside PR 9's scope (e.g., a multi-survivor disambiguation fixture, an arbitration-error fixture, etc.) | Rejected at the spec layer per framing §5.3 (Q3) + §2 out-of-scope. Fixture count is locked at 3; additional fixtures require framing-level review naming the new narrowing-outcome shape exercised + the Gate 4 comparator dependency justified. |

---

## 8. Cross-references

- **`A.5.3.2-PR9-FRAMING.md`** (`5628817`) — binding pre-spec
  contract; §0 governing sentence; §3.2 carrier inheritance
  (15 inherited, zero new); §4.1 fixture corpus directory shape;
  §4.2 integration test surface (5 named); §4.3 Layer 2 fixture
  discipline (parallel-not-extension); §5 Q1–Q6 binding
  decisions; §6.1 member #9 (fixture-surface-data-discipline);
  §7 non-acquisition commitments; §8.2 Layer 2 three-ontology
  partition; §9 phase-end + Gate 2 close criteria; §9 item 5
  test count arithmetic anchor.
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — durable PR 8 archival
  state PR 9 inherits; §2 what PR 9 inherits (the 18 verbatim
  sentences + the `emit_seed_expectation` seam + the
  `drive_seed_fixture` orchestration surface + the schema
  validator's expectation branch + the three-way authority
  partition + the 8-member cleanup-pressure-resistance class
  inventory); §3 what PR 9 changes; §7 11-step reseed protocol
  (this spec executes step 9 of that protocol); §1.6 test count
  archaeology (200 = 175 + 25 forge env).
- **`A.5.3.2-PR8-SPEC.md`** (`85c5bc1`) — §0 18 verbatim
  sentences (PR 9 spec §0 mirrors 16: 15 carriers + binding
  framing clarification; PR-8-LOCAL statements scope-local per
  non-regeneration rule); §4.1.5.1 three-way authority partition
  preserved intact; §7 phase-end conditions rejection table
  (PR 9 may not propose any of those mutations); §6 implementation
  sequence shape (PR 9 mirrors 5-step cadence).
- **`A.5.3.2-PR8-FRAMING.md`** (`23f2a20`) — §0 carrier #15
  (inherited by PR 9); §3.3 three-authority-surface partitioning
  preserved intact; §5 Q1–Q5 binding decisions (Q5 `__all__`
  deferral preserved at PR 9 Q6); §6 members #7 + #8 (scope-
  local; do not regenerate at PR 9).
- **`A.5.3.2-GATE-2-FRAMING.md`** (`ceac9b5`) — §3.4 three-
  authority-surface partition; §5.7 PR 9 = first fixtures +
  end-to-end integration; §10 PR 9 deliverables; §11 Gate 2
  close criteria; §11.3 "Gate 2 ships no comparator artifact,
  stub or otherwise"; §11.6 Gate 2 close artifact lands at PR 9
  close commit.
- **`A.5.3.2-PR7-SPEC.md`** (`84392d2`) — `seed_dispatch_scope`,
  `_persist_expectation_record`, `KNOWN_SOURCE_VALUES`,
  `_KNOWN_RECORD_KINDS` — the substrate PR 9 consumes via
  `drive_seed_fixture`. §7 phase-end rejection table (PR 9
  inherits).
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — durable PR 7 archival
  state continues to apply at PR 9.
- **`forge_bridge/corpus/_seed.py`** — the four PR 7 + PR 8
  surfaces PR 9 transacts with (`drive_seed_fixture` directly,
  the other three indirectly).
- **`tests/corpus/_pr3_helpers.py::base_expectation_args`** —
  PR 8 helper; NOT consumed by PR 9 (PR 8's helper is for
  testing `emit_seed_expectation`'s signature; PR 9 fixtures
  carry data directly).
- **`tests/corpus/conftest.py`** — `clean_rate_limit_state`
  fixture (PR 8 contribution) consumed by all 5 integration
  tests; `tmp_corpus_dir` fixture — existing `conftest.py`
  fixture surface — consumed by all 5 integration tests.
- **`tests/corpus/test_pr4_participation_creep.py`** — PR 4
  walker; PR 9's `test_pr9_fixture_discipline.py` walker is
  EXPLICITLY NOT an extension of this module. Shared AST
  mechanics; distinct ontologies.
- **`tests/corpus/test_pr8_seed_surface.py`** — PR 8 walker
  (`_SEED_PERMITTED_IMPORTS` + `_corpus_references`); PR 9
  walker generalizes the AST mechanics pattern to a directory
  glob target with distinct admission ontology.
- **`project_v1_4_x_harness_debt.md`** (local memory) — forge-
  bridge env 6-test gap inherited; PR 9 close §6 documents both
  env counts (forge env 207 / forge-bridge env 201).
- **`feedback_counts_are_archaeology_grade.md`** (local memory) —
  test count arithmetic in PR 9 spec §5.3 + §6 Step 5 + §9 are
  archaeology-grade; recount at Step 5 verification; do not
  approximate.
- **`feedback_ground_specs_in_actual_files.md`** (local memory)
  — Step 2 fixture prompt selection must read `chat_handler`'s
  live behavior; do not infer from arbitration documentation.

---

## Resume protocol — what the next session does with this spec

When the next session opens (Step 1 implementation):

1. **Read this spec first.** §0 carriers + §1 real job/success
   condition + §4 module surface + §6 implementation sequence
   are the load-bearing sections.

2. **Read the framing artifact** (`A.5.3.2-PR9-FRAMING.md` at
   `5628817`) for the binding decisions + rationale. Especially
   §0 (governing sentence), §4.3 (parallel-not-extension
   Layer 2), §6.1 (member #9), §9 (test count arithmetic
   anchor).

3. **Read the PR 8 close artifact** (`A.5.3.2-PR8-CLOSE.md` at
   `b102010`) §2 (what PR 9 inherits) + §3 (what PR 9 changes)
   for the durable archival state context.

4. **Read PR 8 spec §6 implementation sequence** for the
   step-by-step cadence pattern PR 9 mirrors.

5. **Ground against actual code:**
   - `forge_bridge/corpus/_seed.py` (lines 19–135 for carrier
     block; lines 221–319 for `emit_seed_expectation`; lines
     430–526 for `drive_seed_fixture`).
   - `tests/corpus/test_pr8_seed_surface.py` (lines 107–250 for
     `_SEED_PERMITTED_IMPORTS` + `_corpus_references` walker
     shape — PR 9's walker mirrors this with different target
     glob).
   - `tests/corpus/test_pr4_participation_creep.py` (verify the
     PR 4 walker's target set; confirm parallel-not-extension
     boundary).
   - `tests/corpus/conftest.py` (verify `clean_rate_limit_state`
     + `tmp_corpus_dir` fixture availability).

6. **Begin Step 1** (per §6): fixture directory + discipline
   scaffolding + placeholder `fix_single_survivor.py`. The
   placeholder approach is the deviation from PR 8 noted at §6
   Step 1; commit message names the placeholder rationale.

7. **Surface diff for review** at every commit regardless of
   review depth (per PR 8 close §5.3 methodology). The cadence-
   matches-work-depth review rule applies at every step.

8. **Expect verbatim-travel verification at Step 5** to
   potentially surface implementation-time amendments analogous
   to PR 8's 5th–7th. If drift surfaces, register a surgical
   Step 4.5 commit before Step 5 verification (the Step 4.5
   pattern from PR 8 close §5.2).

9. **PR 9 close + Gate 2 close** land at the same commit per
   Gate 2 framing §11.6 + PR 8 close §7 step 11. Two artifacts
   in one commit: `A.5.3.2-PR9-CLOSE.md` (PR 9 archival) +
   `A.5.3.2-GATE-2-CLOSE.md` (Gate 2 archival). The Gate 2
   close artifact follows the PR 6 close artifact's structure
   (predecessors, what Gate 2 established, what Gate 3 / Gate 4
   inherits, methodology observations, cross-references).

The cadence — framing → spec → spec-amendments-at-incarnation
→ steps → verification-amendments-if-surfaced → close — carries
unchanged from PR 7 + PR 8 with one extension for PR 9 (Gate 2
close artifact lands at the PR 9 close commit alongside the
PR 9 close artifact).

---

End of PR 9 spec. The spec derives the implementation contract
from the framing's locked decisions: zero production source
file modifications; 3 fixture modules under
`tests/corpus/fixtures/`; 5 integration tests in
`test_pr9_fixture_integration.py`; 2 discipline tests in
`test_pr9_fixture_discipline.py`; new parallel
`_FIXTURE_PERMITTED_IMPORTS` frozenset (1 symbol) + new walker
explicitly NOT an extension of PR 4's walker; 7 named tests
total (named == collected; no parametrize); 207 forge env /
201 forge-bridge env collected target at PR 9 close; member #9
contribution to the cleanup-pressure-resistance class final
inventory (9 members at PR 9 close subject to corroboration);
two close artifacts at PR 9 close commit (PR 9 + Gate 2);
governing sentence "PR 9 proves topology, not infrastructure."
travels through spec §0 + commit message bodies + optionally
fixture module docstrings (Step 2 amendment candidate).

PR 9 implementation begins at Step 1 (fixture directory +
discipline scaffolding + placeholder fixture). The 11-step
reseed protocol from PR 8 close §7 has now executed through
step 9 (spec drafted); step 10 (implementation) begins next.
