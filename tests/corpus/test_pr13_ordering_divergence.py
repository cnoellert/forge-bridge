"""End-to-end ordering-divergence recomposition arc test —
fixture → drive_seed_fixture → chat_handler → emission →
readback → compare_records → DivergenceReport
(narrow_diverged=True).

PR-13-LOCAL binding statement (A.5.3.2-PR13-FRAMING.md §5.5,
scope-local per PR-N-LOCAL non-regeneration rule):

  PR 13 isolates ordering divergence as the sole pressure
  vector. Multi-vector fixture pressure within PR 13 scope —
  combining ordering with cardinality, partial-set,
  semantic-normalization, duplicate-handling, or any other
  divergence form — is rejected at the spec layer. The
  pure-isolation property is what gives PR 13 its
  laboratory-grade methodology corroboration value for
  Placement A + Placement B substrate.

Traversal trace (A.5.3.2-PR13-FRAMING.md §2.1 verbatim):

  fixture (tests/corpus/fixtures/fix_ordering_divergence.py)
    → drive_seed_fixture          [orchestration seam]
      → emit_seed_expectation     [expectation persistence seam]
      → chat_handler arbitration  [observation production seam]
        → emit_divergence_capture [observation persistence seam]
          → JSONL persistence     [persistence-topology seam]
            → reader              [readback seam (via _read_records)]
              → compare_records   [interpretive-read seam]
                → DivergenceReport assertions (narrow_diverged=True)

Each arrow is a decomposition seam established at Gate 2 or
Gate 3 substrate work. PR 13 traverses the seams under
ordering-divergence pressure; no helper absorbs the arc into
a single call (PR-11-LOCAL traverses-not-erases-seams
inherited at gate level per A.5.3.2-GATE-3-CLOSE.md §3
item 10).

Carrier travel — citation by reference (A.5.3.2-PR13-SPEC.md
§0 + A.5.3.2-PR13-FRAMING.md §3.1):

  17 active carriers + Gate 2 binding framing clarification +
  inherited PR-LOCAL bindings travel by reference to canonical
  sources:

    - forge_bridge/corpus/_capture.py:6-135 — carriers
      #1–#14 + Gate 2 binding framing clarification on
      call-site-owned arbitration inputs.
    - forge_bridge/corpus/_seed.py:19-135 — carrier #15 +
      PR-8-LOCAL bindings (member #7 truth-partitioning,
      member #8 semantics-not-topology).
    - forge_bridge/corpus/_compare.py module docstring +
      compare_records function docstring — carrier #17 +
      PR-10-LOCAL read-only mutability invariant + PR 10 §4.2
      binding behavioral commitment ("compare as persisted") +
      cross-surface unbinding clarification + proactive scope
      guardrail.
    - A.5.3.2-GATE-3-CLOSE.md §1.6 — carrier #16
      ("Reliability work proves topology, not infrastructure").

Test infrastructure import discipline (A.5.3.2-PR13-SPEC.md
§4.2.1 site 9 + A.5.3.2-PR11-SPEC.md §4.1.1 site 11
inheritance):

  PR 13 imports `_apply_pr9_patches` and `_read_records` from
  `tests.corpus.test_pr9_fixture_integration` as
  **test-internal archaeology surfaces**, NOT as public APIs.
  The underscored-private status is preserved — the import is
  test-internal and archaeology-explicit, mirroring the PR 11
  consumption pattern
  (`test_pr11_recomposition_arc.py:111-114`). This does NOT
  promote the helpers to public APIs; future contributors
  must NOT read this as a general invitation to import
  underscored-private helpers across production modules.

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
    PR 10 §4.2 binding behavioral commitment exercised under
    ordering-divergence pressure).
  - tests/corpus/test_pr11_recomposition_arc.py
    (recomposition arc consumption pattern inherited).
  - tests/corpus/fixtures/fix_multi_match.py:105-140
    (PR 9 multi-match arbitration trace inherited).
"""

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
