# A.5.3.2 PR 14 — Close (partial-set divergence pure-isolation case)

**Status:** Durable archival state. PR 14 is the SECOND of
three primary PRs sequenced within Gate 4 (PR 13 ordering-
divergence + PR 14 partial-set + PR 15; conditional PR 12
disposition deferred to Gate 4 close per Gate 4 framing §5.10).
The implementation arc that began at PR 14 framing commit
`30412a3` (2026-05-12) closes at this commit.

PR 14 ships **two new files** containing **exactly one named
test** that exercises a partial-set divergence pure-isolation
case at the chat-handler observation surface:

| File | Lines | Role |
|---|---|---|
| `tests/corpus/fixtures/fix_partial_narrow_divergence.py` | 208 | Seed fixture — `prompt "list"` + `expected_narrow [forge_list_projects, flame_list_libraries, forge_ping]` (authored-superset Direction A — observation's two members at positions 0+1 verbatim PLUS `forge_ping` at position 2 as partial-set extension element orthogonal to prompt tokens) |
| `tests/corpus/test_pr14_partial_narrow_divergence.py` | 252 | Single integration test (`test_recomposition_arc_partial_narrow_divergence`) driving the fixture through the full decomposition seam path under partial-set divergence pressure |

The implementation arc traveled with **ZERO production source
modifications**, **ZERO spec amendments at incarnation**,
**ZERO cleanup-pressure forms surfacing**, and **ZERO Step
N.5 surgical commits**. Three predicted cleanup-pressure
forms named pre-implementation (PR 14 framing §5.4 + spec
§4.2.4) all exhibited ABSENCE — operationally suppressed at
the assertion contract through PR-11-LOCAL discipline at gate
level + PR 10 §4.2 binding behavioral commitment + the spec-
level four-key assertion contract + three-key fixture schema
lock.

**This artifact ships STANDALONE** per Gate 4 framing §11.8 +
PR 14 framing §11 + spec §6.4 + PR 13 close §7 inheritance.
Gate 4 close (`A.5.3.2-GATE-4-CLOSE.md`) pairs at the same
commit with the FINAL primary PR's close (PR 15 close OR
PR 12 close if PR 12 materializes last per Gate 2 + Gate 3
close precedent). PR 14 is the SECOND of three primary PRs
sequenced within Gate 4; PR 14 close ships at its own commit.
The §7 section below documents the standalone-close discipline
+ the cross-artifact responsibility deferral toward Gate 4
close.

---

## 1. What PR 14 established

### 1.1 Partial-set divergence recomposition arc operational

PR 14 ships `tests/corpus/test_pr14_partial_narrow_divergence.py`
(252 lines) — a single new test module containing one
integration test that exercises the end-to-end recomposition
arc under partial-set-only divergence pressure per spec §4.2:

| Test | Fixture | Outcome | Divergence vector |
|---|---|---|---|
| `test_recomposition_arc_partial_narrow_divergence` | `fix-pr14-partial-narrow-divergence` (prompt `"list"`) | PR14 yields 2 candidates; PR21 cannot collapse; observed `narrower.decision = ["forge_list_projects", "flame_list_libraries"]` | Authored `expected_narrow = ["forge_list_projects", "flame_list_libraries", "forge_ping"]` (positions 0+1 shared with observation verbatim; position 2 extends with `forge_ping` as partial-set extension element); `narrow_diverged=True` per `_compare.py:503` direct list-equality (length asymmetry 2 vs 3 + element-membership asymmetry at position 2) |

The test traverses the full decomposition seam path
explicitly at the test body level (per spec §4.2.3 nine-step
traversal annotation; pattern inherited verbatim from PR 13
§4.2.3):

