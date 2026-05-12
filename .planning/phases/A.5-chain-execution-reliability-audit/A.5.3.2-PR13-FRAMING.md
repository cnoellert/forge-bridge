# A.5.3.2 PR 13 — Framing (ordering divergence as Gate 4 calibration exercise)

**Status:** PR 13 opens at `fbf2285` (local main, Gate 4
framing landed). This framing locks the architectural posture
for the ordering-divergence exercise — Gate 4's first
primary PR + the calibration substrate for Placement A +
Placement B operational corroboration — and the binding
decisions reached during the Gate 4 framing → PR 13 framing
convergence pass.

PR 13 is the first of three primary PRs sequenced within
Gate 4 per Gate 4 framing §10. The three-PR slot structure
(PR 13 ordering → PR 14 partial-narrow → PR 15 multi-survivor
mismatch) is locked at Gate 4 framing §5.5; PR 13 framing
operates against the locked sequence + ordering.

The convergence pass produced four binding decisions: PR 13
ships exactly one new fixture (filename
`fix_ordering_divergence.py`; `fixture_id` field
`fix-pr13-ordering-divergence`; module export `FIXTURE` per
PR 9 canonical convention) + exactly one new test
(`test_recomposition_arc_ordering_divergence`) — single-
vector, single-direction, single-instance of the ordering-
divergence calibration exercise (§5.1 + §5.2 binding); 0
production source modifications is the architectural
sufficiency signal target inherited at gate level from Gate 4
framing §2.2 (§5.3 binding); three predicted cleanup-pressure
forms enumerated with named suppression mechanisms (§5.4
binding, Placement A + B substrate); one PR-13-LOCAL binding
statement (§0 + §5.5) — pure-isolation discipline rejecting
multi-vector fixture pressure.

**Active carrier count at PR 13 open: 17.** Composition
unchanged from Gate 4 framing §3.1: 15 inherited carriers
(#1–#15) + carrier #16 (active, promoted at Gate 3 close)
+ carrier #17 (active from Gate 3 framing). PR 13 introduces
NO new carriers; the no-new-carriers discipline preserves
from Gate 4 framing §3.1 + §6.1.

**Reference discipline (binding):** *"17 active carriers"*
is the canonical reference. The candidate-substrate marking
discipline retired at Gate 3 close; PR 13 surfaces travel
carriers in natural numeric ordering without substrate
marking.

---

## 0. PR-13-LOCAL binding statement — pure-isolation discipline

One sentence governs PR 13 verbatim. It appears at the top
of the PR 13 test module docstring + PR 13 fixture module
docstring + PR 13 commit message bodies under "preserved
invariants."

**PR-13-LOCAL binding statement — ordering isolation:**

> **PR 13 isolates ordering divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 13 scope —
> combining ordering with cardinality, partial-set,
> semantic-normalization, duplicate-handling, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 13 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

This is the operational discipline statement governing PR 13
implementation. PR 13's evidentiary value depends entirely
on single-vector isolation: if multi-vector pressure surfaces
within the fixture or the test, attribution from observed
outcomes to the single shaping constraint becomes impossible,
and the absence-evidence loses its methodology-corroboration
weight.

**Why "laboratory-grade":**

The vocabulary is deliberate. PR 14 and PR 15 introduce
different pressure vectors (partial-narrow / multi-survivor
mismatch); they are NOT pure-isolation cases — their
divergence vectors are inherently compound (partial-set
implicates cardinality; multi-survivor implicates cardinality
+ ordering subtly). PR 13 IS the no-confound case. Its
ordering-only-vector property is the calibration substrate
that lets Placement A + Placement B corroborate cleanly
before more confounded substrates land.

**Why PR-13-LOCAL is non-regenerating:**

Per the PR-N-LOCAL non-regeneration rule (Gate 2 framing
§3.1), PR-13-LOCAL is scope-local. It does NOT travel to
PR 14 or PR 15 surfaces — those PRs author their own
PR-N-LOCAL bindings appropriate to their divergence
dimensions. The non-regeneration is the discipline; PR 14
inheriting "ordering isolation" verbatim would be category
error since PR 14's substrate is not ordering-isolated.

**Travel discipline at PR 13:**

PR-13-LOCAL appears at:

- `tests/corpus/test_pr13_ordering_divergence.py` module
  docstring (Step 1 surface).
- `tests/corpus/fixtures/fix_ordering_divergence.py`
  module docstring (Step 2 surface).
- All PR 13 commit message bodies under "preserved
  invariants" / "PR-13-LOCAL" sections.
- This framing artifact §0 (verbatim form above).

**No Gate-4-LOCAL governing sentence accompanies PR-13-
LOCAL.** Gate 4 framing §3.1 + §6.1 + §7 item 22 explicitly
rejected speculative Gate-4-LOCAL authoring. The §0 carries
PR-13-LOCAL alone; the asymmetry vs. PR 11 framing §0 (which
carried Gate-3-LOCAL + PR-11-LOCAL) is structurally
deliberate, not an oversight.

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
  grounding-time amendment variant; member #9; fixture
  corpus locked as archaeology; **fixture naming
  convention** (`fix-pr9-single-survivor` etc.) PR 13 inherits;
  PR 9 integration test infrastructure (`_apply_pr9_patches`,
  `_read_records`) PR 13 reuses as test-internal archaeology
  surfaces.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis;
  four §7.3 ontological questions unbinding (preserved at
  PR 13 inheritance via Gate 4 framing §5.2).
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — Path B locked
  precedent; binding framing clarification on cross-surface
  unbinding (preserved at Gate 4 inheritance + PR 13
  inheritance).
- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — comparator surface
  operational; `compare_records` + `DivergenceReport` +
  `ComparatorInputError` (PR 10 spec §4.1.6 reference
  implementation) PR 13 consumes unchanged; **§4.2 binding
  behavioral commitment ("compare as persisted")** is the
  central architectural commitment PR 13 exercises under
  ordering-divergence pressure; class member #10.
- `A.5.3.2-PR11-CLOSE.md` (`ee2225b`) — recomposition arc
  operational end-to-end; **PR-11-LOCAL traverses-not-erases-
  seams discipline** applied at gate level (Gate 3 close §3
  item 10) — PR 13 inherits the discipline as gate-level
  constraint, not PR-11-LOCAL regeneration; zero-incarnation-
  amendments cleanest arc; §5.3 candidate methodology
  second-instance ABSENCE outcome (third-instance corroboration
  target for PR 13 via Placement A).
- `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`) — gate-arc synthesis;
  carrier #16 promotion; cleanup-pressure-resistance class
  promotion to named methodology (10 members); 17 active
  carriers; four-walker Layer 2 partition operational;
  conditional PR 12 DEFER; four §7.3 ontological questions
  hand forward to Gate 4 (preserved at PR 13 inheritance).
- `A.5.3.2-GATE-4-FRAMING.md` (`fbf2285`) — **immediate
  predecessor; the gate-level inheritance contract PR 13
  operates against.** §2.4 architectural commitment ("Gate 4
  is the deliberate continuation of empirically bounded
  topology proof through divergence-shape robustness
  exercise"); three-PR primary slot structure locked (§5.5);
  PR ordering locked (§5.6); §10 PR 13 sub-section provides
  the architectural commitment + predicted cleanup-pressure
  forms + suppression mechanisms PR 13 framing builds on;
  Placement A operational corroboration target (§5.8 + §6.2);
  Placement B methodology-stack maturation claim with three
  causality preconditions (§4.4 + §4.5 + §6.3); §7 22 non-
  acquisition commitments PR 13 honors at gate level.
- **Gate 4 framing → PR 13 framing convergence pass (this
  session):** four binding decisions locked (PR-13-LOCAL
  binding statement authored at framing-level decision; fixture
  + test name + count locked at one of each; 0-prod-mod target
  inherited from Gate 4 with explicit deviation protocol; three
  predicted cleanup-pressure forms enumerated with named
  suppression mechanisms for Placement A + B substrate). One
  PR-13-LOCAL binding statement (§0) without introducing new
  carriers — PR 13 inherits Gate 4 framing's carrier set
  unchanged. The convergence pass surfaced **evidence
  inflation rejection** as the discipline anchoring the 1-test
  decision (one clean traversal proves the architectural
  commitment; symmetric inverse-direction testing tests the
  same discipline twice and inflates evidence without
  contributing architectural value); **repetition under
  changing pressure is corroboration** as the methodology-
  stack observation anchoring the 3-step PR 11 cadence
  preservation; **observations emerge from pressure rather
  than being architected into existence** as the discipline
  rejecting 4-step decomposition that would engineer
  cumulative-multi-step concentration evidence into existence.

---

## 2. PR 13 objective

### 2.1 The narrow architectural question

**PR 13's architectural question is sharp and singular:**

> **Does the comparator's compare-as-persisted discipline
> (PR 10 §4.2 binding behavioral commitment) survive an
> ordering-only divergence vector through the full
> recomposition arc?**

The question is **not** "do all permutations diverge?" Pure
permutation behavior is implicit in the PR 10 §4.2 binding
(the comparator preserves authored sequence exactly as
persisted; sequence-different inputs produce sequence-
preserving divergence reports). PR 13 is not surveying the
permutation space.

The question is **not** "is ordering meaningful?" That is
implicit in the comparator's structured return shape (the
report carries sequences, not sets — sequence-encoding
already commits to ordering as meaningful).

The question **is** the operational discipline question:
when the end-to-end recomposition arc (validated under
no-divergence + intentional-divergence at PR 11) is
exercised under pure-structure ordering divergence, does
every seam in the seam path preserve sequence-as-persisted
without canonicalization, sorting, repair, or semantic
coercion at any traversal step?

