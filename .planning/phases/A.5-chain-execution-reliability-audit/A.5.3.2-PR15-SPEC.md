# A.5.3.2 PR 15 — Spec (multi-survivor cardinality divergence as Gate 4 calibration exercise + PR-12 trigger surface)

**Status:** Spec-stage artifact for PR 15 of Gate 4. PR 15
framing locked at `de50fea` (1964 lines); this spec derives
the implementation contract by finalizing the symbol-level
decisions named in the framing's six binding decisions
(§5.1, §5.2, §5.3, §5.4, §5.10, §5.12) — fixture filename +
symbol export name + `fixture_id` + prompt selection +
authored expectation element list (singleton subset of
observation) + test module filename + test function name +
assertion contract + PR-12 trigger surface evaluation
responsibility encoding. All decisions inherit ground from
PR 9 multi-match arbitration trace at
`fix_multi_match.py:105-140` + `_PR9_REACHABLE_TOOLS`
declared order at `test_pr9_fixture_integration.py:208-213`
+ comparator's direct list-equality at `_compare.py:503`.

PR 15 is the third + final of three primary PRs sequenced
within Gate 4 per Gate 4 framing §5.5 + §5.6 + §10. **PR 15
close pairs at same-commit with Gate 4 close** per Gate 4
framing §11.8 + PR 14 framing §11 inheritance + PR 14 close
§7 deferral. This is the **DIFFERENT close cadence from
PR 13 + PR 14 standalone closes** — the same-commit-pairing
handles the gate-arc synthesis responsibility cleanly: PR 15
close owns PR-15-scoped archaeology; Gate 4 close owns gate-
arc synthesis; the two artifacts ship at one commit. The
same-commit-pairing pattern was established at Gate 2 close
(`a6e42f0`) + Gate 3 close (`ee2225b`); PR 15 close + Gate 4
close pairing is the third operational instance.

This spec's job: derive file-level precision from framing's
locked decisions. Two new files at PR 15:
`tests/corpus/fixtures/fix_multi_survivor_mismatch.py` (new
fixture) + `tests/corpus/test_pr15_multi_survivor_mismatch.py`
(new test module containing exactly one named test). The
spec's outputs are mergeability anchors — file paths,
function names, test names, assertion contracts, exact
docstring shape, exact commit-body sections — that PR 15
close §6 + Gate 4 close §x will verify against.

