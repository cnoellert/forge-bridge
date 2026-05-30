"""Shared helpers for PR 4 + PR 5 tests.

Ships PR 4 infrastructure (chat-handler integration) and PR 5
extensions (chain-step integration). Per
``A.5.3.2-PR5-SPEC.md`` §6.2: extending this file in place rather
than renaming or splitting — the file's name encodes its history
(PR 4 introduction), not its ownership; both PRs share the
hostile-environment infrastructure for arbitration-invariance
testing under capture-state cycling.

PR 4 surface (chat-handler):

  - ``CaptureState`` Literal + ``capture_state_cycling`` fixture +
    narrow ``Path.open`` failure-injection helper.
  - Chat-handler construction helpers (``_make_test_tool``,
    ``_passthrough_filter``, ``_stub_chat_result``,
    ``_reset_rate_limit_fixture``).
  - ``_drive_chat_request`` — single-invocation chat driver returning
    ``(response, mock_router)``.
  - PR 4 assertion helpers — ``_assert_arbitration_invariance``,
    ``_assert_arbitration_response_equivalent``,
    ``_assert_no_failed_write_residue``,
    ``_assert_authority_surface_invariance``.

PR 5 surface (chain-step):

  - ``_stub_call_tool`` + ``_stub_resolve_required_params`` —
    chain-path stubs for ``mcp.call_tool`` and
    ``forge_bridge.console._tool_chain.resolve_required_params``.
    Default success-path returns; tests override per-scenario.
  - ``_drive_chain_request`` — multi-step chain driver. Drives a
    multi-step prompt through the chat handler (which routes to
    ``_execute_chain → run_chain_steps → execute_chain_step``).
    Returns ``(response, mock_call_tool)``.
  - PR 5 assertion helpers — ``_assert_chain_step_arbitration_invariance``
    (chain envelope shape variant) +
    ``_assert_chain_step_arbitration_response_equivalent``
    (IS-compared / IS-ignored boundary re-derived for the chain
    envelope per ``A.5.3.2-PR4-CLOSE.md`` §3.5).

Both PRs reuse ``capture_state_cycling`` unchanged. The fixture is
closed for extension at the spec layer; PR 5 must NOT add a fifth
state.

Per ``A.5.3.2-PR4-FRAMING.md`` §1.2 and ``A.5.3.2-PR4-SPEC.md`` §5,
the architectural concern PR 4 introduces (capture-call-site state
coupling — arbitration invariance under all capture states) deserves
explicit fixture vocabulary. Stretching the existing chat-handler
fixtures to absorb capture-state cycling was rejected at the spec
layer; this module is where the new vocabulary lives.

Four cycling states, each exercising a distinct property:

  - ``disabled``   : zero-capture path; pre-PR-4 baseline.
  - ``enabled``    : successful-capture happy path.
  - ``failing``    : I-6 failure-invisibility at integration level.
  - ``recovering`` : transition between failure and success;
                     no inter-call state retention.

The fixture is parametrized via ``request.param``. Tests opt in
with ``indirect=True`` parametrization on the fixture name itself
(``capture_state_cycling``), routing each parameter through the
fixture rather than passing it as a raw argument.

Adding more states (e.g., ``permission_denied``, ``partial_write``,
``disk_full``) would duplicate PR 3's I-6 unit-level coverage at
the integration level without adding new architectural invariants.
Removing any of the four loses a distinct property. The fixture
is closed for extension at the spec layer; growth requires spec
amendment.

Verification-layer vocabulary (load-bearing — keep distinct):

  - Architectural property: what invariant matters.
  - Operational expression: today's observable manifestation of
    the property.
  - Verification mechanism: the assertion / helper enforcing it.
  - Bite-verification mutation: the empirical scratch proving the
    assertion would fire.

Architectural questions are settled at topology review; bite
scratches are settled empirically during incarnation.
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable, Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


CaptureState = Literal["disabled", "enabled", "failing", "recovering"]


_ALL_STATES: tuple[CaptureState, ...] = (
    "disabled", "enabled", "failing", "recovering",
)


# ─── Path.open failure-injection helper ────────────────────────────────────


def _scoped_failing_open(
    real_open: Callable[..., object],
    corpus_dir: Path,
    fail_until_call: int | None = None,
) -> Callable[..., object]:
    """Wrap ``Path.open`` to raise ``OSError`` on calls inside the
    corpus directory and pass through every other call.

    ``fail_until_call=None``: every corpus-scoped call fails.
    ``fail_until_call=N``  : the first N corpus-scoped calls fail,
                             subsequent calls succeed. Used by the
                             ``recovering`` state to verify that no
                             inter-call state is retained between
                             writes.

    Calls outside the corpus directory (pytest internals, log files,
    user code under tmp_path siblings) MUST pass through unchanged —
    a global ``Path.open`` mock would break the test harness.

    Path-boundary check uses ``Path.is_relative_to`` rather than
    ``str.startswith`` because the latter encodes path-boundary
    semantics into string-prefix semantics, failing on sibling
    directories that share a name prefix (e.g., ``/tmp/corpus`` vs.
    ``/tmp/corpus_backup``). This helper defines what counts as
    corpus adjacency — an architectural boundary, not a convenience
    predicate.
    """
    call_count = [0]

    def wrapper(self: Path, *args: object, **kwargs: object) -> object:
        if self.is_relative_to(corpus_dir):
            call_count[0] += 1
            if fail_until_call is None or call_count[0] <= fail_until_call:
                raise OSError(
                    f"simulated capture write failure (corpus-scoped "
                    f"call #{call_count[0]})"
                )
        return real_open(self, *args, **kwargs)

    return wrapper


# ─── Capture-state-cycling fixture ─────────────────────────────────────────


@pytest.fixture
def capture_state_cycling(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[tuple[CaptureState, Path]]:
    """Configure the capture environment per the parametrized state.

    Tests that exercise arbitration invariance under capture states
    request this fixture with ``indirect=True`` parametrization::

        @pytest.mark.parametrize(
            "capture_state_cycling",
            ["disabled", "enabled", "failing"],
            indirect=True,
        )
        def test_arbitration_invariant(capture_state_cycling):
            state, corpus_dir = capture_state_cycling
            # ... drive a chat request, assert envelope equivalence ...

    Per ``A.5.3.2-PR4-FRAMING.md`` §1.2, this fixture is binding for
    every test that asserts arbitration invariance. Older
    chat-handler fixtures answer different questions; conflating them
    here would obscure which assertion is protecting which property.

    The corpus directory is always pinned to a tmp_path child, even
    in ``disabled`` state where the gate short-circuits before any
    directory access — defensive isolation against future regressions
    where something might accidentally read the corpus dir when
    disabled.

    Yields a ``(state, corpus_dir)`` tuple so tests can address the
    corpus directory directly (for residue and record-content
    assertions) without re-deriving it from ``tmp_path``.

    Fixture dependency note: relies on the production env-var read
    happening per-emission rather than at module-load. If a future PR
    moves any env-var read to module-import time, this fixture
    silently degrades — the env var would be set per-test but the
    handler would have cached the wrong value. The dependency is
    pinned here so the regression remains detectable.
    """
    state: CaptureState = request.param
    if state not in _ALL_STATES:
        raise ValueError(
            f"capture_state_cycling: unknown state {state!r}; "
            f"expected one of {list(_ALL_STATES)}"
        )

    corpus_dir = tmp_path / "corpus"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(corpus_dir))

    if state == "disabled":
        # Env var unset; gate returns False; emit_divergence_capture
        # short-circuits before touching the corpus dir.
        monkeypatch.delenv(
            "FORGE_BRIDGE_DIVERGENCE_CAPTURE", raising=False,
        )
    else:
        # All non-disabled states route through divergence_capture_enabled() == True.
        monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "1")

    if state == "failing":
        real_open = pathlib.Path.open
        monkeypatch.setattr(
            pathlib.Path,
            "open",
            _scoped_failing_open(real_open, corpus_dir),
        )
    elif state == "recovering":
        # Tests using this state must assert recovery across separate
        # arbitration invocations, not merely successive Path.open calls
        # within one invocation. The fixture mechanism is temporal
        # call-level failure transition; the spec §5.3 protected property
        # is inter-emission state independence. These coincide because
        # _capture.py makes one Path.open per emission (verified at
        # PR 4 step 4 commit time); future writer changes that break
        # this property require the fixture to be re-evaluated.
        real_open = pathlib.Path.open
        monkeypatch.setattr(
            pathlib.Path,
            "open",
            _scoped_failing_open(
                real_open, corpus_dir, fail_until_call=1,
            ),
        )

    yield (state, corpus_dir)


# ─── Chat-handler construction helpers ─────────────────────────────────────
#
# Relocated from ``test_pr4_no_dependency.py`` at PR 4 step 7 because both
# step 5 (no-dependency assertion) and step 7 (chat-handler integration
# tests) compose the same chat-handler test setup. The helpers are now
# shared PR-4 hostile-environment infrastructure, not owned by step 5.


def _make_test_tool(name: str = "forge_test_probe") -> Any:
    """Non-empty Tool so the chat handler's empty-registry guard does
    not short-circuit before we exercise the property under test.

    Default name ``forge_test_probe`` is chosen so PR14's keyword
    filter falls back to the full list (no token overlap with typical
    test prompts like ``"hi"``); ``filter_tools_by_message`` returns
    the input unchanged. Custom names are supported for tests that
    need to mutate the tool list and assert hash differences.
    """
    from mcp.types import Tool
    return Tool(
        name=name,
        description=f"Test probe {name!r} for PR 4 integration tests.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools: list[Any]) -> list[Any]:
    """Default reachability-filter stub: pass all tools through. The
    chat handler's real filter would TCP-probe :9999, which is
    unwanted in test context."""
    return tools


async def _stub_chat_result(**kwargs: Any) -> Any:
    """LLMRouter mock: returns a minimal ChatTurnResult so the chat
    handler reaches the divergence-capture call site (where step 6
    landed integration code) before constructing the response."""
    from forge_bridge.llm.router import ChatTurnResult
    return ChatTurnResult(
        final_text="OK",
        messages=list(kwargs.get("messages") or [])
        + [{"role": "assistant", "content": "OK"}],
        tool_trace=[],
    )


@pytest.fixture
def _reset_rate_limit_fixture() -> Iterator[None]:
    """Mirror the chat-handler suite's rate-limit isolation. Tests
    that drive a chat request must request this fixture (or rely on
    an autouse equivalent in the test file) to keep IP-keyed token
    buckets from carrying state across tests within one pytest
    process."""
    from forge_bridge.console import _rate_limit
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


# ─── Single-invocation chat-request driver ─────────────────────────────────


def _drive_chat_request(
    *,
    tools_list: list[Any] | None = None,
    prompt: str = "hi",
) -> tuple[Any, MagicMock]:
    """Drive a single chat request through a freshly-built console app.

    Returns ``(response, mock_router)``.

    The caller may pass ``tools_list`` to share a reference for
    post-response mutation tests (the authority-surface invariance
    probe for the ``enabled`` state). If ``None``, defaults to a
    single ``forge_test_probe`` tool.

    This driver is the canonical chat-request setup for PR 4 tests.
    It is deliberately self-contained — no imports from
    ``tests.console.*`` — so future ``tests/console/conftest.py``
    refactors cannot silently weaken §1.2's arbitration-invariance
    guard. (Chris convergence directive — locked.)

    The TestClient context manager wraps the actual request so the
    Starlette app's lifespan events fire correctly.
    """
    from starlette.testclient import TestClient

    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    if tools_list is None:
        tools_list = [_make_test_tool()]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(side_effect=_stub_chat_result)
    # A.1 chat compile branch added compile_intent() as the first await on
    # the chat path (before complete_with_tools). It is async and returns
    # list[str]. Without an AsyncMock here, the parent MagicMock auto-
    # generates a sync MagicMock for the attribute and the handler's
    # `await router.compile_intent(...)` raises TypeError.
    mock_router.compile_intent = AsyncMock(return_value=[])
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)

    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ManifestService(),
        llm_router=mock_router,
    )
    app = build_console_app(api)

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ):
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": prompt}]},
        )

    return response, mock_router


# ─── Record-reading helper ─────────────────────────────────────────────────


def _read_records(corpus_dir: Path) -> list[dict]:
    """Read every record across every ``capture-*.jsonl`` file in
    ``corpus_dir``. Returns records in (file, line) order.

    Skips header lines. Returns ``[]`` if ``corpus_dir`` does not
    exist or contains no capture files. Bypasses
    ``read_capture_file`` deliberately so the helper does not impose
    the reader's schema-version-mismatch error semantics on tests
    that probe the writer in isolation; tests that need full reader
    semantics call ``read_capture_file`` directly.
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