**One clean traversal proves it.** The test exercises:

```
fixture (FIX_ordering_divergence)
  → drive_seed_fixture          [orchestration seam]
    → emit_seed_expectation     [expectation persistence seam]
    → chat_handler arbitration  [observation production seam]
      → emit_divergence_capture [observation persistence seam]
        → JSONL persistence     [persistence-topology seam]
          → reader              [readback seam (via _read_records)]
            → compare_records   [interpretive-read seam]
              → DivergenceReport assertions
```

At every seam, if sequence-as-persisted holds, the discipline
operates end-to-end. If sequence drifts at any seam (e.g.,
JSONL persistence canonicalizes via JSON serialization
behavior; reader collapses ordering through dict iteration;
comparator sorts inputs pre-comparison), PR 13's
DivergenceReport assertion will surface the drift — and the
drift becomes the work, NOT a justification for production
modification within PR 13 scope (it would surface as Gate-X
inheritance instead).

### 2.2 What PR 13 ships

PR 13 ships **exactly one new fixture + exactly one new test**:

- **Fixture:** `tests/corpus/fixtures/fix_ordering_divergence.py`
  authoring `expected_narrow=[A, B, C]` (canonical sequence)
  against an arbitration outcome that observes
  `narrower.decision=[C, A, B]` (rotated sequence; same set).
  Single direction, single dimension, single divergence
  vector.

- **Test:** `tests/corpus/test_pr13_ordering_divergence.py`
  containing one named test
  (`test_recomposition_arc_ordering_divergence`) that
  exercises the fixture through the full end-to-end seam
  path + asserts the four-key `DivergenceReport` shape with
  `narrow_diverged=True` and field-by-field sequence
  preservation.

The single-test scope is binding (§5.2). PR 13 does NOT
ship:

- Inverse-direction variant (authored `[C, A, B]` vs observed
  `[A, B, C]`). The compare-as-persisted discipline is
  direction-symmetric by construction; testing the inverse
  tests the same discipline twice through symmetric assertion
  paths. **Evidence inflation rejected** (§5.2 + §4.4).
- Multi-permutation variants (e.g., `[A, C, B]`, `[B, A, C]`,
  `[B, C, A]`). Pure permutation behavior is implicit in the
  PR 10 §4.2 binding; PR 13 does not survey permutation space.
- Bidirectional inverse pairs (authored `[A, B]` vs observed
  `[B, A]` as a minimal case alongside the three-element
  case). One representative-of-class case proves the
  discipline survives the divergence vector; minimal-case
  variants are evidence inflation.

### 2.3 Gate 4 calibration role

PR 13 is **Gate 4's calibration exercise**. The first PR in
the three-PR primary sequence (per Gate 4 framing §5.5 +
§5.6) operates as substrate for everything Gate 4 close
evaluates:

- **Placement A operational corroboration substrate**
  (Gate 4 framing §5.8 + §6.2) — PR 13's three predicted
  cleanup-pressure forms either surface or remain absent
  during implementation; the outcome contributes the first
  Gate 4 instance toward Placement A third-instance
  corroboration evaluation.

- **Placement B methodology-stack maturation claim
  substrate** (Gate 4 framing §4.4 + §6.3) — PR 13's three
  causality preconditions (framing-time prediction at this
  §5.4; named suppression mechanisms at this §5.4;
  corroborated recurrence accumulated cross-PR at Gate 4
  close) operationally manifest at the first independent-
  conditions instance.

- **§2.4 architectural commitment substrate** — PR 13 is
  the first Gate 4 PR carrying Gate 4 framing §2.4's
  architectural commitment verbatim into PR-level
  framing/spec/close + commit message bodies. The travel
  discipline at PR 13 establishes the operational pattern
  PR 14 + PR 15 inherit.

- **0-prod-mod-as-architectural-sufficiency-signal
  substrate** (Gate 4 framing inheritance + Gate 3 close
  §2.3) — PR 13's 0-prod-mod outcome contributes to the
  three-instance candidate methodology now in Gate 4
  cumulative evaluation.

**Calibration value depends on pure-isolation.** If PR 13's
fixture or test introduces multi-vector pressure (the
"while we're here, also test..." pressure forms §5.4
predicts), the calibration substrate becomes mixed-pressure
and attribution from outcomes to single shaping constraints
becomes impossible. PR-13-LOCAL (§0 + §5.5) is the binding
guardrail.

### 2.4 PR 13 in the three-PR sequence

PR 13 is **first** in the three-PR primary sequence per
Gate 4 framing §5.6:

| # | Dimension | Pure-isolation? | Calibration role |
|---|---|---|---|
| **PR 13** | **Ordering divergence** | **Yes — single vector, no confound** | **Calibration exercise (this PR)** |
| PR 14 | Partial-narrow divergence | No — implicates cardinality + presence-absence | Semantic preservation pressure under richer recomposition |
| PR 15 | Multi-survivor mismatch | No — implicates cardinality + ambiguity-class | Ambiguity topology under most adversarial recomposition pressure |

PR 13's role within the sequence:

- **Calibration first.** PR 13 establishes that the validated
  recomposition arc preserves authored structure through
  pure-vector pressure before PR 14 + PR 15 introduce
  multi-vector pressure surfaces. Without PR 13's
  calibration, PR 14 + PR 15 outcomes would not be
  cleanly attributable.

- **Substrate accumulator.** PR 13's predicted-pressure-
  form outcomes + 0-prod-mod outcome accumulate toward
  cumulative Placement A + Placement B evidence; PR 14 +
  PR 15 add further independent-conditions instances; Gate
  4 close evaluates the cumulative.

- **Cadence anchor.** PR 13's 3-step PR 11-pattern cadence
  establishes the operational shape PR 14 + PR 15 inherit.
  Repetition of the cadence under different divergence
  pressures is corroboration of the cadence itself as
  methodology substrate (Gate 4 framing §3.5 + PR 11 close
  §4 archaeology precedent).

---

## 3. Architectural inheritance from Gate 4

### 3.1 17 active carriers + no new carriers at PR 13

PR 13 inherits 17 active carriers unchanged from Gate 4
framing §3.1 + §6.1:

- Carriers #1–#13 (active; PR 4 + PR 5 + PR 6 lineage).
- Carrier #14 (active; declared epistemic class vs. persisted
  provenance).
- Carrier #15 (active; chat-handler-only seeding scope; third
  clause binding at PR 13 inheritance).
- Carrier #16 (active; *"Reliability work proves topology,
  not infrastructure"*).
- Carrier #17 (active; recomposition discipline).

**PR 13 introduces NO new carriers.** The no-new-carriers
discipline preserves from Gate 4 framing §3.1. PR 13 framing
does NOT speculatively author Gate-4-LOCAL governing sentence
candidates (rejected by Gate 4 framing §7 item 22) and does
NOT author candidate carriers (no operational basis;
candidate-carrier corroboration substrate is gate-scope, not
PR-scope authorship).

The 17 carriers travel verbatim at:

- `test_pr13_ordering_divergence.py` module docstring (Step 1
  surface).
- `fix_ordering_divergence.py` module docstring (Step 2
  surface, when authored).
- All PR 13 commit message bodies under "preserved
  invariants."

Relevance-by-file ordering applies (most-load-bearing carrier
at top of each PR 13 module per PR 8 spec §0 travel rule).
The PR-N-LOCAL non-regeneration rule preserves — PR-11-LOCAL
does NOT travel to PR 13; PR 10-LOCAL pair-input lock remains
scoped to the comparator surface; PR 9 fixture-data-
discipline contract remains scoped to fixture modules
(applies operationally because PR 13 fixture is one of those
modules).

### 3.2 The validated comparator + recomposition arc

PR 13 consumes the PR 10 comparator + PR 11 recomposition
arc unchanged:

- `forge_bridge/corpus/_compare.py` — `compare_records` +
  `DivergenceReport` + `ComparatorInputError` (PR 10 spec
  §4.1.6 reference implementation). **The §4.2 binding
  behavioral commitment ("compare as persisted") is the
  central commitment PR 13 exercises.**
- `tests/corpus/test_pr11_recomposition_arc.py` — recomposition
  arc consumption pattern PR 13 reuses verbatim per Gate 3
  close §2.2 + Gate 4 framing §3.7. The PR 11 nine-step
  traversal annotation + the underscored-private PR 9 imports
  as test-internal archaeology surfaces operate as inherited
  consumption pattern.

PR 13 ships against the substrate, NOT atop it. Modifications
to the comparator surface or the recomposition arc pattern
are rejected at the spec layer per Gate 4 framing §5.3 + §7
items 3 + 9.

### 3.3 The PR 9 three-fixture corpus + fixture naming convention

PR 9's three-fixture corpus is preserved unchanged at PR 13
(Gate 4 framing §7 item 10 non-acquisition). PR 13 extends
the corpus with one new chat-handler-surface fixture
(`fix-pr13-ordering-divergence`) under the existing PR 9
fixture-data-discipline.

**Fixture naming convention inherited from PR 9 (grounded
from `tests/corpus/fixtures/`):**

PR 9 fixtures carry **two distinct naming surfaces** that
together encode the fixture's identity:

1. **Filename** (`fix_<shape>.py`, snake_case, NO PR anchor):
   - `fix_single_survivor.py`
   - `fix_multi_match.py`
   - `fix_no_keyword_match.py`

2. **`fixture_id` field value** (`fix-pr<N>-<shape>`,
   kebab-case, WITH PR anchor) — embedded as the
   `fixture_id` key inside the fixture's `FIXTURE` dict:
   - `"fix-pr9-single-survivor"` (inside `fix_single_survivor.py`)
   - `"fix-pr9-multi-match"` (inside `fix_multi_match.py`)
   - `"fix-pr9-no-keyword-match"` (inside `fix_no_keyword_match.py`)

