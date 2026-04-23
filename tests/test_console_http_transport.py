"""Integration tests for the console HTTP API served via a real uvicorn task.

Uses the same `_start_console_task` helper that _lifespan uses. Each test
stands up a fresh ConsoleReadAPI + Starlette app + uvicorn Server on an
ephemeral port, hits it via httpx.AsyncClient, then tears down.
"""
from __future__ import annotations

import asyncio
import socket

import httpx
import pytest

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import (
    ConsoleReadAPI,
    register_canonical_singletons,
)
from forge_bridge.mcp.server import _start_console_task


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name, origin="synthesized", namespace="synth",
        tags=("synthesized",),
    )


@pytest.fixture
async def console_server(tmp_path, monkeypatch):
    """Spin up a real uvicorn-served ConsoleReadAPI on an ephemeral port."""
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    # No canonical watcher task — use the fallback gate in _check_watcher.
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )

    log = ExecutionLog(log_path=tmp_path / "execs.jsonl")
    ms = ManifestService()
    await ms.register(_record("a_tool"))
    register_canonical_singletons(log, ms)
    api = ConsoleReadAPI(execution_log=log, manifest_service=ms)

    app = build_console_app(api)
    port = _find_free_port()
    task, server = await _start_console_task(app, "127.0.0.1", port)
    assert task is not None and server is not None

    try:
        yield port, log, ms, api
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                task.cancel()
                try:
                    await task
                except Exception:
                    pass


async def test_console_http_transport_serves_tools_on_bound_port(console_server):
    port, _, _, _ = console_server
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"http://127.0.0.1:{port}/api/v1/tools")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "a_tool"


async def test_console_http_transport_handles_concurrent_requests(console_server):
    port, _, _, _ = console_server
    async with httpx.AsyncClient(timeout=5.0) as client:
        results = await asyncio.gather(*[
            client.get(f"http://127.0.0.1:{port}/api/v1/tools")
            for _ in range(20)
        ])
    assert all(r.status_code == 200 for r in results)


async def test_console_http_transport_serves_health_on_bound_port(console_server):
    port, _, _, _ = console_server
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"http://127.0.0.1:{port}/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    # Instance identity should be green — we registered the canonical singletons
    assert body["data"]["instance_identity"]["execution_log"]["id_match"] is True
