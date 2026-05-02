"""Unit + byte-identity tests for register_console_resources (D-24..D-26,
MFST-02/MFST-03, TOOLS-04)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources


def _record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name, origin="synthesized", namespace="synth",
        tags=("synthesized",),
    )


async def _populated_ms() -> ManifestService:
    ms = ManifestService()
    await ms.register(_record("a_tool"))
    await ms.register(_record("b_tool"))
    return ms


@pytest.fixture
def ms_populated():
    loop = asyncio.new_event_loop()
    try:
        ms = loop.run_until_complete(_populated_ms())
    finally:
        loop.close()
    return ms


@pytest.fixture
def api(ms_populated):
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    mock_log._storage_callback = None
    return ConsoleReadAPI(execution_log=mock_log, manifest_service=ms_populated)


class _ResourceSpy:
    """Mimics FastMCP's decorator API — captures decorated functions by uri/name."""

    def __init__(self):
        self.resources: dict[str, callable] = {}
        self.tools: dict[str, callable] = {}
        # These MagicMock surfaces let us also assert on registration args
        self.resource = MagicMock(side_effect=self._resource_decorator_factory)
        self.tool = MagicMock(side_effect=self._tool_decorator_factory)

    def _resource_decorator_factory(self, uri: str, **kwargs):
        def decorator(fn):
            self.resources[uri] = fn
            return fn
        return decorator

    def _tool_decorator_factory(self, **kwargs):
        name = kwargs.get("name", "")

        def decorator(fn):
            self.tools[name] = fn
            return fn
        return decorator


