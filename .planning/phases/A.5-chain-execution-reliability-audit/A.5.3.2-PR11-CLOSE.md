# A.5.3.2 PR 11 — Close (end-to-end recomposition arc)

**Status:** Durable archival state. PR 11 is the second of two
PRs sequenced within Gate 3 per Gate 3 framing §10
(conditional PR 12 disposition is Gate 3 close scope per
framing §5.5). The implementation arc that began at PR 11
framing commit `97c3fb4` (2026-05-11) closes at this commit.

PR 11 ships **the end-to-end recomposition arc** as a single
new test module
(`tests/corpus/test_pr11_recomposition_arc.py`, 313 lines)
containing three integration tests that drive each PR 9
fixture through the full decomposition seam path
(fixture → `drive_seed_fixture` → `chat_handler` arbitration
→ emission → JSONL → reader → `compare_records` →
`DivergenceReport` assertions). The implementation arc
traveled with **ZERO production source modifications**, **ZERO
spec amendments at incarnation**, and **ZERO cleanup-pressure
forms surfacing** — the cleanest reliability-PR arc to date.

This artifact mirrors PR 9 close + PR 10 close §1-§8 shape +
reseed protocol. **The Gate 3 close artifact
(`A.5.3.2-GATE-3-CLOSE.md`) ships at the same commit as this
artifact** per Gate 3 framing §11 + PR 11 framing §11 +
Gate 2 close 2026-05-11 (`a6e42f0`) precedent.

**Cross-artifact responsibility split (per PR 11 framing §11):**

- **PR 11 close (this artifact)** owns:
  - PR 11 implementation arc archaeology (4-commit chain).
  - Recomposition-through-existing-seams operational evidence.
  - Architectural sufficiency signal validation at PR 11
    scope (0-prod-mod outcome).
  - PR-11-LOCAL discipline archaeology
    (traverses-not-erases-seams operational).
  - §5.3 candidate methodology observation outcome at PR 11
    scope (second-instance ABSENCE).
  - PR 11-scoped cleanup-pressure-form encounters (none
    surfaced) + zero-incarnation-amendments archaeology.
- **Gate 3 close** (same commit) owns:
  - Gate-arc synthesis across PR 10 + PR 11.
  - Cleanup-pressure-resistance class final inventory at
    Gate 3 scope.
  - Candidate carrier #16 promotion evaluation against the
    12-surface cumulative evidence.
  - Conditional PR 12 disposition (promote / defer / reject).
  - Cross-PR methodology promotion candidacies
    (recomposition-through-existing-seams; 0-prod-mod-as-
    architectural-sufficiency; §5.3 framing-time-pressure-
    prediction-through-absence; three-PR catch-point
    migration).
  - Gate-level inheritance contract toward Gate 4.
  - The four §7.3 ontological questions handoff (per Gate 2
    close §7.3 + Gate 3 framing inheritance).

No section of this artifact pre-empts Gate 3 close's gate-arc
synthesis. Where overlap surfaces, this artifact defers.

---

## 1. What PR 11 established

### 1.1 Recomposition arc operational end-to-end

PR 11 ships `tests/corpus/test_pr11_recomposition_arc.py` (313
lines) — a single new test module containing three integration
tests that exercise the end-to-end recomposition arc per
spec §4.1.4–4.1.6:

| Test | Fixture | Outcome | Divergence |
|---|---|---|---|
| `test_recomposition_arc_single_survivor_no_divergence` | `fix-pr9-single-survivor` (prompt "ping forge") | PR14 + PR21 collapse to `["forge_ping"]` | `narrow_diverged=False` |
| `test_recomposition_arc_multi_match_no_divergence` | `fix-pr9-multi-match` (prompt "list") | PR14 yields `["forge_list_projects", "flame_list_libraries"]`; PR21 cannot collapse | `narrow_diverged=False` |
| `test_recomposition_arc_no_keyword_match_divergence` | `fix-pr9-no-keyword-match` (prompt "what time is it") | PR14 fallback returns full 4-tool reachable set; authored `[]` vs. observed full set | `narrow_diverged=True` |

Each test traverses the full decomposition seam path
explicitly at the test body level (per spec §4.1.4 nine-step
traversal annotation):

```
fixture (FIX_<shape>)
  → drive_seed_fixture          [orchestration seam]
    → emit_seed_expectation     [expectation persistence seam]
    → chat_handler arbitration  [observation production seam]
      → emit_divergence_capture [observation persistence seam]
        → JSONL persistence     [persistence-topology seam]
          → reader              [readback seam (via _read_records)]
            → compare_records   [interpretive-read seam]
              → DivergenceReport assertions (four-key structural)
```

No PR 11 test wraps `drive_seed_fixture` in a convenience
function; no test extracts a "fixture-to-DivergenceReport"
helper; no test factors the readback + comparator invocation
into a reusable assertion helper. Each test traverses the
full path explicitly per PR-11-LOCAL discipline.

### 1.2 ZERO incarnation amendments — the cleanest arc to date

PR 11 shipped with **ZERO spec amendments at any incarnation
surface**:

- ZERO drafting-time amendments at spec drafting.
- ZERO grounding-time amendments at Step 1 implementation
  prep.
- ZERO implementation-time amendments during Steps 1–2.
- ZERO verification-time amendments at Step 3.
- ZERO Step N.5 surgical commits.

