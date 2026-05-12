# A.5.3.2 PR 14 — Framing (partial-set divergence as Gate 4 calibration exercise)

**Status:** PR 14 opens at `f53a469` (local main, PR 13
closed). This framing locks the architectural posture for the
partial-set divergence exercise — Gate 4's second primary PR
+ the second calibration substrate for Placement A + Placement
B operational corroboration — and the binding decisions
reached during the PR 13 close → PR 14 framing convergence
pass.

PR 14 is the second of three primary PRs sequenced within
Gate 4 per Gate 4 framing §5.5 + §5.6. The three-PR slot
structure (PR 13 ordering → PR 14 partial-narrow → PR 15
multi-survivor mismatch) is locked at Gate 4 framing §5.5;
PR 14 framing operates against the locked sequence + ordering.

The convergence pass produced five binding decisions: PR 14
ships exactly one new fixture (filename
`fix_partial_narrow_divergence.py`; `fixture_id` field
`fix-pr14-partial-narrow-divergence`; module export `FIXTURE`
per PR 9 canonical convention) + exactly one new test
(`test_recomposition_arc_partial_narrow_divergence`) — single-
vector, single-direction (authored-superset), single-instance
of the partial-set divergence calibration exercise (§5.1 +
§5.2 binding); 0 production source modifications is the
architectural sufficiency signal target inherited at gate
level from Gate 4 framing §2.2 (§5.3 binding); three predicted
cleanup-pressure forms enumerated with named suppression
mechanisms (§5.4 binding, Placement A + B substrate); one
PR-14-LOCAL binding statement (§0 + §5.5) — partial-set
isolation discipline rejecting multi-vector fixture pressure
(references PR-13-LOCAL as PR-of-origin for the pure-isolation
pattern per PR 13 close §2.2); **the authored-superset
direction is an affirmative architectural decision** (§5.10)
— the overlap-interpretation pressure vector is direction-
symmetric, so the inversion of Gate 4 framing §10's example
sketch is the stronger architectural move for PR 14's specific
calibration role within the three-PR series.

**Active carrier count at PR 14 open: 17.** Composition
unchanged from Gate 4 framing §3.1 + PR 13 inheritance: 15
inherited carriers (#1–#15) + carrier #16 (active, promoted at
Gate 3 close) + carrier #17 (active from Gate 3 framing). PR
14 introduces NO new carriers; the no-new-carriers discipline
preserves from Gate 4 framing §3.1 + §6.1 + PR 13 framing
§3.1.

**Reference discipline (binding):** *"17 active carriers"* is
the canonical reference. The candidate-substrate marking
discipline retired at Gate 3 close; PR 14 surfaces travel
carriers in natural numeric ordering without substrate
marking, citing by reference to canonical sources per PR 13
framing §3.1 citation-by-reference precedent.

---

## 0. PR-14-LOCAL binding statement — pure-isolation discipline

One sentence governs PR 14 verbatim. It appears at the top
of the PR 14 test module docstring + PR 14 fixture module
docstring + PR 14 commit message bodies under "preserved
invariants."

**PR-14-LOCAL binding statement — partial-set isolation:**

> **PR 14 isolates partial-set divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 14 scope —
> combining partial-set with ordering, semantic-normalization,
> duplicate-handling, multi-survivor-cardinality, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 14 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

This is the operational discipline statement governing PR 14
implementation. PR 14's evidentiary value depends entirely on
single-vector isolation: if multi-vector pressure surfaces
within the fixture or the test, attribution from observed
outcomes to the single shaping constraint becomes impossible,
and the absence-evidence loses its methodology-corroboration
weight.

**Why "laboratory-grade":**

The vocabulary is deliberate and inherits the framing PR 13
established. PR 14 IS a pure-isolation case — its partial-set
vector operates at the comparator's interpretive layer
without ordering, semantic-normalization, duplicate, or
multi-survivor-cardinality confound. The authored expectation
preserves the shared elements at their observed positions
verbatim (no ordering confound); the partial-set extension
element shares no tokens with the prompt (no semantic-
normalization confound); each list contains distinct elements
(no duplicate confound); both lists are multi-element with
non-trivial overlap (no multi-survivor-cardinality confound —
that pressure surface is PR 15's substrate).

PR 14's partial-set-only-vector property is the second
calibration point in the three-PR series; the cumulative
calibration arc (PR 13 ordering / PR 14 partial-set / PR 15
multi-survivor) gives Placement A + Placement B operational
corroboration substrate at three independent-conditions
substrates before Gate 4 close evaluates promotion candidacy.

**Why PR-14-LOCAL is non-regenerating:**

Per the PR-N-LOCAL non-regeneration rule (Gate 2 framing
§3.1) + PR 13 framing §0 inheritance, PR-14-LOCAL is scope-
local. It does NOT travel to PR 15 surfaces — PR 15 authors
its own PR-N-LOCAL binding appropriate to its multi-survivor
mismatch divergence dimension. The non-regeneration is the
discipline; PR 15 inheriting "partial-set isolation" verbatim
would be category error since PR 15's substrate is not partial-
set-isolated (it implicates cardinality-class ambiguity
topology).

**PR-13-LOCAL as PR-of-origin (pure-isolation pattern):**

PR-13-LOCAL is the PR-of-origin for the pure-isolation
discipline pattern (per PR 13 close §2.2). PR-14-LOCAL is
parallel scope-local — it authors its own discipline statement
appropriate to partial-set divergence rather than regenerating
PR-13-LOCAL's ordering-isolation form. The pattern (single-
vector fixture pressure as laboratory-grade calibration
substrate) inherits as architectural-substrate evidence; the
specific PR-N-LOCAL statements are non-regenerating scope-
local bindings.

**Travel discipline at PR 14:**

PR-14-LOCAL appears at:

- `tests/corpus/test_pr14_partial_narrow_divergence.py` module
  docstring (Step 1 surface).
