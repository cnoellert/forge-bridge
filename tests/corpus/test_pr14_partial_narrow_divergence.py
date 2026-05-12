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
