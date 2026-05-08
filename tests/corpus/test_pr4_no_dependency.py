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


_CORPUS_PACKAGE = "forge_bridge.corpus"
_HANDLER_MODULE = "forge_bridge.console.handlers"


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


def _make_test_tool():
    """Non-empty Tool so the chat handler's empty-registry guard does
    not short-circuit before we exercise the no-dependency property."""
    from mcp.types import Tool
    return Tool(
        name="forge_test_probe",
        description="Test probe for no-dependency assertion.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools):
    """Default reachability-filter stub: pass all tools through. The
    chat handler's real filter would TCP-probe :9999, which is
    unwanted in test context."""
    return tools


async def _stub_chat_result(**kwargs):
    """LLMRouter mock: returns a minimal ChatTurnResult so the chat
    handler reaches the divergence-capture call site (where step 6
    will land integration code) before constructing the response."""
    from forge_bridge.llm.router import ChatTurnResult
    return ChatTurnResult(
        final_text="OK",
        messages=list(kwargs.get("messages") or [])
        + [{"role": "assistant", "content": "OK"}],
        tool_trace=[],
    )


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Mirror the chat-handler suite's rate-limit isolation."""
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def test_arbitration_completes_when_corpus_unavailable(
    monkeypatch, tmp_path,
):
    """The chat handler must complete arbitration successfully when
    ``forge_bridge.corpus`` is structurally absent.

    Asserts:
      - Status code is exactly 200.
      - Response body is JSON-parseable.
      - Response envelope matches the success shape (``messages``,
        ``stop_reason``, ``request_id``).
      - No exception propagates from the corpus-import attempt.
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

    # If the reimport itself raises, the no-dependency property has
    # been violated. The assertion here is: the import succeeds.
    importlib.import_module(_HANDLER_MODULE)

    # Build a fresh app under the sentinel patch.
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(side_effect=_stub_chat_result)
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
        new=AsyncMock(return_value=[_make_test_tool()]),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ):
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    # Tightened assertion (per converged review): framing §1.4
    # protects arbitration non-dependency, not merely graceful
    # degradation. Persistent 500/error-envelope behavior when
    # corpus is absent would represent the exact architectural
    # collapse this test exists to prevent.
    assert response.status_code == 200, (
        f"chat handler returned status {response.status_code} "
        f"when forge_bridge.corpus is structurally absent; expected "
        f"200. Per A.5.3.2-PR4-FRAMING.md §1.4, arbitration must "
        f"complete successfully — not merely degrade gracefully — "
        f"when capture infrastructure is unavailable. Body: "
        f"{response.text!r}"
    )
    body = response.json()
    assert isinstance(body, dict), (
        f"chat handler response is not a JSON object: {body!r}"
    )
    for required_key in ("messages", "stop_reason", "request_id"):
        assert required_key in body, (
            f"chat handler success envelope missing required key "
            f"{required_key!r}: {body!r}. Per A.5.3.2-PR4-FRAMING.md "
            f"§1.4, the chat handler must produce a well-formed "
            f"success response when forge_bridge.corpus is "
            f"structurally absent — never a malformed envelope."
        )
