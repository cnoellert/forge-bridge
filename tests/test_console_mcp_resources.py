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
    assert len(uris) == 4


def test_register_console_resources_registers_two_tool_shims(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    names = [call.kwargs.get("name") for call in mock_mcp.tool.call_args_list]
    assert "forge_manifest_read" in names
    assert "forge_tools_read" in names
    assert len(names) == 2


def test_all_resources_have_application_json_mime(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    for call in mock_mcp.resource.call_args_list:
        assert call.kwargs.get("mime_type") == "application/json"


def test_tool_shims_have_read_only_hint(api):
    mock_mcp = MagicMock()
    register_console_resources(mock_mcp, api._manifest_service, api)
    for call in mock_mcp.tool.call_args_list:
        ann = call.kwargs.get("annotations") or {}
        assert ann.get("readOnlyHint") is True


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


async def test_tools_shim_with_name_returns_single_tool(api):
    spy = _ResourceSpy()
    register_console_resources(spy, api._manifest_service, api)
    body = await spy.tools["forge_tools_read"]("a_tool")
    decoded = json.loads(body)
    assert "data" in decoded
    assert decoded["data"]["name"] == "a_tool"

    body_missing = await spy.tools["forge_tools_read"]("nope")
    decoded_missing = json.loads(body_missing)
    assert decoded_missing["error"]["code"] == "tool_not_found"


async def test_tools_shim_without_name_returns_list(api):
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