The two surfaces encode three identity properties:

1. **Archaeological origin** — the `fixture_id` field's
   `-pr<N>-` segment anchors the fixture to its PR of
   authoring; archaeology readers can trace fixture-of-
   origin through the field value. The filename does NOT
   carry PR anchor.
2. **Pressure-vector identity** — both surfaces carry the
   shape suffix (`single-survivor` / `multi-match` /
   `no-keyword-match`) encoding the divergence/outcome
   dimension the fixture exercises. Filename uses snake_case;
   `fixture_id` uses kebab-case.
3. **Future corpus readability** — the filename remains
   navigable through directory listing (no PR anchor
   crowds the visual scan); the `fixture_id` retains
   chronological traceability through its PR anchor.

**Symbol export convention:** Each fixture module exports
exactly one symbol named **`FIXTURE`** (PR 9 convention is
canonical; not `FIX_<NAME>` per-module). Consuming tests
alias on import:

```python
from tests.corpus.fixtures.fix_single_survivor import (
    FIXTURE as FIX_SINGLE_SURVIVOR,
)
```

The `FIXTURE` constant name is consistent across all fixture
modules; the test-side alias carries the per-fixture local
identifier.

**PR 13 fixture naming preserves the convention:**

| Surface | PR 13 value |
|---|---|
| Filename | `tests/corpus/fixtures/fix_ordering_divergence.py` |
| `fixture_id` field | `"fix-pr13-ordering-divergence"` |
| Module export | `FIXTURE` (canonical) |
| Test-side import alias | `FIX_ORDERING_DIVERGENCE` (per PR 11 aliasing pattern) |

The two-surface preservation is binding (§5.9). The
filename-without-PR-anchor + `fixture_id`-with-PR-anchor
asymmetry is itself archaeology — PR 9 made the convention
choice; PR 13 inherits, not relitigates.

Alternatives considered + rejected at framing convergence:

- **PR-anchored filename** (`fix_pr13_ordering_divergence.py`)
  — would break PR 9's filename convention. PR 9 chose
  filename-without-PR-anchor for visual-scan navigability;
  changing the convention at PR 13 introduces inconsistency
  across the corpus without operational benefit.
- **Non-PR-anchored `fixture_id`** (`fix-ordering-divergence`)
  — would erase archaeological-origin chronology from the
  `fixture_id` field. PR 9 chose `fixture_id`-with-PR-anchor
  for chronology preservation; changing the convention at
  PR 13 would silently weaken the project's per-PR fixture
  archaeology discipline.
- **Module export `FIX_ORDERING_DIVERGENCE`** (per-module
  constant name) — would break PR 9's canonical `FIXTURE`
  symbol export. Test-side aliasing handles the per-fixture
  local identifier need without requiring module-level
  asymmetry.

### 3.4 Placement A operational corroboration substrate role

PR 13 is the first Gate 4 PR contributing to Placement A
operational corroboration. The §5.3 candidate methodology
(framing-time-pressure-prediction-through-absence) sits at
two-instance corroboration entering Gate 4 (PR 10 + PR 11
ABSENCE outcomes per Gate 3 close §1.7). Gate 4 framing
§5.8 names the third-instance promotion criterion:

> **One Gate 4 PR contributing ABSENCE-evidence under
> independent conditions (i.e., under different divergence-
> dimension conditions than PR 10 + PR 11) meets the three-
> instance bar.**

PR 13's contribution mechanism (operational):

1. **Predicted cleanup-pressure forms enumerated at framing
   time** (this §5.4 — three forms named explicitly).
2. **Named suppression mechanisms paired with each
   predicted form** (this §5.4 — each form's suppression
   mechanism named explicitly).
3. **Per-PR-13 close artifact records outcomes** (ABSENCE
   or SURFACE per predicted form).

Three possible outcome distributions at PR 13 close:

| Outcome | Placement A contribution | Promotion implication |
|---|---|---|
| All three forms ABSENCE | One full ABSENCE-evidence instance under independent conditions | Third-instance bar met at PR 13 alone (PR 14 + PR 15 add corroboration cushion) |
| Mixed ABSENCE + SURFACE | Mixed-evidence instance — partial absence-evidence, partial resistance-evidence | Third-instance bar NOT met at PR 13 alone; PR 14 + PR 15 corroboration accumulates toward bar |
| All three forms SURFACE | Full resistance-evidence instance — no absence-evidence | Third-instance bar NOT contributed-toward at PR 13; PR 14 + PR 15 still available |

PR 13 framing does NOT pre-bind which outcome surfaces. The
prediction discipline (this §5.4) is operationally separate
from the outcome (recorded at close). Pre-binding the outcome
at framing would itself constitute the discipline failure
mode Placement B precondition 1 guards against (retrospective
prediction-construction from observed outcomes).

### 3.5 Placement B methodology-stack maturation substrate role

PR 13 is the first Gate 4 PR contributing to Placement B
methodology-stack maturation claim corroboration. Per Gate 4
framing §4.4 + §4.5 + §5.9, the claim operationally requires
all three causality preconditions to manifest across three
genuinely independent divergence dimensions.

**PR 13's contribution to the three preconditions:**

| Precondition | PR 13 contribution |
|---|---|
| 1: Prior pressure prediction at framing time | This §5.4 enumerates three predicted cleanup-pressure forms BEFORE PR 13 implementation begins. Operational manifestation: framing-time prediction at PR 13 framing. |
| 2: Named suppression mechanism | This §5.4 pairs each predicted form with a named suppression mechanism. Operational manifestation: named mechanism at PR 13 framing. |
| 3: Corroborated recurrence across independent conditions | PR 13 contributes one instance under ordering-divergence conditions. PR 14 contributes second instance (partial-narrow conditions); PR 15 contributes third instance (multi-survivor mismatch conditions). Cumulative manifestation requires all three primary PRs. |

PR 13 alone does NOT satisfy precondition 3 — single-instance
absence is raw archaeology per Gate 4 framing §6.5
governance discipline. PR 13's role is contributing the
first independent-conditions instance; corroborated recurrence
manifests only through the cumulative three-PR contribution
evaluated at Gate 4 close (per Gate 4 framing §11.4).

**This is per design.** Placement B's promotion gate is
deliberately set at the gate level (three primary PRs
collectively manifest preconditions), not the per-PR level.
A single-PR Placement B promotion would itself violate
precondition 3.

### 3.6 §2.4 architectural commitment travels at PR 13

Gate 4 framing §2.4's architectural commitment sentence
travels verbatim at PR 13 framing/spec/close artifact bodies
+ PR 13 commit message bodies under "architectural
commitment" sections per Gate 4 framing §2.4 binding form:

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

PR 13 is the first Gate 4 PR establishing this travel
discipline. The travel pattern at PR 13 sets the operational
template for PR 14 + PR 15.

**Travel placement at PR 13 (binding):**

- This framing artifact §2.4 (referenced) + §3.6 (this
  subsection) + §5.6 (binding decision form).
- PR 13 spec §2 architectural commitment section.
- PR 13 Step 1 commit message body under "architectural
  commitment" section.
- PR 13 Step 2 commit message body under "architectural
  commitment" section.
- PR 13 Step 3 commit message body under "architectural
  commitment" section.
- PR 13 close artifact §1 + §6.5 (or equivalent
  architectural-commitment + architectural-sufficiency
  sections).

**Travel deliberately does NOT extend to:**

- The PR 13 test module docstring.
- The PR 13 fixture module docstring.

Per Gate 4 framing §2.4 binding clarification: the §2.4
sentence is gate-shaped architectural posture, NOT carrier-
shaped governance. Carriers travel through fixture/test
docstrings (per Gate 4 framing §3.1 + §6.1 + this §3.1);
the §2.4 commitment does not. The asymmetry preserves the
carrier / governing sentence / methodology-stack distinction.

### 3.7 10-member promoted cleanup-pressure-resistance class

PR 13 inherits the 10-member class promoted to named
methodology at Gate 3 close §1.5. Members #1–#10 protections
operate at PR 13:

| # | Member | Operationally relevant at PR 13? |
|---|---|---|
| 1 | Helper duplication | No new helpers authored — implicit compliance |
| 2 | Visual asymmetry / Properties A–D | PR 13 is not an emission surface — Layer 3 lint not triggered |
| 3 | Intentionally inert structural parameters | No new parameters introduced — implicit compliance |
| 4 | Always-present `fixture_id` field | New fixture authors `fixture_id` per existing observation record builder — implicit compliance |
| 5 | Nested-not-unconditional synthesis form | No reader-side modifications — implicit compliance |
| 6 | Inline I-6 wrapper duplication | No `_persist_expectation_record` modifications — implicit compliance |
| 7 | Companion records as truth-partitioning | New fixture follows existing companion-record pattern — implicit compliance |
| 8 | `emit_seed_expectation` as semantics-not-topology | No `_seed.py` modifications — implicit compliance |
| 9 | **Fixture-surface-data-discipline** | **DIRECTLY RELEVANT — PR 13 authors a new fixture under member #9's protection. The fixture is pure-data-declaration: no orchestration imports, no helper imports, no infrastructure imports.** |
| 10 | Speculative-reserved-imports rejection | **DIRECTLY RELEVANT — PR 13 test module follows imports-land-when-used. Step 1 has `from __future__ import annotations` only; imports land at Step 2 when test body uses them.** |

**Members #9 + #10 are PR-13-active protections.** Both
operationally enforce at PR 13 implementation — fixture
authoring (Step 2) lands fixture under Layer 2
`_FIXTURE_PERMITTED_IMPORTS` value-locked + PR 9 walker
protection; test module authoring (Steps 1 + 2) lands
imports per member #10 discipline.

