"""PR27 — Unit and integration tests for deterministic multi-entity
disambiguation.

Two layers covered:

  - **Unit tests** target ``_tool_chain.resolve_required_params`` and
    ``_resolve_project_id`` directly. They pin the sentinel return
    shape, the no-memory-write rule, and the precedence interaction
    with PR26 caller params + memory.

  - **Integration tests** drive the chat handler end-to-end with a
    multi-project fixture and verify the wire contract: 400 status,
    structured error envelope with ``code: MULTIPLE_PROJECTS``,
    ``details.candidates`` populated, and zero downstream tool /
    LLM activity.

Per the PR27 brief's six ACs:
  1. Multiple projects   → MULTIPLE_PROJECTS sentinel + 400 envelope
  2. Single project      → unchanged PR25/PR26 behavior
  3. Zero projects       → unchanged MISSING_PROJECT_ID path
  4. Memory hit          → bypass disambiguation entirely
  5. Caller-provided id  → bypass disambiguation entirely
  6. Strict candidate validation (PR27 fail-closed constraint)
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._memory import _MEMORY
from forge_bridge.console._tool_chain import (
    _resolve_project_id,
    resolve_required_params,
)
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI


# ── Helpers — unit-level (mocked mcp.call_tool) ──────────────────────────


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
    mcp = AsyncMock()

    async def fake(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_projects_payload(project_count))
        return _text_block(json.dumps({"called": name, "args": arguments}))

    mcp.call_tool = AsyncMock(side_effect=fake)
    return mcp


# ── Unit AC #1: Multi → sentinel ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_pr27_multi_projects_returns_disambiguation_sentinel():
    """Resolver detects 2+ projects → ``resolve_required_params`` returns
    a sentinel dict with ``__disambiguation__`` key. Sentinel structure:
    ``{"type": "project", "candidates": [{"id", "name"}, ...]}``."""
    mcp = _make_mcp(project_count=3)

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert "__disambiguation__" in out
    sentinel = out["__disambiguation__"]
    assert sentinel["type"] == "project"
    candidates = sentinel["candidates"]
    assert len(candidates) == 3
    # Each candidate exposes only id + name — extra fields stripped.
    for i, c in enumerate(candidates):
        assert set(c.keys()) == {"id", "name"}
        assert c["id"] == f"proj-{i}"
        assert c["name"] == f"P{i}"
    # Order preserved from upstream.
    assert [c["id"] for c in candidates] == ["proj-0", "proj-1", "proj-2"]


@pytest.mark.asyncio
async def test_pr27_multi_projects_does_not_write_memory():
    """Brief constraint #3: ambiguous resolution must NOT update
    memory. Verifies memory stays empty after a multi-candidate
    resolution."""
    assert _MEMORY.get("project_id") is None  # autouse guarantee
    mcp = _make_mcp(project_count=2)

    await resolve_required_params("forge_list_versions", {}, mcp)

    assert _MEMORY.get("project_id") is None


@pytest.mark.asyncio
async def test_pr27_sentinel_does_not_carry_caller_params():
    """Per the brief's literal sentinel-only return: caller-provided
    non-required params are NOT preserved on the disambiguation path.
    This is intentional — the handler short-circuits to 400 before any
    tool would run, so non-required params have no destination.

    Tracking-friendly: if a future change starts merging caller params
    into the sentinel (for trace context), this test catches the
    semantic change so the contract update is deliberate."""
    mcp = _make_mcp(project_count=2)
    out = await resolve_required_params(
        "forge_list_versions", {"shot_id": "extra-context"}, mcp,
    )
    assert "__disambiguation__" in out
    assert "shot_id" not in out


# ── Unit AC #2: Single → existing PR25/PR26 path ─────────────────────────


@pytest.mark.asyncio
async def test_pr27_single_project_keeps_existing_inject_path():
    """One project → resolver returns a string id (not a list), the
    PR25/PR26 inject + memory-write path runs unchanged. No sentinel."""
    mcp = _make_mcp(project_count=1)

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {"project_id": "proj-0"}
    assert "__disambiguation__" not in out
    assert _MEMORY.get("project_id") == "proj-0"


# ── Unit AC #3: Zero → existing MISSING_PROJECT_ID path ──────────────────


@pytest.mark.asyncio
async def test_pr27_zero_projects_does_not_emit_sentinel():
    """Zero projects keeps the existing fail-closed behavior — empty
    dict return, NO sentinel. Handler then surfaces MISSING_PROJECT_ID
    via the PR22 graceful contract (200 + tool message), distinct from
    PR27's MULTIPLE_PROJECTS (400 + structured envelope)."""
    mcp = _make_mcp(project_count=0)

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {}
    assert "__disambiguation__" not in out