```
fixture (fix_partial_narrow_divergence.py)
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
assertions) is inherited unchanged. PR 14 adds the partial-
set-divergence-specific authored expectation (the superset
extension by one element at position 2) and the list-equality
assertions that read the four-key shape at full structural
fidelity.

**Pure-isolation property** (PR 14 framing §5.5 + spec §4.1.1):

| Dimension | PR 14 outcome |
|---|---|
| Same set membership at intersection | Positions 0+1 share `{forge_list_projects, flame_list_libraries}` at observation positions verbatim |
| Ordering at intersection | NO divergence (shared elements preserve at observation positions) |
| Cardinality asymmetry | IS the partial-set vector (expectation length 3 vs. observation length 2) — same architectural-pressure-surface phenomenon, not two separate confounds |
| Semantic-normalization | NO divergence (exact-match identifiers) |
| Duplicate-handling | NO divergence (distinct elements at both lists) |
| Multi-survivor cardinality | NO divergence (both lists multi-element; cardinality-class divergence is PR 15's substrate) |

PR 14 isolates the partial-set-divergence vector as the sole
pressure on the comparator's compare-as-persisted discipline.
This is the laboratory-grade methodology-corroboration value
PR 14 contributes to Placement A + Placement B substrate
(per Gate 4 framing §6); SECOND calibration point in the
three-point series PR 13 + PR 14 + PR 15.

### 1.2 ZERO incarnation amendments — implementation traveled clean

PR 14 shipped with **ZERO spec amendments at any incarnation
surface**:

- ZERO drafting-time amendments at spec drafting (one
  grounding-citation correction was caught pre-spec-lock per
  §1.8 below; NOT an amendment in the post-lock sense).
- ZERO grounding-time amendments at Step 1 implementation
  prep.
- ZERO implementation-time amendments during Steps 1–2.
- ZERO verification-time amendments at Step 3.
- ZERO Step N.5 surgical commits.

PR 14 matches PR 11's + PR 13's zero-incarnation-amendments
archaeology verbatim. The framing → spec → implementation arc
traveled clean without in-flight realignment at ANY
incarnation surface.

**The framing-convergence + spec-drafting passes registered
the grounding discipline operationally** at TWO catch-points
within PR 14's scope (per spec §0):

1. **Framing-convergence-pass pre-commit** (catch-shape
   continuation of instance #4) — four file-grounding catches
   at framing convergence per PR 14 framing convergence
   archaeology.
2. **Spec-drafting-time pre-spec-lock** (catch-shape
   continuation of instance #5) — one line-number-citation
   grounding catch caught BEFORE spec lock. Spec §4.1.2
   FIXTURE grounding table initially cited
   `fix_multi_match.py:127` and `:128` as source lines for
   the two observation list values; re-grounding showed both
   values appear on a single list-literal line at
   `fix_multi_match.py:126`. Citation corrected pre-commit.

**Both catches are treated as catch-shape continuations of
the existing five-instance descriptive progression, NOT new
methodology instances** per the recursive-self-governance
discipline that PR 13 close §1.8 + spec §0 established. The
distinguishing property of a candidate methodology instance
is "the catch migrates earlier in the lifecycle," not "every
individual catch becomes a separately counted corroboration."
PR 14's framing-convergence catches share catch-shape with
instance #4; PR 14's spec-drafting catch shares catch-shape
with instance #5. The progression remains five-instance
descriptive at PR 14 close.

**A third catch-shape continuation emerged at implementation
time:** Steps 1 + 2 + 3 implemented per spec §6.1 + §6.2 +
§6.3 bindings + §4.1 + §4.2 file-shape bindings WITHOUT
amendment. This is catch-shape continuation of instance #3
(ZERO-AMENDMENT clean propagation; PR 11 implementation-time
precedent per PR 11 close §1).

The methodology-stack-level recursion operating at PR 14
extends the discipline-on-its-own-evidence pattern PR 13
introduced. Gate 4 close §x evaluates instance #3 + #4 + #5's
combined cumulative contribution toward catch-point-migration
candidate methodology promotion candidacy.

### 1.3 Architectural sufficiency signal — 0 production source modifications

PR 14 ships **0 modifications to production source files**:

```
$ git diff --stat 30412a3..HEAD -- forge_bridge/
(empty)
```

Verified by inspection across all 4 PR 14 commits (spec + 3
implementation steps). The 0-prod-mod outcome is the
**architectural sufficiency signal** per Gate 4 framing §2.4
+ PR 14 framing §5.3 binding decision + spec §1 regression
contract #10.

**Five-PR architectural sufficiency escalation** (PR 13 ended
at four-PR; PR 14 makes it five-PR):

| PR | Production diff | Validation strength |
|---|---|---|
| PR 9 | 0 prod mods (test-surface-only fixture authoring) | Substrate surfaces sufficient for fixture authoring + integration tests against existing surfaces |
| PR 10 | Exactly 1 new file (`_compare.py`, 523 lines), 0 mods elsewhere | New read-side surface composable without modifying existing surfaces |
| PR 11 | 0 prod mods (test-surface-only end-to-end recomposition) | Full recomposition arc traversable without modifying ANY production surface — decomposition strategy operationally validated by end-to-end exercise |
| PR 13 | 0 prod mods (test-surface-only ordering-divergence pure-isolation exercise) | Ordering-divergence vector detectable end-to-end through validated PR 10 comparator + PR 11 recomposition arc WITHOUT ANY production source change — divergence-shape robustness operationally validated at first calibration point |
| **PR 14** | **0 prod mods (test-surface-only partial-set divergence pure-isolation exercise)** | **Partial-set divergence vector detectable end-to-end through validated PR 10 comparator + PR 11 recomposition arc + PR 13 calibration substrate WITHOUT ANY production source change — divergence-shape robustness operationally validated at SECOND calibration point** |

PR 14's 0-prod-mod outcome is the **second piece of evidence
toward Gate 4 close's three-PR cumulative architectural-
sufficiency evaluation** (cumulative across PR 13 + PR 14 +
PR 15; Gate 4 close performs the gate-level evaluation per
spec §6.4 + Gate 4 framing §6). The five-PR escalation across
Gate 3 + Gate 4 substrate (PR 9 + PR 10 + PR 11 + PR 13 +
PR 14) corroborates the architectural-sufficiency-signal
template introduced at PR 11 framing §5.2.

The signal travels at:

- All 3 PR 14 step commit message bodies under
  "Architectural sufficiency signal" sections.
- This close artifact §1.3 + §6.5.
- (Future) Gate 4 close — gate-level evaluation at same-
  commit pairing with the final primary PR's close.

### 1.4 PR-14-LOCAL pure-isolation discipline operational

PR-14-LOCAL binding statement (per PR 14 framing §5.5 + spec
§0, scope-local per PR-N-LOCAL non-regeneration rule):

> **PR 14 isolates partial-set divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 14 scope —
> combining partial-set with ordering, semantic-normalization,
> duplicate-handling, multi-survivor-cardinality, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 14 its
> laboratory-grade methodology corroboration value for
> Placement A + Placement B substrate.**

**Operational evidence at PR 14:**

- The fixture authors exactly ONE divergence vector
  (partial-set / cardinality-asymmetry-at-superset) and
  ZERO divergence vectors across the other five dimensions
  (ordering at intersection, semantic-normalization,
  duplicate-handling, multi-survivor cardinality, sequence
  elsewhere). Verified at
  `fix_partial_narrow_divergence.py:114-130` (pure-isolation
  property enumerated at every dimension).
- The test asserts list-equality at four DivergenceReport
  keys at full structural fidelity (NOT set-equality, NOT
  partial-match-aware, NOT narrow_diverged-only, NOT a
  single-call helper) per spec §4.2.3 + §4.2.4.
- No fixture extension toward multi-vector pressure was
  authored. No "partial-set+ordering" combined fixture; no
  "partial-set+duplicates" combined fixture; no "partial-
  set-with-semantic-normalization" variant. Each is
  intentionally unbound pending PR 15 + future-gate framing
  pressure.

**Operational travel of PR-14-LOCAL** (9 surfaces; parallel
to PR 13 close §1.4 9-surface inventory):

| # | Surface | Carrier-shape |
|---|---|---|
| 1 | `tests/corpus/fixtures/fix_partial_narrow_divergence.py` module docstring | Verbatim |
| 2 | `tests/corpus/test_pr14_partial_narrow_divergence.py` module docstring | Verbatim |
| 3 | Step 1 commit body | Verbatim |
| 4 | Step 2 commit body | Verbatim |
| 5 | Step 3 commit body | Verbatim |
| 6 | PR 14 spec §0 | Verbatim |
| 7 | PR 14 spec §1 | Verbatim |
| 8 | PR 14 spec §2 | Verbatim |
| 9 | This close artifact §1.4 | Verbatim (above) |

**PR-14-LOCAL does NOT regenerate beyond PR 14.** PR 15 +
future-gate framing passes do not inherit PR-14-LOCAL as
carrier. The pure-isolation pattern's PR-of-origin (per PR 13
close §2.2) is PR-13-LOCAL; PR-14-LOCAL is **parallel scope-
local discipline, not regeneration of PR-13-LOCAL**. The
scope-local discipline itself is PR-14-specific.

### 1.5 §2.4 Gate 4 architectural commitment travel inventory

§2.4 Gate 4 architectural commitment (verbatim, per Gate 4
framing §2.4 + spec §0):

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**Operational travel of §2.4 commitment at PR 14 scope**
(8 surfaces; deliberately NOT at fixture/test docstrings per
spec §0 + framing §3.6 — carrier / gate-shaped governance
asymmetry preserved; mirrors PR 13 close §1.5 8-surface
inventory):

| # | Surface | Carrier-shape |
|---|---|---|
| 1 | PR 14 spec §0 (above the line) | Verbatim |
| 2 | PR 14 spec §1 architectural commitment section | Verbatim |
| 3 | PR 14 spec §2 architectural commitment section | Verbatim |
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
category integrity Gate 4 framing established + PR 13 close
§1.5 codified.

The asymmetry is verified by inspection at both module
docstrings: PR-14-LOCAL appears verbatim at both; the §2.4
sentence appears at neither.

### 1.6 Placement A contribution — 3-form-ABSENCE evidence

Three predicted cleanup-pressure forms were named at PR 14
framing §5.4 + spec §4.2.4 pre-implementation. **All three
exhibited ABSENCE during PR 14 implementation:**

| Form | Outcome | Operational evidence at PR 14 |
|---|---|---|
| Partial-match-to-full-divergence collapse pressure (framing §5.4 form 1) | ABSENCE | Four-key structural assertion contract held at the landed test body (`test_pr14_partial_narrow_divergence.py:242-252`). No `narrow_diverged`-only shortcut surfaced; structural list values in assertions 2 + 3 preserve the partial-match shape at full fidelity (length 3 expectation + length 2 observation surfaces with shared elements at positions 0+1 verbatim). |
| `partial_match` field-addition pressure (framing §5.4 form 2) | ABSENCE | No fifth key checked at assertion; no `partial_match` reference anywhere in fixture, test, or comparator surface. PR 10 spec §4.1.6 reference implementation preserved unchanged. The structural shape preservation in assertions 2 + 3 IS the partial-match disclosure. |
| Fixture-shape extension pressure (framing §5.4 form 3) | ABSENCE | FIXTURE dict carries exactly three keys (`fixture_id`, `prompt`, `expected_narrow`) per the spec-layer schema lock; no fourth declared-intent field surfaced. The authored expectation list's three-element content carries the partial-set intent structurally. |

**PR 14 contributes 3-form-ABSENCE evidence toward Placement
A as the SECOND Gate 4 PR instance.** Gate 4 close reads
cumulative across PR 13 + PR 14 + PR 15 for the three-PR-
cumulative Placement A operational corroboration evaluation
per Gate 4 framing §6.1.

**Why the framing-time discipline operated at PR 14
specifically:** PR-14-LOCAL elevated the pure-isolation
property to named-discipline status (per §1.4 above). The
discipline operated as anchored governance at each Step 1 +
Step 2 implementation decision. The temptation to "make the
partial-set-divergence assertion cleaner" via any of the
three forms would have been a real pressure under different
framing — but the laboratory-grade-methodology-corroboration
goal made every form rejected at the design level (per spec
§4.2.4 + framing §5.4 + PR-11-LOCAL inherited at gate level).

This is the operational form of the §5.3 candidate methodology
observation (per PR 10 close §5.3 + PR 11 close §1.6 + PR 13
close §1.6): when framing-time prediction elevates a goal to
named-discipline status, the discipline shapes implementation
decisions without needing per-pressure rejection events.
**PR 14 contributes the FOURTH instance** to this candidate
methodology observation (after PR 10's first, PR 11's second,
PR 13's third); four independent instances now corroborate
the framing-time-pressure-prediction-through-absence pattern:

| Instance | PR | Outcome |
|---|---|---|
| 1 | PR 10 | ABSENCE (helper merger / persistence creep / walker abstraction) |
| 2 | PR 11 | ABSENCE (helper merger / premature surface normalization / fixture widening / recomposition smoothing) |
| 3 | PR 13 | ABSENCE (canonicalization / set-equality collapse / ordering-specific helper) |
| **4** | **PR 14** | **ABSENCE (partial-match-to-full-divergence collapse / `partial_match` field-addition / fixture-shape extension)** |

PR 14 close registers the fourth-instance outcome as raw
archaeology; Gate 4 close performs the gate-level promotion
evaluation against the four-instance cumulative evidence per
asymmetric weighting (PR 11 framing §6.4 + Gate 4 framing
§6.4 + PR 13 close §1.6).

### 1.7 Placement B precondition 1 + 2 manifestation

Gate 4 framing §6.2 named Placement B as
**methodology-stack-maturation-substrate** with three
preconditions toward operational manifestation. PR 14's
contribution to Placement B precondition manifestation:

| Precondition | Manifest at PR 14? | Evidence |
|---|---|---|
| 1 — Prior pressure prediction at framing time | YES | PR 14 framing §5.4 + spec §4.2.4 named three predicted cleanup-pressure forms pre-implementation; framing-time discipline operationally enforced per §1.6 above. |
| 2 — Named suppression mechanism per predicted form | YES | Each suppression mechanism named and grounded: four-key structural assertion contract at spec §4.2.4; comparator surface preservation at PR 10 spec §4.1.6 reference; three-key fixture schema lock at spec §4.1.2. All three grounded in PR 10 §4.2 binding behavioral commitment + PR-11-LOCAL discipline inherited at gate level + cleanup-pressure-resistance class member #4 (expectation record schema lock) + member #9 (fixture-surface-data-discipline). |
| 3 — Corroborated recurrence across multiple PR scopes | **Strengthens at PR 14 — cumulative across PR 13 + PR 14** | Precondition 3 requires multi-PR corroborated recurrence. PR 13 + PR 14 now constitute two independent same-direction instances at Gate 4 substrate. PR 15 may contribute a third instance; Gate 4 close evaluates final cumulative manifestation per Gate 4 framing §6.2. |

PR 14's contribution to Placement B is **operationally
substrate** — preconditions 1 + 2 manifest at PR 14's
framing → spec → implementation arc. Precondition 3's
cross-PR-recurrence evaluation strengthens at PR 14 (two-PR
manifestation across PR 13 + PR 14) but final-cumulative
evaluation deferred to Gate 4 close per framing §6.2 + spec
§6.4.

### 1.8 Catch-point migration — instance #5 catch-shape continuation

PR 10 close §5.3 + PR 11 close §1.6 + PR 11 close §5.1
established the catch-point migration candidate methodology
across three PR scopes. Gate 3 close §1 registered the
four-instance descriptive progression. PR 13 close §1.8
added the fifth instance + introduced the recursive-self-
governance discipline. **PR 14 contributes three catch-shape
continuations**, NOT new methodology instances:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration (fixture-cardinality) |
| 5 (continuation) | PR 14 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of #4 (four file-grounding catches) |
| 5 (continuation) | PR 14 spec | Spec-drafting-time pre-spec-lock | Catch-shape continuation of #5 (one line-number-citation grounding catch) |
| 3 (continuation) | PR 14 implementation | Implementation-time | Catch-shape continuation of #3 (ZERO-AMENDMENT clean propagation) |

**Three catch-shape continuations at PR 14 are treated as
continuations of existing instances** per the recursive-self-
governance discipline (PR 13 close §1.8 precedent
operationalized at PR 14 framing + maintained at PR 14 spec
+ maintained at PR 14 implementation):

1. **PR 14 framing-convergence** (catch-shape #4 continuation):
   four file-grounding catches caught pre-commit at framing
   convergence; same catch-point + same catch-shape as PR 13
   framing-convergence's six catches.
2. **PR 14 spec-drafting-time** (catch-shape #5 continuation):
   one line-number-citation grounding catch caught pre-spec-
   lock; same catch-point + same catch-shape as PR 13's
   fixture-cardinality grounding catch.
3. **PR 14 implementation-time** (catch-shape #3
   continuation): ZERO-AMENDMENT clean propagation; same
   catch-point + same catch-shape as PR 11's clean arc.

**The recursive-self-governance discipline operates at THREE
methodology-stack levels at PR 14**: at catch-shape #4
continuation (NOT promoting framing-convergence catches into
new instance counts); at catch-shape #5 continuation (NOT
promoting spec-drafting catch into instance #6); at catch-
shape #3 continuation (NOT promoting clean-arc outcome into
instance #6 either). The discipline operates symmetrically
across all three continuations.

**The progression remains five-instance descriptive at PR 14
close.** Per the recursive-self-governance discipline,
catch-shape continuations expand the corroboration depth of
existing instances without inflating the methodology's
instance count. PR 14's contribution is depth-corroboration
across three existing instances simultaneously, not breadth-
addition of new instances.

**Why the three-fold continuation is archaeology-grade:**
PR 14's contribution is not "yet another instance" of catch-
point migration. The recursive application of evidence-
inflation rejection AT three catch-shapes simultaneously
demonstrates the discipline functioning as its own quality
control across the methodology stack. The recursive-self-
governance property PR 13 introduced operates AT PR 14 across
multiple catch-shapes in a single PR scope — the discipline
is operational, not just descriptive.

PR 14 close registers the three-fold continuation as raw
archaeology; Gate 4 close evaluates whether the recursive-
self-governance property warrants prescriptive elevation
alongside the catch-point-migration progression itself
(building on PR 13 close §1.8's recursive-self-governance
introduction).

### 1.9 Test count anchor — 219 forge env collected (exact spec target)

PR 14 close test count arithmetic (per spec §5.1
archaeology-grade):

```
218 baseline (PR 13 close §1.9 forge env collected)
+ 1 PR 14 partial-set divergence recomposition arc test (Step 2)
= 219 forge env collected at PR 14 close
```

**Step 3 verification re-confirmed (and re-verified at
close):**

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
219 tests collected in 0.05s
```

