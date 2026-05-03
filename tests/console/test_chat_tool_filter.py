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


# ── PR14: message-based tool pre-filter ─────────────────────────────────────


def _names(tools):
    return [t.name for t in tools]


def test_pr14_message_match_keeps_overlapping_tools_only():
    """A message that names tools should yield just those (in input order)."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool(n) for n in [
            "flame_ping", "flame_list_libraries", "forge_get_project",
            "forge_list_shots", "synth_tools_list",
        ]
    ]
    out = filter_tools_by_message(tools, "please run flame_ping for me")
    # flame_ping matches by full name; flame_list_libraries matches via 'flame'.
    assert _names(out) == ["flame_ping", "flame_list_libraries"]


def test_pr14_no_matches_falls_back_to_full_list():
    """When nothing in the message overlaps any tool, return the full list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("flame_ping"), _make_tool("forge_get_project")]
    out = filter_tools_by_message(tools, "tell me a joke about elephants")
    assert _names(out) == ["flame_ping", "forge_get_project"]


def test_pr14_empty_message_falls_back_to_full_list():
    """An empty / non-string message must not narrow the list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("flame_ping"), _make_tool("forge_get_project")]
    assert _names(filter_tools_by_message(tools, "")) == _names(tools)
    assert _names(filter_tools_by_message(tools, None)) == _names(tools)  # type: ignore[arg-type]


def test_pr14_filtered_count_capped_at_max_tools():
    """At most PR14_MAX_TOOLS survive a category-wide match like 'flame'."""
    from forge_bridge.console._tool_filter import (
        PR14_MAX_TOOLS,
        filter_tools_by_message,
    )

    tools = [_make_tool(f"flame_op_{i}") for i in range(15)]  # 15 flame_* tools
    out = filter_tools_by_message(tools, "do something with flame")
    assert len(out) == PR14_MAX_TOOLS
    # Stable ordering — first N kept, no rank/sort.
    assert _names(out) == [t.name for t in tools[:PR14_MAX_TOOLS]]


def test_pr14_category_keyword_picks_up_full_prefix_family():
    """Mentioning the prefix word ('forge') matches every forge_* tool."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("flame_ping"),
        _make_tool("forge_get_project"),
        _make_tool("forge_list_shots"),
        _make_tool("synth_tools_list"),
    ]
    out = filter_tools_by_message(tools, "show me what forge knows")
    assert _names(out) == ["forge_get_project", "forge_list_shots"]


def test_pr14_verb_keyword_matches_action_tools():
    """A bare verb in the message ('ping') matches tools that share the token."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("flame_ping"),
        _make_tool("forge_ping"),
        _make_tool("forge_list_shots"),
    ]
    out = filter_tools_by_message(tools, "ping please")
    assert _names(out) == ["flame_ping", "forge_ping"]


def test_pr14_pure_punctuation_message_falls_back_to_full_list():
    """No alphanumeric tokens in the message → no match → fallback."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("flame_ping"), _make_tool("forge_get_project")]
    out = filter_tools_by_message(tools, "?!.")
    assert _names(out) == _names(tools)


def test_pr14_overrides_max_tools_via_kwarg_for_tests():
    """``max_tools`` is wired through so future callers can tune it."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"flame_op_{i}") for i in range(10)]
    out = filter_tools_by_message(tools, "flame", max_tools=3)
    assert len(out) == 3
    assert _names(out) == [t.name for t in tools[:3]]


# ── PR17: exact-match preservation past the cap ──────────────────────────


def test_pr17_exact_match_survives_cap_when_pushed_past_input_position():
    """The motivating UAT case: many forge_* token-matches sit before
    flame_list_libraries in input order. Pre-PR17 the cap would drop the
    flame tool. PR17 must rescue it."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # 9 forge_* tools that match the "list" token, then flame_list_libraries.
    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "use flame_list_libraries", max_tools=8,
    )
    names = _names(out)
    assert "flame_list_libraries" in names, (
        f"PR17: exact-match tool was dropped by the cap: {names}"
    )


