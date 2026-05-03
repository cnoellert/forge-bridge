"""PR25 — Unit tests for ``forge_bridge.console._tool_chain``.

Tests target the module's public contract directly, with a mocked
``mcp`` whose ``call_tool`` is an ``AsyncMock`` driven by a small
in-test dispatcher. Integration-level coverage (chat handler → forced
execution → injection → tool result) lives in ``test_chat_handler.py``;
this file isolates the resolution logic so we can pin the five
correctness claims from the PR25 brief one at a time.

Five tests, one per brief AC:
  1. Single project       → injects project_id
  2. Zero projects        → no injection
  3. Multiple projects    → no injection
  4. No recursion         → exactly ONE upstream call per resolution
  5. Non-chain tool       → passes through unchanged (no upstream call)
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console._tool_chain import (
    _PR25_CHAINS,
    _resolve_project_id,
    resolve_required_params,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────


def _projects_payload(count: int) -> str:
    """Build the JSON string `forge_list_projects` would return for `count`."""
    if count == 0:
        projects: list[dict] = []
    else:
        projects = [
            {"id": f"proj-{i}", "name": f"P{i}", "code": f"P{i}"}
            for i in range(count)
        ]
    return json.dumps({"count": len(projects), "projects": projects})


def _text_block(text: str):
    """A FastMCP-shaped TextContent block carrying a JSON string."""
    from mcp.types import TextContent
    return [TextContent(type="text", text=text)]


def _make_mcp(project_count: int) -> Any:
    """Build a minimal mock with ``mcp.call_tool`` as an AsyncMock that
    returns a TextContent block for `forge_list_projects` matching the
    requested project count."""
    mcp = AsyncMock()

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_projects_payload(project_count))
        # Other tools — unused in resolver tests, but return something
        # well-formed in case a defect calls through.
        return _text_block(json.dumps({"called": name, "args": arguments}))

    mcp.call_tool = AsyncMock(side_effect=fake_call_tool)
    return mcp


# ── AC #1: Single project → inject project_id ─────────────────────────────


@pytest.mark.asyncio
async def test_pr25_single_project_injects_project_id():
    """One project in the registry → the resolver returns its id and
    ``resolve_required_params`` merges it into the returned dict.
    The original `params` arg is NOT mutated."""
    mcp = _make_mcp(project_count=1)
    original: dict = {}

    out = await resolve_required_params("forge_list_versions", original, mcp)

    assert out == {"project_id": "proj-0"}
    # Defensive: original input must remain empty (no in-place mutation).
    assert original == {}
    # The resolver issued exactly one upstream call to forge_list_projects.
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})


# ── AC #2: Zero projects → no injection ───────────────────────────────────


@pytest.mark.asyncio
async def test_pr25_zero_projects_does_not_inject():
    """Zero projects → resolver returns None → params unchanged.
    Caller surfaces MISSING_PROJECT_ID via the PR22 graceful contract."""
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {}
    # The probe still went out — the rule's predicate runs unconditionally
    # for chain-listed tools; only the outcome differs.
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})


# ── AC #3: Multiple projects → no injection ───────────────────────────────


@pytest.mark.asyncio
async def test_pr25_multiple_projects_does_not_inject():
    """Two-or-more projects → ambiguous → resolver returns None →
    params unchanged. PR25 never picks arbitrarily."""
    mcp = _make_mcp(project_count=3)

    out = await resolve_required_params("forge_list_shots", {}, mcp)

    assert out == {}
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})


# ── AC #4: No recursion — exactly one upstream call ───────────────────────


@pytest.mark.asyncio
async def test_pr25_resolution_is_single_step_no_recursion():
    """Resolution must not recurse. ``resolve_required_params`` calls
    the resolver once; the resolver calls ``forge_list_projects`` once.
    No matter the project count, total upstream calls == 1."""
    for project_count in (0, 1, 2, 5):
        mcp = _make_mcp(project_count=project_count)

        await resolve_required_params("forge_list_versions", {}, mcp)

        assert mcp.call_tool.call_count == 1, (
            f"expected 1 upstream call for project_count={project_count}, "
            f"got {mcp.call_tool.call_count}"
        )
        # Always the projects probe — never the downstream tool, never
        # a self-referential chain (forge_list_projects is intentionally
        # NOT in _PR25_CHAINS).
        mcp.call_tool.assert_called_once_with("forge_list_projects", {})


# ── AC #5: Non-chain tool → no injection, no probe ────────────────────────


@pytest.mark.asyncio
async def test_pr25_non_chain_tool_passes_through_unchanged():
    """A tool not in ``_PR25_CHAINS`` returns ``params`` unchanged with
    NO upstream call. PR25 is a tight allow-list, not a heuristic."""
    mcp = _make_mcp(project_count=1)
    original = {"some": "value"}

    out = await resolve_required_params("flame_ping", original, mcp)

    # Identical contents AND identity preserved when no chain matches.
    assert out is original
    assert out == {"some": "value"}
    # Crucial: ZERO upstream calls — the registry guard short-circuits
    # before any work happens.
    mcp.call_tool.assert_not_called()


# ── Direct resolver tests — defensive failure paths ───────────────────────


@pytest.mark.asyncio
async def test_pr25_resolver_returns_none_on_call_tool_exception():
    """Any error from `forge_list_projects` (transport, ToolError, etc.)
    → resolver returns None. Fail closed."""
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(side_effect=RuntimeError("backend down"))

    pid = await _resolve_project_id(mcp)

    assert pid is None
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})


@pytest.mark.asyncio
async def test_pr25_resolver_returns_none_on_malformed_payload():
    """A non-JSON or non-dict payload → resolver returns None."""
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block("this is not json"))

    pid = await _resolve_project_id(mcp)

    assert pid is None


@pytest.mark.asyncio
async def test_pr25_resolver_returns_none_when_id_missing_from_project():
    """One project but no `id` key → fail closed; never substitute a
    default."""
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(json.dumps(
        {"count": 1, "projects": [{"name": "P0", "code": "P0"}]},  # no id
    )))

    pid = await _resolve_project_id(mcp)

    assert pid is None


# ── Registry sanity — pin the documented chain coverage ───────────────────


def test_pr25_chains_covers_exactly_the_two_pr22_graceful_tools():
    """The chain registry MUST track PR22's graceful surface 1:1.
    A drift here means a tool got added to the chain without verifying
    its PR22 contract — the failure mode is opaque (silent injection
    into a tool that doesn't gracefully surface MISSING_PROJECT_ID).
    Update both this test and the registry together."""
    assert set(_PR25_CHAINS.keys()) == {
        "forge_list_versions",
        "forge_list_shots",
    }
    for tool, chain in _PR25_CHAINS.items():
        assert chain["requires"] == frozenset({"project_id"}), tool
        assert chain["resolver"] == "_resolve_project_id", tool
