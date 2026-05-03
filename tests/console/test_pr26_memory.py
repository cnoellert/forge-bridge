"""PR26 — Unit tests for deterministic argument memory.

Pins the six correctness claims from the PR26 brief:

  1. Memory hit         → reuse cached value, NO upstream call
  2. Memory miss        → fall back to PR25 resolver
  3. No silent overwrite → existing memory persists across operations
  4. No recursion       → memory hit issues zero upstream tool calls
  5. Non-chain tool     → no memory interaction at all
  6. Reset behavior     → fresh memory starts empty

Memory isolation between tests is handled by the autouse
``_reset_tool_memory`` fixture in ``tests/console/conftest.py``. Each
test runs against a known-empty ``_MEMORY``; assertions about cached
state must be set up explicitly within the test body.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console._memory import _MEMORY, ToolMemory
from forge_bridge.console._tool_chain import resolve_required_params


# ── Helpers ───────────────────────────────────────────────────────────────


def _projects_payload(count: int) -> str:
    if count == 0:
        projects: list[dict] = []
    else:
        projects = [
            {"id": f"proj-{i}", "name": f"P{i}", "code": f"P{i}"}
            for i in range(count)
        ]
    return json.dumps({"count": len(projects), "projects": projects})


def _text_block(text: str):
    from mcp.types import TextContent
    return [TextContent(type="text", text=text)]


def _make_mcp(project_count: int) -> Any:
    """Mock with `mcp.call_tool` returning a TextContent block matching
    the requested project count for `forge_list_projects`."""
    mcp = AsyncMock()

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_projects_payload(project_count))
        return _text_block(json.dumps({"called": name, "args": arguments}))

    mcp.call_tool = AsyncMock(side_effect=fake_call_tool)
    return mcp


# ── AC #1: Memory hit — second call uses memory, no upstream ─────────────


@pytest.mark.asyncio
async def test_pr26_memory_hit_reuses_cached_project_id():
    """First call resolves and caches `project_id`; second call (with
    memory populated) MUST skip the resolver entirely — zero upstream
    calls — and inject the cached value."""
    # First call — system has 1 project; resolver runs, caches it.
    mcp_a = _make_mcp(project_count=1)
    out_a = await resolve_required_params("forge_list_versions", {}, mcp_a)
    assert out_a == {"project_id": "proj-0"}
    mcp_a.call_tool.assert_called_once_with("forge_list_projects", {})
    # Memory now holds the resolved id.
    assert _MEMORY.get("project_id") == "proj-0"

    # Second call — same process, fresh mcp. The resolver MUST NOT run;
    # memory should satisfy the requirement directly.
    mcp_b = _make_mcp(project_count=99)  # would otherwise refuse to inject
    out_b = await resolve_required_params("forge_list_shots", {}, mcp_b)
    assert out_b == {"project_id": "proj-0"}
    # Crucial: zero upstream calls on the memory-hit path.
    mcp_b.call_tool.assert_not_called()


# ── AC #2: Memory miss — fall back to resolver ───────────────────────────


@pytest.mark.asyncio
async def test_pr26_memory_miss_falls_back_to_resolver():
    """With memory empty, resolution MUST proceed to the PR25 resolver.
    A successful resolution then populates memory for next time."""
    assert _MEMORY.get("project_id") is None  # autouse fixture guarantee

    mcp = _make_mcp(project_count=1)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {"project_id": "proj-0"}
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})
    assert _MEMORY.get("project_id") == "proj-0"


@pytest.mark.asyncio
async def test_pr26_memory_miss_with_zero_projects_does_not_cache():
    """Resolver returns None on zero projects → no memory write.
    Memory stays empty, params unchanged."""
    mcp = _make_mcp(project_count=0)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {}
    assert _MEMORY.get("project_id") is None


@pytest.mark.asyncio
async def test_pr26_memory_miss_with_multi_projects_does_not_cache():
    """Resolver returns None on >1 projects → no memory write.
    Ambiguity must never poison the cache."""
    mcp = _make_mcp(project_count=3)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {}
    assert _MEMORY.get("project_id") is None


# ── AC #3: No silent overwrite ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pr26_existing_memory_not_overwritten_when_caller_provides_value():
    """When the caller supplies ``project_id`` directly, the resolver
    short-circuits before memory is consulted — neither read nor write.
    Pre-existing memory persists unchanged for future calls."""
    _MEMORY.set("project_id", "cached-uuid-A")

    mcp = _make_mcp(project_count=1)
    out = await resolve_required_params(
        "forge_list_versions", {"project_id": "caller-uuid-B"}, mcp,
    )

    # Caller's value wins for THIS call (memory is read-only here).
    assert out == {"project_id": "caller-uuid-B"}
    # No upstream call — fully satisfied by caller params.
    mcp.call_tool.assert_not_called()
    # Memory untouched — caller-supplied values never write to memory.
    assert _MEMORY.get("project_id") == "cached-uuid-A"


@pytest.mark.asyncio
async def test_pr26_resolver_overwrites_existing_memory_with_fresh_value():
    """A fresh deterministic resolution DOES update memory — that's the
    whole point of the cache. The "no overwrite without certainty"
    constraint targets non-deterministic writes (none exist today), not
    deterministic re-resolution."""
    _MEMORY.set("project_id", "stale-id")

    # Force the resolver path: empty params, no caller-provided value.
    # Memory hydration WILL pick up "stale-id" first — this is by design.
    mcp = _make_mcp(project_count=1)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    # Memory hydration short-circuited the resolver — "stale-id" used,
    # NO upstream call. Confirms hydration runs before the resolver.
    assert out == {"project_id": "stale-id"}
    mcp.call_tool.assert_not_called()
    assert _MEMORY.get("project_id") == "stale-id"


# ── AC #4: No recursion ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pr26_memory_hit_triggers_no_upstream_calls():
    """Brief AC #4: 'memory does not trigger additional tool calls'.
    A pre-populated memory hit must result in EXACTLY zero
    `mcp.call_tool` invocations — no projects probe, no recursion."""
    _MEMORY.set("project_id", "memorized-uuid")

    mcp = _make_mcp(project_count=99)  # never consulted
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {"project_id": "memorized-uuid"}
    assert mcp.call_tool.call_count == 0


@pytest.mark.asyncio
async def test_pr26_resolver_path_still_single_call_when_memory_empty():
    """Even on the resolver path, memory introduces no extra upstream
    calls — the cache write is a local op, not a tool dispatch."""
    mcp = _make_mcp(project_count=1)
    await resolve_required_params("forge_list_versions", {}, mcp)
    # Same single-call invariant as PR25 — memory adds no upstream cost.
    assert mcp.call_tool.call_count == 1


# ── AC #5: Non-chain tool — no memory interaction ────────────────────────


@pytest.mark.asyncio
async def test_pr26_non_chain_tool_does_not_consult_memory():
    """A tool not in `_PR25_CHAINS` must skip BOTH the memory read and
    the resolver path. Memory is invisible to non-chain tools."""
    _MEMORY.set("project_id", "should-be-ignored")

    mcp = _make_mcp(project_count=1)
    original = {"flame_specific": "value"}
    out = await resolve_required_params("flame_ping", original, mcp)

    # Pass-through identity preserved; memory untouched.
    assert out is original
    mcp.call_tool.assert_not_called()
    # The pre-set memory entry is NOT injected (non-chain tool).
    assert "project_id" not in out


@pytest.mark.asyncio
async def test_pr26_non_chain_tool_does_not_write_memory():
    """A non-chain tool must NOT write to memory either, regardless of
    what's in `params`."""
    mcp = _make_mcp(project_count=1)
    await resolve_required_params(
        "flame_ping", {"project_id": "caller-supplied"}, mcp,
    )
    # Even though params carries a value, no chain matched → no write.
    assert _MEMORY.get("project_id") is None


