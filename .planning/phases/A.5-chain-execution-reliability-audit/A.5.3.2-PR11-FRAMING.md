# A.5.3.2 PR 11 — Framing (end-to-end recomposition arc + Gate 3 closure convergence)

**Status:** PR 11 opens at `cf2b7ee` (origin/main, PR 10 close
landed). This framing locks the architectural posture for the
end-to-end recomposition arc and the binding decisions reached
during the PR 10 close → PR 11 framing convergence pass.

PR 11 is the second of two (or conditionally three) PRs
sequenced within Gate 3 per Gate 3 framing §10. **The Gate 3
close artifact (`A.5.3.2-GATE-3-CLOSE.md`) ships at the same
commit as PR 11 close** per Gate 3 framing §11; PR 11 framing
therefore operates against a same-commit gate-close convergence
and defers most gate-arc synthesis to Gate 3 close.

The convergence pass produced four binding decisions: PR 11
scope is end-to-end recomposition through real `chat_handler`
arbitration (§5.1); 0 production source modifications is
elevated from "clean diff hygiene" to **named architectural
sufficiency signal** (§5.2); no production abstraction whose
primary purpose is "making recomposition cleaner" (§5.3); PR 12
trigger criterion preserved as conditional pending PR 11 close
evaluation (§5.5). One PR-11-LOCAL binding statement (§5.6).

---

## 0. Crystallizing pair — Gate-3-LOCAL governing sentence + PR-11-LOCAL traverses-not-erases-seams

Two sentences govern PR 11 verbatim. They appear at the top of
PR 11 test module docstrings + PR 11 commit message bodies
under "preserved invariants."

**Gate-3-LOCAL governing sentence (corroboration substrate
for candidate carrier #16):**

> **Gate 3 proves topology, not infrastructure.**

PR 11 contributes the remaining ≥1 surface (≥4 total) for the
Gate 3 close candidate-carrier-#16 promotion evaluation per
Gate 3 framing §6.1 criterion 1. PR 10 contributed 8 surfaces
of corroboration substrate; PR 11 needs only ≥1 additional
surface, and the Gate 3 close evaluation reads the cumulative
evidence base.

**PR-11-LOCAL binding statement — recomposition traverses, does
not erase, decomposition seams:**

> **PR 11 traverses the decomposition seams established by
> Gate 2 + Gate 3 substrate work without erasing them.
> Call-site awkwardness during recomposition is acceptable
> evidence that the decomposition boundaries held; introducing
> production abstractions whose primary purpose is "making
> recomposition cleaner" is rejected at the spec layer.**

This is the operational discipline statement governing PR 11
implementation. Successful recomposition is evidence the
decomposition was real; it is NOT justification for collapsing
the seams back together. The discipline applies at every
PR 11 test surface: the traversal explicitly visits each seam
in turn.

**Travel discipline at PR 11:**

The pair travels at PR 11 test module docstrings + commit
message bodies. Gate-3-LOCAL appears with explicit *candidate
carrier #16 corroboration substrate* marking (asymmetric
ordering preserved from PR 10 — carrier #17 active + primary;
Gate-3-LOCAL form secondary + substrate marking). PR-11-LOCAL
appears as scope-local discipline per the PR-N-LOCAL non-
regeneration rule (Gate 2 framing §3.1).

PR 11 must NOT write *"17 active carriers"* or *"carriers
#1–#17"* — correct phrasing remains *"16 active carriers +
candidate #16"* (per PR 10 framing §3.1 + PR 10 close §2.3).
Promotion of candidate #16 happens at Gate 3 close, not at
PR 11 close.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, six
  interlocking structural-invariant pairs.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing, three
  architecturally-prohibited patterns, helper signature,
  visual-asymmetry pattern.
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — three-authority-
  surface partition; carrier #14; binding clarification on
  call-site-owned arbitration inputs.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces; carrier #14;
  `_KNOWN_RECORD_KINDS` 2-element lock; cleanup-pressure-
  resistance class members #1–#6.
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface; PR-INTERNAL three-way authority partition (write-
  side); carrier #15; members #7 + #8.
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus;
  grounding-time amendment variant; member #9; the authored/
  observed divergence proof case; PR 9 integration test
  infrastructure (`_apply_pr9_patches`, `_PR9_REACHABLE_TOOLS`,
  `_read_records`, `_make_patched_invoke`) PR 11 reuses.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis;
  Gate 4 comparator's two foundational dependencies
  operationally verified.
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — gate-level
  inheritance contract; three inherited truths; Path B locked;
  candidate carrier #16 + Gate-3-LOCAL form; carrier #17;
  binding framing clarification on cross-surface unbinding;
  seven canonical cleanup-pressure forms; §11 Gate 3 close
  criteria.
- `A.5.3.2-PR10-FRAMING.md` (`8ad7fe9`) — comparator helper
  framing; pair-input pure-functional lock; Layer 2 Option A;
  carrier #17 operational landing posture.
- `A.5.3.2-PR10-SPEC.md` (`54d0ab9` + amendment `6830888`) —
  comparator implementation contract; §4.1.6 reference
  implementation; §4.4 amendment 2026-05-11 (sharpened
  Layer 1 semantics — corpus-subtree auto-exclusion + named-
  integration-call-site admission).
- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — **immediate
  predecessor; the durable PR 10 archival state PR 11 operates
  against.** §1.2 four architectural signals; §1.7
  cleanup-pressure-resistance class member 10 promotion (10
  members at PR 10 close); §2 PR 11 inheritance contract; §3
  what PR 11 / Gate 3 changes; §6.5 architectural success
  signal verification; §7 reseed protocol.
- **PR 10 close → PR 11 framing convergence pass (this
  session):** four binding decisions locked (scope; 0-prod-mod
  as architectural sufficiency signal; no recomposition
  abstraction; PR 12 conditional preserved). One PR-11-LOCAL
  binding statement (§5.6) without introducing new carriers —
  PR 11 inherits Gate 3 framing's carrier set unchanged.

---

## 2. PR 11 objective

PR 11 ships the **end-to-end recomposition arc** — integration
tests that drive each PR 9 fixture through the full
decomposition seam traversal:

```
fixture (tests/corpus/fixtures/fix_*.py)
  → drive_seed_fixture          [orchestration seam]
    → emit_seed_expectation     [expectation persistence seam]
    → chat_handler arbitration  [observation production seam]
      → emit_divergence_capture [observation persistence seam]
        → JSONL persistence     [persistence-topology seam]
          → reader              [readback seam]
            → compare_records   [interpretive-read seam]
              → DivergenceReport assertions
```

Each arrow is a decomposition seam established at Gate 2 or
Gate 3 substrate work. PR 11 traversal visits each seam
explicitly; no seam is collapsed; no helper is introduced that
short-circuits the traversal.