PR 14 ships **1 named test**; named == collected (no
parametrize per spec §5.3 inventory lock + §4.2.3 single-test
contract).

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`). Target at PR 14 close:
**212 baseline (PR 13 close §1.9) + 1 new = 213 forge-bridge
env collected.** Not re-verified at PR 14 close beyond
inheritance documentation — the 6-test gap is PR 7-scope,
not PR 14-scope. **Do not conflate the two env counts** per
PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close §1.7 + PR 13
close §1.9.

### 1.10 No cleanup-pressure-resistance class additions at PR 14

The 10-member cleanup-pressure-resistance class (Gate 3
close §1.6 final inventory; PR 11 close §1.8 unchanged
verification; PR 13 close §1.10 unchanged verification)
preserves unchanged. PR 14 surfaced **no new candidate class
members** during implementation:

- Partial-match-to-full-divergence collapse pressure: did
  NOT surface.
- `partial_match` field-addition pressure: did NOT surface.
- Fixture-shape extension pressure: did NOT surface.

The 10-member class inventory at PR 14 close is **unchanged
from Gate 3 close §1.6** (which was unchanged at PR 11 close
+ PR 13 close). The class is now demonstrably populatable
across **five reliability phases (PR 6 + PR 7 + PR 8 + PR 9
+ PR 10)** under genuinely independent conditions, with
THREE additional reliability phases (PR 11 + PR 13 + PR 14)
operationally corroborating the framing-level protections
through absence (per §1.6 above; cumulative four-instance
ABSENCE corroboration of the §5.3 candidate methodology
observation).

Gate 4 close §x reads the five-PR populating evidence + the
four-PR ABSENCE-corroboration evidence in the class-
promotion-to-SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+
evaluation per Gate 4 framing §6.

### 1.11 Both-skeletons-at-Step-1 lock operationally verified

Per PR 14 framing §9.12 + spec §6.1 lifecycle invariant
(inherited from PR 13 close §2.4 as PR-of-origin):

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
(`57e4180`); Step 2 landed BOTH bodies in ONE commit
(`685b91d`); Step 3 was empty verification with archaeology
in body (`9a09c86`).

**PR 14 is the SECOND PR within Gate 4 to operate the
invariant** (PR 13 was PR-of-origin per PR 13 close §1.11 +
§2.4). The lifecycle invariant operated cleanly without
amendment at PR 14, confirming the PR-of-origin pattern's
stability under independent PR-scope conditions. PR 15 + 
future-gate multi-file PRs inherit the lifecycle invariant
via PR 13 close §2.4 as PR-of-origin archaeology + this §1.11
as second operational corroboration.

### 1.12 Imports-land-when-used (member #10) symmetric verification

Per spec §4.1.3 + §4.2.2 + framing §9.9, both PR 14 files
verify the imports-land-when-used discipline (cleanup-
pressure-resistance class member #10) symmetrically:

| File | Step 1 imports | Step 2 imports landed (when first used) | Step 3 imports |
|---|---|---|---|
| `fix_partial_narrow_divergence.py` | `from __future__ import annotations` only | NO additional imports (FIXTURE dict only requires literal syntax; fixture-data-discipline member #9 prevents) | No changes |
| `test_pr14_partial_narrow_divergence.py` | `from __future__ import annotations` only | `pathlib`, `pytest`, `compare_records`, `drive_seed_fixture`, `FIX_PARTIAL_NARROW_DIVERGENCE`, `_apply_pr9_patches`, `_read_records` (each landed when first used at test body) | No changes |

**The fixture file's single-import discipline is structural**
(fixture-data-discipline member #9 prevents any import
beyond `__future__`); the test file's seven-import landing
at Step 2 is member #10's standard operational form.

**No speculative-reserved imports** at either file. Member #10
operated cleanly across both new files. PR 14 contributes a
FOURTH instance of member-#10 verification under integration-
work conditions (after PR 10 + PR 11 + PR 13).

### 1.13 Test-internal archaeology surfaces inheritance verified

Per framing §9.11 + spec §4.2.1 site 9: `_apply_pr9_patches`
and `_read_records` are imported from
`tests.corpus.test_pr9_fixture_integration` as **test-
internal archaeology surfaces, NOT public APIs.** PR 14
preserves the underscored-private status discipline PR 9 +
PR 11 + PR 13 established.

**Operational verification at PR 14:**

- The imports are placed in a dedicated section of the
  test module file with explicit "Test-internal archaeology
  surfaces (NOT public APIs)" comment marker (per spec
  §4.2.2;
  `test_pr14_partial_narrow_divergence.py:114-120`).
- The module docstring's "Test infrastructure import
  discipline" section (spec §4.2.1 site 9) registers the
  underscored-private status explicitly with anti-promotion
  framing.
- No PR 14 surface promotes either helper to public API;
  no PR 14 surface modifies either helper's semantics.

Per PR 11 close §2.1 + PR 13 close §1.13 + spec §4.2.1 site
9: future Gate-X work that imports either helper must
register the same test-internal-archaeology-surfaces framing.
PR 14 operationally confirms the consumption pattern's
stability under independent PR-scope conditions (second
corroboration after PR 13).

---

## 2. What Gate 4 / future Gate-X work inherits from PR 14

PR 14 is the SECOND primary PR within Gate 4. Future Gate-X
work inherits PR 14's contributions; the gate-level
inheritance contract lives at Gate 4 close. This section
names PR 14-scoped inheritance only.

### 2.1 The partial-set divergence pure-isolation case as substrate

`tests/corpus/test_pr14_partial_narrow_divergence.py` +
`tests/corpus/fixtures/fix_partial_narrow_divergence.py` ship
as **substrate** for Gate 4 close's three-PR cumulative
Placement A + Placement B evaluation. The pure-isolation
property operates as laboratory-grade calibration: PR 14's
partial-set-only fixture is the **SECOND calibration point**
in the three-point series PR 13 + PR 14 + PR 15 will complete.

**What Gate 4 / future work may reuse:**

- The fixture authoring pattern (single-vector divergence
  with pure-isolation property enumerated at every
  dimension) at PR 15 + future-gate framing pressure for
  analogous calibration exercises.
- The PR 11 consumption pattern (`_apply_pr9_patches` +
  `drive_seed_fixture` + `_read_records` + partition + four-
  key assertions) inherited unchanged at PR 13 + PR 14 and
  at future analogous PR scopes.
- The 9-surface PR-14-LOCAL travel inventory (§1.4) as
  precedent for PR-N-LOCAL discipline placement at PR-scope
  reliability work.
- The Direction A authored-superset rationale (per spec §1
  + §4.1 + framing §5.10) — three-reason argumentation
  pattern (single-variable discipline + semantic legibility
  + substrate reuse) for affirmative architectural decisions
  at framing-level direction-symmetric pressure.

**What Gate 4 / future work must NOT do:**

- Promote PR-14-LOCAL beyond PR 14 (scope-local discipline;
  does not regenerate).
- Modify the fixture's pure-isolation property (would erase
  the laboratory-grade calibration substrate).
- Modify the FIXTURE dict's three-key schema (would erase
  the fixture-shape extension pressure suppression evidence).
- Modify the test body's four-key assertion contract (would
  erase the partial-match-to-full-divergence collapse
  pressure suppression evidence).
- Promote the test-body's nine-step traversal annotation
  comment style to a stricter prescriptive template (the
  annotation is PR-13-PR-of-origin archaeology + PR 14
  inherited pattern, not a Gate 4 binding).

### 2.2 PR-14-LOCAL pure-isolation discipline as parallel scope-local archaeology

PR-14-LOCAL is scope-local. It does NOT regenerate beyond
PR 14. PR-13-LOCAL is the PR-of-origin for the pure-isolation
pattern (per PR 13 close §2.2); PR-14-LOCAL is **parallel
scope-local discipline, not regeneration of PR-13-LOCAL**.

The **discipline observation** — that single-vector fixture
pressure is operationally valuable as laboratory-grade
calibration substrate for cumulative gate-arc evaluation —
registers as a TWO-PR-CORROBORATED archaeological pattern
at Gate 4 close + future-gate framing (with PR 13 as PR-of-
origin and PR 14 as second corroboration).

If PR 15 authors an analogous single-vector fixture (multi-
survivor-cardinality-only divergence at PR 15 per Gate 4
framing §5), the PR-N-LOCAL discipline statement for PR 15
may **reference PR-13-LOCAL as PR-of-origin + PR-14-LOCAL as
second corroboration** for the pure-isolation pattern while
authoring its own scope-local discipline.

The three-PR calibration series is the substrate Gate 4
close evaluates for Placement A operational corroboration;
PR 14's contribution is the **second calibration point**.

### 2.3 The architectural sufficiency signal at PR 14 — five-PR escalation

PR 14's 0-prod-mod outcome extends the four-PR escalation
(PR 9 + PR 10 + PR 11 + PR 13) to a five-PR pattern
(PR 9 + PR 10 + PR 11 + PR 13 + PR 14). The methodology-
contribution template PR 11 close §2.3 introduced + PR 13
close §2.3 corroborated operates unchanged at PR 14:

1. Framing names architectural sufficiency signal as goal
   (NOT just "clean diff hygiene") — Gate 4 framing §2.4
   + PR 14 framing §5.3.
2. Spec encodes the signal as a regression contract — spec
   §1 contract #10 + §6.2 Step 2 verification.
3. Implementation respects the signal at each commit
   (verified at each Step verification) — Steps 1–3 all
   verified.
4. Close artifact documents the signal as architectural
   archaeology, not just metric pass/fail — this §1.3
   + §6.5.

The five-PR escalation registers as cumulative archaeology
toward Gate 4 close's gate-level architectural-sufficiency-
signal evaluation per Gate 4 framing §6 + spec §6.4 +
PR 11 close §2.3 + PR 13 close §2.3.

Gate 4 close evaluates whether the signal warrants
prescriptive promotion alongside the cleanup-pressure-
resistance class + §5.3 candidate methodology observation +
catch-point migration candidate methodology — three
candidate-methodology promotion candidacies cumulative at
Gate 4 close per framing §6 + Gate 3 close §3 + PR 13 close
§2.3.

### 2.4 Both-skeletons-at-Step-1 lifecycle invariant — second operational corroboration

PR 13 framing §9.12 introduced the both-skeletons-at-Step-1
lifecycle invariant for multi-file PRs at gate-level
reliability work; PR 13 was PR-of-origin per PR 13 close
§2.4. PR 14 is the **second PR within Gate 4 to operate the
invariant** (§1.11 above documents the operational
verification).

The lifecycle invariant inherits at framing level via PR 13
close §2.4 as PR-of-origin archaeology + this §2.4 as second
operational corroboration. If PR 15 ships a multi-file PR,
the lifecycle invariant inherits as TWO-PR-CORROBORATED
archaeological pattern (PR 13 as PR-of-origin + PR 14 as
second corroboration). Single-file PRs (like PR 11's
`test_pr11_recomposition_arc.py`) remain out of scope — the
invariant is "multi-file lifecycle symmetry," not "all
multi-file PRs use this exact step count."

---

## 3. What Gate 4 / future work changes (deferred to Gate 4 close)

PR 14 close defers gate-level inheritance contract to Gate 4
close (same-commit-pairing with the final primary PR's close
per §7 below). This section names PR 14-scoped permanence
only.

### 3.1 Permanent PR 14 archaeology

Regardless of Gate 4's specific deliverables at PR 15, the
following PR 14 outcomes are **permanent archaeology**:

- **The single PR 14 partial-set divergence recomposition arc
  test** ships as stable archaeology. Any modification
  requires framing-level review.
- **The PR 14 fixture's pure-isolation property** at every
  enumerated dimension (ordering at intersection / semantic-
  normalization / duplicate-handling / multi-survivor
  cardinality) ships as stable archaeology. The fixture is
  laboratory-grade calibration substrate; multi-vector
  pressure modifications would erase the calibration
  discipline.
- **The Direction A authored-superset rationale** at spec §1
  + §4.1 + §4.2.3 (three-reason argumentation: single-
  variable discipline + semantic legibility + substrate
  reuse) is permanent archaeology.
- **The 0-prod-mod outcome at PR 14** is recorded as
  validation evidence for the five-PR architectural-
  sufficiency escalation.
- **The 9 cumulative PR-14-LOCAL travel surfaces** (§1.4)
  are the verbatim-travel evidence base Gate 4 close reads.
- **The 8 cumulative §2.4 architectural commitment travel
  surfaces at PR 14** (§1.5) are the gate-shaped-governance
  evidence base.
- **The 3-form-ABSENCE Placement A contribution** (§1.6) is
  recorded; Gate 4 close performs gate-level Placement A
  cumulative evaluation across PR 13 + PR 14 + PR 15.
- **The Placement B precondition 1 + 2 manifestation at
  PR 14** (§1.7) is recorded; Gate 4 close evaluates
  precondition 3 cumulative manifestation (PR 14 strengthens
  to two-PR manifestation).
- **The catch-point migration three-fold continuation
  interpretation** (§1.8) is recorded; Gate 4 close
  evaluates the recursive-self-governance property's
  multi-catch-shape operation for prescriptive promotion
  candidacy.
- **The fourth-instance ABSENCE outcome for the §5.3
  candidate methodology observation** (§1.6) is recorded;
  Gate 4 close performs four-instance promotion evaluation.
- **The 10-member cleanup-pressure-resistance class final
  inventory** is unchanged at PR 14 close (no PR 14
  additions; §1.10).
- **The both-skeletons-at-Step-1 lifecycle invariant** is
  operationally verified for the SECOND time at PR 14
  (§1.11); two-PR corroborated archaeological pattern
  (PR 13 PR-of-origin + PR 14 second corroboration).
- **PR-14-LOCAL as parallel scope-local discipline (not
  regeneration)** (§1.4 + §2.2) — parallel-not-regenerative
  pattern is permanent archaeology distinguishing PR-N-LOCAL
  discipline from PR-of-origin substrate.
- **`forge_bridge.__all__` stays at 19 symbols.**

---

## 4. Step-by-step archaeology — 4-commit PR 14 chain

PR 14's implementation arc is 4 commits, beginning at spec
commit `23c358a` (2026-05-12) and closing at this commit
(separate close commit; standalone, NOT same-commit with
Gate 4 close per §7 below). The chain is shorter than PR 9's
10-commit + PR 10's 7-commit arcs because PR 14 had **zero
spec amendments + zero Step N.5 surgical commits + zero
implementation-time amendments** (matching PR 11's and
PR 13's clean arcs exactly).

| # | Commit | Type | Step | Lines | Cumulative |
|---|---|---|---|---|---|
| 1 | `23c358a` | Spec | (pre-step) | +2156 | 2156 |
| 2 | `57e4180` | Step 1 — both skeletons bundled | Step 1 | +298 | 2454 |
| 3 | `685b91d` | Step 2 — architectural-center (test body + FIXTURE dict bundled) | Step 2 | +161 | 2615 |
| 4 | `9a09c86` | Step 3 — final verification (empty) | Step 3 | 0 | 2615 |

(Close commit ships as a distinct subsequent commit; this
artifact only. PR 14 close is the 5th commit in the PR 14
chain when counting the close.)

**Step archaeology — methodology contributions per commit:**

- **Spec** (`23c358a`) — File-level precision derived from
  framing's binding decisions (PR-14-LOCAL pure-isolation +
  one-fixture-one-test + Direction A authored-superset +
  three predicted cleanup-pressure forms + both-skeletons-
  at-Step-1 lock + 17 active carriers cited by reference).
  Spec-drafting-time line-number-citation grounding catch
  (catch-shape continuation of instance #5; single line-
  number correction `fix_multi_match.py:127`→`:126` per
  spec §0). 2156 lines. **Zero amendments** at spec drafting.
- **Step 1** (`57e4180`) — Both skeletons bundled. Module
  docstrings only at both files (per spec §4.1.1 + §4.2.1);
  `from __future__ import annotations` ONLY at each file
  (member 10 discipline). No test bodies, no FIXTURE dict,
  no helpers, no module-level constants. 298 lines split
  across the two new files (fixture 198-line docstring +
  test 100-line docstring). The both-skeletons-at-Step-1
  lock operated cleanly (second operational corroboration
  after PR 13).
- **Step 2** (`685b91d`) — Architectural-center commit
  (test body + FIXTURE dict bundled). Imports landed per
  member 10 (imports-land-when-used): pathlib, pytest,
  compare_records, drive_seed_fixture,
  FIX_PARTIAL_NARROW_DIVERGENCE, two PR 9 test-internal
  archaeology surface imports. One test function with full
  body + explicit nine-step traversal annotation comments +
  four-key assertion contract. FIXTURE dict at
  `fix_partial_narrow_divergence.py` per spec §4.1.2 with
  Direction A authored-superset (`expected_narrow =
  [forge_list_projects, flame_list_libraries, forge_ping]`).
  Full three-round review applied per Gate 2 framing §5.7
  integration-work elevation. 161 lines added across the
  two files.
- **Step 3** (`9a09c86`) — Final verification. Empty commit;
  10-item verification checklist + Placement A 3-form-
  ABSENCE recording + Placement B preconditions 1+2 manifest
  + catch-point migration three-fold continuation recorded
  + cleanup-pressure-resistance class additions: none + spec
  amendments at incarnation: none + PR 14 commit chain
  summary in commit body. No new code.

**Step N.5 surgical cadence: NOT triggered at PR 14.** Per
PR 9's twice-corroborated pattern + PR 10's + PR 11's + 
PR 13's zero corroborations: PR 14 also added zero
corroborations. The 3-times-corroborated promotion status
from Gate 2 close §5 preserves intact (PR 8 Step 4.5 + PR 9
Step 2.5 + PR 9 Step 5.5); PR 10 + PR 11 + PR 13 + PR 14
each added no corroborations.

The pattern's availability is preserved at framing §3.5 +
spec §6.5 + this close §4; absent corroboration is not
falsification.

---

## 5. Methodology observations at PR 14 scope

PR 14's methodology contributions are largely **deferred to
Gate 4 close** for cross-PR synthesis. This section names
PR 14-scoped observations only; the gate-level synthesis
(three-PR Placement A cumulative evaluation + Placement B
precondition 3 evaluation + catch-point migration prescriptive
promotion evaluation + cleanup-pressure-resistance class
promotion evaluation) lives at Gate 4 close.

### 5.1 Three-fold catch-shape continuation with recursive-self-governance operating at three methodology-stack levels — PR 14's specific archaeology

PR 14's specific methodology archaeology is the **three-fold
catch-shape continuation** outcome (per §1.2 + §1.8). Three
sub-observations:

1. **Catch-shape continuation operates at three catch-points
   in a single PR scope** — at framing-convergence-pass
   pre-commit (continuation of instance #4); at spec-
   drafting-time pre-spec-lock (continuation of instance
   #5); at implementation-time (continuation of instance #3).
   PR 14 is the first PR scope to exhibit catch-shape
   continuation simultaneously across three independent
   methodology-stack levels.

2. **Recursive-self-governance through evidence-inflation
   rejection operates symmetrically across all three
   continuations** — the discipline that PR 13 close §1.8
   introduced now operates at PR 14 across THREE methodology-
   stack levels at once. None of the three continuations
   inflated the methodology's instance count; each catch-
   shape continuation expanded the corroboration depth of
   an existing instance without creating a new instance.

3. **Direction A authored-superset rationale at framing
   level** (per spec §1 + §4.1 + framing §5.10) — three-
   reason argumentation pattern (single-variable discipline
   + semantic legibility + substrate reuse) for affirmative
   architectural decisions at framing-level direction-
   symmetric pressure. This is PR-14-specific archaeology;
   gate-level evaluation deferred to Gate 4 close.

The progression is **mechanically observed** (three-fold
catch-shape continuation at PR 14; recursive-self-governance
operating across three methodology-stack levels). PR 14
close registers the raw progression; Gate 4 close §x
performs methodology-promotion evaluation.

**Reasonable archaeology framings (Gate 4 close evaluates):**

- *"Grounding discipline operational maturation through
  three-fold catch-shape continuation"* — names the
  progression mechanically without claiming generalized
  methodology (would require further-gate corroboration).
- *"`feedback_ground_specs_in_actual_files` operational
  maturation with recursive-self-governance across three
  methodology-stack levels"* — frames as instance of the
  underlying memory discipline with the recursive-self-
  governance property operating symmetrically across all
  three continuations.
- *"Catch-shape continuation as depth-corroboration, not
  breadth-addition"* — names the methodology-self-governance
  property mechanically (catch-shape continuations expand
  corroboration depth of existing instances; the
  methodology's instance count is preserved).

PR 14 close does NOT canonicalize naming; Gate 4 close §x
makes the framing-vs-naming decision at gate level (cumulative
across PR 13 + PR 14 + PR 15 catch-point instances).

### 5.2 Pointer to Gate 4 close for cross-PR synthesis

Gate 4 close (future, same-commit-paired with final primary
PR per §7 below) owns:

- Complete catch-point migration progression evaluation
  across PR 13 + PR 14 + PR 15 (PR 13 contributes instances
  #4 + #5; PR 14 contributes three catch-shape continuations
  of instances #3 + #4 + #5; PR 15 may contribute additional
  instances or continuations).
- Cumulative architectural-sufficiency five-PR escalation
  (PR 9 + PR 10 + PR 11 + PR 13 + PR 14) plus PR 15
  evaluation.
- Cleanup-pressure-resistance class promotion evaluation
  reading five-PR populating evidence (PR 6 + PR 7 + PR 8
  + PR 9 + PR 10) + four-PR ABSENCE-corroboration evidence
  (PR 11 + PR 13 + PR 14 + (PR 15)).
- §5.3 candidate methodology observation gate-level
  promotion evaluation (four-instance ABSENCE evidence per
  asymmetric weighting; PR 15 may add a fifth instance).
- Three-PR Placement A operational corroboration evaluation
  (PR 13 + PR 14 contribute 3-form-ABSENCE each; PR 15
  contributes its own predicted-form outcomes per its
  framing).
- Placement B precondition 3 cumulative manifestation
  evaluation (PR 14 strengthens to two-PR manifestation;
  PR 15 may complete to three-PR manifestation).
- Catch-point migration candidate methodology prescriptive
  promotion candidacy (recursive-self-governance property
  added at PR 13 instance #5; PR 14 demonstrated multi-
  catch-shape simultaneous operation).
- PR-14-LOCAL parallel-not-regenerative pattern evaluation.
- Direction A authored-superset rationale archaeology
  evaluation.
- Conditional PR 12 disposition (deferred per Gate 4
  framing §5.10).
- Gate-level inheritance contract toward Gate 5.

Future phase architects read **Gate 4 close**, not PR 14
close, for the cross-PR methodology synthesis at Gate 4
scope.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 3 item 2)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
219 tests collected in 0.05s
```

