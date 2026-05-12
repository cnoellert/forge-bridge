"""Seed fixture — ordering-divergence pure-isolation case at
the chat-handler observation surface.

PR-13-LOCAL binding statement (``A.5.3.2-PR13-FRAMING.md`` §5.5,
scope-local per PR-N-LOCAL non-regeneration rule):

  PR 13 isolates ordering divergence as the sole pressure
  vector. Multi-vector fixture pressure within PR 13 scope —
  combining ordering with cardinality, partial-set,
  semantic-normalization, duplicate-handling, or any other
  divergence form — is rejected at the spec layer. The
  pure-isolation property is what gives PR 13 its
  laboratory-grade methodology corroboration value for
  Placement A + Placement B substrate.

Carrier travel — citation by reference (``A.5.3.2-PR13-SPEC.md``
§0 + ``A.5.3.2-PR13-FRAMING.md`` §3.1):

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

This fixture exercises the chat-handler-surface ordering-
divergence pure-isolation case. The prompt ``"list"`` (single-
step shape; does NOT fire chain-step arbitration) is identical
to PR 9 multi-match's prompt (``fix_multi_match.py``); the
arbitration trace through PR14 + PR21 is grounded at
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

(positions swapped relative to observation — the SAME set,
DIFFERENT sequence; the single-direction pure-isolation
ordering-divergence vector PR-13-LOCAL binds.)

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

The comparator's compare-as-persisted discipline (PR 10 §4.2
binding behavioral commitment) detects the ordering-only
divergence as ``narrow_diverged=True`` per direct list-equality
at ``_compare.py:503`` (``obs_decision != exp_narrow``; no
sort, no canonicalization, no semantic coercion at any
traversal seam).

This fixture differs from PR 9 multi-match
(``fix_multi_match.py``) at exactly one surface: the authored
expectation. PR 9 multi-match authors ``expected_narrow``
matching observation verbatim (no-divergence baseline). PR 13
authors the swap. Prompt reuse is NOT collision — fixture
identity discriminator is ``fixture_id``, not ``prompt``;
per-test ``tmp_path`` corpus isolation prevents record
co-existence between PR 9 multi-match's invocation and PR 13's
invocation. The prompt-reuse-without-collision is itself
architectural evidence: arbitration topology + fixture identity
+ divergence semantics are independent authority surfaces.

The arbitration trace recorded above is archaeology-grade per
``feedback_counts_are_archaeology_grade.md``. Future
contributors diagnosing PR 13 regressions can verify against
the trace recorded here + the PR 9 multi-match trace.

References:

  - ``A.5.3.2-PR13-SPEC.md`` (this fixture's implementation
    contract).
  - ``A.5.3.2-PR13-FRAMING.md`` (binding pre-spec contract).
  - ``A.5.3.2-GATE-4-FRAMING.md`` (immediate predecessor;
    gate-level inheritance contract).
  - ``tests/corpus/fixtures/fix_multi_match.py:105-140``
    (PR 9 multi-match arbitration trace; PR 13 inherits the
    trace grounding).
  - ``tests/corpus/test_pr9_fixture_integration.py:208-213``
    (``_PR9_REACHABLE_TOOLS`` declared order).
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
    "fixture_id": "fix-pr13-ordering-divergence",
    "prompt": "list",
    "expected_narrow": ["flame_list_libraries", "forge_list_projects"],
}
