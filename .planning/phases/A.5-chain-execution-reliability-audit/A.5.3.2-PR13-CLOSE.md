# A.5.3.2 PR 13 — Close (ordering-divergence pure-isolation case)

**Status:** Durable archival state. PR 13 is the FIRST of
three primary PRs sequenced within Gate 4 (PR 13 ordering-
divergence + PR 14 + PR 15; conditional PR 12 disposition
deferred to Gate 4 close per Gate 4 framing §5.10). The
implementation arc that began at PR 13 framing commit
`8f429b2` (2026-05-12) closes at this commit.

PR 13 ships **two new files** containing **exactly one named
test** that exercises an ordering-divergence pure-isolation
case at the chat-handler observation surface:

| File | Lines | Role |
|---|---|---|
| `tests/corpus/fixtures/fix_ordering_divergence.py` | 149 | Seed fixture — `prompt "list"` + `expected_narrow [flame_list_libraries, forge_list_projects]` (swap of observed PR 9 multi-match arbitration order) |
| `tests/corpus/test_pr13_ordering_divergence.py` | 224 | Single integration test (`test_recomposition_arc_ordering_divergence`) driving the fixture through the full decomposition seam path under ordering-divergence pressure |

The implementation arc traveled with **ZERO production source
modifications**, **ZERO spec amendments at incarnation**,
**ZERO cleanup-pressure forms surfacing**, and **ZERO Step
N.5 surgical commits**. Three predicted cleanup-pressure
forms named pre-implementation (PR 13 framing §5.4 + spec
§4.2.4) all exhibited ABSENCE — operationally suppressed at
the assertion contract through PR-11-LOCAL discipline at gate
level + PR 10 §4.2 binding behavioral commitment.

**This artifact ships STANDALONE** per Gate 4 framing §11.8 +
PR 13 framing §3.6 + spec §6.4. Gate 4 close
(`A.5.3.2-GATE-4-CLOSE.md`) pairs at the same commit with the
FINAL primary PR's close (PR 15 close OR PR 12 close if PR 12
materializes last per Gate 2 + Gate 3 close precedent). PR 13
is the FIRST of three primary PRs sequenced within Gate 4;
PR 13 close ships at its own commit. The §7 section below
documents the standalone-close discipline + the cross-artifact
responsibility deferral toward Gate 4 close.

---

## 1. What PR 13 established

### 1.1 Ordering-divergence recomposition arc operational

PR 13 ships `tests/corpus/test_pr13_ordering_divergence.py`
(224 lines) — a single new test module containing one
integration test that exercises the end-to-end recomposition
arc under ordering-only divergence pressure per spec §4.2:

| Test | Fixture | Outcome | Divergence vector |
|---|---|---|---|
| `test_recomposition_arc_ordering_divergence` | `fix-pr13-ordering-divergence` (prompt `"list"`) | PR14 yields 2 candidates; PR21 cannot collapse; observed `narrower.decision = ["forge_list_projects", "flame_list_libraries"]` | Authored `expected_narrow = ["flame_list_libraries", "forge_list_projects"]` (positions 0 and 1 swapped); `narrow_diverged=True` per `_compare.py:503` direct list-equality |

The test traverses the full decomposition seam path
explicitly at the test body level (per spec §4.2.3 nine-step
traversal annotation):

```
fixture (fix_ordering_divergence.py)
  → drive_seed_fixture          [orchestration seam]
    → emit_seed_expectation     [expectation persistence seam]
    → chat_handler arbitration  [observation production seam]
      → emit_divergence_capture [observation persistence seam]
        → JSONL persistence     [persistence-topology seam]
          → reader              [readback seam (via _read_records)]
            → compare_records   [interpretive-read seam]
              → DivergenceReport assertions (narrow_diverged=True)
```

The PR 11 consumption pattern (`_apply_pr9_patches` +
`drive_seed_fixture` + `_read_records` + partition-by-
fixture-id-and-record-kind + `compare_records` + four-key
assertions) is inherited unchanged. PR 13 adds the ordering-
divergence-specific authored expectation (the swap) and the
list-equality assertions that read the four-key shape at
full structural fidelity.

**Pure-isolation property** (PR 13 framing §5.5 + spec §4.1.1):

| Dimension | PR 13 outcome |
|---|---|
| Same set | `{forge_list_projects, flame_list_libraries}` at both surfaces |
| Different sequence | Positions 0 and 1 swapped |
| Cardinality | NO divergence (both lists length 2) |
| Partial-set membership | NO divergence (identical membership) |
| Semantic-normalization | NO divergence (exact-match identifiers) |
| Duplicate-handling | NO divergence (distinct elements at both lists) |

PR 13 isolates the ordering-divergence vector as the sole
pressure on the comparator's compare-as-persisted discipline.
This is the laboratory-grade methodology-corroboration value
PR 13 contributes to Placement A + Placement B substrate
(per Gate 4 framing §6).

### 1.2 ZERO incarnation amendments — implementation traveled clean

PR 13 shipped with **ZERO spec amendments at any incarnation
surface**:

- ZERO drafting-time amendments at spec drafting.
- ZERO grounding-time amendments at Step 1 implementation
  prep.
- ZERO implementation-time amendments during Steps 1–2.
- ZERO verification-time amendments at Step 3.
- ZERO Step N.5 surgical commits.

PR 13 matches PR 11's zero-incarnation-amendments archaeology
verbatim. The framing → spec → implementation arc traveled
clean without in-flight realignment at ANY incarnation
surface.

**The framing-convergence + spec-drafting passes registered
the grounding discipline operationally** at TWO catch-points
within PR 13's scope (per spec §0):

1. **Framing-convergence-pass pre-commit** (fourth catch-
   point migration instance) — six file-grounding catches at
   framing convergence per PR 13 framing §3.6.