**PR 13 surfaces no new candidate class members
speculatively** (Gate 4 framing §3.4 + §7 item 21). If
implementation pressure surfaces a new candidate, the
candidate registers at PR 13 close based on actual evidence;
framing-time speculative authoring is rejected.

### 3.8 Four-walker Layer 2 partition operational

PR 13 operates within the four-walker partition (PR 4 + PR 8
+ PR 9 + PR 10) unchanged. PR 13 introduces NO fifth walker
(Gate 4 framing §3.3 + §7 item 9 non-acquisition).

**Walker-relevant surfaces at PR 13:**

- PR 9 walker (`_FIXTURE_PERMITTED_IMPORTS` value-locked) —
  PR 13's new fixture lands under this walker's protection
  + must satisfy the single-symbol-gate import constraint.
- PR 10 walker (`_compare.py` `_PERMITTED_IMPORTS` value-
  locked to zero non-`__future__` imports per PR 10 spec
  §4.2.1) — PR 13 does NOT modify `_compare.py` so the PR 10
  walker is not exercised by PR 13.

PR 4 + PR 8 walkers are not relevant at PR 13's substrate
(PR 13 does NOT modify the narrowing subsystem; PR 13 does
NOT modify `_seed.py`).

### 3.9 Five candidate methodologies + PR 13's contribution

Gate 4 framing §3.6 inventoried five candidate methodologies
pending Gate 4 corroboration. PR 13's contribution to each:

| Methodology | PR 13 contribution mechanism |
|---|---|
| §5.3 framing-time-pressure-prediction-through-absence | Placement A (§3.4 above); first Gate 4 instance toward third-instance corroboration |
| Three-PR amendment-at-incarnation catch-point migration | PR 13's catch-point evidence (framing-spec-drafting-time terminal-catch OR earlier-catch progression) registers at close — descriptive contribution |
| 0-prod-mod-as-architectural-sufficiency-signal | PR 13 ships 0-prod-mod (§5.3 binding) as named architectural sufficiency signal — first Gate 4 instance toward gate-level promotion |
| Recomposition-through-existing-seams | PR 13 exercises the validated recomposition arc through a new fixture without introducing new substrate — corroboration of PR 11 first-instance |
| Single-center vs. cumulative multi-step architectural concentration | PR 13's 3-step structure with single architectural-center commit (Step 2) registers as single-center pattern — first Gate 4 instance toward taxonomy interpretation |

PR 13 framing does NOT pre-bind promotion outcomes for any
candidate. Promotion evaluation belongs at Gate 4 close per
Gate 4 framing §11.5.

---

## 4. Architectural delta — what PR 13 introduces

### 4.1 One new fixture file

`tests/corpus/fixtures/fix_ordering_divergence.py` is
the single new fixture file PR 13 authors. The fixture is
chat-handler-surface scope (per carrier #15 + Gate 4 framing
§2.3 scope guardrail) + ordering-divergence pressure vector
isolated (per §0 PR-13-LOCAL binding).

**Canonical fixture shape (PR 13 spec to detail exact
values; matches PR 9 convention grounded from
`tests/corpus/fixtures/fix_single_survivor.py:147-153`):**

```python
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr13-ordering-divergence",
    "prompt": "<short prompt that drives chat_handler to produce ordered
              arbitration with multiple survivors>",
    "expected_narrow": ["<tool_A>", "<tool_B>", "<tool_C>"],
    # The arbitration outcome must observe a different ordering
    # (e.g., [tool_C, tool_A, tool_B]) — fixture authors prompt
    # such that chat_handler reliably produces multi-survivor
    # ordered arbitration that diverges from the authored sequence.
}
```

The module exports exactly **one symbol named `FIXTURE`**
(canonical convention per §3.3). Consuming tests alias on
import — see §4.2 for the import-aliasing pattern.

The fixture is a pure-data declaration per member #9
protection. Exact tool names + exact prompt wording derive
at PR 13 spec per `feedback_ground_specs_in_actual_files`
discipline — read the existing PR 9 fixtures + the chat_handler
arbitration behavior before locking specific values.

**Fixture data discipline (binding per member #9):**

- No orchestration imports (`drive_seed_fixture`,
  `chat_handler`, etc.).
- No helper imports.
- No infrastructure imports.
- Single-symbol export: the module exports `FIXTURE`
  (canonical name per §3.3). The dict is the only top-level
  symbol assigned at module scope (excepting the
  `from __future__ import annotations` line at the head of
  the module).
- Pure-data structure (dict literal; no function calls; no
  expression evaluation beyond literal construction).

### 4.2 One new test module + one named test

`tests/corpus/test_pr13_ordering_divergence.py` is the single
new test module PR 13 authors. The module contains exactly
one named test. Imports follow PR 11's grounded pattern
(`tests/corpus/test_pr11_recomposition_arc.py:89-111`) —
fixture symbol aliased on import; PR 9 underscored helpers
imported as test-internal archaeology surfaces:

```python
from __future__ import annotations

import pathlib

import pytest

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._seed import drive_seed_fixture

from tests.corpus.fixtures.fix_ordering_divergence import (
    FIXTURE as FIX_ORDERING_DIVERGENCE,
)

from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)


def test_recomposition_arc_ordering_divergence(monkeypatch, tmp_path):
    # Traversal: fixture → drive_seed_fixture → chat_handler arbitration
    #   → emit_divergence_capture → JSONL persistence → reader
    #   → compare_records → DivergenceReport assertions.
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)
    drive_seed_fixture(**FIX_ORDERING_DIVERGENCE)
    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == FIX_ORDERING_DIVERGENCE["fixture_id"]]
    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")
    report = compare_records(
        observation_record=observation,
        expectation_record=expectation,
    )
    # DivergenceReport four-key structural assertions:
    assert report["fixture_id"] == FIX_ORDERING_DIVERGENCE["fixture_id"]
    assert report["expectation"]["expected_narrow"] == [...]  # sequence-preserving
    assert report["observation"]["observed_narrow"] == [...]  # sequence-preserving (different sequence)
    assert report["divergence"]["narrow_diverged"] is True
```

**The test traverses the full recomposition arc explicitly
at the test body level** per PR-11-LOCAL discipline applied
at gate level (Gate 3 close §3 item 10). No helper wraps
the traversal; no fixture-to-DivergenceReport helper;
no reader+comparator assertion helper.

**The PR 9 underscored imports** (`_apply_pr9_patches`,
`_read_records`) are consumed as **test-internal archaeology
surfaces** per PR 11 spec §4.1.2 + Gate 3 close §2.2. They
are NOT promoted to public APIs.

Exact assertion shape + sequence values derive at PR 13 spec
per `feedback_ground_specs_in_actual_files` — read the PR 11
test patterns + PR 10 `DivergenceReport` reference
implementation before locking specific assertion-equality
constructs.

### 4.3 Ordering divergence as pure single-vector pressure

PR 13's substrate is **pure-isolation**:

- **Same set, different sequence.** `expected_narrow` and
  `observed_narrow` contain the same elements. The only
  divergence vector is the ordering of those elements.
- **No cardinality divergence.** Both lists have the same
  length. The comparator does not need to handle missing-
  elements / extra-elements.
- **No partial-set divergence.** Every element in
  `expected_narrow` appears in `observed_narrow` and vice
  versa.
- **No semantic-normalization divergence.** Tool names are
  exact-match identifiers; no canonical-form transformations
  involved.
- **No duplicate-handling divergence.** Each list contains
  distinct elements; no duplicates to canonicalize.

**Why pure-isolation matters:**

PR 13's evidentiary value depends on attribution. If the
comparator correctly reports `narrow_diverged=True` under
PR 13's fixture, the outcome is attributable to one specific
discipline: compare-as-persisted (PR 10 §4.2). If the
fixture also varied cardinality or partial-set membership,
attributing the outcome to compare-as-persisted vs. some
other comparator discipline would be impossible.

The pure-isolation property is what gives PR 13 laboratory-
grade methodology corroboration value. PR-13-LOCAL (§0)
binds the project to that property.

### 4.4 Evidence inflation rejection

PR 13 ships **exactly one test**, NOT two (inverse-direction
variant), NOT three (multi-permutation), NOT N (permutation
survey). The 1-test discipline is anchored against an
explicit failure mode: **evidence inflation**.

**Evidence inflation = adding test variants whose primary
value is psychological reassurance rather than architectural
evidence.**

The inverse-direction variant (authored `[C, A, B]` vs
observed `[A, B, C]`) is the canonical evidence-inflation
candidate at PR 13. Its addition:

- Adds 0 architectural evidence (the comparator's behavior is
  direction-symmetric by construction per PR 10 §4.2; testing
  the inverse tests the same discipline twice through
  symmetric assertion paths).
- Adds 1 test to the count (218 → 219 forge env collected).
- Adds N% to PR 13's apparent thoroughness without
  contributing to Placement A + Placement B substrate
  corroboration weight.

**The rejection is operational, not stylistic.** Evidence
inflation is a documented failure mode the project has been
getting better at rejecting (Gate 3 framing §5.5 default
lean preserved; PR 11 close §1.8 zero-additions to the
cleanup-pressure-resistance class as discipline; PR 10 +
PR 11 close-time non-promotion of candidate methodologies
without three-instance bar met).

**If review pressure surfaces the inverse-direction case
as genuinely architecturally distinct**, the addition
registers as drafting-time amendment per the canonicalized
amendment-at-incarnation cadence (per Gate 4 framing §3.5).
Pre-paying for the variant at PR 13 framing time is
rejected.

### 4.5 The single-test traversal as architectural test posture

Each of PR 13's framing-time decisions (1 fixture / 1 test /
single direction / 3-step cadence) reinforces a single
architectural posture: **one clean traversal proves the
discipline.**