- `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
  module docstring (Step 2 surface, when authored).
- All PR 14 commit message bodies under "preserved
  invariants" / "PR-14-LOCAL" sections.
- This framing artifact §0 (verbatim form above).

**No Gate-4-LOCAL governing sentence accompanies PR-14-
LOCAL.** Gate 4 framing §3.1 + §6.1 + §7 item 22 explicitly
rejected speculative Gate-4-LOCAL authoring; PR 13 framing §0
preserved the rejection; PR 14 framing inherits the rejection
unchanged. The §0 carries PR-14-LOCAL alone.

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
  convention** PR 14 inherits; PR 9 integration test
  infrastructure (`_apply_pr9_patches`, `_read_records`) PR 14
  reuses as test-internal archaeology surfaces; **multi-match
  arbitration trace** at `fix_multi_match.py:105-140` PR 14
  inherits as observation-emission grounding.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis;
  four §7.3 ontological questions unbinding (preserved at
  PR 14 inheritance via Gate 4 framing §5.2).
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — Path B locked
  precedent; binding framing clarification on cross-surface
  unbinding (preserved at Gate 4 inheritance + PR 14
  inheritance).
- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — comparator surface
  operational; `compare_records` + `DivergenceReport` +
  `ComparatorInputError` (PR 10 spec §4.1.6 reference
  implementation) PR 14 consumes unchanged; **§4.2 binding
  behavioral commitment ("compare as persisted")** is the
  central architectural commitment PR 14 exercises under
  partial-set divergence pressure; class member #10.
- `A.5.3.2-PR11-CLOSE.md` (`ee2225b`) — recomposition arc
  operational end-to-end; **PR-11-LOCAL traverses-not-erases-
  seams discipline** applied at gate level (Gate 3 close §3
  item 10) — PR 14 inherits the discipline as gate-level
  constraint, not PR-11-LOCAL regeneration; zero-incarnation-
  amendments cleanest arc; §5.3 candidate methodology
  second-instance ABSENCE outcome.
- `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`) — gate-arc synthesis;
  carrier #16 promotion; cleanup-pressure-resistance class
  promotion to named methodology (10 members); 17 active
  carriers; four-walker Layer 2 partition operational;
  conditional PR 12 DEFER; four §7.3 ontological questions
  hand forward to Gate 4 (preserved at PR 14 inheritance).
- `A.5.3.2-GATE-4-FRAMING.md` (`fbf2285`) — gate-level
  inheritance contract PR 14 operates against. §2.4
  architectural commitment ("Gate 4 is the deliberate
  continuation of empirically bounded topology proof through
  divergence-shape robustness exercise"); three-PR primary
  slot structure locked (§5.5); PR ordering locked (§5.6);
  **§10 PR 14 sub-section provides the architectural
  commitment + predicted cleanup-pressure forms + suppression
  mechanisms PR 14 framing builds on**; Placement A
  operational corroboration target (§5.8 + §6.2); Placement B
  methodology-stack maturation claim with three causality
  preconditions (§4.4 + §4.5 + §6.3); §7 22 non-acquisition
  commitments PR 14 honors at gate level.
- `A.5.3.2-PR13-FRAMING.md` (`8f429b2`) — **first-of-three
  primary PR framing precedent.** PR 13's 11-section framing
  shape (§0–§10 inclusive) + 9-surface PR-LOCAL travel
  inventory (per PR 13 close §1.4 close-time inventory) +
  8-surface §2.4 architectural commitment travel inventory
  (per PR 13 close §1.5; framing surfaces deliberately
  excluded from the close inventory) + three-predicted-
  cleanup-pressure-forms-with-named-suppression-mechanisms
  pattern + evidence inflation rejection discipline + both-
  skeletons-at-Step-1 lifecycle invariant all inherit as
  framing-shape precedent at PR 14. Citation-by-reference
  discipline (carriers + bindings travel via canonical-source
  references rather than verbatim repetition) inherits as
  framing-artifact-content discipline.
- `A.5.3.2-PR13-SPEC.md` (`2e05149`) — fixture +
  test implementation contract precedent. PR 14 spec drafting
  inherits the 11-section spec shape + locked-mergeability-
  anchors table + citation-by-reference interpretation +
  travel-discipline-asymmetry table + both-skeletons-at-Step-1
  lifecycle lock as spec-shape precedent.
- `A.5.3.2-PR13-CLOSE.md` (`f53a469`) — **immediate
  predecessor; the calibration substrate PR 14 builds on at
  the second calibration point.** PR 13 close's 0-prod-mod
  outcome + 3-form-ABSENCE Placement A contribution +
  Placement B preconditions 1+2 manifestation + catch-point
  migration instance #5 single-corroboration + cleanup-
  pressure-resistance class 10 members unchanged + PR-13-LOCAL
  pure-isolation discipline operational verification all
  inherit as predecessor archaeology. **PR-13-LOCAL is now
  PR-of-origin archaeology** (PR 13 close §2.2) — PR 14
  authors PR-14-LOCAL as parallel scope-local discipline
  appropriate to partial-set divergence. **The both-skeletons-
  at-Step-1 lifecycle invariant is now PR-of-origin
  archaeology** (PR 13 close §2.4) — PR 14 inherits the
  invariant if it ships multi-file PRs (it does: one fixture
  + one test).
- **PR 13 close → PR 14 framing convergence pass (this
  session):** five binding decisions locked (PR-14-LOCAL
  binding statement authored at framing-level decision; fixture
  + test name + count locked at one of each; 0-prod-mod target
  inherited from Gate 4 with explicit deviation protocol;
  three predicted cleanup-pressure forms enumerated with named
  suppression mechanisms for Placement A + B substrate;
  authored-superset direction as affirmative architectural
  decision per the overlap-interpretation pressure being
  direction-symmetric). The convergence pass surfaced **the
  single-variable discipline across PR 9 / PR 13 / PR 14** as
  load-bearing architectural-substrate evidence (the comparator
  surface becomes the only moving interpretive layer across
  the three-PR series — prompt, reachable-tool set,
  arbitration trace, and observation emission path all hold
  constant; only the authored expectation varies); **the
  authored-superset direction** as the stronger architectural
  move (Direction A over Direction B per the single-variable
  discipline + the overlap-interpretation direction-symmetry
  argument); **the `"list"`-as-calibration-prompt** archaeology
  spanning three independent reliability PRs (PR 9 no-
  divergence baseline / PR 13 ordering / PR 14 partial-set) as
  becoming known-good substrate within Gate 4.

---

## 2. PR 14 objective

### 2.1 The narrow architectural question

PR 14 isolates a single architectural question:

> **Does the recomposition arc's interpretive layer preserve
> partial-set divergence faithfully — surfacing the structural
> partial-match shape at the DivergenceReport without
> conflating partial-match with full-divergence and without
> normalizing the superset-subset relationship into a binary
> outcome?**

The question is narrow by construction. PR 14 does not
exercise the comparator under multi-vector pressure (those
substrates are PR 15 + future work) and does not introduce
new comparator surface (Gate 4 framing §5.3 + §7 item 3 non-
acquisition). PR 14 exercises the **PR 10 §4.2 binding
behavioral commitment ("compare as persisted") under partial-
set divergence pressure** by:

1. Authoring an `expected_narrow` list containing the
   observation's two members PLUS one additional tool that is
   not present in the observation (authored-superset
   direction, per §5.10 affirmative architectural decision).
2. Driving the fixture through the PR 11 recomposition arc
   (`_apply_pr9_patches` → `drive_seed_fixture` → emission →
   persistence → `_read_records` → partition → `compare_records`).
3. Asserting the DivergenceReport contains the partial-set
   shape at full fidelity: `narrow_diverged=True` and both
   the expectation's and observation's `expected_narrow` /
   `observed_narrow` lists preserved verbatim (the partial-
   match structure surfaces at the structural shape level
   without normalization).

The expected outcome: the recomposition arc returns a
DivergenceReport with `narrow_diverged=True` and verbatim list
values reflecting the partial-match structure. The comparator
detects the divergence via direct list-equality at
`_compare.py:503` (`obs_decision != exp_narrow`) — the list
length asymmetry + element membership asymmetry at the third
authored position both contribute to the inequality. No caller-
side normalization, no `partial_match` field synthesis, no
overlap-aware helper field on the DivergenceReport.

### 2.2 What PR 14 ships

PR 14 ships **one new fixture file** + **one new test module**.
Both files are new — PR 14 introduces no production-source
modifications, no comparator surface changes, no new public
API symbols.

**File 1: `tests/corpus/fixtures/fix_partial_narrow_divergence.py`**

A new seed fixture in the PR 9 fixture-data-discipline
convention (per cleanup-pressure-resistance class member #9 +
Gate 4 framing §9.6 binding). The fixture authors a partial-
set divergence: the same prompt `"list"` + the same `_PR9_REACHABLE_TOOLS`
reachable-tool set as PR 9 multi-match (and as PR 13 ordering-
divergence). The arbitration pipeline produces the same
deterministic observation as PR 9 multi-match + PR 13. The
fixture's contribution is the authored expectation:

```python
FIXTURE: dict = {
    "fixture_id": "fix-pr14-partial-narrow-divergence",
    "prompt": "list",
    "expected_narrow": [
        "forge_list_projects",
        "flame_list_libraries",
        "forge_ping",
    ],
}
```

The authored expectation contains the observation's two
members at positions 0+1 verbatim (no ordering confound)
PLUS `forge_ping` at position 2 as the partial-set extension
element. `forge_ping` is in the PR 9 reachable-tool set but
shares no tokens with the prompt `"list"` (no semantic-
normalization confound).

**File 2: `tests/corpus/test_pr14_partial_narrow_divergence.py`**

A new pytest test module containing **exactly one named test
function**: `test_recomposition_arc_partial_narrow_divergence`.
The test exercises the recomposition arc end-to-end and
asserts the DivergenceReport at full structural fidelity (four-
key shape preserved; the partial-match structure surfaces at
the structural list values).

The 9-step traversal annotation pattern PR 13 introduced
(per `test_pr13_ordering_divergence.py:150-203`; six header
comments covering nine logical traversal steps) inherits at
PR 14: each step of the traversal is explicitly annotated at
the call site; no helper absorbs the arc.

### 2.3 Gate 4 calibration role

PR 14 is the **second calibration point** in the three-PR
Gate 4 series (first: PR 13 ordering divergence; second: PR 14
partial-set divergence; third: PR 15 multi-survivor mismatch).

PR 14's calibration role within Gate 4:

- **Pure-isolation discipline at the second substrate.** PR 14
  authors a single-vector fixture under partial-set pressure
  while preserving pure-isolation at every other dimension
  (ordering / semantic-normalization / duplicates / multi-
  survivor-cardinality). The discipline tested is identical
  to PR 13's (laboratory-grade single-vector pressure as
  Placement A + Placement B substrate) under a different
  pressure vector.

- **The architectural commitment under partial-set pressure.**
  The recomposition arc's preservation of authored structure
  through partial-set divergence is the specific exercise.
  The comparator's compare-as-persisted discipline (PR 10 §4.2
  binding behavioral commitment) must detect partial-set
  divergence as `narrow_diverged=True` via direct list-
  equality at `_compare.py:503`. The fixture-data-discipline
  must preserve the authored superset verbatim through the
  emission → persistence → readback path. The four-key
  DivergenceReport assertion must read the partial-match
  structure at full fidelity.

- **Substrate accumulator (second instance).** PR 14's
  predicted-pressure-form outcomes + 0-prod-mod outcome
  accumulate the **second instance** toward cumulative
  Placement A + Placement B evidence; PR 15 adds the third;
  Gate 4 close evaluates the three-instance cumulative.

- **The architectural sufficiency signal escalation.** The
  three-PR Gate 3 escalation (PR 9 + PR 10 + PR 11) became
  four-PR at PR 13 close. PR 14 extends to five-PR if the
  0-prod-mod target holds. Gate 4 close evaluates the
  cumulative architectural-sufficiency-signal evidence at
  five-PR escalation per Gate 4 framing §6 + Gate 3 close §3
  item 11.

### 2.4 PR 14 in the three-PR sequence

PR 14 is **second** in the three-PR primary sequence per
Gate 4 framing §5.6:

| # | Dimension | Pure-isolation? | Calibration role |
|---|---|---|---|
| PR 13 | Ordering divergence | Yes — single vector, no confound | Calibration first (closed) |
| **PR 14** | **Partial-set divergence (authored-superset)** | **Yes — single vector, pure-isolation at every non-target dimension** | **Calibration second (this PR)** |
| PR 15 | Multi-survivor mismatch | No — implicates cardinality + ambiguity-class | Ambiguity topology under most adversarial recomposition pressure |

A note on the table's pure-isolation column. Gate 4 framing
§4.2 dimension 2 originally described partial-narrow as
"implicating cardinality + presence-absence" — language
suggesting an inherent confound. **PR 14 framing rejects the
confound framing for the authored-superset direction.** Per
§5.10 affirmative architectural decision below: the authored-
superset form makes partial-set divergence operationally
pure-isolation because the shared elements preserve at their
observation positions verbatim (no ordering vector engaged)
and the partial-set extension element shares no prompt tokens
(no semantic-normalization vector engaged). The cardinality
asymmetry IS the partial-set vector itself, not a separate
confound. Gate 4 framing §4.2's "implicating cardinality"
language anticipates the Direction-B variant (authored subset
vs observed superset, requiring a 3+-survivor prompt
topology) where the new prompt + new reachable-set behavior
would constitute additional moving axes. Direction A reuses
PR 9 + PR 13 arbitration substrate verbatim, eliminating
those moving axes.

PR 14's role within the sequence:

- **Calibration second.** PR 14 establishes that the validated
  recomposition arc preserves authored structure through a
  second pure-vector pressure. Without PR 14's calibration,
  PR 15 outcomes under multi-survivor mismatch (the inherently
  multi-vector substrate) would not have a partial-set
  baseline to compare against. The three-point calibration
  arc gives Placement A + Placement B operational
  corroboration substrate at three independent-conditions
  pressure surfaces.

- **Substrate accumulator (second instance).** PR 14's
  predicted-pressure-form outcomes + 0-prod-mod outcome
  accumulate the second instance toward cumulative Placement A
  + Placement B evidence; PR 15 adds the third; Gate 4 close
  evaluates the three-instance cumulative.

- **Cadence anchor preservation.** PR 14's 3-step PR 11-pattern
  cadence preserves the operational shape PR 13 established
  + PR 15 inherits. Repetition of the cadence under different
  divergence pressures is corroboration of the cadence itself
  as methodology substrate (Gate 4 framing §3.5 + PR 13 close
  §4 archaeology).

- **Single-variable discipline propagator.** PR 14 propagates
  the single-variable discipline (prompt + reachable-set +
  arbitration trace + observation all constant across the
  series; only authored expectation varies) from PR 9 + PR 13
  to the second-PR scope. PR 15 will break the discipline
  by necessity (multi-survivor mismatch requires either a
  different prompt or different reachable-set semantics); PR
  14 is the last PR within Gate 4 where the discipline can
  hold cleanly. This makes PR 14's calibration-substrate role
  architecturally load-bearing in a way that's specific to
  PR 14 (not inherited from PR 13).

---

## 3. Architectural inheritance from Gate 4 + PR 13

### 3.1 17 active carriers + no new carriers at PR 14

PR 14 inherits 17 active carriers unchanged from Gate 4
framing §3.1 + §6.1 + PR 13 framing §3.1 + PR 13 close §1
inheritance:

- Carriers #1–#13 (active; PR 4 + PR 5 + PR 6 lineage).
- Carrier #14 (active; declared epistemic class vs. persisted
  provenance).
- Carrier #15 (active; chat-handler-only seeding scope; third
  clause binding at PR 14 inheritance).
- Carrier #16 (active; *"Reliability work proves topology,
  not infrastructure"*).
- Carrier #17 (active; recomposition discipline).

**PR 14 introduces NO new carriers.** The no-new-carriers
discipline preserves from Gate 4 framing §3.1 + PR 13 framing
§3.1. PR 14 framing does NOT speculatively author Gate-4-LOCAL
governing sentence candidates (rejected by Gate 4 framing §7
item 22) and does NOT author candidate carriers (no
operational basis; candidate-carrier corroboration substrate
is gate-scope, not PR-scope authorship).

The 17 carriers travel by **citation-by-reference** (PR 13
framing §3.1 precedent) at:

- `test_pr14_partial_narrow_divergence.py` module docstring
  (Step 1 surface; citation-by-reference form per PR 13
  precedent).
- `fix_partial_narrow_divergence.py` module docstring (Step 2
  surface, when authored; citation-by-reference form per PR 13
  precedent).
- All PR 14 commit message bodies under "preserved
  invariants."

Citation-by-reference means the docstrings reference canonical
sources rather than reciting carrier content verbatim:

- `forge_bridge/corpus/_capture.py:6-135` — carriers #1–#14 +
  Gate 2 binding framing clarification on call-site-owned
  arbitration inputs.
- `forge_bridge/corpus/_seed.py:19-135` — carrier #15 +
  PR-8-LOCAL bindings.
- `forge_bridge/corpus/_compare.py` module docstring +
  `compare_records` function docstring — carrier #17 +
  PR-10-LOCAL read-only mutability invariant + PR 10 §4.2
  binding behavioral commitment + cross-surface unbinding
  clarification + proactive scope guardrail.
- `A.5.3.2-GATE-3-CLOSE.md` §1.6 — carrier #16.

The PR-N-LOCAL non-regeneration rule preserves — PR-11-LOCAL,
PR-13-LOCAL, PR 10-LOCAL pair-input lock, and PR 9 fixture-
data-discipline contract remain scoped to their respective
surfaces (PR-13-LOCAL is PR-of-origin archaeology per PR 13
close §2.2; PR-14-LOCAL is parallel scope-local discipline at
PR 14 surfaces).

### 3.2 The validated comparator + recomposition arc

PR 14 consumes the PR 10 comparator + PR 11 recomposition arc
unchanged (identical to PR 13's consumption pattern):

- `forge_bridge/corpus/_compare.py` — `compare_records` +
  `DivergenceReport` + `ComparatorInputError` (PR 10 spec
  §4.1.6 reference implementation). **The §4.2 binding
  behavioral commitment ("compare as persisted") is the
  central commitment PR 14 exercises under partial-set
  divergence pressure.** Direct list-equality at
  `_compare.py:503` detects the partial-set divergence
  (`obs_decision != exp_narrow`) — list-length asymmetry +
  element-membership asymmetry at the third authored position
  both contribute to the inequality.
- `tests/corpus/test_pr11_recomposition_arc.py` — recomposition
  arc consumption pattern PR 14 reuses verbatim per Gate 3
  close §2.2 + Gate 4 framing §3.7 + PR 13 framing §3.2. The
  PR 11 nine-step traversal annotation + the underscored-
  private PR 9 imports as test-internal archaeology surfaces
  operate as inherited consumption pattern.

PR 14 ships against the substrate, NOT atop it. Modifications
to the comparator surface or the recomposition arc pattern
are rejected at the spec layer per Gate 4 framing §5.3 + §7
items 3 + 9 + PR 13 framing §3.2.

### 3.3 The PR 9 three-fixture corpus + PR 13 calibration-substrate inheritance

PR 9's three-fixture corpus is preserved unchanged at PR 14
(Gate 4 framing §7 item 10 non-acquisition + PR 13 framing
§3.3 + PR 13 close §1 inheritance). PR 14 extends the
fixtures directory with one new chat-handler-surface fixture
(`fix-pr14-partial-narrow-divergence`) under the existing PR 9
fixture-data-discipline.

**PR 13 calibration-substrate inheritance (NEW at PR 14):**

PR 13 close §2.1 established the ordering-divergence pure-
isolation case as substrate for Gate 4 close's three-PR
cumulative Placement A + Placement B evaluation. PR 14
inherits the calibration-substrate pattern + the specific
substrate elements:

- The single-variable discipline (prompt + reachable-set +
  arbitration trace + observation all constant; only authored
  expectation varies). PR 14 propagates the discipline to
  the second-PR scope.
- The prompt-reuse-without-collision discipline (different
  `fixture_id` discriminator; per-test `tmp_path` isolation).
  PR 14 reuses the same prompt `"list"` as PR 9 multi-match +
  PR 13 ordering-divergence with `fixture_id` =
  `"fix-pr14-partial-narrow-divergence"` (distinct
  discriminator).
- The 9-step traversal annotation pattern (per
  `test_pr13_ordering_divergence.py:150-203`; six header
  comments covering nine logical traversal steps). PR 14's
  test body inherits the pattern, with the four-key
  DivergenceReport assertion at the final step reading the
  partial-match structure at full fidelity.

**Fixture naming convention inherited from PR 9 + PR 13
(grounded from `tests/corpus/fixtures/`):**

PR 14 fixture preserves the two-surface naming convention:

| Surface | PR 14 value | PR 9 + PR 13 convention preserved |
|---|---|---|
| Filename | `fix_partial_narrow_divergence.py` | snake_case; NO PR anchor in filename |
| `fixture_id` field | `"fix-pr14-partial-narrow-divergence"` | kebab-case; WITH PR anchor in field |
| Module symbol export | `FIXTURE` | canonical name across all fixture modules |

(Full discussion of the naming convention's three identity
properties + the test-of-time discipline at PR 9 framing §3.3
+ PR 13 framing §3.3.)

### 3.4 Placement A operational corroboration substrate role

PR 14 contributes the **second instance** to the §5.3 candidate
methodology observation's third-instance corroboration target
at Gate 4 close per Gate 4 framing §5.8 + §6.2 + PR 13 close
§1.6.

The candidate methodology observation (per PR 10 close §5.3
+ PR 11 close §1.6 + PR 13 close §1.6): when framing-time
prediction elevates a goal to named-discipline status, the
discipline shapes implementation decisions without needing
per-pressure rejection events — yielding ABSENCE outcomes
across the predicted pressure forms.

Three-instance progression at PR 14 open:

| Instance | PR | Outcome |
|---|---|---|
| 1 | PR 10 | ABSENCE (helper merger / persistence creep / walker abstraction) |
| 2 | PR 11 | ABSENCE (helper merger / premature surface normalization / fixture widening / recomposition smoothing) |
| 3 | PR 13 | ABSENCE (canonicalization / set-equality collapse / ordering-specific helper) |
| **4 (target)** | **PR 14** | **TBD (target: ABSENCE — partial-match-to-full-divergence collapse / `partial_match` field-addition / fixture-shape extension)** |
| 5 (target) | PR 15 | TBD (target: ABSENCE — multi-survivor cardinality smoothing / join-helper proliferation / recomposition-smoothing-through-helper) |

PR 14's contribution toward Placement A operational
corroboration is the **fourth-instance ABSENCE outcome** under
partial-set divergence pressure (where the discipline tested
is fundamentally identical to PR 10 + PR 11 + PR 13:
framing-time pressure prediction yielding ABSENCE through
named suppression mechanisms). Gate 4 close performs the
gate-level corroboration evaluation across the three Gate 4
primary PRs (PR 13 + PR 14 + PR 15) per §6.1 + Gate 4 framing
§6.2.

### 3.5 Placement B methodology-stack maturation substrate role

PR 14 contributes the **second-PR instance** of Placement B's
three causality preconditions per Gate 4 framing §4.5 + §6.3
+ PR 13 close §1.7:

| Precondition | Manifest at PR 14? (target) | Operational basis |
|---|---|---|
| 1 — Prior pressure prediction at framing time | Target: YES | PR 14 framing §5.4 + PR 14 spec §4.2.4 name three predicted cleanup-pressure forms pre-implementation. |
| 2 — Named suppression mechanism per predicted form | Target: YES | Each suppression mechanism named and grounded (PR 10 §4.2 binding behavioral commitment; `forge_bridge.__all__` 19-symbol lock; expectation record schema three-required-keys lock; PR-11-LOCAL discipline at gate level). |
| 3 — Corroborated recurrence across multiple PR scopes | NOT manifest at PR 14 alone | Precondition 3 requires multi-PR corroborated recurrence. PR 14 contributes the second instance (PR 13 first); PR 15 contributes the third; Gate 4 close evaluates cumulative manifestation per Gate 4 framing §6.2. |

PR 14's contribution to Placement B is **operationally
substrate** — preconditions 1 + 2 target manifest at PR 14's
framing → spec → implementation arc; precondition 3's cross-PR-
recurrence evaluation is deferred to Gate 4 close.

### 3.6 §2.4 architectural commitment travels at PR 14

The Gate 4 framing §2.4 architectural commitment sentence
travels at PR 14 surfaces (relaxed travel discipline per Gate 4
framing §2.4 binding + PR 13 framing §3.6 precedent):

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

Operational placement at PR 14 (binding, parallel to PR 13):

- This framing artifact §2.4 + §3.6 + §5.6.
- PR 14 spec §2 architectural commitment section.
- PR 14 Step 1, 2, 3 commit message body under "architectural
  commitment" section.
- PR 14 close artifact §1 + §6.5 (or equivalent architectural-
  commitment + architectural-sufficiency sections).

NOT in PR 14 test module docstring. NOT in PR 14 fixture
module docstring. The asymmetry vs. carrier travel (active
carriers DO travel through fixture/test docstrings per §3.1)
preserves the carrier / governing sentence / methodology-
stack category integrity Gate 4 framing established + PR 13
operationally verified (per PR 13 close §1.5 inventory).

### 3.7 10-member promoted cleanup-pressure-resistance class

PR 14 inherits the 10-member cleanup-pressure-resistance class
unchanged from Gate 3 close §1.6 + PR 13 close §1.10:

1. Three-authority-surface partition rigidity (PR 4–PR 7
   lineage).
2. `forge_bridge.__all__` 19-symbol lock (Gate 2 close §2.4
   item 2).
3. `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS` 2-element
   locks (Gate 2 close §2.4 items 3 + 4).
4. Expectation record schema three-required-keys lock (Gate 2
   close §2.4 item 5).
5. Four-walker Layer 2 partition target-disjointness (Gate 2
   close §2.4 item 6, extended at Gate 3).
6. Carrier #10's chat-handler-surface topology lock (Gate 2
   close §2.4 item 7).
7. Truth-partitioning discipline at the seed boundary (PR-8-
   LOCAL member; Gate 2 close §2.4 item 8).
8. Semantics-not-topology at the seed boundary (PR-8-LOCAL
   member; Gate 2 close §2.4 item 9).
9. Fixture-surface-data-discipline (PR-9-LOCAL member; PR 9
   framing §6.1; Gate 3 close §1.5).
10. Imports-land-when-used (PR 10 + PR 11 + PR 13
    corroboration; Gate 3 close §1.6).

The class is now demonstrably populatable across **five
reliability phases (PR 6 + PR 7 + PR 8 + PR 9 + PR 10)** under
genuinely independent conditions, with **THREE additional
reliability phases (PR 11 + PR 13)** operationally
corroborating the framing-level protections through ABSENCE.
PR 14's predicted-form outcomes contribute the **second Gate 4
ABSENCE-corroboration evidence** (cumulative across PR 11 +
PR 13 + PR 14).

**PR 14's predicted cleanup-pressure forms (§5.4 below) name
the suppression mechanisms grounding each prediction in the
10-member class:**

- **Partial-match-to-full-divergence collapse pressure** —
  suppression mechanism: PR 10 §4.2 binding behavioral
  commitment ("compare as persisted") + comparator structural-
  shape preservation discipline (member #10 extended to
  structural-shape surface).
- **`partial_match` field-addition pressure** — suppression
  mechanism: `forge_bridge.__all__` 19-symbol lock (member #2)
  + Gate 3 close §3 item 2 (comparator surface non-revisitable
  per PR 10 spec §4.1.6 reference implementation) + §5.3
  binding.
- **Fixture-shape extension pressure** — suppression
  mechanism: expectation record schema three-required-keys
  non-revisitable (member #4; Gate 2 close §2.4 item 5) +
  §5.4 binding.

Gate 4 close reads the cumulative five-PR populating evidence
+ the three-Gate-4-PR ABSENCE-corroboration evidence (PR 13 +
PR 14 + PR 15) in the class-promotion-to-SEED-RELIABILITY-
PHASE-METHODOLOGY-V1.6+ evaluation per Gate 4 framing §6.

### 3.8 Four-walker Layer 2 partition operational

PR 14 inherits the four-walker Layer 2 partition unchanged
from Gate 3 close §1.4 + Gate 4 framing §3.3 + PR 13 framing
§3.8:

- `forge_bridge_persistence_walker.py` — JSONL emission
  semantics.
- `forge_bridge_reader_walker.py` — JSONL readback semantics.
- `forge_bridge_capture_walker.py` — capture-side authority
  partitioning.
- `forge_bridge_seed_walker.py` — seed-side authority
  partitioning.

PR 14 is **target-disjoint from all four walkers** — the new
fixture + new test do not invoke walker traversal logic; the
walkers operate against `forge_bridge/corpus/` production
modules + `tests/corpus/test_*.py` test modules, not against
the fixture data files in `tests/corpus/fixtures/`.

The four-walker partition's target-disjointness from fixture
modules is class member #5 protection (Gate 2 close §2.4 item
6, extended at Gate 3). PR 14 fixture preserves the protection.

### 3.9 Five candidate methodologies + PR 14's contribution

PR 14 inherits the five candidate methodologies from Gate 3
close + PR 13 framing §3.9 + PR 13 close §1.6 + §1.7 + §1.8:

1. **§5.3 candidate methodology observation** (Gate 3 close
   §1.7) — framing-time-pressure-prediction-through-absence
   pattern. PR 14 contributes the **fourth-instance ABSENCE
   outcome target** under partial-set divergence pressure
   (cumulative: PR 10 + PR 11 + PR 13 + PR 14).
2. **Recomposition-through-existing-seams** (Gate 3 close
   §1.10) — first-instance at PR 11. PR 14 contributes a
   **second-instance** under partial-set pressure (the
   discipline operates at gate level per Gate 3 close §3
   item 10; PR 14 test body inlines the recomposition arc
   without absorbing helpers).
3. **0-prod-mod-as-architectural-sufficiency-signal** (Gate 3
   close §1.11) — three-instance at Gate 3 close (PR 9 + PR
   10 + PR 11); four-instance at PR 13 close. PR 14
   contributes a **fifth-instance target** if the 0-prod-mod
   outcome holds at PR 14 close.
4. **Catch-point migration** (Gate 3 close §1.8) — four-
   instance descriptive at PR 13 framing/spec; five-instance
   descriptive at PR 13 close (single-corroboration at
   instance #5 per evidence-inflation rejection applied
   recursively). PR 14 may contribute instance #6 if a new
   catch-point surfaces, OR may match PR 11's zero-amendment
   precedent if framing/spec drafting catch discipline
   matures further.
5. **Cleanup-pressure-resistance class** (Gate 3 close §1.6
   promoted-class methodology) — 10 members at Gate 3 close;
   PR 14 inherits unchanged; predicted-form outcomes
   contribute to the gate-level ABSENCE-corroboration evidence
   (per §3.7 above).

PR 14's contribution to each is the second-Gate-4-PR-substrate
instance; Gate 4 close evaluates the cumulative across all
three primary PRs per Gate 4 framing §6 + §11.5.

### 3.10 PR-13-LOCAL as PR-of-origin (NEW inheritance type at PR 14)

PR 13 close §2.2 established PR-13-LOCAL pure-isolation
discipline as **PR-of-origin archaeology**. The pattern (single-
vector fixture pressure as laboratory-grade calibration
substrate for cumulative gate-arc evaluation) is operationally
useful at PR 14 + PR 15 + future-gate framing pressure. The
specific PR-N-LOCAL statements are non-regenerating scope-local
bindings; the pattern inherits as architectural-substrate
evidence.

PR-14-LOCAL (§0 + §5.5) is PR 14's scope-local discipline
statement. PR-14-LOCAL **references PR-13-LOCAL as PR-of-
origin** for the pure-isolation pattern while authoring its
own discipline appropriate to partial-set divergence. The
reference is structural — PR-14-LOCAL's wording is parallel
to but not identical to PR-13-LOCAL (different divergence
vector implies different language).

**The both-skeletons-at-Step-1 lifecycle invariant as
PR-of-origin (PR 13 close §2.4):**

PR 13 framing §9.12 introduced the both-skeletons-at-Step-1
lifecycle invariant for multi-file PRs at gate-level
reliability work. PR 14 ships two new files (one fixture + one
test) — same multi-file structure as PR 13 — and inherits the
lifecycle invariant as PR-of-origin archaeology. The Step
structure at PR 14 (§9.12 below) matches PR 13's: Step 1 lands
both skeletons in one commit; Step 2 lands both bodies in one
commit; Step 3 is empty verification with archaeology in body.

---

## 4. Architectural delta — what PR 14 introduces

### 4.1 One new fixture file

**File:** `tests/corpus/fixtures/fix_partial_narrow_divergence.py`

**Module purpose:** Seed fixture for the partial-set divergence
pure-isolation case at the chat-handler observation surface.

**Module structure (preview; full contract at PR 14 spec
§4.1):**

```python
"""Seed fixture — partial-set divergence pure-isolation case
at the chat-handler observation surface.

[PR-14-LOCAL binding statement — §5.5 verbatim form]

[Carrier travel — citation by reference per PR 13 framing §3.1
precedent]

[Fixture purpose — partial-set divergence under prompt "list"
with PR 9 reachable-tool set; authored-superset direction]

[Arbitration trace — verbatim from PR 9 multi-match per
fix_multi_match.py:105-140; observation reuses verbatim]

[Authored expectation — three-element list extending observation
by forge_ping at position 2]

[Pure-isolation property at every dimension — partial-set vector
isolated; ordering / semantic-normalization / duplicate /
multi-survivor-cardinality all absent]

[The architectural pressure vector — overlap-interpretation
direction-symmetry — references §5.10]

[Prompt-reuse-without-collision discipline — same prompt "list"
as PR 9 multi-match + PR 13 ordering-divergence; fixture_id
discriminator; per-test tmp_path isolation]

[Archaeology-grade trace per feedback_counts_are_archaeology_grade]

[References to spec + framing + Gate 4 framing + PR 13 framing
+ PR 13 close + fix_multi_match.py:105-140 +
test_pr9_fixture_integration.py:208-213 + _compare.py:503]

[Fixture-data-discipline note — data + one orchestration call
only; no helpers; member #9]
"""