# ── Unit AC #4: Memory hit → bypass disambiguation entirely ──────────────


@pytest.mark.asyncio
async def test_pr27_memory_hit_bypasses_disambiguation_even_with_multiple_projects():
    """When memory holds a value, the satisfied-via-memory short-circuit
    fires BEFORE the resolver runs — so even a system with multiple
    projects yields a clean inject path. No probe call, no sentinel."""
    _MEMORY.set("project_id", "memorized-uuid")

    # System has many projects, but memory short-circuits everything.
    mcp = _make_mcp(project_count=10)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {"project_id": "memorized-uuid"}
    assert "__disambiguation__" not in out
    # Crucial: NO upstream call — the resolver never ran.
    mcp.call_tool.assert_not_called()


# ── Unit AC #5: Caller-supplied id → bypass disambiguation entirely ──────


@pytest.mark.asyncio
async def test_pr27_caller_supplied_project_id_bypasses_disambiguation():
    """Caller-provided ``project_id`` satisfies the requirement before
    memory or resolver runs. Even a multi-project system yields the
    caller's value with no probe and no sentinel.

    This is the PR26 precedence contract (``explicit > memory >
    resolver``) carrying through into PR27 unchanged: ambiguity is only
    detected when the resolver would have fired."""
    mcp = _make_mcp(project_count=5)
    out = await resolve_required_params(
        "forge_list_versions", {"project_id": "caller-pick"}, mcp,
    )

    assert out == {"project_id": "caller-pick"}
    assert "__disambiguation__" not in out
    mcp.call_tool.assert_not_called()


# ── Unit AC #6: Strict candidate validation (fail-closed) ────────────────


@pytest.mark.asyncio
async def test_pr27_resolver_returns_none_on_malformed_multi_candidate():
    """Brief constraint #4: malformed candidates → treat as None.
    A single missing-id entry collapses the entire multi-candidate
    list to None — better to surface MISSING_PROJECT_ID than expose
    half-validated candidates to a caller selecting from them."""
    mcp = AsyncMock()
    # 3 projects, middle one has no id — strict fail-closed → None.
    mcp.call_tool = AsyncMock(return_value=_text_block(json.dumps({
        "count": 3,
        "projects": [
            {"id": "proj-0", "name": "P0"},
            {"name": "P1"},  # missing id
            {"id": "proj-2", "name": "P2"},
        ],
    })))

    result = await _resolve_project_id(mcp)

    assert result is None


@pytest.mark.asyncio
async def test_pr27_resolver_normalizes_missing_name_in_multi_candidate():
    """Missing ``name`` is non-fatal (normalized to empty string) —
    only ``id`` is strictly required for a candidate to be usable."""
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(json.dumps({
        "count": 2,
        "projects": [
            {"id": "proj-0", "name": "P0"},
            {"id": "proj-1"},  # name missing → normalized
        ],
    })))

    result = await _resolve_project_id(mcp)

    assert isinstance(result, list)
    assert result == [
        {"id": "proj-0", "name": "P0"},
        {"id": "proj-1", "name": ""},
    ]


# ── Constant-coupling lock — single source of truth ──────────────────────


@pytest.mark.asyncio
async def test_pr27_uses_constant_for_disambiguation_key():
    """Lock the sentinel-key contract to a single source of truth.

    Two assertions, two distinct regression risks:

      1. ``DISAMBIGUATION_KEY in out`` — the production code path
         must produce a sentinel whose key matches the EXPORTED
         constant. If a refactor reintroduces a magic-string literal
         and lets the constant drift, this fails.

      2. ``"__disambiguation__" == DISAMBIGUATION_KEY`` — the
         constant's VALUE must remain the wire string. External
         consumers of the chat error envelope (and the rest of this
         test file's assertions) reference the literal; if someone
         renames the value of the constant, this catches it before
         the rename ships."""
    from forge_bridge.console._tool_chain import DISAMBIGUATION_KEY

    mcp = _make_mcp(project_count=3)
    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert DISAMBIGUATION_KEY in out
    assert "__disambiguation__" == DISAMBIGUATION_KEY


# ── Integration tests — chat handler end-to-end ──────────────────────────