This posture is the inheritance from PR 11 framing §2.4
("the traversal trace as architectural test posture")
operationalized at single-test granularity. PR 11 had three
tests against three existing PR 9 fixtures (one traversal
per fixture); PR 13 has one test against one new fixture
(one traversal per fixture).

**The posture is anchored:**

- PR 13's test body explicitly traverses each decomposition
  seam in order (per §4.2 traversal annotation).
- No helper absorbs the traversal.
- No assertion factoring obscures the seam-by-seam path.
- The DivergenceReport four-key assertions read the
  comparator's structured return at full structural fidelity.

---

## 5. Binding decisions

### 5.1 PR 13 scope locked: one fixture + one test, single-direction ordering divergence

PR 13 scopes ship to **exactly one new fixture file
(`tests/corpus/fixtures/fix_ordering_divergence.py`; module
export `FIXTURE`; `fixture_id` field
`"fix-pr13-ordering-divergence"`) + exactly one new test
(`test_recomposition_arc_ordering_divergence` in
`tests/corpus/test_pr13_ordering_divergence.py`)**. Pure-
isolation ordering divergence (same set, different sequence)
in a single direction (authored canonical sequence vs.
observed rotated sequence).

**Operational scope boundaries:**

- Fixture exercises chat-handler arbitration surface only
  (per carrier #15 + Gate 4 framing §2.3 scope guardrail).
- No cross-surface fixture identity (per Gate 4 framing
  §5.2 + carrier #15 third clause).
- No multi-vector fixture pressure (per §0 PR-13-LOCAL
  binding + §5.5 below).
- Single-test count locked (§5.2).

### 5.2 Test count locked at exactly 1

PR 13 ships exactly **one named test**. The architectural
rationale + the evidence-inflation rejection are detailed
at §4.4.

**The 1-test count is binding archaeology** per
`feedback_counts_are_archaeology_grade`. Recount at every
PR 13 commit-time reference. PR 13 framing references "1
PR 13 new test" verbatim; PR 13 spec carries forward; PR 13
close arithmetic reads "217 baseline + 1 PR 13 new = 218
forge env collected."

**Amendment clause:** If implementation review surfaces the
inverse-direction or multi-permutation case as genuinely
architecturally distinct (i.e., contributing evidence the
single test does not), the addition registers as drafting-
time amendment per the canonicalized cadence. The current
default is rejection (the project's two-instance pattern at
PR 10 + PR 11 close: variants whose primary purpose is
psychological reassurance are not added).

### 5.3 0 production source modifications

PR 13 ships **0 modifications to production source files**.
The architectural sufficiency signal target inherited at
gate level from Gate 4 framing §2.2 (per Gate 3 close §2.3
named-signal-not-metric template):

> **PR 13 demonstrates the comparator's compare-as-persisted
> discipline survives ordering-only divergence pressure
> without requiring extension, relaxation, or modification
> of any production source surface.**

**0-prod-mod verification at each Step:**

```
$ git diff --stat <previous-step>..HEAD -- forge_bridge/
(empty)
```

Verified at Step 1 + Step 2 + Step 3. If diff is non-empty
at any verification surface, the deviation registers as
**justified-deviation archaeology** per PR 11 spec §5.2
deviation protocol:

- Cause of the production modification documented explicitly
  (likely: a real bug in the comparator's compare-as-
  persisted discipline that PR 13's pure-isolation case
  revealed but PR 10 + PR 11 substrate did not surface).
- The modification's architectural meaning recorded as PR 13
  archaeology, not silent addition.
- The justification accepted under PR 11 spec §5.2 protocol
  OR rejected as out-of-scope for PR 13 (in which case the
  bug registers as Gate-X inheritance + PR 13 reverts the
  production modification with the bug-finding archaeology
  preserved as evidence of substrate gap).

The deviation protocol is enumerated here so PR 13
implementation knows the operational path without consulting
PR 11 spec §5.2 in flight.

### 5.4 Three predicted cleanup-pressure forms + named suppression mechanisms

PR 13 framing predicts three cleanup-pressure forms PR 13
implementation may encounter. Each prediction pairs with a
named suppression mechanism (per Placement B precondition 2
operational manifestation at PR 13).

**Predicted form 1: Canonicalization pressure.**

The pressure form: pressure to sort or canonicalize lists
(e.g., alphabetize tool names) before comparison — either at
the comparator surface or at caller-side wrapping in PR 13's
test body.

**Named suppression mechanism:** PR 10 §4.2 binding
behavioral commitment ("compare as persisted"). The
comparator preserves authored sequence exactly as persisted;
caller-side canonicalization that defeats the commitment is
rejected at the spec layer per Gate 3 close §3 item 4
non-revisitable. PR 13 implementation MUST NOT introduce
caller-side sorting or canonicalization at any point in
the test body's traversal path.

**Predicted form 2: Set-equality collapse pressure.**

The pressure form: pressure to interpret the fixture's
same-set-different-sequence outcome as "no real divergence"
or "trivially equivalent" — leading to test assertion
shortcuts (e.g., `assert set(observed) == set(expected)`)
that mask the actual sequence divergence the comparator is
supposed to detect.

**Named suppression mechanism:** PR 10 spec §4.1.6 reference
implementation + cleanup-pressure-resistance class member
#10 protection (compare-as-persisted at import-set surface
extended to compare-as-persisted at sequence-content surface).
The comparator returns sequence-preserving
`DivergenceReport`; PR 13 assertions read the four-key
shape at full structural fidelity (not via set-equality
shortcuts).

**Predicted form 3: Ordering-specific test helper pressure.**

The pressure form: pressure to author an "ordering-divergence
assertion helper" that absorbs the comparison logic — e.g.,
`assert_ordering_divergence(report, expected_sequence,
observed_sequence)` that wraps the four-key DivergenceReport
assertion. The helper's primary purpose would be "making
ordering-divergence test bodies cleaner."

**Named suppression mechanism:** PR-11-LOCAL traverses-not-
erases-seams discipline applied at gate level (Gate 3 close
§3 item 10 + Gate 4 framing §3.7). Helpers whose primary
purpose is "making recomposition cleaner" are rejected at
the spec layer. PR 13 test body inlines the four-key
DivergenceReport assertions explicitly; no helper absorbs
the assertion logic.

**Three "while we're here" pressure forms PR-13-LOCAL
explicitly rejects:**

In addition to the three predicted forms above (canonical-
ization / set-equality collapse / helper proliferation),
PR-13-LOCAL guards against three implementation-pressure
forms that would multi-vector PR 13's fixture/test:

- *"While we're here, also test subset mismatch"* — adding
  a partial-set element to the ordering-divergence fixture
  would convert PR 13 from pure-vector to multi-vector. PR
  14 owns subset/partial-narrow pressure.
- *"While we're here, also test duplicate handling"* —
  adding a duplicate element to the ordering-divergence
  fixture would introduce duplicate-handling-class divergence
  as a confound. Duplicate handling is not in Gate 4 scope
  at any of the three primary PRs.
- *"While we're here, also test semantic normalization"* —
  adding casing variants or substring matches to the
  ordering-divergence fixture would introduce semantic-
  normalization pressure as a confound. Semantic
  normalization is not in Gate 4 scope.

All three "while we're here" pressures are rejected at the
spec layer per PR-13-LOCAL + §7 non-acquisition commitments
items 5 + 6 + 7 below.

### 5.5 PR-13-LOCAL binding statement — pure-isolation discipline

Repeated verbatim from §0 (single-form discipline; one
authoritative wording):

> **PR 13 isolates ordering divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 13 scope —
> combining ordering with cardinality, partial-set,
> semantic-normalization, duplicate-handling, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 13 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

Operational placement (binding):

- `test_pr13_ordering_divergence.py` module docstring.
- `fix_ordering_divergence.py` module docstring.
- All PR 13 commit message bodies under "preserved
  invariants" / "PR-13-LOCAL" sections.

Cleanup pressure to soften the binding (e.g., "the inverse-
direction case isn't really multi-vector since it's the same
vector with roles swapped") is rejected at the spec layer:
even role-swap variants test the same discipline through
symmetric assertion paths and constitute evidence inflation
per §4.4.

### 5.6 §2.4 architectural commitment travels verbatim at PR 13 framing/spec/close + commit bodies

Gate 4 framing §2.4's architectural commitment sentence
travels verbatim at PR 13 surfaces per Gate 4 framing §2.4
binding form (relaxed travel discipline; deliberately stops
short of fixture/test docstrings per Gate 4 framing §2.4
binding):

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

Operational placement (binding):

- This framing artifact §2.4 + §3.6 + §5.6 (this binding
  decision).
- PR 13 spec §2 architectural commitment section.
- PR 13 Step 1, 2, 3 commit message body under "architectural
  commitment" section.
- PR 13 close artifact §1 + §6.5 (or equivalent
  architectural-commitment + architectural-sufficiency
  sections).

NOT in PR 13 test module docstring. NOT in PR 13 fixture
module docstring. The asymmetry vs. carrier travel (active
carriers DO travel through fixture/test docstrings per
§3.1) preserves the carrier / governing sentence / methodology-
stack category integrity Gate 4 framing established.

### 5.7 Comparator surface preserved unchanged

PR 13 does NOT modify the comparator surface
(`compare_records` + `DivergenceReport` + `ComparatorInputError`)
per Gate 4 framing §5.3 binding + §7 item 3 non-acquisition.

- No new `DivergenceReport` field (no `ordering_divergent`,
  no `sequence_signature`, no `permutation_class`).
- No new `compare_records` keyword argument (no
  `ordering_strict`, no `compare_mode`, no caller-side
  configuration).
- No pre-processing helper on the comparator side.
- No change to the §4.2 binding behavioral commitment.

If PR 13 implementation surfaces a real gap in comparator
behavior that requires modification, the gap registers as
Gate-X inheritance archaeology per §5.3 deviation protocol
— NOT as in-flight production modification within PR 13.

### 5.8 `forge_bridge.__all__` stays at 19 symbols

PR 13 does NOT modify `forge_bridge.__all__` per Gate 4
framing §5.4 + §7 item 12 non-acquisition. The 19-symbol
public API preserves.

PR 13 fixture + test consume the comparator + recomposition
arc through corpus-internal import paths
(`from forge_bridge.corpus._compare import compare_records`
+ underscored-private PR 9 imports as test-internal
archaeology surfaces).

### 5.9 PR 9 fixture naming convention preserved (two-surface form)

PR 13 fixture preserves the PR 9 fixture naming convention
(§3.3 above) at both naming surfaces:

| Surface | PR 13 value | PR 9 convention preserved |
|---|---|---|
| Filename | `fix_ordering_divergence.py` | snake_case; NO PR anchor in filename |
| `fixture_id` field | `"fix-pr13-ordering-divergence"` | kebab-case; WITH PR anchor in field |
| Module symbol export | `FIXTURE` | canonical name across all fixture modules |

Alternative naming patterns at any surface are rejected at
the spec layer per §3.3 archaeology preservation discipline:

- PR-anchored filename (`fix_pr13_ordering_divergence.py`)
  rejected — breaks PR 9 visual-scan navigability convention.
- Non-PR-anchored `fixture_id` (`"fix-ordering-divergence"`)
  rejected — erases archaeological-origin chronology.
- Per-module symbol export name (`FIX_ORDERING_DIVERGENCE`
  at module scope) rejected — breaks PR 9 canonical
  `FIXTURE` symbol; consuming tests handle per-fixture local
  identifier needs via import-time aliasing per PR 11
  pattern.

### 5.10 Justified-deviation protocol if 0-prod-mod target falsifies

If PR 13 implementation surfaces a real production-source
gap that compels modification (highly unlikely per Gate 4
framing §5.3 + PR 10/11 validation), the deviation registers
explicitly:

1. **Step verification fails** at the verification git-diff
   check (production source diff is non-empty).
2. **Cause documented** in the failing-step commit message
   body OR in PR 13 spec amendment.
3. **Two dispositions available:**
   - **Accept the deviation** under PR 11 spec §5.2 protocol
     (justified-deviation archaeology; PR 13 ships with
     prod-mod + explicit close-artifact recording).
   - **Reject the deviation** as out-of-scope for PR 13;
     register the bug-finding as Gate-X inheritance
     archaeology; PR 13 reverts the production modification
     + ships against the substrate gap as evidence-of-gap.

The default lean is **reject + register as Gate-X
inheritance** unless the production source gap is itself
the primary architectural revelation of PR 13 (in which
case the substrate gap was the empirical pressure PR 13
was operationally designed to reveal — this is the strongest
form of Placement B substrate evidence).

---

## 6. Placement A + Placement B substrate contribution

### 6.1 Placement A operational corroboration substrate

PR 13's three predicted cleanup-pressure forms (§5.4) +
their named suppression mechanisms (§5.4) operationalize
Placement A precondition 1 + 2 (Gate 4 framing §4.5 + §6.2)
at PR 13 scope.

**PR 13 close-time evaluation surface (per Gate 4 framing
§6.2):**

| Form | Suppression mechanism | Outcome at PR 13 close |
|---|---|---|
| Canonicalization pressure | PR 10 §4.2 binding | ABSENCE / SURFACE |
| Set-equality collapse pressure | PR 10 §4.1.6 reference + member #10 | ABSENCE / SURFACE |
| Ordering-specific test helper pressure | PR-11-LOCAL discipline at gate level | ABSENCE / SURFACE |

PR 13 close §1 records each form's outcome explicitly +
contributes to Placement A third-instance corroboration
evaluation at Gate 4 close.

### 6.2 Placement B methodology-stack maturation substrate

PR 13 contributes the **first independent-conditions
instance** toward Placement B three-precondition operational
manifestation (Gate 4 framing §4.4 + §5.9):

| Precondition | PR 13 contribution at framing time | PR 13 contribution at close time |
|---|---|---|
| 1: Prior pressure prediction at framing time | This §5.4 enumerates three predicted forms at framing time | (Already manifest at framing; close confirms framing-time predictions were authored at framing-time, not retrofitted) |
| 2: Named suppression mechanism | This §5.4 pairs each predicted form with a named suppression mechanism at framing time | (Already manifest at framing; close confirms mechanisms accompany predictions verbatim) |
| 3: Corroborated recurrence | (NOT manifest at PR 13 alone — requires PR 14 + PR 15 to contribute additional independent-conditions instances) | (Cumulative across three primary PRs; evaluated at Gate 4 close) |

PR 13 alone cannot satisfy Placement B precondition 3. Per
Gate 4 framing §6.5 governance discipline, single-instance
absence is raw archaeology, NOT reliability evidence.
PR 13's role is contributing the first instance; cumulative
recurrence manifests through PR 14 + PR 15 at Gate 4 close.

### 6.3 Two-placement substrate independence

PR 13's contribution to Placement A and PR 13's contribution
to Placement B are **operationally distinct** even though
they share the same framing-time prediction + suppression-
mechanism content (§5.4):

- **Placement A** evaluates a single named methodology
  (framing-time-pressure-prediction-through-absence)
  promoting to named methodology in
  `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` at three-
  instance corroboration. PR 13's ABSENCE-evidence
  contribution (if outcomes are ABSENCE across all three
  forms) directly contributes to the third-instance bar.

- **Placement B** evaluates the broader methodology-stack
  architecture claim (causal absence as peer-class evidence
  to resistance-evidence) promoting to named methodology-
  stack architecture at three-precondition operational
  manifestation across three independent divergence
  dimensions. PR 13's manifestation of the three preconditions
  (predictions + mechanisms + recurrence-substrate
  contribution) registers regardless of whether PR 13's
  outcomes are ABSENCE or SURFACE.

The two placements are **not redundant** — Placement A
corroborates a specific named methodology; Placement B
claims the methodology-stack architecture should classify
causal-absence as peer-class evidence. They promote
independently per Gate 4 framing §5.9 + §6.4.

### 6.4 Evidence inflation rejection as PR 13 framing discipline

The 1-test count + 1-fixture count + single-direction
substrate decisions (§5.1 + §5.2) are themselves Placement
B substrate evidence operating at framing time. The
framing recognized:

- "Add the inverse-direction test for thoroughness" =
  evidence inflation candidate at framing time.
- Suppression mechanism: PR 10 §4.2 binding's direction-
  symmetric construction.
- Outcome at framing time: the inverse-direction case was
  predicted as plausible cleanup pressure, the suppression
  mechanism was named, and the variant was rejected pre-
  emptively.

**This pattern is the framing-time form of the very
methodology-stack maturation Placement B encodes.** The
framing-time recognition + suppression + rejection is causal-
absence-under-framing-shaped-constraint operating one
abstraction level higher than the implementation-time
manifestation Placement A measures.

PR 13 framing's §4.4 + §5.2 evidence-inflation rejection
is recorded as PR-13-framing-time absence-evidence
contribution to a meta-Placement-B substrate (the framing
itself constraining its own evidence-inflation pressure).
This is the operational discipline observation Placement B
predicts at the gate level operating at the framing-pass
level.

---

## 7. Non-acquisition commitments

PR 13 explicitly does **not**:

1. **Author multi-vector fixture pressure.** PR-13-LOCAL
   binding (§0 + §5.5). The fixture isolates ordering
   divergence as the sole pressure vector.

2. **Author the inverse-direction test variant** at PR 13
   framing time. Evidence inflation rejection (§4.4 + §5.2).
   If review pressure surfaces the variant as genuinely
   architecturally distinct, addition registers as drafting-
   time amendment per canonicalized cadence.

3. **Author multi-permutation variants** (e.g.,
   `[A, C, B]`, `[B, A, C]`). Pure permutation behavior is
   implicit in PR 10 §4.2 binding (§2.2).

4. **Modify the comparator surface** (`compare_records` /
   `DivergenceReport` / `ComparatorInputError`). §5.7
   binding + Gate 4 framing §5.3 + §7 item 3 inheritance.

5. **Add a "while we're here, also test subset mismatch"
   element.** PR-13-LOCAL binding (§0 + §5.5). Partial-narrow
   pressure is PR 14's substrate.

6. **Add a "while we're here, also test duplicate handling"
   element.** PR-13-LOCAL binding. Duplicate handling is
   not in Gate 4 scope.

7. **Add a "while we're here, also test semantic
   normalization" element.** PR-13-LOCAL binding. Semantic
   normalization is not in Gate 4 scope.

8. **Modify existing PR 9 fixtures.** Gate 4 framing §7
   item 10 + Gate 3 close §3 item 1 non-revisitable.

9. **Re-author `_apply_pr9_patches` or `_read_records`**
   with modified semantics. PR 11 spec §4.1.2 + Gate 3
   close §2.2 inheritance — the imports are stable
   consumption surfaces.

10. **Promote PR 9 underscored helpers to public APIs.**
    PR 11 spec §4.1.2 + Gate 3 close §3 item 9 inheritance.

11. **Introduce a test-helper function** that absorbs the
    recomposition traversal. PR-11-LOCAL discipline at gate
    level (Gate 3 close §3 item 10) + this §5.4 predicted-
    form 3 suppression.

12. **Introduce caller-side canonicalization** (sort,
    normalize) before invoking `compare_records`. PR 10
    §4.2 binding + §5.4 predicted-form 1 suppression.

13. **Use set-equality assertion shortcuts** (e.g.,
    `assert set(observed) == set(expected)`) in PR 13 test
    body. §5.4 predicted-form 2 suppression — assertions
    read the four-key DivergenceReport shape at full
    structural fidelity.

14. **Introduce a new `record_kind`.** Gate 4 framing §7
    item 4 + Gate 3 close §3 item 1 non-revisitable.

15. **Extend `KNOWN_SOURCE_VALUES`.** Gate 4 framing §7
    item 5 + Gate 3 close §3 item 1 non-revisitable.

16. **Modify the expectation record schema** (3 required
    keys). Gate 4 framing §7 item 6 + Gate 3 close §3 item 1
    non-revisitable.

17. **Modify the three-authority-surface partition.** Gate 4
    framing §7 item 7 + Gate 3 close §3 item 1 non-revisitable.

18. **Author a fifth walker.** Gate 4 framing §7 item 9.

19. **Add cleanup-pressure-resistance class members
    speculatively** at framing time. Gate 4 framing §3.4 +
    §7 item 21. Class members surface at PR 13 close based
    on actual implementation pressure encountered.

20. **Introduce a candidate carrier (#18) at PR 13.** Gate 4
    framing §3.1 + §6.1 + §7 item 13 non-acquisition. PR 13
    inherits Gate 4's no-new-carriers discipline.

21. **Speculatively author a Gate-4-LOCAL governing
    sentence.** Gate 4 framing §7 item 22 non-acquisition.

22. **Pre-bind Placement A outcome predictions** at PR 13
    framing. The prediction discipline (§5.4) is
    operationally separate from the outcome (recorded at
    close). Pre-binding outcomes at framing constitutes
    Placement B precondition 1 violation (retrospective
    prediction-construction).

23. **Pre-bind PR 12 disposition** at PR 13 framing. Gate 4
    framing §5.10 binding — PR 12 disposition belongs at
    Gate 4 close. PR 13 implementation contributes call-
    site count toward cumulative ≥4 threshold evaluation but
    does NOT pre-bind disposition outcome.

24. **Touch the Layer 3 lint** (`test_pr6_visual_asymmetry.py`).
    PR 13 substrate is not an emission surface.

25. **Modify `divergence_capture_enabled()` or its env-gate.**
    Carrier #5 protection preserves (Gate 3 framing §7
    item 8).

26. **Extend `_KNOWN_RECORD_KINDS`.** Two-element lock
    non-revisitable.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` unchanged

PR 13 introduces NO new comparator-side imports or new
production-surface imports. The Layer 1 `_ALLOWLIST` (PR 4
narrowing-subsystem production import topology) preserves
unchanged at PR 13.

### 8.2 Layer 2 — four-walker partition unchanged

The four-walker partition (PR 4 + PR 8 + PR 9 + PR 10)
preserves unchanged at PR 13. Gate 4 framing §3.3 + §7
item 9 non-acquisition binds.

**PR-13-relevant walker:** PR 9 walker
(`_FIXTURE_PERMITTED_IMPORTS` value-locked) operates against
PR 13's new fixture (`fix_ordering_divergence.py`).
The fixture's imports must satisfy the single-symbol-gate
constraint per member #9.

**PR-13-irrelevant walkers:** PR 4 walker (PR 13 does not
modify narrowing subsystem); PR 8 walker (PR 13 does not
modify `_seed.py`); PR 10 walker (PR 13 does not modify
`_compare.py`).

### 8.3 Layer 3 — unchanged

PR 13 substrate is not an emission surface; Property A–D
visual asymmetry lint is not exercised.

---

## 9. Phase-end conditions for PR 13

PR 13 closes when the following conditions are met (close
verification checklist surface):

### 9.1 Test count anchor — 218 forge env collected

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
218 tests collected in 0.04s
```

**Arithmetic (binding):** 217 baseline (PR 11 close) + 1
PR 13 new = **218 forge env collected at PR 13 close**.

If the actual count diverges from 218 at verification,
recount at close + reconcile arithmetically per
`feedback_counts_are_archaeology_grade`. Divergence almost
certainly indicates one of: (a) PR 13 added more tests than
the 1-test count locked (violates §5.2); (b) PR 13 added
the same test as parametrize variants (collected count
> named count); (c) test-collection picked up an unrelated
test addition (rare; investigate). Verify expected count
matches actual at close.

### 9.2 PR 13 suite regression — 1/1 passed

```
$ python -m pytest tests/corpus/test_pr13_ordering_divergence.py
======================== 1 passed, 1 warning in 0.10s =========================
```

PR 13 suite: **1/1** ✓ at close verification.

Full corpus suite execution at PR 13 close: `218/218 passed`.
Zero regressions inherited from PR 13's substrate addition.

### 9.3 0-prod-mod outcome verified

```
$ git diff --stat <PR-13-framing-commit>..HEAD -- forge_bridge/
(empty)
```

PR 13 close arithmetic: **0 production source modifications**.
Architectural sufficiency signal target met. PR 13 contributes
the first Gate 4 instance toward 0-prod-mod-as-architectural-
sufficiency-signal candidate methodology (Gate 4 framing
§3.6 + §11.5).

If non-empty: justified-deviation archaeology per §5.10
protocol.

### 9.4 Predicted cleanup-pressure form outcomes recorded

PR 13 close §1 (or equivalent) records the outcome per
predicted form (per §5.4 + §6.1):

| Form | Outcome | Placement A contribution |
|---|---|---|
| Canonicalization pressure | ABSENCE / SURFACE | (per outcome) |
| Set-equality collapse pressure | ABSENCE / SURFACE | (per outcome) |
| Ordering-specific test helper pressure | ABSENCE / SURFACE | (per outcome) |

The record is structural; PR 13 close evaluates Placement A
contribution at this surface. Gate 4 close reads cumulative
contribution across PR 13 + PR 14 + PR 15.

### 9.5 Placement B precondition operational manifestation recorded

PR 13 close records (per §6.2):

- **Precondition 1 (prior pressure prediction at framing
  time):** Manifest at PR 13 framing §5.4 — three predicted
  forms authored at framing-time.
- **Precondition 2 (named suppression mechanism):** Manifest
  at PR 13 framing §5.4 — each form paired with named
  suppression mechanism.
- **Precondition 3 (corroborated recurrence):** PR 13
  contributes one independent-conditions instance;
  cumulative manifestation requires PR 14 + PR 15.

The record is structural; PR 13 close confirms the framing-
time manifestation of preconditions 1 + 2 (no retrospective
construction). Gate 4 close evaluates cumulative manifestation
of precondition 3.

### 9.6 Module docstring carrier travel verified

PR 13 test module + fixture module docstrings carry:

- 17 active carriers verbatim (per §3.1).
- PR-13-LOCAL binding statement verbatim (per §0 + §5.5).

§2.4 architectural commitment does NOT appear in test/fixture
docstrings per §3.6 (relaxed travel discipline). Verified at
close.

### 9.7 §2.4 architectural commitment travel verified

§2.4 sentence appears verbatim at:

- PR 13 spec §2 architectural commitment section.
- All three PR 13 step commit message bodies under
  "architectural commitment" section.
- PR 13 close artifact §1 + §6.5 (or equivalent).

Verified at close.

### 9.8 Public API anchor — `forge_bridge.__all__` at 19 symbols

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

§5.8 binding preserved at close.

### 9.9 Imports-land-when-used discipline verified (member #10)

PR 13 close verifies the discipline at **both new module
files** symmetrically:

- **Step 1 commit** had `from __future__ import annotations`
  only in `test_pr13_ordering_divergence.py` AND
  `fix_ordering_divergence.py`. No other imports landed at
  Step 1 (both files at skeleton state).
- **Step 2 commit** landed imports + bodies simultaneously
  for both files: test module landed its 5-import block
  (pathlib + pytest + comparator + seed + fixture aliasing +
  PR 9 archaeology imports) alongside the test body;
  fixture module landed its `FIXTURE` dict alongside (the
  fixture module's only "import" remains
  `from __future__ import annotations` carried from Step 1
  — fixture-data-discipline member #9 prevents any other
  imports). Each import is consumed by code added in Step 2
  (no speculative-reserved imports).
- **Step 3** added zero imports (empty commit; archaeology
  in body only).

The imports-land-when-used pattern is class member #10
protection (Gate 3 close §1.5 + Gate 4 framing §3.4). PR 13
close §1 records the discipline operationally enforced at
both files symmetrically — the symmetry itself is a
file-lifecycle invariant (§9.12).

### 9.10 Cleanup-pressure-resistance class additions registered

If PR 13 implementation pressure surfaced a new candidate
class member meeting the four-criterion standard (genuine
cleanup pressure / prevented real erosion / recurred
independently / required active enforcement), PR 13 close
§1 inventories the candidate. Gate 4 close §1 evaluates
class extension cumulatively across all three primary PRs.

### 9.11 Test-internal archaeology surfaces inheritance verified

PR 13 close §1 records:

- `_apply_pr9_patches` consumed unchanged from
  `test_pr11_recomposition_arc.py`.
- `_read_records` consumed unchanged.
- Neither helper modified at PR 13.

Per PR 11 spec §4.1.2 + Gate 3 close §2.2 + Gate 4 framing
§3.7 inheritance.

### 9.12 Step archaeology summary

PR 13 close §4 (or equivalent) inventories the 3-step
PR 13 commit chain. The step structure mirrors PR 11's 3-step
PR 11 pattern verbatim (skeleton → architectural-center →
empty verification), preserving the implementation-cadence
methodology substrate (repetition under changing pressure is
corroboration).

**Both-skeletons-at-Step-1 lock (binding):**

PR 13 introduces **two** new files (test module + fixture
module). Both files pass through the same lifecycle
transition: **establishment → activation**. The lifecycle
invariant is preserved across both files:

| Step | Test module state | Fixture module state |
|---|---|---|
| 1 (skeleton) | Module docstring (carriers + PR-13-LOCAL + traversal trace + references); `from __future__ import annotations` only; no test bodies, no constants, no other imports | Module docstring (carriers + PR-13-LOCAL + fixture purpose + references); `from __future__ import annotations` only; no `FIXTURE` dict declaration |
| 2 (architectural-center) | Imports landed + test body landed (single commit) | `FIXTURE` dict landed (single commit) |
| 3 (verification) | No changes (empty commit) | No changes (empty commit) |

**Why both-skeletons-at-Step-1 matters:**

- **Lifecycle-invariant preservation.** Both files undergo
  the same establishment → activation transition. Asymmetric
  treatment (one file skeleton-then-body, the other file
  whole-at-once) would introduce an unnecessary second axis
  of variation into PR 13's archaeology and weaken the
  skeleton/body discipline's meaning at the per-artifact-
  type level.
- **Fixture file as first-class governed surface.** The
  fixture is governed by member #9 fixture-data-discipline
  + Layer 2 walker + PR-13-LOCAL travel discipline. Treating
  it as inline payload bundled into Step 2 would
  opportunistically bypass the skeleton discipline that
  member #9 + Layer 2 expects.
- **Carrier travel symmetry.** Carriers + PR-13-LOCAL travel
  through both module docstrings (§3.1 + §0). Step 1 is the
  surface where docstring + carrier-travel content is
  established + reviewed before functional content lands at
  Step 2. The symmetric Step 1 surface preserves carrier
  travel discipline at both artifact classes.
- **No hidden precedent for fixture-discipline bypass.**
  Asymmetric step structure would establish a precedent —
  "pure-data fixtures can skip skeleton discipline" — that
  PR 14 + PR 15 would inherit. The both-skeletons lock
  prevents the precedent from forming.
- **Gate 4 emphasis fit.** Gate 4 framing's architectural
  thesis is "absence of pressure through explicit shaping
  constraints" (Placement B). The file lifecycle is shaped
  explicitly enough that asymmetry pressure never appears
  during implementation. Same methodology operating at the
  per-PR-step granularity.

**Commit chain (binding):**

| # | Commit | Type | Lines added (approx) |
|---|---|---|---|
| 1 | (TBD at Step 1) | Step 1 — both skeletons (test module + fixture module); docstrings + `from __future__ import annotations` only at each | ~80-130 (both files combined) |
| 2 | (TBD at Step 2) | Step 2 — architectural-center; both files land their bodies in one commit (test module: imports + test body; fixture module: `FIXTURE` dict) | ~100-150 |
| 3 | (TBD at Step 3) | Step 3 — final verification (empty commit; 10-item verification checklist + carriers + PR-13-LOCAL + Placement A/B contribution archaeology in body) | 0 |

Plus PR 13 spec commit (precedes Step 1) + PR 13 framing
commit (precedes spec).

**Step structure asymmetry rejected at framing:**

- **4-step decomposition** (skeleton + fixture-whole + test-
  body + verification) rejected. Would engineer cumulative-
  multi-step architectural concentration evidence into
  existence rather than allowing the candidate methodology
  (Gate 4 framing §3.9 emerging taxonomy) to surface from
  actual implementation pressure. Observations emerge from
  pressure rather than being architected into existence.
- **2-step compression** (combined skeleton + architectural-
  center + drop empty verification) rejected. Would break
  PR 9/10/11 3-step pattern + lose the empty-verification
  surface where verification checklist + Placement A/B
  contribution + carrier travel verification + pressure-
  suppression archaeology become durable.
- **File-asymmetric structure** (test module skeleton at
  Step 1, fixture-whole at Step 2) rejected. Would weaken
  the establishment → activation lifecycle invariant + set
  a fixture-discipline-bypass precedent for PR 14/15.

---

## 10. Cross-references

- **`A.5.3.2-GATE-4-FRAMING.md`** (`fbf2285`) — **immediate
  predecessor; gate-level inheritance contract PR 13 operates
  against.** §1 + §2 + §3 + §5 + §6 + §10 + §11 load-bearing
  for this framing. §2.4 architectural commitment (binding
  form travels at PR 13 surfaces per §5.6); §3.6 PR 13 sub-
  section (architectural commitment + predicted cleanup-
  pressure forms + suppression mechanisms — this framing
  expands at framing-level granularity); §5.5 three-PR slot
  structure; §5.6 PR ordering lock; §5.8 Placement A target;
  §6.3 Placement B claim; §7 22 non-acquisition commitments
  inherited.
- **`A.5.3.2-GATE-3-CLOSE.md`** (`ee2225b`) — gate-level
  inheritance contract for Gate 4 + PR 13 inherits
  transitively. §1.5 cleanup-pressure-resistance class
  promotion (10 members); §1.6 carrier #16 promotion; §1.7
  §5.3 candidate methodology two-instance corroboration
  (PR 13 Placement A target inherits); §2 Gate 4 inheritance
  contract; §3 13 non-revisitable items; §6 four §7.3
  ontological questions handed forward.
- **`A.5.3.2-PR11-CLOSE.md`** (`ee2225b`) — recomposition
  arc operational evidence; PR-11-LOCAL traverses-not-erases-
  seams discipline (inherited at gate level per Gate 3 close
  §3 item 10 + Gate 4 framing §3.7); zero-incarnation-
  amendments cleanest arc (PR 13 framing-spec-drafting-time
  catch-point inherits); 217 forge env baseline (PR 13 close
  arithmetic: 217 + 1 = 218).
- **`A.5.3.2-PR10-CLOSE.md`** (`cf2b7ee`) — comparator surface
  operational; PR 10 spec §4.1.6 reference implementation
  (preserved at PR 13); PR 10 §4.2 binding behavioral
  commitment ("compare as persisted") — **the central
  architectural commitment PR 13 exercises**; class member
  #10 (imports-land-when-used; operationally enforced at
  PR 13).
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — three-fixture corpus
  + fixture naming convention PR 13 inherits; PR 9 walker
  + member #9 protection (operationally enforced at PR 13
  fixture); test-internal archaeology surfaces
  (`_apply_pr9_patches`, `_read_records`) PR 13 consumes
  unchanged.
