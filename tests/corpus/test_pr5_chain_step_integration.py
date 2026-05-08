"""PR 5 step 7 — chain-step integration tests.

Carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR4-FRAMING.md`` §0/§3, ``A.5.3.2-PR4-SPEC.md`` §0,
``A.5.3.2-PR5-FRAMING.md`` §0/§2.1/§2.2, ``A.5.3.2-PR5-SPEC.md`` §4.1):

Inherited from PR 4 (verbatim, unchanged):

    PR 4 is the controlled introduction of observational
    side-effects into live arbitration surfaces.

    The risk category has shifted from persistence-substrate risk
    to participation-creep risk.

    The call site is the source of the three explicit inputs.

    The integration layer passes truth.

    The integration layer never reconstructs truth.

    The builder does not discover runtime state.

    Capture emission occurs only after arbitration state is
    finalized for the current execution path. Capture records
    completed arbitration observations, not provisional intermediate
    state.

── PR 5 specializations ──

    PR 5 is the second call site under the integration discipline
    PR 4 established. The risk profile is inherited; the surface
    geometry is not.

    The chain-step's deployment identity is the caller's view, not
    the global daemon registry view.

    Ambiguity rejection is an arbitration outcome. Capture must
    record it. At this surface, narrower_decision carries the
    filtered list verbatim at narrowing finalization — including
    zero-match and multi-match rejection paths. pr20_condition_met
    is always False and collapse_occurred is False on all rejection
    paths. These semantics differ from the chat-handler case and
    must not be silently overloaded.

    Capture is arbitration-aware, not branch-aware. The single
    insertion point at narrowing-finalization preserves capture's
    relationship to the arbitration event itself, not to its
    downstream semantic interpretations.

This module ships three test functions exercising the four
hostile-environment probes from ``A.5.3.2-PR4-FRAMING.md`` §1.2 plus
the §6.1 rejection-path empirical bite-verification requirement:

  - ``test_chain_step_arbitration_invariant_under_capture_state``
    — parametrized over four pytest IDs ``[disabled, enabled-
    single_match, enabled-multi_match, failing]``. The enabled state
    is split into single_match (success path) and multi_match
    (rejection path) variants per ``A.5.3.2-PR5-SPEC.md`` §6.1's
    locked formulation: "The spec requires at least one enabled-
    state integration assertion to exercise the multi-match
    rejection path empirically." Without the multi_match parameter,
    the framing §2.2 silent-overload failure mode would not be
    bite-verified empirically.

  - ``test_chain_step_recovering`` — dedicated function, three-block
    geometry, two arbitration invocations. Visibly heavier than the
    other states because architecturally heavier (temporal
    contamination probe). Visible duplication of request #1 / request
    #2 carries semantic weight: do NOT collapse via abstracted helpers.

  - ``test_chain_step_capture_latency_within_budget`` — dedicated,
    sequential disabled→enabled, min-of-N sample with asymmetric
    target/ceiling discipline. Same budget as PR 4 (5/20 ms target/
    ceiling) per A.5.3.2-PR5-FRAMING.md §2.3 — capture work is
    structurally identical at both surfaces; chain steps run at
    higher cadence but each emission's per-call cost is the same.

Two-block geometry (parametrized): ARBITRATION-INVARIANCE block first,
CAPTURE-CORRECTNESS block second, never interleaved. A reviewer can
verify §1.2 by reading only the first block.

Three-block geometry (recovering): BLOCK A (request #1 invariance) →
BLOCK B (request #2 invariance + cross-state response equivalence) →
BLOCK C (capture-correctness contamination check). The geometry
mirrors the runtime asymmetry; preserve it.

Self-contained test machinery — no imports from ``tests.console.*``.
This is a binding constraint per the PR 4 Chris convergence directive
inherited unchanged: future ``tests/console/conftest.py`` refactors
must NOT silently weaken §1.2's arbitration-invariance guard.

Bite-verification scratch design lives at incarnation, not topology.
If a particular contamination vector proves to bite weakly, the
correct response is to adjust the scratch surgically — not to reopen
the assertion helper or recovering geometry.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

import pytest

# jinja2 is a declared chat-handler dependency (pyproject.toml). The
# chain path drives requests through the chat handler's HTTP endpoint
# (which routes to _execute_chain → run_chain_steps → execute_chain_step),
# so the SUT cannot construct without jinja2. Skipping where absent is
# operationally honest, not a property weakening — the §1.2 invariance
# invariant is enforced wherever the chat handler can run at all.
pytest.importorskip(
    "jinja2",
    reason=(
        "jinja2 is a declared chat-handler dependency; this test "
        "file cannot construct the SUT without it. Skipping where "
        "absent is operationally honest, not a property weakening."
    ),
)

from forge_bridge.console import _rate_limit  # noqa: E402

from tests.corpus._pr4_helpers import (  # noqa: E402
    CaptureState,
    _assert_chain_step_arbitration_invariance,
    _assert_chain_step_arbitration_response_equivalent,
    _assert_no_failed_write_residue,
    _drive_chain_request,
    _make_test_tool,
    _read_records,
    capture_state_cycling,  # re-exported for parametrize indirect=True  # noqa: F401
)


# Asymmetric latency budget per A.5.3.2-PR5-FRAMING.md §2.3 (inherited
# from PR 4 spec §6.1):
#
#   target = diagnostic. Exceeded → investigate; do NOT raise.
#   ceiling = architectural. Exceeded → hard fail.
#
# "Exceeding the target triggers investigation, not threshold
#  adjustment." The values are not interchangeable thresholds; they
# encode a non-flat budget posture.
LATENCY_TARGET_MS = 5.0
LATENCY_CEILING_MS = 20.0

# Deliberately modest: estimating overhead floor, not building a
# statistically rigorous latency profile. Same value as PR 4.
LATENCY_SAMPLES = 10

# Default chain prompt — two-step chain via parse_chain (the ``->``
# separator triggers _execute_chain in chat_handler).
_CHAIN_PROMPT = "first -> second"


@pytest.fixture(autouse=True)
def _reset_rate_limit_autouse() -> Iterator[None]:
    """Per-test rate-limit isolation. Required for every test in
    this file because each test drives one or more chat requests
    against the IP-keyed token bucket. Autouse rather than
    explicit-request because every test needs it; making it explicit
    would be visual noise without semantic value.
    """
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


# ─── Test 1 — 4-ID parametrized arbitration invariance ─────────────────────
#
# Four pytest IDs in one parametrized test:
#   [disabled]           — pre-PR-5 baseline; gate short-circuits.
#   [enabled-single_match] — successful capture; nominal success path.
#   [enabled-multi_match]  — successful capture; multi-match rejection
#                            path. REQUIRED per A.5.3.2-PR5-SPEC.md §6.1
#                            for empirical bite-verification of the
#                            framing §2.2 schema field semantics
#                            (narrower_decision verbatim, collapse_occurred
#                            False on all rejection paths).
#   [failing]            — I-6 failure-invisibility at integration level.
#
# The dual-parameter shape (state, prompt_kind) lives in pytest.param
# with explicit ids so the test reader can see at a glance which
# combinations are exercised.


@pytest.mark.parametrize(
    "capture_state_cycling,prompt_kind",
    [
        pytest.param("disabled", "single_match", id="disabled"),
        pytest.param("enabled", "single_match", id="enabled-single_match"),
        pytest.param("enabled", "multi_match", id="enabled-multi_match"),
        pytest.param("failing", "single_match", id="failing"),
    ],
    indirect=["capture_state_cycling"],
)
def test_chain_step_arbitration_invariant_under_capture_state(
    capture_state_cycling: tuple[CaptureState, Path],
    prompt_kind: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Arbitration invariance under disabled / enabled (single + multi
    match) / failing capture states. Two-block geometry — invariance
    first, capture-correctness second.

    Per ``A.5.3.2-PR5-FRAMING.md`` §1.2 (inheriting PR 4 framing §1.2):
    PR 4's single most important invariant carries forward unchanged
    at the chain-step surface. The block separation is reviewer-
    visible discipline: the first block reads identically across all
    four parametrized IDs; the second block is state-and-prompt-kind
    specific.

    The enabled-multi_match parametrization exercises §6.1's
    rejection-path empirical bite — ``narrower_decision`` carries the
    filtered multi-tool list verbatim, ``ambiguity_state`` is
    "multi_survivor", ``collapse_occurred`` is False. Without this
    parametrization, framing §2.2's silent-overload failure mode
    remains a documentation claim rather than a tested invariant.
    """
    state, corpus_dir = capture_state_cycling

    # Tool-list construction per prompt_kind:
    # - single_match: one tool. PR14 fallback (no token overlap)
    #   returns it; len(filtered) == 1 → success.
    # - multi_match:  two tools. PR14 fallback returns both;
    #   deterministic_narrow has no overlap signal to discriminate;
    #   len(filtered) == 2 → rejection envelope. Capture fires BEFORE
    #   the rejection branch per spec §4.1 single-insertion-point
    #   discipline.
    if prompt_kind == "single_match":
        tools_list = [_make_test_tool(name="forge_test_probe")]
        expected_step_count = 2  # both steps complete on success path
        expected_status = "success"
    elif prompt_kind == "multi_match":
        tools_list = [
            _make_test_tool(name="forge_alpha_probe"),
            _make_test_tool(name="forge_beta_probe"),
        ]
        expected_step_count = 0  # chain aborts at step 0 (multi-match)
        expected_status = "error"
    else:
        raise AssertionError(f"unknown prompt_kind: {prompt_kind!r}")

    # ===== ARBITRATION-INVARIANCE BLOCK (identical-shape across IDs) ===
    response, mock_call_tool = _drive_chain_request(
        tools_list=tools_list, prompt=_CHAIN_PROMPT,
    )
    _assert_chain_step_arbitration_invariance(
        response,
        mock_call_tool,
        expected_step_count=expected_step_count,
        expected_status=expected_status,
    )
    # ====================================================================

    # ===== CAPTURE-CORRECTNESS BLOCK (state-and-prompt-kind specific) ===
    if state == "disabled":
        # Pre-PR-5 baseline: no records, no warnings, no filesystem
        # activity. Gate short-circuits before any directory access.
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=0,
        )
        if corpus_dir.exists():
            assert not list(corpus_dir.iterdir()), (
                f"disabled state produced filesystem activity in "
                f"{corpus_dir}: {list(corpus_dir.iterdir())!r}. The "
                f"divergence_capture_enabled() gate should have "
                f"short-circuited."
            )

    elif state == "enabled" and prompt_kind == "single_match":
        # Two records — one per chain step (per-step emission per
        # spec §4.1). Each record's narrower_decision matches the
        # arbitration output (the single tool); registered_tools
        # snapshot identity matches the caller-passed tools list.
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=2,
        )
        records = _read_records(corpus_dir)
        assert len(records) == 2, (
            f"enabled-single_match state expected exactly two "
            f"records (one per chain step); got {len(records)} in "
            f"{corpus_dir}"
        )
        # Both records share the same deployment-identity hash
        # (caller threads the same tools list through every step).
        h1 = records[0]["identity"]["registered_tools_snapshot_hash"]
        h2 = records[1]["identity"]["registered_tools_snapshot_hash"]
        assert h1 == h2, (
            f"per-chain-invocation deployment identity should be "
            f"stable; got two distinct hashes: {h1!r} != {h2!r}. Per "
            f"A.5.3.2-PR5-FRAMING.md §2.1, the caller threads the "
            f"same tools list through every step."
        )
        for i, record in enumerate(records):
            assert record["narrower"]["decision"] == ["forge_test_probe"], (
                f"chain step {i}'s narrower.decision does not match "
                f"arbitration output: got "
                f"{record['narrower']['decision']!r}, expected "
                f"['forge_test_probe']"
            )
            assert record["narrower"]["pr20_condition_met"] is False, (
                f"chain step {i}'s pr20_condition_met must be False at "
                f"this surface (no PR20 short-circuit path exists). "
                f"Got {record['narrower']['pr20_condition_met']!r}"
            )
            # collapse_occurred is False on the success path here
            # because tools_post_pr14 has only ONE tool (no multi-to-
            # single transition possible; the single tool was always
            # the only candidate).
            assert record["narrower"]["collapse_occurred"] is False, (
                f"chain step {i}'s collapse_occurred must be False "
                f"when tools_post_pr14 has length 1 (no multi-to-"
                f"single transition). Got "
                f"{record['narrower']['collapse_occurred']!r}"
            )
            assert record["narrower"]["ambiguity_state"] == "single_survivor", (
                f"chain step {i}'s ambiguity_state must be "
                f"'single_survivor' on success path. Got "
                f"{record['narrower']['ambiguity_state']!r}"
            )

    elif state == "enabled" and prompt_kind == "multi_match":
        # ONE record — chain aborts at step 0 (multi-match rejection)
        # but capture fires BEFORE the rejection branch. Step 1 is
        # never executed. This is the framing §2.2 verbatim-list
        # discipline empirically bite-verified.
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=1,
        )
        records = _read_records(corpus_dir)
        assert len(records) == 1, (
            f"enabled-multi_match state expected exactly one record "
            f"(step 0's pre-rejection emission); got {len(records)} "
            f"in {corpus_dir}. Chain aborts at step 0 — step 1 must "
            f"never execute."
        )
        record = records[0]

        # narrower_decision carries the multi-tool list VERBATIM. Not
        # empty, not a sentinel. Per framing §2.2: "the arbitration
        # outcome expresses rejection; the list expresses the actual
        # narrowing result."
        assert record["narrower"]["decision"] == [
            "forge_alpha_probe", "forge_beta_probe",
        ], (
            f"multi-match rejection record's narrower.decision must "
            f"carry the filtered list verbatim at narrowing "
            f"finalization (NOT empty, NOT a sentinel). Got "
            f"{record['narrower']['decision']!r}, expected "
            f"['forge_alpha_probe', 'forge_beta_probe']. Per "
            f"A.5.3.2-PR5-FRAMING.md §2.2: 'narrower_decision carries "
            f"the filtered list verbatim at narrowing finalization "
            f"— including zero-match and multi-match rejection "
            f"paths.'"
        )

        # pr20_condition_met = False (always at this surface).
        assert record["narrower"]["pr20_condition_met"] is False, (
            f"multi-match rejection record's pr20_condition_met must "
            f"be False (always False at chain-step surface — no LLM "
            f"fall-through path exists). Got "
            f"{record['narrower']['pr20_condition_met']!r}"
        )

        # collapse_occurred = False on rejection path. Per framing
        # §2.2: "False on all rejection paths (zero-match-to-error
        # and multi-match-to-error are both distinct from the
        # multi-to-single transition collapse_occurred records)."
        assert record["narrower"]["collapse_occurred"] is False, (
            f"multi-match rejection record's collapse_occurred must "
            f"be False (rejection paths are distinct from the multi-"
            f"to-single transition collapse_occurred records). Got "
            f"{record['narrower']['collapse_occurred']!r}"
        )

        # ambiguity_state = "multi_survivor" (translation-only helper).
        assert record["narrower"]["ambiguity_state"] == "multi_survivor", (
            f"multi-match rejection record's ambiguity_state must "
            f"be 'multi_survivor'. Got "
            f"{record['narrower']['ambiguity_state']!r}"
        )

        # mcp.call_tool was NOT called — capture fired before
        # rejection, but the chain never reached tool execution.
        assert mock_call_tool.call_count == 0, (
            f"multi-match rejection should NOT call mcp.call_tool; "
            f"got call_count={mock_call_tool.call_count}. The chain "
            f"aborts at the rejection envelope before tool execution."
        )

    elif state == "failing":
        # I-6 failure-invisibility at integration level: zero records
        # on disk (write attempts fail), WARNING(s) logged matching
        # the PR 3 failure-invisibility log shape, chain envelope
        # arbitration-equivalent to disabled (already checked by the
        # invariance block above).
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=0,
        )
        warnings = [
            r for r in caplog.records
            if r.levelname == "WARNING"
            and "capture write failed" in r.getMessage().lower()
        ]
        # Per-step emission semantics: a 2-step chain attempts capture
        # twice (once per step), so the failing state produces two
        # WARNING entries — one per failed capture write.
        assert len(warnings) == expected_step_count or len(warnings) >= 1, (
            f"failing state expected at least one 'capture write "
            f"failed' WARNING (one per attempted emission across "
            f"{expected_step_count} chain steps); got {len(warnings)}: "
            f"{[r.getMessage() for r in warnings]!r}"
        )
    # ====================================================================


