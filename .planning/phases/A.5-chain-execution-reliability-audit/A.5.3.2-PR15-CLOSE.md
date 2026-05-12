# A.5.3.2 PR 15 — Close (multi-survivor cardinality divergence pure-isolation case)

**Status:** PR 15 implementation arc CLOSED. Four-commit
post-spec arc landed verbatim per spec §6.1–§6.3: Step 1
(`d670174`) → Step 2 (`ee88669`) → Step 3 (`693bbb7`) →
this close commit. Zero Step N.5 surgical commits; zero
production source modifications across the full chain
(`de50fea` framing → this close); 220 forge env collected
(EXACT MATCH with spec §5.1 projection of 219 + 1 = 220);
3-form-ABSENCE Placement A contribution; THREE-PR cumulative
manifestation of Placement B precondition 3 completes at
this close.

**PR 15 close pairs at same-commit with Gate 4 close** per
PR 15 framing §11 + §2.4 + Gate 4 framing §11.8 + PR 14
close §7 deferral. **DIFFERENT close cadence from PR 13 +
PR 14 standalone closes** (PR 13 close `f53a469` standalone;
PR 14 close `bbbeead` standalone). PR 15 close + Gate 4
close is the **third operational instance of the same-
commit-pairing pattern** after Gate 2 close (`a6e42f0` —
Gate 2 + PR 6 close pair) + Gate 3 close (`ee2225b` —
Gate 3 + PR 11 close pair). The same-commit-pairing handles
the gate-arc synthesis responsibility cleanly: this artifact
ships PR-15-scoped archaeology; sibling `A.5.3.2-GATE-4-CLOSE.md`
ships gate-arc synthesis; the two artifacts ship at one
commit.

**Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**PR-15-LOCAL binding statement (verbatim per A.5.3.2-PR15-FRAMING.md §0 + §5.5):**

> **PR 15 isolates multi-survivor cardinality divergence as
> the sole pressure vector. Multi-vector fixture pressure
> within PR 15 scope — combining cardinality with ordering,
> semantic-normalization, duplicate-handling, partial-set
> (within shared cardinality), or any other divergence form
> — is rejected at the spec layer. The pure-isolation
> property is what gives PR 15 its laboratory-grade
> methodology corroboration value for Placement A +
> Placement B substrate.**

---

## 1. What PR 15 established

### 1.1 Multi-survivor cardinality divergence recomposition arc operational

PR 15 ships exactly two new files containing exactly one
named test exercising the multi-survivor cardinality
divergence pure-isolation case through the full end-to-end
recomposition arc:

```
fixture (tests/corpus/fixtures/fix_multi_survivor_mismatch.py)
  → drive_seed_fixture          [orchestration seam]
    → emit_seed_expectation     [expectation persistence seam]
    → chat_handler arbitration  [observation production seam]
      → emit_divergence_capture [observation persistence seam]
        → JSONL persistence     [persistence-topology seam]
          → reader              [readback seam (via _read_records)]
            → compare_records   [interpretive-read seam]
              → DivergenceReport assertions (narrow_diverged=True)
```

The fixture authors `expected_narrow` as the **authored-
subset** singleton `["forge_list_projects"]` (Direction A
INVERSE per framing §5.10): a singleton list containing the
observation's position 0 element verbatim. The comparator's
compare-as-persisted discipline (PR 10 §4.2 binding
behavioral commitment) detects the multi-survivor cardinality
divergence at direct list-equality (`obs_decision !=
exp_narrow` per `_compare.py:503`) via length asymmetry (1
vs 2) + element-membership asymmetry at the non-shared
position. No sort / canonicalization / semantic coercion /
cardinality-aware computation at any traversal seam.

**The single test `test_recomposition_arc_multi_survivor_mismatch`
ships at Step 2** with the 9-step traversal annotation pattern
(six header comments covering nine logical traversal steps)
mirroring PR 13 (`test_pr13_ordering_divergence.py:150-203`)
+ PR 14 (`test_pr14_partial_narrow_divergence.py:172-226`)
verbatim except for the multi-survivor-cardinality-specific
content at Step 8 (comparator invocation comment) + Step 9
(four-key assertion contract with singleton/multi-survivor
list values).

**Architectural-pressure-vector-under-test:** cardinality-
class preservation. The structural-shape preservation of
singleton (length 1) vs. multi-survivor (length 2)
cardinality classes IS the architectural claim. The
DivergenceReport's per-surface partitioning preserves
authorship through the recomposition arc; the cardinality-
class structural shape surfaces at distinct list lengths
at `report["expectation"]["expected_narrow"]` (length 1)
vs. `report["observation"]["observed_narrow"]` (length 2).

### 1.2 ZERO incarnation amendments — implementation traveled clean (THIRD operational instance)

PR 15 spec drafting (`6100273`) → Step 1 (`d670174`) →
Step 2 (`ee88669`) → Step 3 (`693bbb7`) traveled **ZERO
incarnation amendments**. The spec was authored verbatim per
PR 15 framing's six binding decisions; the fixture +
test files implemented verbatim per spec §4.1.2 + §4.2.2 +
§4.2.3; the Step 3 verification checklist (10 items) passed
first-try.

**This is the THIRD operational instance of zero-amendment
clean propagation within Gate 4 substrate** (after PR 13 +
PR 14 implementation-time per their Step 3 archaeology;
both ZERO-AMENDMENT). The catch-point migration candidate
methodology accumulates catch-shape continuation of instance
#3 (zero amendments — clean propagation) across the three-PR
Gate 4 substrate:

| PR | Implementation-time outcome |
|---|---|
| PR 13 | ZERO-AMENDMENT clean propagation |
| PR 14 | ZERO-AMENDMENT clean propagation |
| **PR 15 (this PR)** | **ZERO-AMENDMENT clean propagation** |

**THREE-PR cumulative zero-amendment clean-propagation
pattern** at Gate 4 implementation substrate. Gate 4 close
§x evaluates whether the three-PR cumulative archaeology
warrants prescriptive elevation of instance #3 catch-shape.

Additionally, PR 15 surfaces a **three-fold catch-shape
continuation of instance #3 within the single PR scope**
(framing-convergence-pass + spec-drafting-time +
implementation-time, all ZERO-AMENDMENT). PR 15 is the
first PR in catch-point migration archaeology to surface
three continuations of instance #3 in one PR scope. The
single-PR three-fold continuation is observed at this close
and handed to Gate 4 close §x for cross-PR methodology
synthesis.

### 1.3 Architectural sufficiency signal — 0 production source modifications (SIX-PR cumulative)

**`git diff --stat de50fea..693bbb7 -- forge_bridge/`
returns EMPTY.** Zero production source modifications
across the full PR 15 chain (framing → spec → Step 1 →
Step 2 → Step 3).

**SIX-PR cumulative architectural sufficiency escalation
verified** at PR 15 close:

| PR | Production diff | Status |
|---|---|---|
| PR 9 | 0 prod mods | Confirmed (PR 9 close `a6e42f0`) |
| PR 10 | 1 new file (`_compare.py`), 0 mods elsewhere | Confirmed (PR 10 close `cf2b7ee`) |
| PR 11 | 0 prod mods | Confirmed (PR 11 close `ee2225b`) |
| PR 13 | 0 prod mods | Confirmed (PR 13 close `f53a469`) |
| PR 14 | 0 prod mods | Confirmed (PR 14 close `bbbeead`) |
| **PR 15 (this PR)** | **0 prod mods** | **Confirmed (this close)** |

The six-PR cumulative pattern establishes that **the corpus
substrate (PR 9 fixture corpus + PR 10 comparator + PR 11
recomposition arc) is architecturally sufficient for
divergence-shape robustness work**. Each Gate 4 calibration
PR (PR 13 + PR 14 + PR 15) ships against the validated
substrate unchanged, contributing test/fixture surfaces only.
Gate 4 close §x evaluates the six-PR cumulative pattern for
prescriptive promotion candidacy.

**Spec §5.11 justified-deviation protocol NOT triggered** at
PR 15. Zero Step N.5 surgical commits across the PR 15 chain.

### 1.4 PR-15-LOCAL pure-isolation discipline operational (SECOND corroboration of parallel-not-regenerative)

PR-15-LOCAL binding statement operationally verified at
PR 15:

- The fixture authors single-vector pressure: cardinality-
  class asymmetry IS the divergence vector. No ordering /
  semantic-normalization / duplicate-handling / partial-set-
  within-shared-cardinality confound.
- The test asserts the four-key DivergenceReport contract at
  full structural fidelity. No `narrow_diverged`-only
  shortcut; no `cardinality_class` field addition pressure;
  no `expected_cardinality_class` fixture schema extension
  pressure.
- The implementation lands verbatim per spec §4.1.2 + §4.2.3
  without falsifying the pure-isolation property at any
  surface.

**PR-15-LOCAL is the SECOND corroboration of the parallel-
not-regenerative pattern PR 14 introduced** (per PR 14 close
§1.4 + §2.2). The pattern:

