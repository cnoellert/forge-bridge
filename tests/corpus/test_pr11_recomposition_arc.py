"""End-to-end recomposition arc tests — fixture → drive_seed_fixture → chat_handler → emission → readback → compare_records → DivergenceReport.

Gate-3-LOCAL governing sentence (candidate carrier #16
corroboration substrate per A.5.3.2-GATE-3-FRAMING.md §6.1):

  Gate 3 proves topology, not infrastructure.

The Gate-3-LOCAL form travels at PR 11 surfaces with explicit
*candidate carrier #16 corroboration substrate* marking.
Promotion to carrier #16 is evaluated at Gate 3 close (ships at
PR 11 final commit per Gate 3 framing §11), NOT at PR 11
implementation. PR 11 must NOT write "17 active carriers" or
"carriers #1–#17"; correct phrasing is "16 active carriers +
candidate #16."

PR-11-LOCAL binding statement (A.5.3.2-PR11-FRAMING.md §5.6,
scope-local per PR-N-LOCAL non-regeneration rule):

  PR 11 traverses the decomposition seams established by Gate 2
  + Gate 3 substrate work without erasing them. Call-site
  awkwardness during recomposition is acceptable evidence that
  the decomposition boundaries held; introducing production
  abstractions whose primary purpose is "making recomposition
  cleaner" is rejected at the spec layer.

Traversal trace (A.5.3.2-PR11-FRAMING.md §2 verbatim):

  fixture (tests/corpus/fixtures/fix_*.py)
    → drive_seed_fixture          [orchestration seam]
      → emit_seed_expectation     [expectation persistence seam]
      → chat_handler arbitration  [observation production seam]
        → emit_divergence_capture [observation persistence seam]
          → JSONL persistence     [persistence-topology seam]
            → reader              [readback seam]
              → compare_records   [interpretive-read seam]
                → DivergenceReport assertions

Each arrow is a decomposition seam established at Gate 2 or
Gate 3 substrate work. PR 11 tests traverse each seam explicitly
at the test body level; no helper absorbs the arc into a single
call (PR-11-LOCAL §5.6 + framing §5.3).

Inherited carrier citations (PR 4 + PR 5 + PR 6 + PR 8 + Gate 2
+ Gate 3 lineage). Carriers #1–#15 + #17 + the Gate 2 binding
framing clarification (call-site-owned arbitration inputs) + the
PR 10 proactive scope guardrail + the PR 10 §4.2 binding
behavioral commitment ("compare as persisted") + the PR-10-LOCAL
read-only mutability invariant are inherited unchanged.
Canonical sources:

  - forge_bridge/corpus/_capture.py:6-135 (carriers #1-#14 +
    Gate 2 binding framing clarification).
  - forge_bridge/corpus/_seed.py:19-135 (carrier #15 +
    PR-8-LOCAL bindings).
  - forge_bridge/corpus/_compare.py module docstring +
    compare_records function docstring (carrier #17 +
    proactive scope guardrail + §4.2 binding behavioral
    commitment + PR-10-LOCAL).

Test infrastructure import discipline (A.5.3.2-PR11-SPEC.md
§4.1.1 site 11 + §4.1.2):

  PR 11 imports `_apply_pr9_patches` and `_read_records` from
  `tests.corpus.test_pr9_fixture_integration` as
  **test-internal archaeology surfaces**, NOT as public APIs.
  The underscored-private status is preserved — the import is
  test-internal and archaeology-explicit, demonstrating that
  PR 9's fixture-driving infrastructure is a stable consumption
  surface within the test archaeology layer. This does NOT
  promote the helpers to public API; future contributors must
  NOT read this as a general invitation to import underscored-
  private helpers across production modules.

References:

  - A.5.3.2-PR11-SPEC.md (this module's implementation
    contract).
  - A.5.3.2-PR11-FRAMING.md (binding pre-spec contract).
  - A.5.3.2-PR10-CLOSE.md (durable PR 10 archival state PR 11
    inherits; §1.2 four architectural signals; §2 PR 11
    inheritance contract).
  - A.5.3.2-PR9-CLOSE.md (three-fixture corpus PR 11 drives;
    §2.4 authored/observed divergence proof case).
  - A.5.3.2-GATE-3-FRAMING.md (gate-level inheritance contract;
    §6.1 candidate carrier #16 promotion criteria; §11 same-
    commit Gate 3 close convergence).
"""