2. **Spec-drafting-time pre-spec-lock** (fifth catch-point
   migration instance, single corroboration) — fixture-
   cardinality grounding caught BEFORE spec lock. The
   framing's §2.2 + §4.1 symbolic notation `[A, B, C] →
   [C, A, B]` (3-element rotation) could have silently
   drifted into spec-level implementation assumption.
   Instead, grounding the arbitration topology in actual
   `_PR9_REACHABLE_TOOLS` arbitration behavior BEFORE
   locking spec values surfaced the structural constraint
   (3-element deterministic survival unavailable from the
   existing reachable set without modifying it OR adding
   patches — both rejected per framing §3.7 + §9.11). Spec
   adopted 2-element form preserving empirically bounded
   topology discipline.

The post-draft §11.8 cadence verification catch is treated
as part of the SAME fifth-instance corroboration as the
pre-draft fixture-cardinality grounding catch — both share
catch-shape ("grounded in framing's actual text before spec
commits"). The evidence-inflation rejection discipline that
PR 13 framing §4.4 encodes for variant evidence operates
recursively at the methodology-stack level here.

The methodology-stack-level recursion is itself archaeology-
grade: the discipline operating on its own evidence is the
operational form of methodology maturation. Gate 4 close §x
evaluates instance #5's contribution toward catch-point-
migration candidate methodology promotion candidacy.

### 1.3 Architectural sufficiency signal — 0 production source modifications

PR 13 ships **0 modifications to production source files**:

```
$ git diff --stat 8f429b2..HEAD -- forge_bridge/
(empty)
```

Verified by inspection across all 4 PR 13 commits (spec + 3
implementation steps). The 0-prod-mod outcome is the
**architectural sufficiency signal** per Gate 4 framing §2.4
+ PR 13 framing §5.3 binding decision + spec §1 regression
contract #10.

**Four-PR architectural sufficiency escalation** (Gate 3
ended at three-PR; PR 13 makes it four-PR):

| PR | Production diff | Validation strength |
|---|---|---|
| PR 9 | 0 prod mods (test-surface-only fixture authoring) | Substrate surfaces sufficient for fixture authoring + integration tests against existing surfaces |
| PR 10 | Exactly 1 new file (`_compare.py`, 523 lines), 0 mods elsewhere | New read-side surface composable without modifying existing surfaces |
| PR 11 | 0 prod mods (test-surface-only end-to-end recomposition) | Full recomposition arc traversable without modifying ANY production surface — decomposition strategy operationally validated by end-to-end exercise |
| **PR 13** | **0 prod mods (test-surface-only ordering-divergence pure-isolation exercise)** | **Ordering-divergence vector detectable end-to-end through validated PR 10 comparator + PR 11 recomposition arc WITHOUT ANY production source change — divergence-shape robustness operationally validated** |

PR 13's 0-prod-mod outcome is the **first piece of evidence
toward Gate 4 close's three-PR cumulative architectural-
sufficiency evaluation** (cumulative across PR 13 + PR 14 +
PR 15; Gate 4 close performs the gate-level evaluation per
spec §6.4 + Gate 4 framing §6). The four-PR escalation
across Gate 3 + Gate 4 substrate (PR 9 + PR 10 + PR 11 +
PR 13) corroborates the architectural-sufficiency-signal
template introduced at PR 11 framing §5.2.

The signal travels at:

- All 3 PR 13 step commit message bodies under
  "Architectural sufficiency signal" sections.
- This close artifact §1.3 + §6.5.
- (Future) Gate 4 close — gate-level evaluation at same-
  commit pairing with the final primary PR's close.

### 1.4 PR-13-LOCAL pure-isolation discipline operational

PR-13-LOCAL binding statement (per PR 13 framing §5.5 + spec
§0, scope-local per PR-N-LOCAL non-regeneration rule):

> **PR 13 isolates ordering divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 13 scope —
> combining ordering with cardinality, partial-set,
> semantic-normalization, duplicate-handling, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 13 its
> laboratory-grade methodology corroboration value for
> Placement A + Placement B substrate.**

**Operational evidence at PR 13:**

- The fixture authors exactly ONE divergence vector
  (ordering) and ZERO divergence vectors across the other
  five dimensions (cardinality, partial-set, semantic-
  normalization, duplicate-handling, sequence elsewhere).
  Verified at fix_ordering_divergence.py:78–93 (pure-
  isolation property enumerated at every dimension).
- The test asserts list-equality at four DivergenceReport
  keys at full structural fidelity (NOT set-equality, NOT
  canonicalization, NOT a single-call helper) per spec
  §4.2.3 + §4.2.4.
- No fixture extension toward multi-vector pressure was
  authored. No "ordering+cardinality" combined fixture; no
  "ordering+partial-set" combined fixture; no "ordering-
  with-duplicates" variant. Each is intentionally unbound
  pending PR 14 + PR 15 + future-gate framing pressure.

**Operational travel of PR-13-LOCAL** (9 surfaces):

| # | Surface | Carrier-shape |
|---|---|---|
| 1 | `tests/corpus/fixtures/fix_ordering_divergence.py` module docstring | Verbatim |
| 2 | `tests/corpus/test_pr13_ordering_divergence.py` module docstring | Verbatim |
| 3 | Step 1 commit body | Verbatim |
| 4 | Step 2 commit body | Verbatim |
| 5 | Step 3 commit body | Verbatim |
| 6 | PR 13 spec §0 | Verbatim |
| 7 | PR 13 spec §1 | Verbatim |
| 8 | PR 13 spec §2 | Verbatim |
| 9 | This close artifact §1.4 | Verbatim (above) |

**PR-13-LOCAL does NOT regenerate beyond PR 13.** PR 14 + PR
15 + future-gate framing passes do not inherit PR-13-LOCAL
as carrier. The pure-isolation pattern may register as PR-of-
origin substrate for Gate 4 close's Placement A cumulative
evaluation (per §2.2 below); the scope-local discipline
itself is PR-13-specific.

### 1.5 §2.4 Gate 4 architectural commitment travel inventory

§2.4 Gate 4 architectural commitment (verbatim, per Gate 4
framing §2.4 + spec §0):

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**Operational travel of §2.4 commitment at PR 13 scope**
(8 surfaces; deliberately NOT at fixture/test docstrings per
spec §0 + framing §3.6 — carrier / gate-shaped governance
asymmetry preserved):

| # | Surface | Carrier-shape |
|---|---|---|
| 1 | PR 13 spec §0 (above the line) | Verbatim |
| 2 | PR 13 spec §1 architectural commitment section | Verbatim |
| 3 | PR 13 spec §2 architectural commitment section | Verbatim |
| 4 | Step 1 commit body "Architectural commitment" section | Verbatim |
| 5 | Step 2 commit body "Architectural commitment" section | Verbatim |
| 6 | Step 3 commit body "Architectural commitment" section | Verbatim |
| 7 | This close artifact §1.5 (above) | Verbatim |
| 8 | This close artifact §6.5 architectural-sufficiency verification | Verbatim |

**Travel deliberately stops short of fixture/test docstrings.**
The §2.4 sentence is gate-shaped architectural posture, NOT
carrier-shaped governance. Carriers travel through fixture/
test docstrings; the §2.4 commitment does not. The asymmetry
preserves the carrier / governing sentence / methodology-stack
category integrity Gate 4 framing established.

The asymmetry is verified by inspection at both module
docstrings: PR-13-LOCAL appears verbatim at both; the §2.4
sentence appears at neither.

### 1.6 Placement A contribution — 3-form-ABSENCE evidence

Three predicted cleanup-pressure forms were named at PR 13
framing §5.4 + spec §4.2.4 pre-implementation. **All three
exhibited ABSENCE during PR 13 implementation:**

| Form | Outcome | Operational evidence at PR 13 |
|---|---|---|
| Canonicalization pressure (framing §5.4 form 1) | ABSENCE | No `sorted()` call in test body; no sort instruction at fixture authoring; comparator's direct list-equality at `_compare.py:503` detected the ordering-only divergence without caller-side normalization. |
| Set-equality collapse pressure (framing §5.4 form 2) | ABSENCE | No `set(...) == set(...)` shortcut in test body; the four-key structural assertion contract reads list-equality at full structural fidelity. |
| Ordering-specific test helper pressure (framing §5.4 form 3) | ABSENCE | No `assert_ordering_divergence(...)` helper authored; assertions inlined explicitly at test body per PR-11-LOCAL discipline at gate level (Gate 3 close §3 item 10). |

**PR 13 contributes 3-form-ABSENCE evidence toward Placement
A.** Gate 4 close reads cumulative across PR 13 + PR 14 +
PR 15 for the three-PR-cumulative Placement A operational
corroboration evaluation per Gate 4 framing §6.1.

**Why the framing-time discipline operated at PR 13
specifically:** PR-13-LOCAL elevated the pure-isolation
property to named-discipline status (per §1.4 above). The
discipline operated as anchored governance at each Step 1 +
Step 2 implementation decision. The temptation to "make the
ordering-divergence assertion cleaner" via any of the three
forms would have been a real pressure under different
framing — but the laboratory-grade-methodology-corroboration
goal made every form rejected at the design level (per spec
§4.2.4 + framing §5.4 + PR-11-LOCAL inherited at gate level).

This is the operational form of the §5.3 candidate methodology
observation (per PR 10 close §5.3 + PR 11 close §1.6): when
framing-time prediction elevates a goal to named-discipline
status, the discipline shapes implementation decisions
without needing per-pressure rejection events. PR 13
contributes the THIRD instance to this candidate methodology
observation (after PR 10's first and PR 11's second);
**three independent instances now corroborate the
framing-time-pressure-prediction-through-absence pattern**:

| Instance | PR | Outcome |
|---|---|---|
| 1 | PR 10 | ABSENCE (helper merger / persistence creep / walker abstraction) |
| 2 | PR 11 | ABSENCE (helper merger / premature surface normalization / fixture widening / recomposition smoothing) |
| **3** | **PR 13** | **ABSENCE (canonicalization / set-equality collapse / ordering-specific helper)** |

PR 13 close registers the third-instance outcome as raw
archaeology; Gate 4 close performs the gate-level promotion
evaluation against the three-instance cumulative evidence per
asymmetric weighting (PR 11 framing §6.4 + Gate 4 framing
§6.4).

### 1.7 Placement B precondition 1 + 2 manifestation

Gate 4 framing §6.2 named Placement B as
**methodology-stack-maturation-substrate** with three
preconditions toward operational manifestation. PR 13's
contribution to Placement B precondition manifestation:

| Precondition | Manifest at PR 13? | Evidence |
|---|---|---|
| 1 — Prior pressure prediction at framing time | YES | PR 13 framing §5.4 + spec §4.2.4 named three predicted cleanup-pressure forms pre-implementation; framing-time discipline operationally enforced per §1.6 above. |
| 2 — Named suppression mechanism per predicted form | YES | Each suppression mechanism named and grounded: list-equality (NOT set-equality) at `_compare.py:503`; no caller-side sort at framing §5.4 form 1 suppression; inlined assertions at framing §5.4 form 3 suppression. All three grounded in PR 10 §4.2 binding behavioral commitment + PR-11-LOCAL discipline inherited at gate level. |
| 3 — Corroborated recurrence across multiple PR scopes | **NOT manifest at PR 13 alone** | Precondition 3 requires multi-PR corroborated recurrence. PR 13 contributes the first instance; PR 14 + PR 15 contribute additional instances; Gate 4 close evaluates cumulative manifestation per Gate 4 framing §6.2. |

PR 13's contribution to Placement B is **operationally
substrate** — preconditions 1 + 2 manifest at PR 13's
framing → spec → implementation arc. Precondition 3's
cross-PR-recurrence evaluation is deferred to Gate 4 close
per framing §6.2 + spec §6.4.

### 1.8 Catch-point migration instance #5 — single corroboration

PR 10 close §5.3 + PR 11 close §1.6 + PR 11 close §5.1
established the catch-point migration candidate methodology
across three PR scopes. Gate 3 close §1 registered the
four-instance descriptive progression. PR 13 contributes a
**fifth descriptive instance**:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration (per evidence-inflation rejection) |

**Instance #5 is treated as a SINGLE corroboration** per
the evidence-inflation rejection discipline applied
recursively at the methodology-stack level (per spec §0 +
Step 3 body). The pre-draft fixture-cardinality grounding
catch + post-draft §11.8 cadence verification catch share
catch-shape ("grounded in framing's actual text before spec
commits"); splitting them into separate instances would
inflate evidence by treating sub-instances as independent
corroborations. The discipline operates on its own evidence.

**Catch-points migrate earlier monotonically across the
five instances.** Instances #4 + #5 are both at PR 13,
indicating two distinct catch-surfaces operate at PR 13's
framing/spec boundary. The candidate methodology continues
maturing operationally; Gate 4 close evaluates the
cumulative five-instance progression for prescriptive
promotion candidacy per Gate 4 framing §11.5.

**Why the recursion is archaeology-grade:** PR 13's
contribution is not merely "another instance" of catch-point
migration. The recursive application of evidence-inflation
rejection AT the methodology-stack level demonstrates the
discipline functioning as its own quality control.
Methodologies that govern only their objects (not their own
evidence) are vulnerable to inflation through sub-instance
splitting; PR 13's instance #5 single-corroboration treatment
is the first operational instance of self-governing
discipline in the candidate methodology's emerging
operational record.

PR 13 close registers the recursion as raw archaeology;
Gate 4 close evaluates whether the recursive-self-governance
property warrants prescriptive elevation alongside the catch-
point-migration progression itself.

### 1.9 Test count anchor — 218 forge env collected (exact spec target)

PR 13 close test count arithmetic (per spec §5.1
archaeology-grade):

```
217 baseline (PR 11 close §1.7 forge env collected)
+ 1 PR 13 ordering-divergence recomposition arc test (Step 2)
= 218 forge env collected at PR 13 close
```

**Step 3 verification re-confirmed (and re-verified at
close):**

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
218 tests collected in 0.05s
```

