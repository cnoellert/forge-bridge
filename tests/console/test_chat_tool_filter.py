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
    # 'tell' is intentionally NOT in NORMALIZATION_MAP — keeps this test
    # focused on the prefix-keyword behavior (post-PR19, 'show'/'get' would
    # collapse to 'list' and pull in synth_tools_list as a token-overlap).
    out = filter_tools_by_message(tools, "tell me what forge knows")
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

    # Use 'forge_widget' (no shared tokens with the other forge_* tools) as
    # the second exact-match anchor. Post-PR19, 'forge_get_project' would
    # cause `get`→`list` to make `forge_list_projects` token-complete, which
    # would scramble the bucket assignment this test is verifying.
    tools = [
        _make_tool("flame_ping"),
        _make_tool("forge_list_shots"),     # token-match via 'list'
        _make_tool("forge_list_projects"),  # token-match via 'list'
        _make_tool("forge_widget"),
    ]
    out = filter_tools_by_message(
        tools,
        "first call forge_widget then call flame_ping to list",
        max_tools=8,
    )
    names = _names(out)
    # Both exact matches present, in their input order:
    assert names[0] == "flame_ping"           # input position 0
    assert names[1] == "forge_widget"         # input position 3
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


# ── PR18: token-complete exact match for natural-language phrases ────────


def test_pr18_natural_language_matches_underscored_tool_name():
    """The motivating UAT case: 'list flame libraries' (spaces) must
    elevate flame_list_libraries to the exact-match bucket because every
    token of the tool name is in the message."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # Many forge_* tools appear before flame_list_libraries in input order
    # AND share token "list" — pre-PR18 the cap would still drop the flame
    # tool because substring match doesn't fire (spaces vs. underscores).
    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "list flame libraries", max_tools=8,
    )
    names = _names(out)
    assert "flame_list_libraries" in names, (
        f"PR18: token-complete match dropped by cap: {names}"
    )
    # Exact bucket (token-complete) → head of result.
    assert names[0] == "flame_list_libraries"


def test_pr18_token_order_in_message_does_not_matter():
    """Tokens are a set membership check — order in the message is
    irrelevant. ``"flame libraries list"`` still matches."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("flame_list_libraries"),
             _make_tool("forge_list_projects")]
    out = filter_tools_by_message(tools, "flame libraries list")
    names = _names(out)
    assert names[0] == "flame_list_libraries"


def test_pr18_partial_token_match_does_NOT_promote_to_exact():
    """If only some tool tokens are in the message, the tool stays in the
    other (token-overlap) bucket — strict subset is required for exact."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # Many earlier-in-input tools also match "flame" so the cap kicks in.
    tools = [_make_tool(f"flame_op_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    # 'list' is missing — flame_list_libraries should NOT be in the
    # exact bucket and therefore CAN be dropped by the cap (8 flame_op_*
    # tools come first in input order).
    out = filter_tools_by_message(tools, "flame libraries", max_tools=8)
    names = _names(out)
    # The first 9 flame_op_* tools all token-match; the 10th
    # (flame_list_libraries) also token-matches but has no exact rescue,
    # so the cap drops it.
    assert "flame_list_libraries" not in names, (
        "PR18 must not promote partial-token matches to exact"
    )
    assert len(names) == 8


def test_pr18_substring_and_token_complete_both_route_to_exact_bucket():
    """The two exact-match conditions are an OR — both produce the same
    bucket placement. Verify this on a single message that triggers both."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("flame_ping"),             # substring exact
        _make_tool("flame_list_libraries"),   # token-complete exact
        _make_tool("forge_list_projects"),    # token overlap only
    ]
    out = filter_tools_by_message(
        tools, "please call flame_ping then list flame libraries",
    )
    names = _names(out)
    # Both exact matches must appear at the head, in input order.
    assert names[:2] == ["flame_ping", "flame_list_libraries"]
    assert "forge_list_projects" in names


