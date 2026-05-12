"""PR 10 comparator behavioral tests — unit tests (one per
PR 9 fixture) at Step 3; authorship-preservation tests
(mutation + sort rejection) land at Step 4.

Active carrier #17 — recomposition discipline (Gate 3,
introduced at Gate 3 framing §5.1):

  Recomposition preserves authorship. The comparator joins
  observation + expectation records by fixture_id at read time;
  the join produces a derived view that names each authority
  surface's contribution explicitly. Cleanup pressure to
  collapse the three-authority-surface partition through
  interpretive synthesis is rejected at the spec layer.

Gate-3-LOCAL governing sentence — *candidate carrier #16
corroboration substrate* (Gate 3 framing §0 + §6.1; promotion
to active carrier #16 evaluated at Gate 3 close, NOT PR 10):

  Gate 3 proves topology, not infrastructure.

Proactive scope guardrail (Gate 3 framing §2.3 + PR 10 framing
§3.5):

  The comparator compares authored expectation records against
  observed arbitration records within a single operational
  arbitration surface.

PR-10-LOCAL binding statement (paraphrased per
``A.5.3.2-PR10-SPEC.md`` §0): tests assert the comparator does
not mutate its inputs and produces no side effects. The
mechanical assertion lands at Step 4
(``test_compare_records_does_not_mutate_inputs``).

Inherited carriers #1–#15 + Gate 2 binding framing clarification
cited by reference per §4.3.1 abbreviation discipline (this
module is the comparator's behavioral test surface, one layer
removed from production authority emission):

  - Canonical source: ``forge_bridge/corpus/_capture.py:6–135``
    + ``forge_bridge/corpus/_seed.py:19–135`` +
    ``forge_bridge/corpus/_compare.py`` module docstring.

PR-7-LOCAL pairs, PR-8-LOCAL binding statements, and
PR-9-LOCAL fixture-data discipline do NOT regenerate here per
the PR-N-LOCAL non-regeneration rule
(``A.5.3.2-PR10-SPEC.md`` §0).

Test inventory at PR 10 close (default disposition; 5 tests):

  Unit tests (one per PR 9 fixture, landed at Step 3):
    - test_compare_records_single_survivor_no_divergence
      (risk #1)
    - test_compare_records_multi_match_no_divergence (risk #2)
    - test_compare_records_no_keyword_match_divergence (risk #3)

  Authorship-preservation tests (landed at Step 4):
    - test_compare_records_does_not_mutate_inputs (risk #4 /
      PR-10-LOCAL invariant)
    - test_compare_records_does_not_sort_inputs (risk #5 / §4.2
      binding behavioral commitment — sort-rejection vector)

Conditional 6th test (incarnation-time decision per
``A.5.3.2-PR10-SPEC.md`` §4.3.3): NOT triggered at this
implementation. The §4.1.6 reference implementation uses direct
list equality (``obs_decision != exp_narrow``) with no
pre-comparison string processing; the canonicalization vector
is structurally unreachable; the conditional test is omitted
per default disposition.

See ``A.5.3.2-PR10-SPEC.md`` §4.3 + §5.1 + §6 Steps 3–4 for
the contract this module implements.
"""
from __future__ import annotations

import copy
from typing import Any

from forge_bridge.corpus._compare import compare_records
from forge_bridge.corpus._schema import SCHEMA_VERSION

# PR 9 fixture data — re-used by reference as the source of
# fixture_id / prompt / expected_narrow values. The FIXTURE
# dicts are data sources; the tests build full records
# (observation + expectation) in-memory via the builder helpers
# below by combining FIXTURE data with arbitration-trace +
# universal-key fields.
from tests.corpus.fixtures.fix_single_survivor import FIXTURE as FIX_SINGLE
from tests.corpus.fixtures.fix_multi_match import FIXTURE as FIX_MULTI
from tests.corpus.fixtures.fix_no_keyword_match import FIXTURE as FIX_NO_KW


