"""No-dependency invariant — arbitration must complete successfully
when ``forge_bridge.corpus`` is structurally absent.

Per ``A.5.3.2-PR4-FRAMING.md`` §1.4 and ``A.5.3.2-PR4-SPEC.md`` §6.1:
the strongest possible no-dependency test. If arbitration runs
without corpus, the dependency is structurally absent.

The framing's binding sentence:

  *"The arbitration layer now expects capture infrastructure to
  exist."*

That sentence MUST remain false for the lifetime of this
architecture. Capture is a downstream observer of arbitration, not
an upstream dependency of it. If the chat handler stops working
when capture is disabled, broken, or removed, the participation
boundary has already collapsed.

This test is a forcing function for PR 4 step 6 (chat-handler
integration): the integration code MUST be designed such that
``forge_bridge.corpus`` absence does not break arbitration.
Defensive imports, try/except guards, lazy imports — the
implementation is free to choose; this test enforces the property.

Mechanism:

  1. Patch ``sys.modules['forge_bridge.corpus']`` (and submodules)
     to a sentinel that raises ``AttributeError`` on every
     attribute access.
  2. Force-reload the chat handler module so its corpus imports
     re-resolve under the sentinel. A naive
     ``from forge_bridge.corpus import ...`` at module top will
     fail at reload; a defensive guard will succeed with fallback
     bindings.
  3. Build a fresh Console app and drive a chat request.
  4. Assert the request returns 200 with a well-formed success
     envelope. Persistent error-envelope behavior when corpus is
     absent would represent the exact architectural collapse this
     test exists to prevent — framing §1.4 protects arbitration
     non-dependency, not merely graceful degradation.
  5. ``monkeypatch`` restores ``sys.modules`` on teardown.

Today (before step 6 lands) the chat handler imports nothing from
corpus, so the test passes trivially. The test exists to lock in
the property BEFORE step 6 has the chance to violate it.
"""
from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# jinja2 is a declared chat-handler dependency (pyproject.toml).
# Skip where absent rather than fail loudly: a test that drives a
# chat request cannot meaningfully execute when the SUT itself
# cannot construct. The skip is operationally honest, not a
# property weakening — the no-dependency invariant is enforced
# wherever the chat handler can run at all.
pytest.importorskip(
    "jinja2",
    reason=(
        "jinja2 is a declared chat-handler dependency; this test "
        "cannot construct the SUT without it. Skipping where absent "
        "is operationally honest, not a property weakening."
    ),
)

from starlette.testclient import TestClient  # noqa: E402

from forge_bridge.console import _rate_limit  # noqa: E402

# Construction helpers relocated to _pr4_helpers.py at PR 4 step 7.
# They are shared PR-4 hostile-environment infrastructure now, not
# step-5-owned. Step-5 behavior is unchanged — these are import
# substitutions only.
from tests.corpus._pr4_helpers import (  # noqa: E402
    _make_test_tool,
    _passthrough_filter,
    _stub_chat_result,
)


_CORPUS_PACKAGE = "forge_bridge.corpus"
_HANDLER_MODULE = "forge_bridge.console.handlers"
# forge_bridge.console.app's top-level `from forge_bridge.console.handlers
# import chat_handler` binds the chat_handler SYMBOL at module-load time.
# If app loaded BEFORE this test (e.g., another corpus test in the same
# pytest session called build_console_app via tests/corpus/_pr4_helpers.py),
# app.chat_handler points at the PRE-reload handlers module — bypassing
# the fallback bindings the reload installs. Reloading app along with
# handlers ensures the re-imported chat_handler symbol resolves to the
# post-reload module. The no-dependency property (arbitration completes
# when corpus is structurally absent) is unchanged; this hardens the
# test against ordering with respect to other suite members that import
# app at their own discretion.
_APP_MODULE = "forge_bridge.console.app"
# PR 5: forward-looking module deletion for the chain-step path.
# `_step.py` is the chain-step executor (analogous to the chat
# handler's narrowing surface). `_engine.py` is its caller; both must
# reload under the corpus-sentinel patch so that `_step.py`'s Shape A
# guarded import (added at PR 5 step 6) re-resolves against the
# sentinel and installs fallback bindings. Pre-step-6 these are no-ops
# (neither module imports corpus today); post-step-6 they exercise the
# chain-step's no-dependency guarantee per A.5.3.2-PR5-SPEC.md §6.3
# path 1 (the multi-step prompt parametrization). Naming both modules
# explicitly so the chain re-resolution chain is auditable from this
# test alone — `_engine.py` imports `execute_chain_step` from
# `_step.py` at module-load time, so reloading `_step.py` without
# also reloading `_engine.py` would leave the cached `_engine.py`
# bound to the pre-reload `_step.py`, defeating the sentinel.
_ENGINE_MODULE = "forge_bridge.console._engine"
_STEP_MODULE = "forge_bridge.console._step"