Forge env collected: **219** ✓ (anchor matches spec §5.1
arithmetic: 218 baseline + 1 PR 14 new = 219; **exact
target**).

Full corpus suite execution: `219/219 passed` (verified at
Step 3).

Forge-bridge env not re-verified at PR 14 close; 6-test gap
inherited from PR 7 per `project_v1_4_x_harness_debt.md`.

### 6.2 PR 14 suite regression (Step 3 item 1)

```
$ python -m pytest tests/corpus/test_pr14_partial_narrow_divergence.py
========================= 1 passed, 1 warning in 0.07s =========================
```

PR 14 suite: **1/1** ✓.

### 6.3 Public API anchor (Step 3 item 8)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

`forge_bridge.__all__` count at PR 14 close: **19** ✓.

`compare_records`, `DivergenceReport`, `ComparatorInputError`
remain corpus-internal per PR 10 spec §5.7 + PR 11 framing
§5.7 + PR 13 framing §3.4 + PR 14 framing inheritance. PR 8's
`test_pr8_helpers_remain_corpus_internal` continues to
enforce mechanically.

### 6.4 Four-walker Layer 2 partition (Step 3 item 5)

All four Layer 2 walkers operational at PR 14 close:

- PR 4 walker (`test_pr4_participation_creep.py`) —
  production-import-topology — 1/1 passing.
