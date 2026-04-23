"""Unit tests for ConsoleReadAPI (API-01 + EXECS-04 + API-04 precondition)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI


def _make_record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name, origin="synthesized", namespace="synth",
        tags=("synthesized",),
    )


# -- Instance-identity / construction ---------------------------------------


def test_console_read_api_init_requires_execution_log_and_manifest_service():
    with pytest.raises(TypeError):
        ConsoleReadAPI()  # no args
    with pytest.raises(TypeError):
        ConsoleReadAPI(execution_log=MagicMock())  # missing manifest_service
    # Both required args -> ok
    ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ManifestService())


# -- Tools delegation -------------------------------------------------------


async def test_get_tools_delegates_to_manifest_service():
    ms = ManifestService()
    await ms.register(_make_record("a_tool"))
    await ms.register(_make_record("b_tool"))
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)
    got = await api.get_tools()
    assert [t.name for t in got] == ["a_tool", "b_tool"]


async def test_get_tool_returns_single_record_or_none():
    ms = ManifestService()
    await ms.register(_make_record("x"))
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)
    assert (await api.get_tool("x")).name == "x"
    assert await api.get_tool("nope") is None


# -- Executions forwarding --------------------------------------------------


async def test_get_executions_forwards_all_kwargs_to_snapshot():
    # W-01: `tool` kwarg intentionally absent -- route layer rejects with 400.
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ManifestService())
    since = datetime(2026, 4, 22, 0, 0, 0)
    await api.get_executions(
        limit=5, offset=2, since=since,
        promoted_only=True, code_hash="abc",
    )
    mock_log.snapshot.assert_called_once_with(
        limit=5, offset=2, since=since,
        promoted_only=True, code_hash="abc",
    )


async def test_get_executions_does_not_accept_tool_kwarg():
    """W-01: `tool` kwarg must NOT exist on ConsoleReadAPI.get_executions.

    The /api/v1/execs route handler in Plan 09-03 rejects `?tool=...` with
    a 400 `not_implemented` response; the read layer therefore never sees
    it and should not quietly accept it.
    """
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ManifestService())
    with pytest.raises(TypeError):
        # Attempting to pass tool= must raise (unexpected kwarg)
        await api.get_executions(tool="synth_*")


# -- Manifest envelope shape -----------------------------------------------


async def test_get_manifest_returns_envelope_shape():
    ms = ManifestService()
    await ms.register(_make_record("a"))
    await ms.register(_make_record("b"))
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)
    got = await api.get_manifest()
    assert set(got.keys()) == {"tools", "count", "schema_version"}
    assert got["count"] == 2
    assert got["schema_version"] == "1"
    assert isinstance(got["tools"], list)
    assert got["tools"][0]["name"] == "a"
    # tags should be on the wire as a list, not a tuple
    assert isinstance(got["tools"][0]["tags"], list)


# -- Async method signatures -----------------------------------------------


def test_get_tools_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_tools)


def test_get_executions_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_executions)


def test_get_manifest_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_manifest)
