"""Seed fixture — partial-set divergence pure-isolation case
at the chat-handler observation surface.

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

Fixture purpose:

This fixture exercises the chat-handler-surface partial-set
divergence pure-isolation case. The prompt ``"list"`` (single-
step shape; does NOT fire chain-step arbitration) is identical
to PR 9 multi-match's prompt (``fix_multi_match.py``) and PR 13
ordering-divergence's prompt (``fix_ordering_divergence.py``);
the arbitration trace through PR14 + PR21 is grounded at
``fix_multi_match.py:105-140``.

PR14 keyword filter yields 2 candidates against the PR 9
controlled reachable-tool set (4 tools; see
``test_pr9_fixture_integration.py:208-213``):

  - ``forge_list_projects`` (token "list" matches)
  - ``flame_list_libraries`` (token "list" matches)

Both are other-match (single-token overlap; PR14 input order
from ``_PR9_REACHABLE_TOOLS`` declared order preserved through
the filter).

PR21 deterministic_narrow cannot collapse: both tools tie at
max-overlap=1 ("list"); no domain-priority pair fires (the
closed list ``(("version", "project"),)`` does not include
"list"); Rule 3 raw-token tie-breaker finds no asymmetry —
both tools have identical raw-token overlap with the message.
Survivor set is unchanged.

Observation record (deterministic per PR 9 multi-match
arbitration trace; identical to PR 13 ordering-divergence's
observation):

  narrower.decision = ["forge_list_projects",
                       "flame_list_libraries"]

(verbatim PR14 input order through PR21;
``_PR9_REACHABLE_TOOLS`` declared ordering at
``test_pr9_fixture_integration.py:208-213``. Both observation
values appear on the same list-literal line at
``fix_multi_match.py:126``.)

Expectation record (PR 14 fixture-author choice — the
authored-superset partial-set divergence vector, Direction A
per ``A.5.3.2-PR14-FRAMING.md`` §5.10):

  expected_narrow = ["forge_list_projects",
                     "flame_list_libraries",
                     "forge_ping"]

(positions 0+1 share observation's elements at observation
positions verbatim; position 2 extends with ``forge_ping`` as
the partial-set extension element. ``forge_ping`` is in the
PR 9 reachable-tool set per
``test_pr9_fixture_integration.py:209`` but shares NO tokens
with the prompt ``"list"``. The author asserts: "I expected
this unrelated tool to survive narrowing.")

The authored-superset direction is an affirmative architectural
decision per framing §5.10 — the architectural pressure vector
under test is overlap-interpretation, not directional ownership
of the superset relation. The temptation toward overlap-aware
DivergenceReport fields (predicted form 2 at framing §5.4)
operates symmetrically regardless of which side contains the
additional element; Direction A is selected for three reasons:
(1) preserves the single-variable discipline across PR 9 /
PR 13 / PR 14 — same prompt + same reachable-tool set + same
arbitration trace + same observation; (2) semantically legible
authorial claim — ``forge_ping`` is orthogonal to prompt tokens,
preventing collapse into fuzzy keyword semantics; (3) substrate
reuse preserving the ``"list"``-as-calibration-prompt
archaeology PR 9 + PR 13 established (framing §4.6).

The pure-isolation property holds at every dimension except
the target partial-set vector:

  - Same set membership at intersection: positions 0+1 contain
    {forge_list_projects, flame_list_libraries} at observation
    positions verbatim.
  - No ordering divergence at intersection: shared elements
    preserve at observation positions.
  - Cardinality asymmetry IS the partial-set vector:
    expectation length 3 vs. observation length 2. The
    cardinality asymmetry and the partial-set vector are the
    same architectural-pressure-surface phenomenon, not two
    separate confounds (per framing §2.4 + §4.3 clarification).
  - No semantic-normalization divergence: tool names are
    exact-match identifiers; no canonical-form transformations
    involved.
  - No duplicate-handling divergence: each list contains
    distinct elements.
  - No multi-survivor cardinality confound: both lists are
    multi-element (>1); the cardinality-class divergence vector
    is PR 15's substrate, not PR 14's.

The comparator's compare-as-persisted discipline (PR 10 §4.2
binding behavioral commitment) detects the partial-set
divergence as ``narrow_diverged=True`` per direct list-equality
at ``_compare.py:503`` (``obs_decision != exp_narrow``; length
asymmetry (2 vs 3) + element-membership asymmetry at position 2
both contribute to the inequality; no sort, no canonicalization,
no semantic coercion, no overlap-aware computation at any
traversal seam).

This fixture differs from PR 9 multi-match
(``fix_multi_match.py``) and PR 13 ordering-divergence
(``fix_ordering_divergence.py``) at exactly one surface: the
authored expectation. PR 9 multi-match authors
``expected_narrow`` matching observation verbatim (no-divergence
baseline). PR 13 authors the ordering swap (same set, different
sequence). PR 14 authors the superset extension (same elements
at positions 0+1, additional element at position 2). The
single-variable discipline across PR 9 / PR 13 / PR 14 is itself
architectural-substrate evidence — the comparator surface is
the only moving interpretive layer across the three-PR series
(framing §4.6).

Prompt reuse is NOT collision — fixture identity discriminator
is ``fixture_id``, not ``prompt``; per-test ``tmp_path`` corpus
isolation prevents record co-existence between PR 9 multi-
match's invocation, PR 13 ordering-divergence's invocation,
and PR 14 partial-set-divergence's invocation. The prompt-
reuse-without-collision discipline is itself architectural
evidence (PR 13 close §2.1 PR-of-origin archaeology).

The arbitration trace recorded above is archaeology-grade per
``feedback_counts_are_archaeology_grade.md``. Future
contributors diagnosing PR 14 regressions can verify against
the trace recorded here + the PR 9 multi-match trace + the
PR 13 ordering-divergence trace.

References:

  - ``A.5.3.2-PR14-SPEC.md`` (this fixture's implementation
    contract).
  - ``A.5.3.2-PR14-FRAMING.md`` (binding pre-spec contract).
  - ``A.5.3.2-GATE-4-FRAMING.md`` (immediate gate-level
    inheritance contract).
  - ``A.5.3.2-PR13-CLOSE.md`` (PR-13-LOCAL as PR-of-origin for
    the pure-isolation pattern; calibration substrate at first
    calibration point).
  - ``tests/corpus/fixtures/fix_multi_match.py:105-140``
    (PR 9 multi-match arbitration trace; PR 14 inherits the
    trace grounding).
  - ``tests/corpus/fixtures/fix_ordering_divergence.py``
    (PR 13 ordering-divergence fixture; PR 14 mirrors the
    fixture structural shape).
  - ``tests/corpus/test_pr9_fixture_integration.py:208-213``
    (``_PR9_REACHABLE_TOOLS`` declared order including
    ``forge_ping`` at index 0).
  - ``forge_bridge/corpus/_compare.py:503`` (comparator's
    direct list-equality semantics).

This fixture is data + one orchestration call only — no
helpers, no factories, no parametrization. Per cleanup-pressure-
resistance class member #9 (fixture-surface-data-discipline;
``A.5.3.2-PR9-FRAMING.md`` §6.1 + ``A.5.3.2-GATE-3-CLOSE.md``
§1.5).
"""

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
