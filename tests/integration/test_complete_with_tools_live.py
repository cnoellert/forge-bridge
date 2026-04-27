"""LLMTOOL-01 and LLMTOOL-02: env-gated live integration tests.

Per FB-C D-32: these tests run ONLY when env vars are set, so the default
`pytest tests/` developer experience continues to work without requiring a
live Ollama daemon or an Anthropic API key.

Env-var contract (codified here for FB-C; future live integration tests in
phases 16+ should mirror this convention):

  FB_INTEGRATION_TESTS=1
      Required for ANY live integration test in this directory.
      Acts as the master gate — without it, all tests in tests/integration/
      are skipped at collection time.

  ANTHROPIC_API_KEY=sk-...
      Additionally required for the LLMTOOL-02 (Anthropic cloud) test.
      The Ollama test only needs FB_INTEGRATION_TESTS=1 plus a reachable
      Ollama daemon at FORGE_LOCAL_LLM_URL (default http://localhost:11434/v1).

Run on assist-01 (the canonical local LLM hardware host):

    # Ollama-only (LLMTOOL-01):
    FB_INTEGRATION_TESTS=1 pytest tests/integration/

    # Both Ollama + Anthropic (LLMTOOL-01 + LLMTOOL-02):
    FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=sk-... pytest tests/integration/

Local developer laptop (default):

    pytest tests/   # both tests SKIPPED — no Ollama or Anthropic dep needed

Acceptance per ROADMAP success criteria 1 (LLMTOOL-01) + 2 (LLMTOOL-02):
the loop must (1) call the registered tool, (2) receive its result, (3)
return a terminal text response that incorporates recognizable evidence
from the tool result (proves the LLM saw the tool result and used it,
ruling out a hallucinated answer that ignored the tool entirely).
"""
from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Env-gating skip markers (the greenfield pattern this file codifies)
# ---------------------------------------------------------------------------


requires_integration = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1",
    reason=(
        "live LLM integration tests require FB_INTEGRATION_TESTS=1 — "
        "default `pytest tests/` skips them so developers without Ollama "
        "or Anthropic credentials get a clean run"
    ),
)

requires_anthropic = pytest.mark.skipif(
    (
        os.environ.get("FB_INTEGRATION_TESTS") != "1"
        or not os.environ.get("ANTHROPIC_API_KEY")
    ),
    reason=(
        "LLMTOOL-02 cloud test requires FB_INTEGRATION_TESTS=1 AND ANTHROPIC_API_KEY"
    ),
)


# ---------------------------------------------------------------------------
# Test tool — a deterministic in-test executor that returns a known string.
# Both live tests use this so we can assert the LLM's terminal text shows
# evidence of the tool result (proving the loop actually fed the result back
# to the model rather than the model hallucinating an answer that ignored it).
# ---------------------------------------------------------------------------


# A unique sentinel string the LLM cannot plausibly produce without seeing
# the tool result. We assert this substring appears in the terminal text.
_SENTINEL_RESULT = "FORGE-INTEGRATION-SENTINEL-XJK29Q"


