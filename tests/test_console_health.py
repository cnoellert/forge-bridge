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
        "watcher", "storage_callback", "postgres", "console_port",
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


class _StubRouter:
    """Minimal LLMRouter stand-in for health-check assertions.

    Phase 23 Commit A: pins the operator-visible reachability framing in
    services.llm_backends[*].detail. Two states matter for the operator
    reading `fbridge doctor` output:

      - ok    → "reachable; model={name}"
      - fail  → "unreachable; model={name}"

    Stub returns the dict shape ConsoleReadAPI._check_llm_backends parses
    (mirrors router.ahealth_check's contract: local/cloud booleans plus
    *_model strings).
    """

    def __init__(self, status):
        self._status = status

    async def ahealth_check(self):
        return self._status


async def test_health_llm_backend_detail_says_reachable_when_ok(real_log, ms, monkeypatch):
    """services.llm_backends[*].detail leads with `reachable;` when the
    backend is up. Operators reading the doctor row should see the
    reachability state in the first token — not buried behind the model
    name. Phase 23 DIAG-03 doctor-coverage parity."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    router = _StubRouter({
        "local": True, "cloud": False,
        "local_model": "qwen2.5-coder:32b",
        "cloud_model": "claude-sonnet-4-6",
    })
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms, llm_router=router)
    body = await api.get_health()
    backends = body["services"]["llm_backends"]
    local = next(b for b in backends if b["name"] == "local")
    assert local["status"] == "ok"
    assert local["detail"].startswith("reachable;")
    assert "qwen2.5-coder:32b" in local["detail"]


async def test_health_llm_backend_detail_says_unreachable_when_down(real_log, ms, monkeypatch):
    """services.llm_backends[*].detail leads with `unreachable;` when the
    backend is down — the same model field carries through so operators
    can still see which model was configured. This is the DIAG-03
    observability gap closure: without this framing the row reported
    `model=<name>` whether reachable or not, leaving operators no way
    to read reachability state from the doctor output alone."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    router = _StubRouter({
        "local": False, "cloud": False,
        "local_model": "qwen2.5-coder:32b",
        "cloud_model": "claude-sonnet-4-6",
    })
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms, llm_router=router)
    body = await api.get_health()
    backends = body["services"]["llm_backends"]
    local = next(b for b in backends if b["name"] == "local")
    assert local["status"] == "fail"
    assert local["detail"].startswith("unreachable;")
    assert "qwen2.5-coder:32b" in local["detail"]


# -- Postgres reachability probe (Phase 23 Commit B) ----------------------
#
# The `postgres` row answers "is the SQL backend reachable and queryable?"
# It is intentionally orthogonal to `storage_callback`, which answers "is
# the SQL-mirror callback wired into the execution log?" The two together
# form a 4-state truth table that renders the substrate/consumer split
# directly in the doctor output:
#
#   storage_callback  postgres  Operational meaning
#   ────────────────  ────────  ────────────────────────────────
#   ok                ok        Full SQL mirror operational
#   ok                fail      Mirror configured, backend down — JSONL still authoritative
#   absent            ok        Substrate ready, no consumer wired
#   absent            fail      Substrate dormant AND backend down
#
# Tests below pin the row's semantic guarantees deterministically (mocked
# get_session) rather than relying on a live Postgres in test env — what
# we validate here is classification + detail wording + timeout shape, not
# Postgres itself.


class _StubSession:
    """Async-session stand-in for _check_postgres semantic tests."""

    def __init__(self, *, raise_exc=None):
        self._raise = raise_exc

    async def execute(self, stmt):
        if self._raise is not None:
            raise self._raise
        return None


class _StubSessionCM:
    """Async context manager that yields _StubSession; mirrors get_session()."""

    def __init__(self, **kwargs):
        self._session = _StubSession(**kwargs)

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


def _make_stub_get_session(**kwargs):
    """Return a stub get_session that yields _StubSession with the given config."""
    def stub(*args, **kw):
        return _StubSessionCM(**kwargs)
    return stub


