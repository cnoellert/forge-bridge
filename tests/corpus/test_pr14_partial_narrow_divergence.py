"""End-to-end partial-set divergence recomposition arc test —
fixture → drive_seed_fixture → chat_handler → emission →
readback → compare_records → DivergenceReport
(narrow_diverged=True).

PR-14-LOCAL binding statement (``A.5.3.2-PR14-FRAMING.md`` §0 +
§5.5, scope-local per PR-N-LOCAL non-regeneration rule):

  PR 14 isolates partial-set divergence as the sole pressure
  vector. Multi-vector fixture pressure within PR 14 scope —
  combining partial-set with ordering, semantic-normalization,
  duplicate-handling, multi-survivor-cardinality, or any other
  divergence form — is rejected at the spec layer. The
  pure-isolation property is what gives PR 14 its
  laboratory-grade methodology corroboration value for
  Placement A + Placement B substrate.

Traversal trace (``A.5.3.2-PR14-FRAMING.md`` §2.1 verbatim):

  fixture (tests/corpus/fixtures/fix_partial_narrow_divergence.py)
    → drive_seed_fixture          [orchestration seam]
      → emit_seed_expectation     [expectation persistence seam]
      → chat_handler arbitration  [observation production seam]
        → emit_divergence_capture [observation persistence seam]
          → JSONL persistence     [persistence-topology seam]
            → reader              [readback seam (via _read_records)]
              → compare_records   [interpretive-read seam]
                → DivergenceReport assertions (narrow_diverged=True)

Each arrow is a decomposition seam established at Gate 2 or
Gate 3 substrate work. PR 14 traverses the seams under
partial-set divergence pressure; no helper absorbs the arc into
a single call (PR-11-LOCAL traverses-not-erases-seams
inherited at gate level per ``A.5.3.2-GATE-3-CLOSE.md`` §3
item 10).

Carrier travel — citation by reference (``A.5.3.2-PR14-SPEC.md``
§0 + ``A.5.3.2-PR14-FRAMING.md`` §3.1):

  17 active carriers + Gate 2 binding framing clarification +
  inherited PR-LOCAL bindings travel by reference to canonical
  sources:

    - ``forge_bridge/corpus/_capture.py:6-135`` — carriers
      #1–#14 + Gate 2 binding framing clarification on
      call-site-owned arbitration inputs.
    - ``forge_bridge/corpus/_seed.py:19-135`` — carrier #15 +
      PR-8-LOCAL bindings (member #7 truth-partitioning,
      member #8 semantics-not-topology).
    - ``forge_bridge/corpus/_compare.py`` module docstring +
      ``compare_records`` function docstring — carrier #17 +
      PR-10-LOCAL read-only mutability invariant + PR 10 §4.2
      binding behavioral commitment ("compare as persisted") +
      cross-surface unbinding clarification + proactive scope
      guardrail.
    - ``A.5.3.2-GATE-3-CLOSE.md`` §1.6 — carrier #16
      ("Reliability work proves topology, not infrastructure").

Test infrastructure import discipline (``A.5.3.2-PR14-SPEC.md``
§4.2.1 site 9 + ``A.5.3.2-PR11-SPEC.md`` §4.1.1 site 11 +
``A.5.3.2-PR13-SPEC.md`` §4.2.1 site 9 inheritance):

  PR 14 imports ``_apply_pr9_patches`` and ``_read_records``
  from ``tests.corpus.test_pr9_fixture_integration`` as
  **test-internal archaeology surfaces**, NOT as public APIs.
  The underscored-private status is preserved — the import is
  test-internal and archaeology-explicit, mirroring the PR 11
  consumption pattern
  (``test_pr11_recomposition_arc.py:111-114``) + PR 13
  consumption pattern
  (``test_pr13_ordering_divergence.py:110-113``). This does NOT
  promote the helpers to public APIs; future contributors must
  NOT read this as a general invitation to import underscored-
  private helpers across production modules.

References:

  - ``A.5.3.2-PR14-SPEC.md`` (this module's implementation
    contract).
  - ``A.5.3.2-PR14-FRAMING.md`` (binding pre-spec contract).
  - ``A.5.3.2-GATE-4-FRAMING.md`` (immediate gate-level
    inheritance contract; §2.4 architectural commitment).
  - ``A.5.3.2-PR13-CLOSE.md`` (PR-13-LOCAL as PR-of-origin for
    the pure-isolation pattern; both-skeletons-at-Step-1
    lifecycle invariant as PR-of-origin).
  - ``A.5.3.2-PR11-CLOSE.md`` (recomposition arc operational
    evidence; PR-11-LOCAL traverses-not-erases-seams inherited
    at gate level per Gate 3 close §3 item 10).
  - ``A.5.3.2-PR10-CLOSE.md`` (durable PR 10 archival state;
    PR 10 §4.2 binding behavioral commitment exercised under
    partial-set divergence pressure).
  - ``tests/corpus/test_pr13_ordering_divergence.py``
    (PR 13 test module; PR 14 mirrors the 9-step traversal
    annotation pattern + four-key assertion contract).
  - ``tests/corpus/test_pr11_recomposition_arc.py``
    (recomposition arc consumption pattern inherited).
  - ``tests/corpus/fixtures/fix_multi_match.py:105-140``
    (PR 9 multi-match arbitration trace inherited).
"""

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


def test_recomposition_arc_partial_narrow_divergence(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
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