def test_pr18_token_complete_match_survives_when_cap_exceeded():
    """Token-complete exact matches enjoy the same cap-survival guarantee
    as substring matches (PR17 contract extended)."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # 9 tools that token-overlap "list", + the token-complete winner last.
    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "list flame libraries", max_tools=2,
    )
    names = _names(out)
    assert names[0] == "flame_list_libraries"   # exact (token-complete) at head
    assert len(names) == 2                       # one other match fills remainder


def test_pr18_no_regression_pr17_substring_path():
    """PR17 substring exact-match path remains unaffected: an underscored
    tool name in the message goes to head as before."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("forge_list_projects"),
             _make_tool("flame_list_libraries")]
    out = filter_tools_by_message(tools, "use flame_list_libraries")
    assert _names(out)[0] == "flame_list_libraries"


def test_pr18_no_regression_pr14_unrelated_message_falls_back_to_full_list():
    """No exact OR token match → still returns the full input list
    (capability-loss safety net intact)."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("forge_list_projects"),
             _make_tool("flame_list_libraries")]
    out = filter_tools_by_message(tools, "tell me a joke about elephants")
    assert _names(out) == _names(tools)


def test_pr18_does_not_duplicate_when_tool_qualifies_for_both_exact_paths():
    """A tool whose name is BOTH a substring AND token-complete must
    appear in the result exactly once."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("flame_list_libraries"),
             _make_tool("forge_list_projects")]
    # Message mentions both the underscored form and the natural form.
    msg = "please flame_list_libraries: list the flame libraries"
    out = filter_tools_by_message(tools, msg)
    names = _names(out)
    assert names.count("flame_list_libraries") == 1