# ─── Step-7 assertion helpers ──────────────────────────────────────────────


def _tool_name_list(tools: list[Any]) -> list[str]:
    """Extract names for element-wise comparison. Mirrors
    ``forge_bridge.corpus._capture._tool_names`` semantics so tests
    compare apples to apples regardless of whether the chat handler
    passes ``Tool`` objects or copies."""
    out: list[str] = []
    for t in tools:
        if isinstance(t, str):
            out.append(t)
            continue
        n = getattr(t, "name", None)
        if n is None and isinstance(t, dict):
            n = t.get("name")
        out.append(str(n) if n is not None else "")
    return out


def _assert_arbitration_invariance(
    response: Any,
    mock_router: MagicMock,
    *,
    expected_tool_names: list[str],
) -> None:
    """Single-invocation structural properties shared across all
    capture states.

    PROTECTED PROPERTY:
      Capture state must not change what the chat handler sends to
      the LLM router or what it returns to the operator. Per
      ``A.5.3.2-PR4-FRAMING.md`` §1.2: "If operator-visible behavior
      changes based on capture state, the participation boundary has
      already been crossed regardless of internal architecture
      claims."

    OPERATIONAL EXPRESSION (today's checks):
      1. HTTP status code == 200.
      2. Response body has keys ``{messages, stop_reason, request_id}``.
      3. ``body["messages"]`` is a non-empty list.
      4. ``response.headers`` contains ``X-Request-ID``.
      5. ``body.get("tool_trace", [])`` is empty (stub path; no
         inadvertent invocation).
      6. ``mock_router.complete_with_tools`` called exactly once.
      7. ``call_args.kwargs["tools"]`` element-equal (by name) to
         ``expected_tool_names`` — the arbitration output upstream
         of LLM stochasticity.
      8. ``call_args.kwargs["sensitive"]`` is True (D-05 invariant).

    Each assertion protects a distinct failure mode. Removing any one
    is a spec amendment, not an implementation choice.
    """
    # 1. Status code.
    assert response.status_code == 200, (
        f"chat handler returned status {response.status_code}; "
        f"expected 200. Capture state must not perturb arbitration "
        f"output. Body: {response.text!r}"
    )

    # 2. Response body keys.
    body = response.json()
    assert isinstance(body, dict), (
        f"response body is not a JSON object: {body!r}"
    )
    for required_key in ("messages", "stop_reason", "request_id"):
        assert required_key in body, (
            f"response envelope missing required key {required_key!r}: "
            f"{body!r}"
        )

    # 3. Non-empty messages list.
    assert isinstance(body["messages"], list) and body["messages"], (
        f"response.messages must be a non-empty list; got: "
        f"{body['messages']!r}"
    )

    # 4. X-Request-ID header.
    assert "X-Request-ID" in response.headers, (
        f"response missing X-Request-ID header. Headers: "
        f"{dict(response.headers)!r}"
    )

    # 5. tool_trace empty.
    tool_trace = body.get("tool_trace", [])
    assert tool_trace == [], (
        f"unexpected tool_trace: {tool_trace!r}. Stub path returns "
        f"empty trace; non-empty implies tool execution happened "
        f"that should not have."
    )

    # 6. complete_with_tools called exactly once.
    call_count = mock_router.complete_with_tools.call_count
    assert call_count == 1, (
        f"complete_with_tools call_count={call_count}; expected exactly 1."
    )

    # 7. tools list passed to LLM matches expected (element-equal by name).
    call_kwargs = mock_router.complete_with_tools.call_args.kwargs
    actual_tool_names = _tool_name_list(call_kwargs["tools"])
    assert actual_tool_names == expected_tool_names, (
        f"tools passed to LLM router differ from expected: "
        f"got {actual_tool_names!r}, expected {expected_tool_names!r}. "
        f"This is the arbitration output upstream of LLM stochasticity; "
        f"capture state must not perturb it."
    )

    # 8. sensitive=True (D-05).
    assert call_kwargs.get("sensitive") is True, (
        f"sensitive kwarg expected True (D-05 invariant); got "
        f"{call_kwargs.get('sensitive')!r}"
    )


