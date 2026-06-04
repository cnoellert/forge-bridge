"""A.1 SSE transport-disposition tests for chat_handler.

These tests preserve transport/error-shape contracts across the A.1
authority-model transition. The retired agentic-loop SSE authority contract
now lives in tests/console/test_chat_compile_branch.py.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from forge_bridge.console import _chat_compile
from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.llm.router import CompileBudgetExceeded


def _parse_sse_stream(text: str) -> list[tuple[str, dict]]:
    """Parse forge-bridge's single-line JSON SSE frames."""
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    current_data: str | None = None
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "":
            if current_event is not None and current_data is not None:
                events.append((current_event, json.loads(current_data)))
            current_event = None
            current_data = None
    return events


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _make_test_tool():
    from mcp.types import Tool
    return Tool(
        name="forge_test_probe",
        description="Test probe tool for chat handler SSE tests.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools):
    return tools


def _chain_success_body() -> dict:
    return {
        "status": "success",
        "request_id": "test-request",
        "chain": [{"step": "forge_test_probe", "result": {"ok": True}}],
        "error": None,
    }


def _build_compile_mock_router(
    *,
    steps: list[str] | None = None,
    side_effect: BaseException | None = None,
):
    mock_router = MagicMock()
    mock_router.compile_intent = AsyncMock(
        side_effect=side_effect,
        return_value=steps or ["forge_test_probe"],
    )
    return mock_router


@pytest.fixture
def make_client():
    """Factory fixture — caller provides the mock router."""
    def _build(mock_router):
        ms = ManifestService()
        mock_log = MagicMock()
        mock_log.snapshot.return_value = ([], 0)
        api = ConsoleReadAPI(
            execution_log=mock_log,
            manifest_service=ms,
            llm_router=mock_router,
        )
        app = build_console_app(api)
        patches = (
            patch(
                "forge_bridge.mcp.server.mcp.list_tools",
                new=AsyncMock(return_value=[_make_test_tool()]),
            ),
            patch(
                "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
                side_effect=_passthrough_filter,
            ),
            patch.object(
                _chat_compile,
                "run_chain_steps",
                new=AsyncMock(return_value=_chain_success_body()),
            ),
        )
        return TestClient(app), patches
    return _build


def test_chat_sse_accept_returns_event_stream_content_type(make_client):
    """`Accept: text/event-stream` flips the response to SSE."""
    mock_router = _build_compile_mock_router()
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers["content-type"]
    assert "X-Request-ID" in response.headers
    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_complete", "chain_complete"]


def test_compile_complete_exposes_compiled_graph_exposure_only(make_client):
    """S3.1 — compile_complete surfaces compiled_graph == list(outcome.steps).
    Exposed, never transformed: a copy of the steps, steps_count unchanged, event
    sequence identical (no behavior change to compile/dispatch/ratify)."""
    mock_router = _build_compile_mock_router(steps=["forge_test_probe", "forge_test_probe"])
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )
    assert response.status_code == 200, response.text
    events = dict(_parse_sse_stream(response.text))
    cc = events["compile_complete"]
    assert cc["compiled_graph"] == ["forge_test_probe", "forge_test_probe"]  # exposed verbatim
    assert cc["steps_count"] == 2 and cc["steps_count"] == len(cc["compiled_graph"])  # unchanged
    assert "chain_complete" in events  # same terminal taxon — behavior unchanged


def test_chat_sse_no_accept_header_returns_json(make_client):
    """No Accept header routes to the JSON transport, not SSE."""
    mock_router = _build_compile_mock_router()
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert response.status_code == 200, response.text
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert body["stop_reason"] == "chain_complete"
    assert body["chain"] == _chain_success_body()["chain"]


def test_chat_sse_rate_limit_gate_returns_json_429(make_client):
    """Rate-limit fires before stream start, so SSE clients still get JSON."""
    mock_router = _build_compile_mock_router()
    client, patches = make_client(mock_router)
    payload = {"messages": [{"role": "user", "content": "hi"}]}

    with patches[0], patches[1], patches[2]:
        for _ in range(10):
            response = client.post(
                "/api/v1/chat",
                json=payload,
                headers={"Accept": "text/event-stream"},
            )
            assert response.status_code == 200

        response = client.post(
            "/api/v1/chat",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 429
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in response.headers


def test_chat_sse_compile_budget_exceeded_emits_compile_error_event(make_client):
    """Compile budget exhaustion is a compile_error SSE taxon, not transport."""
    mock_router = _build_compile_mock_router(
        side_effect=CompileBudgetExceeded(30.0, 31.0),
    )
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 200
    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_error"]
    payload = events[0][1]
    assert payload["error"]["code"] == "compile_budget_exceeded"
    assert payload["stop_reason"] == "compile_error"


def test_chat_sse_outer_timeout_emits_in_stream_error(make_client):
    """Outer wait_for timeout remains a transport error event."""
    mock_router = _build_compile_mock_router(side_effect=asyncio.TimeoutError())
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 200
    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["error"]
    assert events[0][1]["error"]["code"] == "request_timeout"


def test_chat_sse_event_format_is_strict_html5_sse(make_client):
    """Frame terminator is `\\n\\n`; each frame has event and data lines."""
    mock_router = _build_compile_mock_router()
    client, patches = make_client(mock_router)
    with patches[0], patches[1], patches[2]:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Accept": "text/event-stream"},
        )

    frames = [frame for frame in response.text.split("\n\n") if frame.strip()]
    for frame in frames:
        lines = frame.split("\n")
        assert any(line.startswith("event:") for line in lines), (
            f"frame missing `event:` line: {frame!r}"
        )
        assert any(line.startswith("data:") for line in lines), (
            f"frame missing `data:` line: {frame!r}"
        )
        data_line = next(line for line in lines if line.startswith("data:"))
        json.loads(data_line[len("data:"):].strip())