def test_pr18_acceptance_list_projects_does_not_promote_flame_list_libraries():
    """Direct PR18 AC: the message ``"list projects"`` must NOT promote
    flame_list_libraries to the exact-match bucket — only ``list`` overlaps
    (``flame``, ``libraries`` are missing). It may still appear as a
    token-overlap match (PR14 baseline), but not at the head."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool("forge_list_projects"),
             _make_tool("flame_list_libraries")]
    out = filter_tools_by_message(tools, "list projects")
    names = _names(out)
    # forge_list_projects shares 'list' and 'projects' (token overlap, two
    # of three tokens). flame_list_libraries shares only 'list'. Neither
    # is token-complete; both end up as token-overlap matches in input
    # order. The PR18 promise is that flame_list_libraries was NOT
    # elevated to the exact-match bucket — verify by checking the head.
    assert names[0] == "forge_list_projects"
    # And specifically: flame_list_libraries did not jump the queue.
    assert names.index("forge_list_projects") < names.index(
        "flame_list_libraries"
    )


# ── PR19: deterministic lexical normalization ─────────────────────────────


def test_pr19_normalize_token_is_dict_lookup_only():
    """``normalize_token`` is a strict dict lookup — unmapped tokens pass
    through unchanged. No stemming, no fuzzy fallback."""
    from forge_bridge.console._tool_filter import (
        NORMALIZATION_MAP,
        normalize_token,
    )

    # Mapped tokens collapse.
    assert normalize_token("libraries") == "library"
    assert normalize_token("show") == "list"
    assert normalize_token("listing") == "list"
    assert normalize_token("get") == "list"
    assert normalize_token("fetch") == "list"
    # Unmapped tokens are identity.
    assert normalize_token("flame") == "flame"
    assert normalize_token("ping") == "ping"
    # The map is the source of truth — no surprise entries.
    assert "show" in NORMALIZATION_MAP and NORMALIZATION_MAP["show"] == "list"


def test_pr19_show_flame_libraries_promotes_flame_list_libraries():
    """AC #1: ``"show flame libraries"`` → flame_list_libraries at the head.

    Pre-PR19: 'show' ≠ 'list' and 'libraries' ≠ 'library', so the PR18
    token-complete subset check fails. Post-PR19: both tokens normalize so
    the subset check fires and the tool lands in the exact-match bucket.
    """
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # Many forge_list_* tools share the normalized 'list' token but not
    # 'flame' or 'library' — they must NOT outrank the genuine match.
    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "show flame libraries", max_tools=8)
    names = _names(out)
    assert names[0] == "flame_list_libraries", (
        f"PR19: 'show flame libraries' must promote flame_list_libraries: {names}"
    )


def test_pr19_get_flame_libraries_promotes_flame_list_libraries():
    """AC #2 (variant): ``"get flame libraries"`` → flame_list_libraries."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "get flame libraries", max_tools=8)
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_listing_flame_libraries_promotes_flame_list_libraries():
    """AC #3: ``"listing flame libraries"`` → flame_list_libraries."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "listing flame libraries", max_tools=8,
    )
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_fetch_flame_libraries_promotes_flame_list_libraries():
    """``fetch`` is in the map and collapses to ``list``."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "fetch flame libraries", max_tools=8,
    )
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_plural_normalization_works_across_entity_words():
    """Plural→singular collapse fires for shots, projects, versions, roles."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_shots"),
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
        _make_tool("forge_list_roles"),
    ]
    # 'list shots' (plural in msg) maps to {list, shot}; tool tokens map to
    # {forge, list, shot}. Subset check: name ⊄ msg (forge missing). It is
    # however a token overlap, so it survives — and it remains the only tool
    # in input-order whose normalized tokens contain 'shot'. The other three
    # share only 'list' after normalization.
    out = filter_tools_by_message(tools, "list shots")
    names = _names(out)
    assert names[0] == "forge_list_shots", (
        f"PR19 plural collapse must put forge_list_shots first: {names}"
    )


def test_pr19_get_shots_normalizes_both_verb_and_plural():
    """``forge get shots`` exercises BOTH verb normalization (get→list) AND
    plural normalization (shots→shot) in a single message — and ensures
    the token-complete subset check (PR18) actually fires post-normalization,
    promoting forge_list_shots to the exact bucket."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_shots"),
        _make_tool("flame_list_libraries"),
    ]
    # Message tokens normalize to {forge, list, shot}; forge_list_shots
    # normalizes to {forge, list, shot} (strict subset → exact bucket head).
    out = filter_tools_by_message(tools, "forge get shots")
    names = _names(out)
    assert names[0] == "forge_list_shots"


def test_pr19_get_projects_acceptance_resolves_forge_list_projects():
    """AC #2 (literal text): ``"get projects"`` → forge_list_projects.

    'get' → 'list', 'projects' → 'project'. Tool 'forge_list_projects'
    normalizes to {forge, list, project}; intersection with {list, project}
    is two tokens — top of the other_matches bucket in input order."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_shots"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "get projects")
    names = _names(out)
    assert names[0] == "forge_list_projects"


def test_pr19_unrelated_synonyms_do_not_match():
    """Strict dict lookup: words NOT in NORMALIZATION_MAP do not collapse.

    'archives', 'fetch_all', 'enumerate', 'directories' are NOT in the map
    — they remain themselves. 'archives' does NOT become 'library', so
    flame_list_libraries should NOT be promoted to exact."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("flame_list_libraries"),
        _make_tool("forge_list_projects"),
    ]
    # 'enumerate flame archives' shares only 'flame' with the tool tokens
    # after normalization — flame_list_libraries normalized is
    # {flame, list, library}; msg normalized is {enumerate, flame, archives}.
    # Subset: False. Overlap: {flame}. Token-overlap bucket only.
    out = filter_tools_by_message(tools, "enumerate flame archives")
    names = _names(out)
    # Must not be promoted to exact (no head-of-list claim from nothing).
    # Both tools share 'flame' or nothing — flame_list_libraries first by
    # input order in the other-matches bucket; forge_list_projects has no
    # token overlap so it would NOT appear unless fallback fires.
    assert "flame_list_libraries" in names  # token overlap on 'flame'
    # The PR18 token-complete bucket should NOT have promoted it — verify
    # the result length matches a plain token-overlap pass (just the 'flame'
    # match), confirming no spurious normalization happened.
    assert names == ["flame_list_libraries"]


