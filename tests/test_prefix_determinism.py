"""Phase 24.1 — prefix determinism for KV-cache-aware runtime.

Two substrate-level invariants that together stabilize the prefix
(``{system, tools_compiled}``) sent to the Ollama backend on every
chat request:

  1. ``mcp.list_tools()`` returns a stable order across consecutive
     calls. Closes ``.planning/COLD-START-INVESTIGATION.md`` open
     question #1: "Does mcp.list_tools() return a stable ordering
     across requests?" The investigation believed-but-did-not-assert
     this property; this test asserts it.
  2. ``OllamaToolAdapter._compile_tools`` sorts tools alphabetically
     by name regardless of input order. Closes COLD-START
     recommendation #1 tactic 1: sort at the compilation boundary so
     reachability/filter ordering can't leak into the prefix.

Without these invariants, every request can produce a different prefix
even when nothing in the underlying tool registry changed — which
busts Ollama's KV-cache prefix match and turns every chat into a
~3.5s prompt-eval miss instead of a 0.05s cache hit (70x slowdown
documented in the investigation, p. 76-87).

This file does NOT assert prompt-eval timing (that's backend behavior,
not substrate). It asserts the substrate properties the cache relies
on. Cache hit/miss measurement remains an operational concern.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from forge_bridge.llm._adapters import OllamaToolAdapter


# ── Invariant 1: mcp.list_tools() stable ordering ────────────────────────


@pytest.mark.asyncio
async def test_mcp_list_tools_returns_stable_order_across_calls():
    """Consecutive ``list_tools()`` calls against the same registry
    produce identical ordering. If this ever fails, every chat request
    silently busts the KV cache because the tool list arrives in a
    different order; the bridge would be doing ~3.5s of cache-miss
    prompt-eval per call for no semantic reason."""
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("test")
    register_builtins(mcp)

    tools_a = await mcp.list_tools()
    tools_b = await mcp.list_tools()
    tools_c = await mcp.list_tools()

    names_a = [t.name for t in tools_a]
    names_b = [t.name for t in tools_b]
    names_c = [t.name for t in tools_c]

    assert names_a == names_b == names_c, (
        f"mcp.list_tools() must return stable ordering; "
        f"call A: {names_a}\ncall B: {names_b}\ncall C: {names_c}"
    )
    # Sanity: more than one tool registered (otherwise stability is
    # trivially satisfied and the test would silently lose its bite).
    assert len(names_a) >= 5, (
        f"register_builtins should register multiple tools; "
        f"saw only {len(names_a)}: {names_a}"
    )


# ── Invariant 2: _compile_tools alphabetical-sort discipline ────────────


class _FakeTool:
    """Mimic the duck-typed Tool object ``_compile_tools`` consumes."""
    def __init__(self, name: str, description: str = "", inputSchema: dict | None = None):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema if inputSchema is not None else {"type": "object"}


def test_compile_tools_sorts_by_name_regardless_of_input_order():
    """Whatever the upstream filter chain returns (reachability flip,
    PR14 narrow, PR21 disambiguator, set-iteration leak, etc.),
    ``_compile_tools`` emits a canonical alphabetical order. Without
    this, each request's prefix is filter-state-dependent and the KV
    cache misses on every call."""
    adapter = OllamaToolAdapter(MagicMock(), "qwen2.5-coder:32b")

    expected_order = [
        "flame_context",
        "flame_execute_python",
        "flame_list_desktop",
        "forge_get_project",
        "forge_list_staged",
    ]

    permutations = [
        # already-sorted forward
        [_FakeTool(n) for n in expected_order],
        # reverse-sorted
        [_FakeTool(n) for n in reversed(expected_order)],
        # arbitrary scramble
        [_FakeTool(n) for n in [
            "forge_list_staged",
            "flame_context",
            "forge_get_project",
            "flame_execute_python",
            "flame_list_desktop",
        ]],
        # another scramble (catches accidental partial-sort bugs)
        [_FakeTool(n) for n in [
            "flame_list_desktop",
            "forge_list_staged",
            "flame_context",
            "forge_get_project",
            "flame_execute_python",
        ]],
    ]

    for perm in permutations:
        compiled = adapter._compile_tools(perm)
        names = [c["function"]["name"] for c in compiled]
        assert names == expected_order, (
            f"compiled order {names} != expected {expected_order} "
            f"on input perm {[t.name for t in perm]}"
        )


def test_compile_tools_is_stable_across_repeated_calls_with_same_input():
    """Same input list produces same output across multiple calls.
    Pins the contract at our surface — Python's Timsort IS stable on
    equal keys, but the assertion guards against future
    implementations that might use an unstable sort or set-based
    intermediate."""
    adapter = OllamaToolAdapter(MagicMock(), "qwen2.5-coder:32b")
    tools = [_FakeTool("c"), _FakeTool("a"), _FakeTool("b")]

    out_a = [c["function"]["name"] for c in adapter._compile_tools(tools)]
    out_b = [c["function"]["name"] for c in adapter._compile_tools(tools)]
    out_c = [c["function"]["name"] for c in adapter._compile_tools(tools)]

    assert out_a == out_b == out_c == ["a", "b", "c"]


def test_compile_tools_empty_input_compiles_to_empty():
    """Edge: empty tools list compiles to empty output; sort doesn't
    crash on empty input."""
    adapter = OllamaToolAdapter(MagicMock(), "qwen2.5-coder:32b")
    assert adapter._compile_tools([]) == []


def test_compile_tools_single_tool_unchanged_by_sort():
    """Edge: single tool returns single-element compiled list with
    the tool's name preserved."""
    adapter = OllamaToolAdapter(MagicMock(), "qwen2.5-coder:32b")
    compiled = adapter._compile_tools([_FakeTool("only")])
    assert len(compiled) == 1
    assert compiled[0]["function"]["name"] == "only"
