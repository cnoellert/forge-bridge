"""PR 4 step 7 — chat-handler integration tests.

Carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR4-FRAMING.md`` §0/§3 + ``A.5.3.2-PR4-SPEC.md`` §0):

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

This module ships three test functions exercising the four
hostile-environment probes from ``A.5.3.2-PR4-FRAMING.md`` §1.2:

  - ``test_chat_handler_arbitration_invariant_under_capture_state``
    — parametrized over ``["disabled", "enabled", "failing"]``
    (single-invocation, two-block geometry).

  - ``test_chat_handler_arbitration_invariant_under_capture_state_recovering``
    — dedicated function, three-block geometry, two arbitration
    invocations. Visibly heavier than the other states because it
    is architecturally heavier (temporal contamination probe). The
    visible duplication of request #1 / request #2 carries semantic
    weight: do NOT collapse via abstracted helpers.

  - ``test_chat_handler_capture_latency_delta_bounded`` — dedicated,
    sequential disabled→enabled, min-of-N sample with asymmetric
    target/ceiling discipline.

Two-block geometry (parametrized): ARBITRATION-INVARIANCE block
first, CAPTURE-CORRECTNESS block second, never interleaved. A
reviewer can verify §1.2 by reading only the first block.

Three-block geometry (recovering): BLOCK A (request #1 invariance)
→ BLOCK B (request #2 invariance + cross-state response equivalence)
→ BLOCK C (capture-correctness contamination check). The geometry
mirrors the runtime asymmetry; preserve it.

Self-contained test machinery — no imports from ``tests.console.*``.
This is a binding constraint per Chris convergence directive: future
``tests/console/conftest.py`` refactors must NOT silently weaken
§1.2's arbitration-invariance guard.

Verification-layer vocabulary the room now treats as methodology:

  - Architectural property: what invariant matters.
  - Operational expression: today's observable manifestation.
  - Verification mechanism: the assertion / helper enforcing it.
  - Bite-verification mutation: the empirical scratch proving the
    assertion would fire.

Bite-verification scratch design lives at incarnation, not at
topology. If a particular contamination vector proves to bite
weakly, the correct response is to adjust the scratch surgically —
not to reopen the assertion helper or recovering geometry.
"""
from __future__ import annotations

import pathlib
import time
from pathlib import Path
from typing import Iterator

import pytest

# jinja2 is a declared chat-handler dependency (pyproject.toml).
# Skip where absent rather than fail loudly: a test that drives a
# chat request cannot meaningfully execute when the SUT itself
# cannot construct. The skip is operationally honest, not a
# property weakening — the §1.2 arbitration-invariance invariant is
# enforced wherever the chat handler can run at all.
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
    _assert_arbitration_invariance,
    _assert_arbitration_response_equivalent,
    _assert_authority_surface_invariance,
    _assert_no_failed_write_residue,
    _drive_chat_request,
    _make_test_tool,
    _read_records,
    _scoped_failing_open,
    capture_state_cycling,  # re-exported for parametrize indirect=True
)


# Asymmetric latency budget per A.5.3.2-PR4-SPEC.md §6.1:
#
#   target = diagnostic. Exceeded → investigate; do NOT raise.
#   ceiling = architectural. Exceeded → hard fail.
#
# "Exceeding the target triggers investigation, not threshold
#  adjustment." (Spec §6.1.) The values are not interchangeable
# thresholds; they encode a non-flat budget posture.
LATENCY_TARGET_MS = 5.0
LATENCY_CEILING_MS = 20.0

# Deliberately modest: we are estimating overhead floor, not
# building a statistically rigorous latency profile. Increasing
# N primarily increases CI runtime after the floor stabilizes.
LATENCY_SAMPLES = 10


@pytest.fixture(autouse=True)
def _reset_rate_limit_autouse() -> Iterator[None]:
    """Per-test rate-limit isolation. Required for every test in
    this file because each test drives one or more chat requests
    against the IP-keyed token bucket. Autouse rather than
    explicit-request because every test needs it; making it
    explicit would be visual noise without semantic value.
    """
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


# ─── Test 1 — 3-state parametrized arbitration invariance ──────────────────