def _build_observation_record(
    *,
    fixture_id: str,
    prompt: str,
    narrower_decision: list[str],
    pr20_condition_met: bool = False,
    collapse_occurred: bool = False,
    ambiguity_state: str = "multi_survivor",
) -> dict[str, Any]:
    """Build a minimum-shape valid observation record.

    Mirrors the pattern from
    ``tests/corpus/test_pr8_seed_surface.py::_minimum_valid_expectation_record``.
    Returns a dict carrying the 4 universal keys + the 6
    observation-required keys (source, prompt, candidate_set,
    topology, identity, narrower) + ``fixture_id`` (always
    present on observation records per PR 7 §4.3 Q3 structural-
    uniformity decision).

    The defaults align with the multi-match arbitration outcome
    (pr20=False, collapse=False, multi_survivor); callers
    override per test (single-survivor sets pr20=True +
    collapse=True + ambiguity_state="single_survivor"; no-keyword-
    match sets pr20=False + collapse=False).

    This helper is local because the comparator tests need
    full-shape observation records, not the schema-test
    minimum-shape (which only validates the schema validator's
    branch logic). Reusing PR 7/8 test helpers would couple
    PR 10 tests to PR 7/8 test internals; building locally
    preserves test-module independence.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "test-capture-id-obs",
        "captured_at": "2026-05-11T12:00:00.000Z",
        "record_kind": "observation",
        "source": "seed",
        "fixture_id": fixture_id,
        "prompt": prompt,
        "candidate_set": {
            "post_reachability": ["forge_ping", "forge_list_projects"],
            "post_pr14_filter": narrower_decision,
        },
        "topology": {
            "probed_at": "2026-05-11T12:00:00.000Z",
            "backends": {
                "flame_bridge": {"reachable": True},
                "ollama_local": {"reachable": True},
                "anthropic": {"reachable": True},
            },
        },
        "identity": {
            "narrower_version_hash": "test-narrower-hash",
            "registered_tools_snapshot_hash": "test-tools-hash",
            "daemon_git_sha": "test-git-sha",
        },
        "narrower": {
            "decision": narrower_decision,
            "pr20_condition_met": pr20_condition_met,
            "collapse_occurred": collapse_occurred,
            "ambiguity_state": ambiguity_state,
            "latency_ms": 12.5,
        },
    }


def _build_expectation_record(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> dict[str, Any]:
    """Build a minimum-shape valid expectation record.

    Mirrors PR 8's helper at
    ``test_pr8_seed_surface.py::_minimum_valid_expectation_record``.
    Carries the 4 universal keys + the 3 PR 8-required
    expectation keys (fixture_id, prompt, expected_narrow). No
    ``source`` field (per the schema validator's expectation-
    branch no-source check at ``_schema.py:243–247``).
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "test-capture-id-exp",
        "captured_at": "2026-05-11T12:00:00.000Z",
        "record_kind": "expectation",
        "fixture_id": fixture_id,
        "prompt": prompt,
        "expected_narrow": expected_narrow,
    }


def test_compare_records_single_survivor_no_divergence() -> None:
    """Single-survivor fixture: expected = observed =
    ['forge_ping']; comparator reports no divergence + correct
    per-surface contributions.

    Sources fixture_id + prompt + expected_narrow from
    ``tests.corpus.fixtures.fix_single_survivor.FIXTURE``. Builds
    a matching observation record (narrower.decision =
    ['forge_ping'], pr20_condition_met=True,
    collapse_occurred=True per the fixture's PR 9 spec §4.2
    arbitration trace archaeology).

    Risk #1 per A.5.3.2-PR10-SPEC.md §3: single-survivor
    narrowing produces expectation + observation that compose
    end-to-end and the comparator surfaces zero divergence.
    """
    obs = _build_observation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        narrower_decision=["forge_ping"],
        pr20_condition_met=True,
        collapse_occurred=True,
        ambiguity_state="single_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        expected_narrow=list(FIX_SINGLE["expected_narrow"]),
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-single-survivor",
        "expectation": {"expected_narrow": ["forge_ping"]},
        "observation": {"observed_narrow": ["forge_ping"]},
        "divergence": {"narrow_diverged": False},
    }