from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr14-partial-narrow-divergence",
    "prompt": "list",
    "expected_narrow": [
        "forge_list_projects",
        "flame_list_libraries",
        "forge_ping",
    ],
}
```

**Module-export contract:**

- Module-level public symbol: `FIXTURE` (dict) — single export.
- `__future__` import: `annotations` (PR 9 + PR 13 convention).
- No other imports (member #9 fixture-surface-data-discipline).
- No helpers, no factories, no parametrization (member #9).
- Module docstring carries PR-14-LOCAL + carrier citation-by-
  reference + arbitration trace + authored expectation rationale
  + pure-isolation property enumeration + cross-references.

**Fixture content rationale:**

The `FIXTURE` dict contains three keys per the expectation
record schema three-required-keys lock (Gate 2 close §2.4 item
5; class member #4):

1. `fixture_id`: `"fix-pr14-partial-narrow-divergence"` —
   kebab-case with PR anchor per PR 9 + PR 13 naming
   convention.
2. `prompt`: `"list"` — the same single-token prompt PR 9
   multi-match + PR 13 ordering-divergence use. The prompt-
   reuse-without-collision discipline is architectural evidence
   (single-variable discipline propagation; per §4.6 below).
3. `expected_narrow`: `["forge_list_projects",
   "flame_list_libraries", "forge_ping"]` — the authored
   superset.

The authored expectation contains:

- Positions 0+1: `["forge_list_projects", "flame_list_libraries"]`
  — the observation's two members at their observation
  positions verbatim (preserves PR 9 multi-match's deterministic
  arbitration output's ordering; no ordering vector engaged
  per §4.3 pure-isolation property).
- Position 2: `"forge_ping"` — the partial-set extension
  element. `forge_ping` is in the PR 9 reachable-tool set per
  `test_pr9_fixture_integration.py:208-213` (verified
  archaeologically); shares no tokens with the prompt `"list"`
  (no semantic-normalization vector engaged); is distinct from
  positions 0+1 (no duplicate vector engaged).

The fixture asserts (via its authored expectation): "I
expected three tools to survive narrowing, including the
unrelated `forge_ping`. Arbitration produced only two." This
is a semantically legible authorial claim — the partial-set
extension element is **orthogonal to the prompt tokens**, which
prevents the divergence from collapsing into fuzzy keyword
semantics. The authored expectation is visibly interpretive
rather than mechanically derived.

### 4.2 One new test module + one named test

**File:** `tests/corpus/test_pr14_partial_narrow_divergence.py`

**Module purpose:** End-to-end partial-set divergence
recomposition arc test — fixture → drive_seed_fixture →
chat_handler → emission → readback → compare_records →
DivergenceReport (narrow_diverged=True).

**Module structure (preview; full contract at PR 14 spec
§4.2):**

```python
"""End-to-end partial-set divergence recomposition arc test —
fixture → drive_seed_fixture → chat_handler → emission →
readback → compare_records → DivergenceReport
(narrow_diverged=True).

[PR-14-LOCAL binding statement — §5.5 verbatim form]

[Traversal trace — same 9-step path as PR 13 inheriting from
PR 11]

[Carrier travel — citation by reference per PR 13 framing §3.1
precedent]

[Test infrastructure import discipline — _apply_pr9_patches +
_read_records as test-internal archaeology surfaces, NOT public
APIs; inherits PR 11 + PR 13 framing]

[References to spec + framing + Gate 4 framing + PR 13 close +
PR 11 close + PR 10 close + test_pr11_recomposition_arc.py +
test_pr13_ordering_divergence.py + fix_multi_match.py:105-140]
"""

