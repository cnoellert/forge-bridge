"""routing-real: `stage` reachable through the deterministic `/api/v1/exec` entry.

Regression guard for the gap where `execute_command` (and thus `/api/v1/exec`)
did not thread `session_factory` into `run_chain_steps`, so a `stage(...)` step
returned `GRAPH_SESSION_UNAVAILABLE` on the daemon's deterministic path even
though the engine composed correctly in isolation (proven by
`tests/console/test_stage_chain.py`, which drives `run_chain_steps` directly).

These tests drive the actual entry points: the `execute_command` function the
exec handler invokes, and the live `POST /api/v1/exec` ASGI route.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from forge_bridge.console._execute import execute_command
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.store.staged_operations import StagedOpRepo
from tests.console.test_pr30_chain import _text_block

_DRIFT_CHAIN = (
    "forge_assess_drift -> if(disposition == drifted) -> stage(ee_drift_review)"
)
_FILTER_TARGET = (
    "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends"
)


def _assessment(disposition: str) -> dict:
    return {
        "disposition": disposition,
        "verdict": "operator-should-not-see-this-as-parameter",
        "artifact": {
            "assessment_reason": f"assessment reason for {disposition}",
            "source_characterization_id": "src-char-1",
            "comp_characterization_id": "comp-char-1",
        },
    }


def _assess_tool():
    return SimpleNamespace(
        name="forge_assess_drift",
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


class _AssessMCP:
    """Fake MCP exposing `forge_assess_drift` for both list_tools + call_tool.

    Unlike `test_stage_chain.AssessMCP`, this also implements `list_tools`,
    because the exec entry (`execute_command`) builds the tool snapshot itself.
    """

    def __init__(self, disposition: str):
        self._disposition = disposition

    async def list_tools(self):
        return [_assess_tool()]

    async def call_tool(self, name, arguments):
        return _text_block(json.dumps(_assessment(self._disposition)))


async def _passthrough(tools):
    return tools


async def _staged(session_factory):
    async with session_factory() as session:
        records, _total = await StagedOpRepo(session).list()
        return records


@pytest.mark.asyncio
async def test_execute_command_threads_session_factory_and_stages(session_factory):
    with patch(_FILTER_TARGET, new=AsyncMock(side_effect=_passthrough)):
        result = await execute_command(
            _DRIFT_CHAIN,
            mcp=_AssessMCP("drifted"),
            session_factory=session_factory,
        )

    assert result["status"] == "success", result
    records = await _staged(session_factory)
    assert len(records) == 1
    assert records[0].operation == "ee_review.drifted"
    assert records[0].proposer == "bridge.ee_routing"
    assert "verdict" not in records[0].parameters


@pytest.mark.asyncio
async def test_execute_command_without_factory_is_unavailable(session_factory):
    # The exact gap this fix closes: with no factory threaded, the stage node
    # cannot persist and reports GRAPH_SESSION_UNAVAILABLE — no row is staged.
    with patch(_FILTER_TARGET, new=AsyncMock(side_effect=_passthrough)):
        result = await execute_command(_DRIFT_CHAIN, mcp=_AssessMCP("drifted"))

    assert result["status"] == "error"
    assert "GRAPH_SESSION_UNAVAILABLE" in json.dumps(result["error"])
    assert await _staged(session_factory) == []


@pytest.mark.asyncio
async def test_exec_endpoint_stages_through_daemon(session_factory):
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        llm_router=MagicMock(),
        session_factory=session_factory,
    )
    api._execution_log.snapshot.return_value = ([], 0)
    app = build_console_app(api, session_factory=session_factory)

    with patch("forge_bridge.mcp.server.mcp", _AssessMCP("drifted")), patch(
        _FILTER_TARGET, new=AsyncMock(side_effect=_passthrough)
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            resp = await client.post(
                "/api/v1/exec", content=json.dumps({"text": _DRIFT_CHAIN})
            )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success", resp.text
    records = await _staged(session_factory)
    assert len(records) == 1
    assert records[0].operation == "ee_review.drifted"
    assert records[0].proposer == "bridge.ee_routing"
    assert records[0].parameters["assessment_reason"] == (
        "assessment reason for drifted"
    )
    assert "verdict" not in records[0].parameters