- **`A.5.3.2-GATE-3-FRAMING.md`** (`2f70cbf`) — Path B locked
  precedent; binding framing clarification on cross-surface
  unbinding (preserved at PR 13 inheritance via Gate 4
  framing §5.2).
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — gate-arc
  synthesis precedent; §7.3 four ontological questions
  (preserved unbound at PR 13 inheritance).
- **`A.5.3.2-GATE-2-FRAMING.md`** (`ceac9b5`) — three-
  authority-surface partition (preserved at PR 13
  inheritance); call-site-owned arbitration inputs binding
  clarification (preserved).
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — PR-INTERNAL three-
  way authority partition (write-side §4.1.5.1) preserved
  at PR 13 inheritance; carrier #15 source; member #7 +
  member #8.
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — observation +
  dispatch-provenance surfaces; class members #1–#6.
- **`A.5.3.2-FRAMING.md`** — phase shape, objective lock.
- **`A.5.3.2-INSTRUMENT-CONTRACT.md`** — instrument shape;
  six interlocking structural-invariant pairs.
- **`A.5.3.2-GATE-1-SPEC.md`** — Gate 1 sequencing.
- **`forge_bridge/corpus/_compare.py`** — PR 10 comparator
  module; PR 13 consumes `compare_records` + `DivergenceReport`
  unchanged.
