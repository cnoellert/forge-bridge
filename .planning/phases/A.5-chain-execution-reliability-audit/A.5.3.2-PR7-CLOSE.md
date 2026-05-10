# A.5.3.2 PR 7 — Close (Gate 2 mid-flight; PR 8 inherits)

**Status:** PR 7 closed at commit `7838f9a` on `origin/main`. Gate 2
remains mid-flight; PR 8 (the seed driver) is the next deliverable.
Archival framing + continuity definition for the room as it crosses
the PR 7 → PR 8 boundary inside Gate 2.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-SPEC.md` — persistence layer.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — risk-category shift;
  integration-discipline quartet.
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — surface geometry
  asymmetry; chain-step integration durable archival state.
- `A.5.3.2-PR6-CLOSE.md` (commit `9168df7`) — Layer 3 lint; Gate 1
  closure; truth-vs-mechanism distinction; durable archival state
  Gate 2 inherits.
- `A.5.3.2-GATE-2-FRAMING.md` (commit `ceac9b5`) — gate-level
  architecture; §6.1 carrier #14; §6.2 binding framing
  clarification; §9 schema delta; §10 PR partitioning; §3.4
  three-authority-surface partitioning.
- `A.5.3.2-PR7-FRAMING.md` (commit `1c1e061`) — pre-spec binding
  contract; §6 cleanup-pressure-resistance class (introduced
  here); §4.2 inert-parameter binding pair; §5.5 legacy-synthesis
  binding pair; §7 seven non-acquisition commitments.
- `A.5.3.2-PR7-SPEC.md` (commit `84392d2`) — implementation
  contract; nineteen verbatim sentences; 8-step staircase; 27
  tests across five files; two spec amendments (§4.5
  admission-vs-import correction at `0a2ad7e`; §4.3
  `_VALID_SOURCES` discovery + Step 5↔6 reorder at `30d3ca9`).
- PR 7 step commits: `0187e9d` → `7838f9a` (8 commits ending at
  Step 8 — expectation persistence helper).

**The threshold PR 7 confirmed:**

> The three-authority-surface partitioning is structurally
> mechanically protected, not merely conceptually distinct.

This sentence — implicit in Gate 2 framing §3.4 — exits PR 7 as
operational reality. Three helpers, three guards, three test
classes:

- `emit_divergence_capture` (observation surface) — Property C
  literal at the call site, contextvar resolution internally.
- `seed_dispatch_scope` (operational dispatch-provenance surface)
  — public no-yield context manager activating `source="seed"`
  inside the scope.
- `_persist_expectation_record` (authored expectation surface) —
  authority pre-check + non-participation guard; private helper
  consumed by PR 8 exclusively.

Each helper carries the docstring binding statement that protects
its surface. Each surface has at least one test that fires
mechanically when the surface erodes.

---

## 1. What PR 7 established

### 1.1 The three-authority-surface partitioning, made operational

PR 6 closed Gate 1 by mechanically protecting one architectural
property (the visual-asymmetry pattern). PR 7 extends the
discipline: three distinct authority surfaces are now structurally
non-collapsible.

| Surface | Helper | Guard | Mechanical test |
|---|---|---|---|
| **Observation (call-site)** | `emit_divergence_capture` | Property C literal `source="runtime"` at every call site; §4.2 inert-parameter binding pair in helper docstring | `test_pr6_visual_asymmetry.py` (Layer 3 lint) + `test_call_site_source_value_is_inert` |
| **Dispatch provenance (operational)** | `seed_dispatch_scope` | Context-managed; no public yield; private `_DispatchContext` frozen dataclass | `test_dispatch_context_dataclass_is_frozen` + `test_scope_resets_on_exception` + `test_nested_scope_inner_overrides` |
| **Authored expectation (PR 8 surface)** | `_persist_expectation_record` | Non-participation guard + authority pre-check; both verbatim in docstring | `test_helper_does_not_consult_dispatch_context` + `test_helper_authority_pre_check_rejects_observation_record` + `test_helper_authority_pre_check_rejects_missing_record_kind` |

The three surfaces share file space (`_capture.py`) but do not
share resolution path. The asymmetry is structural: the
observation surface consults `_dispatch_context`; the expectation
surface does not. The expectation surface's non-participation is
load-bearing — collapsing it would smear authored expectation
into generic persistence routing.

PR 7's §4.2.6 helper sketch ships verbatim. Three test classes
across three failure modes (non-participation, missing
record_kind, well-formed observation) mechanically lock the
authority boundary. Test 4
(`test_helper_authority_pre_check_rejects_observation_record`)
is the most architecturally pointed: the record is structurally
valid against `validate_capture_record`; the pre-check rejects
it on truth-class grounds. Without that test, a future PR could
remove the pre-check and rely on the schema validator alone.

### 1.2 The cleanup-pressure-resistance class — final inventory

PR 7 framing §6 introduced the architectural class. PR 7
implementation populated it. Final inventory at PR 7 close:

1. **Helper duplication.** `emit_divergence_capture` +
   `_persist_expectation_record`. Sibling, not subordinate. No
   shared internal writer.
2. **Visual asymmetry.** The load-bearing visual pattern
   (Properties A–D, validated by the Layer 3 lint) at every emit
   call site. PR 6's contribution; unchanged at PR 7 close.
3. **Intentionally inert structural parameters.** The call-site
   `source="runtime"` literal. PR 7 added; member #3.
4. **Always-present `fixture_id` field on observation records.**
   The builder dict carries `"fixture_id": None` when no scope
   is active (per Q3 cleanup-pressure-resistance decision at
   Step 6). Removing the field when None would create silent
   structural drift across observation records.
5. **Nested-not-unconditional synthesis form in the reader.**
   Reader synthesis: `fixture_id` synthesis is NESTED inside
   the `record_kind not in record` branch. Unconditional
   synthesis would foreclose PR 8's expectation-record-shape
   design space and mask hypothetical writer bugs.
6. **Inline I-6 wrapper duplication in
   `_persist_expectation_record`.** No shared
   `_log_persistence_warning` helper extracted. The duplication
   tracks helper duplication (member #1) at the
   WARNING-pattern level.

Each member carries inline documentation (in the source) naming
its protection. Future PRs adding members follow the pattern.
The class is candidate methodology contribution — promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is gated on at
least one more reliability phase surfacing a member of the class
under genuinely independent conditions.

### 1.3 The §4.3 amendment — post-Step-4 grounding correction

PR 7's spec drafting carried one large archaeology event worth
naming explicitly: the §4.3 amendment, registered at commit
`30d3ca9` BEFORE the new Step 5 implementation landed.

**What happened.** The original spec §4.3 was drafted assuming
`_schema.py` had no source-class governance constant — the
validator was assumed to accept any string for `source`. The
Step 5 pre-implementation surface pass (post-Step-4 grounding)
read the actual `_schema.py` for the first time during PR 7
implementation. The file already contained:

```python
_VALID_SOURCES = frozenset({"fixture", "runtime"})
```

with validator enforcement at line 132 (a PR 6 close artifact).
The spec's new Step 5 (resolution path) would emit
`source="seed"` records that the existing validator would reject
— a hard implementation blocker.

**What the amendment did.**

- Removed `_VALID_SOURCES` from `_schema.py` entirely
  (single-source-of-truth resolution).
- Made `KNOWN_SOURCE_VALUES` in `_sources.py` the canonical
  authority — `_schema.py` imports it at module-top.
- Dropped the legacy `"fixture"` value (test-isolation pattern,
  not a persisted production provenance class).
- Migrated 11 test usages from `source="fixture"` to
  `source="runtime"` — structural test-as-construction-site
  distinction preserved via the test's location, not via the
  source field.
- Reordered Steps 5↔6: the schema validator extension +
  `_VALID_SOURCES` replacement + test migration land FIRST (new
  Step 5, light-touch), then the resolution path lands SECOND
  (new Step 6, full three-round review).

**Why this matters at close.** The amendment is the second
occurrence in PR 7 of the spec-inferred-from-memory-not-file
pattern. PR 4 surfaced a smaller version. PR 7's
post-amendment behavior — read the file, then amend the spec,
then implement — was saved as a feedback memory mid-session
(`feedback_ground_specs_in_actual_files.md`).

The amendment also confirmed a methodological discipline:
**spec amendments at incarnation are normal and valuable**.
The amendment was registered as its own commit (NO code), not
folded into the Step 5 commit. Reviewers reading the history
see the discovery → amendment → implementation cadence
distinctly.

### 1.4 Fourteen inherited carriers + binding clarification + two PR-7-LOCAL pairs

PR 7 ships nineteen verbatim sentences into three module
docstrings + commit message bodies:

- **Fourteen inherited carriers** (#1–#13 from PR 4 + PR 5 +
  PR 6; #14 from Gate 2 framing). These travel into
  `_capture.py`, `_sources.py`, and `reader.py` module
  docstrings.
- **Binding framing clarification** (Gate 2 framing §6.2):
  *Arbitration-state fields remain call-site-owned explicit
  inputs. Dispatch provenance is contextual metadata derived
  at emission time and does not participate in arbitration
  semantics.*
- **§4.2 inert-parameter pair** (PR-7-LOCAL, scope `_capture.py`
  only): two sentences locking the call-site `source` literal
  as structurally authoritative and operationally inert.
  Mechanically enforced by
  `test_call_site_source_value_is_inert`.
- **§5.5 legacy-synthesis pair** (PR-7-LOCAL, scope `reader.py`
  only): two sentences locking read-time synthesis as
  interpretation-only, not in-place normalization. Mechanically
  enforced by `test_legacy_file_unchanged_after_read`
  (SHA-256 byte-identicality check before/after read).

The two PR-7-LOCAL pairs anchor cleanup-pressure-resistance
class members #3 (inert parameter) and #5 (nested-not-
unconditional synthesis). Each pair appears verbatim AT the
modification point inside the file (docstring + inline comment
at the resolution site) — defense in depth. Future contributors
landing mid-function via grep see the binding text without
needing to scroll to the docstring.

### 1.5 Carrier order inversion — relevance-by-file ordering

Steps 6 + 7 surfaced an explicit decision about carrier
placement order inside two different files:

- **`_capture.py`** — PR 7 carriers land AFTER the PR 3
  carriers (per Step 6 Q6 lock). The PR 3 persistence-layer
  framing is the foundation; PR 7 layers above it.
- **`reader.py`** — PR 7 carriers land AT TOP, BEFORE the
  PR 3 corruption-locality contract (per spec §4.4.1). The
  §5.5 legacy-synthesis pair is the carrier most relevant to
  read-time interpretation; lifting PR 7 carriers to the top
  puts the most-current PR-anchored governance first.

The inversion is per-file, justified by what each file's job
is. Same emphasis-by-position logic; different file = different
relevance ordering. Both correct.

### 1.6 27 new tests across five files

PR 7 added 27 new pytest IDs across five new test files:

| File | Tests | Step | Risk anchored |
|---|---|---|---|
| `test_pr7_known_source_values.py` | 3 | 1 | ontology constant existence + governance |
| `test_pr7_dispatch_context.py` | 6 | 3, 4, 6 | substrate / scope / resolution path; risks #1, #2 |
| `test_pr7_record_kind_schema.py` | 4 | 5 | schema discriminator; risk #4 |
| `test_pr7_reader_validation.py` | 5 | 7 | record-kind-conditional schema extension at read time |
| `test_pr7_legacy_record_synthesis.py` | 4 | 7 | synthesis layer; risk #3 (byte-identicality test) |
| `test_pr7_expectation_persistence.py` | 5 | 8 | expectation helper; risk #5 |

**Zero modifications to existing test files** other than the
11 test usages migrated from `source="fixture"` to
`source="runtime"` per the §4.3 amendment (Step 5).

Final counts (forge env, Python 3.12):
- **175 corpus tests pass** (148 baseline + 27 new). ✓
- **Layer 3 lint passes unchanged** — 17/17 against the modified
  `_capture.py`. ✓
- **PR 4 + PR 5 integration tests pass unchanged** under all
  four capture states (gate-on/off × scope-active/inactive). ✓
- **chat-handler tests** — 50/50 unchanged. ✓

### 1.7 `KNOWN_SOURCE_VALUES` as single-source ontology constant

The post-§4.3-amendment resolution made `_sources.py` the single
authority for persisted source-class governance. The constant
governs four downstream surfaces in lockstep (per the protected
property documented at the constant's definition):

1. **`KNOWN_SOURCE_VALUES`** in `_sources.py` (the constant
   itself).
2. **Reader validation** (`reader.py`) — observation records
   carrying an unknown `source` value are skipped + WARNING.
3. **The contextvar resolution path** inside
   `emit_divergence_capture` — only known source values can
   be emitted.
4. **The Gate 4 comparator's partition logic** (forward-
   inheriting; defined when Gate 4 implements).

Adding a new source value requires synchronous updates across
all four surfaces. A cleanup PR that touches only
`KNOWN_SOURCE_VALUES` cannot satisfy the mergeability contract.
The protected-property framing in the file's comment block
states this explicitly.

This pattern is the **second canonical instance** of the
truth-vs-mechanism distinction PR 6 introduced — `KNOWN_SOURCE_VALUES`
is the mechanism; the property is "persisted provenance classes
are governed in lockstep." The discipline generalizes.

### 1.8 The reader's nested synthesis form — architectural correctness

The Step 7 redline pass caught the architectural choice point.
The original spec §4.4.2 sketch synthesized only `record_kind`:

```python
if isinstance(record, dict) and "record_kind" not in record:
    record["record_kind"] = "observation"