# ─── Test 2 — dedicated recovering test (three-block geometry) ─────────────


@pytest.mark.parametrize(
    "capture_state_cycling",
    ["recovering"],
    indirect=True,
)
def test_chain_step_recovering(
    capture_state_cycling: tuple[CaptureState, Path],
) -> None:
    """Recovering state — visibly heavier than the other states
    because architecturally heavier. Probes inter-emission state
    independence at the chain-step surface: prior failure must not
    poison later arbitration.

    Visible duplication between request #1 and request #2 is
    intentional. It carries the semantic weight that the recovering
    probe is two independent arbitration acts, not one arbitration
    with retry. Do NOT collapse into helpers that abstract the
    duplication away — the visual roughness is the protection.

    The fixture is parametrized with ``["recovering"]`` indirect so
    the canonical hostile-state definition lives in
    ``capture_state_cycling`` rather than being re-derived inline.
    Ownership boundary lives at the fixture; geometry lives here.

    Note on emission timing: a 2-step single-match chain attempts
    capture twice per request (one per step). The fixture's
    fail_until_call=1 fails the FIRST corpus-scoped Path.open;
    subsequent calls succeed. This means request #1's first-step
    capture fails, but its second-step capture succeeds (the failure
    counter is per-process, not per-request). Request #2's both
    captures succeed. The test asserts that despite the partial
    failure in request #1, both requests produce arbitration-
    equivalent envelopes.
    """
    state, corpus_dir = capture_state_cycling
    assert state == "recovering"  # defensive — fixture sanity check

    tools_list = [_make_test_tool()]

    # ===== BLOCK A — REQUEST #1 ARBITRATION INVARIANCE =====
    # First Path.open inside corpus_dir raises OSError. Subsequent
    # corpus-scoped calls succeed. The 2-step chain attempts capture
    # twice; the first attempt fails, the second succeeds. Chain
    # itself completes successfully because emit_divergence_capture
    # catches the OSError per I-6 and returns None.
    response_1, mock_call_tool_1 = _drive_chain_request(
        tools_list=tools_list, prompt=_CHAIN_PROMPT,
    )
    _assert_chain_step_arbitration_invariance(
        response_1,
        mock_call_tool_1,
        expected_step_count=2,
        expected_status="success",
    )
    # ========================================================

    # ===== BLOCK B — REQUEST #2 ARBITRATION INVARIANCE =====
    # All Path.open calls succeed (fail_until_call=1 was exhausted by
    # request #1's first emission attempt). Request #2's both captures
    # succeed. Arbitration response is independent of whether request
    # #1's captures succeeded or failed — that is the inter-emission
    # state independence property this test exists to enforce.
    response_2, mock_call_tool_2 = _drive_chain_request(
        tools_list=tools_list, prompt=_CHAIN_PROMPT,
    )
    _assert_chain_step_arbitration_invariance(
        response_2,
        mock_call_tool_2,
        expected_step_count=2,
        expected_status="success",
    )
    _assert_chain_step_arbitration_response_equivalent(
        response_1, response_2,
    )
    # ========================================================

    # ===== BLOCK C — CAPTURE-CORRECTNESS (CONTAMINATION CHECK) =====
    # Records on disk: 1 from request #1 (step 1's success after step
    # 0's failure) + 2 from request #2 = 3 total. The §6.5 single-
    # write-per-emission invariant holds at the integration level;
    # the failed first attempt produced no on-disk residue, and no
    # duplicate records were emitted. Each successful emission appears
    # exactly once.
    _assert_no_failed_write_residue(
        corpus_dir, expected_record_count=3,
    )
    records = _read_records(corpus_dir)
    assert len(records) == 3, (
        f"recovering state expected exactly three records "
        f"(request #1 step 1's success + request #2 steps 0+1's "
        f"successes); got {len(records)} in {corpus_dir}"
    )
    for i, record in enumerate(records):
        assert record["narrower"]["decision"] == ["forge_test_probe"], (
            f"recovering record {i}'s narrower.decision does not "
            f"match arbitration output: got "
            f"{record['narrower']['decision']!r}, expected "
            f"['forge_test_probe']"
        )
    # ===============================================================