**Gate 4 architectural commitment (travels at this spec body
+ all PR 15 commit message bodies under "architectural
commitment" sections + Gate 4 close architectural-commitment
section; deliberately NOT in fixture/test docstrings per
Gate 4 framing §2.4 binding + PR 15 framing §3.6 + §5.6):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Seventeen active carriers** travel into PR 15's surface
(same set Gate 4 framing locked at §3.1 + PR 13 spec §0 +
PR 14 spec §0 + PR 15 framing §3.1; no new carriers
introduced at PR 15 per Gate 4 framing §3.1 + §6.1 + §7
item 13 + PR 15 framing §3.1 + §7 item 1). Composition
unchanged: 15 inherited carriers (#1–#15) + carrier #16
(active, promoted at Gate 3 close §1.6 — *"Reliability work
proves topology, not infrastructure"*) + carrier #17 (active
from Gate 3 framing §5.1 — recomposition discipline).

**Reference discipline (binding per Gate 4 framing §3.1 +
PR 15 framing §3.1):** *"17 active carriers"* is canonical
phrasing post-Gate-3-close-promotion. PR 15 surfaces travel
carriers in natural numeric ordering WITHOUT substrate
marking. The candidate-substrate marking discipline retired
at Gate 3 close.

### Carrier travel form at PR 15 module docstrings — citation by reference

PR 15 spec interprets the framing §3.1 "17 carriers travel
verbatim" discipline as **verbatim citation to canonical
sources** (mirroring PR 11 spec §0 + PR 13 spec §0 + PR 14
spec §0 interpretation; per DRY + canonical-source
discipline). The 17 carriers + Gate 2 binding framing
clarification + inherited PR-LOCAL bindings travel by
reference to:

- `forge_bridge/corpus/_capture.py:6-135` — carriers #1–#14
  + Gate 2 binding framing clarification on call-site-owned
  arbitration inputs.
- `forge_bridge/corpus/_seed.py:19-135` — carrier #15 +
  PR-8-LOCAL bindings (member #7 truth-partitioning,
  member #8 semantics-not-topology).
- `forge_bridge/corpus/_compare.py` module docstring +
  `compare_records` function docstring — carrier #17 +
  PR-10-LOCAL read-only mutability invariant + PR 10 §4.2
  binding behavioral commitment ("compare as persisted") +
  cross-surface unbinding clarification + proactive scope
  guardrail.
- `A.5.3.2-GATE-3-CLOSE.md` §1.6 — carrier #16 promotion
  ("Reliability work proves topology, not infrastructure").

This interpretation choice continues the PR 11 + PR 13 +
PR 14 citation-by-reference precedent. PR 15 adopts the
lower-DRY form unchanged.

### Verbatim travel — PR-15-LOCAL binding statement

The **PR-15-LOCAL binding statement** travels verbatim at:

1. `tests/corpus/test_pr15_multi_survivor_mismatch.py`
   module docstring (Step 1 surface).
2. `tests/corpus/fixtures/fix_multi_survivor_mismatch.py`
   module docstring (Step 1 surface).
3. All PR 15 commit message bodies under "preserved
   invariants" / "PR-15-LOCAL" sections.
4. This spec §0 + §1 + §2 (verbatim form below).

**PR-15-LOCAL binding statement (verbatim — pure-isolation
discipline):**

> **PR 15 isolates multi-survivor cardinality divergence as
> the sole pressure vector. Multi-vector fixture pressure
> within PR 15 scope — combining cardinality with ordering,
> semantic-normalization, duplicate-handling, partial-set
> (within shared cardinality), or any other divergence form
> — is rejected at the spec layer. The pure-isolation
> property is what gives PR 15 its laboratory-grade
> methodology corroboration value for Placement A +
> Placement B substrate.**

**PR-13-LOCAL + PR-14-LOCAL as predecessor references
(binding per PR 15 framing §3.10 + §5.5):** PR-15-LOCAL
references BOTH PR-13-LOCAL (PR-of-origin for pure-isolation
discipline pattern per PR 13 close §2.2) AND PR-14-LOCAL
(parallel-not-regenerative scope-local at second calibration
point per PR 14 close §1.4 + §2.2). The references are
structural — PR-15-LOCAL is **the third parallel scope-local
discipline** + **the second corroboration of the parallel-
not-regenerative pattern PR 14 introduced**. PR-13-LOCAL and
PR-14-LOCAL do NOT travel to PR 15 surfaces directly; the
pattern (single-vector fixture pressure as laboratory-grade
calibration substrate) inherits as architectural-substrate
evidence; the specific PR-N-LOCAL statements are non-
regenerating scope-local bindings.

### Verbatim travel — §2.4 Gate 4 architectural commitment

The **§2.4 Gate 4 architectural commitment** travels
verbatim at (per Gate 4 framing §2.4 binding + PR 15 framing
§3.6 + §5.6):

1. This spec §0 (above the line) + §1 + §2 architectural
   commitment section.
2. All three PR 15 step commit message bodies under
   "architectural commitment" sections.
3. PR 15 close artifact §1 + §6.5 (or equivalent
   architectural-commitment + architectural-sufficiency
   sections).
4. **Gate 4 close artifact** (same-commit-paired with PR 15
   close per framing §9.12 + §2.4 + Gate 4 framing §11.8) —
   Gate 4 close carries §2.4 architectural commitment at its
   own architectural-commitment section (gate-arc-synthesis
   surface). **This +1 surface is the close-cadence-
   asymmetry artifact** vs. PR 13 + PR 14 standalone closes
   (PR 13 + PR 14 close-time §2.4 inventories were 8
   surfaces; PR 15 close-time §2.4 inventory is 9 surfaces).

**Travel deliberately stops short of fixture/test
docstrings.** The §2.4 sentence is gate-shaped architectural
posture, NOT carrier-shaped governance. Carriers travel
through fixture/test docstrings; the §2.4 commitment does
not. The asymmetry preserves the carrier / governing
sentence / methodology-stack category integrity Gate 4
framing established + PR 13 close §1.5 + PR 14 close §1.5
operationally verified.

**§2.4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

### Spec-drafting-time grounding catch — outcome

Per Gate 3 close §1.8 + PR 13 close §1.8 + PR 14 close §1.8
+ PR 15 framing §3.9 inheritance, the catch-point-migration
candidate methodology accumulated five descriptive instances
+ multiple catch-shape continuations by PR 14 close
landing. Progression entering PR 15 spec drafting:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration (fixture-cardinality grounding) |
| 5 (continuation) | PR 14 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #4 (four file-grounding catches) |
| 5 (continuation) | PR 14 spec | Spec-drafting-time pre-spec-lock | Catch-shape continuation of instance #5 (one line-number-citation grounding catch) |
| 5 (continuation) | PR 14 implementation | Step 3 final verification | Catch-shape continuation of instance #3 (zero amendments — clean propagation) |
| 5 (continuation) | PR 15 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #3 (zero amendments — clean propagation; recorded at framing landing absence of §0 catch section) |

**PR 15 spec-drafting-time outcome (this drafting session):**
**zero grounding catches surfaced pre-spec-lock.** The
spec-drafting session performed file-grounding checks
against four sources:

1. `fix_multi_match.py:126` — observation list-literal
   source line. Verified: line 126 carries
   `"forge_list_projects", "flame_list_libraries"]` as the
   list-literal completion (line 125 opens with
   `narrower_decision = [`). PR 14 spec's `:127`/`:128` →
   `:126` correction inherited cleanly at PR 15 spec
   drafting; no re-correction needed.
2. `test_pr9_fixture_integration.py:208-213` —
   `_PR9_REACHABLE_TOOLS` declared order. Verified: the
   constant declaration spans lines 208–213 with
   `forge_ping` at index 0, `forge_list_projects` at
   index 1, `flame_list_libraries` at index 2,
   `flame_render_status` at index 3.
3. `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
   line count (207 lines) — PR 14 fixture structural shape
   reference. Verified.
4. `tests/corpus/test_pr13_ordering_divergence.py:150-203`
   + `tests/corpus/test_pr14_partial_narrow_divergence.py:172-226`
   — 9-step traversal annotation pattern source lines.
   Verified: both files carry the six header comments
   (Step 1, Steps 2–5, Step 6, Step 7, Step 8, Step 9) at
   identical pattern at the canonical line ranges.

**This is catch-shape continuation of instance #3** (PR 11
framing-spec drafting time zero-amendment clean propagation;
+ PR 14 implementation-time zero-amendment continuation),
NOT inflation into a new methodology instance #6. Per the
recursive-self-governance discipline (PR 13 close §1.8
precedent + PR 14 close §1.8 three-fold operational
continuation): zero-amendment outcomes accumulate as catch-
shape continuations of instance #3, not as new descriptive
instances. The progression remains **five-instance
descriptive at PR 15 spec landing** with multiple catch-
shape continuations under instances #3, #4, #5.

Progression as of PR 15 spec landing:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration (fixture-cardinality grounding) |
| 5 (cont) | PR 14 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #4 (four catches) |
| 5 (cont) | PR 14 spec | Spec-drafting-time pre-spec-lock | Catch-shape continuation of instance #5 (one line-number-citation catch) |
| 3 (cont) | PR 14 implementation | Step 3 final verification | Catch-shape continuation of instance #3 (zero amendments) |
| 3 (cont) | PR 15 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #3 (zero amendments) |
| 3 (cont) | PR 15 spec | Spec-drafting-time pre-spec-lock | **Catch-shape continuation of instance #3 (this drafting; zero grounding catches surfaced)** |

The two-fold accumulation under instance #3 (PR 14
implementation + PR 15 framing) extends to three-fold at
PR 15 spec drafting. The recursive-self-governance
discipline operates symmetrically across the methodology
stack: zero-amendment outcomes register as catch-shape
continuations of instance #3, not as separately counted
instances.

PR 15 close §1 records the spec-drafting-time outcome as
contributing instance toward Gate 4 close's catch-point
migration evaluation per Gate 4 framing §11.5.

---

## 1. Real job (PR 15 in one paragraph)

PR 15 ships **two new files** containing **exactly one named
test** that exercises a multi-survivor cardinality divergence
pure-isolation case through the full end-to-end recomposition
arc:

```
fixture (fix_multi_survivor_mismatch.py)
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
subset** (Direction A INVERSE per framing §5.10): a singleton
list containing the observation's position 0 element verbatim
(`["forge_list_projects"]`). The comparator's compare-as-
persisted discipline (PR 10 §4.2 binding behavioral
commitment) detects the multi-survivor cardinality divergence
at direct list-equality (`obs_decision != exp_narrow` per
`_compare.py:503`) via length asymmetry (1 vs 2) + element-
membership asymmetry at the non-shared position. No sort /
canonicalization / semantic coercion / cardinality-aware
computation at any traversal seam. The test asserts the
four-key `DivergenceReport` structural shape with explicit
per-surface partitioning (carrier #17 at use) +
`narrow_diverged=True`.

**Direction A INVERSE is an affirmative architectural
decision** (framing §5.10) — the inverse of PR 14's
authored-superset direction. The two-PR direction-symmetric
pair (PR 14: authored ⊃ observed with length asymmetry 3
vs 2; PR 15: authored ⊂ observed with length asymmetry 1
vs 2) operationally corroborates the comparator's compare-as-
persisted discipline operates direction-symmetrically. This
is the **second corroboration of the framing-level direction-
selection rationale pattern** PR 14 §5.10 introduced.

**Gate 4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**Regression contracts at PR 15 close (10 items):**

1. PR 15 suite (`test_pr15_multi_survivor_mismatch.py`):
   1/1 passed.
2. PR 4 + PR 5 + PR 6 + PR 7 + PR 8 + PR 9 + PR 10 + PR 11
   + PR 13 + PR 14 suites pass unchanged.
3. PR 3 discipline passes unchanged (no `_ALLOWLIST`
   modification per §8.1).
4. Four Layer 2 walkers (PR 4 + PR 8 + PR 9 + PR 10) pass
   unchanged.
5. Layer 3 lint (`test_pr6_visual_asymmetry.py`) passes
   unchanged.
6. Full corpus suite: **220 forge env collected** (219
   baseline + 1 PR 15 new).
7. Console tests + Public API anchor (`forge_bridge.__all__`
   at 19 symbols) unchanged.
8. Verbatim carrier travel: 17 carriers cited by reference +
   PR-15-LOCAL verbatim at both PR 15 module docstrings +
   PR 15 commit message bodies.
9. §2.4 Gate 4 architectural commitment travels verbatim at
   this spec §0 + §1 + §2 + all 3 PR 15 step commit message
   bodies under "architectural commitment" sections + PR 15
   close artifact + Gate 4 close artifact (NOT at
   fixture/test docstrings). **9-surface inventory** at PR 15
   close (extended by 1 vs. PR 13 + PR 14 close-time 8-
   surface inventory; the +1 surface is Gate 4 close's
   architectural-commitment section).
10. **Architectural sufficiency signal: 0 production source
    modifications across PR 15's commit chain. Six-PR
    cumulative escalation (PR 9 + PR 10 + PR 11 + PR 13 +
    PR 14 + PR 15) if 0-prod-mod target holds.**

---

## 2. In-scope / out-of-scope

### In scope (PR 15)

- New file:
  `tests/corpus/fixtures/fix_multi_survivor_mismatch.py`
  containing module docstring (carrying PR-15-LOCAL + 17
  carriers by reference + grounded arbitration trace +
  fixture purpose with Direction A INVERSE rationale) +
  `from __future__ import annotations` + `FIXTURE` dict
  with three keys (`fixture_id`, `prompt`,
  `expected_narrow`).
- New file:
  `tests/corpus/test_pr15_multi_survivor_mismatch.py`
  containing module docstring (carrying PR-15-LOCAL + 17
  carriers by reference + traversal trace + test
  infrastructure import discipline) + imports + 1 named
  test (`test_recomposition_arc_multi_survivor_mismatch`).
- IMPORT of PR 9 test infrastructure (`_apply_pr9_patches`,
  `_read_records`) from
  `tests.corpus.test_pr9_fixture_integration` as
  **test-internal archaeology surfaces** (not public APIs;
  inherited from PR 11 + PR 13 + PR 14 pattern).
- PR 15 commit message bodies carrying "architectural
  commitment" + "preserved invariants" + "PR-15-LOCAL" +
  "Placement A/B substrate contribution" sections per the
  PR 13 + PR 14 commit-body pattern adapted for PR 15 scope.
- **PR-12 trigger surface evaluation inputs** registered at
  PR 15 close §1 (per framing §5.12): actual join call-site
  count contribution + qualitative second-clause pressure
  observation. Gate 4 close §x consumes the inputs for
  final PR-12 disposition decision.
- **PR 15 close paired at same-commit with Gate 4 close**
  per framing §9.12 + §2.4 + Gate 4 framing §11.8.

**Gate 4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**PR-15-LOCAL binding statement (verbatim per §0 + framing
§5.5):**

> **PR 15 isolates multi-survivor cardinality divergence as
> the sole pressure vector. Multi-vector fixture pressure
> within PR 15 scope — combining cardinality with ordering,
> semantic-normalization, duplicate-handling, partial-set
> (within shared cardinality), or any other divergence form
> — is rejected at the spec layer. The pure-isolation
> property is what gives PR 15 its laboratory-grade
> methodology corroboration value for Placement A +
> Placement B substrate.**

### Out of scope (architecturally-prohibited at PR 15)

PR 15 inherits the framing §7 24-item non-acquisition list
in full + adds spec-layer enforcement:

1. **Any production source file modification.** Framing
   §5.3 binding decision; framing §7 item 10. Justified
   deviations register as archaeology at PR 15 close per
   framing §5.11 justified-deviation protocol, not silent
   additions.
2. **Authoring multi-vector fixture pressure.** Framing
   §5.1 + §5.5 PR-15-LOCAL binding; framing §7 items 6 +
   24 (multi-vector + combined-divergence rejections). The
   fixture isolates multi-survivor cardinality divergence
   as the sole pressure vector.
3. **Authoring the symmetric-direction (Direction B,
   authored ⊃ observed) variant** at spec layer. Framing
   §4.4 + §5.10 + §7 item 17 + §7 item 18 (no Direction B
   authoring; no fixture authored expectation regeneration
   of PR 14's direction). Direction A INVERSE (authored ⊂
   observed) locked at framing per §5.10 affirmative
   architectural decision.
4. **Modifying the comparator surface**
   (`compare_records` / `DivergenceReport` /
   `ComparatorInputError`). Framing §5.7 binding + §7
   item 3 + Gate 3 close §3 item 2.
5. **Adding a `cardinality_class` (or `survivor_count`,
   `singleton_side`, `multi_survivor_side`,
   `divergence_kind`) field to `DivergenceReport`.** Framing
   §5.4 predicted-form 1 + §5.7 + §7 item 12 (declared-
   classification field extension rejection). The comparator
   surface preserves at PR 10 spec §4.1.6 reference
   implementation.
6. **Adding "while we're here" elements** (ordering /
   duplicate handling / semantic normalization to the
   multi-survivor fixture). Framing §5.4 three "while we're
   here" pressure forms explicitly enumerated + §5.5
   PR-15-LOCAL + §7 items 6 + 24 (rejecting "while we're
   here" pressure forms).
7. **Modifying existing PR 9 fixtures, PR 13 fixture, or
   PR 14 fixture.** Framing §7 item 22 (test-internal
   archaeology surface non-modification) + spec §3 NOT
   MODIFIED rows. PR 9 + PR 13 + PR 14 fixtures are stable
   archaeology; PR 15 inherits, does not modify.
8. **Re-authoring `_apply_pr9_patches` or `_read_records`**
   with modified semantics. Framing §7 item 22.
9. **Promoting PR 9 underscored helpers to public APIs.**
   Framing §7 item 22 + Gate 3 close §3 item 10.
10. **Introducing a test-helper function** that absorbs the
    recomposition traversal. Framing §5.4 predicted-form 3
    suppression at use; framing §7 item 14 (no
    recomposition-arc helper extraction). PR 15 test body
    inlines the 9-step traversal annotation pattern.
11. **Introducing a join-helper** (`join_records_by_fixture_id`,
    `filter_records_by_fixture_id` + `partition_by_record_kind`,
    or any other helper that absorbs the explicit filter +
    partition decomposition seam). Framing §5.4 predicted-
    form 2 + §7 item 13 (no join-helper extraction at
    PR 15; PR 12 conditional disposition deferred to Gate 4
    close). The PR-12 trigger surface evaluation responsibility
    is encoded at PR 15 close §1 inventory per framing §5.12,
    NOT pre-bound at PR 15 spec drafting.
12. **Asserting `narrow_diverged=True` only** without
    asserting the structural list values. Framing §5.4
    predicted-form 1 + §9.4 close-time verification.
    Cardinality-class-divergence-to-narrow-diverged-only
    collapse pressure rejected. The structural-shape
    preservation IS the cardinality-class disclosure.
13. **Using set-equality assertion shortcuts** (e.g.,
    `assert set(observed) == set(expected)`) in PR 15 test
    body. Framing §5.4 predicted-form 1 suppression at use.
    The four-key DivergenceReport assertion contract
    preserves the structural shape (length + ordering +
    membership at full fidelity).
14. **Adding a fourth structural field to the expectation
    record schema** (e.g., `expected_cardinality_class`,
    `expected_subset_of_observation`). Framing §5.4
    predicted-form 1 second variant + §7 item 11 (no
    declared-intent FIXTURE schema extension) + Gate 2
    close §2.4 item 5 inheritance. FIXTURE schema preserves
    at exactly three required keys.
15. **Introducing a new `record_kind`.** Framing §7 item 2
    (2-element observation/expectation lock) + Gate 2 close
    §2.4 inheritance.
16. **Extending `KNOWN_SOURCE_VALUES`** or
    `_KNOWN_RECORD_KINDS`. Framing §7 items inherited from
    Gate 2 close §2.4 items 3 + 4 + cleanup-pressure-
    resistance class member #1.
17. **Modifying the three-authority-surface partition.**
    Framing §3.2 + Gate 4 framing §3.2 + Gate 3 close §1.3
    inheritance + cleanup-pressure-resistance class member
    #3.
18. **Authoring a fifth walker.** Framing §8.2 + Gate 3
    close §1.4 + Gate 4 framing §3.3 inheritance.
19. **Adding cleanup-pressure-resistance class members
    speculatively** at framing/spec time. Framing §3.7 +
    §9.10. Class members surface at PR 15 close based on
    actual implementation pressure encountered.
20. **Introducing a candidate carrier (#18)** at PR 15.
    Framing §7 item 1.
21. **Speculatively authoring a Gate-4-LOCAL governing
    sentence.** Framing §0 + §7 item 16 + Gate 4 framing §7
    item 22 inheritance.
22. **Pre-binding Placement A outcome predictions** at
    framing/spec. Framing §6.1 + §9.4. Outcomes register
    at PR 15 close based on actual encountered pressure.
23. **Pre-binding PR 12 disposition** at PR 15
    framing/spec. Framing §7 item 19 (no premature PR-12
    disposition finalization) + §5.12 (PR 15 close ships
    evaluation inputs; Gate 4 close ships final
    disposition).
24. **Touching the Layer 3 lint**
    (`test_pr6_visual_asymmetry.py`). §8.3 explicit.
25. **Modifying `divergence_capture_enabled()` or its
    env-gate.** Inherited from PR 13 spec §2 item 24 +
    PR 14 spec §2 item 25.
26. **Speculative-reserved imports.** Per cleanup-pressure-
    resistance class member #10; imports land when first
    used at Step 2 implementation (spec §4.2.2 + §6.2).
27. **Cross-surface vocabulary in test names or
    docstrings.** Per framing §5.4 predicted-form 1
    suppression + PR 13 spec §2 item 27 + PR 14 spec §2
    item 27 inheritance. No `task_outcome` /
    `prompt_resolution` field names; no `cardinality_class`
    / `survivor_count` / `singleton_marker` field names.
28. **`forge_bridge.__all__` modification.** Framing §5.8
    binding + §7 item 4 (implicit). Stays at 19 symbols.
29. **Layer 1 `_ALLOWLIST` modification.** §8.1 explicit;
    corpus-subtree auto-exclusion semantics inherited from
    PR 10 §4.4.
30. **Layer 2 walker addition.** §8.2 explicit; no fifth
    walker.
31. **Surfacing the four §7.3 ontological questions.**
    Framing inherits via Gate 4 framing §5.2 + Gate 2 close
    inheritance. The four §7.3 questions remain
    intentionally unbound.
32. **Cross-surface comparator semantics introduction.**
    Framing inherits via Gate 3 framing binding clarification
    on cross-surface unbinding + PR 13 framing §7 item 22
    + PR 14 spec §2 item 32.
33. **Modifying prompt selection.** Framing §4.6 + §5.10
    direction-symmetric rationale. Prompt `"list"` locked
    per single-variable-discipline preservation across
    PR 9 / PR 13 / PR 14 / PR 15.
34. **Modifying authored expectation element selection.**
    Framing §4.1 + §5.1 + §5.10. Authored expectation
    locked at one element: `forge_list_projects` (PR 9
    multi-match observation position 0 verbatim).
35. **Introducing a multi-token prompt** or modifying
    `_PR9_REACHABLE_TOOLS` to enable Direction B variant.
    Framing §5.10 + §7 items 17 + 18. Both rejected at
    affirmative-architectural-decision layer.
36. **Same-commit-pairing PR 15 close with PR 13 close or
    PR 14 close.** PR 13 + PR 14 closes shipped STANDALONE;
    framing §7 item 20 + §9.12 + §2.4. PR 15 close pairs
    at same-commit with **Gate 4 close** (not PR 13/PR 14
    close).
37. **Silent re-ordering of three-PR sequence.** Framing
    §7 item 23 (PR 13 → PR 14 → PR 15 ordering locked at
    Gate 4 framing §5.6).
38. **`clean_rate_limit_state` fixture modification.**
    Framing §7 item 21 (consumed unchanged from conftest.py).
39. **Pre-binding PR-12 join-helper extraction at PR 15.**
    Framing §5.4 predicted-form 2 + §5.12 + §7 items 13 +
    19. PR-12 trigger surface evaluation inputs registered
    at PR 15 close §1 inventory; final PR-12 disposition
    is Gate 4 close §x scope, NOT PR 15 scope.

---

## 3. Files modified / created at PR 15

| File | Disposition | Lines (final at PR 15 close) |
|---|---|---|
| `tests/corpus/fixtures/fix_multi_survivor_mismatch.py` | **NEW** | ~90–115 |
| `tests/corpus/test_pr15_multi_survivor_mismatch.py` | **NEW** | ~125–160 |
| `forge_bridge/**` | NOT MODIFIED (architectural sufficiency signal target) | 0 |
| `tests/corpus/test_pr3_discipline.py` | NOT MODIFIED (corpus-subtree auto-exclusion) | 0 |
| `tests/corpus/test_pr4_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr6_visual_asymmetry.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr7_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr8_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr9_fixture_integration.py` | NOT MODIFIED (imported FROM as test-internal archaeology surface) | 0 |
| `tests/corpus/test_pr9_fixture_discipline.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr10_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr11_recomposition_arc.py` | NOT MODIFIED (consumption pattern inherited; not imported FROM) | 0 |
| `tests/corpus/test_pr13_ordering_divergence.py` | NOT MODIFIED (PR 13 calibration substrate stable archaeology; not imported FROM) | 0 |
| `tests/corpus/test_pr14_partial_narrow_divergence.py` | NOT MODIFIED (PR 14 calibration substrate stable archaeology; not imported FROM) | 0 |
| `tests/corpus/fixtures/fix_*.py` (PR 9 + PR 13 + PR 14 fixtures) | NOT MODIFIED (stable archaeology) | 0 |
| `tests/corpus/conftest.py` | NOT MODIFIED | 0 |

**Two new files. Zero modifications to any production source
or existing test/fixture file.** The 0-prod-mod-outside-the-
new-test-and-fixture-files outcome IS the architectural
sufficiency signal PR 15 demonstrates (framing §5.3 + §9.3).

PR 15 extends the five-PR architectural sufficiency
escalation (PR 9 + PR 10 + PR 11 + PR 13 + PR 14) to
**six-PR escalation** if the 0-prod-mod target holds at
PR 15 close (per PR 15 framing §5.3 + §9.3 + PR 14 close
§1.3 inheritance).

---

## 4. Per-file derivation

### 4.1 `tests/corpus/fixtures/fix_multi_survivor_mismatch.py` — new fixture

#### 4.1.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering — most
load-bearing at TOP per PR 8 spec §0 travel rule + PR 13
spec §4.1.1 + PR 14 spec §4.1.1 + PR 15 framing §3.1):

1. **One-line summary**: `"""Seed fixture — multi-survivor cardinality divergence pure-isolation case at the chat-handler observation surface."""`
2. **Blank line.**
3. **PR-15-LOCAL binding statement** (verbatim, per §0 + framing §5.5):

   > PR 15 isolates multi-survivor cardinality divergence
   > as the sole pressure vector. Multi-vector fixture
   > pressure within PR 15 scope — combining cardinality
   > with ordering, semantic-normalization, duplicate-
   > handling, partial-set (within shared cardinality), or
   > any other divergence form — is rejected at the spec
   > layer. The pure-isolation property is what gives PR 15
   > its laboratory-grade methodology corroboration value
   > for Placement A + Placement B substrate.

4. **Blank line.**
5. **Carrier travel — citation by reference paragraph** (per §0):

   > 17 active carriers + Gate 2 binding framing
   > clarification + inherited PR-LOCAL bindings travel by
   > reference to canonical sources:
   >
   > - ``forge_bridge/corpus/_capture.py:6-135`` — carriers
   >   #1–#14 + Gate 2 binding framing clarification on
   >   call-site-owned arbitration inputs.
   > - ``forge_bridge/corpus/_seed.py:19-135`` — carrier #15 +
   >   PR-8-LOCAL bindings (member #7 truth-partitioning,
   >   member #8 semantics-not-topology).
   > - ``forge_bridge/corpus/_compare.py`` module docstring +
   >   ``compare_records`` function docstring — carrier #17 +
   >   PR-10-LOCAL read-only mutability invariant + PR 10 §4.2
   >   binding behavioral commitment ("compare as persisted") +
   >   cross-surface unbinding clarification + proactive scope
   >   guardrail.
   > - ``A.5.3.2-GATE-3-CLOSE.md`` §1.6 — carrier #16
   >   ("Reliability work proves topology, not infrastructure").

6. **Blank line.**
7. **Fixture purpose** section (grounded arbitration trace
   per PR 9 fixture precedent at `fix_multi_match.py:105-140`
   + PR 13 fixture precedent at
   `fix_ordering_divergence.py` + PR 14 fixture precedent
   at `fix_partial_narrow_divergence.py`):

   ```
   Fixture purpose:

   This fixture exercises the chat-handler-surface multi-
   survivor cardinality divergence pure-isolation case. The
   prompt ``"list"`` (single-step shape; does NOT fire
   chain-step arbitration) is identical to PR 9 multi-
   match's prompt (``fix_multi_match.py``), PR 13 ordering-
   divergence's prompt (``fix_ordering_divergence.py``),
   and PR 14 partial-set-divergence's prompt
   (``fix_partial_narrow_divergence.py``); the arbitration
   trace through PR14 + PR21 is grounded at
   fix_multi_match.py:105-140.

   PR14 keyword filter yields 2 candidates against the PR 9
   controlled reachable-tool set (4 tools; see
   ``test_pr9_fixture_integration.py:208-213``):

     - ``forge_list_projects`` (token "list" matches)
     - ``flame_list_libraries`` (token "list" matches)

   Both are other-match (single-token overlap; PR14 input
   order from ``_PR9_REACHABLE_TOOLS`` declared order
   preserved through the filter).

   PR21 deterministic_narrow cannot collapse: both tools tie
   at max-overlap=1 ("list"); no domain-priority pair fires
   (the closed list ``(("version", "project"),)`` does not
   include "list"); Rule 3 raw-token tie-breaker finds no
   asymmetry — both tools have identical raw-token overlap
   with the message. Survivor set is unchanged.

   Observation record (deterministic per PR 9 multi-match
   arbitration trace; identical to PR 13 ordering-divergence's
   observation + PR 14 partial-set-divergence's observation):

     narrower.decision = ["forge_list_projects",
                          "flame_list_libraries"]

   (verbatim PR14 input order through PR21;
   ``_PR9_REACHABLE_TOOLS`` declared ordering at
   ``test_pr9_fixture_integration.py:208-213``.)

   Expectation record (PR 15 fixture-author choice — the
   authored-subset multi-survivor cardinality divergence
   vector, Direction A INVERSE per A.5.3.2-PR15-FRAMING.md
   §5.10):

     expected_narrow = ["forge_list_projects"]

   (single element matching observation position 0 verbatim;
   length 1 vs. observation length 2; cardinality classes
   singleton vs. multi-survivor. The author asserts: "I
   expected only this one tool to survive narrowing;
   arbitration's ambiguity is unexpected.")

   The authored-subset direction is an affirmative
   architectural decision per framing §5.10 — the
   architectural pressure vector under test is cardinality-
   class preservation, not directional ownership of the
   cardinality-class asymmetry. The temptation toward
   cardinality-aware DivergenceReport fields (predicted
   form 1 at framing §5.4) operates symmetrically regardless
   of which side contains the multi-survivor cardinality;
   Direction A INVERSE is selected for three reasons:

     (1) Direction-symmetric corroboration with PR 14 —
         PR 14 exercised authored ⊃ observed (superset
         relation; partial-set divergence). Direction A
         INVERSE at PR 15 inverts to authored ⊂ observed
         (subset relation; multi-survivor cardinality
         divergence). The two-PR pair (PR 14 + PR 15)
         operationally corroborates the comparator's
         compare-as-persisted discipline operates
         direction-symmetrically.

     (2) Single-variable discipline preservation across
         PR 9 / PR 13 / PR 14 / PR 15 — Direction A INVERSE
         reuses PR 9 multi-match's deterministic arbitration
         output verbatim (same prompt + same reachable-tool
         set + same arbitration trace + same observation).
         The comparator surface becomes the only moving
         interpretive layer across the four-PR series.

     (3) Semantically legible authorial claim — the author
         asserts "I expected only this one tool to survive
         narrowing; arbitration's ambiguity is unexpected,"
         a visibly interpretive cardinality-class prediction
         orthogonal to the multi-survivor arbitration
         outcome. This is the typical authorial direction
         (predict clean outcome → encounter ambiguity), the
         inverse of which (predict ambiguity → encounter
         clean outcome) would be Direction B.

   The pure-isolation property holds at every dimension
   except the target multi-survivor cardinality vector:

     - Shared element at observation position 0:
       ``forge_list_projects`` appears at both authored
       position 0 and observed position 0 (no ordering
       confound).
     - Cardinality-class asymmetry IS the divergence vector:
       authored length 1 (singleton) vs. observation length 2
       (multi-survivor). The cardinality-class shape
       (singleton vs. multi-survivor) is what the comparator
       preserves structurally.
     - No semantic-normalization divergence: tool names are
       exact-match identifiers; no canonical-form
       transformations involved.
     - No duplicate-handling divergence: each list contains
       distinct elements.
     - No partial-set-within-shared-cardinality confound:
       the shared cardinality is 1 at the intersection (one
       shared element verbatim); no partial-set vector
       operating WITHIN a shared cardinality class. The
       partial-set-within-shared-cardinality form is PR 14's
       substrate (different shared cardinality with
       additional element); PR 15's substrate is direct
       cardinality-class asymmetry.

   The comparator's compare-as-persisted discipline (PR 10
   §4.2 binding behavioral commitment) detects the multi-
   survivor cardinality divergence as ``narrow_diverged=True``
   per direct list-equality at ``_compare.py:503``
   (``obs_decision != exp_narrow``; length asymmetry (1 vs 2)
   + element-membership asymmetry at the non-shared position
   both contribute to the inequality; no sort, no
   canonicalization, no semantic coercion, no cardinality-
   aware computation at any traversal seam).

   This fixture differs from PR 9 multi-match
   (``fix_multi_match.py``), PR 13 ordering-divergence
   (``fix_ordering_divergence.py``), and PR 14 partial-set-
   divergence (``fix_partial_narrow_divergence.py``) at
   exactly one surface: the authored expectation. PR 9
   multi-match authors ``expected_narrow`` matching
   observation verbatim (no-divergence baseline). PR 13
   authors the ordering swap (same set, different sequence,
   same cardinality). PR 14 authors the authored-superset
   extension (same elements at positions 0+1, additional
   element at position 2; +1 cardinality). PR 15 authors
   the authored-subset shrinkage (singleton element matching
   observation position 0 verbatim; -1 cardinality). The
   single-variable discipline across PR 9 / PR 13 / PR 14 /
   PR 15 is itself architectural-substrate evidence — the
   comparator surface is the only moving interpretive layer
   across the four-PR series (framing §4.6).

   Prompt reuse is NOT collision — fixture identity
   discriminator is ``fixture_id``, not ``prompt``; per-test
   ``tmp_path`` corpus isolation prevents record co-existence
   between PR 9 multi-match's invocation, PR 13 ordering-
   divergence's invocation, PR 14 partial-set-divergence's
   invocation, and PR 15 multi-survivor-mismatch's
   invocation. The prompt-reuse-without-collision discipline
   is itself architectural evidence (PR 13 close §2.1 PR-of-
   origin archaeology; PR 14 close §2.1 second corroboration).
   ```

   The arbitration trace recorded above is archaeology-
   grade per
   `feedback_counts_are_archaeology_grade.md`. Future
   contributors diagnosing PR 15 regressions can verify
   against the trace recorded here + the PR 9 multi-match
   trace + the PR 13 ordering-divergence trace + the PR 14
   partial-set-divergence trace.

8. **Blank line.**
9. **References** paragraph citing:

   ```
   References:
     - A.5.3.2-PR15-SPEC.md (this fixture's implementation
       contract).
     - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
     - A.5.3.2-GATE-4-FRAMING.md (immediate gate-level
       inheritance contract).
     - A.5.3.2-PR14-CLOSE.md (PR-14-LOCAL as parallel-not-
       regenerative scope-local discipline at second
       calibration point; second calibration substrate).
     - A.5.3.2-PR13-CLOSE.md (PR-13-LOCAL as PR-of-origin
       for the pure-isolation pattern; calibration substrate
       at first calibration point).
     - tests/corpus/fixtures/fix_multi_match.py:105-140
       (PR 9 multi-match arbitration trace; PR 15 inherits
       the trace grounding).
     - tests/corpus/fixtures/fix_multi_match.py:126 (PR 9
       observation list-literal source line; PR 15's
       ``expected_narrow[0]`` (``forge_list_projects``)
       grounds against the first element on this line).
     - tests/corpus/fixtures/fix_ordering_divergence.py
       (PR 13 ordering-divergence fixture; PR 15 mirrors
       the fixture structural shape).
     - tests/corpus/fixtures/fix_partial_narrow_divergence.py
       (PR 14 partial-set-divergence fixture; PR 15 mirrors
       the fixture structural shape; authored-superset
       Direction A precedent which PR 15 inverts to
       authored-subset Direction A INVERSE).
     - tests/corpus/test_pr9_fixture_integration.py:208-213
       (_PR9_REACHABLE_TOOLS declared order; PR 15 inherits
       the reachable-tool set verbatim).
     - forge_bridge/corpus/_compare.py:503 (comparator's
       direct list-equality semantics).
   ```

10. **Blank line.**
11. **Fixture-data-discipline closing**:

    > This fixture is data + one orchestration call only —
    > no helpers, no factories, no parametrization. Per
    > cleanup-pressure-resistance class member #9 (fixture-
    > surface-data-discipline; ``A.5.3.2-PR9-FRAMING.md``
    > §6.1 + Gate 3 close §1.5).

**Total docstring: ~85–105 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent
steps.

#### 4.1.2 Module body (Step 2 contents)

```python
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr15-multi-survivor-mismatch",
    "prompt": "list",
    "expected_narrow": ["forge_list_projects"],
}
```

**Locked values (binding):**

| Key | Value | Grounding |
|---|---|---|
| `fixture_id` | `"fix-pr15-multi-survivor-mismatch"` | Framing §5.9 two-surface form; kebab-case with PR anchor |
| `prompt` | `"list"` | Framing §4.6 + §5.10 single-variable discipline preservation across PR 9 / PR 13 / PR 14 / PR 15 |
| `expected_narrow[0]` | `"forge_list_projects"` | PR 9 multi-match observation position 0 (verbatim from `fix_multi_match.py:126`; first element on the observation list-literal line per arbitration trace section) |

The single-symbol module export is `FIXTURE` (canonical name
per framing §3.3 + §5.9 + PR 9 + PR 13 + PR 14 precedent;
consuming test aliases on import).

**Symbol export form lock:** PR 15 fixture exports exactly
one module-level symbol named `FIXTURE`. No additional
constants, no helper functions, no factories. The only
module-level statement beyond the docstring + `FIXTURE`
assignment is `from __future__ import annotations` at the
head of the module body.

**`expected_narrow` list formatting:** the singleton element
is formatted on a single line (`["forge_list_projects"]`) —
the structural shape claim is "this is a singleton list,"
and single-line formatting is the canonical Python form for
single-element list literals. **No multi-line formatting**
of the singleton list (which would visually parallel PR 14's
three-element multi-line format but would mask the
singleton-cardinality structural claim).

**Cardinality-class structural-claim asymmetry vs. PR 13 +
PR 14:**

| PR | List length | Format |
|---|---|---|
| PR 13 | 2 | multi-line (one element per line) |
| PR 14 | 3 | multi-line (one element per line) |
| **PR 15** | **1 (singleton)** | **single-line** |

The format asymmetry is structural — PR 15's singleton-line
form visually encodes the singleton-cardinality structural
claim. The format choice IS the structural shape claim, not
ornamental.

#### 4.1.3 Imports discipline

Imports inventory at PR 15 close (final state):

```python
from __future__ import annotations
```

**One import only.** `from __future__ import annotations` is
the sole import at the fixture module per cleanup-pressure-
resistance class member #9 (fixture-surface-data-
discipline). No `from typing import Any` or similar — the
`FIXTURE: dict` annotation does not require it.

**Step 1 → Step 2 import transition:**

- Step 1 (skeleton): `from __future__ import annotations`
  only (the file is at skeleton state with docstring + the
  single `__future__` import).
- Step 2 (architectural-center): `FIXTURE` dict landed; no
  new imports.
- Step 3 (verification): no changes.

The single-import discipline is structural at PR 15's
fixture file — no imports land at Step 2 because the
`FIXTURE` dict only requires literal-construction syntax
(strings + list of strings + dict literal). Member #9 +
member #10 protections operate symmetrically (parallel to
PR 13 close §1.12 + PR 14 close §1.12).

### 4.2 `tests/corpus/test_pr15_multi_survivor_mismatch.py` — new test module

#### 4.2.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering):

1. **One-line summary**: `"""End-to-end multi-survivor cardinality divergence recomposition arc test — fixture → drive_seed_fixture → chat_handler → emission → readback → compare_records → DivergenceReport (narrow_diverged=True)."""`
2. **Blank line.**
3. **PR-15-LOCAL binding statement** (verbatim, per §0 + framing §5.5).
4. **Blank line.**
5. **Traversal trace** (verbatim from PR 15 framing §2.1 +
   parallel to PR 13 spec §4.2.1 site 5 + PR 14 spec
   §4.2.1 site 5):

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

   Each arrow is a decomposition seam established at Gate 2
   or Gate 3 substrate work. PR 15 traverses the seams under
   multi-survivor cardinality divergence pressure; no helper
   absorbs the arc into a single call (PR-11-LOCAL
   traverses-not-erases-seams inherited at gate level per
   A.5.3.2-GATE-3-CLOSE.md §3 item 10).

6. **Blank line.**
7. **Carrier travel — citation by reference paragraph** (per §0; same form as fixture module §4.1.1 site 5).

8. **Blank line.**
9. **Test infrastructure import discipline** paragraph (per
   PR 11 spec §4.1.1 site 11 + PR 13 spec §4.2.1 site 9 +
   PR 14 spec §4.2.1 site 9 + framing §9.11 inheritance):

   > PR 15 imports ``_apply_pr9_patches`` and ``_read_records``
   > from ``tests.corpus.test_pr9_fixture_integration`` as
   > **test-internal archaeology surfaces**, NOT as public APIs.
   > The underscored-private status is preserved — the import is
   > test-internal and archaeology-explicit, mirroring the PR 11
   > consumption pattern (``test_pr11_recomposition_arc.py:111-114``)
   > + PR 13 consumption pattern
   > (``test_pr13_ordering_divergence.py:110-113``) + PR 14
   > consumption pattern
   > (``test_pr14_partial_narrow_divergence.py``). This does
   > NOT promote the helpers to public APIs; future contributors
   > must NOT read this as a general invitation to import
   > underscored-private helpers across production modules.
   > **Third operational corroboration of the underscored-
   > private-status discipline** at PR 15.

10. **Blank line.**
11. **References** trailing paragraph citing:

    ```
    References:
      - A.5.3.2-PR15-SPEC.md (this module's implementation
        contract).
      - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
      - A.5.3.2-GATE-4-FRAMING.md (immediate gate-level
        inheritance contract; §2.4 architectural commitment).
      - A.5.3.2-PR14-CLOSE.md (PR-14-LOCAL parallel-not-
        regenerative scope-local discipline at second
        calibration point; second calibration substrate;
        Direction A authored-superset precedent which PR 15
        inverts to Direction A INVERSE authored-subset).
      - A.5.3.2-PR13-CLOSE.md (PR-13-LOCAL as PR-of-origin
        for the pure-isolation pattern; both-skeletons-at-
        Step-1 lifecycle invariant as PR-of-origin).
      - A.5.3.2-PR11-CLOSE.md (recomposition arc operational
        evidence; PR-11-LOCAL traverses-not-erases-seams
        inherited at gate level per Gate 3 close §3 item 10).
      - A.5.3.2-PR10-CLOSE.md (durable PR 10 archival state;
        PR 10 §4.2 binding behavioral commitment exercised
        under multi-survivor cardinality divergence pressure).
      - tests/corpus/test_pr14_partial_narrow_divergence.py
        (PR 14 test module; PR 15 mirrors the 9-step
        traversal annotation pattern + four-key assertion
        contract).
      - tests/corpus/test_pr13_ordering_divergence.py
        (PR 13 test module; PR 15 mirrors the 9-step
        traversal annotation pattern + four-key assertion
        contract; PR-of-origin precedent).
      - tests/corpus/test_pr11_recomposition_arc.py
        (recomposition arc consumption pattern inherited).
      - tests/corpus/fixtures/fix_multi_match.py:105-140
        (PR 9 multi-match arbitration trace inherited).
    ```

**Total docstring: ~70–90 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent
steps.

#### 4.2.2 Imports discipline (per member 10: imports land when first used)

**Step 1 imports (skeleton state):**

```python
from __future__ import annotations
```

**One import at Step 1.** `from __future__ import
annotations` is the sole import at the test module file at
skeleton state per cleanup-pressure-resistance class
member #10 (imports land when first used).

**Step 2 imports landed (final state at PR 15 close):**

```python
from __future__ import annotations

import pathlib

import pytest

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._seed import drive_seed_fixture

from tests.corpus.fixtures.fix_multi_survivor_mismatch import (
    FIXTURE as FIX_MULTI_SURVIVOR_MISMATCH,
)

# Test-internal archaeology surfaces (NOT public APIs) per
# module-docstring "Test infrastructure import discipline"
# framing + A.5.3.2-PR15-SPEC.md §4.2.1 site 9.
from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)
```

**Seven new imports land at Step 2 (per member 10 discipline
+ PR 13 spec §4.2.2 + PR 14 spec §4.2.2 precedent):**

| Symbol | Source | First-use site at test body |
|---|---|---|
| `pathlib` | stdlib | `tmp_path: pathlib.Path` parameter annotation in test signature |
| `pytest` | external | `monkeypatch: pytest.MonkeyPatch` parameter annotation in test signature |
| `compare_records` | `forge_bridge.corpus._compare` | Step 8 of traversal (comparator invocation) |
| `drive_seed_fixture` | `forge_bridge.corpus._seed` | Steps 2-5 of traversal (orchestration seam invocation) |
| `FIX_MULTI_SURVIVOR_MISMATCH` (alias for `FIXTURE`) | `tests.corpus.fixtures.fix_multi_survivor_mismatch` | Steps 2-5 of traversal (`drive_seed_fixture(**FIX_MULTI_SURVIVOR_MISMATCH)`) + Step 7 of traversal (fixture_id partition filter) + Step 9 of traversal (assertion comparison fixture_id) |
| `_apply_pr9_patches` | `tests.corpus.test_pr9_fixture_integration` | Step 1 of traversal (monkeypatch suite application) |
| `_read_records` | `tests.corpus.test_pr9_fixture_integration` | Step 6 of traversal (records readback) |

**Import grouping discipline** (per PEP 8 + PR 13 spec
§4.2.2 + PR 14 spec §4.2.2 precedent):

1. `from __future__ import` (one-line group).
2. **Blank line.**
3. Standard library imports (`pathlib`).
4. **Blank line.**
5. External libraries (`pytest`).
6. **Blank line.**
7. Internal package imports
   (`forge_bridge.corpus._compare`, `forge_bridge.corpus._seed`).
8. **Blank line.**
9. Test-package imports (the `FIX_MULTI_SURVIVOR_MISMATCH`
   alias).
10. **Blank line.**
11. Test-internal archaeology surfaces (the
    `_apply_pr9_patches` + `_read_records` imports). The
    "Test-internal archaeology surfaces (NOT public APIs)"
    comment marker precedes this import block per PR 13
    close §1.13 + PR 14 close §1.13 precedent — explicit
    underscored-private-status registration at the import
    site.

**No speculative-reserved imports.** No imports land for
"might be useful later" purposes (member #10 protection).

#### 4.2.3 The single test — `test_recomposition_arc_multi_survivor_mismatch`

**Test function signature:**

```python
def test_recomposition_arc_multi_survivor_mismatch(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
```

**Signature contract:**

- Test function name:
  `test_recomposition_arc_multi_survivor_mismatch` (locked
  per framing §5.1).
- Fixtures consumed: `clean_rate_limit_state` (from
  conftest.py — chat-handler rate-limit state cleanup) +
  `monkeypatch` (pytest stdlib — for `_apply_pr9_patches`
  invocation) + `tmp_path` (pytest stdlib — for per-test
  corpus dir isolation).
- Return type: `None` (pytest test functions return None;
  raised exceptions signal failure).
- No decorators (no `@pytest.mark.skipif` /
  `@pytest.mark.parametrize` / `@pytest.mark.asyncio` /
  etc. per framing §5.2 single-test-with-no-parametrize
  lock).

**Test function docstring shape:**

```python
"""Recomposition arc — multi-survivor cardinality divergence pure-isolation case.

Drives ``fix-pr15-multi-survivor-mismatch`` through the
full decomposition seam path. The fixture authors
``expected_narrow`` as a singleton subset of observation
(Direction A INVERSE per framing §5.10): PR 9 multi-match
deterministic outcome (prompt "list" produces
``narrower.decision = ["forge_list_projects",
"flame_list_libraries"]``) vs. authored ``expected_narrow =
["forge_list_projects"]`` (authored subset by one element;
cardinality classes singleton vs. multi-survivor).

The comparator's compare-as-persisted discipline (PR 10 §4.2
binding behavioral commitment) detects the multi-survivor
cardinality divergence as ``narrow_diverged=True`` per direct
list-equality at ``_compare.py:503`` (length asymmetry (1 vs 2)
+ element-membership asymmetry at the non-shared position both
contribute to ``obs_decision != exp_narrow``). Carrier #17 at
use: the DivergenceReport's per-surface partitioning preserves
authorship through emission → persistence → readback → join
→ interpretive comparison; the multi-survivor cardinality
divergence vector is identifiable at the structural shape level
(``expectation.expected_narrow`` has length 1;
``observation.observed_narrow`` has length 2; shared element
at position 0 verbatim).

Pure-isolation property at every dimension: multi-survivor
cardinality only — no ordering / semantic-normalization /
duplicate-handling / partial-set-within-shared-cardinality
confound. PR-15-LOCAL pure-isolation discipline binding.

The authored-subset direction (Direction A INVERSE per framing
§5.10) is an affirmative architectural decision — the INVERSE
of PR 14's authored-superset Direction A. The two-PR direction-
symmetric pair (PR 14 + PR 15) operationally corroborates the
comparator's compare-as-persisted discipline operates
direction-symmetrically. Direction A INVERSE maximizes (1)
direction-symmetric corroboration with PR 14, (2) single-
variable discipline preservation across PR 9 / PR 13 / PR 14
/ PR 15, and (3) semantically legible authorial claim ("I
expected only this one tool to survive narrowing;
arbitration's ambiguity is unexpected" — typical authorial
direction predicting clean outcome).
"""
```

**Test body 9-step traversal pattern** (six header
comments covering nine logical traversal steps; mirroring
PR 13 test body at `test_pr13_ordering_divergence.py:150-203`
+ PR 14 test body at `test_pr14_partial_narrow_divergence.py:172-226`
verbatim except for the multi-survivor-cardinality-specific
content at Step 8 + Step 9 assertions):

```python
# ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
# Test-internal archaeology surface (NOT a public API).
corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

# ── Steps 2-5 of traversal: drive fixture → emission ───────
# drive_seed_fixture orchestrates expectation persistence,
# chat_handler arbitration, observation emission. The seam
# traversal is explicit at the call site — no helper absorbs
# the arc (PR-11-LOCAL discipline at gate level per Gate 3
# close §3 item 10 + PR 15 framing §5.4 predicted-form 3
# suppression).
drive_seed_fixture(**FIX_MULTI_SURVIVOR_MISMATCH)

# ── Step 6 of traversal: read back persisted records ───────
# Test-internal archaeology surface; reads every
# capture-*.jsonl record across the corpus dir, skipping
# headers.
records = _read_records(corpus_dir)

# ── Step 7 of traversal: partition by fixture_id + record_kind ──
# Gate 2 close §2.1 foundational dependencies exercised:
# fixture_id joinability (filter step) + record_kind
# partitioning (separation step). Call-site awkwardness
# (filter + partition explicit at the test) is acceptable
# evidence the decomposition boundaries held (PR-11-LOCAL
# discipline at gate level + PR 15 framing §5.4 predicted-
# form 2 suppression — the PR-12 trigger surface evaluation
# is encoded at the explicit filter + partition pattern,
# not absorbed into a helper).
matching = [
    r for r in records
    if r.get("fixture_id") == FIX_MULTI_SURVIVOR_MISMATCH["fixture_id"]
]
assert len(matching) == 2, (
    f"Expected exactly 2 records for "
    f"{FIX_MULTI_SURVIVOR_MISMATCH['fixture_id']!r}; got "
    f"{len(matching)}.\nAll records: {records}"
)

observation = next(r for r in matching if r["record_kind"] == "observation")
expectation = next(r for r in matching if r["record_kind"] == "expectation")

# ── Step 8 of traversal: invoke comparator ─────────────────
# The interpretive-read seam. compare_records joins
# observation + expectation by fixture_id (Gate 2 close
# §2.1) and produces the DivergenceReport per carrier #17.
# Direct list-equality at _compare.py:503 detects the
# multi-survivor cardinality divergence (length 1 != length
# 2; element mismatch at the non-shared position); no
# caller-side cardinality-aware interpretation per PR 15
# framing §5.4 predicted-form 1 suppression (PR 10 §4.2
# binding behavioral commitment at use).
report = compare_records(
    observation_record=observation,
    expectation_record=expectation,
)

# ── Step 9 of traversal: assertions on DivergenceReport ────
# Four-key structural assertion contract — carrier #17 at
# use: each authority surface's contribution structurally
# identifiable at the report's outer dict shape. The
# multi-survivor cardinality divergence vector surfaces at
# distinct list lengths at expectation vs. observation
# sub-dicts (no cardinality_class-aware field; no
# cardinality-aware computation; the structural shape
# preservation IS the cardinality-class disclosure per
# PR 15 framing §5.4 predicted-form 1 suppression).
#
# Full-fidelity list assertions (NOT set-equality, NOT
# narrow_diverged-only) per PR 15 framing §5.4 predicted-
# form 1 suppression — set-equality shortcuts mask the
# load-bearing cardinality-class structural claim;
# narrow_diverged-only shortcuts mask the structural-shape
# disclosure.
assert report["fixture_id"] == FIX_MULTI_SURVIVOR_MISMATCH["fixture_id"]
assert report["expectation"]["expected_narrow"] == ["forge_list_projects"]
assert report["observation"]["observed_narrow"] == [
    "forge_list_projects",
    "flame_list_libraries",
]
assert report["divergence"]["narrow_diverged"] is True
```

**Body structure (binding):**

- 9 logical traversal steps explicitly annotated with 6
  header comments. The structure mirrors PR 13's + PR 14's
  9-step / 6-header pattern verbatim except for the multi-
  survivor-cardinality-specific content at Step 8 + Step 9.
- 5 inline call-site comments preceding each assertion or
  call invocation explain the architectural rationale
  (carrier #17 at use; PR 10 §4.2 binding at use;
  predicted-form suppression names).
- Test-internal archaeology surface comment marker (Step 1)
  preserves the underscored-private-status registration at
  the call site.

**Assertion 2 format asymmetry (single-line):** the
`expected_narrow` assertion at `["forge_list_projects"]` is
formatted on a single line (matching the FIXTURE dict's
single-line singleton form per §4.1.2). Assertion 3's
`observed_narrow` is multi-line (two elements, one per line)
matching PR 13's + PR 14's multi-element assertion format.
The format asymmetry between assertions 2 + 3 visually
encodes the cardinality-class divergence at the assertion
site itself.

#### 4.2.4 Assertion contract — four DivergenceReport keys verified

The test body asserts exactly four keys at the
DivergenceReport at full structural fidelity (per framing
§5.4 + framing §4.4 four-key structural assertion contract
inherited from PR 13 + PR 14 + PR 11):

| # | Assertion | Architectural rationale |
|---|---|---|
| 1 | `report["fixture_id"] == FIX_MULTI_SURVIVOR_MISMATCH["fixture_id"]` | Fixture identity preservation through the recomposition arc (Gate 2 close §2.1 joinability). |
| 2 | `report["expectation"]["expected_narrow"] == ["forge_list_projects"]` | Authored expectation list preserved verbatim through emission → persistence → readback → comparator (PR 10 §4.2 binding behavioral commitment at expectation surface). Single-element list asserts the multi-survivor cardinality vector's singleton-subset shape at full fidelity. |
| 3 | `report["observation"]["observed_narrow"] == ["forge_list_projects", "flame_list_libraries"]` | Arbitration observation preserved verbatim through chat_handler emission → persistence → readback → comparator (PR 10 §4.2 binding behavioral commitment at observation surface). Two-element list asserts the multi-survivor cardinality vector's multi-survivor shape at full fidelity. |
| 4 | `report["divergence"]["narrow_diverged"] is True` | Comparator's direct list-equality detected the multi-survivor cardinality divergence (`_compare.py:503`). Boolean field signals divergence presence; the structural-shape preservation in assertions 2 + 3 IS the cardinality-class disclosure (no separate `cardinality_class` field needed; framing §5.4 predicted-form 1 suppression). |

**Three predicted cleanup-pressure forms operationally
suppressed at the assertion contract:**

1. **Multi-survivor cardinality smoothing pressure**
   suppressed by asserting all four keys explicitly (NOT
   `narrow_diverged=True` only). The structural list
   values in assertions 2 + 3 preserve the cardinality-
   class shape at full fidelity. The cardinality-class
   structural shape (length 1 vs. length 2; singleton vs.
   multi-survivor) is the load-bearing architectural claim.
2. **Join-helper proliferation pressure (PR-12 trigger
   surface)** suppressed by inlining the filter +
   partition at the test body (Step 7 of traversal). No
   `join_records_by_fixture_id` helper invocation; no
   `filter_records_by_fixture_id` + `partition_by_record_kind`
   abstraction. The explicit filter + partition decomposition
   seam (Gate 2 close §2.1 foundational dependency) is
   preserved at the call site. **PR 15 close §1 inventories
   the actual join call-site count contribution** (expected:
   1 site, mirroring PR 11 + PR 13 + PR 14 pattern) +
   **qualitative second-clause pressure observation**
   (expected: NO qualitative pressure that "preserving
   decomposition becomes harder than abstracting" — mirroring
   PR 11 + PR 13 + PR 14 cumulative ABSENCE evidence). Gate
   4 close §x consumes the inventory inputs for final PR-12
   disposition.
3. **Recomposition-smoothing-through-helper pressure**
   suppressed by inlining the 9-step traversal at the test
   body. No `assert_recomposition_arc_divergence(...)`
   helper; no traversal-absorbing abstraction. PR-11-LOCAL
   traverses-not-erases-seams discipline at gate level
   (Gate 3 close §3 item 10).

**Assertion ordering rationale (binding per PR 13 spec
§4.2.4 + PR 14 spec §4.2.4 precedent):**

The four assertions appear in dependency order:

1. `fixture_id` first (Gate 2 close §2.1 joinability is the
   foundational dependency).
2. `expectation.expected_narrow` second (authored surface;
   write-side authority).
3. `observation.observed_narrow` third (arbitration surface;
   write-side authority).
4. `divergence.narrow_diverged` fourth (interpretive surface;
   read-side authority depends on both write-side surfaces).

The ordering mirrors the three-authority-surface partition
(Gate 2 close §2.4 item 1; PR 13 close §1.3; PR 14 close §1.3)
— each authority surface's contribution surfaces explicitly
at distinct assertion sites.

---

## 5. Test count anchors

### 5.1 Forge env test count projection

```
219 baseline (PR 14 close §1.9 forge env collected)
+   1 PR 15 multi-survivor cardinality divergence test
= 220 forge env collected at PR 15 close
```

Per `feedback_counts_are_archaeology_grade`: 220 is the
locked target at PR 15 close. If the actual count at Step 3
(final verification) differs from 220, spec author must:

- Investigate the divergence (test collection issue?
  parametrize expansion? skip condition? PR 14 baseline
  drift?).
- Amend §5.1 with archaeology before close.
- Document the divergence at PR 15 close §6 (mechanical
  checkpoints).

**Named-vs-collected discipline:** PR 15 ships 1 named test;
no `parametrize` decorators; named == collected. The
named-equals-collected identity is structurally locked at
PR 15 by single-test pattern (one test function; no
parametrization; no test class). Per framing §5.2 binding.

### 5.2 Forge-bridge env test count projection

```
213 baseline (PR 14 close §1.9 forge-bridge env projection;
              6-test gap inherited per
              project_v1_4_x_harness_debt)
+   1 PR 15 multi-survivor cardinality divergence test
= 214 forge-bridge env collected at PR 15 close (projected)
```

Forge-bridge env count NOT re-verified at PR 15 close beyond
inheritance documentation. The 6-test gap is PR 7-scope, not
PR 15-scope. **Do not conflate the two env counts** per
PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close §5.2 +
PR 13 close §1.9 + PR 14 close §1.9.

### 5.3 Test inventory at PR 15 close (locked)

| # | Test | File | Step |
|---|---|---|---|
| 1 | `test_recomposition_arc_multi_survivor_mismatch` | `test_pr15_multi_survivor_mismatch.py` | 2 |

The single test lands at Step 2 (the architectural-center).

---

## 6. Atomic step decomposition

PR 15 ships as a **3-step + close** atomic sequence per
framing §9.12 both-skeletons-at-Step-1 lifecycle invariant
(inherited from PR 13 close §2.4 as PR-of-origin + PR 14
close §2.4 second operational instance + PR 15 third
operational instance — THREE-PR-CORROBORATED archaeological
pattern):

- Step 1: both skeletons (test module + fixture module, in
  one commit).
- Step 2: both architectural-centers (test body + FIXTURE
  dict, in one commit).
- Step 3: final verification (empty commit; archaeology in
  body).
- Close: **PR 15 close artifact paired at same-commit with
  Gate 4 close artifact** (single commit landing TWO close
  artifacts; per framing §9.12 + §2.4 + Gate 4 framing
  §11.8 + PR 14 close §7 deferral). **DIFFERENT close
  cadence from PR 13 + PR 14 standalone closes.**

### 6.1 Step 1 — both skeletons (test module + fixture module, bundled)

**Atomic commit content (single commit landing TWO new files):**

- New file:
  `tests/corpus/test_pr15_multi_survivor_mismatch.py`
  - Module docstring (per §4.2.1 — PR-15-LOCAL +
    traversal trace + carrier travel by reference +
    test infrastructure import discipline + references).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports until used by test body
    at Step 2).
  - No test bodies, no module-level constants, no helper
    functions.
- New file:
  `tests/corpus/fixtures/fix_multi_survivor_mismatch.py`
  - Module docstring (per §4.1.1 — PR-15-LOCAL + carrier
    travel by reference + fixture purpose with grounded
    arbitration trace + Direction A INVERSE rationale +
    references + fixture-data-discipline closing).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports — fixture-data-discipline
    member #9 prevents any import beyond `__future__`).
  - No `FIXTURE` dict declaration; no helpers; no constants.

**Both files at structurally-symmetric skeleton state.**
The lifecycle invariant (establishment → activation) holds
across both files. Framing §9.12 both-skeletons-at-Step-1
lifecycle invariant operational (inherited from PR 13 as
PR-of-origin + PR 14 second operational instance + PR 15
third operational instance).

**Step 1 verification:**

- `pytest tests/corpus/test_pr15_multi_survivor_mismatch.py
  --collect-only -q` → 0 tests collected (skeleton only).
- `python -c "import tests.corpus.test_pr15_multi_survivor_mismatch"`
  → imports cleanly.
- `python -c "import tests.corpus.fixtures.fix_multi_survivor_mismatch"`
  → imports cleanly; no module-level symbols beyond docstring.
- `pytest tests/corpus/ --collect-only -q | tail -1` → 219
  collected (PR 14 baseline preserved at Step 1; PR 15 test
  not yet activated).
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr4_participation_creep.py
  tests/corpus/test_pr6_visual_asymmetry.py
  tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr9_*.py tests/corpus/test_pr10_*.py
  tests/corpus/test_pr11_recomposition_arc.py
  tests/corpus/test_pr13_ordering_divergence.py
  tests/corpus/test_pr14_partial_narrow_divergence.py` →
  passes unchanged (PR 15 skeleton is target-disjoint from
  all four Layer 2 walkers' input sets + Layer 3 lint +
  PR 11 recomposition arc + PR 13 + PR 14 calibration
  substrates).

**Step 1 commit body sections (mirroring PR 14 Step 1 pattern adapted for PR 15 scope):**

```
phase-a.5.3.2: PR 15 Step 1 — both skeletons (test module + fixture module bundled)

PR 15 establishes two new files at skeleton state:

  - tests/corpus/fixtures/fix_multi_survivor_mismatch.py
  - tests/corpus/test_pr15_multi_survivor_mismatch.py

Both files at structurally-symmetric skeleton state. Module
docstrings carry PR-15-LOCAL binding statement verbatim +
17 active carriers cited by reference to canonical sources +
traversal/arbitration trace + Direction A INVERSE rationale
(fixture docstring only) + references. `from __future__
import annotations` is the only import at each file. No
test bodies, no FIXTURE dict, no constants, no helpers.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-15-LOCAL binding statement (verbatim per A.5.3.2-PR15-FRAMING.md §0 + §5.5):

  PR 15 isolates multi-survivor cardinality divergence as
  the sole pressure vector. Multi-vector fixture pressure
  within PR 15 scope — combining cardinality with ordering,
  semantic-normalization, duplicate-handling, partial-set
  (within shared cardinality), or any other divergence
  form — is rejected at the spec layer. The pure-isolation
  property is what gives PR 15 its laboratory-grade
  methodology corroboration value for Placement A +
  Placement B substrate.

Preserved invariants:

  - 17 active carriers cited by reference to canonical
    sources (forge_bridge/corpus/_capture.py:6-135 +
    _seed.py:19-135 + _compare.py module docstring;
    A.5.3.2-GATE-3-CLOSE.md §1.6 for carrier #16).
  - Gate 2 binding framing clarification (call-site-owned
    arbitration inputs) cited by reference.
  - Cross-surface unbinding clarification inherited
    unchanged.
  - PR-11-LOCAL discipline (traverses-not-erases-seams) at
    gate level per Gate 3 close §3 item 10.
  - PR-13-LOCAL as PR-of-origin for pure-isolation pattern
    per PR 13 close §2.2; PR-14-LOCAL parallel-not-
    regenerative scope-local at second calibration point
    per PR 14 close §2.2; PR-15-LOCAL parallel scope-local
    at third calibration point — second corroboration of
    the parallel-not-regenerative pattern PR 14 introduced.

Architectural sufficiency signal (Step 1):

  - 0 production source modifications.
  - 2 new test/fixture files added at skeleton state.
  - 0 fifth walker; 0 _ALLOWLIST modifications; 0 Layer 3
    lint changes.

Both-skeletons-at-Step-1 lifecycle invariant (binding per
A.5.3.2-PR15-FRAMING.md §9.12 + inherited from PR 13 close
§2.4 as PR-of-origin + PR 14 close §2.4 second operational
instance — PR 15 third operational instance, THREE-PR-
CORROBORATED archaeological pattern):

  Both PR 15 files undergo the same establishment →
  activation lifecycle transition. Asymmetric step
  structures (file-asymmetric / 4-step / 2-step compression)
  rejected at framing. Step 1 lands BOTH skeletons in one
  commit; Step 2 lands BOTH bodies in one commit; Step 3 is
  empty verification with archaeology in body.

What does NOT land at Step 1: test body (Step 2), FIXTURE
dict (Step 2), imports beyond `__future__ annotations`
(Step 2 + member 10 discipline).

Surfaces inventory at Step 1:

  1. fix_multi_survivor_mismatch.py module docstring.
  2. test_pr15_multi_survivor_mismatch.py module docstring.
  3. This commit body.

Total PR 15 surfaces accumulating toward close-time
archaeology: 3 (Step 1) + 1 (Step 2 commit body) + 1 (Step 3
commit body) + 1 (PR 15 close artifact body) + 1 (Gate 4
close artifact body, same-commit-paired) = 6 commit-chain
surfaces. **+1 surface vs. PR 13 + PR 14 5-surface
inventory; the +1 is Gate 4 close's body accessible via
same-commit-pairing per framing §9.12 + §2.4.**

References:

  - A.5.3.2-PR15-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR14-CLOSE.md (immediate predecessor;
    parallel-not-regenerative pattern introduction; second
    calibration substrate).
  - A.5.3.2-PR13-CLOSE.md (PR-of-origin precedents — pure-
    isolation discipline + both-skeletons-at-Step-1
    lifecycle invariant).
```

### 6.2 Step 2 — both architectural-centers (test body + FIXTURE dict bundled)

**Atomic commit content (single commit landing TWO file bodies):**

- `tests/corpus/test_pr15_multi_survivor_mismatch.py`:
  - Imports landed (per §4.2.2 final-state inventory):
    `pathlib`, `pytest`, `compare_records`,
    `drive_seed_fixture`, `FIX_MULTI_SURVIVOR_MISMATCH`,
    `_apply_pr9_patches`, `_read_records`.
  - Test function: `test_recomposition_arc_multi_survivor_mismatch`
    (full body per §4.2.3).
  - No new module-level constants, no helper functions, no
    parametrize decorators.
- `tests/corpus/fixtures/fix_multi_survivor_mismatch.py`:
  - `FIXTURE` dict landed (per §4.1.2):
    ```python
    FIXTURE: dict = {
        "fixture_id": "fix-pr15-multi-survivor-mismatch",
        "prompt": "list",
        "expected_narrow": ["forge_list_projects"],
    }
    ```
  - No additional imports (member #9 fixture-data-
    discipline; `from __future__ import annotations`
    carried from Step 1 unchanged).

**Three-round review applies** per Gate 2 framing §5.7
integration-work elevation. PR 15's architectural-center is
the multi-survivor-cardinality-divergence recomposition arc
operational landing; carrier #17 at use + §4.2 binding
behavioral commitment at use + §5.4 three predicted cleanup-
pressure forms operationally suppressed (with PR-12 trigger
surface evaluation inputs registered per §5.12) are the
load-bearing verifications.

**Step 2 verification:**

- `pytest tests/corpus/test_pr15_multi_survivor_mismatch.py` →
  1/1 passed.
- `pytest tests/corpus/test_pr14_partial_narrow_divergence.py
  tests/corpus/test_pr13_ordering_divergence.py
  tests/corpus/test_pr11_recomposition_arc.py
  tests/corpus/test_pr10_*.py tests/corpus/test_pr9_*.py
  tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr7_*.py
  tests/corpus/test_pr4_participation_creep.py` → passes
  unchanged.
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr6_visual_asymmetry.py` → passes
  unchanged.
- `pytest tests/corpus/ --collect-only -q | tail -1` →
  **220 collected** forge env (219 baseline + 1 PR 15 new).
  EXACT MATCH with §5.1 projection.
- Architectural sufficiency signal: `git diff --stat
  <PR-15-Step-1-commit>..HEAD -- forge_bridge/` returns
  EMPTY (zero production source modifications).

**Step 2 commit body sections (mirroring PR 14 Step 2 pattern adapted):**

```
phase-a.5.3.2: PR 15 Step 2 — architectural-center (test body + FIXTURE dict bundled)

PR 15 architectural-center lands two bodies in one commit:

  - tests/corpus/test_pr15_multi_survivor_mismatch.py:
    imports (pathlib, pytest, compare_records,
    drive_seed_fixture, FIX_MULTI_SURVIVOR_MISMATCH,
    _apply_pr9_patches, _read_records) + 1 named test
    (test_recomposition_arc_multi_survivor_mismatch)
    exercising the full end-to-end recomposition arc.
  - tests/corpus/fixtures/fix_multi_survivor_mismatch.py:
    FIXTURE dict with fixture_id, prompt "list",
    expected_narrow [forge_list_projects] (singleton;
    authored-subset Direction A INVERSE per framing §5.10
    — observation's position 0 element verbatim; length 1
    vs. observation length 2; cardinality classes singleton
    vs. multi-survivor).

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-15-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

Bundled-commit rationale:

The test needs the FIXTURE import + FIXTURE dict body
together to function. Both bodies bundled per spec §6.2 +
framing §9.12 both-skeletons-at-Step-1 lifecycle invariant
applied symmetrically at architectural-center (both bodies
land in one commit, mirroring the both-skeletons lifecycle
invariant at Step 1; PR-of-origin precedent at PR 13 close
§1.11 + §2.4 + PR 14 close §1.11 second operational
instance).

Architectural-center load-bearing verifications:

  - Carrier #17 at use: DivergenceReport per-surface
    partitioning preserves authorship through emission →
    persistence → readback → join → interpretive comparison;
    assertions 2 + 3 satisfy distinct dict paths
    (report["expectation"] vs. report["observation"]) with
    distinct list lengths (1 vs 2; singleton vs. multi-
    survivor).
  - PR 10 §4.2 binding behavioral commitment at use:
    comparator's direct list-equality (_compare.py:503)
    detects the multi-survivor cardinality divergence as
    narrow_diverged=True via length asymmetry + element-
    membership asymmetry at the non-shared position.
  - Three predicted cleanup-pressure forms (framing §5.4)
    operationally suppressed at assertion contract:
    multi-survivor cardinality smoothing pressure (no
    narrow_diverged-only assertion; full four-key
    structural assertion contract), join-helper
    proliferation pressure / PR-12 trigger surface (no
    helper invocation; explicit filter + partition at
    Step 7), recomposition-smoothing-through-helper
    pressure (9-step traversal inlined at test body; no
    assert_recomposition_arc_divergence helper).
  - PR-11-LOCAL discipline at gate level (Gate 3 close §3
    item 10): test body inlines the 9-step traversal
    annotation pattern; no helper absorbs the assertion
    logic.

Direction A INVERSE affirmative architectural decision verification:

  - Authored expectation is singleton [forge_list_projects].
    forge_list_projects appears at observation position 0
    verbatim per PR 9 multi-match arbitration trace
    (fix_multi_match.py:126). Authored ⊂ observed (length 1
    ⊂ length 2). Semantically legible authorial claim
    preserved ("I expected only this one tool to survive
    narrowing").
  - Direction-symmetric with PR 14: PR 14 authored ⊃ observed
    (length 3 ⊃ length 2); PR 15 authored ⊂ observed (length
    1 ⊂ length 2). Two-PR pair exercises comparator's
    compare-as-persisted discipline direction-symmetrically.
  - Single-variable discipline across PR 9 / PR 13 / PR 14
    / PR 15 preserved: same prompt + same reachable-tool
    set + same arbitration trace + same observation. Only
    the authored expectation varies (four-PR cumulative
    discipline; framing §4.6).
  - "list"-as-calibration-prompt archaeology preserved per
    framing §4.6 four-PR cumulative.

PR-12 trigger surface evaluation inputs (registered at
Step 2; final disposition deferred to Gate 4 close per
framing §5.12):

  - Actual join call-site count contribution: 1 site (the
    standard filter + partition pattern PR 11 + PR 13 +
    PR 14 inherited unchanged; encoded explicitly at
    Step 7 of traversal per test body §4.2.3).
  - Qualitative second-clause pressure observation:
    [SURFACE / ABSENCE at Step 2 implementation — recorded
    at Step 3 commit body per framing §9.4 + §5.12].
    Expected outcome: ABSENCE (mirroring PR 11 + PR 13 +
    PR 14 cumulative pattern).

Recomposition-through-existing-seams operational evidence:

  PR 15 ships against the validated PR 10 comparator + PR 11
  recomposition arc + PR 13 + PR 14 calibration substrates
  unchanged. Zero modifications to comparator surface,
  recomposition arc pattern, fixture corpus, or test
  infrastructure. Architectural sufficiency signal target
  met at Step 2 (six-PR cumulative escalation: PR 9 + 10 +
  11 + 13 + 14 + 15).

Preserved invariants:

  - 17 active carriers cited by reference (Step 1
    inheritance).
  - Gate 2 binding framing clarification cited by reference.
  - Cross-surface unbinding clarification inherited
    unchanged.
  - PR-11-LOCAL discipline at gate level.
  - PR-13-LOCAL as PR-of-origin for pure-isolation pattern;
    PR-14-LOCAL parallel-not-regenerative second instance;
    PR-15-LOCAL parallel-not-regenerative third instance
    (second corroboration of the parallel-not-regenerative
    pattern).

Architectural sufficiency signal (Step 2):

  - 0 production source modifications (verified at Step 2
    via `git diff --stat <Step-1-commit>..HEAD --
    forge_bridge/`).
  - 2 new test/fixture files activated at this commit.
  - 219 + 1 = 220 forge env collected (locked).

§4.2 binding behavioral commitment verification at use:

  Test asserts list-equality on expected_narrow and
  observed_narrow at distinct dict paths. The comparator's
  compare-as-persisted discipline preserves the multi-
  survivor cardinality vector through every traversal seam
  (length 1 expectation + length 2 observation surfaces at
  full structural fidelity; singleton-vs-multi-survivor
  cardinality classes preserved).

Surfaces inventory at Step 2:

  1. fix_multi_survivor_mismatch.py module docstring +
     FIXTURE dict.
  2. test_pr15_multi_survivor_mismatch.py module docstring
     + test body.
  3. Step 1 commit body.
  4. This commit body.

Total PR 15 surfaces accumulating toward close-time
archaeology: 4 commit-chain surfaces at Step 2.

References:

  - A.5.3.2-PR15-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR14-CLOSE.md (second calibration substrate;
    Direction A authored-superset precedent which PR 15
    inverts to Direction A INVERSE authored-subset).
  - A.5.3.2-PR13-CLOSE.md (calibration substrate at first
    calibration point; PR-of-origin precedents).
```

### 6.3 Step 3 — final verification (empty commit; archaeology in body)

**Atomic commit content:**

- No file changes (empty commit; `git commit --allow-empty`).
- Commit message body carries:
  - 10-item Step 3 verification checklist (per §1 regression
    contracts + framing §9 phase-end conditions).
  - 17 inherited carriers cited by reference.
  - PR-15-LOCAL binding statement verbatim.
  - §2.4 Gate 4 architectural commitment verbatim.
  - Full PR 15 surfaces inventory.
  - Spec amendments at incarnation (if any surfaced during
    Steps 1–2).
  - Cleanup-pressure-resistance archaeology (predicted-form
    outcomes: ABSENCE / SURFACE per framing §5.4 three
    predicted forms).
  - **PR-12 trigger surface evaluation inputs (final
    inventory at Step 3):** actual join call-site count +
    qualitative second-clause pressure observation per
    framing §5.12.
  - Placement A contribution recording (predicted-form
    outcomes per framing §6.1; third Gate 4 PR instance
    contributing to three-PR cumulative).
  - Placement B precondition manifestation recording
    (preconditions 1 + 2 manifest at framing time;
    precondition 3 cumulative across PR 13 + PR 14 + PR 15;
    Gate 4 close §x evaluates final-cumulative).
  - §5.3 candidate methodology observation outcome (third-
    Gate-4-PR instance; potential fifth-instance cumulative
    ABSENCE evidence: PR 10 + 11 + 13 + 14 + 15).
  - Catch-point migration candidate methodology contribution
    (PR 15 spec-drafting-time outcome per spec §0; PR 15
    implementation outcome at Step 3 close).
  - PR 15 commit chain summary (Step 1 + Step 2 + Step 3
    commit hashes).
  - Next: **PR 15 close artifact paired at same-commit
    with Gate 4 close** (DIFFERENT cadence from PR 13 +
    PR 14 standalone closes).

**Step 3 verification checklist (10 items):**

1. **PR 15 suite:** `pytest tests/corpus/test_pr15_multi_survivor_mismatch.py`
   → 1/1 passed.
2. **Existing suites regression:** `pytest tests/corpus/
   --collect-only -q | tail -1` → 220 collected forge env;
   all suites pass unchanged.
3. **PR 4 + PR 5 chat-handler + no-dependency integration
   tests:** pass unchanged (no chat_handler arbitration
   surface modifications at PR 15).
4. **PR 6 Layer 3 lint regression:** 17/17 passed unchanged;
   zero new `emit_divergence_capture` call sites at PR 15.
5. **Four Layer 2 walkers regression:** all four (PR 4 +
   PR 8 + PR 9 + PR 10) pass unchanged; parallel-not-
   extension boundary preserved.
6. **PR 3 discipline:** 1/1 passed unchanged; corpus-
   subtree auto-exclusion handles
   `tests/corpus/test_pr15_*.py` +
   `tests/corpus/fixtures/fix_multi_survivor_mismatch.py`
   placements.
7. **PR 11 + PR 13 + PR 14 regression:** PR 11 3/3 passed
   unchanged + PR 13 1/1 passed unchanged + PR 14 1/1
   passed unchanged; PR 15 inherits consumption patterns
   without modification.
8. **Public API regression:** `forge_bridge.__all__` at 19
   symbols.
9. **Verbatim travel verification:**
   - PR-15-LOCAL + 17 carriers cited by reference at both
     PR 15 module docstrings (Step 1 verified).
   - §2.4 Gate 4 architectural commitment travels at this
     spec §0 + §1 + §2 + Step 1, 2, 3 commit body
     "architectural commitment" sections + PR 15 close
     §1 + §6.5 + Gate 4 close §x (9-surface inventory at
     PR 15 close, +1 vs. PR 13 + PR 14 8-surface inventory).
   - 17 inherited carriers cited by reference at both PR 15
     module docstrings per §4.1.1 + §4.2.1.
10. **Architectural sufficiency signal verification:** `git
    diff --stat <PR-15-framing-commit>..HEAD -- forge_bridge/`
    returns EMPTY (zero production source modifications
    across PR 15's commit chain). §1 regression contract
    #10 + framing §5.3 binding decision + framing §9.3.
    **Six-PR cumulative escalation** (PR 9 + 10 + 11 + 13
    + 14 + 15) verified.

**Step 3 commit type:** empty verification commit, no code
changes. Mirrors PR 9 Step 5 (`159ccd2`) + PR 10 Step 5
(`d04753c`) + PR 11 Step 3 (`ae69fba`) + PR 13 Step 3
(`d7f2a6a`) + PR 14 Step 3 (`9a09c86`) pattern.

**Step 3 commit body sections (mirroring PR 14 Step 3 pattern adapted):**

```
phase-a.5.3.2: PR 15 Step 3 — final verification (empty commit; archaeology in body)

Step 3 final verification: empty commit; archaeology
documented in body.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-15-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

10-item Step 3 verification checklist:

  [10-item checklist per §6.3 above]

Cleanup-pressure-resistance archaeology — predicted-form outcomes:

  - Multi-survivor cardinality smoothing pressure:
    [ABSENCE / SURFACE — record actual outcome].
  - Join-helper proliferation pressure (PR-12 trigger
    surface): [ABSENCE / SURFACE — record actual outcome].
  - Recomposition-smoothing-through-helper pressure:
    [ABSENCE / SURFACE — record actual outcome].

PR-12 trigger surface evaluation inputs (final per framing §5.12):

  - Actual join call-site count contribution: 1 site
    (verified at Step 7 of traversal in test body).
  - Cumulative call-site count projection (PR 11 3 + PR 13
    1 + PR 14 1 + PR 15 1 = 6 sites at Gate 4 close).
    Threshold ≥4 numerically satisfied.
  - Qualitative second-clause pressure observation:
    [SURFACE / ABSENCE — record actual outcome]. Expected:
    ABSENCE per framing §5.12 (PR 11 + PR 13 + PR 14
    cumulative ABSENCE evidence).
  - Final PR-12 disposition decision: DEFERRED to Gate 4
    close §x per framing §5.12 (PR 15 ships evaluation
    inputs; Gate 4 close ships final disposition).

Placement A contribution at PR 15: [N-form-ABSENCE /
N-form-SURFACE evidence summary; third Gate 4 PR instance
contributing toward §5.3 candidate methodology observation's
operational corroboration. Cumulative across three-PR
substrate (PR 13 + PR 14 + PR 15) — if all three-PR
3-form-ABSENCE, total nine-form-ABSENCE evidence].

Placement B preconditions manifestation:
  - Precondition 1 (prior pressure prediction at framing
    time): manifest per framing §5.4 + spec §4.2.4.
  - Precondition 2 (named suppression mechanism per
    predicted form): manifest per framing §5.4 + spec
    §4.2.4.
  - Precondition 3 (corroborated recurrence across multiple
    PR scopes): completes to THREE-PR cumulative
    manifestation at PR 15 (PR 13 + PR 14 + PR 15); Gate
    4 close evaluates final-cumulative per Gate 4 framing
    §6.2.

Catch-point migration candidate methodology contribution:

  - PR 15 framing-convergence-pass pre-commit: catch-shape
    continuation of instance #3 (zero amendments — clean
    propagation; recorded at framing landing absence of §0
    catch section).
  - PR 15 spec-drafting-time: catch-shape continuation of
    instance #3 (zero grounding catches surfaced per spec
    §0).
  - PR 15 implementation-time: [SURFACE / ZERO-AMENDMENT —
    record actual outcome at Step 3]. Expected: catch-shape
    continuation of instance #3 (zero amendments —
    cumulative clean-propagation pattern).

PR 15 commit chain summary:
  - Step 1 commit: <hash> — both skeletons.
  - Step 2 commit: <hash> — both architectural-centers.
  - Step 3 commit: this commit — final verification.

Surfaces inventory at Step 3:

  1. fix_multi_survivor_mismatch.py module docstring +
     FIXTURE dict.
  2. test_pr15_multi_survivor_mismatch.py module docstring
     + test body.
  3. Step 1 commit body.
  4. Step 2 commit body.
  5. This commit body.

Total PR 15 surfaces at Step 3: 5 commit-chain surfaces.

Next: PR 15 close artifact + Gate 4 close artifact paired
at same-commit (DIFFERENT cadence from PR 13 + PR 14
standalone closes per framing §11 + §2.4 + Gate 4 framing
§11.8 + PR 14 close §7 deferral).

References:

  - A.5.3.2-PR15-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR14-CLOSE.md (immediate predecessor; second
    calibration substrate).
  - A.5.3.2-PR13-CLOSE.md (PR-of-origin precedents;
    first calibration substrate).
```

### 6.4 Close commit — PR 15 close artifact PAIRED WITH Gate 4 close (same commit)

**Atomic commit content:**

- New file:
  `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR15-CLOSE.md`
  - PR 15 close artifact (PR-15-scoped archaeology per
    framing §9.12 + §2.4; paired at same-commit with Gate
    4 close per framing §11.8 + PR 14 close §7 deferral).
  - Sections (target shape per PR 14 close 8-section
    inventory):
    - §1 What PR 15 established (with subsections per
      PR 14 close precedent; includes §1.X PR-12 trigger
      surface evaluation inputs).
    - §2 What Gate 4 / future Gate-X work inherits from
      PR 15.
    - §3 What Gate 4 / future work changes (resolved at
      Gate 4 close — same-commit-paired sibling artifact).
    - §4 Step-by-step archaeology — 4-commit PR 15 chain.
    - §5 Methodology observations at PR 15 scope.
    - §6 Mechanical checkpoints.
    - §7 Same-commit-paired close with Gate 4 close
      (DIFFERENT cadence from PR 13 + PR 14 standalone
      closes; third operational instance of same-commit-
      pairing pattern after Gate 2 + Gate 3 closes).
    - §8 Cross-references.
- New file:
  `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-GATE-4-CLOSE.md`
  - Gate 4 close artifact (gate-arc synthesis; same-commit-
    paired with PR 15 close per framing §11.8 + Gate 4
    framing §11.8).
  - Sections (target shape per Gate 2 close + Gate 3 close
    precedent):
    - §1 Gate 4 substrate — three-PR cumulative archaeology
      (PR 13 + PR 14 + PR 15).
    - §2 What Gate 4 inherits from Gate 3 (preserved).
    - §3 §5.3 candidate methodology observation evaluation
      against potential five-instance cumulative ABSENCE
      evidence (PR 10 + 11 + 13 + 14 + 15).
    - §4 Placement A cumulative evaluation (three-PR
      contribution; nine-form-ABSENCE if all three).
    - §5 Placement B precondition 3 final cumulative
      manifestation (three-PR cumulative).
    - §6 Six-PR architectural sufficiency signal escalation
      (PR 9 + 10 + 11 + 13 + 14 + 15).
    - §7 Catch-point migration candidate methodology
      prescriptive promotion evaluation.
    - §8 PR-N-LOCAL parallel-not-regenerative pattern
      promotion evaluation (two-PR corroboration: PR 14 +
      PR 15).
    - §9 Direction selection rationale at framing-level
      direction-symmetric pressure SECOND corroboration
      (PR 14 + PR 15 two-PR-corroborated).
    - §10 Both-skeletons-at-Step-1 lifecycle invariant
      THREE-PR-corroborated archaeological pattern (PR 13
      + PR 14 + PR 15).
    - §11 PR-12 final disposition decision (consumes PR 15
      close §1 inputs).
    - §12 Cleanup-pressure-resistance class promotion
      evaluation (current 10-member class; any new
      candidates surfaced at Gate 4 substrate).
    - §13 Gate-level inheritance contract toward Gate 5
      (or end-of-A.5.3.2 archaeology if Gate 4 closes the
      phase).
    - §14 Cross-references.

**Close commit body sections (mirroring PR 14 close commit pattern adapted for same-commit-paired form):**

```
phase-a.5.3.2: PR 15 close + Gate 4 close (same-commit paired) — three-PR Gate 4 cumulative

PR 15 close artifact (PR-15-scoped archaeology) + Gate 4
close artifact (gate-arc synthesis) paired at same commit
per A.5.3.2-PR15-FRAMING.md §11 + §2.4 + Gate 4 framing
§11.8 + PR 14 close §7 deferral.

DIFFERENT cadence from PR 13 + PR 14 standalone closes —
this is the THIRD OPERATIONAL INSTANCE of the same-commit-
pairing pattern (Gate 2 close `a6e42f0` + Gate 3 close
`ee2225b` + this commit).

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

  This sentence travels at PR 15 close §1 + §6.5 + Gate 4
  close architectural-commitment section. **9-surface
  inventory** at PR 15 close (extended by 1 vs. PR 13 +
  PR 14 close-time 8-surface inventory; the +1 surface is
  Gate 4 close's architectural-commitment section,
  accessible via this same-commit-pairing).

PR-15-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

  PR-15-LOCAL travel terminates at PR 15 surfaces only
  (does NOT travel to Gate 4 close per non-regeneration
  discipline + scope-local nature).

PR 15 commit chain (4-commit post-spec implementation arc;
mirrors PR 14 close §4 "4-commit PR 14 chain" framing — spec
is predecessor context, not counted in the post-spec arc):

  Predecessor: <hash> — spec
  (A.5.3.2-PR15-SPEC.md; this artifact's predecessor).

  1. <hash> — Step 1 (both skeletons).
  2. <hash> — Step 2 (both architectural-centers).
  3. <hash> — Step 3 (final verification).
  4. <hash> — close (this commit; PR 15 close + Gate 4
     close PAIRED).

Same-commit-pairing rationale:

  Gate 4 close pairs at same-commit with the FINAL primary
  PR's close (PR 15 close in the locked PR 13 → PR 14 →
  PR 15 sequence) per Gate 2 + Gate 3 close precedent +
  Gate 4 framing §11.8. The same-commit-pairing handles
  the gate-arc synthesis responsibility cleanly:

    - PR 15 close: PR-15-scoped archaeology (implementation
      arc + cleanup-pressure-form outcomes + 0-prod-mod
      outcome + Placement A 3-form-ABSENCE-or-SURFACE
      contribution + Placement B precondition 1+2
      manifestation + PR-12 trigger surface evaluation
      inputs).
    - Gate 4 close: gate-arc synthesis (three-PR Placement
      A cumulative evaluation; Placement B precondition 3
      final cumulative manifestation; §5.3 candidate
      methodology promotion evaluation against potential
      five-instance ABSENCE evidence; six-PR architectural-
      sufficiency-signal escalation evaluation; catch-point
      migration candidate methodology prescriptive promotion
      evaluation; PR-12 final disposition; cleanup-pressure-
      resistance class promotion evaluation; gate-level
      inheritance contract).

References:

  - A.5.3.2-PR15-CLOSE.md (this commit's PR-15-scoped
    archaeology artifact).
  - A.5.3.2-GATE-4-CLOSE.md (this commit's gate-arc
    synthesis artifact).
  - A.5.3.2-PR15-SPEC.md (PR 15 implementation contract).
  - A.5.3.2-PR15-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance
    contract).
  - A.5.3.2-PR14-CLOSE.md (immediate predecessor; second
    calibration substrate; parallel-not-regenerative
    pattern PR 14 introduced; PR 15 second corroboration).
  - A.5.3.2-PR13-CLOSE.md (first calibration substrate;
    PR-of-origin for pure-isolation pattern + both-
    skeletons-at-Step-1 lifecycle invariant).
  - A.5.3.2-GATE-3-CLOSE.md (Gate 3 close precedent —
    second operational instance of same-commit-pairing
    pattern after Gate 2 close).
  - A.5.3.2-GATE-2-CLOSE.md (Gate 2 close precedent —
    first operational instance of same-commit-pairing
    pattern).
```

### 6.5 Step N.5 surgical cadence — available if needed

The Step N.5 surgical cadence (Gate 2 framing §5.7
introduction; Gate 3 close §1.12 three-times-corroborated +
zero-times-at-Gate-3 archaeology; PR 13 spec §6.5 + PR 13
close §5.1 + PR 14 spec §6.5 inheritance) is available at
PR 15 if needed.

If implementation surfaces a real production-source need at
Step 2 (per framing §5.11 justified-deviation protocol):

1. Pause Step 2 at the moment of falsification.
2. Surface the deviation at framing-level evaluation.
3. If real architectural gap: ship the modification as a
   Step 2.5 surgical commit BEFORE Step 3 verification.
4. PR 15 close §5 records the deviation as Gate-X inheritance
   archaeology.

The Step N.5 cadence is goal-oriented availability, not
constraint. PR 15's expected outcome is **zero Step N.5
commits** (per framing §5.3 0-prod-mod target + Gate 3 close
§1.11 + five-PR architectural-sufficiency-signal escalation
target extending to six-PR at PR 15).

---

## 7. Phase-end conditions for PR 15

PR 15 close + Gate 4 close (same-commit paired) phase-end
conditions inherit from framing §9 (12 subsections)
unchanged. This spec §7 summarizes the operational
verification target per phase-end condition:

| # | Condition | Operational target |
|---|---|---|
| 9.1 | Test count anchor | 220 forge env collected (219 + 1) |
| 9.2 | PR 15 suite regression | 1/1 passed (`test_recomposition_arc_multi_survivor_mismatch`) |
| 9.3 | 0-prod-mod outcome verified | `git diff --stat de50fea..<PR-15-final-commit> -- forge_bridge/` empty |
| 9.4 | Predicted cleanup-pressure form outcomes recorded | Target: 3-form-ABSENCE (parallel to PR 13 + PR 14); includes PR-12 trigger surface inputs |
| 9.5 | Placement B precondition operational manifestation recorded | Preconditions 1 + 2 manifest at PR 15 framing + spec; precondition 3 completes to three-PR cumulative at PR 15 |
| 9.6 | Module docstring carrier travel verified | 17 carriers cited by reference at both PR 15 module docstrings |
| 9.7 | §2.4 architectural commitment travel verified | 9 surfaces (PR 13 + PR 14 8-surface baseline + 1 Gate 4 close section accessible via same-commit-pairing) |
| 9.8 | Public API anchor | `forge_bridge.__all__` at 19 symbols |
| 9.9 | Imports-land-when-used discipline verified (member #10) | Both files verified symmetrically |
| 9.10 | Cleanup-pressure-resistance class additions registered | Target: no new candidate class members |
| 9.11 | Test-internal archaeology surfaces inheritance verified | `_apply_pr9_patches` + `_read_records` consumed unchanged; THIRD operational corroboration |
| 9.12 | Step archaeology summary | Both-skeletons-at-Step-1 lifecycle invariant THIRD operational corroboration (PR 13 PR-of-origin + PR 14 second + PR 15 third) |

PR 15 close §1.X records each condition's operational
verification outcome. Gate 4 close consumes the verifications
for gate-arc synthesis.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` no modification

PR 15 does NOT modify `forge_bridge/corpus/_ALLOWLIST` or
any Layer 1 surface (per framing §8.1 + Gate 4 framing §8.1
+ PR 13 spec §8.1 + PR 14 spec §8.1 + class member #1 lock).

**Why unchanged:** PR 15 fixture + test consume corpus-
internal surfaces through already-allowlisted import paths:

- `forge_bridge.corpus._compare.compare_records` — already
  consumed by PR 11 + PR 13 + PR 14.
- `forge_bridge.corpus._seed.drive_seed_fixture` — already
  consumed by PR 11 + PR 13 + PR 14.

No new corpus-internal import paths required at PR 15.

**Corpus-subtree auto-exclusion semantics** (inherited from
PR 10 §4.4 + PR 13 spec §8.1 + PR 14 spec §8.1): the new
`tests/corpus/test_pr15_*.py` placement +
`tests/corpus/fixtures/fix_multi_survivor_mismatch.py`
placement fall within the corpus-subtree auto-exclusion
scope; no allowlist modification needed.

### 8.2 Layer 2 — four-walker partition no modification

PR 15 does NOT add a fifth walker, NOT modify any of the
four existing walkers, NOT modify the walker-partition
boundary semantics (per framing §8.2 + Gate 4 framing §8.2
+ Gate 3 close §1.4 + PR 13 spec §8.2 + PR 14 spec §8.2 +
class member #5 lock).

The four walkers:

- PR 4 walker — Production-import-topology.
- PR 8 walker — Orchestration-participation (5-symbol
  bounded toolbox).
- PR 9 walker — Declarative-fixture-data (single-symbol-
  gate).
- PR 10 walker — Read-only-interpretive-authority (zero-
  symbol-gate).

**Why unchanged:** PR 15's fixture is data-only (member #9);
PR 15's test invokes already-existing seam paths (PR 11
recomposition arc consumption pattern). No new walker
operational requirement at PR 15.

**Target-disjointness verification at close:** PR 15 fixture
+ test do NOT trigger walker traversal logic. The four
walkers' regression at Step 3 phase-end condition 9.X
verifies the target-disjointness preserves.

### 8.3 Layer 3 — unchanged

PR 15 does NOT modify `tests/corpus/test_pr6_visual_asymmetry.py`
or any Layer 3 lint surface (per framing §8.3 + Gate 4
framing §8.3 + PR 13 spec §8.3 + PR 14 spec §8.3 + spec §2
item 24).

**Why unchanged:** Layer 3 lint operates against
`emit_divergence_capture` call sites at chat_handler. PR 15
test invokes `drive_seed_fixture` (which internally calls
`emit_divergence_capture` once per fixture invocation); no
new call-site surface at PR 15 production code.

**Layer 3 regression target:** 17/17 passed at PR 15 close
(unchanged from PR 14 close).

---

## 9. Resume protocol (for future archaeology)

If a future session resumes PR 15 implementation mid-flight
(after Step 1 but before close), the resume protocol
follows:

1. **Read this spec first.** §0 + §1 + §2 + §6 carry the
   load-bearing implementation context.
2. **Read PR 15 framing** (`A.5.3.2-PR15-FRAMING.md`, 1964
   lines) for the binding pre-spec contract.
3. **Read PR 14 close artifact**
   (`A.5.3.2-PR14-CLOSE.md`, 1421 lines) for the immediate
   predecessor — second calibration substrate + parallel-
   not-regenerative pattern introduction + Direction A
   authored-superset precedent (which PR 15 inverts).
4. **Read PR 13 close artifact**
   (`A.5.3.2-PR13-CLOSE.md`, 1247 lines) for the first
   calibration substrate + PR-of-origin precedents (pure-
   isolation + both-skeletons-at-Step-1).
5. **Confirm state:**
   - HEAD at `<expected-commit>` per the PR 15 commit chain
     summary at Step 3 (or in this spec's §6.X if Step 3
     not yet committed).
   - Working tree clean (AGENTS.md untracked OK).
6. **Verify Step N inheritance:**
   - If Step 1 committed: both files at skeleton state with
     full module docstrings + `from __future__ import
     annotations`.
   - If Step 2 committed: both files at architectural-center
     state with FIXTURE dict + test body + full imports.
7. **Resume at next Step:**
   - Step 2 after Step 1: implement per §4.1.2 (FIXTURE
     dict) + §4.2.2 + §4.2.3 (test body).
   - Step 3 after Step 2: empty commit per §6.3.
   - Close commit after Step 3: **PAIRED PR 15 close +
     Gate 4 close at same commit** per §6.4 (DIFFERENT
     cadence from PR 13 + PR 14 standalone closes).

**Surface inventory at PR 15 close (target):**

- 2 new test/fixture files.
- 4 commit-chain artifacts at the PR 15 chain (spec +
  Step 1 + Step 2 + Step 3 + paired close).
- 5 PR 15 commit-chain surfaces accumulating toward close-
  time archaeology (per Step 1, 2, 3 commit body
  inventories + the close artifact commit body + this
  spec). **+1 surface accessible via same-commit-pairing
  (Gate 4 close body), totaling 6 surfaces.**
- Target line counts:
  - PR 15 fixture: ~90–115 lines.
  - PR 15 test: ~125–160 lines.
  - PR 15 close artifact: ~1100–1400 lines (parallel to
    PR 13 close at 1247 lines + PR 14 close at 1421
    lines).
  - Gate 4 close artifact: target shape parallel to Gate
    2 close + Gate 3 close (~800–1200 lines, gate-arc-
    synthesis-shaped).

**PR-12 trigger surface evaluation responsibility resume:**

The PR-12 trigger surface evaluation responsibility encoded
at framing §5.12 lives at PR 15 close §1 inventory. The
resume protocol must include:

- Step 2 commit body: register actual join call-site count
  contribution (1 site) + qualitative second-clause pressure
  observation (SURFACE / ABSENCE) per framing §5.12.
- Step 3 commit body: finalize the PR-12 trigger surface
  evaluation inputs per framing §9.4.
- Gate 4 close: consume the evaluation inputs for final
  PR-12 disposition decision per framing §5.12 (PROMOTION /
  DEFERRAL PRESERVED / REJECTION; three disposition options
  per Gate 4 framing §5.10).

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
   ontological questions unbinding; **first operational
   instance of same-commit-pairing pattern** PR 15 close +
   Gate 4 close inherits as third operational instance.
9. `A.5.3.2-GATE-3-FRAMING.md` — Path B locked precedent;
   binding framing clarification on cross-surface unbinding.
10. `A.5.3.2-PR10-CLOSE.md` — comparator surface operational;
    §4.2 binding behavioral commitment; class member #10.
11. `A.5.3.2-PR11-CLOSE.md` — recomposition arc operational;
    PR-11-LOCAL discipline at gate level; consumption
    pattern; **3-call-site contribution to PR-12 trigger
    surface evaluation cumulative count.**
12. `A.5.3.2-GATE-3-CLOSE.md` — gate-arc synthesis; carrier
    #16 promotion; 10-member class promotion; 17 active
    carriers; four-walker Layer 2 partition; conditional
    PR 12 DEFER (PR 15 reopens evaluation per Gate 4 framing
    §5.10 + §10 PR 15 binding); **second operational
    instance of same-commit-pairing pattern** PR 15 close +
    Gate 4 close inherits as third operational instance.
13. `A.5.3.2-GATE-4-FRAMING.md` — gate-level inheritance
    contract; three-PR primary slot structure; PR ordering;
    §10 PR 15 sub-section; §11.8 same-commit Gate 4 close
    pattern.
14. `A.5.3.2-PR13-FRAMING.md` — first-of-three primary PR
    framing precedent; 11-section framing shape; citation-by-
    reference discipline.
15. `A.5.3.2-PR13-SPEC.md` — fixture + test implementation
    contract precedent; 11-section spec shape; locked-
    mergeability-anchors discipline; both-skeletons-at-
    Step-1 lifecycle invariant.
16. `A.5.3.2-PR13-CLOSE.md` — first calibration point
    predecessor; PR-13-LOCAL as PR-of-origin for pure-
    isolation pattern + PR-of-origin for both-skeletons-
    at-Step-1 lifecycle invariant; 3-form-ABSENCE Placement
    A contribution; four-PR architectural sufficiency
    escalation.
17. `A.5.3.2-PR14-FRAMING.md` — second-of-three primary PR
    framing precedent; Direction A authored-superset
    rationale precedent (§5.10 three-reason argumentation
    pattern; PR 15 §5.10 inverts to authored-subset
    Direction A INVERSE as SECOND corroboration);
    `"list"`-as-calibration-prompt archaeology elevation
    (§4.6); both-skeletons-at-Step-1 second operational
    instance.
18. `A.5.3.2-PR14-SPEC.md` — second-of-three primary PR
    spec precedent; 11-section / ~30-subsection spec shape
    precedent at PR 15.
19. `A.5.3.2-PR14-CLOSE.md` — **immediate predecessor;
    second calibration substrate.** PR-14-LOCAL parallel-
    not-regenerative scope-local discipline at second
    calibration point (PR 15 second corroboration); 3-form-
    ABSENCE SECOND Gate 4 PR instance (PR 15 expected
    THIRD instance); three-fold catch-shape continuation
    precedent (§1.8); five-PR architectural-sufficiency
    escalation evidence (PR 15 extends to six-PR).
20. `A.5.3.2-PR15-FRAMING.md` — **immediate predecessor;
    PR 15 third-calibration-point framing.** PR-15-LOCAL
    binding statement + 6 binding decisions + 17 carriers
    inheritance + cleanup-pressure-resistance class
    inheritance + §2.4 architectural commitment travel +
    9-step traversal annotation pattern + Direction A
    INVERSE affirmative architectural decision + PR-12
    trigger surface evaluation responsibility encoded +
    same-commit-paired close cadence asymmetry +
    `"list"`-as-calibration-prompt archaeology four-PR
    cumulative.
21. **This spec artifact** — PR 15 implementation contract.

**Forward references (post-spec artifacts):**

- PR 15 Step 1, 2, 3 commits — per §6.1–§6.3.
- `A.5.3.2-PR15-CLOSE.md` — PR 15 close artifact (same-
  commit-paired with Gate 4 close per Gate 4 framing
  §11.8 + PR 14 close §7 deferral).
- `A.5.3.2-GATE-4-CLOSE.md` — Gate 4 close artifact (same-
  commit-paired with PR 15 close; gate-arc synthesis).

**Implementation file references (grounding):**

- `tests/corpus/fixtures/fix_multi_match.py:105-140` — PR 9
  multi-match arbitration trace; PR 15 fixture inherits the
  trace as observation grounding.
- `tests/corpus/fixtures/fix_multi_match.py:126` — PR 9
  observation list-literal source line; PR 15's
  `expected_narrow[0]` (`forge_list_projects`) grounds
  against the first element on this line.
- `tests/corpus/test_pr9_fixture_integration.py:208-213` —
  `_PR9_REACHABLE_TOOLS` declared order; PR 15 inherits
  the reachable-tool set verbatim.
- `tests/corpus/fixtures/fix_ordering_divergence.py` — PR 13
  fixture (149 lines); PR 15 fixture mirrors the structural
  shape (one divergence vector + pure-isolation property
  enumeration + authored-expectation rationale).
- `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
  — PR 14 fixture (207 lines); PR 15 fixture mirrors the
  structural shape (authored expectation varies: PR 14
  superset vs. PR 15 singleton subset).
- `tests/corpus/test_pr13_ordering_divergence.py:150-203` —
  PR 13 test 9-step traversal annotation pattern; PR 15
  test mirrors.
- `tests/corpus/test_pr14_partial_narrow_divergence.py:172-226`
  — PR 14 test 9-step traversal annotation pattern; PR 15
  test mirrors. PR 14 test 252 lines; PR 13 test 224 lines.
- `tests/corpus/test_pr11_recomposition_arc.py` — PR 11
  recomposition arc consumption pattern; PR 15 inherits
  via PR 13 + PR 14 inheritance chain.
- `forge_bridge/corpus/_compare.py:503` — comparator's
  direct list-equality semantics (`obs_decision !=
  exp_narrow`); PR 15 exercises the line under multi-
  survivor cardinality divergence pressure (length
  asymmetry (1 vs 2) + element-membership asymmetry at the
  non-shared position both contribute to the inequality).

**Memory cursor references:**

- `feedback_ground_specs_in_actual_files.md` — operative
  discipline at every spec assertion about existing file
  shape; applied at PR 15 spec drafting time pre-spec-lock
  (zero grounding catches surfaced per §0; catch-shape
  continuation of instance #3 zero-amendment clean
  propagation).
- `feedback_counts_are_archaeology_grade.md` — operative at
  every count assertion (219 baseline; 220 target; 17
  active carriers; 10-member class; 19 `__all__` symbols;
  9-step traversal pattern; 9-surface §2.4 close inventory;
  PR-12 trigger surface 6-call-site cumulative target;
  six-PR architectural sufficiency escalation).
- `feedback_writers_room_lead_with_views.md` — operative at
  spec drafting structural seams (Direction A INVERSE
  spec-level expression at §1 + §4.1 + §4.2 + §5.10
  rationale; PR-12 trigger surface evaluation responsibility
  spec-level expression at §2 + §4.2.4 + §6.2 + §6.3 + §6.4
  + §9; same-commit-paired close cadence asymmetry spec-
  level expression at §6.4 + §7 + §9).
- `feedback_deferral_first_class_governance.md` — same-
  commit-paired close discipline at PR 15 close + Gate 4
  close inherits from Gate 2 + Gate 3 close precedents +
  Gate 4 framing §11.8; PR-12 final disposition deferral
  to Gate 4 close per framing §5.12 is first-class
  governance action.
- `feedback_explicitly_unbound_vs_implicitly_rejected.md` —
  cross-surface unbinding + citation-by-reference travel
  discipline at PR 15 spec inheritance; PR-12 disposition
  deferral is intentional-unbound-pending-Gate-4-close
  language, NOT implicit rejection.
- `feedback_cursor_before_retrospective_synthesis.md` —
  operative at PR 15 spec close (cursor before PR 15
  implementation begins; planned at next session boundary)
  + at PR 15 close + Gate 4 close pairing (cursor before
  gate-arc retrospective synthesis at Gate 4 close).
- `feedback_decomposition_recomposition_validation_arc.md`
  — operative at Gate 4 close evaluation surface (Gate 4
  is the third reliability gate; the recomposition arc
  completes its cumulative validation across the three-PR
  primary slot structure; cleanup-pressure-resistance class
  members PR 15 enumerates at §5.4 close the cleanup-
  pressure-form enumeration cycle for Gate 4 substrate).
- `feedback_deferral_first_class_governance.md` —
  PR-12-conditional-disposition operational deferral at
  Gate 4 close is governance-as-architecture; treating
  the deferral as ornamental would erode the architecture.
- `project_three_architectural_layers.md` — Layer 2 walkers
  + Layer 3 lint regression sweep evidence persists; PR 15
  is target-disjoint from all four walkers + Layer 3 lint
  (verified at §8).
