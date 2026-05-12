# A.5.3.2 PR 14 — Spec (partial-set divergence as Gate 4 calibration exercise)

**Status:** Spec-stage artifact for PR 14 of Gate 4. PR 14
framing locked at `30412a3` (2458 lines); this spec derives
the implementation contract by finalizing the symbol-level
decisions named in the framing's five binding decisions
(§5.1–§5.11) — fixture filename + symbol export name +
`fixture_id` + prompt selection + authored expectation
element list + test module filename + test function name +
assertion contract. All decisions inherit ground from PR 9
multi-match arbitration trace at `fix_multi_match.py:105-140`
+ `_PR9_REACHABLE_TOOLS` declared order at
`test_pr9_fixture_integration.py:208-213` + comparator's
direct list-equality at `_compare.py:503`.

PR 14 is the second of three primary PRs sequenced within
Gate 4 per Gate 4 framing §10. **PR 14 close artifact ships
standalone at its own commit** (NOT same-commit with Gate 4
close). Per Gate 4 framing §11.8 + PR 13 close §7 precedent,
Gate 4 close pairs at same-commit with the final primary PR
close (PR 15 close, OR PR 12 close if PR 12 materializes
last) per Gate 2 + Gate 3 close precedent. PR 14's close
commit closes PR 14 alone.

This spec's job: derive file-level precision from framing's
locked decisions. Two new files at PR 14:
`tests/corpus/fixtures/fix_partial_narrow_divergence.py`
(new fixture) +
`tests/corpus/test_pr14_partial_narrow_divergence.py` (new
test module containing exactly one named test). The spec's
outputs are mergeability anchors — file paths, function
names, test names, assertion contracts, exact docstring
shape, exact commit-body sections — that PR 14 close §6 will
verify against.

**Gate 4 architectural commitment (travels at this spec body
+ all PR 14 commit message bodies under "architectural
commitment" sections; deliberately NOT in fixture/test
docstrings per Gate 4 framing §2.4 binding + PR 14 framing
§3.6 + §5.6):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Seventeen active carriers** travel into PR 14's surface
(same set Gate 4 framing locked at §3.1 + PR 13 spec §0 +
PR 14 framing §3.1; no new carriers introduced at PR 14 per
Gate 4 framing §3.1 + §6.1 + §7 item 13 + PR 14 framing §3.1
+ §7 item 7). Composition unchanged: 15 inherited carriers
(#1–#15) + carrier #16 (active, promoted at Gate 3 close
§1.6 — *"Reliability work proves topology, not
infrastructure"*) + carrier #17 (active from Gate 3 framing
§5.1 — recomposition discipline).

**Reference discipline (binding per Gate 4 framing §3.1 +
PR 14 framing §3.1):** *"17 active carriers"* is canonical
phrasing post-Gate-3-close-promotion. PR 14 surfaces travel
carriers in natural numeric ordering WITHOUT substrate
marking. The candidate-substrate marking discipline retired
at Gate 3 close.

### Carrier travel form at PR 14 module docstrings — citation by reference

PR 14 spec interprets the framing §3.1 "17 carriers travel
verbatim" discipline as **verbatim citation to canonical
sources** (mirroring PR 11 spec §0 + PR 13 spec §0
interpretation; per DRY + canonical-source discipline). The
17 carriers + Gate 2 binding framing clarification +
inherited PR-LOCAL bindings travel by reference to:

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

This interpretation choice continues the PR 11 + PR 13
citation-by-reference precedent. PR 14 adopts the lower-DRY
form unchanged.

### Verbatim travel — PR-14-LOCAL binding statement

The **PR-14-LOCAL binding statement** travels verbatim at:

1. `tests/corpus/test_pr14_partial_narrow_divergence.py`
   module docstring (Step 1 surface).
2. `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
   module docstring (Step 1 surface).
3. All PR 14 commit message bodies under "preserved
   invariants" / "PR-14-LOCAL" sections.
4. This spec §0 + §1 + §2 (verbatim form below).

**PR-14-LOCAL binding statement (verbatim — pure-isolation
discipline):**

> **PR 14 isolates partial-set divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 14 scope —
> combining partial-set with ordering, semantic-normalization,
> duplicate-handling, multi-survivor-cardinality, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 14 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

**PR-13-LOCAL as PR-of-origin reference (binding per PR 14
framing §3.10 + §5.5 + PR 13 close §2.2):** PR-14-LOCAL
references PR-13-LOCAL as PR-of-origin for the pure-isolation
discipline pattern. The reference is structural — PR-14-LOCAL
is parallel scope-local discipline appropriate to partial-set
divergence, not a regeneration of PR-13-LOCAL's ordering-
isolation form. PR-13-LOCAL does NOT travel to PR 14
surfaces directly; the pattern (single-vector fixture
pressure as laboratory-grade calibration substrate)
inherits as architectural-substrate evidence.

### Verbatim travel — §2.4 Gate 4 architectural commitment

The **§2.4 Gate 4 architectural commitment** travels
verbatim at (per Gate 4 framing §2.4 binding + PR 14 framing
§3.6 + §5.6):

1. This spec §0 (above the line) + §1 + §2 architectural
   commitment section.
2. All three PR 14 step commit message bodies under
   "architectural commitment" sections.
3. PR 14 close artifact §1 + §6.5 (or equivalent
   architectural-commitment + architectural-sufficiency
   sections).

**Travel deliberately stops short of fixture/test
docstrings.** The §2.4 sentence is gate-shaped architectural
posture, NOT carrier-shaped governance. Carriers travel
through fixture/test docstrings; the §2.4 commitment does
not. The asymmetry preserves the carrier / governing
sentence / methodology-stack category integrity Gate 4
framing established + PR 13 close §1.5 operationally
verified.

**§2.4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

### Spec-drafting-time grounding catch — convergence pass outcome

Per Gate 3 close §1.8 + PR 13 close §1.8 + PR 14 framing
§3.9 inheritance, the catch-point-migration candidate
methodology accumulated five descriptive instances at PR 14
framing landing:

1. PR 9 grounding-time amendment (implementation post-Step-1).
2. PR 10 grounding-time amendment (implementation-prep).
3. PR 11 framing-spec drafting time (zero amendments).
4. PR 13 framing-convergence-pass file-grounding pre-commit
   (six file-grounding catches).
5. PR 13 spec-drafting-time pre-spec-lock (fixture-cardinality
   grounding; single-corroboration per recursive-self-
   governance).

**PR 14 framing-convergence-pass pre-commit (post-framing
draft):** Four grounding catches landed pre-commit at PR 14
framing convergence pass (per PR 14 framing-landed cursor +
PR 14 framing commit body §catch-point migration paragraph).
The four catches are **catch-shape continuation of instance
#4** (PR 13 framing convergence pass; framing-convergence-
pass pre-commit catch-point) — NOT inflated into a new
methodology instance per evidence-inflation rejection
discipline (PR 13 close §1.8 recursive-self-governance
precedent operationalized at PR 14 framing). The four catches
are uniformly: structural (artifact fidelity to grounded
reality), grounding-derived (caught by reading actual
files), pre-commit (caught before framing landing), and
non-architectural (none altered architectural intent).

**PR 14 spec-drafting-time outcome:** This spec's drafting
inherits PR 14 framing's grounded substrate. PR 14 framing
performed framing-time file-grounding (forge_ping membership
in `_PR9_REACHABLE_TOOLS`; partial-set extension element
orthogonality to prompt tokens; observation list verbatim
from PR 9 multi-match arbitration trace) at framing-time. At
spec-drafting-time pre-spec-lock, **one grounding catch
surfaced**: spec table §4.1.2 initially cited
`fix_multi_match.py:127` and `:128` as the source lines for
the two observation list values (`forge_list_projects` +
`flame_list_libraries`). Re-grounding against the actual
file showed both values appear on a single list-literal line
at `fix_multi_match.py:126`. The citations were corrected
pre-commit.

**This is catch-shape continuation of instance #5** (PR 13
spec-drafting-time pre-spec-lock catch-point; single-
corroboration catch-shape), NOT inflation into a new
methodology instance #6. Per the recursive-self-governance
discipline (PR 13 close §1.8 precedent operationalized at
PR 14 framing): the distinguishing property of the migration
candidate is "the catch migrates earlier in the lifecycle,"
not "every individual catch becomes a separately counted
corroboration." Instance #5's catch-shape (spec-drafting-time
grounding catch caught pre-spec-lock) now has two corroboration
sub-instances (PR 13 fixture-cardinality grounding + PR 14
line-number-citation grounding); both share the same catch-
point + catch-shape. The progression remains **five-instance
descriptive at PR 14 spec landing**.

Progression as of PR 14 spec landing:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Single corroboration (fixture-cardinality grounding) |
| 5 (continuation) | PR 14 framing | Framing-convergence-pass pre-commit | Catch-shape continuation of instance #4 (four file-grounding catches) |
| 5 (continuation) | PR 14 spec | Spec-drafting-time pre-spec-lock | Catch-shape continuation of instance #5 (one line-number-citation grounding catch) |

PR 14 close §1 records the spec-drafting-time outcome as
contributing instance toward Gate 4 close's catch-point
migration evaluation per Gate 4 framing §11.5.

---

## 1. Real job (PR 14 in one paragraph)

PR 14 ships **two new files** containing **exactly one named
test** that exercises a partial-set divergence pure-isolation
case through the full end-to-end recomposition arc:

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

The fixture authors `expected_narrow` as the **authored-
superset** (Direction A per framing §5.10): the observation's
two members at positions 0+1 verbatim PLUS `forge_ping` at
position 2 as the partial-set extension element. The
comparator's compare-as-persisted discipline (PR 10 §4.2
binding behavioral commitment) detects the partial-set
divergence at direct list-equality (`obs_decision !=
exp_narrow` per `_compare.py:503`) via length asymmetry
(2 vs 3) + element-membership asymmetry at position 2. No
sort / canonicalization / semantic coercion / overlap-aware
computation at any traversal seam. The test asserts the
four-key `DivergenceReport` structural shape with explicit
per-surface partitioning (carrier #17 at use) +
`narrow_diverged=True`.

**Gate 4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**Regression contracts at PR 14 close (10 items):**

1. PR 14 suite (`test_pr14_partial_narrow_divergence.py`):
   1/1 passed.
2. PR 4 + PR 5 + PR 6 + PR 7 + PR 8 + PR 9 + PR 10 + PR 11
   + PR 13 suites pass unchanged.
3. PR 3 discipline passes unchanged (no `_ALLOWLIST`
   modification per §8.1).
4. Four Layer 2 walkers (PR 4 + PR 8 + PR 9 + PR 10) pass
   unchanged.
5. Layer 3 lint (`test_pr6_visual_asymmetry.py`) passes
   unchanged.
6. Full corpus suite: **219 forge env collected** (218
   baseline + 1 PR 14 new).
7. Console tests + Public API anchor (`forge_bridge.__all__`
   at 19 symbols) unchanged.
8. Verbatim carrier travel: 17 carriers cited by reference +
   PR-14-LOCAL verbatim at both PR 14 module docstrings +
   PR 14 commit message bodies.
9. §2.4 Gate 4 architectural commitment travels verbatim at
   this spec §0 + §1 + §2 + all 3 PR 14 step commit message
   bodies under "architectural commitment" sections + PR 14
   close artifact (NOT at fixture/test docstrings).
10. **Architectural sufficiency signal: 0 production source
    modifications across PR 14's commit chain.**

---

## 2. In-scope / out-of-scope

### In scope (PR 14)

- New file:
  `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
  containing module docstring (carrying PR-14-LOCAL + 17
  carriers by reference + grounded arbitration trace +
  fixture purpose with Direction A rationale) + `from
  __future__ import annotations` + `FIXTURE` dict with three
  keys (`fixture_id`, `prompt`, `expected_narrow`).