- PR 8 walker (`test_pr8_seed_surface.py`) — orchestration-
  participation (5-symbol bounded toolbox) — 5/5 passing.
- PR 9 walker (`test_pr9_fixture_discipline.py`) —
  declarative-fixture-data (single-symbol-gate) — passing.
- PR 10 walker (`test_pr10_comparator_discipline.py`) —
  read-only-interpretive-authority (zero-symbol-gate) —
  passing.

Combined Layer 2 walker partition: **40/40 passing**
(including PR 9 + PR 10 walker tests in the partition).
Parallel-not-extension boundary preserved. Shared AST
mechanics do not imply shared ontology. PR 14's two new
files are target-disjoint from all four walkers' input sets.

### 6.5 Architectural sufficiency signal (Step 3 item 10)

```
$ git diff --stat 30412a3..HEAD -- forge_bridge/
(empty)
```

**Zero production source modifications across all 4 PR 14
commits** ✓ (spec + 3 implementation steps).

§2.4 Gate 4 architectural commitment travel verification at
this surface:

> Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.

The signal travels verbatim at this §6.5 per spec §0 + §1 +
§2 + Step 1, 2, 3 commit bodies + this close §1.5 + §6.5 =
8 cumulative travel surfaces at PR 14 close. Travel
deliberately stops short of fixture/test docstrings (carrier
/ gate-shaped governance asymmetry per §1.5).

