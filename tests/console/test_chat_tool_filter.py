"""Unit tests for forge_bridge/console/_tool_filter.py (Phase 16.1 D-01).

Tests the backend-aware tool-list scoping filter. All tests use deterministic
mocks — no real TCP probes. The filter module is exercised in isolation.

Test roster:
  1. test_in_process_tool_set_matches_resources_module
  2. test_filter_keeps_synth_when_all_backends_down
  3. test_filter_keeps_in_process_forge_when_flame_down
  3b. test_filter_all_seven_in_process_tools_survive_when_flame_down (parametrized)
  4. test_filter_keeps_flame_dependent_forge_when_flame_up
  5. test_probe_cache_hits_within_ttl
  6. test_probe_cache_expires_after_ttl
  7. test_probe_failure_returns_false_no_propagation
  8. test_chat_filter_returns_at_least_in_process_tools_when_all_remote_unreachable
"""
from __future__ import annotations

import asyncio
import inspect
import re
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


def _make_tool(name: str):
    """Minimal mcp.types.Tool for filter tests."""
    from mcp.types import Tool
    return Tool(
        name=name,
        description="Test tool.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


@pytest.fixture(autouse=True)
def _reset_filter_cache():
    """Reset the _tool_filter module cache before each test for isolation."""
    import forge_bridge.console._tool_filter as _tool_filter
    _tool_filter._reset_for_tests()
    yield
    _tool_filter._reset_for_tests()


# ── Test 1: In-process tool set matches resources module ──────────────────────

def test_in_process_tool_set_matches_resources_module():
    """Regression guard: _IN_PROCESS_FORGE_TOOLS must contain EXACTLY the seven
    names registered by register_console_resources in forge_bridge/console/resources.py.

    If register_console_resources adds another in-process tool, this test fails —
    forcing the classification to be updated. Expected cardinality is SEVEN (not six).
    """
    from forge_bridge.console._tool_filter import _IN_PROCESS_FORGE_TOOLS
    from forge_bridge.console.resources import register_console_resources

    # Extract all @mcp.tool name="forge_..." literals from the source
    source = inspect.getsource(register_console_resources)
    # Match name= "..." patterns for forge_ prefixed tools
    registered_names = set(re.findall(r'name=["\']?(forge_\w+)["\']?', source))

    assert registered_names == _IN_PROCESS_FORGE_TOOLS, (
        f"_IN_PROCESS_FORGE_TOOLS is out of sync with register_console_resources.\n"
        f"  In filter : {sorted(_IN_PROCESS_FORGE_TOOLS)}\n"
        f"  In resources: {sorted(registered_names)}\n"
        f"Update _IN_PROCESS_FORGE_TOOLS in _tool_filter.py."
    )
    # The expected cardinality is SEVEN — not six.
    assert len(_IN_PROCESS_FORGE_TOOLS) == 7, (
        f"Expected exactly 7 in-process forge_* tools, got {len(_IN_PROCESS_FORGE_TOOLS)}: "
        f"{sorted(_IN_PROCESS_FORGE_TOOLS)}"
    )


# ── Test 2: All backends down — only synth_* survive ─────────────────────────

@pytest.mark.asyncio
async def test_filter_keeps_synth_when_all_backends_down():
    """When all remote backends are unreachable, only synth_* tools pass through."""
    import forge_bridge.console._tool_filter as _tool_filter

    tools = [
        _make_tool("synth_x"),
        _make_tool("forge_list_projects"),
        _make_tool("flame_ping"),
    ]

    with patch.object(_tool_filter, "_probe_backend", new=AsyncMock(return_value=False)):
        result = await _tool_filter.filter_tools_by_reachable_backends(tools)

    assert [t.name for t in result] == ["synth_x"]


# ── Test 3: In-process forge_* stays when Flame is down ──────────────────────

@pytest.mark.asyncio
async def test_filter_keeps_in_process_forge_when_flame_down():
    """In-process forge_* (forge_list_staged) stays regardless of Flame reachability."""
    import forge_bridge.console._tool_filter as _tool_filter

    tools = [
        _make_tool("forge_list_staged"),
        _make_tool("forge_list_projects"),  # Flame-dependent
    ]

    with patch.object(_tool_filter, "_probe_backend", new=AsyncMock(return_value=False)):
        result = await _tool_filter.filter_tools_by_reachable_backends(tools)

    result_names = [t.name for t in result]
    assert "forge_list_staged" in result_names, (
        "In-process tool forge_list_staged must survive even when Flame is unreachable"
    )
    assert "forge_list_projects" not in result_names, (
        "Flame-dependent forge_list_projects must be dropped when Flame is unreachable"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("in_process_name", [
    "forge_manifest_read",
    "forge_tools_read",
    "forge_list_staged",
    "forge_get_staged",
    "forge_approve_staged",
    "forge_reject_staged",
    "forge_staged_pending_read",
])
async def test_filter_all_seven_in_process_tools_survive_when_flame_down(in_process_name):
    """All SEVEN in-process forge_* tools must survive when Flame is unreachable.

    Regression guard: if a name is accidentally dropped from _IN_PROCESS_FORGE_TOOLS,
    this test fails immediately instead of letting the chat handler return 503 on
    bare assist-01.
    """
    import forge_bridge.console._tool_filter as _tool_filter

    # Include the in-process tool plus a Flame-dependent one and a synth_
    tools = [
        _make_tool(in_process_name),
        _make_tool("forge_list_projects"),
        _make_tool("synth_synthesis"),
    ]

    with patch.object(_tool_filter, "_probe_backend", new=AsyncMock(return_value=False)):
        result = await _tool_filter.filter_tools_by_reachable_backends(tools)

    result_names = [t.name for t in result]
    assert in_process_name in result_names, (
        f"In-process tool {in_process_name!r} must survive when Flame is unreachable. "
        f"Check _IN_PROCESS_FORGE_TOOLS in _tool_filter.py."
    )
    assert "forge_list_projects" not in result_names
    assert "synth_synthesis" in result_names


# ── Test 4: Flame up — flame-dependent tools pass through ────────────────────

@pytest.mark.asyncio
async def test_filter_keeps_flame_dependent_forge_when_flame_up():
    """When Flame is reachable, Flame-dependent forge_* and all flame_* tools pass."""
    import forge_bridge.console._tool_filter as _tool_filter

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_ping"),
    ]

    with patch.object(_tool_filter, "_probe_backend", new=AsyncMock(return_value=True)):
        result = await _tool_filter.filter_tools_by_reachable_backends(tools)

    result_names = [t.name for t in result]
    assert "forge_list_projects" in result_names
    assert "flame_ping" in result_names


# ── Test 5: Cache hits within TTL ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_cache_hits_within_ttl():
    """Two consecutive calls within 5s perform the probe ONCE (cache hit on second call)."""
    import forge_bridge.console._tool_filter as _tool_filter

    probe_mock = AsyncMock(return_value=True)
    tools = [_make_tool("forge_list_projects")]

    with patch.object(_tool_filter, "_probe_backend", new=probe_mock):
        await _tool_filter.filter_tools_by_reachable_backends(tools)
        # Second call within TTL — cache should be used
        await _tool_filter.filter_tools_by_reachable_backends(tools)

    # Only one probe was performed across two filter calls
    assert probe_mock.call_count == 1, (
        f"Expected 1 probe call (cache hit on second call), got {probe_mock.call_count}"
    )


# ── Test 6: Cache expires after TTL ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_cache_expires_after_ttl():
    """After TTL expires, a second call re-probes the backend."""
    import forge_bridge.console._tool_filter as _tool_filter

    probe_mock = AsyncMock(return_value=True)
    tools = [_make_tool("forge_list_projects")]

    # First call — populates cache
    call_times = [0.0, 10.0, 10.0]  # First at t=0, then advance past TTL
    call_idx = [0]

    def fake_monotonic():
        idx = min(call_idx[0], len(call_times) - 1)
        call_idx[0] += 1
        return call_times[idx]

    with patch.object(_tool_filter, "_probe_backend", new=probe_mock), \
         patch("forge_bridge.console._tool_filter.time") as mock_time:
        mock_time.monotonic.side_effect = fake_monotonic
        await _tool_filter.filter_tools_by_reachable_backends(tools)
        # Second call — time has advanced past TTL (5s), cache should be expired
        await _tool_filter.filter_tools_by_reachable_backends(tools)

    assert probe_mock.call_count == 2, (
        f"Expected 2 probe calls (cache expired), got {probe_mock.call_count}"
    )


# ── Test 7: Probe failure returns False, no exception propagation ─────────────

@pytest.mark.asyncio
async def test_probe_failure_returns_false_no_propagation():
    """If asyncio.open_connection raises OSError, _probe_backend returns False (no exception)."""
    import forge_bridge.console._tool_filter as _tool_filter

    async def raise_os_error(*args, **kwargs):
        raise OSError("Connection refused")

    with patch("forge_bridge.console._tool_filter.asyncio") as mock_asyncio:
        mock_asyncio.wait_for = AsyncMock(side_effect=OSError("Connection refused"))
        mock_asyncio.TimeoutError = asyncio.TimeoutError
        result = await _tool_filter._probe_backend("127.0.0.1", 9999)

    assert result is False, "probe_backend must return False on OSError (no exception propagation)"


# ── Test 8: All-remote-unreachable precondition guard ────────────────────────

@pytest.mark.asyncio
async def test_chat_filter_returns_at_least_in_process_tools_when_all_remote_unreachable():
    """Precondition guard: when ALL remote backends fail, the filter returns a NON-EMPTY
    list containing all seven in-process forge_* tools + all synth_* tools.

    This is the Issue-1-class regression guard: if a future edit accidentally removes a
    name from _IN_PROCESS_FORGE_TOOLS, this test FAILS instead of letting the chat
    handler return 503 on bare assist-01.
    """
    import forge_bridge.console._tool_filter as _tool_filter

    in_process_names = sorted(_tool_filter._IN_PROCESS_FORGE_TOOLS)
    synth_names = ["synth_tools_create", "synth_tools_list"]
    flame_dependent_names = ["forge_list_projects", "forge_ping", "flame_ping"]

    tools = (
        [_make_tool(n) for n in in_process_names]
        + [_make_tool(n) for n in synth_names]
        + [_make_tool(n) for n in flame_dependent_names]
    )

    # Patch ALL probe calls to fail
    with patch.object(_tool_filter, "_probe_backend", new=AsyncMock(return_value=False)):
        result = await _tool_filter.filter_tools_by_reachable_backends(tools)

    result_names = {t.name for t in result}
    expected_names = _tool_filter._IN_PROCESS_FORGE_TOOLS | set(synth_names)

    assert result_names == expected_names, (
        f"When all remote backends are down, expected exactly in-process + synth tools.\n"
        f"  Expected : {sorted(expected_names)}\n"
        f"  Got      : {sorted(result_names)}\n"
        f"Check _IN_PROCESS_FORGE_TOOLS in _tool_filter.py."
    )

    # Non-empty guarantee
    assert len(result) > 0, (
        "filter_tools_by_reachable_backends must never return empty when in-process "
        "tools exist in the input list"
    )