```

The locked form nests `fixture_id` synthesis inside the same
branch:

```python
if isinstance(record, dict) and "record_kind" not in record:
    record["record_kind"] = "observation"
    if "fixture_id" not in record:
        record["fixture_id"] = None
```

Four reasons the nested form is correct, recorded in the Step 7
commit body (`38a1c5f`):

1. **Architectural scoping.** Q3's structural-uniformity
   decision was scoped to "across observation records" —
   observation-only. Pre-PR-7 records were all observation by
   definition (expectation records ship with PR 8). Nesting
   under "record_kind not in record" captures the exact legacy
   cohort.
2. **Single conceptual unit.** Both syntheses share the trigger
   (legacy detection); treating them as independent rules
   invites future drift.
3. **Preserves PR 8's design space.** Whether expectation
   records carry `fixture_id` is PR 8's decision.
   Unconditional synthesis would foreclose that choice by
   silently adding `fixture_id=None` to PR 8+ expectation
   records that lack it.
4. **Defends against bug-masking.** A future PR 7+ observation
   record somehow lacking `fixture_id` would NOT get papered
   over at read-time under the nested form. The bug surfaces
   at the consumer rather than getting silently fixed by the
   reader.

The fourth test in `test_pr7_legacy_record_synthesis.py`
(`test_mixed_legacy_and_contemporary_records`) carries the
mechanical guard: it asserts `"fixture_id" not in yielded[2]`
for the contemporary expectation record. If a future change
relaxes the nested form, this test fails at the third
assertion.

---

## 2. What PR 8 inherits from PR 7

### 2.1 The 19 verbatim sentences

Fourteen inherited carriers + binding framing clarification +
two PR-7-LOCAL pairs travel into PR 8 unchanged. PR 8's seed
driver surface is consumed-side of the `_persist_expectation_record`
seam PR 7 ships; the §4.2 + §5.5 binding pairs do NOT regenerate
(they are PR-7-LOCAL by definition), but the fourteen + binding
clarification do — they travel into PR 8's seed-driver module
docstring + commit message bodies.

PR 8 will likely introduce additional carriers (the seed driver
is structurally distinct from the contextvar resolution path
PR 7 ships). PR 8's framing names those at framing time.

### 2.2 The `_persist_expectation_record` seam

The single most consequential PR-8-bound artifact PR 7 ships.
The helper:

- Lives in `_capture.py` as a private (underscore-prefixed)
  helper.
- Takes a pre-built expectation record dict.
- Performs an authority pre-check (`record_kind == "expectation"`)
  BEFORE generic schema validation.
- Validates the record via `validate_capture_record`.
- Persists via the atomic-append discipline shared with
  `emit_divergence_capture`.
- Wraps everything in I-6 failure-invisibility.

PR 8's `emit_seed_expectation` is the single production call
site. The helper does NOT consult `_dispatch_context` — the
non-participation guard's binding statement is verbatim in the
helper docstring.

**What PR 8 must NOT do:**

- Couple `_persist_expectation_record` to the dispatch context
  (per non-participation guard).
- Remove the authority pre-check ("schema validator covers it")
  — per authority guard.
- Refactor `_persist_expectation_record` + `emit_divergence_capture`
  into a shared internal writer (per cleanup-pressure-
  resistance class member #1 + spec §7 phase-end conditions
  row).
- Promote the helper to `forge_bridge.__all__` (the public-
  export question may be revisited at PR 8 framing if the
  seed driver consumer establishes external need; the
  question never lands inside an unrelated cleanup PR).

### 2.3 The `seed_dispatch_scope` operational surface

The public context manager that activates `source="seed"`
provenance. PR 8's seed driver opens scope per fixture; per
spec §3 risk #1 the contextvar must reset cleanly on scope
exit (including on exception).

The helper yields nothing public — internal `ContextVar.set()`
token use is implementation detail. PR 8 must not propose a
nested-scope-introspection surface inside a cleanup PR (per
spec §7 close conditions; framing-level expansion event if
genuinely needed).

The scope helper is consumed by tests directly today (the
`test_pr7_dispatch_context.py` tests open and close scopes
without an arbitration call between). PR 8's seed driver is
the first production caller.

### 2.4 The KNOWN_SOURCE_VALUES + record_kind ontology

PR 8 inherits two governance constants and the lockstep
contract that binds them:

- `KNOWN_SOURCE_VALUES = frozenset({"runtime", "seed"})` in
  `_sources.py`. PR 8 must not add a third value inside a
  cleanup PR (per spec §7 close conditions).
- `_KNOWN_RECORD_KINDS = frozenset({"observation",
  "expectation"})` in `_schema.py`. PR 8 must not add a third
  value (per spec §7 close conditions; new record_kind
  values imply a new authority surface, which is a
  framing-level decision).

PR 8's seed driver will emit `source="seed"` records — the
contextvar resolution path is what makes this work. PR 8 does
not modify the resolution path; it drives it from above via
`seed_dispatch_scope`.

### 2.5 Reader synthesis + corruption-locality contract

PR 8 inherits a reader that:

- Synthesizes `record_kind="observation"` + `fixture_id=None`
  for legacy records (nested form).
- Validates `record_kind` against `_KNOWN_RECORD_KINDS`.
- Validates observation records' `source` against
  `KNOWN_SOURCE_VALUES`.
- Rejects expectation records that carry a `source` field
  (per spec §4.3.1).
- Preserves the PR 3 corruption-locality contract (malformed
  records skip with WARNING; never abort iteration).
- Never mutates the source file (per §5.5 binding pair;
  byte-identicality test enforces).

PR 8 will likely add expectation-record-specific reader test
cases. The synthesis layer is already in place; PR 8 does not
modify it.

### 2.6 Test infrastructure conventions

PR 8 inherits the `base_writer_args()` / `base_builder_args()`
split:

- `base_writer_args()` — canonical default-valid kwargs for
  `emit_divergence_capture` (the writer surface).
- `base_builder_args()` — layered on `base_writer_args()` with
  `record_kind="observation"` added (per the §4.3 amendment's
  builder requirement).

PR 8 will need `base_expectation_args()` — the third helper for
expectation record construction. This expectation is named in
the framing memory (`project_pr8_base_expectation_args.md`)
and in PR 7 Step 5's commit body. PR 8 framing should flag the
addition as expected test infrastructure, not as
incarnation-time discovery.

The `test_pr7_expectation_persistence.py::_make_expectation_record`
helper PR 7 ships is the prototype shape — minimal four universal
keys + `record_kind`. PR 8's `base_expectation_args` will likely
extend with the operational expectation fields the seed driver
defines.

### 2.7 Surface-before-implementation discipline

The PR 3 → PR 4 → PR 5 → PR 6 → PR 7 cadence carries unchanged
into PR 8:

- Framing artifact (registered, surfaced for review).
- Spec derived from framing (surfaced for review).
- Spec amendments registered as their own commits if surface
  positions surface mismatches at incarnation (the §4.3
  amendment pattern; saved as feedback memory).
- Implementation derived from spec, with cadence-matches-work-
  depth review (light-touch for plumbing, full three-round
  for boundary work, surface-diff-for-review at every commit
  regardless of depth).
- Atomic merge.

PR 8 drafts framing after this commit.

---

## 3. What PR 8 changes

### 3.1 Introduces `emit_seed_expectation` — the seed driver's
public seam

PR 8 introduces a new public helper that builds and persists an
expectation record. The single production call site for
`_persist_expectation_record` lands inside `emit_seed_expectation`.

The exact shape — signature, builder fields, integration with
`seed_dispatch_scope` — is PR 8 framing work. What's locked from
PR 7 is the persistence path:

- `emit_seed_expectation` MUST call
  `_persist_expectation_record(record)` rather than reaching
  for `_resolve_corpus_dir` / `_serialize_line` / file I/O
  directly. The authority pre-check + atomic-append discipline
  are not bypassable.
- `emit_seed_expectation` MUST set
  `record_kind="expectation"` on the record it builds. The
  authority pre-check fires otherwise.

### 3.2 Defines the operational expectation record shape

PR 7 ships the seam; PR 8 defines what an expectation record
*contains* beyond the four universal keys + `record_kind`. The
schema validator's `record_kind == "expectation"` branch
currently rejects only "carries a `source` field"; PR 8 will
extend with expectation-specific required keys (per the
in-source comment block in `_schema.py:225–228`).

PR 8 framing must articulate:

- The seed-fixture's relationship to the expectation record's
  content (does each fixture emit exactly one expectation? a
  bundle? a sequence?).
- Whether expectation records carry `fixture_id` (the nested
  synthesis form preserves PR 8's choice — see §1.8).
- Whether expectation records carry arbitration-state fields
  (decision, candidate sets, identity hashes) or a structurally
  distinct shape.

### 3.3 Wires the seed-driver loop

The high-level shape from PR 7's framing/spec references
(though PR 8 framing is the authoritative artifact):

```python
for fixture in load_seed_corpus():
    expectation_record = build_expectation_record(fixture)
    _persist_expectation_record(expectation_record)
    with seed_dispatch_scope(fixture_id=fixture.id):
        drive_arbitration_pipeline(fixture.prompt)
    # Inside the scope, emit_divergence_capture (called from
    # handlers.py or _step.py) automatically persists
    # source="seed" observation records carrying fixture_id.