def _build_test_tool():
    """Build a mcp.types.Tool that the LLM should invoke to learn the sentinel."""
    from mcp.types import Tool
    return Tool(
        name="forge_get_integration_secret",
        description=(
            "Returns a unique integration-test sentinel string. "
            "Call this tool with no arguments to get the secret value, then "
            "include the secret value verbatim in your final response."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )


async def _executor(name: str, args: dict) -> str:
    """In-test tool_executor — returns the sentinel for our one fake tool."""
    if name == "forge_get_integration_secret":
        return _SENTINEL_RESULT
    raise KeyError(f"unexpected tool name in integration test: {name!r}")


# ---------------------------------------------------------------------------
# LLMTOOL-01 — Ollama (local, sensitive=True) live test
# ---------------------------------------------------------------------------


@requires_integration
@pytest.mark.asyncio
async def test_ollama_tool_call_loop_live():
    """LLMTOOL-01 / ROADMAP success criterion 1.

    Two-step loop: LLM calls forge_get_integration_secret with no args,
    receives the sentinel string, returns a terminal text response that
    includes the sentinel substring.

    Backend: Ollama daemon at FORGE_LOCAL_LLM_URL (default http://localhost:11434/v1).
    Model: FORGE_LOCAL_MODEL (default qwen2.5-coder:32b per FB-C D-28).

    Skipped unless FB_INTEGRATION_TESTS=1.
    Should be run on assist-01 (the canonical hardware host) per the v1.4
    UAT plan; runs anywhere Ollama+qwen2.5-coder:32b is reachable.
    """
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()  # picks up FORGE_LOCAL_MODEL etc. from env or defaults
    tools = [_build_test_tool()]

    response = await router.complete_with_tools(
        prompt=(
            "Call the forge_get_integration_secret tool to learn the secret value, "
            "then tell me what value the tool returned. Include the value verbatim."
        ),
        tools=tools,
        sensitive=True,                   # routes to Ollama per D-01
        tool_executor=_executor,          # use our in-test executor
        max_iterations=4,                 # two-step loop fits in 4 with headroom
        max_seconds=60.0,                 # qwen2.5-coder:32b on assist-01 is fast
    )

    assert isinstance(response, str) and response, (
        f"complete_with_tools returned empty / non-string: {response!r}"
    )
    assert _SENTINEL_RESULT in response, (
        f"LLMTOOL-01 acceptance failed: terminal response does NOT contain "
        f"sentinel '{_SENTINEL_RESULT}'. Either the LLM didn't call the tool, "
        f"or didn't incorporate its result. Got: {response[:500]!r}"
    )


# ---------------------------------------------------------------------------
# LLMTOOL-02 — Anthropic (cloud, sensitive=False) live test
# ---------------------------------------------------------------------------


@requires_anthropic
@pytest.mark.asyncio
async def test_anthropic_tool_call_loop_live():
    """LLMTOOL-02 / ROADMAP success criterion 2.

    Same prompt + tool schema as LLMTOOL-01 but routed to Anthropic
    (sensitive=False). Verifies cloud-path parity with the local path.

    Backend: api.anthropic.com via the AsyncAnthropic SDK.
    Model: FORGE_CLOUD_MODEL (default claude-opus-4-6 per FB-C D-30).
    Auth: ANTHROPIC_API_KEY env var (consumed by AsyncAnthropic SDK directly).

    Skipped unless FB_INTEGRATION_TESTS=1 AND ANTHROPIC_API_KEY is set.
    """
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()  # picks up FORGE_CLOUD_MODEL etc. from env or defaults
    tools = [_build_test_tool()]

    response = await router.complete_with_tools(
        prompt=(
            "Call the forge_get_integration_secret tool to learn the secret value, "
            "then tell me what value the tool returned. Include the value verbatim."
        ),
        tools=tools,
        sensitive=False,                  # routes to Anthropic per D-01
        tool_executor=_executor,
        max_iterations=4,
        max_seconds=60.0,
    )

    assert isinstance(response, str) and response, (
        f"complete_with_tools returned empty / non-string: {response!r}"
    )
    assert _SENTINEL_RESULT in response, (
        f"LLMTOOL-02 acceptance failed: terminal response does NOT contain "
        f"sentinel '{_SENTINEL_RESULT}'. Either the LLM didn't call the tool, "
        f"or didn't incorporate its result. Got: {response[:500]!r}"
    )


# ---------------------------------------------------------------------------
# Sanity: env-gating works (ALWAYS runs — no env required, just verifies
# that the skipif markers are correctly defined as marker objects, not
# accidentally as decorators that swallowed something).
# ---------------------------------------------------------------------------


def test_env_gating_markers_are_skipif_marks():
    """Standing regression guard for the env-gating pattern itself.

    If a future contributor accidentally inverts the skipif logic (e.g.,
    `os.environ.get("X") == "1"` instead of `!= "1"`) the tests would run on
    laptops without backends and fail noisily. This test ensures the markers
    exist as proper skipif Marks; the SKIP behavior itself is verified by
    just running `pytest tests/integration/` without env vars (both tests
    above show SKIPPED, this one PASSES).
    """
    assert hasattr(requires_integration, "name") and requires_integration.name == "skipif"
    assert hasattr(requires_anthropic, "name") and requires_anthropic.name == "skipif"