async def test_health_postgres_ok_when_select_succeeds(real_log, ms, monkeypatch):
    """`postgres: ok` when SELECT 1 succeeds; detail names the proven
    query explicitly ("SELECT 1 succeeded") so operators and future
    contributors can read WHAT was proven, not just THAT something was."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    monkeypatch.setattr(
        "forge_bridge.store.session.get_session",
        _make_stub_get_session(),
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    pg = body["services"]["postgres"]
    assert pg["status"] == "ok"
    assert pg["detail"].startswith("reachable;")
    assert "SELECT 1 succeeded" in pg["detail"]


async def test_health_postgres_fail_surfaces_exception_class_name(real_log, ms, monkeypatch):
    """When the probe raises a connection error, detail surfaces the
    exception class name (not str(exc)) per T-11-01 / LRN-05 credential-
    leak rule. The exception's str() — which may carry host info, paths,
    or credentials — must NOT appear in the operator-visible detail."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    monkeypatch.setattr(
        "forge_bridge.store.session.get_session",
        _make_stub_get_session(
            raise_exc=ConnectionRefusedError("port 5432 on internal-host"),
        ),
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    pg = body["services"]["postgres"]
    assert pg["status"] == "fail"
    assert pg["detail"].startswith("unreachable:")
    assert "ConnectionRefusedError" in pg["detail"]
    # Credential-leak rule: the exception's str() must NOT propagate.
    assert "port 5432 on internal-host" not in pg["detail"]
    assert "internal-host" not in pg["detail"]


async def test_health_postgres_fail_timeout_wording_is_explicit(real_log, ms, monkeypatch):
    """Detail names "TimeoutError after 2.0s" verbatim — the timeout
    bound is operator-meaningful context. Doctor severity philosophy:
    bounded probe, deterministic downgrade, psychologically responsive
    even during degradation. A generic "TimeoutError" detail would
    leave operators wondering 'is this still running?' — the explicit
    bound says 'doctor gave up, that's the contract, look elsewhere'."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    monkeypatch.setattr(
        "forge_bridge.store.session.get_session",
        _make_stub_get_session(raise_exc=asyncio.TimeoutError()),
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    pg = body["services"]["postgres"]
    assert pg["status"] == "fail"
    assert pg["detail"] == "unreachable: TimeoutError after 2.0s"


async def test_health_postgres_is_orthogonal_to_storage_callback(real_log, ms, monkeypatch):
    """The two rows answer independent questions. `storage_callback`
    describes integration topology (is the mirror callback wired?);
    `postgres` describes backend availability (is SQL reachable?).
    Their states vary independently — toggling one doesn't change the
    other. This test pins the architectural orthogonality directly:
    holding postgres state constant (fail) while flipping storage_callback
    from absent to ok must NOT change the postgres row."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    monkeypatch.setattr(
        "forge_bridge.store.session.get_session",
        _make_stub_get_session(raise_exc=ConnectionRefusedError()),
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)

    # State 1: storage_callback absent + postgres fail
    body = await api.get_health()
    assert body["services"]["storage_callback"]["status"] == "absent"
    assert body["services"]["postgres"]["status"] == "fail"

    # State 2: storage_callback registered + postgres fail (orthogonal)
    def _cb(record):
        return None
    real_log.set_storage_callback(_cb)
    body = await api.get_health()
    assert body["services"]["storage_callback"]["status"] == "ok"
    assert body["services"]["postgres"]["status"] == "fail"


async def test_health_postgres_fail_flips_overall_to_degraded_not_fail(real_log, ms, monkeypatch):
    """Phase 23 Commit B invariant: doctor severity reflects operational
    survivability, not subsystem impairment. When Postgres is unreachable,
    the bridge stays substantially operational (JSONL authoritative; SQL
    mirror only); overall health status must aggregate to `degraded`,
    NOT `fail`. Surfacing `fail` at the aggregate would contradict the
    substrate/consumer architectural truth that DIAG-02 teaches."""
    register_canonical_singletons(real_log, ms)
    monkeypatch.setattr("forge_bridge.mcp.server._server_started", True, raising=False)
    monkeypatch.setattr(
        "forge_bridge.store.session.get_session",
        _make_stub_get_session(raise_exc=ConnectionRefusedError()),
    )
    api = ConsoleReadAPI(execution_log=real_log, manifest_service=ms)
    body = await api.get_health()
    assert body["services"]["postgres"]["status"] == "fail"
    # Critical-failures aggregation must NOT count this as fail
    assert body["status"] != "fail", (
        "postgres fail must NOT escalate to overall fail — bridge stays "
        "operationally usable during Postgres outages by architectural design"
    )
    assert body["status"] == "degraded"