| PR | PR-N-LOCAL | Relationship |
|---|---|---|
| PR 13 | PR-13-LOCAL | PR-of-origin for pure-isolation discipline pattern |
| PR 14 | PR-14-LOCAL | Parallel scope-local discipline at second calibration point (introduced parallel-not-regenerative pattern) |
| **PR 15 (this PR)** | **PR-15-LOCAL** | **Parallel scope-local discipline at third calibration point — SECOND corroboration of parallel-not-regenerative pattern** |

The pattern (single-vector fixture pressure as laboratory-
grade calibration substrate) inherits as architectural-
substrate evidence; the specific PR-N-LOCAL statements are
non-regenerating scope-local bindings. PR-15-LOCAL travel
terminates at PR-15-scoped surfaces only (does NOT travel
to Gate 4 close per non-regeneration discipline + scope-
local nature).

Gate 4 close §x evaluates the two-PR-corroborated parallel-
not-regenerative pattern (PR 14 introduce + PR 15 second
corroboration) for prescriptive lineage-discipline promotion
candidacy.

### 1.5 §2.4 Gate 4 architectural commitment travel inventory

§2.4 Gate 4 architectural commitment travels at **9 cumulative
surfaces at PR 15 close** (extended by 1 vs. PR 13 + PR 14
close-time 8-surface inventory; the +1 surface is Gate 4
close's architectural-commitment section, accessible via
same-commit-pairing per framing §9.7):

| # | Surface | Status |
|---|---|---|
| 1 | A.5.3.2-PR15-SPEC.md §0 | LANDED at `6100273` |
| 2 | A.5.3.2-PR15-SPEC.md §1 | LANDED at `6100273` |
| 3 | A.5.3.2-PR15-SPEC.md §2 | LANDED at `6100273` |
| 4 | Step 1 commit body (`d670174`) "architectural commitment" section | LANDED |
| 5 | Step 2 commit body (`ee88669`) "architectural commitment" section | LANDED |
| 6 | Step 3 commit body (`693bbb7`) "architectural commitment" section | LANDED |
| 7 | This close artifact §1 (above the line) | LANDED at this close |
| 8 | This close artifact §6.5 architectural-sufficiency section | LANDED below |
| 9 | A.5.3.2-GATE-4-CLOSE.md architectural-commitment section (same-commit-paired sibling) | LANDED at this close (sibling artifact) |

**+1 surface vs. PR 13 + PR 14 close-time 8-surface
inventory.** The +1 is the Gate 4 close artifact's
architectural-commitment section, accessible via the same-
commit-pairing mechanism. **First operational instance of
9-surface §2.4 travel inventory** in Gate 4 substrate.

**§2.4 commitment travel deliberately stops short of
fixture/test docstrings.** The asymmetry vs. carrier travel
(active carriers DO travel through fixture/test docstrings
per §3.1) preserves the carrier / governing sentence /
methodology-stack category integrity Gate 4 framing
established + PR 13 + PR 14 + PR 15 operationally verified
(per PR 13 close §1.5 + PR 14 close §1.5 inventory
precedents).

### 1.6 Placement A contribution — 3-form-ABSENCE evidence (THIRD Gate 4 PR instance)

PR 15 contributes **3-form-ABSENCE outcome** to Placement A
operational corroboration substrate per framing §6.1:

| Predicted form | Outcome at PR 15 close | Suppression mechanism verified |
|---|---|---|
| Multi-survivor cardinality smoothing pressure | **ABSENCE** | Four-key DivergenceReport assertion contract held; PR 10 §4.2 binding + cleanup-pressure-resistance class member #10 |
| Join-helper proliferation pressure (PR-12 trigger surface) | **ABSENCE** | Step 7 inlines explicit filter + partition; PR-11-LOCAL traverses-not-erases-seams discipline at gate level; PR 12 conditional disposition preserved |
| Recomposition-smoothing-through-helper pressure | **ABSENCE** | 9-step traversal annotation pattern inlined verbatim; PR-11-LOCAL traverses-not-erases-seams discipline at gate level; four-walker Layer 2 partition target-disjointness preserved |

**3-form-ABSENCE outcome at PR 15** mirrors PR 13 + PR 14
pattern exactly. **Third Gate 4 PR contributing 3-form-
ABSENCE** → **nine-form-ABSENCE evidence cumulative across
Gate 4 substrate** (PR 13 + PR 14 + PR 15 each contribute
3-form).

**Cumulative §5.3 candidate methodology observation evidence
at PR 15 close:**

| # | PR | Gate | Outcome |
|---|---|---|---|
| 1 | PR 10 | Gate 3 | ABSENCE |
| 2 | PR 11 | Gate 3 | ABSENCE |
| 3 | PR 13 | Gate 4 (first calibration) | 3-form-ABSENCE |
| 4 | PR 14 | Gate 4 (second calibration) | 3-form-ABSENCE |
| 5 | **PR 15 (this PR)** | **Gate 4 (third + final calibration)** | **3-form-ABSENCE** |

**FIVE-INSTANCE cumulative ABSENCE evidence** for Gate 4
close gate-level promotion evaluation per asymmetric
weighting (PR 11 framing §6.4 + Gate 4 framing §6.4 + PR 13
close §1.6 + PR 14 close §1.6).

### 1.7 Placement B precondition 1 + 2 manifestation; precondition 3 COMPLETES to THREE-PR cumulative

PR 15 contributes to Placement B methodology-stack
maturation substrate per framing §6.2:

| Precondition | PR 15 status | Cumulative across Gate 4 substrate |
|---|---|---|
| 1 (prior pressure prediction at framing time) | MANIFEST at framing §5.4 | **THREE-PR cumulative manifestation** (PR 13 + PR 14 + PR 15) |
| 2 (named suppression mechanism per predicted form) | MANIFEST at framing §5.4 + spec §4.2.4 | **THREE-PR cumulative manifestation** (PR 13 + PR 14 + PR 15) |
| 3 (corroborated recurrence across multiple PR scopes) | **COMPLETES to THREE-PR cumulative manifestation at this close** | **FINAL three-PR manifestation across Gate 4 substrate** |

**Precondition 3 completes at PR 15 close.** The three-PR
cumulative manifestation across Gate 4 substrate (PR 13 +
PR 14 + PR 15 each contribute preconditions 1 + 2) provides
the cumulative-PR-scope evidence Placement B precondition 3
required.

Gate 4 close §x evaluates the THREE-PR final-cumulative
manifestation per Gate 4 framing §6.2 for prescriptive
methodology-stack maturation candidacy toward seed
reliability phase methodology V1.6+.

### 1.8 Catch-point migration — three-fold catch-shape continuation of instance #3 within PR 15 (NOVEL)

PR 15 contributes **three catch-shape continuations of
instance #3** (zero-amendment clean propagation) within the
single PR scope — the **first PR in catch-point migration
archaeology to surface three continuations in one PR scope**:

| Catch-point within PR 15 | Outcome | Catch-shape |
|---|---|---|
| Framing-convergence-pass (pre-framing-landing) | ZERO AMENDMENTS | Framing §0 contains no catch-point section; framing landed at `de50fea` clean |
| Spec-drafting-time (pre-spec-lock) | ZERO GROUNDING CATCHES | Four file-grounding checks performed (`fix_multi_match.py:126`, `_PR9_REACHABLE_TOOLS` at `test_pr9_fixture_integration.py:208-213`, `fix_partial_narrow_divergence.py` line count 207, PR 13/14 traversal markers); all verified intact at spec §0; spec landed at `6100273` clean |
| Implementation-time (Step 3 verification) | ZERO AMENDMENT | No spec amendments surfaced during Steps 1-2 implementation; both files implemented verbatim per spec §4.1.2 + §4.2.2 + §4.2.3; all Step 3 verification checks passed first-try |

**PR 15 single-PR three-fold continuation of instance #3 is
NOVEL within the catch-point migration archaeology.** PR 11
surfaced two-fold continuation (framing-spec + implementation,
both zero-amendment); PR 13 surfaced one continuation
(implementation zero-amendment); PR 14 surfaced one
continuation (implementation zero-amendment); PR 15 surfaces
three within a single PR scope.

**NOT inflated into new methodology instance #6** per
recursive-self-governance discipline (PR 13 close §1.8
precedent + PR 14 close §1.8 three-fold operational
continuation across three methodology-stack levels). The
recursive-self-governance discipline's distinguishing
property: "the catch migrates earlier in the lifecycle,"
NOT "every individual zero-amendment outcome becomes a
separately counted corroboration." Instance #3's catch-
shape (zero-amendment clean propagation) now has multiple
cumulative continuations:

- PR 11 framing-spec drafting time (first occurrence).
- PR 13 implementation-time (continuation).
- PR 14 implementation-time (continuation).
- PR 14 framing-convergence-pass + spec-drafting-time + implementation-time (three continuations in PR 14 scope — pattern surfaced first at PR 14 retrospectively).
- **PR 15 framing-convergence-pass + spec-drafting-time + implementation-time (three continuations in PR 15 scope; this close establishes the single-PR three-fold continuation as a candidate observable pattern at Gate 4 close §x evaluation surface).**