PR 13 ships **1 named test**; named == collected (no
parametrize per spec §5.3 inventory lock + §4.2.3 single-test
contract).

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`). Target at PR 13 close:
**211 baseline (PR 11 close §1.7) + 1 new = 212 forge-bridge
env collected.** Not re-verified at PR 13 close beyond
inheritance documentation — the 6-test gap is PR 7-scope,
not PR 13-scope. **Do not conflate the two env counts** per
PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close §1.7.

### 1.10 No cleanup-pressure-resistance class additions at PR 13

The 10-member cleanup-pressure-resistance class (Gate 3
close §1.6 final inventory; PR 11 close §1.8 unchanged
verification) preserves unchanged. PR 13 surfaced **no new
candidate class members** during implementation:

- Canonicalization pressure: did NOT surface.
- Set-equality collapse pressure: did NOT surface.
- Ordering-specific test helper pressure: did NOT surface.

The 10-member class inventory at PR 13 close is **unchanged
from Gate 3 close §1.6** (which itself was unchanged from
PR 10 close §1.7). The class is now demonstrably populatable
across **five reliability phases (PR 6 + PR 7 + PR 8 + PR 9
+ PR 10)** under genuinely independent conditions, with
TWO additional reliability phases (PR 11 + PR 13)
operationally corroborating the framing-level protections
through absence (per §1.6 above; cumulative three-instance
ABSENCE corroboration of the §5.3 candidate methodology
observation).

Gate 4 close §x reads the five-PR populating evidence + the
three-PR ABSENCE-corroboration evidence in the class-
promotion-to-SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+
evaluation per Gate 4 framing §6.

### 1.11 Both-skeletons-at-Step-1 lock operationally verified

Per PR 13 framing §9.12 + spec §6.1 lifecycle invariant:

| Step | Test module state | Fixture module state |
|---|---|---|
| 1 (skeleton) | Module docstring + `from __future__ import annotations` only | Module docstring + `from __future__ import annotations` only |
| 2 (architectural-center) | Imports + test body landed (single commit) | `FIXTURE` dict landed (single commit) |
| 3 (verification) | No changes (empty commit) | No changes (empty commit) |

**Both files traveled the establishment → activation
lifecycle symmetrically.** The asymmetric step structures
rejected at framing (file-asymmetric / 4-step / 2-step
compression per framing §9.12) did NOT surface during
implementation. Step 1 landed BOTH skeletons in ONE commit
(`376ed52`); Step 2 landed BOTH bodies in ONE commit
(`5d03ba1`); Step 3 was empty verification with archaeology
in body (`d7f2a6a`).

The both-skeletons-at-Step-1 lock is a NEW lifecycle invariant
introduced at PR 13 framing §9.12. PR 13 is the first PR
within Gate 4 to ship two new files at structurally-symmetric
skeleton state; the lifecycle invariant operated cleanly
without amendment. PR 14 + PR 15 inherit the lifecycle
invariant as PR-of-origin archaeology if they ship multi-file
PRs; the invariant's scope is "multi-file PRs at gate-level
reliability work," not PR-13-specific.

### 1.12 Imports-land-when-used (member #10) symmetric verification

Per spec §4.1.3 + §4.2.2 + framing §9.9, both PR 13 files
verify the imports-land-when-used discipline (cleanup-
pressure-resistance class member #10) symmetrically:

| File | Step 1 imports | Step 2 imports landed (when first used) | Step 3 imports |
|---|---|---|---|
| `fix_ordering_divergence.py` | `from __future__ import annotations` only | NO additional imports (FIXTURE dict only requires literal syntax; fixture-data-discipline member #9 prevents) | No changes |
| `test_pr13_ordering_divergence.py` | `from __future__ import annotations` only | `pathlib`, `pytest`, `compare_records`, `drive_seed_fixture`, `FIX_ORDERING_DIVERGENCE`, `_apply_pr9_patches`, `_read_records` (each landed when first used at test body) | No changes |

**The fixture file's single-import discipline is structural**
(fixture-data-discipline member #9 prevents any import
beyond `__future__`); the test file's seven-import landing
at Step 2 is member #10's standard operational form.

**No speculative-reserved imports** at either file. Member #10
operated cleanly across both new files. PR 13 contributes a
THIRD instance of member-#10 verification under integration-
work conditions (after PR 10 + PR 11).

### 1.13 Test-internal archaeology surfaces inheritance verified

Per framing §9.11 + spec §4.2.1 site 9: `_apply_pr9_patches`
and `_read_records` are imported from
`tests.corpus.test_pr9_fixture_integration` as **test-
internal archaeology surfaces, NOT public APIs.** PR 13
preserves the underscored-private status discipline PR 9 +
PR 11 established.

**Operational verification at PR 13:**

- The imports are placed in a dedicated section of the
  test module file with explicit "Test-internal archaeology
  surfaces (NOT public APIs)" comment marker (per spec
  §4.2.2).
- The module docstring's "Test infrastructure import
  discipline" section (spec §4.2.1 site 9) registers the
  underscored-private status explicitly with anti-promotion
  framing.
- No PR 13 surface promotes either helper to public API;
  no PR 13 surface modifies either helper's semantics.

Per PR 11 close §2.1 + spec §4.2.1 site 9: future Gate-X
work that imports either helper must register the same
test-internal-archaeology-surfaces framing. PR 13
operationally confirms the consumption pattern's stability
under independent PR-scope conditions.

---

## 2. What Gate 4 / future Gate-X work inherits from PR 13

PR 13 is the FIRST primary PR within Gate 4. Future Gate-X
work inherits PR 13's contributions; the gate-level
inheritance contract lives at Gate 4 close. This section
names PR 13-scoped inheritance only.

### 2.1 The ordering-divergence pure-isolation case as substrate

`tests/corpus/test_pr13_ordering_divergence.py` +
`tests/corpus/fixtures/fix_ordering_divergence.py` ship as
**substrate** for Gate 4 close's three-PR cumulative
Placement A + Placement B evaluation. The pure-isolation
property operates as laboratory-grade calibration: PR 13's
ordering-only fixture is one calibration point in the
three-point series PR 14 + PR 15 will complete.

**What Gate 4 / future work may reuse:**

- The fixture authoring pattern (single-vector divergence
  with pure-isolation property enumerated at every
  dimension) at PR 14 + PR 15 + future-gate framing pressure
  for analogous calibration exercises.
- The PR 11 consumption pattern (`_apply_pr9_patches` +
  `drive_seed_fixture` + `_read_records` + partition + four-
  key assertions) inherited unchanged at PR 13 and at
  future analogous PR scopes.
- The 9-surface PR-13-LOCAL travel inventory (§1.4) as
  precedent for PR-N-LOCAL discipline placement at PR-scope
  reliability work.

**What Gate 4 / future work must NOT do:**

- Promote PR-13-LOCAL beyond PR 13 (scope-local discipline;
  does not regenerate).
- Modify the fixture's pure-isolation property (would erase
  the laboratory-grade calibration substrate).
- Promote the test-body's nine-step traversal annotation
  comment style to a stricter prescriptive template (the
  annotation is PR-13-specific archaeology, not a Gate 4
  binding).

### 2.2 PR-13-LOCAL pure-isolation discipline as PR-of-origin archaeology

PR-13-LOCAL is scope-local. It does NOT regenerate beyond
PR 13. But the **discipline observation** — that single-
vector fixture pressure is operationally valuable as
laboratory-grade calibration substrate for cumulative
gate-arc evaluation — registers as PR-of-origin archaeology
at Gate 4 close + future-gate framing.

If PR 14 + PR 15 author analogous single-vector fixtures
(cardinality-only divergence at PR 14; partial-set-only or
duplicate-handling-only divergence at PR 15), the PR-N-LOCAL
discipline statement for each PR may **reference PR-13-LOCAL
as PR-of-origin** for the pure-isolation pattern while
authoring its own scope-local discipline.

The three-PR calibration series is the substrate Gate 4
close evaluates for Placement A operational corroboration;
PR 13's contribution is the first calibration point.

### 2.3 The architectural sufficiency signal at PR 13 — four-PR escalation

PR 13's 0-prod-mod outcome extends the three-PR Gate 3
escalation (PR 9 + PR 10 + PR 11) to a four-PR pattern
(PR 9 + PR 10 + PR 11 + PR 13). The methodology-contribution
template PR 11 close §2.3 introduced operates unchanged at
PR 13:

1. Framing names architectural sufficiency signal as goal
   (NOT just "clean diff hygiene") — Gate 4 framing §2.4
   + PR 13 framing §5.3.
2. Spec encodes the signal as a regression contract — spec
   §1 contract #10 + §6.2 Step 2 verification.
3. Implementation respects the signal at each commit
   (verified at each Step verification) — Steps 1–3 all
   verified.
4. Close artifact documents the signal as architectural
   archaeology, not just metric pass/fail — this §1.3
   + §6.5.

The four-PR escalation registers as cumulative archaeology
toward Gate 4 close's gate-level architectural-sufficiency-
signal evaluation per Gate 4 framing §6 + spec §6.4 +
PR 11 close §2.3.

Gate 4 close evaluates whether the signal warrants
prescriptive promotion alongside the cleanup-pressure-
resistance class + §5.3 candidate methodology observation +
catch-point migration candidate methodology — three
candidate-methodology promotion candidacies cumulative at
Gate 4 close per framing §6 + Gate 3 close §3.

### 2.4 Both-skeletons-at-Step-1 lifecycle invariant as PR-of-origin

PR 13 framing §9.12 introduced the both-skeletons-at-Step-1
lifecycle invariant for multi-file PRs at gate-level
reliability work. PR 13 is the first PR within Gate 4 to
operate the invariant; §1.11 above documents the operational
verification.

If PR 14 or PR 15 ships multi-file PRs, the lifecycle
invariant inherits at framing level as PR-of-origin
archaeology per §9.12 + this §2.4. Single-file PRs (like
PR 11's `test_pr11_recomposition_arc.py`) are out of scope
for the invariant — the invariant is "multi-file lifecycle
symmetry," not "all multi-file PRs use this exact step
count."

---

## 3. What Gate 4 / future work changes (deferred to Gate 4 close)

PR 13 close defers gate-level inheritance contract to Gate 4
close (same-commit-pairing with the final primary PR's close
per §7 below). This section names PR 13-scoped permanence
only.

### 3.1 Permanent PR 13 archaeology

Regardless of Gate 4's specific deliverables at PR 14 + PR
15, the following PR 13 outcomes are **permanent archaeology**:

- **The single PR 13 ordering-divergence recomposition arc
  test** ships as stable archaeology. Any modification
  requires framing-level review.
- **The PR 13 fixture's pure-isolation property** at every
  enumerated dimension (cardinality / partial-set / semantic-
  normalization / duplicate-handling) ships as stable
  archaeology. The fixture is laboratory-grade calibration
  substrate; multi-vector pressure modifications would erase
  the calibration discipline.
- **The 0-prod-mod outcome at PR 13** is recorded as
  validation evidence for the four-PR architectural-
  sufficiency escalation.
- **The 9 cumulative PR-13-LOCAL travel surfaces** (§1.4)
  are the verbatim-travel evidence base Gate 4 close reads.
- **The 8 cumulative §2.4 architectural commitment travel
  surfaces at PR 13** (§1.5) are the gate-shaped-governance
  evidence base.
- **The 3-form-ABSENCE Placement A contribution** (§1.6) is
  recorded; Gate 4 close performs gate-level Placement A
  cumulative evaluation across PR 13 + PR 14 + PR 15.
- **The Placement B precondition 1 + 2 manifestation at
  PR 13** (§1.7) is recorded; Gate 4 close evaluates
  precondition 3 cumulative manifestation.
- **The catch-point migration instance #5 single-
  corroboration interpretation** (§1.8) is recorded; Gate 4
  close evaluates the recursive-self-governance property
  for prescriptive promotion candidacy.
- **The third-instance ABSENCE outcome for the §5.3
  candidate methodology observation** (§1.6) is recorded;
  Gate 4 close performs three-instance promotion
  evaluation.
- **The 10-member cleanup-pressure-resistance class final
  inventory** is unchanged at PR 13 close (no PR 13
  additions; §1.10).
- **The both-skeletons-at-Step-1 lifecycle invariant** is
  operationally verified at PR 13 (§1.11); PR-of-origin
  archaeology for future multi-file PRs.
- **`forge_bridge.__all__` stays at 19 symbols.**

---

## 4. Step-by-step archaeology — 4-commit PR 13 chain

PR 13's implementation arc is 4 commits, beginning at spec
commit `2e05149` (2026-05-12) and closing at this commit
(separate close commit; standalone, NOT same-commit with
Gate 4 close per §7 below). The chain is shorter than PR 9's
10-commit + PR 10's 7-commit arcs because PR 13 had **zero
spec amendments + zero Step N.5 surgical commits + zero
implementation-time amendments** (matching PR 11's clean
arc exactly).

| # | Commit | Type | Step | Lines | Cumulative |
|---|---|---|---|---|---|
| 1 | `2e05149` | Spec | (pre-step) | +1988 | 1988 |
| 2 | `376ed52` | Step 1 — both skeletons bundled | Step 1 | +237 | 2225 |
| 3 | `5d03ba1` | Step 2 — architectural-center (test body + FIXTURE dict bundled) | Step 2 | +136 | 2361 |
| 4 | `d7f2a6a` | Step 3 — final verification (empty) | Step 3 | 0 | 2361 |

(Close commit ships as a distinct subsequent commit; this
artifact only. PR 13 close is the 5th commit in the PR 13
chain when counting the close.)

**Step archaeology — methodology contributions per commit:**

- **Spec** (`2e05149`) — File-level precision derived from
  framing's binding decisions (PR-13-LOCAL pure-isolation
  + one-fixture-one-test + three predicted cleanup-pressure
  forms + both-skeletons-at-Step-1 lock + 17 active carriers
  cited by reference). Spec-drafting-time fixture-cardinality
  grounding catch (catch-point migration instance #5; single
  corroboration per spec §0). 1988 lines. **Zero
  amendments** at spec drafting.
- **Step 1** (`376ed52`) — Both skeletons bundled. Module
  docstrings only at both files (per spec §4.1.1 + §4.2.1);
  `from __future__ import annotations` ONLY at each file
  (member 10 discipline). No test bodies, no FIXTURE dict,
  no helpers, no module-level constants. 237 lines split
  across the two new files. The both-skeletons-at-Step-1
  lock operated cleanly.
- **Step 2** (`5d03ba1`) — Architectural-center commit
  (test body + FIXTURE dict bundled). Imports landed per
  member 10 (imports-land-when-used): pathlib, pytest,
  compare_records, drive_seed_fixture, FIX_ORDERING_DIVERGENCE,
  two PR 9 test-internal archaeology surface imports. One
  test function with full body + explicit nine-step traversal
  annotation comments + four-key assertion contract. FIXTURE
  dict at fix_ordering_divergence.py per spec §4.1.2. Full
  three-round review applied per Gate 2 framing §5.7
  integration-work elevation. 136 lines added across the
  two files.
- **Step 3** (`d7f2a6a`) — Final verification. Empty commit;
  10-item verification checklist + Placement A 3-form-
  ABSENCE recording + Placement B preconditions 1+2 manifest
  + catch-point migration instance #5 recorded + cleanup-
  pressure-resistance class additions: none + spec
  amendments at incarnation: none + PR 13 commit chain
  summary in commit body. No new code.

**Step N.5 surgical cadence: NOT triggered at PR 13.** Per
PR 9's twice-corroborated pattern + PR 10's + PR 11's zero
corroborations: PR 13 also added zero corroborations. The
3-times-corroborated promotion status from Gate 2 close §5
preserves intact (PR 8 Step 4.5 + PR 9 Step 2.5 + PR 9
Step 5.5); PR 10 + PR 11 + PR 13 each added no
corroborations.

The pattern's availability is preserved at framing §3.5 +
spec §6.5 + this close §4; absent corroboration is not
falsification.

---

## 5. Methodology observations at PR 13 scope

PR 13's methodology contributions are largely **deferred to
Gate 4 close** for cross-PR synthesis. This section names
PR 13-scoped observations only; the gate-level synthesis
(three-PR Placement A cumulative evaluation + Placement B
precondition 3 evaluation + catch-point migration prescriptive
promotion evaluation + cleanup-pressure-resistance class
promotion evaluation) lives at Gate 4 close.

### 5.1 Spec-drafting-time catch-point with recursive-self-governance as PR 13's specific archaeology

PR 13's specific methodology archaeology is the **catch-point
migration instance #5 single-corroboration** outcome (per
§1.2 + §1.8). Two sub-observations:

1. **Catch-point migration earlier still** — from PR 11
   framing-spec drafting time (instance #3) and PR 13
   framing-convergence-pass pre-commit (instance #4) to
   PR 13 spec-drafting-time pre-spec-lock (instance #5).
   The catch-point migrates earlier within PR 13's own
   framing → spec drafting arc.

2. **Recursive-self-governance through evidence-inflation
   rejection** — the pre-draft + post-draft catches at PR 13
   spec drafting were treated as a SINGLE corroboration
   per the evidence-inflation rejection discipline that
   PR 13 framing §4.4 encodes. The methodology operates on
   its own evidence, demonstrating self-governing quality
   control.

The progression is **mechanically observed** (catch-point
migrates earlier across PRs; recursive-self-governance
emerges at PR 13). PR 13 close registers the raw progression;
Gate 4 close §x performs methodology-promotion evaluation.

**Reasonable archaeology framings (Gate 4 close evaluates):**

- *"Grounding discipline maturation pattern (five-instance
  cumulative)"* — names the progression mechanically
  without claiming generalized methodology (would require
  further-gate corroboration).
- *"`feedback_ground_specs_in_actual_files` operational
  maturation with recursive-self-governance"* — frames as
  instance of the underlying memory discipline with the
  recursive-self-governance property added at PR 13.
- *"Framing/spec-drafting-time grounding with evidence-
  inflation rejection at the methodology-stack level"* —
  names the discipline endpoint mechanically + the recursive
  property.

PR 13 close does NOT canonicalize naming; Gate 4 close §x
makes the framing-vs-naming decision at gate level (cumulative
across PR 13 + PR 14 + PR 15 catch-point instances).

### 5.2 Pointer to Gate 4 close for cross-PR synthesis

Gate 4 close (future, same-commit-paired with final primary
PR per §7 below) owns:

- Complete catch-point migration progression evaluation
  across PR 13 + PR 14 + PR 15 (PR 13 contributes instances
  #4 + #5; PR 14 + PR 15 may contribute additional
  instances).
- Cumulative architectural-sufficiency four-PR escalation
  (PR 9 + PR 10 + PR 11 + PR 13) plus PR 14 + PR 15
  evaluation.
- Cleanup-pressure-resistance class promotion evaluation
  reading five-PR populating evidence (PR 6 + PR 7 + PR 8
  + PR 9 + PR 10) + three-PR ABSENCE-corroboration evidence
  (PR 11 + PR 13 + (PR 14 / PR 15)).
- §5.3 candidate methodology observation gate-level
  promotion evaluation (three-instance ABSENCE evidence per
  asymmetric weighting; PR 14 + PR 15 may add further
  instances).
- Three-PR Placement A operational corroboration evaluation
  (PR 13 contributes 3-form-ABSENCE; PR 14 + PR 15
  contribute their own predicted-form outcomes per their
  framings).
- Placement B precondition 3 cumulative manifestation
  evaluation.
- Catch-point migration candidate methodology prescriptive
  promotion candidacy (recursive-self-governance property
  added at PR 13 instance #5).
- Conditional PR 12 disposition (deferred per Gate 4
  framing §5.10).
- Gate-level inheritance contract toward Gate 5.

Future phase architects read **Gate 4 close**, not PR 13
close, for the cross-PR methodology synthesis at Gate 4
scope.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 3 item 2)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
218 tests collected in 0.05s
```