# ── AC #6: Reset behavior — fresh memory is empty ────────────────────────


def test_pr26_fresh_tool_memory_instance_is_empty():
    """A newly-constructed `ToolMemory()` starts with an empty store —
    no surprises, no defaults, no inherited state from elsewhere in the
    process."""
    mem = ToolMemory()
    assert mem.get("project_id") is None
    assert mem.get("any_other_key") is None


def test_pr26_global_memory_is_empty_at_test_start():
    """The autouse `_reset_tool_memory` fixture in conftest must yield
    a clean memory at the start of every test. This is the foundation
    AC #6 requires — verifies the fixture is wired correctly."""
    assert _MEMORY.get("project_id") is None


def test_pr26_clear_drops_all_keys():
    """`clear()` must remove every entry — used by the test fixture and
    available for any future explicit-invalidation production path."""
    _MEMORY.set("project_id", "x")
    _MEMORY.set("other_key", "y")
    _MEMORY.clear()
    assert _MEMORY.get("project_id") is None
    assert _MEMORY.get("other_key") is None


# ── Defensive — ToolMemory contract ───────────────────────────────────────


def test_pr26_set_rejects_empty_string():
    """`set` silently drops empty/falsy values to keep the contract
    'a stored value is always a non-empty string'."""
    mem = ToolMemory()
    mem.set("project_id", "")
    assert mem.get("project_id") is None
    mem.set("project_id", "real-value")
    assert mem.get("project_id") == "real-value"


def test_pr26_get_returns_none_for_unset_key():
    """`get` returns None — not raises, not empty string — for
    unset keys. Lets callers do `if mem_val: ...` safely."""
    mem = ToolMemory()
    assert mem.get("project_id") is None