Five-PR continuity (PR 9 + PR 10 + PR 11 + PR 13 + PR 14):
the divergence-shape robustness exercise demonstrates the
decomposition strategy operationally + reads the validated
comparator + recomposition arc + PR 13 calibration substrate
under partial-set divergence pressure without any production
surface change.

### 6.6 Layer 3 lint regression (Step 3 item 4)

```
$ python -m pytest tests/corpus/test_pr6_visual_asymmetry.py
17 passed in 0.18s
```

PR 6 Layer 3 lint: **17/17** ✓ unchanged across PR 14.

Zero new `emit_divergence_capture` call sites at PR 14; lint's
discovery walk input set unchanged.

### 6.7 PR 11 recomposition arc + PR 13 ordering-divergence regression (Step 3 item 7)

```
$ python -m pytest tests/corpus/test_pr11_recomposition_arc.py tests/corpus/test_pr13_ordering_divergence.py
========================= 4 passed, 1 warning in 0.16s =========================
```

PR 11 recomposition arc: **3/3** ✓ unchanged.
PR 13 ordering-divergence: **1/1** ✓ unchanged.
Combined: **4/4** ✓ ✓. PR 14 inherits the consumption pattern
without modification; PR 11 + PR 13's tests pass unchanged
after PR 14's addition.

### 6.8 PR 4 + PR 5 chat-handler + no-dependency regression (Step 3 item 3)

```
$ python -m pytest tests/corpus/test_pr4_chat_handler_integration.py tests/corpus/test_pr4_no_dependency.py tests/corpus/test_pr5_chain_step_integration.py
======================== 13 passed, 1 warning in 0.26s =========================
```