def test_pr17_exact_match_is_first_in_result():
    """Exact matches go to the head, in original input order, regardless of
    where they sit in the input list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_shots"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "please call flame_list_libraries")
    assert _names(out)[0] == "flame_list_libraries"


def test_pr17_multiple_exact_matches_preserved_in_input_order():
    """Two tools both named in the message both survive, in input order."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("flame_ping"),
        _make_tool("forge_list_shots"),     # token-match via 'list'
        _make_tool("forge_list_projects"),  # token-match via 'list'
        _make_tool("forge_get_project"),
    ]
    out = filter_tools_by_message(
        tools,
        "first call forge_get_project then call flame_ping to list",
        max_tools=8,
    )
    names = _names(out)
    # Both exact matches present, in their input order:
    assert names[0] == "flame_ping"           # input position 0
    assert names[1] == "forge_get_project"    # input position 3
    # Token matches still included at the tail:
    assert "forge_list_shots" in names
    assert "forge_list_projects" in names


def test_pr17_no_exact_match_falls_back_to_pr14_behavior():
    """If nothing in the message names a tool, the cap behaves exactly as
    PR14 did — first N token matches in input order, no rescue, no rank."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"flame_op_{i}") for i in range(15)]
    out = filter_tools_by_message(tools, "do something with flame", max_tools=8)
    assert len(out) == 8
    assert _names(out) == [t.name for t in tools[:8]]


def test_pr17_no_match_at_all_still_falls_back_to_full_list():
    """The PR14 capability-loss safety net must remain — empty match set
    still returns the full list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("forge_get_project"), _make_tool("flame_ping")]
    out = filter_tools_by_message(tools, "tell me a joke about elephants")
    assert _names(out) == _names(tools)


def test_pr17_exact_matches_alone_exceed_cap_truncated_in_input_order():
    """If exact matches alone are more than ``max_tools``, return only
    the first N exact matches in input order — don't add token matches."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # All 5 tool names appear in the message as substrings.
    tools = [
        _make_tool("forge_alpha"),
        _make_tool("forge_beta"),
        _make_tool("forge_gamma"),
        _make_tool("flame_ping"),
        _make_tool("synth_widget"),
    ]
    msg = "use forge_alpha forge_beta forge_gamma flame_ping synth_widget"
    out = filter_tools_by_message(tools, msg, max_tools=3)
    assert _names(out) == ["forge_alpha", "forge_beta", "forge_gamma"]


def test_pr17_other_matches_only_fill_remaining_slots():
    """When exact_matches=k and max_tools=N, exactly N-k other matches
    are appended (k+other ≤ N)."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),  # token match (list)
        _make_tool("forge_list_shots"),     # token match (list)
        _make_tool("forge_list_media"),     # token match (list)
        _make_tool("flame_list_libraries"), # EXACT match
    ]
    out = filter_tools_by_message(
        tools, "list flame_list_libraries please", max_tools=2,
    )
    names = _names(out)
    assert len(names) == 2
    assert names[0] == "flame_list_libraries"  # exact, at head
    # Then exactly ONE other match (max_tools=2, exact=1, remaining=1).
    assert names[1] == "forge_list_projects"   # first in input order


def test_pr17_exact_match_that_also_token_matches_counts_as_exact_only():
    """A tool whose name matches both substring + token shouldn't appear
    twice — exact-match takes precedence and there is no duplication."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "use flame_list_libraries")
    names = _names(out)
    assert names.count("flame_list_libraries") == 1


def test_pr17_input_order_preserved_within_each_bucket():
    """Stability: order within exact_matches and within other_matches is
    the same as input order — no sorting."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("z_token_match"),  # token match (z)
        _make_tool("a_exact"),        # exact match
        _make_tool("y_token_match"),  # token match (y)
        _make_tool("b_exact"),        # exact match
    ]
    msg = "call a_exact and b_exact, with z and y around"
    out = filter_tools_by_message(tools, msg, max_tools=8)
    names = _names(out)
    # Exact matches: a_exact (input #1), b_exact (input #3) — head, in input order.
    assert names[0] == "a_exact"
    assert names[1] == "b_exact"
    # Token matches: z_token_match (input #0), y_token_match (input #2).
    assert names[2:4] == ["z_token_match", "y_token_match"]