Forge env collected: **218** ✓ (anchor matches spec §5.1
arithmetic: 217 baseline + 1 PR 13 new = 218; **exact
target**).

Full corpus suite execution: `218/218 passed` (verified at
Step 3).

Forge-bridge env not re-verified at PR 13 close; 6-test gap
inherited from PR 7 per `project_v1_4_x_harness_debt.md`.

### 6.2 PR 13 suite regression (Step 3 item 1)

```
$ python -m pytest tests/corpus/test_pr13_ordering_divergence.py
========================= 1 passed, 1 warning in 0.07s =========================
```

PR 13 suite: **1/1** ✓.

### 6.3 Public API anchor (Step 3 item 8)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

`forge_bridge.__all__` count at PR 13 close: **19** ✓.

`compare_records`, `DivergenceReport`, `ComparatorInputError`
remain corpus-internal per PR 10 spec §5.7 + PR 11 framing
§5.7 + PR 13 framing §3.4. PR 8's
`test_pr8_helpers_remain_corpus_internal` continues to
enforce mechanically.

### 6.4 Four-walker Layer 2 partition (Step 3 item 5)

All four Layer 2 walkers operational at PR 13 close:

- PR 4 walker (`test_pr4_participation_creep.py`) —
  production-import-topology — 1/1 passing.