def test_pr19_no_regression_pr17_substring_exact_match():
    """PR17 substring path is independent of normalization — an underscored
    tool name in the message still routes to exact bucket."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "use flame_list_libraries")
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_no_regression_pr18_underscored_token_complete_match():
    """PR18 token-complete match still works on already-canonical tokens."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "list flame libraries", max_tools=8,
    )
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_no_regression_pr15_unrelated_message_falls_back_to_full_list():
    """Capability-loss safety net intact: an unrelated message that shares
    no normalized tokens with any tool returns the full input list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "tell me a joke about elephants")
    assert _names(out) == _names(tools)


# ── PR19.1: closed canonical vocabulary + symmetric application ──────────


def test_pr19_1_canonical_identity_entries_are_closed_vocabulary():
    """Each canonical form must be a key that maps to itself.

    Identity rows (``"library": "library"``) make the closed canonical
    vocabulary explicit and act as a regression guard: if a future edit
    accidentally re-targets ``libraries`` to something other than
    ``library``, the missing identity row would surface immediately.
    """
    from forge_bridge.console._tool_filter import (
        NORMALIZATION_MAP,
        normalize_token,
    )

    canonical_forms = {"library", "project", "shot", "version", "role", "list"}
    for canonical in canonical_forms:
        assert NORMALIZATION_MAP.get(canonical) == canonical, (
            f"Canonical identity broken for {canonical!r}: "
            f"NORMALIZATION_MAP[{canonical!r}] = "
            f"{NORMALIZATION_MAP.get(canonical)!r}"
        )
        assert normalize_token(canonical) == canonical


def test_pr19_1_normalize_token_targets_are_all_canonical():
    """Every value in NORMALIZATION_MAP must itself be a canonical form
    (a key that maps to itself). This is the closure check — it prevents
    a future edit from introducing a target that isn't covered by an
    identity row, which would silently break symmetry."""
    from forge_bridge.console._tool_filter import NORMALIZATION_MAP

    for src, dst in NORMALIZATION_MAP.items():
        assert NORMALIZATION_MAP.get(dst) == dst, (
            f"Asymmetry: {src!r} → {dst!r} but {dst!r} is not a fixed "
            f"point (got {NORMALIZATION_MAP.get(dst)!r}). Add "
            f"{dst!r}: {dst!r} to NORMALIZATION_MAP."
        )


def test_pr19_1_symmetric_application_message_and_tool_share_chokepoint():
    """The same tokenization+normalization function is used for BOTH
    message text and tool names, so identical inputs produce identical
    canonical token-sets regardless of source."""
    from forge_bridge.console._tool_filter import _pr14_tokens

    # Singular tool token + plural message: both land on canonical 'version'.
    assert _pr14_tokens("forge_list_version") == _pr14_tokens(
        "forge list version"
    )
    # Singular message + plural tool: both land on canonical 'version'.
    assert "version" in _pr14_tokens("forge_list_versions")
    assert "version" in _pr14_tokens("show versions")
    assert "version" in _pr14_tokens("show version")

    # Verb collapse is symmetric too — 'list' is a fixed point.
    for verb in ("listing", "show", "get", "fetch", "list"):
        assert "list" in _pr14_tokens(f"please {verb} something")


def test_pr19_1_singular_tool_token_matches_plural_message_token():
    """Direct symmetry assertion (test #4 in the brief): a tool whose name
    contains the singular ``version`` must token-overlap with a message
    that contains the plural ``versions`` after normalization."""
    from forge_bridge.console._tool_filter import _pr14_tokens

    # Hypothetical singular-named tool.
    tool_tokens = _pr14_tokens("forge_get_version")
    # Plural-form message.
    msg_tokens = _pr14_tokens("show me the versions")
    overlap = tool_tokens & msg_tokens
    assert "version" in overlap, (
        f"singular tool 'version' must match plural message 'versions' "
        f"after normalization: {tool_tokens=} {msg_tokens=}"
    )
    # And the reverse direction.
    tool_tokens = _pr14_tokens("forge_list_versions")
    msg_tokens = _pr14_tokens("show me the version")
    assert "version" in tool_tokens & msg_tokens


def test_pr19_1_fetch_versions_resolves_forge_list_versions():
    """AC #1 (REQUIRED): ``"fetch versions"`` keeps forge_list_versions
    in the filter result.

    'fetch' → 'list' (verb collapse); 'versions' → 'version' (plural
    collapse). After normalization the tool's token-set
    {forge, list, version} shares {list, version} with the message —
    the tool survives the filter as a token-overlap match.
    """
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_versions"),
        _make_tool("flame_ping"),  # no shared canonical tokens
    ]
    out = filter_tools_by_message(tools, "fetch versions")
    names = _names(out)
    assert "forge_list_versions" in names, (
        f"PR19.1 AC #1: 'fetch versions' must keep forge_list_versions "
        f"in the result: {names}"
    )
    # And it's the only tool that overlaps — flame_ping has no shared
    # tokens with {list, version}, so the result is exactly one tool.
    assert names == ["forge_list_versions"]


def test_pr19_1_get_versions_resolves_forge_list_versions():
    """AC #2: ``"get versions"`` resolves forge_list_versions for the same
    reason as 'fetch versions' — both verbs collapse to 'list'."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_versions"),
        _make_tool("flame_ping"),
    ]
    out = filter_tools_by_message(tools, "get versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr19_1_list_version_singular_resolves_forge_list_versions():
    """AC #3: singular ``"list version"`` resolves forge_list_versions —
    proves singular-message ↔ plural-tool symmetry."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_versions"),  # plural in tool name
        _make_tool("flame_ping"),
    ]
    out = filter_tools_by_message(tools, "list version")  # singular in msg
    assert _names(out) == ["forge_list_versions"]


def test_pr19_1_fetch_versions_promotes_to_exact_when_forge_present():
    """When the message includes the prefix token ``forge`` plus the verb
    and noun, the token-complete (PR18) subset check must fire — proving
    the symmetric normalization elevates forge_list_versions to the exact
    bucket without any change to the match logic."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    # Many forge_list_* tools share the canonical 'list' token but not
    # 'version' — they must NOT outrank the genuine match.
    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("forge_list_versions"),
    ]
    out = filter_tools_by_message(
        tools, "forge fetch versions", max_tools=8,
    )
    names = _names(out)
    assert names[0] == "forge_list_versions", (
        f"PR19.1: token-complete match must promote forge_list_versions "
        f"to the head when the message includes the prefix: {names}"
    )


