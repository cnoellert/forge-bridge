"""PLACEHOLDER fixture module — Step 1 of A.5.3.2-PR9-SPEC.md.

This module exists at Step 1 solely to satisfy the
``_fixture_corpus_references`` walker's ≥1-fixture-module
precondition (see ``test_pr9_fixture_discipline.py::
test_fixture_modules_references_subset_of_permitted_imports``).
The placeholder ``FIXTURE`` constant has no semantic content;
its keys are placeholder strings + the empty list.

**Step 2 (per ``A.5.3.2-PR9-SPEC.md`` §4.2) replaces this
placeholder with:**

1. The full module docstring — 15 inherited carriers + binding
   framing clarification per the relevance-by-file ordering
   principle (carrier #15 at top); fixture purpose paragraph
   specific to the single-survivor narrowing outcome.
2. The real ``FIXTURE`` constant with a hand-selected single-step
   prompt + the corresponding ``expected_narrow`` (single-element
   list) verified at Step 2 against live ``chat_handler``
   arbitration trace.

The placeholder-and-replace pattern preserves four properties as
one atomic Step 1 construct (per ``A.5.3.2-PR9-SPEC.md`` §6 Step
1 verification deviation + Step 2 implementation note):

  - ontology (fixture-surface-data-discipline operational)
  - walker mechanics (≥1 fixture module satisfies precondition)
  - fixture topology (parallel-not-extension Layer 2 surface)
  - parallel-not-extension rationale (PR 4 / PR 8 / PR 9 walkers
    each ship distinct ontology under shared AST mechanics)

The placeholder ``FIXTURE`` carries no corpus imports. The walker
subset-check at Step 1 passes vacuously (empty set ⊂ any set).

**Do not consume this placeholder from integration tests.** The
``fixture_id`` "placeholder" is reserved; PR 9's integration tests
(Step 3) consume the real fixture content Step 2 lands.
"""
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "placeholder",
    "prompt": "placeholder",
    "expected_narrow": [],
}