### 2.1 Recomposition-through-existing-seams (governing framing posture)

PR 11 proves **recomposition-through-existing-seams**, not
**new integration infrastructure**. The architectural value
PR 11 demonstrates is that independently hardened surfaces
remain compositionally compatible without introducing new
orchestration helpers:

- `drive_seed_fixture` (PR 8) is the existing orchestration
  entry point; PR 11 invokes it without wrapping it.
- `chat_handler` (production code, hardened during Gate 2) is
  the existing arbitration surface; PR 11 patches the
  reachable-tool set per PR 9's strategy and invokes it
  without mocking.
- `emit_divergence_capture` + `emit_seed_expectation` (PR 7 +
  PR 8) are the existing emission helpers; PR 11 does NOT
  invoke them directly — they are invoked transitively through
  `drive_seed_fixture` + `chat_handler`.
- The reader (PR 7) is the existing readback surface; PR 11
  invokes it via `_read_records` test helper inherited from
  PR 9.
- `compare_records` (PR 10) is the existing interpretive-read
  surface; PR 11 invokes it as the final step in the traversal.

**No PR 11 test introduces a new orchestration helper.** No
test wraps `drive_seed_fixture` in a "convenience" function;
no test extracts a "fixture-to-DivergenceReport" helper that
absorbs the traversal; no test factors the readback +
comparator invocation into a reusable assertion helper. Each
test traverses the full path explicitly.

### 2.2 Recomposition asymmetry — successful recomposition does NOT justify collapsing seams

Gate 2 decomposition expanded + separated authority surfaces.
Gate 3 substrate (PR 10 comparator) extended the decomposition
with a new read-side surface. **PR 11 recomposition is
intentionally NOT symmetric with the decomposition.**

The asymmetry:

- Decomposition's job (Gate 2) was to **establish** distinct
  authority surfaces with mechanical enforcement (Layer 1
  allowlist, Layer 2 walkers, Layer 3 lint, PR-INTERNAL
  three-way partition).
- Recomposition's job (PR 11) is to **traverse** the
  established surfaces, NOT to **establish a new joining
  authority** that would erase them.

Successful recomposition is **evidence the decomposition was
real**. It is NOT justification for:

- Adding a "fixture-to-comparator" orchestration helper to
  production (the seams are the value; a helper that absorbs
  them removes the value).
- Promoting `compare_records` to consume corpus reader internals
  directly (the existing reader interface is sufficient;
  acquiring reader internals at the comparator would collapse
  two seams).