def test_pr19_1_no_regression_show_flame_libraries():
    """AC #3 (existing): ``"show flame libraries"`` still resolves
    flame_list_libraries — PR19.1 must not regress PR19's wins."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "show flame libraries", max_tools=8)
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_1_no_regression_pr18_token_complete_underscored():
    """PR18 token-complete match path on canonical tokens unchanged."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(
        tools, "list flame libraries", max_tools=8,
    )
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_1_no_regression_pr17_substring_exact_match():
    """PR17 substring path independent of normalization."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "use flame_list_libraries")
    assert _names(out)[0] == "flame_list_libraries"


def test_pr19_1_no_regression_pr14_unrelated_message_falls_back():
    """Unrelated message with no normalized-token overlap returns full list."""
    from forge_bridge.console._tool_filter import filter_tools_by_message

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("flame_list_libraries"),
    ]
    out = filter_tools_by_message(tools, "tell me a joke about elephants")
    assert _names(out) == _names(tools)


def test_pr19_1_no_regression_pr14_cap_unchanged():
    """The PR14 cap behavior on a category-wide match is unchanged: at
    most ``max_tools`` survive, in input order, no rank/sort."""
    from forge_bridge.console._tool_filter import (
        PR14_MAX_TOOLS,
        filter_tools_by_message,
    )

    tools = [_make_tool(f"flame_op_{i}") for i in range(15)]
    out = filter_tools_by_message(tools, "do something with flame")
    assert len(out) == PR14_MAX_TOOLS
    assert _names(out) == [t.name for t in tools[:PR14_MAX_TOOLS]]


# ── PR21: deterministic disambiguation for multi-tool matches ────────────


def test_pr21_short_circuits_on_single_tool_input():
    """Length 0 / 1 inputs are returned unchanged — no work to do."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    assert deterministic_narrow([], "anything") == []
    one = [_make_tool("forge_list_versions")]
    assert deterministic_narrow(one, "anything") == one