- New file:
  `tests/corpus/test_pr14_partial_narrow_divergence.py`
  containing module docstring (carrying PR-14-LOCAL + 17
  carriers by reference + traversal trace + test
  infrastructure import discipline) + imports + 1 named
  test (`test_recomposition_arc_partial_narrow_divergence`).
- IMPORT of PR 9 test infrastructure (`_apply_pr9_patches`,
  `_read_records`) from
  `tests.corpus.test_pr9_fixture_integration` as
  **test-internal archaeology surfaces** (not public APIs;
  inherited from PR 11 + PR 13 pattern).
- PR 14 commit message bodies carrying "architectural
  commitment" + "preserved invariants" + "PR-14-LOCAL" +
  "Placement A/B substrate contribution" sections per the
  PR 13 commit-body pattern adapted for PR 14 scope.

**Gate 4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**PR-14-LOCAL binding statement (verbatim per §0 + framing
§5.5):**

> **PR 14 isolates partial-set divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 14 scope —
> combining partial-set with ordering, semantic-normalization,
> duplicate-handling, multi-survivor-cardinality, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 14 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

### Out of scope (architecturally-prohibited at PR 14)

PR 14 inherits the framing §7 22-item non-acquisition list
in full + adds spec-layer enforcement:

1. **Any production source file modification.** Framing
   §5.3 binding decision; framing §7 item 6 inherited from
   Gate 4 framing. Justified deviations register as
   archaeology at PR 14 close per framing §5.11 justified-
   deviation protocol, not silent additions.
2. **Authoring multi-vector fixture pressure.** Framing
   §5.1 + §5.5 PR-14-LOCAL binding; framing §7 items 1 + 5
   + 6 + 7 (while-we're-here ordering + duplicate +
   semantic-normalization rejections). The fixture isolates
   partial-set divergence as the sole pressure vector.
3. **Authoring the symmetric-direction (Direction B)
   variant** at spec layer. Framing §4.4 + §5.10 + §7
   item 2 + §7 item 20 evidence inflation rejection.
   Direction A (authored-superset) locked at framing per
   §5.10 affirmative architectural decision.
4. **Modifying the comparator surface**
   (`compare_records` / `DivergenceReport` /
   `ComparatorInputError`). Framing §5.7 binding + §7
   item 3 + Gate 3 close §3 item 2.
5. **Adding a `partial_match` field to `DivergenceReport`.**
   Framing §5.4 predicted-form 2 + §5.7 + §7 item 3 +
   §7 item 21. The comparator surface preserves at PR 10
   spec §4.1.6 reference implementation.
6. **Adding "while we're here" elements** (ordering /
   duplicate handling / semantic normalization to the
   partial-set fixture). Framing §5.4 + §5.5 PR-14-LOCAL +
   §7 items 1 + 9 (rejecting "while we're here" pressure
   forms).
7. **Modifying existing PR 9 fixtures or PR 13 fixture.**
   Framing §7 item 13 + §7 item 14 + §7 item 17 (no
   `_PR9_REACHABLE_TOOLS` modification; no PR 9 multi-match
   arbitration trace modification; no test-internal
   archaeology surface modification).
8. **Re-authoring `_apply_pr9_patches` or `_read_records`**
   with modified semantics. Framing §7 item 17.
9. **Promoting PR 9 underscored helpers to public APIs.**
   Framing §7 item 17 + Gate 3 close §3 item 10.
10. **Introducing a test-helper function** that absorbs the
    recomposition traversal. Framing §7 item 9; framing
    §5.4 predicted-form 3 suppression at use. PR 14 test
    body inlines the 9-step traversal annotation pattern.
11. **Introducing caller-side overlap-aware computation**
    (e.g., `overlap = set(authored) & set(observed)`,
    `partial_match = bool(overlap)`) in PR 14 test body.
    Framing §7 item 21; framing §5.4 predicted-form 2
    suppression at use.
12. **Using set-equality assertion shortcuts** (e.g.,
    `assert set(observed) == set(expected)`) in PR 14 test
    body. Framing §5.4 predicted-form 1 suppression at use.
    The four-key DivergenceReport assertion contract
    preserves the structural shape (length + ordering +
    membership at full fidelity).
13. **Asserting `narrow_diverged=True` only** without
    asserting the structural list values. Framing §5.4
    predicted-form 1 + §9.4 close-time verification.
    Partial-match-to-full-divergence collapse pressure
    rejected.
14. **Adding a fourth structural field to the expectation
    record schema** (e.g., `expected_partial_match`,
    `expected_subset_of_observation`). Framing §5.4
    predicted-form 3 + §7 item 5 + §7 item 11 + Gate 2
    close §2.4 item 5 inheritance. Schema preserves at
    exactly three required keys.
15. **Introducing a new `record_kind`.** Framing §7 item 5
    (implicit; expectation record schema unchanged) +
    Gate 2 close §2.4 inheritance.
16. **Extending `KNOWN_SOURCE_VALUES`** or `_KNOWN_RECORD_KINDS`.
    Framing §7 items inherited from Gate 2 close §2.4
    items 3 + 4.
17. **Modifying the three-authority-surface partition.**
    Framing §3.2 + Gate 4 framing §3.2 + Gate 3 close §1.3
    inheritance.
18. **Authoring a fifth walker.** Framing §8.2 + Gate 3
    close §1.4 + Gate 4 framing §3.3 inheritance.
19. **Adding cleanup-pressure-resistance class members
    speculatively** at framing/spec time. Framing §3.7 +
    §9.10. Class members surface at PR 14 close based on
    actual implementation pressure encountered.
20. **Introducing a candidate carrier (#18)** at PR 14.
    Framing §7 item 7.
21. **Speculatively authoring a Gate-4-LOCAL governing
    sentence.** Framing §7 item 8 + Gate 4 framing §7
    item 22 inheritance.
22. **Pre-binding Placement A outcome predictions** at
    framing/spec. Framing §6.1 + §9.4. Outcomes register
    at PR 14 close based on actual encountered pressure.
23. **Pre-binding PR 12 disposition** at PR 14 framing/spec.
    Framing §7 item 18 + Gate 3 close §1.9 + Gate 4
    framing §5.7 inheritance.
24. **Touching the Layer 3 lint**
    (`test_pr6_visual_asymmetry.py`). §8.3 explicit.
25. **Modifying `divergence_capture_enabled()` or its
    env-gate.** Inherited from PR 13 spec §2 item 24.
26. **Speculative-reserved imports.** Per cleanup-pressure-
    resistance class member #10; imports land when first
    used at Step 2 implementation (spec §4.2.2 + §6.2).
27. **Cross-surface vocabulary in test names or
    docstrings.** Per framing §5.4 predicted-form 2
    suppression + PR 13 spec §2 item 27 inheritance. No
    `task_outcome` / `prompt_resolution` field names; no
    `partial_match` / `overlap_count` / `cardinality_class`
    field names.
28. **`forge_bridge.__all__` modification.** Framing §5.8
    binding + §7 item 4. Stays at 19 symbols.
29. **Layer 1 `_ALLOWLIST` modification.** §8.1 explicit;
    corpus-subtree auto-exclusion semantics inherited from
    PR 10 §4.4.
30. **Layer 2 walker addition.** §8.2 explicit; no fifth
    walker.
31. **Surfacing the four §7.3 ontological questions.**
    Framing §7 item 19 + Gate 4 framing §5.2 + Gate 2
    close inheritance. The four §7.3 questions remain
    intentionally unbound.
32. **Cross-surface comparator semantics introduction.**
    Framing §7 item 22 + Gate 3 framing binding clarification
    on cross-surface unbinding + PR 13 framing §7 item 22.
33. **Modifying prompt selection.** Framing §4.6 + §5.10 +
    §7 item 12. Prompt `"list"` locked per single-variable-
    discipline preservation across PR 9 / PR 13 / PR 14.
34. **Modifying authored expectation element selection.**
    Framing §4.1 + §5.1 + §5.10. Authored expectation
    locked at three elements: `forge_list_projects`,
    `flame_list_libraries`, `forge_ping`.
35. **Introducing a multi-token prompt** or modifying
    `_PR9_REACHABLE_TOOLS` to enable Direction B variant.
    Framing §5.10 + §7 items 12 + 13. Both rejected at
    affirmative-architectural-decision layer.

---

## 3. Files modified / created at PR 14

| File | Disposition | Lines (final at PR 14 close) |
|---|---|---|
| `tests/corpus/fixtures/fix_partial_narrow_divergence.py` | **NEW** | ~95–115 |
| `tests/corpus/test_pr14_partial_narrow_divergence.py` | **NEW** | ~125–155 |
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
| `tests/corpus/fixtures/fix_*.py` (PR 9 + PR 13 fixtures) | NOT MODIFIED (PR 9 + PR 13 fixtures stable archaeology) | 0 |
| `tests/corpus/conftest.py` | NOT MODIFIED | 0 |

**Two new files. Zero modifications to any production source
or existing test/fixture file.** The 0-prod-mod-outside-the-
new-test-and-fixture-files outcome IS the architectural
sufficiency signal PR 14 demonstrates (framing §5.3 + §9.3).

PR 14 extends the four-PR architectural sufficiency escalation
(PR 9 + PR 10 + PR 11 + PR 13) to **five-PR escalation** if
the 0-prod-mod target holds at PR 14 close (per PR 14 framing
§5.3 + §9.3 + PR 13 close §1.3 inheritance).

---

## 4. Per-file derivation

### 4.1 `tests/corpus/fixtures/fix_partial_narrow_divergence.py` — new fixture

#### 4.1.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering — most
load-bearing at TOP per PR 8 spec §0 travel rule + PR 13
spec §4.1.1 + PR 14 framing §3.1):

