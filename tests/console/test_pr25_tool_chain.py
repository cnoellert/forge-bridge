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
    _resolve_rename_params,
    _resolve_sequence_name,
    _RESOLVERS,
    UNRESOLVED_KEY,
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
    """Two-or-more projects → ambiguous → resolver does NOT pick
    arbitrarily.

    PR25 originally returned ``params`` unchanged on this path (the
    same fail-closed shape as zero-projects). PR27 supersedes that:
    the multi-candidate case now returns a structured
    ``__disambiguation__`` sentinel so the handler can short-circuit
    to MULTIPLE_PROJECTS instead of letting the empty-args call hit
    the PR22 graceful contract. The PR25 invariant under test here is
    still valid — no ``project_id`` is injected — just the surrounding
    sentinel is new.
    """
    mcp = _make_mcp(project_count=3)

    out = await resolve_required_params("forge_list_shots", {}, mcp)

    # PR27 — sentinel, NOT empty dict. project_id was never injected.
    assert "project_id" not in out
    assert "__disambiguation__" in out
    assert out["__disambiguation__"]["type"] == "project"
    mcp.call_tool.assert_called_once_with("forge_list_projects", {})


# ── AC #4: No recursion — exactly one upstream call ───────────────────────


@pytest.mark.asyncio
async def test_pr25_resolution_is_single_step_no_recursion():
    """Resolution must not recurse. ``resolve_required_params`` calls
    the resolver once; the resolver calls ``forge_list_projects`` once.
    No matter the project count, total upstream calls == 1."""
    # PR26 — memory persists across calls within a process; clear it
    # between iterations so each one exercises the resolver path from a
    # known-empty state (the no-recursion property under test here is
    # PR25's resolver behavior, not PR26's memory behavior).
    from forge_bridge.console._memory import _MEMORY

    for project_count in (0, 1, 2, 5):
        _MEMORY.clear()
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


def test_pr25_chains_covers_project_and_sequence_resolution_tools():
    """The chain registry MUST track deterministic resolver coverage.
    A drift here means a tool got added without pinning its required-key
    ownership and resolver path. Update both this test and the registry
    together."""
    assert set(_PR25_CHAINS.keys()) == {
        "forge_list_versions",
        "forge_list_shots",
        "flame_inspect_sequence_versions",
        "flame_get_sequence_segments",
        "flame_preview_start_frames",
        "flame_rename_shots",
        "flame_preview_rename",
    }
    for tool in ("forge_list_versions", "forge_list_shots"):
        chain = _PR25_CHAINS[tool]
        assert chain["requires"] == frozenset({"project_id"}), tool
        assert chain["resolver"] == "_resolve_project_id", tool
    for tool in (
        "flame_inspect_sequence_versions",
        "flame_get_sequence_segments",
        "flame_preview_start_frames",
    ):
        chain = _PR25_CHAINS[tool]
        assert chain["requires"] == frozenset({"sequence_name"}), tool
        assert chain["resolver"] == "_resolve_sequence_name", tool
    rename_chain = _PR25_CHAINS["flame_rename_shots"]
    assert rename_chain["requires"] == frozenset({"sequence_name", "prefix"})
    assert rename_chain["resolver"] == "_resolve_rename_params"
    preview_rename_chain = _PR25_CHAINS["flame_preview_rename"]
    assert preview_rename_chain["requires"] == frozenset({"sequence_name", "prefix"})
    assert preview_rename_chain["resolver"] == "_resolve_rename_params"


@pytest.mark.asyncio
async def test_pr25_sequence_resolver_delegates_to_query_resolver():
    mcp = _make_mcp(project_count=0)

    resolved = await _resolve_sequence_name(
        "Give me the versions on the sequence 30sec 21", mcp,
    )

    assert resolved == "30sec_21"
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_sequence_tool_resolves_required_sequence_name_from_message():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_get_sequence_segments",
        {},
        mcp,
        message="Get the segments on the sequence 30sec 21",
    )

    assert out == {"sequence_name": "30sec_21"}
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_sequence_tool_unresolved_returns_sentinel():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_get_sequence_segments",
        {},
        mcp,
        message="Get the segments",
    )

    assert out == {
        UNRESOLVED_KEY: {
            "key": "sequence_name",
            "tool": "flame_get_sequence_segments",
        }
    }
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_rename_resolver_returns_full_structured_payload():
    mcp = _make_mcp(project_count=0)

    resolved = await _resolve_rename_params(
        "Rename the shots on 30sec 21 using prefix genesis "
        "4-digit padding increment 10 starting at 10",
        mcp,
    )

    assert resolved == {
        "sequence_name": "30sec_21",
        "prefix": "genesis",
        "padding": 4,
        "increment": 10,
        "start": 10,
    }
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_rename_tool_merges_structured_resolver_payload():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_rename_shots",
        {},
        mcp,
        message=(
            "Rename the shots on 30sec 21 using prefix genesis "
            "4-digit padding increment 10 starting at 10"
        ),
    )

    assert out == {
        "sequence_name": "30sec_21",
        "prefix": "genesis",
        "padding": 4,
        "increment": 10,
        "start": 10,
    }
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_preview_rename_tool_merges_dry_run_modifier():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_preview_rename",
        {},
        mcp,
        message="Preview rename shots on 30sec 21 using prefix genesis",
    )

    assert out == {
        "sequence_name": "30sec_21",
        "prefix": "genesis",
        "dry_run": True,
    }
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_rename_tool_missing_prefix_returns_unresolved_sentinel():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_rename_shots",
        {},
        mcp,
        message="Rename the shots on 30sec 21",
    )

    assert out == {
        UNRESOLVED_KEY: {
            "key": "prefix",
            "tool": "flame_rename_shots",
        }
    }
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_rename_tool_omits_numeric_defaults_when_absent():
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params(
        "flame_rename_shots",
        {},
        mcp,
        message="Rename the shots on 30sec 21 using prefix genesis",
    )

    assert out == {"sequence_name": "30sec_21", "prefix": "genesis"}
    assert "increment" not in out
    assert "padding" not in out
    assert "start" not in out
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_pr25_polymorphic_dispatch_handles_scalar_and_dict_resolvers(
    monkeypatch,
):
    async def scalar_resolver(message, mcp):
        return "scalar-value"

    async def dict_resolver(message, mcp):
        return {"alpha": "a", "beta": "b"}

    chains = {
        **_PR25_CHAINS,
        "test_scalar_tool": {
            "requires": frozenset({"alpha"}),
            "resolver": "_test_scalar_resolver",
        },
        "test_dict_tool": {
            "requires": frozenset({"alpha", "beta"}),
            "resolver": "_test_dict_resolver",
        },
    }
    resolvers = {
        **_RESOLVERS,
        "_test_scalar_resolver": scalar_resolver,
        "_test_dict_resolver": dict_resolver,
    }
    monkeypatch.setattr("forge_bridge.console._tool_chain._PR25_CHAINS", chains)
    monkeypatch.setattr("forge_bridge.console._tool_chain._RESOLVERS", resolvers)
    mcp = _make_mcp(project_count=0)

    scalar_out = await resolve_required_params(
        "test_scalar_tool",
        {},
        mcp,
        message="scalar",
    )
    dict_out = await resolve_required_params(
        "test_dict_tool",
        {},
        mcp,
        message="dict",
    )

    assert scalar_out == {"alpha": "scalar-value"}
    assert dict_out == {"alpha": "a", "beta": "b"}
    mcp.call_tool.assert_not_called()