- PR 8 walker (`test_pr8_seed_surface.py`) — orchestration-
  participation (5-symbol bounded toolbox) — 5/5 passing.
- PR 9 walker (`test_pr9_fixture_discipline.py`) —
  declarative-fixture-data (single-symbol-gate) — 2/2 passing.
- PR 10 walker (`test_pr10_comparator_discipline.py`) —
  read-only-interpretive-authority (zero-symbol-gate) — 2/2
  passing.

Combined: **30/30 passing.** Parallel-not-extension boundary
preserved. Shared AST mechanics do not imply shared ontology.
PR 13's two new files are target-disjoint from all four
walkers' input sets.

### 6.5 Architectural sufficiency signal (Step 3 item 10)

```
$ git diff --stat 8f429b2..HEAD -- forge_bridge/
(empty)
```

**Zero production source modifications across all 4 PR 13
commits** ✓ (spec + 3 implementation steps).

§2.4 Gate 4 architectural commitment travel verification at
this surface:

> Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.

The signal travels verbatim at this §6.5 per spec §0 + §1 +
§2 + Step 1, 2, 3 commit bodies + this close §1.5 + §6.5 =
8 cumulative travel surfaces at PR 13 close. Travel
deliberately stops short of fixture/test docstrings (carrier
/ gate-shaped governance asymmetry per §1.5).