PR 4 + PR 5 chat-handler + no-dependency integration: **13/13**
✓ unchanged. PR 14's partial-set-divergence test exercises the
chat_handler arbitration surface through PR 9's monkeypatch
suite, but introduces zero modifications to the production
chat_handler surface.

### 6.9 Verbatim travel verification (Step 3 item 9)

- PR-14-LOCAL at fix_partial_narrow_divergence.py module
  docstring + test_pr14_partial_narrow_divergence.py module
  docstring (verified at Step 1; preserved through Steps 2-3).
- PR-14-LOCAL verbatim at all 3 PR 14 step commit message
  bodies (Step 1 + Step 2 + Step 3).
- PR-14-LOCAL verbatim at PR 14 spec §0 + §1 + §2 +
  this close §1.4 = **9 cumulative travel surfaces**
  (per §1.4 table).
- §2.4 Gate 4 architectural commitment verbatim at PR 14
  spec §0 + §1 + §2 + all 3 PR 14 step commit message
  bodies + this close §1.5 + §6.5 = **8 cumulative travel
  surfaces**. Travel deliberately stops short of fixture/
  test docstrings (carrier / gate-shaped governance
  asymmetry per §1.5).
- 17 inherited carriers cited by reference to canonical
  sources at both PR 14 module docstrings per spec §4.1.1
  + §4.2.1 (citation-by-reference discipline per spec §0
  + framing §3.1).
- Traversal trace verbatim from framing §2.1 at PR 14 test
  module docstring.
- Test-internal-archaeology-surfaces framing at PR 14 test
  module docstring (PR 9 helper imports admitted as test-
  internal archaeology surfaces, NOT public APIs).

---

## 7. Standalone close — Gate 4 close pairs with the final primary PR

Per Gate 4 framing §11.8 + PR 14 framing §11 + spec §6.4 +
Gate 2 + Gate 3 + PR 13 close §7 precedent:

**PR 14 close (this artifact) ships STANDALONE.** Gate 4
close (`A.5.3.2-GATE-4-CLOSE.md`) pairs at the same commit
with the FINAL primary PR's close (PR 15 close OR PR 12 close
if PR 12 materializes last). PR 14 is the SECOND of three
primary PRs sequenced within Gate 4; PR 14 close ships at
its own commit (PR 13 close shipped STANDALONE; PR 14 close
ships STANDALONE; the final primary PR's close pairs at
same commit with Gate 4 close).

**Cross-artifact responsibility deferral (per Gate 4 framing
§11.8 + spec §6.4 + PR 13 close §7 inheritance):**

**PR 14 close owns (this artifact):**

- PR 14 implementation arc archaeology (4-commit chain at
  §4 + close commit at §7).
- Partial-set divergence pure-isolation case operational
  archaeology (§1.1).
- Architectural sufficiency signal validation at PR 14 scope
  (§1.3 + §6.5 — 0-prod-mod outcome; five-PR escalation
  evidence).
- §1.6 fourth-instance ABSENCE outcome at PR 14 scope
  (Placement A contribution; second Gate 4 PR instance).
- §1.7 Placement B preconditions 1 + 2 manifestation at
  PR 14 scope (precondition 3 strengthening to two-PR
  manifestation; final-cumulative deferred to Gate 4 close).
