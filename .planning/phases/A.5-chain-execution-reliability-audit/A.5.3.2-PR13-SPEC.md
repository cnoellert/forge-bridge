# A.5.3.2 PR 13 — Spec (ordering divergence as Gate 4 calibration exercise)

**Status:** Spec-stage artifact for PR 13 of Gate 4. PR 13
framing locked at `8f429b2` (1850 lines); this spec derives
the implementation contract by finalizing the symbol-level
decisions named in the framing's ten binding decisions
(§5.1–§5.10) and the two spec-drafting-time decisions
surfaced at framing→spec convergence: **fixture cardinality
(2-element)** and **prompt selection (`"list"`)** — both
grounded in `_PR9_REACHABLE_TOOLS` arbitration topology, not
extrapolated from the framing's symbolic `[A, B, C]` example.

PR 13 is the first of three primary PRs sequenced within
Gate 4 per Gate 4 framing §10. **PR 13 close artifact ships
standalone at its own commit** (NOT same-commit with Gate 4
close). Per Gate 4 framing §11.8, Gate 4 close pairs at
same-commit with the final primary PR close (PR 15 close,
OR PR 12 close if PR 12 materializes last) per Gate 2 +
Gate 3 close precedent. PR 13's close commit closes PR 13
alone.

This spec's job: derive file-level precision from framing's
locked decisions. Two new files at PR 13:
`tests/corpus/fixtures/fix_ordering_divergence.py` (new
fixture) + `tests/corpus/test_pr13_ordering_divergence.py`
(new test module containing exactly one named test). The
spec's outputs are mergeability anchors — file paths,
function names, test names, assertion contracts, exact
docstring shape, exact commit-body sections — that PR 13
close §6 will verify against.

**Gate 4 architectural commitment (travels at this spec body
+ all PR 13 commit message bodies under "architectural
commitment" sections; deliberately NOT in fixture/test
docstrings per Gate 4 framing §2.4 binding + PR 13 framing
§3.6):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Seventeen active carriers** travel into PR 13's surface
(same set Gate 4 framing locked at §3.1 + PR 11 spec §0
mirrored; no new carriers introduced at PR 13 per Gate 4
framing §3.1 + §6.1 + §7 item 13 + PR 13 framing §3.1).
Composition unchanged: 15 inherited carriers (#1–#15) +
carrier #16 (active, promoted at Gate 3 close §1.6 —
*"Reliability work proves topology, not infrastructure"*) +
carrier #17 (active from Gate 3 framing §5.1 — recomposition
discipline).

**Reference discipline (binding per Gate 4 framing §3.1 +
PR 13 framing §3.1):** *"17 active carriers"* is canonical
phrasing post-Gate-3-close-promotion. PR 13 surfaces travel
carriers in natural numeric ordering WITHOUT substrate
marking. The candidate-substrate marking discipline retired
at Gate 3 close.

### Carrier travel form at PR 13 module docstrings — citation by reference

PR 13 spec interprets the framing §3.1 "17 carriers travel
verbatim" discipline as **verbatim citation to canonical
sources** (mirroring PR 11 spec §0's interpretation; per
DRY + canonical-source discipline). The 17 carriers + Gate 2
binding framing clarification + inherited PR-LOCAL bindings
travel by reference to:

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

This interpretation choice diverges from PR 9 fixture
precedent (`fix_single_survivor.py` + `fix_multi_match.py` +
`fix_no_keyword_match.py` carried carriers #1–#15 verbatim
in full). The divergence is deliberate: PR 9 authored the
fixture corpus when canonical sources at `_capture.py` +
`_seed.py` were less mature; PR 13 authors with established
canonical sources + the more recent PR 11 test-module
citation-by-reference precedent operative. Citation-by-
reference is verbatim-travel-by-canonical-source-pointer —
the framing's verbatim-travel discipline accommodates both
forms; PR 13 adopts the lower-DRY form.

### Verbatim travel — PR-13-LOCAL binding statement

The **PR-13-LOCAL binding statement** travels verbatim at:

1. `tests/corpus/test_pr13_ordering_divergence.py` module
   docstring (Step 1 surface).
2. `tests/corpus/fixtures/fix_ordering_divergence.py` module
   docstring (Step 1 surface).
3. All PR 13 commit message bodies under "preserved
   invariants" / "PR-13-LOCAL" sections.
4. This spec §0 + §1 + §2 (verbatim form below).

**PR-13-LOCAL binding statement (verbatim — pure-isolation
discipline):**

> **PR 13 isolates ordering divergence as the sole pressure
> vector. Multi-vector fixture pressure within PR 13 scope —
> combining ordering with cardinality, partial-set,
> semantic-normalization, duplicate-handling, or any other
> divergence form — is rejected at the spec layer. The
> pure-isolation property is what gives PR 13 its laboratory-
> grade methodology corroboration value for Placement A +
> Placement B substrate.**

### Verbatim travel — §2.4 Gate 4 architectural commitment

The **§2.4 Gate 4 architectural commitment** travels
verbatim at (per Gate 4 framing §2.4 binding + PR 13 framing
§3.6 + §5.6):

1. This spec §0 (above the line) + §1 + §2 architectural
   commitment section.
2. All three PR 13 step commit message bodies under
   "architectural commitment" sections.
3. PR 13 close artifact §1 + §6.5 (or equivalent
   architectural-commitment + architectural-sufficiency
   sections).

**Travel deliberately stops short of fixture/test
docstrings.** The §2.4 sentence is gate-shaped architectural
posture, NOT carrier-shaped governance. Carriers travel
through fixture/test docstrings; the §2.4 commitment does
not. The asymmetry preserves the carrier / governing
sentence / methodology-stack category integrity Gate 4
framing established.

**§2.4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

### Spec-drafting-time grounding catch — fifth catch-point-migration instance

Per Gate 3 close §1.8 + Gate 4 framing §3.6 + PR 13 framing
§3.6 cursor-record, the catch-point-migration candidate
methodology accumulated four descriptive instances at PR 13
framing landing:

1. PR 9 grounding-time amendment (implementation post-Step-1).
2. PR 10 grounding-time amendment (implementation-prep).
3. PR 11 framing-spec drafting time (zero amendments).
4. PR 13 framing-convergence-pass file-grounding pre-commit
   (six grounding catches at file/symbol naming conventions).