Four-PR continuity (PR 9 + PR 10 + PR 11 + PR 13): the
divergence-shape robustness exercise demonstrates the
decomposition strategy operationally + reads the validated
comparator + recomposition arc under ordering-divergence
pressure without any production surface change.

### 6.6 Layer 3 lint regression (Step 3 item 4)

```
$ python -m pytest tests/corpus/test_pr6_visual_asymmetry.py
17 passed in 0.18s
```

PR 6 Layer 3 lint: **17/17** ✓ unchanged across PR 13.

Zero new `emit_divergence_capture` call sites at PR 13; lint's
discovery walk input set unchanged.

### 6.7 PR 11 recomposition arc regression (Step 3 item 7)

```
$ python -m pytest tests/corpus/test_pr11_recomposition_arc.py
======================== 3 passed, 1 warning in 0.10s =========================
```

PR 11 recomposition arc: **3/3** ✓ unchanged. PR 13 inherits
the consumption pattern without modification; PR 11's three
tests pass unchanged after PR 13's addition.

### 6.8 Console tests regression

```
$ python -m pytest tests/console/ -k "chat_handler"
50 passed in 0.51s
```

Console chat-handler subset: **50/50** ✓ unchanged (matches
PR 11 close §6.7 anchor exactly).

Full `tests/console/` execution: 361 tests collected
unchanged (matches PR 11 close §6.7 exactly).