This is the cleanest amendment archaeology of any A.5.3.2
reliability PR. The framing → spec → implementation arc
traveled clean without in-flight realignment at ANY incarnation
surface.

**The framing→spec convergence pass DID register the grounding
discipline operationally** — the six grounded reads (per
framing §3.7) were performed at the framing→spec session
boundary BEFORE drafting any spec assertion about the surfaces.
The spec drafted against grounded-source-of-truth from the
start; Step 1 implementation prep found nothing to amend. The
grounding-discipline operated at framing-time, eliminating the
gap that grounding-time amendments at PR 9 + PR 10 had
caught.

**This contributes the third instance to the three-PR
amendment-at-incarnation catch-point progression** (Gate 3
close §1 will synthesize the cross-PR pattern; this section
names PR 11's specific instance):

| PR | Amendment | Catch point |
|---|---|---|
| PR 9 | §4.7 amendment 2026-05-11 | Step 2 implementation post-Step-1 (`627b104` precursor) |
| PR 10 | §4.4 amendment 2026-05-11 | Step 1 implementation prep (read-before-implement) |
| **PR 11** | **(none)** | **Framing/spec drafting time — six grounded reads completed at framing→spec convergence pass; no amendment surfaced** |

PR 11's contribution to the progression is **the discipline
operating at framing/spec drafting time**, removing the gap
that the amendment cadence existed to close. The progression
encodes maturation of `feedback_ground_specs_in_actual_files`:
the catch point migrates earlier across PRs, ultimately to
**before** any spec text drafts that could later require
amendment.

### 1.3 Architectural sufficiency signal — 0 production source modifications

PR 11 ships **0 modifications to production source files**:

```
$ git diff --stat 97c3fb4..HEAD -- forge_bridge/
(empty)
```

Verified by inspection across all 4 PR 11 commits (spec + 3
implementation steps). The 0-prod-mod outcome is the
**architectural sufficiency signal** per spec §5.2 + framing
§2.3:

> **PR 11 demonstrates the Gate 2 + Gate 3 decomposition
> strategy was sufficient — the recomposition arc traverses
> every seam without requiring extension, relaxation, or
> modification of any production source surface.**

**Three-PR architectural sufficiency escalation:**

| PR | Production diff | Validation strength |
|---|---|---|
| PR 9 | 0 prod mods (test-surface-only fixture authoring) | Substrate surfaces sufficient for fixture authoring + integration tests against existing surfaces |
| PR 10 | Exactly 1 new file (`_compare.py`, 523 lines), 0 mods elsewhere | New read-side surface composable without modifying existing surfaces |
| **PR 11** | **0 prod mods (test-surface-only end-to-end recomposition)** | **Full recomposition arc traversable without modifying ANY production surface — decomposition strategy operationally validated by end-to-end exercise** |

PR 11's 0-prod-mod outcome is **the strongest individual
evidence** that the Gate 2 + Gate 3 decomposition strategy
was sufficient. The three-PR escalation registers at Gate 3
close §1 as the materially-validates archaeology toward Gate 4
inheritance.

The signal travels at:

- PR 11 test module docstring (Step 1 surface).
- All 4 PR 11 commit message bodies under "Architectural
  sufficiency signal" sections.
- This close artifact §1.3 + §6.5.
- Gate 3 close §1 (gate-arc synthesis; same-commit).

### 1.4 PR-11-LOCAL discipline operational

PR-11-LOCAL binding statement (per PR 11 framing §5.6,
scope-local per PR-N-LOCAL non-regeneration rule):

> **PR 11 traverses the decomposition seams established by
> Gate 2 + Gate 3 substrate work without erasing them.
> Call-site awkwardness during recomposition is acceptable
> evidence that the decomposition boundaries held; introducing
> production abstractions whose primary purpose is "making
> recomposition cleaner" is rejected at the spec layer.**

**Operational evidence at PR 11:**

- Each PR 11 test body explicitly traverses each decomposition
  seam (per spec §4.1.4 nine-step annotation). No helper
  absorbs the arc.
- The join boilerplate per test (filter by fixture_id +
  partition by record_kind + comparator invocation) is
  ~4–5 lines of explicit code at each test surface. This is
  the "call-site awkwardness" the discipline accepts as
  evidence the decomposition held.
- No PR 11 test module helper functions were authored. No
  fixture-to-DivergenceReport orchestrator. No reader-side
  join helper. No comparator-side batch variant.

**Operational placement of PR-11-LOCAL:**

- Test module docstring (Step 1; verbatim).
- All 4 PR 11 commit message bodies under "preserved
  invariants" / "PR-11-LOCAL" sections.
- This close artifact §1.4 + §7 (close-artifact archaeology).

PR-11-LOCAL does NOT regenerate beyond PR 11. PR 12 (if
promoted by Gate 3 close) / Gate 4 / future-gate work does
not inherit PR-11-LOCAL as carrier; new PR-N-LOCAL statements
may be authored at framing level as their own PR-scope
discipline statements per the canonicalized pattern.

### 1.5 Gate-3-LOCAL governing sentence — 4 PR 11 surfaces (12 cumulative)

The Gate-3-LOCAL governing sentence
("Gate 3 proves topology, not infrastructure.") traveled
verbatim through **4 PR 11 surfaces** with explicit *candidate
carrier #16 corroboration substrate* marking:

| # | Surface | Step | Commit |
|---|---|---|---|
| 1 | `tests/corpus/test_pr11_recomposition_arc.py` module docstring | Step 1 | `2c65746` |
| 2 | Step 1 commit body | Step 1 | `2c65746` |
| 3 | Step 2 commit body | Step 2 | `1b81436` |
| 4 | Step 3 commit body | Step 3 | `ae69fba` |

**Cumulative across PR 10 + PR 11: 12 surfaces** (PR 10's 8
per PR 10 close §1.2 Signal 4 + PR 11's 4 above). The ≥4
threshold for Gate 3 close candidate-carrier-#16 promotion
evaluation per Gate 3 framing §6.1 criterion 1 is significantly
exceeded (3x over).

The asymmetric ordering (active carrier #17 primary +
Gate-3-LOCAL form secondary + substrate marking) preserved
verbatim at every site. PR 11 wrote "16 active carriers +
candidate #16" verbatim; nowhere wrote "17 active carriers"
or "carriers #1-#17." Implicit promotion of candidate #16
rejected at every PR 11 travel site per framing §3.1 + spec
§0.

**Promotion of candidate #16 to active carrier is NOT
performed at this PR 11 close.** Per Gate 3 framing §6.1 +
spec §0 + PR 10 close §1.2 + PR 11 framing §3.10 + cursor
§"Things that might trip up #4": the promotion evaluation
happens at **Gate 3 close** (same-commit per §11). This
artifact preserves the candidate-substrate marking
discipline; Gate 3 close performs the evaluation.

### 1.6 §5.3 candidate methodology observation — SECOND corroborating instance (ABSENCE outcome)

PR 10 close §5.3 registered as first-corroborated-instance
candidate methodology observation:

> Framing-time pressure prediction operates load-bearing
> through absence rather than rejection.

PR 11 framing §3.6 enumerated four most-likely-to-surface
cleanup-pressure forms (helper merger / premature surface
normalization / speculative fixture-semantics widening /
recomposition smoothing). **PR 11 implementation did NOT
surface any of the four predicted forms.**

Per PR 11 framing §6.4 asymmetric weighting:

> **Absence STRENGTHENS candidacy** (cause-not-coincidence).
> Corroborated absence is stronger evidence than rejected-
> instance archaeology.

The §5.3 candidate methodology observation now has TWO
independent corroborating instances:

| Instance | PR | Predicted forms (framing) | Surfaced? | Outcome |
|---|---|---|---|---|
| 1 | PR 10 | helper merger / persistence creep / walker abstraction | None | ABSENCE |
| **2** | **PR 11** | **helper merger / premature surface normalization / fixture widening / recomposition smoothing** | **None** | **ABSENCE** |

Two independent ABSENCE outcomes across two independent PRs.
The framing-time prediction operating as **cause** (not
coincidence) is now operationally observed across two
independent PR scopes. The candidate observation strengthens
toward promotion at Gate 3 close (gate-level methodology
promotion evaluation reads the two-instance cumulative
evidence per §3.9 + §6.4).

**PR 11 does NOT pre-empt the methodology-promotion
evaluation.** This section registers PR 11's second-instance
outcome as raw archaeology; Gate 3 close §1 performs the
gate-level evaluation.

**Why the framing-time discipline operated at PR 11
specifically:**

PR 11's particular cleanup-pressure-resistance mechanism was
the **architectural-sufficiency-signal target** itself.
Framing §5.2 elevated 0-prod-mod from "clean diff hygiene"
to **named architectural sufficiency signal**; that
elevation operated as anchored discipline at every Step 1 +
Step 2 implementation decision. The temptation to "make
recomposition cleaner" via a helper would have been a real
pressure under different framing — but the architectural-
sufficiency-signal target made the temptation rejected at
the design level (per spec §5.3 + §5.6 + PR-11-LOCAL §1.4).

This is the operational form of the candidate methodology
observation: when framing-time prediction elevates a goal to
named-discipline status, the discipline shapes implementation
decisions without needing per-pressure rejection events.

### 1.7 Test count anchor — 217 forge env collected (exact spec target)

PR 11 close test count arithmetic (per spec §5.1
archaeology-grade):

```
214 baseline (PR 10 close §1.4 forge env collected)
+ 3 PR 11 recomposition arc tests (Step 2)
= 217 forge env collected at PR 11 close
```

**Step 3 verification re-confirmed (and re-verified at close):**

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
217 tests collected in 0.04s
```

PR 11 ships **3 named tests**; named == collected (no
parametrize across the 3 tests per spec §5.3 inventory lock).

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`). Target at PR 11 close:
**208 baseline + 3 new = 211 forge-bridge env collected.**
Not re-verified at PR 11 close beyond inheritance
documentation — the 6-test gap is PR 7-scope, not PR 11-scope.
**Do not conflate the two env counts** per PR 8 close §5.6 +
PR 10 close §1.4.

### 1.8 No cleanup-pressure-resistance class additions at PR 11

The 10-member cleanup-pressure-resistance class (PR 10 close
§1.7 final inventory) preserves unchanged. PR 11 surfaced
**no new candidate class members** during implementation:

- Helper merger pressure: did NOT surface.
- Premature surface normalization pressure: did NOT surface
  (test 3's set-equality at the test assertion surface is
  property-isolation discipline, NOT premature normalization;
  the comparator itself preserves list-equality per PR 10
  §4.2).
- Speculative fixture-semantics widening: did NOT surface.
- Recomposition smoothing (the framing's PR 11 signature
  candidate form): did NOT surface.

The 10-member class inventory at PR 11 close is **unchanged
from PR 10 close**:

| # | Member | PR | Protection |
|---|---|---|---|
| 1 | Helper duplication | PR 7 | Framing §6 + spec §7 close conditions |
| 2 | Visual asymmetry / Properties A–D | PR 6 | Layer 3 lint |
| 3 | Intentionally inert structural parameters | PR 7 | §4.2 binding pair + test enforcement |
| 4 | Always-present `fixture_id` field on observation records | PR 7 | Builder dict structure + test enforcement |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 | §5.5 binding pair + test enforcement |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 | Inline pattern + Step 8 spec |
| 7 | Companion records as truth-partitioning | PR 8 | `_seed.py` docstring + framing §6.1 + schema validator branch rejection |
| 8 | `emit_seed_expectation` as semantics-not-topology | PR 8 | `_seed.py` + helper docstrings + framing §6.2 + Layer 2 `_SEED_PERMITTED_IMPORTS` value-lock |
| 9 | Fixture-surface-data-discipline | PR 9 | Fixture module docstrings + framing §6.1 + Layer 2 `_FIXTURE_PERMITTED_IMPORTS` value-lock + PR 9 walker |
| 10 | Speculative-reserved-imports rejection (import-set compare-as-persisted) | PR 10 | Spec §4.1.2 amendment + Step-N imports discipline + framing §3.6 form #5 sibling archaeology |

The class is now demonstrably populatable across **four
reliability phases (PR 6 + PR 7 + PR 8 + PR 9 + PR 10)** under
genuinely independent conditions. PR 11 adds no member but
**operationally corroborates the framing-level protections**
through absence (per §1.6 above).

Gate 3 close §1 reads the four-PR populating evidence in the
class-promotion-to-SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+
evaluation.

---

## 2. What Gate 4 / future Gate-X work inherits from PR 11

PR 11 is the recomposition arc terminus within Gate 3. Future
Gate-X work inherits PR 11's contributions; the gate-level
inheritance contract lives at Gate 3 close §2. This section
names PR 11-scoped inheritance only.

### 2.1 The recomposition arc as consumption pattern

`tests/corpus/test_pr11_recomposition_arc.py` ships as a
reusable consumption pattern for future end-to-end fixture-
driven recomposition tests. The pattern is:

```python
# 1. Apply PR 9 monkeypatch suite (test-internal archaeology
#    surface inherited from PR 9).
corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

# 2. Drive fixture through full decomposition seam path.
drive_seed_fixture(**FIXTURE)

# 3. Read back persisted records.
records = _read_records(corpus_dir)

# 4. Partition records by fixture_id + record_kind.
matching = [r for r in records if r.get("fixture_id") == FIXTURE["fixture_id"]]
observation = next(r for r in matching if r["record_kind"] == "observation")
expectation = next(r for r in matching if r["record_kind"] == "expectation")

# 5. Invoke comparator.
report = compare_records(
    observation_record=observation,
    expectation_record=expectation,
)

# 6. Assert against DivergenceReport four-key structural shape.
assert report["fixture_id"] == FIXTURE["fixture_id"]
assert report["expectation"]["expected_narrow"] == [...]
assert report["observation"]["observed_narrow"] == [...]
assert report["divergence"]["narrow_diverged"] is [True | False]
```

**What Gate 4 / future work may reuse:**

- The pattern verbatim for future fixture-driven recomposition
  tests (e.g., chain-step-surface seeding tests if/when
  carrier #15's third clause framing pass occurs).
- The PR 9 `_apply_pr9_patches` + `_read_records` imports as
  **test-internal archaeology surfaces** (NOT public APIs;
  preserves the underscored-private status discipline per
  spec §4.1.2).

**What Gate 4 / future work must NOT do:**

- Promote the pattern into a test-helper function that
  absorbs the traversal (would violate the PR-11-LOCAL
  discipline at its scope; even if PR-11-LOCAL doesn't
  regenerate, the underlying recomposition-asymmetry framing
  applies at gate level per Gate 3 close).
- Promote PR 9 underscored helpers to public APIs (the
  test-internal archaeology surfaces framing is operational
  discipline; promotion requires explicit framing-level
  review).
- Re-author `_apply_pr9_patches` or `_read_records` with
  modified semantics (the imports are stable consumption
  surfaces; modifications would break PR 11 + future
  consumers' contract).

### 2.2 PR-11-LOCAL traverses-not-erases-seams as PR-of-origin archaeology

PR-11-LOCAL is scope-local. It does NOT regenerate beyond
PR 11. But the **discipline observation** — that successful
recomposition is evidence the decomposition was real and is
NOT justification for collapsing seams — registers as
PR-of-origin archaeology at Gate 3 close + future-gate
framing.

If a future Gate-X phase recomposes additional decomposition
seams (e.g., chain-step-surface seeding via a separate framing
pass per carrier #15's third clause), the PR-N-LOCAL
discipline statement for that PR may **reference PR-11-LOCAL
as PR-of-origin** for the recomposition-asymmetry pattern
while authoring its own scope-local discipline.

### 2.3 The architectural sufficiency signal as Gate-X validation criterion

PR 11's 0-prod-mod outcome — and the three-PR escalation
(PR 9 + PR 10 + PR 11) — registers as a **validation criterion
template** for future Gate-X reliability work. The pattern:

1. Framing names architectural sufficiency signal as goal
   (NOT just "clean diff hygiene").
2. Spec encodes the signal as a regression contract.
3. Implementation respects the signal at each commit (verified
   at each Step verification).
4. Close artifact documents the signal as architectural
   archaeology, not just metric pass/fail.

Future Gate-X framings may adopt the template at their own
gate-level architectural commitments; the elevation discipline
(0-prod-mod as named signal vs. metric) is the
methodology contribution PR 11 + the three-PR escalation
demonstrate.

Gate 3 close §1 + the methodology-promotion-candidacies
evaluation registers this as candidate methodology pending
Gate 4 corroboration.

---

## 3. What Gate 4 / future work changes (deferred to Gate 3 close)

PR 11 close defers gate-level inheritance contract to Gate 3
close §2 (same commit). This section names PR 11-scoped
permanence only.

### 3.1 Permanent PR 11 archaeology

Regardless of Gate 4's specific deliverables, the following
PR 11 outcomes are **permanent archaeology**:

- **The three PR 11 recomposition arc tests** ship as stable
  archaeology. Any modification requires framing-level review.
- **The 0-prod-mod outcome at PR 11** is recorded as
  validation evidence for the Gate 2 + Gate 3 decomposition
  strategy.
- **The 12 cumulative Gate-3-LOCAL surfaces** (PR 10's 8 +
  PR 11's 4) are the evidence base Gate 3 close reads.
- **The §5.3 candidate methodology observation second-instance
  ABSENCE outcome** is recorded; Gate 3 close performs
  promotion evaluation.
- **The three-PR amendment-at-incarnation catch-point
  progression** (PR 9 post-Step-1 / PR 10 Step-1-prep / PR 11
  framing-spec-drafting-time) is recorded as raw progression
  archaeology; Gate 3 close performs methodology-naming
  evaluation.
- **The 10-member cleanup-pressure-resistance class final
  inventory** is unchanged at PR 11 close (no PR 11
  additions).
- **`forge_bridge.__all__` stays at 19 symbols.**

---

## 4. Step-by-step archaeology — 4-commit PR 11 chain

PR 11's implementation arc is 4 commits, beginning at spec
commit `6a5df95` (2026-05-11) and closing at this commit +
Gate 3 close (same commit). The chain is shorter than PR 9's
10-commit + PR 10's 7-commit arcs because PR 11 had **zero
spec amendments + zero Step N.5 surgical commits + zero
implementation-time amendments**.

| # | Commit | Type | Step | Lines | Cumulative |
|---|---|---|---|---|---|
| 1 | `6a5df95` | Spec | (pre-step) | +1332 | 1332 |
| 2 | `2c65746` | Step 1 — skeleton (single-file) | Step 1 | +89 | 1421 |
| 3 | `1b81436` | Step 2 — architectural-center (3 tests bundled) | Step 2 | +224 | 1645 |
| 4 | `ae69fba` | Step 3 — final verification (empty) | Step 3 | 0 | 1645 |

**Step archaeology — methodology contributions per commit:**

- **Spec** (`6a5df95`) — File-level precision derived from
  framing's six binding decisions + the two pre-spec decisions
  surfaced at framing→spec convergence (test count locked at
  3; test infrastructure IMPORT from PR 9 as test-internal
  archaeology surfaces). One redline applied at spec review
  (§4.1.6 set-equality assertion archaeology strengthened with
  property-isolation framing). 1332 lines.
- **Step 1** (`2c65746`) — Test module skeleton (single-file).
  Module docstring (13-item structure per §4.1.1 carrying
  Gate-3-LOCAL form + PR-11-LOCAL + traversal trace + 17
  inherited carriers cited by reference + test-internal-
  archaeology-surfaces framing + spec/framing/close references).
  Imports: `from __future__ import annotations` ONLY (member
  10 discipline). No test bodies, no constants, no helpers.
  89 lines.
- **Step 2** (`1b81436`) — Architectural-center commit (3
  recomposition arc tests bundled). Imports landed per member
  10 (imports-land-when-used): pathlib, pytest, compare_records,
  drive_seed_fixture, three FIXTURE imports, two PR 9 test-
  internal archaeology surface imports. Three test functions
  with full bodies + explicit nine-step traversal annotation
  comments. Full three-round review applied per Gate 2
  framing §5.7 integration-work elevation. 224 lines added;
  313 lines total.
- **Step 3** (`ae69fba`) — Final verification. Empty commit;
  10-item verification checklist + 17 inherited carriers
  cited by reference + PR-11-LOCAL verbatim + Gate-3-LOCAL
  form verbatim with substrate marking + 12-surface cumulative
  Gate-3-LOCAL travel count + zero-amendment archaeology +
  §5.3 second-instance ABSENCE outcome + PR 11 commit chain
  summary in commit body. No new code.

**Step N.5 surgical cadence: NOT triggered at PR 11.** Per
PR 9's twice-corroborated pattern + PR 10's zero
corroborations: PR 11 also added zero corroborations. The
3-times-corroborated promotion status from Gate 2 close §5
preserves intact (PR 8 Step 4.5 + PR 9 Step 2.5 + PR 9
Step 5.5); PR 10 + PR 11 each added no corroborations.

The pattern's availability is preserved at framing §3.8 + this
close §4; absent corroboration is not falsification.

---

## 5. Methodology observations at PR 11 scope

PR 11's methodology contributions are largely **deferred to
Gate 3 close §1** for cross-PR synthesis. This section names
PR 11-scoped observations only; the gate-level synthesis
(four-variant amendment taxonomy + cleanup-pressure-resistance
class final inventory + cross-PR promotion candidacies) lives
at Gate 3 close.

### 5.1 Zero-incarnation-amendments as PR 11's specific archaeology

PR 11's specific methodology archaeology is the **zero-
incarnation-amendments outcome** (per §1.2). This is the third
instance in the catch-point migration progression PR 9 + PR 10
established. Per the asymmetric weighting framing applied at
the §5.3 candidate methodology observation (framing §6.4):

- PR 9: grounding-time amendment at Step 2 implementation
  post-Step-1 — discipline operating at implementation surface.
- PR 10: grounding-time amendment at Step 1 implementation
  PREP — discipline operating at implementation-prep surface
  (earlier catch).
- **PR 11: zero amendments at any surface — discipline operating
  at framing/spec drafting time** (the six grounded reads
  completed at framing→spec convergence; the spec drafted
  against grounded source-of-truth from the start).

The progression is **mechanically observed** (catch point
migrates earlier across PRs). PR 11 close registers the raw
progression; Gate 3 close §1 performs methodology-promotion
evaluation.

**Reasonable archaeology framings (Gate 3 close evaluates):**

- *"Grounding discipline maturation pattern"* — names the
  progression mechanically without claiming generalized
  methodology (would require further-PR corroboration).
- *"`feedback_ground_specs_in_actual_files` operational
  maturation"* — frames as instance of the underlying memory
  discipline rather than new methodology.
- *"Framing/spec-drafting-time grounding as terminal catch-
  point"* — names the discipline endpoint mechanically.

PR 11 close does NOT canonicalize naming; Gate 3 close §1
makes the framing-vs-naming decision at gate level.

### 5.2 Pointer to Gate 3 close §1 for cross-PR synthesis

Gate 3 close §1 (same commit) owns:

- Complete four-variant amendment-at-incarnation taxonomy
  with PR-of-origin noted per variant.
- Three-PR amendment catch-point progression
  (mechanically-observed pattern; promotion evaluation).
- Cumulative architectural concentration framing across
  PR 10 + PR 11 (per PR 9 close §1.8 + PR 10 close §1.8
  precedents).
- Cleanup-pressure-resistance class final inventory at Gate 3
  scope (10 members; no PR 11 additions; class-promotion
  evaluation reading four-PR populating evidence).
- §5.3 candidate methodology observation gate-level promotion
  evaluation (two-instance ABSENCE evidence per asymmetric
  weighting).
- Recomposition-through-existing-seams + 0-prod-mod-as-
  architectural-sufficiency promotion candidacies (first-
  instance at PR 11; cross-PR or future-gate corroboration
  pending).
- Four-walker Layer 2 partition operational at Gate 3 close.
- Three-authority-surface partition + PR-INTERNAL three-way
  authority partition (write-side) + PR 10 read-side structural
  parallel preserved at Gate 3 close.

Future phase architects read **Gate 3 close**, not PR 11 close,
for the cross-PR methodology synthesis at Gate 3 scope.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 3 item 2)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
217 tests collected in 0.04s
```

Forge env collected: **217** ✓ (anchor matches spec §5.1
arithmetic: 214 baseline + 3 PR 11 new = 217; **exact target**).

Full corpus suite execution: `217/217 passed` (verified at
Step 3).

Forge-bridge env not re-verified at PR 11 close; 6-test gap
inherited from PR 7 per `project_v1_4_x_harness_debt.md`.

### 6.2 PR 11 suite regression (Step 3 item 1)

```
$ python -m pytest tests/corpus/test_pr11_recomposition_arc.py
======================== 3 passed, 1 warning in 0.10s =========================
```

PR 11 suite: **3/3** ✓.

### 6.3 Public API anchor (Step 3 item 8)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

`forge_bridge.__all__` count at PR 11 close: **19** ✓.

`compare_records`, `DivergenceReport`, `ComparatorInputError`
remain corpus-internal per PR 10 spec §5.7 + PR 11 framing
§5.7. PR 8's `test_pr8_helpers_remain_corpus_internal`
continues to enforce mechanically.

### 6.4 Four-walker Layer 2 partition (Step 3 item 5)

All four Layer 2 walkers operational at PR 11 close:

- PR 4 walker (`test_pr4_participation_creep.py`) —
  production-import-topology — 1/1 passing.
- PR 8 walker (`test_pr8_seed_surface.py`) — orchestration-
  participation (5-symbol bounded toolbox) — 5/5 passing.
- PR 9 walker (`test_pr9_fixture_discipline.py`) —
  declarative-fixture-data (single-symbol-gate) — 2/2 passing.
- PR 10 walker (`test_pr10_comparator_discipline.py`) —
  read-only-interpretive-authority (zero-symbol-gate) — 2/2
  passing.

Parallel-not-extension boundary preserved. Shared AST mechanics
do not imply shared ontology.

### 6.5 Architectural sufficiency signal (Step 3 item 10)

```
$ git diff --stat 97c3fb4..HEAD -- forge_bridge/
(empty)
```

**Zero production source modifications across all 4 PR 11
commits** ✓.

Three-PR continuity (PR 9 + PR 10 + PR 11): the recomposition
arc demonstrates the decomposition strategy operationally
across substrate authoring + isolated comparator authoring +
end-to-end traversal.

### 6.6 Layer 3 lint regression (Step 3 item 4)

```
$ python -m pytest tests/corpus/test_pr6_visual_asymmetry.py
17 passed in 0.14s
```

PR 6 Layer 3 lint: **17/17** ✓ unchanged across PR 11.

Zero new `emit_divergence_capture` call sites at PR 11; lint's
discovery walk input set unchanged.

### 6.7 Console tests regression (Step 3 item 7)

```
$ python -m pytest tests/console/ -k "chat_handler"
50 passed in 0.41s
```

Console chat-handler subset: **50/50** ✓ unchanged (matches
PR 10 anchor exactly).

Full `tests/console/` execution: 361/361 passed unchanged
(strictly stronger than the 50-test anchor; documented for
archaeology).

### 6.8 Gate-3-LOCAL travel verification (Step 3 item 9)

Gate-3-LOCAL governing sentence ("Gate 3 proves topology, not
infrastructure.") traveled verbatim through **4 PR 11 surfaces**
with explicit *candidate carrier #16 corroboration substrate*
marking (per §1.5 table).

≥1 PR 11 surface threshold required at PR 11 close (per
framing §9 condition 9): met (4 surfaces). Cumulative across
PR 10 + PR 11: **12 surfaces** — ≥4 Gate 3 close threshold
significantly exceeded (3x over).

### 6.9 Verbatim travel verification (Step 3 item 9)

- Gate-3-LOCAL form + PR-11-LOCAL at PR 11 test module
  docstring (verified at Step 1; preserved through Steps 2-3).
- 17 inherited carriers cited by reference to canonical
  sources at PR 11 test module docstring per spec §4.1.1
  abbreviation discipline.
- Traversal trace verbatim from framing §2 at PR 11 test
  module docstring.
- Test-internal-archaeology-surfaces framing at PR 11 test
  module docstring (PR 9 helper imports admitted as test-
  internal archaeology surfaces, NOT public APIs).
- PR-11-LOCAL verbatim at all 4 PR 11 commit message bodies.

---

## 7. Same-commit Gate 3 close convergence

Per Gate 3 framing §11 + PR 11 framing §11 + this spec §6.4 +
Gate 2 close 2026-05-11 (`a6e42f0`) precedent:

**PR 11 close (this artifact) + Gate 3 close
(`A.5.3.2-GATE-3-CLOSE.md`) ship at the same final commit.**

Two artifacts at one commit. Responsibility split (per PR 11
framing §11 + this §0):

**PR 11 close owns (this artifact):**

- PR 11 implementation arc archaeology (4-commit chain at §4).
- Recomposition-through-existing-seams operational evidence
  at PR 11 scope (§1.1 + §1.4).
- Architectural sufficiency signal validation at PR 11 scope
  (§1.3 + §6.5).
- §5.3 second-instance ABSENCE outcome at PR 11 scope (§1.6).
- PR-11-LOCAL discipline archaeology (§1.4).
- Zero-incarnation-amendments archaeology at PR 11 scope
  (§1.2 + §5.1).

**Gate 3 close owns (sibling artifact, same commit):**

- Gate-arc synthesis across PR 10 + PR 11.
- Cleanup-pressure-resistance class final inventory at Gate 3
  scope.
- Candidate carrier #16 promotion evaluation against 12-
  surface cumulative evidence.
- Conditional PR 12 disposition (promote / defer / reject)
  per framing §5.5 qualitative trigger.
- Cross-PR methodology promotion candidacies (recomposition-
  through-existing-seams; 0-prod-mod-as-architectural-
  sufficiency; §5.3 framing-time-pressure-prediction-
  through-absence; three-PR amendment-catch-point-migration).
- Gate-level inheritance contract toward Gate 4.
- The four §7.3 ontological questions handoff (per Gate 2
  close §7.3 + Gate 3 framing inheritance).

Where overlap surfaces, this artifact defers to Gate 3 close.

---

## 8. Cross-references

- **`A.5.3.2-GATE-3-CLOSE.md`** (this commit) — sibling
  artifact; ships at the same commit per §7. Gate 3 close
  owns gate-arc synthesis, candidate carrier #16 promotion
  evaluation, conditional PR 12 disposition, cross-PR
  methodology promotion candidacies, gate-level inheritance
  contract toward Gate 4.
- **`A.5.3.2-PR11-FRAMING.md`** (`97c3fb4`) — binding pre-spec
  contract; §0 governing pair; §2 objective + traversal
  trace; §3 architectural inheritance; §4 architectural delta;
  §5 binding decisions (including the §5.2 0-prod-mod
  elevated to architectural sufficiency signal); §6.4
  asymmetric weighting framing for §5.3 candidate
  observation; §7 23 non-acquisition commitments; §11 same-
  commit convergence responsibility split.
- **`A.5.3.2-PR11-SPEC.md`** (`6a5df95`) — implementation
  contract; §0 carrier travel inventory; §4.1 per-file
  derivation (single new test module); §6 atomic step
  decomposition (3 steps + close); §9 resume protocol.
- **`A.5.3.2-PR10-CLOSE.md`** (`cf2b7ee`) — durable PR 10
  archival state PR 11 inherited; §1 PR 10 established
  (comparator surface + 4 architectural signals + member 10
  promotion); §2 PR 11 inheritance contract; §1.2 Signal 4
  (PR 10's 8 Gate-3-LOCAL surfaces — PR 11's 4 add to make
  12 cumulative).
- **`A.5.3.2-GATE-3-FRAMING.md`** (`2f70cbf`) — gate-level
  inheritance contract PR 11 operated against; §6.1
  promotion-evaluation criteria for candidate carrier #16
  (PR 11 contributed the ≥1 final surface; ≥9 cumulative
  significantly exceeds ≥4); §10 PR sequencing (PR 11
  second; PR 12 conditional pending Gate 3 close
  evaluation); §11 Gate 3 close criteria.
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — three-fixture
  corpus PR 11 drives + PR 9 integration test infrastructure
  PR 11 imports as test-internal archaeology surfaces; §1.1
  fixture corpus; §2.2 PR 9 integration test infrastructure
  consumption surface; §2.4 authored/observed divergence
  proof case (PR 11 test 3 operationally verifies).
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — gate-arc
  synthesis precedent for PR 11 close + Gate 3 close
  same-commit convergence (Gate 2 close + PR 9 close shipped
  at the same commit); §2.1 Gate 4 comparator's two
  foundational dependencies operationally exercised at every
  PR 11 test.
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — authored expectation
  surface PR 11 traverses transitively via `drive_seed_fixture`;
  `emit_seed_expectation` inherited unchanged.
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — observation +
  dispatch-provenance surfaces PR 11 traverses transitively
  via `chat_handler` under `seed_dispatch_scope`;
  `emit_divergence_capture` + `_dispatch_context` +
  `seed_dispatch_scope` inherited unchanged.
- **`forge_bridge/corpus/_compare.py::compare_records`** —
  PR 10 interpretive-read surface PR 11 consumes at every
  test's final step.
- **`forge_bridge/corpus/_seed.py::drive_seed_fixture`** —
  PR 8 orchestration entry point PR 11 invokes per fixture.
- **`forge_bridge/console/handlers.py::chat_handler`** —
  production arbitration surface PR 11 drives via the PR 9
  patched `_invoke_chat_handler_in_process`.
- **`tests/corpus/test_pr11_recomposition_arc.py`** (PR 11
  new, 313 lines) — single new test module; 3 recomposition
  arc tests + module docstring.
- **`tests/corpus/test_pr9_fixture_integration.py::_apply_pr9_patches`**
  — test-internal archaeology surface PR 11 imports.
- **`tests/corpus/test_pr9_fixture_integration.py::_read_records`**
  — test-internal archaeology surface PR 11 imports.
- **`tests/corpus/fixtures/fix_single_survivor.py::FIXTURE`** —
  PR 11 test 1 imports as `FIX_SINGLE_SURVIVOR`.
- **`tests/corpus/fixtures/fix_multi_match.py::FIXTURE`** —
  PR 11 test 2 imports as `FIX_MULTI_MATCH`.
- **`tests/corpus/fixtures/fix_no_keyword_match.py::FIXTURE`** —
  PR 11 test 3 imports as `FIX_NO_KW_MATCH`.
- **PR 11 4-commit chain** (`6a5df95` → `ae69fba`) per §4
  table.
- **Local memory updates this session arc:**
  - PR-11-implementation-closed cursor written pre-synthesis
    per `feedback_cursor_before_retrospective_synthesis`.
  - MEMORY.md index updated.
  - Pushed to origin/main at the implementation-arc
    archaeology boundary (parity restored before close-
    artifact drafting).
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; PR 11 contributes
  (Gate 3 close evaluates):
  - Zero-incarnation-amendments as third instance in the
    catch-point migration progression.
  - Architectural-sufficiency-signal elevation as
    methodology contribution.
  - PR-11-LOCAL traverses-not-erases-seams as
    recomposition-asymmetry archaeology.
  - §5.3 candidate methodology observation second-instance
    ABSENCE outcome (strengthens candidacy per asymmetric
    weighting).

---

End of PR 11 close. The implementation arc that began at
PR 11 framing (`97c3fb4`) closes here. The 4-commit chain
ships the end-to-end recomposition arc + the three integration
tests + the PR-11-LOCAL traverses-not-erases-seams discipline
+ the architectural sufficiency signal validation (0 production
source modifications across the PR) + the zero-incarnation-
amendments archaeology (the cleanest arc to date) + the §5.3
candidate methodology observation second-instance ABSENCE
outcome.

PR 11 governs by inherited active carrier #17 (recomposition
discipline; enacted at use through the DivergenceReport's
per-surface partitioning preserved end-to-end) + the Gate-3-
LOCAL governing sentence (traveled through 4 PR 11 surfaces;
12 cumulative across PR 10 + PR 11; significantly exceeds the
≥4 Gate 3 close evaluation threshold) + the PR-11-LOCAL
binding statement (scope-local discipline; traverses seams,
does NOT erase them).

The recomposition arc operates end-to-end. The decomposition
strategy is operationally validated. Gate 3 close — sibling
artifact at this same commit — performs the gate-arc synthesis
across PR 10 + PR 11, the candidate carrier #16 promotion
evaluation, the conditional PR 12 disposition, the cross-PR
methodology promotion candidacies, and the gate-level
inheritance contract toward Gate 4.

**Gate 3 advances. Gate 4 inherits a validated comparator + a
corroborated recomposition demonstration + an
architecturally-sufficient decomposition strategy.**