def test_compare_records_multi_match_no_divergence() -> None:
    """Multi-match fixture: expected = observed =
    ['forge_list_projects', 'flame_list_libraries'] verbatim
    (list-equality, order preserved per carrier #10); comparator
    reports no divergence.

    The two-element list ordering is meaningful per carrier #10:
    "narrower_decision carries the filtered list verbatim at
    narrowing finalization." Test asserts the comparator does
    NOT sort or reorder before comparison.

    Risk #2 per A.5.3.2-PR10-SPEC.md §3: multi-match ambiguity-
    rejection narrowing produces records that compose end-to-
    end without overloading chat-handler semantics or firing
    chain-step.
    """
    obs = _build_observation_record(
        fixture_id=FIX_MULTI["fixture_id"],
        prompt=FIX_MULTI["prompt"],
        narrower_decision=["forge_list_projects", "flame_list_libraries"],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_MULTI["fixture_id"],
        prompt=FIX_MULTI["prompt"],
        expected_narrow=list(FIX_MULTI["expected_narrow"]),
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-multi-match",
        "expectation": {
            "expected_narrow": ["forge_list_projects", "flame_list_libraries"],
        },
        "observation": {
            "observed_narrow": ["forge_list_projects", "flame_list_libraries"],
        },
        "divergence": {"narrow_diverged": False},
    }


def test_compare_records_no_keyword_match_divergence() -> None:
    """No-keyword-match fixture: expected = [], observed = full
    4-tool controlled set; comparator reports
    narrow_diverged=True + correct per-surface contributions.

    THE load-bearing PR 9-authored divergence proof case (per
    PR 9 spec §4.4 + the authored/observed divergence framing
    in fix_no_keyword_match.py). The fixture-author's
    aspirational claim (``expected_narrow=[]``) disagrees with
    the chat-handler's actual PR14 fallback behavior (full
    capability preserved); the comparator surfaces the
    divergence as a structured report claim.

    Risk #3 per A.5.3.2-PR10-SPEC.md §3: no-keyword-match
    prompt produces records that exercise the PR14 full-
    capability fallback path AND the comparator surfaces the
    authored-vs-observed disagreement as a structured
    ``DivergenceReport`` claim.
    """
    obs = _build_observation_record(
        fixture_id=FIX_NO_KW["fixture_id"],
        prompt=FIX_NO_KW["prompt"],
        narrower_decision=[
            "forge_ping",
            "forge_list_projects",
            "flame_list_libraries",
            "flame_render_status",
        ],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_NO_KW["fixture_id"],
        prompt=FIX_NO_KW["prompt"],
        expected_narrow=list(FIX_NO_KW["expected_narrow"]),  # []
    )

    report = compare_records(obs, exp)

    assert report == {
        "fixture_id": "fix-pr9-no-keyword-match",
        "expectation": {"expected_narrow": []},
        "observation": {
            "observed_narrow": [
                "forge_ping",
                "forge_list_projects",
                "flame_list_libraries",
                "flame_render_status",
            ],
        },
        "divergence": {"narrow_diverged": True},
    }