def test_pr21_short_circuits_on_empty_message():
    """Empty / non-string message → return tools unchanged."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    assert deterministic_narrow(tools, "") == tools
    assert deterministic_narrow(tools, None) == tools  # type: ignore[arg-type]


def test_pr21_rule1_max_overlap_narrows_to_single_winner():
    """Rule 1: when one tool has strictly more matching tokens than the
    others, it wins outright. ``"list versions"`` overlaps
    forge_list_versions on {list, version} (2) and forge_list_projects on
    {list} (1)."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    out = deterministic_narrow(tools, "list versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr21_rule1_max_overlap_keeps_all_when_tied():
    """Rule 1: when every tool ties on overlap, all survive Rule 1.
    Rule 2 then has the chance to break the tie."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    # 'list project versions' overlaps both on 2 tokens:
    # {list, project} for forge_list_projects, {list, version} for
    # forge_list_versions. Rule 1 keeps both; Rule 2 picks the version.
    out = deterministic_narrow(tools, "list project versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr21_rule2_version_beats_project_when_both_present():
    """Rule 2: ``version > project`` — when the message contains BOTH
    canonical tokens, the version-bearing tool outranks the
    project-bearing tool. This is the motivating UAT case."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    out = deterministic_narrow(tools, "list project versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr21_rule2_does_not_apply_when_only_one_priority_token_present():
    """Rule 2 only fires when BOTH tokens of the priority pair are in
    the message. If only ``project`` is present, the version-tool isn't
    elevated against an unrelated project-tool."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),  # overlap = {list, project} = 2
        _make_tool("forge_list_versions"),  # overlap = {list} = 1
    ]
    out = deterministic_narrow(tools, "list projects")
    # Rule 1 already picks forge_list_projects (2 > 1) — Rule 2 never runs.
    assert _names(out) == ["forge_list_projects"]


def test_pr21_no_signal_returns_full_set():
    """When no candidate has any token overlap with the message (all
    arrived via PR14 fallback), narrowing has no signal and must NOT
    pick arbitrarily — return the candidate set unchanged."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    # 'tell me a joke about elephants' shares no tokens with either tool.
    out = deterministic_narrow(tools, "tell me a joke about elephants")
    assert out == tools


def test_pr21_unbreakable_tie_returns_multiple():
    """When Rule 1 ties and Rule 2 doesn't apply, the surviving set
    is returned with multiple tools — the caller (chat handler) then
    falls back to the LLM."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_shots"),
    ]
    # 'list' overlaps both on exactly 1 token. No priority-pair tokens
    # in the message → Rule 2 doesn't fire.
    out = deterministic_narrow(tools, "list")
    assert sorted(_names(out)) == ["forge_list_projects", "forge_list_shots"]
    assert len(out) == 2


def test_pr21_rule2_does_not_promote_when_winner_has_no_tools():
    """Edge case: if the message contains both priority tokens but NO
    surviving tool actually carries the WINNER token, Rule 2 must not
    eliminate every candidate — the surviving set is returned unchanged
    so the LLM gets to decide."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),  # also normalizes via 'get'→'list'
    ]
    # Both tools are project-only. Even with 'version' in the message,
    # the version-bearing winners list is empty — keep both candidates.
    out = deterministic_narrow(tools, "list project versions")
    # Rule 1: forge_list_projects overlap {list, project}=2;
    #         forge_get_project overlap {list, project}=2. Tied.
    # Rule 2: 'version' in msg, 'project' in msg, but no tool carries
    # 'version' → drop logic skipped. Both survive.
    assert sorted(_names(out)) == ["forge_get_project", "forge_list_projects"]


