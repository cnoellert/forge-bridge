"""Phase 16.1 (D-07 #3) — Strategy B chat E2E.

Drives the full chat path with REAL LLMRouter() + REAL mcp.list_tools()
(post Plan 01 backend-aware filter) through httpx.AsyncClient(ASGITransport).
Plugs the Bug A/B/C automated-coverage gap that Phase 16 missed in deploy.

WHAT THIS TEST COVERS:
  - The full /api/v1/chat handler path including Plan 01's
    filter_tools_by_reachable_backends() (REAL TCP probe, no stub).
  - LLMRouter routing to live Ollama (qwen2.5-coder:32b, sensitive=True).
  - The real mcp.list_tools() registry snapshot (49 tools pre-filter).
  - Response structural shape — stop_reason, messages envelope, content
    quality proxy (length >= 40 chars, no rate-limit fallback).

WHY NO MOCKS BELOW THE HTTP BOUNDARY:
  Phase 16 deploy bugs A/B/C were all invisible to mocked-router tests:
  - Bug A (Starlette TemplateResponse incompat) — always-on render smoke test
    catches this class now (tests/console/test_ui_handlers_render.py).
  - Bug B (LLMRouter never wired into ConsoleReadAPI) — boot-wiring smoke test
    catches this class (tests/console/test_lifespan_wiring.py).
  - Bug C (49-tool hang) — THIS TEST catches this class. A mocked router would
    return immediately regardless of the tool list. Only a REAL router + REAL
    registry + REAL Ollama can reveal the hang.

Gate: FB_INTEGRATION_TESTS=1 + Ollama reachable at http://localhost:11434.
Skipped on dev machines without Ollama. Ollama-only — sensitive=True locked
for v1.4 (16-CONTEXT D-05).

Pitfall 9 (16.1-RESEARCH §6): preload qwen2.5-coder:32b before running on
assist-01 — first call adds 10-30s cold start which can blow the <60s budget:
    ollama run qwen2.5-coder:32b "warm" >/dev/null 2>&1

How to run on assist-01:
    ollama run qwen2.5-coder:32b "warm" >/dev/null 2>&1
    FB_INTEGRATION_TESTS=1 pytest tests/integration/test_chat_endpoint_live.py -v --tb=short

Expected on dev machine (no Ollama):
    pytest tests/integration/test_chat_endpoint_live.py -v  # → 1 SKIPPED
"""
from __future__ import annotations

import os
import re
import time
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

# ---------------------------------------------------------------------------
# Environment-gate skip markers — reused verbatim from Phase 15 FB-C convention
# (tests/integration/test_complete_with_tools_live.py:49-66)
# ---------------------------------------------------------------------------

requires_integration = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1",
    reason=(
        "live LLM integration tests require FB_INTEGRATION_TESTS=1 — "
        "default `pytest tests/` skips them so developers without Ollama "
        "or Anthropic credentials get a clean run"
    ),
)


def _ollama_reachable() -> bool:
    """Defense-in-depth: verify Ollama daemon is up before running any test."""
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_reachable(),
    reason="Ollama daemon not reachable at http://localhost:11434",
)


# ---------------------------------------------------------------------------
# Phase 16.2 Bug D regression-guard regex (D-06 #1)
# ---------------------------------------------------------------------------

# Matches the canonical Bug D failure shape: a terminal assistant response
# whose content begins with a JSON object containing a "name" key — i.e.,
# the LLM emitted a tool call as text and the adapter / loop failed to
# execute it. Permissive whitespace handling covers pretty-printed variants.
# See Phase 16.2 D-06 #1; the exact captured shape is recorded at
#   .planning/phases/16.2-bug-d-chat-tool-call-loop/16.2-CAPTURED-OLLAMA-RESPONSE.json
# CONTEXT D-07 explicitly rejects natural-prose-detection heuristics; this
# regex is surgical — it fires on the exact symptom and not on legitimate
# short answers like "yes" or numeric responses.
_BUG_D_TERMINAL_JSON_RE = re.compile(r'^\s*\{\s*"name"\s*:', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Fixture: REAL LLMRouter + REAL mcp.list_tools() — no mocks below HTTP
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def live_chat_client():
    """Build the console app with a REAL LLMRouter() and let chat_handler
    call the REAL mcp.list_tools() registry (post Plan 01 backend-aware filter).

    No mocks below the HTTP boundary — this is the Strategy B pattern.

    Pitfall 9: preload qwen2.5-coder:32b on assist-01 before running this
    fixture. First call without preload adds 10-30s cold start which can blow
    the <60s budget assertion.

    The only mock here is execution_log (a ManifestService dependency that
    records operations — we don't need a real DB for the chat surface test).
    """
    from forge_bridge.console import _rate_limit
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI
    from forge_bridge.console.resources import register_console_resources
    from forge_bridge.llm.router import LLMRouter
    from forge_bridge.mcp.server import mcp as mcp_server

    _rate_limit._reset_for_tests()

    # Reset the tool-filter cache so this test gets a fresh probe instead of
    # inheriting a stale cache entry from a prior test run in the same process.
    try:
        from forge_bridge.console._tool_filter import _reset_for_tests as _filter_reset

        _filter_reset()
    except ImportError:
        pass  # Plan 01 not present — test will fail downstream with a useful message

    real_router = LLMRouter()  # pure env-reading init, no I/O at construction

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)

    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=real_router,  # REAL router — not a mock
    )
    app = build_console_app(api)

    # Mirror _lifespan's Step 5: register the 7 in-process console tools that
    # the backend-aware filter relies on for graceful degradation when the
    # Flame bridge (:9999) is unreachable. Without this call only backend-
    # dependent tools exist in mcp.list_tools(), the filter drops them all,
    # and the handler returns 503. Production goes through _lifespan which
    # always runs this; the test would silently mock it away otherwise.
    register_console_resources(mcp_server, ms, api)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=130.0,  # outer cap: 125s asyncio.wait_for + 5s framing
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# CHAT-04 / 16.1 success criterion 4: canonical UAT prompt under 60s
# ---------------------------------------------------------------------------


