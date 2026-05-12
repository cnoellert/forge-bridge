# A.5.3.2 PR 11 — Spec (end-to-end recomposition arc + Gate 3 closure convergence)

**Status:** Spec-stage artifact for PR 11 of Gate 3. PR 11
framing locked at `97c3fb4` (1283 lines); this spec derives the
implementation contract by finalizing the symbol-level decisions
named in the framing's six binding decisions + the two pre-spec
decisions surfaced at framing→spec convergence (test count = 3;
test infrastructure = IMPORT from PR 9 as test-internal
archaeology surfaces).

PR 11 is the second of two (or conditionally three) PRs sequenced
within Gate 3 per Gate 3 framing §10. **PR 11 close artifact +
Gate 3 close artifact ship at the SAME final commit** per Gate 3
framing §11 — PR 11 close owns PR 11-scoped archaeology; Gate 3
close owns gate-arc synthesis (per PR 11 framing §11 explicit
owns/defers split).

This spec's job: derive file-level precision from framing's
locked decisions. Single new test module
(`tests/corpus/test_pr11_recomposition_arc.py`); three named
tests mapped 1:1 to the three PR 9 fixture outcome classes;
explicit recomposition-through-existing-seams discipline at
every test body. The spec's outputs are mergeability anchors —
file paths, function names, test names, assertion contracts —
that PR 11 close §6 will verify against.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

**Seventeen carriers** travel verbatim into PR 11's surface
(same set Gate 3 framing locked at §3.1 + PR 10 spec §0
mirrored). PR 11 introduces **zero new numbered carriers**
beyond Gate 3 framing's #17 (per PR 11 framing §3.1). Carrier
count discipline: **16 active carriers + candidate #16**, NOT
"17 active" — promotion of candidate #16 is Gate 3 close scope.

**Two additional governing sentences travel at reduced sites:**