- **`forge_bridge/corpus/_seed.py`** — PR 8 authored
  expectation surface; PR 13 drives through
  `drive_seed_fixture` unchanged.
- **`forge_bridge/corpus/_capture.py`** — PR 7 observation
  surface; PR 13 captures through `emit_divergence_capture`
  unchanged (transitively via `chat_handler`).
- **`tests/corpus/test_pr11_recomposition_arc.py`** — PR 11
  recomposition arc consumption pattern; PR 13 reuses the
  pattern verbatim per Gate 3 close §2.2.
- **`tests/corpus/test_pr10_comparator.py` +
  `test_pr10_comparator_discipline.py`** — PR 10 comparator
  test modules; PR 13 consumes unchanged.
- **`tests/corpus/fixtures/`** — PR 9 fixture corpus
  preserved unchanged; PR 13 adds one new fixture under the
  existing fixture-data-discipline + walker protection.
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; PR 13 contributes
  first-Gate-4-instance toward Placement A (§5.3 candidate
  methodology) third-instance corroboration + Placement B
  three-precondition operational manifestation evaluation.

---

**Framing locks at this commit.** Spec drafting for PR 13
follows per established cadence (framing → spec → spec-
amendments-at-incarnation → 3 steps → close). The four-variant
amendment-at-incarnation cluster + Step N.5 surgical cadence
are available without re-framing. PR-N-LOCAL non-regeneration
discipline preserves (PR-13-LOCAL does not regenerate beyond
PR 13).

**The discipline carries unchanged.** Promotion is earned,
not declared. Speculative authoring of new cleanup-pressure-
resistance class members at framing time is rejected. Counts
are archaeology-grade (1 fixture / 1 test / 3 steps / 218
forge env target). Ground specs in actual files (PR 13 spec
reads PR 9 fixtures + PR 11 test patterns + PR 10 comparator
reference implementation before locking specific values).
Lead with views at structural seams. Evidence inflation is
rejected. Observations emerge from pressure rather than
being architected into existence.