### 6.9 Verbatim travel verification (Step 3 item 9)

- PR-13-LOCAL at fix_ordering_divergence.py module docstring
  + test_pr13_ordering_divergence.py module docstring
  (verified at Step 1; preserved through Steps 2-3).
- PR-13-LOCAL verbatim at all 3 PR 13 step commit message
  bodies (Step 1 + Step 2 + Step 3).
- PR-13-LOCAL verbatim at PR 13 spec §0 + §1 + §2 +
  this close §1.4 = **9 cumulative travel surfaces**
  (per §1.4 table).
- §2.4 Gate 4 architectural commitment verbatim at PR 13
  spec §0 + §1 + §2 + all 3 PR 13 step commit message
  bodies + this close §1.5 + §6.5 = **8 cumulative travel
  surfaces**. Travel deliberately stops short of fixture/
  test docstrings (carrier / gate-shaped governance
  asymmetry per §1.5).
- 17 inherited carriers cited by reference to canonical
  sources at both PR 13 module docstrings per spec §4.1.1
  + §4.2.1 (citation-by-reference discipline per spec §0
  + framing §3.1).
- Traversal trace verbatim from framing §2.1 at PR 13 test
  module docstring.
- Test-internal-archaeology-surfaces framing at PR 13 test
  module docstring (PR 9 helper imports admitted as test-
  internal archaeology surfaces, NOT public APIs).

---

## 7. Standalone close — Gate 4 close pairs with the final primary PR

Per Gate 4 framing §11.8 + PR 13 framing §3.6 + spec §6.4 +
Gate 2 + Gate 3 close precedent:

**PR 13 close (this artifact) ships STANDALONE.** Gate 4
close (`A.5.3.2-GATE-4-CLOSE.md`) pairs at the same commit
with the FINAL primary PR's close (PR 15 close OR PR 12 close
if PR 12 materializes last). PR 13 is the FIRST of three
primary PRs sequenced within Gate 4; PR 13 close ships at
its own commit; PR 14 close will also ship STANDALONE; the
final primary PR's close pairs at same commit with Gate 4
close.

**Cross-artifact responsibility deferral (per Gate 4 framing
§11.8 + spec §6.4 inheritance):**

**PR 13 close owns (this artifact):**

- PR 13 implementation arc archaeology (4-commit chain at
  §4 + close commit at §7).
- Ordering-divergence pure-isolation case operational
  archaeology (§1.1).
- Architectural sufficiency signal validation at PR 13 scope
  (§1.3 + §6.5 — 0-prod-mod outcome).
- §1.6 third-instance ABSENCE outcome at PR 13 scope
  (Placement A contribution).
- §1.7 Placement B preconditions 1 + 2 manifestation at
  PR 13 scope (precondition 3 deferred to Gate 4 close).
- §1.8 catch-point migration instance #5 single-corroboration
  contribution at PR 13 scope.
- PR-13-LOCAL pure-isolation discipline archaeology (§1.4).
- §2.4 Gate 4 architectural commitment travel inventory at
  PR 13 scope (§1.5).
- Zero-incarnation-amendments archaeology at PR 13 scope
  (§1.2 + §5.1).
- Both-skeletons-at-Step-1 lifecycle invariant operational
  verification (§1.11).
