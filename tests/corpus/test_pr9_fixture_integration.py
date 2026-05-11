"""PR 9 end-to-end integration tests — fixture corpus consumption
through the real chat_handler arbitration surface.

This module houses the three end-to-end integration tests
(architectural-center #1 per ``A.5.3.2-PR9-SPEC.md`` §6 Step 3):

  - ``test_fixture_runs_end_to_end_single_survivor``
  - ``test_fixture_runs_end_to_end_multi_match``
  - ``test_fixture_runs_end_to_end_no_keyword_match``

Each test independently drives one fixture through the REAL
``chat_handler`` arbitration pipeline (PR14 keyword filter +
PR21 deterministic narrow + emission) and asserts the
expectation + observation records persist with the grounded
shape recorded at Step 2 commit ``50a7caf``.

Step 4 (separate commit) adds the two Gate 4 unblock proof
tests:

  - ``test_observation_and_expectation_distinguishable_by_record_kind``
  - ``test_records_join_on_fixture_id``

Test count per A.5.3.2-PR9-SPEC.md §5.1: 5 integration + 2
discipline = 7 named tests; 207 forge env collected target at
PR 9 close (200 baseline + 7 new; named == collected; no
parametrize per framing Q3).

METHODOLOGY — MOCKING VS. CONSTRAINING ARBITRATION SURFACE
==========================================================

Per ``A.5.3.2-PR9-SPEC.md`` §4.5 + §4.7 amendment 2026-05-11
+ Step 2 commit body: the integration tests use
``monkeypatch.setattr`` to constrain reachable-tool topology
WITHOUT mocking ``chat_handler`` itself. The real chat_handler
arbitration pipeline (PR14 + PR21 + emission) runs unmodified
against the controlled tool set.

The patching strategy (this module's structural commitment):

  1. ``_PR9_REACHABLE_TOOLS`` — module-scope constant declaring
     the 4-tool controlled reachable set. Lives HERE, not in
     conftest.py, per Step 3 guidance: the controlled set is
     module-local arbitration grounding, NOT reusable suite
     infrastructure.
  2. ``_build_app_with_console_state`` — helper that constructs
     a stub Starlette ``app`` namespace carrying
     ``app.state.console_read_api._llm_router`` (the chat_handler
     prerequisite). The stub LLM router's ``complete_with_tools``
     returns a benign response — chat_handler reaches LLM
     dispatch only AFTER emission has already fired.
  3. ``_patched_invoke_chat_handler_in_process`` (factory
     produces a per-test version) — replaces
     ``forge_bridge.corpus._seed._invoke_chat_handler_in_process``
     in the CONSUMER namespace (matching PR 8's patching
     pattern at ``test_pr8_seed_surface.py:683``). The
     replacement builds the same minimal Starlette Request that
     ``_seed.py`` builds, PLUS injects ``scope["app"]`` with the
     stub app state. The replacement THEN invokes the REAL
     ``chat_handler`` — preserving the arbitration surface.
  4. Per-test ``monkeypatch.setattr`` on
     ``forge_bridge.mcp.server.mcp.list_tools`` and
     ``forge_bridge.console.handlers.filter_tools_by_reachable_backends``
     — returns the controlled set + passthrough respectively.
     Bypasses host-environment reachability dependence (the
     daemon's backends report ``available=False`` on dev hosts
     without Flame instances reachable).

Why NOT mock chat_handler itself:

  - Mocking chat_handler would collapse the arbitration surface
    under test. The integration tests exist to assert what the
    real chat-handler arbitration produced; mocking it defeats
    that purpose.
  - PR 8 tests mocked chat_handler with ``benign_chat_handler``
    because PR 8 was UNIT-scoped (driver invocation contract
    only; not arbitration outcome). PR 9 is INTEGRATION-scoped;
    chat_handler must run unmocked.
  - The user redline at amendment convergence (2026-05-11) was
    explicit: "Do NOT mock chat_handler itself." Constraining
    reachable-tool topology preserves the arbitration surface
    while removing host-environment nondeterminism.

ORDERING SEMANTICS — LIST EQUALITY, NOT SET EQUALITY
=====================================================

Per carrier #10's "narrower_decision carries the filtered list
verbatim at narrowing finalization" language + Step 3 guidance
item 4: PR 9 e2e test assertions use **list equality**, NOT
set equality. Tool ordering in ``narrower.decision`` is
semantic — Gate 4 comparator semantics will depend on whether
ordering is signal or incidental; PR 9 commits to "ordering is
signal" per carrier #10's "verbatim" language.

Specifically:

  - Test 2 (multi-match) asserts
    ``observation["narrower"]["decision"] == ["forge_list_projects",
    "flame_list_libraries"]`` — PR14 input order preserved
    through PR21 (PR21 made no reduction so input order survives).
  - Test 3 (no-keyword-match) asserts
    ``observation["narrower"]["decision"] == [t.name for t in
    _PR9_REACHABLE_TOOLS]`` — PR14 fallback returns
    ``list(tools)`` verbatim per ``_tool_filter.py:320–321``.

If a future PR proposes set-equality assertion (sort-then-
compare) without amending carrier #10's "verbatim" language at
the framing/spec layer, the proposal is rejected at the spec
layer per ``A.5.3.2-PR9-SPEC.md`` §7 + this module's commit
archaeology.

NESTED RECORD-FIELD PATH (grounding-time discovery at Step 3)
==============================================================

The observation record's narrowing decision is stored at
``observation["narrower"]["decision"]`` (nested), NOT at
``observation["narrower_decision"]`` (top-level). Spec §4.5
test bodies originally extrapolated the top-level path; Step
3 implementation surfaced the nested path empirically. The
spec §4.5 test bodies in the implementation contract reflect
the corrected path per Step 3 commit body archaeology.

Companion fields on the observation record:

  - ``observation["narrower"]["decision"]`` — list[str]; tool
    names in PR14 + PR21 output order.
  - ``observation["narrower"]["pr20_condition_met"]`` — bool;
    True iff ``tools_filtered_count == 1`` AND
    ``tools_filtered_count < tools_available_count``.
  - ``observation["narrower"]["collapse_occurred"]`` — bool;
    True iff ``tools_filtered_count == 1`` AND
    ``len(tools_post_pr14) > 1`` (multi-to-single transition).
  - ``observation["narrower"]["ambiguity_state"]`` — str;
    one of "single_survivor" / "multi_survivor" / etc.

Carriers carried by reference from
``forge_bridge/corpus/_seed.py`` (canonical verbatim source):

  - #1–#2 risk-category shift (PR 4).
  - #3–#6 integration-discipline quartet (PR 4).
  - #7 finalized-state contract (PR 4).
  - #8 risk-inheritance + surface-geometry distinction (PR 5).
  - #9 caller's view of deployment identity (PR 5).
  - #10 ambiguity-as-arbitration-outcome (PR 5).
  - #11 measured-not-inferred coverage (PR 5).
  - #12 structural-backstop framing (PR 6).
  - #13 observation-not-participation framing (PR 6).
  - #14 declared epistemic class vs. persisted provenance
    (Gate 2).
  - #15 chat-handler-only seeding scope (PR 8) — most-relevant
    inherited governance for PR 9 integration tests per
    relevance-by-file ordering.
  - Binding framing clarification (Gate 2) — call-site-owned
    arbitration inputs.

PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5 legacy-synthesis)
do NOT travel here. PR-8-LOCAL binding statements (member #7
truth-partitioning, member #8 semantics-not-topology) do NOT
regenerate here — scope-local to ``_seed.py`` +
``emit_seed_expectation``.

PR 9 governing sentence (framing-artifact-scoped per
``A.5.3.2-PR9-FRAMING.md`` §0):

  PR 9 proves topology, not infrastructure.

See ``A.5.3.2-PR9-SPEC.md`` §4.5 + §5.1 + §6 Step 3 for the
contract this module implements.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from typing import Any

import pytest

from forge_bridge.corpus._seed import drive_seed_fixture
from tests.corpus.fixtures.fix_single_survivor import FIXTURE as FIXTURE_SINGLE_SURVIVOR
from tests.corpus.fixtures.fix_multi_match import FIXTURE as FIXTURE_MULTI_MATCH
from tests.corpus.fixtures.fix_no_keyword_match import FIXTURE as FIXTURE_NO_KEYWORD_MATCH


# ── Controlled reachable-tool set (module-local arbitration grounding) ──────
#
# Locked at A.5.3.2-PR9-SPEC.md §4.7 amendment convergence
# (2026-05-11) per user direction. The four tools were selected
# for clean token-shape diversity:
#
#   - forge_ping            (single-token name; only "ping" tool)
#   - forge_list_projects   (multi-token forge namespace)
#   - flame_list_libraries  (multi-token flame namespace; ties
#                            with forge_list_projects on "list"
#                            token for multi-match coverage)
#   - flame_render_status   (flame namespace; no token collision
#                            on "ping" or "list")
#
# Rationale: clean topology partitioning. forge_ping is the only
# "ping" tool (single-survivor disambiguation without namespace
# artifacts); both list_* tools tie on "list" token (true
# multi-match without forced collapse); no tool's tokens overlap
# "what time is it" (clean PR14 fallback exercise).
#
# This constant lives at module scope per Step 3 guidance item 3:
# the controlled set is module-local arbitration grounding,
# NOT reusable suite infrastructure. conftest.py placement would
# incorrectly imply broader semantic scope.
_PR9_REACHABLE_TOOLS: list[Any] = [
    SimpleNamespace(name="forge_ping"),
    SimpleNamespace(name="forge_list_projects"),
    SimpleNamespace(name="flame_list_libraries"),
    SimpleNamespace(name="flame_render_status"),
]


# ── Stub LLM router (post-emission; never structurally exercised) ───────────
#
# chat_handler reaches the LLM router AFTER emit_divergence_capture
# has already fired. The stub's complete_with_tools returns a
# benign response; chat_handler's post-emission code path
# completes without raising. The records under test are persisted
# BEFORE the LLM router is consulted.


async def _benign_complete_with_tools(*args: Any, **kwargs: Any) -> Any:
    """Stub LLM completion. Returns benign response object;
    chat_handler's LLM-dispatch code path completes without
    propagating exceptions to drive_seed_fixture.
    """
    return SimpleNamespace(
        text="benign-stub-response",
        tool_calls=[],
        reasoning=None,
        usage=None,
    )


def _build_app_with_console_state() -> Any:
    """Construct a minimal Starlette-app stub carrying
    ``app.state.console_read_api._llm_router``.

    chat_handler reads ``request.app.state.console_read_api`` at
    handlers.py:347 + line 950 to access the LLM router. Without
    this attribute path resolved, chat_handler returns 500
    BEFORE reaching the narrowing pipeline + emission.

    The stub deliberately exposes ONLY the attributes chat_handler
    actually consults during the pre-emission code path
    (.state.console_read_api._llm_router and its required
    methods). The LLM router's complete_with_tools is invoked
    POST-emission; the stub's benign return ensures no exception
    propagates back through drive_seed_fixture.
    """
    llm_router = SimpleNamespace(
        complete_with_tools=_benign_complete_with_tools,
        system_prompt="pr9-stub-system-prompt",
        model="pr9-stub-model",
        base_url=None,
        api_key=None,
    )
    console_read_api = SimpleNamespace(_llm_router=llm_router)
    return SimpleNamespace(
        state=SimpleNamespace(console_read_api=console_read_api),
    )


def _make_patched_invoke():
    """Factory producing a per-test replacement for
    ``forge_bridge.corpus._seed._invoke_chat_handler_in_process``.

    The replacement builds the same minimal Starlette Request the
    original constructs, PLUS injects ``scope["app"]`` with the
    stub app state from ``_build_app_with_console_state``. It
    THEN invokes the REAL chat_handler from
    ``forge_bridge.console.handlers``.

    The patching pattern mirrors PR 8's
    ``test_pr8_seed_surface.py:683`` pattern: replace
    ``_invoke_chat_handler_in_process`` in the CONSUMER namespace
    (``forge_bridge.corpus._seed._invoke_chat_handler_in_process``)
    so the function-scoped import inside the original (line 377
    of _seed.py) is bypassed.

    Returns a coroutine function (matching the original's async
    signature) suitable for ``monkeypatch.setattr(...)``.
    """
    import os

    async def _invoke(prompt: str) -> None:
        # Function-scoped import — same scope discipline as the
        # original at _seed.py:377. Preserves carrier #15's
        # chat-handler-only scope at the test seam.
        from forge_bridge.console.handlers import chat_handler
        from starlette.requests import Request

        body = {"messages": [{"role": "user", "content": prompt}]}
        body_bytes = json.dumps(body).encode("utf-8")
        # Per-invocation synthetic client identity — same as
        # original at _seed.py:394 (UUID-based). Ensures the
        # rate-limit pre-gate sees a fresh client per test
        # invocation; the clean_rate_limit_state fixture
        # additionally grounds the rate-limit cache.
        synthetic_client = (f"pr9-test-{os.urandom(4).hex()}", 0)
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/chat",
            "raw_path": b"/api/v1/chat",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": synthetic_client,
            "server": ("pr9-test", 0),
            "scheme": "http",
            "http_version": "1.1",
            # ── Test-only addition: inject app state ────────────
            # chat_handler reads request.app.state.console_read_api
            # at handlers.py:347 + line 950. The original
            # _invoke_chat_handler_in_process omits scope["app"]
            # because PR 8 tests mocked chat_handler entirely.
            # PR 9 runs the REAL chat_handler; the injected app
            # is the minimum needed to reach the emission line.
            "app": _build_app_with_console_state(),
        }
        request = Request(scope)
        request._body = body_bytes  # type: ignore[attr-defined]
        # chat_handler returns a JSONResponse on errors; never
        # raises unhandled exceptions. The seed driver does not
        # consume chat_handler's output — only the emission
        # side-effect (which fires inside chat_handler before
        # the response is built).
        await chat_handler(request)

    return _invoke


def _read_records(corpus_dir: pathlib.Path) -> list[dict]:
    """Read every record across every ``capture-*.jsonl`` file in
    ``corpus_dir``. Returns records in (file, line) order.

    Skips header lines. Returns ``[]`` if ``corpus_dir`` does not
    exist or contains no capture files. Mirrors the pattern at
    ``tests/corpus/_pr4_helpers.py::_read_records``.
    """
    if not corpus_dir.exists():
        return []

    records: list[dict] = []
    for path in sorted(corpus_dir.glob("capture-*.jsonl")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("_header") is True:
                continue
            records.append(obj)
    return records


def _apply_pr9_patches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> pathlib.Path:
    """Apply the standard PR 9 integration-test monkeypatch suite.

    Returns the isolated corpus directory path.

    Patches applied:

      1. ``FORGE_BRIDGE_CORPUS_DIR`` env var → tmp_path/corpus.
      2. ``FORGE_BRIDGE_DIVERGENCE_CAPTURE`` env var → "1".
      3. ``forge_bridge.corpus._seed._invoke_chat_handler_in_process``
         → patched version with injected app state (CONSUMER
         namespace; mirrors PR 8 pattern).
      4. ``forge_bridge.mcp.server.mcp.list_tools`` →
         coroutine returning ``_PR9_REACHABLE_TOOLS``.
      5. ``forge_bridge.console.handlers.filter_tools_by_reachable_backends``
         → passthrough (returns input unchanged).

    The patches in aggregate preserve the REAL chat_handler
    arbitration surface (PR14 + PR21 + emission) while removing
    host-environment reachability variance + the LLM-dispatch
    post-emission complexity.
    """
    corpus_dir = tmp_path / "corpus"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(corpus_dir))
    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "1")

    # Patch _invoke_chat_handler_in_process in CONSUMER namespace
    # (forge_bridge.corpus._seed) — drive_seed_fixture's
    # asyncio.run targets this name.
    monkeypatch.setattr(
        "forge_bridge.corpus._seed._invoke_chat_handler_in_process",
        _make_patched_invoke(),
    )

    # Patch MCP server's list_tools to return controlled set.
    # chat_handler imports _mcp_server inside the handler body
    # (handlers.py:965); the monkeypatch must target the actual
    # attribute on the imported module.
    from forge_bridge.mcp import server as _mcp_server

    async def _list_controlled(*args: Any, **kwargs: Any) -> list[Any]:
        return _PR9_REACHABLE_TOOLS

    monkeypatch.setattr(_mcp_server.mcp, "list_tools", _list_controlled)

    # Patch filter_tools_by_reachable_backends to passthrough.
    # The chat_handler imports the symbol at module load
    # (handlers.py:61); patching CONSUMER namespace
    # (forge_bridge.console.handlers.filter_tools_by_reachable_backends)
    # intercepts the lookup.
    async def _passthrough_reachable(tools: list[Any]) -> list[Any]:
        return list(tools)

    monkeypatch.setattr(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        _passthrough_reachable,
    )

    return corpus_dir


# ─── Integration tests — PR 9 Step 3 ────────────────────────────────────────


def test_fixture_runs_end_to_end_single_survivor(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Single-survivor e2e: drive fixture → assert two records persist
    with grounded arbitration shape.

    Per A.5.3.2-PR9-SPEC.md §4.5 + §5.1 risk #1: drives the
    fixture ``fix-pr9-single-survivor`` (prompt "ping forge")
    through the real chat_handler arbitration pipeline against
    the controlled reachable-tool set. PR14 keyword filter
    yields 2 candidates (forge_ping, forge_list_projects); PR21
    deterministic_narrow collapses to 1 (forge_ping; max-overlap
    = 2 tokens vs. 1). Observation record reflects PR20
    short-circuit semantics: pr20_condition_met=True (single
    survivor AND filtered < available); collapse_occurred=True
    (multi-to-single transition).
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for fix-pr9-single-survivor; got {len(matching)}.\n"
        f"All records: {records}"
    )

    record_kinds = {r["record_kind"] for r in matching}
    assert record_kinds == {"observation", "expectation"}, (
        f"Expected record_kinds={{observation, expectation}}; got {record_kinds}"
    )

    expectation = next(r for r in matching if r["record_kind"] == "expectation")
    observation = next(r for r in matching if r["record_kind"] == "observation")

    # Expectation record assertions
    assert expectation["prompt"] == FIXTURE_SINGLE_SURVIVOR["prompt"]
    assert expectation["expected_narrow"] == FIXTURE_SINGLE_SURVIVOR["expected_narrow"]
    assert "source" not in expectation, (
        "expectation must not carry source field (member #7 truth-partitioning protection)"
    )

    # Observation record assertions
    assert observation["source"] == "seed", (
        "observation must carry source='seed' under driver scope (seed_dispatch_scope)"
    )
    # narrower.decision (nested path; grounded at Step 3 spike)
    assert observation["narrower"]["decision"] == FIXTURE_SINGLE_SURVIVOR["expected_narrow"], (
        f"narrower.decision mismatch.\n"
        f"Expected: {FIXTURE_SINGLE_SURVIVOR['expected_narrow']}\n"
        f"Observed: {observation['narrower']['decision']}\n"
    )
    # PR20 short-circuit fired for single-survivor + collapse
    # from PR14's 2-candidate output.
    assert observation["narrower"]["pr20_condition_met"] is True
    assert observation["narrower"]["collapse_occurred"] is True


def test_fixture_runs_end_to_end_multi_match(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Multi-match e2e: drive fixture → assert ambiguity-rejection
    observation per carrier #10 (filtered list verbatim, no collapse).

    Per A.5.3.2-PR9-SPEC.md §4.5 + §5.1 risk #2: drives the
    fixture ``fix-pr9-multi-match`` (prompt "list") through the
    real chat_handler arbitration pipeline. PR14 keyword filter
    yields 2 candidates (both list_* tools); PR21 cannot
    collapse (tie at max-overlap=1; no domain-priority pair).
    Observation record reflects carrier #10 multi-match
    rejection-path semantics: pr20_condition_met=False;
    collapse_occurred=False; narrower.decision carries the
    filtered list verbatim (list equality per Step 3 guidance
    item 4 + carrier #10's "verbatim" language).
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    drive_seed_fixture(**FIXTURE_MULTI_MATCH)

    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-multi-match"]
    assert len(matching) == 2

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    # Carrier #10 enforcement at multi-match — list equality
    # (ordering is semantic per carrier #10's "filtered list
    # verbatim" language). Step 3 guidance item 4 rejects
    # set-equality semantics.
    assert observation["narrower"]["decision"] == FIXTURE_MULTI_MATCH["expected_narrow"], (
        f"narrower.decision mismatch (list equality required per carrier #10).\n"
        f"Expected: {FIXTURE_MULTI_MATCH['expected_narrow']}\n"
        f"Observed: {observation['narrower']['decision']}\n"
    )
    assert observation["narrower"]["pr20_condition_met"] is False, (
        "multi-match must NOT trigger PR20 short-circuit (count > 1)"
    )
    assert observation["narrower"]["collapse_occurred"] is False, (
        "multi-match must NOT exhibit collapse (no multi-to-single transition)"
    )
    assert len(observation["narrower"]["decision"]) >= 2, (
        "multi-match fixture must yield ≥2 tool names from narrowing"
    )

    # Expectation matches observation verbatim (intentional —
    # this fixture's expected_narrow declares arbitration's
    # actual outcome; Gate 4 comparator will detect zero
    # divergence on this fixture).
    assert expectation["expected_narrow"] == observation["narrower"]["decision"], (
        "multi-match fixture's expectation should match observation verbatim"
    )


def test_fixture_runs_end_to_end_no_keyword_match(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """No-keyword-match e2e: drive fixture → assert PR14
    full-capability-fallback observation + intentional
    authored/observed divergence.

    Per A.5.3.2-PR9-SPEC.md §4.4 + §4.5 + §4.7 amendment
    2026-05-11 + §5.1 risk #3: drives the fixture
    ``fix-pr9-no-keyword-match`` (prompt "what time is it")
    through the real chat_handler arbitration pipeline. PR14
    keyword filter returns the FULL controlled reachable set
    verbatim per the "no capability loss" fallback
    (_tool_filter.py:320-321) — zero keywords match. PR21
    deterministic_narrow does not reduce (max-overlap = 0; "no
    signal, leave the candidate set untouched"). Observation
    record reflects: pr20_condition_met=False (count > 1);
    collapse_occurred=False (tools_post_pr14 == tools); and
    narrower.decision carries the full reachable set verbatim.

    The authored/observed divergence framing per
    fix_no_keyword_match.py module docstring:

      The authored expectation declares expected_narrow = [].
      The observed chat-handler behavior preserves the full
      reachable tool set via PR14's "no capability loss"
      fallback. The divergence is intentional and operationally
      valuable: it proves the companion-record topology can
      represent authored expectation separately from observed
      arbitration outcome — the Gate 4 comparator-unblock
      condition this fixture exists to exercise.

    Assertion semantics: list equality on the observation
    against ``[t.name for t in _PR9_REACHABLE_TOOLS]`` (the
    declared controlled-set ordering; PR14 fallback returns
    ``list(tools)`` per _tool_filter.py:321).
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    drive_seed_fixture(**FIXTURE_NO_KEYWORD_MATCH)

    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-no-keyword-match"]
    assert len(matching) == 2

    observation = next(r for r in matching if r["record_kind"] == "observation")
    expectation = next(r for r in matching if r["record_kind"] == "expectation")

    # PR14 fallback enforcement: narrower.decision carries the
    # FULL controlled reachable set verbatim. List equality on
    # the declared ordering (PR14 fallback returns list(tools)).
    expected_full_set = [t.name for t in _PR9_REACHABLE_TOOLS]
    assert observation["narrower"]["decision"] == expected_full_set, (
        f"narrower.decision did not match the controlled reachable set verbatim.\n"
        f"Expected (controlled set, declared order): {expected_full_set}\n"
        f"Observed (narrower.decision):              {observation['narrower']['decision']}\n"
        f"\n"
        f"This fixture exercises the PR14 no-keyword-match "
        f"full-capability fallback. If observed ≠ declared "
        f"ordering, either (a) the fixture's prompt accidentally "
        f"matched a keyword (re-ground per §4.4 Step 2 "
        f"implementation note), or (b) the PR14 fallback path "
        f"regressed at _tool_filter.py:320-321."
    )

    # Carrier #10 rejection-path semantics hold even at the
    # chat-handler surface's fallback shape:
    assert observation["narrower"]["pr20_condition_met"] is False, (
        "no-keyword-match must NOT trigger PR20 short-circuit (count > 1)"
    )
    assert observation["narrower"]["collapse_occurred"] is False, (
        "no-keyword-match must NOT exhibit collapse "
        "(tools_post_pr14 == tools; no transition)"
    )

    # Authored/observed divergence — INTENTIONAL per §4.4 + §4.7.
    # The fixture-author's expected_narrow = [] expresses the
    # aspirational claim "expected zero-survivor narrowing for
    # this prompt"; observation's narrower.decision is the full
    # 4-tool set. The divergence IS the Gate 4 comparator-
    # unblock proof. Do NOT "fix" by aligning expectation with
    # observation.
    assert expectation["expected_narrow"] == [], (
        "fixture-author's aspirational claim is the empty list — "
        "'expected zero-survivor narrowing for this prompt' per "
        "emit_seed_expectation's contract. The divergence between "
        "this claim and the observation's full-list narrower.decision "
        "IS the Gate 4 comparator-unblock proof per §4.4 authored/"
        "observed divergence framing."
    )
    assert observation["narrower"]["decision"] != expectation["expected_narrow"], (
        "Observation must structurally diverge from aspirational expectation "
        "on this fixture (Gate 4 comparator-unblock proof)."
    )


# ─── Step 4 — Gate 4 unblock proof tests (architectural-center #2) ──────────


def test_observation_and_expectation_distinguishable_by_record_kind(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Gate 4 unblock proof #1: record_kind partition correctness.

    Per A.5.3.2-PR9-SPEC.md §4.5 + §5.1 risk #5: drives one
    fixture (single-survivor) and asserts the two persisted
    records have distinct ``record_kind`` values that the
    schema validator accepts. Independent of tests 1-3 —
    drives its own fixture, asserts a different property.
    Decouples the comparator's partition dependency from any
    e2e regression in tests 1-3.

    Independence is structural: a future PR could break test 1
    (e2e regression) without breaking this test, and vice
    versa. The two failure modes are orthogonal; both must pass
    for Gate 4 to remain unblocked.

    Why this is a Gate 4 unblock proof:

      Gate 4's comparator depends on ``record_kind`` discriminator
      correctness — the comparator partitions the corpus by
      record_kind ("observation" vs. "expectation") before
      joining on fixture_id. If the discriminator is not
      structurally distinct (e.g., a future PR merges the two
      record shapes; member #7 truth-partitioning violation),
      the comparator cannot be written against a stable
      foundation.

      This test asserts the partition mechanically WITHOUT
      shipping the comparator (per Gate 2 framing §11.3: "Gate 2
      ships no comparator artifact, stub or otherwise").
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2, (
        f"Expected exactly 2 records for fix-pr9-single-survivor; got {len(matching)}.\n"
        f"All records: {records}"
    )

    # Partition by record_kind:
    expectations = [r for r in matching if r["record_kind"] == "expectation"]
    observations = [r for r in matching if r["record_kind"] == "observation"]
    assert len(expectations) == 1, (
        f"exactly one expectation record per fixture invocation; got {len(expectations)}"
    )
    assert len(observations) == 1, (
        f"exactly one observation record per fixture invocation; got {len(observations)}"
    )

    # Schema validator accepts both record kinds. The expectation
    # branch validates fixture_id + prompt + expected_narrow +
    # rejects records carrying a source field (member #7
    # truth-partitioning persistence-boundary guard). The
    # observation branch validates Property C source values.
    # Both branches must accept the records this fixture
    # produces for the partition to be operationally valid.
    from forge_bridge.corpus._schema import validate_capture_record

    validate_capture_record(expectations[0])
    validate_capture_record(observations[0])

    # Mechanical assertion that the discriminator IS distinct:
    # the two record_kind values must form a 2-element set under
    # set semantics. If a future PR merges the discriminator
    # (e.g., introduces "observation_with_expectation"
    # composite), this test fails at the set-cardinality check.
    record_kinds = {r["record_kind"] for r in matching}
    assert record_kinds == {"observation", "expectation"}, (
        f"record_kind discriminator must form the 2-element set "
        f"{{'observation', 'expectation'}}; got {record_kinds}. "
        f"Member #7 truth-partitioning protection requires the "
        f"discriminator stay structurally distinct."
    )


def test_records_join_on_fixture_id(
    clean_rate_limit_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Gate 4 unblock proof #2: fixture_id joinability.

    Per A.5.3.2-PR9-SPEC.md §4.5 + §5.1 risk #6: drives one
    fixture (single-survivor) and asserts the two persisted
    records share the same fixture_id; a fixture_id-keyed join
    over the corpus reader output reunites them as a pair.
    Independent of tests 1-4 — drives its own fixture, asserts
    a different property. Decouples the comparator's join
    dependency from any partition regression in test 4.

    Independence is structural: a future PR could break test 4
    (partition regression) without breaking this test, and
    vice versa. The two Gate 4 unblock proofs are orthogonal;
    both must pass for the comparator to remain unblocked.

    Why this is a Gate 4 unblock proof:

      Gate 4's comparator's join key is fixture_id — the
      comparator pairs each observation record with the
      expectation record sharing the same fixture_id, then
      compares the pair for divergence. If the fixture_id is
      not populated identically at both persistence sites
      (emit_seed_expectation at _seed.py:296 + handlers.py
      emit_divergence_capture under seed_dispatch_scope), the
      comparator cannot pair records mechanically.

      This test asserts the join mechanically WITHOUT shipping
      the comparator (per Gate 2 framing §11.3).

    The join is built as a dict[fixture_id, dict[record_kind,
    record]] — the same shape Gate 4's comparator will consume.
    Asserting the shape now operationalizes the join
    dependency.
    """
    corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)

    drive_seed_fixture(**FIXTURE_SINGLE_SURVIVOR)

    records = _read_records(corpus_dir)
    matching = [r for r in records if r.get("fixture_id") == "fix-pr9-single-survivor"]
    assert len(matching) == 2

    # Both records share the same fixture_id mechanically. The
    # join key is the fixture_id field, populated identically at
    # expectation persistence (emit_seed_expectation at
    # _seed.py:296) and observation persistence (handlers.py
    # emit_divergence_capture under seed_dispatch_scope). If a
    # future PR decouples the two population sites, this test
    # fires.
    fixture_ids = {r["fixture_id"] for r in matching}
    assert fixture_ids == {"fix-pr9-single-survivor"}, (
        f"both records must share the same fixture_id — Gate 4 "
        f"comparator depends on this. Got: {fixture_ids}"
    )

    # Joinability proof: build a fixture_id-keyed dict over the
    # corpus reader output; verify the entry for our fixture_id
    # contains both record kinds. This mirrors the join shape
    # Gate 4's comparator will consume.
    by_fixture: dict[str, dict[str, dict]] = {}
    for r in records:
        fid = r.get("fixture_id")
        kind = r.get("record_kind")
        if fid is None or kind is None:
            continue
        by_fixture.setdefault(fid, {})[kind] = r

    paired = by_fixture.get("fix-pr9-single-survivor", {})
    assert set(paired.keys()) == {"observation", "expectation"}, (
        f"fixture_id-keyed join did not reunite the pair.\n"
        f"Expected keys: {{'observation', 'expectation'}}\n"
        f"Actual keys:   {set(paired.keys())}\n"
        f"\n"
        f"The join shape is the Gate 4 comparator's foundational "
        f"data structure. If the join cannot reunite the pair "
        f"mechanically, the comparator cannot be written against "
        f"a stable foundation."
    )

    # Additionally assert that the paired records are
    # individually well-formed (defense in depth — if the
    # corpus reader silently produced corrupt records, the join
    # could succeed with malformed payloads).
    assert paired["observation"]["fixture_id"] == "fix-pr9-single-survivor"
    assert paired["expectation"]["fixture_id"] == "fix-pr9-single-survivor"
    assert paired["observation"]["record_kind"] == "observation"
    assert paired["expectation"]["record_kind"] == "expectation"