@requires_integration
@requires_ollama
@pytest.mark.asyncio
async def test_chat_canonical_uat_prompt_under_60s(live_chat_client: httpx.AsyncClient) -> None:
    """ROADMAP CHAT-04 / 16.1 success criterion 4.

    Drives the canonical UAT prompt through the full chat path:
      POST /api/v1/chat  →  chat_handler  →  filter_tools_by_reachable_backends
        →  complete_with_tools(REAL LLMRouter, REAL tools)  →  live Ollama
        →  structured JSON response

    Structural proxy for "useful response" (D-07 #3):
      - stop_reason == "end_turn" (NOT loop_budget_exceeded)
      - assistant content is a non-error string >= 40 chars
      - elapsed < 60s (the CHAT-04 budget)
      - no rate-limit fallback in the content

    Quality grading is the human UAT (Plan 05 / D-12 fresh-operator gate).
    This test only asserts structural correctness — the LLM's answer quality
    is not machine-gradable.

    This test closes the Bug C automated-coverage gap: a mocked router would
    return immediately regardless of tool count; only a real router + real
    registry + real Ollama can reveal the 49-tool hang.
    """
    start = time.monotonic()
    r = await live_chat_client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "what synthesis tools were created this week?",
                }
            ]
        },
    )
    elapsed = time.monotonic() - start

    assert r.status_code == 200, (
        f"non-200: {r.status_code}\n{r.text[:500]}"
    )

    body = r.json()

    assert body["stop_reason"] == "end_turn", (
        f"expected stop_reason=end_turn, got {body.get('stop_reason')!r}. "
        f"Full body: {body}"
    )

    messages = body.get("messages", [])
    assert messages, f"response has no messages: {body}"

    final_msg = messages[-1]
    assert final_msg["role"] == "assistant", (
        f"last message is not from assistant: {final_msg}"
    )

    content = final_msg.get("content", "")
    assert isinstance(content, str), (
        f"content is not a string: {type(content)} — {content!r}"
    )
    assert len(content) >= 40, (
        f"response too short to be 'useful' (got {len(content)} chars): {content!r}"
    )
    assert "rate limit" not in content.lower(), (
        f"rate-limit fallback text leaked into response: {content!r}"
    )

    # Phase 16.2 D-06 #1: reject raw tool-call JSON as terminal content.
    # Phase 16.1 HUMAN-UAT recorded `{"name": "forge_tools_read", ...}` as
    # the assistant's terminal text on assist-01 — a 57-char string that
    # satisfies len(content) >= 40 and stop_reason == "end_turn" but is NOT
    # a useful answer. Strengthen the assertion to fail on this exact shape.
    assert not _BUG_D_TERMINAL_JSON_RE.match(content), (
        f"Bug D regression — terminal content is raw tool-call JSON, not a "
        f"natural-language answer. The Ollama adapter likely failed to salvage "
        f"a text-shaped tool call (see Phase 16.2 D-03 + Phase 16.1 HUMAN-UAT). "
        f"Content: {content!r}"
    )

    # Phase 16.2 D-06 #2 was originally a loop-iteration check on the messages[]
    # array (require >=1 role=tool + >=2 role=assistant). Dropped 2026-04-28
    # during the Plan 04 fresh-operator UAT on assist-01: the chat API response
    # exposes only [user_input, final_assistant_answer] — intermediate tool and
    # assistant turns happen inside LLMRouter.complete_with_tools() and are NOT
    # forwarded into body["messages"]. The assertion as planned could not
    # succeed against any healthy response, only against itself. D-06 #1 above
    # is the load-bearing Bug D guard; iteration is implicit in producing a
    # useful natural-language answer rather than raw JSON. Server-side iteration
    # evidence (router.py "iter=N" log markers) is captured in 16.2-HUMAN-UAT.md
    # rather than re-encoded here.

    assert elapsed < 60.0, (
        f"CHAT-04 budget exceeded: {elapsed:.1f}s > 60.0s. "
        f"Response content (first 300 chars): {content[:300]!r}"
    )
