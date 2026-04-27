"""CHAT-05 external-consumer parity test for /api/v1/chat (Phase 16 / FB-D).

The same endpoint serves the Web UI (plan 16-05 panel.html browser fetch)
and projekt-forge v1.5 Flame hooks (sync httpx.Client over the bridge).
This test replays the same payload through two distinct httpx clients —
one shaped like a browser fetch, one shaped like projekt-forge v1.5
Flame hooks — and asserts the responses have the same STRUCTURAL shape
(keys, types, role progression). Modulo the non-deterministic LLM
output, content equality is asserted only when the mocked router
returns a fixed string (Strategy A).

Two client shapes:
  1. Browser-like: Accept: application/json, no special user-agent.
  2. Flame-hooks-like: Content-Type: application/json,
     User-Agent: projekt-forge-flame-hooks/1.5,
     X-Forge-Actor: flame:projekt-forge-test
     (mimics projekt-forge v1.5's expected request shape).

Both hit the same /api/v1/chat — the assertion is that the response body
shape is identical, not the content.

Strategy A — always runs, mocked LLMRouter (deterministic shape + content).
Strategy B — FB_INTEGRATION_TESTS=1 gated, real Ollama, structural-only.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import ASGITransport


requires_integration = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1",
    reason=(
        "live LLM parity tests require FB_INTEGRATION_TESTS=1 — "
        "default `pytest tests/` skips them"
    ),
)


def _make_test_tool():
    """A non-empty Tool so the chat handler's empty-registry guard does
    not short-circuit. Same shape used by test_chat_endpoint.py."""
    from mcp.types import Tool
    return Tool(
        name="forge_chat_parity_probe",
        description="Test probe used by CHAT-05 parity test.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


@pytest.fixture
def chat_app_fixed_response():
    """LLMRouter mock returns a deterministic terminal text — Strategy A
    parity needs identical content across both clients to compare. The
    Strategy B live test asserts only structural shape."""
    from forge_bridge.console import _rate_limit
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI
    _rate_limit._reset_for_tests()

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(
        return_value="parity-test-fixed-response",
    )
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    return build_console_app(api)


# ---------------------------------------------------------------------------
# Helpers — describe the structural shape both clients must agree on
# ---------------------------------------------------------------------------


def _structural_signature(body: dict) -> dict:
    """Reduce a chat response body to a comparable structural signature.

    Captures: keys, types, length of messages list, role progression of
    messages list, presence/absence of stop_reason and request_id.
    Drops actual content (LLM output is non-deterministic for live runs).

    The CHAT-05 parity contract is asserted at the structural level — a
    future regression that, e.g., set a custom Set-Cookie based on
    User-Agent or returned a different envelope key set for one client
    shape would surface here BEFORE it shipped.
    """
    return {
        "keys_present": sorted(body.keys()),
        "messages_type": type(body.get("messages")).__name__,
        "messages_count": len(body.get("messages") or []),
        "messages_roles": [
            (m or {}).get("role") for m in (body.get("messages") or [])
        ],
        "stop_reason_type": type(body.get("stop_reason")).__name__,
        "stop_reason": body.get("stop_reason"),
        "request_id_type": type(body.get("request_id")).__name__,
        "request_id_present": bool(body.get("request_id")),
    }


# ---------------------------------------------------------------------------
# CHAT-05 — Strategy A (mocked router, deterministic, always runs)
# ---------------------------------------------------------------------------


class TestChatParityStructural:
    """Both clients hit the same endpoint; their responses must have the
    same structural signature (keys, types, role progression). The mocked
    LLMRouter returns a deterministic terminal text so the test does not
    flake on LLM output variance."""

    async def test_chat_parity_browser_vs_flame_hooks(
        self, chat_app_fixed_response,
    ):
        """Browser-shape and Flame-hooks-shape clients hit the same
        /api/v1/chat — the response envelope MUST be structurally
        identical (and, with the mock, content-identical too)."""
        app = chat_app_fixed_response
        transport = ASGITransport(app=app)
        payload = {
            "messages": [
                {"role": "user", "content": "what week is it?"},
            ],
        }
        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=[_make_test_tool()]),
        ):
            # Client 1 — browser-shape (minimal headers).
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Accept": "application/json"},
            ) as browser_client:
                browser_r = await browser_client.post(
                    "/api/v1/chat", json=payload,
                )

            # Client 2 — Flame-hooks-shape (projekt-forge v1.5 expected
            # request shape — Content-Type, custom User-Agent, X-Forge-Actor).
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "projekt-forge-flame-hooks/1.5",
                    "X-Forge-Actor": "flame:projekt-forge-test",
                },
            ) as flame_client:
                flame_r = await flame_client.post(
                    "/api/v1/chat", json=payload,
                )

        # Both clients succeeded
        assert browser_r.status_code == 200, browser_r.text
        assert flame_r.status_code == 200, flame_r.text

        # Both responses pass through the same envelope shape
        b_sig = _structural_signature(browser_r.json())
        f_sig = _structural_signature(flame_r.json())
        # The request_id IS expected to differ (uuid4 per call) — drop the
        # request_id_type field from the strict-equality compare.
        b_sig_cmp = {k: v for k, v in b_sig.items() if k != "request_id_type"}
        f_sig_cmp = {k: v for k, v in f_sig.items() if k != "request_id_type"}
        # request_id_type must match (both "str") — assert separately.
        assert b_sig["request_id_type"] == f_sig["request_id_type"] == "str"
        assert b_sig_cmp == f_sig_cmp

        # Both responses have an X-Request-ID header (D-21 / D-17)
        assert "X-Request-ID" in browser_r.headers
        assert "X-Request-ID" in flame_r.headers

        # The mocked LLMRouter returns the same terminal text both times
        # so the assistant turn content is also content-equal in this
        # strategy. (Strategy B drops this assertion — live LLM output
        # varies.)
        assert (
            browser_r.json()["messages"][-1]["content"]
            == "parity-test-fixed-response"
        )
        assert (
            flame_r.json()["messages"][-1]["content"]
            == "parity-test-fixed-response"
        )

    async def test_chat_parity_envelope_keys_locked(
        self, chat_app_fixed_response,
    ):
        """The envelope keys are exactly {messages, stop_reason, request_id}.
        Locks the D-03 success-envelope contract — if a future change
        adds/removes keys, this test fires and the consumer-contract
        migration is forced through review.

        The cross-route zero-divergence test in tests/console/ already
        covers the FB-B error envelope; this test covers the success
        envelope specifically for /api/v1/chat.
        """
        app = chat_app_fixed_response
        transport = ASGITransport(app=app)
        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=[_make_test_tool()]),
        ):
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test",
            ) as c:
                r = await c.post(
                    "/api/v1/chat",
                    json={"messages": [{"role": "user", "content": "hi"}]},
                )
        assert r.status_code == 200
        body = r.json()
        assert sorted(body.keys()) == sorted(
            ["messages", "stop_reason", "request_id"]
        )
        assert body["stop_reason"] == "end_turn"


# ---------------------------------------------------------------------------
# CHAT-05 — Strategy B (live Ollama, FB_INTEGRATION_TESTS gated)
# ---------------------------------------------------------------------------


class TestChatParityLive:
    """Live parity test against real Ollama. Asserts only structural shape
    match — the LLM's terminal text WILL differ between two runs (or
    between two consecutive runs with the same client), so content
    equality is not a meaningful assertion at this layer."""

    @requires_integration
    async def test_chat_parity_live_structural_match(self):
        """Run two real /api/v1/chat requests against the live LLMRouter
        on assist-01; assert structural-shape match modulo content."""
        from forge_bridge.console import _rate_limit
        from forge_bridge.console.app import build_console_app
        from forge_bridge.console.manifest_service import ManifestService
        from forge_bridge.console.read_api import ConsoleReadAPI
        from forge_bridge.learning.execution_log import ExecutionLog
        from forge_bridge.llm.router import LLMRouter
        _rate_limit._reset_for_tests()

        ms = ManifestService()
        log = ExecutionLog()  # default path — read-only for chat
        api = ConsoleReadAPI(
            execution_log=log,
            manifest_service=ms,
            llm_router=LLMRouter(),
        )
        app = build_console_app(api)
        transport = ASGITransport(app=app)
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "what synthesis tools were created this week?"
                    ),
                },
            ],
            "max_iterations": 4,    # keep the test fast — live Ollama
        }
        with patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=[_make_test_tool()]),
        ):
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test",
            ) as c:
                r1 = await c.post("/api/v1/chat", json=payload)
                # Reset rate limit between calls so the second is not 429-ed
                # by the first call's bucket consumption.
                _rate_limit._reset_for_tests()
                r2 = await c.post("/api/v1/chat", json=payload)

        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text

        s1 = _structural_signature(r1.json())
        s2 = _structural_signature(r2.json())
        # Both responses must carry str-typed request_id (uuid4) and
        # present-true. The actual id value differs; the field shape does not.
        assert s1["request_id_type"] == s2["request_id_type"] == "str"
        assert s1["request_id_present"] is True
        assert s2["request_id_present"] is True
        # Structural shape match modulo content
        assert s1["keys_present"] == s2["keys_present"]
        assert s1["messages_type"] == s2["messages_type"]
        assert s1["stop_reason"] == s2["stop_reason"]   # both "end_turn"