- §1.8 catch-point migration three-fold continuation
  contribution at PR 14 scope (continuations of instances
  #3 + #4 + #5).
- PR-14-LOCAL pure-isolation discipline archaeology (§1.4);
  parallel-not-regenerative-of-PR-13-LOCAL pattern (§2.2).
- §2.4 Gate 4 architectural commitment travel inventory at
  PR 14 scope (§1.5).
- Zero-incarnation-amendments archaeology at PR 14 scope
  (§1.2 + §5.1).
- Both-skeletons-at-Step-1 lifecycle invariant operational
  verification at PR 14 (§1.11) as second corroboration of
  PR 13's PR-of-origin discipline (§2.4).
- Imports-land-when-used (member #10) symmetric verification
  at both new files (§1.12; fourth instance).
- Test-internal archaeology surfaces inheritance verification
  (§1.13; second corroboration of PR 13's inheritance).
- Direction A authored-superset rationale archaeology
  (§3.1).

**Gate 4 close will own (future, same-commit with final
primary PR's close):**

- Gate-arc synthesis across PR 13 + PR 14 + PR 15.
- Cleanup-pressure-resistance class final inventory at Gate 4
  scope (10 members + any PR 13/14/15 additions; PR 13 +
  PR 14 added zero per §1.10).
- Three-PR Placement A operational corroboration evaluation
  (cumulative across PR 13 + PR 14 + PR 15).
- Placement B precondition 3 final cumulative manifestation
  evaluation (PR 14 strengthens to two-PR manifestation;
  PR 15 may complete to three-PR).
- §5.3 candidate methodology observation gate-level
  promotion evaluation (four-instance ABSENCE evidence at
  PR 14; PR 15 may add a fifth instance).
- 0-prod-mod-as-architectural-sufficiency-signal gate-level
  promotion evaluation (five-PR escalation through PR 14;
  PR 15 may extend the escalation further).
- Catch-point migration candidate methodology gate-level
  promotion evaluation (instances #4 + #5 at PR 13; three-
  fold continuation at PR 14; PR 15 may add additional
  instances or continuations; recursive-self-governance
  property emerged at PR 13 instance #5 + demonstrated
  multi-catch-shape simultaneous operation at PR 14).
- PR-14-LOCAL parallel-not-regenerative pattern evaluation
  for prescriptive lineage discipline.
- Direction A authored-superset rationale evaluation for
  prescriptive direction-symmetric-pressure-decision pattern.
- Conditional PR 12 disposition (deferred per Gate 4
  framing §5.10).
- Gate-level inheritance contract toward Gate 5.

Where overlap surfaces between PR 14 close and the
forthcoming Gate 4 close, this artifact defers.

---

## 8. Cross-references

- **`A.5.3.2-PR14-FRAMING.md`** (`30412a3`) — binding pre-spec
  contract; §0 governing pair + carrier inventory; §2
  objective + traversal trace; §3 architectural inheritance;
  §3.1 17-carrier inheritance from Gate 4 framing; §3.6 both-
  bodies-at-Step-2 + Step 3 carriers-by-reference; §4
  architectural delta; §4.6 `"list"`-as-calibration-prompt
  archaeology; §5.4 three predicted cleanup-pressure forms;
  §5.5 PR-14-LOCAL binding statement; §5.10 Direction A
  affirmative architectural decision; §6.1 Placement A
  predicted-form-outcome contribution; §6.2 Placement B
  precondition manifestation contribution; §9.9 + §9.10 +
  §9.11 + §9.12 close-condition contributions.
- **`A.5.3.2-PR14-SPEC.md`** (`23c358a`) — implementation
  contract; §0 carrier travel by citation + travel discipline
  asymmetry table + spec-drafting-time grounding catch as
  catch-shape continuation of instance #5; §4.1 per-file
  derivation (fixture; including §4.1.2 grounded FIXTURE
  values lock with `:126` source-line citation); §4.2 per-
  file derivation (test); §4.2.3 single-test contract +
  nine-step traversal annotation inherited from PR 13;
  §4.2.4 four-key assertion contract + three-cleanup-
  pressure-form suppression evidence; §5 test count anchors
  (218 → 219 forge env); §6 atomic step decomposition
  (3 steps + close, all bundled-bundled-empty); §7 phase-end
  conditions; §9 resume protocol.
- **`A.5.3.2-PR13-CLOSE.md`** (`f53a469`) — immediate
  predecessor; PR-of-origin for pure-isolation discipline
  (§2.2 inherited at PR 14 §2.2); PR-of-origin for both-
  skeletons-at-Step-1 lifecycle invariant (§2.4 inherited at
  PR 14 §2.4); first calibration point precedent (§2.1
  inherited at PR 14 §2.1); recursive-self-governance
  discipline introduction (§1.8 operationalized symmetrically
  at PR 14 §1.8 across three methodology-stack levels);
  three-instance ABSENCE corroboration of §5.3 candidate
  methodology observation (PR 14 contributes fourth
  instance).
- **`A.5.3.2-GATE-4-FRAMING.md`** (`fbf2285`) — gate-level
  inheritance contract PR 14 operated against; §2.4 Gate 4
  architectural commitment travels at PR 14 surfaces per
  §1.5 table; §5 binding decisions (including §5.10
  conditional PR 12 disposition deferred); §6 Placement A +
  Placement B substrate; §11.5 + §11.8 close-cadence
  inheritance contract; §11.8 standalone-vs-paired close
  convergence rule per §7 above.
- **`A.5.3.2-GATE-3-CLOSE.md`** (`ee2225b`) — durable Gate 3
  archival state PR 14 inherited; §1.6 carrier #16
  promotion + 17 active carriers (cited by reference at PR
  14 module docstrings); §1.7 10-member cleanup-pressure-
  resistance class final inventory (unchanged at PR 14 per
  §1.10); §3 item 10 PR-11-LOCAL discipline inherited at
  gate level.
- **`A.5.3.2-PR11-CLOSE.md`** (`ee2225b`) — durable PR 11
  archival state PR 14 inherited; §1.4 PR-11-LOCAL
  traverses-not-erases-seams (inherited at gate level via
  Gate 3 close §3 item 10); §1.6 second-instance ABSENCE
  outcome (PR 14 contributes fourth instance per §1.6
  above); §2.1 recomposition arc consumption pattern (PR 14
  inherits unchanged); §2.3 architectural sufficiency
  signal Gate-X validation criterion (PR 14 extends to
  five-PR escalation per §2.3).
- **`A.5.3.2-PR10-CLOSE.md`** (`cf2b7ee`) — durable PR 10
  archival state PR 14 inherited; PR 10 §4.2 binding
  behavioral commitment ("compare as persisted") exercised
  under partial-set divergence pressure at PR 14 (per §1.6
  + §6.5 evidence); §5.3 candidate methodology observation
  first-instance precedent (PR 14 contributes fourth
  instance per §1.6 above).
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — four-fixture
  corpus PR 14's fixture sits alongside (PR 9 three fixtures
  + PR 13 ordering + PR 14 partial-set); PR 9 integration
  test infrastructure PR 14 imports as test-internal
  archaeology surfaces (`_apply_pr9_patches` +
  `_read_records` per §1.13); `fix_multi_match.py:105-140`
  arbitration trace PR 14's fixture inherits at
  `fix_partial_narrow_divergence.py` module docstring;
  `fix_multi_match.py:126` observation list-literal source
  PR 14's FIXTURE `expected_narrow[0:2]` grounds against.
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — §2.1 Gate 4
  comparator's two foundational dependencies operationally
  exercised at the PR 14 test (fixture_id joinability +
  record_kind partitioning).
- **`forge_bridge/corpus/_compare.py::compare_records`** —
  PR 10 interpretive-read surface PR 14 consumes at the
  test's final step; `_compare.py:503` direct list-equality
  detects partial-set divergence as `narrow_diverged=True`
  via length asymmetry (2 vs 3) + element-membership
  asymmetry at position 2.
- **`forge_bridge/corpus/_seed.py::drive_seed_fixture`** —
  PR 8 orchestration entry point PR 14 invokes per fixture;
  signature `(*, fixture_id, prompt, expected_narrow)`
  matches `FIXTURE` dict keys exactly.
- **`forge_bridge/console/handlers.py::chat_handler`** —
  production arbitration surface PR 14 drives via the PR 9
  patched `_invoke_chat_handler_in_process`.
- **`tests/corpus/test_pr14_partial_narrow_divergence.py`** (PR
  14 new, 252 lines) — single new test module; 1
  recomposition arc test + module docstring.
- **`tests/corpus/fixtures/fix_partial_narrow_divergence.py`**
  (PR 14 new, 208 lines) — single new fixture module;
  FIXTURE dict + module docstring (with grounded arbitration
  trace inherited from `fix_multi_match.py:105-140`).
- **`tests/corpus/test_pr9_fixture_integration.py::_apply_pr9_patches`**
  — test-internal archaeology surface PR 14 imports.
- **`tests/corpus/test_pr9_fixture_integration.py::_read_records`**
  — test-internal archaeology surface PR 14 imports.
- **`tests/corpus/fixtures/fix_multi_match.py:105-140`** —
  PR 9 multi-match arbitration trace PR 14's fixture
  inherits at `fix_partial_narrow_divergence.py` module
  docstring.
- **`tests/corpus/fixtures/fix_multi_match.py:126`** —
  PR 9 observation list-literal source line PR 14's
  `expected_narrow[0:2]` grounds against (both observation
  values appear on the same list-literal line per spec §0
  + §4.1.2 grounded citation).
- **`tests/corpus/test_pr9_fixture_integration.py:208-213`**
  — `_PR9_REACHABLE_TOOLS` declared order PR 14's fixture
  arbitration trace grounds against; `forge_ping` at line
  209 is the partial-set extension element source.
- **`tests/corpus/fixtures/fix_ordering_divergence.py`** (PR
  13 new, 149 lines) — PR 13 ordering-divergence fixture;
  PR 14 mirrors the fixture structural shape at the
  pure-isolation discipline.
- **`tests/corpus/test_pr13_ordering_divergence.py`** (PR 13
  new, 224 lines) — PR 13 ordering-divergence test;
  PR 14 mirrors the 9-step traversal annotation pattern +
  four-key assertion contract.
- **PR 14 4-commit chain** (`23c358a` → `9a09c86`) per §4
  table.
- **Local memory updates this session arc:**
  - PR-14-implementation-closed cursor written pre-synthesis
    per `feedback_cursor_before_retrospective_synthesis`.
  - MEMORY.md index updated.
  - origin/main push deferred to session close per prior-
    cursor pattern (PR 14 close is local-only at this
    commit).
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; PR 14 contributes
  (Gate 4 close evaluates):
  - Four-instance ABSENCE corroboration of the §5.3
    candidate methodology observation (per asymmetric
    weighting).
  - Five-PR architectural-sufficiency-signal escalation.
  - Catch-point migration three-fold continuation with
    recursive-self-governance operating symmetrically across
    three methodology-stack levels.
  - Both-skeletons-at-Step-1 lifecycle invariant second
    operational corroboration (PR 13 PR-of-origin + PR 14
    second instance).
  - PR-N-LOCAL parallel-not-regenerative pattern (PR-14-LOCAL
    as parallel scope-local discipline distinct from PR-13-
    LOCAL PR-of-origin substrate).
  - Direction A authored-superset rationale (three-reason
    argumentation pattern at framing-level direction-
    symmetric pressure).

---

End of PR 14 close. The implementation arc that began at
PR 14 framing (`30412a3`) closes here. The 4-commit chain
ships the partial-set divergence pure-isolation case + the
single integration test + the PR-14-LOCAL pure-isolation
discipline (parallel-not-regenerative-of-PR-13-LOCAL) + the
architectural sufficiency signal validation (0 production
source modifications across the PR; five-PR escalation
evidence) + the zero-incarnation-amendments archaeology
(matching PR 11's + PR 13's clean arcs) + the fourth-instance
ABSENCE outcome for the §5.3 candidate methodology
observation (corroborating across four independent PRs) +
the catch-point migration three-fold catch-shape continuation
(recursive-self-governance operating symmetrically across
three methodology-stack levels) + the both-skeletons-at-Step-1
lifecycle invariant second operational corroboration (PR 13
PR-of-origin + PR 14 second instance) + the Direction A
authored-superset rationale archaeology (three-reason
argumentation pattern at framing-level direction-symmetric
pressure).

PR 14 governs by inherited active carrier #17 (recomposition
discipline; enacted at use through the DivergenceReport's
per-surface partitioning preserved end-to-end under partial-
set divergence pressure) + the §2.4 Gate 4 architectural
commitment (divergence-shape robustness exercise as Gate 4's
deliberate continuation of empirically bounded topology
proof) + the PR-14-LOCAL binding statement (scope-local
discipline; pure-isolation property as laboratory-grade
methodology corroboration substrate, parallel to PR-13-LOCAL,
not regenerative of it).

The partial-set divergence vector is detectable end-to-end
through the validated PR 10 comparator + PR 11 recomposition
arc + PR 13 calibration substrate WITHOUT ANY production
source change. The divergence-shape robustness exercise's
second calibration point is operationally validated.

**Gate 4 advances. PR 15 inherits a validated comparator +
a corroborated recomposition demonstration + an
architecturally-sufficient decomposition strategy + the
first two calibration points of the three-PR Placement A +
Placement B substrate series.**
