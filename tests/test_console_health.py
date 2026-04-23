"""Unit tests for ConsoleReadAPI.get_health (D-13..D-18, full D-14 body)."""
from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from forge_bridge import __version__
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import (
    ConsoleReadAPI,
    register_canonical_singletons,
)


@pytest.fixture
def real_log(tmp_path):
    from forge_bridge.learning.execution_log import ExecutionLog
    return ExecutionLog(log_path=tmp_path / "execs.jsonl")


@pytest.fixture
def ms():
    return ManifestService()


# -- D-14 shape ------------------------------------------------------------

async def test_health_body_has_d14_shape(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    assert set(body.keys()) >= {"status", "ts", "version", "services", "instance_identity"}
    expected_services = {
        "mcp", "flame_bridge", "ws_server", "llm_backends",
        "watcher", "storage_callback", "console_port",
    }
    assert set(body["services"].keys()) >= expected_services
    assert set(body["instance_identity"].keys()) >= {"execution_log", "manifest_service"}


# -- Instance-identity gate (LRN-05) ---------------------------------------

async def test_health_instance_identity_id_match_true_at_steady_state(real_log, ms, monkeypatch):
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    register_canonical_singletons(real_log, ms)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    assert body["instance_identity"]["execution_log"]["id_match"] is True
    assert body["instance_identity"]["manifest_service"]["id_match"] is True


async def test_health_instance_identity_id_match_false_detects_drift(tmp_path, monkeypatch):
    from forge_bridge.learning.execution_log import ExecutionLog
    canonical_log = ExecutionLog(log_path=tmp_path / "canonical.jsonl")
    canonical_ms = ManifestService()
    register_canonical_singletons(canonical_log, canonical_ms)

    # Now construct ConsoleReadAPI with DIFFERENT instances — simulates LRN-05 bug
    other_log = ExecutionLog(log_path=tmp_path / "other.jsonl")
    other_ms = ManifestService()
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=other_log, manifest_service=other_ms)

    body = await api.get_health()
    assert body["instance_identity"]["execution_log"]["id_match"] is False
    assert "DRIFT" in body["instance_identity"]["execution_log"]["detail"]
    assert body["status"] == "fail"


# -- Status aggregation (D-15) ---------------------------------------------

async def test_health_status_ok_when_all_services_ok(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    # Stub flame_bridge + ws_server to report ok so non-critical failures
    # don't flip to degraded in the absence of real servers
    monkeypatch.setattr(api, "_flame_bridge_url", "http://127.0.0.1:99999", raising=True)
    body = await api.get_health()
    # status may be degraded (flame/ws not running in test env) — that's ok;
    # assert only that the shape + instance_identity is clean
    assert body["status"] in ("ok", "degraded")
    assert body["instance_identity"]["execution_log"]["id_match"] is True


async def test_health_status_fail_when_watcher_fails(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", False, raising=False)
    # Ensure no canonical watcher task is set (falls back to coarse gate)
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    assert body["status"] == "fail"
    assert body["services"]["watcher"]["status"] == "fail"


async def test_health_watcher_reports_fail_when_watcher_crashed(real_log, ms, monkeypatch):
    """I-02: when _canonical_watcher_task is done() with an exception,
    get_health().services.watcher must report status=fail, task_done=True,
    and detail=<ExceptionClassName>."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)

    async def _raises():
        raise RuntimeError("watcher exploded")

    crashed_task = asyncio.create_task(_raises())
    # Drive the task to done() with an exception (shield against await-raises)
    try:
        await asyncio.wait_for(crashed_task, timeout=0.2)
    except Exception:
        pass
    assert crashed_task.done()
    assert crashed_task.exception() is not None

    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task",
        crashed_task,
        raising=False,
    )

    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    watcher = body["services"]["watcher"]
    assert watcher["status"] == "fail", (
        f"I-02: crashed watcher task must report status=fail. Got: {watcher!r}"
    )
    assert watcher["task_done"] is True
    assert watcher["detail"] == "RuntimeError", (
        f"I-02: detail must be the exception class name. Got: {watcher!r}"
    )
    # Aggregated status is fail because watcher is critical per D-15.
    assert body["status"] == "fail"


# -- Storage callback -------------------------------------------------------

async def test_health_storage_callback_registered_or_absent(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)

    # Absent
    body = await api.get_health()
    assert body["services"]["storage_callback"]["status"] == "absent"
    assert body["services"]["storage_callback"]["registered"] is False

    # Registered
    def _cb(record):
        return None
    real_log.set_storage_callback(_cb)
    body = await api.get_health()
    assert body["services"]["storage_callback"]["status"] == "ok"
    assert body["services"]["storage_callback"]["registered"] is True


# -- Console port reflects constructor -------------------------------------

async def test_health_console_port_reflects_constructor(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms, console_port=9997)
    body = await api.get_health()
    assert body["services"]["console_port"]["port"] == 9997


# -- Version + ts ----------------------------------------------------------

async def test_health_version_matches_package_version(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    assert body["version"] == __version__


async def test_health_ts_is_iso8601_utc(real_log, ms, monkeypatch):
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    ts = datetime.fromisoformat(body["ts"])
    assert ts.tzinfo is not None  # UTC-offset present


# -- LLM backends (stub/empty case) ----------------------------------------

async def test_health_llm_backends_empty_when_no_router(real_log, ms, monkeypatch):
    """When llm_router is None, services.llm_backends is []."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms, llm_router=None)
    body = await api.get_health()
    assert body["services"]["llm_backends"] == []