def test_register_console_resources_registers_all_four_resources(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    uris = [call.args[0] for call in mock_mcp.resource.call_args_list]
    assert "forge://manifest/synthesis" in uris
    assert "forge://tools" in uris
    assert "forge://tools/{name}" in uris
    assert "forge://health" in uris
    # Phase 14 (FB-B) STAGED-07 adds forge://staged/pending (D-12)
    assert "forge://staged/pending" in uris
    assert len(uris) == 5


def test_register_console_resources_registers_two_tool_shims(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    names = [call.kwargs.get("name") for call in mock_mcp.tool.call_args_list]
    # Phase 9 shims (2) + Phase 14 FB-B staged-ops tools (4) + STAGED-07 shim (1) = 7 total.
    assert "forge_manifest_read" in names
    assert "forge_tools_read" in names
    assert "forge_list_staged" in names
    assert "forge_get_staged" in names
    assert "forge_approve_staged" in names
    assert "forge_reject_staged" in names
    assert "forge_staged_pending_read" in names
    assert len(names) == 7


def test_all_resources_have_application_json_mime(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    for call in mock_mcp.resource.call_args_list:
        assert call.kwargs.get("mime_type") == "application/json"


_READ_ONLY_TOOLS = {"forge_manifest_read", "forge_tools_read", "forge_list_staged", "forge_get_staged", "forge_staged_pending_read"}
_WRITE_TOOLS = {"forge_approve_staged", "forge_reject_staged"}


def test_tool_shims_have_read_only_hint(api):
    """Read-only tools carry readOnlyHint=True; write tools carry readOnlyHint=False.

    Phase 14 FB-B adds 4 staged-ops tools: 2 read (list/get) and 2 write
    (approve/reject). The write tools intentionally have readOnlyHint=False per D-16.
    """
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    for call in mock_mcp.tool.call_args_list:
        name = call.kwargs.get("name", "")
        ann = call.kwargs.get("annotations") or {}
        if name in _READ_ONLY_TOOLS:
            assert ann.get("readOnlyHint") is True, f"{name} should have readOnlyHint=True"
        elif name in _WRITE_TOOLS:
            assert ann.get("readOnlyHint") is False, f"{name} should have readOnlyHint=False"
            assert ann.get("destructiveHint") is False, f"{name} should have destructiveHint=False"


def test_barrel_exposes_register_console_resources():
    from forge_bridge.console import register_console_resources as imported
    assert imported is not None


async def test_mfst06_consumer_reads_manifest_via_both_surfaces(api):
    """MFST-06: simulates a consumer (projekt-forge shape) reading without
    duplicating in-process state.

    A MFST-06-compliant consumer must be able to read the synthesis manifest
    via EITHER the /api/v1/manifest HTTP route OR the forge_manifest_read
    MCP tool shim, and see the same canonical state — no in-memory
    duplication on the consumer side. This test reads via BOTH surfaces
    from the same ConsoleReadAPI instance and asserts byte-identity
    (mod. serialization formatting) of the resulting dicts.

    Deliberately uses the MCP tool shim path (spy-captured) rather than a
    live MCP subprocess to keep the test hermetic; Task 6's SC#1 test
    exercises the real subprocess path end-to-end.
    """
    # Surface 1 — HTTP route via TestClient.
    http_body = TestClient(build_console_app(api)).get("/api/v1/manifest").json()

    # Surface 2 — MCP tool shim captured via the spy.
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    tool_body_str = await spy.tools["forge_manifest_read"]()
    tool_body = json.loads(tool_body_str)

    # MFST-06 byte-identity mod formatting: the same ManifestService instance
    # produced both payloads; deserialized dicts MUST be equal.
    assert http_body == tool_body, (
        f"MFST-06 violation — consumer would see different state via the two "
        f"surfaces. Consumers must be able to read via EITHER surface without "
        f"duplicating in-process state.\nHTTP: {http_body!r}\nTool: {tool_body!r}"
    )


# -- Byte-identity tests (D-26) --------------------------------------------

async def test_manifest_resource_body_matches_http_route_bytes(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    resource_body_str = await spy.resources["forge://manifest/synthesis"]()

    client = TestClient(build_console_app(api))
    http_resp = client.get("/api/v1/manifest")
    http_body_str = http_resp.content.decode()

    # Normalize whitespace — JSON byte-identity mod. formatting
    assert json.loads(resource_body_str) == json.loads(http_body_str), (
        f"D-26: resource body must match HTTP route bytes.\n"
        f"Resource: {resource_body_str!r}\nHTTP: {http_body_str!r}"
    )


async def test_tools_resource_body_matches_http_route_bytes(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    resource_body_str = await spy.resources["forge://tools"]()

    client = TestClient(build_console_app(api))
    http_body_str = client.get("/api/v1/tools").content.decode()

    assert json.loads(resource_body_str) == json.loads(http_body_str)


async def test_manifest_tool_shim_matches_manifest_resource_bytes(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    resource_body = await spy.resources["forge://manifest/synthesis"]()
    tool_body = await spy.tools["forge_manifest_read"]()
    assert resource_body == tool_body, (
        f"MFST-03: forge_manifest_read tool must return byte-identical payload to "
        f"forge://manifest/synthesis resource.\n"
        f"Resource: {resource_body!r}\nTool: {tool_body!r}"
    )


def _patch_mcp_to_match_manifest(monkeypatch, names: list[str]) -> None:
    """Bug C — get_tools/get_tool now consult the live MCP registry. Stub it
    to mirror the manifest fixture so the byte-identity assertions stay
    focused on shim behavior rather than the real ~49-tool registry."""
    import forge_bridge.mcp.server as real_server
    from types import SimpleNamespace as _SN
    from forge_bridge.console import _tool_filter

    async def _list_tools():
        return [_SN(name=n) for n in names]

    async def _reach():
        return {"flame_bridge": True}

    monkeypatch.setattr(real_server, "mcp", _SN(list_tools=_list_tools))
    monkeypatch.setattr(_tool_filter, "_get_backend_reachability", _reach)


async def test_tools_shim_with_name_returns_single_tool(api, monkeypatch):
    _patch_mcp_to_match_manifest(monkeypatch, ["a_tool", "b_tool"])
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    body = await spy.tools["forge_tools_read"]("a_tool")
    decoded = json.loads(body)
    assert "data" in decoded
    assert decoded["data"]["name"] == "a_tool"

    body_missing = await spy.tools["forge_tools_read"]("nope")
    decoded_missing = json.loads(body_missing)
    assert decoded_missing["error"]["code"] == "tool_not_found"


async def test_tools_shim_without_name_returns_list(api, monkeypatch):
    _patch_mcp_to_match_manifest(monkeypatch, ["a_tool", "b_tool"])
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    body = await spy.tools["forge_tools_read"](None)
    decoded = json.loads(body)
    assert "data" in decoded
    assert decoded["meta"]["total"] == 2


async def test_tool_detail_resource_returns_tool_not_found_for_missing(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    body = await spy.resources["forge://tools/{name}"]("does_not_exist")
    decoded = json.loads(body)
    assert decoded["error"]["code"] == "tool_not_found"


# -- Phase 14 (FB-B) STAGED-07 D-20 byte-identity tests --------------------

import pytest_asyncio
from forge_bridge.console.read_api import ConsoleReadAPI as _ConsoleReadAPI
from forge_bridge.console.manifest_service import ManifestService as _ManifestService
from forge_bridge.store.staged_operations import StagedOpRepo as _StagedOpRepo
from forge_bridge.mcp.tools import ListStagedInput


@pytest_asyncio.fixture
async def api_with_staged_data(session_factory):
    """A ConsoleReadAPI seeded with a mix of statuses for D-20."""
    ms = _ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = _ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = _StagedOpRepo(session)
        await repo.propose(operation="op_a", proposer="seed", parameters={})
        await repo.propose(operation="op_b", proposer="seed", parameters={})
        op_c = await repo.propose(operation="op_c", proposer="seed", parameters={})
        op_d = await repo.propose(operation="op_d", proposer="seed", parameters={})
        await session.commit()
    async with session_factory() as session:
        repo = _StagedOpRepo(session)
        await repo.approve(op_c.id, approver="seed")  # one approved
        await repo.reject(op_d.id, actor="seed")       # one rejected
        await session.commit()
    return api


async def test_staged_pending_resource_matches_list_tool(api_with_staged_data, session_factory):
    """STAGED-07 / D-20 — forge://staged/pending bytes == forge_list_staged(proposed, 500) bytes.

    Also asserts the shim is byte-identical (P-03 prevention pattern)."""
    spy = _ResourceSpy()
    register_console_resources(
        spy, api_with_staged_data._manifest_service, api_with_staged_data,
        session_factory=session_factory,
    )
    resource_body = await spy.resources["forge://staged/pending"]()
    tool_body = await spy.tools["forge_list_staged"](
        ListStagedInput(status="proposed", limit=500, offset=0)
    )
    shim_body = await spy.tools["forge_staged_pending_read"]()

    assert json.loads(resource_body) == json.loads(tool_body), (
        f"D-20 resource ↔ list_tool divergence.\n"
        f"Resource: {resource_body!r}\nTool: {tool_body!r}"
    )
    assert json.loads(shim_body) == json.loads(resource_body), (
        f"P-03 shim ↔ resource divergence.\n"
        f"Shim: {shim_body!r}\nResource: {resource_body!r}"
    )
    decoded = json.loads(resource_body)
    assert len(decoded["data"]) == 2, decoded   # only proposed ops counted (the 2 un-transitioned)
    assert decoded["meta"]["total"] == 2
    assert decoded["meta"]["limit"] == 500


async def test_staged_pending_empty_queue(session_factory):
    ms = _ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = _ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, session_factory=session_factory,
    )
    spy = _ResourceSpy()
    register_console_resources(spy, ms, api, session_factory=session_factory)
    resource_body = await spy.resources["forge://staged/pending"]()
    decoded = json.loads(resource_body)
    assert decoded["data"] == []
    assert decoded["meta"]["total"] == 0
    assert decoded["meta"]["limit"] == 500