**PR 13 spec drafting contributes a fifth instance: spec-
drafting-time fixture-cardinality grounding pre-spec-lock.**
The framing's §2.2 + §4.1 symbolic notation `[A, B, C]` →
`[C, A, B]` (3-element rotation) could have silently drifted
into spec-level implementation assumption ("3 tools to
choose; 3 tools in the expected list"). Instead, grounding
the arbitration topology in actual `_PR9_REACHABLE_TOOLS`
arbitration behavior (PR14 + PR21 rules) BEFORE locking
spec values surfaced the structural constraint: 3-element
deterministic survival is unavailable from the existing
reachable set without modifying the reachable set OR adding
patches (both rejected per framing §3.7 + §9.11). The
correction landed at spec-drafting-time **before spec lock**
— the catch-point migrates earlier still: from framing-
convergence-pass pre-commit (PR 13 instance #4) to spec-
drafting-time pre-spec-lock (PR 13 instance #5).

The progression is now **five-instance descriptive**.
Catch-points across the sequence:

| # | PR | Catch-point | Catch-shape |
|---|---|---|---|
| 1 | PR 9 | Implementation post-Step-1 | Grounding-time amendment |
| 2 | PR 10 | Implementation-prep | Grounding-time amendment |
| 3 | PR 11 | Framing-spec drafting time | Zero amendments — clean propagation |
| 4 | PR 13 | Framing-convergence-pass pre-commit | Six file-grounding catches |
| 5 | PR 13 | Spec-drafting-time pre-spec-lock | Fixture-cardinality grounding catch |

Catch-points migrate earlier monotonically across the five
instances; instances #4 + #5 are both at PR 13, indicating
two distinct catch-surfaces operate at PR 13's framing/spec
boundary. The candidate methodology continues maturing
operationally. Gate 4 close evaluates cumulative progression
for prescriptive promotion candidacy.

PR 13 close §1 records the spec-drafting-time catch as a
contributing instance toward Gate 4 close's catch-point
migration evaluation per Gate 4 framing §11.5.

---

## 1. Real job (PR 13 in one paragraph)

PR 13 ships **two new files** containing **exactly one named
test** that exercises an ordering-divergence pure-isolation
case through the full end-to-end recomposition arc:

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

The fixture authors `expected_narrow` with the **same
membership** as observed arbitration but with the **two
elements swapped**. The comparator's compare-as-persisted
discipline (PR 10 §4.2 binding behavioral commitment) detects
the ordering-only divergence at direct list-equality
(`obs_decision != exp_narrow` per
`_compare.py:503`) without sort / canonicalization / semantic
coercion at any traversal seam. The test asserts the four-key
`DivergenceReport` structural shape with explicit per-surface
partitioning (carrier #17 at use) + `narrow_diverged=True`.

**Gate 4 architectural commitment (verbatim):**

> **Gate 4 is the deliberate continuation of empirically
> bounded topology proof through divergence-shape robustness
> exercise.**

**Regression contracts at PR 13 close (10 items):**

1. PR 13 suite (`test_pr13_ordering_divergence.py`): 1/1
   passed.
2. PR 4 + PR 5 + PR 6 + PR 7 + PR 8 + PR 9 + PR 10 + PR 11
   suites pass unchanged.
3. PR 3 discipline passes unchanged (no `_ALLOWLIST`
   modification per §8.1).
4. Four Layer 2 walkers (PR 4 + PR 8 + PR 9 + PR 10) pass
   unchanged.
5. Layer 3 lint (`test_pr6_visual_asymmetry.py`) passes
   unchanged.
6. Full corpus suite: **218 forge env collected** (217
   baseline + 1 PR 13 new).
7. Console tests + Public API anchor (`forge_bridge.__all__`
   at 19 symbols) unchanged.
8. Verbatim carrier travel: 17 carriers cited by reference +
   PR-13-LOCAL verbatim at both PR 13 module docstrings +
   PR 13 commit message bodies.
9. §2.4 Gate 4 architectural commitment travels verbatim at
   this spec §0 + §1 + §2 + all 3 PR 13 step commit message
   bodies under "architectural commitment" sections + PR 13
   close artifact (NOT at fixture/test docstrings).
10. **Architectural sufficiency signal: 0 production source
    modifications across PR 13's commit chain.**

---

## 2. In-scope / out-of-scope

### In scope (PR 13)

- New file: `tests/corpus/fixtures/fix_ordering_divergence.py`
  containing module docstring (carrying PR-13-LOCAL + 17
  carriers by reference + grounded arbitration trace +
  fixture purpose) + `from __future__ import annotations` +
  `FIXTURE` dict with three keys (`fixture_id`, `prompt`,
  `expected_narrow`).
- New file: `tests/corpus/test_pr13_ordering_divergence.py`
  containing module docstring (carrying PR-13-LOCAL + 17
  carriers by reference + traversal trace + test
  infrastructure import discipline) + imports + 1 named
  test (`test_recomposition_arc_ordering_divergence`).
- IMPORT of PR 9 test infrastructure (`_apply_pr9_patches`,
  `_read_records`) from
  `tests.corpus.test_pr9_fixture_integration` as
  **test-internal archaeology surfaces** (not public APIs;
  inherited from PR 11 pattern).
- PR 13 commit message bodies carrying "architectural
  commitment" + "preserved invariants" + "PR-13-LOCAL" +
  "Placement A/B substrate contribution" sections per the
  PR 11 commit-body pattern adapted for Gate 4 / PR 13
  scope.

### Out of scope (architecturally-prohibited at PR 13)

PR 13 inherits the framing §7 26-item non-acquisition list
in full + adds spec-layer enforcement:

1. **Any production source file modification.** Framing
   §5.3 binding decision; framing §7 item 4 inherited from
   Gate 4 framing. Justified deviations register as
   archaeology at PR 13 close per framing §5.10 justified-
   deviation protocol, not silent additions.
2. **Authoring multi-vector fixture pressure.** Framing
   §5.1 + §5.5 PR-13-LOCAL binding; framing §7 items 1 +
   5 + 6 + 7. The fixture isolates ordering divergence as
   the sole pressure vector.
3. **Authoring the inverse-direction test variant** at
   spec layer. Framing §4.4 + §5.2 + §7 item 2 evidence
   inflation rejection.
4. **Authoring multi-permutation variants** (e.g.,
   `[A, C, B]`, `[B, A, C]`). Framing §7 item 3; pure
   permutation behavior is implicit in PR 10 §4.2 binding.
5. **Modifying the comparator surface**
   (`compare_records` / `DivergenceReport` /
   `ComparatorInputError`). Framing §5.7 binding + §7
   item 4.
6. **Adding "while we're here" elements** (subset
   mismatch / duplicate handling / semantic
   normalization). Framing §5.5 PR-13-LOCAL + §7 items
   5 + 6 + 7.
7. **Modifying existing PR 9 fixtures.** Framing §7
   item 8.
8. **Re-authoring `_apply_pr9_patches` or `_read_records`**
   with modified semantics. Framing §7 item 9.
9. **Promoting PR 9 underscored helpers to public APIs.**
   Framing §7 item 10.
10. **Introducing a test-helper function** that absorbs
    the recomposition traversal. Framing §7 item 11;
    framing §5.4 predicted-form 3 suppression at use.
11. **Introducing caller-side canonicalization** (sort,
    normalize) before invoking `compare_records`. Framing
    §7 item 12; framing §5.4 predicted-form 1 suppression
    at use.
12. **Using set-equality assertion shortcuts** (e.g.,
    `assert set(observed) == set(expected)`) in PR 13 test
    body. Framing §7 item 13; framing §5.4 predicted-form 2
    suppression at use.
13. **Introducing a new `record_kind`.** Framing §7 item 14.
14. **Extending `KNOWN_SOURCE_VALUES`.** Framing §7 item 15.
15. **Modifying the expectation record schema** (3 required
    keys). Framing §7 item 16.
16. **Modifying the three-authority-surface partition.**
    Framing §7 item 17.
17. **Authoring a fifth walker.** Framing §7 item 18.
18. **Adding cleanup-pressure-resistance class members
    speculatively** at framing/spec time. Framing §7
    item 19. Class members surface at PR 13 close based on
    actual implementation pressure encountered.
19. **Introducing a candidate carrier (#18)** at PR 13.
    Framing §7 item 20.
20. **Speculatively authoring a Gate-4-LOCAL governing
    sentence.** Framing §7 item 21.
21. **Pre-binding Placement A outcome predictions** at
    framing/spec. Framing §7 item 22. Outcomes register at
    PR 13 close based on actual encountered pressure.
22. **Pre-binding PR 12 disposition** at PR 13 framing/spec.
    Framing §7 item 23.
23. **Touching the Layer 3 lint**
    (`test_pr6_visual_asymmetry.py`). Framing §7 item 24.
24. **Modifying `divergence_capture_enabled()` or its
    env-gate.** Framing §7 item 25.
25. **Extending `_KNOWN_RECORD_KINDS`.** Framing §7 item 26.
26. **Speculative-reserved imports.** Per cleanup-pressure-
    resistance class member #10; imports land when first
    used at Step 2 implementation (spec §4.2.2 + §6.2).
27. **Cross-surface vocabulary in test names or
    docstrings.** Per framing §5.4 predicted-form 3
    suppression + PR 11 framing §7 item 22 inheritance. No
    `task_outcome` / `prompt_resolution` field names.
28. **`forge_bridge.__all__` modification.** Framing §5.8
    binding. Stays at 19 symbols.
29. **Layer 1 `_ALLOWLIST` modification.** §8.1 explicit;
    corpus-subtree auto-exclusion semantics inherited from
    PR 10 §4.4.
30. **Layer 2 walker addition.** §8.2 explicit; no fifth
    walker.

---

## 3. Files modified / created at PR 13

| File | Disposition | Lines (final at PR 13 close) |
|---|---|---|
| `tests/corpus/fixtures/fix_ordering_divergence.py` | **NEW** | ~90–110 |
| `tests/corpus/test_pr13_ordering_divergence.py` | **NEW** | ~120–150 |
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
| `tests/corpus/fixtures/fix_*.py` (existing PR 9 fixtures) | NOT MODIFIED (PR 9 fixtures stable archaeology) | 0 |
| `tests/corpus/conftest.py` | NOT MODIFIED | 0 |

**Two new files. Zero modifications to any production source
or existing test/fixture file.** The 0-prod-mod-outside-the-
new-test-and-fixture-files outcome IS the architectural
sufficiency signal PR 13 demonstrates (framing §5.3 + §9.3).

---

## 4. Per-file derivation

### 4.1 `tests/corpus/fixtures/fix_ordering_divergence.py` — new fixture

#### 4.1.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering — most
load-bearing at TOP per PR 8 spec §0 travel rule + PR 13
framing §3.1):

1. **One-line summary**: `"""Seed fixture — ordering-divergence pure-isolation case at the chat-handler observation surface."""`
2. **Blank line.**
3. **PR-13-LOCAL binding statement** (verbatim, per §0 + framing §5.5):

   > PR 13 isolates ordering divergence as the sole pressure
   > vector. Multi-vector fixture pressure within PR 13 scope —
   > combining ordering with cardinality, partial-set,
   > semantic-normalization, duplicate-handling, or any other
   > divergence form — is rejected at the spec layer. The
   > pure-isolation property is what gives PR 13 its
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
   per PR 9 fixture precedent at `fix_multi_match.py:105-140`):

   ```
   Fixture purpose:

   This fixture exercises the chat-handler-surface ordering-
   divergence pure-isolation case. The prompt ``"list"``
   (single-step shape; does NOT fire chain-step arbitration)
   is identical to PR 9 multi-match's prompt
   (``fix_multi_match.py``); the arbitration trace through
   PR14 + PR21 is grounded at fix_multi_match.py:105-140.

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
   arbitration trace):

     narrower.decision = ["forge_list_projects",
                          "flame_list_libraries"]

   (verbatim PR14 input order through PR21;
   ``_PR9_REACHABLE_TOOLS`` declared ordering at
   ``test_pr9_fixture_integration.py:208-213``.)

   Expectation record (PR 13 fixture-author choice — the
   ordering-divergence vector):

     expected_narrow = ["flame_list_libraries",
                        "forge_list_projects"]

   (positions swapped relative to observation — the SAME
   set, DIFFERENT sequence; the single-direction pure-
   isolation ordering-divergence vector PR-13-LOCAL binds.)

   The pure-isolation property holds at every dimension:

     - Same set: {forge_list_projects, flame_list_libraries}.
     - Different sequence: positions 0 and 1 swapped.
     - No cardinality divergence: both lists length 2.
     - No partial-set divergence: identical membership.
     - No semantic-normalization divergence: tool names are
       exact-match identifiers; no canonical-form
       transformations involved.
     - No duplicate-handling divergence: each list contains
       distinct elements.

   The comparator's compare-as-persisted discipline (PR 10
   §4.2 binding behavioral commitment) detects the ordering-
   only divergence as ``narrow_diverged=True`` per direct
   list-equality at ``_compare.py:503`` (``obs_decision !=
   exp_narrow``; no sort, no canonicalization, no semantic
   coercion at any traversal seam).

   This fixture differs from PR 9 multi-match
   (``fix_multi_match.py``) at exactly one surface: the
   authored expectation. PR 9 multi-match authors
   ``expected_narrow`` matching observation verbatim
   (no-divergence baseline). PR 13 authors the swap. Prompt
   reuse is NOT collision — fixture identity discriminator
   is ``fixture_id``, not ``prompt``; per-test ``tmp_path``
   corpus isolation prevents record co-existence between PR
   9 multi-match's invocation and PR 13's invocation. The
   prompt-reuse-without-collision is itself architectural
   evidence: arbitration topology + fixture identity +
   divergence semantics are independent authority surfaces.
   ```

   The arbitration trace recorded above is archaeology-
   grade per
   `feedback_counts_are_archaeology_grade.md`. Future
   contributors diagnosing PR 13 regressions can verify
   against the trace recorded here + the PR 9 multi-match
   trace.

8. **Blank line.**
9. **References** paragraph citing:

   ```
   References:
     - A.5.3.2-PR13-SPEC.md (this fixture's implementation
       contract).
     - A.5.3.2-PR13-FRAMING.md (binding pre-spec contract).
     - A.5.3.2-GATE-4-FRAMING.md (immediate predecessor;
       gate-level inheritance contract).
     - tests/corpus/fixtures/fix_multi_match.py:105-140
       (PR 9 multi-match arbitration trace; PR 13 inherits
       the trace grounding).
     - tests/corpus/test_pr9_fixture_integration.py:208-213
       (_PR9_REACHABLE_TOOLS declared order).
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

**Total docstring: ~85–110 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent
steps.

#### 4.1.2 Module body (Step 2 contents)

```python
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr13-ordering-divergence",
    "prompt": "list",
    "expected_narrow": ["flame_list_libraries", "forge_list_projects"],
}
```

**Locked values (binding):**

| Key | Value | Grounding |
|---|---|---|
| `fixture_id` | `"fix-pr13-ordering-divergence"` | Framing §5.9 two-surface form; kebab-case with PR anchor |
| `prompt` | `"list"` | Spec-drafting-time grounding — PR 9 multi-match deterministic 2-element multi-match outcome (`fix_multi_match.py:151`) |
| `expected_narrow` | `["flame_list_libraries", "forge_list_projects"]` | Swap of observed sequence; ordering-divergence vector |

The single-symbol module export is `FIXTURE` (canonical name
per framing §3.3 + §5.9; consuming test aliases on import).

**Symbol export form lock:** PR 13 fixture exports exactly
one module-level symbol named `FIXTURE`. No additional
constants, no helper functions, no factories. The only
module-level statement beyond the docstring + `FIXTURE`
assignment is `from __future__ import annotations` at the
head of the module body.

#### 4.1.3 Imports discipline

Imports inventory at PR 13 close (final state):

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

The single-import discipline is structural at PR 13's
fixture file — no imports land at Step 2 because the
`FIXTURE` dict only requires literal-construction syntax
(strings + list of strings + dict literal). Member #9 +
member #10 protections operate symmetrically.

### 4.2 `tests/corpus/test_pr13_ordering_divergence.py` — new test module

#### 4.2.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering):

1. **One-line summary**: `"""End-to-end ordering-divergence recomposition arc test — fixture → drive_seed_fixture → chat_handler → emission → readback → compare_records → DivergenceReport (narrow_diverged=True)."""`
2. **Blank line.**
3. **PR-13-LOCAL binding statement** (verbatim, per §0 + framing §5.5).
4. **Blank line.**
5. **Traversal trace** (verbatim from PR 13 framing §2.1):

   ```
   fixture (tests/corpus/fixtures/fix_ordering_divergence.py)
     → drive_seed_fixture          [orchestration seam]
       → emit_seed_expectation     [expectation persistence seam]
       → chat_handler arbitration  [observation production seam]
         → emit_divergence_capture [observation persistence seam]
           → JSONL persistence     [persistence-topology seam]
             → reader              [readback seam (via _read_records)]
               → compare_records   [interpretive-read seam]
                 → DivergenceReport assertions (narrow_diverged=True)
   ```

6. **Blank line.**
7. **Carrier travel — citation by reference paragraph** (per §0; same form as fixture module §4.1.1 site 5).

8. **Blank line.**
9. **Test infrastructure import discipline** paragraph (per PR 11 spec §4.1.1 site 11 + framing §9.11 inheritance):

   > PR 13 imports ``_apply_pr9_patches`` and ``_read_records``
   > from ``tests.corpus.test_pr9_fixture_integration`` as
   > **test-internal archaeology surfaces**, NOT as public APIs.
   > The underscored-private status is preserved — the import is
   > test-internal and archaeology-explicit, mirroring the PR 11
   > consumption pattern (``test_pr11_recomposition_arc.py:111-114``).
   > This does NOT promote the helpers to public APIs; future
   > contributors must NOT read this as a general invitation to
   > import underscored-private helpers across production modules.

10. **Blank line.**
11. **References** trailing paragraph citing:

    ```
    References:
      - A.5.3.2-PR13-SPEC.md (this module's implementation
        contract).
      - A.5.3.2-PR13-FRAMING.md (binding pre-spec contract).
      - A.5.3.2-GATE-4-FRAMING.md (immediate predecessor;
        gate-level inheritance contract; §2.4 architectural
        commitment).
      - A.5.3.2-PR11-CLOSE.md (recomposition arc operational
        evidence; PR-11-LOCAL traverses-not-erases-seams
        inherited at gate level per Gate 3 close §3 item 10).
      - A.5.3.2-PR10-CLOSE.md (durable PR 10 archival state;
        PR 10 §4.2 binding behavioral commitment exercised
        under ordering-divergence pressure).
      - tests/corpus/test_pr11_recomposition_arc.py
        (recomposition arc consumption pattern inherited).
      - tests/corpus/fixtures/fix_multi_match.py:105-140
        (PR 9 multi-match arbitration trace inherited).
    ```

**Total docstring: ~55–75 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent
steps.

#### 4.2.2 Imports discipline (per member 10: imports land when first used)

Imports inventory at PR 13 close (final state):

```python
from __future__ import annotations

import pathlib

import pytest

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._seed import drive_seed_fixture

from tests.corpus.fixtures.fix_ordering_divergence import (
    FIXTURE as FIX_ORDERING_DIVERGENCE,
)

# Test-internal archaeology surfaces (NOT public APIs) per
# module-docstring "Test infrastructure import discipline"
# framing + A.5.3.2-PR13-SPEC.md §4.2.1 site 9.
from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)
```

**Imports discipline at Step 1 skeleton:** the skeleton
commit imports ONLY `from __future__ import annotations`.
Per cleanup-pressure-resistance class member 10:

- `__future__ annotations` lands at Step 1 (module-level
  posture).
- `pathlib`, `pytest`, `compare_records`,
  `drive_seed_fixture`, `FIX_ORDERING_DIVERGENCE`,
  `_apply_pr9_patches`, `_read_records` land at Step 2
  (architectural-center, when first used by test body).

**No speculative-reserved imports.** No `import copy`, no
`import json`, no `ComparatorInputError`, no
`DivergenceReport` (the test asserts against dict keys, not
the typed alias).

**Test-internal archaeology surfaces:** the two imports from
`tests.corpus.test_pr9_fixture_integration` are the ONLY
underscored-private cross-test-module imports at PR 13.
Admitted under the explicit "test-internal archaeology
surfaces" framing per §4.2.1 site 9 docstring + PR 11 spec
§4.1.2 inheritance.

**Module-level constants at PR 13 test module:** none. The
FIXTURE dict is imported per-fixture; the PR 9 helpers are
imported per-helper; the single test uses them directly at
body scope.

#### 4.2.3 The single test — `test_recomposition_arc_ordering_divergence`

**Test name:** `test_recomposition_arc_ordering_divergence`

**Fixtures consumed:** `clean_rate_limit_state` (rate-limit
isolation per `conftest.py`; inherited from PR 11 pattern),
`monkeypatch` (pytest standard), `tmp_path` (pytest
standard).

**Test body (final state at Step 2):**

```python
def test_recomposition_arc_ordering_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — ordering-divergence pure-isolation case.

    Drives ``fix-pr13-ordering-divergence`` through the full
    decomposition seam path. The fixture authors
    ``expected_narrow`` with the SAME set but DIFFERENT
    sequence as observed arbitration: PR 9 multi-match
    deterministic outcome (prompt "list" produces
    ``narrower.decision = ["forge_list_projects",
    "flame_list_libraries"]``) vs. authored
    ``expected_narrow = ["flame_list_libraries",
    "forge_list_projects"]`` (positions swapped).

    The comparator's compare-as-persisted discipline (PR 10
    §4.2 binding behavioral commitment) detects the
    ordering-only divergence as ``narrow_diverged=True`` per
    direct list-equality at ``_compare.py:503``. Carrier #17
    at use: the DivergenceReport's per-surface partitioning
    preserves authorship through emission → persistence →
    readback → join → interpretive comparison; the
    ordering-divergence vector is identifiable at the
    structural shape level (``expectation.expected_narrow``
    vs. ``observation.observed_narrow`` carry distinct
    sequences with shared membership).

    Pure-isolation property at every dimension: same set,
    different sequence; no cardinality / partial-set /
    semantic-normalization / duplicate-handling confound.
    PR-13-LOCAL pure-isolation discipline binding.
    """
    # ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
    # Test-internal archaeology surface (NOT a public API).
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    # ── Steps 2-5 of traversal: drive fixture → emission ───────
    # drive_seed_fixture orchestrates expectation persistence,
    # chat_handler arbitration, observation emission. The seam
    # traversal is explicit at the call site — no helper absorbs
    # the arc (PR-11-LOCAL discipline at gate level per Gate 3
    # close §3 item 10 + PR 13 framing §5.4 predicted-form 3
    # suppression).
    drive_seed_fixture(**FIX_ORDERING_DIVERGENCE)

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
        if r.get("fixture_id") == FIX_ORDERING_DIVERGENCE["fixture_id"]
    ]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for "
        f"{FIX_ORDERING_DIVERGENCE['fixture_id']!r}; got "
        f"{len(matching)}.\nAll records: {records}"
    )

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    # ── Step 8 of traversal: invoke comparator ─────────────────
    # The interpretive-read seam. compare_records joins
    # observation + expectation by fixture_id (Gate 2 close
    # §2.1) and produces the DivergenceReport per carrier #17.
    # Direct list-equality at _compare.py:503 detects the
    # ordering-only divergence; no caller-side sort or
    # canonicalization per PR 13 framing §5.4 predicted-form 1
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
    # ordering-divergence vector surfaces at distinct list
    # values at expectation vs. observation sub-dicts.
    #
    # List-equality (NOT set-equality) per PR 13 framing §5.4
    # predicted-form 2 suppression — set-equality shortcuts
    # mask the load-bearing ordering-divergence claim. The
    # comparator detects the divergence; PR 13 assertions read
    # the four-key shape at full structural fidelity.
    assert report["fixture_id"] == FIX_ORDERING_DIVERGENCE["fixture_id"]
    assert report["expectation"]["expected_narrow"] == [
        "flame_list_libraries",
        "forge_list_projects",
    ]
    assert report["observation"]["observed_narrow"] == [
        "forge_list_projects",
        "flame_list_libraries",
    ]
    assert report["divergence"]["narrow_diverged"] is True
```

**Total test body: ~50–65 lines** (including docstring +
inline comments).

#### 4.2.4 Assertion contract — four DivergenceReport keys verified

The four-key structural assertion contract enforces carrier
#17 (per-surface partitioning structurally identifiable) AND
verifies the ordering-divergence vector at full structural
fidelity:

| Key | Assertion type | Authority surface | Ordering-divergence verification |
|---|---|---|---|
| `report["fixture_id"]` | Direct equality with fixture's `fixture_id` | Join key | Join correctness (the comparator joined the right pair) |
| `report["expectation"]["expected_narrow"]` | Direct list equality with `["flame_list_libraries", "forge_list_projects"]` | Authored expectation surface | Authored sequence preserved through emission → persistence → readback → comparator |
| `report["observation"]["observed_narrow"]` | Direct list equality with `["forge_list_projects", "flame_list_libraries"]` | Runtime observation surface | Observed sequence preserved through chat_handler arbitration → emission → persistence → readback → comparator |
| `report["divergence"]["narrow_diverged"]` | Direct `is True` equality | Comparator's interpretive claim | Comparator's compare-as-persisted discipline detects the ordering-only divergence at direct list-equality |

**Order of assertions in the test body:**

1. `fixture_id` (join correctness).
2. `expectation["expected_narrow"]` (authored surface; the
   ordering-divergence vector's authored half).
3. `observation["observed_narrow"]` (runtime surface; the
   ordering-divergence vector's observed half).
4. `divergence["narrow_diverged"]` (interpretive claim; the
   comparator's recognition of the divergence).

The ordering mirrors the traversal trace: input → authored
→ runtime → comparator-derived. Future readers can verify
the ordering-divergence vector by inspection: assertions 2
+ 3 carry the same set in different order; assertion 4
confirms the comparator detected the divergence.

**Carrier #17 verification at use:** assertions 2 + 3 are
satisfied at distinct dict paths (`report["expectation"]`
vs. `report["observation"]`), structurally enforcing the
per-surface partitioning. The ordering-divergence vector is
identifiable at the structural shape level — both surfaces'
contributions are preserved in their authored sequence,
NOT collapsed through set-equality interpretive synthesis.

**§4.2 binding behavioral commitment verification at use:**
the comparator returns `narrow_diverged=True` per direct
list-equality (`_compare.py:503` — `obs_decision !=
exp_narrow`). No sort, no canonicalization, no semantic
coercion. The compare-as-persisted discipline holds end-to-
end under ordering-only pressure.

**Three predicted cleanup-pressure forms operationally
suppressed at the assertion contract:**

| Form | Suppression evidence at PR 13 assertion contract |
|---|---|
| Canonicalization pressure (framing §5.4 form 1) | Test body does NOT sort either list before comparison; comparator does not sort internally; assertions read sequences verbatim. |
| Set-equality collapse pressure (framing §5.4 form 2) | Test body uses direct list-equality assertions, NOT `set(...) == set(...)` shortcuts. The four-key structural shape is read at full fidelity. |
| Ordering-specific test helper pressure (framing §5.4 form 3) | Test body inlines all four assertions explicitly; no `assert_ordering_divergence(report, expected, observed)` helper absorbs the assertion logic. PR-11-LOCAL traverses-not-erases-seams discipline at gate level. |

---

## 5. Test count anchors

### 5.1 Forge env test count projection

```
217 baseline (PR 11 close §1 forge env collected)
+   1 PR 13 ordering-divergence test
= 218 forge env collected at PR 13 close
```

Per `feedback_counts_are_archaeology_grade`: 218 is the
locked target at PR 13 close. If the actual count at Step 3
(final verification) differs from 218, spec author must:

- Investigate the divergence (test collection issue?
  parametrize expansion? skip condition? PR 11 baseline
  drift?).
- Amend §5.1 with archaeology before close.
- Document the divergence at PR 13 close §6 (mechanical
  checkpoints).

**Named-vs-collected discipline:** PR 13 ships 1 named test;
no `parametrize` decorators; named == collected. The
named-equals-collected identity is structurally locked at
PR 13 by single-test pattern (one test function; no
parametrization; no test class).

### 5.2 Forge-bridge env test count projection

```
211 baseline (PR 11 close §1.4 forge-bridge env target;
              6-test gap inherited per
              project_v1_4_x_harness_debt)
+   1 PR 13 ordering-divergence test
= 212 forge-bridge env collected at PR 13 close (projected)
```

Forge-bridge env count NOT re-verified at PR 13 close beyond
inheritance documentation. The 6-test gap is PR 7-scope, not
PR 13-scope. **Do not conflate the two env counts** per
PR 8 close §5.6 + PR 10 close §1.4 + PR 11 close §5.2.

### 5.3 Test inventory at PR 13 close (locked)

| # | Test | File | Step |
|---|---|---|---|
| 1 | `test_recomposition_arc_ordering_divergence` | `test_pr13_ordering_divergence.py` | 2 |

The single test lands at Step 2 (the architectural-center).

---

## 6. Atomic step decomposition

PR 13 ships as a **3-step + close** atomic sequence per
framing §9.12 both-skeletons-at-Step-1 lock:

- Step 1: both skeletons (test module + fixture module, in
  one commit).
- Step 2: both architectural-centers (test body + FIXTURE
  dict, in one commit).
- Step 3: final verification (empty commit; archaeology in
  body).
- Close: PR 13 close artifact (single artifact at one
  commit; NOT same-commit with Gate 4 close per framing §11
  inheritance).

### 6.1 Step 1 — both skeletons (test module + fixture module, bundled)

**Atomic commit content (single commit landing TWO new files):**

- New file:
  `tests/corpus/test_pr13_ordering_divergence.py`
  - Module docstring (per §4.2.1 — PR-13-LOCAL +
    traversal trace + carrier travel by reference +
    test infrastructure import discipline + references).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports until used by test body
    at Step 2).
  - No test bodies, no module-level constants, no helper
    functions.
- New file:
  `tests/corpus/fixtures/fix_ordering_divergence.py`
  - Module docstring (per §4.1.1 — PR-13-LOCAL + carrier
    travel by reference + fixture purpose with grounded
    arbitration trace + references + fixture-data-
    discipline closing).
  - `from __future__ import annotations` ONLY (member 10
    discipline; no other imports — fixture-data-discipline
    member #9 prevents any import beyond `__future__`).
  - No `FIXTURE` dict declaration; no helpers; no constants.

**Both files at structurally-symmetric skeleton state.**
The lifecycle invariant (establishment → activation) holds
across both files. Framing §9.12 both-skeletons-at-Step-1
lock operational.

**Step 1 verification:**

- `pytest tests/corpus/test_pr13_ordering_divergence.py
  --collect-only -q` → 0 tests collected (skeleton only).
- `python -c "import tests.corpus.test_pr13_ordering_divergence"`
  → imports cleanly.
- `python -c "import tests.corpus.fixtures.fix_ordering_divergence"`
  → imports cleanly; no module-level symbols beyond docstring.
- `pytest tests/corpus/ --collect-only -q | tail -1` → 217
  collected (PR 11 baseline preserved at Step 1; PR 13 test
  not yet activated).
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr4_participation_creep.py
  tests/corpus/test_pr6_visual_asymmetry.py
  tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr9_*.py tests/corpus/test_pr10_*.py
  tests/corpus/test_pr11_recomposition_arc.py` → passes
  unchanged (PR 13 skeleton is target-disjoint from all
  four Layer 2 walkers' input sets + Layer 3 lint + PR 11
  recomposition arc).

**Step 1 commit body sections (mirroring PR 11 Step 1
pattern adapted for Gate 4 / PR 13 scope):**

```
phase-a.5.3.2: PR 13 Step 1 — both skeletons (test module + fixture module bundled)

PR 13 establishes two new files at skeleton state:

  - tests/corpus/fixtures/fix_ordering_divergence.py
  - tests/corpus/test_pr13_ordering_divergence.py

Both files at structurally-symmetric skeleton state. Module
docstrings carry PR-13-LOCAL binding statement verbatim +
17 active carriers cited by reference to canonical sources +
traversal/arbitration trace + references. `from __future__
import annotations` is the only import at each file. No
test bodies, no FIXTURE dict, no constants, no helpers.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-13-LOCAL binding statement (verbatim per A.5.3.2-PR13-FRAMING.md §0 + §5.5):

  PR 13 isolates ordering divergence as the sole pressure
  vector. Multi-vector fixture pressure within PR 13 scope —
  combining ordering with cardinality, partial-set,
  semantic-normalization, duplicate-handling, or any other
  divergence form — is rejected at the spec layer. The
  pure-isolation property is what gives PR 13 its
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

Architectural sufficiency signal (Step 1):

  - 0 production source modifications.
  - 2 new test/fixture files added at skeleton state.
  - 0 fifth walker; 0 _ALLOWLIST modifications; 0 Layer 3
    lint changes.

Both-skeletons-at-Step-1 lock (binding per A.5.3.2-PR13-FRAMING.md §9.12):

  Both PR 13 files undergo the same establishment →
  activation lifecycle transition. Asymmetric step
  structures (file-asymmetric / 4-step / 2-step compression)
  rejected at framing. Step 1 lands BOTH skeletons in one
  commit; Step 2 lands BOTH bodies in one commit; Step 3 is
  empty verification with archaeology in body.

What does NOT land at Step 1: test body (Step 2), FIXTURE
dict (Step 2), imports beyond `__future__ annotations`
(Step 2 + member 10 discipline).

Surfaces inventory at Step 1:

  1. fix_ordering_divergence.py module docstring.
  2. test_pr13_ordering_divergence.py module docstring.
  3. This commit body.

Total PR 13 surfaces accumulating toward close-time
archaeology: 3 (Step 1) + 1 (Step 2 commit body) + 1 (Step 3
commit body) = 5 commit-chain surfaces.

References:

  - A.5.3.2-PR13-SPEC.md (this step's implementation
    contract).
  - A.5.3.2-PR13-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
```

### 6.2 Step 2 — both architectural-centers (test body + FIXTURE dict bundled)

**Atomic commit content (single commit landing TWO file bodies):**

- `tests/corpus/test_pr13_ordering_divergence.py`:
  - Imports landed (per §4.2.2 final-state inventory):
    `pathlib`, `pytest`, `compare_records`,
    `drive_seed_fixture`, `FIX_ORDERING_DIVERGENCE`,
    `_apply_pr9_patches`, `_read_records`.
  - Test function: `test_recomposition_arc_ordering_divergence`
    (full body per §4.2.3).
  - No new module-level constants, no helper functions, no
    parametrize decorators.
- `tests/corpus/fixtures/fix_ordering_divergence.py`:
  - `FIXTURE` dict landed (per §4.1.2):
    ```python
    FIXTURE: dict = {
        "fixture_id": "fix-pr13-ordering-divergence",
        "prompt": "list",
        "expected_narrow": ["flame_list_libraries", "forge_list_projects"],
    }
    ```
  - No additional imports (member #9 fixture-data-
    discipline; `from __future__ import annotations`
    carried from Step 1 unchanged).

**Three-round review applies** per Gate 2 framing §5.7
integration-work elevation. PR 13's architectural-center is
the ordering-divergence recomposition arc operational
landing; carrier #17 at use + §4.2 binding behavioral
commitment at use + §5.4 three predicted cleanup-pressure
forms operationally suppressed are the load-bearing
verifications.

**Step 2 verification:**

- `pytest tests/corpus/test_pr13_ordering_divergence.py` →
  1/1 passed.
- `pytest tests/corpus/test_pr11_recomposition_arc.py
  tests/corpus/test_pr10_*.py tests/corpus/test_pr9_*.py
  tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr7_*.py
  tests/corpus/test_pr4_participation_creep.py` → passes
  unchanged.
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr6_visual_asymmetry.py` → passes
  unchanged.
- `pytest tests/corpus/ --collect-only -q | tail -1` →
  **218 collected** forge env (217 baseline + 1 PR 13 new).
  EXACT MATCH with §5.1 projection.
- Architectural sufficiency signal: `git diff --stat
  <PR-13-Step-1-commit>..HEAD -- forge_bridge/` returns
  EMPTY (zero production source modifications).

**Step 2 commit body sections (mirroring PR 11 Step 2 pattern adapted):**

```
phase-a.5.3.2: PR 13 Step 2 — architectural-center (test body + FIXTURE dict bundled)

PR 13 architectural-center lands two bodies in one commit:

  - tests/corpus/test_pr13_ordering_divergence.py: imports
    (pathlib, pytest, compare_records, drive_seed_fixture,
    FIX_ORDERING_DIVERGENCE, _apply_pr9_patches, _read_records)
    + 1 named test (test_recomposition_arc_ordering_divergence)
    exercising the full end-to-end recomposition arc.
  - tests/corpus/fixtures/fix_ordering_divergence.py: FIXTURE
    dict with fixture_id, prompt "list", expected_narrow
    [flame_list_libraries, forge_list_projects] (swap of
    observed arbitration order; the pure-isolation
    ordering-divergence vector).

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-13-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

Bundled-commit rationale:

The test needs the FIXTURE import + FIXTURE dict body
together to function. Both bodies bundled per spec §6.2 +
framing §9.12 both-skeletons-at-Step-1 lock applied
symmetrically at architectural-center (both bodies land in
one commit, mirroring the both-skeletons lock at Step 1).

Architectural-center load-bearing verifications:

  - Carrier #17 at use: DivergenceReport per-surface
    partitioning preserves authorship through emission →
    persistence → readback → join → interpretive comparison;
    assertions 2 + 3 satisfy distinct dict paths
    (report["expectation"] vs. report["observation"]).
  - PR 10 §4.2 binding behavioral commitment at use:
    comparator's direct list-equality (_compare.py:503)
    detects the ordering-only divergence as
    narrow_diverged=True without sort/canonicalization.
  - Three predicted cleanup-pressure forms (framing §5.4)
    operationally suppressed at assertion contract:
    canonicalization (no caller-side sort), set-equality
    collapse (no set(...) assertion shortcut), helper
    proliferation (no ordering-specific assertion helper).
  - PR-11-LOCAL discipline at gate level (Gate 3 close §3
    item 10): test body inlines the four-key assertion
    contract; no helper absorbs the assertion logic.

Recomposition-through-existing-seams operational evidence:

  PR 13 ships against the validated PR 10 comparator + PR 11
  recomposition arc unchanged. Zero modifications to
  comparator surface, recomposition arc pattern, fixture
  corpus, or test infrastructure. Architectural sufficiency
  signal target met at Step 2.

Preserved invariants:

  - 17 active carriers cited by reference (Step 1 inheritance).
  - Gate 2 binding framing clarification cited by reference.
  - Cross-surface unbinding clarification inherited unchanged.
  - PR-11-LOCAL discipline at gate level.

Architectural sufficiency signal (Step 2):

  - 0 production source modifications (verified at Step 2
    via `git diff --stat <Step-1-commit>..HEAD -- forge_bridge/`).
  - 2 new test/fixture files activated at this commit.
  - 217 + 1 = 218 forge env collected (locked).

§4.2 binding behavioral commitment verification at use:

  Test asserts list-equality on expected_narrow and
  observed_narrow at distinct dict paths. The comparator's
  compare-as-persisted discipline preserves the ordering
  vector through every traversal seam.

Surfaces inventory at Step 2:

  1. fix_ordering_divergence.py module docstring + FIXTURE dict.
  2. test_pr13_ordering_divergence.py module docstring +
     test body.
  3. Step 1 commit body.
  4. This commit body.

Total PR 13 surfaces accumulating toward close-time
archaeology: 4 commit-chain surfaces at Step 2.

References:

  - A.5.3.2-PR13-SPEC.md (this step's implementation contract).
  - A.5.3.2-PR13-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
```

### 6.3 Step 3 — final verification (empty commit; archaeology in body)

**Atomic commit content:**

- No file changes (empty commit; `git commit --allow-empty`).
- Commit message body carries:
  - 10-item Step 3 verification checklist (per §1 regression
    contracts + framing §9 phase-end conditions).
  - 17 inherited carriers cited by reference.
  - PR-13-LOCAL binding statement verbatim.
  - §2.4 Gate 4 architectural commitment verbatim.
  - Full PR 13 surfaces inventory.
  - Spec amendments at incarnation (if any surfaced during
    Steps 1–2).
  - Cleanup-pressure-resistance archaeology (predicted-form
    outcomes: ABSENCE / SURFACE per framing §5.4).
  - Placement A contribution recording (predicted-form
    outcomes per framing §6.1).
  - Placement B precondition manifestation recording
    (preconditions 1 + 2 manifest at framing time;
    precondition 3 cumulative across PR 14 + PR 15).
  - §5.3 candidate methodology observation outcome.
  - Catch-point migration candidate methodology contribution
    (spec-drafting-time grounding catch — fifth instance
    per spec §0).
  - PR 13 commit chain summary (Step 1 + Step 2 + Step 3
    commit hashes).
  - Next: PR 13 close artifact (single artifact at next
    commit; NOT same-commit with Gate 4 close).

**Step 3 verification checklist (10 items):**

1. **PR 13 suite:** `pytest tests/corpus/test_pr13_ordering_divergence.py`
   → 1/1 passed.
2. **Existing suites regression:** `pytest tests/corpus/
   --collect-only -q | tail -1` → 218 collected forge env;
   all suites pass unchanged.
3. **PR 4 + PR 5 chat-handler + no-dependency integration
   tests:** pass unchanged (no chat_handler arbitration
   surface modifications at PR 13).
4. **PR 6 Layer 3 lint regression:** 17/17 passed unchanged;
   zero new `emit_divergence_capture` call sites at PR 13.
5. **Four Layer 2 walkers regression:** all four (PR 4 +
   PR 8 + PR 9 + PR 10) pass unchanged; parallel-not-
   extension boundary preserved.
6. **PR 3 discipline:** 1/1 passed unchanged; corpus-
   subtree auto-exclusion handles `tests/corpus/test_pr13_*.py`
   + `tests/corpus/fixtures/fix_ordering_divergence.py`
   placements.
7. **PR 11 recomposition arc regression:** 3/3 passed
   unchanged; PR 13 inherits consumption pattern without
   modification.
8. **Public API regression:** `forge_bridge.__all__` at 19
   symbols.
9. **Verbatim travel verification:**
   - PR-13-LOCAL + 17 carriers cited by reference at both
     PR 13 module docstrings (Step 1 verified).
   - §2.4 Gate 4 architectural commitment travels at this
     spec §0 + §1 + §2 + Step 1, 2, 3 commit body
     "architectural commitment" sections.
   - 17 inherited carriers cited by reference at both PR 13
     module docstrings per §4.1.1 + §4.2.1.
10. **Architectural sufficiency signal verification:** `git
    diff --stat <PR-13-framing-commit>..HEAD -- forge_bridge/`
    returns EMPTY (zero production source modifications
    across PR 13's commit chain). §1 regression contract #10
    + framing §5.3 binding decision + framing §9.3.

**Step 3 commit type:** empty verification commit, no code
changes. Mirrors PR 9 Step 5 (`159ccd2`) + PR 10 Step 5
(`d04753c`) + PR 11 Step 3 (`ae69fba`) pattern.

**Step 3 commit body sections (mirroring PR 11 Step 3 pattern adapted):**

```
phase-a.5.3.2: PR 13 Step 3 — final verification (empty commit; archaeology in body)

Step 3 final verification: empty commit; archaeology
documented in body.

Architectural commitment (verbatim per A.5.3.2-GATE-4-FRAMING.md §2.4):

  Gate 4 is the deliberate continuation of empirically
  bounded topology proof through divergence-shape robustness
  exercise.

PR-13-LOCAL binding statement (verbatim per §0 + framing §5.5):

  [verbatim form]

Step 3 verification checklist (10/10 items):

  1. PR 13 suite: pytest tests/corpus/test_pr13_ordering_divergence.py
     → 1/1 passed ✓
  2. Existing suites regression: 218 forge env collected ✓
  3. PR 4 + PR 5 chat-handler + no-dependency tests: pass
     unchanged ✓
  4. PR 6 Layer 3 lint regression: 17/17 passed unchanged ✓
  5. Four Layer 2 walkers regression: pass unchanged ✓
  6. PR 3 discipline: 1/1 passed unchanged; corpus-subtree
     auto-exclusion handles new PR 13 files ✓
  7. PR 11 recomposition arc regression: 3/3 passed
     unchanged ✓
  8. Public API regression: forge_bridge.__all__ at 19
     symbols ✓
  9. Verbatim travel verification: PR-13-LOCAL + 17 carriers
     cited by reference at both PR 13 module docstrings;
     §2.4 architectural commitment at spec + commit bodies
     (NOT at docstrings) ✓
 10. Architectural sufficiency signal: 0 production source
     modifications ✓

Placement A contribution recording (per A.5.3.2-PR13-FRAMING.md §6.1):

  | Form | Outcome | Placement A contribution |
  |---|---|---|
  | Canonicalization pressure | ABSENCE / SURFACE | [per outcome] |
  | Set-equality collapse pressure | ABSENCE / SURFACE | [per outcome] |
  | Ordering-specific test helper pressure | ABSENCE / SURFACE | [per outcome] |

  PR 13 contributes [N]-form-ABSENCE evidence toward
  Placement A third-instance corroboration; Gate 4 close
  reads cumulative across PR 13 + PR 14 + PR 15.

Placement B precondition manifestation recording (per A.5.3.2-PR13-FRAMING.md §6.2):

  Precondition 1 (prior pressure prediction at framing time):
    Manifest at A.5.3.2-PR13-FRAMING.md §5.4 + this spec §4.2.4.
  Precondition 2 (named suppression mechanism):
    Manifest at A.5.3.2-PR13-FRAMING.md §5.4 + this spec §4.2.4.
  Precondition 3 (corroborated recurrence):
    NOT manifest at PR 13 alone; cumulative across PR 14 +
    PR 15; Gate 4 close evaluates.

§5.3 candidate methodology observation outcome:

  PR 13 framing → spec drafting catch-point: spec-drafting-
  time fixture-cardinality grounding (this PR's instance
  per spec §0 fifth catch-point-migration instance).
  Catch-point migrates earlier still: from PR 11 framing-
  spec drafting time (PR 11 instance #3) and PR 13 framing-
  convergence-pass pre-commit (PR 13 instance #4) to PR 13
  spec-drafting-time pre-spec-lock (PR 13 instance #5).

Catch-point migration candidate methodology contribution:

  Instance #5: spec-drafting-time fixture-cardinality
  grounding. The framing's §2.2 + §4.1 symbolic notation
  [A, B, C] → [C, A, B] (3-element rotation) could have
  silently drifted into spec-level implementation
  assumption. Instead, grounding the arbitration topology
  in actual _PR9_REACHABLE_TOOLS arbitration behavior
  BEFORE locking spec values surfaced the structural
  constraint (3-element deterministic survival
  unavailable). Spec adopted 2-element form preserving
  empirically bounded topology discipline.

Cleanup-pressure-resistance class additions registered (if any):

  [recorded based on actual implementation pressure
   encountered at Steps 1–2]

PR 13 commit chain:

  Step 1 (skeleton): [TBD commit hash]
  Step 2 (architectural-center): [TBD commit hash]
  Step 3 (verification): [this commit]

Total PR 13 surfaces at Step 3 close: 5 commit-chain surfaces.

Next: PR 13 close artifact (single artifact at next commit;
NOT same-commit with Gate 4 close per Gate 4 framing §11.8 —
Gate 4 close pairs at same commit with the final primary PR
close, which is PR 15 close OR PR 12 close if PR 12
materializes last per Gate 2 + Gate 3 close precedent).

References:

  - A.5.3.2-PR13-SPEC.md (PR 13 implementation contract).
  - A.5.3.2-PR13-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-GATE-4-FRAMING.md (gate-level inheritance).
```

### 6.4 Close commit — PR 13 close artifact (single artifact at one commit)

Per framing §11 inheritance: PR 13 close ships standalone,
NOT same-commit with Gate 4 close. Per Gate 4 framing §11.8,
Gate 4 close artifact pairs at same commit with the final
primary PR close (PR 15 close OR PR 12 close if PR 12
materializes last) per Gate 2 + Gate 3 close precedent. PR 13
is the FIRST of the three primary PRs sequenced within
Gate 4; PR 13 close ships standalone at its own commit.

**Atomic commit content:**

- New file:
  `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR13-CLOSE.md`

**PR 13 close artifact owns (per framing §11 close criteria):**

- PR 13 implementation arc archaeology (commit chain table).
- §5.3 candidate methodology observation evaluation at
  PR 13 scope (ABSENCE vs. SURFACE outcomes per predicted
  form).
- §5.5 PR-13-LOCAL pure-isolation discipline operational
  archaeology.
- Ordering-divergence pure-isolation case operational
  archaeology.
- Architectural sufficiency signal (0-prod-mod) validation
  evidence at PR 13 scope.
- PR-13-scoped cleanup-pressure-form encounters + protection
  registrations (per framing §9.10).
- Placement A operational corroboration contribution
  (predicted-form outcomes per framing §6.1).
- Placement B methodology-stack maturation substrate
  contribution (preconditions 1 + 2 manifestation
  recording per framing §6.2).
- §2.4 Gate 4 architectural commitment travel inventory
  per framing §9.7.
- Catch-point migration candidate methodology contribution
  (spec-drafting-time grounding catch — fifth instance per
  spec §0).
- Test-internal archaeology surfaces inheritance
  verification per framing §9.11.
- Imports-land-when-used (member #10) discipline
  verification at both new files symmetrically per
  framing §9.9.
- Both-skeletons-at-Step-1 lock operational archaeology per
  framing §9.12.

**Gate 4 close (same-commit-paired with PR 15 close per framing §11.8) will own (NOT in PR 13 close scope):**

- Gate-arc synthesis across PR 13 + PR 14 + PR 15.
- Cleanup-pressure-resistance class final inventory at
  Gate 4 scope (10 members + any PR 13/14/15 additions).
- Placement A third-instance corroboration evaluation
  (cumulative across PR 13 + PR 14 + PR 15).
- Placement B three-precondition operational manifestation
  evaluation (precondition 3 cumulative across PR 13 +
  PR 14 + PR 15).
- §5.3 candidate methodology gate-level promotion evaluation.
- 0-prod-mod-as-architectural-sufficiency-signal gate-level
  promotion evaluation.
- Recomposition-through-existing-seams cumulative
  corroboration evaluation.
- Catch-point migration candidate methodology gate-level
  promotion evaluation.
- Gate-level inheritance contract toward Gate 5.
- Conditional PR 12 disposition at gate level (deferred per
  Gate 4 framing §5.10).

**Close artifact not bundled into Steps 1–3:** the close
artifact ships as a distinct subsequent commit after Step 3.
No code changes in the close commit beyond the new close
artifact.

### 6.5 Step N.5 surgical cadence — available if needed

If implementation prep or three-round review at Steps 1–2
surfaces mid-flight guidance that adds value to a recently-
shipped deliverable, the Step N.5 surgical cadence is
available (3-times corroborated at Gate 2 close + PR 10
added zero + PR 11 added zero). PR 13 framing §3.5 +
canonicalized amendment-at-incarnation cluster: pattern
available without re-framing.

**If Step N.5 fires at PR 13:** the surgical commit lands
as a small additive amendment before the next major
deliverable (Step 2 architectural-center commit OR Step 3
verification commit), preserving the "distinct atomic
boundary" discipline.

---

## 7. Phase-end conditions for PR 13

PR 13 closes when (mirroring framing §9):

1. **The ordering-divergence recomposition arc operates
   end-to-end.** The fixture drives through the full seam
   traversal and returns the four-key DivergenceReport
   shape with `narrow_diverged=True`.

2. **The full seam traversal is visible at the test
   surface.** No helper absorbs the traversal; the test
   explicitly visits each seam at the body level.

3. **0 production source modifications.** Framing §5.3
   binding decision; §1 regression contract #10; §6.2
   Step 2 verification.

4. **No production abstraction whose primary purpose is
   "making recomposition cleaner."** Framing §5.4
   predicted-form 3 suppression + PR-11-LOCAL discipline
   at gate level.

5. **Layer 1 allowlist** verified unchanged (§8.1).

6. **Four Layer 2 walkers** pass unchanged (§8.2).

7. **Layer 3 lint** passes unchanged (§8.3).

8. **Carrier #17 holds operationally** through the
   ordering-divergence recomposition arc — the test's
   DivergenceReport assertions verify per-surface
   partitioning structurally at the report's outer dict
   shape.

9. **PR-13-LOCAL binding statement travels verbatim** at
   both PR 13 module docstrings + all PR 13 commit message
   bodies under "preserved invariants" / "PR-13-LOCAL"
   sections.

10. **§2.4 Gate 4 architectural commitment travels
    verbatim** at this spec §0 + §1 + §2 + all 3 PR 13
    step commit bodies under "architectural commitment"
    sections + PR 13 close artifact §1 + §6.5 (NOT at
    fixture/test docstrings).

11. **17 carriers cited by reference** at both PR 13 module
    docstrings per §4.1.1 + §4.2.1 (relevance-by-file
    ordering with PR-13-LOCAL at TOP).

12. **Test count locks at PR 13 close target** (218 forge
    env collected; verified at §6.3 Step 3 + §6.4 close).

13. **PR 13 close artifact ships standalone** at single
    commit (NOT same-commit with Gate 4 close per framing
    §11 inheritance).

14. **`forge_bridge.__all__`** stays at 19 symbols.

15. **Three-authority-surface partition + PR-8-INTERNAL
    three-way authority partition + 10-member cleanup-
    pressure-resistance class + PR 10 read-side structural
    parallel** all preserve unchanged.

16. **Four-walker Layer 2 partition** preserves unchanged
    (parallel-not-extension boundary; shared AST mechanics
    do not imply shared ontology).

17. **Any new cleanup-pressure-resistance class members
    surfaced during PR 13** register at PR 13 close with
    explicit protection language + operational enforcement
    placement (per framing §9.10).

18. **Placement A predicted-form outcomes recorded** at
    PR 13 close per framing §6.1 (ABSENCE / SURFACE per
    form).

19. **Placement B precondition manifestation recorded** at
    PR 13 close per framing §6.2 (preconditions 1 + 2
    manifest at framing time; precondition 3 cumulative
    deferred).

20. **§5.3 candidate methodology observation evaluation
    registered** at PR 13 close per framing §6.4 asymmetric
    weighting.

21. **Catch-point migration candidate methodology
    contribution registered** at PR 13 close (spec-
    drafting-time fixture-cardinality grounding — fifth
    instance per spec §0).

22. **Both-skeletons-at-Step-1 lock operationally
    verified** — both files traveled the establishment →
    activation lifecycle symmetrically; no asymmetric step
    structure surfaced.

23. **Imports-land-when-used (member #10) discipline
    verified at both new files** — Step 1 had only
    `__future__ annotations`; Step 2 landed all imports +
    bodies; Step 3 added zero imports.

24. **Test-internal archaeology surfaces inheritance
    verified** — `_apply_pr9_patches` + `_read_records`
    consumed unchanged from PR 9 + PR 11 patterns.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` no modification

`tests/corpus/test_pr13_ordering_divergence.py` ships under
`tests/corpus/`; `tests/corpus/fixtures/fix_ordering_divergence.py`
ships under `tests/corpus/fixtures/`. Neither is inside the
corpus subtree (`forge_bridge/corpus/`). The PR 3
discipline's `_ALLOWLIST` check applies to files in the
broader codebase that import `from forge_bridge.corpus`;
`tests/corpus/` files are NOT subject to the discipline
check in the same way (per existing PR 4–PR 11 test
module precedent + PR 10 §4.4 amendment archaeology +
PR 11 spec §8.1 inheritance).

**Verification step at Step 1 implementation prep:**
confirm PR 3 discipline implementation
(`test_pr3_discipline.py:92-96` corpus-subtree auto-exclusion)
handles `tests/corpus/` + `tests/corpus/fixtures/` files
blanket-style. Expected: no allowlist modification needed;
PR 13 Step 1 verification confirms.

### 8.2 Layer 2 — four-walker partition no modification

PR 13 adds no fifth walker. The four existing walkers
(PR 4 + PR 8 + PR 9 + PR 10) continue to enforce their
respective ontologies; PR 13 test/fixture additions
operationally engage:

- PR 4 walker target: narrowing-subsystem production sources
  (`forge_bridge/console/_tool_filter.py` etc.). PR 13
  modifies none.
- PR 8 walker target: `forge_bridge/corpus/_seed.py`.
  PR 13 modifies none.
- PR 9 walker target: `tests/corpus/fixtures/*.py`. **PR 13
  adds one new fixture** under the walker's
  `_FIXTURE_PERMITTED_IMPORTS` value-locked constraint
  (member #9 fixture-data-discipline). The new fixture's
  imports are limited to `from __future__ import
  annotations` only; the single-symbol gate (`FIXTURE`
  module export) is satisfied.
- PR 10 walker target: `forge_bridge/corpus/_compare.py`.
  PR 13 modifies none.

Step 3 verification item 5 confirms all four walkers pass
unchanged against the post-PR-13 codebase.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 13.
Properties A–D govern `emit_divergence_capture` call sites;
PR 13 introduces no new call sites (the chat_handler-driven
emission inside `drive_seed_fixture` consumes the existing
call site at `handlers.py:1185`, which is PR 4–authored
and PR 6-protected). The lint's discovery walk input set
unchanged.

Step 3 verification item 4 confirms 17/17 PR 6 lint tests
pass unchanged.

---

## 9. Resume protocol (for future archaeology)

**If implementation pauses mid-PR-13 and resumes in a new
session, the resume protocol is:**

1. **Read this spec** (§4 per-file derivation + §6 atomic
   step decomposition + §7 phase-end conditions).
2. **Read PR 13 framing** (`8f429b2`) §0 + §1 + §2 + §3 +
   §5 + §9 + §10 (load-bearing binding decisions per
   framing-close direction).
3. **Read Gate 4 framing** (`fbf2285`) §2.4 + §3 + §5 + §6
   (gate-level inheritance contract).
4. **Read PR 11 close** (`ee2225b`) §1 + §2 (architectural
   signals + PR 13 inheritance contract per Gate 4 framing
   §3.7).
5. **Confirm state:** `git log --oneline -10` reflects the
   PR 13 commits to-date.
6. **Identify resume point:** which Step has landed; which
   Step is next.
7. **Apply member 10 + grounding discipline** before
   re-entering implementation.

**For new sessions resuming at Step 2 (post-skeleton):**

- Read Step 1 commit body's archaeology section.
- Verify Step 1 skeleton matches §4.1.1 + §4.2.1 +
  imports-discipline contracts.
- If skeleton drift detected, register Step N.5 surgical
  amendment before Step 2 architectural-center commit
  lands.

**For new sessions resuming at Step 3 (post-architectural-
center):**

- Read Step 2 commit body's archaeology section.
- Run Step 2 verification checklist (§6.2 verification
  items).
- If verification surfaces drift (test count divergence,
  carrier travel gap, §2.4 commitment travel gap),
  register Step N.5 surgical amendment before Step 3
  final-verification commit lands.

**For new sessions resuming at Close (post-Step-3):**

- Read Step 3 commit body's full archaeology.
- Draft PR 13 close artifact (mirror PR 11 close §1–§8
  structure adapted for Gate 4 / PR 13 scope) per §6.4.

---

## 10. Cross-references

- `A.5.3.2-PR13-FRAMING.md` (`8f429b2`) — **immediate
  predecessor; binding pre-spec contract.** §0 PR-13-LOCAL
  binding statement; §1 predecessors; §2 PR 13 objective +
  Gate 4 calibration role; §3 architectural inheritance
  from Gate 4; §4 architectural delta (fixture shape +
  test shape + ordering-divergence as pure single-vector
  pressure + evidence inflation rejection); §5 ten binding
  decisions; §6 Placement A + B substrate contribution;
  §7 26 non-acquisition commitments; §9 12 phase-end
  conditions; §10 cross-references inherited.
- `A.5.3.2-GATE-4-FRAMING.md` (`fbf2285`) — gate-level
  inheritance contract; §2.4 architectural commitment
  (verbatim form); §3.1 17 active carriers + no new
  carriers; §3.6 five candidate methodologies inherited;
  §3.7 PR-11-LOCAL discipline at gate level; §4.4 + §4.5
  Placement B claim + three causality preconditions; §5.5
  three-PR slot structure; §5.6 PR ordering locked; §5.8
  Placement A target; §6.3 Placement B claim; §6.5 causal
  vs. passive absence governance; §7 22 non-acquisition
  commitments.
- `A.5.3.2-PR11-CLOSE.md` (`ee2225b`) — recomposition arc
  operational end-to-end; PR-11-LOCAL traverses-not-erases-
  seams discipline (inherited at gate level per Gate 3
  close §3 item 10 + Gate 4 framing §3.7); zero-incarnation-
  amendments cleanest arc; 217 forge env baseline (PR 13
  close arithmetic: 217 + 1 = 218).
- `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`) — gate-level
  inheritance contract for Gate 4; §1.5 cleanup-pressure-
  resistance class promotion (10 members); §1.6 carrier
  #16 promotion; §1.7 §5.3 candidate methodology two-
  instance corroboration (PR 13 Placement A target
  inherits); §2 Gate 4 inheritance contract; §3 13
  non-revisitable items; §6 four §7.3 ontological
  questions handed forward.
- `A.5.3.2-PR11-SPEC.md` (`6a5df95`) — **spec structure
  precedent.** PR 13 spec mirrors PR 11 spec shape per
  established cadence; relevant sections: §0 (citation by
  reference interpretation), §4.1 (per-file derivation
  pattern), §6 (atomic step decomposition pattern), §7
  (phase-end conditions pattern).
- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — comparator surface
  operational; PR 10 spec §4.1.6 reference implementation
  (preserved at PR 13); **PR 10 §4.2 binding behavioral
  commitment ("compare as persisted") — the central
  architectural commitment PR 13 exercises under ordering-
  divergence pressure**; class member #10 (imports-land-
  when-used; operationally enforced at PR 13).
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture
  corpus + fixture naming convention PR 13 inherits; PR 9
  walker + member #9 protection (operationally enforced
  at PR 13 fixture); test-internal archaeology surfaces
  (`_apply_pr9_patches`, `_read_records`) PR 13 consumes
  unchanged.
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — Path B locked
  precedent; binding framing clarification on cross-
  surface unbinding (preserved at PR 13 inheritance via
  Gate 4 framing §5.2).
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc
  synthesis precedent; §2.1 two foundational dependencies
  PR 13 exercises operationally (record_kind partitioning
  + fixture_id joinability); §7.3 four ontological
  questions (preserved unbound at PR 13 inheritance).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — three-
  authority-surface partition (preserved at PR 13
  inheritance); call-site-owned arbitration inputs binding
  clarification (preserved).
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — PR-INTERNAL three-
  way authority partition (write-side §4.1.5.1) preserved
  at PR 13 inheritance; carrier #15 source; member #7 +
  member #8.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces; class members #1–#6.
- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape; six
  interlocking structural-invariant pairs.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing.
- `forge_bridge/corpus/_compare.py` — PR 10 comparator
  module; PR 13 consumes `compare_records` +
  `DivergenceReport` unchanged. `_compare.py:503` is the
  direct list-equality computation point PR 13's
  ordering-divergence pressure operationally exercises.
- `forge_bridge/corpus/_seed.py` — PR 8 authored
  expectation surface; PR 13 drives through
  `drive_seed_fixture` unchanged.
- `forge_bridge/corpus/_capture.py` — PR 7 observation
  surface; PR 13 captures through `emit_divergence_capture`
  unchanged (transitively via `chat_handler`).
- `forge_bridge/console/_tool_filter.py` — PR14 +
  PR21 arbitration semantics; PR 13's prompt `"list"`
  exercises the PR14 keyword filter (2-candidate output)
  + PR21 deterministic_narrow (no-collapse-at-tie). PR 13
  does NOT modify this surface.
- `tests/corpus/test_pr11_recomposition_arc.py` — PR 11
  recomposition arc consumption pattern; PR 13 reuses the
  pattern verbatim per Gate 3 close §2.2 + Gate 4 framing
  §3.7.
- `tests/corpus/test_pr10_comparator.py` +
  `test_pr10_comparator_discipline.py` — PR 10 comparator
  test modules; PR 13 consumes unchanged.
- `tests/corpus/fixtures/fix_multi_match.py:105-140` —
  **PR 9 multi-match arbitration trace; PR 13 fixture
  reuses the grounded trace at exactly one surface
  variance (authored expectation swap).** This is the
  ground-truth grounding source for PR 13 fixture's
  arbitration trace.
- `tests/corpus/fixtures/fix_single_survivor.py` +
  `fix_no_keyword_match.py` — PR 9 fixture corpus
  preserved unchanged.
- `tests/corpus/test_pr9_fixture_integration.py` —
  `_apply_pr9_patches` + `_read_records` PR 13 imports as
  test-internal archaeology surfaces;
  `_PR9_REACHABLE_TOOLS:208-213` declares the 4-tool
  reachable set + ordering PR 13 inherits.
- `tests/corpus/conftest.py::clean_rate_limit_state` —
  PR 13 test consumes per PR 9 + PR 10 + PR 11 fixture
  pattern.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` —
  Layer 1; NOT MODIFIED at PR 13 per §8.1.
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2
  (PR 4 walker); preserves unchanged.
- `tests/corpus/test_pr8_seed_surface.py` — Layer 2 (PR 8
  walker); preserves unchanged.
- `tests/corpus/test_pr9_fixture_discipline.py` — Layer 2
  (PR 9 walker); **PR 13 fixture engages this walker
  operationally** — the new fixture must satisfy
  `_FIXTURE_PERMITTED_IMPORTS` value-lock + single-symbol-
  gate constraints per member #9.
- `tests/corpus/test_pr10_comparator_discipline.py` —
  Layer 2 (PR 10 walker); preserves unchanged.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3
  lint; preserves unchanged.
- `tests/corpus/test_pr13_ordering_divergence.py` (planned,
  PR 13) — single new test module.
- `tests/corpus/fixtures/fix_ordering_divergence.py`
  (planned, PR 13) — single new fixture file.
- `A.5.3.2-PR13-CLOSE.md` (planned at PR 13 final commit) —
  PR 13 close artifact; standalone (NOT same-commit with
  Gate 4 close).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` —
  promotion-candidate methodology seed; PR 13 will
  contribute (at PR 13 close evaluation):
  - First-Gate-4-instance toward §5.3 candidate methodology
    third-instance corroboration (Placement A).
  - First-Gate-4-instance toward 0-prod-mod-as-architectural-
    sufficiency-signal cumulative evidence.
  - First-Gate-4-instance toward recomposition-through-
    existing-seams cumulative corroboration.
  - First-Gate-4-instance toward single-center vs.
    cumulative-multi-step architectural-concentration
    taxonomy interpretation.
  - **Fifth catch-point-migration candidate methodology
    instance** (spec-drafting-time fixture-cardinality
    grounding pre-spec-lock).

---

PR 13 spec locks here. PR 13 Step 1 (both skeletons; test
module + fixture module bundled) drafts at the next
implementation step per the cadence (spec → Step 1 → Step 2
→ Step 3 → close). The Step 1 commit lands the two new files
at structurally-symmetric skeleton state; Step 2 lands both
file bodies (test body + FIXTURE dict) in one commit; Step 3
empty-commits the final verification archaeology; the close
commit ships PR 13 close artifact standalone (NOT
same-commit with Gate 4 close — Gate 4 close pairs at same
commit with the final primary PR close per Gate 4 framing
§11.8, which is PR 15 close OR PR 12 close if PR 12
materializes last per Gate 2 + Gate 3 close precedent).

PR 13 is **the Gate 4 calibration exercise**. The substrate
operates against the validated PR 10 comparator + PR 11
recomposition arc unchanged. The ordering-divergence
pure-isolation case operates as Placement A substrate
(predicted cleanup-pressure forms register at close as
ABSENCE / SURFACE per framing §6.1) + Placement B substrate
(preconditions 1 + 2 manifest at framing time; precondition
3 cumulative across PR 13 + PR 14 + PR 15). The architectural
sufficiency signal (0 production source modifications)
operationalizes as the first Gate 4 instance toward gate-
level promotion candidacy. The catch-point-migration
candidate methodology continues maturing operationally —
PR 13 contributes a fifth instance at spec-drafting-time
pre-spec-lock; Gate 4 close evaluates cumulative
progression for prescriptive promotion candidacy.

PR-13-LOCAL pure-isolation discipline binds. The §2.4 Gate 4
architectural commitment travels verbatim at this spec body
+ all PR 13 commit message bodies under "architectural
commitment" sections + PR 13 close artifact (NOT at fixture/
test docstrings). PR-13-LOCAL travels verbatim at both PR 13
module docstrings + all PR 13 commit message bodies under
"preserved invariants" / "PR-13-LOCAL" sections. The
asymmetry preserves the carrier / governing sentence /
methodology-stack category integrity Gate 4 framing
established.
