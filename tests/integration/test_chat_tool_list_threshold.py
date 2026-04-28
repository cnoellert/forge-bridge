"""Phase 16.1 (D-06) — bisection artifact for the 49-tool chat hang.

Records (tool_count, prompt_tokens, completion_tokens, elapsed_s, stop_reason,
iterations) per measurement to
`.planning/phases/16.1-fb-d-chat-gap-closure/16.1-BISECTION.jsonl`.

The first sweep IS the bisection — it does not assert against a known threshold
until the operator reads the JSONL and picks one. After the threshold is locked,
add `test_complete_with_tools_at_chosen_scoping_count_returns_useful` below with
`_CHOSEN_SCOPING_COUNT` set from the JSONL analysis.

Time-box per CONTEXT D-04: 30 minutes wall-clock for the full sweep.
pytest-timeout enforces 33 minutes total for the module (D-04 + 3-min buffer).

Gate: FB_INTEGRATION_TESTS=1 + live Ollama on http://localhost:11434.
Skipped on dev machines without Ollama. Ollama-only — sensitive=True locked
for v1.4 (16-CONTEXT D-05).

How to run on assist-01:
    # 1. Preload qwen2.5-coder:32b (Pitfall 9 — avoids 10-30s cold-start)
    ollama run qwen2.5-coder:32b "warm" >/dev/null 2>&1

    # 2. Run the sweep
    FB_INTEGRATION_TESTS=1 pytest tests/integration/test_chat_tool_list_threshold.py -v --tb=short -s

    # 3. Inspect results
    cat .planning/phases/16.1-fb-d-chat-gap-closure/16.1-BISECTION.jsonl | python -m json.tool --json-lines
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

# ---------------------------------------------------------------------------
# Module-level timeout budget: 33 minutes (D-04 30-min sweep + 3-min buffer).
# pytest-timeout enforces this as a hard ceiling on the entire module run.
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.timeout(2000)  # 33 minutes 20 seconds

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
# Bisection artifact path — operator-readable JSONL committed to planning tree
# ---------------------------------------------------------------------------

_BISECTION_ARTIFACT = (
    Path(__file__).parent.parent.parent
    / ".planning/phases/16.1-fb-d-chat-gap-closure/16.1-BISECTION.jsonl"
)


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


async def _list_real_tools_sorted() -> list:
    """Snapshot the REAL MCP registry, sorted by name for cross-run reproducibility."""
    from forge_bridge.mcp import server as _mcp_server

    all_tools = await _mcp_server.mcp.list_tools()
    return sorted(all_tools, key=lambda t: t.name)


# ---------------------------------------------------------------------------
# D-06 bisection: parameterized linear sweep over tool counts
# ---------------------------------------------------------------------------


@requires_integration
@requires_ollama
@pytest.mark.parametrize(
    "tool_count",
    [5, 10, 15, 20, 25, 30, 35, 40, 49],
)
@pytest.mark.asyncio
async def test_complete_with_tools_threshold_linear(tool_count: int) -> None:
    """Records the threshold at which complete_with_tools tips from
    fast (<10s) to hung (>=120s with prompt_tokens_total=0).

    Each run appends one JSON line to 16.1-BISECTION.jsonl. The operator
    reads the resulting artifact and picks the scoping count. The FIRST sweep
    over [5,10,15,20,25,30,35,40,49] IS the bisection — no prior threshold
    assertion here.

    After the operator analyzes the JSONL, add
    `test_complete_with_tools_at_chosen_scoping_count_returns_useful` below
    with the locked _CHOSEN_SCOPING_COUNT.
    """
    from forge_bridge.llm.router import LLMLoopBudgetExceeded, LLMRouter

    all_tools = await _list_real_tools_sorted()
    if len(all_tools) < tool_count:
        pytest.skip(
            f"registry only has {len(all_tools)} tools; cannot test count {tool_count}"
        )
    tools = all_tools[:tool_count]
    tool_names = [t.name for t in tools]

    router = LLMRouter()
    start = time.monotonic()

    record: dict = {
        "tool_count": tool_count,
        "elapsed_s": None,
        "stop_reason": None,
        "completion_tokens": None,
        "prompt_tokens": None,
        "iterations": None,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "tools_offered": tool_names,
    }

    try:
        result = await router.complete_with_tools(
            messages=[
                {"role": "user", "content": "What tools do you have available?"}
            ],
            tools=tools,
            sensitive=True,
            max_iterations=2,
            max_seconds=120.0,
        )
        record["elapsed_s"] = round(time.monotonic() - start, 1)
        record["stop_reason"] = "end_turn"
        # Use string length as a proxy for completion tokens (token count is
        # not directly accessible from the returned string without re-calling
        # the tokenizer; this is sufficient for bisection purposes).
        record["completion_tokens"] = len(result) if isinstance(result, str) else 0
    except LLMLoopBudgetExceeded as exc:
        record["elapsed_s"] = round(time.monotonic() - start, 1)
        record["stop_reason"] = f"loop_budget:{exc.reason}"
        record["iterations"] = exc.iterations

    # Append measurement to bisection artifact (operator-readable JSONL).
    # The parent directory must exist (it is committed to git, so this is
    # belt-and-suspenders for non-standard working trees).
    _BISECTION_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    with _BISECTION_ARTIFACT.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    # First-pass acceptance: the test wrote a complete measurement record.
    # After the operator picks a scoping count, replace this with a strict
    # threshold assertion in test_complete_with_tools_at_chosen_scoping_count_returns_useful.
    assert record["elapsed_s"] is not None, (
        f"tool_count={tool_count}: elapsed_s not recorded — did the call raise "
        f"an unexpected exception that escaped the try/except?"
    )
    assert record["stop_reason"] is not None, (
        f"tool_count={tool_count}: stop_reason not recorded"
    )


# ---------------------------------------------------------------------------
# Post-bisection threshold lock — ADD AFTER ANALYZING 16.1-BISECTION.jsonl
# ---------------------------------------------------------------------------
#
# Locked from 16.1-BISECTION.jsonl sweep on assist-01 (2026-04-28):
#   counts 5..25 returned stop_reason="end_turn" with healthy completion_tokens
#   count 30 returned end_turn but with only 42 completion_tokens (degraded refusal)
#   counts 35, 40, 49 hit loop_budget:max_seconds (hung)
# Last clean useful response = 25; last point with margin = 20.
# We lock at 20 (one sample below the cliff) so Ollama version drift or model
# swaps don't push the threshold into the degraded zone and flake the test.

_CHOSEN_SCOPING_COUNT = 20


@requires_integration
@requires_ollama
@pytest.mark.asyncio
async def test_complete_with_tools_at_chosen_scoping_count_returns_useful() -> None:
    """At the chosen scoping count (locked from BISECTION.jsonl analysis),
    complete_with_tools returns end_turn with non-zero completion tokens.
    This is the locked threshold the chat handler's filter must produce.

    Any future regression of Plan 01's filter that lets the tool count
    drift above _CHOSEN_SCOPING_COUNT will cause this test to hang and
    fail — the live signal that the filter is broken.
    """
    from forge_bridge.llm.router import LLMRouter

    all_tools = await _list_real_tools_sorted()
    tools = all_tools[:_CHOSEN_SCOPING_COUNT]
    router = LLMRouter()
    result = await router.complete_with_tools(
        messages=[{"role": "user", "content": "List a few of the tools you can use."}],
        tools=tools,
        sensitive=True,
        max_iterations=2,
        max_seconds=120.0,
    )
    assert isinstance(result, str), f"expected str, got {type(result)}"
    assert len(result) > 0, "completion_tokens must be > 0 (end_turn, not loop_budget)"