@pytest.mark.parametrize(
    "capture_state_cycling",
    ["disabled", "enabled", "failing"],
    indirect=True,
)
def test_chat_handler_arbitration_invariant_under_capture_state(
    capture_state_cycling: tuple[CaptureState, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Arbitration invariance under disabled / enabled / failing
    capture states. Two-block geometry — invariance first,
    capture-correctness second.

    Per ``A.5.3.2-PR4-FRAMING.md`` §1.2, this is PR 4's single most
    important invariant. The block separation is reviewer-visible
    discipline: the first block reads identically across all three
    parametrized states; the second block is state-specific.
    """
    state, corpus_dir = capture_state_cycling

    # Shared setup — held outside both blocks so the source-list
    # reference is reachable for the enabled-state authority-surface
    # probe.
    expected_tool_names = ["forge_test_probe"]
    tools_list = [_make_test_tool()]

    # ===== ARBITRATION-INVARIANCE BLOCK (identical across states) =====
    response, mock_router = _drive_chat_request(tools_list=tools_list)
    _assert_arbitration_invariance(
        response,
        mock_router,
        expected_tool_names=expected_tool_names,
    )
    # ==================================================================

    # ===== CAPTURE-CORRECTNESS BLOCK (state-specific) =================
    if state == "disabled":
        # Pre-PR-4 baseline: no records, no warnings.
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=0,
        )
        # Defensive: corpus_dir should not even exist (gate
        # short-circuits before any directory access).
        if corpus_dir.exists():
            assert not list(corpus_dir.iterdir()), (
                f"disabled state produced filesystem activity in "
                f"{corpus_dir}: {list(corpus_dir.iterdir())!r}. The "
                f"divergence_capture_enabled() gate should have "
                f"short-circuited."
            )

    elif state == "enabled":
        # Exactly one record; record's narrower decision matches
        # arbitration output; record's snapshot identity matches the
        # producer-surface tool list.
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=1,
        )
        records = _read_records(corpus_dir)
        assert len(records) == 1, (
            f"enabled state expected exactly one record; got "
            f"{len(records)} in {corpus_dir}"
        )
        record = records[0]

        assert record["narrower"]["decision"] == expected_tool_names, (
            f"narrower.decision in record does not match arbitration "
            f"output: got {record['narrower']['decision']!r}, expected "
            f"{expected_tool_names!r}"
        )

        # PRIMARY bite — authority-surface invariance probe.
        # See ``_assert_authority_surface_invariance`` docstring for
        # the architectural property + bite-verification rationale.
        _assert_authority_surface_invariance(
            corpus_dir=corpus_dir,
            source_tools_list=tools_list,
            expected_pre_mutation_hash=(
                record["identity"]["registered_tools_snapshot_hash"]
            ),
        )

    elif state == "failing":
        # I-6 failure-invisibility at integration level: zero records
        # on disk, one WARNING logged matching the PR 3 failure-
        # invisibility log shape, response envelope arbitration-
        # equivalent to disabled (already checked by the invariance
        # block above).
        _assert_no_failed_write_residue(
            corpus_dir, expected_record_count=0,
        )
        warnings = [
            r for r in caplog.records
            if r.levelname == "WARNING"
            and "capture write failed" in r.getMessage().lower()
        ]
        assert len(warnings) == 1, (
            f"failing state expected exactly one 'capture write "
            f"failed' WARNING; got {len(warnings)}: "
            f"{[r.getMessage() for r in warnings]!r}"
        )
    # ==================================================================


# ─── Test 2 — dedicated recovering test (three-block geometry) ─────────────


@pytest.mark.parametrize(
    "capture_state_cycling",
    ["recovering"],
    indirect=True,
)
def test_chat_handler_arbitration_invariant_under_capture_state_recovering(
    capture_state_cycling: tuple[CaptureState, Path],
) -> None:
    """Recovering state — visibly heavier than the other states
    because it is architecturally heavier. Probes inter-emission
    state independence: prior failure must not poison later
    arbitration.

    Visible duplication between request #1 and request #2 is
    intentional. It carries the semantic weight that the recovering
    probe is two independent arbitration acts, not one arbitration
    with retry. Do NOT collapse into helpers that abstract the
    duplication away — the visual roughness is the protection.

    The fixture is parametrized with ``["recovering"]`` indirect so
    the canonical hostile-state definition lives in
    ``capture_state_cycling`` rather than being re-derived inline.
    Ownership boundary lives at the fixture; geometry lives here.
    """
    state, corpus_dir = capture_state_cycling
    assert state == "recovering"  # defensive — fixture sanity check

    expected_tool_names = ["forge_test_probe"]

    # ===== BLOCK A — REQUEST #1 ARBITRATION INVARIANCE =====
    # First Path.open inside corpus_dir raises OSError (per fixture's
    # fail_until_call=1). Expected behavior: emit_divergence_capture
    # catches the OSError per I-6, logs WARNING, returns None. Chat
    # handler proceeds to LLM-loop → arbitration response succeeds.
    tools_list_1 = [_make_test_tool()]
    response_1, mock_router_1 = _drive_chat_request(tools_list=tools_list_1)
    _assert_arbitration_invariance(
        response_1,
        mock_router_1,
        expected_tool_names=expected_tool_names,
    )
    # ========================================================

    # ===== BLOCK B — REQUEST #2 ARBITRATION INVARIANCE =====
    # Second Path.open succeeds (fail_until_call=1 exhausted). Expected
    # behavior: emit_divergence_capture writes the record. Arbitration
    # response is independent of whether request #1 succeeded or
    # failed — that is the inter-emission state independence property
    # this test exists to enforce.
    tools_list_2 = [_make_test_tool()]
    response_2, mock_router_2 = _drive_chat_request(tools_list=tools_list_2)
    _assert_arbitration_invariance(
        response_2,
        mock_router_2,
        expected_tool_names=expected_tool_names,
    )
    _assert_arbitration_response_equivalent(response_1, response_2)
    # ========================================================

    # ===== BLOCK C — CAPTURE-CORRECTNESS (CONTAMINATION CHECK) =====
    # Exactly one record on disk (request #2's success). Failed first
    # attempt produced no on-disk residue. The §6.5 single-write-per-
    # emission invariant holds at the integration level: no orphan
    # state, no duplicate records, no partial writes.
    _assert_no_failed_write_residue(corpus_dir, expected_record_count=1)
    records = _read_records(corpus_dir)
    assert len(records) == 1, (
        f"recovering state expected exactly one record (request #2's "
        f"success); got {len(records)} in {corpus_dir}"
    )
    assert records[0]["narrower"]["decision"] == expected_tool_names, (
        f"recovering record's narrower.decision does not match "
        f"arbitration output: got "
        f"{records[0]['narrower']['decision']!r}, expected "
        f"{expected_tool_names!r}"
    )
    # ===============================================================


# ─── Test 3 — dedicated latency-delta test (sequential, min-of-N) ──────────


def test_chat_handler_capture_latency_delta_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Latency delta between disabled and enabled states must respect
    the asymmetric target/ceiling discipline.

    Sample shape: minimum of N samples per state. Minimum measures
    the floor of overhead — what "capture path acquired hidden
    complexity" actually shifts. Mean/max would capture noise (GC,
    OS scheduling) rather than signal. Single-shot would flake on
    shared CI hardware; min-of-N is the operationally honest
    expression of the architectural discipline.

    Per ``A.5.3.2-PR4-SPEC.md`` §6.1:

        Exceeding the target triggers investigation, not threshold
        adjustment. PR 4 remains observational append-only
        integration, not persistence-budget engineering. Unexpected
        latency growth is suspicious, diagnostically important, and
        architecturally meaningful — not merely "within budget."

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
    # this loop-local reset is the per-sample equivalent — keeps the
    # two-batch loop measuring what it claims to measure.

    # --- Sample N times in disabled state ---
    monkeypatch.delenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", raising=False)
    disabled_samples_ms: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        _rate_limit._reset_for_tests()
        t0 = time.perf_counter()
        response, _ = _drive_chat_request()
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
        response, _ = _drive_chat_request()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert response.status_code == 200, (
            f"enabled-state sample request failed with "
            f"status={response.status_code}: {response.text!r}"
        )
        enabled_samples_ms.append(elapsed_ms)

    delta_ms = min(enabled_samples_ms) - min(disabled_samples_ms)

    # --- Diagnostic target ---
    assert delta_ms < LATENCY_TARGET_MS, (
        f"DIAGNOSTIC FAILURE: capture-path latency delta "
        f"{delta_ms:.3f}ms exceeds target {LATENCY_TARGET_MS}ms. "
        f"The capture path may have acquired hidden complexity. "
        f"Investigate the cause; do NOT raise this target. "
        f"(A.5.3.2-PR4-SPEC.md §6.1: 'exceeding the target triggers "
        f"investigation, not threshold adjustment.') "
        f"disabled min={min(disabled_samples_ms):.3f}ms, "
        f"enabled min={min(enabled_samples_ms):.3f}ms"
    )

    # --- Architectural ceiling ---
    assert delta_ms < LATENCY_CEILING_MS, (
        f"HARD ARCHITECTURAL FAILURE: capture-path latency delta "
        f"{delta_ms:.3f}ms exceeds ceiling {LATENCY_CEILING_MS}ms. "
        f"This is no longer a diagnostic signal — capture is "
        f"materially impacting arbitration latency. PR 4's I-3 "
        f"latency contribution invariant has been violated."
    )