1. **One-line summary**: `"""Seed fixture — partial-set divergence pure-isolation case at the chat-handler observation surface."""`
2. **Blank line.**
3. **PR-14-LOCAL binding statement** (verbatim, per §0 + framing §5.5):

   > PR 14 isolates partial-set divergence as the sole pressure
   > vector. Multi-vector fixture pressure within PR 14 scope —
   > combining partial-set with ordering, semantic-normalization,
   > duplicate-handling, multi-survivor-cardinality, or any other
   > divergence form — is rejected at the spec layer. The
   > pure-isolation property is what gives PR 14 its
   > laboratory-grade methodology corroboration value for
   > Placement A + Placement B substrate.

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
   `fix_ordering_divergence.py:38-114`):

   ```
   Fixture purpose:

   This fixture exercises the chat-handler-surface partial-
   set divergence pure-isolation case. The prompt ``"list"``
   (single-step shape; does NOT fire chain-step arbitration)
   is identical to PR 9 multi-match's prompt
   (``fix_multi_match.py``) and PR 13 ordering-divergence's
   prompt (``fix_ordering_divergence.py``); the arbitration
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
   observation):

     narrower.decision = ["forge_list_projects",
                          "flame_list_libraries"]

   (verbatim PR14 input order through PR21;
   ``_PR9_REACHABLE_TOOLS`` declared ordering at
   ``test_pr9_fixture_integration.py:208-213``.)

   Expectation record (PR 14 fixture-author choice — the
   authored-superset partial-set divergence vector, Direction
   A per A.5.3.2-PR14-FRAMING.md §5.10):

     expected_narrow = ["forge_list_projects",
                        "flame_list_libraries",
                        "forge_ping"]

   (positions 0+1 share observation's elements at observation
   positions verbatim; position 2 extends with ``forge_ping``
   as the partial-set extension element. ``forge_ping`` is in
   the PR 9 reachable-tool set per
   ``test_pr9_fixture_integration.py:208-213`` but shares NO
   tokens with the prompt ``"list"``. The author asserts:
   "I expected this unrelated tool to survive narrowing.")

   The authored-superset direction is an affirmative
   architectural decision per framing §5.10 — the
   architectural pressure vector under test is overlap-
   interpretation, not directional ownership of the superset
   relation. The temptation toward overlap-aware
   DivergenceReport fields (predicted form 2 at framing §5.4)
   operates symmetrically regardless of which side contains
   the additional element; Direction A is selected for three
   reasons: (1) preserves the single-variable discipline
   across PR 9 / PR 13 / PR 14 — same prompt + same
   reachable-tool set + same arbitration trace + same
   observation; (2) semantically legible authorial claim —
   ``forge_ping`` is orthogonal to prompt tokens, preventing
   collapse into fuzzy keyword semantics; (3) substrate reuse
   preserving the ``"list"``-as-calibration-prompt
   archaeology PR 9 + PR 13 established (framing §4.6).

   The pure-isolation property holds at every dimension
   except the target partial-set vector:

     - Same set membership at intersection: positions 0+1
       contain {forge_list_projects, flame_list_libraries}
       at observation positions verbatim.
     - No ordering divergence at intersection: shared
       elements preserve at observation positions.
     - Cardinality asymmetry IS the partial-set vector:
       expectation length 3 vs. observation length 2. The
       cardinality asymmetry and the partial-set vector are
       the same architectural-pressure-surface phenomenon,
       not two separate confounds (per framing §2.4 + §4.3
       clarification).
     - No semantic-normalization divergence: tool names are
       exact-match identifiers; no canonical-form
       transformations involved.
     - No duplicate-handling divergence: each list contains
       distinct elements.
     - No multi-survivor cardinality confound: both lists
       are multi-element (>1); the cardinality-class
       divergence vector is PR 15's substrate, not PR 14's.

   The comparator's compare-as-persisted discipline (PR 10
   §4.2 binding behavioral commitment) detects the partial-
   set divergence as ``narrow_diverged=True`` per direct
   list-equality at ``_compare.py:503`` (``obs_decision !=
   exp_narrow``; length asymmetry (2 vs 3) + element-
   membership asymmetry at position 2 both contribute to
   the inequality; no sort, no canonicalization, no semantic
   coercion, no overlap-aware computation at any traversal
   seam).

   This fixture differs from PR 9 multi-match
   (``fix_multi_match.py``) and PR 13 ordering-divergence
   (``fix_ordering_divergence.py``) at exactly one surface:
   the authored expectation. PR 9 multi-match authors
   ``expected_narrow`` matching observation verbatim
   (no-divergence baseline). PR 13 authors the ordering swap
   (same set, different sequence). PR 14 authors the
   superset extension (same elements at positions 0+1,
   additional element at position 2). The single-variable
   discipline across PR 9 / PR 13 / PR 14 is itself
   architectural-substrate evidence — the comparator surface
   is the only moving interpretive layer across the three-PR
   series (framing §4.6).

   Prompt reuse is NOT collision — fixture identity
   discriminator is ``fixture_id``, not ``prompt``; per-test
   ``tmp_path`` corpus isolation prevents record co-existence
   between PR 9 multi-match's invocation, PR 13 ordering-
   divergence's invocation, and PR 14 partial-set-
   divergence's invocation. The prompt-reuse-without-
   collision discipline is itself architectural evidence
   (PR 13 close §2.1 PR-of-origin archaeology).
   ```

   The arbitration trace recorded above is archaeology-
   grade per
   `feedback_counts_are_archaeology_grade.md`. Future
   contributors diagnosing PR 14 regressions can verify
   against the trace recorded here + the PR 9 multi-match
   trace + the PR 13 ordering-divergence trace.

8. **Blank line.**
9. **References** paragraph citing:

   ```
   References:
     - A.5.3.2-PR14-SPEC.md (this fixture's implementation
       contract).
     - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
     - A.5.3.2-GATE-4-FRAMING.md (immediate gate-level
       inheritance contract).
     - A.5.3.2-PR13-CLOSE.md (PR-13-LOCAL as PR-of-origin
       for the pure-isolation pattern; calibration substrate
       at first calibration point).
     - tests/corpus/fixtures/fix_multi_match.py:105-140
       (PR 9 multi-match arbitration trace; PR 14 inherits
       the trace grounding).
     - tests/corpus/fixtures/fix_ordering_divergence.py
       (PR 13 ordering-divergence fixture; PR 14 mirrors
       the fixture structural shape).
     - tests/corpus/test_pr9_fixture_integration.py:208-213
       (_PR9_REACHABLE_TOOLS declared order including
       forge_ping at index 0).
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

**Total docstring: ~90–110 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent
steps.

#### 4.1.2 Module body (Step 2 contents)

```python
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

**Locked values (binding):**

| Key | Value | Grounding |
|---|---|---|
| `fixture_id` | `"fix-pr14-partial-narrow-divergence"` | Framing §5.9 two-surface form; kebab-case with PR anchor |
| `prompt` | `"list"` | Framing §4.6 + §5.10 single-variable discipline preservation across PR 9 / PR 13 / PR 14 |
| `expected_narrow[0]` | `"forge_list_projects"` | PR 9 multi-match observation position 0 (verbatim from `fix_multi_match.py:126`; both observation values appear on the same list-literal line per arbitration trace section) |
| `expected_narrow[1]` | `"flame_list_libraries"` | PR 9 multi-match observation position 1 (verbatim from `fix_multi_match.py:126`; same list-literal line as position 0) |
| `expected_narrow[2]` | `"forge_ping"` | Partial-set extension element; in `_PR9_REACHABLE_TOOLS` at `test_pr9_fixture_integration.py:209`; orthogonal to prompt `"list"` per framing §4.6 + §5.10 |

The single-symbol module export is `FIXTURE` (canonical name
per framing §3.3 + §5.9 + PR 9 + PR 13 precedent; consuming
test aliases on import).