def _assert_arbitration_response_equivalent(
    response_a: Any,
    response_b: Any,
) -> None:
    """Assert two chat-handler responses are arbitration-equivalent.

    The protected property is *semantic* arbitration equivalence, not
    literal byte-for-byte identity. Capture state must not perturb
    the arbitration output observed by the operator.

    COMPARED (must match):
      - HTTP status code
      - Response body keys: ``{messages, stop_reason, request_id}``
      - ``body["messages"]`` length and per-message ``(role, content)``
      - ``body["stop_reason"]``
      - Presence of ``X-Request-ID`` header
      - ``body.get("tool_trace", [])`` (must be empty under stub setup)

    INTENTIONALLY IGNORED (expected to differ across requests):
      - ``body["request_id"]`` — UUID per request
      - ``X-Request-ID`` header VALUE — UUID per request
      - Any timestamp fields surfaced in body or headers
      - Server-Date / response timing headers

    Failure under this assertion means capture state perturbed
    arbitration output — PR 4's single most important invariant has
    been violated. (``A.5.3.2-PR4-FRAMING.md`` §1.2.)

    Helper renamed away from "byte-identical" language at Chris's
    convergence directive: keeps the checksum discipline honest by
    enumerating the IS-compared / IS-ignored boundary explicitly.
    Future contributors editing this helper inherit the boundary
    rather than re-deriving it from the helper name.
    """
    assert response_a.status_code == response_b.status_code, (
        f"response status codes differ: {response_a.status_code} vs "
        f"{response_b.status_code}. Capture state must not perturb "
        f"arbitration output."
    )

    body_a = response_a.json()
    body_b = response_b.json()
    assert set(body_a.keys()) == set(body_b.keys()), (
        f"response body keys differ: {sorted(body_a.keys())} vs "
        f"{sorted(body_b.keys())}"
    )

    msgs_a = body_a.get("messages", [])
    msgs_b = body_b.get("messages", [])
    assert len(msgs_a) == len(msgs_b), (
        f"response.messages length differs: {len(msgs_a)} vs {len(msgs_b)}"
    )
    for i, (ma, mb) in enumerate(zip(msgs_a, msgs_b)):
        assert ma.get("role") == mb.get("role"), (
            f"messages[{i}].role differs: {ma.get('role')!r} vs "
            f"{mb.get('role')!r}"
        )
        assert ma.get("content") == mb.get("content"), (
            f"messages[{i}].content differs: {ma.get('content')!r} vs "
            f"{mb.get('content')!r}"
        )

    assert body_a.get("stop_reason") == body_b.get("stop_reason"), (
        f"stop_reason differs: {body_a.get('stop_reason')!r} vs "
        f"{body_b.get('stop_reason')!r}"
    )

    for resp, label in ((response_a, "a"), (response_b, "b")):
        assert "X-Request-ID" in resp.headers, (
            f"response_{label} missing X-Request-ID header"
        )

    trace_a = body_a.get("tool_trace", [])
    trace_b = body_b.get("tool_trace", [])
    assert trace_a == trace_b == [], (
        f"tool_trace differs or is non-empty: a={trace_a!r}, b={trace_b!r}"
    )