class _CorpusSentinel(ModuleType):
    """Sentinel module: every attribute access raises AttributeError.

    Patched into ``sys.modules['forge_bridge.corpus']`` and every
    pre-loaded ``forge_bridge.corpus.*`` submodule for the duration
    of the no-dependency test. Mirrors the behavior of a structurally
    absent corpus package — distinguishable from a "real" package
    only by ``AttributeError`` on any attribute lookup.

    Per ``A.5.3.2-PR4-FRAMING.md`` §1.4, this is the strongest
    possible test of the no-dependency property: if arbitration runs
    without corpus, the dependency is structurally absent.
    """

    def __getattr__(self, name: str) -> object:
        raise AttributeError(
            f"{self.__name__} is structurally absent in this test "
            f"context (no-dependency assertion). Attempted attribute "
            f"access: {name!r}. Per A.5.3.2-PR4-FRAMING.md §1.4: "
            f"'The arbitration layer now expects capture infrastructure "
            f"to exist.' That sentence must remain false for the "
            f"lifetime of this architecture."
        )


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Mirror the chat-handler suite's rate-limit isolation."""
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


@pytest.mark.parametrize(
    "prompt,expected_envelope_keys",
    [
        pytest.param(
            "hi",
            ("messages", "stop_reason", "request_id"),
            id="single_step",
        ),
        pytest.param(
            "list projects -> list shots",
            ("status", "request_id", "chain", "error"),
            id="multi_step_chain",
        ),
    ],
)
def test_arbitration_completes_when_corpus_unavailable(
    monkeypatch, tmp_path, prompt, expected_envelope_keys,
):
    """Arbitration must complete successfully when
    ``forge_bridge.corpus`` is structurally absent — at BOTH the
    chat-handler single-step surface and the chain-step multi-step
    surface.

    Per ``A.5.3.2-PR5-SPEC.md`` §6.3 path 1 (preferred): coverage of
    the chain-step surface is parametrized into this test rather than
    duplicated in a sibling file. The protected property —
    *arbitration runs without corpus, period* — is one property;
    expressing it as one parametrized test reads as one invariant.
    The multi-step parametrization drives `_execute_chain →
    run_chain_steps → execute_chain_step` end-to-end, exercising
    `_step.py`'s Shape A guarded import + emission fallback (added at
    PR 5 step 6).

    Per ``A.5.3.2-PR5-FRAMING.md`` §5: no-dependency coverage at the
    chain-step surface must be MEASURED, not inferred. The PR 4
    single-step probe alone does not reach `_step.py`; the multi-step
    parametrization closes that empirical gap.

    Asserts (per parametrized envelope shape):
      - Status code is exactly 200.
      - Response body is JSON-parseable.
      - Response envelope contains all keys in
        ``expected_envelope_keys``.
      - No exception propagates from the corpus-import attempt at
        EITHER call site.
    """
    # Defensive isolation: even if the chat handler accidentally
    # accesses the corpus dir during this test, route it to a
    # tmp_path child instead of the operator's real
    # ~/.forge-bridge/corpus/.
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path / "corpus"))
    # Explicitly enable the capture gate. This means: "the operator
    # has asked for capture, but the corpus is structurally absent."
    # The strongest expression of the no-dependency property —
    # arbitration must complete EVEN when capture is requested AND
    # corpus is unavailable.
    monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "1")

    # Patch sys.modules: forge_bridge.corpus + every pre-loaded
    # submodule → sentinel. Defensive: anything that bypasses the
    # package and reaches for a submodule directly still hits a
    # sentinel.
    corpus_keys = [
        k for k in sys.modules
        if k == _CORPUS_PACKAGE or k.startswith(_CORPUS_PACKAGE + ".")
    ]
    for k in corpus_keys:
        monkeypatch.setitem(sys.modules, k, _CorpusSentinel(k))

    # This reload step is the forcing function on step 6's import
    # shape: handler-module imports of forge_bridge.corpus.* must
    # tolerate package absence (defensive try/except, lazy-inside-
    # guarded-block, or the gate function itself imported lazily).
    # Naive top-level imports would fail here. The test enforces
    # the constraint; the implementation chooses its mechanism.
    monkeypatch.delitem(sys.modules, _HANDLER_MODULE, raising=False)
    # Drop the app module too: its top-level `from
    # forge_bridge.console.handlers import chat_handler` binds the
    # symbol at module-load time. If app was loaded earlier in the
    # same pytest session (e.g., by step 7's integration tests
    # calling `_drive_chat_request`), app.chat_handler would still
    # point at the pre-reload handlers and would bypass the fallback
    # bindings that the reload below installs.
    monkeypatch.delitem(sys.modules, _APP_MODULE, raising=False)
    # PR 5: drop the chain-step modules too. `_engine.py` imports
    # `execute_chain_step` from `_step.py` at module-load time;
    # reloading `_step.py` without `_engine.py` leaves the cached
    # `_engine.py` bound to pre-reload `_step.py`, defeating the
    # sentinel for the chain path. Pre-step-6 these delitems are
    # no-ops (neither module imports corpus today); post-step-6
    # they make the multi-step parametrization meaningfully exercise
    # the Shape A guarded-import fallback in `_step.py`. Same forcing
    # function shape as the handler reload above.
    monkeypatch.delitem(sys.modules, _ENGINE_MODULE, raising=False)
    monkeypatch.delitem(sys.modules, _STEP_MODULE, raising=False)

    # If the reimport itself raises, the no-dependency property has
    # been violated. The assertion here is: the import succeeds.
    importlib.import_module(_HANDLER_MODULE)

    # Build a fresh app under the sentinel patch. The import below
    # re-loads forge_bridge.console.app (delitem above) so its
    # chat_handler symbol resolves to the post-reload handlers.
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

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

    # Stubs for chain-path execution: _stub_call_tool and
    # _stub_resolve_required_params drive a successful chain
    # completion through `mcp.call_tool` and the resolver chain.
    # These patches are inert for the single-step prompt (which
    # reaches the LLM-router path and returns through
    # `_stub_chat_result`) and active for the multi-step prompt
    # (which routes through `_execute_chain → run_chain_steps →
    # execute_chain_step` per step). One mock setup serves both
    # parametrizations cleanly.
    from tests.corpus._pr4_helpers import (
        _stub_call_tool,
        _stub_resolve_required_params,
    )

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=[_make_test_tool()]),
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=_stub_call_tool),
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

    # Tightened assertion (per converged review): framing §1.4
    # protects arbitration non-dependency, not merely graceful
    # degradation. Persistent 500/error-envelope behavior when
    # corpus is absent would represent the exact architectural
    # collapse this test exists to prevent.
    assert response.status_code == 200, (
        f"arbitration returned status {response.status_code} "
        f"when forge_bridge.corpus is structurally absent (prompt="
        f"{prompt!r}); expected 200. Per A.5.3.2-PR4-FRAMING.md §1.4 "
        f"+ A.5.3.2-PR5-FRAMING.md §5, arbitration must complete "
        f"successfully — not merely degrade gracefully — when "
        f"capture infrastructure is unavailable, at BOTH the "
        f"chat-handler and chain-step surfaces. Body: "
        f"{response.text!r}"
    )
    body = response.json()
    assert isinstance(body, dict), (
        f"arbitration response is not a JSON object: {body!r}"
    )
    for required_key in expected_envelope_keys:
        assert required_key in body, (
            f"arbitration success envelope missing required key "
            f"{required_key!r} (prompt={prompt!r}; expected_keys="
            f"{expected_envelope_keys!r}): {body!r}. Per "
            f"A.5.3.2-PR4-FRAMING.md §1.4 + A.5.3.2-PR5-FRAMING.md §5, "
            f"both arbitration surfaces must produce a well-formed "
            f"envelope when forge_bridge.corpus is structurally "
            f"absent — never a malformed response at either surface."
        )