from __future__ import annotations

import pathlib

import pytest

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._seed import drive_seed_fixture

from tests.corpus.fixtures.fix_single_survivor import (
    FIXTURE as FIX_SINGLE_SURVIVOR,
)
from tests.corpus.fixtures.fix_multi_match import (
    FIXTURE as FIX_MULTI_MATCH,
)
from tests.corpus.fixtures.fix_no_keyword_match import (
    FIXTURE as FIX_NO_KW_MATCH,
)

# Test-internal archaeology surfaces (NOT public APIs) per
# module-docstring "Test infrastructure import discipline"
# framing + A.5.3.2-PR11-SPEC.md §4.1.2.
from tests.corpus.test_pr9_fixture_integration import (
    _apply_pr9_patches,
    _read_records,
)


def test_recomposition_arc_single_survivor_no_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Recomposition arc — single-survivor fixture: no divergence.

    Drives ``fix-pr9-single-survivor`` through the full
    decomposition seam path. PR14 + PR21 collapse to single
    survivor; observation's ``narrower.decision`` matches
    expectation's ``expected_narrow`` verbatim.
    ``compare_records`` reports ``narrow_diverged=False``.
    Carrier #17 verified at use: the DivergenceReport's
    per-surface partitioning preserves authorship through
    emission → persistence → readback → join → interpretive
    comparison.
    """
    # ── Step 1 of traversal: apply PR 9 monkeypatch suite ──────
    # Test-internal archaeology surface (NOT a public API).
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    # ── Steps 2-5 of traversal: drive fixture → emission ───────
    # drive_seed_fixture orchestrates expectation persistence,
    # chat_handler arbitration, observation emission. The seam
    # traversal is explicit at the call site — no helper absorbs
    # the arc (PR-11-LOCAL + framing §5.3 + §5.6).
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
        f"{FIX_SINGLE_SURVIVOR['fixture_id']!r}; got "
        f"{len(matching)}.\nAll records: {records}"
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
    # identifiable at the report's outer dict shape.
    assert report["fixture_id"] == FIX_SINGLE_SURVIVOR["fixture_id"]
    assert report["expectation"]["expected_narrow"] == ["forge_ping"]
    assert report["observation"]["observed_narrow"] == ["forge_ping"]
    assert report["divergence"]["narrow_diverged"] is False


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
    # ordering preserved through the full arc.
    # List-equality assertion (NOT set-equality, NOT sorted-
    # equality) is the §4.2 binding behavioral commitment
    # ("compare as persisted") verification AT USE — the
    # ordering survives emission → persistence → readback →
    # comparator without normalization.
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
    full 4-tool reachable set. The divergence is intentional +
    operationally valuable — it is the Gate 4 comparator-unblock
    proof case PR 9 close §2.4 named. ``compare_records``
    reports ``narrow_diverged=True``; the authored/observed
    divergence surfaces as a structured DivergenceReport claim
    per carrier #17.
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

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
    # surfaces structurally at the DivergenceReport.
    #
    # Property isolation across tests (per spec §4.1.6 + §4.1.7):
    # ordering-preservation semantics are exercised at test 2
    # (multi-match list-equality); test 3 isolates fallback-
    # membership semantics — did PR14's "no capability loss"
    # fallback preserve the entire reachable set? — independent
    # of ordering, which is incidental at the fallback path
    # (dict iteration order through _tool_filter.py). The
    # set(...) assertion sharpens the load-bearing claim by
    # removing ordering noise. The comparator itself still uses
    # list-equality (PR 10 §4.2 preserved); the set(...)
    # operation lives ONLY at the test assertion surface.
    assert report["fixture_id"] == FIX_NO_KW_MATCH["fixture_id"]
    assert report["expectation"]["expected_narrow"] == []
    assert len(report["observation"]["observed_narrow"]) == 4, (
        f"Expected full 4-tool reachable set in PR14 fallback; "
        f"got {report['observation']['observed_narrow']!r}"
    )
    # The full reachable set per _PR9_REACHABLE_TOOLS at
    # test_pr9_fixture_integration.py:208-213.
    assert set(report["observation"]["observed_narrow"]) == {
        "forge_ping",
        "forge_list_projects",
        "flame_list_libraries",
        "flame_render_status",
    }
    assert report["divergence"]["narrow_diverged"] is True