def _assert_no_failed_write_residue(
    corpus_dir: Path,
    *,
    expected_record_count: int,
) -> None:
    """Assert no failed write left interpretable residue in
    ``corpus_dir``.

    PROTECTED PROPERTY:
      Failed writes must not leave interpretable residue capable of
      contaminating later observation or review.

    Today's filesystem-level assertions are the operational
    expression of this property. They derive from
    ``A.5.3.2-PR3-SPEC.md`` §6.5 atomic-append guarantees (the
    writer fsyncs full records or leaves the file structurally
    unchanged). The architectural property is the interpretability
    constraint, not the filesystem expression — a future writer
    change that satisfied the filesystem assertions but left an
    interpretable orphan record (e.g., header-only file, or
    truncated-record-with-valid-prefix) would still violate this
    helper's contract.

    OPERATIONAL EXPRESSION (today's filesystem-level checks):
      1. No empty files in corpus_dir (header-only would parse as
         malformed and confuse the reader).
      2. No file with a valid header but zero records.
      3. No file with one or more records but no header.
      4. No file with a malformed (non-JSON / partial) record.
      5. Total record count across all files matches the expected
         emission count for the test state (positive-shape complement
         to the negative-shape orphan checks; expresses §6.5
         single-write-per-emission at the integration level).

    DEPENDENCY:
      The fixture's failure-injection wrapper raises ``OSError``
      BEFORE delegating to ``real_open``. Today's "failing" state
      therefore produces zero on-disk activity — the orphan checks
      bite only when a future writer change introduces a
      partial-write window. They are forcing functions on the
      writer's atomicity property, not nominal-state validators.
    """
    from forge_bridge.corpus._schema import (
        SchemaValidationError,
        validate_capture_record,
    )

    if not corpus_dir.exists():
        # Directory absent → no files possible. Valid for "no capture
        # happened at all" scenarios (disabled or failing-with-no-mkdir).
        assert expected_record_count == 0, (
            f"corpus_dir {corpus_dir} does not exist but expected "
            f"{expected_record_count} record(s)."
        )
        return

    files = sorted(corpus_dir.glob("capture-*.jsonl"))

    if expected_record_count == 0 and not files:
        return

    total_records = 0

    for path in files:
        text = path.read_text(encoding="utf-8")

        # 1. No empty files.
        assert text.strip(), (
            f"empty corpus file {path}: header-only would parse as "
            f"malformed and confuse the reader. Per "
            f"A.5.3.2-PR3-SPEC.md §6.5 (atomic-append), files exist "
            f"iff at least one truthful record was written."
        )

        lines = [ln for ln in text.split("\n") if ln.strip()]
        assert lines, f"unexpectedly empty corpus file {path}"

        # 2. First non-empty line is the header.
        try:
            header = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"first line of {path} is not valid JSON: {exc}. "
                f"Header-line corruption violates §6.5 atomic-append."
            ) from exc
        assert header.get("_header") is True, (
            f"first line of {path} is not a header (missing "
            f"_header:True): {header!r}. Records-without-header would "
            f"represent header-line corruption — orphan-record "
            f"interpretability hazard."
        )

        # 3. Header → followed by ≥1 record (no header-only files).
        assert len(lines) > 1, (
            f"{path} contains a header but no records — header-only "
            f"file is interpretable residue per §6.5 (atomic-append "
            f"should have bundled header + first record into one "
            f"write)."
        )

        # 4. Every non-header line is a valid record per the schema.
        for i, line in enumerate(lines[1:], start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"line {i} of {path} is not valid JSON: {exc}. "
                    f"Partial-write residue violates §6.5 atomicity."
                ) from exc
            try:
                validate_capture_record(record)
            except SchemaValidationError as exc:
                raise AssertionError(
                    f"line {i} of {path} fails schema validation: "
                    f"{exc}"
                ) from exc
            total_records += 1

    # 5. Total record count matches expected emission count.
    assert total_records == expected_record_count, (
        f"expected {expected_record_count} record(s), found "
        f"{total_records} in {corpus_dir}. Mismatch indicates §6.5 "
        f"single-write-per-emission invariant violation: either "
        f"records were dropped or duplicates emitted."
    )