- The **Gate-3-LOCAL governing sentence** ("Gate 3 proves
  topology, not infrastructure.") is the **candidate carrier
  #16 corroboration substrate** per Gate 3 framing §6.1. PR 11
  contributes the remaining ≥1 surface (≥4 total) the Gate 3
  close promotion evaluation reads. Travels into PR 11 test
  module docstring + PR 11 commit message bodies, always with
  explicit *candidate carrier #16 corroboration substrate*
  marking.

- The **Gate 3 binding framing clarification on cross-surface
  unbinding** (Gate 3 framing §6.2):
  > **The comparator's authority is bounded to within-surface
  > divergence between authored expectation and observed
  > arbitration outcome for a single operational arbitration
  > surface. Cross-surface comparator semantics are
  > intentionally unbound pending dedicated framing review.**
  Inherited at PR 11 unchanged; governs scope.

**One PR-11-LOCAL binding statement** (per PR 11 framing §5.6,
scope-local per PR-N-LOCAL non-regeneration rule):

> **PR 11 traverses the decomposition seams established by
> Gate 2 + Gate 3 substrate work without erasing them.
> Call-site awkwardness during recomposition is acceptable
> evidence that the decomposition boundaries held; introducing
> production abstractions whose primary purpose is "making
> recomposition cleaner" is rejected at the spec layer.**

Travels into PR 11 test module docstring + PR 11 commit
message bodies. Does NOT regenerate beyond PR 11 scope.

**Three additional PR-LOCAL bindings inherited unchanged** (per
PR 10 spec §0 mirroring; none regenerate at PR 11 surfaces
beyond their PR-of-origin scope):

- PR 10 proactive scope guardrail (`_compare.py` module
  docstring + comparator function docstring).
- PR 10 §4.2 binding behavioral commitment ("compare as
  persisted").
- PR-10-LOCAL binding statement (read-only mutability
  invariant; `_compare.py` function docstring).

The seventeen carriers + Gate-3-LOCAL form + PR-11-LOCAL
travel into:

1. `tests/corpus/test_pr11_recomposition_arc.py` top-level
   docstring (relevance-by-file ordering: Gate-3-LOCAL +
   PR-11-LOCAL + traversal trace at TOP; inherited carriers
   #1–#15 + #17 + Gate 2 binding framing clarification cited
   by reference to canonical sources after).
2. PR 11 commit message bodies under "preserved invariants" /
   "Gate-3-LOCAL corroboration" sections.

### Active carrier #17 — recomposition discipline (introduced at Gate 3 framing §5.1)

> **Recomposition preserves authorship. The comparator joins
> observation + expectation records by `fixture_id` at read
> time; the join produces a derived view that names each
> authority surface's contribution explicitly. Cleanup pressure
> to collapse the three-authority-surface partition through
> interpretive synthesis is rejected at the spec layer.**

Carrier #17 is enacted at PR 11 **at use** — every PR 11 test
body traverses the join (observation + expectation → comparator
→ DivergenceReport) and asserts on the report's per-surface
partitioning structurally.

### Inherited carriers #1–#15 — verbatim

PR 11 spec mirrors PR 10 spec §0's full carrier text by
reference to canonical sources rather than reproducing
in-line. The 15 inherited carriers (production-truth source:
`forge_bridge/corpus/_capture.py:6–135` + `forge_bridge/corpus/_seed.py:19–135`
+ `forge_bridge/corpus/_compare.py` module docstring) carry
forward unchanged. PR 11 spec authors must NOT reproduce them
in-line — citing by reference + verbatim travel at the
test-module docstring is the discipline.

### Binding framing clarification — call-site-owned arbitration inputs (Gate 2)

> **Arbitration-state fields remain call-site-owned explicit
> inputs. Dispatch provenance is contextual metadata derived at
> emission time and does not participate in arbitration
> semantics.**

Inherited unchanged. PR 11 does not modify dispatch-provenance
resolution or arbitration-state field handling; the carrier's
operational placement remains at `_capture.py` +
`_dispatch_context`.

---

## 1. Real job (PR 11 in one paragraph)

PR 11 ships a single new test module
(`tests/corpus/test_pr11_recomposition_arc.py`) containing
**three integration tests** that exercise the end-to-end
recomposition arc — driving each PR 9 fixture through the full
decomposition seam path (fixture → `drive_seed_fixture` →
`chat_handler` arbitration → `emit_divergence_capture` +
`emit_seed_expectation` → JSONL persistence → reader →
`compare_records` → `DivergenceReport` assertions). The tests
operationally demonstrate (a) recomposition through existing
seams (PR-11-LOCAL §0); (b) carrier #17 at use; (c) the
Gate 2 + Gate 3 decomposition strategy's architectural
sufficiency (0 production source modifications outside the
test addition). PR 11 close ships at the same commit as Gate 3
close per PR 11 framing §11.

**Regression contracts at PR 11 close (10 items):**

1. PR 11 suite (`test_pr11_recomposition_arc.py`): 3/3 passed.
2. PR 4 + PR 5 + PR 6 + PR 7 + PR 8 + PR 9 + PR 10 suites
   pass unchanged.
3. PR 3 discipline passes unchanged (no `_ALLOWLIST`
   modification per §8.1).
4. Four Layer 2 walkers (PR 4 + PR 8 + PR 9 + PR 10) pass
   unchanged.
5. Layer 3 lint (`test_pr6_visual_asymmetry.py`) passes
   unchanged.
6. Full corpus suite: **217 forge env collected** (214
   baseline + 3 PR 11 new).
7. Console tests + Public API anchor (`forge_bridge.__all__`
   at 19 symbols) unchanged.
8. Verbatim carrier travel: 17 carriers + Gate-3-LOCAL form +
   PR-11-LOCAL travel verbatim at PR 11 test module docstring
   + PR 11 commit message bodies.
9. Gate-3-LOCAL travel count contributes ≥1 PR 11 surface
   (≥4 total for Gate 3 close evaluation).
10. **Architectural sufficiency signal: 0 production source
    modifications outside the new test file.**

---

## 2. In-scope / out-of-scope

### In scope (PR 11)

- New test module: `tests/corpus/test_pr11_recomposition_arc.py`.
- 3 named tests (one per PR 9 fixture outcome class).
- IMPORT of PR 9 test infrastructure (`_apply_pr9_patches`,
  `_read_records`) as **test-internal archaeology surfaces**
  (not public APIs).
- Module docstring carrying Gate-3-LOCAL form + PR-11-LOCAL +
  traversal trace + inherited carrier citations.
- PR 11 commit message bodies carrying "preserved invariants"
  + "Gate-3-LOCAL corroboration" + "architectural sufficiency
  signal" sections per the PR 10 commit-body pattern.

### Out of scope (architecturally-prohibited at PR 11)

- **Any production source file modification.** §5.2 framing
  binding decision; §7 framing item 1. Justified deviations
  register as archaeology at PR 11 close, not silent additions.
- **Any new production abstraction whose primary purpose is
  "making recomposition cleaner."** §5.3 framing binding
  decision + §5.6 PR-11-LOCAL.
- **Any test helper that absorbs the full traversal arc into a
  single call.** Acceptable: small per-test helpers improving
  clarity at a single surface. Rejected: helpers wrapping
  fixture-drive + readback + comparator into one function.
- **Modification of the PR 9 three-fixture corpus.** PR 9
  close §2.1 + Gate 3 framing §7 item 4.
- **Addition of new fixtures.** PR 9 close §2.1; PR 10+
  fixtures require explicit Gate 4 comparator dependency
  justification.
- **Boundary/error-path comparator tests.** Comparator
  contract verification is PR 10 scope (`test_pr10_comparator.py`
  + `test_pr10_comparator_discipline.py`); PR 11 inherits the
  contract as precondition and does NOT re-test it.
- **Multi-fixture co-traversal helper.** PR 12 trigger
  territory per framing §5.5 + PR 10 framing §2.1.
- **Pair-not-found / orphan-record handling.** Orchestration
  policy outside PR 11's recomposition arc scope.
- **Layer 1 `_ALLOWLIST` modification.** §8.1 explicit;
  inherited corpus-subtree-auto-exclusion semantics from PR 10
  §4.4 amendment (corpus-internal modules NEVER in
  `_ALLOWLIST`; PR 11 test modules under `tests/corpus/`
  are not subject to allowlist check).
- **Layer 2 walker addition.** §8.2 explicit; no fifth walker.
- **Layer 3 lint modification.** §8.3 explicit; no new
  `emit_divergence_capture` call sites at PR 11.
- **`forge_bridge.__all__` modification.** Stays at 19 symbols
  per framing §5.7.
- **Speculative-reserved imports.** Per member 10 (PR 10 close
  §1.7); imports land when first used.
- **Cross-surface vocabulary in test names or docstrings.**
  Per framing §7 item 22 + Gate 3 framing §5.6 + PR 10 framing
  §3.5. No `task_outcome` / `prompt_resolution` field names.

---

## 3. Files modified / created at PR 11

| File | Disposition | Lines |
|---|---|---|
| `tests/corpus/test_pr11_recomposition_arc.py` | **NEW** | ~280–360 (final at PR 11 close) |
| `forge_bridge/**` | NOT MODIFIED (architectural sufficiency signal target) | 0 |
| `tests/corpus/test_pr3_discipline.py` | NOT MODIFIED (corpus-subtree auto-exclusion) | 0 |
| `tests/corpus/test_pr4_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr6_visual_asymmetry.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr7_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr8_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr9_fixture_integration.py` | NOT MODIFIED (imported FROM as test-internal archaeology surface) | 0 |
| `tests/corpus/test_pr9_fixture_discipline.py` | NOT MODIFIED | 0 |
| `tests/corpus/test_pr10_*.py` | NOT MODIFIED | 0 |
| `tests/corpus/fixtures/fix_*.py` | NOT MODIFIED (PR 9 fixtures stable archaeology) | 0 |
| `tests/corpus/conftest.py` | NOT MODIFIED | 0 |

**Single new file.** Zero modifications to any production
source or existing test file. The 0-prod-mod-outside-the-new-
test-file outcome IS the architectural sufficiency signal
PR 11 demonstrates.

---

## 4. Per-file derivation

### 4.1 `tests/corpus/test_pr11_recomposition_arc.py` — new test module

#### 4.1.1 Module-level docstring shape

The docstring carries (relevance-by-file ordering):

1. **One-line summary**: `"""End-to-end recomposition arc tests — fixture → drive_seed_fixture → chat_handler → emission → readback → compare_records → DivergenceReport."""`
2. **Blank line.**
3. **Gate-3-LOCAL governing sentence** (verbatim) with explicit
   *candidate carrier #16 corroboration substrate* marking.
4. **Blank line.**
5. **PR-11-LOCAL binding statement** (verbatim).
6. **Blank line.**
7. **Traversal trace** (verbatim from PR 11 framing §2):

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
8. **Blank line.**
9. **"Inherited carrier citations"** paragraph:

   > Carriers #1–#15 + #17 + the Gate 2 binding framing
   > clarification (call-site-owned arbitration inputs) +
   > the PR 10 proactive scope guardrail + the PR 10 §4.2
   > binding behavioral commitment ("compare as persisted")
   > + the PR-10-LOCAL read-only mutability invariant are
   > inherited unchanged. Canonical sources:
   > ``forge_bridge/corpus/_capture.py:6-135``,
   > ``forge_bridge/corpus/_seed.py:19-135``,
   > ``forge_bridge/corpus/_compare.py`` module docstring +
   > ``compare_records`` function docstring.
10. **Blank line.**
11. **"Test infrastructure import discipline"** paragraph
    (per §4.1.2 below):

    > PR 11 imports `_apply_pr9_patches` and `_read_records`
    > from `tests.corpus.test_pr9_fixture_integration` as
    > **test-internal archaeology surfaces**, NOT as public
    > APIs. The underscored-private status is preserved —
    > the import is test-internal and archaeology-explicit,
    > demonstrating that PR 9's fixture-driving infrastructure
    > is a stable consumption surface within the test
    > archaeology layer. This does NOT promote the helpers
    > to public API; future contributors must NOT read this
    > as a general invitation to import underscored-private
    > helpers across production modules.
12. **Blank line.**
13. **"Reference"** trailing paragraph citing:
    `A.5.3.2-PR11-SPEC.md`, `A.5.3.2-PR11-FRAMING.md`,
    `A.5.3.2-PR10-CLOSE.md`, `A.5.3.2-PR9-CLOSE.md`,
    `A.5.3.2-GATE-3-FRAMING.md`.

**Total docstring: ~70–90 lines.** Authored at Step 1
skeleton commit; preserved verbatim through subsequent steps.

#### 4.1.2 Imports discipline (per member 10: imports land when first used)

Imports inventory at PR 11 close (final state):

```python
from __future__ import annotations

import pathlib  # used by tmp_path type annotation
from typing import Any  # used by builder return type if needed
                        # (omit if not used by final tests)

import pytest

from forge_bridge.corpus._compare import compare_records

from tests.corpus.fixtures.fix_single_survivor import (
    FIXTURE as FIX_SINGLE_SURVIVOR,
)
from tests.corpus.fixtures.fix_multi_match import (
    FIXTURE as FIX_MULTI_MATCH,
)
from tests.corpus.fixtures.fix_no_keyword_match import (
    FIXTURE as FIX_NO_KW_MATCH,
)

from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)
```

**Imports discipline at Step 1 skeleton:** the skeleton commit
imports ONLY what the module docstring + module-level
constants (if any) USE. Per member 10:

- `__future__ annotations` lands at Step 1 (module-level
  posture).
- `pathlib`, `pytest`, `compare_records`, FIXTURE imports,
  PR 9 helper imports land at Step 2 (architectural-center,
  when first used by test bodies).
- `typing.Any` lands ONLY if a test body requires it (final
  evaluation at Step 2 implementation prep).

**No speculative-reserved imports.** No `import copy`, no
`import json`, no `ComparatorInputError`, no `DivergenceReport`
(the tests assert against dict keys, not the typed alias).

**Test-internal archaeology surfaces (cross-test-module imports
acceptance criterion):**

The two imports from `tests.corpus.test_pr9_fixture_integration`
are the ONLY underscored-private cross-test-module imports
at PR 11. They are admitted under the explicit
"test-internal archaeology surfaces" framing per §4.1.1 site
11 docstring. Future PR 11 spec amendments adding additional
underscored-private cross-test-module imports require explicit
framing-level review.

#### 4.1.3 Module-level constants

No module-level constants required at PR 11. The FIXTURE
dicts are imported per-fixture; the PR 9 helpers are imported
per-helper; tests use them directly at body scope.

(Contrast with PR 9 which exposed `_PR9_REACHABLE_TOOLS` at
module scope — PR 11 does NOT need its own controlled set
because it imports `_apply_pr9_patches` which constructs the
controlled set from PR 9's module-scope constant.)

#### 4.1.4 Test 1 — `test_recomposition_arc_single_survivor_no_divergence`

**Test name:** `test_recomposition_arc_single_survivor_no_divergence`

**Fixtures consumed:** `clean_rate_limit_state` (rate-limit
isolation per `conftest.py`), `monkeypatch` (pytest standard),
`tmp_path` (pytest standard).

**Test body (full):**

```python
def test_recomposition_arc_single_survivor_no_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — single-survivor fixture: no divergence.

    Drives ``fix-pr9-single-survivor`` through the full
    decomposition seam path. PR14 + PR21 collapse to single
    survivor; observation's ``narrower.decision`` matches
    expectation's ``expected_narrow`` verbatim. ``compare_records``
    reports ``narrow_diverged=False``. Carrier #17 verified at
    use: the DivergenceReport's per-surface partitioning preserves
    authorship through emission → persistence → readback → join →
    interpretive comparison.
    """
    # ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
    # Test-internal archaeology surface (NOT a public API).
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    # ── Steps 2-5 of traversal: drive fixture → emission ───────
    # drive_seed_fixture orchestrates expectation persistence,
    # chat_handler arbitration, observation emission. The seam
    # traversal is explicit at the call site — no helper absorbs
    # the arc (PR-11-LOCAL §0 + framing §5.3 + §5.6).
    from forge_bridge.corpus._seed import drive_seed_fixture

    drive_seed_fixture(**FIX_SINGLE_SURVIVOR)

    # ── Step 6 of traversal: read back persisted records ───────
    # Test-internal archaeology surface; reads every
    # capture-*.jsonl record across the corpus dir, skipping
    # headers.
    records = _read_records(corpus_dir)

    # ── Step 7 of traversal: partition by fixture_id + record_kind ──
    # Gate 2 close §2.1 foundational dependencies exercised:
    # fixture_id joinability (filter step) + record_kind
    # partitioning (separation step). The call-site awkwardness
    # (filter + partition explicit at each test) is acceptable
    # evidence the decomposition boundaries held (PR-11-LOCAL).
    matching = [
        r for r in records
        if r.get("fixture_id") == FIX_SINGLE_SURVIVOR["fixture_id"]
    ]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for "
        f"{FIX_SINGLE_SURVIVOR['fixture_id']!r}; got {len(matching)}.\n"
        f"All records: {records}"
    )

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    # ── Step 8 of traversal: invoke comparator ─────────────────
    # The interpretive-read seam. compare_records joins
    # observation + expectation by fixture_id (Gate 2 close
    # §2.1) and produces the DivergenceReport per carrier #17.
    report = compare_records(
        observation_record=observation,
        expectation_record=expectation,
    )

    # ── Step 9 of traversal: assertions on DivergenceReport ────
    # Four-key structural assertion contract — carrier #17 at
    # use: each authority surface's contribution structurally
    # identifiable.
    assert report["fixture_id"] == FIX_SINGLE_SURVIVOR["fixture_id"]
    assert report["expectation"]["expected_narrow"] == ["forge_ping"]
    assert report["observation"]["observed_narrow"] == ["forge_ping"]
    assert report["divergence"]["narrow_diverged"] is False
```

**Assertion contract — four DivergenceReport keys verified:**

1. `report["fixture_id"]` — join correctness (the join key is
   the persisted fixture_id; matches input fixture).
2. `report["expectation"]["expected_narrow"]` — expectation
   surface's authored contribution preserved through emission
   → persistence → readback → comparator.
3. `report["observation"]["observed_narrow"]` — observation
   surface's runtime contribution preserved through
   chat_handler arbitration → emission → persistence →
   readback → comparator.
4. `report["divergence"]["narrow_diverged"]` — comparator's
   interpretive claim about the pair.

**Carrier #17 verification at use:** assertions 2 + 3 are
satisfied at distinct dict paths (`report["expectation"]` vs.
`report["observation"]`), structurally enforcing the per-surface
partitioning at the report's outer geometry.

**§4.2 binding behavioral commitment verification at use:**
assertion 3 asserts `observed_narrow == ["forge_ping"]` (a
single-element list); the comparator's compare-as-persisted
discipline preserves the exact list verbatim from PR14's
emission output.

#### 4.1.5 Test 2 — `test_recomposition_arc_multi_match_no_divergence`

**Test name:** `test_recomposition_arc_multi_match_no_divergence`

**Test body (full):**

```python
def test_recomposition_arc_multi_match_no_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — multi-match fixture: no divergence.

    Drives ``fix-pr9-multi-match`` through the full
    decomposition seam path. PR14 yields 2 candidates; PR21
    cannot collapse (tie at max-overlap). Carrier #10
    enforcement: ``narrower.decision`` carries the filtered
    list verbatim (list equality preserves ordering;
    comparator's compare-as-persisted discipline preserves
    ordering through the join). Expectation matches observation
    verbatim per fixture-author intent; ``compare_records``
    reports ``narrow_diverged=False``.
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    from forge_bridge.corpus._seed import drive_seed_fixture

    drive_seed_fixture(**FIX_MULTI_MATCH)

    records = _read_records(corpus_dir)
    matching = [
        r for r in records
        if r.get("fixture_id") == FIX_MULTI_MATCH["fixture_id"]
    ]
    assert len(matching) == 2

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    report = compare_records(
        observation_record=observation,
        expectation_record=expectation,
    )

    # Multi-match: 2-element list with carrier #10 verbatim
    # ordering preserved.
    assert report["fixture_id"] == FIX_MULTI_MATCH["fixture_id"]
    assert report["expectation"]["expected_narrow"] == [
        "forge_list_projects",
        "flame_list_libraries",
    ]
    assert report["observation"]["observed_narrow"] == [
        "forge_list_projects",
        "flame_list_libraries",
    ]
    assert report["divergence"]["narrow_diverged"] is False
```

**Carrier #10 verification at use:** the 2-element list ordering
(`forge_list_projects` before `flame_list_libraries`) is
preserved through the entire arc; the comparator's list-equality
(NOT set-equality, NOT sorted-equality) preserves the carrier-#10
"filtered list verbatim" semantics.

#### 4.1.6 Test 3 — `test_recomposition_arc_no_keyword_match_divergence`

**Test name:** `test_recomposition_arc_no_keyword_match_divergence`

**Test body (full):**

```python
def test_recomposition_arc_no_keyword_match_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — no-keyword-match fixture: authored/observed divergence.

    Drives ``fix-pr9-no-keyword-match`` through the full
    decomposition seam path. PR14 keyword filter matches zero
    tools; PR14 fallback returns the full reachable set
    verbatim ("no capability loss" per
    ``_tool_filter.py:320-321``). The fixture's
    ``expected_narrow=[]`` is the fixture-author's aspirational
    claim; the observation's ``narrower.decision`` carries the
    full 4-tool reachable set. The divergence is intentional
    + operationally valuable — it is the Gate 4 comparator-
    unblock proof case PR 9 close §2.4 named. ``compare_records``
    reports ``narrow_diverged=True``; the authored/observed
    divergence surfaces as a structured DivergenceReport claim
    per carrier #17.
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    from forge_bridge.corpus._seed import drive_seed_fixture

    drive_seed_fixture(**FIX_NO_KW_MATCH)

    records = _read_records(corpus_dir)
    matching = [
        r for r in records
        if r.get("fixture_id") == FIX_NO_KW_MATCH["fixture_id"]
    ]
    assert len(matching) == 2

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    report = compare_records(
        observation_record=observation,
        expectation_record=expectation,
    )

    # No-keyword-match: authored ``[]`` vs. observed full
    # 4-tool reachable set. The authored/observed divergence
    # surfaces structurally.
    assert report["fixture_id"] == FIX_NO_KW_MATCH["fixture_id"]
    assert report["expectation"]["expected_narrow"] == []
    assert len(report["observation"]["observed_narrow"]) == 4, (
        f"Expected full 4-tool reachable set in PR14 fallback; "
        f"got {report['observation']['observed_narrow']!r}"
    )
    # The full reachable set per _PR9_REACHABLE_TOOLS at PR 9
    # test_pr9_fixture_integration.py:208-213.
    assert set(report["observation"]["observed_narrow"]) == {
        "forge_ping",
        "forge_list_projects",
        "flame_list_libraries",
        "flame_render_status",
    }
    assert report["divergence"]["narrow_diverged"] is True
```

**Carrier #17 + authored/observed divergence verification at
use:** the DivergenceReport's `expectation` field preserves
the authored `[]` (the fixture-author's claim); the
`observation` field preserves the runtime full-reachable-set
(the arbitration's actual outcome); the `divergence` field
names the comparator's interpretive claim
(`narrow_diverged=True`). The three are structurally distinct
+ identifiable at the report level — recomposition preserves
authorship.

**Note on the set-equality assertion — property isolation
across tests:** the three PR 11 tests intentionally split
distinct properties across distinct assertion surfaces.
Ordering-preservation semantics are exercised at test 2
(multi-match) via list equality per the §4.2 binding
behavioral commitment verification at use; test 3 isolates
**fallback-membership semantics** — did PR14's "no capability
loss" fallback preserve the entire reachable set? —
independent of ordering, which is incidental at the fallback
path (dict iteration order through `_tool_filter.py`). The
`set(...)` assertion sharpens the test's load-bearing claim
by removing ordering noise. **The comparator itself still uses
list-equality** (PR 10 §4.2 preserved at the function-body
layer); the `set(...)` operation lives ONLY at the test's
assertion surface, never at the comparator's input handling
or output construction. The architectural discipline remains
intact at the production layer; only the test's verification
shape adapts to the property it isolates.

#### 4.1.7 Assertion-contract summary (cross-test invariants)

Every PR 11 test asserts on the same four DivergenceReport
top-level keys:

| Key | Assertion type | Authority surface |
|---|---|---|
| `report["fixture_id"]` | Direct equality with fixture's `fixture_id` | Join key |
| `report["expectation"]["expected_narrow"]` | Direct list equality with expected value | Authored expectation surface |
| `report["observation"]["observed_narrow"]` | Direct list equality OR set membership | Runtime observation surface |
| `report["divergence"]["narrow_diverged"]` | Direct bool equality (`True` or `False`) | Comparator's interpretive claim |

The four-key structural assertion contract per test enforces
carrier #17 (per-surface partitioning identifiable) operationally
at every recomposition arc.

**Order of assertions in each test:**

1. `fixture_id` (join correctness).
2. `expectation["expected_narrow"]` (authored surface).
3. `observation["observed_narrow"]` (runtime surface).
4. `divergence["narrow_diverged"]` (interpretive claim).

The ordering mirrors the traversal trace: input → authored →
runtime → comparator-derived. Future readers can verify the
recomposition arc by inspection of the assertion order.

---

## 5. Test count anchors

### 5.1 Forge env test count projection

```
214 baseline (PR 10 close §1.4 forge env collected)
+   3 PR 11 recomposition arc tests
= 217 forge env collected at PR 11 close
```

Per `feedback_counts_are_archaeology_grade`: 217 is the locked
target at PR 11 close. If the actual count at Step 3 (final
verification) differs from 217, spec author must:

- Investigate the divergence (test collection issue?
  parametrize expansion? skip condition?).
- Amend §5.1 with archaeology before close.
- Document the divergence at PR 11 close §6 (mechanical
  checkpoints).

**Named-vs-collected discipline:** PR 11 ships 3 named tests;
no `parametrize` decorators; named == collected. The
named-equals-collected identity is structurally locked at
PR 11 by per-fixture-hand-written test pattern (one test
function per fixture; no shared parametrization).

### 5.2 Forge-bridge env test count projection

```
208 baseline (PR 10 close §1.4 forge-bridge env target;
              6-test gap inherited per
              project_v1_4_x_harness_debt)
+   3 PR 11 recomposition arc tests
= 211 forge-bridge env collected at PR 11 close (projected)
```

Forge-bridge env count NOT re-verified at PR 11 close beyond
inheritance documentation. The 6-test gap is PR 7-scope, not
PR 11-scope. **Do not conflate the two env counts** per PR 8
close §5.6 + PR 10 close §1.4.

### 5.3 Test inventory at PR 11 close (locked)

| # | Test | File | Step |
|---|---|---|---|
| 1 | `test_recomposition_arc_single_survivor_no_divergence` | `test_pr11_recomposition_arc.py` | 2 |
| 2 | `test_recomposition_arc_multi_match_no_divergence` | `test_pr11_recomposition_arc.py` | 2 |
| 3 | `test_recomposition_arc_no_keyword_match_divergence` | `test_pr11_recomposition_arc.py` | 2 |

All three tests land at Step 2 (the architectural-center).

---

## 6. Atomic step decomposition

PR 11 ships as a **3-step + close** atomic sequence:

- Step 1: skeleton (module docstring + minimum imports).
- Step 2: architectural-center (all 3 tests).
- Step 3: final verification (empty commit; archaeology in
  body).
- Close: PR 11 close artifact + Gate 3 close artifact (TWO
  artifacts at ONE commit per Gate 3 framing §11).

### 6.1 Step 1 — `test_pr11_recomposition_arc.py` skeleton

**Atomic commit content:**

- New file: `tests/corpus/test_pr11_recomposition_arc.py`.
- Module docstring (per §4.1.1 — Gate-3-LOCAL form +
  PR-11-LOCAL + traversal trace + inherited carrier citations
  + test-internal archaeology surfaces framing + spec/framing
  references).
- Imports: `from __future__ import annotations` ONLY (member 10
  discipline; no other imports until used by tests at Step 2).
- No test bodies, no module-level constants, no helper
  functions.

**Step 1 verification:**

- `pytest tests/corpus/test_pr11_recomposition_arc.py
  --collect-only -q` → 0 tests collected (skeleton only).
- `python -c "import tests.corpus.test_pr11_recomposition_arc"`
  → imports cleanly (`__future__ annotations` is the only
  active import).
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr4_*.py tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr9_*.py tests/corpus/test_pr10_*.py` →
  passes unchanged (PR 11 skeleton is target-disjoint from
  all four Layer 2 walkers' input sets).
- `pytest tests/corpus/ --collect-only -q | tail -1` → 214
  collected (PR 10 baseline preserved).

**Step 1 commit body sections (mirroring PR 10 Step 1 pattern):**

- Architectural success signal: zero production source
  modifications; one new test file added.
- Preserved invariants: Gate-3-LOCAL form + PR-11-LOCAL +
  17 inherited carriers cited by reference + Gate 2 binding
  framing clarification cited by reference.
- Gate-3-LOCAL corroboration: surfaces 1 (module docstring)
  + 2 (this commit body) = 2 PR 11 surfaces; ≥1 of ≥1
  framing-§9-condition-9 surface count satisfied at Step 1.
- What does NOT land at Step 1: test bodies (Step 2), imports
  beyond `__future__ annotations` (Step 2 + member 10
  discipline).

### 6.2 Step 2 — three recomposition arc tests (architectural-center)

**Atomic commit content:**

- Imports landed (per §4.1.2 final-state inventory):
  - `pathlib`, `pytest`, `compare_records`, three FIXTURE
    imports, two PR 9 helper imports.
  - `typing.Any` ONLY if a test body actually uses it (final
    evaluation at this step).
  - `drive_seed_fixture` imported at function scope inside
    each test body (mirrors PR 9 pattern at
    `test_pr9_fixture_integration.py` for symmetry with the
    function-scoped import discipline carrier #15 enforces
    at the production seed module). Alternatively, top-level
    import is acceptable if member-10-imports-land-when-used
    discipline is maintained (all three tests use it). Spec
    finalization: **top-level import** (simpler; all three
    tests use; member 10 discipline preserved — landed when
    first used at Step 2).
- Three test functions (full bodies per §4.1.4 + §4.1.5 +
  §4.1.6).
- No new module-level constants, no helper functions, no
  parametrize decorators.

**Three-round review applies** per Gate 2 framing §5.7
integration-work elevation. PR 11's architectural-center is
the recomposition arc operational landing; carrier #17 at use
is the load-bearing verification.

**Step 2 verification:**

- `pytest tests/corpus/test_pr11_recomposition_arc.py` → 3/3
  passed.
- `pytest tests/corpus/test_pr10_*.py
  tests/corpus/test_pr9_*.py tests/corpus/test_pr8_seed_surface.py
  tests/corpus/test_pr7_*.py
  tests/corpus/test_pr4_participation_creep.py` → passes
  unchanged.
- `pytest tests/corpus/test_pr3_discipline.py
  tests/corpus/test_pr6_visual_asymmetry.py` → passes
  unchanged.
- `pytest tests/corpus/ --collect-only -q | tail -1` → **217
  collected** forge env (214 baseline + 3 PR 11 new). EXACT
  MATCH with §5.1 projection.
- Architectural sufficiency signal: `git diff --stat
  97c3fb4..HEAD -- forge_bridge/` returns EMPTY (zero
  production source modifications).

**Step 2 commit body sections:**

- Bundled-commit rationale: tests need access to FIXTURE
  imports + PR 9 helpers + compare_records together; bundled
  per spec §6.2 + Gate 2 framing §5.7.
- Architectural-center: carrier #17 at use; three tests
  exercise the full recomposition arc; each test asserts on
  the four-key DivergenceReport structural contract.
- Test infrastructure import discipline: explicit "test-
  internal archaeology surfaces, not public APIs" framing
  per §4.1.1 site 11 docstring.
- Recomposition-through-existing-seams operational evidence:
  no test absorbs the arc; each test traverses the seam path
  explicitly at the body level.
- Preserved invariants: Gate-3-LOCAL form + PR-11-LOCAL +
  17 inherited carriers + 4 PR 10-inherited PR-LOCAL bindings.
- Gate-3-LOCAL corroboration progress: surfaces 1 + 2 (Step 1)
  + 3 (this commit body) + (optionally) test body docstrings
  IF they cite Gate-3-LOCAL form by reference (counting
  decision at implementation prep).
- §4.2 binding behavioral commitment verification at use:
  test 2 asserts list equality (NOT set equality, NOT
  sort-and-compare) — ordering preserved through the arc.
- Carrier #10 verification at use: test 2's 2-element list
  ordering preserved verbatim per carrier #10 "filtered list
  verbatim" requirement.
- Carrier #17 verification at use: tests 1 + 2 + 3 each
  assert on the per-surface partitioning structurally at the
  report dict shape.
- Architectural sufficiency signal: zero production source
  modifications (verified at Step 2 close).

### 6.3 Step 3 — final verification (empty commit; archaeology in body)

**Atomic commit content:**

- No file changes (empty commit).
- Commit message body carries:
  - 10-item Step 3 verification checklist (per §1 regression
    contracts).
  - 17 inherited carriers cited by reference.
  - PR-11-LOCAL binding statement verbatim.
  - Gate-3-LOCAL form verbatim with *candidate carrier #16
    corroboration substrate* marking.
  - Full PR 11 surfaces inventory (Gate-3-LOCAL travel count
    + carrier #17 verification at use sites + architectural
    sufficiency signal verification).
  - Spec amendments at incarnation (if any surfaced during
    Steps 1–2).
  - Cleanup-pressure-resistance archaeology (if any pressure
    forms surfaced + were rejected at Steps 1–2).
  - §5.3 candidate methodology observation outcome (absence
    vs. rejection per framing §6.4 + §3.9 asymmetric
    weighting).
  - PR 11 commit chain summary.
  - Next: PR 11 close + Gate 3 close (two artifacts at one
    commit per framing §11).

**Step 3 verification checklist (10 items):**

1. **PR 11 suite:** `pytest tests/corpus/test_pr11_recomposition_arc.py`
   → 3/3 passed.
2. **Existing suites regression:** `pytest tests/corpus/
   --collect-only -q | tail -1` → 217 collected forge env;
   all suites pass unchanged.
3. **PR 4 + PR 5 chat-handler + no-dependency integration
   tests:** pass unchanged (no chat_handler arbitration
   surface modifications at PR 11).
4. **PR 6 Layer 3 lint regression:** 17/17 passed unchanged;
   zero new `emit_divergence_capture` call sites at PR 11.
5. **Four Layer 2 walkers regression:** all four (PR 4 + PR 8
   + PR 9 + PR 10) pass unchanged; parallel-not-extension
   boundary preserved.
6. **PR 3 discipline:** 1/1 passed unchanged; corpus-subtree
   auto-exclusion handles `tests/corpus/test_pr11_*.py`
   placement.
7. **Console tests:** 50/50 passed unchanged.
8. **Public API regression:** `forge_bridge.__all__` at 19
   symbols.
9. **Verbatim travel verification:**
   - Carrier #17 + Gate-3-LOCAL form + PR-11-LOCAL at PR 11
     test module docstring (Step 1 verified).
   - Gate-3-LOCAL travel count ≥1 PR 11 surface (≥1 of ≥1
     framing-§9-condition-9 requirement satisfied).
   - 17 inherited carriers cited by reference at PR 11 test
     module docstring per §4.1.1.
10. **Architectural sufficiency signal verification:** `git
    diff --stat 97c3fb4..HEAD -- forge_bridge/` returns EMPTY
    (zero production source modifications outside the new
    test file). §1 regression contract #10 + §5.2 framing
    binding decision.

**Step 3 commit type:** empty verification commit, no code
changes. Mirrors PR 9 Step 5 (`159ccd2`) and PR 10 Step 5
(`d04753c`) pattern.

### 6.4 Close commit — PR 11 close + Gate 3 close artifacts (TWO artifacts at ONE commit)

Per Gate 3 framing §11 + PR 11 framing §11 + Gate 2 close
2026-05-11 precedent (`a6e42f0` = "PR 9 close + Gate 2 close —
two artifacts at one commit").

**Atomic commit content:**

- New file: `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR11-CLOSE.md`
- New file: `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-GATE-3-CLOSE.md`

Both artifacts share the same commit per the same-commit
convergence discipline. Responsibility split per PR 11 framing
§11:

**PR 11 close owns:**

- PR 11 implementation arc archaeology (commits chain table).
- §5.3 candidate methodology observation evaluation at PR 11
  scope (absence vs. rejection outcome).
- §5.6 PR-11-LOCAL traverses-not-erases-seams discipline
  archaeology.
- Recomposition-through-existing-seams operational
  archaeology.
- Architectural sufficiency signal (0-prod-mod) validation
  evidence at PR 11 scope.
- PR 11-scoped cleanup-pressure-form encounters + protection
  registrations.

**Gate 3 close owns:**

- Gate-arc synthesis across PR 10 + PR 11.
- Cleanup-pressure-resistance class final inventory at Gate 3
  scope (10 members + any PR 11 additions).
- Candidate carrier #16 promotion evaluation against ≥4-
  surface evidence base (PR 10's 8 surfaces + PR 11's ≥1
  surface).
- Conditional PR 12 disposition (promote / defer / reject)
  per framing §5.5 qualitative trigger criterion.
- Recomposition-through-existing-seams promotion candidacy.
- 0-prod-mod-as-architectural-sufficiency promotion candidacy.
- §5.3 candidate methodology observation gate-level promotion
  evaluation.
- Gate-level inheritance contract toward Gate 4.
- Four-variant amendment-at-incarnation taxonomy final
  cross-PR inventory.

**Close artifacts not bundled into Steps 1–3:** the close
artifacts ship as a distinct subsequent commit after Step 3.
No code changes in the close commit beyond the two new
artifacts.

### 6.5 Step N.5 surgical cadence — available if needed

If implementation prep or three-round review at Steps 1–2
surfaces mid-flight guidance that adds value to a recently-
shipped deliverable, the Step N.5 surgical cadence is
available (3-times corroborated at Gate 2 close + PR 10 added
zero). PR 11 framing §3.8 explicit: pattern available without
re-framing.

**If Step N.5 fires at PR 11:** the surgical commit lands as
a small additive amendment before the next major deliverable
(Step 2 architectural-center commit OR Step 3 verification
commit), preserving the "distinct atomic boundary" discipline.

---

## 7. Phase-end conditions for PR 11

PR 11 closes when (mirroring framing §9):

1. **The recomposition arc operates end-to-end.** All three
   PR 9 fixtures drive through the full seam traversal and
   return the expected DivergenceReport shape per
   `compare_records`.

2. **The full seam traversal is visible at the test surface.**
   No PR 11 test absorbs the traversal; each test explicitly
   visits each seam at the body level.

3. **0 production source modifications.** §5.2 framing binding
   decision; §1 regression contract #10; §6.2 Step 2
   verification.

4. **No production abstraction whose primary purpose is
   "making recomposition cleaner."** §5.3 framing binding
   decision + §5.6 PR-11-LOCAL.

5. **Layer 1 allowlist** verified unchanged (§8.1).

6. **Four Layer 2 walkers** pass unchanged (§8.2).

7. **Layer 3 lint** passes unchanged (§8.3).

8. **Carrier #17 holds operationally** through the
   recomposition arc — every PR 11 test's DivergenceReport
   assertions verify per-surface partitioning structurally.

9. **Gate-3-LOCAL governing sentence travels verbatim** through
   ≥1 PR 11 surface (PR 11 test module docstring +
   conceptually all PR 11 commit message bodies). ≥1 of ≥1
   framing-§9-condition-9 requirement satisfied. PR 10's 8
   surfaces + PR 11's ≥1 surface = ≥9 total Gate-3-LOCAL
   travel surfaces, significantly exceeding the ≥4 threshold
   Gate 3 close reads.

10. **Carriers + binding statements travel verbatim** into
    PR 11 test module docstring per relevance-by-file ordering:
    - Gate-3-LOCAL form + PR-11-LOCAL at TOP.
    - 17 inherited carriers cited by reference to canonical
      sources.

11. **PR-11-LOCAL binding statement** (§0 + framing §5.6)
    lives in PR 11 test module docstring + PR 11 commit
    message bodies. Does NOT regenerate beyond PR 11.

12. **Test count locks at PR 11 close target** (217 forge env
    collected; verified at §6.3 Step 3 + §6.4 close).

13. **PR 11 close artifact AND Gate 3 close artifact BOTH ship
    at PR 11 final commit** per §6.4 + framing §11.

14. **`forge_bridge.__all__`** stays at 19 symbols.

15. **Three-authority-surface partition + PR-8-INTERNAL three-
    way authority partition + 10-member cleanup-pressure-
    resistance class + PR 10 read-side structural parallel**
    all preserve unchanged.

16. **Four-walker Layer 2 partition** preserves unchanged
    (parallel-not-extension boundary; shared AST mechanics
    do not imply shared ontology).

17. **Any new cleanup-pressure-resistance class members
    surfaced during PR 11** register at PR 11 close with
    explicit protection language + operational enforcement
    placement (per framing §6.2).

18. **§5.3 candidate methodology observation evaluation
    registered** at PR 11 close per framing §6.4 asymmetric
    weighting (absence STRENGTHENS candidacy; rejection
    PRESERVES first-instance candidacy without invalidating).

19. **PR 12 disposition evaluated at Gate 3 close** (NOT at
    PR 11 close standalone) per framing §5.5 qualitative
    trigger criterion (promote / defer / reject).

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` no modification

`tests/corpus/test_pr11_recomposition_arc.py` ships under
`tests/corpus/`, which is NOT inside the corpus subtree
(`forge_bridge/corpus/`). The PR 3 discipline's `_ALLOWLIST`
check applies to files in the broader codebase that import
`from forge_bridge.corpus`; `tests/corpus/` files are NOT
subject to the discipline check in the same way (per
existing PR 4–PR 10 test module precedent + PR 10 §4.4
amendment archaeology).

**Verification step at Step 1 implementation prep:** confirm
PR 3 discipline implementation (`test_pr3_discipline.py:92-96`
corpus-subtree auto-exclusion) handles `tests/corpus/` files
blanket-style (per
[[feedback_ground_specs_in_actual_files]]). Expected: no
allowlist modification needed; PR 11 Step 1 verification item
1 confirms.

### 8.2 Layer 2 — four-walker partition no modification

PR 11 adds no fifth walker. The four existing walkers (PR 4 +
PR 8 + PR 9 + PR 10) continue to enforce their respective
ontologies; PR 11 test additions are target-disjoint for all
four:

- PR 4 walker target: narrowing-subsystem production sources
  (`forge_bridge/console/_tool_filter.py` +
  `_tool_filter_helpers.py` etc.). PR 11 modifies none.
- PR 8 walker target: `forge_bridge/corpus/_seed.py`. PR 11
  modifies none.
- PR 9 walker target: `tests/corpus/fixtures/*.py`. PR 11
  adds no fixtures.
- PR 10 walker target: `forge_bridge/corpus/_compare.py`.
  PR 11 modifies none.

Step 3 verification item 5 confirms all four walkers pass
unchanged against the post-PR-11 codebase.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 11.
Properties A–D govern `emit_divergence_capture` call sites;
PR 11 introduces no new call sites (the chat_handler-driven
emission inside `drive_seed_fixture` consumes the existing
call site at `handlers.py:1185`, which is PR 4–authored and
PR 6-protected). The lint's discovery walk input set unchanged.

Step 3 verification item 4 confirms 17/17 PR 6 lint tests
pass unchanged.

---

## 9. Resume protocol (for future archaeology)

**If implementation pauses mid-PR-11 and resumes in a new
session, the resume protocol is:**

1. **Read this spec** (§4 per-file derivation + §6 atomic
   step decomposition + §7 phase-end conditions).
2. **Read PR 11 framing** (`97c3fb4`) §2 + §3 + §5 (load-
   bearing binding decisions per framing-close direction).
3. **Read PR 10 close** (`cf2b7ee`) §1 + §2 (architectural
   signals + PR 11 inheritance contract).
4. **Confirm state:** `git log --oneline -10` reflects the
   PR 11 commits to-date.
5. **Identify resume point:** which Step has landed; which
   Step is next.
6. **Apply member 10 + grounding discipline** before
   re-entering implementation.

**For new sessions resuming at Step 2 (post-skeleton):**

- Read Step 1 commit body's archaeology section.
- Verify Step 1 skeleton matches §4.1.1 + §4.1.2 + §4.1.3
  contract.
- If skeleton drift detected, register Step N.5 surgical
  amendment before Step 2 architectural-center commit lands.

**For new sessions resuming at Step 3 (post-architectural-
center):**

- Read Step 2 commit body's archaeology section.
- Run Step 2 verification checklist (§6.2 verification items).
- If verification surfaces drift (test count divergence,
  carrier travel gap), register Step N.5 surgical amendment
  before Step 3 final-verification commit lands.

**For new sessions resuming at Close (post-Step-3):**

- Read Step 3 commit body's full archaeology.
- Draft PR 11 close artifact (mirror PR 10 close §1-§8
  structure) + Gate 3 close artifact at the same commit per
  §6.4.

---

## 10. Cross-references

- `A.5.3.2-PR11-FRAMING.md` (`97c3fb4`) — **immediate
  predecessor; binding pre-spec contract.** §0 governing
  pair; §2 objective + traversal trace; §3 architectural
  inheritance; §4 architectural delta; §5 binding decisions;
  §6 cleanup-pressure-resistance discipline; §7 23 non-
  acquisition commitments; §9 19 phase-end conditions; §11
  same-commit convergence responsibility split.
- `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) — durable PR 10
  archival state PR 11 inherits; §1 PR 10 established
  (comparator surface + 4 architectural signals + member 10
  promotion); §2 PR 11 inheritance contract.
- `A.5.3.2-PR10-SPEC.md` (`54d0ab9` + amendment `6830888`) —
  `compare_records` interface PR 11 consumes; §4.1.6
  reference implementation; §4.2 binding behavioral commitment
  ("compare as persisted"); §4.4 amendment archaeology
  (sharpened Layer 1 semantics — corpus-subtree auto-exclusion
  inherited at PR 11 §8.1).
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — gate-level
  inheritance contract; §6.1 promotion-evaluation criteria
  for candidate carrier #16 (PR 11 contributes the ≥1 final
  surface; ≥9 cumulative for the ≥4 threshold significantly
  exceeded); §10 PR sequencing (PR 11 is second; PR 12
  conditional pending Gate 3 close evaluation); §11 Gate 3
  close criteria (close ships at PR 11 final commit).
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus
  PR 11 drives + PR 9 integration test infrastructure PR 11
  imports as test-internal archaeology surfaces; §1.1 fixture
  corpus + grounding traces; §2.1 fixtures are stable
  archaeology; §2.2 PR 9 integration test infrastructure
  consumption surface; §2.4 authored/observed divergence
  proof case (PR 11 test 3 verifies as structured
  DivergenceReport claim).
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis
  precedent for PR 11 close + Gate 3 close same-commit
  convergence; §2.1 Gate 4 comparator's two foundational
  dependencies (record_kind partition + fixture_id joinability)
  PR 11 exercises operationally end-to-end at every test.
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface PR 11 traverses transitively via `drive_seed_fixture`;
  `emit_seed_expectation` inherited unchanged.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces PR 11 traverses transitively
  via `chat_handler` under `seed_dispatch_scope`;
  `emit_divergence_capture` + `_dispatch_context` +
  `seed_dispatch_scope` inherited unchanged.
- `forge_bridge/corpus/_compare.py::compare_records` — PR 10
  interpretive-read surface PR 11 consumes at every test's
  final step.
- `forge_bridge/corpus/_compare.py::DivergenceReport` — typed
  alias (`dict[str, Any]`) PR 11 tests assert against
  field-by-field (NOT by typed alias import per member 10).
- `forge_bridge/corpus/_seed.py::drive_seed_fixture` — PR 8
  orchestration entry point PR 11 invokes per fixture.
- `forge_bridge/console/handlers.py::chat_handler` —
  production arbitration surface PR 11 drives via the PR 9
  patched `_invoke_chat_handler_in_process` (preserves REAL
  chat_handler arbitration; patches reachable-tool set).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture`
  — observation helper invoked transitively through
  chat_handler at `handlers.py:1185`.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` —
  expectation helper invoked transitively through
  `drive_seed_fixture` at `_seed.py:505-509`.
- `forge_bridge/corpus/reader.py::read_capture_file` —
  readback surface consumed indirectly via `_read_records`
  test helper imported from PR 9.
- `tests/corpus/fixtures/fix_single_survivor.py::FIXTURE` —
  PR 11 test 1 imports as `FIX_SINGLE_SURVIVOR`.
- `tests/corpus/fixtures/fix_multi_match.py::FIXTURE` —
  PR 11 test 2 imports as `FIX_MULTI_MATCH`.
- `tests/corpus/fixtures/fix_no_keyword_match.py::FIXTURE` —
  PR 11 test 3 imports as `FIX_NO_KW_MATCH`.
- `tests/corpus/test_pr9_fixture_integration.py::_apply_pr9_patches`
  — PR 11 imports as test-internal archaeology surface (NOT
  public API).
- `tests/corpus/test_pr9_fixture_integration.py::_read_records`
  — PR 11 imports as test-internal archaeology surface (NOT
  public API).
- `tests/corpus/test_pr9_fixture_integration.py::_PR9_REACHABLE_TOOLS`
  — controlled reachable-tool set; consumed transitively via
  `_apply_pr9_patches` (NOT imported directly at PR 11).
- `tests/corpus/conftest.py::clean_rate_limit_state` — PR 11
  tests consume per PR 9 + PR 10 fixture pattern.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer 1;
  NOT MODIFIED at PR 11 per §8.1.
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
- `tests/corpus/test_pr11_recomposition_arc.py` (planned,
  PR 11) — single new test module.
- `A.5.3.2-PR11-CLOSE.md` (planned at PR 11 final commit) —
  PR 11 close artifact; same-commit convergence with Gate 3
  close.
- `A.5.3.2-GATE-3-CLOSE.md` (planned at PR 11 final commit) —
  Gate 3 close artifact; gate-arc synthesis; candidate
  carrier #16 promotion evaluation; conditional PR 12
  disposition; gate-level inheritance contract toward Gate 4.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; PR 11 will contribute (at PR 11
  close evaluation):
  - Recomposition-through-existing-seams operational
    archaeology (first instance; candidacy strengthens at
    Gate 3 close evaluation).
  - 0-prod-mod-as-architectural-sufficiency-signal first
    full-arc validation (PR 9 + PR 10 + PR 11 three-PR
    evidence escalation).
  - PR 10 §5.3 candidate methodology observation second-
    instance evaluation per framing §6.4 asymmetric weighting
    (absence strengthens; rejection preserves first-instance).

---

PR 11 spec locks here. PR 11 Step 1 (skeleton) drafts at the
next implementation step per the cadence (spec → Step 1 →
Step 2 → Step 3 → close). The Step 1 commit lands the test
module skeleton with the module docstring carrying Gate-3-
LOCAL + PR-11-LOCAL + traversal trace; Step 2 lands the three
recomposition arc tests (the architectural-center); Step 3
empty-commits the final verification archaeology; the close
commit ships PR 11 close artifact + Gate 3 close artifact as
two distinct artifacts at one commit per the same-commit
convergence discipline.

PR 11 is **the recomposition arc operational landing**. PR 9
established substrate readiness; PR 10 established the
interpretive-read surface; PR 11 demonstrates the
recomposition-through-existing-seams discipline at end-to-end
scale, the architectural-sufficiency-signal continuity from
PR 9 + PR 10 (0-prod-mod outside the new test file), and the
final Gate-3-LOCAL surface count (≥9 cumulative for the ≥4
threshold). Gate 3 close (same commit) closes the Gate 3 arc;
Gate 4 inherits the validated comparator + the corroborated
recomposition demonstration.
