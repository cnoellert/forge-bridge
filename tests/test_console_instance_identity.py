"""Integration tests for API-04 / D-16 instance-identity gate.

SC#3 (09-VALIDATION.md): a live ExecutionLog.record() call must be visible
via ConsoleReadAPI.get_executions() when both seats share the canonical
instance. A mismatch must flip /api/v1/health.status to "fail".
"""
from __future__ import annotations

import pytest

from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import (
    ConsoleReadAPI,
    register_canonical_singletons,
)


@pytest.fixture
def shared(tmp_path, monkeypatch):
    """Canonical (ExecutionLog, ManifestService, ConsoleReadAPI) bundle."""
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )
    log = ExecutionLog(log_path=tmp_path / "execs.jsonl")
    ms = ManifestService()
    register_canonical_singletons(log, ms)
    api = ConsoleReadAPI(execution_log=log, manifest_service=ms)
    return log, ms, api


# -- SC#3 — live bridge.execute -> /api/v1/execs round-trip ---------------

async def test_instance_identity_bridge_execute_appears_in_execs(shared):
    log, ms, api = shared
    # Simulate the bridge.execute codepath — this goes through the canonical
    # ExecutionLog (same id as what api wraps).
    log.record("x = 1")
    log.record("y = 2")

    records, total = await api.get_executions(limit=50)
    assert total == 2
    raw_codes = [r.raw_code for r in records]
    assert "x = 1" in raw_codes
    assert "y = 2" in raw_codes


async def test_instance_identity_health_id_match_true_end_to_end(shared):
    log, ms, api = shared
    body = await api.get_health()
    assert body["instance_identity"]["execution_log"]["id_match"] is True
    assert body["instance_identity"]["manifest_service"]["id_match"] is True


# -- LRN-05 — two instances must flip health to fail ----------------------

async def test_instance_identity_two_instances_flips_health_to_fail(tmp_path, monkeypatch):
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )

    canonical_log = ExecutionLog(log_path=tmp_path / "canonical.jsonl")
    canonical_ms = ManifestService()
    register_canonical_singletons(canonical_log, canonical_ms)

    # LRN-05 bug: pass a DIFFERENT log to ConsoleReadAPI
    other_log = ExecutionLog(log_path=tmp_path / "other.jsonl")
    other_ms = ManifestService()
    api = ConsoleReadAPI(execution_log=other_log, manifest_service=other_ms)

    body = await api.get_health()
    assert body["instance_identity"]["execution_log"]["id_match"] is False
    assert body["instance_identity"]["manifest_service"]["id_match"] is False
    assert body["status"] == "fail", (
        f"Expected status='fail' when instance_identity mismatches. "
        f"Got: {body['status']!r}"
    )


# -- Storage callback preserves identity -----------------------------------

async def test_instance_identity_preserves_across_record_callback(shared):
    log, ms, api = shared
    captured_records = []

    def _cb(record):
        captured_records.append(record)

    log.set_storage_callback(_cb)
    log.record("x = 42")

    # The callback saw the record
    assert len(captured_records) == 1
    assert captured_records[0].raw_code == "x = 42"

    # The canonical ConsoleReadAPI also sees it (same ExecutionLog instance)
    records, total = await api.get_executions(limit=10)
    assert total == 1
    assert records[0].raw_code == "x = 42"

    # Instance identity still green
    body = await api.get_health()
    assert body["instance_identity"]["execution_log"]["id_match"] is True