def _assert_authority_surface_invariance(
    *,
    corpus_dir: Path,
    source_tools_list: list[Any],
    expected_pre_mutation_hash: str,
) -> None:
    """Authority-surface invariance: post-capture mutation of the
    producer-surface tool list must not alter the on-disk record's
    snapshot hash.

    PROTECTED PROPERTY:
      Capture must reflect the producer-surface truth at the moment
      of authority, not reconstructed downstream state.
      (``A.5.3.2-PR4-FRAMING.md`` §3 + Chris convergence directive.)

    OPERATIONAL EXPRESSION:
      1. Mutate ``source_tools_list`` AFTER the capture has completed
         (append a marker tool that would alter the hash).
      2. Re-read the on-disk record.
      3. Assert ``identity.registered_tools_snapshot_hash`` is
         UNCHANGED.

    BITE-VERIFICATION RATIONALE:
      Today's writer is eager: ``_build_capture_record`` calls
      ``_tool_names`` and ``registered_tools_snapshot_hash`` eagerly
      at emit time, the dict is ``json.dumps``'d to a line, and the
      file is flushed and closed before ``emit_divergence_capture``
      returns. Closed-file bytes are sealed; today's bite passes
      trivially.

      The assertion is a forcing function on FUTURE writer changes.
      A regression that retains a live reference to the input list
      and re-resolves the snapshot lazily (e.g., flushing later via
      a buffered writer that re-reads the input) would let
      post-capture mutation leak into the on-disk record. The
      assertion would then fire.

      The bite-verification mutation lives at incarnation, not at
      topology — a particular writer scratch shape may need to be
      adjusted surgically without reopening this assertion or the
      enabled-state geometry.
    """
    # Mutate the source AFTER capture has completed.
    source_tools_list.append(_make_test_tool(name="MUTATION_PROBE_AFTER_CAPTURE"))

    # Re-read the on-disk record. Hash must be UNCHANGED.
    records = _read_records(corpus_dir)
    assert len(records) >= 1, (
        f"_assert_authority_surface_invariance called with no records "
        f"on disk in {corpus_dir}. Helper should be invoked from a "
        f"capture-correctness block where at least one record exists."
    )
    on_disk_hash = records[0]["identity"]["registered_tools_snapshot_hash"]
    assert on_disk_hash == expected_pre_mutation_hash, (
        f"on-disk record's registered_tools_snapshot_hash changed "
        f"after post-capture mutation of the producer surface: "
        f"expected {expected_pre_mutation_hash!r}, got "
        f"{on_disk_hash!r}. The writer holds a live reference to the "
        f"input list and re-resolves the snapshot lazily — the "
        f"authority-surface invariance has been violated. Capture "
        f"must reflect the producer-surface truth at the moment of "
        f"authority, not reconstructed downstream state."
    )