- Refactoring `drive_seed_fixture` to "produce" the comparison
  pair as a tuple (the orchestrator's job is orchestration; the
  pair-input shape is the comparator's contract).

PR 11 traverses the seams. The seams remain.

### 2.3 0 production source modifications as named architectural sufficiency signal

PR 9 demonstrated recomposition readiness with **isolated
comparator addition** (PR 10's `_compare.py`, single new file,
523 lines). PR 11 projecting **full end-to-end recomposition
with 0 production source modifications** materially validates
the Gate 2 + Gate 3 decomposition strategy:

| PR | Architectural success signal | Strength of validation |
|---|---|---|
| PR 9 | 0 prod mods (test-surface only) | Substrate surfaces were sufficient for fixture authoring + integration tests against existing surfaces |
| PR 10 | Exactly 1 new prod file (`_compare.py`), 0 mods elsewhere | New read-side surface composable without modifying existing surfaces |
| **PR 11 (projected)** | **0 prod mods** | **Full recomposition arc traversable without modifying ANY surface — decomposition strategy operationally validated by end-to-end exercise** |

This is **stronger than "clean diff hygiene."** It is
**corroborated evidence that the decomposition boundaries were
sufficient** — every seam admits the traversal without
extension, every surface accepts its existing contract without
relaxation, every authority class is preserved through the
arc.

The signal travels into PR 11 commit message bodies under
"architectural sufficiency signal" + into PR 11 close §6 (or
Gate 3 close §1 — same-commit convergence) as the durable
archaeology.

**If PR 11 implementation surfaces a genuine production need**
(e.g., a reader-level helper to join records by `fixture_id`,
or a comparator-side mechanism the current API doesn't
support), framing decision: name + justify it explicitly. The
0-prod-mod signal is **goal**, not **constraint**. A
justified deviation is reportable archaeology; an unjustified
deviation is rejected at spec review.

### 2.4 The traversal trace as architectural test posture

Each PR 11 integration test is **named and shaped by the
traversal** it exercises. Test names should reflect the
fixture being driven + the divergence outcome being verified.
Test bodies should make the traversal visible (no
single-line "convenience" calls that absorb the arc); the
intent is that a reader of the test code can verify the
recomposition is real by inspection.

The traversal trace is a documentation artifact at PR 11
scope: it appears verbatim at PR 11 test module docstrings
and at PR 11 commit message bodies. Future archaeology
reading PR 11 finds the traversal explicit in the test code +
the trace explicit in the docstring/commit body.

---

## 3. Architectural inheritance

### 3.1 16 active carriers + candidate #16 + binding clarifications

Inherited from PR 10 close unchanged. PR 11 introduces **no
new carriers** and **one PR-11-LOCAL binding statement** (§5.6,
scope-local to PR 11 surfaces).

**Active carrier count at PR 11 framing: 16** (#1–#15 + #17).
**Candidate carrier #16** preserved. **Gate-3-LOCAL governing
sentence** active as corroboration substrate; PR 11 contributes
the remaining ≥1 surface for the ≥4 total Gate 3 close reads.

Carriers travel verbatim into PR 11 test module docstrings +
commit message bodies. The 16-active-count discipline holds:
PR 11 spec authors must not write *"17 carriers"* or *"carriers
#1–#17."*

### 3.2 Three-authority-surface partition operational

Gate 2 §3.4 partition preserves unchanged:

- Observation surface — `emit_divergence_capture` + contextvar
  resolution.
- Dispatch provenance surface — `seed_dispatch_scope` +
  `_DispatchContext`.
- Authored expectation surface — `emit_seed_expectation` +
  `drive_seed_fixture` + schema validator.

**PR 11 traverses all three surfaces transitively.** The
fixture-driven arc invokes `drive_seed_fixture` which emits
the expectation (authored expectation surface), then
`chat_handler` arbitration which produces the observation
(observation surface) under dispatch context (dispatch
provenance surface). PR 11 tests assert against the readback
of all three surfaces' persisted output, joined by
`fixture_id` and compared via `compare_records`.

The PR 10 read-side **structural parallel** (per PR 10 close
§1.6 — emergent architectural archaeology, NOT peer-class
governance) is also exercised through `compare_records`
invocation, but PR 11 does NOT introduce a parallel structure
of its own at the test surface.

### 3.3 Four-walker Layer 2 partition operational

PR 4 + PR 8 + PR 9 + PR 10 walkers preserve unchanged. PR 11
adds **no fifth walker** — PR 11 is test-surface-only at a
consumption tier; no new production module surface requires
admission-ontology protection.

The four walkers continue to enforce their respective
ontologies; PR 11 implementation prep should verify the
walkers pass unchanged against the post-PR-11 codebase
(test-surface additions are walker-target-disjoint for all
four walkers).

### 3.4 Cleanup-pressure-resistance class at 10 members

Inherited from PR 10 close unchanged. PR 11 framing does
**NOT speculatively author new members** (per Gate 3 framing
§7 item 13 + PR 10 framing §6). New members surface at PR 11
close based on actual pressure encountered during
implementation; framing names likely surface candidates (§3.6
below) without authoring them.

### 3.5 Member 10 inherits as discipline (imports-land-when-used)

PR 10 close §1.7 promoted member 10 to numbered class status:

> **Imports land when first used. Reserved imports for
> hypothetical future cases are rejected at the spec layer,
> matching the compare-as-persisted discipline applied at the
> import-set surface.**

PR 11 inherits the discipline operationally. Specifically:

- PR 11 test module(s) import only what their tests USE. No
  speculative-reserved imports.
- PR 11 spec final-state imports inventory must NOT list any
  symbol unused by the named tests.
- If a PR 11 test surfaces a need for an import mid-
  implementation, the import lands at the same commit as the
  test that uses it (or as a small Step N.5 surgical
  amendment if the import is small + the timing aligns).

The discipline applies regardless of which PR 11 test files
ship.

### 3.6 Cleanup-pressure forms PR 11 may encounter

Gate 3 framing §4.2 enumerated seven canonical pressure
forms. PR 11 expects to encounter four most directly under
recomposition pressure:

- **Form 1 (helper merger).** *"Just extract the readback +
  comparator invocation into a shared helper."* Mechanism: a
  PR 11 test helper that absorbs the arc traversal. Rejected
  per §5.3 + §5.6.
- **Form 5 (premature surface normalization).** *"Just sort
  the observation record's `narrower.decision` before passing
  to compare_records to make the assertion stable."*
  Mechanism: pre-comparison normalization at the test surface
  that defeats `compare_records`'s "compare as persisted"
  commitment. Rejected per PR 10 spec §4.2 commitment + PR 11
  §5.6.
- **Form 6 (speculative fixture-semantics widening).** *"Add
  a fixture for partial-match divergence to broaden coverage."*
  Mechanism: PR 11 framing-time fixture additions. Rejected
  per PR 9 close §2.4 (PR 9 fixtures are stable archaeology;
  PR 10+ fixtures require explicit framing-level justification
  + Gate 4 comparator dependency).
- **Form (new candidate — recomposition smoothing).** *"The
  test traversal is awkward — let's add a production helper
  to make recomposition cleaner."* Mechanism: production
  abstraction surfaces whose primary purpose is recomposition
  ergonomics. **Rejected per §5.3 + §5.6 — PR 11's signature
  guardrail.** This form may not be among Gate 3 framing's
  enumerated seven; if surfaced + rejected during PR 11, it
  registers at PR 11 close as candidate cleanup-pressure-
  resistance class member 11+ for evaluation.

Forms 2 (schema merger), 3 (persistence creep), 4 (inline
emission), 7 (walker abstraction) may surface secondarily.
The discipline at PR 11: when a pressure form surfaces,
reject inline at the rejection site + register at PR 11 close
as either operational corroboration of existing protection or
candidate class member 11+ (if structurally distinct from
existing forms + class members).

### 3.7 Four-variant amendment-at-incarnation taxonomy

Available to PR 11 implementation without re-framing. The
grounding-time variant (2-instance corroborated per PR 10
close §5.1) is most likely to surface at PR 11 — the
recomposition arc may surface empirical misalignment between
spec-extrapolated record shape and the actual persisted JSONL
shape from `chat_handler` arbitration. Implementations should
*expect* grounding-time amendments and register them per the
canonicalized discipline (separate NO-code amendment commit
per user direction at amendment convergence).

The PR 10 §4.4 amendment's "earlier catch" set the bar at
Step 1 prep (read-before-implement). PR 11 framing/spec
drafting should READ:

- `forge_bridge/corpus/_seed.py::drive_seed_fixture` body to
  ground orchestration shape.
- `forge_bridge/console/handlers.py::chat_handler` to ground
  arbitration shape.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture`
  to ground observation record shape.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` to
  ground expectation record shape.
- `forge_bridge/corpus/reader.py` to ground readback shape.
- `tests/corpus/test_pr9_fixture_integration.py` for the
  inherited test infrastructure pattern.

…BEFORE drafting any PR 11 spec section that asserts shape of
these surfaces. Inference is the same archaeology-grade
hazard as inferred counts (per
`feedback_ground_specs_in_actual_files`).

### 3.8 Step N.5 surgical cadence

3-times corroborated at Gate 2 close (PR 8 Step 4.5 + PR 9
Step 2.5 + PR 9 Step 5.5). PR 10 added zero corroborations.
The pattern is available to PR 11 without re-framing.
PR 11 may contribute additional corroboration instances if
mid-flight guidance surfaces an additive improvement to a
recently-shipped deliverable.

### 3.9 §5.3 candidate methodology observation — framing-time pressure prediction through absence

PR 10 close §5.3 registered as first-corroborated-instance
candidate methodology. PR 11 framing's §3.6 cleanup-pressure-
form enumeration creates a second opportunity. The two
possible outcomes are **not equally weighted as evidence**:

- **Absence strengthens candidacy.** If PR 11 implementation
  does NOT surface any of the four predicted forms (1 / 5 / 6
  / recomposition smoothing), the absence-as-load-bearing
  observation gains its second independent corroborating
  instance. This is the **stronger evidentiary outcome** — it
  is the framing's prediction operating as cause rather than
  coincidence.
- **Rejection preserves first-instance candidacy.** If PR 11
  surfaces + rejects pressure forms explicitly, the observation
  does not gain a second instance — but it does NOT lose its
  first-instance candidacy either. The candidate observation
  preserves at first-instance status pending further
  corroboration from Gate 4 or future-gate scope.

The asymmetry matters: corroborated absence is stronger
evidence for promotion than rejected-instance archaeology.
Both outcomes are reportable; only the absence outcome
materially advances the candidacy. PR 11 close registers the
actual outcome; Gate 3 close performs the methodology-
promotion evaluation against the weighted evidence.

---

## 4. Architectural delta from PR 11

### 4.1 PR 11 integration test module

New test module: `tests/corpus/test_pr11_recomposition_arc.py`
(exact name = PR 11 spec).

**Module structure:**

- **Module docstring** carries (relevance-by-file ordering):
  1. Gate-3-LOCAL governing sentence with *candidate carrier
     #16 corroboration substrate* marking.
  2. PR-11-LOCAL binding statement (§5.6 — traverses-not-
     erases-seams).
  3. The traversal trace (§2 verbatim) as architectural-test-
     posture documentation.
  4. Inherited carriers #1–#15 + #17 + Gate 2 binding
     clarification cited by reference per PR 9 + PR 10
     abbreviation discipline (this module is two layers
     removed from production authority emission).
- **Imports:** `__future__` annotations, stdlib (`pathlib`,
  `json`, others as tests USE), test infrastructure
  (`_read_records` pattern, `_apply_pr9_patches` pattern from
  PR 9), production targets (`compare_records`,
  `drive_seed_fixture`, fixture FIXTURE dicts), monkeypatch
  factories per PR 9's strategy. Member 10 discipline:
  imports land when first used.
- **Integration test infrastructure reuse:** PR 9 close §2.2
  named the inherited infrastructure (`_apply_pr9_patches`,
  `_PR9_REACHABLE_TOOLS`, `_read_records`, `_make_patched_invoke`).
  PR 11 should evaluate at spec time whether to:
  - Import from PR 9 module (preferred — exercises the
    test-surface inheritance discipline).
  - Re-author scope-local copies (acceptable if scope
    divergence justifies; framing leans against).
  Spec decides; framing's default lean: **import from PR 9**
  to demonstrate test-infrastructure-as-stable-consumption-
  surface.

**Body shape — one test function per fixture-driven traversal:**

Each test invokes the full arc explicitly. No helper absorbs
the traversal. Assertion contract verifies:

- The expectation record persisted (per PR 8's emission).
- The observation record persisted (per PR 7's emission +
  PR 9's arbitration grounding).
- The reader returns both records.
- `compare_records` returns the expected `DivergenceReport`
  shape for the fixture's authored/observed divergence
  status.

### 4.2 Test count target — 3 to 5 new tests at PR 11

Framing-time estimate (exact count = PR 11 spec):

| Test category | Estimated count |
|---|---|
| Recomposition arc per fixture (one per PR 9 fixture) | 3 |
| Boundary/error path traversal (optional) | 0–2 |

**Total PR 11 framing target: 3–5 new tests.**

**Cumulative test count anchor at PR 11 close target: 217–219
forge env corpus tests** (214 PR 10 baseline + 3–5 PR 11).
Exact count locked at PR 11 spec and verified at PR 11 close.

Per `feedback_counts_are_archaeology_grade`, count
inconsistencies are rejected at PR 11 spec review. If the spec
lands at 2 or 6+ tests, the spec author must amend the
framing-time estimate range with archaeology.

### 4.3 No production source modifications

Per §2.3 + §5.2. PR 11 ships ZERO modifications to production
source files. The recomposition arc traverses existing
surfaces without modifying any of them.

If implementation surfaces a genuine production need, the spec
amends explicitly + justifies. Framing default: no production
modifications required.

### 4.4 No new test-infrastructure abstractions whose primary purpose is recomposition

Per §2.1 + §5.3. PR 11 test infrastructure inherits from PR 9
(via import or scope-local copy per spec decision); PR 11 does
NOT introduce new test-infrastructure abstractions whose
primary purpose is "making the recomposition arc cleaner."

Acceptable: small per-test helpers that improve clarity at a
single test surface without absorbing the traversal (e.g., a
fixture-id-to-expected-divergence-shape lookup).

Rejected: helpers that wrap the full arc into a single call.

The discipline boundary at PR 11 spec review: any new helper
must justify on grounds OTHER than "making recomposition
cleaner." Reasonable justifications include: type narrowing,
assertion ergonomics at a single surface, monkeypatch factory
parameterization. Unreasonable justifications: "the test
became repetitive when I copy-pasted the arc."

### 4.5 DivergenceReport assertion ergonomics

PR 10 close §2.1 established the comparator's surface as a
stable consumption interface. PR 11 tests assert against
`DivergenceReport` field-by-field for assertion ergonomics —
the report's nested dict shape is structurally visible to
callers.

Assertion examples (PR 11 spec finalizes):

```python
# Single-survivor fixture: no divergence expected.
report = compare_records(observation, expectation)
assert report["divergence"]["narrow_diverged"] is False
assert report["expectation"]["expected_narrow"] == ["forge_ping"]
assert report["observation"]["observed_narrow"] == ["forge_ping"]

# No-keyword-match fixture: authored/observed divergence expected.
report = compare_records(observation, expectation)
assert report["divergence"]["narrow_diverged"] is True
assert report["expectation"]["expected_narrow"] == []
assert len(report["observation"]["observed_narrow"]) == 4  # full reachable set
```

The assertions verify carrier #17 operationally: each surface's
contribution remains structurally identifiable through the
`DivergenceReport`'s per-surface partitioning.

---

## 5. Binding decisions

### 5.1 PR 11 scope locked: end-to-end recomposition through real `chat_handler` arbitration

Per §2 reasoning + Q-A convergence decision. PR 11 traverses
the full decomposition seam path:

```
fixture → drive_seed_fixture → chat_handler → emit_divergence_capture
+ emit_seed_expectation → JSONL → reader → compare_records → DivergenceReport
```

**Alternatives explicitly rejected at framing:**

- **Reader-comparator only** (narrower scope without
  `chat_handler` invocation) — rejected because PR 9 Step 3
  already verified the chat_handler path produces records;
  PR 11's value is the recomposition demonstration, not the
  arbitration verification (which is PR 9 archaeology).
- **Comparator + new fixture cases** (extend PR 9 corpus) —
  rejected because PR 9 fixtures are stable archaeology per
  PR 9 close §2.1; fixture additions require explicit Gate 4
  comparator dependency justification (PR 10 framing §2 +
  PR 10 framing §7 item 6).
- **Comparator + synthetic records constructed in tests**
  (bypass fixture + chat_handler path) — rejected because it
  defeats the recomposition demonstration; synthetic records
  do not traverse the seams.

### 5.2 0 production source modifications — named architectural sufficiency signal

Per §2.3. PR 11 ships **0 production source modifications**.

This decision elevates the architectural-success-signal
continuity from "clean diff hygiene" (PR 10 framing §2.3 +
PR 10 spec §1) to **named architectural sufficiency signal**:

> **PR 11 demonstrates the Gate 2 + Gate 3 decomposition
> strategy was sufficient — the recomposition arc traverses
> every seam without requiring extension, relaxation, or
> modification of any production source surface.**

The signal travels at:

- PR 11 test module docstring.
- PR 11 commit message bodies under "architectural
  sufficiency signal" section.
- PR 11 close §6 (same-commit-as-Gate-3-close per §11) as
  durable archaeology.
- Gate 3 close §1 or §2 as gate-arc validation evidence.

**If a genuine production need surfaces at PR 11
implementation,** framing default does NOT bind blindly:

- The framing-time prediction is goal-zero.
- A justified deviation at PR 11 spec or implementation must
  name + justify the modification explicitly.
- An unjustified deviation is rejected at spec review or
  three-round implementation review.
- The deviation registers at PR 11 close as part of the
  architectural archaeology (validation strength reduced from
  "0 mods" to "0 mods plus N justified additions"; both are
  reportable).

### 5.3 No production abstraction whose primary purpose is "making recomposition cleaner"

Per §2.1 + §2.2. PR 11 must NOT introduce any production
abstraction whose primary purpose is to make the
recomposition arc cleaner. Specifically:

- **No fixture-to-DivergenceReport orchestrator** in
  production code (production helper that drives fixture +
  reads + compares).
- **No reader-side `read_pair_by_fixture_id`** in production
  code (helper that joins observation + expectation records).
- **No comparator-side batch variant** in production code
  (PR 12 conditional pending join-boilerplate evaluation; not
  PR 11 scope).
- **No `drive_seed_fixture` return-shape change** that
  packages records for the comparator (orchestrator's job is
  orchestration; pair-input shape is the comparator's
  contract per PR 10 §5.2).

**Acceptable test-surface helpers:** small per-test helpers
that improve clarity without absorbing the traversal (see
§4.4).

**Discipline statement at spec review:** any new helper or
abstraction proposed during PR 11 implementation must justify
on grounds OTHER than "making recomposition cleaner."
"Recomposition is awkward" is acceptable evidence that the
decomposition boundaries held (§5.6 PR-11-LOCAL); it is NOT
justification for production abstraction.

### 5.4 Test count target: 3 to 5 new tests at PR 11

Per §4.2. Framing-time estimate (exact count = PR 11 spec):
3 base recomposition tests + 0–2 boundary/error-path tests.
Total PR 11 framing target: **3–5 new tests.**

Cumulative test count anchor: **217–219 forge env corpus
tests at PR 11 close target** (214 PR 10 baseline + 3–5
PR 11).

### 5.5 PR 12 trigger criterion preserved as conditional

Per Q-B convergence decision + PR 10 framing §2.1 + PR 10
close §3.1. PR 12 is conditional within Gate 3 per Gate 3
framing §10. PR 11 framing **restates the trigger criterion**
+ defers evaluation to PR 11 close.

**Trigger criterion (binding):**

> **PR 12 (conditional join helper) triggers if join
> boilerplate repeats at ≥4 call sites AND if preserving
> decomposition (i.e., requiring callers to perform the join
> explicitly) becomes harder to defend than abstracting it.**

The sharpened wording (per user direction at convergence
pass): the trigger is **NOT** "join boilerplate exists" (a
single occurrence is the natural shape per PR 10 framing §2.1
+ §5.2 pair-input lock). The trigger is **operational
repetition forcing generalization** — when the boilerplate's
proliferation becomes evidence that the decomposition's
caller-handles-join discipline is no longer defensible.

PR 11 contributes the **first batch of operational call
sites**. PR 11 close evaluates:

- How many distinct call sites perform the join (each PR 11
  test counts as 1; future Gate 4 + future-gate work
  contributes additional sites).
- Whether the boilerplate at PR 11 call sites is
  **acceptable evidence the decomposition held** (per §5.6
  PR-11-LOCAL: call-site awkwardness is acceptable) OR
  **mounting evidence that the decomposition's caller-
  handles-join discipline is no longer defensible** (the
  trigger condition).

**Evaluation discipline at PR 11 close:**

The evaluation is **qualitative judgment**, not mechanical
count. ≥4 call sites is a NECESSARY condition (per PR 10
framing §2.1); it is NOT a SUFFICIENT condition. The
sufficient condition requires affirming the second clause:
preserving decomposition becomes harder than abstracting it.

If PR 11 ships 3 recomposition tests + Gate 4 framing
projects ~2–3 additional call sites, the ≥4 condition is in
reach but not yet decisive. PR 12 disposition at PR 11 close
may be:

- **Promote** (conditions met decisively) — PR 12 joins
  Gate 3 deliverable sequence.
- **Defer** (conditions not yet met) — PR 12 stays conditional
  pending Gate 4 framing's projection of additional join
  sites.
- **Reject** (conditions structurally unlikely to be met) —
  PR 12 graduates from conditional to rejected; Gate 3
  closes at PR 11 final commit without PR 12.

Framing default lean: **defer** — PR 11 contributes too few
call sites for decisive evaluation, but the criterion remains
operationally available.

### 5.6 PR-11-LOCAL binding statement — recomposition traverses, does not erase, decomposition seams

> **PR 11 traverses the decomposition seams established by
> Gate 2 + Gate 3 substrate work without erasing them.
> Call-site awkwardness during recomposition is acceptable
> evidence that the decomposition boundaries held; introducing
> production abstractions whose primary purpose is "making
> recomposition cleaner" is rejected at the spec layer.**

This is the operational discipline statement governing PR 11
implementation. Structurally parallel to PR-7-LOCAL pairs
(scope-local to `_capture.py` + `reader.py`), PR-8-LOCAL
binding statements (scope-local to `_seed.py`), PR-9 fixture-
data discipline (scope-local to fixtures), and PR-10-LOCAL
(read-only mutability; scope-local to `_compare.py`).

**Operational placement of PR-11-LOCAL:**

- PR 11 integration test module docstring (verbatim).
- PR 11 commit message bodies under "preserved invariants."
- At PR 11 close + Gate 3 close convergence commit, the
  PR-11-LOCAL statement registers as PR 11's
  recomposition-discipline archaeology.

PR-11-LOCAL does NOT regenerate beyond PR 11 scope. PR 12 (if
promoted) / Gate 4 / future-gate work does not inherit
PR-11-LOCAL; new PR-N-LOCAL statements may be authored at
their own framing level per the canonicalized pattern.

### 5.7 No public-API change at PR 11

`forge_bridge.__all__` stays at 19 symbols. Comparator surface
(`compare_records`, `DivergenceReport`, `ComparatorInputError`)
remains corpus-internal per PR 10 spec §5.7. If a concrete
external consumer surfaces during Gate 4 or future-gate work,
promotion to `__all__` is a framing-level decision at that
point (per PR 8 framing §5.6 Q5 + PR 9 framing §5.6 Q6 +
PR 10 framing §5.7 pattern).

---

## 6. Constructs intentionally resistant to cleanup pressure

The 10 inherited cleanup-pressure-resistance class members
(PR 10 close §1.7) preserve unchanged. PR 11 framing does
**NOT speculatively author new members** at framing time.

### 6.1 Likely surface candidates during PR 11 implementation

Per §3.6, the four PR 11-relevant cleanup pressure forms
(helper merger / premature surface normalization / speculative
fixture-semantics widening / recomposition smoothing) are
most likely to surface. The protections already operational
at PR 11 entry:

- Member 10 (imports-land-when-used) protects against
  speculative test-module imports.
- PR-11-LOCAL §5.6 protects against recomposition-smoothing
  abstractions.
- §5.2 0-prod-mod target + §5.3 no-abstraction lock protect
  against production abstraction additions.
- PR 10 spec §4.2 binding behavioral commitment ("compare as
  persisted") protects against premature surface normalization
  at the test surface.
- PR 9 close §2.1 (PR 9 fixtures are stable archaeology)
  protects against speculative fixture-semantics widening.

### 6.2 Discipline at PR 11 implementation

**If a cleanup pressure form surfaces:**

1. **Reject inline** at the rejection site (commit body or
   in-flight discussion).
2. **Cite the protection** that rejects it (member 10,
   PR-11-LOCAL §5.6, §5.2/§5.3, PR 10 spec §4.2, or PR 9
   close §2.1).
3. **Register at PR 11 close** as either:
   - Operational corroboration of an existing class member
     (no new member; the existing member proved load-bearing
     under this specific pressure).
   - A new candidate class member 11+ (only if the pressure
     form is structurally distinct from the 7 enumerated
     forms + the existing 10 class members; cluster
     "promotion-from-precursor" archaeology with the new
     member's per-PR close protection summary).

### 6.3 Speculative authoring rejected

Per Gate 3 framing §7 item 13 + PR 10 framing §6.3. **Framing
does not author new class members at framing time** even
when likely surface candidates can be predicted. The
discipline gate:

- Predicted pressure ≠ encountered pressure. The predictive
  enumeration (§3.6 + §6.1) is operational arming, not
  authorial proof.
- New members register at PR 11 close based on archaeological
  evidence (the specific commit / discussion / line of code
  where the pressure surfaced + the specific protection that
  rejected it).
- Promotion of any new class member to gate-level inventory
  happens at **Gate 3 close** (same-commit as PR 11 close per
  §11), reading the cumulative PR 10 + PR 11 evidence.

### 6.4 §5.3 candidate methodology observation evaluation at PR 11 close

PR 10 close §5.3 registered "framing-time pressure prediction
load-bearing through absence" as candidate methodology
observation requiring an independent corroborating instance.
PR 11 framing's §3.6 + §6.1 enumeration creates the second
opportunity, but the two outcomes are **not symmetric as
evidence** (per §3.9):

- **Absence outcome — strengthens candidacy.** If PR 11
  implementation does NOT surface any of the four predicted
  forms (1 / 5 / 6 / recomposition smoothing), the absence-
  as-load-bearing observation gains its second independent
  corroborating instance. This is the stronger evidentiary
  outcome: framing-time prediction operating as cause rather
  than coincidence.
- **Rejection outcome — preserves first-instance candidacy.**
  If PR 11 surfaces + rejects pressure forms inline, the
  observation does not gain a second instance. The first-
  instance candidacy is not invalidated, but it does not
  advance; promotion remains pending Gate 4 or future-gate
  corroboration.

PR 11 close registers the actual outcome with the asymmetric
weighting preserved. Gate 3 close (same commit) performs the
methodology-promotion evaluation reading the weighted
evidence — absence carries more weight than rejection-without-
falsification.

---

## 7. Non-acquisition commitments

PR 11 explicitly does **NOT**:

1. **Modify any production source file.** Per §5.2 architectural
   sufficiency signal target. Justified deviations register
   as archaeology, not silent additions.
2. **Add a production abstraction whose primary purpose is
   "making recomposition cleaner."** Per §5.3 + §5.6
   PR-11-LOCAL.
3. **Add a fixture-to-DivergenceReport orchestrator helper**
   anywhere (production or test). Per §5.3.
4. **Add a reader-side fixture-id-join helper** in production
   code. Per §5.3 (PR 12 conditional pending).
5. **Modify the PR 9 three-fixture corpus.** Per Gate 3
   framing §7 item 4 + PR 9 close §2.1.
6. **Add new fixtures.** Per PR 9 close §2.1 — fixture
   additions require explicit Gate 4 comparator dependency
   justification.
7. **Modify the three-authority-surface partition.** Per Gate 3
   framing §7 item 5.
8. **Modify the PR-8-INTERNAL three-way authority partition**
   (write-side). Per PR 10 close §3.2.
9. **Modify the PR 10 read-side structural parallel** in a way
   that elevates it to peer-class governance. Per PR 10 close
   §1.6 — promotion to peer-class is a future-framing
   decision, not a PR 11 implementation decision.
10. **Touch the Layer 3 lint** (`test_pr6_visual_asymmetry.py`).
    PR 11 introduces no new `emit_divergence_capture` call
    sites; lint's discovery walk input set unchanged.
11. **Modify the comparator helper** (`_compare.py`). PR 10
    close §2.1 — modification requires framing-level review.
12. **Modify the four Layer 2 walkers.** Per PR 10 close §2.2
    + PR 11 §3.3.
13. **Modify `divergence_capture_enabled()` or its env-gate.**
    Carrier #5 protection preserves.
14. **Extend `KNOWN_SOURCE_VALUES`.** Per Gate 3 framing §7
    item 9.
15. **Extend `_KNOWN_RECORD_KINDS`.** Two-element set locked
    per PR 7 spec §7 close conditions.
16. **Modify the expectation record schema.** Three required
    keys (`fixture_id`, `prompt`, `expected_narrow`) locked.
17. **Modify `forge_bridge.__all__`.** Stays at 19 symbols
    (§5.7).
18. **Author new cleanup-pressure-resistance class members
    speculatively.** Per §6.
19. **Promote candidate carrier #16 to active.** Promotion
    gated on Gate 3 close evaluation (same-commit as PR 11
    close). PR 11 contributes Gate-3-LOCAL form travel as
    corroboration substrate but does NOT promote at PR 11
    close itself.
20. **Pre-empt Gate 3 close's gate-arc synthesis.** PR 11
    close ships at the same commit as Gate 3 close per §11;
    PR 11 close owns PR 11-scoped archaeology only. Gate-arc
    synthesis, candidate carrier #16 promotion evaluation,
    conditional PR 12 disposition, and the gate-level
    inheritance contract toward Gate 4 live at Gate 3 close.
21. **Pre-determine PR 12 disposition at framing.** Per §5.5.
    Disposition is a PR 11 close evaluation against the
    sharpened qualitative trigger criterion (≥4 call sites
    AND preserving decomposition becomes harder than
    abstracting it).
22. **Use cross-surface vocabulary in field names or
    docstrings.** Per Gate 3 framing §5.6 + PR 10 framing
    §3.5. The proactive scope guardrail applies at PR 11
    surfaces; no `task_outcome` / `prompt_resolution` field
    names; no smuggling of cross-surface semantics into PR 11
    archaeology.
23. **Speculative-reserve imports in PR 11 test modules.** Per
    member 10 protection. Imports land when first used.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST`: no extension required

Per PR 10 §4.4 amendment + spec amendment archaeology: the
`_ALLOWLIST` is for files **outside** the corpus subtree that
need to import **from** the corpus.

PR 11 test module(s) ship under `tests/corpus/` which is NOT
inside the corpus subtree (which is `forge_bridge/corpus/`).
The PR 3 discipline's `_ALLOWLIST` check applies to files in
the broader codebase that import `from forge_bridge.corpus`;
`tests/corpus/` files are NOT subject to the discipline check
in the same way (per the existing `test_pr3_discipline.py`
implementation pattern + PR 4–PR 9 test module precedent).

**Verification step at PR 11 implementation prep:** READ
`tests/corpus/test_pr3_discipline.py` to confirm the
discipline's actual semantics applied to PR 11 test module
placement (`feedback_ground_specs_in_actual_files`). Framing
expectation: no allowlist modification needed; spec confirms
at drafting.

### 8.2 Layer 2 — four-walker partition preserves unchanged

Per §3.3. PR 11 adds no fifth walker. The four existing
walkers (PR 4 + PR 8 + PR 9 + PR 10) continue to enforce
their respective ontologies; PR 11 test additions are
target-disjoint for all four:

- PR 4 walker target: narrowing-subsystem production sources.
  PR 11 modifies none.
- PR 8 walker target: `_seed.py`. PR 11 modifies none.
- PR 9 walker target: `tests/corpus/fixtures/*.py`. PR 11
  adds no fixtures.
- PR 10 walker target: `_compare.py`. PR 11 modifies none.

Step 5 verification at PR 11 close confirms all four walkers
pass unchanged.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 11.
Properties A–D govern `emit_divergence_capture` call sites;
PR 11 introduces no new call sites. The lint's discovery walk
input set unchanged.

---

## 9. Phase-end conditions for PR 11

PR 11 closes when:

1. **The recomposition arc operates end-to-end.** Each PR 9
   fixture drives through the full seam traversal (fixture →
   `drive_seed_fixture` → `chat_handler` → emission → JSONL →
   reader → `compare_records` → `DivergenceReport`) and
   returns the expected divergence shape for the fixture's
   authored/observed outcome.

2. **The full seam traversal is visible at the test surface.**
   No PR 11 test absorbs the traversal into a single
   convenience call; each test explicitly visits each seam.

3. **0 production source modifications.** Per §5.2
   architectural sufficiency signal target. Verified via
   `git diff --stat <pre-PR-11-base>..HEAD -- forge_bridge/`
   at Step N final verification.

4. **No production abstraction whose primary purpose is
   "making recomposition cleaner"** has been introduced. Per
   §5.3 + §5.6 PR-11-LOCAL.

5. **Layer 1 allowlist** verified unchanged (per §8.1).

6. **Four Layer 2 walkers** pass unchanged (per §8.2).

7. **Layer 3 lint** passes unchanged (per §8.3).

8. **Carrier #17 holds operationally** through the recomposition
   arc — the `DivergenceReport` returned by each PR 11 test
   preserves each authority surface's contribution
   identifiably.

9. **Gate-3-LOCAL governing sentence travels verbatim** through
   ≥1 PR 11 surface (PR 11 test module docstring + ≥1 PR 11
   commit message body). PR 11 contributes the ≥1 surface
   completing the ≥4 total Gate 3 close evaluates.

10. **16 active carriers + candidate #16 + Gate-3-LOCAL form +
    PR-11-LOCAL binding statement** all travel verbatim into
    PR 11 test module docstring per relevance-by-file
    ordering.

11. **PR-11-LOCAL binding statement** (§5.6) lives in PR 11
    test module docstring + PR 11 commit message bodies.
    Does NOT regenerate beyond PR 11.

12. **Test count locks at PR 11 close target** (217–219 forge
    env corpus tests; exact count = PR 11 spec; verify at
    PR 11 close).

13. **PR 11 close artifact (`A.5.3.2-PR11-CLOSE.md`) AND Gate 3
    close artifact (`A.5.3.2-GATE-3-CLOSE.md`) BOTH ship at
    the PR 11 final commit** per Gate 3 framing §11.

14. **`forge_bridge.__all__`** stays at 19 symbols.

15. **Three-authority-surface partition + PR-8-INTERNAL three-
    way authority partition + 10-member cleanup-pressure-
    resistance class** all preserve unchanged.

16. **Four-walker Layer 2 partition** preserves unchanged
    (parallel-not-extension boundary; shared AST mechanics do
    not imply shared ontology).

17. **Any new cleanup-pressure-resistance class members
    surfaced during PR 11** register at PR 11 close with
    explicit protection language + operational enforcement
    placement (§6.2).

18. **§5.3 candidate methodology observation evaluation
    registered** at PR 11 close per §6.4 (absence corroborates
    or rejection-without-falsification preserves first-
    instance candidacy).

19. **PR 12 disposition evaluated** at PR 11 close per §5.5
    qualitative trigger criterion (promote / defer / reject).

---

## 10. Cross-references

- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — **immediate predecessor;
  durable archival state PR 11 inherits.** §1 PR 10
  established (4 architectural signals; member 10 promotion;
  test count anchor; four-walker partition); §2 PR 11 / Gate 3
  inheritance contract; §3 what PR 11 / Gate 3 changes; §7
  reseed protocol.
- `A.5.3.2-PR10-FRAMING.md` (`8ad7fe9`) — carrier #17
  operational landing posture; pair-input lock; framing-time
  cleanup-pressure-form enumeration PR 11's §3.6 mirrors at
  PR 11 scope.
- `A.5.3.2-PR10-SPEC.md` (`54d0ab9` + amendment `6830888`) —
  §4.1.6 reference implementation PR 11 consumes; §4.2 binding
  behavioral commitment ("compare as persisted") PR 11 tests
  must not defeat at the test surface; §4.4 amendment
  archaeology (sharpened Layer 1 semantics).
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — gate-level
  inheritance contract; §6.1 promotion-evaluation criteria
  for candidate carrier #16 (PR 11 contributes the remaining
  ≥1 surface); §10 PR sequencing (PR 11 is second; PR 12
  conditional); §11 Gate 3 close criteria — Gate 3 close
  ships at PR 11 final commit.
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus
  PR 11 drives; §1.1 fixture corpus + grounding traces; §2.1
  fixtures are stable archaeology; §2.2 PR 9 integration test
  infrastructure (`_apply_pr9_patches`, `_PR9_REACHABLE_TOOLS`,
  `_read_records`, `_make_patched_invoke`) PR 11 reuses.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis
  PR 11 close + Gate 3 close convergence pre-empts at gate
  scope; §2.1 Gate 4 comparator's two foundational dependencies
  (record_kind partition + fixture_id joinability) PR 11
  exercises operationally end-to-end.
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface PR 11 traverses; `emit_seed_expectation` +
  `drive_seed_fixture` + schema validator inherited unchanged.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces PR 11 traverses;
  `emit_divergence_capture` + contextvar resolution +
  `seed_dispatch_scope` + `_DispatchContext` inherited
  unchanged.
- `forge_bridge/corpus/_compare.py::compare_records` — PR 10
  interpretive-read surface; PR 11 invokes at the final step
  of each test traversal.
- `forge_bridge/corpus/_seed.py::drive_seed_fixture` — PR 8
  orchestration entry point; PR 11 invokes at the start of
  each test traversal.
- `forge_bridge/console/handlers.py::chat_handler` — production
  arbitration surface PR 11 drives (PR 9 patches reachable-tool
  set; PR 11 inherits the patching strategy).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper invoked transitively through chat_handler.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` —
  expectation helper invoked transitively through
  `drive_seed_fixture`.
- `forge_bridge/corpus/reader.py` — readback surface; PR 11
  tests invoke via inherited `_read_records` helper pattern
  from PR 9.
- `tests/corpus/fixtures/fix_single_survivor.py` — PR 9
  fixture; PR 11 test 1 drives.
- `tests/corpus/fixtures/fix_multi_match.py` — PR 9 fixture;
  PR 11 test 2 drives.
- `tests/corpus/fixtures/fix_no_keyword_match.py` — PR 9
  fixture; PR 11 test 3 drives.
- `tests/corpus/test_pr9_fixture_integration.py` — PR 9
  integration test infrastructure (`_apply_pr9_patches`,
  `_PR9_REACHABLE_TOOLS`, `_read_records`,
  `_make_patched_invoke`); PR 11 spec decides import vs.
  scope-local copy.
- `tests/corpus/test_pr11_recomposition_arc.py` (planned,
  PR 11) — PR 11 integration test module.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer 1;
  preserves unchanged at PR 11.
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2
  (PR 4 walker); preserves unchanged.
- `tests/corpus/test_pr8_seed_surface.py` — Layer 2 (PR 8
  walker); preserves unchanged.
- `tests/corpus/test_pr9_fixture_discipline.py` — Layer 2
  (PR 9 walker); preserves unchanged.
- `tests/corpus/test_pr10_comparator_discipline.py` — Layer 2
  (PR 10 walker); preserves unchanged.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 lint;
  preserves unchanged.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; PR 11 contributes:
  - Recomposition-through-existing-seams as governing framing
    posture (new; candidate methodology pending corroboration).
  - 0-production-mods elevated to named architectural
    sufficiency signal (new; candidate methodology pending
    corroboration).
  - PR 10 §5.3 candidate methodology observation second-
    instance evaluation (absence corroborates OR rejection-
    without-falsification preserves first-instance candidacy).
  - Cleanup-pressure-resistance class fifth-PR populating if
    new member surfaces; class promotion strengthened
    regardless.
  - Gate-3-LOCAL governing sentence ≥1 PR 11 surface (≥4 total
    for Gate 3 close candidate-carrier-#16 promotion
    evaluation).
- `A.5.3.2-PR11-SPEC.md` (planned next) — derives file-level
  precision from this framing's locked decisions: exact PR 11
  test module name + path, exact import set, exact test names
  + assertion contracts, atomic step boundaries, verification
  checklist.
- `A.5.3.2-PR11-CLOSE.md` (planned at PR 11 final commit) —
  durable PR 11 archival state; same-commit convergence with
  Gate 3 close.
- `A.5.3.2-GATE-3-CLOSE.md` (planned at PR 11 final commit) —
  gate-arc synthesis across PR 10 + PR 11; candidate carrier
  #16 promotion evaluation; conditional PR 12 disposition;
  gate-level inheritance contract toward Gate 4.

---

## 11. Same-commit convergence — PR 11 close + Gate 3 close

Per Gate 3 framing §11: **Gate 3 close ships at PR 11 final
commit.** PR 11 close artifact + Gate 3 close artifact land at
the same commit as two distinct deliverables with explicit
responsibility split:

**PR 11 close owns:**

- PR 11 implementation arc archaeology (commits chain table).
- §5.3 candidate methodology observation evaluation (absence
  vs. rejection outcome at PR 11 scope).
- §5.6 PR-11-LOCAL traverses-not-erases-seams discipline
  archaeology.
- Recomposition-through-existing-seams operational
  archaeology.
- Architectural sufficiency signal (0-prod-mod) validation
  evidence.
- PR 11-scoped cleanup-pressure-form encounters + protection
  registrations.

**Gate 3 close owns:**

- Gate-arc synthesis across PR 10 + PR 11.
- Complete 4-variant amendment-at-incarnation taxonomy with
  PR-of-origin noted per variant (final cross-PR inventory).
- Cleanup-pressure-resistance class final inventory at Gate 3
  scope (10 members + any PR 11 additions).
- Candidate carrier #16 promotion evaluation against the ≥4-
  surface evidence base.
- Conditional PR 12 disposition (promote / defer / reject)
  per §5.5 qualitative trigger criterion.
- Recomposition-through-existing-seams promotion candidacy
  (PR 11 first instance; second instance pending Gate 4 or
  future-gate scope).
- 0-prod-mod-as-architectural-sufficiency-signal promotion
  candidacy (PR 11 first instance; second instance pending
  Gate 4 or future-gate scope).
- §5.3 candidate methodology observation gate-level
  promotion evaluation.
- Gate-level inheritance contract toward Gate 4.
- The four §7.3 ontological questions handoff (per Gate 2
  close §7.3 + Gate 3 framing inheritance).

Where overlap surfaces, PR 11 close defers to Gate 3 close.

---

PR 11 framing locks here. PR 11 spec drafts at the next
session boundary; PR 11 implementation derives from that spec
per the Gate 2 + Gate 3 cadence (framing → spec → spec-
amendments-at-incarnation → steps → verification-amendments-
if-surfaced → close).

PR 11 + Gate 3 close together close the Gate 3 arc — Gate 3
recomposition completes; Gate 4 inherits the validated
substrate + the verified comparator + the corroborated
recomposition demonstration.