def test_compare_records_does_not_mutate_inputs() -> None:
    """PR-10-LOCAL binding statement
    (A.5.3.2-PR10-SPEC.md §0):

      The signature returns a new structured value; the inputs
      are read but never modified ... Tests assert input
      records remain byte-identical after the function returns.

    Builds a single-survivor pair; takes ``copy.deepcopy(...)``
    of both records BEFORE invoking ``compare_records``; asserts
    both records equal their pre-invocation deepcopies AFTER
    the function returns.

    Also asserts that mutating the RETURNED report's nested
    lists does NOT propagate back into the input records (the
    report's contained lists are fresh allocations per
    A.5.3.2-PR10-SPEC.md §4.1.6 implementation discipline:
    ``list(obs_decision)`` + ``list(exp_narrow)`` produce new
    list identities).

    Risk #4 per A.5.3.2-PR10-SPEC.md §3.
    """
    obs = _build_observation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        narrower_decision=["forge_ping"],
        pr20_condition_met=True,
        collapse_occurred=True,
        ambiguity_state="single_survivor",
    )
    exp = _build_expectation_record(
        fixture_id=FIX_SINGLE["fixture_id"],
        prompt=FIX_SINGLE["prompt"],
        expected_narrow=["forge_ping"],
    )

    obs_pre = copy.deepcopy(obs)
    exp_pre = copy.deepcopy(exp)

    report = compare_records(obs, exp)

    # Invariant: inputs byte-identical after the function returns.
    assert obs == obs_pre, (
        "observation_record mutated by compare_records — "
        "PR-10-LOCAL binding statement violated"
    )
    assert exp == exp_pre, (
        "expectation_record mutated by compare_records — "
        "PR-10-LOCAL binding statement violated"
    )

    # Defense in depth: mutating the report's contained lists
    # does NOT propagate back into input records. The report's
    # ``expected_narrow`` and ``observed_narrow`` lists are
    # FRESH allocations per §4.1.6 ("Report construction —
    # fresh-allocated lists"); mutation here would alias back
    # into inputs only if the implementation skipped the
    # ``list(...)`` wraps.
    report["observation"]["observed_narrow"].append("smuggled_tool")
    report["expectation"]["expected_narrow"].clear()

    assert obs == obs_pre, (
        "observation_record mutated by report-list mutation — "
        "report's lists must be fresh allocations per "
        "A.5.3.2-PR10-SPEC.md §4.1.6 implementation discipline"
    )
    assert exp == exp_pre, (
        "expectation_record mutated by report-list mutation — "
        "report's lists must be fresh allocations per "
        "A.5.3.2-PR10-SPEC.md §4.1.6 implementation discipline"
    )


def test_compare_records_does_not_sort_inputs() -> None:
    """§4.2 binding behavioral commitment
    (A.5.3.2-PR10-SPEC.md §0):

      The comparator does NOT sort narrower.decision or
      expected_narrow before comparing — order is meaningful
      observation/expectation; reordering masks divergence.

    Builds a pair where
    ``observation_record["narrower"]["decision"]`` and
    ``expectation_record["expected_narrow"]`` contain identical
    multi-element lists in DIFFERENT orderings. Asserts the
    comparator reports ``narrow_diverged=True`` (NOT False —
    silent sorting would mask the ordering divergence).

    Carrier #10 ("narrower_decision carries the filtered list
    verbatim") makes ordering meaningful — list-equality
    preserves it; set-equality or sorted-equality would
    structurally mask divergence at the chat-handler
    observation surface where PR14 input order is preserved
    through PR21.

    Risk #5 per A.5.3.2-PR10-SPEC.md §3 (sort-rejection
    vector of the §4.2 binding behavioral commitment).
    """
    obs = _build_observation_record(
        fixture_id="fix-pr10-sort-test",
        prompt="test sort rejection",
        narrower_decision=["tool_a", "tool_b"],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="multi_survivor",
    )
    exp = _build_expectation_record(
        fixture_id="fix-pr10-sort-test",
        prompt="test sort rejection",
        expected_narrow=["tool_b", "tool_a"],  # SAME contents, DIFFERENT order
    )

    report = compare_records(obs, exp)

    assert report["divergence"]["narrow_diverged"] is True, (
        "compare_records silently sorted/reordered one or both "
        "lists before comparison — §4.2 binding behavioral "
        "commitment violated. Input ordering must be preserved "
        "verbatim per carrier #10's 'filtered list verbatim' "
        "requirement at the chat-handler observation surface."
    )

    # Defense in depth: assert the per-surface contributions
    # preserve the ORIGINAL input orderings, not a sorted view.
    assert report["observation"]["observed_narrow"] == ["tool_a", "tool_b"], (
        "observation.observed_narrow does not preserve input "
        "ordering — comparator silently sorted/reordered the "
        "observation list. §4.2 binding behavioral commitment "
        "violated."
    )
    assert report["expectation"]["expected_narrow"] == ["tool_b", "tool_a"], (
        "expectation.expected_narrow does not preserve input "
        "ordering — comparator silently sorted/reordered the "
        "expectation list. §4.2 binding behavioral commitment "
        "violated."
    )