- Imports-land-when-used (member #10) symmetric verification
  at both new files (§1.12).
- Test-internal archaeology surfaces inheritance verification
  (§1.13).

**Gate 4 close will own (future, same-commit with final
primary PR's close):**

- Gate-arc synthesis across PR 13 + PR 14 + PR 15.
- Cleanup-pressure-resistance class final inventory at Gate 4
  scope (10 members + any PR 13/14/15 additions; PR 13 added
  zero per §1.10).
- Three-PR Placement A operational corroboration evaluation
  (cumulative across PR 13 + PR 14 + PR 15).
- Placement B precondition 3 cumulative manifestation
  evaluation.
- §5.3 candidate methodology observation gate-level
  promotion evaluation (three-instance ABSENCE evidence at
  PR 13; PR 14 + PR 15 may add additional instances).
- 0-prod-mod-as-architectural-sufficiency-signal gate-level
  promotion evaluation (four-PR escalation through PR 13;
  PR 14 + PR 15 may extend the escalation further).
- Catch-point migration candidate methodology gate-level
  promotion evaluation (instances #4 + #5 at PR 13;
  PR 14 + PR 15 may add additional instances; recursive-self-
  governance property emerged at PR 13 instance #5).
- Conditional PR 12 disposition (deferred per Gate 4
  framing §5.10).
- Gate-level inheritance contract toward Gate 5.

Where overlap surfaces between PR 13 close and the
forthcoming Gate 4 close, this artifact defers.

---

## 8. Cross-references

- **`A.5.3.2-PR13-FRAMING.md`** (`8f429b2`) — binding pre-spec
  contract; §0 governing pair + carrier inventory; §2
  objective + traversal trace; §3 architectural inheritance;
  §3.1 17-carrier inheritance from Gate 4 framing; §3.6 both-
  bodies-at-Step-2 + Step 3 carriers-by-reference; §4
  architectural delta; §5.4 three predicted cleanup-pressure
  forms; §5.5 PR-13-LOCAL binding statement; §6.1 Placement
  A predicted-form-outcome contribution; §6.2 Placement B
  precondition manifestation contribution; §9.9 + §9.10 +
  §9.11 + §9.12 close-condition contributions.
- **`A.5.3.2-PR13-SPEC.md`** (`2e05149`) — implementation
  contract; §0 carrier travel by citation + travel discipline
  asymmetry table + spec-drafting-time grounding catch as
  fifth catch-point migration instance; §4.1 per-file
  derivation (fixture); §4.2 per-file derivation (test);
  §4.2.3 single-test contract + nine-step traversal
  annotation; §4.2.4 four-key assertion contract + three-
  cleanup-pressure-form suppression evidence; §5 test count
  anchors (217 → 218 forge env); §6 atomic step decomposition
  (3 steps + close, all bundled-bundled-empty); §7 phase-end
  conditions; §9 resume protocol.
- **`A.5.3.2-GATE-4-FRAMING.md`** (`fbf2285`) — gate-level
  inheritance contract PR 13 operated against; §2.4 Gate 4
  architectural commitment travels at PR 13 surfaces per
  §1.5 table; §5 binding decisions (including §5.10
  conditional PR 12 disposition deferred); §6 Placement A +
  Placement B substrate; §11.5 + §11.8 close-cadence
  inheritance contract; §11.8 standalone-vs-paired close
  convergence rule per §7 above.
- **`A.5.3.2-GATE-3-CLOSE.md`** (`ee2225b`) — durable Gate 3
  archival state PR 13 inherited; §1.6 carrier #16
  promotion + 17 active carriers (cited by reference at PR
  13 module docstrings); §1.7 10-member cleanup-pressure-
  resistance class final inventory (unchanged at PR 13 per
  §1.10); §3 item 10 PR-11-LOCAL discipline inherited at
  gate level.
- **`A.5.3.2-PR11-CLOSE.md`** (`ee2225b`) — durable PR 11
  archival state PR 13 inherited; §1.4 PR-11-LOCAL
  traverses-not-erases-seams (inherited at gate level via
  Gate 3 close §3 item 10); §1.6 second-instance ABSENCE
  outcome (PR 13 contributes third instance per §1.6
  above); §2.1 recomposition arc consumption pattern (PR 13
  inherits unchanged); §2.3 architectural sufficiency
  signal Gate-X validation criterion (PR 13 extends to
  four-PR escalation per §2.3).
- **`A.5.3.2-PR10-CLOSE.md`** (`cf2b7ee`) — durable PR 10
  archival state PR 13 inherited; PR 10 §4.2 binding
  behavioral commitment ("compare as persisted") exercised
  under ordering-divergence pressure at PR 13 (per §1.6
  + §6.5 evidence); §5.3 candidate methodology observation
  first-instance precedent (PR 13 contributes third
  instance per §1.6 above).
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — three-fixture
  corpus PR 13's fixture sits alongside; PR 9 integration
  test infrastructure PR 13 imports as test-internal
  archaeology surfaces (`_apply_pr9_patches` +
  `_read_records` per §1.13); fix_multi_match.py:105-140
  arbitration trace PR 13's fixture inherits at
  fix_ordering_divergence.py module docstring.
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — §2.1 Gate 4
  comparator's two foundational dependencies operationally
  exercised at the PR 13 test (fixture_id joinability +
  record_kind partitioning).
- **`forge_bridge/corpus/_compare.py::compare_records`** —
  PR 10 interpretive-read surface PR 13 consumes at the
  test's final step; `_compare.py:503` direct list-equality
  detects ordering-only divergence as `narrow_diverged=True`.
- **`forge_bridge/corpus/_seed.py::drive_seed_fixture`** —
  PR 8 orchestration entry point PR 13 invokes per fixture;
  signature `(*, fixture_id, prompt, expected_narrow)`
  matches `FIXTURE` dict keys exactly.
- **`forge_bridge/console/handlers.py::chat_handler`** —
  production arbitration surface PR 13 drives via the PR 9
  patched `_invoke_chat_handler_in_process`.
- **`tests/corpus/test_pr13_ordering_divergence.py`** (PR 13
  new, 224 lines) — single new test module; 1 recomposition
  arc test + module docstring.
- **`tests/corpus/fixtures/fix_ordering_divergence.py`** (PR
  13 new, 149 lines) — single new fixture module; FIXTURE
  dict + module docstring (with grounded arbitration trace
  inherited from `fix_multi_match.py:105-140`).
- **`tests/corpus/test_pr9_fixture_integration.py::_apply_pr9_patches`**
  — test-internal archaeology surface PR 13 imports
  (`tests/corpus/test_pr9_fixture_integration.py:360`).
- **`tests/corpus/test_pr9_fixture_integration.py::_read_records`**
  — test-internal archaeology surface PR 13 imports
  (`tests/corpus/test_pr9_fixture_integration.py:336`).
- **`tests/corpus/fixtures/fix_multi_match.py:105-140`** —
  PR 9 multi-match arbitration trace PR 13's fixture
  inherits at fix_ordering_divergence.py module docstring.
- **`tests/corpus/test_pr9_fixture_integration.py:208-213`**
  — `_PR9_REACHABLE_TOOLS` declared order PR 13's fixture
  arbitration trace grounds against.
- **PR 13 4-commit chain** (`2e05149` → `d7f2a6a`) per §4
  table.
- **Local memory updates this session arc:**
  - PR-13-implementation-closed cursor written pre-synthesis
    per `feedback_cursor_before_retrospective_synthesis`.
  - MEMORY.md index updated.
  - Pushed to origin/main at the implementation-arc
    archaeology boundary (parity restored before close-
    artifact drafting).
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; PR 13 contributes
  (Gate 4 close evaluates):
  - Three-instance ABSENCE corroboration of the §5.3
    candidate methodology observation (per asymmetric
    weighting).
  - Four-PR architectural-sufficiency-signal escalation.
  - Catch-point migration instance #5 with recursive-self-
    governance property at the methodology-stack level.
  - Both-skeletons-at-Step-1 lifecycle invariant as PR-of-
    origin archaeology for multi-file PRs.

---

End of PR 13 close. The implementation arc that began at
PR 13 framing (`8f429b2`) closes here. The 4-commit chain
ships the ordering-divergence pure-isolation case + the
single integration test + the PR-13-LOCAL pure-isolation
discipline + the architectural sufficiency signal validation
(0 production source modifications across the PR) + the
zero-incarnation-amendments archaeology (matching PR 11's
clean arc) + the third-instance ABSENCE outcome for the §5.3
candidate methodology observation (corroborating across three
independent PRs) + the catch-point migration instance #5
single-corroboration interpretation (recursive-self-governance
at the methodology-stack level) + the both-skeletons-at-Step-1
lifecycle invariant operational verification (PR-of-origin
for multi-file PRs).

PR 13 governs by inherited active carrier #17 (recomposition
discipline; enacted at use through the DivergenceReport's
per-surface partitioning preserved end-to-end under ordering-
divergence pressure) + the §2.4 Gate 4 architectural
commitment (divergence-shape robustness exercise as Gate 4's
deliberate continuation of empirically bounded topology
proof) + the PR-13-LOCAL binding statement (scope-local
discipline; pure-isolation property as laboratory-grade
methodology corroboration substrate).

The ordering-divergence vector is detectable end-to-end
through the validated PR 10 comparator + PR 11 recomposition
arc WITHOUT ANY production source change. The divergence-
shape robustness exercise's first calibration point is
operationally validated.

**Gate 4 advances. PR 14 inherits a validated comparator +
a corroborated recomposition demonstration + an
architecturally-sufficient decomposition strategy + the
first calibration point of the three-PR Placement A +
Placement B substrate series.**