from __future__ import annotations

import pathlib

import pytest

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._seed import drive_seed_fixture

from tests.corpus.fixtures.fix_partial_narrow_divergence import (
    FIXTURE as FIX_PARTIAL_NARROW_DIVERGENCE,
)

# Test-internal archaeology surfaces (NOT public APIs) per
# module-docstring "Test infrastructure import discipline"
# framing + A.5.3.2-PR14-SPEC.md §4.2.1 site 9.
from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)


def test_recomposition_arc_partial_narrow_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — partial-set divergence pure-isolation case.

    [Drives fix-pr14-partial-narrow-divergence through the full
    decomposition seam path. Fixture authors expected_narrow with
    observation's two members at positions 0+1 verbatim PLUS
    forge_ping at position 2 (partial-set extension element
    orthogonal to prompt tokens).]

    [Comparator's compare-as-persisted discipline detects the
    partial-set divergence as narrow_diverged=True per direct
    list-equality at _compare.py:503 (length asymmetry +
    element-membership asymmetry at position 2 both contribute).]

    [Carrier #17 at use: DivergenceReport's per-surface
    partitioning preserves authorship through emission →
    persistence → readback → join → interpretive comparison;
    partial-set divergence vector identifiable at the structural
    shape level (expectation.expected_narrow has length 3;
    observation.observed_narrow has length 2; shared elements at
    positions 0+1 verbatim).]

    [Pure-isolation property at every dimension: partial-set
    only — no ordering / semantic-normalization /
    duplicate / multi-survivor-cardinality confound.
    PR-14-LOCAL pure-isolation discipline binding.]
    """
    # ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
    # Test-internal archaeology surface (NOT a public API).
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    # ── Steps 2-5 of traversal: drive fixture → emission ───────
    # drive_seed_fixture orchestrates expectation persistence,
    # chat_handler arbitration, observation emission. The seam
    # traversal is explicit at the call site — no helper absorbs
    # the arc (PR-11-LOCAL discipline at gate level + PR 14
    # framing §5.4 predicted-form 3 suppression).
    drive_seed_fixture(**FIX_PARTIAL_NARROW_DIVERGENCE)

    # ── Step 6 of traversal: read back persisted records ───────
    # Test-internal archaeology surface; reads every
    # capture-*.jsonl record across the corpus dir, skipping
    # headers.
    records = _read_records(corpus_dir)

    # ── Step 7 of traversal: partition by fixture_id + record_kind ──
    # Same partition pattern as PR 13 (per PR-11-LOCAL discipline
    # at gate level + Gate 2 close §2.1 foundational dependencies
    # — fixture_id joinability + record_kind partitioning).
    matching = [
        r for r in records
        if r.get("fixture_id") == FIX_PARTIAL_NARROW_DIVERGENCE["fixture_id"]
    ]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for "
        f"{FIX_PARTIAL_NARROW_DIVERGENCE['fixture_id']!r}; got "
        f"{len(matching)}.\nAll records: {records}"
    )

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    # ── Step 8 of traversal: invoke comparator ─────────────────
    # The interpretive-read seam. compare_records joins
    # observation + expectation by fixture_id (Gate 2 close §2.1)
    # and produces the DivergenceReport per carrier #17. Direct
    # list-equality at _compare.py:503 detects the partial-set
    # divergence (length 2 != length 3; element mismatch at
    # position 2); no caller-side overlap interpretation per PR
    # 14 framing §5.4 predicted-form 1 suppression (PR 10 §4.2
    # binding behavioral commitment at use).
    report = compare_records(
        observation_record=observation,
        expectation_record=expectation,
    )

    # ── Step 9 of traversal: assertions on DivergenceReport ────
    # Four-key structural assertion contract — carrier #17 at
    # use: each authority surface's contribution structurally
    # identifiable at the report's outer dict shape. The
    # partial-set divergence vector surfaces at distinct list
    # lengths at expectation vs. observation sub-dicts (no
    # partial_match-aware field; no overlap-aware computation;
    # the structural shape preservation IS the partial-match
    # disclosure per PR 14 framing §5.4 predicted-form 2
    # suppression).
    assert report["fixture_id"] == FIX_PARTIAL_NARROW_DIVERGENCE["fixture_id"]
    assert report["expectation"]["expected_narrow"] == [
        "forge_list_projects",
        "flame_list_libraries",
        "forge_ping",
    ]
    assert report["observation"]["observed_narrow"] == [
        "forge_list_projects",
        "flame_list_libraries",
    ]
    assert report["divergence"]["narrow_diverged"] is True
```

**Test contract:**

- Module-level public symbol: `test_recomposition_arc_partial_narrow_divergence`
  — single test function export.
- Imports: minimal — `pathlib`, `pytest`, `compare_records`,
  `drive_seed_fixture`, `FIX_PARTIAL_NARROW_DIVERGENCE`,
  `_apply_pr9_patches`, `_read_records` (each lands when first
  used per cleanup-pressure-resistance class member #10).
- Module docstring carries PR-14-LOCAL + carrier citation-by-
  reference + traversal trace + test infrastructure import
  discipline + cross-references.
- Test function docstring carries the recomposition arc shape
  + partial-set divergence detection narrative + carrier #17
  at use + pure-isolation property enumeration.

### 4.3 Partial-set divergence as pure single-vector pressure

The pure-isolation property holds at every non-target dimension:

| Dimension | Observation | Expectation (authored) | Pure-isolation? |
|---|---|---|---|
| Set membership | `{forge_list_projects, flame_list_libraries}` | `{forge_list_projects, flame_list_libraries, forge_ping}` | NO — this is the partial-set divergence vector (single direction: authored is superset by one element). |
| Sequence | `[forge_list_projects, flame_list_libraries]` | `[forge_list_projects, flame_list_libraries, forge_ping]` (positions 0+1 shared verbatim) | YES — shared elements preserve at observation positions verbatim. |
| Semantic normalization | `[forge_list_projects, flame_list_libraries]` (exact-match identifiers) | `[forge_list_projects, flame_list_libraries, forge_ping]` (exact-match identifiers) | YES — no casing variants, no substring matches, no canonical-form transformations. |
| Duplicate handling | Each list contains distinct elements (no duplicates). | Each list contains distinct elements (no duplicates). | YES — distinct elements only. |
| Multi-survivor cardinality | 2 elements. | 3 elements (cardinality-class increment matches partial-set vector). | YES — both lists are multi-element (>1); the cardinality asymmetry IS the partial-set vector itself, not a separate confound (per §2.4 + §5.10 clarification). |

The partial-set vector is the **single divergence vector**. The
fixture isolates this vector at the architectural-pressure-
surface level (the comparator's interpretive layer under partial-
match structure) without ordering / semantic-normalization /
duplicate-handling / multi-survivor-cardinality confound.

The cardinality asymmetry (2 vs 3 elements) and the partial-
set vector (authored-superset) are the same architectural-
pressure-surface phenomenon, not two separate confounds. Gate
4 framing §4.2 dimension 2's "implicating cardinality" language
anticipates Direction B (authored subset / observed superset)
where a new prompt + new reachable-set behavior would
constitute additional moving axes; Direction A (this PR) avoids
those moving axes by reusing PR 9 + PR 13 arbitration substrate
verbatim. See §5.10 for the affirmative architectural decision
on direction selection.

### 4.4 The single-test traversal as architectural test posture

PR 14 ships **exactly one named test** per Gate 4 framing
§5.5 + PR 13 framing §4.5 precedent. The single-test discipline
inherits from PR 13 unchanged.

**Why one test, not multiple:**

The architectural commitment under test is **the recomposition
arc's preservation of authored structure through partial-set
divergence pressure**. One clean end-to-end traversal exercises
the commitment fully:

- The fixture authors a partial-set divergence (one
  divergence vector).
- The traversal exercises every seam (emission → persistence
  → readback → join → interpretive comparison).
- The four-key DivergenceReport assertion contract reads the
  result at full structural fidelity (the partial-match shape
  surfaces at the structural list values).

A second test (inverse direction — authored subset / observed
superset) would test the same discipline through the symmetric
path. Per the evidence inflation rejection discipline (§4.5
below + PR 13 framing §4.4), symmetric-direction testing tests
the same architectural commitment twice and inflates evidence
without contributing architectural value. The architectural
question — "does the comparator preserve partial-set divergence
faithfully?" — is answered by one clean traversal; the inverse
direction would test "does the comparator preserve partial-set
divergence faithfully under the symmetric assertion path?",
which is a different question (and a less interesting one
because the symmetry of the comparator surface makes the
answer trivially yes by direct list-equality at
`_compare.py:503`).

**Why authored-superset direction specifically:**

Per §5.10 affirmative architectural decision below: the
authored-superset direction is the **stronger architectural
move** for PR 14's specific calibration role. Three reasons:

1. **Single-variable discipline preservation across PR 9 / PR
   13 / PR 14.** Same prompt + same reachable-tool set + same
   arbitration trace + same observation — the comparator
   surface becomes the only moving interpretive layer across
   the three-PR series. The single-variable discipline IS
   architectural-substrate evidence for Gate 4 close (per
   §4.6 below).

2. **Semantically legible authorial claim.** The authored
   expectation contains `forge_ping` — a tool with no token
   overlap with the prompt. The author is asserting "I
   expected this unrelated tool to survive narrowing" — a
   visibly interpretive claim, not a mechanically derived
   one. The partial-set extension element's orthogonality to
   prompt tokens prevents the divergence from collapsing into
   fuzzy keyword semantics.

3. **Pressure-vector direction-symmetry.** The cleanup-pressure
   vector (temptation toward a `partial_match` field or
   overlap-aware helper) is **direction-symmetric** —
   regardless of which side contains the additional element,
   the temptation operates identically. So the authored-
   superset direction tests the discipline as strongly as the
   authored-subset direction would, while preserving the
   single-variable discipline + the substrate reuse.

### 4.5 Evidence inflation rejection

PR 14 framing inherits the evidence inflation rejection
discipline PR 11 + PR 13 framings authored. The discipline
shapes three PR 14 framing-time decisions:

1. **The 1-test decision** (per §4.4 above + §5.2 below). One
   clean traversal proves the architectural commitment;
   symmetric-direction testing inflates evidence without
   contributing architectural value.

2. **The 3-step cadence preservation** (§9.12 below
   inheriting PR 13's). Stepwise decomposition is methodology
   archaeology, not structurally necessary for the test +
   fixture content. The 3-step cadence preserves PR 11 + PR
   13 precedent; engineering a 4-step or 5-step decomposition
   to manufacture cumulative-multi-step concentration evidence
   would be evidence inflation.

3. **The rejection of catch-point migration instance #5-style
   sub-instance splitting** (per PR 13 close §1.8 recursive-
   self-governance precedent). If PR 14 framing/spec drafting
   produces multiple catch-shape-related sub-events, the
   sub-events combine into a single corroboration instance
   per the recursive-self-governance discipline; the
   methodology operates on its own evidence at PR 14 the same
   way it operated at PR 13.

The evidence inflation rejection discipline is itself
methodology-stack maturation (per PR 11 close §2.3 + PR 13
close §1.8). PR 14 inherits the discipline unchanged.

### 4.6 The `"list"`-as-calibration-prompt archaeology

PR 14 makes visible an architectural-substrate pattern that
crystallizes at the third reliability PR (PR 9 + PR 13 + PR
14) using the prompt `"list"`:

| PR | Authored expectation | Divergence vector | Architectural pressure tested |
|---|---|---|---|
| PR 9 multi-match | `["forge_list_projects", "flame_list_libraries"]` (matches observation verbatim) | None — no-divergence baseline | Arbitration determinism + emission topology |
| PR 13 ordering | `["flame_list_libraries", "forge_list_projects"]` (positions swapped) | Ordering divergence | Compare-as-persisted under ordering pressure |
| **PR 14 partial-set** | **`["forge_list_projects", "flame_list_libraries", "forge_ping"]` (superset extension)** | **Partial-set divergence (authored-superset)** | **Compare-as-persisted under partial-set pressure** |

**What the table reveals:**

- **Same prompt.** `"list"` across all three PRs.
- **Same reachable-tool set.** `_PR9_REACHABLE_TOOLS` (4 tools)
  across all three PRs.
- **Same arbitration trace.** The PR14 keyword filter + PR21
  deterministic_narrow path produces the same observation
  (`narrower.decision = ["forge_list_projects",
  "flame_list_libraries"]`) verbatim across all three PRs.
- **Same observation emission path.** The chat_handler →
  emit_divergence_capture → JSONL persistence path is
  invariant across all three PRs.
- **Only the authored expectation varies.**

The comparator surface becomes the **only moving interpretive
layer** across the three-PR series. The single-variable
discipline IS architectural-substrate evidence for Gate 4
close — it demonstrates that the validated comparator can be
exercised under independent divergence vectors WITHOUT requiring
new arbitration topology / new prompt semantics / new
reachable-set behavior at each test scope. The substrate is
becoming reusable known-good calibration substrate within
Gate 4.

**Architectural archaeology recommendation for Gate 4 close:**

The `"list"`-as-calibration-prompt pattern is becoming
load-bearing substrate for Gate 4's three-PR cumulative
evaluation. Future Gate-X work that introduces additional
divergence vectors (semantic-normalization / duplicate-handling
/ etc.) **should consider reusing the same calibration prompt
+ reachable-tool set + arbitration trace** to preserve the
single-variable discipline as architectural-substrate evidence.
The discipline is not free — it requires that the new
divergence vector be expressible as an authored-expectation
modification only — but where the discipline is preservable,
it is the strongest single piece of architectural-substrate
evidence the gate-arc can produce.

**Note on PR 15:** PR 15 (multi-survivor mismatch) **may break
the single-variable discipline by necessity.** Multi-survivor
mismatch requires either a different prompt (one producing
3+ candidates) or a different reachable-set semantic (one
forcing single-survivor disambiguation). PR 15 framing must
explicitly evaluate whether the single-variable discipline can
be preserved at PR 15's substrate; if not, PR 14 will be the
**last** PR within Gate 4 where the discipline holds cleanly.
This makes PR 14's specific calibration-substrate role
architecturally load-bearing in a way that's specific to PR 14.

---

## 5. Binding decisions

### 5.1 PR 14 scope locked: one fixture + one test, authored-superset partial-set divergence

PR 14 ships:

1. **Exactly one new fixture file:**
   `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
   - Filename: `fix_partial_narrow_divergence.py` (snake_case;
     NO PR anchor per PR 9 + PR 13 convention).
   - `fixture_id`: `"fix-pr14-partial-narrow-divergence"`
     (kebab-case; WITH PR anchor per PR 9 + PR 13 convention).
   - Module export: `FIXTURE` (canonical name per PR 9 + PR 13
     convention).
   - Content: three-key dict with `fixture_id` + `prompt:
     "list"` + `expected_narrow:
     ["forge_list_projects", "flame_list_libraries",
     "forge_ping"]`.

2. **Exactly one new test module:**
   `tests/corpus/test_pr14_partial_narrow_divergence.py`
   - Filename: `test_pr14_partial_narrow_divergence.py` (PR-
     anchored per PR 9 + PR 13 test module convention).
   - Single test function:
     `test_recomposition_arc_partial_narrow_divergence`.
   - Module structure: parallel to
     `test_pr13_ordering_divergence.py` (PR 13 framing §4.2
     precedent).

3. **Zero modifications to existing files.** Per §5.3 below.

The scope is locked at the architectural-pressure-surface
isolation discipline + the substrate-reuse + the calibration-
substrate role within the three-PR Gate 4 series.

Alternative scope shapes are rejected at the framing layer:

- Multiple fixtures (e.g., authored-superset + authored-subset
  variants) — rejected per §4.4 + §5.2 evidence inflation.
- Multiple tests (e.g., one test per assertion key) — rejected
  per PR 11 + PR 13 single-test-per-architectural-commitment
  precedent.
- Multi-vector fixture (partial-set + ordering) — rejected per
  §0 + §5.5 PR-14-LOCAL pure-isolation discipline.
- Direction B variant (authored subset / observed superset
  via new 3+-survivor prompt topology) — rejected per §5.10
  affirmative architectural decision.

### 5.2 Test count locked at exactly 1

PR 14 adds **exactly 1 new test** to the forge env collected
count.

- **Baseline:** 218 tests collected (PR 13 close §1.9 forge
  env collected).
- **PR 14 contribution:** +1
  (`test_recomposition_arc_partial_narrow_divergence`).
- **PR 14 close target:** 219 tests collected.

The PR 14 close phase-end condition (§9.1) re-verifies this
arithmetic at close commit + the actual test contribution from
PR 14 Step 2. **The test count is archaeology-grade** per
`feedback_counts_are_archaeology_grade.md`.

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`). Target at PR 14 close:
**212 baseline (PR 13 close §1.9 + PR 11 close §1.7) + 1 new
= 213 forge-bridge env collected.** Not re-verified at PR 14
close beyond inheritance documentation — the 6-test gap is
PR 7-scope, not PR 14-scope. **Do not conflate the two env
counts** per PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close
§1.7 + PR 13 close §1.9.

### 5.3 0 production source modifications

PR 14 modifies **zero production source files**. Per Gate 4
framing §2.2 + §5.3 binding + PR 13 framing §5.3 + PR 13 close
§1.3 four-PR escalation:

- No changes to `forge_bridge/corpus/_compare.py`.
- No changes to `forge_bridge/corpus/_capture.py`.
- No changes to `forge_bridge/corpus/_seed.py`.
- No changes to any other `forge_bridge/` module.
- No changes to `forge_bridge/__all__`.

The 0-prod-mod target is the **architectural sufficiency
signal target** inherited at gate level. If PR 14 implementation
surfaces a real production-source need, the deviation registers
as Gate-X inheritance archaeology per §5.11 below — NOT as
in-flight production modification within PR 14.

**Four-PR escalation context (PR 13 close §1.3):** PR 9 + PR
10 + PR 11 + PR 13 all shipped 0-prod-mod. PR 14 extends to
**five-PR escalation** if the target holds at PR 14 close.
Gate 4 close reads the cumulative five-PR architectural-
sufficiency-signal evidence in the candidate methodology
promotion evaluation per Gate 4 framing §6 + Gate 3 close
§1.11.

### 5.4 Three predicted cleanup-pressure forms + named suppression mechanisms

PR 14 framing predicts three cleanup-pressure forms PR 14
implementation may encounter. Each prediction pairs with a
named suppression mechanism (per Placement B precondition 2
operational manifestation at PR 14). The predictions inherit
the three forms Gate 4 framing §10 PR 14 named pre-PR-14-
framing; PR 14 framing grounds each in PR 14-specific
implementation surfaces.

**Predicted form 1: Partial-match-to-full-divergence collapse pressure.**

The pressure form: pressure to interpret partial-set
divergence as "full divergence" or as "binary divergence" —
either at the comparator surface (rejected by Gate 3 close §3
item 2) or at caller-side wrapping in PR 14's test body
(rejected at the spec layer). The temptation surfaces as: "the
test body could just assert `narrow_diverged=True` and skip
asserting the structural list values, since divergence is
divergence." This temptation would mask the load-bearing
partial-match claim — the discipline being tested is that the
comparator preserves the structural partial-match shape (not
that divergence is reported at all).

**Named suppression mechanism:** PR 10 §4.2 binding behavioral
commitment ("compare as persisted") + comparator structural-
shape preservation discipline (cleanup-pressure-resistance
class member #10 extended to structural-shape surface). The
comparator returns sequence-and-length-preserving
`DivergenceReport`; PR 14 assertions read the four-key shape
at full structural fidelity (not via narrow_diverged-only
shortcuts). The test body's four-key assertion contract is
identical to PR 13's (assert `fixture_id` + `expectation.expected_narrow`
+ `observation.observed_narrow` + `divergence.narrow_diverged`
explicitly).

**Predicted form 2: `partial_match` field-addition pressure.**

The pressure form: pressure to add a new `DivergenceReport`
field signaling partial-match presence — e.g., `partial_match:
True`, `divergence_kind: "partial_set"`, `overlap_count: 2`,
or any other field whose primary purpose is "making partial-
match interpretation easier for the consumer." The temptation
operates symmetrically across both directions of the partial-
set vector (authored-superset and authored-subset) per §5.10
direction-symmetric pressure-vector observation.

**Named suppression mechanism:** `forge_bridge.__all__`
19-symbol lock (cleanup-pressure-resistance class member #2;
Gate 2 close §2.4 item 2) + Gate 3 close §3 item 2 (comparator
surface preserves per PR 10 spec §4.1.6 reference implementation;
no new `DivergenceReport` field; no new `compare_records`
keyword argument; no pre-processing helper on the comparator
side) + §5.7 binding below + §5.8 binding below. The structural
shape preservation IS the partial-match disclosure — the
consumer reads partial-match from the list-length and list-
membership asymmetry at the report's structural shape; no
overlap-aware computation needed.

**Predicted form 3: Fixture-shape extension pressure.**

The pressure form: pressure to add a fourth structural field
to the expectation record schema to signal partial-match
expectations — e.g., `expected_subset_of_observation: True`,
`expected_partial_match: True`, or any field whose primary
purpose is "making the fixture's partial-set intent explicit
to the comparator." The temptation surfaces as: "the fixture
could declare its partial-set intent in the FIXTURE dict, and
the comparator could read the intent flag to interpret the
divergence." This temptation would convert the partial-set
divergence from a structural property to a declared-intent
property — defeating the compare-as-persisted discipline.

**Named suppression mechanism:** expectation record schema
three-required-keys non-revisitable (cleanup-pressure-
resistance class member #4; Gate 2 close §2.4 item 5; Gate 3
close §3 item 1 inherited at gate level) + §5.4 binding. The
expectation record schema preserves at exactly three keys
(`fixture_id`, `prompt`, `expected_narrow`). PR 14's authored-
superset intent is expressed entirely through the
`expected_narrow` list's content (the three-element list IS
the partial-set intent); no fourth field carries declared
intent.

**Three "while we're here" pressure forms PR-14-LOCAL
explicitly rejects:**

In addition to the three predicted forms above, PR-14-LOCAL
guards against three implementation-pressure forms that would
multi-vector PR 14's fixture/test:

- *"While we're here, also test ordering divergence at the
  partial-set"* — adding an ordering-vector to the partial-set
  fixture would convert PR 14 from pure-vector to multi-vector.
  PR 13 owns ordering pressure.
- *"While we're here, also test duplicate handling at the
  partial-set"* — adding a duplicate element to the partial-set
  fixture would introduce duplicate-handling-class divergence
  as a confound. Duplicate handling is not in Gate 4 scope at
  any of the three primary PRs.
- *"While we're here, also test semantic normalization at the
  partial-set"* — adding casing variants or substring matches
  to the partial-set fixture would introduce semantic-
  normalization pressure as a confound. Semantic normalization
  is not in Gate 4 scope.

All three "while we're here" pressures are rejected at the
spec layer per PR-14-LOCAL + §7 non-acquisition commitments
items below.

### 5.5 PR-14-LOCAL binding statement — pure-isolation discipline

Repeated verbatim from §0 (single-form discipline; one
authoritative wording):

> **PR 14 isolates partial-set divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 14 scope —
> combining partial-set with ordering, semantic-normalization,
> duplicate-handling, multi-survivor-cardinality, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 14 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

Operational placement (binding):

- `test_pr14_partial_narrow_divergence.py` module docstring.
- `fix_partial_narrow_divergence.py` module docstring.
- All PR 14 commit message bodies under "preserved
  invariants" / "PR-14-LOCAL" sections.

**PR-13-LOCAL as PR-of-origin reference:** PR-14-LOCAL
references PR-13-LOCAL as PR-of-origin for the pure-isolation
discipline pattern (per PR 13 close §2.2 + §3.10 above). The
reference is structural — PR-14-LOCAL is parallel scope-local
discipline appropriate to partial-set divergence, not a
regeneration of PR-13-LOCAL's ordering-isolation form.

Cleanup pressure to soften the binding (e.g., "the symmetric-
direction case isn't really multi-vector since it's the same
divergence vector with sides swapped") is rejected at the spec
layer: even direction-swap variants test the same discipline
through symmetric assertion paths and constitute evidence
inflation per §4.5 + §5.10 direction-symmetric pressure-vector
observation.

### 5.6 §2.4 architectural commitment travels verbatim at PR 14 framing/spec/close + commit bodies

Gate 4 framing §2.4's architectural commitment sentence
travels verbatim at PR 14 surfaces per Gate 4 framing §2.4
binding form + PR 13 framing §5.6 precedent (relaxed travel
discipline; deliberately stops short of fixture/test
docstrings):

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

Operational placement (binding, parallel to PR 13):

- This framing artifact §2.4 + §3.6 + §5.6 (this binding
  decision).
- PR 14 spec §2 architectural commitment section.
- PR 14 Step 1, 2, 3 commit message body under "architectural
  commitment" section.
- PR 14 close artifact §1 + §6.5 (or equivalent architectural-
  commitment + architectural-sufficiency sections).

NOT in PR 14 test module docstring. NOT in PR 14 fixture
module docstring. The asymmetry vs. carrier travel (active
carriers DO travel through fixture/test docstrings per §3.1)
preserves the carrier / governing sentence / methodology-
stack category integrity Gate 4 framing established + PR 13
operationally verified (per PR 13 close §1.5 inventory).

### 5.7 Comparator surface preserved unchanged

PR 14 does NOT modify the comparator surface (`compare_records`
+ `DivergenceReport` + `ComparatorInputError`) per Gate 4
framing §5.3 binding + §7 item 3 non-acquisition + PR 13
framing §5.7 + Gate 3 close §3 item 2:

- No new `DivergenceReport` field (no `partial_match`, no
  `divergence_kind`, no `overlap_count`, no `cardinality_class`,
  no `superset_side`, no `subset_side`).
- No new `compare_records` keyword argument (no
  `compare_mode`, no `partial_match_aware`, no
  `overlap_interpretation`, no caller-side configuration).
- No pre-processing helper on the comparator side.
- No change to the §4.2 binding behavioral commitment.

If PR 14 implementation surfaces a real gap in comparator
behavior that requires modification, the gap registers as
Gate-X inheritance archaeology per §5.11 deviation protocol
— NOT as in-flight production modification within PR 14.

### 5.8 `forge_bridge.__all__` stays at 19 symbols

PR 14 does NOT modify `forge_bridge.__all__` per Gate 4 framing
§5.4 + §7 item 12 non-acquisition + PR 13 framing §5.8 + Gate
2 close §2.4 item 2. The 19-symbol public API preserves.

PR 14 fixture + test consume the comparator + recomposition
arc through corpus-internal import paths
(`from forge_bridge.corpus._compare import compare_records`
+ `from forge_bridge.corpus._seed import drive_seed_fixture`
+ underscored-private PR 9 imports as test-internal archaeology
surfaces).

### 5.9 PR 9 fixture naming convention preserved (two-surface form)

PR 14 fixture preserves the PR 9 fixture naming convention
(§3.3 above) at both naming surfaces:

| Surface | PR 14 value | PR 9 + PR 13 convention preserved |
|---|---|---|
| Filename | `fix_partial_narrow_divergence.py` | snake_case; NO PR anchor in filename |
| `fixture_id` field | `"fix-pr14-partial-narrow-divergence"` | kebab-case; WITH PR anchor in field |
| Module symbol export | `FIXTURE` | canonical name across all fixture modules |

Alternative naming patterns at any surface are rejected at the
spec layer per §3.3 archaeology preservation discipline:

- PR-anchored filename (`fix_pr14_partial_narrow_divergence.py`)
  rejected — breaks PR 9 + PR 13 visual-scan navigability
  convention.
- Non-PR-anchored `fixture_id` (`"fix-partial-narrow-divergence"`)
  rejected — erases archaeological-origin chronology.
- Per-module symbol export name (`FIX_PARTIAL_NARROW_DIVERGENCE`
  at module scope) rejected — breaks PR 9 + PR 13 canonical
  `FIXTURE` symbol; consuming tests handle per-fixture local
  identifier needs via import-time aliasing per PR 11 + PR 13
  pattern.

### 5.10 Authored-superset direction as affirmative architectural decision

PR 14 selects the **authored-superset direction** (authored
list contains observation's elements PLUS one additional
element) as an **affirmative architectural decision**, not as
a tolerated inversion of Gate 4 framing §10's example sketch.

**The pressure vector under test is overlap-interpretation,
not directional ownership of the superset relation.** The
temptation toward overlap-aware helper fields on the
DivergenceReport (predicted form 2 at §5.4 above) operates
symmetrically regardless of which side contains the additional
element:

| Direction | Authored | Observed | Cleanup pressure |
|---|---|---|---|
| **A (this PR)** | `[X, Y, Z]` | `[X, Y]` | "Maybe we should add `partial_match: True` to signal that authored ⊃ observed." |
| B (rejected) | `[X, Y]` | `[X, Y, Z]` | "Maybe we should add `partial_match: True` to signal that observed ⊃ authored." |

Both directions test the same architectural commitment (the
comparator preserves the partial-match structure faithfully
without normalization) and produce the same cleanup-pressure
vector (overlap-aware field on the DivergenceReport). Selecting
Direction A is the **stronger architectural move** for three
reasons:

1. **Single-variable discipline preservation across PR 9 / PR
   13 / PR 14** (per §4.6). Direction A reuses PR 9 multi-
   match's deterministic arbitration output verbatim — same
   prompt, same reachable-tool set, same observation. The
   comparator surface becomes the only moving interpretive
   layer across the three-PR series. Direction B would require
   either a multi-token prompt (e.g., `"ping list"`) or a
   modified reachable-tool set; either choice introduces new
   arbitration topology + new prompt semantics + possibly new
   reachable-set behavior as additional moving axes —
   simultaneously testing partial-set divergence and second-
   order arbitration variation.

2. **Semantically legible authorial claim.** Direction A's
   authored expectation includes `forge_ping` — a tool with
   no token overlap with the prompt `"list"`. The author is
   asserting "I expected this unrelated tool to survive
   narrowing." This is a visibly interpretive claim, not a
   mechanically derived one. The partial-set extension
   element's orthogonality to prompt tokens prevents the
   divergence from collapsing into fuzzy keyword semantics.
   Direction B's authored expectation (subset of observation)
   would be mechanically derivable from observation (drop one
   element); it carries less semantic weight as an authorial
   claim.

3. **Substrate reuse + cumulative architectural archaeology.**
   Direction A preserves the `"list"`-as-calibration-prompt
   archaeology PR 9 + PR 13 established (per §4.6 above). The
   `"list"` prompt is becoming reusable known-good substrate
   within Gate 4. Direction B would require giving up the
   substrate at PR 14 without compensating architectural
   gain.

The architectural-pressure-vector is direction-symmetric per
the table above. Selecting Direction A is the affirmative move
that maximally exploits the substrate-reuse + single-variable
discipline + semantic-legibility advantages. The framing-time
selection rationale is preserved at PR 14 spec §0 + close §1
for archaeology.

**Cleanup pressure to revisit the direction selection at spec
or implementation phase is rejected.** The direction is bound
at framing per the affirmative architectural decision; any
direction-revisit pressure registers as evidence-inflation-
through-direction-symmetry-testing (per §5.5 binding above).

### 5.11 Justified-deviation protocol if 0-prod-mod target falsifies

If PR 14 implementation surfaces a real production-source need,
the deviation follows the protocol from Gate 4 framing §2.2 +
PR 13 framing §5.10:

1. **Pause Step 2** at the moment of falsification.
2. **Surface the deviation at framing-level evaluation**
   before adding production-source modifications. The
   evaluation considers: is this a real architectural gap or
   a transient implementation pressure?
3. **If real gap:** PR 14 close registers the deviation as
   Gate-X inheritance archaeology; the production modification
   ships as a separate PR (numbered Gate 4 framing §5.7
   conditional PR 12 if it fits the topology, OR a new PR
   numbering decision).
4. **If transient pressure:** PR 14 implementation reroutes
   through the existing seams; the falsification registers as
   spec-layer pressure-form discovery (potentially a new
   cleanup-pressure-resistance class member candidate).

The deviation protocol is **goal-oriented**, not constraint-
oriented per Gate 3 close §3 item 11 + PR 13 framing §5.10.
0-prod-mod is the target; justified deviations register as
archaeology, not silent additions.

---

## 6. Placement A + Placement B substrate contribution

### 6.1 Placement A operational corroboration substrate

PR 14 contributes the **second Gate 4 PR instance** of the
§5.3 candidate methodology observation's third-instance
corroboration target at Gate 4 close per Gate 4 framing §5.8
+ §6.2 + PR 13 close §1.6.

The candidate methodology observation (per PR 10 close §5.3
+ PR 11 close §1.6 + PR 13 close §1.6): when framing-time
prediction elevates a goal to named-discipline status, the
discipline shapes implementation decisions without needing
per-pressure rejection events — yielding ABSENCE outcomes
across the predicted pressure forms.

**Three-instance progression at PR 14 open + PR 14's target
contribution:**

| Instance | PR | Outcome |
|---|---|---|
| 1 | PR 10 | ABSENCE (helper merger / persistence creep / walker abstraction) |
| 2 | PR 11 | ABSENCE (helper merger / premature surface normalization / fixture widening / recomposition smoothing) |
| 3 | PR 13 | ABSENCE (canonicalization / set-equality collapse / ordering-specific helper) |
| **4 (target)** | **PR 14** | **TARGET: ABSENCE (partial-match-to-full-divergence collapse / `partial_match` field-addition / fixture-shape extension)** |
| 5 (target) | PR 15 | Target: ABSENCE (multi-survivor cardinality smoothing / join-helper proliferation / recomposition-smoothing-through-helper) |

If PR 14 produces ABSENCE evidence for all three predicted
forms, the cumulative evidence at PR 14 close is **four-
instance ABSENCE** across four independent reliability PRs.
Gate 4 close evaluates the cumulative across all three Gate 4
primary PRs (PR 13 + PR 14 + PR 15) for the gate-level
operational corroboration evaluation per §6.2 + Gate 4 framing
§6.1.

### 6.2 Placement B methodology-stack maturation substrate

PR 14 contributes the **second-PR instance** of Placement B's
three causality preconditions per Gate 4 framing §4.5 + §6.3
+ PR 13 close §1.7.

Three causality preconditions for Placement B (methodology-
stack maturation claim corroborated):

| Precondition | Manifest at PR 14? (target) | Operational basis |
|---|---|---|
| 1 — Prior pressure prediction at framing time | Target: YES | This framing §5.4 names three predicted cleanup-pressure forms pre-implementation. PR 14 spec §4.2.4 will inherit the form prediction; PR 14 close §1 records the implementation-time outcomes. |
| 2 — Named suppression mechanism per predicted form | Target: YES | §5.4 above names suppression mechanism for each predicted form. PR 14 spec §4.2.4 inherits the suppression mechanism naming; PR 14 close §1 records the operational mechanism manifestation. |
| 3 — Corroborated recurrence across multiple PR scopes | NOT manifest at PR 14 alone | Precondition 3 requires multi-PR corroborated recurrence. PR 14 contributes the second instance (PR 13 first); PR 15 contributes the third; Gate 4 close evaluates cumulative manifestation per Gate 4 framing §6.2. |

PR 14's contribution to Placement B is **operationally
substrate** — preconditions 1 + 2 target manifest at PR 14's
framing → spec → implementation arc. Precondition 3's cross-PR-
recurrence evaluation is deferred to Gate 4 close.

### 6.3 Two-placement substrate independence

PR 14 contributes substrate to BOTH Placement A and Placement
B independently — same architectural substrate (the one-test
+ one-fixture work product + the framing-time discipline +
the implementation-time discipline) produces both pieces of
evidence. Per Gate 4 framing §6.4 + PR 13 framing §6.3 + PR 13
close §1.6 + §1.7:

- **Placement A** evaluates the §5.3 candidate methodology
  observation (framing-time-pressure-prediction-through-
  absence pattern) under cumulative three-Gate-4-PR ABSENCE
  evidence.
- **Placement B** evaluates the methodology-stack maturation
  claim (causality preconditions 1+2+3) under cumulative
  three-PR multi-instance recurrence evidence.

The two placements share substrate but evaluate different
properties: Placement A evaluates "does the pattern keep
producing ABSENCE outcomes?" (operational corroboration of
the pattern itself); Placement B evaluates "does the
methodology-stack mature through causal recurrence at multiple
PR scopes?" (causal-not-passive corroboration of the
methodology-stack maturation claim).

### 6.4 Evidence inflation rejection as PR 14 framing discipline

PR 14 framing inherits the evidence inflation rejection
discipline PR 11 + PR 13 framings authored. The discipline
operates at three PR 14 framing-time decisions:

1. **The 1-test decision** (§5.2). One clean traversal proves
   the architectural commitment; symmetric-direction testing
   inflates evidence without contributing architectural value.

2. **The single-direction selection** (§5.10). Direction A
   selected as affirmative architectural decision; Direction
   B's symmetric pressure-vector means the inversion would
   test the same discipline and inflate evidence.

3. **The recursive-self-governance discipline** (per PR 13
   close §1.8). If PR 14 framing/spec/implementation produces
   multiple catch-shape-related sub-events at framing-spec
   convergence pass time or spec-drafting time, the sub-events
   combine into single corroboration instances per evidence-
   inflation rejection applied recursively to the methodology
   stack itself.

The evidence inflation rejection discipline is methodology-
stack maturation in its own right (per PR 11 close §2.3 + PR
13 close §1.8 + Placement B precondition 3 recurrence).
Gate 4 close evaluates the cumulative discipline operation
across the three Gate 4 primary PRs (PR 13 + PR 14 + PR 15).

---

## 7. Non-acquisition commitments

PR 14 framing locks the following non-acquisition commitments
(parallel to PR 13 framing §7; gate-level commitments
inherited from Gate 4 framing §7):

**Item 1: No multi-vector fixture.** Per §0 + §5.5 PR-14-
LOCAL pure-isolation discipline. PR 14 ships single-vector
partial-set fixture only. Multi-vector pressure (partial-set +
ordering, partial-set + duplicate-handling, partial-set +
semantic-normalization, partial-set + multi-survivor) is
rejected at the spec layer.

**Item 2: No symmetric-direction fixture or test.** Per §4.4
+ §5.10. PR 14 ships single-direction (authored-superset)
fixture only. Direction-swap variants test the same discipline
through symmetric assertion paths and constitute evidence
inflation.

**Item 3: No new comparator surface.** Per §5.7 + Gate 4
framing §5.3 + Gate 3 close §3 item 2. No new
`DivergenceReport` field; no new `compare_records` keyword
argument; no comparator helper.

**Item 4: No new public API symbols.** Per §5.8 + Gate 4
framing §5.4. `forge_bridge.__all__` preserves at 19 symbols.

**Item 5: No new expectation record schema field.** Per §5.4
predicted form 3 suppression + Gate 2 close §2.4 item 5 + Gate
3 close §3 item 1 inheritance. Expectation record schema
preserves at exactly three required keys (`fixture_id`,
`prompt`, `expected_narrow`).

**Item 6: No production source modifications.** Per §5.3 +
Gate 4 framing §2.2 + Gate 3 close §3 item 11. 0-prod-mod is
the architectural sufficiency signal target; deviations
register as Gate-X inheritance archaeology per §5.11.

**Item 7: No new candidate carriers.** Per §3.1 + Gate 4
framing §3.1 + PR 13 framing §3.1 inheritance. 17 active
carriers; no candidate carrier introduced at PR 14.

**Item 8: No Gate-4-LOCAL governing sentence.** Per §0 + §3.1
+ Gate 4 framing §7 item 22. No speculative Gate-4-LOCAL
authoring at PR 14.

**Item 9: No recomposition arc helper proliferation.** Per
§5.4 predicted form 3 + Gate 3 close §3 item 10. No helper
absorbs the recomposition arc traversal; PR 14 test body
inlines the nine-step traversal annotation pattern PR 11 + PR
13 established.

**Item 10: No PR-N-LOCAL regeneration.** Per §3.10 + Gate 2
framing §3.1 + PR 13 close §2.2. PR-13-LOCAL is PR-of-origin
archaeology; PR-14-LOCAL is parallel scope-local discipline
appropriate to partial-set divergence; PR-14-LOCAL does NOT
regenerate as Gate 4 carrier and does NOT propagate to PR 15.

**Item 11: No fixture-shape extension at the FIXTURE dict.**
Per §5.4 predicted form 3 + Gate 2 close §2.4 item 5. The
FIXTURE dict carries exactly three keys (`fixture_id`,
`prompt`, `expected_narrow`); no fourth key signaling partial-
match intent or direction.

**Item 12: No multi-token prompt + no modified reachable-tool
set.** Per §5.10 Direction A affirmative architectural
decision + §4.6 single-variable discipline preservation. PR 14
reuses prompt `"list"` + `_PR9_REACHABLE_TOOLS` verbatim from
PR 9 + PR 13.

**Item 13: No `_PR9_REACHABLE_TOOLS` modification.** Per §3.3
+ Gate 4 framing §7 item 10. The PR 9 reachable-tool set
declaration preserves at exactly four tools (`forge_ping`,
`forge_list_projects`, `flame_list_libraries`,
`flame_render_status`).

**Item 14: No PR 9 multi-match arbitration trace
modification.** Per §3.3 + Gate 4 framing §7 item 10. The
arbitration trace at `fix_multi_match.py:105-140` preserves
verbatim; PR 14 fixture's arbitration trace section
references the PR 9 multi-match trace as observation grounding.

**Item 15: No 4-step or 5-step decomposition.** Per §4.5 + PR
11 + PR 13 3-step cadence precedent. PR 14 ships 3-step
cadence (Step 1 both skeletons; Step 2 architectural-center
bodies; Step 3 empty verification). 4-step or 5-step
decompositions would engineer cumulative-multi-step
concentration evidence into existence.

**Item 16: No spec layer revisitation at the divergence-vector
selection.** Per §5.10. Direction A is bound at framing per
the affirmative architectural decision; spec-layer revisit
pressure registers as evidence-inflation-through-direction-
symmetry-testing.

**Item 17: No new test-internal archaeology surface.** Per
Gate 3 close §3 item 10 + PR 11 close §2.1 + PR 13 framing §3.2.
`_apply_pr9_patches` + `_read_records` remain test-internal
archaeology surfaces (NOT public APIs); PR 14 consumes them
unchanged; no helper absorbs their behavior at PR 14 scope.

**Item 18: No conditional PR 12 promotion via PR 14.** Per
Gate 4 framing §5.7 + Gate 3 close §1.9. Conditional PR 12
disposition is Gate 4 close scope; PR 14 implementation does
NOT contribute toward PR 12 numbering promotion or rejection.

**Item 19: No four §7.3 ontological question surfacing.** Per
Gate 4 framing §5.2 + Gate 2 close + PR 13 framing §7 item
20. The four §7.3 questions remain intentionally unbound;
PR 14 does NOT surface them at framing/spec/implementation.

**Item 20: No symmetric-direction inverse test pressure.**
Per §4.4 + §5.10. Even if PR 14 implementation surfaces "the
inverse direction is structurally interesting," the inversion
is rejected at the spec layer per §5.10 binding.

**Item 21: No partial_match-aware caller-side computation.**
Per §5.4 predicted form 2 + §5.7. PR 14 test body asserts the
four-key DivergenceReport at full structural fidelity; no
caller-side `overlap = set(authored) & set(observed)`
computation; no caller-side `partial_match = len(overlap) > 0`
derivation; no other consumer-side overlap-aware logic.

**Item 22: No introduction of cross-surface comparator
semantics.** Per Gate 4 framing §5.2 + Gate 3 framing binding
clarification on cross-surface unbinding + PR 13 framing §7
item 22. Cross-surface comparator semantics remain
intentionally unbound at Gate 4; PR 14 does NOT surface them
at framing/spec/implementation.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` unchanged

PR 14 does NOT modify `forge_bridge/corpus/_ALLOWLIST`. The
allowlist preserves unchanged per cleanup-pressure-resistance
class member #1 lock + PR 13 framing §8.1 + Gate 4 framing §8.1.

PR 14 fixture + test consume corpus-internal surfaces through
already-allowlisted import paths.

### 8.2 Layer 2 — four-walker partition unchanged

PR 14 is **target-disjoint from all four walkers** per §3.8
above + Gate 4 framing §8.2 + PR 13 framing §8.2.

The four-walker partition:

- `forge_bridge_persistence_walker.py` — JSONL emission
  semantics. PR 14 emission semantics are inherited from PR
  11 recomposition arc; no new emission topology introduced.
- `forge_bridge_reader_walker.py` — JSONL readback semantics.
  PR 14 readback semantics inherited from PR 11; no new
  readback topology.
- `forge_bridge_capture_walker.py` — capture-side authority
  partitioning. PR 14 does NOT modify capture-side authority
  surfaces.
- `forge_bridge_seed_walker.py` — seed-side authority
  partitioning. PR 14 fixture is data-only (member #9); no
  seed-side authority modifications.

PR 14's target-disjointness from the four walkers preserves
the partition's operational verification target inherited
from Gate 3 close §1.4.

### 8.3 Layer 3 — unchanged

PR 14 does NOT modify `forge_bridge/corpus/_lint.py` or any
Layer 3 lint rule per Gate 4 framing §8.3 + PR 13 framing
§8.3.

Layer 3 lint rules currently include:

- Tool registration via `_TOOL_REGISTRY` lookup (not module-
  level imports).
- Test function naming (e.g., test functions in
  `test_corpus.py` modules).
- Other architectural surface rules.

PR 14 fixture is data-only (no tool registration; no test
function). PR 14 test module has exactly one test function
following the `test_*` naming convention. No Layer 3 lint
modifications required.

---

## 9. Phase-end conditions for PR 14

### 9.1 Test count anchor — 219 forge env collected

PR 14 close phase-end condition:

```
218 baseline (PR 13 close §1.9 forge env collected)
+ 1 PR 14 partial-set divergence recomposition arc test (Step 2)
= 219 forge env collected at PR 14 close
```

**PR 14 Step 3 verification target:**

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
219 tests collected in 0.05s
```

PR 14 ships **1 named test**; named == collected (no
parametrize per §4.4 + §5.2 single-test contract).

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`). Target at PR 14 close:
**212 baseline (PR 13 close §1.9 inheritance) + 1 new = 213
forge-bridge env collected.** Not re-verified at PR 14 close
beyond inheritance documentation — the 6-test gap is PR 7-
scope, not PR 14-scope. **Do not conflate the two env counts**
per PR 13 close §1.9.

### 9.2 PR 14 suite regression — 1/1 passed

PR 14 close phase-end condition:

```
$ python -m pytest tests/corpus/test_pr14_partial_narrow_divergence.py -v
1 passed
```

PR 14 ships **exactly 1 test** per §5.2 + §4.4. The 1/1 pass
result is the operational verification target.

### 9.3 0-prod-mod outcome verified

PR 14 close phase-end condition:

```
$ git diff --stat f53a469..<PR14-final-commit> -- forge_bridge/
(empty)
```

PR 14 modifies **zero production source files**. The
operational verification at close is the git diff --stat
result showing no `forge_bridge/` file modifications across
the PR 14 commit chain.

If the verification fails (production-source modifications
present), the deviation registers per §5.11 protocol — pause,
surface at framing-level evaluation, decide whether deviation
is real architectural gap or transient pressure.

### 9.4 Predicted cleanup-pressure form outcomes recorded

PR 14 close phase-end condition: §5.4 three predicted forms'
implementation-time outcomes recorded at close §1.

| Form | Target outcome | Operational evidence at PR 14 close |
|---|---|---|
| Partial-match-to-full-divergence collapse pressure | ABSENCE | No `narrow_diverged=True` only assertion in test body; four-key structural assertion contract intact. |
| `partial_match` field-addition pressure | ABSENCE | No new `DivergenceReport` field; comparator surface preserves at PR 10 spec §4.1.6 reference implementation. |
| Fixture-shape extension pressure | ABSENCE | FIXTURE dict carries exactly three required keys (`fixture_id`, `prompt`, `expected_narrow`); no fourth key. |

If all three outcomes are ABSENCE, PR 14 contributes 3-form-
ABSENCE evidence toward Placement A (parallel to PR 13's
contribution). If any predicted form surfaces, the outcome
registers as Placement B precondition 3 candidate evidence +
potential cleanup-pressure-resistance class member candidate
per §3.7 + close §1.10 precedent.

### 9.5 Placement B precondition operational manifestation recorded

PR 14 close phase-end condition: §6.2 three Placement B
preconditions' implementation-time manifestation recorded.

| Precondition | Target | Operational verification at PR 14 close |
|---|---|---|
| 1 — Prior pressure prediction at framing time | YES | This framing §5.4 named three predicted forms pre-implementation. |
| 2 — Named suppression mechanism per predicted form | YES | Each suppression mechanism named + grounded (PR 10 §4.2 binding behavioral commitment; `forge_bridge.__all__` 19-symbol lock; expectation record schema three-required-keys lock; PR-11-LOCAL discipline at gate level). |
| 3 — Corroborated recurrence across multiple PR scopes | NOT manifest at PR 14 alone | Cumulative evaluation deferred to Gate 4 close per Gate 4 framing §6.2. |

### 9.6 Module docstring carrier travel verified

PR 14 close phase-end condition: 17 active carriers cited by
reference at both PR 14 module docstrings (per §3.1 citation-
by-reference discipline).

Operational verification at close:

- `test_pr14_partial_narrow_divergence.py` module docstring
  contains the four canonical-source citations (per §3.1
  inventory).
- `fix_partial_narrow_divergence.py` module docstring contains
  the four canonical-source citations.
- The PR 14 commit message bodies under "preserved invariants"
  reference the canonical sources (no verbatim carrier
  recitation).

### 9.7 §2.4 architectural commitment travel verified

PR 14 close phase-end condition: §2.4 architectural commitment
travels verbatim at PR 14 framing/spec/close + commit bodies
per §5.6 + §3.6.

Travel inventory at PR 14 close (target: 8 surfaces, parallel
to PR 13's 8-surface inventory per close §1.5; framing surfaces
deliberately excluded from the close inventory per PR 13 close
§1.5 precedent — framing-internal §2.4 references are framing-
level, not part of the operational travel of the commitment at
PR 14 scope):

| # | Target surface | Carrier-shape |
|---|---|---|
| 1 | PR 14 spec §0 | Verbatim |
| 2 | PR 14 spec §1 architectural commitment section | Verbatim |
| 3 | PR 14 spec §2 architectural commitment section | Verbatim |
| 4 | Step 1 commit body "Architectural commitment" section | Verbatim |
| 5 | Step 2 commit body "Architectural commitment" section | Verbatim |
| 6 | Step 3 commit body "Architectural commitment" section | Verbatim |
| 7 | PR 14 close §1.5 (or equivalent close-time inventory section) | Verbatim |
| 8 | PR 14 close §6.5 architectural-sufficiency verification | Verbatim |

This framing's §2.4 + §3.6 + §5.6 surfaces (3 framing-internal
references) are framing-level binding-decision surfaces and
are NOT counted in the 8-surface close inventory (parallel to
PR 13 close §1.5 inventory exclusion).

NOT in PR 14 test module docstring; NOT in PR 14 fixture
module docstring (per §5.6 binding asymmetry).

### 9.8 Public API anchor — `forge_bridge.__all__` at 19 symbols

PR 14 close phase-end condition:

```python
>>> from forge_bridge import __all__
>>> len(__all__)
19
```

Per §5.8 binding + Gate 4 framing §5.4 + class member #2.

### 9.9 Imports-land-when-used discipline verified (member #10)

PR 14 close phase-end condition: cleanup-pressure-resistance
class member #10 (imports-land-when-used) verified at both PR
14 files symmetrically (per PR 13 close §1.12 precedent).

| File | Step 1 imports | Step 2 imports landed | Step 3 imports |
|---|---|---|---|
| `fix_partial_narrow_divergence.py` | `from __future__ import annotations` only | NO additional imports (FIXTURE dict only requires literal syntax; fixture-data-discipline member #9 prevents). | No changes |
| `test_pr14_partial_narrow_divergence.py` | `from __future__ import annotations` only | `pathlib`, `pytest`, `compare_records`, `drive_seed_fixture`, `FIX_PARTIAL_NARROW_DIVERGENCE`, `_apply_pr9_patches`, `_read_records` (each landed when first used at test body). | No changes |

**No speculative-reserved imports** at either file (member #10
protection). PR 14 contributes a FOURTH instance of member-
#10 verification under integration-work conditions (after
PR 10 + PR 11 + PR 13).

### 9.10 Cleanup-pressure-resistance class additions registered

PR 14 close phase-end condition: any cleanup-pressure-
resistance class additions surfaced during PR 14
implementation are registered at close §1.10 + handed forward
to Gate 4 close for class-level evaluation.

Target outcome: **no new candidate class members surface
during PR 14 implementation** (parallel to PR 13 close §1.10
outcome). The three predicted cleanup-pressure forms (§5.4)
all yield ABSENCE outcomes per discipline operation; no new
class member candidates emerge from PR 14's substrate.

If a new candidate class member surfaces, the candidate
registers as Gate-X inheritance archaeology for Gate 4 close
class-level evaluation (per §3.7 + PR 13 close §1.10
precedent).

### 9.11 Test-internal archaeology surfaces inheritance verified

PR 14 close phase-end condition: `_apply_pr9_patches` and
`_read_records` consumed unchanged at PR 14 as test-internal
archaeology surfaces (NOT public APIs) per PR 11 close §2.1
+ PR 13 close §1.13 precedent.

Operational verification at PR 14 close:

- Imports are placed in a dedicated section of the test module
  file with explicit "Test-internal archaeology surfaces (NOT
  public APIs)" comment marker (per PR 13 close §1.13
  precedent).
- Module docstring's "Test infrastructure import discipline"
  section registers the underscored-private status explicitly
  with anti-promotion framing.
- No PR 14 surface promotes either helper to public API; no
  PR 14 surface modifies either helper's semantics.

PR 14 contributes a **third instance** of the consumption
pattern's stability verification (after PR 11 + PR 13).

### 9.12 Step archaeology summary

PR 14 ships 3 steps following PR 13's both-skeletons-at-Step-1
lifecycle invariant (PR-of-origin archaeology per PR 13 close
§2.4) + PR 11 + PR 13 3-step cadence precedent:

**Step 1: Both skeletons (one commit).**

- `tests/corpus/fixtures/fix_partial_narrow_divergence.py` —
  skeleton: module docstring + `from __future__ import
  annotations` only. NO `FIXTURE` dict yet.
- `tests/corpus/test_pr14_partial_narrow_divergence.py` —
  skeleton: module docstring + `from __future__ import
  annotations` only. NO imports beyond `__future__`. NO test
  function yet.
- Both files land in **one commit** per both-skeletons-at-
  Step-1 lifecycle invariant.
- Commit message format: `phase-a.5.3.2: PR 14 Step 1 — both
  skeletons (test module + fixture module bundled)` + body
  carrying PR-14-LOCAL + carriers travel by citation + Step 1
  archaeology.

**Step 2: Architectural-center (one commit).**

- `tests/corpus/fixtures/fix_partial_narrow_divergence.py` —
  add `FIXTURE` dict.
- `tests/corpus/test_pr14_partial_narrow_divergence.py` —
  add imports (`pathlib`, `pytest`, `compare_records`,
  `drive_seed_fixture`, `FIX_PARTIAL_NARROW_DIVERGENCE`,
  `_apply_pr9_patches`, `_read_records`) + test function
  body.
- Both files land in **one commit** per both-skeletons-at-
  Step-1 lifecycle invariant + symmetric Step 2 landing.
- Commit message format: `phase-a.5.3.2: PR 14 Step 2 —
  architectural-center (test body + FIXTURE dict bundled)` +
  body carrying PR-14-LOCAL + arbitration trace + four-key
  assertion contract.

**Step 3: Final verification (empty commit; archaeology in body).**

- Verification checklist (parallel to PR 13 Step 3 verification
  per close §1):
  1. PR 14 suite: 1/1 ✓ pass.
  2. Full corpus: 219/219 ✓ collected + passed.
  3. PR 4 + PR 5 integration: 13/13 ✓ (regression sweep).
  4. PR 6 Layer 3 lint: 17/17 ✓.
  5. Four Layer 2 walkers: 30/30 ✓.
  6. PR 3 discipline + PR 11 recomposition arc + PR 13
     ordering-divergence: 5/5 ✓ (cumulative regression sweep).
  7. Console chat_handler subset: 50/50 ✓ (PR 11 close §6.7
     anchor preserved).
  8. Full console: 361 collected ✓ (PR 11 close §6.7 anchor
     preserved).
  9. `forge_bridge.__all__` at 19 symbols ✓.
  10. Architectural sufficiency signal verified
      (`git diff --stat f53a469..<PR14-final-commit> --
      forge_bridge/` empty).
- Empty commit + body carrying 10/10 checklist + Placement A
  contribution summary + Placement B preconditions
  manifestation + catch-point migration outcome.
- Commit message format: `phase-a.5.3.2: PR 14 Step 3 — final
  verification (empty commit; archaeology in body)`.

**The 3-step cadence preserves PR 11 + PR 13 precedent** per
§4.5 + Gate 4 framing §3.5. 4-step or 5-step decompositions
are rejected at the framing layer per §4.5 evidence inflation
discipline.

**The both-skeletons-at-Step-1 lifecycle invariant** preserves
from PR 13 close §1.11 + §2.4 PR-of-origin archaeology. PR
14 is the second PR within Gate 4 to ship two new files at
structurally-symmetric skeleton state; the lifecycle invariant
operates against the PR-of-origin precedent.

---

## 10. Cross-references

**Predecessor artifacts (in operational reading order):**

1. `A.5.3.2-FRAMING.md` — phase shape.
2. `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument substrate.
3. `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing.
4. `A.5.3.2-GATE-2-FRAMING.md` — three-authority-surface
   partition; carrier #14.
5. `A.5.3.2-PR7-CLOSE.md` — observation + dispatch-provenance
   surfaces; carrier #14; class members #1–#6.
6. `A.5.3.2-PR8-CLOSE.md` — authored expectation surface;
   class members #7 + #8.
7. `A.5.3.2-PR9-CLOSE.md` — three-fixture corpus; multi-match
   arbitration trace; class member #9; fixture naming
   convention; test infrastructure surfaces.
8. `A.5.3.2-GATE-2-CLOSE.md` — gate-arc synthesis; four §7.3
   ontological questions unbinding.
9. `A.5.3.2-GATE-3-FRAMING.md` — Path B locked precedent;
   binding framing clarification on cross-surface unbinding.
10. `A.5.3.2-PR10-CLOSE.md` — comparator surface operational;
    §4.2 binding behavioral commitment; class member #10.
11. `A.5.3.2-PR11-CLOSE.md` — recomposition arc operational;
    PR-11-LOCAL discipline at gate level; consumption pattern.
12. `A.5.3.2-GATE-3-CLOSE.md` — gate-arc synthesis; carrier
    #16 promotion; 10-member class promotion; 17 active
    carriers; four-walker Layer 2 partition; conditional PR
    12 DEFER.
13. `A.5.3.2-GATE-4-FRAMING.md` — gate-level inheritance
    contract; three-PR primary slot structure; PR ordering;
    §10 PR 14 sub-section.
14. `A.5.3.2-PR13-FRAMING.md` — first-of-three primary PR
    framing precedent; 11-section framing shape (§0–§10
    inclusive); citation-by-reference discipline.
15. `A.5.3.2-PR13-SPEC.md` — fixture + test implementation
    contract precedent.
16. **`A.5.3.2-PR13-CLOSE.md`** — **immediate predecessor;
    calibration substrate at first calibration point;
    PR-13-LOCAL as PR-of-origin archaeology; both-skeletons-
    at-Step-1 lifecycle invariant as PR-of-origin archaeology;
    four-PR architectural sufficiency escalation.**
17. **This framing artifact** — PR 14 second calibration point
    framing.

**Forward references (post-framing artifacts):**

- `A.5.3.2-PR14-SPEC.md` — PR 14 implementation contract (to
  be drafted next per framing-spec convergence pass).
- `A.5.3.2-PR14-CLOSE.md` — PR 14 close artifact (standalone
  close per Gate 4 framing §11.8 + PR 13 close §7 precedent;
  pairs at same commit with FINAL primary PR's close only).

**Implementation file references:**

- `tests/corpus/fixtures/fix_multi_match.py:105-140` — PR 9
  multi-match arbitration trace; PR 14 fixture inherits the
  trace as observation grounding.
- `tests/corpus/test_pr9_fixture_integration.py:208-213` —
  `_PR9_REACHABLE_TOOLS` declared order; PR 14 inherits the
  reachable-tool set verbatim.
- `tests/corpus/fixtures/fix_ordering_divergence.py` — PR 13
  fixture; PR 14 fixture mirrors the structural shape (one
  divergence vector + pure-isolation property enumeration +
  authored-expectation rationale + reference to PR 9 multi-
  match arbitration trace).
- `tests/corpus/test_pr13_ordering_divergence.py` — PR 13
  test; PR 14 test mirrors the 9-step traversal annotation
  pattern + four-key structural assertion contract.
- `tests/corpus/test_pr11_recomposition_arc.py` — PR 11
  recomposition arc consumption pattern; PR 14 inherits via
  PR 13 inheritance chain.
- `forge_bridge/corpus/_compare.py:503` — comparator direct
  list-equality semantics (`obs_decision != exp_narrow`); PR
  14 exercises the line under partial-set divergence pressure.

**Memory cursor references:**

- `feedback_ground_specs_in_actual_files.md` — operative
  discipline at framing-convergence-pass time + spec-drafting
  time for PR 14 (any cited file/section/signature MUST be
  re-read before assertion).
- `feedback_counts_are_archaeology_grade.md` — operative
  discipline at every framing/spec/close count assertion (218
  baseline → 219 target; 17 active carriers; 10-member class;
  19 `__all__` symbols; 5-instance catch-point migration
  descriptive at PR 14 open; 9-surface PR-14-LOCAL travel
  target; 8-surface §2.4 travel target).
- `feedback_writers_room_lead_with_views.md` — operative
  discipline at structural seams in PR 14 framing (direction
  selection at §5.10 led with affirmative architectural-
  decision view; carrier-by-reference adoption at §3.1 led
  with PR 13 precedent inheritance; single-variable-discipline
  recognition at §4.6 led with architectural-substrate-
  evidence view).
- `feedback_deferral_first_class_governance.md` — standalone-
  close discipline at PR 14 close inherits from PR 13 close
  §7 + Gate 4 framing §11.8.
- `feedback_explicitly_unbound_vs_implicitly_rejected.md` —
  cross-surface unbinding + citation-by-reference travel
  discipline at PR 14 framing inheritance.
- `feedback_cursor_before_retrospective_synthesis.md` —
  operative at PR 14 framing close (cursor before PR 14 spec
  drafting begins).
- `project_three_architectural_layers.md` — Layer 2 walkers +
  Layer 3 lint regression sweep evidence persists; PR 14 is
  target-disjoint from all four walkers + Layer 3 lint
  (verified at §3.8 + §8).
