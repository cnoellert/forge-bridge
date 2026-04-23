"""Unit tests for console HTTP route handlers (D-01..D-05, CORS)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI


def _record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name, origin="synthesized", namespace="synth",
        tags=("synthesized",),
    )


@pytest.fixture
def client():
    ms = ManifestService()
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(ms.register(_record("a_tool")))
        loop.run_until_complete(ms.register(_record("b_tool")))
    finally:
        loop.close()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    app = build_console_app(api)
    return TestClient(app)


# -- Tools ------------------------------------------------------------------

def test_tools_route_returns_envelope(client):
    r = client.get("/api/v1/tools")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["total"] == 2
    names = [t["name"] for t in body["data"]]
    assert names == ["a_tool", "b_tool"]
    # D-04 snake_case on the wire; tuples become lists
    assert isinstance(body["data"][0]["tags"], list)


def test_tool_detail_route_returns_single(client):
    r = client.get("/api/v1/tools/a_tool")
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "a_tool"

    r = client.get("/api/v1/tools/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "tool_not_found"


# -- Execs — pagination + clamping + filters ------------------------------

def test_execs_route_returns_envelope_with_pagination(client):
    r = client.get("/api/v1/execs?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["limit"] == 2
    assert body["meta"]["offset"] == 0
    assert "total" in body["meta"]


def test_execs_route_limit_is_clamped_to_500(client):
    r = client.get("/api/v1/execs?limit=1000")
    assert r.status_code == 200
    assert r.json()["meta"]["limit"] == 500  # D-05


def test_execs_route_parses_since_query(client):
    r = client.get("/api/v1/execs?since=2026-04-22T00:00:00")
    assert r.status_code == 200
    # Verify it was forwarded as a datetime
    api: ConsoleReadAPI = client.app.state.console_read_api
    api._execution_log.snapshot.assert_called()
    kwargs = api._execution_log.snapshot.call_args.kwargs
    assert isinstance(kwargs["since"], datetime)
    assert kwargs["since"].year == 2026


def test_execs_route_parses_promoted_only(client):
    r = client.get("/api/v1/execs?promoted_only=true")
    assert r.status_code == 200
    api: ConsoleReadAPI = client.app.state.console_read_api
    assert api._execution_log.snapshot.call_args.kwargs["promoted_only"] is True


def test_execs_route_parses_code_hash_prefix(client):
    r = client.get("/api/v1/execs?code_hash=abcd")
    assert r.status_code == 200
    api: ConsoleReadAPI = client.app.state.console_read_api
    assert api._execution_log.snapshot.call_args.kwargs["code_hash"] == "abcd"


def test_execs_route_bad_since_returns_400(client):
    r = client.get("/api/v1/execs?since=not-a-timestamp")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_request"


def test_execs_tool_filter_returns_400_not_implemented(client):
    """W-01: ?tool=... is rejected with 400 `not_implemented` in v1.3.

    RESEARCH.md Open Questions (RESOLVED) Q#1 defers the tool-glob join
    to v1.4 (streaming + richer filters). The handler MUST reject the param
    early so clients get a clear deferral signal rather than a silently
    ignored filter.
    """
    r = client.get("/api/v1/execs?tool=synth_*")
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "not_implemented", (
        f"Expected error.code == 'not_implemented', got {body!r}"
    )
    assert "v1.4" in body["error"]["message"].lower() or "reserved" in body["error"]["message"].lower()


# -- Manifest + Health ------------------------------------------------------

def test_manifest_route_returns_envelope(client):
    r = client.get("/api/v1/manifest")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["count"] == 2
    assert body["data"]["schema_version"] == "1"
    assert len(body["data"]["tools"]) == 2


def test_health_route_returns_envelope(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body["data"]
    assert "instance_identity" in body["data"]


# -- CORS -------------------------------------------------------------------

def test_cors_allow_origin_localhost(client):
    r = client.options(
        "/api/v1/tools",
        headers={
            "Origin": "http://localhost:9996",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:9996"


def test_cors_rejects_other_origin(client):
    r = client.options(
        "/api/v1/tools",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") != "http://evil.example.com"


# -- LOGGING_CONFIG ---------------------------------------------------------

def test_logging_config_routes_to_stderr():
    from forge_bridge.console.logging_config import STDERR_ONLY_LOGGING_CONFIG
    assert STDERR_ONLY_LOGGING_CONFIG["handlers"]["default"]["stream"] == "ext://sys.stderr"
    assert "uvicorn" in STDERR_ONLY_LOGGING_CONFIG["loggers"]
    assert "uvicorn.access" in STDERR_ONLY_LOGGING_CONFIG["loggers"]
    assert "uvicorn.error" in STDERR_ONLY_LOGGING_CONFIG["loggers"]
    for lg in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert STDERR_ONLY_LOGGING_CONFIG["loggers"][lg]["handlers"] == ["default"]


# -- Error envelope (no traceback leak) -------------------------------------

def test_error_handler_returns_error_envelope():
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.side_effect = RuntimeError("secret credentials in str(exc)")
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    app = build_console_app(api)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/v1/execs")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    # MUST NOT leak the raised exception message into the response
    assert "secret credentials" not in body["error"]["message"]