```

This is illustrative, not binding — PR 8 framing locks the
actual shape. The structural commitments PR 7 makes are:

- The driver invokes `_persist_expectation_record` directly
  (one production call site).
- The driver opens `seed_dispatch_scope` per fixture (per-
  fixture scope, not per-batch).
- The driver does NOT modify the arbitration call sites.
- The driver does NOT modify the env gate.

### 3.4 What does NOT change

- v1 schema continues unchanged (additive `record_kind`; no
  version bump per spec §7 close conditions).
- The 14 inherited carriers + binding framing clarification
  travel verbatim.
- The §4.2 + §5.5 PR-7-LOCAL pairs do NOT regenerate (they
  are scoped to `_capture.py` + `reader.py` respectively).
- The three-layer structural-test discipline carries.
- The cadence-matches-work-depth review rule carries.
- The cleanup-pressure-resistance class final inventory
  carries — PR 8 may add members if a structural commitment
  surfaces, but the existing six members are unchanged.

---

## 4. Step-by-step verification archaeology

Per spec §6, PR 7 implemented an 8-step staircase. Each step's
verification observations:

| Step | Commit | Review depth | What landed | Verification |
|---|---|---|---|---|
| 1 | `0187e9d` | Light-touch | `_sources.py` created with `KNOWN_SOURCE_VALUES` constant + protected-property docstring | 3/3 new tests in `test_pr7_known_source_values.py`; `_ALLOWLIST` admits `_sources.py` by structural location |
| 2 | `b987d31` | Light-touch | Discipline boundary verification (no code change to discipline test); Step 1 docstring correction surfaced inline | `test_pr3_discipline.py` passes with `_sources.py` present; admission-vs-import distinction verified |
| 3 | `6e5b82e` | Light-touch | `_DispatchContext` frozen dataclass + module-private `_dispatch_context` ContextVar | `test_dispatch_context_dataclass_is_frozen` |
| 4 | `ea7d3fe` | Light-touch | `seed_dispatch_scope` public no-yield context manager | `test_scope_resets_on_exception` + `test_nested_scope_inner_overrides`; mid-Step-4 probe (`python -c "from forge_bridge.corpus._capture import seed_dispatch_scope, _dispatch_context; ..."`) confirmed contextvar transitions before the schema validator landed |
| 5 | `219d89a` | Light-touch | Schema validator + `_VALID_SOURCES` replacement + 11 test migrations (post-§4.3-amendment reorder) | 4/4 new tests in `test_pr7_record_kind_schema.py`; mid-Step-5 probe (validator accepts `record_kind="observation"` + `source="runtime"`) confirmed before Step 6 introduces `source="seed"` emission |
| 6 | `0de62a6` | **Full three-round** | Provenance resolution path inside `emit_divergence_capture` — the architectural center; `fixture_id` parameter on builder; always-present field on observation records | 3 new resolution-path tests in `test_pr7_dispatch_context.py`; **mandatory Layer 3 lint regression checkpoint — 17/17 passed unchanged**; Property C structurally intact |
| 7 | `38a1c5f` | Light-touch | Reader interpretation — PR 7 carriers AT TOP of reader docstring; nested legacy-record synthesis form | 9 new tests across `test_pr7_reader_validation.py` (5) + `test_pr7_legacy_record_synthesis.py` (4); SHA-256 byte-identicality test enforces §5.5 binding pair |
| 8 | `7838f9a` | Light-touch | `_persist_expectation_record` private helper — sibling of `emit_divergence_capture`, not subordinate; non-participation guard + authority guard | 5 new tests in `test_pr7_expectation_persistence.py`; three are authority-boundary load-bearing (non-participation byte-identical; missing record_kind pre-check; well-formed observation pre-check) |

**The architectural-center moment — Step 6.**

Step 6 was the only step that received full three-round review.
The framing §5.1 + spec §6 amendment locked Step 6 as the most
load-bearing step in PR 7: it lands the resolution path that
makes the contextvar substrate operational, AND it's the step
most at risk of regressing Property C (the Layer 3 lint's
literal check). The mandatory regression checkpoint immediately
after Step 6 confirmed Property C structurally intact (17/17
unchanged). If the lint had regressed, the team would have
converged before any further plumbing steps stacked on top.

The Step 6 commit body (`0de62a6`) carries the four-fold
verification archaeology: substrate transitions verified
(Step 3+4), schema validator green (Step 5), resolution path
emitting `source="seed"` correctly (the new tests), Layer 3
lint unchanged against the modified `_capture.py` (the
regression checkpoint).

**The light-touch-still-warrants-redline pattern — Steps 7 + 8.**

Both Step 7 and Step 8 were light-touch per spec. Both surfaced
a pre-commit redline that improved the diff:

- Step 7's surface-diff pass caught the unconditional-synthesis
  form. The nested form was locked at the redline; the
  unconditional form would have shipped on the first pass.
- Step 8's surface-diff pass caught an unused `import pytest`
  + a function-local `validate_capture_record` import. Both
  cleaned before commit.

The methodology generalizes: **light-touch review depth ≠ skip
pre-commit redline**. The surface-diff-for-review cadence runs
regardless of review depth. The redline is about catching
architectural choice points (Step 7) and small-but-real
cleanliness items (Step 8); both shipped because the cadence
ran.

---

## 5. Methodology observations surfaced during PR 7

PR 6 CLOSE §5 produced four methodology observations (the
methodology was stabilizing). PR 7 produces six — the framing's
introduction of the cleanup-pressure-resistance class plus the
§4.3 amendment surfaced novel methodology gestures worth
surfacing for promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`.