def _passthrough_filter(tools, **_):
    return tools


def _make_handler_app_for_disambiguation(project_count: int):
    """Build a chat-handler app whose tool registry contains a single
    forced-execution target (``forge_list_versions``) and a stubbed
    ``mcp.call_tool`` that returns the requested project count from
    ``forge_list_projects``."""
    from mcp.types import TextContent, Tool

    tools_list = [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in [
            "forge_list_versions",  # the target — narrow filter to 1 hits PR20
            "flame_alpha", "flame_beta", "synth_gamma",  # disjoint vocab
        ]
    ]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, llm_router=mock_router,
    )
    app = build_console_app(api)

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(type="text", text=_projects_payload(project_count))]
        return [TextContent(
            type="text", text=f"{name}-result:{arguments!r}",
        )]

    list_p = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    )
    back_p = patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    )
    call_p = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=fake_call_tool),
    )
    return list_p, back_p, call_p, app, mock_router


def test_pr27_handler_returns_400_with_multiple_projects_envelope():
    """End-to-end: a multi-project deployment + a forced
    ``forge_list_versions`` request → handler returns 400 with the
    full PR27 envelope shape:

        {"error": {
            "code": "MULTIPLE_PROJECTS",
            "message": "Multiple projects found. Please specify one.",
            "details": {"type": "project", "candidates": [...]}
        }}

    No tool call, no LLM call, X-Request-ID still set."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_disambiguation(project_count=3)
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    # Wire contract — 400, structured envelope, request-id header.
    assert r.status_code == 400, r.text
    assert "X-Request-ID" in r.headers
    body = r.json()
    err = body["error"]
    assert err["code"] == "MULTIPLE_PROJECTS"
    assert err["message"] == "Multiple projects found. Please specify one."
    details = err["details"]
    assert details["type"] == "project"
    assert len(details["candidates"]) == 3
    for c in details["candidates"]:
        assert set(c.keys()) == {"id", "name"}

    # Hard contracts — neither tool nor LLM ran.
    mock_router.complete_with_tools.assert_not_called()
    # Only the projects probe was issued; forge_list_versions was NOT.
    call_mock.assert_called_once_with("forge_list_projects", {})


def test_pr27_handler_does_not_write_memory_on_disambiguation():
    """Through the chat handler: a 400 disambiguation response leaves
    memory untouched. Verifies the no-memory-write constraint holds at
    the integration boundary, not just at the unit level."""
    assert _MEMORY.get("project_id") is None  # autouse fixture
    list_p, back_p, call_p, app, _ = (
        _make_handler_app_for_disambiguation(project_count=4)
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 400
    assert _MEMORY.get("project_id") is None


def test_pr27_handler_single_project_path_unchanged():
    """Sanity: with one project, the handler still takes the PR24/26
    forced-execution path (200 + tool messages), not PR27's 400."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_disambiguation(project_count=1)
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    # Probe + actual tool — both called, project_id injected.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {"project_id": "proj-0"})
    mock_router.complete_with_tools.assert_not_called()


def test_pr27_handler_zero_projects_path_unchanged():
    """Sanity: zero projects keeps the existing PR22 contract path
    (200 + tool message with MISSING_PROJECT_ID). Distinct from PR27's
    400 envelope — different failure mode, different wire shape."""
    list_p, back_p, call_p, app, mock_router = (
        _make_handler_app_for_disambiguation(project_count=0)
    )

    # The fixture's default fake returns text-not-JSON for forge_list_versions,
    # which won't hit the PR22 graceful contract (since the real tool isn't
    # invoked through Pydantic here). Layer in a more PR22-faithful stub.
    from mcp.types import TextContent

    async def pr22_aware_fake(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(type="text", text=_projects_payload(0))]
        if name == "forge_list_versions" and "project_id" not in arguments:
            return [TextContent(type="text", text=json.dumps({
                "error": "project_id is required",
                "code": "MISSING_PROJECT_ID",
            }))]
        return [TextContent(type="text", text=f"{name}-result:{arguments!r}")]

    call_p2 = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=pr22_aware_fake),
    )

    with list_p, back_p, call_p2:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    # Zero-projects path is the existing PR22 contract — 200 + tool msg.
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    tool_msg = body["messages"][-1]
    payload = json.loads(tool_msg["content"])
    assert payload["code"] == "MISSING_PROJECT_ID"
    mock_router.complete_with_tools.assert_not_called()