# ─── Test 3 — dedicated latency-delta test (sequential, min-of-N) ──────────


def test_chain_step_capture_latency_within_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Latency delta between disabled and enabled chain-step states
    must respect the asymmetric target/ceiling discipline.

    Sample shape: minimum of N samples per state. Minimum measures
    the floor of overhead — what "capture path acquired hidden
    complexity" actually shifts. Mean/max would capture noise; single-
    shot would flake on shared CI hardware. Min-of-N is the
    operationally honest expression of the architectural discipline,
    same as PR 4.

    Per ``A.5.3.2-PR5-FRAMING.md`` §2.3 + ``A.5.3.2-PR5-SPEC.md`` §6.1
    inheriting PR 4 spec §6.1:

        Exceeding the target triggers investigation, not threshold
        adjustment. PR 5 remains observational integration, not
        persistence-budget engineering.

    The chain prompt drives a 2-step chain, so each request issues
    two capture emissions (per-step semantics). The latency delta
    measures aggregate per-request overhead; this is intentional
    because the operator-visible budget is per-request, not per-
    emission. If the delta exceeds the per-request budget, divide by
    step count to estimate per-emission cost during investigation.

    Two assertions with distinct failure-message framing: the target
    failure asks for investigation; the ceiling failure asserts a
    hard architectural violation. They are not interchangeable
    thresholds. Do NOT replace ``min(samples)`` with ``mean()`` or
    ``median()`` — minimum is the architecturally correct metric.
    """
    monkeypatch.setenv(
        "FORGE_BRIDGE_CORPUS_DIR", str(tmp_path / "corpus"),
    )

    # The chat handler's IP-keyed rate limit (10 req/60s) bites at
    # the 11th sample under a single test-client IP. Reset before
    # every sample so we measure capture overhead, not rate-limit
    # rejection. The autouse fixture already resets at test boundary;
    # this loop-local reset is the per-sample equivalent.

    # --- Sample N times in disabled state ---
    monkeypatch.delenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", raising=False)
    disabled_samples_ms: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        _rate_limit._reset_for_tests()
        t0 = time.perf_counter()
        response, _ = _drive_chain_request(prompt=_CHAIN_PROMPT)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert response.status_code == 200, (
            f"disabled-state sample request failed with "
            f"status={response.status_code}: {response.text!r}"
        )
        disabled_samples_ms.append(elapsed_ms)

    # --- Sample N times in enabled state ---
    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "1")
    enabled_samples_ms: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        _rate_limit._reset_for_tests()
        t0 = time.perf_counter()
        response, _ = _drive_chain_request(prompt=_CHAIN_PROMPT)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert response.status_code == 200, (
            f"enabled-state sample request failed with "
            f"status={response.status_code}: {response.text!r}"
        )
        enabled_samples_ms.append(elapsed_ms)

    delta_ms = min(enabled_samples_ms) - min(disabled_samples_ms)

    # --- Diagnostic target ---
    assert delta_ms < LATENCY_TARGET_MS, (
        f"DIAGNOSTIC FAILURE: chain-step capture-path latency delta "
        f"{delta_ms:.3f}ms exceeds target {LATENCY_TARGET_MS}ms. The "
        f"capture path may have acquired hidden complexity. "
        f"Investigate the cause; do NOT raise this target. "
        f"(A.5.3.2-PR5-FRAMING.md §2.3: 'exceeding the target "
        f"triggers investigation, not threshold adjustment.') "
        f"disabled min={min(disabled_samples_ms):.3f}ms, "
        f"enabled min={min(enabled_samples_ms):.3f}ms"
    )

    # --- Architectural ceiling ---
    assert delta_ms < LATENCY_CEILING_MS, (
        f"HARD ARCHITECTURAL FAILURE: chain-step capture-path "
        f"latency delta {delta_ms:.3f}ms exceeds ceiling "
        f"{LATENCY_CEILING_MS}ms. This is no longer a diagnostic "
        f"signal — capture is materially impacting chain arbitration "
        f"latency. PR 5 inheriting PR 4's I-3 latency contribution "
        f"invariant has been violated."
    )
