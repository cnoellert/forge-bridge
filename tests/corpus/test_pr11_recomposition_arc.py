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