# ─── PR 5 chain-step infrastructure ────────────────────────────────────────
#
# Per A.5.3.2-PR5-SPEC.md §6.2: extending this file in place. The
# chain-step driver and assertion helpers below compose against the
# same capture_state_cycling fixture, the same _make_test_tool /
# _passthrough_filter helpers, the same _read_records reader. The
# only PR-5-specific construction infrastructure is here.


async def _stub_call_tool(name: str, params: dict, /) -> Any:
    """Default ``mcp.call_tool`` mock for chain-step integration tests.

    Returns a JSON-string structure that ``serialize_forced_tool_result``
    handles cleanly (string passthrough). Tests requiring richer return
    shapes pass an explicit override via ``_drive_chain_request``'s
    ``call_tool_side_effect`` parameter.
    """
    return f'{{"result": "called:{name}"}}'


async def _stub_resolve_required_params(
    tool_name: str,
    resolver_input: dict,
    mcp: Any,
    /,
    **_kwargs: Any,
) -> dict:
    """Default ``resolve_required_params`` mock — returns empty params.

    The chain-step capture call site fires BEFORE ``resolve_required_params``
    is invoked (capture is at narrowing-finalization, params resolution is
    downstream). Tests asserting capture-emission therefore do not depend
    on params resolution behavior; this stub keeps the chain proceeding
    past the resolution step without forcing tests to construct realistic
    resolver chains.

    Per A.5.3.2-PR5-SPEC.md §4.1 architectural property: capture is
    arbitration-aware, not branch-aware. Subsequent failure paths
    (e.g., MULTIPLE_PROJECTS) do not re-trigger capture. This stub's
    empty-params return path drives the success branch through
    ``mcp.call_tool``; tests for the MULTIPLE_PROJECTS-style downstream
    failure shape would override this stub.
    """
    return {}