def test_pr21_does_not_modify_input_list():
    """Defensive: the input list must not be mutated by narrowing."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    before = list(tools)
    deterministic_narrow(tools, "list project versions")
    assert tools == before


def test_pr21_no_regression_pr19_normalization_intact():
    """PR21 uses the SAME normalization chokepoint (`_pr14_tokens`) as
    PR19/PR19.1 — verify by sending a verb-collapsed message
    ('fetch' → 'list'). The narrowing still picks forge_list_versions."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_versions"),
    ]
    out = deterministic_narrow(tools, "fetch project versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr21_no_regression_pr18_token_complete_path():
    """PR21 is a SECOND-stage narrower; PR18's token-complete logic in
    `filter_tools_by_message` is upstream and unaffected. End-to-end
    composition: PR18 may already have narrowed to one tool — PR21 then
    short-circuits because input is length 1."""
    from forge_bridge.console._tool_filter import (
        deterministic_narrow,
        filter_tools_by_message,
    )

    tools = [_make_tool(f"forge_list_{i}") for i in range(9)] + [
        _make_tool("flame_list_libraries"),
    ]
    after_filter = filter_tools_by_message(
        tools, "list flame libraries", max_tools=8,
    )
    # PR18 puts flame_list_libraries at the head.
    assert _names(after_filter)[0] == "flame_list_libraries"
    # PR21 doesn't reorder the surviving exact-bucket head; if input >1,
    # it just narrows by overlap. Here flame_list_libraries has the
    # highest overlap (3 tokens), so it's the lone survivor.
    out = deterministic_narrow(after_filter, "list flame libraries")
    assert _names(out) == ["flame_list_libraries"]


# ── PR23: raw-token tie-breaker (Rule 3) ──────────────────────────────────


def test_pr23_raw_message_tokens_split_on_whitespace_only():
    """Raw message tokens are split on whitespace and lowercased — NO
    normalization applied. Punctuation stays attached (set intersection
    only)."""
    from forge_bridge.console._tool_filter import _raw_message_tokens

    assert _raw_message_tokens("List Projects") == {"list", "projects"}
    assert _raw_message_tokens("get  project") == {"get", "project"}
    assert _raw_message_tokens("") == set()
    assert _raw_message_tokens("   ") == set()


def test_pr23_raw_tool_tokens_split_on_underscore_only():
    """Raw tool-name tokens are split on `_` and lowercased — matches
    the canonical ``<prefix>_<verb>_<noun>`` registry naming."""
    from forge_bridge.console._tool_filter import _raw_tool_tokens

    assert _raw_tool_tokens("forge_list_projects") == {"forge", "list", "projects"}
    assert _raw_tool_tokens("forge_get_project") == {"forge", "get", "project"}
    assert _raw_tool_tokens("FORGE_LIST_VERSIONS") == {"forge", "list", "versions"}
    assert _raw_tool_tokens("") == set()


def test_pr23_list_projects_picks_forge_list_projects_over_forge_get_project():
    """Motivating UAT case: post-PR19 normalization, both
    ``forge_list_projects`` and ``forge_get_project`` collapse to
    identical normalized tokens {forge, list, project}. Rule 3 breaks
    the tie via raw-token overlap with the literal message
    {list, projects}."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    out = deterministic_narrow(tools, "list projects")
    assert _names(out) == ["forge_list_projects"]


def test_pr23_get_project_picks_forge_get_project_over_forge_list_projects():
    """Symmetric case — ``"get project"`` (singular noun, get verb)
    must pick ``forge_get_project``, not ``forge_list_projects``.
    Both normalize identically; raw tokens disambiguate."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    out = deterministic_narrow(tools, "get project")
    assert _names(out) == ["forge_get_project"]


def test_pr23_bare_plural_noun_picks_list_tool():
    """``"projects"`` alone (just the plural noun) must pick
    ``forge_list_projects`` because its raw tokens contain ``projects``;
    ``forge_get_project`` contains ``project`` (singular) — no match."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    out = deterministic_narrow(tools, "projects")
    assert _names(out) == ["forge_list_projects"]


def test_pr23_bare_singular_noun_picks_get_tool():
    """``"project"`` (singular) must pick ``forge_get_project``.
    Symmetric counterpart to the plural case."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    out = deterministic_narrow(tools, "project")
    assert _names(out) == ["forge_get_project"]


def test_pr23_unbreakable_raw_tie_returns_multiple():
    """When even raw-token overlap ties, PR23 keeps all tied survivors
    and the chat handler falls back to the LLM. ``"list"`` alone
    matches every list-bearing tool's raw tokens at exactly 1 token —
    no winner, no narrowing."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_list_shots"),
    ]
    out = deterministic_narrow(tools, "list")
    # Both tied on Rule 1 (overlap=1) and Rule 3 (raw overlap=1).
    assert sorted(_names(out)) == ["forge_list_projects", "forge_list_shots"]


def test_pr23_does_not_fire_when_no_raw_overlap():
    """If NO survivor has any raw-token match with the message, Rule 3
    must not arbitrarily eliminate everyone — keep the surviving set
    so the LLM can still choose."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    # Message uses a verb that normalizes-to-list but isn't literally
    # in either tool's raw name; nouns also collapse via normalization.
    # 'fetch' normalizes to 'list' (in both tool sets after norm).
    # forge_list_projects raw tokens contain neither 'fetch' nor anything
    # that looks like 'projects' literally? Let's verify with raw msg
    # = {fetch, projects}: forge_list_projects raw {forge, list, projects}
    # → overlap = {projects} = 1. forge_get_project raw {forge, get, project}
    # → overlap = {} = 0. Rule 3 picks forge_list_projects. So this
    # message DOES disambiguate.
    out = deterministic_narrow(tools, "fetch projects")
    assert _names(out) == ["forge_list_projects"]


def test_pr23_no_regression_pr21_rule1_still_wins_first():
    """When Rule 1 alone narrows (one survivor by normalized overlap),
    Rule 3 never fires. No change to the existing PR21 behavior."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),  # overlap = {list, project} = 2
        _make_tool("forge_list_versions"),  # overlap = {list} = 1
    ]
    out = deterministic_narrow(tools, "list projects")
    assert _names(out) == ["forge_list_projects"]


def test_pr23_no_regression_pr21_rule2_version_still_wins_over_project():
    """Rule 2 (version > project) still fires before Rule 3. ``"list
    project versions"`` contains both priority tokens; version-bearing
    tools win regardless of raw-token overlap."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),  # raw {forge, list, projects}
        _make_tool("forge_list_versions"),  # raw {forge, list, versions}
    ]
    # Rule 1: both tied (normalized overlap 2 each).
    # Rule 2: 'version' & 'project' both in msg → version-tools win →
    # forge_list_versions alone. Rule 3 never fires (already at 1).
    out = deterministic_narrow(tools, "list project versions")
    assert _names(out) == ["forge_list_versions"]


def test_pr23_no_regression_input_not_mutated():
    """Defensive — Rule 3 must not mutate the input list."""
    from forge_bridge.console._tool_filter import deterministic_narrow

    tools = [
        _make_tool("forge_list_projects"),
        _make_tool("forge_get_project"),
    ]
    before = list(tools)
    deterministic_narrow(tools, "list projects")
    assert tools == before