**Symbol export form lock:** PR 14 fixture exports exactly
one module-level symbol named `FIXTURE`. No additional
constants, no helper functions, no factories. The only
module-level statement beyond the docstring + `FIXTURE`
assignment is `from __future__ import annotations` at the
head of the module body.

**`expected_narrow` list formatting:** the three elements are
formatted across multiple lines (one element per line) per
PEP 8 readability for multi-element list literals + visual
parallelism with the comparator's structural-list output.
The trailing comma after the third element is preserved (PEP
8 + canonical Python convention).

#### 4.1.3 Imports discipline

Imports inventory at PR 14 close (final state):

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

The single-import discipline is structural at PR 14's
fixture file — no imports land at Step 2 because the
`FIXTURE` dict only requires literal-construction syntax
(strings + list of strings + dict literal). Member #9 +
member #10 protections operate symmetrically (parallel to
PR 13 close §1.12).

### 4.2 `tests/corpus/test_pr14_partial_narrow_divergence.py` — new test module

#### 4.2.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering):

1. **One-line summary**: `"""End-to-end partial-set divergence recomposition arc test — fixture → drive_seed_fixture → chat_handler → emission → readback → compare_records → DivergenceReport (narrow_diverged=True)."""`
2. **Blank line.**
3. **PR-14-LOCAL binding statement** (verbatim, per §0 + framing §5.5).
4. **Blank line.**
5. **Traversal trace** (verbatim from PR 14 framing §2.1 +
   parallel to PR 13 spec §4.2.1 site 5):

   ```
   fixture (tests/corpus/fixtures/fix_partial_narrow_divergence.py)
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
   or Gate 3 substrate work. PR 14 traverses the seams under
   partial-set divergence pressure; no helper absorbs the arc
   into a single call (PR-11-LOCAL traverses-not-erases-seams
   inherited at gate level per A.5.3.2-GATE-3-CLOSE.md §3
   item 10).

6. **Blank line.**
7. **Carrier travel — citation by reference paragraph** (per §0; same form as fixture module §4.1.1 site 5).

8. **Blank line.**
9. **Test infrastructure import discipline** paragraph (per
   PR 11 spec §4.1.1 site 11 + PR 13 spec §4.2.1 site 9 +
   framing §9.11 inheritance):

   > PR 14 imports ``_apply_pr9_patches`` and ``_read_records``
   > from ``tests.corpus.test_pr9_fixture_integration`` as
   > **test-internal archaeology surfaces**, NOT as public APIs.
   > The underscored-private status is preserved — the import is
   > test-internal and archaeology-explicit, mirroring the PR 11
   > consumption pattern (``test_pr11_recomposition_arc.py:111-114``)
   > + PR 13 consumption pattern
   > (``test_pr13_ordering_divergence.py:110-113``). This does NOT
   > promote the helpers to public APIs; future contributors must
   > NOT read this as a general invitation to import underscored-
   > private helpers across production modules.

10. **Blank line.**
11. **References** trailing paragraph citing:

    ```
    References:
      - A.5.3.2-PR14-SPEC.md (this module's implementation
        contract).
      - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
      - A.5.3.2-GATE-4-FRAMING.md (immediate gate-level
        inheritance contract; §2.4 architectural commitment).
      - A.5.3.2-PR13-CLOSE.md (PR-13-LOCAL as PR-of-origin
        for the pure-isolation pattern; both-skeletons-at-
        Step-1 lifecycle invariant as PR-of-origin).
      - A.5.3.2-PR11-CLOSE.md (recomposition arc operational
        evidence; PR-11-LOCAL traverses-not-erases-seams
        inherited at gate level per Gate 3 close §3 item 10).
      - A.5.3.2-PR10-CLOSE.md (durable PR 10 archival state;
        PR 10 §4.2 binding behavioral commitment exercised
        under partial-set divergence pressure).
      - tests/corpus/test_pr13_ordering_divergence.py
        (PR 13 test module; PR 14 mirrors the 9-step
        traversal annotation pattern + four-key assertion
        contract).
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

**Step 2 imports landed (final state at PR 14 close):**

```python
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
```

**Seven new imports land at Step 2 (per member 10 discipline
+ PR 13 spec §4.2.2 precedent):**

| Symbol | Source | First-use site at test body |
|---|---|---|
| `pathlib` | stdlib | `tmp_path: pathlib.Path` parameter annotation in test signature |
| `pytest` | external | `monkeypatch: pytest.MonkeyPatch` parameter annotation in test signature |
| `compare_records` | `forge_bridge.corpus._compare` | Step 8 of traversal (comparator invocation) |
| `drive_seed_fixture` | `forge_bridge.corpus._seed` | Steps 2-5 of traversal (orchestration seam invocation) |
| `FIX_PARTIAL_NARROW_DIVERGENCE` (alias for `FIXTURE`) | `tests.corpus.fixtures.fix_partial_narrow_divergence` | Steps 2-5 of traversal (`drive_seed_fixture(**FIX_PARTIAL_NARROW_DIVERGENCE)`) + Step 7 of traversal (fixture_id partition filter) + Step 9 of traversal (assertion comparison list values) |
| `_apply_pr9_patches` | `tests.corpus.test_pr9_fixture_integration` | Step 1 of traversal (monkeypatch suite application) |
| `_read_records` | `tests.corpus.test_pr9_fixture_integration` | Step 6 of traversal (records readback) |

**Import grouping discipline** (per PEP 8 + PR 13 spec
§4.2.2 precedent):

1. `from __future__ import` (one-line group).
2. **Blank line.**
3. Standard library imports (`pathlib`).
4. **Blank line.**
5. External libraries (`pytest`).
6. **Blank line.**
7. Internal package imports
   (`forge_bridge.corpus._compare`, `forge_bridge.corpus._seed`).
8. **Blank line.**
9. Test-package imports (the `FIX_PARTIAL_NARROW_DIVERGENCE`
   alias).
10. **Blank line.**
11. Test-internal archaeology surfaces (the
    `_apply_pr9_patches` + `_read_records` imports). The
    "Test-internal archaeology surfaces (NOT public APIs)"
    comment marker precedes this import block per PR 13
    close §1.13 precedent — explicit underscored-private-
    status registration at the import site.