### 5.1 Spec amendments at incarnation are normal and valuable

The §4.3 amendment registered the post-Step-4 grounding
correction as its own commit (`30d3ca9`) before Step 5 landed.
The commit was NO code — only spec text. The pattern is:

1. Spec drafted from framing + memory (read PR 7 framing,
   recall what `_schema.py` looks like).
2. Implementation begins at Step 1 (read `_sources.py`-related
   files for the first time during implementation).
3. Step 4 + Step 5 boundary: pre-implementation surface pass
   reads `_schema.py` for the first time.
4. Mismatch surfaces (the spec assumed no `_VALID_SOURCES`;
   the file has one).
5. Amendment registered as its own commit, with:
   - The mismatch named.
   - The architectural resolution articulated (sub-path A
     vs. B vs. C analysis; ship A, reject B + C with
     reasoning).
   - The step ordering adjusted if the implementation order
     becomes infeasible.
6. Implementation proceeds against the amended spec.

**The methodology observation:** spec amendments BEFORE
implementation, registered as their own commits, are
mergeable archaeology — they show the discovery → amendment →
implementation cadence distinctly. Folding the amendment into
the Step N commit smears two distinct cognitive events.

This generalizes the existing **ground specs in actual files**
feedback (saved as memory). The amendment cadence makes the
discipline operational at the spec layer when grounding
happens at incarnation rather than at spec drafting time.