def _drive_chain_request(
    *,
    tools_list: list[Any] | None = None,
    prompt: str = "first -> second",
    call_tool_side_effect: Callable | None = None,
) -> tuple[Any, AsyncMock]:
    """Drive a multi-step chain request through a freshly-built console app.

    Returns ``(response, mock_call_tool)``.

    Default prompt parses to a 2-step chain via ``parse_chain``
    (the ``->`` separator triggers the ``_execute_chain`` branch in
    ``chat_handler``, which routes to ``run_chain_steps`` →
    ``execute_chain_step`` per step). Default ``tools_list`` is a single
    ``forge_test_probe`` tool; every step text matches that one tool via
    ``filter_tools_by_message``'s no-token-overlap fallback (returns the
    full input list unchanged), so each step lands in the success path.

    For ambiguity-rejection scenarios, pass ``tools_list`` with multiple
    tools whose names share keywords with the step text (PR14 narrows
    to a multi-survivor set; deterministic_narrow does not collapse;
    ``len(filtered) != 1`` triggers the rejection envelope AFTER capture
    has already emitted).

    For zero-match scenarios, pass tools whose names + descriptions
    have zero token overlap with the step text — but note PR14's
    fallback returns the full list rather than an empty list when no
    overlap exists, so this scenario is hard to construct via
    ``filter_tools_by_message`` alone. Tests requiring a literal
    zero-match path may need to mock ``filter_tools_by_message`` itself.

    The TestClient context manager wraps the actual request so the
    Starlette app's lifespan events fire correctly. Mocks installed:

      - ``forge_bridge.mcp.server.mcp.list_tools`` → returns ``tools_list``
      - ``forge_bridge.mcp.server.mcp.call_tool`` → ``_stub_call_tool``
        (or ``call_tool_side_effect`` override)
      - ``forge_bridge.console.handlers.filter_tools_by_reachable_backends``
        → ``_passthrough_filter``
      - ``forge_bridge.console._tool_chain.resolve_required_params``
        → ``_stub_resolve_required_params``

    The ``mock_call_tool`` is returned so tests can assert on
    invocation count, args, etc. — useful for confirming that
    rejection-path tests did NOT call ``mcp.call_tool`` (capture
    fired but the rejection envelope returned before tool execution).
    """
    from starlette.testclient import TestClient

    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    if tools_list is None:
        tools_list = [_make_test_tool()]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(side_effect=_stub_chat_result)
    # A.1 chat compile branch added compile_intent() as the first await on
    # the chat path (before complete_with_tools). It is async and returns
    # list[str]. Without an AsyncMock here, the parent MagicMock auto-
    # generates a sync MagicMock for the attribute and the handler's
    # `await router.compile_intent(...)` raises TypeError.
    mock_router.compile_intent = AsyncMock(return_value=[])
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)

    mock_call_tool = AsyncMock(
        side_effect=call_tool_side_effect or _stub_call_tool,
    )

    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ManifestService(),
        llm_router=mock_router,
    )
    app = build_console_app(api)

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=mock_call_tool,
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.console._tool_chain.resolve_required_params",
        side_effect=_stub_resolve_required_params,
    ):
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": prompt}]},
        )

    return response, mock_call_tool


def _assert_chain_step_arbitration_invariance(
    response: Any,
    mock_call_tool: AsyncMock,
    *,
    expected_step_count: int,
    expected_status: str = "success",
) -> None:
    """Single-invocation structural properties for the chain envelope
    shared across all capture states.

    PROTECTED PROPERTY:
      Capture state must not change what the chain executor returns to
      the operator. Per ``A.5.3.2-PR5-FRAMING.md`` §1.2 (inheriting
      PR 4 framing §1.2): "If operator-visible behavior changes based on
      capture state, the participation boundary has already been crossed
      regardless of internal architecture claims."

    OPERATIONAL EXPRESSION (today's checks):
      1. HTTP status code: 200 on ``success``, 400 on ``error``.
      2. Response body has chain-envelope keys ``{status, request_id,
         chain, error}``.
      3. ``body["status"]`` matches ``expected_status``.
      4. ``body["chain"]`` is a list of length ``expected_step_count``
         on success (chain executes through). On error, length matches
         the step index that failed (zero-indexed; the failing step
         itself is NOT appended to ``chain``).
      5. ``response.headers`` contains ``X-Request-ID``.
      6. ``mock_call_tool`` invocation count matches expectations:
         ``expected_step_count`` invocations on success;
         ``len(body["chain"])`` invocations on error (each completed
         step before the failing one called ``mcp.call_tool`` once).

    Each assertion protects a distinct failure mode. Removing any one
    is a spec amendment, not an implementation choice.

    Per ``A.5.3.2-PR5-SPEC.md`` §4.1 architectural property: capture
    fires AT narrowing-finalization, not at chain envelope assembly.
    Therefore capture-state perturbation that altered the chain
    envelope shape would indicate a participation-boundary leak —
    capture's per-step emission must not influence subsequent chain
    progression.
    """
    # 1. Status code.
    expected_status_code = 200 if expected_status == "success" else 400
    assert response.status_code == expected_status_code, (
        f"chain executor returned status {response.status_code}; "
        f"expected {expected_status_code}. Capture state must not "
        f"perturb arbitration output. Body: {response.text!r}"
    )

    # 2. Response body keys.
    body = response.json()
    assert isinstance(body, dict), (
        f"response body is not a JSON object: {body!r}"
    )
    for required_key in ("status", "request_id", "chain", "error"):
        assert required_key in body, (
            f"chain envelope missing required key {required_key!r}: "
            f"{body!r}"
        )

    # 3. status field matches expected.
    assert body["status"] == expected_status, (
        f"chain envelope status={body['status']!r}; expected "
        f"{expected_status!r}. Body: {body!r}"
    )

    # 4. chain length.
    chain = body["chain"]
    assert isinstance(chain, list), (
        f"chain field is not a list: {chain!r}"
    )
    if expected_status == "success":
        assert len(chain) == expected_step_count, (
            f"chain length {len(chain)}; expected "
            f"{expected_step_count}. Successful chain executes all "
            f"steps. Body: {body!r}"
        )

    # 5. X-Request-ID header.
    assert "X-Request-ID" in response.headers, (
        f"response missing X-Request-ID header. Headers: "
        f"{dict(response.headers)!r}"
    )

    # 6. mcp.call_tool invocation count matches completed-step count.
    expected_call_tool_count = (
        expected_step_count if expected_status == "success"
        else len(chain)
    )
    assert mock_call_tool.call_count == expected_call_tool_count, (
        f"mcp.call_tool invocation count={mock_call_tool.call_count}; "
        f"expected {expected_call_tool_count} (one per completed "
        f"chain step). Body: {body!r}"
    )