**No speculative-reserved imports.** No imports land for
"might be useful later" purposes (member #10 protection).

#### 4.2.3 The single test — `test_recomposition_arc_partial_narrow_divergence`

**Test function signature:**

```python
def test_recomposition_arc_partial_narrow_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
```

**Signature contract:**

- Test function name:
  `test_recomposition_arc_partial_narrow_divergence` (locked
  per framing §5.1).
- Fixtures consumed: `clean_rate_limit_state` (from
  conftest.py — chat-handler rate-limit state cleanup) +
  `monkeypatch` (pytest stdlib — for `_apply_pr9_patches`
  invocation) + `tmp_path` (pytest stdlib — for per-test
  corpus dir isolation).
- Return type: `None` (pytest test functions return None;
  raised exceptions signal failure).
- No decorators (no `@pytest.mark.skipif` / `@pytest.mark.parametrize`
  / `@pytest.mark.asyncio` / etc. per framing §5.2 single-test-
  with-no-parametrize lock).

**Test function docstring shape:**

```python
"""Recomposition arc — partial-set divergence pure-isolation case.

Drives ``fix-pr14-partial-narrow-divergence`` through the full
decomposition seam path. The fixture authors
``expected_narrow`` with the observation's two members at
positions 0+1 verbatim PLUS ``forge_ping`` at position 2 as
the partial-set extension element (Direction A per framing
§5.10): PR 9 multi-match deterministic outcome (prompt
"list" produces ``narrower.decision = ["forge_list_projects",
"flame_list_libraries"]``) vs. authored ``expected_narrow =
["forge_list_projects", "flame_list_libraries", "forge_ping"]``
(authored superset by one element at position 2).

The comparator's compare-as-persisted discipline (PR 10 §4.2
binding behavioral commitment) detects the partial-set
divergence as ``narrow_diverged=True`` per direct list-
equality at ``_compare.py:503`` (length asymmetry (2 vs 3)
+ element-membership asymmetry at position 2 both contribute
to ``obs_decision != exp_narrow``). Carrier #17 at use: the
DivergenceReport's per-surface partitioning preserves
authorship through emission → persistence → readback → join
→ interpretive comparison; the partial-set divergence vector
is identifiable at the structural shape level
(``expectation.expected_narrow`` has length 3;
``observation.observed_narrow`` has length 2; shared elements
at positions 0+1 verbatim).

Pure-isolation property at every dimension: partial-set
only — no ordering / semantic-normalization / duplicate-
handling / multi-survivor-cardinality confound.
PR-14-LOCAL pure-isolation discipline binding.

The authored-superset direction (Direction A per framing
§5.10) is an affirmative architectural decision —
``forge_ping`` is in the PR 9 reachable-tool set per
``test_pr9_fixture_integration.py:208-213`` but shares no
tokens with the prompt ``"list"``; the author asserts "I
expected this unrelated tool to survive narrowing,"
producing a semantically legible authorial claim orthogonal
to prompt tokens. The overlap-interpretation pressure
vector is direction-symmetric; Direction A maximizes
substrate reuse + single-variable discipline preservation
across PR 9 / PR 13 / PR 14 (framing §4.6).
"""
```

**Test body 9-step traversal pattern** (six header
comments covering nine logical traversal steps; mirroring
PR 13 test body at `test_pr13_ordering_divergence.py:150-203`):

```python
# ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
# Test-internal archaeology surface (NOT a public API).
corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

# ── Steps 2-5 of traversal: drive fixture → emission ───────
# drive_seed_fixture orchestrates expectation persistence,
# chat_handler arbitration, observation emission. The seam
# traversal is explicit at the call site — no helper absorbs
# the arc (PR-11-LOCAL discipline at gate level per Gate 3
# close §3 item 10 + PR 14 framing §5.4 predicted-form 3
# suppression).
drive_seed_fixture(**FIX_PARTIAL_NARROW_DIVERGENCE)

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
# discipline at gate level).
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
# observation + expectation by fixture_id (Gate 2 close
# §2.1) and produces the DivergenceReport per carrier #17.
# Direct list-equality at _compare.py:503 detects the
# partial-set divergence (length 2 != length 3; element
# mismatch at position 2); no caller-side overlap
# interpretation per PR 14 framing §5.4 predicted-form 1
# suppression (PR 10 §4.2 binding behavioral commitment at
# use).
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
#
# Full-fidelity list assertions (NOT set-equality, NOT
# narrow_diverged-only) per PR 14 framing §5.4 predicted-
# form 1 suppression — set-equality shortcuts mask the load-
# bearing partial-match structural claim; narrow_diverged-
# only shortcuts mask the structural-shape disclosure.
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

**Body structure (binding):**

- 9 logical traversal steps explicitly annotated with 6
  header comments. The structure mirrors PR 13's
  9-step / 6-header pattern verbatim except for the
  partial-set-specific content at Step 8 + Step 9.
- 5 inline call-site comments preceding each assertion or
  call invocation explain the architectural rationale
  (carrier #17 at use; PR 10 §4.2 binding at use;
  predicted-form suppression names).
- Test-internal archaeology surface comment marker (Step 1)
  preserves the underscored-private-status registration at
  the call site.

#### 4.2.4 Assertion contract — four DivergenceReport keys verified

The test body asserts exactly four keys at the
DivergenceReport at full structural fidelity (per framing
§5.4 + framing §4.4 four-key structural assertion contract
inherited from PR 13 + PR 11):

| # | Assertion | Architectural rationale |
|---|---|---|
| 1 | `report["fixture_id"] == FIX_PARTIAL_NARROW_DIVERGENCE["fixture_id"]` | Fixture identity preservation through the recomposition arc (Gate 2 close §2.1 joinability). |
| 2 | `report["expectation"]["expected_narrow"] == ["forge_list_projects", "flame_list_libraries", "forge_ping"]` | Authored expectation list preserved verbatim through emission → persistence → readback → comparator (PR 10 §4.2 binding behavioral commitment at expectation surface). Three-element list asserts the partial-set vector's authored-superset shape at full fidelity. |
| 3 | `report["observation"]["observed_narrow"] == ["forge_list_projects", "flame_list_libraries"]` | Arbitration observation preserved verbatim through chat_handler emission → persistence → readback → comparator (PR 10 §4.2 binding behavioral commitment at observation surface). Two-element list asserts the partial-set vector's observation-subset shape at full fidelity. |
| 4 | `report["divergence"]["narrow_diverged"] is True` | Comparator's direct list-equality detected the partial-set divergence (`_compare.py:503`). Boolean field signals divergence presence; the structural-shape preservation in assertions 2 + 3 IS the partial-match disclosure (no separate `partial_match` field needed; framing §5.4 predicted-form 2 suppression). |

**Three predicted cleanup-pressure forms operationally
suppressed at the assertion contract:**

1. **Partial-match-to-full-divergence collapse pressure**
   suppressed by asserting all four keys explicitly (NOT
   `narrow_diverged=True` only). The structural list values
   in assertions 2 + 3 preserve the partial-match shape at
   full fidelity.
2. **`partial_match` field-addition pressure** suppressed by
   the four-key assertion contract — no fifth key checked,
   no `partial_match` reference, no overlap-aware field.
   The comparator surface preserves at PR 10 spec §4.1.6
   reference implementation per Gate 3 close §3 item 2.
3. **Fixture-shape extension pressure** suppressed by the
   fixture's three-key contract (FIXTURE dict carries
   exactly `fixture_id`, `prompt`, `expected_narrow`). The
   authored expectation list's three-element content carries
   the partial-set intent structurally; no fourth field
   carries declared intent.

**Assertion ordering rationale (binding per PR 13 spec
§4.2.4 precedent):**

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
(Gate 2 close §2.4 item 1; PR 13 close §1.3) — each authority
surface's contribution surfaces explicitly at distinct
assertion sites.

---

## 5. Test count anchors

### 5.1 Forge env test count projection

```
218 baseline (PR 13 close §1.9 forge env collected)
+   1 PR 14 partial-set-divergence test
= 219 forge env collected at PR 14 close
```

Per `feedback_counts_are_archaeology_grade`: 219 is the
locked target at PR 14 close. If the actual count at Step 3
(final verification) differs from 219, spec author must:

- Investigate the divergence (test collection issue?
  parametrize expansion? skip condition? PR 13 baseline
  drift?).
- Amend §5.1 with archaeology before close.
- Document the divergence at PR 14 close §6 (mechanical
  checkpoints).

**Named-vs-collected discipline:** PR 14 ships 1 named test;
no `parametrize` decorators; named == collected. The
named-equals-collected identity is structurally locked at
PR 14 by single-test pattern (one test function; no
parametrization; no test class). Per framing §5.2 binding.

### 5.2 Forge-bridge env test count projection

```
212 baseline (PR 13 close §1.9 forge-bridge env projection;
              6-test gap inherited per
              project_v1_4_x_harness_debt)
+   1 PR 14 partial-set-divergence test
= 213 forge-bridge env collected at PR 14 close (projected)
```

Forge-bridge env count NOT re-verified at PR 14 close beyond
inheritance documentation. The 6-test gap is PR 7-scope, not
PR 14-scope. **Do not conflate the two env counts** per
PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close §5.2 +
PR 13 close §1.9.

### 5.3 Test inventory at PR 14 close (locked)

| # | Test | File | Step |
|---|---|---|---|
| 1 | `test_recomposition_arc_partial_narrow_divergence` | `test_pr14_partial_narrow_divergence.py` | 2 |

The single test lands at Step 2 (the architectural-center).

---

## 6. Atomic step decomposition

PR 14 ships as a **3-step + close** atomic sequence per
framing §9.12 both-skeletons-at-Step-1 lifecycle invariant
(inherited from PR 13 close §2.4 as PR-of-origin):

- Step 1: both skeletons (test module + fixture module, in
  one commit).
- Step 2: both architectural-centers (test body + FIXTURE
  dict, in one commit).
- Step 3: final verification (empty commit; archaeology in
  body).
- Close: PR 14 close artifact (single artifact at one
  commit; NOT same-commit with Gate 4 close per framing §11
  + Gate 4 framing §11.8 + PR 13 close §7 inheritance).

### 6.1 Step 1 — both skeletons (test module + fixture module, bundled)

**Atomic commit content (single commit landing TWO new files):**

- New file:
  `tests/corpus/test_pr14_partial_narrow_divergence.py`
  - Module docstring (per §4.2.1 — PR-14-LOCAL +
    traversal trace + carrier travel by reference +
    test infrastructure import discipline + references).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports until used by test body
    at Step 2).
  - No test bodies, no module-level constants, no helper
    functions.
- New file:
  `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
  - Module docstring (per §4.1.1 — PR-14-LOCAL + carrier
    travel by reference + fixture purpose with grounded
    arbitration trace + Direction A rationale + references
    + fixture-data-discipline closing).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports — fixture-data-discipline
    member #9 prevents any import beyond `__future__`).
  - No `FIXTURE` dict declaration; no helpers; no constants.

**Both files at structurally-symmetric skeleton state.**
The lifecycle invariant (establishment → activation) holds
across both files. Framing §9.12 both-skeletons-at-Step-1
lifecycle invariant operational (inherited from PR 13 as
PR-of-origin).

**Step 1 verification:**

- `pytest tests/corpus/test_pr14_partial_narrow_divergence.py
  --collect-only -q` → 0 tests collected (skeleton only).
- `python -c "import tests.corpus.test_pr14_partial_narrow_divergence"`
  → imports cleanly.
- `python -c "import tests.corpus.fixtures.fix_partial_narrow_divergence"`
  → imports cleanly; no module-level symbols beyond docstring.
- `pytest tests/corpus/ --collect-only -q | tail -1` → 218
  collected (PR 13 baseline preserved at Step 1; PR 14 test
  not yet activated).
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr4_participation_creep.py
  tests/corpus/test_pr6_visual_asymmetry.py
  tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr9_*.py tests/corpus/test_pr10_*.py
  tests/corpus/test_pr11_recomposition_arc.py
  tests/corpus/test_pr13_ordering_divergence.py` → passes
  unchanged (PR 14 skeleton is target-disjoint from all
  four Layer 2 walkers' input sets + Layer 3 lint + PR 11
  recomposition arc + PR 13 ordering-divergence).

**Step 1 commit body sections (mirroring PR 13 Step 1
pattern adapted for PR 14 scope):**

```
phase-a.5.3.2: PR 14 Step 1 — both skeletons (test module + fixture module bundled)

PR 14 establishes two new files at skeleton state:

  - tests/corpus/fixtures/fix_partial_narrow_divergence.py
  - tests/corpus/test_pr14_partial_narrow_divergence.py

Both files at structurally-symmetric skeleton state. Module
docstrings carry PR-14-LOCAL binding statement verbatim +
17 active carriers cited by reference to canonical sources +
traversal/arbitration trace + Direction A rationale (fixture
docstring only) + references. `from __future__ import
annotations` is the only import at each file. No test
bodies, no FIXTURE dict, no constants, no helpers.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-14-LOCAL binding statement (verbatim per A.5.3.2-PR14-FRAMING.md §0 + §5.5):

  PR 14 isolates partial-set divergence as the sole pressure
  vector. Multi-vector fixture pressure within PR 14 scope —
  combining partial-set with ordering, semantic-normalization,
  duplicate-handling, multi-survivor-cardinality, or any other
  divergence form — is rejected at the spec layer. The
  pure-isolation property is what gives PR 14 its
  laboratory-grade methodology corroboration value for
  Placement A + Placement B substrate.

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
    per PR 13 close §2.2; PR-14-LOCAL is parallel scope-
    local discipline, not regeneration.

Architectural sufficiency signal (Step 1):

  - 0 production source modifications.
  - 2 new test/fixture files added at skeleton state.
  - 0 fifth walker; 0 _ALLOWLIST modifications; 0 Layer 3
    lint changes.

Both-skeletons-at-Step-1 lifecycle invariant (binding per
A.5.3.2-PR14-FRAMING.md §9.12 + inherited from PR 13 close
§2.4 as PR-of-origin):

  Both PR 14 files undergo the same establishment →
  activation lifecycle transition. Asymmetric step
  structures (file-asymmetric / 4-step / 2-step compression)
  rejected at framing. Step 1 lands BOTH skeletons in one
  commit; Step 2 lands BOTH bodies in one commit; Step 3 is
  empty verification with archaeology in body.

What does NOT land at Step 1: test body (Step 2), FIXTURE
dict (Step 2), imports beyond `__future__ annotations`
(Step 2 + member 10 discipline).

Surfaces inventory at Step 1:

  1. fix_partial_narrow_divergence.py module docstring.
  2. test_pr14_partial_narrow_divergence.py module docstring.
  3. This commit body.

Total PR 14 surfaces accumulating toward close-time
archaeology: 3 (Step 1) + 1 (Step 2 commit body) + 1 (Step 3
commit body) = 5 commit-chain surfaces.

References:

  - A.5.3.2-PR14-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR13-CLOSE.md (PR-of-origin precedents — pure-
    isolation discipline + both-skeletons-at-Step-1
    lifecycle invariant).
```

### 6.2 Step 2 — both architectural-centers (test body + FIXTURE dict bundled)

**Atomic commit content (single commit landing TWO file bodies):**

- `tests/corpus/test_pr14_partial_narrow_divergence.py`:
  - Imports landed (per §4.2.2 final-state inventory):
    `pathlib`, `pytest`, `compare_records`,
    `drive_seed_fixture`, `FIX_PARTIAL_NARROW_DIVERGENCE`,
    `_apply_pr9_patches`, `_read_records`.
  - Test function: `test_recomposition_arc_partial_narrow_divergence`
    (full body per §4.2.3).
  - No new module-level constants, no helper functions, no
    parametrize decorators.
- `tests/corpus/fixtures/fix_partial_narrow_divergence.py`:
  - `FIXTURE` dict landed (per §4.1.2):
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
  - No additional imports (member #9 fixture-data-
    discipline; `from __future__ import annotations`
    carried from Step 1 unchanged).

**Three-round review applies** per Gate 2 framing §5.7
integration-work elevation. PR 14's architectural-center is
the partial-set-divergence recomposition arc operational
landing; carrier #17 at use + §4.2 binding behavioral
commitment at use + §5.4 three predicted cleanup-pressure
forms operationally suppressed are the load-bearing
verifications.

**Step 2 verification:**

- `pytest tests/corpus/test_pr14_partial_narrow_divergence.py` →
  1/1 passed.
- `pytest tests/corpus/test_pr13_ordering_divergence.py
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
  **219 collected** forge env (218 baseline + 1 PR 14 new).
  EXACT MATCH with §5.1 projection.
- Architectural sufficiency signal: `git diff --stat
  <PR-14-Step-1-commit>..HEAD -- forge_bridge/` returns
  EMPTY (zero production source modifications).

**Step 2 commit body sections (mirroring PR 13 Step 2 pattern adapted):**

```
phase-a.5.3.2: PR 14 Step 2 — architectural-center (test body + FIXTURE dict bundled)

PR 14 architectural-center lands two bodies in one commit:

  - tests/corpus/test_pr14_partial_narrow_divergence.py:
    imports (pathlib, pytest, compare_records,
    drive_seed_fixture, FIX_PARTIAL_NARROW_DIVERGENCE,
    _apply_pr9_patches, _read_records) + 1 named test
    (test_recomposition_arc_partial_narrow_divergence)
    exercising the full end-to-end recomposition arc.
  - tests/corpus/fixtures/fix_partial_narrow_divergence.py:
    FIXTURE dict with fixture_id, prompt "list",
    expected_narrow [forge_list_projects,
    flame_list_libraries, forge_ping] (authored-superset
    Direction A per framing §5.10 — observation's two
    members at positions 0+1 verbatim PLUS forge_ping at
    position 2 as partial-set extension element orthogonal
    to prompt tokens).

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-14-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

Bundled-commit rationale:

The test needs the FIXTURE import + FIXTURE dict body
together to function. Both bodies bundled per spec §6.2 +
framing §9.12 both-skeletons-at-Step-1 lifecycle invariant
applied symmetrically at architectural-center (both bodies
land in one commit, mirroring the both-skeletons lifecycle
invariant at Step 1; PR-of-origin precedent at PR 13 close
§1.11 + §2.4).

Architectural-center load-bearing verifications:

  - Carrier #17 at use: DivergenceReport per-surface
    partitioning preserves authorship through emission →
    persistence → readback → join → interpretive comparison;
    assertions 2 + 3 satisfy distinct dict paths
    (report["expectation"] vs. report["observation"]) with
    distinct list lengths (3 vs 2).
  - PR 10 §4.2 binding behavioral commitment at use:
    comparator's direct list-equality (_compare.py:503)
    detects the partial-set divergence as
    narrow_diverged=True via length asymmetry + element-
    membership asymmetry at position 2.
  - Three predicted cleanup-pressure forms (framing §5.4)
    operationally suppressed at assertion contract:
    partial-match-to-full-divergence collapse pressure
    (no narrow_diverged-only assertion; full four-key
    structural assertion contract), `partial_match` field-
    addition pressure (no fifth key checked at assertion;
    comparator surface preserves), fixture-shape extension
    pressure (FIXTURE dict carries exactly three keys; no
    fourth declared-intent field).
  - PR-11-LOCAL discipline at gate level (Gate 3 close §3
    item 10): test body inlines the 9-step traversal
    annotation pattern; no helper absorbs the assertion
    logic.

Direction A affirmative architectural decision verification:

  - Authored expectation includes forge_ping at position 2.
    forge_ping is in _PR9_REACHABLE_TOOLS per
    test_pr9_fixture_integration.py:208-213; orthogonal to
    prompt "list" (no token overlap). Semantically legible
    authorial claim preserved.
  - Single-variable discipline across PR 9 / PR 13 / PR 14
    preserved: same prompt + same reachable-tool set + same
    arbitration trace + same observation. Only the authored
    expectation varies.
  - "list"-as-calibration-prompt archaeology preserved per
    framing §4.6.

Recomposition-through-existing-seams operational evidence:

  PR 14 ships against the validated PR 10 comparator + PR 11
  recomposition arc + PR 13 calibration substrate unchanged.
  Zero modifications to comparator surface, recomposition
  arc pattern, fixture corpus, or test infrastructure.
  Architectural sufficiency signal target met at Step 2.

Preserved invariants:

  - 17 active carriers cited by reference (Step 1
    inheritance).
  - Gate 2 binding framing clarification cited by reference.
  - Cross-surface unbinding clarification inherited
    unchanged.
  - PR-11-LOCAL discipline at gate level.
  - PR-13-LOCAL as PR-of-origin for pure-isolation pattern.

Architectural sufficiency signal (Step 2):

  - 0 production source modifications (verified at Step 2
    via `git diff --stat <Step-1-commit>..HEAD --
    forge_bridge/`).
  - 2 new test/fixture files activated at this commit.
  - 218 + 1 = 219 forge env collected (locked).

§4.2 binding behavioral commitment verification at use:

  Test asserts list-equality on expected_narrow and
  observed_narrow at distinct dict paths. The comparator's
  compare-as-persisted discipline preserves the partial-set
  vector through every traversal seam (length 3 expectation
  + length 2 observation surfaces at full structural
  fidelity).

Surfaces inventory at Step 2:

  1. fix_partial_narrow_divergence.py module docstring +
     FIXTURE dict.
  2. test_pr14_partial_narrow_divergence.py module docstring
     + test body.
  3. Step 1 commit body.
  4. This commit body.

Total PR 14 surfaces accumulating toward close-time
archaeology: 4 commit-chain surfaces at Step 2.

References:

  - A.5.3.2-PR14-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
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
  - PR-14-LOCAL binding statement verbatim.
  - §2.4 Gate 4 architectural commitment verbatim.
  - Full PR 14 surfaces inventory.
  - Spec amendments at incarnation (if any surfaced during
    Steps 1–2).
  - Cleanup-pressure-resistance archaeology (predicted-form
    outcomes: ABSENCE / SURFACE per framing §5.4).
  - Placement A contribution recording (predicted-form
    outcomes per framing §6.1).
  - Placement B precondition manifestation recording
    (preconditions 1 + 2 manifest at framing time;
    precondition 3 cumulative across PR 15).
  - §5.3 candidate methodology observation outcome (second-
    Gate-4-PR instance).
  - Catch-point migration candidate methodology contribution
    (PR 14 spec-drafting-time outcome per spec §0; PR 14
    implementation outcome at Step 3 close).
  - PR 14 commit chain summary (Step 1 + Step 2 + Step 3
    commit hashes).
  - Next: PR 14 close artifact (single artifact at next
    commit; NOT same-commit with Gate 4 close).

**Step 3 verification checklist (10 items):**

1. **PR 14 suite:** `pytest tests/corpus/test_pr14_partial_narrow_divergence.py`
   → 1/1 passed.
2. **Existing suites regression:** `pytest tests/corpus/
   --collect-only -q | tail -1` → 219 collected forge env;
   all suites pass unchanged.
3. **PR 4 + PR 5 chat-handler + no-dependency integration
   tests:** pass unchanged (no chat_handler arbitration
   surface modifications at PR 14).
4. **PR 6 Layer 3 lint regression:** 17/17 passed unchanged;
   zero new `emit_divergence_capture` call sites at PR 14.
5. **Four Layer 2 walkers regression:** all four (PR 4 +
   PR 8 + PR 9 + PR 10) pass unchanged; parallel-not-
   extension boundary preserved.
6. **PR 3 discipline:** 1/1 passed unchanged; corpus-
   subtree auto-exclusion handles
   `tests/corpus/test_pr14_*.py` +
   `tests/corpus/fixtures/fix_partial_narrow_divergence.py`
   placements.
7. **PR 11 recomposition arc + PR 13 ordering-divergence
   regression:** PR 11 3/3 passed unchanged + PR 13 1/1
   passed unchanged; PR 14 inherits consumption patterns
   without modification.
8. **Public API regression:** `forge_bridge.__all__` at 19
   symbols.
9. **Verbatim travel verification:**
   - PR-14-LOCAL + 17 carriers cited by reference at both
     PR 14 module docstrings (Step 1 verified).
   - §2.4 Gate 4 architectural commitment travels at this
     spec §0 + §1 + §2 + Step 1, 2, 3 commit body
     "architectural commitment" sections.
   - 17 inherited carriers cited by reference at both PR 14
     module docstrings per §4.1.1 + §4.2.1.
10. **Architectural sufficiency signal verification:** `git
    diff --stat <PR-14-framing-commit>..HEAD -- forge_bridge/`
    returns EMPTY (zero production source modifications
    across PR 14's commit chain). §1 regression contract #10
    + framing §5.3 binding decision + framing §9.3.

**Step 3 commit type:** empty verification commit, no code
changes. Mirrors PR 9 Step 5 (`159ccd2`) + PR 10 Step 5
(`d04753c`) + PR 11 Step 3 (`ae69fba`) + PR 13 Step 3
(`d7f2a6a`) pattern.

**Step 3 commit body sections (mirroring PR 13 Step 3 pattern adapted):**

```
phase-a.5.3.2: PR 14 Step 3 — final verification (empty commit; archaeology in body)

Step 3 final verification: empty commit; archaeology
documented in body.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-14-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

10-item Step 3 verification checklist:

  [10-item checklist per §6.3 above]

Cleanup-pressure-resistance archaeology — predicted-form outcomes:

  - Partial-match-to-full-divergence collapse pressure:
    [ABSENCE / SURFACE — record actual outcome].
  - `partial_match` field-addition pressure:
    [ABSENCE / SURFACE — record actual outcome].
  - Fixture-shape extension pressure:
    [ABSENCE / SURFACE — record actual outcome].

Placement A contribution at PR 14: [N-form-ABSENCE /
N-form-SURFACE evidence summary; second Gate 4 PR instance
contributing toward §5.3 candidate methodology observation's
operational corroboration].

Placement B preconditions manifestation:
  - Precondition 1 (prior pressure prediction at framing
    time): manifest per framing §5.4 + spec §4.2.4.
  - Precondition 2 (named suppression mechanism per
    predicted form): manifest per framing §5.4 + spec
    §4.2.4.
  - Precondition 3 (corroborated recurrence across multiple
    PR scopes): NOT manifest at PR 14 alone; cumulative
    across PR 15; Gate 4 close evaluates per Gate 4 framing
    §6.2.

Catch-point migration candidate methodology contribution:

  - PR 14 framing-convergence-pass pre-commit: catch-shape
    continuation of instance #4 (four grounding catches; NOT
    inflated into new methodology instance per evidence-
    inflation rejection).
  - PR 14 spec-drafting-time: zero-amendment clean
    propagation (catch-shape of instance #3) per spec §0.
  - PR 14 implementation-time: [SURFACE / ZERO-AMENDMENT —
    record actual outcome at Step 3].

PR 14 commit chain summary:
  - Step 1 commit: <hash> — both skeletons.
  - Step 2 commit: <hash> — both architectural-centers.
  - Step 3 commit: this commit — final verification.

Surfaces inventory at Step 3:

  1. fix_partial_narrow_divergence.py module docstring +
     FIXTURE dict.
  2. test_pr14_partial_narrow_divergence.py module docstring
     + test body.
  3. Step 1 commit body.
  4. Step 2 commit body.
  5. This commit body.

Total PR 14 surfaces at Step 3: 5 commit-chain surfaces.

Next: PR 14 close artifact (single artifact at next commit;
NOT same-commit with Gate 4 close per framing §11 + Gate 4
framing §11.8 + PR 13 close §7 inheritance).

References:

  - A.5.3.2-PR14-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR13-CLOSE.md (PR-of-origin precedents).
```

### 6.4 Close commit — PR 14 close artifact (single artifact at one commit)

**Atomic commit content:**

- New file:
  `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR14-CLOSE.md`
  - Single standalone close artifact (per framing §11 +
    Gate 4 framing §11.8 + PR 13 close §7 precedent).
  - Sections (target shape per PR 13 close 8-section
    inventory):
    - §1 What PR 14 established (with 13 subsections per
      PR 13 close precedent).
    - §2 What Gate 4 / future Gate-X work inherits from
      PR 14.
    - §3 What Gate 4 / future work changes (deferred to
      Gate 4 close).
    - §4 Step-by-step archaeology — 4-commit PR 14 chain.
    - §5 Methodology observations at PR 14 scope.
    - §6 Mechanical checkpoints.
    - §7 Standalone close — Gate 4 close pairs with the
      final primary PR.
    - §8 Cross-references.

**Close commit body sections (mirroring PR 13 close commit
pattern adapted):**

```
phase-a.5.3.2: PR 14 close — partial-set divergence pure-isolation case

PR 14 close artifact (standalone; single artifact at one
commit per A.5.3.2-PR14-FRAMING.md §11 + Gate 4 framing
§11.8 + PR 13 close §7 inheritance).

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-14-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

PR 14 commit chain (4-commit post-spec implementation arc;
mirrors PR 13 close §4 "4-commit PR 13 chain" framing — spec
is predecessor context, not counted in the post-spec arc):

  Predecessor: <hash> — spec
  (A.5.3.2-PR14-SPEC.md; this artifact's predecessor).

  1. <hash> — Step 1 (both skeletons).
  2. <hash> — Step 2 (both architectural-centers).
  3. <hash> — Step 3 (final verification).
  4. <hash> — close (this commit).

Gate 4 close pairing: PR 14 ships STANDALONE close. Gate 4
close pairs at same-commit with the FINAL primary PR's close
(PR 15 close, OR PR 12 close if PR 12 materializes last) per
Gate 2 + Gate 3 close precedent + Gate 4 framing §11.8.

References:

  - A.5.3.2-PR14-CLOSE.md (this commit's artifact).
  - A.5.3.2-PR14-SPEC.md (PR 14 implementation contract).
  - A.5.3.2-PR14-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
  - A.5.3.2-PR13-CLOSE.md (immediate predecessor; calibration
    substrate at first calibration point).
```

### 6.5 Step N.5 surgical cadence — available if needed

The Step N.5 surgical cadence (Gate 2 framing §5.7
introduction; Gate 3 close §1.12 three-times-corroborated +
zero-times-at-Gate-3 archaeology; PR 13 spec §6.5 + PR 13
close §5.1 inheritance) is available at PR 14 if needed.

If implementation surfaces a real production-source need at
Step 2 (per framing §5.11 justified-deviation protocol):

1. Pause Step 2 at the moment of falsification.
2. Surface the deviation at framing-level evaluation.
3. If real architectural gap: ship the modification as a
   Step 2.5 surgical commit BEFORE Step 3 verification.
4. PR 14 close §5 records the deviation as Gate-X inheritance
   archaeology.

The Step N.5 cadence is goal-oriented availability, not
constraint. PR 14's expected outcome is **zero Step N.5
commits** (per framing §5.3 0-prod-mod target + Gate 3 close
§1.11 + four-PR architectural-sufficiency-signal escalation
target extending to five-PR).

---

## 7. Phase-end conditions for PR 14

PR 14 close phase-end conditions inherit from framing §9
(12 subsections) unchanged. This spec §7 summarizes the
operational verification target per phase-end condition:

| # | Condition | Operational target |
|---|---|---|
| 9.1 | Test count anchor | 219 forge env collected (218 + 1) |
| 9.2 | PR 14 suite regression | 1/1 passed (`test_recomposition_arc_partial_narrow_divergence`) |
| 9.3 | 0-prod-mod outcome verified | `git diff --stat f53a469..<PR-14-final-commit> -- forge_bridge/` empty |
| 9.4 | Predicted cleanup-pressure form outcomes recorded | Target: 3-form-ABSENCE (parallel to PR 13) |
| 9.5 | Placement B precondition operational manifestation recorded | Preconditions 1 + 2 manifest at PR 14 framing + spec; precondition 3 cumulative |
| 9.6 | Module docstring carrier travel verified | 17 carriers cited by reference at both PR 14 module docstrings |
| 9.7 | §2.4 architectural commitment travel verified | 8 surfaces parallel to PR 13 close §1.5 (framing surfaces excluded) |
| 9.8 | Public API anchor | `forge_bridge.__all__` at 19 symbols |
| 9.9 | Imports-land-when-used discipline verified (member #10) | Both files verified symmetrically |
| 9.10 | Cleanup-pressure-resistance class additions registered | Target: no new candidate class members |
| 9.11 | Test-internal archaeology surfaces inheritance verified | `_apply_pr9_patches` + `_read_records` consumed unchanged |
| 9.12 | Step archaeology summary | Both-skeletons-at-Step-1 lifecycle invariant inherits from PR 13 as PR-of-origin |

PR 14 close §1.X records each condition's operational
verification outcome.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` no modification

PR 14 does NOT modify `forge_bridge/corpus/_ALLOWLIST` or
any Layer 1 surface (per framing §8.1 + Gate 4 framing §8.1
+ PR 13 spec §8.1 + class member #1 lock).

**Why unchanged:** PR 14 fixture + test consume corpus-
internal surfaces through already-allowlisted import paths:

- `forge_bridge.corpus._compare.compare_records` — already
  consumed by PR 11 + PR 13.
- `forge_bridge.corpus._seed.drive_seed_fixture` — already
  consumed by PR 11 + PR 13.

No new corpus-internal import paths required at PR 14.

**Corpus-subtree auto-exclusion semantics** (inherited from
PR 10 §4.4 + PR 13 spec §8.1): the new
`tests/corpus/test_pr14_*.py` placement +
`tests/corpus/fixtures/fix_partial_narrow_divergence.py`
placement fall within the corpus-subtree auto-exclusion
scope; no allowlist modification needed.

### 8.2 Layer 2 — four-walker partition no modification

PR 14 does NOT add a fifth walker, NOT modify any of the
four existing walkers, NOT modify the walker-partition
boundary semantics (per framing §8.2 + Gate 4 framing §8.2
+ Gate 3 close §1.4 + PR 13 spec §8.2 + class member #5 lock).

The four walkers:

- `forge_bridge_persistence_walker.py` — JSONL emission
  semantics.
- `forge_bridge_reader_walker.py` — JSONL readback semantics.
- `forge_bridge_capture_walker.py` — capture-side authority
  partitioning.
- `forge_bridge_seed_walker.py` — seed-side authority
  partitioning.

**Why unchanged:** PR 14's fixture is data-only (member #9);
PR 14's test invokes already-existing seam paths (PR 11
recomposition arc consumption pattern). No new walker
operational requirement at PR 14.

**Target-disjointness verification at close:** PR 14 fixture
+ test do NOT trigger walker traversal logic. The four
walkers' regression at Step 3 phase-end condition 9.X
verifies the target-disjointness preserves.

### 8.3 Layer 3 — unchanged

PR 14 does NOT modify `tests/corpus/test_pr6_visual_asymmetry.py`
or any Layer 3 lint surface (per framing §8.3 + Gate 4
framing §8.3 + PR 13 spec §8.3 + spec §2 item 24).

**Why unchanged:** Layer 3 lint operates against
`emit_divergence_capture` call sites at chat_handler. PR 14
test invokes `drive_seed_fixture` (which internally calls
`emit_divergence_capture` once per fixture invocation); no
new call-site surface at PR 14 production code.

**Layer 3 regression target:** 17/17 passed at PR 14 close
(unchanged from PR 13 close).

---

## 9. Resume protocol (for future archaeology)

If a future session resumes PR 14 implementation mid-flight
(after Step 1 but before Step 3 close), the resume protocol
follows:

1. **Read this spec first.** §0 + §1 + §2 + §6 carry the
   load-bearing implementation context.
2. **Read PR 14 framing** (`A.5.3.2-PR14-FRAMING.md`, 2458
   lines) for the binding pre-spec contract.
3. **Read PR 13 close artifact**
   (`A.5.3.2-PR13-CLOSE.md`, 1247 lines) for the calibration
   substrate at first calibration point + PR-of-origin
   precedents.
4. **Confirm state:**
   - HEAD at `<expected-commit>` per the PR 14 commit chain
     summary at Step 3 (or in this spec's §6.X if Step 3
     not yet committed).
   - Working tree clean (AGENTS.md untracked OK).
5. **Verify Step N inheritance:**
   - If Step 1 committed: both files at skeleton state with
     full module docstrings + `from __future__ import
     annotations`.
   - If Step 2 committed: both files at architectural-center
     state with FIXTURE dict + test body + full imports.
6. **Resume at next Step:**
   - Step 2 after Step 1: implement per §4.1.2 (FIXTURE
     dict) + §4.2.2 + §4.2.3 (test body).
   - Step 3 after Step 2: empty commit per §6.3.
   - Close commit after Step 3: standalone close artifact
     per §6.4.

**Surface inventory at PR 14 close (target):**

- 2 new files (test + fixture).
- 4 commit-chain artifacts at the PR 14 chain (spec +
  Step 1 + Step 2 + Step 3 + close).
- 5 PR 14 surfaces accumulating toward close-time
  archaeology (per Step 1, 2, 3 commit body inventories +
  the close artifact + this spec).
- Target line counts: fixture ~95–115 lines; test ~125–155
  lines; close artifact ~1100–1300 lines (parallel to
  PR 13 close at 1247 lines).

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
    PR-11-LOCAL discipline at gate level; consumption
    pattern.
12. `A.5.3.2-GATE-3-CLOSE.md` — gate-arc synthesis; carrier
    #16 promotion; 10-member class promotion; 17 active
    carriers; four-walker Layer 2 partition; conditional
    PR 12 DEFER.
13. `A.5.3.2-GATE-4-FRAMING.md` — gate-level inheritance
    contract; three-PR primary slot structure; PR ordering;
    §10 PR 14 sub-section.
14. `A.5.3.2-PR13-FRAMING.md` — first-of-three primary PR
    framing precedent; 11-section framing shape; citation-by-
    reference discipline.
15. `A.5.3.2-PR13-SPEC.md` — fixture + test implementation
    contract precedent; 11-section spec shape; locked-
    mergeability-anchors discipline; both-skeletons-at-
    Step-1 lifecycle invariant.
16. `A.5.3.2-PR13-CLOSE.md` — immediate predecessor;
    calibration substrate at first calibration point;
    PR-13-LOCAL as PR-of-origin archaeology; both-skeletons-
    at-Step-1 lifecycle invariant as PR-of-origin
    archaeology; four-PR architectural sufficiency
    escalation.
17. `A.5.3.2-PR14-FRAMING.md` — **immediate predecessor;
    PR 14 second-calibration-point framing.** PR-14-LOCAL
    binding statement + 5 binding decisions + 17 carriers
    inheritance + cleanup-pressure-resistance class
    inheritance + §2.4 architectural commitment travel +
    9-step traversal annotation pattern + Direction A
    affirmative architectural decision + `"list"`-as-
    calibration-prompt archaeology elevation.
18. **This spec artifact** — PR 14 implementation contract.

**Forward references (post-spec artifacts):**

- PR 14 Step 1, 2, 3 commits — per §6.1–§6.3.
- `A.5.3.2-PR14-CLOSE.md` — PR 14 close artifact (standalone
  close per Gate 4 framing §11.8 + PR 13 close §7
  precedent; pairs at same commit with FINAL primary PR's
  close only).

**Implementation file references (grounding):**

- `tests/corpus/fixtures/fix_multi_match.py:105-140` — PR 9
  multi-match arbitration trace; PR 14 fixture inherits the
  trace as observation grounding.
- `tests/corpus/test_pr9_fixture_integration.py:208-213` —
  `_PR9_REACHABLE_TOOLS` declared order including
  `forge_ping` at index 0; PR 14 inherits the reachable-tool
  set verbatim + grounds the partial-set extension element
  selection.
- `tests/corpus/fixtures/fix_ordering_divergence.py` — PR 13
  fixture; PR 14 fixture mirrors the structural shape (one
  divergence vector + pure-isolation property enumeration +
  authored-expectation rationale + reference to PR 9 multi-
  match arbitration trace).
- `tests/corpus/test_pr13_ordering_divergence.py` — PR 13
  test; PR 14 test mirrors the 9-step traversal annotation
  pattern (per
  `test_pr13_ordering_divergence.py:150-203`; six header
  comments covering nine logical traversal steps) +
  four-key structural assertion contract + import discipline.
- `tests/corpus/test_pr11_recomposition_arc.py` — PR 11
  recomposition arc consumption pattern; PR 14 inherits via
  PR 13 inheritance chain.
- `forge_bridge/corpus/_compare.py:503` — comparator's
  direct list-equality semantics (`obs_decision !=
  exp_narrow`); PR 14 exercises the line under partial-set
  divergence pressure (length asymmetry + element-membership
  asymmetry at position 2 both contribute to the
  inequality).

**Memory cursor references:**

- `feedback_ground_specs_in_actual_files.md` — operative
  discipline at every spec assertion about existing file
  shape; applied at PR 14 framing convergence pass + at
  spec-drafting-time pre-spec-lock (one grounding catch
  surfaced + corrected pre-commit per §0; catch-shape
  continuation of instance #5).
- `feedback_counts_are_archaeology_grade.md` — operative at
  every count assertion (218 baseline; 219 target; 17 active
  carriers; 10-member class; 19 `__all__` symbols; 5-
  instance catch-point migration descriptive at PR 14 spec
  landing; 9-step traversal pattern; 8-surface §2.4 close
  inventory; 9-surface PR-14-LOCAL close inventory).
- `feedback_writers_room_lead_with_views.md` — operative at
  spec drafting structural seams (Direction A spec-level
  expression at §1 + §4.1 + §4.2 + §5.10; calibration-prompt
  archaeology spec-level expression at §4.1 fixture
  docstring; recursive-self-governance discipline at §0
  catch-point migration analysis).
- `feedback_deferral_first_class_governance.md` — standalone-
  close discipline at PR 14 close inherits from PR 13 close
  §7 + Gate 4 framing §11.8.
- `feedback_explicitly_unbound_vs_implicitly_rejected.md` —
  cross-surface unbinding + citation-by-reference travel
  discipline at PR 14 spec inheritance.
- `feedback_cursor_before_retrospective_synthesis.md` —
  operative at PR 14 spec close (cursor before PR 14
  implementation begins; planned at next session boundary).
- `project_three_architectural_layers.md` — Layer 2 walkers
  + Layer 3 lint regression sweep evidence persists; PR 14
  is target-disjoint from all four walkers + Layer 3 lint
  (verified at §8).