### 5.2 The architectural-center identification before
implementation

Spec §6 amendment locked Step 6 as the single step receiving
full three-round review BEFORE Step 6 began. The room
identified the most architecturally load-bearing step in
advance and reserved the deepest review depth for it. Steps
1–5, 7, 8 were all light-touch.

**The methodology observation:** review-depth allocation should
be a framing-time decision, not an incarnation-time decision.
"This step is the architectural center" identified at framing
time + reserved for full review at that time saves cognitive
load at incarnation (no second-guessing "should we go deep on
this one?") and protects the architectural center from
under-review.

The Layer 3 lint regression checkpoint immediately after Step
6 was a structural amplifier — it gave the room a mechanical
test the moment it mattered most. The combination (framing-
time review-depth + immediately-after-architectural-step
mechanical checkpoint) is generalizable.

### 5.3 Light-touch review ≠ skip pre-commit redline

PR 7's eight steps split as: 1 full three-round (Step 6), 7
light-touch. Both light-touch steps after Step 6 (Steps 7 + 8)
surfaced redline items at the pre-commit surface-diff pass.
Without the surface-diff cadence, Step 7 would have shipped
the unconditional synthesis form; Step 8 would have shipped
unused imports and a function-local import.

**The methodology observation:** the surface-diff-for-review
cadence is independent of review depth. "Light-touch" is
about *the depth of architectural analysis*; the pre-commit
redline is about *catching the local diff*. Skipping the
redline at light-touch depth is the failure mode that
masquerades as efficiency.

The PR 7 framing §6 cleanup-pressure-resistance class itself
is a derivative of this observation — the class names
constructs whose value is invisible from inside a local
cleanup diff but load-bearing at the architectural level.
Pre-commit redline catches the local-diff-defensible
mutations.

### 5.4 Memory-feedback-loop validation within a single session

PR 7 surfaced the first within-single-session validation of a
saved feedback memory. The sequence:

1. Step 6 redline pass surfaced the inline-authority-boundary-
   guard pattern. Saved as
   `feedback_inline_authority_boundary_guards.md`.
2. Step 7 implementation needed the synthesis-site comment
   block. The Step 7 commit body (`38a1c5f`) carries the §5.5
   carrier text verbatim AT the synthesis site (not just in
   the module docstring).
3. The memory was load-bearing when applied; not stale by the
   time Step 7's callsite came up.

**The methodology observation:** feedback memories saved
mid-session are mergeable archaeology when the next applicable
callsite arrives in the same session. This validates the
memory infrastructure's design property: memories are useful
at conversation-N+1 boundaries, but also at conversation-N
boundaries when the original feedback's pattern recurs.

### 5.5 The cleanup-pressure-resistance class as architectural defense

PR 7 framing §6 introduced the class. PR 7 implementation
populated it (six members). PR 7 close inventory locks the
class as part of the architectural state PR 8 inherits.

**The methodology observation:** the class is itself a
discipline — each member must carry inline documentation
naming the protection. The discipline is structural defense
against silent erosion via cleanup PRs. Cleanup PRs are
patient: "remove redundant param" looks locally defensible
from inside the cleanup PR's diff. The named class is the
reviewer's lookup — a construct in the class cannot be
removed without first naming the protection and arguing the
protection is no longer needed (a framing-level question,
not a cleanup-PR question).

Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` remains gated on
at-least-one-more-reliability-phase independent corroboration.
PR 7 contributed; a second phase confirming under different
conditions would unlock promotion.

### 5.6 The "what PR N+1 inherits" archaeology section

PR 4 CLOSE introduced the "What PR 5 inherits" section
explicitly. PR 5 CLOSE refined it. PR 6 CLOSE made it the
canonical archaeology shape. PR 7 CLOSE confirms the pattern:
the close artifact's §2 is the bridge artifact PR N+1's
framing consumes.

**The methodology observation:** the inheritance section is
authored at close-time, when context is warm, BEFORE the next
PR's framing begins. Authoring inheritance at framing-time
(once context has decayed) loses fidelity. The close → framing
cadence is itself a methodology pattern: close authors what
inherits; framing consumes inheritance as input rather than
re-deriving it from session history.

---

## 6. Bite-verification observations (PR 7's mechanical checkpoints)

PR 7 did not run operator-driven bite-verification scratches in
the PR 6 style. PR 7's architectural class is "plumbing layer
with mechanical guards"; the guards themselves serve as the
verification surface. The mechanical checkpoints across the
eight steps:

| Checkpoint | When | What it verified | Result |
|---|---|---|---|
| Step 1 → Step 2 | Post-Step-1 | `_sources.py` present + `_ALLOWLIST` admits by structural location | ✓ Discipline boundary held without `_ALLOWLIST` extension (per §4.5 amendment) |
| Step 4 → Step 5 (mid-substrate) | Post-Step-4 | Contextvar transitions work in isolation before schema validator layers ontology enforcement | ✓ `python -c "from forge_bridge.corpus._capture import seed_dispatch_scope, _dispatch_context; ..."` confirmed |
| Step 5 → Step 6 (mid-validator) | Post-Step-5 | Schema validator accepts `record_kind="observation"` + `source="runtime"` before Step 6 introduces `source="seed"` emission | ✓ Migrated test suite passes; failure-mode ambiguity (resolution-path vs. validator) is split |
| Step 6 immediately-after | Post-Step-6 | **Layer 3 lint regression — `test_pr6_visual_asymmetry.py` passes unchanged against the modified `_capture.py`** | ✓ **17/17 unchanged**; Property C structurally intact |
| Step 6 → Step 7 (mid-resolution) | Post-Step-6 | Resolution path operational + lint unchanged before reader synthesis layer | ✓ Both passed |
| Step 7 → Step 8 (mid-reader) | Post-Step-7 | Reader validation extension operational before expectation persistence helper introduces records to read | ✓ 9 new reader tests passed; legacy synthesis byte-identicality confirmed |
| Step 8 (PR 7 close) | Final | 175 corpus tests pass; same 4 pre-existing failures unchanged | ✓ 175/175 (forge env); Layer 3 lint 17/17 |

**The Step 6 regression checkpoint was the architectural-
center mechanical guard.** It was the moment in PR 7's
implementation most at risk of architectural regression
(resolution path lands while Property C's literal check must
hold structurally). Its passing 17/17 unchanged is the single
most important verification observation in PR 7's archaeology.

**No scratch landed in main.** No bite-verification mutation
was applied to production code paths. The guards in the
source itself are the verification surface — every guard's
absence regresses a named test.

---

## 7. Reseed protocol — what the PR 8 framing session does with this artifact

When the PR 8 framing session opens:

1. **Read this CLOSE artifact first.** It contains the durable
   PR 7 state PR 8 inherits — particularly §2 (what PR 8
   inherits), §3 (what PR 8 changes), and §1.2 (cleanup-
   pressure-resistance class final inventory). Skipping it
   means re-deriving the three-authority-surface partitioning
   + the seam contract from session history rather than from
   a stable archival document.

2. **Read `A.5.3.2-PR7-FRAMING.md`** (`1c1e061`). PR 7
   framing's §6 cleanup-pressure-resistance class + §7
   non-acquisition commitments + §5 binding decisions
   continue to govern PR 8.

3. **Read `A.5.3.2-PR7-SPEC.md`** §4.2.6 + §6 step 8 + §7
   phase-end conditions. §7 contains the "future PR rejection"
   table — PR 8 may not propose any of those mutations
   (refactor helpers together, remove pre-check, surface
   nested-scope token, etc.) even incidentally.

4. **Read `A.5.3.2-GATE-2-FRAMING.md`** §3.4
   three-authority-surface partitioning + §9 schema delta +
   §10 PR partitioning. Gate 2's framing is what PR 8 closes
   when PR 8 closes.

5. **Re-read project memory `project_pr8_base_expectation_args.md`.**
   PR 8 framing should flag the `base_expectation_args` test
   infrastructure helper as expected (not incarnation-time
   discovery). Mirror of PR 7 Step 5's `base_writer_args` /
   `base_builder_args` split.

6. **Draft `A.5.3.2-PR8-FRAMING.md`.** PR 8's framing must
   articulate:
   - The seed driver's structural shape (loop? single
     entry point? CLI? hook into existing daemon flow?).
   - The operational expectation record shape (beyond the
     four universal keys + `record_kind`).
   - The relationship between fixture loading and
     `seed_dispatch_scope` invocation (per-fixture? per-
     batch?).
   - The seed driver's call-site relationship to the Layer 3
     lint (does it use Properties A–D? a distinct shape with
     its own Layer-3 lint? no shape requirement because it's
     a non-arbitration surface?).
   - The non-acquisition commitments PR 8 makes (what PR 8
     does NOT do, in PR 7 framing §7 style).
   - The binding decisions PR 8 ships (in PR 7 framing §5
     style).
   - The cleanup-pressure-resistance class members PR 8 adds
     (if any).

7. **Surface the framing for review** before drafting the
   spec. PR 7's discipline holds.

8. **Draft `A.5.3.2-PR8-SPEC.md`** from the locked framing.
   Spec amendments at incarnation are normal (per §5.1
   methodology); register them as NO-code commits.

9. **Implement** against the spec per the cadence-matches-
   work-depth review rule. Surface-diff-for-review at every
   commit regardless of review depth (per §5.3 methodology).

10. **Close PR 8 with `A.5.3.2-PR8-CLOSE.md`** following this
    artifact's structure. If PR 8 closes Gate 2 (per Gate 2
    framing §10 PR partitioning), the close includes a Gate 2
    closure section in PR 6 CLOSE §6 style.

The cadence — framing → spec → spec-amendments-at-incarnation
→ steps → close — carries unchanged.

---

## 8. Cross-references

- `A.5.3.2-PR7-FRAMING.md` (commit `1c1e061`) — pre-spec
  binding contract; §4.2 inert-parameter binding pair; §5.5
  legacy-synthesis binding pair; §6 cleanup-pressure-resistance
  class (introduced); §7 seven non-acquisition commitments;
  §5 four binding decisions.
- `A.5.3.2-PR7-SPEC.md` (commit `84392d2`) — implementation
  contract; nineteen verbatim sentences; 27 tests across five
  files; 8-step staircase; §7 phase-end conditions
  (rejection table for future PR proposals); §6 step 8
  authority guard + non-participation guard.
- `A.5.3.2-PR7-SPEC.md` amendments — `0a2ad7e` (§4.5
  admission-vs-import correction; NO code) and `30d3ca9`
  (§4.3 `_VALID_SOURCES` discovery + Step 5↔6 reorder; NO
  code). Both registered as their own commits per
  methodology §5.1.
- `A.5.3.2-GATE-2-FRAMING.md` (commit `ceac9b5`) — gate-level
  architecture; §3.4 three-authority-surface partitioning
  (this CLOSE §1.1); §6.1 carrier #14 (this CLOSE §1.4);
  §6.2 binding framing clarification (this CLOSE §1.4); §9
  schema delta (this CLOSE §1.7); §10 PR partitioning
  (this CLOSE §3).
- `A.5.3.2-PR6-CLOSE.md` (commit `9168df7`) — durable archival
  state PR 7 inherited; §1.3 truth-vs-mechanism distinction
  (informs `_sources.py` governance docstring); §1.1 Layer 3
  lint operational shape (regression-asserted at PR 7 Step 6);
  §5 methodology shape (this CLOSE §5 follows).
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherited; reviewed for inheritance continuity.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; "What PR N+1 inherits" section
  established (this CLOSE §2 follows).
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (Properties A–D); preserved unchanged through PR 7 (Layer 3
  lint passes 17/17 against modified `_capture.py`).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §3 — record shape; PR 7
  extends with `record_kind` per Gate 2 framing §9.2.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation surface; PR 7 §4.2.5 added contextvar resolution
  internally; signature unchanged from external view.
- `forge_bridge/corpus/_capture.py::seed_dispatch_scope` —
  PR 7 §4.2.4; public no-yield context manager; PR 8's seed
  driver invokes per fixture.
- `forge_bridge/corpus/_capture.py::_persist_expectation_record` —
  PR 7 §4.2.6; private helper; consumed by PR 8's
  `emit_seed_expectation` exclusively; non-participation guard
  + authority guard verbatim in docstring.
- `forge_bridge/corpus/_sources.py::KNOWN_SOURCE_VALUES` —
  PR 7 §4.1; single authority for persisted source-class
  governance; lockstep contract across four downstream
  surfaces (this CLOSE §1.7).
- `forge_bridge/corpus/_schema.py::_KNOWN_RECORD_KINDS` —
  PR 7 §4.3.1; `record_kind` ontology constant; private to
  the validator; truth-class discriminator.
- `forge_bridge/corpus/reader.py` — PR 7 §4.4; carrier
  inheritance + nested legacy-record synthesis; §5.5 binding
  pair verbatim in module docstring + inline at synthesis
  site (defense in depth).
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 lint;
  **unchanged by PR 7**, regression-asserted at Step 6
  immediate-after checkpoint and at PR 7 close.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` —
  unchanged at PR 7 close per §4.5 spec amendment; `_sources.py`
  admitted by structural location (in `corpus/` subtree), not
  by name-based extension.
- `tests/corpus/test_pr7_*.py` — five new test files (27
  tests total) per spec §5.1; zero modifications to existing
  test files other than 11 `source="fixture"` → `source="runtime"`
  migrations per §4.3 amendment.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidates from this CLOSE §5:
  - §5.1 spec-amendments-at-incarnation cadence.
  - §5.2 framing-time review-depth allocation +
    architectural-center identification.
  - §5.3 light-touch ≠ skip pre-commit redline.
  - §5.4 memory-feedback-loop validation within a single
    session.
  - §5.5 cleanup-pressure-resistance class as architectural
    defense (already candidate at PR 7 framing; PR 7
    implementation provides corroboration).
  - §5.6 close-authors-inheritance / framing-consumes-
    inheritance cadence.
- `project_pr8_base_expectation_args.md` (local memory) — PR
  8 framing flag for the third test infrastructure helper.
- `project_state_2026_05_10_pr7_closed.md` (local memory) —
  active cursor; supersedes `project_state_2026_05_09_post_step7.md`.
- PR 7 step commits (origin/main):
  - `1c1e061` — PR 7 framing registered (NO spec, NO code).
  - `84392d2` — PR 7 spec registered (NO code).
  - `0187e9d` — Step 1: ontology constant (`_sources.py`).
  - `0a2ad7e` — Spec amendment 1: §4.5 admission-vs-import
    correction (NO code).
  - `b987d31` — Step 2: discipline boundary verification +
    Step 1 docstring correction.
  - `6e5b82e` — Step 3: dispatch substrate (`_DispatchContext`
    + `ContextVar`).
  - `ea7d3fe` — Step 4: scope surface (`seed_dispatch_scope`).
  - `30d3ca9` — Spec amendment 2: §4.3 `_VALID_SOURCES`
    discovery + Step 5↔6 reorder (NO code).
  - `219d89a` — Step 5: schema validator + `_VALID_SOURCES`
    replacement + 11 test migrations.
  - `0de62a6` — Step 6: provenance resolution path
    (architectural center; full three-round review; Layer 3
    lint regression checkpoint 17/17 passed unchanged).
  - `38a1c5f` — Step 7: reader interpretation (nested
    legacy-record synthesis form).
  - `7838f9a` — Step 8: expectation persistence helper
    (PR 7 close).

---

PR 7 closes here. **Gate 2 continues into PR 8** (seed driver
+ `emit_seed_expectation` + operational expectation record
shape). The next session opens at PR 8 framing per §7 reseed
protocol.