def _assert_chain_step_arbitration_response_equivalent(
    response_a: Any,
    response_b: Any,
) -> None:
    """Assert two chain-executor responses are arbitration-equivalent.

    The protected property is *semantic* arbitration equivalence, not
    literal byte-for-byte identity. Capture state must not perturb the
    chain envelope observed by the operator.

    COMPARED (must match):
      - HTTP status code
      - Response body keys: ``{status, request_id, chain, error}``
      - ``body["status"]``
      - ``body["chain"]`` length and per-step ``step`` text
      - ``body["error"]`` shape on error path (code, step_index;
        ``original_error.type`` if present)
      - Presence of ``X-Request-ID`` header

    INTENTIONALLY IGNORED (expected to differ across requests):
      - ``body["request_id"]`` — UUID per request
      - ``X-Request-ID`` header VALUE — UUID per request
      - Per-step ``result`` content (may vary by stub timing /
        invocation order details that don't affect arbitration)
      - ``body["error"]["message"]`` — human-readable text
      - ``body["error"]["original_error"]["message"]`` — same
      - Server-Date / response timing headers

    The IS-compared / IS-ignored boundary is re-derived from PR 4's
    chat-envelope variant per ``A.5.3.2-PR4-CLOSE.md`` §3.5: chain
    steps return ``{status, request_id, chain, error}``, not
    ``{messages, stop_reason, request_id}``. The structural
    difference forces a chain-envelope-specific helper rather than
    parameterizing the chat-envelope helper.

    Failure under this assertion means capture state perturbed
    arbitration output — PR 5 inheriting PR 4's single most
    important invariant has been violated at the chain-step surface.
    """
    assert response_a.status_code == response_b.status_code, (
        f"response status codes differ: {response_a.status_code} vs "
        f"{response_b.status_code}. Capture state must not perturb "
        f"chain envelope."
    )

    body_a = response_a.json()
    body_b = response_b.json()
    assert set(body_a.keys()) == set(body_b.keys()), (
        f"chain envelope body keys differ: {sorted(body_a.keys())} "
        f"vs {sorted(body_b.keys())}"
    )

    assert body_a.get("status") == body_b.get("status"), (
        f"chain envelope status differs: {body_a.get('status')!r} vs "
        f"{body_b.get('status')!r}"
    )

    chain_a = body_a.get("chain", [])
    chain_b = body_b.get("chain", [])
    assert len(chain_a) == len(chain_b), (
        f"chain length differs: {len(chain_a)} vs {len(chain_b)}"
    )
    for i, (step_a, step_b) in enumerate(zip(chain_a, chain_b)):
        assert step_a.get("step") == step_b.get("step"), (
            f"chain[{i}].step differs: {step_a.get('step')!r} vs "
            f"{step_b.get('step')!r}"
        )

    err_a = body_a.get("error")
    err_b = body_b.get("error")
    if err_a is None and err_b is None:
        pass  # success path on both sides; nothing more to compare.
    else:
        assert err_a is not None and err_b is not None, (
            f"error field presence differs: a={err_a!r}, b={err_b!r}"
        )
        assert err_a.get("code") == err_b.get("code"), (
            f"error.code differs: {err_a.get('code')!r} vs "
            f"{err_b.get('code')!r}"
        )
        assert err_a.get("step_index") == err_b.get("step_index"), (
            f"error.step_index differs: {err_a.get('step_index')!r} "
            f"vs {err_b.get('step_index')!r}"
        )
        orig_a = err_a.get("original_error") or {}
        orig_b = err_b.get("original_error") or {}
        assert orig_a.get("type") == orig_b.get("type"), (
            f"error.original_error.type differs: "
            f"{orig_a.get('type')!r} vs {orig_b.get('type')!r}"
        )

    for resp, label in ((response_a, "a"), (response_b, "b")):
        assert "X-Request-ID" in resp.headers, (
            f"response_{label} missing X-Request-ID header"
        )