**Three-fold continuation candidate pattern observable:**
**single-PR three-fold cumulative continuation of instance #3
within Gate 4 substrate** (PR 14 + PR 15 both surface
framing + spec + implementation three-fold continuation).
Gate 4 close §x evaluates whether the candidate pattern
warrants prescriptive elevation (e.g., "Gate 4 PRs reliably
exhibit three-fold zero-amendment clean propagation across
the framing → spec → implementation lifecycle").

Progression as of PR 15 close:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration |
| 3 (cont) | PR 13 | Implementation-time | Zero amendments — clean propagation |
| 5 (cont) | PR 14 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #4 (four catches) |
| 5 (cont) | PR 14 spec | Spec-drafting-time pre-spec-lock | Catch-shape continuation of instance #5 (one catch) |
| 3 (cont) | PR 14 implementation | Step 3 final verification | Zero amendments — clean propagation |
| 3 (cont) | PR 15 framing | Framing-convergence-pass pre-commit | Zero amendments — clean propagation |
| 3 (cont) | PR 15 spec | Spec-drafting-time pre-spec-lock | Zero amendments — clean propagation |
| 3 (cont) | **PR 15 implementation** | **Step 3 final verification** | **Zero amendments — clean propagation** |

Progression remains **five-instance descriptive at PR 15
close** with multiple catch-shape continuations under
instances #3, #4, #5. Gate 4 close §x performs the cross-PR
methodology synthesis evaluation across three-PR cumulative
single-PR three-fold continuations.

### 1.9 Test count anchor — 220 forge env collected (exact spec target)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
220 tests collected in 0.05s
```

**EXACT MATCH** with spec §5.1 projection:

```
219 baseline (PR 14 close §1.9 forge env collected)
+   1 PR 15 multi-survivor cardinality divergence test
= 220 forge env collected at PR 15 close
```

**Named-vs-collected discipline:** PR 15 ships 1 named test
(`test_recomposition_arc_multi_survivor_mismatch`); no
`parametrize` decorators; named == collected. The named-
equals-collected identity is structurally locked at PR 15
by single-test pattern.

**Per `feedback_counts_are_archaeology_grade`:** 220 is the
locked archaeology-grade fact at PR 15 close. The four-PR
test count progression across Gate 4 substrate:

| PR | Forge env baseline | Forge env at close | Delta |
|---|---|---|---|
| PR 13 | 217 | 218 | +1 |
| PR 14 | 218 | 219 | +1 |
| **PR 15 (this PR)** | **219** | **220** | **+1** |

**Three-PR cumulative test count delta = +3** across Gate 4
calibration arc (217 → 220).

**Forge-bridge env projection at PR 15 close:** 213 baseline
+ 1 PR 15 = 214 forge-bridge env collected (projected). The
6-test gap inherited from PR 7-scope test-harness debt
(`project_v1_4_x_harness_debt.md`) is NOT in PR 15 scope.

### 1.10 No cleanup-pressure-resistance class additions at PR 15

PR 15 surfaced **no new candidate cleanup-pressure-
resistance class members**. The 10-member class promoted-to-
named-methodology at Gate 3 close §1.6 remains operative
unchanged across the full PR 15 chain (framing → spec →
Step 1 → Step 2 → Step 3 → this close).

The 10-member class operative at PR 15 implementation:

| Member | Discipline | Operational at PR 15 |
|---|---|---|
| #1 | `_KNOWN_RECORD_KINDS` 2-element lock | Inherited; PR 15 fixture's `record_kind` field constrained to observation/expectation |
| #2 | `forge_bridge.__all__` 19-symbol lock | Inherited; 19 symbols preserved (`__all__` length verified) |
| #3 | Three-authority-surface partition | Inherited; PR 15 test asserts three surfaces (fixture_id + expectation + observation + divergence) at distinct dict paths |
| #4 | Expectation record schema three-required-keys non-revisitable | Inherited; FIXTURE dict carries exactly three keys |
| #5 | PR-INTERNAL three-way authority partition | Inherited at gate level |
| #6 | Observation record schema five-required-keys non-revisitable | Inherited |
| #7 | Truth-partitioning (PR-8-LOCAL) | Inherited at gate level |
| #8 | Semantics-not-topology (PR-8-LOCAL) | Inherited at gate level |
| #9 | Fixture-surface-data-discipline | Inherited; PR 15 fixture observes the discipline (data + `from __future__ import annotations` only) |
| #10 | Imports-land-when-used | Inherited; PR 15 test imports land at Step 2 per discipline |

Gate 4 close §x evaluates whether the three-PR cumulative
Gate 4 substrate (PR 13 + PR 14 + PR 15) surfaced any new
candidate class member at any incarnation stage. The
no-new-class-members outcome holds at PR 15 close.

### 1.11 Both-skeletons-at-Step-1 lock operationally verified (THIRD operational corroboration)

PR 15 verifies the both-skeletons-at-Step-1 lifecycle
invariant at **third operational corroboration**:

- Step 1 (`d670174`): BOTH skeletons in one commit (test
  module + fixture module). Module docstrings + `from
  __future__ import annotations` only at each file.
- Step 2 (`ee88669`): BOTH architectural-centers in one
  commit (test body + FIXTURE dict). Imports + 9-step
  traversal + 4-key assertion contract + singleton FIXTURE
  dict landed bundled.
- Step 3 (`693bbb7`): empty verification commit.

**THREE-PR-CORROBORATED archaeological pattern verified:**

| PR | Step 1 | Step 2 | Step 3 |
|---|---|---|---|
| PR 13 (PR-of-origin) | BOTH skeletons bundled | BOTH architectural-centers bundled | empty verification |
| PR 14 (second operational instance) | BOTH skeletons bundled | BOTH architectural-centers bundled | empty verification |
| **PR 15 (third operational instance)** | **BOTH skeletons bundled** | **BOTH architectural-centers bundled** | **empty verification** |

**Three-PR-corroborated archaeological pattern** at Gate 4
close evaluation surface. Asymmetric step structures (file-
asymmetric / 4-step / 2-step compression) rejected at framing
across the three-PR substrate; the both-skeletons lifecycle
invariant operates as architectural-substrate evidence.

Gate 4 close §x evaluates the THREE-PR-CORROBORATED pattern
for prescriptive promotion candidacy.

### 1.12 Imports-land-when-used (member #10) symmetric verification

Both PR 15 files verify the imports-land-when-used discipline
symmetrically:

| File | Step 1 imports | Step 2 imports landed (when first used) | Step 3 imports |
|---|---|---|---|
| `fix_multi_survivor_mismatch.py` | `from __future__ import annotations` only | NO additional imports (FIXTURE dict only requires literal syntax) | No changes |
| `test_pr15_multi_survivor_mismatch.py` | `from __future__ import annotations` only | `pathlib`, `pytest`, `compare_records`, `drive_seed_fixture`, `FIX_MULTI_SURVIVOR_MISMATCH`, `_apply_pr9_patches`, `_read_records` (each landed when first used at test body) | No changes |

**Symmetric application** — both files verify member #10 at
both file-asymmetric points (Step 1 → Step 2 transition).
The single-import discipline at the fixture file is
structural (member #9 fixture-data-discipline + member #10
imports-land-when-used operating jointly). The seven-new-
import discipline at the test file is operational (each
import lands at first-use site at Step 2).

**No speculative-reserved imports** at either file across the
full chain. No imports land for "might be useful later"
purposes (member #10 protection).

### 1.13 Test-internal archaeology surfaces inheritance verified (THIRD operational corroboration)

PR 15 imports `_apply_pr9_patches` and `_read_records` from
`tests.corpus.test_pr9_fixture_integration` as **test-internal
archaeology surfaces**, NOT as public APIs.

**THIRD operational corroboration** of the underscored-
private-status discipline:

| PR | Consumption pattern |
|---|---|
| PR 11 (PR-of-origin) | `test_pr11_recomposition_arc.py:111-114` |
| PR 13 (second corroboration) | `test_pr13_ordering_divergence.py:110-113` |
| PR 14 (second corroboration) | `test_pr14_partial_narrow_divergence.py:117-120` |
| **PR 15 (third corroboration)** | **`test_pr15_multi_survivor_mismatch.py:117-120`** |

**Four-PR cumulative inheritance** of the underscored-
private-status discipline. The "Test-internal archaeology
surfaces (NOT public APIs)" comment marker precedes the
import block at all four files; the discipline is operative
unchanged.

The underscored-private status is preserved — the import is
test-internal and archaeology-explicit; this does NOT promote
the helpers to public APIs. Future contributors must NOT
read this as a general invitation to import underscored-
private helpers across production modules.

### 1.14 PR-12 trigger surface evaluation inputs (NOVEL — final per framing §5.12)

PR 15 contributes the **PR-12 trigger surface evaluation
inputs** per framing §5.12 — a NOVEL contribution surface
at PR 15 (absent from PR 13 + PR 14 close artifacts):

**Actual join call-site count contribution at PR 15:** **1
site** (verified at Step 7 of traversal in
`test_pr15_multi_survivor_mismatch.py`; the standard filter
+ partition pattern PR 11 + PR 13 + PR 14 inherited
unchanged). The single join call-site:

```python
# ── Step 7 of traversal: partition by fixture_id + record_kind ──
matching = [
    r for r in records
    if r.get("fixture_id") == FIX_MULTI_SURVIVOR_MISMATCH["fixture_id"]
]
# ... filter then partition by record_kind
```

**Cumulative call-site count projection at Gate 4 close:**

| PR | Join call-site count contribution |
|---|---|
| PR 11 | 3 sites (recomposition arc 3-test suite) |
| PR 13 | 1 site |
| PR 14 | 1 site |
| **PR 15 (this PR)** | **1 site** |
| **Cumulative at Gate 4 close** | **6 sites** |

**Threshold ≥4 numerically satisfied** at Gate 4 close per
Gate 4 framing §5.10 first clause.

**Qualitative second-clause pressure observation at PR 15:**
**ABSENCE.** No qualitative pressure that "preserving
decomposition becomes harder than abstracting" surfaced
during PR 15 implementation. The filter + partition pattern
remained call-site-explicit; no pressure toward helper
extraction encountered.

**Four-PR cumulative ABSENCE pattern for second-clause
evidence** (PR 11 + PR 13 + PR 14 + PR 15 cumulative ABSENCE
across the four-PR scope evaluation):

| PR | Second-clause qualitative pressure observation |
|---|---|
| PR 11 | ABSENCE (per PR 11 close §1.9 archaeology) |
| PR 13 | ABSENCE (per PR 13 close §1.6 + §5.2 archaeology) |
| PR 14 | ABSENCE (per PR 14 close §1.6 + §5.2 archaeology) |
| **PR 15 (this PR)** | **ABSENCE** |

**Final PR-12 disposition decision:** **DEFERRED to Gate 4
close §x** per framing §5.12 (PR 15 close ships evaluation
inputs; Gate 4 close ships final disposition; three options
per Gate 4 framing §5.10: PROMOTION / DEFERRAL PRESERVED /
REJECTION). The deferral is intentional-unbound-pending-
Gate-4-close per `feedback_explicitly_unbound_vs_implicitly_rejected`,
NOT implicit rejection.

**Sibling artifact `A.5.3.2-GATE-4-CLOSE.md` (same-commit-
paired with this artifact) ships the final PR-12 disposition
decision** based on these PR 15 close §1.14 inputs +
cumulative cross-PR evaluation.

### 1.15 Format-as-structural-claim discipline (NOVEL at PR 15)

PR 15 introduces a **NOVEL format-as-structural-claim
discipline** at two surfaces — first instance in Gate 4
substrate where source-code format encodes architectural-
claim content:

**Surface 1: FIXTURE dict singleton format
(`fix_multi_survivor_mismatch.py:199`):**

```python
FIXTURE: dict = {
    "fixture_id": "fix-pr15-multi-survivor-mismatch",
    "prompt": "list",
    "expected_narrow": ["forge_list_projects"],   # SINGLE LINE — singleton claim
}
```

Contrast PR 14 fixture's three-element multi-line format:

```python
"expected_narrow": [
    "forge_list_projects",
    "flame_list_libraries",
    "forge_ping",
],
```

PR 13 fixture's two-element multi-line format follows the
same multi-line discipline. PR 15 inverts the format
discipline: **singleton list = single-line literal**; the
format choice IS the cardinality-class structural claim
encoded at the source.

**Surface 2: Test body assertion format asymmetry
(`test_pr15_multi_survivor_mismatch.py:148-152`):**

```python
assert report["fixture_id"] == FIX_MULTI_SURVIVOR_MISMATCH["fixture_id"]
assert report["expectation"]["expected_narrow"] == ["forge_list_projects"]   # SINGLE LINE
assert report["observation"]["observed_narrow"] == [                          # MULTI LINE
    "forge_list_projects",
    "flame_list_libraries",
]
assert report["divergence"]["narrow_diverged"] is True
```

Assertion 2 (`expected_narrow`) on a single line; assertion
3 (`observed_narrow`) on multiple lines. **Format asymmetry
visually encodes the cardinality-class divergence at the
assertion site itself.**

**Format-as-structural-claim observation at PR 15:** both
surfaces encode the cardinality-class structural shape claim
directly in the source. Format is the architectural claim,
not ornamental. The reader's eye perceives the cardinality-
class asymmetry at the literal level without consulting the
list element content.

Gate 4 close §x evaluates whether the NOVEL format-as-
structural-claim discipline warrants prescriptive elevation
within the architectural-substrate evidence layer. The
candidate pattern: **"Source-code format encodes architectural-
claim content where the format choice is itself structurally
informative."** Gate 4 close §x assesses against the three-
PR Gate 4 substrate (PR 13 + PR 14 multi-element multi-line
+ PR 15 singleton single-line + format-asymmetric assertion
pair).

---

## 2. What Gate 4 / future Gate-X work inherits from PR 15

### 2.1 The multi-survivor cardinality divergence pure-isolation case as substrate

PR 15 establishes the multi-survivor cardinality divergence
pure-isolation case as **architectural-substrate evidence**
within the Gate 4 three-PR calibration arc. The substrate:

- Fixture corpus extends from PR 9 three-fixture corpus +
  PR 13 ordering-divergence fixture + PR 14 partial-set-
  divergence fixture to **five-fixture Gate 4 corpus**
  (adding `fix_multi_survivor_mismatch.py`).
- Test corpus extends from PR 13 + PR 14 calibration tests
  to **three-test Gate 4 calibration arc** (adding
  `test_pr15_multi_survivor_mismatch.py`).
- Four-PR cumulative single-variable discipline preserved:
  PR 9 / PR 13 / PR 14 / PR 15 share prompt + reachable-tool
  set + arbitration trace + observation; only authored
  expectation varies across four divergence directions.

Future Gate-X work inherits the five-fixture + three-test
calibration arc as stable archaeology; modifications rejected
per spec §3 + §7 + §8 + PR 9 + PR 13 + PR 14 + PR 15 close
inheritance.

**Direction A INVERSE precedent** for future direction-
symmetric pressure evaluation: PR 15 inverts PR 14's
Direction A (authored ⊃ observed) to Direction A INVERSE
(authored ⊂ observed) at the third calibration point.
The two-PR direction-symmetric pair (PR 14 + PR 15)
operationally corroborates the comparator's compare-as-
persisted discipline operates direction-symmetrically. Future
Gate-X work targeting other divergence vectors (semantic-
normalization, duplicate-handling) may evaluate direction-
symmetric variants per the PR 14 + PR 15 precedent.

### 2.2 PR-15-LOCAL pure-isolation discipline as parallel scope-local archaeology

PR-15-LOCAL is **the second corroboration of the parallel-
not-regenerative pattern PR 14 introduced** (per PR 14 close
§1.4 + §2.2). The two-PR-corroborated pattern:

- PR-of-origin: PR 13 (PR-13-LOCAL ordering-isolation
  discipline).
- Second instance (introduce parallel-not-regenerative
  pattern): PR 14 (PR-14-LOCAL partial-set-isolation
  discipline; parallel scope-local to PR-13-LOCAL).
- Third instance (second corroboration of parallel-not-
  regenerative pattern): PR 15 (PR-15-LOCAL multi-survivor-
  cardinality-isolation discipline; parallel scope-local
  to BOTH PR-13-LOCAL AND PR-14-LOCAL).

**Travel discipline preserves at PR 15:** PR-N-LOCAL
statements are non-regenerating scope-local bindings. The
pattern (single-vector fixture pressure as laboratory-grade
calibration substrate) inherits as architectural-substrate
evidence; the specific PR-N-LOCAL statements travel only at
PR-N-scoped surfaces.

Future Gate-X work authoring PR-X-LOCAL bindings inherits
the parallel-not-regenerative pattern: each PR's PR-N-LOCAL
authored fresh appropriate to its target divergence
dimension, NOT regenerated from prior PR-N-LOCAL statements.

### 2.3 The architectural sufficiency signal at PR 15 — six-PR escalation

PR 15 extends the five-PR architectural sufficiency
escalation (PR 9 + PR 10 + PR 11 + PR 13 + PR 14) to
**six-PR cumulative escalation** (adding PR 15). The signal:

- Six PRs ship test/fixture/comparator surfaces only.
- Zero production source modifications across the five-PR
  reliability-extension scope (PR 9 + PR 11 + PR 13 + PR 14
  + PR 15) at the 0-prod-mod outcome.
- One PR (PR 10) ships exactly one new production file
  (`_compare.py`) with zero modifications elsewhere; the
  production-source-addition is itself architectural-
  substrate establishment, not modification of existing
  surfaces.

The six-PR cumulative pattern establishes **the corpus
substrate is architecturally sufficient for divergence-shape
robustness work**. Future Gate-X work targeting other
divergence vectors at Gate 5 (or end-of-A.5.3.2 archaeology)
inherits the six-PR architectural-sufficiency-signal as
substrate-readiness evidence.

Gate 4 close §x evaluates the six-PR cumulative pattern for
prescriptive promotion candidacy.

### 2.4 Both-skeletons-at-Step-1 lifecycle invariant — THIRD operational corroboration

PR 15 contributes the **THIRD operational corroboration**
of the both-skeletons-at-Step-1 lifecycle invariant:

- PR-of-origin: PR 13 (per PR 13 close §2.4 archaeology).
- Second operational instance: PR 14 (per PR 14 close §2.4
  archaeology).
- **Third operational instance: PR 15 (this PR; Step 1
  `d670174` lands BOTH skeletons in one commit).**

**THREE-PR-CORROBORATED archaeological pattern** verified
at PR 15 close. Three independent reliability PRs (each
targeting distinct divergence vectors) reach the both-
skeletons-at-Step-1 lifecycle invariant operationally without
falsification or asymmetric structure pressure.

Future Gate-X work targeting test+fixture-pair-shipping PRs
inherits the both-skeletons-at-Step-1 lifecycle invariant
as substrate-discipline evidence. The pattern's
distinguishing property: both files undergo the same
establishment → activation lifecycle transition; asymmetric
step structures (file-asymmetric / 4-step / 2-step
compression) rejected at framing.

Gate 4 close §x evaluates the THREE-PR-CORROBORATED pattern
for prescriptive promotion candidacy.

### 2.5 Direction selection rationale at framing-level direction-symmetric pressure — SECOND corroboration

PR 15 contributes the **SECOND corroboration** of the
direction selection rationale pattern PR 14 §5.10 introduced.
The two-PR-corroborated pattern:

- Introduction: PR 14 §5.10 — three-reason argumentation
  pattern (substrate reuse + single-variable discipline +
  semantic legibility) for Direction A (authored ⊃ observed).
- Second corroboration: PR 15 §5.10 — three-reason
  argumentation INVERSE (direction-symmetric corroboration
  with PR 14 + single-variable discipline + semantic
  legibility) for Direction A INVERSE (authored ⊂ observed).

**Pattern's distinguishing property:** at framing-level
direction-symmetric pressure (multiple directions could be
selected with equivalent architectural-pressure-vector
content), the affirmative architectural decision is
documented at framing §5.10 with three-reason argumentation.
The argumentation pattern's specific reasons adapt to PR
scope (substrate reuse + single-variable + semantic-legibility
at PR 14; direction-symmetric corroboration + single-variable
+ semantic-legibility at PR 15) while the structural shape
(three-reason argumentation) holds.

Future Gate-X work facing framing-level direction-symmetric
pressure inherits the three-reason argumentation pattern as
direction-selection-discipline evidence.

Gate 4 close §x evaluates the two-PR-corroborated pattern
for prescriptive promotion candidacy.

### 2.6 `"list"`-as-calibration-prompt archaeology — FOUR-PR cumulative

PR 15 extends the `"list"`-as-calibration-prompt archaeology
from PR 9 + PR 13 + PR 14 three-PR cumulative to **four-PR
cumulative** (adding PR 15). The four-PR cumulative pattern:

| PR | Prompt | Divergence vector | Cardinality | Direction |
|---|---|---|---|---|
| PR 9 | "list" | None (baseline) | 2 (multi-survivor, matched) | n/a |
| PR 13 | "list" | Ordering | 2 (same as observation) | n/a (set-equal) |
| PR 14 | "list" | Partial-set | 3 (authored superset) | A (authored ⊃ observed) |
| **PR 15** | **"list"** | **Multi-survivor cardinality** | **1 (singleton subset)** | **A INVERSE (authored ⊂ observed)** |

**The prompt `"list"` is no longer per-PR choice but mature
substrate primitive within Gate 4 reliability work.** Four
independent reliability PRs have inherited the prompt;
prescriptive elevation evaluation pending at Gate 4 close §x
(candidate: "the canonical calibration prompt for Gate 4-
style reliability work").

Future Gate-X work targeting Gate 4-style reliability
calibration inherits the `"list"`-as-calibration-prompt
substrate primitive as predecessor archaeology.

### 2.7 PR-12 trigger surface evaluation inputs handoff to Gate 4 close

PR 15 hands off the **PR-12 trigger surface evaluation
inputs** to Gate 4 close §x for final disposition (per
framing §5.12 + §1.14 above):

- Actual join call-site count at PR 15: 1 site.
- Cumulative call-site count at Gate 4 close: 6 sites (PR 11
  3 + PR 13 1 + PR 14 1 + PR 15 1).
- Threshold ≥4: numerically satisfied.
- Qualitative second-clause pressure: ABSENCE at PR 15
  (four-PR cumulative ABSENCE pattern: PR 11 + PR 13 + PR 14
  + PR 15).
- Final disposition: DEFERRED to Gate 4 close §x.

**Future Gate-X work at Gate 4 close** consumes these inputs
to ship the final PR-12 disposition decision (three options
per Gate 4 framing §5.10: PROMOTION / DEFERRAL PRESERVED /
REJECTION).

### 2.8 Format-as-structural-claim discipline observation — handoff to Gate 4 close

PR 15 surfaces the **NOVEL format-as-structural-claim
discipline** (per §1.15 above) as candidate observation for
Gate 4 close §x cross-PR methodology synthesis evaluation.

**Candidate pattern observation:** "Source-code format
encodes architectural-claim content where the format choice
is itself structurally informative."

Evidence at PR 15:
- Singleton FIXTURE list on single line (cardinality-class
  structural claim).
- Test body assertion 2 single-line / assertion 3 multi-
  line (format asymmetry encoding divergence at assertion
  site).

Gate 4 close §x evaluates whether the candidate pattern
warrants prescriptive elevation. Future Gate-X work
targeting structurally-informative source formatting may
inherit the discipline if Gate 4 close §x promotes it.

---

## 3. What Gate 4 close (sibling artifact) resolves

PR 15 close pairs at same-commit with Gate 4 close per
framing §11 + §2.4 + Gate 4 framing §11.8. **No deferrals
to future Gate-X work at this artifact** — gate-arc synthesis
ships at the sibling Gate 4 close artifact at this same
commit. The synthesis surfaces Gate 4 close resolves:

### 3.1 Gate 4 close synthesis surfaces

| Surface | Resolution venue |
|---|---|
| §5.3 candidate methodology observation promotion evaluation against five-instance cumulative ABSENCE evidence (PR 10 + 11 + 13 + 14 + 15) | Gate 4 close §x |
| Placement A nine-form-ABSENCE cumulative evaluation (PR 13 + PR 14 + PR 15 each 3-form) | Gate 4 close §x |
| Placement B precondition 3 final cumulative manifestation (THREE-PR cumulative; preconditions 1+2 manifest at PR 13 + PR 14 + PR 15) | Gate 4 close §x |
| Six-PR architectural sufficiency signal escalation evaluation (PR 9 + 10 + 11 + 13 + 14 + 15) | Gate 4 close §x |
| Catch-point migration candidate methodology prescriptive promotion evaluation (five-instance descriptive + multiple catch-shape continuations; PR 15 contributes single-PR three-fold continuation observation) | Gate 4 close §x |
| PR-N-LOCAL parallel-not-regenerative pattern promotion evaluation (two-PR corroboration: PR 14 introduce + PR 15 second instance) | Gate 4 close §x |
| Direction selection rationale at framing-level direction-symmetric pressure SECOND corroboration evaluation (PR 14 Direction A + PR 15 Direction A INVERSE) | Gate 4 close §x |
| Both-skeletons-at-Step-1 lifecycle invariant THREE-PR-CORROBORATED archaeological pattern promotion evaluation | Gate 4 close §x |
| PR-12 final disposition decision (consumes PR 15 close §1.14 inputs; three options: PROMOTION / DEFERRAL PRESERVED / REJECTION) | Gate 4 close §x |
| Cleanup-pressure-resistance class promotion evaluation (current 10-member class; any new candidates at Gate 4 substrate) | Gate 4 close §x |
| `"list"`-as-calibration-prompt archaeology prescriptive elevation evaluation (four-PR cumulative: PR 9 + PR 13 + PR 14 + PR 15) | Gate 4 close §x |
| Format-as-structural-claim discipline observation evaluation (NOVEL at PR 15) | Gate 4 close §x |
| Same-commit-paired close cadence operational instance archaeology (third instance: Gate 2 + Gate 3 + this commit) | Gate 4 close §x |
| Four §7.3 ontological questions inheritance toward Gate 5 (or end-of-A.5.3.2 archaeology if Gate 4 closes the phase) | Gate 4 close §x |
| Gate-level inheritance contract toward Gate 5 (or end-of-A.5.3.2 archaeology) | Gate 4 close §x |

PR 15 close ships PR-15-scoped archaeology only; the cross-
PR + gate-arc synthesis surfaces above are resolved at the
sibling artifact at this same commit.

---

## 4. Step-by-step archaeology — 4-commit PR 15 chain

PR 15 implementation arc ships as a 4-commit post-spec arc
(matching PR 13 + PR 14 4-commit precedent except for the
close cadence asymmetry; spec is predecessor context, not
counted in the post-spec arc):

### 4.1 Predecessor: spec `6100273`

`A.5.3.2-PR15-SPEC.md` — 2615 lines / 11 sections /
19 + 7 = 26 subsection-headers (EXACT PARITY with PR 14 spec
26-subsection count; first instance of exact-subsection-
count parity across Gate 4 substrate).

Six binding decisions encoded at file-level precision
(matches framing six-binding count):

1. Fixture filename + module symbol + fixture_id locked.
2. FIXTURE content locked (singleton single-line format).
3. Test module filename + test function name locked.
4. Four-key DivergenceReport assertion contract locked
   (assertion 2 single-line + assertion 3 multi-line format
   asymmetry).
5. PR-12 trigger surface evaluation responsibility encoded
   at six surfaces (§2 + §4.2.4 + §6.2 + §6.3 + §6.4 + §9).
6. Same-commit-paired PR 15 close + Gate 4 close cadence
   encoded at §6.4 + §7 + §9.

Catch-shape continuation of instance #3: zero grounding
catches at spec drafting.

### 4.2 Step 1: `d670174` — both skeletons (test module + fixture module bundled)

343 lines added across two new files:

- `tests/corpus/fixtures/fix_multi_survivor_mismatch.py` —
  module docstring (PR-15-LOCAL + 17 carriers cited by
  reference + grounded arbitration trace + Direction A
  INVERSE rationale + references + fixture-data-discipline
  closing) + `from __future__ import annotations` only.
- `tests/corpus/test_pr15_multi_survivor_mismatch.py` —
  module docstring (PR-15-LOCAL + 17 carriers cited by
  reference + traversal trace + test infrastructure import
  discipline + references) + `from __future__ import
  annotations` only.

Both files at structurally-symmetric skeleton state. Step 1
verification: 0 tests collected at PR 15 module; 219 collected
forge env (PR 14 baseline preserved); 70/70 regression suite
passes unchanged.

### 4.3 Step 2: `ee88669` — both architectural-centers (test body + FIXTURE dict bundled)

157 lines added across the two existing files:

- Fixture: `FIXTURE` dict with three keys (`fixture_id`,
  `prompt`, `expected_narrow`); singleton `expected_narrow`
  in single-line format (format-as-structural-claim).
- Test: 7 imports (pathlib, pytest, compare_records,
  drive_seed_fixture, FIX_MULTI_SURVIVOR_MISMATCH alias,
  _apply_pr9_patches, _read_records) + test function
  `test_recomposition_arc_multi_survivor_mismatch` with
  9-step traversal annotation pattern + 4-key assertion
  contract.

Step 2 verification: 1/1 passed (PR 15 suite); 220 collected
forge env (EXACT MATCH with spec §5.1); 0 production source
modifications; 70/70 regression suite passes unchanged.

### 4.4 Step 3: `693bbb7` — final verification (empty commit; archaeology in body)

Empty commit; archaeology documented in body:

- 10-item Step 3 verification checklist (all PASSED).
- 3-form-ABSENCE cleanup-pressure-resistance outcomes.
- PR-12 trigger surface evaluation inputs (1 site + ABSENCE
  qualitative observation).
- Placement A contribution (3-form-ABSENCE; third Gate 4 PR
  instance).
- Placement B precondition manifestation (1+2 manifest;
  3 completes to THREE-PR cumulative).
- Five-instance §5.3 cumulative ABSENCE evidence (PR 10 +
  11 + 13 + 14 + 15).
- Catch-point migration three-fold continuation of instance
  #3 within PR 15.
- Both-skeletons-at-Step-1 THIRD operational corroboration.
- PR-N-LOCAL parallel-not-regenerative SECOND corroboration.
- Direction selection rationale SECOND corroboration.
- `"list"`-as-calibration-prompt FOUR-PR cumulative.
- Format-as-structural-claim discipline novel introduction.

Verification: `git diff --stat de50fea..HEAD -- forge_bridge/`
→ EMPTY (six-PR cumulative escalation verified).

### 4.5 Close: this commit — PR 15 close + Gate 4 close (same-commit-paired)

PR 15 close artifact (this file) + Gate 4 close artifact
(`A.5.3.2-GATE-4-CLOSE.md`) ship at one commit per framing
§11 + §2.4 + Gate 4 framing §11.8 + PR 14 close §7 deferral.

**Third operational instance of same-commit-pairing
pattern** after Gate 2 close (`a6e42f0`) + Gate 3 close
(`ee2225b`).

Responsibility split:

- PR 15 close (this artifact): PR-15-scoped archaeology
  (§1.1–§1.15) + what Gate 4 / future Gate-X inherits from
  PR 15 (§2) + what Gate 4 close (sibling artifact) resolves
  (§3) + step archaeology (§4) + methodology observations
  at PR 15 scope (§5) + mechanical checkpoints (§6) + same-
  commit-paired close cadence (§7) + cross-references (§8).
- Gate 4 close (sibling artifact): gate-arc synthesis at
  three-PR cumulative scope + cross-PR methodology synthesis
  + prescriptive promotion evaluation + PR-12 final
  disposition + gate-level inheritance contract.

**4-commit post-spec arc verified.** Total PR 15 chain:
framing (`de50fea`) + spec (`6100273`) + Step 1
(`d670174`) + Step 2 (`ee88669`) + Step 3 (`693bbb7`) +
this close = **6 commits across the full PR 15 chain**.

---

## 5. Methodology observations at PR 15 scope

### 5.1 Three-fold catch-shape continuation within single PR scope — candidate observation

PR 15 surfaces the **single-PR three-fold catch-shape
continuation of instance #3** as candidate observation for
Gate 4 close §x cross-PR methodology synthesis:

- Framing-convergence-pass: ZERO AMENDMENTS.
- Spec-drafting-time pre-spec-lock: ZERO GROUNDING CATCHES.
- Implementation-time (Step 3 final verification): ZERO
  AMENDMENT.

**Three-fold cumulative continuation within PR 15 alone.**
The recursive-self-governance discipline operates
symmetrically across the three methodology-stack levels
(framing + spec + implementation). PR 14 close §1.8 surfaced
three-fold catch-shape continuation across instances #3 + #4
+ #5; **PR 15 surfaces three-fold catch-shape continuation
across instance #3 alone (single-instance three-fold)**.

The single-instance three-fold continuation pattern is
distinct from PR 14's three-instance three-fold continuation
pattern. Gate 4 close §x evaluates whether the two patterns
warrant distinct prescriptive elevations.

PR 15's specific archaeology contributes:

- Single-PR three-fold continuation within instance #3 as
  candidate cumulative-archaeology pattern observable.
- Operative discipline at each catch-point: zero amendments
  / zero grounding catches / zero amendments respectively.
- Recursive-self-governance applied at instance-internal
  scope (instance #3's continuations) symmetric to PR 14's
  application at cross-instance scope (instances #3 + #4 +
  #5).

### 5.2 Pointer to Gate 4 close for cross-PR synthesis

Cross-PR methodology synthesis at Gate 4 close §x consumes
the PR 13 + PR 14 + PR 15 archaeology as three-PR cumulative
substrate. Specific synthesis surfaces:

- Three-PR cumulative single-PR three-fold continuation
  observation (PR 13 + PR 14 + PR 15 each surfacing within-
  PR multi-fold continuations of various shapes).
- Three-PR cumulative §5.3 candidate methodology operational
  corroboration (3-form-ABSENCE at each PR; cumulative
  nine-form-ABSENCE).
- Three-PR cumulative both-skeletons-at-Step-1 lifecycle
  invariant operational verification (PR 13 PR-of-origin +
  PR 14 second + PR 15 third).
- Three-PR cumulative PR-N-LOCAL parallel-not-regenerative
  pattern corroboration (PR 13 PR-of-origin pure-isolation +
  PR 14 parallel-not-regenerative pattern introduction +
  PR 15 second corroboration).
- Two-PR cumulative direction selection rationale at framing-
  level direction-symmetric pressure (PR 14 introduce +
  PR 15 second corroboration).
- Four-PR cumulative `"list"`-as-calibration-prompt
  archaeology (PR 9 + PR 13 + PR 14 + PR 15).
- Six-PR cumulative architectural sufficiency signal
  escalation (PR 9 + PR 10 + PR 11 + PR 13 + PR 14 + PR 15).
- Five-instance cumulative §5.3 ABSENCE evidence (PR 10 +
  PR 11 + PR 13 + PR 14 + PR 15).
- Four-PR cumulative PR-12 trigger surface evaluation
  ABSENCE (PR 11 + PR 13 + PR 14 + PR 15 second-clause
  qualitative ABSENCE).
- Single-PR format-as-structural-claim discipline observation
  (PR 15 NOVEL).
- Third-operational-instance same-commit-paired close cadence
  (Gate 2 + Gate 3 + Gate 4 closes).

Gate 4 close §x performs the cross-PR synthesis evaluation
against five candidate methodologies + two PR-14-introduced
patterns + the recursive-self-governance discipline + the
PR-15-introduced format-as-structural-claim discipline
observation + Gate 4 framing §10 four-§7.3 ontological
question inheritance.

### 5.3 PR-15-specific recursive-self-governance application

PR 15 applies the recursive-self-governance discipline at
two surfaces:

**Surface 1: PR 15 close §1.8 catch-point migration
archaeology.** PR 15's single-PR three-fold continuation
of instance #3 is NOT inflated into new methodology instance
#6. The progression remains five-instance descriptive at
PR 15 close. The catch-shape distinguishing property ("the
catch migrates earlier in the lifecycle") preserves; multiple
cumulative continuations of instance #3 register as catch-
shape continuations, NOT separately counted instances.

**Surface 2: PR 15 close §1.14 PR-12 trigger surface
evaluation inputs.** PR 15 ships evaluation inputs (count +
qualitative observation) WITHOUT finalizing the disposition
decision. The decision is deferred to Gate 4 close §x per
framing §5.12. The recursive-self-governance discipline
preserves: the catch (PR-12 trigger surface materialization)
migrates earlier in the lifecycle (from Gate 4 close
unilateral disposition to PR 15 close inputs + Gate 4 close
final disposition), but the disposition itself remains at
gate scope per the cross-PR architectural-decision-locus
discipline.

Gate 4 close §x evaluates whether the recursive-self-
governance discipline's two-surface application at PR 15
warrants prescriptive elevation within the gate-arc synthesis.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 3 item 2)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
220 tests collected in 0.05s
```

**EXACT MATCH** with spec §5.1 + framing §9.1 projection of
219 + 1 = 220. The named-equals-collected discipline holds
at PR 15 close (single test, no parametrize).

### 6.2 PR 15 suite regression (Step 3 item 1)

```
$ python -m pytest tests/corpus/test_pr15_multi_survivor_mismatch.py
============================== 1 passed in 0.07s ==============================
```

**1/1 passed.** The single test
`test_recomposition_arc_multi_survivor_mismatch` exercises
the full end-to-end recomposition arc under multi-survivor
cardinality divergence pressure; all four assertions
(fixture_id + expected_narrow singleton + observed_narrow
multi-survivor + narrow_diverged=True) verify.

### 6.3 Public API anchor (Step 3 item 8)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

**19 symbols preserved.** Cleanup-pressure-resistance class
member #2 (`forge_bridge.__all__` 19-symbol lock) holds at
PR 15 close. Six-PR cumulative preservation: PR 9 + PR 10 +
PR 11 + PR 13 + PR 14 + PR 15 all preserve the 19-symbol
public API.

### 6.4 Four-walker Layer 2 partition (Step 3 item 5)

All four Layer 2 walkers (PR 4 production-import-topology +
PR 8 orchestration-participation + PR 9 declarative-fixture-
data + PR 10 read-only-interpretive-authority) pass
unchanged at PR 15 close. The four-walker partition target-
disjointness from PR 15's two new files preserved:

- PR 4 walker: target-disjoint (no production imports at
  PR 15).
- PR 8 walker: target-disjoint (no orchestration-participation
  surface modification at PR 15).
- PR 9 walker: target-disjoint (PR 15 fixture's single
  `FIXTURE` symbol is the partition's signature member).
- PR 10 walker: target-disjoint (no interpretive-authority
  surface modification at PR 15).

### 6.5 Architectural sufficiency signal (Step 3 item 10)

```
$ git diff --stat de50fea..693bbb7 -- forge_bridge/
(empty)
```

**Zero production source modifications across the full PR 15
chain** (framing `de50fea` → Step 3 `693bbb7`). Six-PR
cumulative architectural sufficiency escalation verified.

**Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

### 6.6 Layer 3 lint regression (Step 3 item 4)

`tests/corpus/test_pr6_visual_asymmetry.py` 17/17 passed
unchanged at PR 15 close. Layer 3 lint operates against
`emit_divergence_capture` call sites at chat_handler; PR 15
test invokes `drive_seed_fixture` (which internally calls
`emit_divergence_capture` once per fixture invocation); no
new call-site surface at PR 15 production code.

### 6.7 PR 11 + PR 13 + PR 14 regression (Step 3 item 7)

- PR 11 recomposition arc: 3/3 passed unchanged.
- PR 13 ordering-divergence: 1/1 passed unchanged.
- PR 14 partial-set-divergence: 1/1 passed unchanged.

PR 15 inherits consumption patterns without modification;
predecessor calibration substrates preserved as stable
archaeology.

### 6.8 PR 4 + PR 5 chat-handler + no-dependency regression (Step 3 item 3)

All PR 4 + PR 5 chat-handler + no-dependency integration
tests pass unchanged at PR 15 close. No `chat_handler`
arbitration surface modifications at PR 15.

### 6.9 Verbatim travel verification (Step 3 item 9)

- **PR-15-LOCAL** verbatim at both PR 15 module docstrings
  + PR 15 commit message bodies + spec §0 + §1 + §2 + this
  close §0 (above the line) + §1.4. Travel terminates at
  PR-15-scoped surfaces (does NOT travel to Gate 4 close per
  non-regeneration discipline + scope-local nature).
- **17 active carriers cited by reference** at both PR 15
  module docstrings per spec §4.1.1 + §4.2.1.
- **§2.4 Gate 4 architectural commitment** travels at 9
  cumulative surfaces (per §1.5 inventory): spec §0 + §1 +
  §2 + Step 1 + Step 2 + Step 3 commit body sections + this
  close §1 + §6.5 + Gate 4 close architectural-commitment
  section (same-commit-paired sibling).

### 6.10 PR-12 trigger surface evaluation inputs verification

```
Step 7 of traversal (test_pr15_multi_survivor_mismatch.py:88-99):
  - 1 join call-site (filter by fixture_id + partition by
    record_kind + observation/expectation selection).
  - No helper invocation; explicit decomposition seam
    preserved at the call site.
Qualitative second-clause pressure observation:
  - ABSENCE (no "preserving decomposition becomes harder
    than abstracting" pressure surfaced during PR 15
    implementation).
```

**1 site contribution + ABSENCE qualitative observation
registered.** Gate 4 close §x consumes for cumulative 6-site
projection + four-PR cumulative ABSENCE second-clause pattern
+ final PR-12 disposition decision.

### 6.11 Format-as-structural-claim verification

```
fix_multi_survivor_mismatch.py:199:
  "expected_narrow": ["forge_list_projects"],   # singleton single-line

test_pr15_multi_survivor_mismatch.py:148-152:
  assert report["expectation"]["expected_narrow"] == ["forge_list_projects"]  # single-line
  assert report["observation"]["observed_narrow"] == [                         # multi-line
      "forge_list_projects",
      "flame_list_libraries",
  ]
```

**Format-as-structural-claim discipline operational at both
surfaces.** The format choice encodes cardinality-class
structural shape claim directly at the source. Gate 4 close
§x evaluates NOVEL discipline for prescriptive promotion
candidacy.

---

## 7. Same-commit-paired close — Gate 4 close at this commit

PR 15 close pairs at same-commit with Gate 4 close per
framing §11 + §2.4 + Gate 4 framing §11.8 + PR 14 close §7
deferral. **DIFFERENT close cadence from PR 13 + PR 14
standalone closes.**

### 7.1 Same-commit-pairing pattern operational instances

| # | Operational instance | Commit |
|---|---|---|
| 1 | Gate 2 close + PR 6 close pair | `a6e42f0` |
| 2 | Gate 3 close + PR 11 close pair | `ee2225b` |
| **3** | **Gate 4 close + PR 15 close pair (this commit)** | **`<this commit>`** |

**Third operational instance of same-commit-pairing pattern**
at this commit. The pattern: gate-arc-synthesis pairs at
same-commit with the FINAL primary PR's close in the gate's
sequenced PR slot structure.

### 7.2 Standalone-vs-paired close cadence asymmetry

| Close | Cadence | Commit |
|---|---|---|
| PR 6 close | Same-commit with Gate 2 close | `a6e42f0` |
| PR 7 close | Standalone | `b035c87` |
| PR 8 close | Standalone | `b102010` |
| PR 9 close | Same-commit with Gate 2 close (NOTE: chronologically Gate 2 close pairing) | n/a (preceded Gate 2 close) |
| PR 10 close | Standalone | `cf2b7ee` |
| PR 11 close | Same-commit with Gate 3 close | `ee2225b` |
| PR 13 close | Standalone | `f53a469` |
| PR 14 close | Standalone | `bbbeead` |
| **PR 15 close** | **Same-commit with Gate 4 close** | **`<this commit>`** |

The cadence asymmetry follows a rule: **closes paired at
same-commit only at Gate-close boundaries** (final primary
PR of the gate's sequenced PR slot structure). Standalone
closes at within-gate boundaries.

### 7.3 Responsibility split at same-commit pairing

- **PR 15 close (this artifact):** PR-15-scoped archaeology.
  §1 (15 subsections) inventory of what PR 15 established;
  §2 (8 subsections) what Gate 4 / future Gate-X inherits
  from PR 15; §3 (1 subsection) what Gate 4 close (sibling)
  resolves; §4 (5 subsections) step-by-step archaeology;
  §5 (3 subsections) methodology observations at PR 15 scope;
  §6 (11 subsections) mechanical checkpoints; §7 (4
  subsections) same-commit-paired close cadence; §8 cross-
  references.
- **Gate 4 close (sibling artifact `A.5.3.2-GATE-4-CLOSE.md`):**
  gate-arc synthesis at three-PR cumulative scope. Cross-PR
  methodology synthesis + prescriptive promotion evaluation
  + PR-12 final disposition + four §7.3 ontological questions
  resolution + gate-level inheritance contract toward Gate 5
  (or end-of-A.5.3.2 archaeology).

### 7.4 Same-commit-pairing benefit at Gate 4 close

The same-commit-pairing at this commit:

- Ships the gate-arc synthesis (Gate 4 close) coupled with
  the PR-15-scoped archaeology (PR 15 close) at one
  archaeological landing.
- Eliminates the asynchronous-close-window ambiguity that
  would arise from standalone Gate 4 close after PR 15
  standalone close (Gate 4 close drafted against PR 15
  close as predecessor; same-commit-pairing collapses the
  two artifacts into one commit's archaeological surface).
- Surfaces +1 §2.4 architectural commitment travel surface
  (Gate 4 close's architectural-commitment section)
  accessible to PR 15 close's surface inventory at the
  same commit (per §1.5 9-surface inventory; +1 vs. PR 13
  + PR 14 8-surface inventory).
- Enables single-commit reading of full Gate 4 close-time
  state by future archaeology readers (gate-arc synthesis
  + PR 15-scoped archaeology + cross-PR cumulative
  evaluation all at one commit boundary).

---

## 8. Cross-references

**Predecessor artifacts (in operational reading order):**

1. `A.5.3.2-FRAMING.md` — phase shape.
2. `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument substrate.
3. `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing.
4. `A.5.3.2-GATE-2-FRAMING.md` — three-authority-surface
   partition; carrier #14.
5. `A.5.3.2-PR7-CLOSE.md` — observation + dispatch-
   provenance surfaces; carrier #14; class members #1–#6.
6. `A.5.3.2-PR8-CLOSE.md` — authored expectation surface;
   class members #7 + #8.
7. `A.5.3.2-PR9-CLOSE.md` — three-fixture corpus; multi-
   match arbitration trace; class member #9; fixture naming
   convention; test infrastructure surfaces.
8. `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — first operational
   instance of same-commit-pairing pattern (Gate 2 + PR 6
   close pair).
9. `A.5.3.2-GATE-3-FRAMING.md` — Path B locked precedent;
   binding framing clarification on cross-surface unbinding.
10. `A.5.3.2-PR10-CLOSE.md` — comparator surface operational;
    §4.2 binding behavioral commitment; class member #10.
11. `A.5.3.2-PR11-CLOSE.md` — recomposition arc operational;
    PR-11-LOCAL discipline at gate level; PR-12 trigger
    surface 3-call-site contribution to cumulative
    evaluation.
12. `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`) — second
    operational instance of same-commit-pairing pattern
    (Gate 3 + PR 11 close pair); carrier #16 promotion;
    10-member class promotion; conditional PR 12 DEFER
    (PR 15 reopens evaluation per framing §5.12).
13. `A.5.3.2-GATE-4-FRAMING.md` (`fbf2285`) — gate-level
    inheritance contract; §2.4 architectural commitment;
    three-PR primary slot structure; §10 PR 15 sub-section;
    §11.8 same-commit Gate 4 close pattern.
14. `A.5.3.2-PR13-FRAMING.md` (`8f429b2`) — first-of-three
    primary PR framing precedent.
15. `A.5.3.2-PR13-SPEC.md` (`2e05149`) — first-of-three
    primary PR spec precedent.
16. `A.5.3.2-PR13-CLOSE.md` (`f53a469`) — first calibration
    point predecessor; PR-13-LOCAL as PR-of-origin for
    pure-isolation pattern + both-skeletons-at-Step-1
    lifecycle invariant; 3-form-ABSENCE Placement A
    contribution precedent.
17. `A.5.3.2-PR14-FRAMING.md` (`30412a3`) — second-of-three
    primary PR framing precedent; Direction A authored-
    superset rationale precedent (which PR 15 inverts to
    authored-subset Direction A INVERSE).
18. `A.5.3.2-PR14-SPEC.md` (`23c358a`) — second-of-three
    primary PR spec precedent; 26-subsection-header shape
    matched at PR 15 spec.
19. `A.5.3.2-PR14-CLOSE.md` (`bbbeead`) — **immediate
    predecessor; second calibration substrate.** PR-14-LOCAL
    parallel-not-regenerative scope-local discipline (PR 15
    second corroboration); 3-form-ABSENCE SECOND Gate 4 PR
    instance (PR 15 THIRD instance); three-fold catch-shape
    continuation precedent; five-PR architectural-
    sufficiency escalation evidence (PR 15 extends to
    six-PR).
20. `A.5.3.2-PR15-FRAMING.md` (`de50fea`) — binding pre-spec
    contract for PR 15; six binding decisions; PR-15-LOCAL
    + Direction A INVERSE + PR-12 trigger surface evaluation
    responsibility + same-commit-paired close cadence.
21. `A.5.3.2-PR15-SPEC.md` (`6100273`) — PR 15 implementation
    contract; 11-section / 26-subsection-header shape;
    file-level precision derived from framing.
22. **This close artifact** — PR-15-scoped archaeology.

**Sibling artifact (same-commit-paired):**

- `A.5.3.2-GATE-4-CLOSE.md` — gate-arc synthesis at three-PR
  cumulative scope (Gate 4 substrate: PR 13 + PR 14 + PR 15);
  cross-PR methodology synthesis; prescriptive promotion
  evaluation; PR-12 final disposition; gate-level inheritance
  contract.

**Implementation file references (final state at PR 15
close):**

- `tests/corpus/fixtures/fix_multi_survivor_mismatch.py` —
  PR 15 fixture (final state at Step 2 `ee88669`; ~205
  lines).
- `tests/corpus/test_pr15_multi_survivor_mismatch.py` —
  PR 15 test (final state at Step 2 `ee88669`; ~252 lines).
- `tests/corpus/fixtures/fix_multi_match.py:105-140` — PR 9
  multi-match arbitration trace (inherited).
- `tests/corpus/fixtures/fix_multi_match.py:126` — PR 9
  observation list-literal source line; PR 15's
  `expected_narrow[0]` grounds against.
- `tests/corpus/test_pr9_fixture_integration.py:208-213` —
  `_PR9_REACHABLE_TOOLS` declared order; `forge_list_projects`
  at line 210 (index 1).
- `tests/corpus/test_pr9_fixture_integration.py:117-120` —
  `_apply_pr9_patches` + `_read_records` definitions.
- `tests/corpus/fixtures/fix_ordering_divergence.py` — PR 13
  fixture (149 lines; structural shape PR 15 mirrors).
- `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
  — PR 14 fixture (207 lines; structural shape PR 15
  mirrors with singleton inversion).
- `tests/corpus/test_pr13_ordering_divergence.py:150-203`
  — PR 13 test 9-step traversal annotation pattern (mirrored
  at PR 15).
- `tests/corpus/test_pr14_partial_narrow_divergence.py:172-226`
  — PR 14 test 9-step traversal annotation pattern (mirrored
  at PR 15).
- `forge_bridge/corpus/_compare.py:503` — comparator's
  direct list-equality semantics.
- `forge_bridge/corpus/_capture.py:6-135` — carriers #1-#14.
- `forge_bridge/corpus/_seed.py:19-135` — carrier #15.
- `forge_bridge/corpus/_compare.py` module docstring + 
  `compare_records` function docstring — carrier #17.

**Memory cursor references:**

- `feedback_counts_are_archaeology_grade.md` — operative at
  every count assertion in this close (220 forge env / 19
  `__all__` / 17 carriers / 10-member class / 6-PR
  escalation / 5-instance §5.3 ABSENCE / 3-form-ABSENCE /
  6 cumulative call-sites / 9-surface §2.4 / 6 commit-chain
  surfaces).
- `feedback_ground_specs_in_actual_files.md` — applied at
  spec drafting + implementation; zero grounding catches
  surfaced (three-fold catch-shape continuation of instance
  #3 within PR 15).
- `feedback_writers_room_lead_with_views.md` — operative at
  PR-12 trigger surface evaluation inputs registration +
  format-as-structural-claim discipline introduction +
  same-commit-paired close cadence operationalization.
- `feedback_deferral_first_class_governance.md` — operative
  at same-commit-paired close discipline (Gate 4 close
  same-commit responsibility) + PR-12 final disposition
  deferral to Gate 4 close §x.
- `feedback_decomposition_recomposition_validation_arc.md`
  — Gate 4 close §x evaluation surface; three-PR primary
  slot structure recomposition arc cumulative validation
  completes at this close + Gate 4 close pairing.
- `feedback_explicitly_unbound_vs_implicitly_rejected.md` —
  PR-12 disposition deferral is intentional-unbound-pending-
  Gate-4-close, NOT implicit rejection.
- `feedback_cursor_before_retrospective_synthesis.md` —
  operative at PR 15 implementation-closed cursor cut
  (`project_state_2026_05_12_pr_15_implementation_closed.md`)
  before this close artifact drafting; cursor preserved
  fresh implementation-arc-closed state before close
  artifacts compressed the narrative.
- `project_three_architectural_layers.md` — Layer 2 walkers
  + Layer 3 lint regression sweep evidence persists; PR 15
  is target-disjoint from all four walkers + Layer 3 lint.
- `project_state_2026_05_12_pr_15_implementation_closed.md`
  — immediate predecessor cursor; this close artifact's
  drafting input.
